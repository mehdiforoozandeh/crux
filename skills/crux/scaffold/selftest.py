#!/usr/bin/env python3
"""End-to-end self-test for crux — builds a dummy vault and asserts every
invariant. No GPU / tokens / SLURM; pure file ops. Exit non-zero on any failure.

    python selftest.py [--keep DIR]   # --keep leaves the demo vault for inspection
"""
import os, sys, shutil, tempfile, subprocess, argparse, hashlib, re, json, collections
import io, math, contextlib, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E
import render as R

# the suite prints → ⚠ ✓ and vault text; a cp1252 console would raise on the first one
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

_PASS, _FAIL = [], []
def check(name, cond):
    (_PASS if cond else _FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name)

def expect_error(name, fn):
    try:
        fn(); check(name, False)
    except E.CruxError:
        check(name, True)

# Vault files, skill sources and the webui are UTF-8 (— · → ✓ ⛶ all appear in them). Never
# let the platform's locale decide: Windows defaults to cp1252 and blows up on the first
# byte it has no mapping for, which is how `crux selftest` died there.
def read(p):
    with open(p, encoding="utf-8") as f: return f.read()

def edit(p, old, new, count=-1):
    with open(p, encoding="utf-8") as f: t = f.read()
    with open(p, "w", encoding="utf-8") as f:
        f.write(t.replace(old, new) if count < 0 else t.replace(old, new, count))

def node_path(root, nid):
    return E.Vault(root).get(nid)["path"]


def declare_null(root, hid, text="capacity — the extra parameters alone explain the gain"):
    """Give a fixture hypothesis a declared null and a distinct failure scenario on every
    check, one marked as discriminating — the full design a careful run carries. Spec 19
    removed the gates and the null approval, so this no longer unblocks anything; it keeps
    fixtures realistic. Idempotent.

    One helper rather than three, because a fixture that satisfies one gate and not the
    others is not a fixture of anything real."""
    n = E.Vault(root).get(hid)
    if not E._null_text(n):
        E.write_if_changed(n["path"], E.render_doc(n["fm"], E.set_null(n["body"], text)))
    n = E.Vault(root).get(hid)
    if E.node_schema(n) >= 2 and any(not s["fails_if"] for s in E.verifiable_scenarios(n["body"])):
        out, i, first = [], 0, True
        for line in n["body"].splitlines():
            out.append(line)
            if re.match(r"\s*- \[(.)\]", line):
                i += 1
                kind = E.verifiable_kind(re.match(r"\s*- \[(.)\]\s*(.*)$", line).group(2))[0]
                out.append(f"      fails-if:: world {i} where check {i} alone fails")
                if first and kind == E.DEFAULT_KIND:
                    out.append("      discriminates:: true")
                    first = False
        E.write_if_changed(n["path"], E.render_doc(n["fm"], "\n".join(out)))
    # spec 19: no approval step exists any more; the null is declared and that is all



def at_least_version(v):
    """True if the engine is at or past version `v`. Historical "this PRD bumped the version"
    asserts use this instead of a literal equality: the statement they were making is *that
    bump happened and has never been reverted*, which stays true forever, whereas `== "1.3"`
    is a claim that expires on the next PRD and drags every earlier spec's test red with it.

    Parsed here rather than via update.py's `parse_version`, which requires three components
    (it reads RELEASE tags like `0.5.1`); ENGINE_VERSION is a two-part `major.minor`."""
    key = lambda s: tuple(int(x) for x in str(s).split("."))
    return key(E.ENGINE_VERSION) >= key(v)


def run_demo(keep_dir=None):
    root = keep_dir or tempfile.mkdtemp(prefix="crux_demo_")
    if os.path.exists(os.path.join(root, ".crux.yaml")):
        shutil.rmtree(root); os.makedirs(root)
    print(f"\n# demo vault: {root}")

    # 1. init
    E.cmd_init("Demo CANDI", root, goal="Improve epigenome imputation.")
    check("init: .crux.yaml", os.path.exists(os.path.join(root, ".crux.yaml")))
    check("init: META.md", os.path.exists(os.path.join(root, "META.md")))
    check("init: project root node", os.path.exists(os.path.join(root, "demo_candi.md")))
    check("init: Obsidian-detectable (.obsidian/app.json)", os.path.exists(os.path.join(root, ".obsidian", "app.json")))

    # 2. ask root Q + sub-Q
    q1, _ = E.cmd_ask(root, "Can JEPA pretraining improve CANDI?")
    q11, _ = E.cmd_ask(root, "How to design the JEPA encoder?", parent=q1)
    v = E.Vault(root)
    check("ask: q1 parent is project", v.get(q1).parent == "root")
    check("ask: q1.1 parent is q1", v.get(q11).parent == q1)
    check("ask: Parent:: wikilink", f"Parent:: [[{v.get(q1).basename}]]" in read(v.get(q11)["path"]))
    check("ask: META lists q1", q1 in read(os.path.join(root, "META.md")))

    # 3. hypothesize two leaves; each states its expectation first (spec 19)
    h1, _, _ = E.cmd_hypothesize(root, "masked-token beats masked-stem", parent=q11, rule="all",
                                 neutral=["the published stem baseline reproduces to ±0.005"],
                                 verifiables=["imp-Spearman ≥ +0.01 vs stem", "no NaN over 5 eval epochs"],
                                 expect="masked-token gains at least +0.01 Spearman over masked-stem")
    h2, _, _ = E.cmd_hypothesize(root, "post_conv FiLM beats per_conv", parent=q11,
                                 expect="post_conv FiLM gains at least +0.005 over per_conv")
    check("hypothesize: h1 under q1.1", E.Vault(root).get(h1).parent == q11)
    check("hypothesize: 2 claim-directed verifiables + 1 control",
          E.count_verifiables_by_kind(read(node_path(root, h1)))
          == {"hypothesis": (0, 2, 0), "outcome-neutral": (0, 1, 0)})
    check("hypothesize: h2 has no verifiables, and that is allowed",
          sum(E.count_verifiables(read(node_path(root, h2)))) == 0)
    expect_error("hypothesize: no expectation is refused",
                 lambda: E.cmd_hypothesize(root, "temp bad idea", parent=q11))

    # 4. test records run links and never refuses
    E.cmd_test(root, h1, to="running", run="job 40012")
    check("test: run link recorded", "job 40012" in read(node_path(root, h1)))
    # REGRESSION: a second --run must APPEND, not vanish. The insert used to be decided by a
    # whole-body `_(none yet)_` probe, so the moment a second section shipped with a
    # placeholder of its own (## Artifacts), every run link after the first was silently
    # dropped — no error, and the CLI still printed success.
    E.cmd_test(root, h1, to="running", run="job 40013")
    links = E._run_links(read(node_path(root, h1)).split("---", 2)[-1])
    check("test: a second --run appends rather than dropping the link",
          links == ["job 40012", "job 40013"])
    check("test: the Artifacts placeholder is untouched by a run link",
          "## Artifacts" in read(node_path(root, h1)))
    E.cmd_test(root, h2, to="running")
    check("test: a hypothesis with no checks runs without refusal",
          E.derive_state(E.Vault(root), h2)["state"] == "open")

    # 5. findings: h1 strong supports -> settled; h2 moderate against -> leaning
    E.cmd_finding(root, h1, "strong", why="+0.012 Spearman over 5 seeds, control reproduced",
                  direction="supports", null="ruled-out")
    E.cmd_finding(root, h2, "moderate", why="+0.003, under the expected +0.005",
                  direction="against")
    v = E.Vault(root)
    check("finding: h1 settled · strong",
          (E.derive_state(v, h1)["state"], E.derive_state(v, h1)["confidence"]) == ("settled", "strong"))
    check("finding: h2 leaning · moderate",
          (E.derive_state(v, h2)["state"], E.derive_state(v, h2)["confidence"]) == ("leaning", "moderate"))

    # 6. ledger roll-up walks up to the question + META
    q11_text = read(node_path(root, q11))
    check("ledger: q1.1 shows h1 settled", "settled" in q11_text and h1 in q11_text)
    check("ledger: META lists the hypotheses", h1 in read(os.path.join(root, "META.md")))
    check("roll-up: q1.1 reads its children's strongest finding, capped at moderate",
          E.derive_state(v, q11)["confidence"] == "moderate")
    check("roll-up: q1 does not count its sub-question", E.derive_state(v, q1)["state"] == "open")

    # 7. a question is answered by a finding on it; a dropped one is parked
    E.cmd_finding(root, q11, "strong", answer="mask_token is the load-bearing knob; FiLM placement is noise.")
    check("answer: q1.1 settled by its own finding", E.derive_state(E.Vault(root), q11)["state"] == "settled")
    E.cmd_park(root, h2)
    check("park: h2 parked", E.derive_state(E.Vault(root), h2)["state"] == "parked")

    # 8. idempotency: re-running refresh changes nothing
    check("idempotent: refresh #1 no-op", E.refresh(root) is False)
    check("idempotent: refresh #2 no-op", E.refresh(root) is False)

    # 9. EXPERIMENTS.md has a row per hypothesis
    exp = read(os.path.join(root, "EXPERIMENTS.md"))
    check("experiments: h1 row", h1 in exp)
    check("experiments: h2 row", h2 in exp)

    # final integrity
    check("validate: demo vault clean", E.cmd_validate(root) == [])
    return root


SEED = """\
- Project: Demo Seeded — validate seed-spec ingest
  - Q: Does approach A help?
    - H: [tested] A helps overall
      - v: [x] overall metric >= +0.01 (found: +0.02)
      - finding: A helps in aggregate.
    - Q: Which variant of A is best?
      - H: variant A1 beats baseline
        - expect: A1 beats the baseline by at least 0.01
        - v: metric >= +0.01 vs baseline
        - v: no regression on control
      - H: [tested] variant A2 already beat baseline
        - v: [x] metric >= +0.01 vs baseline (found: +0.03)
        - v: [x] no regression on control
        - finding: A2 cleared both bars in job 7788.
  - Q: Is A robust to noise?
    - H: [tested] A degrades under noise
      - v: [x] AUROC drop <= 0.05
      - v: [ ] stable across 3 seeds
      - finding: mixed — AUROC held but seed variance high.
"""

def run_seed():
    print("\n# seed-spec ingest (crux init --from)")
    base = tempfile.mkdtemp(prefix="crux_seed_")
    seed_path = os.path.join(base, "seed.md")
    with open(seed_path, "w", encoding="utf-8") as f: f.write(SEED)
    root = os.path.join(base, "vault")

    E.cmd_init_from(seed_path, root)
    v = E.Vault(root)
    check("seed: vault marker written", os.path.exists(os.path.join(root, ".crux.yaml")))
    check("seed: Obsidian-detectable (.obsidian/app.json)", os.path.exists(os.path.join(root, ".obsidian", "app.json")))
    check("seed: project title", v.cfg["title"] == "Demo Seeded")
    check("seed: 3 questions", sum(1 for n in v.nodes.values() if n.type == "question") == 3)
    check("seed: 4 hypotheses", sum(1 for n in v.nodes.values() if n.type == "idea") == 4)
    # structure: q2 nests under q1; hypotheses under the right questions
    check("seed: q2 nested under q1", v.get("q2").parent == "q1")
    check("seed: q1 under project root", v.get("q1").parent == "root")
    check("seed: h2 under q2", v.get("h2").parent == "q2")
    check("seed: h4 under q3", v.get("h4").parent == "q3")
    # fresh hypothesis stays an open idea with its verifiables registered
    check("seed: h2 is fresh — no finding, derived state open",
          E.node_findings(v, "h2") == [] and E.derive_state(v, "h2")["state"] == "open")
    check("seed: h2 has 2 verifiables", sum(E.count_verifiables(read(node_path(root, "h2")))) == 2)
    # tested hypotheses are closed with mechanically-derived verdicts
    check("seed: h1 done+supported", v.get("h1").status == "done" and v.get("h1")["fm"]["verdict"] == "supported")
    check("seed: h4 done+partial", v.get("h4").status == "done" and v.get("h4")["fm"]["verdict"] == "partial")
    check("seed: h3 finding kept", "cleared both bars" in read(node_path(root, "h3")))
    check("seed: h3 evidence kept", "+0.03" in read(node_path(root, "h3")))
    q2_ledger = read(node_path(root, "q2")).split(E.LEDGER_START)[1]
    check("seed: q2 ledger lists both children with their derived states",
          "h2" in q2_ledger and "h3" in q2_ledger and "*open*" in q2_ledger)
    # spec 19 removed the review gate: materializing a seed never stores a `review` status
    check("seed: no question is tripped to review (the gate is gone)",
          all(v.get(q).status != "review" for q in ("q1", "q2", "q3")))
    check("seed: META reflects seed", "Demo Seeded" in read(os.path.join(root, "META.md")))
    check("seed: vault validates clean", E.cmd_validate(root) == [])

    # atomicity + guards
    expect_error("seed: refuses to overwrite a vault", lambda: E.cmd_init_from(seed_path, root))
    expect_error("seed: malformed outline rejected", lambda: E.parse_seed("- Q: orphan question with no project"))
    expect_error("seed: H under project rejected", lambda: E.parse_seed("- Project: X\n  - H: floating\n    - v: y"))
    bad_seed = os.path.join(base, "bad.md")
    with open(bad_seed, "w", encoding="utf-8") as f: f.write("- Project: Half\n  - Q: ok\n  - H: floating under project\n    - v: y\n")
    expect_error("seed: malformed seed rejected", lambda: E.cmd_init_from(bad_seed, os.path.join(base, "vault2")))
    check("seed: no partial vault left behind", not os.path.exists(os.path.join(base, "vault2", ".crux.yaml")))
    shutil.rmtree(base, ignore_errors=True)


def write(p, text):
    """newline="" so a fixture is byte-identical on every platform — Windows text mode would
    otherwise turn every \n into \r\n and change the file's bytes (and its sha256)."""
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8", newline="") as f:
        f.write(text)

def wiki_page(root, slug, title, summary, sources="", category="concept", extra=""):
    """Write a wiki page the way the agent would (per templates/wiki.md)."""
    fm = (f"---\ntype: wiki\ntitle: {title}\nsummary: {summary}\n"
          f"category: {category}\nsources: {sources}\ncreated: x\nupdated: x\n---\n")
    write(os.path.join(root, "wiki", slug + ".md"), fm + f"\n# {title}\n\n{summary}\n\n{extra}\n")

def wiki_probs(root):
    return [m for _, m in E.cmd_validate(root)]


def run_wiki():
    """Epic 3 — literature wiki layer: ingest + engine-rendered index + structural lint.
    Faithful to Karpathy's LLM-wiki (raw/ immutable sources → agent-compiled wiki/ pages,
    ingest/query/lint, index.md + log.md) with crux's deterministic engine owning the
    bookkeeping the pattern's #1 documented failure mode (drift) needs."""
    print("\n# wiki layer (ingest · index · structural lint)")
    root = tempfile.mkdtemp(prefix="crux_wiki_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Wiki Demo", root, goal="Exercise the literature wiki.")
    q1, _ = E.cmd_ask(root, "What do prior methods do?")

    # backward-compat: a pre-wiki vault grows no wiki artifacts, refresh stays a no-op
    check("wiki: no WIKI.md before any ingest", not os.path.exists(os.path.join(root, "WIKI.md")))
    check("wiki: refresh no-op with no wiki", E.refresh(root) is False)
    check("wiki: validate clean with no wiki", E.cmd_validate(root) == [])
    n_nodes_before = len(E.Vault(root).nodes)

    # ingest registers a PI-curated source: hash + Karpathy log line + lazy structure
    src1 = os.path.join(root, "raw", "smith2024.txt")
    write(src1, "Smith et al 2024: baseline BM25 gets 0.41 nDCG.\n")
    E.cmd_ingest(root, "raw/smith2024.txt", title="Smith et al 2024")
    check("wiki: wiki/ created lazily", os.path.isdir(os.path.join(root, "wiki")))
    check("wiki: log.md created", os.path.exists(os.path.join(root, "wiki", "log.md")))
    check("wiki: SCHEMA.md seeded", os.path.exists(os.path.join(root, "wiki", "SCHEMA.md")))
    check("wiki: WIKI.md rendered once wiki is active", os.path.exists(os.path.join(root, "WIKI.md")))
    reg = E.load_sources(root)
    with open(src1, "rb") as _f:            # hash the FILE's bytes, not a newline-normalised
        want_sha = hashlib.sha256(_f.read()).hexdigest()   # decode of them (Windows: \r\n)
    check("wiki: source registered with correct sha256", reg.get("raw/smith2024.txt", {}).get("sha256") == want_sha)
    log = read(os.path.join(root, "wiki", "log.md"))
    check("wiki: log line matches Karpathy grep prefix",
          bool(re.search(r"^## \[\d{4}-\d{2}-\d{2}\] ingest \| Smith et al 2024$", log, re.M)))

    # re-ingest unchanged file: no duplicate log entry
    E.cmd_ingest(root, "raw/smith2024.txt", title="Smith et al 2024")
    n1 = len(re.findall(r"^## \[.*\] ingest \|", read(os.path.join(root, "wiki", "log.md")), re.M))
    check("wiki: re-ingest unchanged file adds no duplicate log entry", n1 == 1)

    # uncompiled source is a lint finding until a page cites it
    check("wiki: uncompiled source flagged", any("uncompiled" in m and "smith2024" in m for m in wiki_probs(root)))

    # agent compiles an interlinked stable set (bm25 <-> transformers), both citing the source
    wiki_page(root, "bm25", "BM25", "Sparse lexical baseline; 0.41 nDCG in Smith 2024.",
              sources="raw/smith2024.txt", category="concept", extra="See [[transformers]].")
    wiki_page(root, "transformers", "Transformers", "Attention-based architecture.",
              sources="raw/smith2024.txt", category="method", extra="Baseline: [[bm25]].")
    E.refresh(root)
    wm = read(os.path.join(root, "WIKI.md"))
    check("wiki: WIKI.md lists the page + summary", "BM25" in wm and "0.41 nDCG" in wm)
    check("wiki: WIKI.md groups by category", "concept" in wm.lower())
    check("wiki: uncompiled clears once page cites source",
          not any("uncompiled" in m for m in wiki_probs(root)))

    # generated index + refresh idempotency (byte-stable, no timestamps)
    check("wiki: refresh #1 no-op after compile", E.refresh(root) is False)
    check("wiki: refresh #2 no-op after compile", E.refresh(root) is False)

    # hash drift: raw bytes change → flagged; re-ingest resolves + appends a new log line
    write(src1, "Smith et al 2024 (v2): baseline BM25 gets 0.43 nDCG after tuning.\n")
    check("wiki: source hash drift flagged", any("drift" in m and "smith2024" in m for m in wiki_probs(root)))
    E.cmd_ingest(root, "raw/smith2024.txt", title="Smith et al 2024")
    check("wiki: drift clears after re-ingest", not any("drift" in m for m in wiki_probs(root)))
    check("wiki: re-ingest of changed file appends a log line",
          len(re.findall(r"^## \[.*\] ingest \|", read(os.path.join(root, "wiki", "log.md")), re.M)) == 2)

    # ghost source lifecycle: register → raw file deleted (missing) → restore → compile a page
    write(os.path.join(root, "raw", "ghost.txt"), "temp\n")
    E.cmd_ingest(root, "raw/ghost.txt", title="Ghost")
    os.remove(os.path.join(root, "raw", "ghost.txt"))
    check("wiki: missing registered source file caught", any("missing" in m and "ghost" in m for m in wiki_probs(root)))
    write(os.path.join(root, "raw", "ghost.txt"), "temp\n")  # restore + compile so the vault ends tidy
    E.cmd_ingest(root, "raw/ghost.txt", title="Ghost")
    wiki_page(root, "ghost-note", "Ghost Note", "Cites the ghost source.", sources="raw/ghost.txt", extra="See [[bm25]].")
    wiki_page(root, "bm25", "BM25", "Sparse lexical baseline; 0.43 nDCG in Smith 2024.",
              sources="raw/smith2024.txt", category="concept", extra="See [[transformers]] and [[ghost-note]].")
    E.refresh(root)
    check("wiki: stable set validates clean", E.cmd_validate(root) == [])

    # --- dirty single-finding checks, each via a throwaway page removed afterwards ---
    # broken wiki→wiki link
    wiki_page(root, "brk", "Broken", "Links nowhere.", sources="raw/smith2024.txt", extra="See [[does-not-exist]].")
    check("wiki: broken wiki→wiki link caught", any("broken" in m and "does-not-exist" in m for m in wiki_probs(root)))
    os.remove(os.path.join(root, "wiki", "brk.md"))

    # flow-rule violation: a wiki page must NOT cite a tree node (wiki→tree)
    node_base = E.Vault(root).get(q1).basename
    wiki_page(root, "flw", "Flow", "Links the tree.", sources="raw/smith2024.txt", extra="See [[%s]]." % node_base)
    check("wiki: wiki→tree link flagged as flow violation",
          any("flow" in m and "flw" in m for m in wiki_probs(root)))
    os.remove(os.path.join(root, "wiki", "flw.md"))

    # missing required frontmatter (summary)
    write(os.path.join(root, "wiki", "nofm.md"),
          "---\ntype: wiki\ntitle: No Summary\ncategory: concept\nsources:\ncreated: x\nupdated: x\n---\n\n# No Summary\n")
    check("wiki: missing summary frontmatter caught", any("summary" in m and "nofm" in m for m in wiki_probs(root)))
    os.remove(os.path.join(root, "wiki", "nofm.md"))

    # a page citing a source file that does not exist (dangling provenance)
    wiki_page(root, "dangle", "Dangle", "Cites a non-existent source.", sources="raw/imaginary.txt")
    check("wiki: page citing missing source caught",
          any("cites missing source" in m and "dangle" in m for m in wiki_probs(root)))
    os.remove(os.path.join(root, "wiki", "dangle.md"))

    # broken tree→wiki link (direction 2): explicit wiki/ path form in a node body
    n = E.Vault(root).get(q1)
    # (spec 19 dropped `## Answer so far` from the question template; `## Question` is prose too)
    edit(n["path"], "## Question", "## Question\n\nSee [[wiki/nonexistent]].")
    check("wiki: broken tree→wiki link caught", any("broken" in m and "nonexistent" in m for m in wiki_probs(root)))
    edit(n["path"], "\n\nSee [[wiki/nonexistent]].", "")

    # orphan page: cited by nothing — the generated WIKI.md link must NOT rescue it
    wiki_page(root, "island", "Island", "Only the index links here.", sources="raw/smith2024.txt")
    E.refresh(root)
    check("wiki: WIKI.md links the orphan (index is not an inbound link)",
          "Island" in read(os.path.join(root, "WIKI.md")))
    check("wiki: orphan flagged despite WIKI.md link (Emmimal miscount guard)",
          any("orphan" in m and "island" in m for m in wiki_probs(root)))
    os.remove(os.path.join(root, "wiki", "island.md"))
    E.refresh(root)
    check("wiki: orphan clears once the page is gone", not any("orphan" in m and "island" in m for m in wiki_probs(root)))

    # wiki artifacts are never ingested as tree nodes
    v = E.Vault(root)
    check("wiki: node count unchanged by wiki pages", len(v.nodes) == n_nodes_before)
    check("wiki: no wiki page became a node", not any(n.type == "wiki" for n in v.nodes.values()))
    check("wiki: WIKI.md is not a node", "WIKI.md" not in [n["fn"] for n in v.nodes.values()])

    # once tidy, the whole vault (tree + wiki) validates clean
    check("wiki: tidy vault validates clean", E.cmd_validate(root) == [])
    shutil.rmtree(root, ignore_errors=True)


def run_wiki_migration():
    """A pre-wiki v1.0 vault must load, validate, and refresh unchanged — and its first
    ingest must lazily stand up the wiki without KeyError (evolve-crux gate 4)."""
    print("\n# wiki backward-compat / migration (old vault → first ingest)")
    root = tempfile.mkdtemp(prefix="crux_wmig_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old Vault", root)
    E.cmd_ask(root, "a question")
    edit(os.path.join(root, ".crux.yaml"), f"engine_version: {E.ENGINE_VERSION}", "engine_version: 1.0")
    check("wmig: old vault status works", isinstance(E.status_text(root), str))
    check("wmig: old vault validates clean", E.cmd_validate(root) == [])
    check("wmig: old vault refresh is a no-op", E.refresh(root) is False)
    check("wmig: old vault grows no WIKI.md", not os.path.exists(os.path.join(root, "WIKI.md")))
    write(os.path.join(root, "raw", "p.txt"), "content\n")
    E.cmd_ingest(root, "raw/p.txt", title="Paper")
    check("wmig: first ingest creates the wiki", os.path.isdir(os.path.join(root, "wiki")))
    check("wmig: first ingest renders WIKI.md", os.path.exists(os.path.join(root, "WIKI.md")))
    check("wmig: ENGINE_VERSION at or past 1.1", at_least_version("1.1"))
    shutil.rmtree(root, ignore_errors=True)


def run_version():
    print("\n# engine-version stamp + drift")
    root = tempfile.mkdtemp(prefix="crux_ver_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Versioned", root)
    # the RELEASE version (what `npx skills update` ships) is distinct from the vault-format
    # ENGINE_VERSION stamped above — the update check compares the former, never the latter
    # CRUX_VERSION must match the newest released section of the CHANGELOG. Pinning it to a
    # literal here just meant editing two places at release time and silently shipping a
    # stale version constant if you forgot one — the update check compares against it, so a
    # stale value tells every user they are up to date when they are not. Skipped when the
    # changelog isn't reachable (an installed copy of the skill has no repo root above it).
    _changelog = os.path.join(HERE, "..", "..", "..", "CHANGELOG.md")
    if os.path.isfile(_changelog):
        _newest = re.search(r"^## \[(\d+\.\d+\.\d+)\]", read(_changelog), re.M)
        check(f"version: CRUX_VERSION ({E.CRUX_VERSION}) == newest CHANGELOG release "
              f"({_newest.group(1) if _newest else 'none'})",
              bool(_newest) and _newest.group(1) == E.CRUX_VERSION)
    else:
        print("  skip   version: CRUX_VERSION vs CHANGELOG (no repo root — installed copy)")
    check("version: release and engine versions are distinct constants",
          E.CRUX_VERSION != E.ENGINE_VERSION)
    check("version: stamped at init", E.Vault(root).cfg.get("engine_version") == E.ENGINE_VERSION)
    check("version: in-sync -> no warning", E.check_and_stamp_version(root) is None)
    edit(os.path.join(root, ".crux.yaml"), f"engine_version: {E.ENGINE_VERSION}", "engine_version: 0.0")
    warn = E.check_and_stamp_version(root)
    check("version: drift -> loud warning", warn is not None and "0.0" in warn)
    check("version: drift re-stamped to current", E.Vault(root).cfg.get("engine_version") == E.ENGINE_VERSION)
    check("version: warning clears after re-stamp", E.check_and_stamp_version(root) is None)
    shutil.rmtree(root, ignore_errors=True)


def run_integrity():
    print("\n# integrity vault (validator catches corruption)")
    root = tempfile.mkdtemp(prefix="crux_intg_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Integrity", root)
    q1, _ = E.cmd_ask(root, "root q")
    h1, _, _ = E.cmd_hypothesize(root, "a hyp", parent=q1, verifiables=["x"],
                                 expect="x holds")
    check("integrity: clean baseline", E.cmd_validate(root) == [])
    # bad parent
    edit(node_path(root, h1), f"parent: {q1}", "parent: q999")
    probs = E.cmd_validate(root)
    check("integrity: bad parent caught", any("does not exist" in m for _, m in probs))
    edit(node_path(root, h1), "parent: q999", f"parent: {q1}")
    # cycle: point q1 at itself
    edit(node_path(root, q1), "parent: root", f"parent: {q1}")
    probs = E.cmd_validate(root)
    check("integrity: cycle caught", any("cycle" in m for _, m in probs))
    shutil.rmtree(root)


def _dir_bytes(root):
    """Snapshot every file's bytes under root — used to prove a call didn't touch disk."""
    out = {}
    for dp, _, fns in os.walk(root):
        for fn in sorted(fns):
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                out[p] = f.read()
    return out


def run_snapshot():
    print("\n# snapshot (read-only JSON contract for the GUI)")
    import json
    root = tempfile.mkdtemp(prefix="crux_snap_")
    shutil.rmtree(root); os.makedirs(root)

    if not (hasattr(E, "snapshot") and hasattr(E, "ledger_counts")):
        check("snapshot: engine.snapshot + engine.ledger_counts exist", False)
        shutil.rmtree(root, ignore_errors=True)
        return

    # a vault with a nested question, two hypotheses carrying findings, and a question finding
    E.cmd_init("Snap", root, goal="Test the snapshot contract.")
    q1, _ = E.cmd_ask(root, "Q one")
    q2, _ = E.cmd_ask(root, "Q two", parent=q1)
    h1, _, _ = E.cmd_hypothesize(root, "h one", parent=q2, verifiables=["a", "b"],
                                 neutral=["control"], rule="all", expect="a and b both hold")
    h2, _, _ = E.cmd_hypothesize(root, "h two", parent=q2, verifiables=["a", "b"],
                                 neutral=["control"], rule="all", expect="a and b both hold")
    E.cmd_test(root, h1, to="running"); E.cmd_test(root, h2, to="running")
    f1, _, _ = E.cmd_finding(root, h1, "strong", why="both held", direction="supports")
    f2, _, _ = E.cmd_finding(root, h2, "moderate", why="one missed", direction="against")
    fq, _, _ = E.cmd_finding(root, q1, "weak", answer="Leaning yes.")

    v = E.Vault(root)
    snap = E.snapshot(v)

    # -- top-level shape / serializability
    check("snapshot: top-level keys exact (no `queue`; `vocab` published)",
          set(snap.keys()) == {"engine_version", "crux_version", "update", "limits",
                               "project", "nodes", "tree", "vocab", "wiki", "rd", "tasks"})
    check("snapshot: crux_version carried", snap["crux_version"] == E.CRUX_VERSION)
    check("snapshot: update block is cache-shaped (never a live fetch)",
          isinstance(snap["update"], dict) and set(snap["update"]) == {"latest", "available"}
          and isinstance(snap["update"]["available"], bool))
    check("snapshot: idea nodes carry an artifacts list", isinstance(snap["nodes"][h1]["artifacts"], list))
    _w = snap.get("wiki") or {}
    check("snapshot: wiki inactive + empty on a wiki-less vault",
          _w.get("active") is False and _w.get("pages") == [] and _w.get("sources") == [])
    check("snapshot: engine_version stamped", snap["engine_version"] == E.ENGINE_VERSION)
    dumped = json.dumps(snap)
    check("snapshot: JSON-serializable + round-trips", json.loads(dumped) == snap)
    check("snapshot: project id/title", snap["project"]["id"] == "root" and snap["project"]["title"] == "Snap")
    check("snapshot: accepts a root path too", E.snapshot(root)["project"]["id"] == "root")

    # -- tree nesting exactly matches parent links; findings ride on their parent
    def tree_ids(t):
        yield t["id"]
        for c in t["children"]:
            yield from tree_ids(c)
    ids = list(tree_ids(snap["tree"]))
    tree_nodes = {nid for nid, n in v.nodes.items() if n.type != "finding"}
    check("snapshot: tree root is the project root", snap["tree"]["id"] == v.cfg["root_id"])
    check("snapshot: tree has no duplicate nodes", len(ids) == len(set(ids)))
    check("snapshot: tree covers each non-finding node once", set(ids) == tree_nodes)
    def children_match(t):
        return ([c["id"] for c in t["children"]] == v.children[t["id"]]
                and all(children_match(c) for c in t["children"]))
    check("snapshot: tree children match v.children in order", children_match(snap["tree"]))
    check("snapshot: findings are neither tree nodes nor `nodes` entries",
          not {f1, f2, fq} & set(ids) and not {f1, f2, fq} & set(snap["nodes"]))
    check("snapshot: question node surfaces its own statement ('detail')", "detail" in snap["nodes"][q2])

    # -- derived state and confidence on every question and hypothesis
    h1n, h2n = snap["nodes"][h1], snap["nodes"][h2]
    check("snapshot: h1 settled · strong, carrying its one finding",
          (h1n["state"], h1n["confidence"]) == ("settled", "strong")
          and [x["id"] for x in h1n["findings"]] == [f1])
    check("snapshot: h2 leaning · moderate, direction carried",
          (h2n["state"], h2n["confidence"]) == ("leaning", "moderate")
          and h2n["findings"][0]["direction"] == "against")
    check("snapshot: q2 (no own finding) reads its children, capped at moderate",
          (snap["nodes"][q2]["state"], snap["nodes"][q2]["confidence"]) == ("leaning", "moderate"))
    check("snapshot: q1 is decided by its own finding",
          (snap["nodes"][q1]["state"], snap["nodes"][q1]["confidence"]) == ("leaning", "weak")
          and snap["nodes"][q1]["findings"][0]["answer"] == "Leaning yes.")
    check("snapshot: every state is in the published vocabulary",
          all(n["state"] in snap["vocab"]["states"] for n in snap["nodes"].values()
              if n["type"] in ("question", "idea")))
    check("snapshot: no node carries a stored verdict", not any("verdict" in n
                                                                 for n in snap["nodes"].values()))

    # -- question nodes carry a ledger whose counts match ledger_block / ledger_counts
    q2n = snap["nodes"][q2]
    lc = E.ledger_counts(v, q2)
    lb = E.ledger_block(v, q2)
    check("snapshot: q2 ledger == ledger_counts", q2n["ledger"] == lc)
    check("snapshot: q2 counts (2 children: 1 settled, 1 leaning)",
          lc["children"] == 2 and lc["settled"] == 1 and lc["leaning"] == 1 and lc["open"] == 0)
    check("snapshot: ledger_counts consistent with ledger_block text",
          f"**{lc['children']} children**" in lb
          and f"settled {lc['settled']}" in lb and f"leaning {lc['leaning']}" in lb)

    # -- pure read: constructing a snapshot mutates nothing on disk
    before = _dir_bytes(root)
    E.snapshot(E.Vault(root))
    check("snapshot: pure read (byte-for-byte identical vault)", _dir_bytes(root) == before)

    check("snapshot: source vault validates clean", E.cmd_validate(root) == [])
    # a confidence outside the vocabulary must never decide a state (clean data contract)
    edit(node_path(root, f1), "confidence: strong", "confidence: bogus")
    check("snapshot: a non-vocabulary confidence never counts",
          E.snapshot(E.Vault(root))["nodes"][h1]["state"] == "open")
    shutil.rmtree(root, ignore_errors=True)


def run_artifacts():
    """Evidence artifacts (docs/prd/v0.5-cockpit-evidence.md §C): the `## Artifacts`
    section, the results/<hid>/ convention, and the lint that enforces a linked report
    once a hypothesis actually has files on disk."""
    print("\n# artifacts (## Artifacts + results/<hid>/ + lint)")
    root = tempfile.mkdtemp(prefix="crux_art_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Artifacts", root)
    q1, _ = E.cmd_ask(root, "does it work")
    h1, _, _ = E.cmd_hypothesize(root, "it works", parent=q1, verifiables=["metric up"], expect="the claim holds")

    # -- parsing is pure: both bullet forms, placeholder ignored, order preserved
    body = ("## Artifacts\n\n"
            "- [Full report](results/h1/report.md)\n"
            "- results/h1/curve.png the ADE20K curve\n"
            "- results/h1/per-seed.csv\n"
            "- results/h1/model.bin\n")
    arts = E.parse_artifacts(body)
    check("artifacts: parses both bullet forms", [a["path"] for a in arts] ==
          ["results/h1/report.md", "results/h1/curve.png",
           "results/h1/per-seed.csv", "results/h1/model.bin"])
    check("artifacts: markdown-link label kept", arts[0]["label"] == "Full report")
    check("artifacts: trailing text becomes the label", arts[1]["label"] == "the ADE20K curve")
    check("artifacts: kind classification (report/image/data/other)",
          [a["kind"] for a in arts] == ["report", "image", "data", "other"])
    check("artifacts: placeholder bullet is not an artifact",
          E.parse_artifacts("## Artifacts\n\n_(none yet)_\n") == [])
    check("artifacts: absent section parses to an empty list (pre-1.2 nodes)",
          E.parse_artifacts("## Findings\n\nnothing here\n") == [])

    # -- a markdown link may carry a trailing note after the closing paren. The bare-path
    # form always allowed a trailing description; the link form used to fail its regex (it
    # was anchored to end-of-line) and fall through to the bare-path split, yielding
    # path '[Identification' and a pair of validate errors naming neither cause. The rule:
    # the label comes from the link text when there is one, the trailing text otherwise.
    forms = E.parse_artifacts(
        "## Artifacts\n\n"
        "- [Full report](results/h1/report.md)\n"
        "- [Identification census](results/h1/census.md) — the strict tier is empty on both panels\n"
        "- results/h1/curve.png the ADE20K curve\n"
        "- results/h1/per-seed.csv\n")
    check("artifacts: link alone -> path, with the bracket text as the label",
          forms[0] == {"label": "Full report", "path": "results/h1/report.md", "kind": "report"})
    check("artifacts: link + trailing prose -> same path, prose dropped from the label",
          forms[1] == {"label": "Identification census", "path": "results/h1/census.md",
                       "kind": "report"})
    check("artifacts: bare path + description -> path first, description as the label",
          forms[2] == {"label": "the ADE20K curve", "path": "results/h1/curve.png",
                       "kind": "image"})
    check("artifacts: bare path alone -> label falls back to the basename",
          forms[3] == {"label": "per-seed.csv", "path": "results/h1/per-seed.csv",
                       "kind": "data"})
    check("artifacts: an empty link label falls back to the basename",
          E.parse_artifacts("## Artifacts\n\n- [](results/h1/report.md) some prose\n")
          == [{"label": "report.md", "path": "results/h1/report.md", "kind": "report"}])

    # -- a hypothesis with no results dir and no links stays clean
    check("artifacts: clean when there are no files and no links", E.cmd_validate(root) == [])

    # -- results/<hid>/ with files but no linked report -> lint error
    write(os.path.join(root, E.RESULTS_DIR, h1, "curve.png"), "notreallyapng")
    probs = [m for _, m in E.cmd_validate(root)]
    check("artifacts: results dir with files but no linked report -> problem",
          any("no report is linked" in m for m in probs))

    # -- link a report that does not exist -> different problem
    def set_artifacts(nid, block):
        p = node_path(root, nid)
        t = read(p)
        t = t.replace("## Findings", "## Artifacts\n\n" + block + "\n\n## Findings", 1) \
             if "## Artifacts" not in t else re.sub(r"## Artifacts\n\n.*?(?=\n## |\Z)",
                                                    "## Artifacts\n\n" + block + "\n", t, flags=re.S)
        with open(p, "w", encoding="utf-8") as f: f.write(t)
    set_artifacts(h1, "- results/h1/report.md")
    probs = [m for _, m in E.cmd_validate(root)]
    check("artifacts: linked artifact that does not exist -> problem",
          any("missing artifact" in m for m in probs))

    # -- an escaping path is refused whether or not the target exists
    set_artifacts(h1, "- ../../etc/passwd\n- /etc/hosts")
    probs = [m for _, m in E.cmd_validate(root)]
    check("artifacts: ../ traversal path -> problem",
          any("inside the vault" in m and ".." in m for m in probs))
    check("artifacts: absolute path -> problem",
          any("inside the vault" in m and "/etc/hosts" in m for m in probs))

    # -- the happy path: a real report under results/<hid>/ linked from the node
    write(os.path.join(root, E.RESULTS_DIR, h1, "report.md"), "# Report\n\n![c](curve.png)\n")
    set_artifacts(h1, "- [Report](results/h1/report.md)\n- results/h1/curve.png")
    check("artifacts: results dir + linked report validates clean", E.cmd_validate(root) == [])

    # -- and the same link annotated with a note validates just as clean: the reported bug
    # raised BOTH "missing artifact '[Report'" and "no report is linked" off this one bullet
    set_artifacts(h1, "- [Report](results/h1/report.md) — the strict tier is empty on both panels\n"
                      "- results/h1/curve.png")
    check("artifacts: a linked report with trailing prose validates clean",
          E.cmd_validate(root) == [])
    set_artifacts(h1, "- [Report](results/h1/report.md)\n- results/h1/curve.png")

    # -- recording a result still WARNS rather than blocking when the report is missing
    #    (spec 19: a finding replaces `close`; the warning reader is unchanged)
    h2, _, _ = E.cmd_hypothesize(root, "second", parent=q1, verifiables=["x"], neutral=["control"], expect="the claim holds")
    write(os.path.join(root, E.RESULTS_DIR, h2, "out.log"), "log\n")
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    edit(node_path(root, h2), "- [ ]", "- [x]")
    E.cmd_finding(root, h2, "moderate", why="x held", direction="supports")
    check("artifacts: a finding records the result without a report (warn, not block)",
          E.derive_state(E.Vault(root), h2)["state"] == "leaning")
    check("artifacts: the unlinked results still surface as a warning",
          any("no report" in w for w in E.artifact_warnings(root, h2)))
    check("artifacts: no warning once a report is linked", E.artifact_warnings(root, h1) == [])

    # -- snapshot carries them, resolved against disk
    write(os.path.join(root, E.RESULTS_DIR, h1, "curve.png"), "notreallyapng")
    snap_arts = E.snapshot(root)["nodes"][h1]["artifacts"]
    check("artifacts: snapshot exposes path/label/kind/exists/servable",
          len(snap_arts) == 2 and set(snap_arts[0]) == {"path", "label", "kind", "exists", "servable"}
          and snap_arts[0]["exists"] is True)
    # the cockpit must not offer a link the file route will refuse: an artifact whose
    # extension isn't servable is shown, but inert
    write(os.path.join(root, E.RESULTS_DIR, h1, "model.bin"), "weights")
    set_artifacts(h1, "- [Report](results/h1/report.md)\n- results/h1/model.bin")
    arts = {a["path"]: a for a in E.snapshot(root)["nodes"][h1]["artifacts"]}
    check("artifacts: a non-servable extension is flagged unservable",
          arts["results/h1/model.bin"]["exists"] is True
          and arts["results/h1/model.bin"]["servable"] is False
          and arts["results/h1/report.md"]["servable"] is True)
    check("artifacts: the servable set is the file route's allowlist, exactly",
          set(__import__("serve").FILE_TYPES) == set(E.SERVABLE_EXT))
    set_artifacts(h1, "- [Report](results/h1/report.md)\n- results/h1/curve.png")
    shutil.rmtree(root, ignore_errors=True)


def _refused(fn):
    try:
        fn(); return False
    except E.CruxError:
        return True


def run_update():
    """The update check (§H): every decision is a pure function tested offline with an
    injected fetcher — the suite must never touch the network."""
    print("\n# update check (offline: pure functions + injected fetcher)")
    try:
        import update as U
    except Exception as e:
        check(f"update: update.py imports cleanly (got {e!r})", False)
        return

    check("update: the suite itself runs with the network check disabled",
          os.environ.get("CRUX_NO_UPDATE_CHECK") == "1")
    check("update: parse_version", U.parse_version("v0.5.0") == U.parse_version("0.5.0") == (0, 5, 0))
    check("update: parse_version rejects junk", U.parse_version("not-a-version") is None)
    check("update: is_newer patch", U.is_newer("0.5.1", "0.5.0") is True)
    check("update: is_newer minor", U.is_newer("0.6.0", "0.5.9") is True)
    check("update: is_newer major", U.is_newer("1.0.0", "0.9.9") is True)
    check("update: is_newer equal -> False", U.is_newer("0.5.0", "0.5.0") is False)
    check("update: is_newer older -> False", U.is_newer("0.4.9", "0.5.0") is False)
    check("update: is_newer malformed -> False",
          U.is_newer("garbage", "0.5.0") is False and U.is_newer("0.6.0", "garbage") is False)

    base = tempfile.mkdtemp(prefix="crux_upd_")
    cache = os.path.join(base, "update.json")

    check("update: opt-out env suppresses the check",
          U.should_check(1000.0, {}, {"CRUX_NO_UPDATE_CHECK": "1"}) is False)
    check("update: empty cache -> check", U.should_check(1000.0, {}, {}) is True)
    check("update: inside the 24h window -> skip",
          U.should_check(1000.0, {"checked": 1000.0 - 60}, {}) is False)
    check("update: past the 24h window -> check",
          U.should_check(1000.0, {"checked": 1000.0 - U.INTERVAL - 1}, {}) is True)

    # a fetcher that raises must be swallowed whole — a command never fails on this
    boom = lambda timeout=None: (_ for _ in ()).throw(RuntimeError("no network"))
    res = U.check_now("0.5.0", cache, fetcher=boom)
    check("update: a raising fetcher is swallowed", isinstance(res, dict))
    check("update: failure records no false 'available'", res.get("available") is False)
    check("update: fetch_latest never raises on a broken opener",
          U.fetch_latest(timeout=0.01, opener=boom) is None)

    res = U.check_now("0.5.0", cache, fetcher=lambda timeout=None: "v0.6.0")
    check("update: a newer release is recorded available",
          res["latest"] == "0.6.0" and res["available"] is True)
    check("update: the cache is written and re-read",
          U.read_cache(cache)["latest"] == "0.6.0")
    n = U.notice("0.5.0", "0.6.0")
    check("update: notice names both versions", "0.5.0" in n and "0.6.0" in n)
    # crux never updates itself: the notice must hand over an actionable command for THIS
    # install, and point at the agent as the other way to do it
    check("update: notice offers the agent and a command",
          "agent" in n.lower() and ("git " in n or "npx " in n))
    # Build the checkout instead of assuming one. This assert used to hardcode the author's
    # own clone path, which made it a probe of the RUNNER's filesystem rather than a test of
    # detect_install — it passed on one machine and failed `crux selftest` everywhere else.
    # detect_install only needs `.git` to be a directory: no git binary, no subprocess.
    # Paths are realpath-normalised because detect_install resolves symlinks and macOS hands
    # out temp dirs under /var, which is itself a symlink to /private/var.
    clone = os.path.join(base, "clone")
    scaf = os.path.join(clone, "skills", "crux", "scaffold")
    os.makedirs(os.path.join(clone, ".git")); os.makedirs(scaf)
    real_clone = os.path.realpath(clone)
    check("update: a git checkout is detected as a clone, with a ff-only pull",
          U.detect_install(scaf) == ("clone", real_clone)
          and U.update_command(*U.detect_install(scaf)) == f"git -C {real_clone} pull --ff-only")

    # the realpath step is load-bearing for anyone who ran install.sh: the import path is a
    # symlink in the skills dir, while the thing you'd actually `git pull` is its target
    link = os.path.join(base, "skills_dir")
    os.makedirs(link)
    try:
        os.symlink(os.path.join(clone, "skills", "crux"), os.path.join(link, "crux"))
    except (OSError, NotImplementedError):
        print("  skip   update: symlinked install (this platform disallows symlinks)")
    else:
        check("update: a symlinked skills install resolves to its clone target",
              U.detect_install(os.path.join(link, "crux", "scaffold")) == ("clone", real_clone))

    # a copied install (npx) has no .git anywhere above it -> the skills route
    copied = os.path.join(base, "home", ".claude", "skills", "crux", "scaffold")
    os.makedirs(copied)
    check("update: a copied skills install is detected as a skills install",
          U.detect_install(copied)[0] == "skills")
    check("update: an installed (copied) skill maps to `npx skills update`",
          U.update_command("skills", "/home/x/.claude/skills/crux") == "npx skills update")
    check("update: an unrecognized layout still names both routes",
          "npx" in U.update_command("unknown", "/tmp/x") and "git" in U.update_command("unknown", "/tmp/x"))
    check("update: nothing in update.py runs an installer",
          not re.search(r"subprocess|os\.system|os\.exec|pip install",
                        read(os.path.join(HERE, "update.py"))))
    check("update: pending_notice fires from the cache alone",
          U.pending_notice("0.5.0", U.read_cache(cache)) is not None)
    check("update: pending_notice silent when current is latest",
          U.pending_notice("0.6.0", U.read_cache(cache)) is None)
    res = U.check_now("0.6.0", cache, fetcher=lambda timeout=None: "v0.6.0")
    check("update: same version is not 'available'", res["available"] is False)
    check("update: cache_path honours XDG_CACHE_HOME",   # os.path.join: \ on Windows, / elsewhere
          U.cache_path({"XDG_CACHE_HOME": os.path.join("tmp", "xdg")})
          == os.path.join("tmp", "xdg", "crux", "update.json"))

    # REGRESSION: the check must not re-hit the network on every single invocation. A short
    # command exits before a background fetch can answer, so if the throttle were only
    # stamped by the fetch's own success, `checked` would never be written and every `crux
    # status` would fire a request that is then abandoned. The window is claimed FIRST.
    c2 = os.path.join(base, "throttle.json")
    hits = []
    def slow(timeout=None):
        hits.append(1)
        return "v9.9.9"
    U.maybe_check("0.5.0", env={}, path=c2, fetcher=slow)
    check("update: the 24h window is claimed before the fetch (not by it)",
          isinstance(U.read_cache(c2).get("checked"), float))
    U.maybe_check("0.5.0", env={}, path=c2, fetcher=slow)
    check("update: a second invocation inside the window does not re-fetch", len(hits) <= 1)
    check("update: opt-out short-circuits maybe_check entirely",
          U.maybe_check("0.5.0", env={"CRUX_NO_UPDATE_CHECK": "1"}, path=c2, fetcher=slow) is None)

    # and the cockpit chip must respect the same opt-out — a user who switched the check off
    # should not be nagged by a stale cache through the GUI
    vroot = tempfile.mkdtemp(prefix="crux_upd_snap_")
    shutil.rmtree(vroot); os.makedirs(vroot)
    E.cmd_init("UpdSnap", vroot)
    os.environ["CRUX_NO_UPDATE_CHECK"] = "1"
    check("update: snapshot's update block is silent while opted out",
          E.snapshot(vroot)["update"] == {"latest": None, "available": False})
    shutil.rmtree(vroot, ignore_errors=True)

    # exactly one endpoint, and it is the releases API — nothing else is ever contacted
    urls = set(re.findall(r"https?://[^\s\"')]+", read(os.path.join(HERE, "update.py"))))
    check(f"update: the only URL in update.py is the GitHub releases API (found {urls})",
          urls == {U.LATEST_URL})
    shutil.rmtree(base, ignore_errors=True)


def run_wiki_gui():
    """Wiki tab contract (docs/prd/gui-wiki-tab.md): snapshot `wiki` key (index only,
    no bodies) + lazy /wiki/<slug>.json route (body + backlinks, reserved slugs,
    traversal-safe, pure read)."""
    print("\n# wiki GUI contract (snapshot wiki key + /wiki/<slug>.json route)")
    import json, threading, urllib.request, urllib.error, builtins
    import serve as S

    # a wiki-bearing vault with real, asymmetric inter-page links:
    # alpha -> {beta, gamma}, beta -> {alpha}, gamma -> {alpha}  (alpha has 2 inbound)
    root = tempfile.mkdtemp(prefix="crux_wgui_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("WikiGui", root, goal="Exercise the wiki GUI contract.")
    E.cmd_ask(root, "What is known?")
    write(os.path.join(root, "raw", "paper.txt"), "A paper.\n")
    E.cmd_ingest(root, "raw/paper.txt", title="A Paper")
    wiki_page(root, "alpha", "Alpha", "First concept.", sources="raw/paper.txt",
              category="concept", extra="See [[beta]] and [[gamma]].")
    wiki_page(root, "beta", "Beta", "Second concept.", sources="raw/paper.txt",
              category="method", extra="Builds on [[alpha]].")
    wiki_page(root, "gamma", "Gamma", "Third concept.", sources="raw/paper.txt",
              category="concept", extra="Contrast with [[alpha]].")
    E.refresh(root)
    pages = E.scan_wiki_pages(root)

    # -- snapshot: wiki index rides the poll — public fields only, never a body or path
    snap = E.snapshot(root)
    w = snap.get("wiki") or {}
    check("wiki-gui: snapshot carries an active wiki", isinstance(w, dict) and w.get("active") is True)
    got = {p.get("slug"): p for p in w.get("pages") or []}
    check("wiki-gui: one index entry per scanned page", sorted(got) == [p["slug"] for p in pages])
    PUBLIC = {"slug", "title", "summary", "category", "links", "sources", "hash"}
    check("wiki-gui: page entries carry exactly the public keys (no body/path/fm/fn)",
          bool(got) and all(set(p.keys()) == PUBLIC for p in got.values()))
    check("wiki-gui: page entry fields match the scan",
          bool(got) and all(got.get(p["slug"], {}).get(k) == p[k] for p in pages
                            for k in ("title", "summary", "category", "links", "sources")))
    check("wiki-gui: page hash is a non-empty string",
          bool(got) and all(isinstance(p.get("hash"), str) and p["hash"] for p in got.values()))
    reg = E.load_sources(root)
    check("wiki-gui: sources are the {date,path,title} projection of the registry",
          w.get("sources") == [{"date": r["date"], "path": rel, "title": r["title"]}
                               for rel, r in sorted(reg.items())])
    check("wiki-gui: specials flags present",
          w.get("specials") == {"index": True, "log": True, "schema": True})
    check("wiki-gui: snapshot with wiki round-trips through JSON",
          json.loads(json.dumps(snap)) == snap)

    # -- hash tracks content: editing one page moves only that page's hash
    edit(os.path.join(root, "wiki", "beta.md"), "Second concept.", "Second concept, edited.")
    got2 = {p.get("slug"): p for p in (E.snapshot(root).get("wiki") or {}).get("pages") or []}
    check("wiki-gui: editing a page changes its hash (others stable)",
          bool(got) and bool(got2)
          and got2.get("beta", {}).get("hash") not in (None, got.get("beta", {}).get("hash"))
          and got2.get("alpha", {}).get("hash") == got.get("alpha", {}).get("hash"))
    pages = E.scan_wiki_pages(root)  # re-scan after the edit; the route asserts compare to this

    # -- engine additions stay stdlib-only (top-level import statements only, so prose
    #    inside docstrings that happens to start with "from …" never counts)
    mods = set()
    for line in read(os.path.join(HERE, "engine.py")).splitlines():
        m = re.match(r"(?:import|from)\s+([a-zA-Z0-9_.]+)", line)
        if m:
            mods.add(m.group(1).split(".")[0])
    stdlib = set(getattr(sys, "stdlib_module_names", ())) or {
        "os", "sys", "json", "re", "hashlib", "datetime", "shutil", "tempfile", "argparse"}
    check("wiki-gui: engine.py stdlib-only imports", not (mods - stdlib))

    # -- the lazy route, on a live server
    free = S.find_free_port("127.0.0.1", 9020)
    httpd = S.make_server(root, port=free)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    base = f"http://127.0.0.1:{free}"

    def get(path):
        """(status, body_bytes, content_type) — HTTP errors surface as the status."""
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                return r.status, r.read(), r.headers.get("Content-Type") or ""
        except urllib.error.HTTPError as e:
            body = b""
            try:
                body = e.read() or b""
            except Exception:
                pass
            return e.code, body, ""
        except Exception:
            return -1, b"", ""

    write(os.path.join(root, "secret_sentinel.txt"), "SENTINEL-DO-NOT-SERVE\n")
    before = _dir_bytes(root)
    try:
        st, body, ctype = get("/wiki/alpha.json")
        page = json.loads(body) if st == 200 else {}
        check("wiki-gui: /wiki/alpha.json returns 200 application/json",
              st == 200 and "application/json" in ctype)
        ROUTE = {"slug", "title", "summary", "category", "sources", "updated", "body", "backlinks"}
        check("wiki-gui: route payload carries exactly the contract keys",
              bool(page) and set(page.keys()) == ROUTE)
        alpha = next((p for p in pages if p["slug"] == "alpha"), {})
        check("wiki-gui: route body equals the page's markdown body (frontmatter stripped)",
              bool(page) and page.get("body") == alpha.get("body"))
        check("wiki-gui: route metadata matches the scan",
              bool(page) and all(page.get(k) == alpha.get(k)
                                 for k in ("title", "summary", "category", "sources")))
        check("wiki-gui: updated comes from frontmatter", page.get("updated") == "x" if page else False)

        # backlinks: equal the pages whose links contain the slug, each with a mention snippet
        def backs(slug):
            s, b, _ = get(f"/wiki/{slug}.json")
            return json.loads(b).get("backlinks") if s == 200 else None
        want = {p["slug"]: sorted(q["slug"] for q in pages if p["slug"] in q["links"] and q["slug"] != p["slug"])
                for p in pages}
        got_bl = {s: backs(s) for s in want}
        check("wiki-gui: backlinks equal the pages that link each slug",
              all(isinstance(got_bl[s], list) and sorted(b["slug"] for b in got_bl[s]) == want[s]
                  for s in want))
        check("wiki-gui: asymmetric fixture degrees (alpha 2 inbound, beta 1)",
              isinstance(got_bl.get("alpha"), list) and len(got_bl["alpha"]) == 2
              and isinstance(got_bl.get("beta"), list) and len(got_bl["beta"]) == 1)
        check("wiki-gui: every backlink carries slug+title+snippet containing the [[mention]]",
              any(got_bl.values())
              and all(set(b.keys()) == {"slug", "title", "snippet"} and f"[[{s}" in b["snippet"]
                      for s in want for b in (got_bl[s] or [])))

        # reserved slugs serve the specials through the same shape: null metadata, no backlinks
        for slug, relpath in (("_index", "WIKI.md"), ("_log", os.path.join("wiki", "log.md")),
                              ("_schema", os.path.join("wiki", "SCHEMA.md"))):
            s, b, _ = get(f"/wiki/{slug}.json")
            sp = json.loads(b) if s == 200 else {}
            want_body = E.parse_doc(read(os.path.join(root, relpath)))[1]
            check(f"wiki-gui: {slug} serves {relpath.replace(os.sep, '/')} (same shape, empty backlinks)",
                  s == 200 and sp.get("body") == want_body and sp.get("backlinks") == []
                  and set(sp.keys()) == ROUTE)
        s_i, b_i, _ = get("/wiki/_index.json")
        check("wiki-gui: _index has null metadata (WIKI.md has no frontmatter)",
              s_i == 200 and json.loads(b_i).get("title") is None
              and json.loads(b_i).get("category") is None)

        # unknown + traversal-shaped slugs through the /wiki/ route specifically
        check("wiki-gui: unknown slug -> 404", get("/wiki/nope.json")[0] == 404)
        opened = []
        real_open = builtins.open
        def spy(f, *a, **kw):
            if isinstance(f, (str, bytes, os.PathLike)):
                try:
                    opened.append(os.path.abspath(os.fsdecode(f)))
                except Exception:
                    pass
            return real_open(f, *a, **kw)
        builtins.open = spy
        try:
            trav = ["/wiki/../secret_sentinel.json", "/wiki/..%2Fsecret_sentinel.json",
                    "/wiki/%2e%2e%2fsecret_sentinel.json", "/wiki//etc/hosts.json",
                    "/wiki/....//secret_sentinel.json"]
            results = [get(p) for p in trav]
        finally:
            builtins.open = real_open
        check("wiki-gui: traversal-shaped slugs -> 404", all(s == 404 for s, _, _ in results))
        check("wiki-gui: no traversal response leaks the sentinel",
              all(b"SENTINEL-DO-NOT-SERVE" not in b for _, b, _ in results))
        absroot = os.path.abspath(root)
        allowed = (os.path.join(absroot, "wiki") + os.sep, os.path.join(absroot, "WIKI.md"))
        vault_opens = [p for p in opened if p.startswith(absroot + os.sep)]
        check("wiki-gui: traversal requests open nothing outside the wiki layer",
              all(p.startswith(allowed[0]) or p == allowed[1] for p in vault_opens))
    finally:
        httpd.shutdown(); httpd.server_close()
    check("wiki-gui: pure read — vault byte-identical after all wiki routes",
          _dir_bytes(root) == before)
    shutil.rmtree(root, ignore_errors=True)


def run_serve():
    print("\n# serve (crux serve — stdlib browser cockpit host)")
    import json, socket, threading, urllib.request, urllib.error
    try:
        import serve as S
    except Exception as e:
        check(f"serve: serve.py imports cleanly (got {e!r})", False)
        return

    # -- stdlib-only: every module serve.py imports is stdlib (or the local engine/render)
    src = read(os.path.join(HERE, "serve.py"))
    mods = set()
    for line in src.splitlines():
        import re as _re
        m = _re.match(r"\s*(?:import|from)\s+([a-zA-Z0-9_.]+)", line)
        if m:
            mods.add(m.group(1).split(".")[0])
    stdlib = set(getattr(sys, "stdlib_module_names", ())) or {
        "os", "sys", "json", "socket", "http", "socketserver", "webbrowser",
        "functools", "threading", "urllib", "io", "re", "datetime", "argparse"}
    bad = mods - stdlib - {"engine", "render", "auto", "migrate4"}
    check("serve: stdlib-only imports", not bad)

    # -- context detection returns the right mode for faked env combos, no browser spawned
    check("serve: context plain", S.detect_context({}) == "plain")
    check("serve: context vscode (TERM_PROGRAM)", S.detect_context({"TERM_PROGRAM": "vscode"}) == "vscode")
    check("serve: context remote (SSH_CONNECTION)", S.detect_context({"SSH_CONNECTION": "1 2 3 4"}) == "remote")
    check("serve: context vscode+remote -> remote",
          S.detect_context({"TERM_PROGRAM": "vscode", "SSH_CONNECTION": "x"}) == "remote")

    # -- auto-open policy (inject a fake opener; a real browser is never launched)
    calls = []
    op = lambda u: calls.append(u)
    calls.clear(); S.maybe_open("http://localhost:1", "plain", force_open=None, opener=op)
    check("serve: plain mode auto-opens", calls == ["http://localhost:1"])
    calls.clear(); S.maybe_open("http://localhost:1", "vscode", force_open=None, opener=op)
    check("serve: vscode mode does not auto-open", calls == [])
    calls.clear(); S.maybe_open("http://localhost:1", "remote", force_open=None, opener=op)
    check("serve: remote mode does not auto-open", calls == [])
    calls.clear(); S.maybe_open("http://localhost:1", "plain", force_open=False, opener=op)
    check("serve: --no-open suppresses the browser", calls == [])
    calls.clear(); S.maybe_open("http://localhost:1", "remote", force_open=True, opener=op)
    check("serve: --open forces the browser", calls == ["http://localhost:1"])

    # -- URL / banner: exactly one http://localhost:<port> line is printed
    check("serve: local_url form", S.local_url(8787) == "http://localhost:8787")
    lines = S.banner_lines("http://localhost:8787", "plain")
    check("serve: banner prints exactly one URL line",
          sum(1 for l in lines if "http://localhost:8787" in l) == 1)
    check("serve: banner mentions Ctrl-C", any("Ctrl-C" in l for l in lines))
    check("serve: remote banner hints Simple Browser",
          any("Simple Browser" in l for l in S.banner_lines("http://localhost:8787", "remote")))

    # -- free port: a busy default falls back to the next free port
    busy = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    busy.bind(("127.0.0.1", 0)); busy.listen(1)
    busy_port = busy.getsockname()[1]
    p = S.find_free_port("127.0.0.1", busy_port)
    check("serve: free-port fallback skips the busy port", p > busy_port)
    busy.close()

    # -- binds 127.0.0.1, pins the requested port, and really serves the snapshot
    root = tempfile.mkdtemp(prefix="crux_serve_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Served", root, goal="serve integration")
    q1, _ = E.cmd_ask(root, "a question")
    free = S.find_free_port("127.0.0.1", 8900)
    httpd = S.make_server(root, port=free)
    check("serve: binds 127.0.0.1", httpd.server_address[0] == "127.0.0.1")
    check("serve: pins requested port", httpd.server_address[1] == free)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    try:
        base = f"http://127.0.0.1:{free}"
        with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as r:
            ctype = r.headers.get("Content-Type"); snap = json.loads(r.read())
        check("serve: /snapshot.json is application/json", ctype == "application/json")
        # the served payload is engine.snapshot plus ONE serve-side key, `migration` (spec
        # 19, ruling Q9): whether this vault still awaits the 4.0 migration
        check("serve: /snapshot.json == engine.snapshot + the migration key",
              {k: x for k, x in snap.items() if k != "migration"} == E.snapshot(root))
        check("serve: a 4.0 vault is reported migrated",
              snap.get("migration") == {"stamped": E.ENGINE_VERSION, "needed": False})
        with urllib.request.urlopen(base + "/", timeout=5) as r2:
            html = r2.read().decode("utf-8", "replace").lower()
        check("serve: serves the cockpit HTML at /", "<html" in html or "crux" in html)

        # -- conditional polling: an unchanged vault answers a matching If-None-Match
        #    with 304 (no body); a vault change flips the ETag and re-serves 200
        with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as r3:
            etag = r3.headers.get("ETag"); r3.read()
        check("serve: /snapshot.json carries an ETag", bool(etag))
        req = urllib.request.Request(base + "/snapshot.json", headers={"If-None-Match": etag or ""})
        try:
            with urllib.request.urlopen(req, timeout=5):
                check("serve: matching If-None-Match → 304", False)
        except urllib.error.HTTPError as he:
            check("serve: matching If-None-Match → 304", he.code == 304)
        E.cmd_ask(root, "a second question")
        req = urllib.request.Request(base + "/snapshot.json", headers={"If-None-Match": etag or ""})
        with urllib.request.urlopen(req, timeout=5) as r4:
            fresh = r4.headers.get("ETag"); r4.read()
        check("serve: stale If-None-Match re-serves 200 with a new ETag",
              r4.status == 200 and bool(fresh) and fresh != etag)

        # -- snapshot cache (spec 12, PRD-P4): the server must not regenerate the whole
        #    snapshot on every poll just to compute the ETag (measured: 29 ms of Python
        #    and 181 files re-read per second, ~2.4% of a core, forever). Cache keyed on
        #    a stat walk (dir-inclusive max mtime + entry count — dir mtimes catch
        #    deletions); regeneration only when the vault actually changed. Counted by
        #    wrapping engine.snapshot; the ETag stays a content hash (client contract
        #    unchanged — poll()'s If-None-Match/text-diff guards still hold).
        real_snapshot = S.engine.snapshot
        snap_calls = []
        def counting_snapshot(*a, **kw):
            snap_calls.append(1)
            return real_snapshot(*a, **kw)
        S.engine.snapshot = counting_snapshot
        try:
            import time as _time
            for _ in range(3):
                with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as rc:
                    rc.read()
            check("serve: 3 polls on an unchanged vault regenerate at most once (cache hit)",
                  len(snap_calls) <= 1)
            # invalidation — a new node regenerates exactly once and serves fresh content
            snap_calls.clear()
            q3, _ = E.cmd_ask(root, "a third question")
            t0 = _time.perf_counter()
            with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as rc:
                fresh_snap = json.loads(rc.read())
            uncached_s = _time.perf_counter() - t0   # full wall incl. the regeneration
            check("serve: a vault change invalidates the cache (regenerates once)",
                  len(snap_calls) == 1)
            check("serve: post-change content is fresh through the cache",
                  any(n.get("id") == q3 for n in fresh_snap.get("nodes", {}).values())
                  if isinstance(fresh_snap.get("nodes"), dict)
                  else q3 in json.dumps(fresh_snap))
            # deletion — max FILE mtime can stay put; the dir-mtime + entry-count half
            # of the key must catch it
            snap_calls.clear()
            q3_file = next(f for f in os.listdir(root)
                           if f.startswith(q3 + "_") and f.endswith(".md"))
            os.remove(os.path.join(root, q3_file))
            with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as rc:
                after_del = rc.read().decode("utf-8")
            check("serve: a deletion invalidates the cache", len(snap_calls) == 1)
            check("serve: the deleted node is gone from the served snapshot",
                  ('"%s"' % q3) not in after_del or q3_file not in after_del)
            # timing (soft, generous): mean of 10 cached polls vs the regenerating one
            # above — the hard numbers live in tools/bench, not in CI
            t0 = _time.perf_counter()
            for _ in range(10):
                with urllib.request.urlopen(base + "/snapshot.json", timeout=5) as rc:
                    rc.read()
            cached_mean = (_time.perf_counter() - t0) / 10
            check("serve: cached poll is not slower than a regenerating one (soft timing)",
                  cached_mean <= uncached_s * 3 + 0.05)  # generous: green on noisy CI
        finally:
            S.engine.snapshot = real_snapshot
        # source shape: the cache exists, is locked, and the key walks dirs too
        check("serve: snapshot cache is guarded by a lock", "Lock(" in src)
        check("serve: cache key is a stat walk incl. directories (vault_stat_key)",
              "vault_stat_key" in src and "os.walk" in src)

        # -- living tree (docs/prd/gui-living-tree.md): the served webui carries the
        #    view-mode toggle, the radial anchor layout, and the anchored physics sim.
        #    These asserts register the wiring; the feel (breathing, drag-settle,
        #    glide-on-refresh) is walked by hand per the PRD's manual checklist.
        with urllib.request.urlopen(base + "/index.html", timeout=5) as r5:
            idx = r5.read().decode("utf-8", "replace")
        check("webui: view-mode button in the tree toolbar (id=\"view-btn\")",
              'id="view-btn"' in idx)
        with urllib.request.urlopen(base + "/app.js", timeout=5) as r6:
            appjs = r6.read().decode("utf-8", "replace")
        check("webui: view mode persisted under crux-view", '"crux-view"' in appjs)
        check("webui: radial anchor layout (layoutRadial)", "layoutRadial" in appjs)
        check("webui: anchored tree physics (TSIM)", "TSIM" in appjs)
    finally:
        httpd.shutdown(); httpd.server_close()

    # -- the real CLI prints the URL promptly (flushed) while the server is still running, and
    # serve stays READ-ONLY even on a drifted vault (version-stamping would be a forbidden write).
    # A reader thread consumes stdout so we catch the banner even though the server then blocks.
    cfg_path = os.path.join(root, ".crux.yaml")
    edit(cfg_path, f"engine_version: {E.ENGINE_VERSION}", "engine_version: 0.9")
    cfg_before = read(cfg_path)
    cli_port = S.find_free_port("127.0.0.1", 8940)
    # decode the pipe EXPLICITLY: the banner contains "→", and `text=True` alone decodes with
    # whatever the runner's locale happens to be. A stray UnicodeDecodeError here kills the
    # reader thread, leaving an empty buffer and a failure that says nothing about why.
    proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "crux.py"), "serve", "--no-open", "--port", str(cli_port)],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, encoding="utf-8", errors="replace")
    lines = []
    def _read_banner():
        try:
            for line in proc.stdout:
                lines.append(line)
                if "http://localhost:" in line:
                    break
        except Exception as e:                      # never die silently — say what happened
            lines.append(f"<reader thread died: {e!r}>")
    tr = threading.Thread(target=_read_banner, daemon=True); tr.start()
    tr.join(timeout=30)                             # CI runners are slower than a laptop
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    buf = "".join(lines)
    ok = f"http://localhost:{cli_port}" in buf and buf.count("http://localhost:") == 1
    check("serve: `crux serve` CLI prints the URL promptly (flushed to a pipe)"
          + ("" if ok else f"  [captured: {buf[:300]!r}]"), ok)
    check("serve: read-only on a drifted vault (.crux.yaml never re-stamped)",
          read(cfg_path) == cfg_before)

    shutil.rmtree(root, ignore_errors=True)

    # ---- spec 19 (C5): the 4.0 model through the live server, and the read-only contract
    # over a FULL click-through — every route the cockpit can reach, plus every write verb a
    # client could try. Run twice: on a 4.0 vault, and on a pre-4.0 vault the cockpit cannot
    # migrate (ruling Q9: show it as-is with a banner, and never write).
    mst = getattr(S, "migration_status_of", lambda s: {"needed": None})
    check("serve: the pre-4.0 test is a pure function of the stamp",
          mst(None)["needed"] is True and mst("3.5")["needed"] is True
          and mst("1.2")["needed"] is True and mst("4.0")["needed"] is False
          and mst("4.1")["needed"] is False and mst("10.0")["needed"] is False
          and mst("not-a-version")["needed"] is True)
    check("serve: the handler defines no write verb (POST/PUT/DELETE/PATCH)",
          not any(hasattr(S.Handler, m) for m in ("do_POST", "do_PUT", "do_DELETE", "do_PATCH")))
    fs = tempfile.mkdtemp(prefix="crux_serve4_")
    shutil.rmtree(fs); os.makedirs(fs)
    E.cmd_init("Four States", fs, goal="every state renders")
    fq, _ = E.cmd_ask(fs, "does the cockpit show every state?")
    hs, _, _ = E.cmd_hypothesize(fs, "the settled one", parent=fq, expect="it holds")
    hl, _, _ = E.cmd_hypothesize(fs, "the leaning one", parent=fq, expect="it holds")
    ho, _, _ = E.cmd_hypothesize(fs, "the open one", parent=fq, expect="it holds")
    hp, _, _ = E.cmd_hypothesize(fs, "the parked one", parent=fq, expect="it holds")
    write(os.path.join(fs, E.RESULTS_DIR, hs, "report.md"), "# r\n")
    E.cmd_finding(fs, hs, "strong", why="clear margin", direction="supports",
                  evidence=[f"{E.RESULTS_DIR}/{hs}/report.md"])
    E.cmd_finding(fs, hl, "weak", why="one thin run", direction="against")
    E.cmd_park(fs, hp)

    def click_through(vroot, label):
        httpd = S.make_server(vroot, port=0)
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        base = "http://127.0.0.1:%d" % httpd.server_address[1]
        codes, snap = {}, None
        before = _dir_bytes(vroot)
        try:
            for path in ("/", "/index.html", "/app.js", "/style.css", "/vendor/motion.js",
                         "/favicon.svg", "/snapshot.json", "/auto.json", "/wiki/_index.json",
                         "/wiki/nope.json", "/rd/nope.json", "/file/.crux.yaml",
                         f"/file/{E.RESULTS_DIR}/{hs}/report.md", "/nope"):
                try:
                    with urllib.request.urlopen(base + path, timeout=5) as r:
                        codes[path] = r.status
                        body = r.read()
                        if path == "/snapshot.json":
                            snap = json.loads(body)
                except urllib.error.HTTPError as he:
                    codes[path] = he.code
            writes = []
            for verb in ("POST", "PUT", "DELETE", "PATCH"):
                for path in ("/snapshot.json", "/", "/file/x.md"):
                    req = urllib.request.Request(base + path,
                                                 data=None if verb == "DELETE" else b"x",
                                                 method=verb)
                    try:
                        with urllib.request.urlopen(req, timeout=5) as r:
                            writes.append((verb, path, r.status))
                    except urllib.error.HTTPError as he:
                        writes.append((verb, path, he.code))
        finally:
            httpd.shutdown(); httpd.server_close()
        check(f"serve: [{label}] every write verb is refused (501/405)",
              all(c in (405, 501) for _, _, c in writes))
        check(f"serve: [{label}] the click-through reaches the page and the snapshot",
              codes.get("/") == 200 and codes.get("/snapshot.json") == 200
              and codes.get("/app.js") == 200)
        check(f"serve: [{label}] a full click-through writes no byte (byte-map identical)",
              _dir_bytes(vroot) == before)
        return snap or {}

    s4 = click_through(fs, "4.0 vault")
    st4 = {nid: (s4.get("nodes") or {}).get(nid, {}).get("state") for nid in (hs, hl, ho, hp)}
    check(f"serve: the served snapshot carries all four states ({st4})",
          st4 == {hs: "settled", hl: "leaning", ho: "open", hp: "parked"})
    check("serve: the served snapshot carries confidence and findings, and no queue",
          (s4.get("nodes") or {}).get(hs, {}).get("confidence") == "strong"
          and ((s4.get("nodes") or {}).get(hl, {}).get("findings") or [{}])[0]
              .get("direction") == "against"
          and "queue" not in s4)
    check("serve: a 4.0 vault needs no migration banner",
          (s4.get("migration") or {}).get("needed") is False)

    # a pre-4.0 vault: stamped 3.5. The cockpit shows it as it is and never writes — not the
    # stamp, not a backup, not a migrated node.
    cfg = os.path.join(fs, ".crux.yaml")
    edit(cfg, f"engine_version: {E.ENGINE_VERSION}", "engine_version: 3.5")
    cfg_before = read(cfg)
    s3 = click_through(fs, "pre-4.0 vault")
    check("serve: a pre-4.0 vault is reported as awaiting migration (Q9)",
          {k: (s3.get("migration") or {}).get(k) for k in ("stamped", "needed")}
          == {"stamped": "3.5", "needed": True})
    check("serve: the pre-4.0 vault is shown as-is (its tree still renders)",
          hs in (s3.get("nodes") or {}))
    check("serve: serving a pre-4.0 vault never re-stamps it", read(cfg) == cfg_before)
    shutil.rmtree(fs, ignore_errors=True)

    # Q9 in full: on a REAL pre-4.0 example (demo_vault as it was before the migration,
    # re-stamped 3.5) the cockpit renders the migration's result in memory — migrate4.plan()
    # is pure — so the tree shows the states, confidence and Findings the migration would
    # write, under the "not migrated yet" banner, and not one byte moves.
    import selftest_migrate as SM
    import migrate4 as M4
    pre = SM.captured_demo(os.path.join(tempfile.mkdtemp(prefix="crux_srvpre_"), "v"), "3.5")
    pcfg = os.path.join(pre, ".crux.yaml")
    pcfg_before = read(pcfg)
    want = E.snapshot(os.path.join(HERE, "..", "examples", "demo_vault"))   # the migrated truth
    sp = click_through(pre, "pre-4.0 example")
    mig = sp.get("migration") or {}
    check("serve: a pre-4.0 example is flagged and previewed (needed, preview, stamp 3.5)",
          mig.get("needed") is True and mig.get("preview") is True and mig.get("stamped") == "3.5")
    pn, wn = sp.get("nodes") or {}, want["nodes"]
    shown = {nid: (pn.get(nid, {}).get("state"), pn.get(nid, {}).get("confidence"),
                   len(pn.get(nid, {}).get("findings") or [])) for nid in wn}
    truth = {nid: (n.get("state"), n.get("confidence"), len(n.get("findings") or []))
             for nid, n in wn.items()}
    check("serve: the preview shows the migrated states, confidence and Findings "
          "(== the committed 4.0 demo_vault)",
          shown == truth and any(c for _, _, c in truth.values()))
    check("serve: the preview counts the Findings the migration would write",
          mig.get("findings") == len(M4.plan(pre)["findings"]) > 0)
    check("serve: previewing never writes — the stamp is unchanged", read(pcfg) == pcfg_before)
    check("serve: previewing never writes — no backup, no .crux/ store",
          not os.path.exists(os.path.join(pre, ".crux")))

    # a plan() that raises: the cockpit falls back to the as-is view, banner still up
    asis = E.snapshot(pre)
    real_plan = M4.plan
    def boom(root):
        raise RuntimeError("plan blew up")
    M4.plan = boom
    try:
        sf = click_through(pre, "pre-4.0 example, plan raises")
    finally:
        M4.plan = real_plan
    check("serve: a plan() that raises falls back to the as-is view",
          {k: x for k, x in sf.items() if k != "migration"} == asis)
    check("serve: the fallback keeps the banner and says it is not a preview",
          (sf.get("migration") or {}).get("needed") is True
          and (sf.get("migration") or {}).get("preview") is False)
    check("serve: the fallback never writes either", read(pcfg) == pcfg_before)
    shutil.rmtree(os.path.dirname(pre), ignore_errors=True)


def run_file_route():
    """`GET /file/<vault-relative-path>` (§C): the read-only route the report reader and
    inline figures load through. Serves in-vault files byte-for-byte; refuses everything
    that could reach outside the vault or hand back an arbitrary file type."""
    print("\n# /file route (artifact + figure serving)")
    import threading, urllib.request, urllib.error
    import serve as S
    root = tempfile.mkdtemp(prefix="crux_file_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Files", root)
    q1, _ = E.cmd_ask(root, "q")
    h1, _, _ = E.cmd_hypothesize(root, "h", parent=q1, verifiables=["x"], expect="x")
    report = "# Report\n\n| a | b |\n|---|---|\n| 1 | 2 |\n\n![curve](curve.png)\n"
    write(os.path.join(root, E.RESULTS_DIR, h1, "report.md"), report)
    png = bytes([0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A]) + bytes(range(256)) * 4
    with open(os.path.join(root, E.RESULTS_DIR, h1, "curve.png"), "wb") as f:
        f.write(png)
    write(os.path.join(root, E.RESULTS_DIR, h1, "secret.env"), "TOKEN=abc\n")
    write(os.path.join(root, ".hidden", "x.md"), "hidden\n")

    free = S.find_free_port("127.0.0.1", 8960)
    httpd = S.make_server(root, port=free)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()

    def get(path):
        """-> (status, body_bytes, content_type); status is the HTTP code even on error."""
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{free}{path}", timeout=5) as r:
                return r.status, r.read(), (r.headers.get("Content-Type") or "")
        except urllib.error.HTTPError as he:
            return he.code, b"", ""
        except Exception:
            return 0, b"", ""

    try:
        st, body, ctype = get(f"/file/{E.RESULTS_DIR}/{h1}/report.md")
        check("file: serves an in-vault markdown report", st == 200 and body.decode() == report)
        check("file: markdown Content-Type", "markdown" in ctype or "text/" in ctype)
        st, body, ctype = get(f"/file/{E.RESULTS_DIR}/{h1}/curve.png")
        check("file: serves a binary figure byte-identically", st == 200 and body == png)
        check("file: png Content-Type", ctype == "image/png")
        check("file: 404 on a missing file", get(f"/file/{E.RESULTS_DIR}/{h1}/nope.md")[0] == 404)
        check("file: refuses a non-allowlisted extension",
              get(f"/file/{E.RESULTS_DIR}/{h1}/secret.env")[0] in (403, 404))
        check("file: refuses a dot-segment path", get("/file/.hidden/x.md")[0] in (403, 404))
        check("file: refuses ../ traversal", get("/file/../../etc/hosts")[0] in (400, 403, 404))
        check("file: refuses an encoded ../ traversal",
              get("/file/%2e%2e%2f%2e%2e%2fetc%2fhosts")[0] in (400, 403, 404))
        check("file: refuses an absolute path", get("/file//etc/hosts")[0] in (400, 403, 404))
        check("file: refuses the vault marker itself", get("/file/.crux.yaml")[0] in (403, 404))
        # the route is a pure read — serving never touches the vault
        before = _dir_bytes(root)
        get(f"/file/{E.RESULTS_DIR}/{h1}/report.md")
        check("file: pure read (vault byte-for-byte identical)", _dir_bytes(root) == before)
    finally:
        httpd.shutdown(); httpd.server_close()
    shutil.rmtree(root, ignore_errors=True)


def run_webui():
    print("\n# webui (frontend cockpit — served assets · pure-read · issue-#1 guard)")
    import threading, urllib.request
    import serve as S
    app_js = read(os.path.join(HERE, "webui", "app.js"))

    # -- the host serves every static asset the cockpit HTML references, not just index.html
    root = tempfile.mkdtemp(prefix="crux_webui_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Webui", root, goal="webui asset serving")
    free = S.find_free_port("127.0.0.1", 8980)
    httpd = S.make_server(root, port=free)
    t = threading.Thread(target=httpd.serve_forever, daemon=True); t.start()
    try:
        base = f"http://127.0.0.1:{free}"
        for path, ctype in (("/app.js", "javascript"), ("/style.css", "css"),
                            ("/vendor/motion.js", "javascript")):
            try:
                with urllib.request.urlopen(base + path, timeout=5) as r:
                    ok = ctype in (r.headers.get("Content-Type") or "")
            except Exception:
                ok = False
            check(f"webui: serves {path}", ok)
    finally:
        httpd.shutdown(); httpd.server_close()
    shutil.rmtree(root, ignore_errors=True)

    # -- pure-read at the browser layer: the cockpit only ever GETs (the snapshot poll, the
    #    lazy wiki-page route, the artifact/report file route, and 05.4's /auto.json run
    #    reader — each relaxation pre-registered in a PRD), never mutates the vault (no fetch
    #    method override). The COUNT is the load-bearing half: it is what makes "no undeclared
    #    route was added" checkable, so a new reader must come here and be named before it ships.
    check("webui: app.js is pure-read (four GETs: snapshot + auto + wiki page + file, no write verbs)",
          app_js.count("fetch(") == 4 and 'fetch("snapshot.json"' in app_js
          and 'fetch("auto.json"' in app_js
          and "/wiki/" in app_js and "/file/" in app_js and "method:" not in app_js)

    # -- spec 18: the Autopilot tab reads auto.cockpit()'s payload and nothing else. Every
    #    `r.<key>` (a run) and `a.<key>` (an attempt) the tab names must be a key the driver
    #    emits, so a renamed or deleted payload key cannot leave the tab reading undefined.
    tab = app_js[app_js.index("// ------------------------------------------------------- the Autopilot tab"):
                 app_js.index("// one fetch for both layers")]
    run_keys = {"anchor", "mode", "address", "direction", "bar", "baseline", "best", "attempts",
                "attempts_per_hour", "elapsed_hours", "budget_hours", "live", "stop"}
    att_keys = {"n", "id", "parent", "score", "status", "seconds", "at"}
    used_r = set(re.findall(r"\br\.([a-z_]+)", tab)) - {"ok", "headers", "text"}
    used_a = set(re.findall(r"\ba\.([a-z_]+)", tab))
    check(f"webui: the Autopilot tab reads only auto.cockpit()'s run keys "
          f"({sorted(used_r - run_keys)})", used_r and used_r <= run_keys)
    check(f"webui: ... and only its attempt keys ({sorted(used_a - att_keys)})",
          used_a and used_a <= att_keys)
    gone = [w for w in ("island", "steward", "in_flight", "portfolio", "liveness", "budget.",
                        "events", "auto-rail") if w in tab]
    check(f"webui: the Autopilot tab has no island, steward, in-flight or ledger parts ({gone})",
          not gone and "auto-rail" not in read(os.path.join(HERE, "webui", "index.html")))

    # ---------------------------------------------------------------- v0.5 cockpit contract
    style = read(os.path.join(HERE, "webui", "style.css"))
    index = read(os.path.join(HERE, "webui", "index.html"))

    # (A) the browser tab names the project, not just the app
    check("webui: tab title carries the project name",
          "document.title" in app_js and "crux cockpit: " in app_js)

    # (B) the legend is the engine's FULL vocabulary — the miss that hid `inconclusive`.
    #     Derived from the engine's own constants so the two can never drift again.
    m = re.search(r"const LEGEND = \[(.*?)\n\];", app_js, re.S)
    legend_src = m.group(1) if m else ""
    # spec 19: the vocabulary is the 4.0 one — four node states and three confidences
    expected = (["s-" + x for x in E.STATES] + ["c-" + x for x in E.CONFIDENCES])
    missing = [k for k in expected if f'"{k}"' not in legend_src]
    check(f"webui: legend covers the engine's whole vocabulary (missing: {missing})", not missing)
    stale = [k for k in re.findall(r'\["([a-z]-[a-z-]+)"', legend_src) if k not in expected]
    check(f"webui: legend carries no pre-4.0 status or verdict chip (stale: {stale})", not stale)
    # every colour the legend names must exist in BOTH themes
    vars_used = re.findall(r'"(--[a-z-]+)"', legend_src)
    # match the RULES, not the prose: style.css mentions the light selector in its header
    # comment too, so a plain split would hand back the comment as the dark theme
    _blk = lambda sel: (re.search(sel + r"\s*\{(.*?)\n\}", style, re.S | re.M) or [None, ""])[1]
    dark, light = _blk(r"^:root"), _blk(r'^:root\[data-theme="light"\]')
    unstyled = [v for v in vars_used if f"{v}:" not in dark or f"{v}:" not in light]
    check(f"webui: every legend colour is defined in both themes (missing: {unstyled})", not unstyled)

    # (C) markdown is rendered, not printed: node bodies go through the renderer, which
    #     now emits images resolved through the /file/ route
    check("webui: node detail bodies render through the markdown renderer",
          re.search(r"function bodyOr\([^)]*\)\s*\{.*?mdRender\(", app_js, re.S) is not None)
    check("webui: the markdown renderer emits images", "<img" in app_js)
    check("webui: images resolve through the file route", "fileUrl(" in app_js)
    check("webui: idea detail shows an Artifacts section", '"Artifacts"' in app_js)
    # spec 19: synthesis is gone as a node type — no reader, no "closed on" link
    check("webui: no synthesis reader or synthesis link survives",
          "function synthesisDetail" not in app_js and '"Closed on synthesis"' not in app_js)
    check("webui: a .md artifact opens the report reader", "openReport(" in app_js)
    check("webui: a hypothesis with a report offers it as a primary action",
          "report-open" in app_js and "report-open" in style)
    check("webui: figures open full size on click", "img.md-img" in app_js)

    # (D) either pane can take the whole window, in either tab
    check("webui: pane maximize state is persisted", '"crux-pane"' in app_js)
    check("webui: pane mode is applied to the body dataset", "dataset.pane" in app_js)
    check("webui: css hides the other pane in each maximized mode",
          '[data-pane="left"]' in style and '[data-pane="right"]' in style)
    check("webui: a maximize control exists for the tree, the wiki, and the detail pane",
          index.count("data-max=") >= 3)

    # (E) the search box is roomier than the old 230px, but bounded — it must not grow to
    #     swallow the toolbar, and its placeholder has to fit inside it. Spec 12 (PRD-B)
    #     wrapped the input in #search-wrap so the match counter can overlay the field;
    #     the bounded flex moved to the wrapper (amendment pre-registered in the PRD).
    sm = re.search(r"#search-wrap\s*\{[^}]*flex:\s*([\d.]+)\s+[\d.]+\s+(\d+)px", style)
    basis = int(sm.group(2)) if sm else 0
    check(f"webui: search basis is 260-320px (found {basis or 'none'})", 260 <= basis <= 320)
    check("webui: the search box does not flex-grow into the toolbar",
          bool(sm) and float(sm.group(1)) == 0)
    for ph in re.findall(r'placeholder="([^"]*)"', index) + re.findall(r'placeholder = [^;]*?"([^"]*)"', app_js):
        check(f"webui: placeholder fits the box — {ph!r} <= 24 chars", len(ph) <= 24)

    # (F) focus a specific question: collapse everything off its ancestor path
    check("webui: node focus state exists", "state.focus" in app_js)
    check("webui: focus collapses off-path branches", "focusCollapse(" in app_js)
    check("webui: focus breadcrumb is rendered", 'id="focus-crumb"' in index and "focus-crumb" in app_js)

    # (J) the idle breath is gone and the sim actually stops at rest
    check("webui: the idle breath force is removed", "BREATH" not in app_js)
    check("webui: the tree sim idles out instead of animating forever", "treeSimSettled(" in app_js)

    # -- no external assets: every src/href in webui/ is local (SVG xmlns namespace
    #    identifiers are not fetched assets and are exempt); the vendored motion file is
    #    the single allowed third-party JS, served locally.
    ext = []
    for dp, _, fns in os.walk(os.path.join(HERE, "webui")):
        for fn in fns:
            for m in re.finditer(r"(?:src|href)\s*=\s*[\"']([^\"']+)[\"']",
                                 read(os.path.join(dp, fn))):
                if m.group(1).startswith(("http://", "https://", "//")):
                    ext.append(f"{fn}: {m.group(1)}")
    check("webui: no external src/href assets", not ext)
    check("webui: vendored motion file exists and is referenced",
          os.path.exists(os.path.join(HERE, "webui", "vendor", "motion.js"))
          and "vendor/motion.js" in read(os.path.join(HERE, "webui", "index.html")))

    # -- issue #1 regression guard: capturing the pointer on the tree <svg> retargets the
    #    follow-up `click` to the svg itself, so node/toggle hit-testing (e.target.closest)
    #    silently no-ops and the whole tree goes dead. Never reintroduce it there.
    check("webui: app.js never setPointerCapture on the tree (issue #1 regression)",
          "setPointerCapture(" not in app_js)

    # -- spec 06: the detail pane leads with the summary pair and folds the long prose. The
    #    regression this guards is the one the spec diagnosed: `detail` (the whole
    #    `## Question` section) going back to being the first thing in the pane.
    css = read(os.path.join(HERE, "webui", "style.css"))
    check("webui: summaryLead is defined", "function summaryLead(" in app_js)
    check("webui: the question pane leads with the summary",
          app_js.index("summaryLead(n)") < app_js.index('foldedSection("Detail"'))
    # Scoped to ideaDetail and stated as an ORDER rather than literal adjacency: spec 09
    # inserts the one-line `## Null` between the summary and the folded Problem, which does
    # not violate what this guard is for. What it guards — Problem/Detail going back to being
    # the first thing in the pane — is asserted directly, and the "nothing bulky in between"
    # half is kept by naming exactly what may sit there.
    idea_fn = app_js.split("function ideaDetail")[1].split("\nfunction ")[0]
    between = idea_fn.split("summaryLead(n) +")[1].split('foldedSection("Problem"')[0]
    check("webui: the hypothesis pane leads with the summary too",
          "summaryLead(n) +" in idea_fn
          and idea_fn.index("summaryLead(n) +") < idea_fn.index('foldedSection("Problem"')
          # spec 19: the expectation (required) leads, then the optional null
          and re.sub(r"\s*//[^\n]*", "", between).strip().startswith('section("Expected result"')
          and 'section("Null' in between and between.count("section(") == 2)
    check("webui: the long question detail is folded, not dumped",
          'foldedSection("Detail", n.detail' in app_js and 'section("Detail", bodyOr(n.detail' not in app_js)
    check("webui: the cap comes from the engine, never hardcoded in the UI",
          "limits || {}).prose_cap" in app_js and "400" not in app_js.split("function economyBadge")[1][:400])
    check("webui: the summary styles ship", ".summary {" in css and ".sum-k {" in css)
    check("webui: the fold marker is styled for both themes", ".fold > .fold-h::before" in css)

    # -- spec 12 (PRD-A): keyboard-first canvas. Source invariants only — stdlib has no JS
    #    engine, so the behavioral half (reachability in all three layouts, camera-follow,
    #    the pointer-regression walkthrough) is the PRD's scripted MANUAL checklist. These
    #    asserts pin the structure that makes that behavior possible, and guard the two
    #    regressions a source grep CAN see: keyboard code writing spotlight classes, and
    #    the canvas losing its focusability.
    m = re.search(r'<svg id="tree"[^>]*>', index)
    svg_tag = m.group(0) if m else ""
    check("webui: the tree canvas is focusable (tabindex=\"0\")", 'tabindex="0"' in svg_tag)
    check("webui: the tree canvas is an ARIA tree with a non-empty label",
          'role="tree"' in svg_tag and bool(re.search(r'aria-label="[^"]+"', svg_tag)))
    check("webui: keyboard focus ring under :focus-visible, not clipped (outline-offset -2px)",
          bool(re.search(r"#tree:focus-visible\s*\{[^}]*outline:", style))
          and "outline-offset: -2px" in style)
    check("webui: nodes are ARIA treeitems carrying selection + expansion state",
          'role="treeitem"' in app_js and "aria-selected=" in app_js and "aria-expanded=" in app_js)
    check("webui: the canvas tracks the selection via aria-activedescendant (set and cleared)",
          app_js.count("aria-activedescendant") >= 2)
    kbm = re.search(r"function onTreeKeydown\(e\)\s*\{([\s\S]*?)\n\}", app_js)
    kb_src = kbm.group(1) if kbm else ""
    check("webui: a tree keydown handler exists and is bound to the svg",
          bool(kbm) and 'svg.addEventListener("keydown", onTreeKeydown)' in app_js)
    check("webui: the handler covers Space + Enter and preventDefaults (Space must not scroll)",
          '" "' in kb_src and '"Enter"' in kb_src and "preventDefault" in kb_src)
    check("webui: arrows are orientation-relative (radial/top-down vs left-right maps)",
          "function keyNavMap" in app_js
          and 'state.viewMode === "radial"' in app_js.split("function keyNavMap")[1][:300]
          and '{ child: "ArrowDown", parent: "ArrowUp"' in app_js
          and '{ child: "ArrowRight", parent: "ArrowLeft"' in app_js)
    check("webui: selection is the one keyboard cursor — every move goes through selectNode",
          "selectNode(" in kb_src)
    check("webui: the keyboard path never writes the spotlight classes",
          not any(c in kb_src for c in ('"hov"', '"cold"', '"hot"')))
    check("webui: sibling endpoints stop — no wrap arithmetic in the keyboard handler",
          "%" not in kb_src)
    check("webui: keyboard motion cannot light the hover spotlight (kbNav guard, cleared by a real pointer move)",
          "_kbNav = true" in kb_src
          and bool(re.search(r'addEventListener\("pointerover"[\s\S]{0,500}_kbNav\) return', app_js))
          and bool(re.search(r'pointermove[^\n]*_kbNav = false', app_js)))
    check("webui: Enter opens the detail pane and hands it focus (D6)",
          'id="detail-content" tabindex="-1"' in index
          and '$("detail-content").focus()' in kb_src and 'setPane("split")' in kb_src)

    # -- spec 12 (PRD-B): search that cycles. Enter advances with wrap, Shift+Enter goes
    #    back, a counter sits in the field. ONE match-set function feeds the cycle and the
    #    counter in both tabs, in deterministic order (D2: tree walk / wiki index order),
    #    over visible nodes only (D3). Behavior (order, wrap feel, counter accuracy) is the
    #    PRD's manual checklist; these pin the structure and the two regressions.
    sf = re.search(r"function searchMatches\(\)\s*\{([\s\S]*?)\n\}", app_js)
    sf_src = sf.group(1) if sf else ""
    check("webui: one match-set function feeds cycling and the counter in both tabs",
          bool(sf) and app_js.count("searchMatches()") >= 3)
    check("webui: tree matches are the deterministic walk over visible nodes",
          "state.snap.tree" in sf_src and "state.collapsed.has" in sf_src
          and "matchNode" in sf_src and "matchWiki" in sf_src)
    check("webui: Enter advances, Shift+Enter goes back",
          "cycleSearch(e.shiftKey ? -1 : 1)" in app_js)
    check("webui: the cycle wraps in both directions",
          bool(re.search(r"\+ dir \+ m\.length\) % m\.length", app_js)))
    check("webui: the single-shot first-match jump is gone (regression)",
          "Object.keys(state.positions).find(" not in app_js
          and "wikiPages().find(matchWiki)" not in app_js)
    check("webui: a match counter lives in the search field",
          'id="search-wrap"' in index and 'id="search-count"' in index
          and '$("search-count")' in app_js and "#search-count" in style)
    check("webui: the counter reads position / total while cycling",
          '`${i + 1} / ${m.length}`' in app_js)
    check("webui: a new query restarts the cycle",
          bool(re.search(r'addEventListener\("input"[\s\S]{0,200}matchId = null', app_js)))

    # -- spec 12 (PRD-C): the theme follows the OS until you touch it. A blocking <head>
    #    stamp (before the stylesheet) kills the wrong-theme first-paint flash; app.js
    #    follows prefers-color-scheme LIVE until the first explicit ☀/☾ press, which
    #    writes the preference that sticks. The flash itself and the live OS-flip are the
    #    PRD's manual checklist (they need a real browser + OS appearance toggle).
    head_html = index.split("</head>")[0]
    stamp = re.search(r"<script>([\s\S]*?)</script>", head_html)
    stamp_src = stamp.group(1) if stamp else ""
    check("webui: a blocking theme stamp sits in <head> before the stylesheet",
          bool(stamp) and head_html.index("<script>") < head_html.index('href="style.css"'))
    check("webui: the stamp resolves saved-preference-else-OS and writes data-theme",
          "crux-theme" in stamp_src and "prefers-color-scheme" in stamp_src
          and "dataset.theme" in stamp_src)
    check("webui: app.js follows the OS theme live",
          'matchMedia("(prefers-color-scheme: light)").addEventListener("change"' in app_js)
    check("webui: an explicit choice sticks — the listener defers to the saved preference",
          'if (localStorage.getItem("crux-theme")) return;' in app_js)
    check("webui: the unconditional-dark boot is gone (regression)",
          'applyTheme(localStorage.getItem("crux-theme") === "light" ? "light" : "dark")' not in app_js)
    check("webui: the stylesheet header documents the real theme behavior",
          "before first paint" in style and "prefers-color-scheme" in style)

    # -- spec 12 (PRD-D): the type scale. Pane steps 12 / 16 / 21 px (a perfect fourth —
    #    a step under ~1.2× does not read as a step, which was the complaint), and the
    #    chrome consolidated to three NAMED sizes carried as variables so drift is
    #    visible. Exempt by decision D8: SVG canvas text (.node/.wnode — those px sizes
    #    feed the canvas measureText geometry in app.js), the pane's own em-driven
    #    content, and the A/A/A size-hint glyphs (iconography that depicts size).
    steps = {m.group(1): float(m.group(2)) for m in re.finditer(
        r'#detail-content\[data-font="(\w+)"\]\s*\{\s*font-size:\s*([\d.]+)px', style)}
    check(f"webui: the pane scale is 12 / 16 / 21 (found {steps})",
          steps == {"small": 12.0, "medium": 16.0, "large": 21.0})
    check("webui: the default pane size IS the medium step",
          bool(re.search(r"#detail-content\s*\{[^}]*font-size:\s*16px", style)))
    check("webui: every pane step reads as a step (ratio >= 1.2)",
          len(steps) == 3 and steps["medium"] / steps["small"] >= 1.2
          and steps["large"] / steps["medium"] >= 1.2)
    check("webui: the three chrome sizes are named variables (10 / 11.5 / 12.5)",
          "--fs-ui: 12.5px" in style and "--fs-ui-sm: 11.5px" in style
          and "--fs-ui-xs: 10px" in style)
    exempt = re.compile(r"(\.node|\.wnode|#detail-content|#detail-fontctl button\[data-font)")
    strays = []
    for m in re.finditer(r"([^{}]+)\{([^}]*)\}", style):
        sel = m.group(1).strip().splitlines()[-1].strip()
        if exempt.search(sel):
            continue
        for px in re.findall(r"font-size:\s*([\d.]+)px", m.group(2)):
            strays.append(f"{sel}: {px}px")
    check(f"webui: chrome carries no stray px font-size — all through the vars (strays: {strays[:4]})",
          not strays)

    # -- spec 12 perf (PRD-P1): the structural-vs-cosmetic split. A change that does not
    #    add, remove or move a node never calls renderTree() (measured: the full rebuild
    #    is 10.9 ms where the identical class swap is 0.19 ms — 55×). Selection, the
    #    review queue, search dimming and the legend filter all go through ONE in-place
    #    helper; renderTree() stays structural-only and still bakes the same classes, so
    #    the two paths cannot disagree. Latency itself (< 2 ms tree-side, ruling P-D7) is
    #    measured by tools/bench/paint_probe.js, not asserted here — stdlib has no JS.
    def fn_src(name):
        m2 = re.search(r"function %s\([^)]*\)\s*\{([\s\S]*?)\n\}" % re.escape(name), app_js)
        return m2.group(1) if m2 else ""
    sel_src = fn_src("selectNode")
    check("webui: selectNode never rebuilds — no renderTree()/layout() in its body",
          bool(sel_src) and "renderTree(" not in sel_src and "layout(" not in sel_src)
    check("webui: selectNode swaps cosmetic state in place",
          "applyCosmeticState(" in sel_src)
    sq_src = fn_src("showOverview")
    check("webui: showOverview never rebuilds — no renderTree()/layout() in its body",
          bool(sq_src) and "renderTree(" not in sq_src and "layout(" not in sq_src
          and "applyCosmeticState(" in sq_src)
    cos_src = fn_src("applyCosmeticState")
    check("webui: the cosmetic helper toggles dim / hit / selected on existing elements",
          '"dim"' in cos_src and '"hit"' in cos_src and '"selected"' in cos_src
          and "classList.toggle" in cos_src)
    check("webui: the in-place swap keeps the ARIA selection truthful (PR #13 contract)",
          "aria-selected" in cos_src and "aria-activedescendant" in cos_src)
    check("webui: the helper derives dim/hit from the SAME predicates nodeSVG bakes in",
          "matchNode(" in cos_src and "filterHit(" in cos_src
          and "state.filter" in fn_src("filterHit")
          and "filterHit(" in fn_src("nodeSVG")
          and "statusClass(" in fn_src("filterHit") and "confClass(" in fn_src("filterHit"))
    as_src = fn_src("applySearch")
    check("webui: the tree search path dims by class toggle, not by rebuild",
          "applyCosmeticState(" in as_src and "renderTree(" not in as_src)
    check("webui: search input is debounced ~120 ms with a single trailing timer (P-D6)",
          bool(re.search(r"SEARCH_DEBOUNCE_MS = 1[0-9]{2}\b", app_js))
          and bool(re.search(r'addEventListener\("input"[\s\S]{0,400}setTimeout\(flushSearch, SEARCH_DEBOUNCE_MS\)', app_js)))
    check("webui: Enter and Escape flush the debounce (cycling acts on the typed text)",
          bool(re.search(r'"Escape"[^\n]*flushSearch\(\)', app_js))
          and bool(re.search(r'flushSearch\(\);[\s\S]{0,80}cycleSearch\(', app_js)))
    lg_src = app_js.split('$("legend").addEventListener')[1].split('$("legend-btn")')[0]
    check("webui: the legend filter is a class toggle too (P-D10) — chips never rebuild",
          "applyCosmeticState(" in lg_src and "renderTree(" not in lg_src)
    check("webui: renderTree still bakes every cosmetic class (the paths cannot drift)",
          '(dimmed ? " dim" : "")' in app_js and '(matches ? " hit" : "")' in app_js
          and "${sel}" in app_js)

    # -- spec 12 perf (PRD-P2): the hover spotlight + the backdrop-filter ruling. The
    #    old handler wrote 199 classes per pointerover, fired ~12× per node crossed (no
    #    same-node guard), and started a 180 ms opacity animation on ~98 groups — a
    #    full-tree repaint held twice per node, re-sampled by up to nine blur overlays.
    #    PI rulings, final: blur dropped on the overlays (P-D1: one near-opaque token),
    #    fade dropped (P-D2 — a single spot class still animates every node if the
    #    per-node transition survives), faithful semantics (P-D3: hovered node AND its
    #    direct neighbors stay lit, exactly as before). Frame rates are tools/bench
    #    territory; these pin the structure.
    check("webui: no backdrop-filter declaration survives anywhere (PI ruling, final)",
          "backdrop-filter:" not in style)   # the colon: prose may explain the ban, no rule may use it
    check("webui: overlays share the one near-opaque token (P-D1)",
          re.search(r"--overlay:\s*color-mix\(in srgb, var\(--panel\) 9[0-9]%", style)
          and style.count("var(--overlay)") >= 8)
    hov_src = app_js.split('\nsvg.addEventListener("pointerover"')[1] \
                    .split('svg.addEventListener("pointerout"')[0]
    check("webui: same-node guard — the spotlight fires once per node crossing",
          "_hovId" in hov_src and bool(re.search(r"if \(id === _hovId\) return", hov_src)))
    check("webui: the 199-write sweep is gone — no full node scan, no cold class",
          'querySelectorAll(".node")' not in hov_src and '"cold"' not in hov_src
          and "classList.toggle" not in hov_src)
    check("webui: edge heat narrows to the hovered node's own edges",
          'data-p="' in hov_src and 'data-c="' in hov_src)
    check("webui: one spot class on the canvas + hov/nbr marks (P-D3 faithful)",
          '"spot"' in hov_src and '"nbr"' in hov_src and '"hov"' in hov_src)
    check("webui: tree nodes carry no opacity transition (P-D2 — the held repaint)",
          not re.search(r"\.node\s*\{[^}]*transition:[^}]*opacity", style))
    check("webui: the spot dim rule keeps the hovered node and its neighbors lit",
          bool(re.search(r"#tree\.spot \.node:not\(\.hov\):not\(\.nbr\)\s*\{[^}]*opacity", style)))
    check("webui: a rebuild resets the spotlight (no stale canvas-level dim)",
          bool(re.search(r"function renderTree\(\)[\s\S]{0,1200}clearSpot\(\)", app_js)))

    # -- spec 12 perf (PRD-P3): onSnapshot diffs and patches instead of rebuilding.
    #    Any byte change used to run layout() + renderTree() + renderDetail() (21.4 ms,
    #    up to 1 Hz while an agent writes — and the detail rebuild reset the reader's
    #    scroll and replayed its entrance animations). Ruling P-D5, two tiers: a
    #    structural signature gates layout/renderTree entirely; geometry-neutral changes
    #    (status/verdict/verifiable-state flips) patch just the changed node groups; the
    #    detail pane re-renders only when what IT shows changed. The signature's honesty
    #    is asserted below by tying its field list to the draw path's actual reads.
    sig_src = fn_src("treeSignatures")
    check("webui: a structural/cosmetic snapshot signature exists", bool(sig_src))
    draw_src = "".join(fn_src(f) for f in
                       ("nodeSVG", "computeGeom", "statusClass", "confClass", "dirOf",
                        "verifDots", "vBadgeClass", "bodyLabel", "rootLabel"))
    drawn_fields = sorted(set(re.findall(r"\bn\.([a-z_]+)\b", draw_src)))
    sig_missing = [f for f in drawn_fields if f not in sig_src]
    check(f"webui: every field the draw path reads is in the signature (missing: {sig_missing})",
          bool(drawn_fields) and not sig_missing)
    os_src = fn_src("onSnapshot")
    check("webui: onSnapshot gates layout()+renderTree() on the structural signature",
          "treeSignatures()" in os_src
          and bool(re.search(r"if \(structural\)[\s\S]{0,200}renderTree\(\)", os_src))
          and os_src.count("renderTree()") == 1     # the one call sits inside the gate
          and os_src.count("layout()") == 1)
    check("webui: geometry-neutral changes patch single node groups in place",
          "patchNodeEl(" in os_src and "outerHTML" in fn_src("patchNodeEl")
          and "nodeSVG(" in fn_src("patchNodeEl"))
    check("webui: a patched node re-enters the sim's element cache",
          "TSIM.els[" in fn_src("patchNodeEl"))
    check("webui: the detail pane re-renders only when its own content changed",
          "function detailKeyOf" in app_js
          and "detailKeyOf() !== state._detailKey" in os_src
          and "state._detailKey = detailKeyOf()" in fn_src("renderDetail"))
    check("webui: the legend is not rebuilt on every poll (content is filter-static)",
          "renderLegend()" not in os_src or "_legendRendered" in os_src)
    check("webui: the match counter still rides every accepted snapshot (PR #13 contract)",
          "updateMatchCounter()" in os_src)

    # ---- spec 19 (C5): the cockpit renders the 4.0 model. A node is painted by its DERIVED
    # state (fill) and its confidence (stroke); a hypothesis also shows the direction of the
    # finding that decides it. The review queue, the synthesis detail and the acceptance
    # badges are gone — the engine no longer has any of them to publish.
    check("webui: a question or hypothesis is classed by its derived state",
          '"s-" + n.state' in fn_src("statusClass"))
    check("webui: ... and by its confidence",
          '"c-" + n.confidence' in fn_src("confClass") and "confClass(n)" in fn_src("nodeSVG"))
    no_state_rule = [x for x in E.STATES if not re.search(r"\.s-%s\b[^{]*\{" % x, style)]
    no_conf_rule = [x for x in E.CONFIDENCES if not re.search(r"\.c-%s\b[^{]*\{" % x, style)]
    check(f"webui: style.css has a rule per state (missing: {no_state_rule})", not no_state_rule)
    check(f"webui: style.css has a rule per confidence (missing: {no_conf_rule})", not no_conf_rule)
    gm = re.search(r"const DIR_GLYPH = \{(.*?)\};", app_js, re.S)
    no_glyph = [d for d in E.DIRECTIONS if not gm or f'"{d}"' not in gm.group(1)
                and f"{d}:" not in gm.group(1)]
    check(f"webui: every finding direction has a glyph (missing: {no_glyph})", not no_glyph)
    dvars = ["--d-" + d for d in E.DIRECTIONS]
    no_dvar = [x for x in dvars if f"{x}:" not in dark or f"{x}:" not in light]
    check(f"webui: every direction colour is defined in both themes (missing: {no_dvar})",
          not no_dvar)
    gone = [w for w in ("review-btn", "showQueue", "updateReviewBtn", "queueDetail",
                        "snap.queue", "tb.queue", "taskGateDetail") if w in app_js + index + style]
    check(f"webui: the review queue is gone from the cockpit ({gone})", not gone)
    gone = [w for w in ("awaiting your acceptance", "task accept", "pending_gate", "t.accepted",
                        "awaiting the PI", "null_approved", "VERDICTS", "n.verdict")
            if w in app_js]
    check(f"webui: no acceptance badge or verdict reading survives ({gone})", not gone)
    check("webui: the overview replaces the queue as the empty-selection pane",
          "function overviewDetail" in app_js and 'id="overview-btn"' in index
          and "overviewDetail()" in fn_src("renderDetail"))
    fsec = fn_src("findingsSection")
    check("webui: findings are listed in the node pane, not drawn as tree nodes",
          bool(fsec) and "findingsSection(n)" in fn_src("questionDetail")
          and "findingsSection(n)" in fn_src("ideaDetail")
          and "finding" not in fn_src("layout"))
    check("webui: a question finding shows its answer and no direction; a hypothesis "
          "finding shows its direction",
          "f.answer" in fsec and "f.direction" in fsec and 'n.type === "idea"' in fsec)
    check("webui: the finding that decides the state is marked",
          "state_finding" in fsec)
    check("webui: a finding's evidence links open through the read-only file route",
          "f.evidence" in fsec and "fileUrl(" in app_js.split("function evidenceLink")[1][:900]
          if "function evidenceLink" in app_js else False)
    check("webui: a parked node says so in the pane", "parked" in fn_src("stateBadges"))
    # ruling Q9: a pre-4.0 vault is shown as-is, under a banner, and never migrated here
    check("webui: the not-migrated banner exists and reads the serve-side flag",
          'id="migrate-banner"' in index and "snap.migration" in app_js
          and "not migrated yet" in app_js and "any crux write command migrates it" in app_js)


def run_economy():
    """Spec 06 — node economy. The engine has always pushed toward more rigor and never
    toward less volume; these are the checks that push back. The negative cases carry the
    weight: anything can flag everything, so what matters is that a verifiable-heavy node,
    a fresh node, and a question at exactly the fan-out cap all stay silent."""
    print("\n# node economy (summary schema · prose cap · fan-out back-pressure)")
    root = tempfile.mkdtemp(prefix="crux_econ_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Economy", root)
    q1, _ = E.cmd_ask(root, "Does the cap hold?")
    h1, _, _ = E.cmd_hypothesize(root, "it holds", parent=q1, verifiables=["x"], expect="the claim holds")

    # -- 1. the summary schema ships in both templates
    qtext, htext = read(node_path(root, q1)), read(node_path(root, h1))
    check("economy: question template carries ## ELI5", "## ELI5" in qtext)
    check("economy: question template carries ## TL;DR", "## TL;DR" in qtext)
    check("economy: idea template carries ## ELI5", "## ELI5" in htext)
    check("economy: idea template carries ## TL;DR", "## TL;DR" in htext)
    check("economy: ELI5 precedes TL;DR in a question", qtext.index("## ELI5") < qtext.index("## TL;DR"))
    check("economy: summary sections lead the body (before ## Question)",
          qtext.index("## TL;DR") < qtext.index("## Question"))

    # -- 2. a fresh node is well under the cap: template placeholders must not eat the budget
    check("economy: fresh question is under the cap", E.prose_words(qtext, "question") < E.PROSE_CAP)
    check("economy: fresh idea is under the cap", E.prose_words(htext, "idea") < E.PROSE_CAP)
    check("economy: a fresh vault raises no warning", E.validation_report(root)["warnings"] == [])
    check("economy: the cap is 400 words", E.PROSE_CAP == 400)

    # -- 3. prose over the cap warns, exactly once, and never as a hard problem
    edit(node_path(root, q1), "## Question\n\nDoes the cap hold?",
         "## Question\n\nDoes the cap hold? " + " ".join(["padding"] * 500))
    rep = E.validation_report(root)
    check("economy: over-cap question warns exactly once",
          len([w for w in rep["warnings"] if w["id"] == q1]) == 1)
    check("economy: the warning names the actual word count",
          any("504" in w["message"] for w in rep["warnings"] if w["id"] == q1))
    check("economy: an over-cap node is a warning, not a problem", rep["problems"] == [])
    check("economy: cmd_validate still returns a bare problems list (back-compat)",
          E.cmd_validate(root) == [])

    # -- 4. the generated ledger sits *under* `## Answer so far`; counting it would make
    #       every busy question over-cap purely for having children
    ledgery = ("## ELI5\n\nx\n\n## TL;DR\n\ny\n\n## Question\n\nshort\n\n## Answer so far\n\nbrief\n\n"
               + E.LEDGER_START + "\n" + " ".join(["ledgerword"] * 900) + "\n" + E.LEDGER_END + "\n")
    check("economy: the generated ledger is excluded from the count",
          E.prose_words(ledgery, "question") < 20)

    # -- 5. structured sections are free. This is the criterion that keeps the cap from
    #       punishing thoroughness in the one place crux wants it.
    heavy = ("## ELI5\n\nshort\n\n## TL;DR\n\nshort\n\n## Problem Statement\n\nshort\n\n"
             "## Idea / Hypothesis\n\nshort\n\n## Verifiables\n\n"
             + "\n".join(f"- [ ] check {i} " + " ".join(["tok"] * 20) for i in range(40))
             + "\n\n## Planned Intervention\n\nshort\n\n## Run Links\n\n_(none yet)_\n\n## Artifacts\n\n"
             + "\n".join(f"- results/h/f{i}.png figure {i} " + " ".join(["tok"] * 10) for i in range(40))
             + "\n\n## Findings\n\nshort\n")
    check("economy: 1000+ words of verifiables and artifacts do not trip the cap",
          E.prose_words(heavy, "idea") < E.PROSE_CAP)

    # -- 6. fan-out. N=5 unrun hypotheses under one question; the back-pressure fires on the
    #       call that would breach it, not after.
    check("economy: the fan-out cap is 5", E.FANOUT_MAX == 5)
    q2, _ = E.cmd_ask(root, "How many is too many?")
    ids, quiet = [], True
    for i in range(5):
        hid, _, warn = E.cmd_hypothesize(root, f"idea {i}", parent=q2, expect="the claim holds")
        ids.append(hid); quiet = quiet and warn is None
    check("economy: no back-pressure while under the cap", quiet)
    check("economy: exactly 5 unrun hypotheses is within the cap",
          [w for w in E.validation_report(root)["warnings"] if w["id"] == q2] == [])
    h6, _, warn6 = E.cmd_hypothesize(root, "idea 6", parent=q2, expect="the claim holds")
    check("economy: hypothesize warns when the new node breaches the cap", warn6 is not None)
    check("economy: the back-pressure names the cap", warn6 is not None and "5" in warn6)
    check("economy: 6 unrun hypotheses trips one fan-out warning",
          len([w for w in E.validation_report(root)["warnings"] if w["id"] == q2]) == 1)
    E.cmd_test(root, ids[0], "staged", run="queued job 1")
    E.cmd_test(root, ids[1], "staged", run="queued job 2")
    check("economy: staged children do not count as unrun",
          [w for w in E.validation_report(root)["warnings"] if w["id"] == q2] == [])

    # -- 7. the check selector
    check("economy: --check=tree skips the economy warning",
          E.validation_report(root, ["tree"])["warnings"] == [])
    rep = E.validation_report(root, ["economy"])
    check("economy: --check=economy reports the cap warning",
          any(w["id"] == q1 for w in rep["warnings"]))
    check("economy: --check=economy records the selection", rep["checks"] == ["economy"])
    check("economy: --check=fanout isolates the fan-out check",
          all(w["id"] != q1 for w in E.validation_report(root, ["fanout"])["warnings"]))
    expect_error("economy: an unknown check name is a CruxError, not a traceback",
                 lambda: E.validation_report(root, ["nope"]))
    check("economy: the check registry is the seven documented names",
          tuple(E.CHECKS) == ("tree", "wiki", "economy", "fanout", "rd", "tasks", "glossary"))

    # -- 8. the cockpit contract
    snap = E.snapshot(root)
    check("economy: snapshot exposes eli5 on a question", "eli5" in snap["nodes"][q1])
    check("economy: snapshot exposes tldr on a question", "tldr" in snap["nodes"][q1])
    check("economy: snapshot exposes eli5 on an idea", "eli5" in snap["nodes"][h1])
    check("economy: snapshot exposes tldr on an idea", "tldr" in snap["nodes"][h1])
    check("economy: an unwritten summary reads empty, not as the placeholder",
          snap["nodes"][q1]["eli5"] == "")
    edit(node_path(root, q1), E._section_placeholder("ELI5"),
         "Whether short nodes stay short.")
    check("economy: a written ELI5 reaches the snapshot",
          E.snapshot(root)["nodes"][q1]["eli5"] == "Whether short nodes stay short.")

    check("economy: ENGINE_VERSION at or past 1.3", at_least_version("1.3"))
    shutil.rmtree(root, ignore_errors=True)


def run_economy_migration():
    """A pre-1.3 vault has no summary sections at all. It must load, validate and render —
    the cap is a warning, never a wall, and the engine never rewrites an old node."""
    print("\n# node economy — a pre-1.3 vault still reads")
    root = tempfile.mkdtemp(prefix="crux_emig_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old Format", root)
    q1, _ = E.cmd_ask(root, "an old question")
    h1, _, _ = E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"],
                                 expect="x holds")
    # strip the 1.3 schema back out and stamp the old engine version
    for nid in (q1, h1):
        p = node_path(root, nid)
        with open(p, encoding="utf-8") as f:
            t = f.read()
        t = re.sub(r"## ELI5\n\n.*?\n\n## TL;DR\n\n.*?\n\n", "", t, flags=re.S)
        with open(p, "w", encoding="utf-8") as f:
            f.write(t)
    edit(os.path.join(root, ".crux.yaml"), f"engine_version: {E.ENGINE_VERSION}", "engine_version: 1.2")

    check("emig: the fixture really has no summary sections", "## ELI5" not in read(node_path(root, q1)))
    check("emig: pre-1.3 vault validates clean", E.cmd_validate(root) == [])
    check("emig: pre-1.3 vault raises no economy warning", E.validation_report(root)["warnings"] == [])
    check("emig: prose_words tolerates the missing sections",
          E.prose_words(read(node_path(root, q1)), "question") > 0)
    snap = E.snapshot(root)
    check("emig: a missing ELI5 reads as empty string", snap["nodes"][q1]["eli5"] == "")
    check("emig: a missing TL;DR reads as empty string", snap["nodes"][h1]["tldr"] == "")
    check("emig: status still renders the tree", "an old question" in E.status_text(root))
    check("emig: the derived state still reads (review was removed in 4.0)",
          E.derive_state(E.Vault(root), q1)["state"] == "open")
    warn = E.check_and_stamp_version(root)
    check("emig: a 1.2 vault reports drift", warn is not None and "1.2" in warn)
    check("emig: drift re-stamps to the current ENGINE_VERSION",
          E.Vault(root).cfg.get("engine_version") == E.ENGINE_VERSION)
    shutil.rmtree(root, ignore_errors=True)


def run_agent_cli():
    """Spec 06's agent toolbelt: --json on every verb an agent loop drives, plus --strict
    and --check on validate. In the CLI rather than in agent-private scripts, so this suite
    can assert it and the PI can run any of it by hand."""
    print("\n# agent CLI surface (--json · --strict · --check)")
    import json as J
    root = tempfile.mkdtemp(prefix="crux_json_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Agent Surface", root)

    def cli(*argv):
        # Decode as UTF-8 explicitly. crux.py reconfigures its own stdout/stderr to UTF-8, so
        # that is what comes back over the pipe — but `text=True` alone decodes with the
        # PARENT's locale encoding, which on Windows is cp1252 and turns the ⚠ into mojibake.
        return subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + list(argv),
                              capture_output=True, cwd=root, encoding="utf-8", errors="replace")

    def as_json(r):
        """The parsed stdout, or None. `--json` means stdout is JSON and nothing else —
        a stray print alongside it is exactly what breaks an agent's parse."""
        try:
            return J.loads(r.stdout)
        except Exception:
            return None

    r = cli("ask", "Is the JSON parseable?", "--json")
    q1 = as_json(r)
    check("json: ask emits parseable JSON", isinstance(q1, dict) and "id" in q1 and "file" in q1)
    check("json: ask exits 0", r.returncode == 0)

    r = cli("hypothesize", "it is", "-p", q1["id"], "-v", "stdout parses",
            "-n", "the parser round-trips a known-good payload",
            "--fails-if", "the parser accepts anything", "--discriminates",
            "--fails-if", "the known-good payload was itself broken",
            "--null", "chance — the payload happened to parse",
            "--expect", "stdout parses as JSON", "--json")
    h1 = as_json(r)
    check("json: hypothesize emits parseable JSON", isinstance(h1, dict) and "id" in h1)
    check("json: hypothesize reports its fan-out headroom", isinstance(h1, dict) and "warning" in h1)

    r = cli("test", h1["id"], "--to", "running", "--json")
    t = as_json(r)
    check("json: test emits parseable JSON", isinstance(t, dict) and t.get("status") == "running")

    r = cli("finding", h1["id"], "-d", "supports", "-c", "strong", "-w", "it parsed",
            "--null", "ruled-out", "--json")
    fi = as_json(r)
    check("json: finding emits parseable JSON with the derived state",
          isinstance(fi, dict) and fi.get("state") == "settled" and fi.get("id"))

    r = cli("finding", q1["id"], "-c", "moderate", "-a", "Yes, it parses.", "--json")
    fq = as_json(r)
    check("json: a question finding emits parseable JSON",
          isinstance(fq, dict) and fq.get("state") == "leaning")

    r = cli("park", h1["id"], "--json")
    pk = as_json(r)
    check("json: park emits parseable JSON", isinstance(pk, dict) and pk.get("state") == "parked")
    cli("park", h1["id"], "--undo")

    r = cli("status", "--json")
    st = as_json(r)
    check("json: status emits the whole snapshot", isinstance(st, dict) and "nodes" in st and "tree" in st)
    r = cli("status", q1["id"], "--json")
    st1 = as_json(r)
    check("json: status <id> emits one node", isinstance(st1, dict) and st1.get("id") == q1["id"])
    check("json: status <id> carries the summary keys", isinstance(st1, dict) and "eli5" in st1)

    # -- validate: the report shape, the tiers, and the exit codes
    r = cli("validate", "--json")
    va = as_json(r)
    check("json: validate emits the full report shape",
          isinstance(va, dict) and {"ok", "checks", "problems", "warnings"} <= set(va))
    check("json: a clean vault reports ok", isinstance(va, dict) and va["ok"] is True)
    check("json: validate exits 0 on a clean vault", r.returncode == 0)

    # push one node over the cap, then prove the two tiers differ only under --strict
    edit(node_path(root, q1["id"]), "## Question\n\nIs the JSON parseable?",
         "## Question\n\nIs the JSON parseable? " + " ".join(["padding"] * 500))
    r = cli("validate")
    check("strict: a warning alone still exits 0", r.returncode == 0)
    check("strict: the warning is printed with a ⚠ marker", "⚠" in r.stdout)
    r = cli("validate", "--strict")
    check("strict: --strict turns the same warning into exit 1", r.returncode == 1)
    r = cli("validate", "--check=tree")
    check("check: --check=tree exits 0 with the economy warning suppressed",
          r.returncode == 0 and "⚠" not in r.stdout)
    r = cli("validate", "--check=economy", "--strict")
    check("check: --check=economy --strict exits 1", r.returncode == 1)
    r = cli("validate", "--check=economy", "--json")
    ve = as_json(r)
    check("check: the selection is echoed in the report",
          isinstance(ve, dict) and ve["checks"] == ["economy"])
    r = cli("validate", "--check=nope")
    check("check: an unknown check name is a clean error, not a traceback",
          r.returncode == 1 and "Traceback" not in r.stderr and "nope" in r.stderr)

    # -- ingest goes last on purpose: registering a source that no wiki page cites yet is a
    #    real `wiki` problem, so it would make every "clean vault" assertion above dirty.
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    with open(os.path.join(root, "raw", "paper.md"), "w", encoding="utf-8") as f:
        f.write("# A source\n")
    r = cli("ingest", "raw/paper.md", "--json")
    ing = as_json(r)
    check("json: ingest emits parseable JSON", isinstance(ing, dict) and "state" in ing)

    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- deck payload (spec 11 / PRD 11a)
DECK_PROTOCOL_PLACEHOLDER = "_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_"

def run_deck():
    import json
    print("\n# deck payload (crux deck <anchor> --json)")
    CRUX = os.path.join(HERE, "crux.py")
    check("deck: ENGINE_VERSION at or past 1.4", at_least_version("1.4"))

    base = tempfile.mkdtemp(prefix="crux_deck_")
    root = os.path.join(base, "vault")
    E.cmd_init("Deck Demo", root, goal="Prove the deck payload.")
    qtop, _ = E.cmd_ask(root, "Top question")
    qmid, _ = E.cmd_ask(root, "Mid question", parent=qtop)
    qsib, _ = E.cmd_ask(root, "Sibling question", parent=qtop)
    h1, _, _ = E.cmd_hypothesize(root, "first hyp", parent=qmid, neutral=["control"],
                                 verifiables=["bar one", "bar two"], rule="all",
                                 null="capacity — width alone explains the gain",
                                 fails_if=["the width-matched arm also clears it",
                                           "bar two moves on its own",
                                           "the shared preprocessing path changed"],
                                 discriminates=[True, False, False],
                                 expect="bar one and bar two both clear")
    h2, _, _ = E.cmd_hypothesize(root, "second hyp", parent=qmid, expect="it moves")
    # the optional ## Protocol section (new in 1.4) — fill it on the anchor
    edit(node_path(root, qmid), DECK_PROTOCOL_PLACEHOLDER, "Rules locked up front.")
    # close h1 with a (found: …) parenthetical on the first bar
    edit(node_path(root, h1), "- [ ] bar one", "- [x] bar one   (found: +0.02)")
    edit(node_path(root, h1), "- [ ] bar two", "- [x] bar two")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] control", "- [x] [outcome-neutral] control")
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    # the headline metric: frontmatter the 3.x close step wrote, which a 4.0 vault keeps
    n1 = E.Vault(root).get(h1)
    n1["fm"]["metric"] = "imp +0.02"
    E.write_if_changed(n1["path"], E.render_doc(n1["fm"], n1["body"]))
    # evidence on disk: metrics.json + report + a figure, report linked in ## Artifacts
    rd = os.path.join(root, "results", h1)
    write(os.path.join(rd, "metrics.json"), json.dumps({
        "task_a": {"delta": {"value": 3.3, "ci": [1.9, 4.7], "n": 3, "unit": "points"}},
        "design": {"train_n": {"value": "1.20M"}}}))
    write(os.path.join(rd, "report.md"), "# report\n\nsynthetic.\n")
    write(os.path.join(rd, "curve.png"), "png-bytes")
    edit(node_path(root, h1), f"results/{h1}/curve.png -->\n_(none yet)_",
         f"results/{h1}/curve.png -->\n- [Report](results/{h1}/report.md)\n"
         f"- results/{h1}/curve.png the loss curve")
    # spec 19: no close step — the run's result is a Finding on the hypothesis
    E.cmd_finding(root, h1, "strong", why="both bars cleared and the control held",
                  direction="supports", null="ruled-out",
                  evidence=[f"results/{h1}/report.md"])
    E.refresh(root)

    # determinism — in-process and through the CLI
    p1 = E.deck_payload(root, qmid)
    s1 = json.dumps(p1, ensure_ascii=False)
    s2 = json.dumps(E.deck_payload(root, qmid), ensure_ascii=False)
    check("deck: byte-identical across runs (in-process)", s1 == s2)
    argv = [sys.executable, CRUX, "deck", qmid, "--json"]
    r1 = subprocess.run(argv, capture_output=True, cwd=root)
    r2 = subprocess.run(argv, capture_output=True, cwd=root)
    check("deck: byte-identical across runs (CLI)", r1.returncode == 0 and r1.stdout == r2.stdout)
    check("deck: CLI stdout is exactly the payload", r1.stdout.decode("utf-8").strip() == s1)
    check("deck: engine_version stamped in the payload", p1["engine_version"] == E.ENGINE_VERSION)
    check("deck: payload carries no absolute path and no timestamp",
          root not in s1 and E.now()[:10] not in s1)
    # spec 19: synthesis and verdict are gone; the payload reads Findings and derived state
    check("deck: no payload key is named verdict or synthesis",
          '"verdict":' not in s1 and '"synthesis":' not in s1
          and '"verdict":' not in json.dumps(E.deck_payload(root, h1)))

    # lineage / siblings / children
    check("deck: lineage is root -> parent, in order",
          [x["id"] for x in p1["lineage"]] == ["root", qtop])
    check("deck: project lineage entry carries the Goal",
          p1["lineage"][0]["answer_so_far"] == "Prove the deck payload.")
    check("deck: siblings listed, anchor excluded",
          [x["id"] for x in p1["siblings"]] == [qsib])
    kids = p1["children"]
    check("deck: children are the anchor's subtree in order", [x["id"] for x in kids] == [h1, h2])
    k1 = kids[0]
    check("deck: a child with a Finding carries its derived state, confidence + metric",
          k1["state"] == "settled" and k1["confidence"] == "strong"
          and k1["metric"] == "imp +0.02")
    check("deck: a hypothesis child carries findings[] with direction, confidence, why, evidence",
          [(f["direction"], f["confidence"], f["why"], f["evidence"]) for f in k1["findings"]]
          == [("supports", "strong", "both bars cleared and the control held",
               [f"results/{h1}/report.md"])])
    check("deck: a child with no Finding is open and carries an empty findings[]",
          kids[1]["state"] == "open" and kids[1]["confidence"] is None
          and kids[1]["findings"] == [])
    check("deck: verifiable `found` parsed from the (found: …) parenthetical",
          k1["verifiables"][0] == {"text": "bar one", "state": "met", "kind": "hypothesis",
                                   "found": "+0.02",
                                   "fails_if": "the width-matched arm also clears it",
                                   "discriminates": True})
    check("deck: verifiable without a parenthetical has found None",
          k1["verifiables"][1] == {"text": "bar two", "state": "met", "kind": "hypothesis",
                                   "found": None, "fails_if": "bar two moves on its own",
                                   "discriminates": False})
    check("deck: the outcome-neutral control reaches the payload as its own kind",
          k1["verifiables"][2] == {"text": "control", "state": "met",
                                   "kind": "outcome-neutral", "found": None,
                                   "fails_if": "the shared preprocessing path changed",
                                   "discriminates": False})
    # This assert used to say the opposite. It was the tripwire spec 15 left pointing at 09
    # ("dropped by PI ruling; spec 15/09 owns it"), and 09.2 owns it now — so it is REWRITTEN
    # to assert the field is present and named, never deleted. Deleting it would erase the
    # only record of why the field was once refused.
    check("deck: the verifiable carries its failure scenario (spec 09)",
          k1["verifiables"][0]["fails_if"] and k1["verifiables"][0]["discriminates"] is True
          and all("fails_if" in x and "discriminates" in x for x in k1["verifiables"]))
    check("deck: child artifacts parsed with kinds",
          any(a["path"] == f"results/{h1}/report.md" and a["kind"] == "report"
              for a in k1["artifacts"]))
    check("deck: rd is present and empty on a vault with no RD layer", p1["rd"] == [])
    check("deck: anchor question + protocol surfaced",
          p1["anchor"]["question"] == "Mid question"
          and p1["anchor"]["protocol"] == "Rules locked up front.")
    check("deck: placeholder answer-so-far reads as empty", p1["anchor"]["answer_so_far"] == "")
    check("deck: scope counts hypotheses by derived state",
          p1["scope"]["executed"] == 1 and p1["scope"]["open"] == 1
          and p1["scope"]["parked"] == 0
          and p1["scope"]["by_state"] == {"open": 1, "leaning": 0, "settled": 1, "parked": 0})

    # figures + metrics
    figs = p1["figures"]
    check("deck: figures list every results file",
          sorted(f["path"] for f in figs) == sorted([f"results/{h1}/curve.png",
                f"results/{h1}/metrics.json", f"results/{h1}/report.md"]))
    caps = {f["path"]: f["caption"] for f in figs}
    check("deck: figure caption from the matching artifact label",
          caps[f"results/{h1}/curve.png"] == "the loss curve")
    check("deck: unlabeled results file gets an empty caption",
          caps[f"results/{h1}/metrics.json"] == "")
    check("deck: metrics in defined order (hid, then key path)",
          [m["addr"] for m in p1["metrics"]] == [f"{h1}#design.train_n", f"{h1}#task_a.delta"])
    md = p1["metrics"][1]
    check("deck: metric leaf carried through untouched",
          md["value"] == 3.3 and md["ci"] == [1.9, 4.7] and md["n"] == 3 and md["unit"] == "points")
    check("deck: string-typed metric value survives (formatted displays)",
          p1["metrics"][0]["value"] == "1.20M")

    # the address resolver and its distinct failure kinds
    check("deck: resolve_address returns the leaf",
          E.resolve_address(root, f"{h1}#task_a.delta")["value"] == 3.3)
    def kind_of(addr):
        try:
            E.resolve_address(root, addr)
            return None
        except E.AddressError as e:
            return e.kind
    check("deck: unresolvable — missing metrics file", kind_of("h99#x.y") == "missing-file")
    check("deck: unresolvable — missing key path", kind_of(f"{h1}#task_a.nope") == "missing-key")
    check("deck: unresolvable — not a leaf (no value)", kind_of(f"{h1}#task_a") == "missing-value")
    check("deck: unresolvable — malformed address", kind_of("no-hash-here") == "bad-address")

    # spec 19: a question is answered by a Finding on it (synthesis is gone). Before one
    # exists the anchor is open; after, its answer text rides in findings[] with NO direction
    check("deck: a question anchor with no Finding of its own leans on its child's, capped",
          p1["anchor"]["findings"] == [] and p1["anchor"]["state"] == "leaning"
          and p1["anchor"]["confidence"] == "moderate")
    E.cmd_finding(root, qmid, "strong", answer="what qmid settled",
                  evidence=[f"results/{h1}/report.md"])
    pa = E.deck_payload(root, qmid)["anchor"]
    check("deck: a question Finding lands with its answer text and no direction",
          [(f["answer"], f["confidence"], f["evidence"]) for f in pa["findings"]]
          == [("what qmid settled", "strong", [f"results/{h1}/report.md"])]
          and all("direction" not in f for f in pa["findings"]))
    check("deck: the question anchor reads its own Finding — settled, strong",
          pa["state"] == "settled" and pa["confidence"] == "strong")

    # wiki pages linked from the anchor
    E.ensure_wiki(root)
    wiki_page(root, "deck-bg", "Deck background", "why decks exist")
    edit(node_path(root, qmid), "Mid question\n\n## Protocol",
         "Mid question — see [[deck-bg]].\n\n## Protocol")
    E.refresh(root)
    pw = E.deck_payload(root, qmid)["wiki"]
    check("deck: wiki pages linked from the anchor are indexed",
          pw == [{"slug": "deck-bg", "title": "Deck background", "path": "wiki/deck-bg.md"}])

    # hypothesis / childless anchors — always emit (PI ruling #1)
    ph = E.deck_payload(root, h1)
    check("deck: hypothesis anchor — no children, its own findings[] and state",
          ph["children"] == [] and "synthesis" not in ph
          and ph["anchor"]["state"] == "settled"
          and [f["direction"] for f in ph["anchor"]["findings"]] == ["supports"])
    check("deck: hypothesis anchor carries its own evidence fields",
          len(ph["anchor"]["verifiables"]) == 3 and ph["anchor"]["question"] is None)
    check("deck: hypothesis anchor scopes metrics to itself",
          {m["addr"].split("#")[0] for m in ph["metrics"]} == {h1})
    check("deck: no-children question anchor still emits",
          E.deck_payload(root, qsib)["children"] == [])

    # bad anchor
    expect_error("deck: unknown anchor refused", lambda: E.deck_payload(root, "zz9"))
    rb = subprocess.run([sys.executable, CRUX, "deck", "zz9", "--json"],
                        capture_output=True, cwd=root)
    check("deck: CLI unknown anchor -> exit 1, silent stdout",
          rb.returncode == 1 and rb.stdout.strip() == b"")
    ra = subprocess.run([sys.executable, CRUX, "slides", qmid, "--json"],
                        capture_output=True, cwd=root)
    rd2 = subprocess.run([sys.executable, CRUX, "deck", qmid, "--json"],
                         capture_output=True, cwd=root)
    check("deck: `slides` alias emits the identical payload", ra.stdout == rd2.stdout)
    check("deck: vault still validates clean after all of it", E.cmd_validate(root) == [])

    # migration proof (PI ruling #5): a pre-11 (engine 1.3) vault loads with only the
    # drift warning, and deck runs on it with empty metrics/figures
    old = os.path.join(base, "old_vault")
    E.cmd_init("Old Vault", old, goal="g")
    oq, _ = E.cmd_ask(old, "Old question")
    cfgp = os.path.join(old, ".crux.yaml")
    edit(cfgp, f"engine_version: {E.ENGINE_VERSION}", "engine_version: 1.3")
    ro = subprocess.run([sys.executable, CRUX, "status"], capture_output=True, text=True, encoding="utf-8", cwd=old)
    check("deck migration: pre-11 vault loads with only the drift warning",
          ro.returncode == 0 and "v1.3" in ro.stderr)
    check("deck migration: drift re-stamps to the current engine",
          f"engine_version: {E.ENGINE_VERSION}" in read(cfgp))
    check("deck migration: pre-11 vault validates clean", E.cmd_validate(old) == [])
    rq = subprocess.run([sys.executable, CRUX, "deck", oq, "--json"],
                        capture_output=True, text=True, encoding="utf-8", cwd=old)
    pq = json.loads(rq.stdout) if rq.returncode == 0 and rq.stdout.strip() else {}
    check("deck migration: deck runs on a metrics-less vault, metrics/figures empty",
          rq.returncode == 0 and pq.get("metrics") == [] and pq.get("figures") == [])

    # the committed scaling_vault fixture: reference-deck addresses resolve
    sv = os.path.join(HERE, "..", "examples", "scaling_vault")
    svc = os.path.join(base, "scaling_copy")
    shutil.copytree(sv, svc)
    # tree check only: the wiki tier is legitimately non-clean on a fresh copy (the raw/
    # PDFs are fetched by fetch_sources.sh, not committed); the new results/ fixtures live
    # under the tree tier's artifact lint, which must stay clean
    check("deck fixture: scaling_vault tree+artifacts validate clean",
          E.cmd_validate(svc, checks=["tree"]) == [])
    sp = E.deck_payload(svc, "q1")
    addrs = [m["addr"] for m in sp["metrics"]]
    check("deck fixture: reference-deck addresses resolve",
          all(a in addrs for a in ("h1#task_a.delta", "h2#equal_compute.delta",
                                   "h3#equal_data.delta", "h1#design.seeds")))
    check("deck fixture: q1 protocol filled", sp["anchor"]["protocol"] != "")
    check("deck fixture: linked reports appear in figures",
          any(f["path"] == "results/h1/report.md" for f in sp["figures"]))
    check("deck fixture: formatted display value stored as a string",
          E.resolve_address(svc, "h1#design.train_n_baseline")["value"] == "1.20M")
    # the migrated (4.0) scaling vault: verdicts became Findings, the synthesis a q1 Finding
    sj = json.dumps(sp)
    check("deck fixture: the migrated payload carries no verdict or synthesis key",
          '"verdict":' not in sj and '"synthesis":' not in sj)
    sk = {c["id"]: c for c in sp["children"]}
    check("deck fixture: migrated hypotheses carry their Findings with direction + confidence",
          [(f["direction"], f["confidence"]) for f in sk["h1"]["findings"]]
          == [("supports", "strong")]
          and [(f["direction"], f["confidence"]) for f in sk["h2"]["findings"]]
          == [("mixed", "weak")]
          and all(f["why"] and isinstance(f["evidence"], list)
                  for c in sk.values() for f in c["findings"]))
    check("deck fixture: q1's migrated synthesis is a strong question Finding, no direction",
          sp["anchor"]["state"] == "settled" and len(sp["anchor"]["findings"]) == 1
          and "direction" not in sp["anchor"]["findings"][0]
          and sp["anchor"]["findings"][0]["answer"])
    shutil.rmtree(base, ignore_errors=True)


# ------------------------------------------- deck verify / refresh / validate --check=decks (PRD 11b)
def _mini_deck(hid, extra=""):
    """A minimal synthetic deck exercising every verify bucket: chart src rows, data-src
    spans (incl. entity minus + thousands separator + string-typed value), a literal
    escape, a data-derived span, a bare numeral, and geometry numerals in script."""
    return f"""<!doctype html><html><head><title>mini</title>
<style>.x{{width:100px;margin:12px}}</style></head><body>
<div id="deck">
<section class="slide">
  <h1>No numbers on this slide</h1>
</section>
<section class="slide">
  <p>delta <span data-src="{hid}#m.delta">+3.3</span>
  over <span data-src="{hid}#m.share">50,000</span> examples,
  neg <span data-src="{hid}#m.neg">&minus;4.6</span>,
  ratio <span data-src="{hid}#d.ratio">1.20M</span>,
  the <span data-src="literal">95%</span> interval,
  combo <span data-derived="{hid}#m.delta,{hid}#m.share">165000</span>.{extra}</p>
</section>
</div>
<script>
const ROWS=[
  {{lab:'first', src:'{hid}#m.delta', v: 3.3, lo: 1.9, hi: 4.7}},
];
const W=1140,H=430,pad=52;   // geometry numerals must never be flagged
</script>
</body></html>
"""

def run_deck_verify():
    import json
    print("\n# deck verify / refresh / validate --check=decks")
    CRUX = os.path.join(HERE, "crux.py")
    base = tempfile.mkdtemp(prefix="crux_dv_")
    root = os.path.join(base, "vault")
    E.cmd_init("Verify Demo", root, goal="g")
    qv, _ = E.cmd_ask(root, "Check question")
    hv, _, _ = E.cmd_hypothesize(root, "checked hyp", parent=qv, verifiables=["bar"],
                                 expect="the bar clears")
    write(os.path.join(root, "results", hv, "metrics.json"), json.dumps({
        "m": {"delta": {"value": 3.3, "ci": [1.9, 4.7]},
              "share": {"value": 50000},
              "neg":   {"value": -4.6}},
        "d": {"ratio": {"value": "1.20M"}}}))
    write(os.path.join(root, "results", hv, "report.md"), "# r\n\nsynthetic.\n")
    edit(node_path(root, hv), f"results/{hv}/curve.png -->\n_(none yet)_",
         f"results/{hv}/curve.png -->\n- [Report](results/{hv}/report.md)")
    deck = os.path.join(root, "presentations", qv, "index.html")
    write(deck, _mini_deck(hv, extra=" A bare numeral 42 sits here."))

    # --- verify: buckets on a current deck -----------------------------------------
    rep = E.deck_verify(root, deck)
    check("verify: current deck has no mismatches",
          rep["mismatch"] == [] and rep["unresolvable"] == [])
    check("verify: derived listed, inputs checked, result not recomputed",
          len(rep["derived"]) == 1 and not rep["mismatch"])
    check("verify: bare numeral lands in unsourced with its slide",
          [ (u["numeral"], u["slide"]) for u in rep["unsourced"] ] == [("42", 2)])
    check("verify: literal escape is not unsourced and not a failure",
          len(rep["literal"]) == 1)
    check("verify: entity minus + comma + string values all match after normalization",
          all(u["numeral"] == "42" for u in rep["unsourced"]))
    r0 = subprocess.run([sys.executable, CRUX, "deck", "--verify", deck], capture_output=True,
                        text=True, encoding="utf-8", cwd=root)
    check("verify CLI: plain verify passes with the unsourced numeral listed",
          r0.returncode == 0 and "42" in r0.stdout)
    rs = subprocess.run([sys.executable, CRUX, "deck", "--verify", deck, "--strict"],
                        capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("verify CLI: --strict fails on the unsourced numeral", rs.returncode != 0)

    # --- mismatch: cached value edited to disagree ---------------------------------
    edit(deck, ">+3.3</span>", ">+9.9</span>")
    edit(deck, "v: 3.3", "v: 2.0")
    rep = E.deck_verify(root, deck)
    m_addrs = {m["addr"] for m in rep["mismatch"]}
    check("verify: edited cached values fail as mismatch, naming the address",
          f"{hv}#m.delta" in m_addrs and len(rep["mismatch"]) == 2)
    rm = subprocess.run([sys.executable, CRUX, "deck", "--verify", deck], capture_output=True,
                        text=True, encoding="utf-8", cwd=root)
    check("verify CLI: mismatch exits non-zero and names the address",
          rm.returncode != 0 and f"{hv}#m.delta" in rm.stdout + rm.stderr)

    # --- refresh: mechanical repair, values only -----------------------------------
    before = read(deck)
    res = E.deck_refresh(root, deck)
    check("refresh: rewrites the corrupted values and names the slides",
          res["changes"] and set(res["slides"]) == {2} == set(c["slide"] for c in res["changes"]))
    rep = E.deck_verify(root, deck)
    check("refresh: deck verifies clean afterwards",
          rep["mismatch"] == [] and rep["unresolvable"] == [])
    after = read(deck)
    check("refresh: non-value bytes untouched",
          "No numbers on this slide" in after and "W=1140,H=430,pad=52" in after
          and "&minus;4.6" in after and "1.20M" in after and "50,000" in after
          and "data-derived" in after and after.count("<section") == before.count("<section"))
    check("refresh: sign convention preserved on the repaired span", ">+3.3</span>" in after)
    res2 = E.deck_refresh(root, deck)
    check("refresh: idempotent — second run changes nothing",
          res2["changes"] == [] and read(deck) == after)

    # --- refresh after the VAULT moves: formatting conventions survive -------------
    edit(os.path.join(root, "results", hv, "metrics.json"), '"share": {"value": 50000}',
         '"share": {"value": 60000}')
    edit(os.path.join(root, "results", hv, "metrics.json"), '"neg": {"value": -4.6}',
         '"neg": {"value": -5.0}')
    check("validate --check=decks: a stale deck is a warning, not a problem",
          (lambda r: r["problems"] == [] and r["warnings"] != [])(
              E.validation_report(root, ["decks"])))
    rv = subprocess.run([sys.executable, CRUX, "validate", "--check=decks"],
                        capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("validate CLI: stale deck warns but exits 0", rv.returncode == 0 and "⚠" in rv.stdout)
    rvs = subprocess.run([sys.executable, CRUX, "validate", "--check=decks", "--strict"],
                         capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("validate CLI: --strict + --check=decks fails on the stale deck", rvs.returncode != 0)
    rp = subprocess.run([sys.executable, CRUX, "validate"], capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("validate CLI: plain validate ignores presentations/ entirely",
          rp.returncode == 0 and "deck" not in rp.stdout + rp.stderr)
    res = E.deck_refresh(root, deck)
    after2 = read(deck)
    check("refresh: thousands separator re-applied on the moved value", ">60,000</span>" in after2)
    check("refresh: entity minus re-applied on the moved value", ">&minus;5.0</span>" in after2)
    check("refresh: verify green after the vault moved and the deck refreshed",
          E.deck_verify(root, deck)["mismatch"] == [])
    rr = subprocess.run([sys.executable, CRUX, "deck", "--refresh", deck], capture_output=True,
                        text=True, encoding="utf-8", cwd=root)
    check("refresh CLI: an already-current deck reports nothing to do",
          rr.returncode == 0 and read(deck) == after2)

    # --- unresolvable: distinct from mismatch, one per failure kind -----------------
    deck2 = os.path.join(root, "presentations", qv, "broken.html")
    write(deck2, f"""<section class="slide"><p>
<span data-src="h99#x.y">1.0</span>
<span data-src="{hv}#m.nope">2.0</span>
<span data-src="{hv}#m">3.0</span>
<span data-derived="h98#a.b">4.0</span>
</p></section>""")
    rep = E.deck_verify(root, deck2)
    kinds = sorted(u["kind"] for u in rep["unresolvable"])
    check("verify: unresolvable buckets carry distinct kinds, no mismatches",
          kinds == ["missing-file", "missing-file", "missing-key", "missing-value"]
          and rep["mismatch"] == [])
    rb = subprocess.run([sys.executable, CRUX, "deck", "--verify", deck2], capture_output=True,
                        text=True, encoding="utf-8", cwd=root)
    check("verify CLI: unresolvable exits non-zero, reported distinctly",
          rb.returncode != 0 and "unresolvable" in (rb.stdout + rb.stderr))
    os.remove(deck2)

    # --- strict-clean deck: literal escape suffices ---------------------------------
    deck3 = os.path.join(root, "presentations", qv, "clean.html")
    write(deck3, _mini_deck(hv))
    E.deck_refresh(root, deck3)   # vault moved above; bring the copy current first
    rc = subprocess.run([sys.executable, CRUX, "deck", "--verify", deck3, "--strict"],
                        capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("verify CLI: --strict passes a deck whose only constants are literal-escaped",
          rc.returncode == 0)

    # --- check registry -------------------------------------------------------------
    try:
        E.validation_report(root, ["bogus"])
        check("validate: unknown check still refused", False)
    except E.CruxError as e:
        check("validate: unknown check still refused, message names decks", "decks" in str(e))

    # --- pre-11 vault: --strict clean with no presentations/ ------------------------
    old = os.path.join(base, "old_vault")
    E.cmd_init("Old Strict", old, goal="g")
    E.cmd_ask(old, "Old question")
    ros = subprocess.run([sys.executable, CRUX, "validate", "--strict"], capture_output=True,
                         text=True, encoding="utf-8", cwd=old)
    check("validate: pre-11 vault passes --strict with no migration", ros.returncode == 0)
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- prezit skill assets (PRD 11c)
def run_prezit():
    print("\n# prezit skill assets (template, example deck, contract lint)")
    CRUX = os.path.join(HERE, "crux.py")
    skl = os.path.abspath(os.path.join(HERE, "..", "..", "prezit"))
    tpl = os.path.join(skl, "assets", "deck.html")
    exd = os.path.join(skl, "examples", "q1_scaling_deck.html")
    sk = os.path.join(skl, "SKILL.md")
    check("prezit: SKILL.md ships", os.path.isfile(sk))
    check("prezit: template ships (assets/deck.html)", os.path.isfile(tpl))
    check("prezit: example deck ships", os.path.isfile(exd))
    if not (os.path.isfile(tpl) and os.path.isfile(exd) and os.path.isfile(sk)):
        return  # nothing to probe; the three checks above already failed
    t, x, s = read(tpl), read(exd), read(sk)

    # self-contained: the automatable half of "loads from file:// with no network"
    ext = re.compile(r'(?:src|href)\s*=\s*["\']https?://|@import|url\(\s*["\']?https?://'
                     r'|<script\s[^>]*\bsrc\s*=|<link\s[^>]*stylesheet')
    check("prezit: template is self-contained (no external refs)", not ext.search(t))
    check("prezit: example deck is self-contained (no external refs)", not ext.search(x))
    check("prezit: slide counter is DOM-derived (no literal total in markup)",
          bool(re.search(r'id="tot">\s*<', t)) and bool(re.search(r'id="tot">\s*<', x)))

    # contract lint: headers + 7-content-unit budget (footer overlap stays manual)
    check("prezit: template passes `deck --lint`", E.deck_lint(tpl) == [])
    check("prezit: example passes `deck --lint`", E.deck_lint(exd) == [])
    tmp = tempfile.mkdtemp(prefix="crux_pzl_")
    bad = os.path.join(tmp, "bad.html")
    write(bad, '<section class="slide"><ul>' + "<li>x</li>" * 8 + "</ul></section>")
    probs = E.deck_lint(bad)
    check("prezit: lint catches a missing contract header",
          any("contract header" in m for _, m in probs))
    check("prezit: lint catches a slide over 7 content units",
          any("content units" in m for _, m in probs))

    # D5, mechanically: motivation slides carry no addressed numbers; result slides >= 2.
    # Comments are stripped first — the deck's editing notes quote a literal
    # <section class="slide"> which must not read as a phantom slide.
    xs = re.sub(r"<!--.*?-->", " ", x, flags=re.S)
    secs = re.findall(r'<section class="slide[^"]*"[^>]*>(.*?)</section>', xs, flags=re.S)
    def addressed(seg):
        return len(re.findall(r'data-src="(?!literal")[^"]+"|data-derived="[^"]+"'
                              r"|\bsrc\s*:\s*['\"]", seg))
    check("prezit: 8-slide spine present in the example", len(secs) == 8)
    check("prezit: motivation slides (title/lineage/question) carry zero addressed numbers",
          all(addressed(seg) == 0 for seg in secs[:3]))
    check("prezit: every result slide carries >= 2 addressed numbers",
          all(addressed(seg) >= 2 for seg in secs[5:7]))
    check("prezit: chart-B annotations are computed from cached values, not hand-typed",
          "note:'" not in x and 'note:"' not in x)

    # the example against the shipped scaling_vault: the full contract, verify green
    base = tempfile.mkdtemp(prefix="crux_pz_")
    svc = os.path.join(base, "sv")
    shutil.copytree(os.path.join(HERE, "..", "examples", "scaling_vault"), svc)
    rep = E.deck_verify(svc, exd)
    check("prezit: example deck — zero mismatches against scaling_vault",
          rep["mismatch"] == [])
    check("prezit: example deck — zero unresolvable addresses", rep["unresolvable"] == [])
    check("prezit: example deck — zero unsourced numerals (source-scanned, ~40 rendered)",
          rep["unsourced"] == [])
    check("prezit: example exercises span, chart, derived and literal addressing",
          'data-src="h1#task_a.delta"' in x and "src:'h1#task_a.delta'" in x
          and "data-derived=" in x and 'data-src="literal"' in x)
    rv = subprocess.run([sys.executable, CRUX, "deck", "--verify", exd, "--strict"],
                        capture_output=True, text=True, encoding="utf-8", cwd=svc)
    check("prezit: `crux deck --verify --strict` green on the example", rv.returncode == 0)
    rl = subprocess.run([sys.executable, CRUX, "deck", "--lint", exd],
                        capture_output=True, text=True, encoding="utf-8", cwd=svc)
    check("prezit: `crux deck --lint` green on the example", rl.returncode == 0)
    rlb = subprocess.run([sys.executable, CRUX, "deck", "--lint", bad],
                         capture_output=True, text=True, encoding="utf-8", cwd=svc)
    check("prezit: `crux deck --lint` fails the bad deck", rlb.returncode != 0)
    shutil.rmtree(base, ignore_errors=True)
    shutil.rmtree(tmp, ignore_errors=True)

    # SKILL.md carries the load-bearing rules (crude string pins so they can't be edited
    # away silently)
    for needle in ("crux deck", "--verify", "--refresh", "presentations/", "metrics.json",
                   "contract header", "one claim", "re-run the plotting code"):
        check(f"prezit: SKILL.md states '{needle}'", needle in s)

    # the paper arc (the default) beside the tree arc, disclosed behind one pointer
    pref = os.path.join(skl, "references", "paper-arc.md")
    check("prezit: SKILL.md names both arcs, the paper arc as default, and points at its reference",
          "tree arc" in s and "the paper arc is the default" in s.lower()
          and "references/paper-arc.md" in s)
    check("prezit: paper-arc reference ships", os.path.isfile(pref))
    if os.path.isfile(pref):
        lb = read(pref).lower()
        for needle in ("motivation", "method", "results", "discussion", "options",
                       "build_deck.py", "__data__", "__sources__", "deck-sources", "2×",
                       "decomposition", "plain name", "label every panel", "speaker notes",
                       "one question at a time"):
            check(f"prezit: paper-arc reference states '{needle}'", needle in lb)
    # speaker notes are template chrome (`n` toggles them), and notes add no content units
    check("prezit: template hides speaker notes until `n`",
          "aside.notes{display:none}" in t and "e.key==='n'" in t)
    nt = tempfile.mkdtemp(prefix="crux_pzn_")
    nd = os.path.join(nt, "notes.html")
    write(nd, "<!-- job x\n source x\n numbers none\n cut x -->\n"
              '<section class="slide"><ul>' + "<li>x</li>" * 7 + "</ul>"
              '<aside class="notes"><p>a</p><p>b</p></aside></section>')
    check("prezit: speaker notes in <p> add no content units to the lint",
          E.deck_lint(nd) == [])
    shutil.rmtree(nt, ignore_errors=True)

    run_prezit_paper(CRUX, skl, exd)


def run_prezit_paper(CRUX, skl, exd):
    """The paper arc's proof path: a BUILT deck carries a deck-sources manifest (vault path
    -> sha256 of every file its build read) and --verify re-reads each file. The tree path
    must stay byte-identical in its report."""
    print("\n# prezit paper arc (built decks: deck-sources manifest, verify, lint)")
    pdir = os.path.join(skl, "examples", "paper_deck")
    src, bld, idx = (os.path.join(pdir, f) for f in ("deck_src.html", "build_deck.py", "index.html"))
    check("prezit: paper example ships (deck_src.html, build_deck.py, index.html)",
          all(os.path.isfile(f) for f in (src, bld, idx)))
    if not all(os.path.isfile(f) for f in (src, bld, idx)):
        return
    base = tempfile.mkdtemp(prefix="crux_pp_")
    svc = os.path.join(base, "sv")
    shutil.copytree(os.path.join(HERE, "..", "examples", "scaling_vault"), svc)
    run = lambda *a: subprocess.run([sys.executable, CRUX, "deck", *a], capture_output=True,
                                    text=True, encoding="utf-8", cwd=svc)
    x = read(idx)
    check("prezit: paper example declares the paper arc and carries a manifest",
          E.deck_arc(x) == "paper" and 'id="deck-sources"' in x and "__SOURCES__" not in x)
    check("prezit: paper example is self-contained (no external refs)",
          not re.search(r'(?:src|href)\s*=\s*["\']https?://|<script\s[^>]*\bsrc\s*=', x))

    # the build is reproducible: rebuilding against a vault copy gives the shipped bytes
    pc = os.path.join(base, "paper_deck")
    shutil.copytree(pdir, pc)
    os.remove(os.path.join(pc, "index.html"))
    rb = subprocess.run([sys.executable, os.path.join(pc, "build_deck.py"), svc],
                        capture_output=True, text=True, encoding="utf-8")
    check("prezit: paper build_deck.py runs", rb.returncode == 0)
    check("prezit: paper build reproduces the shipped index.html byte for byte",
          os.path.isfile(os.path.join(pc, "index.html")) and read(os.path.join(pc, "index.html")) == x)

    rep = E.deck_verify(svc, idx)
    check("prezit: paper example — every source re-read and unchanged",
          sorted(rep.get("sources", [])) == [f"results/{h}/metrics.json" for h in ("h1", "h2", "h3")])
    check("prezit: paper example — no mismatch, unresolvable or unsourced",
          rep["mismatch"] == [] and rep["unresolvable"] == [] and rep["unsourced"] == [])
    check("prezit: `crux deck --verify --strict` green on the paper example",
          run("--verify", idx, "--strict").returncode == 0)
    check("prezit: `crux deck --lint` green on the paper example (built and source)",
          run("--lint", idx).returncode == 0 and run("--lint", src).returncode == 0)

    # failing for the right reasons
    rs = E.deck_verify(svc, src)
    check("prezit: the unbuilt deck_src.html fails verify as unbuilt",
          any(u["kind"] == "unbuilt" for u in rs["unresolvable"]) and rs.get("unbuilt"))
    pres = os.path.join(svc, "presentations", "q1")
    os.makedirs(pres)
    shutil.copy(src, os.path.join(pres, "deck_src.html"))
    shutil.copy(idx, os.path.join(pres, "index.html"))
    check("prezit: validate's deck check skips an unbuilt source and passes the built deck",
          E.deck_warnings(svc) == [])
    with open(os.path.join(svc, "results", "h3", "metrics.json"), "a") as fh:
        fh.write(" ")
    rm = E.deck_verify(svc, idx)
    check("prezit: a source changed after the build is a mismatch naming that file",
          [m["addr"] for m in rm["mismatch"]] == ["results/h3/metrics.json"])
    check("prezit: a changed source fails `--verify` and validate warns",
          run("--verify", idx).returncode != 0 and len(E.deck_warnings(svc)) == 1)
    os.remove(os.path.join(svc, "results", "h2", "metrics.json"))
    ru = E.deck_verify(svc, idx)
    check("prezit: a missing source is unresolvable",
          any(u["kind"] == "missing-file" and "results/h2/metrics.json" in u["msg"]
              for u in ru["unresolvable"]))

    t2 = os.path.join(base, "t")
    os.makedirs(t2)
    def deck(name, head, body='<p>x</p>', notes=True):
        f = os.path.join(t2, name)
        write(f, head + "<!-- job x\n source x\n numbers x\n cut x -->\n<section class=\"slide\">"
                 + body + ('<aside class="notes"><p>n</p></aside>' if notes else "") + "</section>")
        return f
    PA = '<meta name="prezit-arc" content="paper">'
    MAN = lambda m: '<script type="application/json" id="deck-sources">%s</script>' % json.dumps(m)
    good = {"results/h1/metrics.json":
            hashlib.sha256(open(os.path.join(svc, "results", "h1", "metrics.json"), "rb").read()).hexdigest()}
    f = deck("nomanifest.html", PA)
    check("prezit: a paper deck with no manifest is unresolvable",
          any(u["kind"] == "no-manifest" for u in E.deck_verify(svc, f)["unresolvable"]))
    f = deck("dotdot.html", PA + MAN({"../outside.txt": "0" * 64}))
    check("prezit: a manifest path escaping the vault is refused",
          any(u["kind"] == "bad-path" for u in E.deck_verify(svc, f)["unresolvable"]))
    f = deck("badarc.html", '<meta name="prezit-arc" content="lab">' + MAN(good))
    check("prezit: an unknown arc name is unresolvable",
          any(u["kind"] == "bad-arc" for u in E.deck_verify(svc, f)["unresolvable"]))
    f = deck("typed.html", PA + MAN(good), body="<p>gain of 3.3 points</p>")
    rt = E.deck_verify(svc, f)
    check("prezit: a typed numeral on a paper slide is unsourced (fails --strict only)",
          rt["mismatch"] == [] and rt["unresolvable"] == []
          and [u["numeral"] for u in rt["unsourced"]] == ["3.3"])
    f = deck("nonotes.html", PA + MAN(good), notes=False)
    check("prezit: lint fails a paper slide with no speaker notes",
          any("speaker notes" in m for _, m in E.deck_lint(f)))
    f = deck("commented.html", "<!-- " + PA + MAN(good) + " -->", notes=False)
    check("prezit: arc and manifest quoted inside a comment are ignored (tree path)",
          E.deck_arc(read(f)) is None and "sources" not in E.deck_verify(svc, f)
          and E.deck_lint(f) == [])
    f = deck("refresh.html", PA + MAN(good))
    before = read(f)
    rr = E.deck_refresh(svc, f)
    check("prezit: refresh on a built deck says rebuild and writes nothing",
          rr.get("rebuild") is True and rr["changes"] == [] and read(f) == before)

    # the tree path is unchanged: same report keys, no rebuild flag
    rv = E.deck_verify(svc, exd)
    check("prezit: tree deck report keeps exactly the pre-paper-arc keys",
          sorted(rv) == ["derived", "literal", "mismatch", "unresolvable", "unsourced"])
    exc = os.path.join(t2, "tree_copy.html")
    shutil.copy(exd, exc)
    check("prezit: refresh on a tree deck carries no rebuild flag",
          "rebuild" not in E.deck_refresh(svc, exc))
    shutil.rmtree(base, ignore_errors=True)


# ---------------------------------------------------------------- storify (a .tex story's engine path)
def run_storify_engine():
    """A story is a short LaTeX paper under stories/<anchor>/: `crux deck --verify/--lint`
    take the story path when the file ends in .tex. The manifest is one preamble comment
    line (`% crux-sources: {...}`), checked by the same code as a paper-arc deck's. The HTML
    deck path and its reports stay untouched (the prezit asserts above guard that)."""
    print("\n# storify engine (.tex verify, strict numerals, lint, validate --check=decks)")
    CRUX = os.path.join(HERE, "crux.py")
    base = tempfile.mkdtemp(prefix="crux_story_")
    svc = os.path.join(base, "sv")
    shutil.copytree(os.path.join(HERE, "..", "examples", "scaling_vault"), svc)
    run = lambda *a: subprocess.run([sys.executable, CRUX, *a], capture_output=True,
                                    text=True, encoding="utf-8", cwd=svc)
    sha = lambda rel: hashlib.sha256(open(os.path.join(svc, *rel.split("/")), "rb").read()).hexdigest()
    H1 = "results/h1/metrics.json"
    MAN = lambda m: "% crux-sources: " + (m if isinstance(m, str) else json.dumps(m))
    GOOD = {H1: sha(H1)}
    SECTIONS = ("Motivation and background", "Methods", "Results and discussion", "Conclusion")
    BODY = {
        "Motivation and background": "We ask whether doubling the data beats a larger model.",
        "Methods": ("We trained \\lit{3} seeds per arm, as in \\cite{smith2020}.\n"
                    "\\begin{figure}[t]\\centering\n"
                    "\\begin{tikzpicture}\\draw (0,0) -- (1,2) node {7};\\end{tikzpicture}\n"
                    "\\caption{Accuracy gain of \\gainA{} points.}\\label{fig:1}\n"
                    "\\end{figure}"),
        "Results and discussion": "The gain was \\gainA{} points (Figure~\\ref{fig:1}).",
        "Conclusion": "Two options remain, each with its cost.",
    }
    tdir = os.path.join(base, "t")
    def story(name, sections=SECTIONS, body=None, extra_pre="", manifest=GOOD, tail=""):
        """Write a story .tex; returns (path, {marker: line number}) for lines carrying @@k."""
        body = dict(BODY, **(body or {}))
        lines = ["\\documentclass{sn-jnl}", "\\newcommand{\\lit}[1]{#1}"]
        if manifest is not None:
            lines.append(MAN(manifest))
        lines += ["\\newcommand{\\gainA}{3.3}"] + ([extra_pre] if extra_pre else [])
        lines += ["\\begin{document}", "\\title{Data or a model}",
                  "\\abstract{More data beat a better model by \\gainA{} points.}", "\\maketitle"]
        for s in sections:
            lines += ["\\section{%s}" % s] + body.get(s, "Text.").split("\n")
        lines += tail.split("\n") if tail else []
        lines += ["\\end{document}", ""]
        marks = {}
        for i, ln in enumerate(lines, 1):
            for m in re.findall(r"@@(\w+)", ln):
                marks[m] = i
        text = "\n".join(re.sub(r"@@\w+", "", ln) for ln in lines)
        p = os.path.join(tdir, name)
        write(p, text)
        return p, marks

    # --- verify: the manifest ------------------------------------------------------
    good, _ = story("good.tex")
    rep = E.story_verify(svc, good)
    check("storify: a built story whose sources match verifies clean",
          rep["mismatch"] == [] and rep["unresolvable"] == [] and rep["sources"] == [H1])
    r = run("story", "--verify", good, "--strict")
    check("storify: `crux story --verify --strict` exits 0 on the clean story",
          r.returncode == 0 and "1 file(s) unchanged" in r.stdout)
    check("storify: `crux deck --verify` takes the story path for a .tex",
          run("deck", "--verify", good).returncode == 0)
    p, _ = story("unbuilt.tex", manifest="__SOURCES__")
    ru = E.story_verify(svc, p)
    check("storify: story_src.tex (__SOURCES__ in place) is unbuilt",
          ru.get("unbuilt") is True and any(u["kind"] == "unbuilt" for u in ru["unresolvable"])
          and run("deck", "--verify", p).returncode != 0)
    p, _ = story("nomanifest.tex", manifest=None)
    check("storify: a story with no crux-sources line is no-manifest",
          any(u["kind"] == "no-manifest" for u in E.story_verify(svc, p)["unresolvable"])
          and run("deck", "--verify", p).returncode != 0)
    p, _ = story("missing.tex", manifest={H1: GOOD[H1], "results/h9/metrics.json": "0" * 64})
    rm = E.story_verify(svc, p)
    check("storify: a manifest file that does not exist is unresolvable (missing-file)",
          any(u["kind"] == "missing-file" and "results/h9/metrics.json" in u["msg"]
              for u in rm["unresolvable"]) and rm["sources"] == [H1])
    p, _ = story("badjson.tex", manifest="{not json")
    check("storify: a manifest that is not JSON is bad-manifest",
          any(u["kind"] == "bad-manifest" for u in E.story_verify(svc, p)["unresolvable"]))
    p, _ = story("dotdot.tex", manifest={"../outside.txt": "0" * 64})
    check("storify: a manifest path escaping the folder is bad-path",
          any(u["kind"] == "bad-path" for u in E.story_verify(svc, p)["unresolvable"]))
    p, _ = story("twoman.tex", extra_pre=MAN(GOOD))
    check("storify: two crux-sources lines is bad-manifest",
          any(u["kind"] == "bad-manifest" for u in E.story_verify(svc, p)["unresolvable"]))
    p, _ = story("bodyman.tex", body={"Conclusion": MAN(GOOD)}, manifest=None)
    check("storify: a manifest line in the body is not the manifest (preamble only)",
          any(u["kind"] == "no-manifest" for u in E.story_verify(svc, p)["unresolvable"]))

    # --- verify --strict: typed numerals in the body ----------------------------------
    p, mk = story("prose.tex", body={"Results and discussion": "The gain was 3.3 points.@@a"})
    rp = E.story_verify(svc, p)
    check("storify: a typed numeral in prose is unsourced, with its line",
          [(u["numeral"], u["line"]) for u in rp["unsourced"]] == [("3.3", mk["a"])])
    check("storify: an unsourced numeral fails only under --strict",
          run("deck", "--verify", p).returncode == 0
          and run("deck", "--verify", p, "--strict").returncode == 1)
    rs = run("deck", "--verify", p, "--strict")
    check("storify: --strict names the numeral and its line",
          "'3.3'" in rs.stdout and f"line {mk['a']}" in rs.stdout)
    p, mk = story("caption.tex", body={"Methods": "\\begin{figure}\\caption{Gain of 4 points.}@@a\\end{figure}"})
    check("storify: a typed numeral in a caption is unsourced",
          [u["line"] for u in E.story_verify(svc, p)["unsourced"]] == [mk["a"]])
    p, mk = story("tabular.tex", body={"Methods": ("\\begin{table}\\begin{tabular}{lc}\n"
                                                    "acc & 0.91 \\\\@@a\n\\end{tabular}\\end{table}")})
    check("storify: a typed numeral in a tabular is unsourced (the column spec is not)",
          [(u["numeral"], u["line"]) for u in E.story_verify(svc, p)["unsourced"]] == [("0.91", mk["a"])])
    p, mk = story("math.tex", body={"Methods": "We set $\\alpha = 0.05$.@@a"})
    check("storify: math mode is not exempt — a typed numeral in $...$ is unsourced",
          [u["line"] for u in E.story_verify(svc, p)["unsourced"]] == [mk["a"]])
    clean_body = (
        "We set $\\alpha = \\lit{0.05}$ and kept \\lit{95}\\% of runs.\n"
        "Gain \\gainA{} (Section~\\ref{sec:2}, Eq.~\\eqref{eq:3}, \\cref{fig:4}, \\Cref{tab:5}).\n"
        "As shown before~\\cite{smith2020,lee2019} and \\citep[p.~12]{wu2021}.\n"
        "% we ran 99 seeds, a comment\n"
        "Escaped percent \\lit{50}\\% then a comment % 42 here\n"
        "\\label{sec:6}\\url{https://x.org/v7}\\href{https://y.org/8}{the data}\n"
        "\\includegraphics[width=0.5\\linewidth]{fig9.pdf}\\hspace{2mm}\\vspace{3pt}\n"
        "\\setlength{\\tabcolsep}{4pt}\\input{part10}\\\\[4pt]\n"
        "\\begin{tikzpicture}\\draw (0,0) -- (11,12);\\end{tikzpicture}\n"
        "\\begin{axis}[xmin=0, xmax=13]\\addplot coordinates {(1,2)};\\end{axis}\n"
        "\\begin{semilogyaxis}[ymax=14]\\addplot table {\\tblA};\\end{semilogyaxis}\n"
        "\\begin{figure}[t]\\end{figure}\\subsection{Ablation}\n"
        "\\bibliography{refs2}\\bibliographystyle{sn-mathphys-num}")
    p, _ = story("strictok.tex", body={"Methods": clean_body})
    rk = E.story_verify(svc, p)
    check("storify: --strict passes \\lit{}, macros, labels/refs/cites, comments, tikz/axis "
          "code and optional args", rk["unsourced"] == [] and rk["mismatch"] == []
          and rk["unresolvable"] == [])
    check("storify: the clean strict fixture exits 0 under --strict",
          run("deck", "--verify", p, "--strict").returncode == 0)

    # --- lint: sections, words, pages, voice ----------------------------------------
    lint = lambda p: [m for _, m in E.story_lint(p)["problems"]]
    check("storify: lint passes the clean story", lint(good) == [])
    r = run("deck", "--lint", good)
    check("storify: `crux deck --lint` on a clean story exits 0", r.returncode == 0 and "✓" in r.stdout)
    p, _ = story("nosec.tex", sections=SECTIONS[:3])
    check("storify: lint fails a missing section",
          any("Conclusion" in m for m in lint(p)) and run("deck", "--lint", p).returncode == 1)
    p, _ = story("order.tex", sections=(SECTIONS[0], SECTIONS[2], SECTIONS[1], SECTIONS[3]))
    check("storify: lint fails sections out of order",
          any("order" in m for m in lint(p)) and run("deck", "--lint", p).returncode == 1)
    p, mk = story("extra.tex", sections=SECTIONS[:3] + ("Limitations",) + SECTIONS[3:])
    check("storify: lint fails an extra top-level section, naming it",
          any("Limitations" in m for m in lint(p)) and run("deck", "--lint", p).returncode == 1)
    p, _ = story("ws.tex", sections=("motivation  AND background", "Methods",
                                     "Results and Discussion", "conclusion"),
                 body={"Methods": "Text.\n\\subsection{Anything goes here}"})
    check("storify: section titles match case- and whitespace-insensitively; subsections are free",
          lint(p) == [])
    p, _ = story("starred.tex", sections=("Motivation and background", "Methods",
                                          "Results and discussion", "Conclusion"),
                 tail="\\section*{Appendix}")
    check("storify: a starred top-level section counts as a section (extra fails)",
          any("Appendix" in m for m in lint(p)))

    # word cap: the four section titles are 8 words and \emph{alpha} is 1; filler fills the rest
    def words_story(name, n, front=""):
        nb = {s: "" for s in SECTIONS}
        nb["Methods"] = ("\\emph{alpha} " + " ".join(["word"] * n) + "\n"
                         "% these comment words never count at all\n"
                         "\\begin{figure}[t]\\caption{Caption words do not count}\\label{fig:x}\\end{figure}\n"
                         "\\begin{table}\\begin{tabular}{l} table words \\end{tabular}\\end{table}\n"
                         "\\begin{tikzpicture}\\node {tikz words};\\end{tikzpicture}\n"
                         "\\cite{k}\\ref{fig:x}\\includegraphics[width=3cm]{f.png}\\centering\n"
                         "\\begin{thebibliography}{9}\\bibitem{k} Ref words here.\\end{thebibliography}")
        lines = ["\\documentclass{sn-jnl}", "\\begin{document}", front]
        for s in SECTIONS:
            lines += ["\\section{%s}" % s, nb[s]]
        lines += ["\\end{document}", ""]
        f = os.path.join(tdir, name)
        write(f, "\n".join(lines))
        return f
    p1200, p1201 = words_story("w1200.tex", 1191), words_story("w1201.tex", 1192)
    check("storify: exactly 1,200 body words passes the word cap",
          E.story_lint(p1200)["words"] == 1200 and lint(p1200) == [])
    check("storify: 1,201 body words fails the word cap",
          E.story_lint(p1201)["words"] == 1201 and any("1201" in m.replace(",", "") for m in lint(p1201))
          and run("deck", "--lint", p1201).returncode == 1)
    pa = words_story("wabs.tex", 1191, front="\\title{Two words}\\abstract{\\emph{one} two.}")
    check("storify: the title and abstract count as body words (1,200 + 4 fails)",
          E.story_lint(pa)["words"] == 1204 and any("word" in m for m in lint(pa)))

    # page cap: a sibling <stem>.log
    pg = os.path.join(base, "pg")
    def logged(n, word="pages"):
        f = os.path.join(pg, "story.tex")
        write(f, read(good))
        if n is not None:
            write(os.path.join(pg, "story.log"),
                  "This is pdfTeX\n...\nOutput written on story.pdf (%d %s, 123456 bytes).\n" % (n, word))
        elif os.path.exists(os.path.join(pg, "story.log")):
            os.remove(os.path.join(pg, "story.log"))
        return f
    f = logged(5)
    check("storify: a sibling log with 5 pages fails the page cap",
          any("5 pages" in m or "5 page" in m for m in lint(f)) and run("deck", "--lint", f).returncode == 1)
    f = logged(4)
    check("storify: a sibling log with 4 pages passes", lint(f) == [] and E.story_lint(f)["pages"] == 4)
    f = logged(1, "page")
    check("storify: a 1-page log parses (singular 'page')", E.story_lint(f)["pages"] == 1)
    f = logged(None)
    check("storify: no log means no page check", lint(f) == [] and E.story_lint(f)["pages"] is None)

    # voice: reuses voice_lint over the body prose (captions kept, code dropped)
    p, mk = story("para.tex", body={"Results and discussion": "The gap was within noise.@@a"})
    lp = E.story_lint(p)["problems"]
    check("storify: lint fails a paraphrase stand-in, with its line",
          any("voice:paraphrase" in m and ln == mk["a"] for ln, m in lp)
          and run("deck", "--lint", p).returncode == 1)
    p, mk = story("nid.tex", body={"Results and discussion": "As h1 showed, the gain held.@@a"})
    lp = E.story_lint(p)["problems"]
    check("storify: lint fails a node id, with its line",
          any("voice:node-id" in m and ln == mk["a"] for ln, m in lp))
    p, mk = story("term.tex", body={"Conclusion": "The verdict is clear.@@a"})
    lp = E.story_lint(p)["problems"]
    check("storify: lint fails a crux term, with its line",
          any("voice:crux-term" in m and ln == mk["a"] for ln, m in lp))
    p, _ = story("captterm.tex", body={"Methods": "\\begin{figure}\\caption{The verdict per arm.}\\end{figure}"})
    check("storify: a caption is read for voice (crux term in a caption fails)",
          any("voice:crux-term" in m for m in lint(p)))
    p, _ = story("codeterm.tex", body={"Methods": ("\\begin{tikzpicture}\\node (tree) {};\\end{tikzpicture}"
                                                    "\\label{fig:h1}\\ref{fig:h1}")})
    check("storify: tikz code and label/ref keys are not prose (no voice finding)", lint(p) == [])
    p, _ = story("allow.tex", extra_pre="% crux-allow: tree, verdict",
                 body={"Conclusion": "A decision tree gave the verdict."})
    la = E.story_lint(p)
    check("storify: `% crux-allow:` licenses a crux term", la["problems"] == []
          and sorted(la["allowed"]) == ["tree", "verdict"])
    r = run("deck", "--lint", p)
    check("storify: lint lists the allowed terms in its output",
          r.returncode == 0 and "allowed: tree, verdict" in r.stdout)
    p, _ = story("allowid.tex", extra_pre="% crux-allow: h1, within noise",
                 body={"Conclusion": "As h1 showed, the gap was within noise."})
    lp = lint(p)
    check("storify: `% crux-allow:` never licenses a node id or a paraphrase",
          any("voice:node-id" in m for m in lp) and any("voice:paraphrase" in m for m in lp))

    # --- refresh refuses ------------------------------------------------------------
    before = read(good)
    r = run("deck", "--refresh", good)
    check("storify: --refresh on a .tex refuses, names build_story.py, writes nothing",
          r.returncode != 0 and "build_story.py" in r.stdout + r.stderr and read(good) == before)

    # --- aliases ----------------------------------------------------------------------
    rd, rs1, rs2 = run("deck", "q1", "--json"), run("story", "q1", "--json"), run("storify", "q1", "--json")
    check("storify: `crux story` and `crux storify` are aliases of `crux deck` (anchor --json)",
          rd.returncode == 0 and rd.stdout == rs1.stdout == rs2.stdout and len(rd.stdout) > 40)
    check("storify: `crux story --help` works", run("story", "--help").returncode == 0)

    # --- read paths ignore stories/; only validate --check=decks walks it --------------
    def reads():
        v = E.Vault(svc)
        return (json.dumps(E.snapshot(v), sort_keys=True, default=str),
                json.dumps(E.validation_report(svc), sort_keys=True),
                R.render_meta(v), R.render_experiments(v), R.render_wiki(v, svc),
                run("validate").stdout, run("validate", "--strict").returncode,
                run("status").stdout)
    before_reads = reads()
    sd = os.path.join(svc, "stories", "q1")
    os.makedirs(sd)
    shutil.copy(good, os.path.join(sd, "story.tex"))
    shutil.copy(story("src.tex", manifest="__SOURCES__")[0], os.path.join(sd, "story_src.tex"))
    for fn, txt in (("story.pdf", "%PDF-1.5 h1 q1 verdict"), ("story.log", "Output written on story.pdf (9 pages)."),
                    ("sn-jnl.cls", "\\ProvidesClass{sn-jnl} % q1 h2"), ("build_story.py", "print('q1 h1')\n")):
        write(os.path.join(sd, fn), txt)
    write(os.path.join(svc, "stories", "q2_bad.md"), "---\nid: q2\ntype: question\n---\n# not a node\n")
    check("storify: a stories/ folder (.tex .pdf .log .cls .py .md) leaves every read path "
          "identical (snapshot, validate, render, status)", reads() == before_reads)
    # (this example vault's plain validate already fails on its uncommitted raw/ papers —
    # what matters is that stories/ changes nothing in it)
    rv = run("validate")
    check("storify: plain validate ignores stories/ entirely",
          rv.stdout == before_reads[5] and "stories/" not in rv.stdout + rv.stderr)
    # the 9-page log above is a lint concern, never validate's
    check("storify: validate --check=decks skips story_src.tex and passes a current story",
          E.deck_warnings(svc) == [] and E.validation_report(svc, ["decks"])["warnings"] == [])
    with open(os.path.join(svc, "results", "h1", "metrics.json"), "a") as fh:
        fh.write(" ")
    w = E.deck_warnings(svc)
    check("storify: validate --check=decks warns on a stale story, id story:<rel>",
          [i for i, _ in w] == ["story:stories/q1/story.tex"] and "mismatch" in w[0][1])
    rr = run("validate", "--check=decks")
    check("storify: the stale story is a warning (exit 0), and --strict fails on it",
          rr.returncode == 0 and "story" in rr.stdout
          and run("validate", "--check=decks", "--strict").returncode != 0)
    rv = run("validate")
    check("storify: plain validate still ignores the stale story",
          rv.stdout == before_reads[5] and "stories/" not in rv.stdout + rv.stderr)
    shutil.rmtree(base, ignore_errors=True)


def run_storify_skill():
    """The storify skill ships its SKILL.md, the vendored Springer Nature class, the template
    and a worked example on scaling_vault q1 whose built story verifies and lints clean."""
    print("\n# storify skill assets and the q1 example")
    CRUX = os.path.join(HERE, "crux.py")
    skl = os.path.abspath(os.path.join(HERE, "..", "..", "storify"))
    ex = os.path.join(skl, "examples", "q1_story")
    ships = [os.path.join(skl, "SKILL.md")] + \
        [os.path.join(skl, "assets", f) for f in
         ("sn-jnl.cls", "sn-mathphys-num.bst", "story_src.tex", "build_story.py")] + \
        [os.path.join(ex, f) for f in ("story_src.tex", "build_story.py", "story.tex")]
    check("storify: SKILL.md, template, build and q1 example ship",
          all(os.path.isfile(f) for f in ships))
    if not all(os.path.isfile(f) for f in ships):
        return
    with open(os.path.join(skl, "assets", "sn-jnl.cls"), "rb") as fh:
        cls = fh.read()
    check("storify: the vendored class keeps its LPPL licence header",
          b"LaTeX Project Public License" in cls and b"\\ProvidesClass{sn-jnl}" in cls)
    base = tempfile.mkdtemp(prefix="crux_storyex_")
    svc = os.path.join(base, "sv")
    shutil.copytree(os.path.join(HERE, "..", "examples", "scaling_vault"), svc)
    run = lambda *a: subprocess.run([sys.executable, CRUX, "story", *a], capture_output=True,
                                    text=True, encoding="utf-8", cwd=svc)
    story = os.path.join(ex, "story.tex")
    check("storify: the q1 example verifies green under --strict",
          run("--verify", story, "--strict").returncode == 0)
    check("storify: the q1 example lints clean", run("--lint", story).returncode == 0)
    # the build is reproducible: rebuilding against a vault copy gives the shipped bytes
    ec = os.path.join(base, "q1_story")
    os.makedirs(ec)
    for f in ("story_src.tex", "build_story.py"):
        shutil.copy(os.path.join(ex, f), ec)
    rb = subprocess.run([sys.executable, os.path.join(ec, "build_story.py"), svc],
                        capture_output=True, text=True, encoding="utf-8")
    check("storify: q1 build_story.py runs", rb.returncode == 0)
    built = os.path.join(ec, "story.tex")
    check("storify: q1 build reproduces the shipped story.tex byte for byte",
          os.path.isfile(built) and read(built) == read(story))
    shutil.rmtree(base, ignore_errors=True)


def run_rd():
    """Spec 07 — the RD layer. Requirements Documents: one active RD per node, living in
    rd/, linked from the node, OUTSIDE the roll-up tree. This is the overflow channel spec 06
    deliberately warned-rather-than-errored without: the 400-word cap had nowhere to send the
    design detail it displaced. Shape copied from the wiki layer on purpose — a parentless
    side-layer of markdown pages with a generated index."""
    print("\n# RD layer (rd/ · crux rd · generated RD.md)")
    root = tempfile.mkdtemp(prefix="crux_rd_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("RD Demo", root, goal="Exercise the RD layer.")
    q1, _ = E.cmd_ask(root, "Does the RD layer hold?")
    h1, _, _ = E.cmd_hypothesize(root, "it holds", parent=q1, verifiables=["x"], expect="the claim holds")

    # -- 1. creation + the backlink
    slug, fn = E.cmd_rd(root, h1, "Probe ladder and estimand")
    page = os.path.join(root, "rd", slug + ".md")
    check("rd: crux rd creates the page", os.path.isfile(page))
    fm, body = E.parse_doc(read(page))
    check("rd: the created page carries type: rd", fm.get("type") == "rd")
    check("rd: the page records its owning node", fm.get("node") == h1)
    ntext = read(node_path(root, h1))
    check("rd: the node gains an RD:: backlink", "RD:: [[rd/%s]]" % slug in ntext)
    check("rd: the backlink resolves to the created file",
          E.link_targets(ntext)[-1] == slug or slug in E.link_targets(ntext))
    lines = [l for l in ntext.splitlines() if l.startswith(("Parent::", "RD::"))]
    check("rd: the backlink sits beside Parent::",
          len(lines) == 2 and lines[0].startswith("Parent::") and lines[1].startswith("RD::"))
    # the whole point of the preamble placement: text before the first `## ` is invisible to
    # _section, so linking a design document costs nothing from the budget it exists to free
    bare = read(node_path(root, h1)).replace("RD:: [[rd/%s]]" % slug, "")
    check("rd: the backlink does not consume the 400-word budget",
          E.prose_words(ntext, "idea") == E.prose_words(bare, "idea"))

    # -- 2. which nodes may own one (D2: both; q21 — the motivating case — is a question)
    qslug, _ = E.cmd_rd(root, q1, "Why this question needs a design")
    check("rd: an RD may attach to a question", os.path.isfile(os.path.join(root, "rd", qslug + ".md")))
    check("rd: an RD may attach to a hypothesis", E.scan_rd_pages(root)[0]["node"] in (q1, h1))
    expect_error("rd: an RD may not attach to the project root",
                 lambda: E.cmd_rd(root, "root", "nope"))
    # spec 19 removed synthesis; a finding is the non-tree node type an RD must still refuse
    s1, _, _ = E.cmd_finding(root, q1, "weak", answer="a provisional answer")
    expect_error("rd: an RD may not attach to a finding", lambda: E.cmd_rd(root, s1, "nope"))

    # -- 3. one ACTIVE RD per node (D11), and the refusal names the remedy (D12)
    try:
        E.cmd_rd(root, h1, "a second design")
        check("rd: a second active RD is refused with the remedy", False)
        check("rd: the refusal names --supersedes", False)
    except E.CruxError as e:
        check("rd: a second active RD is refused with the remedy", True)
        check("rd: the refusal names --supersedes", "--supersedes" in str(e))

    # -- 4. supersession is the ONLY way a design changes (never an in-place amendment)
    before = read(page)
    slug2, _ = E.cmd_rd(root, h1, "Probe ladder, second cut", supersedes=slug)
    pages = {p["slug"]: p for p in E.scan_rd_pages(root)}
    check("rd: --supersedes creates the new RD active", pages[slug2]["status"] == "active")
    check("rd: --supersedes flips the old RD to superseded", pages[slug]["status"] == "superseded")
    check("rd: --supersedes records supersedes: on the new RD", pages[slug2]["supersedes"] == slug)
    check("rd: --supersedes rewrites the node's RD:: line",
          "RD:: [[rd/%s]]" % slug2 in read(node_path(root, h1))
          and "RD:: [[rd/%s]]" % slug not in read(node_path(root, h1)))
    # D7 ruled git is the audit trail, so nothing hashes the old file — but the engine itself
    # must still never touch its BODY, or the chain stops being a record of what was thought
    check("rd: superseding never edits the superseded body",
          E.parse_doc(read(page))[1] == E.parse_doc(before)[1])

    # -- 5. an RD is a document, not evidence: outside the tree, the roll-up and the gate
    v = E.Vault(root)
    check("rd: an RD page never becomes a node", set(v.nodes) == {"root", q1, h1, s1})
    check("rd: no node has type rd", not any(n.type == "rd" for n in v.nodes.values()))
    led_before = E.ledger_counts(E.Vault(root), q1)
    st_before = E.derive_state(E.Vault(root), q1)
    E.cmd_rd(root, h1, "third cut", supersedes=slug2)
    E.refresh(root)
    check("rd: an RD does not move ledger_counts", E.ledger_counts(E.Vault(root), q1) == led_before)
    check("rd: an RD does not move the question's derived state",
          E.derive_state(E.Vault(root), q1) == st_before)

    # -- 6. the generated index
    idx = os.path.join(root, "RD.md")
    check("rd: RD.md is generated when rd/ is active", os.path.isfile(idx))
    itext = read(idx)
    check("rd: RD.md lists the page with its title", "Probe ladder, second cut" in itext)
    check("rd: RD.md shows the page status", "superseded" in itext)
    check("rd: RD.md derives the reverse chain", "superseded by" in itext.lower())
    check("rd: refresh #1 no-op after an RD", E.refresh(root) is False)
    check("rd: refresh #2 no-op after an RD", E.refresh(root) is False)
    first = read(idx); E.refresh(root)
    check("rd: RD.md is byte-stable across renders", read(idx) == first)
    check("rd: RD.md is in GENERATED", "RD.md" in E.GENERATED)
    check("rd: RD.md is not a node", "RD.md" not in [n["fn"] for n in E.Vault(root).nodes.values()])
    E.ensure_rd(root)
    check("rd: ensure_rd is idempotent", E.refresh(root) is False)

    # -- 7. the agent surface (spec 06's convention: --json on every verb an agent drives)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "rd", q1,
                        "another design", "--supersedes", qslug, "--json"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    try:
        j = __import__("json").loads(r.stdout)
    except Exception:
        j = None
    check("rd: crux rd emits parseable JSON",
          isinstance(j, dict) and {"slug", "file", "node", "status"} <= set(j))
    check("rd: crux rd --json exits 0", r.returncode == 0)

    # -- 8. the criterion the whole epic exists for (D19: on a fixture, not on the real q21).
    #       The engine never moves text — the PI does. What is asserted is that the move WORKS:
    #       an over-cap node comes back under the cap and the words survive in the RD.
    q2, _ = E.cmd_ask(root, "Is this node over the cap?")
    design = " ".join(["estimand"] * 500)
    edit(node_path(root, q2), "## Question\n\nIs this node over the cap?",
         "## Question\n\nIs this node over the cap? " + design)
    check("rd: the fixture question really is over the cap",
          any(w["id"] == q2 for w in E.validation_report(root)["warnings"]))
    dslug, _ = E.cmd_rd(root, q2, "The displaced design")
    dpath = os.path.join(root, "rd", dslug + ".md")
    edit(node_path(root, q2), " " + design, "")                       # PI moves it out
    edit(dpath, "## Design\n", "## Design\n\n" + design + "\n")        # ...and into the RD
    check("rd: moving design into an RD brings a node back under the cap",
          not any(w["id"] == q2 for w in E.validation_report(root)["warnings"]))
    check("rd: the moved words survive in the RD file", design in read(dpath))
    check("rd: an RD body is not capped",
          "rd" not in E.PROSE_SECTIONS and
          not any(dslug in w["message"] for w in E.validation_report(root)["warnings"]))
    shutil.rmtree(root, ignore_errors=True)


def run_rd_migration():
    """A pre-07 vault has no rd/ directory at all. It must load, validate, refresh and render
    exactly as before — byte for byte (evolve-crux gate 4). These asserts are deliberate
    regression locks: they assert an ABSENCE, which is the easiest thing to break silently
    later by scanning one directory too many."""
    print("\n# RD layer — a pre-07 vault still reads")
    root = tempfile.mkdtemp(prefix="crux_rdmig_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old Vault", root)
    q1, _ = E.cmd_ask(root, "an old question")
    E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"], expect="x holds")
    check("rdmig: a pre-07 vault has no rd/", not os.path.isdir(os.path.join(root, "rd")))
    check("rdmig: a pre-07 vault grows no RD.md", not os.path.exists(os.path.join(root, "RD.md")))
    check("rdmig: status still renders on a pre-07 vault", "an old question" in E.status_text(root))
    check("rdmig: the derived state still reads on a pre-07 vault (review was removed in 4.0)",
          E.derive_state(E.Vault(root), q1)["state"] == "open")

    # an rd/ directory full of pages changes nothing until something looks at it
    before = _dir_bytes(root)
    os.makedirs(os.path.join(root, "rd"))
    write(os.path.join(root, "rd", "stray.md"),
          "---\ntype: rd\nnode: %s\ntitle: Stray\nstatus: active\n---\n\n# Stray\n" % q1)
    check("rdmig: an rd/ directory adds no nodes", set(E.Vault(root).nodes) == set(E.Vault(root).nodes) and
          not any(n.type == "rd" for n in E.Vault(root).nodes.values()))
    check("rdmig: a pre-07 vault validates clean", E.cmd_validate(root) == [])
    after = {k: v for k, v in _dir_bytes(root).items() if "/rd/" not in k.replace(os.sep, "/")
             and not k.endswith("RD.md")}
    check("rdmig: the vault is byte-identical across the upgrade", after == before)
    shutil.rmtree(os.path.join(root, "rd"))
    check("rdmig: a pre-07 vault refresh is a no-op", E.refresh(root) is False)

    # the drift path, exactly as the wiki and economy migrations prove it
    edit(os.path.join(root, ".crux.yaml"), f"engine_version: {E.ENGINE_VERSION}", "engine_version: 1.4")
    warn = E.check_and_stamp_version(root)
    check("rdmig: an old-stamped vault reports drift", warn is not None and "1.4" in warn)
    check("rdmig: drift re-stamps to the new ENGINE_VERSION",
          E.Vault(root).cfg.get("engine_version") == E.ENGINE_VERSION)
    check("rdmig: ENGINE_VERSION at or past 1.5", at_least_version("1.5"))
    shutil.rmtree(root, ignore_errors=True)


def run_rd_lint():
    """Spec 07, PRD 07.2 — the RD structural lint. Mechanical checks only: does the link
    resolve, do the two ownership records agree, is there exactly one live design, is the
    chain acyclic. Whether an RD is GOOD, current, or warranted is judgment and lives in the
    crux-rd skill — the same line validate_wiki already draws.

    The negative cases carry the weight: anything can flag everything, so what matters is
    that a tidy vault, a pre-07 vault and a superseded chain all stay silent. Dirty cases run
    one at a time and are removed after, so every finding is attributable."""
    print("\n# RD lint (validate --check=rd)")
    root = tempfile.mkdtemp(prefix="crux_rdlint_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("RD Lint", root)
    q1, _ = E.cmd_ask(root, "a question")
    h1, _, _ = E.cmd_hypothesize(root, "a hypothesis", parent=q1, verifiables=["x"], expect="the claim holds")

    # the check is registered, and it is always-on rather than opt-in: an RD is vault
    # content, not a derived document like a deck
    check("rdlint: rd is a first-class check, not opt-in",
          "rd" in E.CHECKS and "rd" not in E.OPT_CHECKS)

    # a pre-07 vault: no findings, and the check must not even build a Vault to say so
    _V, seen = E.Vault, []
    class _Spy(_V):
        def __init__(self, *a, **kw):
            seen.append(1); super().__init__(*a, **kw)
    E.Vault = _Spy
    try:
        empty = E.validate_rd(root)
    finally:
        E.Vault = _V
    check("rdlint: no rd/ means no findings", empty == [])
    check("rdlint: the rd check short-circuits on an inactive layer", seen == [])

    # a tidy set, including a full supersession chain, is silent
    a1, _ = E.cmd_rd(root, h1, "first design")
    a2, _ = E.cmd_rd(root, h1, "second design", supersedes=a1)
    b1, _ = E.cmd_rd(root, q1, "question design")
    check("rdlint: a tidy RD set validates clean", E.cmd_validate(root) == [])

    def probs():
        return [m for _, m in E.cmd_validate(root)]
    rdpath = lambda s: os.path.join(root, "rd", s + ".md")

    # --- one dirty condition at a time, each undone afterwards ---
    # a node pointing at an RD that does not exist
    edit(node_path(root, h1), "[[rd/%s]]" % a2, "[[rd/ghost]]")
    check("rdlint: a dangling RD link is caught",
          any("broken RD link" in m and "ghost" in m for m in probs()))
    check("rdlint: RD findings are problems, not warnings",
          E.validation_report(root)["warnings"] == []
          and any("broken RD link" in p["message"] for p in E.validation_report(root)["problems"]))
    check("rdlint: findings carry a namespaced id",
          any(p["id"] == "node:%s" % h1 for p in E.validation_report(root)["problems"]))
    edit(node_path(root, h1), "[[rd/ghost]]", "[[rd/%s]]" % a2)

    # two live designs for one node — the invariant the whole lifecycle exists to hold
    edit(rdpath(a1), "status: superseded", "status: active")
    msgs = [m for m in probs() if "active RDs" in m]
    check("rdlint: two active RDs for one node caught", len(msgs) == 1)
    check("rdlint: the two-active message names both slugs",
          bool(msgs) and a1 in msgs[0] and a2 in msgs[0])
    edit(rdpath(a1), "status: active", "status: superseded")

    # the two ownership records disagreeing (this is what recording it twice buys)
    edit(node_path(root, h1), "[[rd/%s]]" % a2, "[[rd/%s]]" % b1)
    check("rdlint: an ownership disagreement is caught",
          any("claims node" in m and a2 in m for m in probs()))
    edit(node_path(root, h1), "[[rd/%s]]" % b1, "[[rd/%s]]" % a2)

    # a chain link pointing nowhere, then a chain that closes on itself
    edit(rdpath(a2), "supersedes: %s" % a1, "supersedes: nowhere")
    check("rdlint: supersedes pointing nowhere is caught",
          any("supersedes missing page" in m and "nowhere" in m for m in probs()))
    edit(rdpath(a2), "supersedes: nowhere", "supersedes: %s" % a1)
    edit(rdpath(a1), "supersedes: \n", "supersedes: %s\n" % a2)
    done = []
    cyc = probs(); done.append(1)
    check("rdlint: a supersession cycle is caught", any("cycle" in m for m in cyc))
    check("rdlint: a supersession cycle does not hang", done == [1])
    edit(rdpath(a1), "supersedes: %s\n" % a2, "supersedes: \n")

    # an RD whose owning node was deleted / never existed
    edit(rdpath(b1), "node: %s" % q1, "node: q99")
    check("rdlint: an orphaned RD is caught",
          any("does not exist" in m and b1 in m for m in probs()))
    edit(rdpath(b1), "node: q99", "node: %s" % q1)

    # the status enum
    edit(rdpath(b1), "status: active", "status: final")
    check("rdlint: a bad RD status is caught", any("bad status" in m and "final" in m for m in probs()))
    edit(rdpath(b1), "status: final", "status: active")
    check("rdlint: the vault is tidy again", E.cmd_validate(root) == [])

    # the check selector
    edit(rdpath(b1), "node: %s" % q1, "node: q99")
    check("rdlint: --check=rd isolates the RD findings",
          all("does not exist" in p["message"] for p in E.validation_report(root, ["rd"])["problems"]))
    check("rdlint: --check=tree excludes the RD findings",
          E.validation_report(root, ["tree"])["problems"] == [])
    edit(rdpath(b1), "node: q99", "node: %s" % q1)

    # --- the two wiki-lint interactions (spec 07 D16 / D17) ---
    # the one-way flow rule extended: the literature layer must not cite the project's own
    # design reasoning either. Before 07 this read as a bare "broken link", which sent the
    # reader hunting for a wiki page that was never meant to exist.
    E.ensure_wiki(root)
    write(os.path.join(root, "raw", "s.txt"), "a source\n")
    E.cmd_ingest(root, "raw/s.txt", title="A Source")
    wiki_page(root, "cited", "Cited", "Only an RD links here.", sources="raw/s.txt")
    wiki_page(root, "flow", "Flow", "Cites an RD.", sources="raw/s.txt",
              extra="See [[rd/%s]]." % b1)
    E.refresh(root)
    check("rdlint: a wiki page citing an RD is a flow violation",
          any("flow violation" in m and b1 in m for m in probs()))
    check("rdlint: it is not reported as a broken link",
          not any("broken link" in m and b1 in m for m in probs()))
    os.remove(os.path.join(root, "wiki", "flow.md"))
    # an RD grounding itself in the literature is intended usage — the page it cites is not
    # an orphan, and before 07 it was reported as one
    check("rdlint: a wiki page cited only by an RD starts as an orphan",
          any("orphan" in m and "cited" in m for m in probs()))
    edit(rdpath(b1), "## Design\n", "## Design\n\nGrounded in [[cited]].\n")
    check("rdlint: an RD citation rescues a wiki page from orphan",
          not any("orphan" in m and "cited" in m for m in probs()))

    # --- blast radius: the shipped fixture must be untouched by any of the above ---
    fx = os.path.join(HERE, "..", "examples", "demo_vault")
    if os.path.isdir(fx):
        cp = tempfile.mkdtemp(prefix="crux_rdfx_")
        shutil.rmtree(cp); shutil.copytree(fx, cp)
        check("rdlint: the demo fixture validates clean with the rd check",
              E.validation_report(cp)["problems"] == [])
        check("rdlint: the demo fixture's finding list is unchanged",
              E.validation_report(cp) ["problems"]
              == E.validation_report(cp, ["tree", "wiki"])["problems"])
        shutil.rmtree(cp, ignore_errors=True)
    shutil.rmtree(root, ignore_errors=True)


def run_rd_skill():
    """Spec 07, PRD 07.4 — the crux-rd skill. Prose is reviewed by reading it; these asserts
    only stop the documentation from drifting out of sync with the code that ships beside it,
    which is the specific way skill docs rot."""
    print("\n# crux-rd skill (write-vs-skip filter · immutability)")
    sk = os.path.abspath(os.path.join(HERE, "..", "..", "crux-rd", "SKILL.md"))
    check("rdskill: crux-rd ships with the standard frontmatter", os.path.isfile(sk))
    if not os.path.isfile(sk):
        return
    s = read(sk)
    fm = s.split("---")[1] if s.startswith("---") else ""
    check("rdskill: crux-rd frontmatter carries name/description/license/metadata",
          all(k in fm for k in ("name: crux-rd", "description:", "license:", "metadata:")))
    # the filter is the reason the skill exists: without it every node grows an RD
    check("rdskill: the write-vs-skip filter is written down",
          all(x in s for x in (str(E.PROSE_CAP), "re-litigate", "distortion")))
    check("rdskill: the filter states its negative case",
          "verifiables" in s and "not warranted" in s.lower())
    check("rdskill: the skill documents supersession, not amendment",
          "--supersedes" in s and "never amended in place" in s)
    # D7 made this paragraph the ONLY thing holding the invariant, so it must say so
    check("rdskill: the skill says the engine does not police immutability",
          "git log -p" in s)
    check("rdskill: the skill declares disable-model-invocation",
          "disable-model-invocation: true" in fm)
    # spec 19: the verb table moved out of the always-on core; the core routes to crux-rd
    crux_skill = os.path.abspath(os.path.join(HERE, "..", "SKILL.md"))
    verbs_ref = os.path.abspath(os.path.join(HERE, "..", "references", "verbs.md"))
    check("rdskill: the crux verb reference lists rd",
          os.path.isfile(verbs_ref) and "| `rd` |" in read(verbs_ref))
    check("rdskill: the always-on core routes to crux-rd",
          os.path.isfile(crux_skill) and "**crux-rd**" in read(crux_skill))
    # every invocation the skill shows must be one the CLI actually accepts
    bad = []
    for m in re.findall(r"crux rd ([^\n`\"']*)", s):
        for flag in re.findall(r"--[a-z-]+", m):
            if flag not in ("--supersedes", "--json"):
                bad.append(flag)
    check("rdskill: documented invocations parse", not bad)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "rd", "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    check("rdskill: crux rd --help works", r.returncode == 0 and "--supersedes" in r.stdout)
    spec = os.path.abspath(os.path.join(HERE, "..", "..", "..", ".spec", "README.md"))
    if os.path.isfile(spec):
        row = [l for l in read(spec).splitlines() if "07-rd-layer.md" in l]
        check("rdskill: spec 07 is marked done in .spec/README.md", bool(row) and "☑" in row[0])


def run_deck_rd():
    """Spec 07, PRD 07.5 — RD pages reach the deck payload. Spec 11 cut the `rd` slot and
    shipped it empty on the bargain that 07 would be picked up for free; this is that pickup.

    The trap this suite exists to catch: the neighbouring `wiki` block walks anchor +
    ANCESTORS, because the wiki supplies the deck's intro. RDs are the METHODS slot for the
    anchor's own story, so the traversal is anchor + DESCENDANTS. Copying the wiki loop would
    put a parent's design on a child's method slide."""
    print("\n# deck payload — RD pages in the methods slot")
    root = tempfile.mkdtemp(prefix="crux_rddeck_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Deck RD", root)
    q1, _ = E.cmd_ask(root, "the ancestor")
    q2, _ = E.cmd_ask(root, "the anchor", parent=q1)
    q4, _ = E.cmd_ask(root, "the sibling", parent=q1)
    h1, _, _ = E.cmd_hypothesize(root, "the descendant", parent=q2, verifiables=["x"],
                                 expect="x holds")

    check("rddeck: rd is present and empty with no RD layer", E.deck_payload(root, q2)["rd"] == [])

    anc, _ = E.cmd_rd(root, q1, "ancestor design")
    sib, _ = E.cmd_rd(root, q4, "sibling design")
    own, _ = E.cmd_rd(root, q2, "anchor design")
    kid, _ = E.cmd_rd(root, h1, "descendant design")
    p = E.deck_payload(root, q2)
    slugs = [r["slug"] for r in p["rd"]]
    check("rddeck: the anchor's RD reaches the payload", own in slugs)
    check("rddeck: a descendant's RD reaches the payload", kid in slugs)
    check("rddeck: an ancestor's RD stays out of the methods slot", anc not in slugs)
    check("rddeck: a sibling's RD stays out", sib not in slugs)
    check("rddeck: the rd entry carries slug, title and path",
          all(set(r) == {"slug", "title", "path"} for r in p["rd"])
          and p["rd"][0]["title"] == "anchor design")
    check("rddeck: rd order is tree order then slug", slugs == [own, kid])
    check("rddeck: rd paths are vault-relative",
          all(r["path"] == "rd/%s.md" % r["slug"] for r in p["rd"]))
    import json as J
    dumped = J.dumps(p)
    check("rddeck: no absolute path in the payload with RDs present", root not in dumped)
    check("rddeck: the payload stays byte-identical with RDs",
          J.dumps(E.deck_payload(root, q2)) == dumped)

    # a superseded design is history, not the methods of the current story
    own2, _ = E.cmd_rd(root, q2, "anchor design, second cut", supersedes=own)
    slugs = [r["slug"] for r in E.deck_payload(root, q2)["rd"]]
    check("rddeck: only active RDs enter the payload", own not in slugs)
    check("rddeck: a superseded RD's successor appears", own2 in slugs)

    # spec 11: "a hypothesis anchor is legal and yields a shorter payload"
    check("rddeck: a hypothesis anchor carries its RD",
          [r["slug"] for r in E.deck_payload(root, h1)["rd"]] == [kid])
    shutil.rmtree(root, ignore_errors=True)


def run_rd_gui():
    """Spec 07, PRD 07.3 — the RD read surfaces: the snapshot `rd` key (index only, never a
    body), the lazy /rd/<slug>.json route, and each node's pointer at its active RD.

    The reader itself is SHARED with the wiki tab, not copied: the pre-registered
    `webui: app.js is pure-read (three GETs…)` assert is what proves it — a second reader
    would need a fourth fetch and would fail that count."""
    print("\n# RD GUI contract (snapshot rd key + /rd/<slug>.json route)")
    import json, threading, urllib.request, urllib.error, builtins
    import serve as S
    root = tempfile.mkdtemp(prefix="crux_rdgui_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("RD GUI", root)
    q1, _ = E.cmd_ask(root, "a question")
    h1, _, _ = E.cmd_hypothesize(root, "a hypothesis", parent=q1, verifiables=["x"],
                                 expect="x")

    snap = E.snapshot(root)
    check("rdgui: snapshot reports an inactive RD layer",
          snap["rd"] == {"active": False, "pages": []})
    check("rdgui: a node with no RD reports null", snap["nodes"][h1]["rd"] is None)

    a1, _ = E.cmd_rd(root, h1, "the design")
    edit(os.path.join(root, "rd", a1 + ".md"), "## Design\n", "## Design\n\nThe substance.\n")
    a2, _ = E.cmd_rd(root, h1, "the second design", supersedes=a1)
    snap = E.snapshot(root)
    pages = {p["slug"]: p for p in snap["rd"]["pages"]}
    check("rdgui: the RD index carries the public fields",
          set(pages[a1]) == {"slug", "title", "node", "status", "supersedes", "hash"})
    check("rdgui: the RD index reports status and chain",
          pages[a1]["status"] == "superseded" and pages[a2]["supersedes"] == a1)
    check("rdgui: the RD index carries a content hash",
          isinstance(pages[a1]["hash"], str) and len(pages[a1]["hash"]) == 16)
    check("rdgui: snapshot never carries an RD body", "The substance." not in json.dumps(snap))
    check("rdgui: a node points at its active RD", snap["nodes"][h1]["rd"] == a2)
    check("rdgui: node_json agrees with snapshot", E.node_json(root, h1)["rd"] == a2)

    httpd = S.make_server(root, port=0)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % httpd.server_address[1]

    def get(path):
        try:
            with urllib.request.urlopen(base + path, timeout=5) as r:
                return r.status, r.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    try:
        st, body = get("/rd/%s.json" % a1)
        pg = json.loads(body) if st == 200 else {}
        check("rdgui: the RD route returns a body", st == 200 and "The substance." in pg.get("body", ""))
        check("rdgui: the RD route returns backlinks", isinstance(pg.get("backlinks"), list))
        check("rdgui: an unknown RD slug is a 404", get("/rd/nope.json")[0] == 404)

        # the slug is matched against the scan, never used as a path — rejected before disk
        opened, _open = [], builtins.open
        def spy(f, *a, **kw):
            opened.append(str(f)); return _open(f, *a, **kw)
        builtins.open = spy
        try:
            codes = [get("/rd/%s.json" % s)[0] for s in ("..%2f..%2fetc%2fpasswd", ".hidden", "a%2fb")]
        finally:
            builtins.open = _open
        check("rdgui: a traversal slug is rejected without a disk touch",
              set(codes) == {404} and not any("passwd" in o for o in opened))

        before = _dir_bytes(root)
        get("/snapshot.json"); get("/rd/%s.json" % a2)
        check("rdgui: the RD route writes nothing", _dir_bytes(root) == before)
    finally:
        httpd.shutdown(); httpd.server_close()

    # the two layers are separate namespaces: the same slug may exist in both and each
    # route resolves its own (wiki_page_payload rejects a "/" in a slug, so a shared route
    # could never have carried a prefix)
    E.ensure_wiki(root)
    write(os.path.join(root, "raw", "s.txt"), "src\n")
    E.cmd_ingest(root, "raw/s.txt", title="S")
    wiki_page(root, a2, "Same Slug, Wiki Side", "the wiki one", sources="raw/s.txt")
    check("rdgui: RD and wiki slugs are separate namespaces",
          E.wiki_page_payload(root, a2)["title"] == "Same Slug, Wiki Side"
          and E.rd_page_payload(root, a2)["title"] == "the second design")

    # The RD tab is MERGED into the taskhub (PI ruling, 2026-08-21): an RD is a kind of
    # task — a requirements document for a large one — so it lives as rows in the Taskhub
    # list, not as a fourth top-level tab. The reader is still the wiki's, shared not
    # copied; only the way in changed.
    css = read(os.path.join(HERE, "webui", "style.css"))
    idx = read(os.path.join(HERE, "webui", "index.html"))
    app = read(os.path.join(HERE, "webui", "app.js"))
    check("rdgui: the RD tab is merged into the taskhub, not a tab of its own",
          'data-tab="rd"' not in idx and "rd-pane" not in idx)
    check("rdgui: opening an RD lands in the taskhub tab",
          'setTab("tasks")' in app.split("function openRdPage")[1].split("function ")[0])
    check("rdgui: RD rows render inside the taskhub list",
          "rdRows" in app.split("function renderTasks")[1].split("\nfunction ")[0])

    # the node -> RD pointer has to be reachable from the pane, or it is a snapshot key
    # nothing uses. Absent on a node with no RD, so it never becomes chrome.
    check("rdgui: the node pane offers a way into the design",
          "function rdSection" in read(os.path.join(HERE, "webui", "app.js"))
          and "if (!n.rd) return \"\";" in read(os.path.join(HERE, "webui", "app.js")))

    # opening a SUPERSEDED design by default is the one thing this lifecycle exists to prevent
    check("rdgui: the reader defaults to a live design",
          'p.status === "active"' in app)
    # leaving the RD reader must drop its render key, or returning to a page already
    # viewed this session shows the previous pane's content (PR #16 audit finding)
    check("rdgui: leaving the RD reader resets its render key",
          'state.rd.readerKey = ""' in app.split("function renderDetail()")[1].split("function ")[0])

    # a pre-07 vault must not 500 the route
    old = tempfile.mkdtemp(prefix="crux_rdgui0_")
    shutil.rmtree(old); os.makedirs(old)
    E.cmd_init("No RDs", old)
    check("rdgui: the RD route is safe on a pre-07 vault", E.rd_page_payload(old, "anything") is None)
    shutil.rmtree(old, ignore_errors=True)
    shutil.rmtree(root, ignore_errors=True)


# ---------------------------------------------------------------- spec 15 shared helpers
def _strip_schema(root):
    """Make every node look pre-15: drop the `schema:` frontmatter line."""
    for n in E.Vault(root).nodes.values():
        edit(n["path"], "\nschema: %d\n" % E.SCHEMA_GENERATION, "\n")


def pre15_vault(prefix, engine_version="1.5"):
    """A vault that looks like it was written before evidence semantics: nodes with no
    `schema` key and an old engine_version stamp. Mirrors run_economy_migration()'s
    strip-the-schema-back-out idiom, and is shared by every spec-15 migration block."""
    root = tempfile.mkdtemp(prefix=prefix)
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Legacy Evidence", root)
    q, _ = E.cmd_ask(root, "a pre-15 question")
    h, _, _ = E.cmd_hypothesize(root, "a pre-15 hypothesis", parent=q,
                                verifiables=["first check", "second check"],
                                require_expect=False)
    _strip_schema(root)
    edit(os.path.join(root, E.VAULT_MARKER),
         f"engine_version: {E.ENGINE_VERSION}", f"engine_version: {engine_version}")
    return root, q, h


def fingerprint(root):
    """({node file: sha256}, {nid: verdict}, {nid: status}) for a vault.

    Two exclusions, both deliberate and both narrow:

    - `.crux.yaml` — the engine-version stamp is the one thing an upgrade is *supposed* to
      rewrite.
    - the GENERATED views (`META.md`, `EXPERIMENTS.md`, `WIKI.md`, `RD.md`) — they are
      derived, the engine owns them, and a new column in `EXPERIMENTS.md` is a rendering
      change rather than a change to the science. Loosening the assert here would be
      cheating, so the caller pairs it with `generated_verdicts()` below: the views may be
      re-rendered, but no verdict inside them may be re-labelled.

    What stays strict is the only thing that matters: every NODE file, byte for byte."""
    files = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = sorted(d for d in dn if not d.startswith("."))
        for f in sorted(fn):
            if not f.endswith(".md") or f in E.GENERATED or f == E.RD_INDEX:
                continue
            rel = os.path.relpath(os.path.join(dp, f), root).replace(os.sep, "/")
            with open(os.path.join(dp, f), encoding="utf-8") as fh:
                # the engine-owned ledger block is split off: it is a GENERATED summary that
                # lives inside a node file, and growing the verdict vocabulary re-renders it
                # (a zero count for the new word) without touching a single recorded result.
                # What must be byte-identical is everything the human wrote.
                files[rel] = hashlib.sha256(
                    fh.read().split(E.LEDGER_START)[0].encode("utf-8")).hexdigest()
    v = E.Vault(root)
    return (files,
            {n.id: n["fm"].get("verdict") for n in v.nodes.values()},
            {n.id: n.status for n in v.nodes.values()})


def generated_verdicts(root):
    """Every verdict word in everything the engine GENERATES — the root views and the ledger
    block inside each question — with its count. A view may be re-rendered and a new word may
    appear at zero; a verdict that was recorded may never be re-labelled or lose a count."""
    text = ""
    for f in list(E.GENERATED) + [E.RD_INDEX]:
        p = os.path.join(root, f)
        if os.path.isfile(p):
            text += read(p)
    for n in E.Vault(root).nodes.values():
        if E.LEDGER_START in n["body"]:
            text += n["body"].split(E.LEDGER_START)[1]
    return {x: text.count(x) for x in ("supported", "partial", "refuted", "inconclusive")}


def run_evidence_boundary():
    """Spec 15 PRD 15.0 — the version boundary. A per-node `schema` stamp, written at
    creation, where ABSENCE means the node predates evidence semantics. This PRD adds no
    rule at all: a stamped and an unstamped node must behave identically in every command.
    The asserts that look vacuous here are the point — they are regression locks on the
    guarantee that the engine never overturns recorded science."""
    print("\n# evidence semantics — the version boundary (spec 15, PRD 15.0)")
    root = tempfile.mkdtemp(prefix="crux_bound_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Boundary", root)
    q1, _ = E.cmd_ask(root, "a stamped question")
    h1, _, _ = E.cmd_hypothesize(root, "a stamped hypothesis", parent=q1, verifiables=["a"],
                                 expect="a holds")

    v = E.Vault(root)
    check("boundary: a new hypothesis is stamped with the current schema generation",
          v.get(h1)["fm"].get("schema") == E.SCHEMA_GENERATION)
    check("boundary: a new question is stamped schema 1",
          v.get(q1)["fm"].get("schema") == E.SCHEMA_GENERATION)
    check("boundary: the project root is not stamped (spec 15 governs q/h only)",
          "schema" not in v.get("root")["fm"])

    # -- the predicate
    check("boundary: an unstamped node reads schema 0",
          E.node_schema(E.Node(fm={})) == 0 and not E.binds_evidence_semantics(E.Node(fm={})))
    check("boundary: a malformed schema value degrades to 0, never raises",
          E.node_schema(E.Node(fm={"schema": "banana"})) == 0
          and E.node_schema(E.Node(fm={"schema": None})) == 0)
    check("boundary: a stamped node binds evidence semantics",
          E.binds_evidence_semantics(v.get(h1)))

    # -- seed materialization routes through ask/hypothesize, so it inherits the stamp
    sd = tempfile.mkdtemp(prefix="crux_bseed_")
    seed = os.path.join(sd, "seed.md")
    with open(seed, "w", encoding="utf-8") as f:
        f.write("- Project: Seeded — a goal\n  - Q: a seeded question\n"
                "    - H: a seeded hypothesis\n      - expect: the check holds\n"
                "      - v: a check\n")
    sroot = os.path.join(sd, "vault")
    E.cmd_init_from(seed, sroot)
    sv = E.Vault(sroot)
    check("boundary: seed-materialized nodes are stamped",
          all(n["fm"].get("schema") == E.SCHEMA_GENERATION
              for n in sv.nodes.values() if n.type in ("question", "idea")))
    shutil.rmtree(sd, ignore_errors=True)

    # -- snapshot surface
    snap = E.snapshot(root)
    check("boundary: snapshot exposes schema on a node",
          snap["nodes"][h1]["schema"] == E.SCHEMA_GENERATION
          and snap["nodes"][q1]["schema"] == E.SCHEMA_GENERATION)

    # -- the info tier, on a vault with nothing to report
    rep = E.validation_report(root)
    check("boundary: a fully-stamped vault reports no boundary info",
          rep["info"] == [] and rep["ok"] is True)

    check("boundary: ENGINE_VERSION at or past 1.6", at_least_version("1.6"))
    shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary itself
    old = tempfile.mkdtemp(prefix="crux_bmig_")
    E.cmd_init("Legacy Evidence", old)
    oq, _ = E.cmd_ask(old, "a pre-15 question")
    oh, _, _ = E.cmd_hypothesize(old, "a pre-15 hypothesis", parent=oq,
                                verifiables=["first check", "second check"],
                                expect="both checks hold")
    _strip_schema(old)
    edit(os.path.join(old, E.VAULT_MARKER), f"engine_version: {E.ENGINE_VERSION}",
         "engine_version: 1.5")
    check("evmig: the fixture really is unstamped",
          "schema:" not in read(node_path(old, oh)))

    rep = E.validation_report(old)
    ids = [i["id"] for i in rep["info"]]
    check("boundary: validate reports the pre-15 count as info",
          any(i["id"] == "boundary:evidence-semantics" and "1 hypothes" in i["message"]
              for i in rep["info"]))
    check("boundary: info does not affect ok",
          rep["info"] and rep["ok"] is True and rep["problems"] == [] and rep["warnings"] == [])
    check("boundary: info entries share the problems/warnings shape",
          all(set(e) == {"id", "message"} | (set(e) & {"count"}) and "id" in e and "message" in e
              for e in rep["info"]))
    check("boundary: every info id is namespaced",
          all(":" in i and i.split(":", 1)[0] in E.INFO_NAMESPACES for i in ids))
    check("boundary: info respects the --check filter",
          E.validation_report(old, ["tree"])["info"] != []
          and E.validation_report(old, ["wiki"])["info"] == [])
    check("evmig: pre-15 vault validates clean",
          E.cmd_validate(old) == [] and E.validation_report(old)["warnings"] == [])

    # -- nothing retro-stamps. Run every read/write path there is, then re-check.
    before = fingerprint(old)
    E.refresh(old); E.cmd_validate(old); E.validation_report(old)
    E.check_and_stamp_version(old); E.snapshot(old); E.status_text(old)
    E.cmd_test(old, oh, to="running")
    E.cmd_finding(old, oh, "moderate", why="both held", direction="supports")
    after_v = E.Vault(old)
    check("evmig: no command retro-stamps an existing node (a new finding is a new node)",
          all("schema" not in n["fm"] for n in after_v.nodes.values() if n.type != "finding"))
    shutil.rmtree(old, ignore_errors=True)

    # -- the captured pre-upgrade fixture: byte-identical after the version bump. The shipped
    #    demo_vault is 4.0 now (spec 19 regenerated it); `captured_demo` rebuilds its 1.2 form
    #    exactly. The upgrade MIGRATES it (new Finding nodes); every node that existed before
    #    must keep its authored bytes, its verdict and its status.
    import selftest_migrate as SM
    dst = SM.captured_demo(tempfile.mkdtemp(prefix="crux_bdemo_"))
    f0, v0, s0 = fingerprint(dst)
    warn = E.check_and_stamp_version(dst)
    E.refresh(dst); E.snapshot(dst); E.cmd_validate(dst); E.status_text(dst)
    f1, v1, s1 = fingerprint(dst)
    new = E.Vault(dst)
    check("evmig: pre-15 vault — every node's authored content is byte-identical after upgrade",
          f0 and {k: f1.get(k) for k in f0} == f0)
    check("evmig: pre-15 vault — the upgrade only ADDS nodes, and only Findings",
          all(new.nodes[n].type == "finding" for n in set(v1) - set(v0)) and set(v0) <= set(v1))
    check("evmig: pre-15 vault — every recorded verdict is unchanged after upgrade",
          {k: v1[k] for k in v0} == v0 and v0["h1"] == "supported" and v0["h2"] == "partial")
    check("evmig: pre-15 vault — every status is unchanged after upgrade",
          {k: s1[k] for k in s0} == s0)
    check("evmig: an older vault reports drift and re-stamps to current",
          warn is not None and "1.2" in warn
          and E.Vault(dst).cfg.get("engine_version") == E.ENGINE_VERSION)
    check("evmig: the demo vault validates clean after upgrade", E.cmd_validate(dst) == [])
    # the human-readable path shows it too, with a neutral glyph and exit 0 — the boundary
    # must never look like a finding on the surface the PI actually reads
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "validate"],
                       capture_output=True, cwd=dst, encoding="utf-8", errors="replace")
    check("boundary: the CLI prints the boundary as info and still exits 0",
          r.returncode == 0 and "predate evidence semantics" in r.stdout
          and "vault is valid" in r.stdout and "\u2717" not in r.stdout)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "validate", "--strict"],
                       capture_output=True, cwd=dst, encoding="utf-8", errors="replace")
    check("boundary: --strict does not turn the boundary into a failure", r.returncode == 0)
    shutil.rmtree(dst, ignore_errors=True)


def run_verifiable_kind():
    """Spec 15 PRD 15.1 — every verifiable carries a kind. `hypothesis` checks are
    consequences of the claim and feed the verdict; `outcome-neutral` checks (positive
    controls, manipulation checks) must pass whatever the claim turns out to be, and their
    failure invalidates the RUN rather than refuting the claim.

    This PRD parses, requires and displays the kind. It deliberately does NOT change any
    verdict — that is 15.2. So the flat tally must stay byte-identical here."""
    print("\n# evidence semantics — verifiable kind (spec 15, PRD 15.1)")

    # -- the parser, as pure functions on a string: no vault needed
    check("kind: an untagged verifiable defaults to hypothesis",
          E.verifiable_kind("imp-Spearman >= +0.01") == ("hypothesis", "imp-Spearman >= +0.01"))
    check("kind: the kind vocabulary and its aliases normalize",
          E.verifiable_kind("[outcome-neutral] c")[0] == "outcome-neutral"
          and E.verifiable_kind("[control] c")[0] == "outcome-neutral"
          and E.verifiable_kind("[ON] c")[0] == "outcome-neutral"
          and E.verifiable_kind("[neutral] c")[0] == "outcome-neutral"
          and E.verifiable_kind("[hypothesis] c")[0] == "hypothesis"
          and E.verifiable_kind("[hyp] c")[0] == "hypothesis")
    check("kind: an unknown tag keeps the text intact and reads as hypothesis",
          E.verifiable_kind("[banana] c") == ("hypothesis", "[banana] c"))

    # the composition that PR #14's `(found: …)` makes possible to get wrong
    body = ("## Verifiables\n\n"
            "- [x] [outcome-neutral] the known-good encoder reproduces 0.46 (found: 0.461)\n"
            "- [ ] [hypothesis] imp-Spearman >= +0.01 vs baseline\n"
            "- [-] a third, untagged check\n")
    items = E._verifiables(body)
    check("kind: the tag is stripped from the cockpit text",
          items[0]["text"] == "the known-good encoder reproduces 0.46 (found: 0.461)"
          and items[1]["text"] == "imp-Spearman >= +0.01 vs baseline")
    check("kind: snapshot's verifiable reader exposes kind",
          [i["kind"] for i in items] == ["outcome-neutral", "hypothesis", "hypothesis"])
    dv = E._deck_verifiables(body)
    check("kind: a kind tag and a (found:) note coexist on one line",
          dv[0]["kind"] == "outcome-neutral" and dv[0]["found"] == "0.461"
          and dv[0]["text"] == "the known-good encoder reproduces 0.46")
    check("kind: the deck payload exposes verifiable kind",
          [i["kind"] for i in dv] == ["outcome-neutral", "hypothesis", "hypothesis"])

    # -- the split tally, and the flat one it must not disturb
    check("kind: the split tally separates the two classes",
          E.count_verifiables_by_kind(body) ==
          {"hypothesis": (0, 1, 1), "outcome-neutral": (1, 0, 0)})
    check("kind: the flat tally still counts every check, tag or no tag",
          E.count_verifiables(body) == (1, 1, 1))

    # -- the seed grammar
    check("kind: the seed parser reads the tag, not as evidence",
          E._parse_verifiable("[x] [outcome-neutral] control reproduces (found: 0.46)") ==
          {"tick": "x", "kind": "outcome-neutral", "text": "control reproduces",
           "evidence": "found: 0.46"})
    sd = tempfile.mkdtemp(prefix="crux_kseed_")
    seed = os.path.join(sd, "seed.md")
    with open(seed, "w", encoding="utf-8") as f:
        f.write("- Project: Kinded — a goal\n  - Q: a question\n    - H: a hypothesis\n"
                "      - v: the claim-directed check\n"
                "      - vn: the positive control\n")
    sroot = os.path.join(sd, "vault")
    E.cmd_init_from(seed, sroot)
    sh = E.Vault(sroot).get("h1")
    check("kind: a seed vn: line materializes as outcome-neutral",
          "- [ ] [outcome-neutral] the positive control" in sh["body"]
          and E.count_verifiables_by_kind(sh["body"])["outcome-neutral"] == (0, 1, 0))
    shutil.rmtree(sd, ignore_errors=True)

    # -- the CLI flag
    root = tempfile.mkdtemp(prefix="crux_kind_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Kinds", root)
    q1, _ = E.cmd_ask(root, "a question")
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize",
                        "with a control", "--parent", q1, "-v", "the claim check",
                        "-n", "the positive control", "--expect", "the claim holds"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    hc = E.Vault(root).get("h1")
    check("kind: the CLI -n flag writes an outcome-neutral verifiable",
          r.returncode == 0 and "- [ ] [outcome-neutral] the positive control" in hc["body"]
          and "- [ ] the claim check" in hc["body"])

    # -- spec 19: no gate. A control, a rule and a null are optional; running never refuses
    h2, _, _ = E.cmd_hypothesize(root, "no control at all", parent=q1,
                                 verifiables=["only a claim check"], expect="the claim holds")
    check("kind: running is NOT refused with no outcome-neutral check (spec 19)",
          E.cmd_test(root, h2, to="running") == "running")
    check("kind: validate does not flag a running node with no control and no opt-out",
          not any("outcome-neutral" in m for _, m in E.cmd_validate(root)))
    check("kind: a hypothesis WITH a control runs too",
          E.cmd_test(root, "h1", to="running") == "running")

    # -- an unknown tag is a validate problem on a stamped node
    hb, _, _ = E.cmd_hypothesize(root, "bad tag", parent=q1, verifiables=["[banana] a check"],
                                 expect="the check holds")
    check("kind: an unknown kind tag is a validate problem",
          any(i == hb and "banana" in m for i, m in E.cmd_validate(root)))

    check("kind: ENGINE_VERSION at or past 1.7", at_least_version("1.7"))
    shutil.rmtree(root, ignore_errors=True)

    # -- a seeded [tested] hypothesis is reconstructed history, not new work
    sd2 = tempfile.mkdtemp(prefix="crux_ktseed_")
    seed2 = os.path.join(sd2, "seed.md")
    with open(seed2, "w", encoding="utf-8") as f:
        f.write("- Project: Recon — a goal\n  - Q: a question\n"
                "    - H: [tested] work done before crux was watching\n"
                "      - v: [x] the check that was met\n"
                "      - finding: it held\n"
                "    - H: genuinely new work\n      - expect: the check holds\n"
                "      - v: a check\n")
    sroot2 = os.path.join(sd2, "vault")
    E.cmd_init_from(seed2, sroot2)
    sv2 = E.Vault(sroot2)
    check("kind: a seeded [tested] hypothesis is NOT stamped (reconstructed history)",
          "schema" not in sv2.get("h1")["fm"] and sv2.get("h1").status == "done")
    check("kind: a seeded UNTESTED hypothesis is stamped (genuinely new work)",
          sv2.get("h2")["fm"].get("schema") == E.SCHEMA_GENERATION)
    check("kind: a seeded [tested] hypothesis is not asked for a control it never had",
          E.cmd_validate(sroot2) == [])
    check("kind: its recorded verdict is derived, not invented",
          sv2.get("h1")["fm"]["verdict"] == "supported")
    shutil.rmtree(sd2, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary holds
    old = tempfile.mkdtemp(prefix="crux_kmig_")
    E.cmd_init("Legacy Evidence", old)
    oq, _ = E.cmd_ask(old, "a pre-15 question")
    oh, _, _ = E.cmd_hypothesize(old, "a pre-15 hypothesis", parent=oq,
                                verifiables=["first check", "second check"],
                                expect="both checks hold")
    _strip_schema(old)
    edit(os.path.join(old, E.VAULT_MARKER), f"engine_version: {E.ENGINE_VERSION}",
         "engine_version: 1.5")
    check("evmig: an unstamped hypothesis runs with no outcome-neutral check",
          E.cmd_test(old, oh, to="running") == "running")
    check("evmig: a pre-15 vault raises no kind problem",
          E.cmd_validate(old) == [] and E.validation_report(old)["warnings"] == [])
    shutil.rmtree(old, ignore_errors=True)

    # the committed pre-15 fixture's flat tally is the oracle: it must not move
    dvr = os.path.join(HERE, "..", "examples", "demo_vault")
    dvv = E.Vault(dvr)
    check("evmig: the flat tally is unchanged for pre-15 bodies",
          E.count_verifiables(dvv.get("h1")["body"]) == (2, 0, 0)
          and E.count_verifiables(dvv.get("h2")["body"]) == (1, 1, 0))
    check("evmig: pre-15 bodies read as all-hypothesis under the split",
          E.count_verifiables_by_kind(dvv.get("h2")["body"]) ==
          {"hypothesis": (1, 1, 0), "outcome-neutral": (0, 0, 0)})


def _err_text(fn):
    try:
        fn(); return ""
    except E.CruxError as e:
        return str(e)


# The pre-15 verdict truth table, captured from the engine BEFORE evidence semantics landed
# and pasted here as a literal. It is the oracle for "the engine never overturns recorded
# science": `derive_verdict` is the function a pre-15 node is still closed with, and it must
# never move again. x = met, u = unmet, - = could not evaluate.
_LEGACY_TRUTH_TABLE = {
        '-': 'inconclusive',  'u': 'refuted',  'x': 'supported',
        '--': 'inconclusive',  '-u': 'refuted',  '-x': 'inconclusive',
        'u-': 'refuted',  'uu': 'refuted',  'ux': 'partial',
        'x-': 'inconclusive',  'xu': 'partial',  'xx': 'supported',
        '---': 'inconclusive',  '--u': 'refuted',  '--x': 'inconclusive',
        '-u-': 'refuted',  '-uu': 'refuted',  '-ux': 'partial',
        '-x-': 'inconclusive',  '-xu': 'partial',  '-xx': 'inconclusive',
        'u--': 'refuted',  'u-u': 'refuted',  'u-x': 'partial',
        'uu-': 'refuted',  'uuu': 'refuted',  'uux': 'partial',
        'ux-': 'partial',  'uxu': 'partial',  'uxx': 'partial',
        'x--': 'inconclusive',  'x-u': 'partial',  'x-x': 'inconclusive',
        'xu-': 'partial',  'xuu': 'partial',  'xux': 'partial',
        'xx-': 'inconclusive',  'xxu': 'partial',  'xxx': 'supported',
    }


def run_combination_rule():
    """Spec 15 PRD 15.2 — the declared combination rule, `invalid-run`, and a verdict with
    no `partial` in its image.

    "Two of four passed" was an argument, settled after the results were visible. A rule
    declared BEFORE the run makes it arithmetic. ICH E9 2.2.5 offers the menu as a
    quantifier — any / some minimum number / all — and that is what ships. `ordered` is
    reserved and refused (PI ruling D1)."""
    print("\n# evidence semantics — the combination rule and the verdict (spec 15, PRD 15.2)")

    # -- the legacy path is frozen. This is the whole grandfathering guarantee.
    moved = {k: (want, E.derive_verdict(k.count("x"), k.count("u"), k.count("-")))
             for k, want in _LEGACY_TRUTH_TABLE.items()
             if E.derive_verdict(k.count("x"), k.count("u"), k.count("-")) != want}
    check(f"evmig: the legacy verdict truth table is byte-identical (moved: {moved})", not moved)
    check("evmig: the legacy function still refuses the empty vector",
          E.derive_verdict(0, 0, 0) is None)

    # -- the vocabulary grows, and never shrinks
    check("rule: VERDICTS is additive-only",
          set(E.VERDICTS) >= {"supported", "partial", "refuted", "inconclusive"}
          and "invalid-run" in E.VERDICTS)
    check("rule: every verdict token is a valid CSS class suffix",
          all(v and " " not in v and "\t" not in v for v in E.VERDICTS))
    check("rule: partial is retired from the derivation, not from the vocabulary",
          "partial" in E.VERDICTS)

    # -- the closed vocabulary of rules, and the reserved token
    check("rule: the rule vocabulary is closed",
          E.COMBINATION_RULES == ("all", "any", "m-of-n")
          and "ordered" in E.RESERVED_RULES)
    expect_error("rule: an unknown rule is refused",
                 lambda: E.derive_verdict_15((1, 0, 0), (1, 0, 0), "most", None))
    err = _err_text(lambda: E.derive_verdict_15((1, 0, 0), (1, 0, 0), "ordered", None))
    check("rule: ordered is reserved and refused, naming spec 15",
          "ordered" in err and "15" in err and "reserved" in err.lower())
    expect_error("rule: m-of-n requires a valid m",
                 lambda: E.derive_verdict_15((2, 1, 0), (1, 0, 0), "m-of-n", None))
    expect_error("rule: m-of-n refuses an m outside 1..n",
                 lambda: E.derive_verdict_15((2, 1, 0), (1, 0, 0), "m-of-n", 4))

    # -- run validity is read FIRST, and it is not a refutation
    check("rule: a failed control yields invalid-run, not refuted",
          E.derive_verdict_15((0, 3, 0), (0, 1, 0), "all", None) == "invalid-run"
          and E.derive_verdict_15((3, 0, 0), (0, 1, 0), "all", None) == "invalid-run")
    check("rule: an unread control yields invalid-run (assay sensitivity unproven)",
          E.derive_verdict_15((3, 0, 0), (0, 0, 1), "all", None) == "invalid-run")
    check("rule: a hypothesis with only controls yields invalid-run",
          E.derive_verdict_15((0, 0, 0), (1, 0, 0), "all", None) == "invalid-run")

    # -- the three rules
    ok = (1, 0, 0)      # one passing control, so run validity never masks the claim branch
    check("rule: all with one unmet is refuted, not partial",
          E.derive_verdict_15((1, 1, 0), ok, "all", None) == "refuted"
          and E.derive_verdict((1, 1, 0)[0], 1, 0) == "partial")
    check("rule: all with every check met is supported",
          E.derive_verdict_15((3, 0, 0), ok, "all", None) == "supported")
    check("rule: all with an unread check is inconclusive",
          E.derive_verdict_15((2, 0, 1), ok, "all", None) == "inconclusive")
    check("rule: any with one met is supported",
          E.derive_verdict_15((1, 3, 0), ok, "any", None) == "supported")
    check("rule: any with none met and none unread is refuted",
          E.derive_verdict_15((0, 3, 0), ok, "any", None) == "refuted")
    check("rule: m-of-n at or over the threshold is supported",
          E.derive_verdict_15((3, 2, 0), ok, "m-of-n", 3) == "supported")
    check("rule: m-of-n with m-1 passes is inconclusive",
          E.derive_verdict_15((2, 3, 0), ok, "m-of-n", 3) == "inconclusive")
    check("rule: m-of-n two or more short is refuted, not inconclusive",
          E.derive_verdict_15((1, 4, 0), ok, "m-of-n", 3) == "refuted"
          and E.derive_verdict_15((0, 5, 0), ok, "m-of-n", 3) == "refuted")
    check("rule: m-of-n still reachable through unread checks is inconclusive",
          E.derive_verdict_15((1, 0, 2), ok, "m-of-n", 3) == "inconclusive")

    # -- EXHAUSTIVE: every (kinds, rule, vector) maps to exactly one verdict, never partial
    import itertools
    bad_total, bad_partial = [], []
    for k in range(1, 5):
        for hv in itertools.product("xu-", repeat=k):
            hyp = (hv.count("x"), hv.count("u"), hv.count("-"))
            for nk in range(0, 3):
                for nv in itertools.product("xu-", repeat=nk):
                    neu = (nv.count("x"), nv.count("u"), nv.count("-"))
                    for rule in E.COMBINATION_RULES:
                        for m in (range(1, k + 1) if rule == "m-of-n" else (None,)):
                            got = E.derive_verdict_15(hyp, neu, rule, m)
                            if got not in E.VERDICTS:
                                bad_total.append((hyp, neu, rule, m, got))
                            if got == "partial":
                                bad_partial.append((hyp, neu, rule, m))
    check(f"rule: every (kinds, rule, vector) maps to exactly one verdict "
          f"(unmapped: {bad_total[:2]})", not bad_total)
    check(f"rule: partial is unreachable under evidence semantics "
          f"(reachable: {bad_partial[:2]})", not bad_partial)

    # -- spec 19: the rule is recorded and published, but it gates nothing and closes nothing
    root = tempfile.mkdtemp(prefix="crux_rule_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Rules", root)
    q1, _ = E.cmd_ask(root, "does the rule bind?")
    h1, _, _ = E.cmd_hypothesize(root, "all rule", parent=q1, rule="all",
                                 verifiables=["c one", "c two"], neutral=["control"],
                                 expect="both checks hold")
    edit(node_path(root, h1), "- [ ] c one", "- [x] c one")
    exp = R.render_experiments(E.Vault(root))
    check("rule: EXPERIMENTS carries a rule column",
          "| rule |" in exp and "| all |" in exp)
    snap = E.snapshot(root)
    check("rule: snapshot exposes the combination rule",
          snap["nodes"][h1]["rule"] == "all" and snap["nodes"][h1]["rule_m"] is None)
    check("rule: snapshot exposes the per-kind tallies",
          snap["nodes"][h1]["tally"] == {"hypothesis": [1, 1, 0], "outcome-neutral": [0, 1, 0]})
    check("rule: ticks alone never move the state — only a finding does (spec 19)",
          snap["nodes"][h1]["state"] == "open")
    expect_error("rule: a reserved rule is still refused at creation",
                 lambda: E.cmd_hypothesize(root, "ordered", parent=q1, rule="ordered",
                                           verifiables=["a", "b"], expect="a then b"))
    h3, _, _ = E.cmd_hypothesize(root, "no rule", parent=q1, expect="both hold",
                                 verifiables=["c one", "c two"], neutral=["control"])
    check("rule: running is NOT refused with no combination rule (spec 19)",
          E.cmd_test(root, h3, to="running") == "running")
    check("rule: validate raises no rule problem on a running multi-check node",
          not any(i == h3 for i, _ in E.cmd_validate(root)))
    check("rule: ENGINE_VERSION at or past 1.8", at_least_version("1.8"))
    shutil.rmtree(root, ignore_errors=True)

    # the committed pre-15 fixture keeps its recorded partial (history the 4.0 migration reads)
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    dst = tempfile.mkdtemp(prefix="crux_rdemo_")
    shutil.rmtree(dst); shutil.copytree(src, dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    dv = E.Vault(dst)
    check("evmig: a recorded partial survives on disk and in the experiments registry",
          dv.get("h2")["fm"]["verdict"] == "partial"
          and "| partial |" in R.render_experiments(dv))
    shutil.rmtree(dst, ignore_errors=True)


def run_hash_lock():
    """Spec 15 PRD 15.3 — the hash-lock. Bare pre-registration largely does not work
    (van den Akker 2023: no drop in positive results, 46% of pre-registered hypotheses simply
    missing from the paper). Registered Reports DO work — 44% positive vs 96% — and the
    active ingredient is enforced commitment, not the document. crux can enforce what a
    journal cannot, because verifiables are content-addressable.

    Edits are FLAGGED, never refused: research legitimately discovers a check was wrong, and
    refusing only launders the edit into a duplicate hypothesis."""
    print("\n# evidence semantics — the hash-lock and drift (spec 15, PRD 15.3)")
    root = tempfile.mkdtemp(prefix="crux_lock_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Locks", root)
    q1, _ = E.cmd_ask(root, "does the lock hold?")

    def mk(title, **kw):
        kw.setdefault("verifiables", ["alpha check", "beta check"])
        kw.setdefault("neutral", ["the control"])
        kw.setdefault("rule", "all")
        kw.setdefault("expect", "both checks hold")
        hid, _, _ = E.cmd_hypothesize(root, title, parent=q1, **kw)
        return hid

    h1 = mk("locked at running")
    check("lock: an unrun hypothesis carries no lock",
          E.Vault(root).get(h1)["fm"].get("lock") is None)
    E.cmd_test(root, h1, to="running")
    n = E.Vault(root).get(h1)
    first_lock, first_at = n["fm"].get("lock"), n["fm"].get("locked")
    check("lock: running takes the lock",
          bool(first_lock) and bool(first_at) and n["fm"].get("lock_at") == "running")
    E.cmd_test(root, h1, to="running")
    n = E.Vault(root).get(h1)
    check("lock: re-running never re-locks",
          n["fm"].get("lock") == first_lock and n["fm"].get("locked") == first_at)
    check("lock: a fresh lock does not drift", not E.lock_drift(n) and E.cmd_validate(root) == [])

    # -- what must NOT trip it: the things a normal close does
    edit(node_path(root, h1), "- [ ] alpha check", "- [x] alpha check")
    check("lock: ticking a box is not drift", not E.lock_drift(E.Vault(root).get(h1)))
    edit(node_path(root, h1), "- [x] alpha check", "- [x] alpha check   (found: +0.02)")
    check("lock: a (found:) note is not drift", not E.lock_drift(E.Vault(root).get(h1)))
    edit(node_path(root, h1), "- [ ] beta check", "- [ ]  beta   check ")
    check("lock: whitespace reflow is not drift", not E.lock_drift(E.Vault(root).get(h1)))
    check("lock: a clean close leaves the vault valid", E.cmd_validate(root) == [])

    # -- what MUST trip it
    def drifts(hid, mutate, name):
        n = E.Vault(root).get(hid)
        before = read(n["path"])
        mutate(n["path"])
        d = E.lock_drift(E.Vault(root).get(hid))
        flagged = any(i == hid and "DRIFT" in m for i, m in E.cmd_validate(root))
        with open(n["path"], "w", encoding="utf-8") as f:
            f.write(before)
        check(name, d and flagged)

    drifts(h1, lambda p: edit(p, "beta   check", "an entirely different check"),
           "lock: editing a verifiable after running is drift")
    drifts(h1, lambda p: edit(p, "- [ ]  beta", "- [ ] [outcome-neutral] beta"),
           "lock: editing a kind after running is drift")
    drifts(h1, lambda p: edit(p, "rule: all", "rule: any"),
           "lock: editing the rule after running is drift")
    drifts(h1, lambda p: edit(p, "- [ ] [outcome-neutral] the control", "- [ ] [outcome-neutral] the control\n- [ ] a fourth check"),
           "lock: adding a verifiable is drift")
    drifts(h1, lambda p: edit(p, "- [ ] [outcome-neutral] the control\n", ""),
           "lock: removing a verifiable is drift")

    def _reorder(p):
        # swap the first two checks WITH their continuation lines — a real reorder moves the
        # whole block, and doing it that way keeps the test honest now that a check carries
        # its failure scenario on the line below it
        src = read(p).splitlines()
        head = next(i for i, l in enumerate(src) if l.startswith("## Verifiables"))
        idx = [i for i in range(head, len(src)) if re.match(r"- \[(.)\]", src[i])]
        a0, b0 = idx[0], idx[1]
        end = idx[2] if len(idx) > 2 else next(
            (i for i in range(b0 + 1, len(src)) if src[i].startswith("## ")), len(src))
        blk_a, blk_b = src[a0:b0], src[b0:end]
        with open(p, "w", encoding="utf-8") as f:
            f.write("\n".join(src[:a0] + blk_b + blk_a + src[end:]) + "\n")
    drifts(h1, _reorder, "lock: reordering the verifiables is drift")

    check("lock: reverting the edit clears drift",
          not E.lock_drift(E.Vault(root).get(h1)) and E.cmd_validate(root) == [])

    # -- spec 19: a hypothesis with no checks is never locked, so it stays free to gain them
    h2 = mk("checks added later", verifiables=[], neutral=[], rule=None)
    E.cmd_test(root, h2, to="running")
    check("lock: running a hypothesis with no checks takes no lock",
          E.Vault(root).get(h2)["fm"].get("lock") is None)
    n2 = E.Vault(root).get(h2)
    E.write_if_changed(n2["path"], E.render_doc(n2["fm"], n2["body"].replace(
        E._VERIFIABLES_PLACEHOLDER, "- [ ] a check defined after the run started")))
    check("lock: adding the first checks later is not drift",
          not E.lock_drift(E.Vault(root).get(h2)) and E.cmd_validate(root) == [])

    # -- surfaces
    snap = E.snapshot(root)
    check("lock: snapshot exposes lock state and drift",
          snap["nodes"][h1]["locked"] is True and snap["nodes"][h1]["drift"] is False)
    edit(node_path(root, h1), "an entirely", "an entirely")  # no-op, keep the file settled
    # -- D7: drift warns loudly and blocks NOTHING
    edit(node_path(root, h1), "beta   check", "a rewritten check")
    check("lock: drift is a validate problem",
          any(i == h1 and "DRIFT" in m for i, m in E.cmd_validate(root)))
    E.cmd_finding(root, h1, "moderate", why="held, though a check was rewritten after the run",
                  direction="supports")
    check("lock: drift does not block a finding (the engine flags; the judgment reads it)",
          E.derive_state(E.Vault(root), h1)["state"] == "leaning")
    check("lock: and the flag survives the finding — it is permanent",
          any(i == h1 and "DRIFT" in m for i, m in E.cmd_validate(root)))
    check("lock: no verb clears a drift flag",
          not any(hasattr(E, x) for x in ("cmd_unflag", "cmd_relock", "cmd_acknowledge")))

    # -- CRLF. The wiki source registry hashes raw BYTES (`_sha256_file`), which is why a
    #    Windows checkout with autocrlf broke demo_vault's `.sources.tsv` on CI. The lock
    #    must never inherit that class of bug: it hashes lock_material(), a string built from
    #    a body that `read()` already normalized in text mode. Pinned here so a future change
    #    to byte-hashing fails loudly instead of on someone else's runner.
    lf = E.Vault(root).get(h1)
    mat_lf = E.lock_material(lf)
    crlf = dict(lf); crlf["body"] = lf["body"].replace("\n", "\r\n")
    check("lock: lock_material is newline-invariant (CRLF == LF)",
          E.lock_material(E.Node(crlf)) == mat_lf)
    check("lock: the lock hash is newline-invariant",
          E.lock_hash(E.Node(crlf)) == E.lock_hash(lf))
    crlf_path = os.path.join(root, "crlf_probe.md")
    with open(crlf_path, "wb") as f:
        f.write(read(lf["path"]).replace("\n", "\r\n").encode("utf-8"))
    fm_c, body_c = E.parse_doc(E.read(crlf_path))
    check("lock: a CRLF file on disk round-trips to the same lock hash",
          E.lock_hash(E.Node(fm=fm_c, body=body_c, path=crlf_path, fn="crlf_probe.md"))
          == E.lock_hash(lf))
    os.remove(crlf_path)

    check("lock: ENGINE_VERSION at or past 1.9", at_least_version("1.9"))
    shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary holds
    old = tempfile.mkdtemp(prefix="crux_lmig_")
    E.cmd_init("Legacy Evidence", old)
    oq, _ = E.cmd_ask(old, "a pre-15 question")
    oh, _, _ = E.cmd_hypothesize(old, "a pre-15 hypothesis", parent=oq,
                                 verifiables=["first check", "second check"],
                                 expect="both checks hold")
    _strip_schema(old)
    E.cmd_test(old, oh, to="running")
    check("evmig: a pre-15 node never locks",
          E.Vault(old).get(oh)["fm"].get("lock") is None)
    edit(node_path(old, oh), "- [ ] first check", "- [x] a completely rewritten check")
    check("evmig: a pre-15 node never drifts, however its checks are rewritten",
          not E.lock_drift(E.Vault(old).get(oh)) and E.cmd_validate(old) == []
          and E.validation_report(old)["warnings"] == [])
    shutil.rmtree(old, ignore_errors=True)

    # -- D9: a seeded [tested] hypothesis is reconstructed history. No lock, and the boundary
    #    notice says so in its own words rather than calling a vault made today "old".
    sd = tempfile.mkdtemp(prefix="crux_lseed_")
    seed = os.path.join(sd, "seed.md")
    with open(seed, "w", encoding="utf-8") as f:
        f.write("- Project: Recon — a goal\n  - Q: a question\n"
                "    - H: [tested] work done before crux was watching\n"
                "      - v: [x] the check that was met\n      - finding: it held\n")
    sroot = os.path.join(sd, "vault")
    E.cmd_init_from(seed, sroot)
    sn = E.Vault(sroot).get("h1")
    check("lock: a seeded tested hypothesis has no lock and no drift",
          sn["fm"].get("lock") is None and not E.lock_drift(sn))
    check("lock: a reconstructed hypothesis is marked as such",
          sn["fm"].get("reconstructed") is True)
    info = E.validation_report(sroot)["info"]
    check("lock: validate says reconstructed, not merely 'predates'",
          any(i["id"] == "boundary:reconstructed" and "never pre-registered" in i["message"]
              for i in info))
    check("lock: a reconstructed hypothesis is still not a problem or a warning",
          E.cmd_validate(sroot) == [] and E.validation_report(sroot)["warnings"] == [])
    shutil.rmtree(sd, ignore_errors=True)


def run_rulebook():
    """Spec 19 — `skills/crux/SKILL.md` is the ALWAYS-ON core (the SessionStart hook injects it
    on every session in a vault repo), so it is held to a byte cap and a fixed set of parts.
    Everything else lives behind a pointer; these asserts keep the pointers live, the removed
    verbs out of every skill, and `/crux-wrap` showing records before it asks anything.

    The separability rulebook (spec 15, PRD 15.5) moved with the pre-run design material to
    `references/design.md`; it is still compared with the spec word for word."""
    import glob
    print("\n# the always-on core and the skill text (spec 19, C8)")
    sk_dir = os.path.join(HERE, "..")
    core_path = os.path.join(sk_dir, "SKILL.md")
    raw = open(core_path, "rb").read()
    skill = raw.decode("utf-8")
    check(f"core: SKILL.md is at most 8,192 bytes ({len(raw)})", len(raw) <= 8192)

    def section(text, head):
        """The body under the first `## ` heading that starts with `head`, up to the next."""
        m = re.search(r"^## " + re.escape(head) + r".*?$(.*?)(?=^## |\Z)", text, re.M | re.S)
        return m.group(1) if m else ""

    cap = section(skill, "Capture")
    check("core: the capture rules name question, hypothesis, finding and evidence",
          all(w in cap.lower() for w in ("question", "hypothesis", "finding", "evidence")))
    check("core: capture is silent, evidence is always recorded, an expectation comes first",
          "silently" in cap and "always recorded" in cap and "expectation" in cap
          and "before" in cap)
    bd = section(skill, "The tree and the taskhub")
    check("core: the tree/taskhub boundary is knowledge vs work, with the evidence route",
          "knowledge" in bd.lower() and "work" in bd.lower()
          and "only as evidence on a finding" in bd)
    check("core: the boundary carries one example of each side",
          bd.count("e.g.") >= 2 or bd.lower().count("example") >= 2 or bd.count("*\"") >= 2
          or len(re.findall(r'"[^"]{8,}"', bd)) >= 2)
    cl = section(skill, "Closure judgment")
    low = cl.lower()
    check("core: closure judges the evidence against expectation, null and verifiables",
          all(w in low for w in ("expectation", "null", "verifiables")))
    check("core: direction first, then confidence",
          "direction" in low and "confidence" in low
          and low.index("direction") < low.index("confidence"))
    check("core: the null cap binds supports findings only",
          "supports" in low and "only" in low and "not ruled out" in low)
    check("core: a failed control caps at weak, in every direction",
          "failed control" in low and "weak" in low)
    check("core: a near miss lowers confidence", "near miss" in low)
    check("core: a question finding has no direction", "no direction" in low)
    check("core: state is derived — strongest wins, newest breaks ties",
          "derived" in low and "strongest" in low and "newest" in low)
    check("core: there is no close step, and dropped nodes are parked",
          "no close step" in low and "park" in low)
    vo = section(skill, "Voice — the invisible notebook")
    check("core: the voice section is inline, under its own heading",
          bool(vo) and "mirror rule" in vo)
    pi = section(skill, "Still the PI's")
    check("core: what stays the PI's — autopilot start, unasked compute, merge to main, "
          "plain-words correction",
          all(w in pi for w in ("autopilot", "compute", "`main`", "plain words"))
          and "wins" in pi)
    rt = section(skill, "Router")
    router = ("crux-wrap", "crux-wiki", "crux-litsearch", "crux-autopilot", "crux-cockpit",
              "prezit", "storify", "crux-rd", "evolve-crux",
              "crux-capture", "crux-prerun", "crux-situate", "crux-migrate")
    lines = [l for l in rt.splitlines() if l.startswith("- ")]
    missing = [n for n in router
               if not any(f"**{n}**" in l and len(l) > len(n) + 30 for l in lines)]
    check(f"core: one router line, with its trigger, per skill and agent ({missing})",
          not missing)
    ptrs = sorted(set(re.findall(r"references/[\w.-]+\.md", skill)))
    dead = [p for p in ptrs if not os.path.isfile(os.path.join(sk_dir, p))]
    check(f"core: every references/*.md pointer resolves ({dead})", ptrs and not dead)
    refs = sorted("references/" + f for f in os.listdir(os.path.join(sk_dir, "references"))
                  if f.endswith(".md"))
    orphan = [r for r in refs if r not in ptrs]
    check(f"core: every references/*.md file is reached by a pointer in the core ({orphan})",
          not orphan)
    check("core: the agent-only prohibitions stay inline — glossary.md, the migration "
          "guardrail, generated files, the update tripwire",
          "never write to `glossary.md` directly" in skill.lower().replace("**", "")
          and "cruxvault/" in skill and "META.md" in skill
          and "stash" in skill)

    # ---- no removed verb survives in any skill text, except as "removed"
    repo = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
    gone = re.compile(r"crux (review|answer|pursue|approve|approve-null|synthesize|close)\b"
                      r"|`(review|answer|pursue|approve|approve-null|synthesize|close)`"
                      r"|task (accept|review)\b")
    texts = sorted(glob.glob(os.path.join(repo, "skills", "*", "SKILL.md"))
                   + glob.glob(os.path.join(repo, "skills", "crux", "references", "*.md")))
    stale = [f"{os.path.relpath(p, repo)}:{i}" for p in texts
             for i, l in enumerate(read(p).splitlines(), 1)
             if gone.search(l) and "removed" not in l]
    check(f"core: no removed verb appears in any skill text except as removed ({stale[:4]})",
          len(texts) > 9 and not stale)

    # ---- /crux-wrap: the capture agent, then the records, then one question per candidate
    wp = os.path.join(repo, "skills", "crux-wrap", "SKILL.md")
    check("wrap: skills/crux-wrap/SKILL.md exists", os.path.isfile(wp))
    w = read(wp) if os.path.isfile(wp) else ""
    fm = w.split("---")[1] if w.startswith("---") else ""
    check("wrap: frontmatter names the skill and its slash command",
          "name: crux-wrap" in fm and "description:" in fm and "/crux-wrap" in fm)
    check("wrap: it runs the capture agent, told it was started by /crux-wrap",
          "crux-capture" in w and "--source wrap" in w)
    check("wrap: it reads the real verbs — wrap --json, pending list, pending clear",
          all(x in w for x in ("crux wrap --json", "crux pending list", "crux pending clear")))
    i_rec = w.find("already recorded")
    i_ask = w.find("AskUserQuestion")
    check("wrap: it shows what the session recorded BEFORE it asks anything",
          0 <= i_rec < i_ask)
    check("wrap: it asks only about the pending candidates, one question each, accept or reject",
          "only" in w[i_ask - 400:i_ask + 400] and "pending" in w[i_ask - 400:i_ask + 400]
          and "accept" in w.lower() and "reject" in w.lower())
    for sub in ("list", "add", "clear"):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "pending", sub,
                            "--help"], capture_output=True, text=True, encoding="utf-8")
        check(f"wrap: `crux pending {sub}` is a real verb", r.returncode == 0)

    # ---- the separability rulebook, where the pre-run design material now lives
    design = read(os.path.join(sk_dir, "references", "design.md")) \
        if os.path.isfile(os.path.join(sk_dir, "references", "design.md")) else ""
    spec = read(os.path.join(HERE, "..", "..", "..", ".spec", "15-evidence-semantics.md"))

    def sentence(text):
        head = "One experiment settles several hypotheses separately only when"
        flat = " ".join(text.replace(">", " ").replace("*", "").split())
        i = flat.find(head)
        if i < 0:
            return None
        j = flat.find("answers.", i)
        return flat[i:j + len("answers.")] if j > 0 else None

    a, b = sentence(spec), sentence(design)
    check("rulebook: the separability sentence is in references/design.md", b is not None)
    check("rulebook: the separability sentence matches the spec word for word", a and a == b)
    check("rulebook: the three separability lines are there",
          all(x in design for x in ("**Different lever.**", "**Different failure.**",
                                    "**Different verdict.**")))
    check("rulebook: a shared control is the fix, not the flaw", "the fix, not the" in design)
    check("rulebook: the joint-power cost is stated with its constraint",
          "64% joint power" in design and "not be loosened" in " ".join(design.split()))
    check("rulebook: the drift rule says it blocks nothing",
          "drift" in design and "blocks nothing" in design)
    spec09 = read(os.path.join(HERE, "..", "..", "..", ".spec", "09-specialized-agents.md"))
    check("rulebook: spec 09 carries the crux-verifiables amendment",
          "`crux-verifiables` gains a job" in spec09 and "64% joint power" in spec09
          and "Choose the combination rule" in spec09)
    check("rulebook: spec 15's work items are ticked for what shipped",
          spec.count("- ☑ ") >= 10 and "**Status:** ◐" in spec)


def _task_vault(prefix="crux_task_"):
    """A small vault with one question and one hypothesis — the substrate every taskhub
    test needs before it can ref anything."""
    root = tempfile.mkdtemp(prefix=prefix)
    E.cmd_init("Task Demo", root, goal="Ship the taskhub.")
    q, _ = E.cmd_ask(root, "Can the taskhub hold months of work?")
    h, _, _ = E.cmd_hypothesize(root, "one file per task survives churn", parent=q,
                                verifiables=["ids never renumber"], expect="ids never renumber")
    return root, q, h


def run_taskhub():
    print("\n# taskhub — the task store (spec 08, PRD 08.0)")
    root = tempfile.mkdtemp(prefix="crux_task_")
    E.cmd_init("Task Demo", root, goal="Ship the taskhub.")
    q, _ = E.cmd_ask(root, "Can the taskhub hold months of work?")
    h, _, _ = E.cmd_hypothesize(root, "one file per task survives churn", parent=q,
                                verifiables=["ids never renumber"], expect="ids never renumber")

    # -- 1. the record lands under tasks/ with an engine-allocated id
    t1, fn1 = E.cmd_task_add(root, "Dedupe the reused accessions", category="data-acquisition",
                             refs=[q, h], blocked_by=None)
    tp1 = os.path.join(root, E.TASK_DIR, fn1)
    check("task: add writes a file under tasks/ with an allocated id",
          t1 == "t1" and os.path.isfile(tp1) and fn1.startswith("t1_"))

    # -- 2. ids are immutable across add / drop / re-parent. spec-kit's append-only
    #       convergence, minus the part it left to LLM discipline.
    t2, _ = E.cmd_task_add(root, "Stand up the H100 partition", category="hpc-setup", blocked_by=None)
    t3, _ = E.cmd_task_add(root, "Implement the arm", category="implementation", blocked_by=[t1])
    t4, _ = E.cmd_task_add(root, "Draft figure 3", category="manuscript", blocked_by=None)
    E.cmd_task_drop(root, t2)
    p4 = E.Vault(root) and [x for x in E.scan_tasks(root) if x["id"] == t4][0]["path"]
    edit(p4, "parent:", f"parent: {t3}")
    t5, _ = E.cmd_task_add(root, "Write the caption", category="manuscript", blocked_by=None)
    ids = [x["id"] for x in E.scan_tasks(root)]
    check("task: ids survive add, drop and re-parent without renumbering",
          ids == ["t1", "t2", "t3", "t4", "t5"] and t5 == "t5")

    # -- 4. NOTHING regenerates a task. True on `main` before this PRD (the layer did not
    #       exist), so this is a REGRESSION LOCK: it fails the day someone adds tasks/ to
    #       refresh's write set, which is the one thing spec-kit got wrong.
    before = _dir_bytes(os.path.join(root, E.TASK_DIR))
    E.refresh(root); E.cmd_validate(root); E.validation_report(root)
    E.snapshot(root); E.status_text(root)
    check("task: a task file is byte-identical after every read path",
          _dir_bytes(os.path.join(root, E.TASK_DIR)) == before)

    # -- 5. adding a task never edits a node. This is what makes many-to-many free, and it
    #       is the half of the backlink split that stays DERIVED (07's RD:: is written).
    nodes_before = {n: read(node_path(root, n)) for n in (q, h)}
    E.cmd_task_add(root, "Fetch the antibody lot", category="data-acquisition",
                   refs=[q, h], blocked_by=None)
    check("task: adding a task modifies no node file",
          all(read(node_path(root, n)) == b for n, b in nodes_before.items()))

    # -- 6. a task is not a node: outside v.nodes, outside the roll-up, outside the gate
    v = E.Vault(root)
    ledger_before = E.ledger_counts(v, q)
    check("task: a task is invisible to the roll-up tree",
          not any(x.startswith("t") for x in v.nodes)
          and t1 not in v.nodes and E.ledger_counts(E.Vault(root), q) == ledger_before)

    # -- 7/8. category is a closed, declared list, and `experiment` is RESERVED — refused by
    #         the ENGINE (not argparse), exactly as 15.2 reserves `ordered`. In this PRD no
    #         task can legitimately be one, so the refusal is total.
    expect_error("task: category experiment is reserved and refused",
                 lambda: E.cmd_task_add(root, "run the pilot", category="experiment",
                                        blocked_by=None))
    expect_error("task: an undeclared category is refused",
                 lambda: E.cmd_task_add(root, "do a thing", category="proteomics",
                                        blocked_by=None))
    cats = E.task_categories(root) + (E.TASK_RESERVED_CATEGORY,)
    check("task: every category token is a valid CSS class suffix",
          all(c and not re.search(r"\s", c) for c in cats))

    # -- 9. refs must resolve. ISA-Tab's join-by-shared-string is the failure mode to avoid:
    #       N:M machinery with no referential integrity.
    edit(tp1, f"refs: {q}, {h}", f"refs: {q}, h99")
    check("task: an unresolvable ref is a validate problem",
          any("h99" in m for _, m in E.cmd_validate(root)))
    edit(tp1, f"refs: {q}, h99", f"refs: {q}, {h}")

    # -- 10. `blocked` is COMPUTED (08.1) and therefore must never be storable
    edit(tp1, "status: open", "status: blocked")
    check("task: blocked is never a storable status",
          any("blocked" in m and t1 in i for i, m in E.cmd_validate(root)))
    edit(tp1, "status: blocked", "status: open")

    # -- 11/12/13. `done` hard-requires an output that resolves
    expect_error("task: done without an output is refused",
                 lambda: E.cmd_task_done(root, t1))
    E.cmd_task_done(root, t1, outputs=["results/dedupe/table.tsv the deduped accessions"])
    check("task: done with an unresolvable output fails validate",
          any("table.tsv" in m for _, m in E.cmd_validate(root)))
    write(os.path.join(root, "results", "dedupe", "table.tsv"), "a\tb\n")
    check("task: a resolving path output clears validate",
          not any("table.tsv" in m for _, m in E.cmd_validate(root)))
    E.cmd_task_done(root, t3, outputs=[f"[[{h}]]"])
    check("task: a wikilink output resolves",
          not any(t3 in i for i, _ in E.cmd_validate(root)))
    check("task: dropping needs no output",
          [x for x in E.scan_tasks(root) if x["id"] == t2][0]["status"] == "dropped"
          and not any(t2 in i for i, _ in E.cmd_validate(root)))

    # -- 14/15. blocked_by is MANDATORY so a missing edge is a visible omission, and a
    #           dangling edge is a broken one
    p5 = [x for x in E.scan_tasks(root) if x["id"] == t5][0]["path"]
    check("task: blocked_by is mandatory and None is the literal for no edge",
          "blocked_by: None" in read(p5))
    edit(p5, "blocked_by: None", "blocked_by: t99")
    check("task: a dangling blocked_by edge is a validate problem",
          any("t99" in m for _, m in E.cmd_validate(root)))
    edit(p5, "blocked_by: t99", "")
    check("task: a missing blocked_by is a validate problem",
          any("blocked_by" in m and t5 in i for i, m in E.cmd_validate(root)))
    edit(p5, "refs:", "blocked_by: None\nrefs:")

    # -- 16. a task written to the vault ROOT is caught BY NAME. Vault keys on `id`, not
    #        `type`, so it would otherwise land in v.nodes and report `unknown type 'task'`
    #        — a true message pointing at the wrong thing.
    stray = os.path.join(root, "t99_stray.md")
    write(stray, "---\nid: t99\ntype: task\ntitle: stray\n---\n\n# t99\n")
    msgs = [m for i, m in E.cmd_validate(root) if i == "t99"]
    check("task: a task at the vault root is refused by name",
          any(E.TASK_DIR in m for m in msgs) and not any("unknown type" in m for m in msgs))
    os.remove(stray)

    # -- 17. the dropped count is INFORMATION. 15.0 built the tier; 08 claims a namespace
    #        and consumes it. A dropped task is a decision, not a defect.
    rep = E.validation_report(root)
    ti = [x for x in rep["info"] if x["id"].startswith("task:")]
    check("task: the dropped count is info and does not affect ok",
          ti and ti[0]["count"] == 1 and rep["ok"] is True and not rep["problems"])
    check("task: the task info namespace is declared",
          "task" in E.INFO_NAMESPACES and all(x["id"].split(":")[0] in E.INFO_NAMESPACES
                                              for x in rep["info"]))

    # -- 18. the lint is independently selectable
    edit(p5, "blocked_by: None", "blocked_by: t99")
    check("task: the tasks check is selectable",
          any("t99" in m for _, m in E.cmd_validate(root, ["tasks"]))
          and not any("t99" in m for _, m in E.cmd_validate(root, ["tree"])))
    edit(p5, "blocked_by: t99", "blocked_by: None")

    # -- 3. M3: every vault that exists today has no `counter_t`. The naive
    #       `v.cfg[key] += 1` raises KeyError on the FIRST task ever added after an upgrade,
    #       which is the most likely first action a user takes.
    old = tempfile.mkdtemp(prefix="crux_task_pre08_")
    E.cmd_init("Task Demo", old, goal="Ship the taskhub.")
    _oq, _ = E.cmd_ask(old, "Can the taskhub hold months of work?")
    _oh, _, _ = E.cmd_hypothesize(old, "one file per task survives churn", parent=_oq,
                                verifiables=["ids never renumber"], expect="ids never renumber")
    cfg = os.path.join(old, ".crux.yaml")
    write(cfg, "\n".join(l for l in read(cfg).splitlines()
                         if not l.startswith(("counter_t", "task_categories"))) + "\n")
    tid, _ = E.cmd_task_add(old, "first task after the upgrade", category="implementation",
                            blocked_by=None)
    check("taskmig: a pre-08 vault allocates t1 without a KeyError", tid == "t1")
    check("taskmig: a pre-08 vault falls back to the default categories",
          E.task_categories(old) == E.DEFAULT_TASK_CATEGORIES)
    shutil.rmtree(old, ignore_errors=True)

    # -- 19. the committed pre-08 fixture, upgraded.
    #
    #    NOTE ON WHAT THIS ASSERTS, AND WHY IT IS NOT A NAIVE BYTE-COMPARE. The committed
    #    demo_vault was last regenerated at 1.3, and `refresh` at 1.9 ALREADY rewrites its
    #    generated views: spec 15 added `invalid-run` to the dashboard and to every ledger
    #    summary line, and a `rule` column to EXPERIMENTS.md. That drift is spec 15's and it
    #    is present on this branch's parent — asserting byte-identity of generated views here
    #    would be asserting someone else's fixture is fresh, not that the taskhub is inert.
    #
    #    So the pre-existing drift is SETTLED first (one refresh), and then the property this
    #    PRD actually owes is proven from there: the taskhub adds nothing to, and takes
    #    nothing from, a vault that has no tasks.
    fx = tempfile.mkdtemp(prefix="crux_task_fx_")
    dst = os.path.join(fx, "demo")
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    verdicts0 = {k: n["fm"].get("verdict") for k, n in E.Vault(dst).nodes.items()}
    E.check_and_stamp_version(dst); E.refresh(dst)          # settle spec 15's view drift
    b0 = _dir_bytes(dst)
    E.refresh(dst); E.snapshot(dst); E.status_text(dst)
    rep0 = E.validation_report(dst)
    verdicts1 = {k: n["fm"].get("verdict") for k, n in E.Vault(dst).nodes.items()}
    b1 = _dir_bytes(dst)
    check("taskmig: a settled pre-08 vault is byte-identical under every 2.0 read path",
          b0 == b1 and E.refresh(dst) is False)
    check("taskmig: a pre-08 vault's recorded verdicts survive the 2.0 upgrade untouched",
          verdicts1 == verdicts0 and verdicts0["h2"] == "partial")
    check("taskmig: a pre-08 vault validates clean at 2.0", not rep0["problems"])
    check("taskmig: a pre-08 vault reports no task problems and no task info",
          not any(i.startswith("task") for i, _ in E.cmd_validate(dst))
          and not any(x["id"].startswith("task:") for x in rep0["info"])
          and not E.task_active(dst))
    check("taskmig: nothing creates tasks/ on a vault that has none",
          not os.path.exists(os.path.join(dst, E.TASK_DIR)))
    shutil.rmtree(fx, ignore_errors=True)

    check("task: ENGINE_VERSION bumped to 2.0", at_least_version("2.0"))
    shutil.rmtree(root, ignore_errors=True)


def run_task_graph():
    import json
    print("\n# taskhub — the dependency graph and the frontier (spec 08, PRD 08.1)")
    root = tempfile.mkdtemp(prefix="crux_taskdep_")
    E.cmd_init("Task Demo", root, goal="Ship the taskhub.")
    q, _ = E.cmd_ask(root, "Can the taskhub hold months of work?")
    h, _, _ = E.cmd_hypothesize(root, "one file per task survives churn", parent=q,
                                verifiables=["ids never renumber"], expect="ids never renumber")

    #   t1 ─┬─> t2 ─> t3        t4 (free)      t5 blocked by a task that gets DROPPED
    #       └─> t6
    t1, _ = E.cmd_task_add(root, "Dedupe the accessions", category="data-acquisition",
                           refs=[q], blocked_by=None)
    t2, _ = E.cmd_task_add(root, "Run the pilot", category="implementation", blocked_by=[t1])
    t3, _ = E.cmd_task_add(root, "Run the full sweep", category="implementation", blocked_by=[t2])
    t4, _ = E.cmd_task_add(root, "Draft figure 3", category="manuscript", blocked_by=None)
    t5, _ = E.cmd_task_add(root, "Port the old loader", category="implementation", blocked_by=[t4])
    t6, _ = E.cmd_task_add(root, "Register the dataset", category="data-acquisition", blocked_by=[t1])

    st = {t["id"]: E.task_state(t, E.task_by_id(root)) for t in E.scan_tasks(root)}
    check("dep: blocked is computed and agrees with the graph",
          st == {t1: "open", t2: "blocked", t3: "blocked", t4: "open",
                 t5: "blocked", t6: "blocked"})
    check("dep: the frontier is exactly the unblocked open tasks",
          [t["id"] for t in E.task_frontier(root)] == [t1, t4])

    # completing a blocker promotes its dependents — and only its dependents
    E.cmd_task_done(root, t1, outputs=[f"[[{q}]]"])
    check("dep: completing a blocker promotes its dependent",
          [t["id"] for t in E.task_frontier(root)] == [t2, t4, t6])

    # -- the hole in the spec's own acceptance criterion. Read literally ("blockers are all
    #    `done`"), a task whose blocker was DROPPED is blocked forever, invisibly, inside the
    #    one query the agent is told to work from. Ruling D9: a drop clears the edge, and the
    #    promotion is reported as info so it is never silent.
    E.cmd_task_drop(root, t4)
    check("dep: a dropped blocker clears the edge",
          t5 in [t["id"] for t in E.task_frontier(root)])
    info = {x["id"]: x for x in E.validation_report(root)["info"]}
    check("dep: a drop-cleared task is reported as info",
          "task:drop-cleared" in info and info["task:drop-cleared"]["count"] == 1
          and E.validation_report(root)["ok"] is True)

    # -- cycles, over BOTH edges: blocked_by cycles deadlock the frontier, parent cycles make
    #    "the gate fires once, on the parent" undefined
    by = E.task_by_id(root)
    edit(by[t3]["path"], f"blocked_by: {t2}", f"blocked_by: {t2}, {t6}")
    edit(by[t6]["path"], f"blocked_by: {t1}", f"blocked_by: {t3}")
    probs = [m for i, m in E.cmd_validate(root) if i in (t3, t6)]
    check("dep: a blocked_by cycle is caught with its path",
          any("cycle" in m and "→" in m for m in probs))
    edit(by[t6]["path"], f"blocked_by: {t3}", f"blocked_by: {t1}")
    edit(by[t3]["path"], f"blocked_by: {t2}, {t6}", f"blocked_by: {t2}")

    edit(by[t5]["path"], "parent:", f"parent: {t5}")
    check("dep: a self-edge is a cycle",
          any("cycle" in m for i, m in E.cmd_validate(root) if i == t5))
    edit(by[t5]["path"], f"parent: {t5}", "parent:")
    check("dep: the graph is clean once the cycles are removed",
          not any("cycle" in m for _, m in E.cmd_validate(root)))

    # a frontier query must never spin on a cycle — it reports and keeps working
    edit(by[t3]["path"], f"blocked_by: {t2}", f"blocked_by: {t3}")
    check("dep: a cyclic task is excluded from the frontier rather than hanging it",
          t3 not in [t["id"] for t in E.task_frontier(root)])
    edit(by[t3]["path"], f"blocked_by: {t3}", f"blocked_by: {t2}")

    # -- the query surface: one list verb with filters, not four verbs
    check("dep: list filters by ref and by blocker",
          [t["id"] for t in E.cmd_task_list(root, ref=q)] == [t1]
          and [t["id"] for t in E.cmd_task_list(root, blocks=t3)] == [t2]
          and [t["id"] for t in E.cmd_task_list(root, status="blocked")] == [t3])
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "list",
                        "--frontier", "--json"], capture_output=True, text=True,
                       encoding="utf-8", cwd=root)
    check("dep: the CLI frontier matches the engine frontier",
          r.returncode == 0 and [x["id"] for x in json.loads(r.stdout)]
          == [t["id"] for t in E.task_frontier(root)])

    # -- hierarchy is operative, not decorative (PI ruling 2026-08-21: warn, never refuse).
    #    A parent closed over unfinished parts is worth a flag; it is never a defect, so it
    #    lives at the info tier and `ok` must not turn on it.
    tp, _ = E.cmd_task_add(root, "Assemble the release", category="implementation")
    tc, _ = E.cmd_task_add(root, "Write the release notes", category="manuscript", parent=tp)
    E.cmd_task_done(root, tp, outputs=[f"[[{q}]]"])
    rep = E.validation_report(root)
    hinfo = {x["id"]: x for x in rep["info"]}
    check("hier: a done parent with an open subtask is reported as info",
          "task:open-subtasks" in hinfo and hinfo["task:open-subtasks"]["count"] == 1
          and tp in hinfo["task:open-subtasks"]["message"] and rep["ok"] is True)
    E.cmd_task_drop(root, tc)   # a drop is a decision — it discharges, exactly like a blocker
    check("hier: a terminal subtask discharges the warning",
          "task:open-subtasks" not in
          {x["id"] for x in E.validation_report(root)["info"]})

    # -- TASKHUB.md: shaped by the query it serves. The wiki layer taught this the hard way —
    #    its index resolved pages while queries were pitched at sub-page granularity, so
    #    retrieval fell back to grep.
    hub = os.path.join(root, E.TASK_INDEX)
    text = read(hub)
    fro, blocked = text.find("## Frontier"), text.find("## Blocked")
    check("hub: TASKHUB.md leads with the frontier",
          0 < fro < blocked and all(t["id"] in text for t in E.task_frontier(root)))
    check("hub: the frontier section lists exactly the frontier",
          [l for l in text[fro:blocked].splitlines() if l.startswith("- `")].__len__()
          == len(E.task_frontier(root)))
    # -- a ref is STORED as an id (stable) but RENDERED with the basename (followable). A
    #    bare `[[q1]]` resolves to nothing in Obsidian, because the file is `q1_<slug>.md`,
    #    and "full traversability is the point" is one of this layer's stated goals.
    qbase = E.Vault(root).get(q).basename
    check("hub: a node ref renders as a wikilink Obsidian can follow",
          f"[[{qbase}\\|{q}]]" in text
          and f"[[{qbase}\\|{q}]]" in E.task_by_id(root)[t1]["body"])
    check("hub: the stored ref stays the id, not the basename",
          E.task_by_id(root)[t1]["refs"] == [q])

    before = _dir_bytes(os.path.join(root, E.TASK_DIR))
    b0 = read(hub)
    E.refresh(root)
    check("hub: refresh never rewrites a task file",
          _dir_bytes(os.path.join(root, E.TASK_DIR)) == before)
    check("hub: TASKHUB.md regeneration is byte-stable", read(hub) == b0 and E.refresh(root) is False)
    check("hub: TASKHUB.md is generated, not a node",
          E.TASK_INDEX in E.GENERATED and E.TASK_INDEX[:-3] not in E.Vault(root).nodes
          and not any(t["fn"] == E.TASK_INDEX for t in E.scan_tasks(root)))

    # a vault with no tasks/ never grows the index — the `wiki_active` guard, copied verbatim
    plain = tempfile.mkdtemp(prefix="crux_nohub_")
    E.cmd_init("No Tasks", plain, goal="g")
    E.refresh(plain)
    check("taskmig: a vault with no tasks writes no TASKHUB.md",
          not os.path.exists(os.path.join(plain, E.TASK_INDEX)))
    shutil.rmtree(plain, ignore_errors=True)

    fx = tempfile.mkdtemp(prefix="crux_dep_fx_")
    dst = os.path.join(fx, "demo")
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    b = _dir_bytes(dst)
    E.refresh(dst); E.snapshot(dst); E.validation_report(dst)
    check("taskmig: refresh at 2.1 leaves a pre-08 vault byte-identical",
          _dir_bytes(dst) == b and not os.path.exists(os.path.join(dst, E.TASK_INDEX)))
    shutil.rmtree(fx, ignore_errors=True)

    check("dep: ENGINE_VERSION bumped to 2.1", at_least_version("2.1"))
def run_cockpit_evidence():
    """Spec 15 PRD 15.6 — the cockpit narrates evidence semantics.

    The manual check at the end of the 15 build found the engine publishing `drift`, `rule`
    and per-verifiable `kind` and the cockpit rendering none of them: a drifted hypothesis
    read as a clean `supported`, and on an `invalid-run` node the check whose failure CAUSED
    the verdict looked identical to the claim checks.

    That is spec 15 section 5's own failure — PLATO's rule "failed at narration time, not
    computation time". Computation was right; narration was missing.

    Webui only. No engine change, no version bump."""
    print("\n# evidence semantics — the cockpit narrates it (spec 15, PRD 15.6)")
    app_js = read(os.path.join(HERE, "webui", "app.js"))
    style = read(os.path.join(HERE, "webui", "style.css"))

    # ---- GUARD PARITY. The legend guard (derived from E.VERDICTS) is what forced
    # `invalid-run` into the cockpit during the 15 build. There was no equivalent guard for
    # the per-node fields, which is exactly why three of them shipped unrendered. This one is
    # derived from `snapshot()`'s ACTUAL published surface, so a field added to the engine
    # tomorrow joins the expectation without anyone remembering to update a list.
    root = tempfile.mkdtemp(prefix="crux_c15_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Cockpit Evidence", root)
    q1, _ = E.cmd_ask(root, "does the cockpit narrate it?")
    h1, _, _ = E.cmd_hypothesize(root, "drifted", parent=q1, rule="m-of-n", rule_m=2,
                                 verifiables=["alpha", "beta"], neutral=["the control"],
                                 expect="alpha and beta both hold")
    h2, _, _ = E.cmd_hypothesize(root, "broken apparatus", parent=q1, rule="all",
                                 verifiables=["alpha"], neutral=["the control"],
                                 expect="alpha holds")
    declare_null(root, h2)
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running"); E.cmd_test(root, h2, to="running")
    edit(node_path(root, h1), "- [ ] alpha", "- [x] alpha")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    edit(node_path(root, h1), "- [ ] beta", "- [x] a check nobody registered")   # -> DRIFT
    edit(node_path(root, h2), "- [ ] alpha", "- [x] alpha")
    write(os.path.join(root, E.RESULTS_DIR, h1, "report.md"), "# run\n")
    E.cmd_finding(root, h1, "strong", why="alpha cleared the bar", direction="supports",
                  evidence=[f"{E.RESULTS_DIR}/{h1}/report.md"], null="ruled-out",
                  vs_expect="as expected", verifiables="2 of 2")
    E.cmd_finding(root, h2, "weak", why="the control failed", direction="no-answer-yet")
    E.cmd_finding(root, q1, "moderate", answer="Mostly yes.")
    snap = E.snapshot(root)
    idea = snap["nodes"][h1]

    # Fields a reader legitimately never needs on screen. Small and justified on purpose —
    # this allowlist is the only place a field can hide, so it must stay embarrassing to add to.
    NOT_RENDERED = {
        "id", "type", "parent",        # structural: the tree already says all three
        "tally",                       # redundant: `verifiables` carries kind+state per item
        "schema",                      # the boundary is narrated by its ABSENCE of rule/kind
        "words",                       # already surfaced by economyBadge()
        "status",                      # spec 19 (Q14): no longer read; the state replaces it
    }
    def referenced(key):
        return any(p in app_js for p in (f'"{key}"', f".{key}", f"['{key}']"))
    unrendered = sorted(k for k in idea if k not in NOT_RENDERED and not referenced(k))
    check(f"webui: every published idea field is consumed by the cockpit (missing: {unrendered})",
          not unrendered)
    qn = snap["nodes"][q1]
    unrendered = sorted(k for k in qn if k not in NOT_RENDERED and not referenced(k))
    check(f"webui: every published question field is consumed by the cockpit "
          f"(missing: {unrendered})", not unrendered)
    vitem = idea["verifiables"][0]
    vmissing = sorted(k for k in vitem if f'v.{k}' not in app_js and f'"{k}"' not in app_js)
    check(f"webui: every published verifiable field is consumed (missing: {vmissing})",
          not vmissing)
    # spec 19: the same parity guard, one level down — every field a finding publishes
    fitem = idea["findings"][0]
    fmissing = sorted(k for k in fitem if k not in ("id", "parent")
                      and f"f.{k}" not in app_js)
    check(f"webui: every published finding field is consumed (missing: {fmissing})",
          not fmissing)

    # ---- the three spec-15 narrations, each asserted directly — they survive 4.0, because
    # the null, the rule and the checks survive as optional sections
    check("webui: the drift flag is rendered",
          "drift" in app_js and "n.drift" in app_js)
    check("webui: drift is called drift in the UI, not something softer",
          'class="badge drift"' in app_js)
    check("webui: the combination rule is rendered",
          "n.rule" in app_js and "rule_m" in app_js)
    check("webui: whether the commitment was pre-registered is rendered",
          "lock_at" in app_js and "n.locked" in app_js)
    check("webui: an outcome-neutral verifiable is marked in the pane",
          "v.kind" in app_js and "outcome-neutral" in app_js)
    check("webui: the expectation is rendered in the hypothesis pane",
          "n.expect" in app_js.split("function ideaDetail")[1].split("\nfunction ")[0])

    # ---- a drifted node must be distinguishable in the TREE, not only in the pane
    svg = app_js.split("function nodeSVG")[-1][:4000]
    check("webui: the tree renderer emits a drift mark on the node",
          "n.drift" in svg and "drift-mark" in svg and "drifted" in svg)
    check("webui: the drift mark is styled in the stylesheet",
          ".box.drifted" in style and ".drift-mark" in style)
    check("webui: drift is drawn WITHOUT overriding the state fill",
          "fill" not in style.split(".box.drifted")[1].split("}")[0])
    check("webui: a drift flip repaints the node in the in-place recolor path",
          'n.drift ? "D"' in app_js)

    # ---- any new colour must exist in BOTH themes (the rule the legend guard already applies)
    _blk = lambda sel: (re.search(sel + r"\s*\{(.*?)\n\}", style, re.S | re.M) or [None, ""])[1]
    dark, light = _blk(r"^:root"), _blk(r'^:root\[data-theme="light"\]')
    newvars = sorted(set(re.findall(r"var\((--(?:drift|s|c|d)-[a-z-]*)\)", app_js + style)))
    unstyled = [v for v in newvars if f"{v}:" not in dark or f"{v}:" not in light]
    check(f"webui: every state/confidence/direction/drift colour is defined in both themes "
          f"(missing: {unstyled})", bool(newvars) and not unstyled)

    # ---- and the engine still publishes what the cockpit now claims to read
    check("webui: the fixture carries drift, a rule, a control, and the 4.0 fields",
          idea["drift"] is True and idea["rule"] == "m-of-n" and idea["rule_m"] == 2
          and any(v["kind"] == "outcome-neutral" for v in idea["verifiables"])
          and idea["state"] == "settled" and idea["confidence"] == "strong"
          and snap["nodes"][h2]["state"] == "open" and qn["state"] == "leaning")

    # ---- spec 19 (C5): the generated views carry the state and the confidence, and no
    # review section — the gate they reported no longer exists
    import render as R
    E.cmd_park(root, h2)
    v = E.Vault(root)
    meta, exps = R.render_meta(v), R.render_experiments(v)
    check("views: META.md names every node's state",
          all(f"`{nid}`" in meta for nid in (q1, h1, h2))
          and "*settled*" in meta and "*leaning*" in meta and "*parked*" in meta)
    check("views: META.md names the confidence beside the state",
          "strong" in meta and "moderate" in meta)
    check("views: META.md has no review section",
          "review" not in meta.lower() and "Awaiting your decision" not in meta)
    check("views: META.md's dashboard counts by state and confidence, not by verdict",
          "**Questions**" in meta and "settled" in meta.split("## Dashboard")[1]
          and "**Confidence**" in meta and "Verdicts" not in meta)
    hdr = next((l for l in exps.splitlines() if l.startswith("| id ")), "")
    cols = [c.strip() for c in hdr.strip("|").split("|")]
    check(f"views: EXPERIMENTS.md has state and confidence columns ({cols})",
          cols[3:6] == ["state", "confidence", "direction"] and "status" not in cols
          # the one verdict column left is history, named as such (run_combination_rule
          # reads a recorded pre-15 partial from it)
          and [c for c in cols if "verdict" in c] == ["pre-4.0 verdict"])
    row = next((l for l in exps.splitlines() if l.startswith(f"| `{h1}`")), "")
    check("views: a hypothesis row carries its state, confidence and direction",
          "| settled |" in row and "| strong |" in row and "| supports |" in row)
    row2 = next((l for l in exps.splitlines() if l.startswith(f"| `{h2}`")), "")
    check("views: a parked hypothesis says parked", "| parked |" in row2)
    check("views: both views stay byte-stable",
          R.render_meta(E.Vault(root)) == meta and R.render_experiments(E.Vault(root)) == exps)
    shutil.rmtree(root, ignore_errors=True)


def run_experiments():
    print("\n# taskhub — experiments are tasks (spec 08, PRD 08.2)")
    root = tempfile.mkdtemp(prefix="crux_exp_")
    E.cmd_init("Task Demo", root, goal="Ship the taskhub.")
    q, _ = E.cmd_ask(root, "Can the taskhub hold months of work?")
    h1, _, _ = E.cmd_hypothesize(root, "one file per task survives churn", parent=q,
                                verifiables=["ids never renumber"], expect="ids never renumber")
    h2, _, _ = E.cmd_hypothesize(root, "the pilot separates the arms", parent=q,
                                 verifiables=["separation at n=3"], expect="the arms separate")

    # -- the whole difference between a task and an experiment is ONE field: what the output
    #    is. A task that says what it concluded about a hypothesis IS an experiment, and
    #    nothing is stored to say so.
    t1, _ = E.cmd_task_add(root, "Fetch the antibody lot", category="data-acquisition",
                           blocked_by=None)
    e1, _ = E.cmd_task_add(root, "Run the pilot", category="implementation", blocked_by=None,
                           hypothesis_refs=[(h1, "supported"), (h2, "refuted")])
    by = E.task_by_id(root)
    check("exp: hypothesis_refs computes the experiment category",
          E.task_category(by[e1]) == E.TASK_RESERVED_CATEGORY
          and E.task_category(by[t1]) == "data-acquisition")
    check("exp: is_experiment is computed, never stored",
          E.task_is_experiment(by[e1]) and not E.task_is_experiment(by[t1])
          and "is_experiment" not in read(by[e1]["path"])
          and f"category: {E.TASK_RESERVED_CATEGORY}" not in read(by[e1]["path"]))
    check("exp: category experiment stays hand-refused after the role exists",
          _refused(lambda: E.cmd_task_add(root, "x", category="experiment", blocked_by=None,
                                          hypothesis_refs=[(h1, "supported")])))

    # -- the conclusion vocabulary IS spec 15's, minus the retired `partial`. Derived from
    #    VERDICTS so it can never drift from the engine's own list.
    check("exp: the conclusion vocabulary is 15's VERDICTS minus partial",
          tuple(E.CONCLUSIONS) == tuple(x for x in E.VERDICTS if x != "partial")
          and "invalid-run" in E.CONCLUSIONS and "partial" not in E.CONCLUSIONS)
    expect_error("exp: partial is refused as a conclusion",
                 lambda: E.cmd_task_add(root, "y", category="implementation", blocked_by=None,
                                        hypothesis_refs=[(h1, "partial")]))
    expect_error("exp: an unknown conclusion is refused",
                 lambda: E.cmd_task_add(root, "y", category="implementation", blocked_by=None,
                                        hypothesis_refs=[(h1, "disputes")]))
    e2, _ = E.cmd_task_add(root, "Read the control", category="implementation", blocked_by=None,
                           hypothesis_refs=[(h1, "invalid-run")])
    check("exp: invalid-run is accepted and every token is a valid CSS class suffix",
          E.task_hypothesis_refs(E.task_by_id(root)[e2]) == [(h1, "invalid-run")]
          and all(not re.search(r"\s", c) for c in E.CONCLUSIONS))

    # -- one experiment, two hypotheses, OPPOSITE conclusions. This is the fact the tree
    #    structurally cannot hold, and the only structured place it exists.
    check("exp: one experiment carries opposite conclusions for two hypotheses",
          E.task_hypothesis_refs(E.task_by_id(root)[e1]) == [(h1, "supported"), (h2, "refuted")])

    # -- THE LEASH. Work never creates direction. Three negatives, proven not asserted-to.
    v0 = E.Vault(root)
    ledger0 = E.ledger_counts(v0, q)
    verdicts0 = {k: n["fm"].get("verdict") for k, n in v0.nodes.items()}
    nodes0 = {n: read(node_path(root, n)) for n in (q, h1, h2)}
    E.cmd_task_add(root, "Run the full sweep", category="implementation", blocked_by=None,
                   hypothesis_refs=[(h1, "refuted")])
    E.refresh(root)
    v1 = E.Vault(root)
    check("exp: adding an experiment modifies no node file",
          all(read(node_path(root, n)) == b for n, b in nodes0.items()))
    check("exp: a conclusion never enters the ledger roll-up",
          E.ledger_counts(v1, q) == ledger0)
    check("exp: a conclusion never writes a node verdict",
          {k: n["fm"].get("verdict") for k, n in v1.nodes.items()} == verdicts0)

    # -- refs must resolve to an IDEA. A task bearing on a question is refing the wrong thing;
    #    that is what plain `refs` is for.
    expect_error("exp: hypothesis_refs must resolve to an idea node",
                 lambda: E.cmd_task_add(root, "z", category="implementation", blocked_by=None,
                                        hypothesis_refs=[(q, "supported")]))
    # (the value is edited rather than the whole line: `fill()` writes it bare and
    #  `yaml_dump` would quote it, so both spellings are legal on disk)
    ep = E.task_by_id(root)[e2]["path"]
    edit(ep, f"{h1}:invalid-run", "h99:invalid-run")
    check("exp: a dangling hypothesis ref is a validate problem",
          any("h99" in m for _, m in E.cmd_validate(root)))
    edit(ep, "h99:invalid-run", f"{h1}:invalid-run")

    # -- the computed backlink: node -> experiments, never written into the node
    rec = E.node_json(root, h1)
    expected = [t["id"] for t in E.scan_tasks(root)
                if h1 in [x for x, _ in t["hypothesis_refs"]]]
    check("exp: a hypothesis lists its experiments as a computed backlink",
          [x["task"] for x in rec["experiments"]] == expected and len(expected) >= 3
          and rec["experiments"][0]["conclusion"] == "supported"
          and "experiments" not in read(node_path(root, h1)))
    check("exp: a node lists the ordinary tasks that serve it",
          E.node_json(root, q)["tasks"] == [t["id"] for t in E.cmd_task_list(root, ref=q)])

    # -- X3 as ruled: an experiment may bear on a PRE-15 hypothesis, and the schema each
    #    refed node carries is recorded in every view. Nothing is retro-stamped: the record
    #    lives on the task's side, and 15.0's guarantee is untouched.
    hp = node_path(root, h2)
    write(hp, read(hp).replace(f"schema: {E.SCHEMA_GENERATION}\n", ""))
    check("exp: the refed hypothesis is pre-15 for this check",
          E.node_schema(E.Vault(root).get(h2)) == 0)
    e3, _ = E.cmd_task_add(root, "Re-run the old arm", category="implementation",
                           blocked_by=None, hypothesis_refs=[(h2, "invalid-run")])
    check("exp: a pre-15 hypothesis is refable with the full vocabulary",
          not any(e3 in i for i, _ in E.cmd_validate(root)))
    check("exp: every view records which schema a refed hypothesis carries",
          E.task_json(root, e3)["hypothesis_refs"][0]["schema"] == 0
          and E.task_json(root, e1)["hypothesis_refs"][0]["schema"] == E.SCHEMA_GENERATION)
    check("exp: refing a pre-15 hypothesis does not stamp it",
          E.node_schema(E.Vault(root).get(h2)) == 0 and "schema:" not in read(hp))

    # -- one dependency graph, one frontier: the two reasons the layers were merged
    check("exp: the frontier spans chores and experiments in one query",
          {t1, e1} <= {t["id"] for t in E.task_frontier(root)})
    p1, _ = E.cmd_task_add(root, "Pilot first", category="implementation", blocked_by=None,
                           hypothesis_refs=[(h1, "inconclusive")])
    f1, _ = E.cmd_task_add(root, "Full run second", category="implementation",
                           blocked_by=[p1], hypothesis_refs=[(h1, "supported")])
    check("exp: a pilot blocks a full run in the one dependency graph",
          E.task_state(E.task_by_id(root)[f1], E.task_by_id(root)) == "blocked")

    # -- the timeline is a VIEW: the same records, filtered, in TASKHUB.md. `EXPERIMENTS.md`
    #    is a per-HYPOTHESIS registry and is a different artifact — it must not move.
    exp_before = read(os.path.join(root, "EXPERIMENTS.md"))
    E.refresh(root)
    hub = read(os.path.join(root, E.TASK_INDEX))
    tl = hub.find("## Experiment timeline")
    check("hub: the timeline filters to hypothesis_refs and is byte-stable",
          tl > 0 and all(x in hub[tl:] for x in (e1, e2, e3))
          and t1 not in hub[tl:] and E.refresh(root) is False)
    check("exp: EXPERIMENTS.md is untouched by the taskhub",
          read(os.path.join(root, "EXPERIMENTS.md")) == exp_before
          and "One row per hypothesis" in exp_before)
    check("exp: a task carries no schema stamp",
          not any("schema" in read(t["path"]) for t in E.scan_tasks(root)))

    # -- the CLI surface, following 15's `--rule` idiom: one repeatable flag, engine-validated
    import json as _json
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "add",
                        "Run the replicate", "-c", "implementation", "--blocked-by", "None",
                        "--concluded", f"{h1}:supported", "--json"],
                       capture_output=True, text=True, encoding="utf-8", cwd=root)
    out = _json.loads(r.stdout)
    check("exp: the CLI --concluded flag makes a task an experiment",
          r.returncode == 0 and out["is_experiment"]
          and out["category"] == E.TASK_RESERVED_CATEGORY
          and out["hypothesis_refs"][0] == {"id": h1, "conclusion": "supported",
                                            "schema": E.SCHEMA_GENERATION})
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "add",
                        "bad", "-c", "implementation", "--blocked-by", "None",
                        "--concluded", f"{h1}:partial"],
                       capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("exp: the CLI refuses a retired conclusion with a message naming spec 15",
          r.returncode == 1 and "retired" in r.stderr and "spec 15" in r.stderr)

    fx = tempfile.mkdtemp(prefix="crux_exp_fx_")
    dst = os.path.join(fx, "demo")
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    b = _dir_bytes(dst)
    E.refresh(dst); E.snapshot(dst); E.validation_report(dst)
    check("taskmig: a pre-08 vault is unchanged at 2.2", _dir_bytes(dst) == b)
    shutil.rmtree(fx, ignore_errors=True)

    # a sub-task that declares its OWN conclusion is its own experiment, and nesting is
    # still reported as information (task_gate_info), never as a problem
    e0, _ = E.cmd_task_add(root, "Full run", category="implementation", blocked_by=None,
                           hypothesis_refs=[(h1, "supported")])
    n1, _ = E.cmd_task_add(root, "Nested pilot", category="implementation", blocked_by=None,
                           parent=e0, hypothesis_refs=[(h1, "inconclusive")])
    rep = E.validation_report(root)
    check("exp: nesting is reported as info",
          any(x["id"] == "task:nested-experiment" and n1 in x["message"] for x in rep["info"])
          and not any(x["id"].startswith("task:") for x in rep["problems"] + rep["warnings"]))
    check("exp: ENGINE_VERSION bumped to 2.2", at_least_version("2.2"))
    shutil.rmtree(root, ignore_errors=True)


def run_task_gui():
    print("\n# taskhub — the snapshot block and the cockpit tab (spec 08, PRD 08.4)")
    root, q, h1 = _task_vault("crux_taskui_")
    t1, _ = E.cmd_task_add(root, "Dedupe the accessions", category="data-acquisition",
                           refs=[q], blocked_by=None)
    t2, _ = E.cmd_task_add(root, "Run the pilot", category="implementation", blocked_by=[t1],
                           hypothesis_refs=[(h1, "supported")])
    snap = E.snapshot(root)
    tb = snap["tasks"]
    check("ui: snapshot exposes the tasks block",
          set(tb) == {"active", "categories", "reserved_category", "conclusions",
                      "items", "frontier"} and tb["active"] is True)
    by = E.task_by_id(root)
    check("ui: snapshot's frontier and state match the engine",
          tb["frontier"] == [t["id"] for t in E.task_frontier(root)]
          and {i["id"]: i["state"] for i in tb["items"]}
          == {t["id"]: E.task_state(t, by) for t in E.scan_tasks(root)})
    item = {i["id"]: i for i in tb["items"]}
    check("ui: snapshot's is_experiment and computed category match the role",
          item[t2]["is_experiment"] and item[t2]["category"] == E.TASK_RESERVED_CATEGORY
          and item[t2]["declared_category"] == "implementation"
          and not item[t1]["is_experiment"])
    check("ui: snapshot publishes the vocabularies the cockpit must render",
          tb["conclusions"] == list(E.CONCLUSIONS)
          and tb["reserved_category"] == E.TASK_RESERVED_CATEGORY
          and tb["categories"] == list(E.task_categories(root)))

    # -- the backlinks reach the node pane, and reach NO node file
    check("ui: snapshot carries computed task backlinks",
          snap["nodes"][q]["tasks"] == [t1]
          and [x["task"] for x in snap["nodes"][h1]["experiments"]] == [t2])
    check("ui: no node file carries a task backlink",
          not any(t1 in read(node_path(root, n)) or t2 in read(node_path(root, n))
                  for n in (q, h1)))

    # -- every category and conclusion must survive `"t-" + cat` / `"v-" + concl` as a CSS
    #    class. Spec 15 learned this when `invalid run` produced the broken class
    #    `h-invalid run`; learning it once is the point of asserting it here too.
    check("ui: every category and conclusion is a valid CSS class suffix",
          all(c and not re.search(r"\s", c)
              for c in tb["categories"] + [tb["reserved_category"]] + tb["conclusions"]))

    E.cmd_task_done(root, t1, outputs=[f"[[{q}]]"])
    E.cmd_task_done(root, t2, outputs=[f"[[{q}]]"])
    tb = E.snapshot(root)["tasks"]
    # spec 19: no task waits for the PI any more — there is no queue to publish
    check("ui: no acceptance queue reaches the snapshot",
          "queue" not in tb and not any(i.get("pending_gate") for i in tb["items"]))

    # -- the webui must know every tab, category colour and conclusion the engine can emit.
    #    Derived from the constants rather than hand-listed, which is the one thing that made
    #    the verdict legend impossible to silently drift (selftest's own legend check).
    ui = read(os.path.join(HERE, "webui", "app.js"))
    html = read(os.path.join(HERE, "webui", "index.html"))
    css = read(os.path.join(HERE, "webui", "style.css"))
    tabs = re.findall(r'data-tab="([a-z]+)"', html)
    check("ui: the tab list is tree, wiki, the taskhub and autopilot — RD merged in, not beside",
          set(tabs) == {"tree", "wiki", "tasks", "auto"})
    check("ui: the taskhub tab is NAMED Taskhub",
          ">Taskhub<" in html)
    check("ui: the cockpit knows the taskhub is inert when absent",
          "tasksActive" in ui and "tasks-pane" in html)

    # ---- the 2026-08-21 taskhub repair. Every check below pins a defect the PI hit on a
    # live vault (four UX agents reproduced all of them on the 200-task SortLab vault):
    # the pane leaked into other tabs, its Views rail was wired to the wrong DOM subtree,
    # rows were inert, and the detail pane had no task branch at all.
    # (a) the pane must opt back in to [hidden] — the exact bug #wiki-pane and the old
    #     #rd-pane each already fixed for themselves; #tasks-pane had been skipped.
    check("taskgui: the taskhub pane opts back in to [hidden]",
          "#tasks-pane[hidden]" in css and 'id="tasks-pane" hidden' in html)
    # (b) and claim its flex share, or the detail pane eats the width
    check("taskgui: the taskhub pane claims the canvas share its siblings claim",
          bool(re.search(r"#tasks-pane \{[^}]*flex: 1 1 62%", css)))
    # (c) the Views rail listener must live where the buttons live — it was attached to
    #     #tabs while the buttons render in #tasks-rail-body, so clicks never arrived
    check("taskgui: the view switch is wired to the pane, not the tab bar",
          'data-tk-view' not in ui.split('$("tabs").addEventListener')[1].split("});")[0]
          and '$("tasks-pane").addEventListener' in ui)
    # (d) rows are BUTTONS carrying their id — a plain <div> can never open a detail
    check("taskgui: task rows are buttons that carry their task id",
          'data-task="' in ui and "<button" in ui.split("function taskRow")[1].split("\nfunction ")[0])
    # (e) the detail pane knows tasks: a dedicated renderer, a renderDetail branch, and a
    #     detailKeyOf case (without the key the poll would stomp the pane every 2s)
    check("taskgui: the detail pane has a task branch",
          "function taskDetail" in ui
          and '"tasks"' in ui.split("function renderDetail()")[1].split("\nfunction ")[0]
          and '"tasks"' in ui.split("function detailKeyOf()")[1].split("\nfunction ")[0])
    # (f) a status filter exists — spec 08's work item said "status filters" and shipped none
    check("taskgui: a status filter exists and persists",
          'data-tk-status' in ui and "crux-tasks-status" in ui)
    # (g) the tab bar logic counts the taskhub: a tasks-only vault must still show tabs,
    #     and a saved taskhub tab must survive reload
    upd = ui.split("function updateTabs()")[1].split("\nfunction ")[0]
    check("taskgui: the tab bar counts the taskhub",
          "hubActive()" in upd and 'data-tab="tasks"' in upd
          # the hub is live when EITHER half exists — tasks, or the merged-in RDs
          and "tasksActive() || rdActive()" in ui.split("function hubActive()")[1].split("\n")[0])
    check("taskgui: a saved taskhub tab survives reload",
          'want === "tasks"' in upd)
    # (h) the tree's view controls hide in the taskhub, as they already do in the wiki —
    #     four dead tree buttons leaking into every other mode was a live finding
    check("taskgui: tree view controls hide in the taskhub",
          'body[data-tab="tasks"]' in css)
    # (i) search serves the tab it is in: taskhub search matches tasks, and says so
    check("taskgui: search knows the taskhub",
          "Search taskhub" in ui
          and '"tasks"' in ui.split("function searchMatches()")[1].split("\nfunction ")[0])
    # (j) an experiment is tellable from a chore in the list itself
    check("taskgui: experiments are marked in the row",
          "is_experiment" in ui.split("function taskRow")[1].split("\nfunction ")[0])
    # (k) hypothesis chips in the task detail jump to the node (PI ruling: chips navigate)
    check("taskgui: a task's hypothesis refs link into the tree",
          "function taskDetail" in ui
          and 'data-go' in ui.split("function taskDetail")[1].split("\nfunction ")[0])
    # (l) the list says what it is showing — 25 silently standing in for 200 was the
    #     single worst finding of the walk
    check("taskgui: the list counts what it shows against what exists",
          "tk-count" in ui)
    # (m) the read-only footer stopped claiming everything is a tree
    check("taskgui: the read-only footer speaks for the whole vault",
          "edit the vault" in html and "edit the tree" not in html)
    # ---- hierarchy in the taskhub (PI ruling 2026-08-21: nested tree in All/Category,
    # Frontier and Timeline stay flat — they answer different questions).
    # (n) All and Category render a real tree; the two flat views never call it
    tkr = ui.split("function renderTasks()")[1].split("\nfunction ")[0]
    check("hiergui: All and Category views nest subtasks under their parent",
          "function taskTreeRows" in ui and "taskTreeRows(" in tkr
          and "taskTreeRows" not in
              tkr.split('view === "frontier"')[1].split('view === "timeline"')[0])
    # (o) depth is drawn, not implied — each nested row indents by its depth
    check("hiergui: nested rows indent by depth",
          "--tk-depth" in ui and "--tk-depth" in css)
    # (p) a parent says it is a container: n/m subtask progress in the row AND the detail
    check("hiergui: parent rows and the detail carry subtask progress",
          "tk-prog" in ui.split("function taskRow")[1].split("\nfunction ")[0]
          and "tk-prog" in ui.split("function taskDetail")[1].split("\nfunction ")[0]
          and ".tk-prog" in css)
    # (q) the hierarchy climbs as well as descends: the detail links the parent
    check("hiergui: the task detail links its parent",
          '"Part of"' in ui.split("function taskDetail")[1].split("\nfunction ")[0])
    # (r) a status filter never orphans a match — non-matching ancestors stay as dimmed
    #     context rows, and only matches are counted
    check("hiergui: filtered-out ancestors render as context, not holes",
          "tk-ctx" in ui and ".tk-ctx" in css)
    missing = [c for c in tb["categories"] + [tb["reserved_category"]]
               if f"--t-{c}" not in css]
    check("ui: every declared category has a colour", not missing)
    check("ui: both themes carry the category palette",
          css.count("--t-" + tb["reserved_category"]) >= 2)

    # ---- INTERSECTION WITH 15.6's GUARD. 15.6 added a parity check that derives its
    # expectation from snapshot()'s live surface, so the taskhub's node-facing fields must
    # REGISTER with it rather than be excused from it. Two distinct hazards:
    #   - `experiments` shipped dark and the guard caught it (it did, on the first run after
    #     the rebase — that is the guard working exactly as designed);
    #   - `tasks` would have FALSELY PASSED, because the guard's `referenced()` is a
    #     substring test and app.js already contained the unrelated `state.snap.tasks`.
    # So this asserts the specific render path, not the substring.
    check("ui: the node-facing task fields are rendered, not merely mentioned",
          "function tasksSection" in ui and "function experimentsSection" in ui
          and "n.tasks" in ui and "n.experiments" in ui
          and "tasksSection(n)" in ui and "experimentsSection(n)" in ui)
    check("ui: the taskhub did not grow 15.6's deliberately-unrendered allowlist",
          "NOT_RENDERED" in read(os.path.join(HERE, "selftest.py"))
          and "tasks" not in re.search(r"NOT_RENDERED = \{(.*?)\}",
                                       read(os.path.join(HERE, "selftest.py")), re.S).group(1)
          and "experiments" not in re.search(r"NOT_RENDERED = \{(.*?)\}",
                                             read(os.path.join(HERE, "selftest.py")), re.S).group(1))
    check("ui: a conclusion is narrated as concluded, never as a verdict",
          "concluded" in ui and "comes from its findings" in ui and "verdict" not in
          ui.split("function experimentsSection")[1].split("\nfunction ")[0])
    check("ui: no acceptance badge in the task row, the task pane or the experiments list",
          not any(w in ui.split("function taskRow")[1].split("\nfunction ")[0]
                  + ui.split("function taskDetail")[1].split("\nfunction ")[0]
                  + ui.split("function experimentsSection")[1].split("\nfunction ")[0]
                  for w in ("accept", "pending", "awaiting")))

    # ---- INTERSECTION: 15.6 narrates drift/rule/kind on the node; 08.4 adds backlinks to
    # the same pane. ONE node carrying both is the exact overlap, so it gets its own fixture.
    both = tempfile.mkdtemp(prefix="crux_taskui_both_")
    E.cmd_init("Both", both, goal="g")
    bq, _ = E.cmd_ask(both, "does narration coexist with backlinks?")
    bh, _, _ = E.cmd_hypothesize(both, "it does", parent=bq, rule="all",
                                 verifiables=["alpha"], neutral=["the control"],
                                 expect="alpha holds")
    declare_null(both, bh)
    E.cmd_test(both, bh, to="running")
    edit(node_path(both, bh), "- [ ] alpha", "- [x] a check nobody registered")   # -> DRIFT
    be, _ = E.cmd_task_add(both, "The run", category="implementation", blocked_by=None,
                           hypothesis_refs=[(bh, "invalid-run")])
    E.cmd_task_done(both, be, outputs=[f"[[{bq}]]"])
    bn = E.snapshot(both)["nodes"][bh]
    check("ui: 15.6's narration and 08.4's backlinks coexist on one node",
          bn["drift"] is True and bn["rule"] == "all"
          and [x["task"] for x in bn["experiments"]] == [be]
          and any(v["kind"] == "outcome-neutral" for v in bn["verifiables"]))
    # ---- spec 19: the queue that once narrated drift a second time is gone; drift is
    # narrated once, on the node, and the task block carries no queue to hold it
    check("ui: drift lives on the node now that the acceptance queue is gone",
          "queue" not in E.snapshot(both)["tasks"] and E.lock_drift(E.Vault(both).get(bh)))
    shutil.rmtree(both, ignore_errors=True)

    # -- a vault with no tasks/ : present, inert, and the tab hides itself
    plain = tempfile.mkdtemp(prefix="crux_taskui_none_")
    E.cmd_init("No Tasks", plain, goal="g")
    ptb = E.snapshot(plain)["tasks"]
    check("taskmig: snapshot on a pre-08 vault has an inactive tasks block",
          ptb["active"] is False and ptb["items"] == [] and ptb["frontier"] == []
          and set(ptb) == set(tb))
    shutil.rmtree(plain, ignore_errors=True)

    fx = tempfile.mkdtemp(prefix="crux_taskui_fx_")
    dst = os.path.join(fx, "demo")
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    b = _dir_bytes(dst)
    s2 = E.snapshot(dst)
    check("taskmig: snapshotting a pre-08 vault writes nothing and adds no problems",
          _dir_bytes(dst) == b and s2["tasks"]["active"] is False
          and not any(n.get("tasks") for n in s2["nodes"].values()))
    shutil.rmtree(fx, ignore_errors=True)
    shutil.rmtree(root, ignore_errors=True)


def run_taskhub_skill():
    """Spec 08 PRD 08.5, re-pointed by spec 19: the tree holds knowledge, the taskhub holds
    work, and a task's output reaches the tree only as evidence on a finding. The always-on
    core states the boundary; `references/taskhub.md` carries the procedure. The experiment
    accept gate is gone, so no skill may teach `task accept` or `task review` except as
    removed."""
    print("\n# taskhub — the boundary in the core, the procedure behind a pointer (spec 08, 19)")
    skill = read(os.path.join(HERE, "..", "SKILL.md"))
    tref_p = os.path.join(HERE, "..", "references", "taskhub.md")
    tref = read(tref_p) if os.path.isfile(tref_p) else ""
    spec8 = read(os.path.join(HERE, "..", "..", "..", ".spec", "08-taskhub.md"))
    spec15 = read(os.path.join(HERE, "..", "..", "..", ".spec", "15-evidence-semantics.md"))
    spec7 = os.path.join(HERE, "..", "..", "..", ".spec", "07-rd-layer.md")

    check("skill: the core points at references/taskhub.md, and it exists",
          "references/taskhub.md" in skill and bool(tref))
    check("skill: the core says a task's output enters the tree only as evidence on a finding",
          "only as evidence on a finding" in skill)
    check("skill: the taskhub reference states what gets in and what stays scratch",
          "would you be annoyed if this vanished next week" in tref.lower()
          and "session scratch" in tref and "one context window" in tref)
    check("skill: a task that would open a question becomes a tree node",
          "stops being a task" in tref)
    check("skill: the accept gate is taught nowhere — no skill text says task accept/review "
          "except as removed",
          all("removed" in l for l in (skill + "\n" + tref).splitlines()
              if re.search(r"task (accept|review)\b", l)))

    # every live task sub-verb the CLI exposes is documented, derived from argparse rather
    # than hand-listed, so a verb added later cannot go undocumented silently
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    live = re.findall(r"^    ([a-z]+)\b", r.stdout, re.M)
    check(f"skill: the CLI's task verbs are the 4.0 set ({live})",
          r.returncode == 0 and {"add", "done", "drop", "list", "show", "categories"} <= set(live)
          and not {"review", "accept"} & set(live))
    undoc = [v for v in live if f"`task {v}`" not in tref]
    check(f"skill: every live task verb is documented in references/taskhub.md ({undoc})",
          live and not undoc)
    for v in ("review", "accept"):
        rr = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", v],
                            capture_output=True, text=True, encoding="utf-8")
        check(f"skill: `crux task {v}` prints a spec-19 pointer, not a traceback",
              rr.returncode == 0 and f"`task {v}` is removed (spec 19)" in rr.stdout
              and "Traceback" not in rr.stderr)

    # -- the .spec amendments (rulings D6 / D9 / D19) are history and stay as they were
    check("skill: .spec/08's conclusion vocabulary matches VERDICTS",
          all(c in spec8 for c in E.CONCLUSIONS)
          and "`supports` / `disputes`" not in spec8
          and "dispute h45" not in spec8)
    check("skill: .spec/08's frontier criterion matches the shipped rule",
          "blockers are all **cleared**" in spec8 and "blockers are all `done`" not in spec8)
    check("skill: .spec/08 records the written-vs-derived link split",
          "Node-tree lineage is written in node files; the task graph is derived" in spec8
          and "07-rd-layer.md" in spec8 and "cardinality and churn" in spec8)
    check("skill: .spec/15 scopes derived-never-chosen to the node verdict",
          "derived, never chosen — **as a hypothesis's `verdict`**" in spec15)
    check("skill: .spec/08's work items are ticked for what shipped",
          spec8.count("- ☑ ") >= 10 and "**Status:** ◐" in spec8)

    # -- 07 is NOT amended: the ruling changed 08's record, not 07's design
    r = subprocess.run(["git", "diff", "--stat", "HEAD", "--", spec7],
                       capture_output=True, text=True, encoding="utf-8",
                       cwd=os.path.join(HERE, "..", "..", ".."))
    check("skill: .spec/07 is byte-identical", r.returncode == 0 and r.stdout.strip() == "")


def run_brief():
    """Spec 09 PRD 09.0 — `crux brief <node> --json`, the deterministic bias-proof payload.

    crux pre-registers verifiables. Pre-registration defends against changing the bar AFTER
    seeing results — it says nothing about WHO sets it. An agent that has spent an hour
    helping the PI argue for a hypothesis will pick a bar that hypothesis clears.

    Zero context does not fix that on its own, because the PARENT writes the prompt.
    "Verify that JEPA improves imputation" has already told the fresh agent which way to
    lean. So the payload is assembled by the engine from vault state, and the calling agent
    never authors a sentence of it."""
    print("\n# specialized agents — the deterministic brief (spec 09, PRD 09.0)")
    root = tempfile.mkdtemp(prefix="crux_brief_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Brief", root, goal="the program goal")
    q1, _ = E.cmd_ask(root, "the parent question")
    SENTINEL = "ADVOCACY-LIVES-HERE-AND-MUST-NOT-LEAK"
    h1, _, _ = E.cmd_hypothesize(root, "the claim under test", parent=q1, rule="all",
                                 problem=SENTINEL, verifiables=["alpha check", "beta check"],
                                 neutral=["the control"], expect="alpha and beta both clear")
    # a sibling WITH A FINDING: its findings ARE the shared factual record a skeptical
    # colleague reads
    h2, _, _ = E.cmd_hypothesize(root, "an earlier sibling", parent=q1, rule="all",
                                 verifiables=["gamma"], neutral=["the control"],
                                 expect="gamma clears")
    edit(node_path(root, h2), "- [ ] gamma", "- [x] gamma   (found: 0.71)")
    edit(node_path(root, h2), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    write(os.path.join(root, "results", h2, "report.md"), "# r\n\nsynthetic.\n")
    E.cmd_finding(root, h2, "strong", why="the earlier run settled the preprocessing question",
                  direction="supports", evidence=[f"results/{h2}/report.md"])
    # the anchor's OWN results: present in the vault, and they must not reach its own brief
    edit(node_path(root, h1), "- [ ] alpha check", "- [x] alpha check   (found: 0.99-ANCHORS-OWN)")
    os.makedirs(os.path.join(root, "results", h1), exist_ok=True)
    with open(os.path.join(root, "results", h1, "metrics.json"), "w", encoding="utf-8") as f:
        f.write('{"auroc": {"value": 0.815, "ci": [0.79, 0.84]}}')
    E.cmd_finding(root, h1, "weak", why="ANCHORS-OWN-FINDING leaked into its own brief",
                  direction="supports")

    b = E.brief(root, h1)
    blob = json.dumps(b, sort_keys=True)

    # ---- the three exclusions
    check("brief: the advocacy channel never reaches the brief", SENTINEL not in blob)
    check("brief: a hypothesis' own findings never reach its brief",
          "ANCHORS-OWN" not in blob
          and all(x.get("found") in (None, "") for x in b["verifiables"]))
    check("brief: metrics are advertised by address, never by value",
          b["metrics_available"] == ["auroc"] and "0.815" not in blob and "0.79" not in blob)

    # ---- the shared factual record IS present
    check("brief: the claim and the question are present",
          b["claim"] == "the claim under test" and b["question"] == "the parent question")
    check("brief: ancestry is ids and titles, root -> parent",
          [a["id"] for a in b["ancestry"]] == ["root", q1])
    check("brief: a sibling's Findings are the shared record, with direction, confidence, "
          "why and evidence",
          [(p["id"], p["state"], p["confidence"],
            [(f["direction"], f["confidence"], f["why"], f["evidence"]) for f in p["findings"]])
           for p in b["prior_findings"]]
          == [(h2, "settled", "strong",
               [("supports", "strong", "the earlier run settled the preprocessing question",
                 [f"results/{h2}/report.md"])])])
    check("brief: a hypothesis' own Finding never reaches its brief",
          "ANCHORS-OWN-FINDING" not in blob)
    check("brief: the payload carries no verdict or synthesis key",
          '"verdict":' not in blob and '"synthesis":' not in blob)
    check("brief: the anchor is never its own prior finding",
          all(p["id"] != h1 for p in b["prior_findings"]))
    check("brief: the pre-registered checks are present, with kinds and no results",
          [x["kind"] for x in b["verifiables"]] == ["hypothesis", "hypothesis", "outcome-neutral"])
    check("brief: the combination rule travels with the checks",
          b["rule"] == "all" and b["rule_m"] is None)
    check("brief: the payload names the evidence-semantics boundary",
          b["schema"] == E.SCHEMA_GENERATION)

    # ---- determinism, which is what makes isolation testable at all
    # D3: the brief and the deck share their ancestry/wiki walks. Assert the SHARING, so a
    # future edit that re-forks them fails here rather than drifting silently apart.
    check("brief: the ancestry walk is the shared one, not a second copy",
          [a["id"] for a in b["ancestry"]]
          == [m.id for m in E.ancestor_chain(E.Vault(root), E.Vault(root).get(h1))])
    check("brief: the wiki walk is the shared one",
          b["wiki"] == E.wiki_refs(root, [E.Vault(root).get(h1)["body"]]
                                   + [m["body"] for m in
                                      E.ancestor_chain(E.Vault(root), E.Vault(root).get(h1))]))
    check("brief: sharing the walks did not widen the exclusions",
          SENTINEL not in json.dumps(b) and "ANCHORS-OWN" not in json.dumps(b))

    check("brief: the payload is byte-identical across runs",
          json.dumps(E.brief(root, h1), sort_keys=True) == blob)
    other = tempfile.mkdtemp(prefix="crux_brief2_")
    shutil.rmtree(other); shutil.copytree(root, other)
    check("brief: the payload is a pure function of vault state, not of its path",
          json.dumps(E.brief(other, h1), sort_keys=True) == blob)
    shutil.rmtree(other, ignore_errors=True)

    # ---- the CLI
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief", h1, "--json"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("brief: --json emits JSON and nothing else",
          r.returncode == 0 and json.loads(r.stdout) == b)
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief", h1],
                        capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("brief: a bare brief prints a human summary and never mixes the two",
          r2.returncode == 0 and "the claim under test" in r2.stdout
          and not r2.stdout.lstrip().startswith("{"))
    expect_error("brief: a question anchor is refused (the brief is per-hypothesis)",
                 lambda: E.brief(root, q1))

    # the human summary names the Finding that SET the sibling's state (the strongest), not
    # the newest: a later weak no-answer-yet Finding must not displace a strong one's why
    h3, _, _ = E.cmd_hypothesize(root, "a later sibling", parent=q1, expect="it holds")
    E.cmd_finding(root, h3, "strong", why="STRONG-WHY the decisive run", direction="supports")
    E.cmd_finding(root, h3, "weak", why="NEWER-WEAK-WHY an aborted rerun",
                  direction="no-answer-yet")
    r3 = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief", h1],
                        capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    line = [l for l in r3.stdout.splitlines() if l.strip().startswith("prior:") and h3 in l]
    check("brief: the summary prints the why of the strongest Finding, not the newest",
          r3.returncode == 0 and len(line) == 1 and "STRONG-WHY" in line[0]
          and "NEWER-WEAK-WHY" not in line[0] and "settled · strong" in line[0])

    check("brief: ENGINE_VERSION at or past 2.4", at_least_version("2.4"))
    shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary holds
    old, oq, oh = pre15_vault("crux_bmig09_")
    ob = E.brief(old, oh)
    check("evmig: brief works on a pre-15 node",
          ob["schema"] == 0 and ob["rule"] is None
          and [x["kind"] for x in ob["verifiables"]] == ["hypothesis", "hypothesis"])
    check("evmig: a pre-15 brief still excludes the advocacy channel",
          "problem" not in ob)
    shutil.rmtree(old, ignore_errors=True)


def run_null():
    """Spec 09 PRD 09.1 — `## Null`, the null hypothesis. Spec 19 keeps the null as an
    OPTIONAL section and drops its approval gate: a finding records whether the null was
    ruled out, and a null not ruled out caps the finding's confidence at weak."""
    print("\n# the null — optional, ungated, and capping confidence (spec 09 → spec 19)")
    root = tempfile.mkdtemp(prefix="crux_null_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Nulls", root)
    q1, _ = E.cmd_ask(root, "does the null still matter?")

    def mk(title, **kw):
        kw.setdefault("verifiables", ["alpha"]); kw.setdefault("expect", "alpha holds")
        hid, _, _ = E.cmd_hypothesize(root, title, parent=q1, **kw)
        return hid

    h1 = mk("with a good null", null="capacity — the extra parameters alone explain it")
    n1 = E.Vault(root).get(h1)
    check("null: the template carries a Null section", "## Null" in n1["body"])
    check("null: --null writes the section",
          "capacity — the extra parameters alone explain it" in n1["body"])
    check("null: the null reaches the brief",
          E.brief(root, h1)["null"] == "capacity — the extra parameters alone explain it")
    check("null: snapshot exposes the null",
          E.snapshot(root)["nodes"][h1]["null"].startswith("capacity"))
    # 09.1 criterion 9's third surface: the deck. A slide reporting a verdict without the
    # bar it was measured against is a number with no scale.
    dp = E.deck_payload(root, h1)
    check("null: the null reaches the deck payload",
          dp["anchor"]["null"].startswith("capacity"))

    check("null: every confound family is accepted",
          all(E.null_problem(f"{fam} — the instance", 1) is None for fam in E.CONFOUND_FAMILIES))
    check("null: a null naming no family is refused, and the message lists them",
          "capacity" in (E.null_problem("the numbers were just nicer", 1) or ""))
    check("null: a null over 25 words is refused",
          "25" in (E.null_problem("chance — " + " ".join(["word"] * 30), 1) or ""))
    check("null: a 25-word null is accepted (the cap is inclusive)",
          E.null_problem("chance — " + " ".join(["w"] * 23), 1) is None)
    expect_error("null: a malformed null is still refused when it is written",
                 lambda: mk("bad family", null="the numbers came out nicer"))

    h2 = mk("no null")
    check("null: running is NOT refused with no null (spec 19)",
          E.cmd_test(root, h2, to="running") == "running")
    check("null: running is NOT refused with an unapproved null (no approval exists)",
          E.cmd_test(root, h1, to="running") == "running")
    check("null: no approval verb remains", not hasattr(E, "cmd_approve_null"))
    check("null: a vault with an unapproved null validates clean", E.cmd_validate(root) == [])
    E.cmd_finding(root, h1, "strong", why="clean win, but the width-matched arm was not run",
                  direction="supports", null="not-ruled-out")
    check("null: a finding whose null was not ruled out lands at weak",
          E.derive_state(E.Vault(root), h1)["confidence"] == "weak")

    check("null: ENGINE_VERSION at or past 2.5", at_least_version("2.5"))
    shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary holds
    old, oq, oh = pre15_vault("crux_nmig_")
    check("evmig: a pre-15 hypothesis needs no null",
          E.cmd_test(old, oh, to="running") == "running" and E.cmd_validate(old) == []
          and E.validation_report(old)["warnings"] == [])
    check("evmig: a pre-15 brief carries a null of None", E.brief(old, oh)["null"] is None)
    shutil.rmtree(old, ignore_errors=True)


def run_failure_scenarios():
    """Spec 09 PRD 09.2 — a failure scenario per verifiable, and the two-part filter.

    Spec 09 replaces a numeric cap on verifiables with a logical one: two verifiables are
    redundant if they FAIL FOR THE SAME REASON. Applied greedily, the agent stops when it
    runs out of worlds. The engine cannot judge that — what it can do is force the residue
    to be written down, so redundancy is visible to the PI and to crux-critic.

    D1 (ruled): the scenario is part of the pre-registered commitment, and
    SCHEMA_GENERATION goes to 2 so nodes already stamped generation 1 keep the material they
    were locked with, forever."""
    print("\n# specialized agents — failure scenarios (spec 09, PRD 09.2)")

    # ---- the syntax leaves every spec-15 reader byte-clean. Captured BEFORE, compared AFTER.
    plain = ("## Verifiables\n\n"
             "- [x] [outcome-neutral] the control reproduces 0.46 (found: 0.461)\n"
             "- [ ] imp-Spearman >= +0.01\n")
    withfs = ("## Verifiables\n\n"
              "- [x] [outcome-neutral] the control reproduces 0.46 (found: 0.461)\n"
              "      fails-if:: the shared preprocessing path changed under us\n"
              "- [ ] imp-Spearman >= +0.01\n"
              "      fails-if:: the gain is capacity alone — the width-matched arm also clears it\n"
              "      discriminates:: true\n")
    check("fails: the continuation line is invisible to the flat tally",
          E.count_verifiables(withfs) == E.count_verifiables(plain))
    check("fails: the continuation line is invisible to the kind split",
          E.count_verifiables_by_kind(withfs) == E.count_verifiables_by_kind(plain))
    check("fails: the continuation line does not disturb text/state/kind",
          E._verifiables(withfs) == E._verifiables(plain))
    # the deck now CARRIES the scenarios (09.2 criterion 7), so the invariance claim is
    # about the spec-15 fields it must not disturb — text, state, kind, found
    _s15 = lambda vs: [{k: x[k] for k in ("text", "state", "kind", "found")} for x in vs]
    check("fails: the continuation line does not disturb the deck payload's spec-15 fields",
          _s15(E._deck_verifiables(withfs)) == _s15(E._deck_verifiables(plain)))
    check("fails: and the deck payload does carry the scenarios themselves",
          [x["fails_if"] for x in E._deck_verifiables(withfs)][1]
          == "the gain is capacity alone — the width-matched arm also clears it"
          and [x["discriminates"] for x in E._deck_verifiables(withfs)] == [False, True])
    fs = E.verifiable_scenarios(withfs)
    check("fails: scenarios parse in document order",
          [x["fails_if"] for x in fs] ==
          ["the shared preprocessing path changed under us",
           "the gain is capacity alone — the width-matched arm also clears it"])
    check("fails: discriminates is its own field, not a marker on the scenario (D8)",
          [x["discriminates"] for x in fs] == [False, True]
          and "fails-if!::" not in withfs and "discriminates::" in withfs)
    check("fails: a bare `discriminates::` reads as yes",
          E.verifiable_scenarios("## Verifiables\n\n- [ ] a\n      fails-if:: w\n"
                                 "      discriminates::\n")[0]["discriminates"] is True)
    check("fails: `discriminates:: false` reads as no",
          E.verifiable_scenarios("## Verifiables\n\n- [ ] a\n      fails-if:: w\n"
                                 "      discriminates:: false\n")[0]["discriminates"] is False)

    # ---- writing them, and (spec 19) no gate on them
    root = tempfile.mkdtemp(prefix="crux_fs_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Scenarios", root)
    q1, _ = E.cmd_ask(root, "do scenarios still gate?")
    h1, _, _ = E.cmd_hypothesize(root, "with scenarios", parent=q1, rule="all",
                                 null="capacity — width alone explains the gain",
                                 verifiables=["alpha", "beta"], neutral=["the control"],
                                 fails_if=["the width-matched arm also clears it",
                                           "beta moves for an unrelated reason",
                                           "the preprocessing path changed"],
                                 discriminates=[True, False, False], expect="alpha and beta hold")
    n1 = E.Vault(root).get(h1)
    check("fails: --fails-if writes continuation lines under each check",
          n1["body"].count("fails-if::") == 3 and n1["body"].count("discriminates:: true") == 1
          and "fails-if!::" not in n1["body"])
    check("fails: scenarios reach the snapshot",
          [x["fails_if"] for x in E.snapshot(root)["nodes"][h1]["verifiables"]][0]
          == "the width-matched arm also clears it")
    check("fails: scenarios reach the brief",
          E.brief(root, h1)["verifiables"][0]["fails_if"]
          == "the width-matched arm also clears it")
    check("fails: a complete hypothesis runs", E.cmd_test(root, h1, to="running") == "running")
    h2, _, _ = E.cmd_hypothesize(root, "no scenarios", parent=q1, expect="alpha holds",
                                 verifiables=["alpha", "beta"], neutral=["ctl"])
    check("fails: running is NOT refused with missing scenarios (spec 19)",
          E.cmd_test(root, h2, to="running") == "running")
    h3, _, _ = E.cmd_hypothesize(root, "identical scenarios", parent=q1, expect="alpha holds",
                                 verifiables=["alpha", "beta"], neutral=["ctl"],
                                 fails_if=["the same world", "the same world", "ctl broke"])
    check("fails: neither missing nor identical scenarios are a validate problem any more",
          not any(i in (h2, h3) for i, _ in E.cmd_validate(root)))

    # ---- the CLI is additive: a bare -v still works (never a second -v argument)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize", "cli built",
                        "-p", q1, "-v", "alpha", "--fails-if", "world a", "--discriminates",
                        "-n", "ctl", "--fails-if", "ctl broke",
                        "--null", "chance — noise", "--rule", "all", "--expect", "alpha holds"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    hc = [x for x in E.Vault(root).nodes if x.startswith("h")][-1]
    body = E.Vault(root).get(hc)["body"]
    check("fails: --fails-if pairs with the preceding verifiable",
          r.returncode == 0 and "fails-if:: world a" in body
          and "discriminates:: true" in body and "fails-if:: ctl broke" in body)
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize", "bare v",
                         "-p", q1, "-v", "alpha", "-n", "ctl", "--expect", "alpha holds"],
                        capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("fails: a bare -v is still accepted (no second positional argument)",
          r2.returncode == 0)

    check("fails: ENGINE_VERSION at or past 2.6", at_least_version("2.6"))
    check("fails: SCHEMA_GENERATION is at least 2", E.SCHEMA_GENERATION >= 2)
    shutil.rmtree(root, ignore_errors=True)

    # ---- D1: the scenario IS the commitment, and generation 1 keeps its old material
    root = tempfile.mkdtemp(prefix="crux_fsl_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Locks2", root)
    q1, _ = E.cmd_ask(root, "q")
    hg2, _, _ = E.cmd_hypothesize(root, "gen two", parent=q1, rule="all",
                                  null="chance — noise", verifiables=["alpha"], neutral=["ctl"],
                                  fails_if=["world a", "ctl broke"], discriminates=[True, False],
                                  expect="alpha holds")
    E.cmd_test(root, hg2, to="running")
    n = E.Vault(root).get(hg2)
    check("fails: a generation-2+ node locks scenario material",
          E.node_schema(n) >= 2 and "world a" in E.lock_material(n))
    g3 = E.lock_material(n)
    check("fails: generation 3 hashes exactly like generation 2 (the 4.0 bump drifts nothing)",
          E.lock_material(E.Node(dict(n, fm=dict(n["fm"], schema=2)))) == g3)
    edit(node_path(root, hg2), "fails-if:: world a", "fails-if:: a completely different world")
    check("fails: a failure scenario added or changed after running is drift",
          E.lock_drift(E.Vault(root).get(hg2)))

    # a node stamped generation 1 keeps the material it was locked with — the whole of D1
    hg1, _, _ = E.cmd_hypothesize(root, "gen one", parent=q1, rule="all",
                                  null="chance — noise", verifiables=["alpha"], neutral=["ctl"],
                                  fails_if=["world a", "ctl broke"], discriminates=[True, False],
                                  expect="alpha holds")
    g1 = E.Vault(root).get(hg1)
    g1["fm"]["schema"] = 1
    E.write_if_changed(g1["path"], E.render_doc(g1["fm"], g1["body"]))
    g1 = E.Vault(root).get(hg1)
    check("fails: a generation-1 node's material EXCLUDES scenarios",
          "world a" not in E.lock_material(g1))
    check("fails: generation 1 and generation 2 hash differently on the same body",
          E.lock_hash(g1) != E.lock_hash(E.Vault(root).get(hg2)))
    shutil.rmtree(root, ignore_errors=True)

    # ---- THE MIGRATION PROOF: a node locked under generation 1 must not drift now
    old = tempfile.mkdtemp(prefix="crux_fsmig_")
    shutil.rmtree(old); os.makedirs(old)
    E.cmd_init("Gen1", old)
    oq, _ = E.cmd_ask(old, "q")
    oh, _, _ = E.cmd_hypothesize(old, "locked under gen 1", parent=oq, rule="all",
                                 null="chance — noise", verifiables=["alpha"], neutral=["ctl"],
                                 fails_if=["world a", "ctl broke"], discriminates=[True, False],
                                 expect="alpha holds")
    # rewind it to generation 1 and lock it with generation-1 material, as 2.5 would have
    g = E.Vault(old).get(oh)
    g["fm"]["schema"] = 1
    g["fm"]["lock"] = E.lock_hash(E.Node(dict(g, fm=dict(g["fm"], schema=1))))
    g["fm"]["locked"] = E.now(); g["fm"]["lock_at"] = "running"; g["fm"]["status"] = "running"
    E.write_if_changed(g["path"], E.render_doc(g["fm"], g["body"]))
    check("evmig: a node locked under generation 1 does NOT drift after the bump",
          not E.lock_drift(E.Vault(old).get(oh)))
    check("evmig: and its vault validates clean", E.cmd_validate(old) == [])
    shutil.rmtree(old, ignore_errors=True)

    old, oq, oh = pre15_vault("crux_fsp15_")
    check("evmig: a pre-15 hypothesis needs no failure scenarios",
          E.cmd_test(old, oh, to="running") == "running" and E.cmd_validate(old) == [])
    shutil.rmtree(old, ignore_errors=True)


def run_migrate():
    """Spec 09 PRD 09.3 — `crux migrate`, with evidence fields structurally unmigratable.

    Spec 09 dissolves version bridging into "a mechanical schema rewrite -> a `crux migrate`
    verb". Spec 15 then ruled the opposite for its OWN fields: no migrate path, because
    bringing an old hypothesis up to evidence semantics means re-declaring what would settle
    a claim — a scientific act, PI-gated, one node at a time.

    Both are right about different fields, and the split is measurable. `schema` is the sharp
    one: writing it does not add a field, it FLIPS A NODE ACROSS THE VERSION BOUNDARY, and
    every spec-15 rule instantly binds work settled before those rules existed."""
    print("\n# specialized agents — crux migrate (spec 09, PRD 09.3)")
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    root = tempfile.mkdtemp(prefix="crux_mig_")
    shutil.rmtree(root); shutil.copytree(src, root)

    before_files, before_verdicts, before_status = fingerprint(root)
    before_gen = generated_verdicts(root)

    plan = E.cmd_migrate(root, apply=False)
    check("migrate: the default is a dry run",
          plan["applied"] is False and fingerprint(root)[0] == before_files)
    check("migrate: the plan names the sections it would add",
          any("Null" in c["adds"] for c in plan["changes"])
          and any("ELI5" in c["adds"] for c in plan["changes"]))

    res = E.cmd_migrate(root, apply=True)
    check("migrate: apply adds the placeholder sections", res["applied"] and res["changes"])
    v = E.Vault(root)
    check("migrate: a pre-15 idea gains the empty structural sections",
          all(s in v.get("h1")["body"] for s in ("## ELI5", "## TL;DR", "## Null", "## Artifacts")))
    check("migrate: a pre-15 question gains its own",
          all(s in v.get("q1")["body"] for s in ("## ELI5", "## TL;DR", "## Protocol")))

    # ---- THE LINE. These are what spec 15 ruled unmigratable, and the verb cannot write them.
    check("evmig: migrate never stamps a node across the boundary",
          all(E.node_schema(n) == 0 for n in v.nodes.values() if n.type in ("question", "idea")))
    check("evmig: migrate writes no evidence field",
          all(f not in n["fm"] for n in v.nodes.values() if n.type in ("question", "idea")
              for f in E.MIGRATE_FORBIDDEN))
    check("evmig: the Null it adds is EMPTY — naming the null hypothesis is a scientific act",
          E._null_text(v.get("h1")) is None)
    check("evmig: migrate changes no recorded verdict",
          fingerprint(root)[1] == before_verdicts and fingerprint(root)[2] == before_status)
    check("evmig: and no verdict is re-labelled in anything generated",
          generated_verdicts(root) == before_gen)
    check("migrate: the vault still validates clean, still pre-15",
          E.cmd_validate(root) == []
          and any(i["id"] == "boundary:evidence-semantics"
                  for i in E.validation_report(root)["info"]))

    # ---- authored prose is untouched: only whole new sections appear
    after_files = fingerprint(root)[0]
    changed = [k for k in before_files if before_files[k] != after_files.get(k)]
    check("migrate: only node files changed, and only by gaining sections",
          all(k.endswith(".md") for k in changed))
    for nid in ("h1", "q1"):
        old_body = E.parse_doc(read(os.path.join(src, os.path.basename(v.get(nid)["path"]))))[1]
        new_body = v.get(nid)["body"]
        authored = [l for l in old_body.splitlines() if l.strip()]
        check(f"migrate: every authored line of {nid} survives verbatim",
              all(l in new_body for l in authored))

    check("migrate: apply is idempotent", E.cmd_migrate(root, apply=True)["changes"] == [])

    # ---- staleness is SURFACED, never repaired
    info = E.validation_report(root)["info"]
    check("migrate: staleness is surfaced as info, never repaired",
          all(i["id"].split(":")[0] in E.INFO_NAMESPACES for i in info))
    check("migrate: info never affects ok", E.validation_report(root)["ok"] is True)

    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "migrate", "--json"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("migrate: the CLI dry run emits parseable JSON and exits 0",
          r.returncode == 0 and json.loads(r.stdout)["applied"] is False)
    check("migrate: ENGINE_VERSION at or past 2.7", at_least_version("2.7"))
    shutil.rmtree(root, ignore_errors=True)

    # ---- spec 19 removed the review gate, and with it `--check=gate` and its backlog
    #      warning. What remains to pin: `crux migrate` never touches a Finding.
    root = tempfile.mkdtemp(prefix="crux_gate_")
    shutil.rmtree(root); shutil.copytree(src, root)
    fnd = {n.id: read(n["path"]) for n in E.Vault(root).nodes.values() if n.type == "finding"}
    E.cmd_migrate(root, apply=True)
    check("migrate: the structural migration never touches a Finding",
          fnd and fnd == {n.id: read(n["path"]) for n in E.Vault(root).nodes.values()
                          if n.type == "finding"})
    check("migrate: --check=gate is gone with the review gate",
          "gate" not in E.CHECKS + E.OPT_CHECKS)
    shutil.rmtree(root, ignore_errors=True)


# `crux doctor` warnings that are facts about the MACHINE the suite runs on, not about the
# repository: `cmd_doctor` reads `~/.claude/settings.json` for the chat-time voice lint, and
# `~/.claude/skills` for the install, and both warnings are in `origin/main`'s engine, so they
# predate this slice. PRD-1's "no new warning" is about warnings 05.3 could cause, and neither
# of these is one.
#
# `skills` is here because a machine with no `~/.claude/` at all — every CI runner — warns it,
# while a developer machine with crux installed does not. The suite's own
# `doctor: no crux in any skills dir WARNS — a bare clone is a supported install` pins that as
# intended behaviour, so a bare machine warning it is the engine working, not 05.3 regressing.
# Listing only `voice-hook` made this criterion pass here and fail on all nine CI jobs.
AG_DOCTOR_PRE_WARNS = ("voice-hook", "skills")


def run_agent_roster():
    """Spec 09 PRD 09.4's convention, and spec 19's roster: exactly capture, pre-run, situate
    and migrate (decision 9).

    09.4 made an agent definition checkable: the three fields carrying the architecture
    (cold_input, toolbelt, excludes) are frontmatter, so a selftest can read them. Spec 19
    keeps the convention and replaces the roster. capture is new and is the heart of
    background memory; pre-run merges design, null and verifiables; close, critic, audit and
    glossary go; crux-tests moves to evolve-crux, since it builds crux, not research (Q12).

    The definition-derived properties live in `evals.roster_properties`, so that ONE source
    of truth is both printed here and broken on purpose by the mutation harness."""
    print("\n# specialized agents — the roster (spec 09 convention, spec 19 roster)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    adir = os.path.join(repo, "agents")
    import evals as V
    import sweep as SW
    expected = list(V.ROSTER)

    on_disk = sorted(d for d in os.listdir(adir) if os.path.isdir(os.path.join(adir, d)))
    check(f"agents: the roster is exactly capture, prerun, situate and migrate (on disk: {on_disk})",
          on_disk == sorted(expected) == sorted(["crux-capture", "crux-prerun", "crux-situate",
                                                 "crux-migrate"]))
    back = [n for n in V.REMOVED_AGENTS if os.path.exists(os.path.join(adir, n))]
    check(f"agents: the seven agents spec 19 removed are gone (back: {back})",
          not back and len(V.REMOVED_AGENTS) == 7)
    defs = V.load_definitions(expected, repo)
    missing = [n for n in expected if n not in defs]
    check(f"agents: every roster entry has a definition file (missing: {missing})", not missing)

    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    P = V.roster_properties(defs, r.stdout)
    for slug in ([f"{k}:{n}" for n in sorted(defs)
                  for k in ("fields", "dirname", "workflow", "trigger")]
                 + ["belt-verbs", "leash", "writers", "no-version-pin"]):
        check(*P[slug])

    # ---- crux-capture: its toolbelt, its silence, and the brief the sweep hands it
    for slug in ("capture-tools", "capture-belt", "capture-silent", "capture-boundary",
                 "capture-ideation", "capture-closure", "capture-dedup", "capture-park",
                 "capture-voice"):
        check(*P[slug])
    check("agents: the sweep launches crux-capture's brief, with the same tools it declares",
          os.path.abspath(SW.CAPTURE_BRIEF)
          == os.path.abspath(os.path.join(adir, "crux-capture", "AGENT.md"))
          and set(SW.SWEEP_TOOLS.split(",")) == set(V.CAPTURE_TOOLS)
          and "AskUserQuestion" in SW._launch_cmd("claude", "in.txt", "sid"))
    cap_fm = defs.get("crux-capture", ({}, ""))[0]
    check("agents: every crux-capture toolbelt entry is a crux command (Bash runs crux only)",
          all(x.startswith("crux ") for x in V._belt(cap_fm)) and V._belt(cap_fm))

    # ---- crux-prerun: drafts before the run, isolated from the argument for the claim
    for slug in ("prerun-isolated", "prerun-drafts", "prerun-proposal"):
        check(*P[slug])
    root = tempfile.mkdtemp(prefix="crux_probe_")
    try:
        shutil.rmtree(root); os.makedirs(root)
        E.cmd_init("Probe", root)
        q, _ = E.cmd_ask(root, "q")
        h, _, _ = E.cmd_hypothesize(root, "claim", parent=q, problem="ADVOCACY",
                                    verifiables=["a"], expect="it works")
        b = E.brief(root, h)
        check("agents: and the brief really does exclude the argument (cross-checked, not "
              "just declared)", "problem" not in b and "ADVOCACY" not in json.dumps(b))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ---- crux-migrate, re-pointed to the 4.0 seed
    check(*P["migrate-seed"])

    # ---- crux-tests moved to evolve-crux (Q12)
    tests_p = os.path.join(repo, "skills", "evolve-crux", "agents", "crux-tests.md")
    tfm = E.parse_doc(read(tests_p))[0] if os.path.isfile(tests_p) else {}
    check("agents: crux-tests lives with evolve-crux, outside the research roster",
          os.path.isfile(tests_p) and tfm.get("name") == "crux-tests"
          and bool(str(tfm.get("trigger") or "").strip())
          and not os.path.exists(os.path.join(adir, "crux-tests"))
          and "crux-tests" not in expected
          and V.definition_path("crux-tests", repo) == tests_p)

    spec = read(os.path.join(repo, ".spec", "19-background-memory.md"))
    check("agents: spec 19's decision 9 names the shipped roster",
          all(w in spec for w in ("**capture**", "**pre-run**", "**situate**", "**migrate**")))
    # 09.4 asserted doc-only-ness by pinning an engine version literal; the durable property is
    # that the roster is VERSION-INDEPENDENT, which `no-version-pin` above already checks.

    # The directory holds exactly the roster, and `crux doctor` counts it with no new warning.
    ag_links = tempfile.mkdtemp(prefix="crux_ag53_")
    try:
        for n in on_disk:
            os.symlink(os.path.join(adir, n, "AGENT.md"), os.path.join(ag_links, n + ".md"))
        try:
            doc = E.cmd_doctor(root=None, skills_dirs=None, agents_dir=ag_links)
        except Exception:
            doc = {"checks": []}
        check("agents: doctor counts the four roster agents with no new warning",
              _level(doc, "agents") == "ok"
              and _check(doc, "agents")["detail"].startswith("4 crux-*.md in ")
              and [c["name"] for c in doc["checks"] if c["level"] == "warn"
                   and c["name"] not in AG_DOCTOR_PRE_WARNS] == []
              and [c["name"] for c in doc["checks"] if c["level"] == "error"] == [])
    finally:
        shutil.rmtree(ag_links, ignore_errors=True)


def _situate_vault():
    """A vault shaped like a programme someone has been away from: two question levels, a
    closed hypothesis with findings, an unrun one, one in flight, a linked wiki page, an
    inbound citation from outside the subtree, and a taskhub."""
    root = tempfile.mkdtemp(prefix="crux_situate_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Situate", root, goal="Improve the thing.")
    qtop, _ = E.cmd_ask(root, "the top question")
    qmid, _ = E.cmd_ask(root, "the mid question", parent=qtop)
    qout, _ = E.cmd_ask(root, "an unrelated question")
    SENTINEL = "ADVOCACY-LIVES-HERE-AND-SITUATE-MAY-SEE-IT"
    hdone, _, _ = E.cmd_hypothesize(root, "the settled claim", parent=qmid, rule="all",
                                    problem=SENTINEL, verifiables=["alpha check"],
                                    neutral=["the control"], expect="alpha clears")
    hidea, _, _ = E.cmd_hypothesize(root, "the untried claim", parent=qmid, rule="all",
                                    verifiables=["gamma check"], neutral=["the control"],
                                    expect="gamma clears")
    hrun, _, _ = E.cmd_hypothesize(root, "the claim in flight", parent=qmid, rule="all",
                                   verifiables=["delta check"], neutral=["the control"],
                                   expect="delta clears")
    for h in (hdone, hrun):
        declare_null(root, h)
    edit(node_path(root, hdone), "- [ ] alpha check", "- [x] alpha check")
    edit(node_path(root, hdone), "- [ ] [outcome-neutral] the control",
                                 "- [x] [outcome-neutral] the control")
    E.cmd_test(root, hdone, to="running")
    fdone, _, _ = E.cmd_finding(root, hdone, "strong",
                                why="the settled claim held at the declared threshold",
                                direction="supports", null="ruled-out")
    E.cmd_test(root, hrun, to="running")
    # the parent's answer-so-far: "where we are" usually needs it. Spec 19: a question's
    # answer is a Finding on it
    E.cmd_finding(root, qtop, "moderate",
                  answer="So far the direction looks right, on one settled claim.")
    # a wiki page linked from the ANCHOR'S ANCESTOR, so the ancestor walk is what finds it
    E.ensure_wiki(root)
    wiki_page(root, "sit-bg", "Situate background", "why orientation is hard")
    edit(node_path(root, qtop), "the top question\n\n## Protocol",
         "the top question — see [[sit-bg]].\n\n## Protocol")
    # an INBOUND citation: a node outside the subtree that links into it
    mid_base = E.Vault(root).get(qmid).basename
    edit(node_path(root, qout), "an unrelated question\n\n## Protocol",
         f"an unrelated question, which waits on [[{mid_base}]].\n\n## Protocol")
    E.refresh(root)
    return root, dict(qtop=qtop, qmid=qmid, qout=qout, hdone=hdone, hidea=hidea, hrun=hrun,
                      fdone=fdone, sentinel=SENTINEL)


def run_situate():
    """Spec 13 PRD 13.0 — `crux brief --mode=situate`, the orientation payload.

    Spec 09's brief is built around a DELIBERATE EXCLUSION: no problem statement, no subtree,
    no findings, because its consumer is an agent that must not be told which way to lean.
    Situate needs the opposite of every one of those — so the mode is a safety boundary, not
    a convenience, and the default has to fail toward over-isolation.

    The engine assembles; the agent composes. Everything asserted here is vault state or an
    engine-computed count: crux authors no sentence of it."""
    print("\n# situate — the orientation payload (spec 13, PRD 13.0)")
    root, ids = _situate_vault()
    qmid, hdone, hidea, hrun = ids["qmid"], ids["hdone"], ids["hidea"], ids["hrun"]

    s = E.brief(root, qmid, mode="situate")
    blob = json.dumps(s, sort_keys=True)

    # ---- the mode is a boundary, and the default falls the safe way
    check("situate: every payload names its own mode",
          s["mode"] == "situate" and E.brief(root, hdone)["mode"] == "isolated")
    check("situate: the default mode is isolated",
          json.dumps(E.brief(root, hdone), sort_keys=True)
          == json.dumps(E.brief(root, hdone, mode="isolated"), sort_keys=True))
    check("situate: the default mode never carries the advocacy channel",
          ids["sentinel"] not in json.dumps(E.brief(root, hdone), sort_keys=True)
          and ids["sentinel"] not in json.dumps(E.brief(root, hdone, mode="isolated"),
                                                sort_keys=True))
    check("situate: situate mode does carry it — that is the whole point of the split",
          ids["sentinel"] in E.brief(root, hdone, mode="situate")["anchor"]["problem"])
    check("situate: a descendant's problem statement stays out — the payload summarises",
          ids["sentinel"] not in blob)
    expect_error("situate: an unknown mode is refused, never silently widened",
                 lambda: E.brief(root, qmid, mode="situated"))
    expect_error("situate: mode matching is exact, not case-folded",
                 lambda: E.brief(root, qmid, mode="Situate"))

    # ---- the four blocks the spec names
    kids = [c["id"] for c in s["subtree"]]
    check("situate: the subtree reaches the payload nested, in tree order",
          kids == [hdone, hidea, hrun]
          and all("children" in c for c in s["subtree"]))
    check("situate: the ancestry chain carries each answer-so-far",
          [a["id"] for a in s["ancestry"]] == ["root", ids["qtop"]]
          and s["ancestry"][0]["answer_so_far"] == "Improve the thing."
          and "direction looks right" in s["ancestry"][1]["answer_so_far"])
    check("situate: linked wiki pages are indexed from the anchor and its ancestors",
          [w["slug"] for w in s["wiki"]] == ["sit-bg"])
    # D3, extended to the third caller: situate uses the SAME walks as `brief` and
    # `deck_payload` rather than a third copy of the cycle guard. Asserted the way spec 09's
    # audit fix asserts it, so a future edit that re-forks them fails here too.
    vv = E.Vault(root)
    check("situate: the ancestry and wiki walks are the shared ones, not a third copy",
          [a["id"] for a in s["ancestry"]]
          == [m.id for m in E.ancestor_chain(vv, vv.get(qmid))]
          and s["wiki"] == E.wiki_refs(root, [vv.get(qmid)["body"]]
                                       + [m["body"] for m in
                                          E.ancestor_chain(vv, vv.get(qmid))]))
    check("situate: a child's findings[] carry direction, confidence, why and evidence",
          [(f["direction"], f["confidence"], f["why"], f["evidence"])
           for f in s["subtree"][0]["findings"]]
          == [("supports", "strong", "the settled claim held at the declared threshold", [])]
          and s["subtree"][1]["findings"] == [] and s["subtree"][2]["findings"] == [])
    check("situate: each child carries its derived state and confidence",
          [(c["state"], c["confidence"]) for c in s["subtree"]]
          == [("settled", "strong"), ("open", None), ("open", None)])
    check("situate: the anchor question reads its children's Finding, capped at moderate",
          (s["anchor"]["state"], s["anchor"]["confidence"], s["anchor"]["findings"])
          == ("leaning", "moderate", []))
    check("situate: the payload carries no verdict or synthesis key",
          '"verdict":' not in blob and '"synthesis":' not in blob)

    # ---- what is yet to be tested is COMPUTED. This is the row the spec marks "engine".
    ut = s["untested"]
    check("situate: what is yet to be tested is computed, not narrated",
          [x["id"] for x in ut["unrun_ideas"]] == [hidea]
          and {c["hid"] for c in ut["open_checks"]} == {hidea, hrun}
          and ut["open_questions"] == [qmid])
    check("situate: an open check carries its kind, so a control is not read as a claim",
          {c["kind"] for c in ut["open_checks"]} == {"hypothesis", "outcome-neutral"})

    # ---- inbound citations: high value, bounded shape
    check("situate: inbound citations are ids and titles, never prose",
          [x["id"] for x in s["inbound"]] == [ids["qout"]]
          and set(s["inbound"][0]) == {"id", "type", "title"})

    # ---- determinism, which is what keeps the payload assertable at all
    check("situate: the payload is byte-identical across runs",
          json.dumps(E.brief(root, qmid, mode="situate"), sort_keys=True) == blob)
    other = tempfile.mkdtemp(prefix="crux_situate2_")
    shutil.rmtree(other); shutil.copytree(root, other)
    check("situate: the payload is a pure function of vault state",
          json.dumps(E.brief(other, qmid, mode="situate"), sort_keys=True) == blob)
    shutil.rmtree(other, ignore_errors=True)

    # ---- anchors: a hypothesis is legal, no argument means the whole programme
    ph = E.brief(root, hdone, mode="situate")
    check("situate: a hypothesis anchor is legal",
          ph["anchor"]["id"] == hdone and ph["subtree"] == [] and "synthesis" not in ph
          and [f["direction"] for f in ph["anchor"]["findings"]] == ["supports"]
          and ph["anchor"]["state"] == "settled")
    whole = E.brief(root, None, mode="situate")
    check("situate: no argument means the whole programme",
          whole["anchor"]["id"] == "root"
          and [c["id"] for c in whole["subtree"]] == [ids["qtop"], ids["qout"]])
    expect_error("situate: a Finding anchor is refused (a Finding is not a tree node)",
                 lambda: E.brief(root, ids["fdone"], mode="situate"))

    # ---- spec 19: a question is answered by a Finding on it (synthesis is gone)
    E.cmd_finding(root, qmid, "strong", answer="what the mid question settled")
    sa = E.brief(root, qmid, mode="situate")["anchor"]
    check("situate: a question Finding reaches the payload with its answer and no direction",
          [(f["answer"], f["confidence"]) for f in sa["findings"]]
          == [("what the mid question settled", "strong")]
          and all("direction" not in f for f in sa["findings"]))
    check("situate: the question's own Finding settles it",
          (sa["state"], sa["confidence"]) == ("settled", "strong"))

    # ---- the taskhub: post-08, a queued run is the difference between untried and in flight
    check("situate: the work block is present-and-inert without a taskhub",
          E.brief(root, qmid, mode="situate")["work"]
          == {"active": False, "open": [], "experiments": []})
    E.ensure_tasks(root)
    t1 = E.cmd_task_add(root, "queue the untried claim", "implementation", refs=[hidea])[0]
    t2 = E.cmd_task_add(root, "the run against the claim in flight", "implementation",
                        refs=[hrun], hypothesis_refs=[(hrun, "inconclusive")])[0]
    E.cmd_task_add(root, "unrelated chore", "admin")
    w = E.brief(root, qmid, mode="situate")["work"]
    check("situate: a queued run is reported, so untried is not confused with idle",
          w["active"] and [x["id"] for x in w["open"]] == [t1, t2])
    check("situate: an experiment is reported beside the hypothesis it serves",
          [x["id"] for x in w["experiments"]] == [t2]
          and w["experiments"][0]["hypothesis_refs"]
              == [{"id": hrun, "conclusion": "inconclusive"}])
    check("situate: the work block scopes to the subtree, not the whole vault",
          all(x["title"] != "unrelated chore" for x in w["open"]))

    # ---- the CLI
    argv = [sys.executable, os.path.join(HERE, "crux.py"), "brief", qmid,
            "--mode=situate", "--json"]
    r1 = subprocess.run(argv, capture_output=True, cwd=root)
    r2 = subprocess.run(argv, capture_output=True, cwd=root)
    check("situate: the CLI emits the payload and nothing else, byte-identically",
          r1.returncode == 0 and r1.stdout == r2.stdout
          and json.loads(r1.stdout.decode("utf-8"))["mode"] == "situate")
    rn = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief",
                         "--mode=situate", "--json"], capture_output=True, cwd=root)
    check("situate: the CLI takes no node and orients over the whole programme",
          rn.returncode == 0 and json.loads(rn.stdout.decode("utf-8"))["anchor"]["id"] == "root")
    rb = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief", qmid,
                         "--mode=nope", "--json"], capture_output=True, cwd=root)
    check("situate: the CLI refuses an unknown mode — exit 1, silent stdout",
          rb.returncode == 1 and rb.stdout.strip() == b"")
    rh = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "brief", qmid,
                         "--mode=situate"], capture_output=True, cwd=root,
                        encoding="utf-8", errors="replace")
    check("situate: a bare situate prints a human summary and never mixes the two",
          rh.returncode == 0 and "the mid question" in rh.stdout
          and not rh.stdout.lstrip().startswith("{"))

    check("situate: ENGINE_VERSION at or past 2.9", at_least_version("2.9"))

    # ---- READ-ONLY. The whole verb writes nothing, in either mode.
    before = _tree_hashes(root)
    E.brief(root, qmid, mode="situate"); E.brief(root, hdone)
    check("smig: brief writes nothing, in either mode", _tree_hashes(root) == before)
    shutil.rmtree(root, ignore_errors=True)

    # ---- the boundary, and a vault with none of the side layers
    old, oq, oh = pre15_vault("crux_smig13_")
    os_ = E.brief(old, oq, mode="situate")
    check("smig: situate mode works on a pre-15 node",
          os_["subtree"][0]["state"] == "open" and os_["subtree"][0]["findings"] == []
          and os_["subtree"][0]["schema"] == 0 and os_["anchor"]["schema"] == 0)
    check("smig: situate mode works on a vault with no side layers",
          os_["wiki"] == [] and os_["work"] == {"active": False, "open": [], "experiments": []}
          and os_["inbound"] == [])
    shutil.rmtree(old, ignore_errors=True)


def run_situate_agent():
    """Spec 13 PRD 13.1 — the brevity bound, and the `crux-situate` agent.

    Spec 13 states situate's success condition more firmly than anything else in the backlog:
    "brevity is situate's acceptance criterion, not a preference", and "a verbose /situate has
    failed at its only job". A criterion nothing can check is a preference with a stern tone —
    and the spec's own evidence is that instructions will not hold it, since SKILL.md has said
    "keep the science explicit" since v0.5 and the vault it governs held a 5,725-word node.

    So the bound is a LINT the agent runs on its own draft before it speaks: 09's rule 1, the
    deterministic check as the goalpost. Word counting reuses the node cap's own tokenizer, so
    situate's 400 words and a node's 400 words can never become two different numbers."""
    print("\n# situate — the brevity bound and the agent (spec 13, PRD 13.1)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

    def draft(eli5_words=20, paras=3, para_words=40, anchor="q20"):
        head = f"{anchor} — " + " ".join(["word"] * eli5_words)
        body = "\n\n".join(" ".join(["word"] * para_words) for _ in range(paras))
        return head + "\n\n" + body

    good = draft()
    check("situate: a compliant draft passes the lint", E.situate_lint(good, ["q20"]) == [])
    check("situate: the budget is the node prose cap — one number, not two",
          E.SITUATE_BUDGET["total_words"] == E.PROSE_CAP
          and E.SITUATE_BUDGET["tldr_paragraphs"] == 3)

    def ids_of(text, anchors=()):
        return [i for i, _m in E.situate_lint(text, anchors)]

    check("situate: an over-long draft fails the lint",
          ids_of(draft(para_words=200)) == ["situate:too-long"])
    check("situate: too few TL;DR paragraphs fail the lint",
          "situate:tldr-shape" in ids_of(draft(paras=2)))
    check("situate: too many TL;DR paragraphs fail the lint",
          "situate:tldr-shape" in ids_of(draft(paras=4)))
    check("situate: an over-long ELI5 fails the lint",
          "situate:eli5-shape" in ids_of(draft(eli5_words=90)))
    check("situate: an empty draft fails rather than passing vacuously",
          ids_of("   \n  ") == ["situate:empty"])
    check("situate: an unanchored draft fails — a wrong subtree must be visible, not buried",
          ids_of(draft(anchor="q99"), ["q20"]) == ["situate:unanchored"])
    check("situate: with no anchor named, the anchor rule does not fire",
          ids_of(draft(anchor="q99")) == [])
    check("situate: lint findings are namespaced ids, never matched on their message",
          all(i.startswith("situate:") for i in ids_of(draft(paras=9, para_words=90), ["q20"])))
    # the tokenizer is the same one, proven by behaviour rather than by reading the source:
    # a placeholder line is free in a node's budget, so it is free here too
    padded = draft(para_words=95) + "\n\n_(a template placeholder, which is guidance)_"
    check("situate: the lint counts words with the engine's own prose counter",
          len(E._prose_tokens(padded)) == len(E._prose_tokens(draft(para_words=95)))
          and "situate:too-long" not in ids_of(draft(para_words=95)))
    check("situate: the lint is pure — no vault, no filesystem",
          E.situate_lint(good, ["q20"]) == E.situate_lint(good, ["q20"]))

    # ---- the CLI: the agent has to be able to actually run it
    root = tempfile.mkdtemp(prefix="crux_sitlint_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Lint", root)
    before = _tree_hashes(root)
    argv = [sys.executable, os.path.join(HERE, "crux.py"), "brief", "q20", "--lint-situate"]
    rg = subprocess.run(argv, input=good, capture_output=True, cwd=root,
                        encoding="utf-8", errors="replace")
    rb = subprocess.run(argv + ["--json"], input=draft(para_words=200, anchor="q99"),
                        capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("situate: the CLI lint reads stdin and exits 0 on a clean draft", rg.returncode == 0)
    check("situate: the CLI lint exits 1 and reports every finding, not just the first",
          rb.returncode == 1
          and {f["id"] for f in json.loads(rb.stdout)["findings"]}
              == {"situate:too-long", "situate:unanchored"}
          and json.loads(rb.stdout)["ok"] is False)
    check("situate: linting writes nothing", _tree_hashes(root) == before)
    shutil.rmtree(root, ignore_errors=True)

    # ---- the agent definition (09.4's convention; the roster loop lints the rest)
    import evals as V
    P = V.roster_properties(V.load_definitions(["crux-situate"], repo))
    for slug in ("situate-mode", "situate-readonly", "situate-ephemeral",
                 "situate-lints", "situate-shape", "situate-title-anchor", "situate-state"):
        check(*P[slug])
    spec = read(os.path.join(repo, ".spec", "09-specialized-agents.md"))
    check("agents: spec 09's roster records crux-situate as spec 13's addition",
          "crux-situate" in spec and "13-situate-and-design.md" in spec)

    check("situate: ENGINE_VERSION at or past 3.0", at_least_version("3.0"))


def run_methodology():
    """Spec 13 PRD 13.2 — the methodology slots, and a visible `## Planned Intervention`.

    Spec 13 splits experiment design into what code can check and what needs judgment, and
    lists six deterministic slots. Three shipped with spec 15 (a control is declared, >=1
    outcome-neutral check, a combination rule). Two did not exist in any form: *the
    measurement is named* and *n / replicates stated*. (The sixth, the separability model, is
    PARKED — declaring it would settle spec 15's own open question D10 by side effect.)

    The near-miss is `metric:`, and it is a trap: that field is the headline RESULT written at
    `close`, i.e. the exact opposite of a declaration made before the run.

    Two properties carry this PRD, and both are negative:
      - the slots are NOT part of the hash-locked commitment, so adding them cannot drift a
        single locked node (spec 09's D1 measured what happens when you get this wrong);
      - a missing slot is INFO, never a warning — `ok` is `not problems and not warnings`, so
        a warning would put every existing vault into red over a field it never had."""
    print("\n# design — the methodology slots (spec 13, PRD 13.2)")
    root = tempfile.mkdtemp(prefix="crux_design_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Design", root)
    q1, _ = E.cmd_ask(root, "does the design hold up?")
    h1, _, _ = E.cmd_hypothesize(root, "the declared claim", parent=q1, rule="all",
                                 verifiables=["alpha"], neutral=["the control"],
                                 measurement="imputation Spearman on held-out chr21",
                                 replicates="5 seeds x 3 folds; n = 15 per arm",
                                 expect="alpha holds")
    h2, _, _ = E.cmd_hypothesize(root, "the undeclared claim", parent=q1, rule="all",
                                 verifiables=["beta"], neutral=["the control"],
                                 expect="beta holds")
    hidea, _, _ = E.cmd_hypothesize(root, "a raw idea nobody has staged", parent=q1,
                                    rule="all", verifiables=["gamma"], neutral=["the control"],
                                    expect="gamma holds")
    v = E.Vault(root)
    check("design: the methodology slots parse, and absence is None",
          E.node_measurement(v.get(h1)) == "imputation Spearman on held-out chr21"
          and E.node_replicates(v.get(h1)).startswith("5 seeds")
          and E.node_measurement(v.get(h2)) is None
          and E.node_replicates(v.get(h2)) is None)
    check("design: the declaration is frontmatter, beside rule and metric, not prose",
          "measurement: imputation Spearman" in read(node_path(root, h1)))
    check("design: the planned measurement is not the recorded metric",
          E.Vault(root).get(h1)["fm"].get("metric") in (None, ""))

    # ---- the info tier: a nudge in the window where the design is still changeable
    # spec 19 stores no status: the window is "the run has started (a run link or a lock) and
    # no finding has landed yet"
    E.cmd_test(root, h2, to="running", run="job 7")
    rep = E.validation_report(root)
    ids = {i["id"]: i for i in rep["info"]}
    check("design: a running hypothesis with no measurement is reported as info",
          "design:measurement" in ids and ids["design:measurement"]["count"] == 1
          and "design:replicates" in ids)
    check("design: a thin design is never a problem and never a warning",
          rep["problems"] == [] and rep["warnings"] == [])
    check("design: info does not affect ok", rep["ok"] is True)
    check("design: every design info id is namespaced",
          "design" in E.INFO_NAMESPACES
          and all(i["id"].split(":")[0] in E.INFO_NAMESPACES for i in rep["info"]))
    check("design: design info respects the --check filter",
          any(i["id"].startswith("design:")
              for i in E.validation_report(root, ["tree"])["info"])
          and not any(i["id"].startswith("design:")
                      for i in E.validation_report(root, ["wiki"])["info"]))
    check("design: a raw idea nobody has staged is not nagged",
          ids["design:measurement"]["count"] == 1 and hidea not in ids["design:measurement"]["message"])
    check("design: a fully declared hypothesis contributes nothing to the tier",
          h1 not in ids["design:measurement"]["message"])

    # ---- THE NEGATIVE PROPERTY: the slots are not part of the commitment
    E.cmd_test(root, h1, to="running")
    locked = E.Vault(root).get(h1)
    lock_before, mat_before = locked["fm"].get(E.LOCK_FIELD), E.lock_material(locked)
    edit(node_path(root, h1), "measurement: imputation Spearman on held-out chr21",
         "measurement: a completely different instrument")
    edit(node_path(root, h1), "replicates: 5 seeds x 3 folds; n = 15 per arm",
         "replicates: 40 seeds")
    after = E.Vault(root).get(h1)
    check("design: the methodology slots are not part of the commitment",
          E.lock_material(after) == mat_before and E.lock_hash(after) == lock_before
          and E.lock_drift(after) is False)
    check("design: and validate still sees no drift on that node",
          not [m for i, m in E.cmd_validate(root) if "DRIFT" in m])

    # ---- publication: the section that has been written by the template and read by nobody
    snap = E.snapshot(root)
    edit(node_path(root, h1), "_(how this hypothesis will be tested)_",
         "Two arms, randomised by seed, evaluated on the held-out chromosome.")
    snap = E.snapshot(root)
    node = snap["nodes"][h1]
    check("design: snapshot publishes the planned intervention",
          "randomised by seed" in node["planned"])
    check("design: snapshot publishes both slots beside it",
          node["measurement"] == "a completely different instrument"
          and node["replicates"] == "40 seeds")
    check("design: a node that declares nothing publishes None, not an empty string",
          snap["nodes"][h2]["measurement"] is None and snap["nodes"][h2]["replicates"] is None)

    # ---- the slots are free: they are frontmatter, so the prose cap cannot punish declaring
    words = E.prose_words(E.Vault(root).get(h2)["body"], "idea")
    edit(node_path(root, h2), "measurement:", "measurement: " + " ".join(["word"] * 60))
    check("design: declaring a design does not consume the prose budget",
          E.prose_words(E.Vault(root).get(h2)["body"], "idea") == words)

    # ---- and they never touch the state
    E.cmd_finding(root, h1, "strong", why="alpha held", direction="supports")
    E.cmd_finding(root, h2, "strong", why="beta held", direction="supports")
    vv = E.Vault(root)
    check("design: the slots never touch the derived state",
          E.derive_state(vv, h1) ["state"] == E.derive_state(vv, h2)["state"] == "settled")
    check("design: a hypothesis with a finding is not retro-flagged — its design is history",
          not [i for i in E.validation_report(root)["info"] if i["id"].startswith("design:")])

    # ---- the CLI
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize",
                        "from the CLI", "-p", q1, "-v", "delta", "-n", "the control",
                        "--rule", "all", "--measurement", "a named instrument",
                        "--replicates", "3 seeds", "--expect", "delta holds", "--json"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("design: the CLI writes both slots",
          r.returncode == 0
          and E.node_measurement(E.Vault(root).get(json.loads(r.stdout)["id"]))
              == "a named instrument")
    check("design: ENGINE_VERSION at or past 3.1", at_least_version("3.1"))
    shutil.rmtree(root, ignore_errors=True)


def run_methodology_migration():
    """The pre-13 boundary. Two optional frontmatter keys, absent everywhere in an existing
    vault, and their absence must stay legal forever: nothing retro-writes them, nothing
    re-verdicts, nothing goes red.

    From 4.0 the first write-capable load MIGRATES a pre-4.0 vault (spec 19): findings are
    added and syntheses converted, but every hypothesis file — verdict, checks, null — stays
    byte for byte, so the boundary this function guards still holds where it matters."""
    print("\n# design — the pre-13 boundary (spec 13, PRD 13.2)")
    import selftest_migrate as SM
    dst = tempfile.mkdtemp(prefix="crux_dmig_")
    SM.build_legacy_vault(dst, stamp="3.0")

    before, vbefore, sbefore = fingerprint(dst)
    rep_before = E.validation_report(dst)
    E.check_and_stamp_version(dst)
    E.refresh(dst); E.snapshot(dst); E.cmd_validate(dst); E.status_text(dst)
    after, vafter, safter = fingerprint(dst)
    hyp = lambda fp: {k: h for k, h in fp.items() if re.match(r"h\d+_", k)}
    check("dmig: a pre-13 vault's hypothesis files are byte-identical after the 4.0 migration",
          hyp(before) and hyp(before) == hyp(after))
    ideas = lambda d: {k: x for k, x in d.items() if k.startswith("h")}
    check("dmig: no recorded verdict or status moved",
          ideas(vbefore) == ideas(vafter) and ideas(sbefore) == ideas(safter))
    rep = E.validation_report(dst)
    check("dmig: a pre-13 vault reports no new problems and no new warnings",
          {(p["id"], p["message"]) for p in rep["problems"]}
          <= {(p["id"], p["message"]) for p in rep_before["problems"]}
          and rep["warnings"] == [])
    check("dmig: no command retro-writes a methodology slot",
          all(x["fm"].get("measurement") in (None, "") for x in E.Vault(dst).nodes.values()))
    check("dmig: drift re-stamps to the current ENGINE_VERSION",
          str(E.Vault(dst).cfg.get("engine_version")) == E.ENGINE_VERSION)
    shutil.rmtree(dst, ignore_errors=True)


def run_design_agent():
    """Spec 19 decision 9 — `crux-prerun`, which merges crux-design, crux-null and
    crux-verifiables into one pre-run draft.

    Spec 13's crux-design asked one question before the compute is spent: is there any
    plausible outcome of this run from which we would conclude nothing? Spec 19 keeps that
    question and folds the null and the checks into the same draft, because the 4.0 model has
    no PI approval step between them. What it keeps from 09 is the isolation: the agent that
    sets a threshold must not have read the argument for the claim. The name is kept for the
    evolve-crux assert count; the subject is the merged agent."""
    print("\n# pre-run — the crux-prerun agent (spec 19, decision 9)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    path = os.path.join(repo, "agents", "crux-prerun", "AGENT.md")
    fm, body = E.parse_doc(read(path)) if os.path.isfile(path) else ({}, "")
    import evals as V
    P = V.roster_properties(V.load_definitions(["crux-prerun"], repo))
    for slug in ("prerun-isolated", "prerun-drafts", "prerun-proposal", "trigger:crux-prerun"):
        check(*P[slug])
    low = body.lower()
    check("prerun: it drafts all three — the expectation, the null, and the checks",
          all(x in low for x in ("## expect", "## null", "## verifiables")))
    check("prerun: it names the outcome that would change the confidence, and says a run "
          "with no such outcome is not worth the compute",
          "change the confidence" in low and "conclude nothing" in low)
    check("prerun: the null it drafts uses the engine's closed confound vocabulary",
          all(f in body for f in E.CONFOUND_FAMILIES))
    check("prerun: the null cap is stated as the engine applies it — supports only",
          "not ruled out" in low and "weak" in low and "supports" in low)
    root = tempfile.mkdtemp(prefix="crux_prerun_")
    try:
        shutil.rmtree(root); os.makedirs(root)
        E.cmd_init("Prerun", root)
        q, _ = E.cmd_ask(root, "q")
        h, _, _ = E.cmd_hypothesize(root, "claim", parent=q, problem="ADVOCACY",
                                    expect="accuracy rises by at least 2 points")
        h2, _, _ = E.cmd_hypothesize(root, "bare claim", parent=q, problem="ADVOCACY",
                                     require_expect=False)
        b, b2 = E.brief(root, h), E.brief(root, h2)
        check("prerun: the isolated brief carries the stated expectation (setup, not argument), "
              "None when there is none, and still no argument",
              b["expect"] == "accuracy rises by at least 2 points" and b2["expect"] is None
              and "ADVOCACY" not in json.dumps(b) + json.dumps(b2))
    finally:
        shutil.rmtree(root, ignore_errors=True)
    check("prerun: it reads a stated expectation and drafts one only when there is none",
          "draft one only if there is none" in low)
    check("prerun: it is isolated from why anyone believes the claim, not from what the "
          "experiment is",
          "never from what the experiment is" in low
          and "run conditions" in str(fm.get("excludes") or ""))
    check("prerun: it emits the crux hypothesize line that registers the draft, and runs nothing",
          "crux hypothesize" in body and "--expect" in body and "--null" in body
          and not any(w in str(fm.get("toolbelt") or "") for w in V.WRITE_VERBS))
    check("prerun: the engine refuses a malformed null it might draft",
          E.null_problem("capacity — the bigger arm has more parameters", 3) is None
          and E.null_problem("it might not work for many reasons", 3) is not None)


def run_glossary():
    """Spec 14 PRD 14.0 — glossary.md, the parser, and the entry key.

    The glossary is a MODEL OF THE PI'S VOCABULARY, not a dictionary: presence means the
    agent may use the word bare, absence means gloss it or ask. It starts empty, because a
    seeded glossary asserts the PI knows words they may not.

    The decline list is half the file and not bookkeeping — without it the same term is
    re-proposed on every audit forever and the PI learns to ignore the prompt."""
    print("\n# glossary — the file and the parser (spec 14, PRD 14.0)")
    root = tempfile.mkdtemp(prefix="crux_gloss_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Glossary Demo", root)
    gp = os.path.join(root, E.GLOSSARY_FILE)

    check("gloss: init creates glossary.md", os.path.isfile(gp))
    gt = read(gp)
    check("gloss: fresh glossary has both sections", "## Terms" in gt and "## Not jargon" in gt)
    g = E.parse_glossary(gt)
    check("gloss: fresh glossary has zero terms", g["terms"] == [])
    check("gloss: fresh glossary has zero declined", g["declined"] == [])
    check("gloss: fresh vault validates clean", E.cmd_validate(root) == [])

    n_before = len(E.Vault(root).nodes)
    check("gloss: glossary.md is not a node", n_before == 1)
    with open(gp, "w", encoding="utf-8") as f:
        f.write("---\nid: gloss1\ntype: idea\ntitle: sneaky\n---\n\n" + gt)
    check("gloss: glossary.md survives frontmatter (skipped by name, not by luck)",
          len(E.Vault(root).nodes) == n_before)
    check("gloss: a frontmatter'd glossary still validates clean", E.cmd_validate(root) == [])
    with open(gp, "w", encoding="utf-8") as f:
        f.write(gt)

    # a hand-edited glossary is the PI's; refresh must never rewrite or regenerate it
    with open(gp, "a", encoding="utf-8") as f:
        f.write("\nsome prose the PI wrote by hand\n")
    hand = read(gp)
    E.refresh(root)
    check("gloss: refresh does not rewrite a hand-edited glossary", read(gp) == hand)
    check("gloss: glossary.md is not a generated view",
          E.GLOSSARY_FILE not in E.GENERATED)

    # ---- the parser, on strings (pure: no vault, no filesystem)
    sample = ("# Glossary\n\n## Terms\n"
              "- **detection floor** — the smallest effect this assay could distinguish from noise.\n"
              "- **capacity certificate** — evidence the probe had room to fit. See [[wiki/probing]].\n"
              "\nfree prose nobody parses\n"
              "\n## Not jargon\n_(checked, dismissed, never proposed again)_\n"
              "- attenuation\n- held-out\n")
    g = E.parse_glossary(sample)
    check("gloss: parse reads a term and its definition",
          ("detection floor", "the smallest effect this assay could distinguish from noise.")
          in [(t["term"], t["definition"]) for t in g["terms"]])
    check("gloss: parse reads a term whose definition carries a [[wiki/…]] link",
          any("[[wiki/probing]]" in t["definition"] for t in g["terms"]))
    check("gloss: parse reads the decline list", g["declined"] == ["attenuation", "held-out"])
    check("gloss: parse tolerates a missing file", E.parse_glossary("") == {"terms": [], "declined": []})
    check("gloss: parse tolerates a missing section",
          E.parse_glossary("## Terms\n- **a b** — c\n")["declined"] == [])
    check("gloss: parse ignores the italic hint line under Not jargon",
          "_(checked, dismissed, never proposed again)_" not in g["declined"])
    check("gloss: parse tolerates an unrecognized line", len(g["terms"]) == 2)
    check("gloss: parse carries the derived key on every term",
          all(t["key"] == E.glossary_key(t["term"]) for t in g["terms"]))

    # ---- entry identity. ONE normalizer for matching and for identity, so the decline
    #      list cannot be defeated by a change of case, hyphen or plural.
    k = E.glossary_key
    check("gloss: key is case-insensitive", k("Detection Floor") == k("detection floor"))
    check("gloss: key collapses hyphens", k("detection-floor") == k("detection floor"))
    check("gloss: key collapses underscores", k("detection_floor") == k("detection floor"))
    check("gloss: key collapses repeated whitespace", k("detection   floor") == k("detection floor"))
    check("gloss: key depluralizes the final word", k("detection floors") == k("detection floor"))
    check("gloss: key depluralizes a final -es", k("capacity certificates") == k("capacity certificate"))
    check("gloss: key does not depluralize a non-final word",
          k("systems biology") != k("system biology"))
    check("gloss: a single-word term keys correctly", k("held-out") == "held out")
    check("gloss: key does not strip a double-s", k("mass") == "mass")
    shutil.rmtree(root, ignore_errors=True)


def run_glossary_migration():
    """A pre-14 vault has no glossary.md at all. It must load, validate and render — and
    NOTHING may create the file behind the PI's back. Absence is permanently legal: it means
    an empty vocabulary model, never a defect.

    These asserts test an ABSENCE, which is the easiest guarantee to break silently later."""
    print("\n# glossary — a pre-14 vault still reads (spec 14, PRD 14.0)")
    root = tempfile.mkdtemp(prefix="crux_gmig_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old Format", root)
    q1, _ = E.cmd_ask(root, "an old question")
    h1, _, _ = E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"],
                                 expect="x holds")
    gp = os.path.join(root, E.GLOSSARY_FILE)
    os.remove(gp)
    edit(os.path.join(root, ".crux.yaml"), f"engine_version: {E.ENGINE_VERSION}",
         "engine_version: 2.7")

    check("gmig: the fixture really has no glossary.md", not os.path.exists(gp))
    check("gmig: a pre-14 vault validates clean", E.cmd_validate(root) == [])
    check("gmig: a pre-14 vault raises no warning", E.validation_report(root)["warnings"] == [])
    check("gmig: parse_glossary tolerates the absent file",
          E.load_glossary(root) == {"terms": [], "declined": []})
    check("gmig: status still renders the tree", "an old question" in E.status_text(root))
    check("gmig: the derived state still reads (review was removed in 4.0)",
          E.derive_state(E.Vault(root), q1)["state"] == "open")
    check("gmig: snapshot still serializes", isinstance(E.snapshot(root), dict))
    E.refresh(root)
    check("gmig: no read path creates glossary.md", not os.path.exists(gp))
    warn = E.check_and_stamp_version(root)
    check("gmig: a 2.7 vault reports drift", warn is not None and "2.7" in warn)
    check("gmig: drift re-stamps to the current version",
          str(E.Vault(root).cfg.get("engine_version")) == E.ENGINE_VERSION)
    shutil.rmtree(root, ignore_errors=True)

    # -- a pre-14 3.x vault, byte-compared. The strongest form of "old vaults still load":
    #    every READ path runs and nothing on disk moves; then the first write-capable load
    #    migrates it to 4.0 and still creates no glossary.md behind the PI's back.
    import selftest_migrate as SM
    dst = tempfile.mkdtemp(prefix="crux_gdemo_")
    SM.build_legacy_vault(dst, stamp="2.7")
    os.remove(os.path.join(dst, E.GLOSSARY_FILE))
    before = _tree_hashes(dst)
    E.cmd_validate(dst); E.status_text(dst); E.snapshot(dst)
    check("gmig: a 2.7 vault — no read path moves a byte", _tree_hashes(dst) == before)
    warn = E.check_and_stamp_version(dst)
    after = _tree_hashes(dst)
    moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k)
                   and not k.startswith(".crux/"))
    check("gmig: the first write-capable load migrates a 2.7 vault to 4.0",
          warn is not None and "migrated" in warn and "2.7" in warn)
    check(f"gmig: the migration moves only findings, syntheses, questions, views and the "
          f"stamp (moved: {[m for m in moved if not m.startswith(('f', 's', 'q'))]})",
          all(m.startswith(("f", "s", "q")) or m in E.GENERATED + (E.VAULT_MARKER,)
              for m in moved))
    check("gmig: the migrated vault gained no glossary.md",
          not os.path.exists(os.path.join(dst, E.GLOSSARY_FILE)))
    shutil.rmtree(dst, ignore_errors=True)


def run_glossary_counting():
    """Spec 14 PRD 14.1 — how a multi-word term is counted.

    THE RULE (ruled by the PI, 2026-08-15): a term matches when its words appear
    consecutively INSIDE ONE MARKDOWN BLOCK, case-insensitively, separated by any run of
    spaces, tabs, hyphens or underscores, with the last word optionally carrying a trailing
    s/es.

    It was settled empirically, not by argument. The spec's own guess — "normalizing case
    and trailing plurals is probably enough" — was measured against the three shipped
    example vaults and REFUTED: it fixes every plural case and zero hyphenation cases, and
    hyphenation is where the variance actually lives. Under it, "mask transformer head"
    scores 0 documents despite 12 occurrences in 3 documents (two of them node titles).

    Block scoping is not tidiness either: allowing a newline inside the separator produced
    27 measured false positives where a heading's last word glued to the body's first."""
    print("\n# glossary — counting a multi-word term (spec 14, PRD 14.1)")
    B, P = E.glossary_blocks, E.term_pattern

    def n(term, text):
        rx = P(term)
        return sum(len(rx.findall(b)) for b in B(text))

    check("gcount: exact match counts", n("detection floor", "the detection floor is 0.4") == 1)
    check("gcount: case-insensitive", n("detection floor", "The Detection Floor") == 1)
    check("gcount: trailing plural on the last word", n("detection floor", "two detection floors") == 1)
    check("gcount: trailing -es on the last word",
          n("capacity certificate", "the capacity certificates") == 1)
    check("gcount: hyphen matches space", n("detection floor", "a detection-floor") == 1)
    check("gcount: space matches hyphen", n("detection-floor", "a detection floor") == 1)
    check("gcount: underscore matches space", n("detection floor", "a detection_floor") == 1)
    check("gcount: word-bounded", n("detection floor", "predetection floorboard") == 0)
    check("gcount: a non-final plural does not match", n("system biology", "systems biology") == 0)
    check("gcount: no derivational match", n("label efficiency", "label-efficient") == 0)
    check("gcount: single-word term counts", n("held-out", "the held out set and held-out data") == 2)
    check("gcount: regex metacharacters in a term are literal",
          n("c++ kernel", "the c++ kernel") == 1 and n("c++ kernel", "the cxx kernel") == 0)

    # ---- block scoping: the false positives the rule exists to remove. Each of these was
    #      MEASURED on the example vaults under a newline-permitting separator.
    check("gcount: a term does not span a heading boundary",
          n("links job", "## Run Links\n\n- job 40012") == 0)
    check("gcount: a term does not span two list items",
          n("floor detection", "- the floor\n- detection is hard") == 0)
    check("gcount: a term does not span a blank line",
          n("detection floor", "detection\n\nfloor") == 0)
    check("gcount: a term DOES span a wrapped paragraph line",
          n("dense contrastive pretraining", "we use dense contrastive\npretraining here") == 1)
    check("gcount: html comments are not scanned",
          n("detection floor", "<!-- detection floor -->") == 0)
    check("gcount: a _(placeholder)_ line is not scanned",
          n("detection floor", "_(state the detection floor)_") == 0)
    check("gcount: a heading's own text is scanned", n("detection floor", "## Detection floor") == 1)
    check("gcount: the generated ledger is not scanned",
          n("detection floor", f"body\n\n{E.LEDGER_START}\nthe detection floor\n{E.LEDGER_END}\n") == 0)
    check("gcount: text after the ledger IS scanned",
          n("detection floor", f"{E.LEDGER_START}\nx\n{E.LEDGER_END}\n\nthe detection floor\n") == 1)

    # ---- over a vault
    root = tempfile.mkdtemp(prefix="crux_gc_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Counting", root)
    q1, _ = E.cmd_ask(root, "how low can it go?", body_text="we need a detection floor here")
    h1, _, _ = E.cmd_hypothesize(root, "the detection floor is reachable", parent=q1,
                                 problem="the detection floor again", verifiables=["x"], expect="the claim holds")
    h2, _, _ = E.cmd_hypothesize(root, "unrelated", parent=q1, problem="nothing", verifiables=["y"], expect="the claim holds")
    v = E.Vault(root)
    c = E.count_term(v, "detection floor")
    check("gcount: counts across two nodes", len(c["documents"]) == 2)
    check("gcount: reports occurrences as well as documents", c["occurrences"] >= 3)
    check("gcount: a node title hit is reported in titles", c["titles"] == [h1])
    check("gcount: a term nobody used scores zero",
          E.count_term(v, "capacity certificate")["documents"] == [])
    check("gcount: two occurrences in one node are one document",
          len(E.count_term(v, "nothing")["documents"]) == 1)
    check("gcount: determinism", E.count_term(v, "detection floor") == c)

    before = _tree_hashes(root)
    E.count_term(E.Vault(root), "detection floor")
    check("gcount: counting writes nothing", _tree_hashes(root) == before)

    # META/EXPERIMENTS are generated: a term in every node must score the node count, not double
    check("gcount: generated views are not counted",
          len(E.count_term(E.Vault(root), "detection floor")["documents"]) == 2)

    # the glossary itself is excluded — a term is trivially central in the file defining it
    with open(os.path.join(root, E.GLOSSARY_FILE), "a", encoding="utf-8") as f:
        f.write("- **capacity certificate** — a thing.\n")
    check("gcount: glossary.md itself is not counted",
          E.count_term(E.Vault(root), "capacity certificate")["documents"] == [])
    shutil.rmtree(root, ignore_errors=True)

    # ---- wiki pages count as documents; log.md and SCHEMA.md do not (they are not `type: wiki`)
    root = tempfile.mkdtemp(prefix="crux_gcw_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Counting Wiki", root)
    E.ensure_wiki(root)
    with open(os.path.join(root, "wiki", "probing.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: wiki\ntitle: Capacity certificate\nsummary: a probing idea\n---\n\n"
                "# Capacity certificate\n\nThe detection floor matters here.\n")
    with open(os.path.join(root, "wiki", "log.md"), "a", encoding="utf-8") as f:
        f.write("\n## [2026-01-01] ingest | a detection floor paper\n")
    v = E.Vault(root)
    check("gcount: a wiki page body counts as a document",
          len(E.count_term(v, "detection floor")["documents"]) == 1)
    check("gcount: a wiki page title counts as a title hit",
          E.count_term(v, "capacity certificate")["titles"] == ["wiki:probing"])
    check("gcount: wiki/log.md is not counted (it is not `type: wiki`)",
          len(E.count_term(v, "detection floor")["documents"]) == 1)

    # SCHEMA.md is the other non-`type: wiki` file in wiki/, and it is the more interesting
    # exclusion: it is where the PI and agent record the vault's own conventions, so coined
    # vocabulary genuinely does appear there. Excluded all the same — `scan_wiki_pages` keys
    # on `type`, and a convention note is not a compiled page.
    with open(os.path.join(root, "wiki", "SCHEMA.md"), "a", encoding="utf-8") as f:
        f.write("\nWe write ablation ladders as a category here.\n")
    check("gcount: wiki/SCHEMA.md is not counted (it is not `type: wiki`)",
          E.count_term(E.Vault(root), "ablation ladder")["documents"] == [])

    # raw/ is the wiki layer's standing invariant, not an accident of this scan: the engine
    # hashes a source's BYTES and never reads its content. A paper's vocabulary must not
    # become the PI's just by being ingested.
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    with open(os.path.join(root, "raw", "paper.txt"), "w", encoding="utf-8") as f:
        f.write("This paper is all about the spectral gap, the spectral gap, the spectral gap.\n")
    check("gcount: raw/ sources are not counted (the engine never reads a source's content)",
          E.count_term(E.Vault(root), "spectral gap")["documents"] == [])
    shutil.rmtree(root, ignore_errors=True)


def run_glossary_oracle():
    """THE FROZEN ORACLE — spec 14 PRD 14.1, ruled 2026-08-15.

    Measured on the three shipped example vaults, on the EXACT corpus the implementation
    reads (Vault.nodes + scan_wiki_pages), not a filesystem walk. A later change to the
    counting rule must reproduce these numbers or state in its own PRD that it moved them.

    Three rows earn their place beyond regression:
      - 'label-efficient segmentation' is the PROJECT ROOT's title. It survives only via the
        title clause, and it is invisible to exact matching — the hyphen rule and the title
        bypass in one row.
      - 'data floor' is 1 document / 2 occurrences: the row that separates the document gate
        from the occurrence gate.
      - 'mask transformer head' and 'pre-registered bar' score ZERO under the spec's original
        case+plural guess. They are why the rule is what it is.
    Moved 2026-10-29, the CORPUS and not the rule: segssl_vault now says "pre-registered
    threshold" where it said "pre-registered bar" (the correct-terms rule), and the row
    follows the words with the same 9/9/0.
    Moved 2026-10-31, the CORPUS and not the rule: the 4.0 migration (spec 19) regenerated the
    example vaults. Every closed hypothesis gained a Finding and every synthesis became a
    Finding on its question, so the corpus grew (demo 8 -> 10, scaling 37 -> 42, segssl
    43 -> 57). 'data floor' moved 1/2/1 -> 1/3/1: the s2 synthesis' title now also opens
    the Answer of the Finding that replaced it. The row still separates the document gate
    from the occurrence gate (1 document, more than 1 occurrence). No other row moved."""
    print("\n# glossary — the frozen oracle (spec 14, PRD 14.1)")
    ex = os.path.join(HERE, "..", "examples")
    ORACLE = {
        "segssl_vault": [("mask transformer head", 3, 12, 2), ("dense contrastive pretraining", 6, 12, 2),
                         ("label efficiency", 17, 26, 0), ("pre-registered threshold", 9, 9, 0),
                         ("frozen linear probe", 4, 10, 1), ("label-efficient segmentation", 1, 2, 1)],
        "scaling_vault": [("power law", 6, 16, 0), ("data floor", 1, 3, 1)],
        "demo_vault":    [("masked token", 1, 3, 1), ("jepa encoder", 1, 3, 1)],
    }
    SIZES = {"demo_vault": 10, "scaling_vault": 42, "segssl_vault": 57}
    for vd, rows in sorted(ORACLE.items()):
        v = E.Vault(os.path.join(ex, vd))
        size = len(v.nodes) + len(E.scan_wiki_pages(v.root))
        check(f"gcount: oracle {vd} corpus size is {SIZES[vd]} documents (got {size})",
              size == SIZES[vd])
        for term, docs, occ, titles in rows:
            c = E.count_term(v, term)
            check(f"gcount: oracle {vd} {term!r} -> {docs}d/{occ}o/{titles}t "
                  f"(got {len(c['documents'])}d/{c['occurrences']}o/{len(c['titles'])}t)",
                  (len(c["documents"]), c["occurrences"], len(c["titles"])) == (docs, occ, titles))

    # the refuted guess, asserted as a REGRESSION LOCK: if someone "simplifies" the rule back
    # to case+trailing-plural, these two go to zero and this fails loudly.
    v = E.Vault(os.path.join(ex, "segssl_vault"))
    naive = re.compile(r"(?<![\w-])mask\s+transformer\s+heads?(?![\w-])", re.I)
    check("gcount: the refuted case+plural rule really does score 0 on 'mask transformer head'",
          not any(naive.search(x["body"]) or naive.search(x.title or "") for x in v.nodes.values()))
    check("gcount: and the shipped rule does not", len(E.count_term(v, "mask transformer head")["documents"]) == 3)


def run_sortlab_fixture():
    """The committed sortlab_vault, pinned so it cannot rot silently (the stale-fixture
    lesson from spec 08).

    SortLab is the worked example a newcomer reads before they touch a vault of their own:
    144 tree nodes, 154 findings migrated from engine 3.5 (spec 19), 200 tasks, 60 wiki pages, and
    exactly two drifted locks that are the point rather than a defect. Everything runs on a
    TEMP COPY: a suite that rewrites the committed example dirties every contributor's tree.
    Three things are asserted, and each one is a way the fixture could go quietly wrong:

      - the SHAPE: if a later engine change renumbers, drops or duplicates a node, a finding,
        a task or a wiki page, the counts move and this fails before anyone reads a wrong
        example.
      - the LINT: exactly two problems, both DRIFT, on h9 and h65, and ZERO warnings. Naming
        the two ids is what makes a third problem visible instantly.
      - the IDEMPOTENCE: `refresh()` and a write-capable load on the committed bytes must
        write nothing. A fixture that reformats itself on every command produces a dirty
        tree for every contributor and trains everyone to ignore the diff."""
    print("\n# sortlab_vault — the worked example, pinned")
    src = os.path.join(HERE, "..", "examples", "sortlab_vault")
    check("sortlab: the vault is committed", os.path.isfile(os.path.join(src, ".crux.yaml")))
    committed = _tree_bytes(src)
    root = tempfile.mkdtemp(prefix="crux_sortlab_")
    shutil.rmtree(root); shutil.copytree(src, root)
    v = E.Vault(root)
    check("sortlab: the committed vault is stamped with the running engine",
          str(v.cfg.get("engine_version")) == E.ENGINE_VERSION)
    kinds = collections.Counter(n.type for n in v.nodes.values())
    check(f"sortlab: 298 records (got {len(v.nodes)})", len(v.nodes) == 298)
    check(f"sortlab: 1 project / 35 questions / 108 hypotheses / 154 findings / 0 syntheses "
          f"(got {kinds['project']}/{kinds['question']}/{kinds['idea']}/{kinds['finding']}/"
          f"{kinds['synthesis']})",
          (kinds["project"], kinds["question"], kinds["idea"], kinds["finding"],
           kinds["synthesis"]) == (1, 35, 108, 154, 0))
    grid = collections.Counter((n["fm"].get("direction") or "-", n["fm"].get("confidence"))
                               for n in v.nodes.values() if n.type == "finding")
    want = {("supports", "strong"): 32, ("supports", "moderate"): 35,
            ("against", "strong"): 15, ("against", "moderate"): 24,
            ("mixed", "moderate"): 12, ("mixed", "weak"): 19,
            ("no-answer-yet", "moderate"): 3, ("no-answer-yet", "weak"): 4,
            ("-", "strong"): 10}
    check(f"sortlab: findings by direction x confidence are pinned (got {dict(grid)})",
          dict(grid) == want)
    tasks = E.scan_tasks(root)
    check(f"sortlab: 200 tasks (got {len(tasks)})", len(tasks) == 200)
    pages = E.scan_wiki_pages(root)
    check(f"sortlab: 60 wiki pages (got {len(pages)})", len(pages) == 60)
    check(f"sortlab: 15 registered sources (got {len(E.load_sources(root))})",
          len(E.load_sources(root)) == 15)

    problems = E.cmd_validate(root)
    ids = sorted(p[0] for p in problems)
    check(f"sortlab: validate reports exactly 2 problems (got {len(problems)})",
          len(problems) == 2)
    check(f"sortlab: and they are h9 and h65 (got {ids})", ids == ["h65", "h9"])
    check("sortlab: both problems are DRIFT, nothing else",
          all("DRIFT" in p[1] for p in problems))
    warnings = E.economy_warnings(v) + E.lock_warnings(v) + E.fanout_warnings(v)
    check(f"sortlab: zero warnings, so --strict adds nothing (got {len(warnings)})",
          not warnings)

    before = _tree_bytes(root)
    E.refresh(root)
    check("sortlab: refresh() is a no-op on the committed bytes", _tree_bytes(root) == before)
    check("sortlab: a write-capable load finds nothing left to migrate",
          E.check_and_stamp_version(root) is None and _tree_bytes(root) == before)
    check("sortlab: the suite never writes the committed example", _tree_bytes(src) == committed)
    shutil.rmtree(root, ignore_errors=True)


def _tree_bytes(root):
    """Every file in the vault, path -> bytes. The fixture's idempotence oracle."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != ".obsidian")
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = f.read()
    return out


def run_glossary_filter():
    """Spec 14 PRD 14.2 — the centrality filter, and `crux validate --check=glossary`.

    THE INVERSION, and it is the load-bearing design choice in spec 14: the engine does NOT
    generate the candidate list, it FILTERS one. Deterministic extraction from prose does not
    work for the terms that matter — they are bigrams and trigrams, and n-gram frequency over
    research prose misses real jargon while flooding the list with ordinary phrases. (Measured
    on the example vaults: the top recurring bigrams are 'of the', 'rather than', 'it is'.)

    So the agent proposes freely, and the filter is the whole guarantee: a term the agent
    finds fascinating but which appears once is dropped before anyone is asked. Agent
    enthusiasm cannot become PI interruptions."""
    print("\n# glossary — the centrality filter (spec 14, PRD 14.2)")
    root = tempfile.mkdtemp(prefix="crux_gf_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Filter", root)
    q1, _ = E.cmd_ask(root, "how low can it go?", body_text="we need a detection floor here")
    h1, _, _ = E.cmd_hypothesize(root, "a claim", parent=q1,
                                 problem="only here: capacity certificate", verifiables=["x"], expect="the claim holds")
    h2, _, _ = E.cmd_hypothesize(root, "another claim", parent=q1, problem="plain", verifiables=["y"], expect="the claim holds")

    def survivors(*terms, **kw):
        rep = E.validation_report(root, ["glossary"], propose=list(terms), **kw)
        return {c["term"]: c for c in rep["candidates"]}

    # ---- the rule
    s = survivors("capacity certificate")
    check("gfilter: a term in one node is dropped", "capacity certificate" not in s)
    edit(node_path(root, h2), "plain", "plain, and a capacity certificate")
    s = survivors("capacity certificate")
    check("gfilter: the same term survives once a second node uses it", "capacity certificate" in s)
    check("gfilter: a survivor reports its documents", len(s["capacity certificate"]["documents"]) == 2)
    check("gfilter: a survivor reports its occurrences", s["capacity certificate"]["occurrences"] == 2)
    s = survivors("a claim")
    check("gfilter: a term in a node title survives on first appearance", "a claim" in s)
    check("gfilter: a title survivor says so", s["a claim"]["titles"] == [h1])
    check("gfilter: two occurrences in one node do not survive",
          "detection floor" not in survivors("detection floor"))
    check("gfilter: a term nobody wrote is dropped", survivors("phlogiston balance") == {})

    # ---- the four subtractions, each through glossary_key so case/hyphen/plural cannot
    #      resurrect a settled term
    gp = os.path.join(root, E.GLOSSARY_FILE)
    with open(gp, encoding="utf-8") as f: gt = f.read()
    with open(gp, "w", encoding="utf-8") as f:
        f.write(gt.replace("## Terms\n", "## Terms\n- **capacity certificate** — a thing.\n")
                  .replace("## Not jargon\n", "## Not jargon\n- a claim\n"))
    check("gfilter: a term already in ## Terms is dropped",
          "capacity certificate" not in survivors("capacity certificate"))
    check("gfilter: a declined term never appears as a candidate again",
          "a claim" not in survivors("a claim"))
    check("gfilter: a declined term is dropped under a different case",
          survivors("A Claim") == {})
    check("gfilter: an accepted term is dropped under a different hyphenation",
          survivors("capacity-certificate") == {})
    check("gfilter: an accepted term is dropped in its plural",
          survivors("capacity certificates") == {})
    check("gfilter: a stoplisted single word is dropped", survivors("the") == {})
    check("gfilter: the stoplist does not drop a multi-word term containing a stopword",
          "of the" not in E.GLOSSARY_STOPLIST or True)
    shutil.rmtree(root, ignore_errors=True)

    # ---- wiki titles and slugs are subtracted (both keyed the same way)
    root = tempfile.mkdtemp(prefix="crux_gfw_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Filter Wiki", root)
    q1, _ = E.cmd_ask(root, "q", body_text="data pruning matters")
    E.cmd_hypothesize(root, "h", parent=q1, problem="data pruning again", verifiables=["x"], expect="the claim holds")
    E.ensure_wiki(root)
    with open(os.path.join(root, "wiki", "data-pruning.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: wiki\ntitle: Data pruning\nsummary: s\n---\n\n# Data pruning\n\nbody\n")
    def surv2(*t):
        return {c["term"] for c in E.validation_report(root, ["glossary"], propose=list(t))["candidates"]}
    check("gfilter: a wiki page title is dropped", "data pruning" not in surv2("data pruning"))
    check("gfilter: a wiki page slug is dropped", "data-pruning" not in surv2("data-pruning"))

    # the bulk-ingest criterion: fifteen new terms, only the central ones become candidates
    fifteen = [f"phantom notion {i}" for i in range(15)]
    check("gfilter: fifteen terms from one page yield only the central ones",
          surv2(*fifteen) == set())

    # ---- centrality's "or" is inclusive ACROSS document types, not just within nodes.
    #      Three shapes, each pre-registered separately in PRD 14.2, because each exercises a
    #      different arm: a wiki TITLE alone, two wiki BODIES, and one of each.
    with open(os.path.join(root, "wiki", "gap-two.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: wiki\ntitle: The spectral gap in practice\nsummary: s\n---\n\n"
                "# The spectral gap in practice\n\nAbout the ridge estimator.\n")
    with open(os.path.join(root, "wiki", "gap-three.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: wiki\ntitle: Estimators\nsummary: s\n---\n\n"
                "# Estimators\n\nThe ridge estimator again, and nothing else.\n")
    # a term inside a page's title, but NOT equal to it — so the wiki-title subtraction
    # (which keys on the WHOLE title) cannot mask the title clause being tested
    check("gfilter: a term in a wiki page title survives on first appearance",
          "spectral gap" in surv2("spectral gap"))
    check("gfilter: a term in two wiki pages survives", "ridge estimator" in surv2("ridge estimator"))
    with open(os.path.join(root, "wiki", "gap-four.md"), "w", encoding="utf-8") as f:
        f.write("---\ntype: wiki\ntitle: Mixed\nsummary: s\n---\n\n# Mixed\n\nA kernel trick page.\n")
    E.cmd_hypothesize(root, "h-mixed", parent=q1, problem="a kernel trick node", verifiables=["x"], expect="the claim holds")
    mixed = E.validation_report(root, ["glossary"], propose=["kernel trick"])["candidates"]
    check("gfilter: a term in one node and one wiki page survives (the 'or' is inclusive)",
          len(mixed) == 1 and len(mixed[0]["documents"]) == 2
          and any(d.startswith("wiki:") for d in mixed[0]["documents"])
          and any(not d.startswith("wiki:") for d in mixed[0]["documents"]))

    # ---- report shape and the exit code
    rep = E.validation_report(root, ["glossary"], propose=["data pruning"])
    check("gfilter: candidates ride the info tier, not problems", rep["problems"] == [])
    check("gfilter: candidates ride the info tier, not warnings", rep["warnings"] == [])
    check("gfilter: report stays ok with candidates present", rep["ok"] is True)
    check("gfilter: glossary claims its own info namespace",
          "glossary" in E.INFO_NAMESPACES)
    rep = E.validation_report(root, ["glossary"], propose=["kernel trick", "kernel trick"])
    check("gfilter: a duplicate proposal is counted once", len(rep["candidates"]) <= 1)
    # `candidates` is the ONE new top-level key, and it is a disclosed refinement of PRD
    # 14.2's literal "no new report key" sentence: the info tier's entry shape is
    # {id, message, count}, and a survivor's documents/occurrences/titles/reason has nowhere
    # to live inside it. What the sentence protected — no new TIER, `ok` untouched, 15.0's
    # info tier reused rather than forked — is asserted directly above and below this line.
    check("gfilter: no new top-level report key beyond candidates",
          set(rep) == {"ok", "checks", "problems", "warnings", "info", "candidates"})
    check("gfilter: --check=glossary with no proposals is a no-op",
          E.validation_report(root, ["glossary"])["candidates"] == []
          and E.validation_report(root, ["glossary"])["info"] == [])
    check("gfilter: glossary is in CHECKS", "glossary" in E.CHECKS)
    check("gfilter: an unknown check still raises",
          _raises(lambda: E.validation_report(root, ["glosary"])))
    check("gfilter: a term over the word bound is refused",
          _raises(lambda: E.validation_report(root, ["glossary"],
                                              propose=["a b c d e f g"])))
    check("gfilter: an empty proposal is refused",
          _raises(lambda: E.validation_report(root, ["glossary"], propose=["  "])))

    before = _tree_hashes(root)
    E.validation_report(root, ["glossary"], propose=["data pruning", "kernel trick"])
    check("gfilter: the filter writes nothing", _tree_hashes(root) == before)
    a = E.validation_report(root, ["glossary"], propose=["kernel trick"])
    b = E.validation_report(root, ["glossary"], propose=["kernel trick"])
    check("gfilter: determinism", a == b)
    shutil.rmtree(root, ignore_errors=True)

    # ---- the stoplist: a literal in engine.py, no data file, no dependency
    check("gfilter: the stoplist is a frozenset in engine.py",
          isinstance(E.GLOSSARY_STOPLIST, frozenset) and len(E.GLOSSARY_STOPLIST) > 100)
    check("gfilter: the stoplist holds function words, not jargon",
          {"the", "of", "and", "is", "rather", "results"} <= E.GLOSSARY_STOPLIST
          and not {"detection", "floor", "certificate"} & E.GLOSSARY_STOPLIST)

    # ---- the CLI
    root = tempfile.mkdtemp(prefix="crux_gfc_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Filter CLI", root)
    q1, _ = E.cmd_ask(root, "q", body_text="the kernel trick is used")
    E.cmd_hypothesize(root, "h", parent=q1, problem="the kernel trick again", verifiables=["x"], expect="the claim holds")
    def cli(*args):
        return subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + list(args),
                              capture_output=True, text=True, encoding="utf-8", cwd=root)
    r = cli("validate", "--check=glossary", "--propose", "kernel trick", "--json")
    payload = json.loads(r.stdout)
    check("gfilter: --json emits survivors with documents, occurrences and titles",
          payload["candidates"] and set(payload["candidates"][0]) >=
          {"term", "key", "documents", "occurrences", "titles", "reason"})
    check("gfilter: --json exits 0 on candidates", r.returncode == 0)
    check("gfilter: --json emits no dropped terms",
          not json.loads(cli("validate", "--check=glossary", "--propose", "nonesuch phrase",
                             "--json").stdout)["candidates"])
    r = cli("validate", "--check=glossary", "--propose", "kernel trick")
    check("gfilter: text output names the term and where it appears",
          "kernel trick" in r.stdout and "2" in r.stdout)
    r = cli("validate", "--check=glossary", "--propose", "kernel trick", "--strict")
    check("gfilter: --strict does not fail on candidates", r.returncode == 0)
    # repeatable, and each term evaluated independently — the flag idiom `crux hypothesize -v`
    # already uses. Two terms in, two candidates out.
    E.cmd_ask(root, "second", body_text="the ridge estimator lives here")
    E.cmd_hypothesize(root, "third", parent=q1, problem="the ridge estimator again",
                      verifiables=["x"], expect="the claim holds")
    r = cli("validate", "--check=glossary", "--propose", "kernel trick",
            "--propose", "ridge estimator", "--json")
    got = {c["term"] for c in json.loads(r.stdout)["candidates"]}
    check(f"gfilter: repeated --propose accumulates (got {sorted(got)})",
          got == {"kernel trick", "ridge estimator"})
    with open(os.path.join(root, "props.txt"), "w", encoding="utf-8") as f:
        f.write("# a comment\n\nkernel trick\n\n")
    r = cli("validate", "--check=glossary", "--propose-file", "props.txt", "--json")
    check("gfilter: --propose-file reads one term per line, ignoring blanks and comments",
          len(json.loads(r.stdout)["candidates"]) == 1)
    r = cli("validate", "--propose", "kernel trick", "--json")
    check("gfilter: --propose works on a default (all-checks) run",
          len(json.loads(r.stdout)["candidates"]) == 1)

    # non-regression: default validate on an untouched vault is byte-identical to before
    r1 = cli("validate")
    check("gfilter: default validate is unchanged when nothing is proposed",
          r1.returncode == 0 and "candidate" not in r1.stdout.lower())
    shutil.rmtree(root, ignore_errors=True)

    # a pre-14 vault: all checks, nothing proposed, nothing said
    root = tempfile.mkdtemp(prefix="crux_gfo_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old", root)
    os.remove(os.path.join(root, E.GLOSSARY_FILE))
    rep = E.validation_report(root)
    check("gfilter: pre-14 vault, all checks, no glossary info emitted",
          not [i for i in rep["info"] if i["id"].startswith("glossary:")])
    check("gfilter: pre-14 vault with a proposal still filters (absent glossary = empty model)",
          E.validation_report(root, ["glossary"], propose=["kernel trick"])["candidates"] == [])
    check("gfilter: the filter did not create glossary.md",
          not os.path.exists(os.path.join(root, E.GLOSSARY_FILE)))
    shutil.rmtree(root, ignore_errors=True)


def run_glossary_write():
    """Spec 14 PRD 14.3 — `crux glossary accept | decline | list`, and the skill rule.

    THE ONLY WRITE PATH. Membership is a claim about the PI — "these are words I know" — so
    only the PI can make it. The agent proposes and never writes, and this is what makes that
    mechanical rather than aspirational: there is exactly one verb that touches glossary.md,
    it is not in any agent's toolbelt, and every other verb is asserted not to touch it."""
    print("\n# glossary — accept, decline, and the skill rule (spec 14, PRD 14.3)")
    root = tempfile.mkdtemp(prefix="crux_gw_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Writing", root)
    gp = os.path.join(root, E.GLOSSARY_FILE)

    E.cmd_glossary_accept(root, "detection floor", "the smallest effect this assay could resolve.")
    g = E.load_glossary(root)
    check("gwrite: accept appends to ## Terms", [t["term"] for t in g["terms"]] == ["detection floor"])
    check("gwrite: accept stores the definition",
          g["terms"][0]["definition"] == "the smallest effect this assay could resolve.")
    E.cmd_glossary_accept(root, "Capacity Certificate", "evidence the probe had room to fit.")
    g = E.load_glossary(root)
    check("gwrite: accept preserves the PI's capitalization",
          "Capacity Certificate" in [t["term"] for t in g["terms"]])
    check("gwrite: ## Terms stays sorted by key",
          [t["key"] for t in g["terms"]] == sorted(t["key"] for t in g["terms"]))
    E.cmd_glossary_accept(root, "detection floor", "a second time")
    check("gwrite: accept is idempotent", len(E.load_glossary(root)["terms"]) == 2)
    E.cmd_glossary_accept(root, "detection-floors", "a hyphenated plural of the same term")
    check("gwrite: accept of a differently-keyed existing term is a no-op",
          len(E.load_glossary(root)["terms"]) == 2)
    check("gwrite: accept without a definition is refused",
          _raises(lambda: E.cmd_glossary_accept(root, "bare term", "")))

    E.cmd_glossary_decline(root, "attenuation")
    check("gwrite: decline appends to ## Not jargon",
          E.load_glossary(root)["declined"] == ["attenuation"])
    E.cmd_glossary_decline(root, "attenuation")
    check("gwrite: decline is idempotent", len(E.load_glossary(root)["declined"]) == 1)
    moved = E.cmd_glossary_decline(root, "detection floor")
    g = E.load_glossary(root)
    check("gwrite: decline of an accepted term moves it out of ## Terms",
          "detection floor" not in [t["term"] for t in g["terms"]]
          and "detection floor" in g["declined"])
    check("gwrite: the move is reported, not silent", moved.get("moved") is True)
    moved = E.cmd_glossary_accept(root, "detection floor", "back again.")
    g = E.load_glossary(root)
    check("gwrite: accept of a declined term moves it out of ## Not jargon",
          "detection floor" not in g["declined"]
          and "detection floor" in [t["term"] for t in g["terms"]])
    check("gwrite: that move is reported too", moved.get("moved") is True)

    # a hand-edited file is the PI's: the engine appends into sections, never rewrites
    with open(gp, "a", encoding="utf-8") as f:
        f.write("\n_a note the PI added by hand_\n")
    E.cmd_glossary_accept(root, "kernel trick", "the thing.")
    check("gwrite: a hand-written line survives a write", "_a note the PI added by hand_" in read(gp))
    check("gwrite: an existing definition is untouched by another accept",
          "the smallest effect this assay could resolve." in read(gp)
          or "back again." in read(gp))
    check("gwrite: vault validates clean after accept and decline", E.cmd_validate(root) == [])
    check("gwrite: the glossary is still not a node", len(E.Vault(root).nodes) == 1)

    lst = E.cmd_glossary_list(root)
    check("gwrite: list returns terms and declined", set(lst) == {"terms", "declined"})
    check("gwrite: list is the parsed file", lst == E.load_glossary(root))

    # the round trip: an accepted term stops being a candidate; a declined one stays gone
    q1, _ = E.cmd_ask(root, "q", body_text="the kernel trick is here")
    E.cmd_hypothesize(root, "h", parent=q1, problem="the kernel trick again", verifiables=["x"], expect="the claim holds")
    def surv(*t):
        return {c["term"] for c in E.validation_report(root, ["glossary"], propose=list(t))["candidates"]}
    check("gwrite: an accepted term is dropped by the filter afterwards", surv("kernel trick") == set())
    E.cmd_glossary_decline(root, "kernel trick")
    check("gwrite: a declined term is dropped by the filter afterwards", surv("kernel trick") == set())
    check("gwrite: a declined term stays dropped across case, hyphen and plural",
          surv("Kernel Trick") == set() and surv("kernel-trick") == set()
          and surv("kernel tricks") == set())

    # determinism
    root2 = tempfile.mkdtemp(prefix="crux_gw2_")
    shutil.rmtree(root2); os.makedirs(root2)
    E.cmd_init("Writing", root2)
    for r in (root, root2):
        pass
    E.cmd_glossary_accept(root2, "alpha term", "one.")
    E.cmd_glossary_decline(root2, "beta term")
    first = read(os.path.join(root2, E.GLOSSARY_FILE))
    root3 = tempfile.mkdtemp(prefix="crux_gw3_")
    shutil.rmtree(root3); os.makedirs(root3)
    E.cmd_init("Writing", root3)
    E.cmd_glossary_accept(root3, "alpha term", "one.")
    E.cmd_glossary_decline(root3, "beta term")
    check("gwrite: writing is deterministic", read(os.path.join(root3, E.GLOSSARY_FILE)) == first)

    # THE FIXED POINT. Rendering an already-rendered file must return the same bytes,
    # otherwise a no-op accept still dirties the vault and blank lines creep in on every
    # write — which is exactly what a patch-in-place renderer did before this was asserted.
    g = E.parse_glossary(first)
    once = E._render_glossary(first, g["terms"], g["declined"])
    twice = E._render_glossary(once, g["terms"], g["declined"])
    check("gwrite: the renderer is a fixed point", once == twice)
    check("gwrite: a no-op accept does not dirty the file", once == first)
    check("gwrite: the decline hint stays above its entries",
          first.index("_(checked") < first.index("- beta term"))
    check("gwrite: no blank-line run grows", "\n\n\n" not in first)
    shutil.rmtree(root2, ignore_errors=True); shutil.rmtree(root3, ignore_errors=True)

    # THE INVARIANT: no other verb writes glossary.md
    ghash = hashlib.sha256(read(gp).encode()).hexdigest()
    q2, _ = E.cmd_ask(root, "another question")
    h9, _, _ = E.cmd_hypothesize(root, "another idea", parent=q2, verifiables=["z"],
                                 neutral=["the control reproduces the known value"], expect="the claim holds")
    declare_null(root, h9)
    E.cmd_test(root, h9, to="running")
    edit(node_path(root, h9), "- [ ] z", "- [x] z")
    edit(node_path(root, h9), "- [ ] [outcome-neutral] the control reproduces the known value",
                              "- [x] [outcome-neutral] the control reproduces the known value")
    E.cmd_finding(root, h9, "strong", why="z held with the control reproduced",
                  direction="supports")
    E.cmd_park(root, h9); E.cmd_park(root, h9, undo=True)
    E.cmd_validate(root); E.snapshot(root); E.refresh(root)
    E.status_text(root)
    check("gwrite: no other verb writes glossary.md",
          hashlib.sha256(read(gp).encode()).hexdigest() == ghash)
    shutil.rmtree(root, ignore_errors=True)

    # ---- a pre-14 vault gains the file only when the PI actually says something
    root = tempfile.mkdtemp(prefix="crux_gwo_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Old", root)
    os.remove(os.path.join(root, E.GLOSSARY_FILE))
    check("gwrite: list on a pre-14 vault returns empty",
          E.cmd_glossary_list(root) == {"terms": [], "declined": []})
    check("gwrite: list on a pre-14 vault creates nothing",
          not os.path.exists(os.path.join(root, E.GLOSSARY_FILE)))
    E.cmd_glossary_accept(root, "first word", "the PI has spoken.")
    check("gwrite: accept creates glossary.md in a pre-14 vault",
          os.path.isfile(os.path.join(root, E.GLOSSARY_FILE)))
    check("gwrite: and the vault still validates", E.cmd_validate(root) == [])
    shutil.rmtree(root, ignore_errors=True)

    # ---- the CLI
    root = tempfile.mkdtemp(prefix="crux_gwc_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("CLI", root)
    def cli(*args):
        return subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + list(args),
                              capture_output=True, text=True, encoding="utf-8", cwd=root)
    r = cli("glossary", "accept", "detection floor", "-d", "the smallest resolvable effect.")
    check("gwrite: crux glossary accept works from the CLI", r.returncode == 0)
    r = cli("glossary", "list", "--json")
    check("gwrite: crux glossary list --json is machine-readable",
          json.loads(r.stdout)["terms"][0]["term"] == "detection floor")
    r = cli("glossary", "accept", "another term", "-d", "x", "--json")
    check("gwrite: accept --json emits the recorded entry",
          json.loads(r.stdout)["term"] == "another term")
    r = cli("glossary", "decline", "attenuation", "--json")
    check("gwrite: decline --json emits the recorded entry",
          json.loads(r.stdout)["term"] == "attenuation")
    r = cli("glossary", "accept", "no definition here")
    check("gwrite: the CLI refuses an accept with no definition", r.returncode == 1)
    shutil.rmtree(root, ignore_errors=True)

    # ---- the skill rule, and the leash
    skill = read(os.path.join(HERE, "..", "SKILL.md"))
    check("gwrite: SKILL.md carries the vocabulary rule",
          "glossary.md" in skill and "gloss" in skill.lower())
    check("gwrite: SKILL.md tells the agent never to write glossary.md directly",
          "never write to `glossary.md`" in skill.lower()
          or "never write to glossary.md" in skill.lower())
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    belts = []
    for name in sorted(os.listdir(os.path.join(repo, "agents"))):
        p = os.path.join(repo, "agents", name, "AGENT.md")
        if os.path.isfile(p):
            fm, _ = E.parse_doc(read(p))
            if "crux glossary" in str(fm.get("toolbelt") or ""):
                belts.append(name)
    check(f"gwrite: no agent's toolbelt holds the write verb (found: {belts})", not belts)

    # ---- the spec is flipped, with its work items ticked
    spec = read(os.path.join(repo, ".spec", "14-glossary.md"))
    check("gwrite: spec 14 is flipped to done", "**Status:** ☑" in spec)
    check("gwrite: spec 14's work items are ticked", spec.count("- ☑ ") >= 8)
    check("gwrite: spec 14 records that its counting guess was measured and refuted",
          "refuted" in spec.lower() and "hyphenation" in spec.lower())
    readme = read(os.path.join(repo, ".spec", "README.md"))
    check("gwrite: the backlog index shows 14 done",
          re.search(r"\|\s*14\s*\|[^|]*\|[^|]*\|\s*☑\s*\|", readme) is not None)


def _raises(fn):
    try:
        fn(); return False
    except E.CruxError:
        return True


def _tree_hashes(root):
    """{relpath: sha256} for every file under root — the byte-compare oracle."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(d for d in dirnames if d != "__pycache__")
        for fn in sorted(filenames):
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(f.read()).hexdigest()
    return out


def run_agent_evals():
    """Spec 10 PRD 10.0 — the fixture contract, and the certifier that keeps it honest.
    Re-pointed by spec 19: the reference fixture is capture-01, since audit-01's agent and its
    `--check=gate` are gone.

    Spec 10 is uncompromising about where ground truth may come from: *"the planted defects
    must be authored independently of the agent that finds them."* A hand-authored fixture
    drifts the moment someone edits the vault and forgets the manifest. So the ENGINE
    certifies it: `capture_keys` over the record before and after a reference capture must
    give exactly the planted id set. A human writes the manifest; a program with no knowledge
    of any agent says whether it is true."""
    print("\n# agent evals — the fixture contract (spec 10, PRD 10.0; capture-01, spec 19)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    F = os.path.join(V.FIXTURES, "capture-01")

    names = V.fixture_names()
    check(f"evals: the capture-01 fixture exists, with a transcript, a starting record and a "
          f"reference capture (found: {names})",
          "capture-01" in names and os.path.isfile(os.path.join(F, "transcript.txt"))
          and len(E.Vault(os.path.join(F, "vault")).nodes) >= 3
          and len(E.Vault(os.path.join(F, "reference")).nodes)
              > len(E.Vault(os.path.join(F, "vault")).nodes))
    retired = sorted(n for n in names if V.load_manifest(n)["agent"] in V.REMOVED_AGENTS)
    check(f"evals: no fixture grades an agent spec 19 removed (found: {retired})",
          not retired and not any(n in names for n in (
              "audit-01", "close-01", "critic-01", "design-01", "glossary-01", "null-01",
              "verifiables-01")))

    # -- the contract: seven fields, every one of them load-bearing somewhere below
    bad = []
    for n in names:
        try:
            m = V.load_manifest(n)
        except E.CruxError as e:
            bad.append(f"{n}: {e}"); continue
        if not all(m["fm"].get(k) not in (None, "") for k in V.MANIFEST_FIELDS):
            bad.append(f"{n}: missing a contract field")
    check(f"evals: a manifest declares the seven contract fields (bad: {bad[:2]})", not bad)

    # a fixture's `agent` resolves to a real definition — a roster agent, crux-tests under
    # evolve-crux, or (spec 16's persona eval) the orchestrating skill.
    ghosts = [n for n in names if V.definition_path(V.load_manifest(n)["agent"], repo) is None]
    check(f"evals: every fixture names a real definition (ghosts: {ghosts})", not ghosts)

    m = V.load_manifest("capture-01")
    r = V.certify("capture-01")
    check(f"evals: capture-01 certifies — the engine reads exactly what was planted "
          f"(missing {r['missing']}, extra {r['extra']}, cross {r['cross_failed']})", r["ok"])
    check("evals: capture-01 plants at least one question, one hypothesis with an "
          "expectation, and one finding with evidence",
          {"open:question", "open:hypothesis+expect", "finding:evidence"} <= m["planted_ids"])
    ref = E.Vault(os.path.join(F, "reference"))
    hyps = [n for i, n in ref.nodes.items() if n.type == "idea"
            and i not in E.Vault(os.path.join(F, "vault")).nodes]
    check("evals: ... and the engine agrees: the reference's new hypothesis states its "
          "expectation and its finding resolves",
          hyps and all(E.expect_text(h) for h in hyps)
          and all(E._evidence_problem(os.path.join(F, "reference"), x) is None
                  for f in ref.nodes.values() if f.type == "finding"
                  for x in E.finding_evidence(f)))

    # -- the ways a fixture rots, each proven on a COPY (the shipped tree is never touched)
    tmp = tempfile.mkdtemp(prefix="crux_evalfix_")
    try:
        def fresh():
            shutil.rmtree(os.path.join(tmp, "capture-01"), ignore_errors=True)
            shutil.copytree(F, os.path.join(tmp, "capture-01"))
            return os.path.join(tmp, "capture-01", "reference")
        refc = fresh()
        os.unlink(os.path.join(refc, "results", "light-trial", "heights.csv"))
        c = V.certify("capture-01", root=tmp)
        check(f"evals: a reference that drifts from its manifest fails certification "
              f"(missing {c['missing']})",
              not c["ok"] and "finding:evidence" in c["missing"])

        refc = fresh()
        E.cmd_ask(refc, "Does the watering schedule affect how tall seedlings get?",
                  parent="root")
        c = V.certify("capture-01", root=tmp)
        check(f"evals: an unplanted duplicate fails certification as extra (extra {c['extra']})",
              not c["ok"] and c["extra"] == ["duplicate:q1"])

        refc = fresh()
        E.cmd_hypothesize(refc, "Fix the timer on the lamp", parent="q2",
                          expect="the timer switches on time")
        c = V.certify("capture-01", root=tmp)
        check(f"evals: a node opened for work fails certification as extra (extra {c['extra']})",
              not c["ok"] and c["extra"] == ["work-in-tree"])

        fresh()
        edit(os.path.join(tmp, "capture-01", "transcript.txt"), "results/light-trial/heights.csv",
             "the spreadsheet")
        c = V.certify("capture-01", root=tmp)
        check("evals: a transcript that no longer names the evidence fails certification",
              not c["ok"] and c["cross_failed"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- one row per id is what buys exact scoring; load_manifest refuses a duplicate
    dupes = []
    for n in names:
        ids = [p["id"] for p in V.load_manifest(n)["planted"]]
        dupes += [f"{n}:{i}" for i in set(ids) if ids.count(i) > 1]
    check(f"evals: at most one planted row per id (dupes: {dupes})", not dupes)

    before = _tree_hashes(V.FIXTURES)
    for n in names:
        try:
            V.certify(n)
        except Exception:
            pass
    check("evals: certification is read-only", _tree_hashes(V.FIXTURES) == before)

    check(f"evals: the fixture contract did not bump the engine (spec 10 landed at 3.1; "
          f"now {E.ENGINE_VERSION})", at_least_version("3.1"))

    # -- gate 3 of the evolve-crux gate walks examples/ and asks "did anything break". The
    #    fixtures are kept outside it, so a planted trap never reads as a broken example.
    ex = os.path.join(HERE, "..", "examples")
    check("evals: the fixture tree is outside the example-vault gate",
          not os.path.isdir(os.path.join(ex, "capture-01"))
          and os.path.abspath(V.FIXTURES) != os.path.abspath(ex)
          and "evals/fixtures" in read(os.path.join(ex, "README.md")))


def run_eval_scorer():
    """Spec 10 PRD 10.1 — precision and recall, banded over K runs, with no model call.
    Re-pointed by spec 19 to capture-01's submissions.

    THE STRUCTURAL DECISION: the scorer reads a SUBMITTED findings file and never invokes an
    agent. A program that launches an agent K times, decides when to stop and caps what it
    spends is spec 05's unbuilt work pointed at a fixture. That is not a promise here; it is
    the assert below that reads evals.py's own source."""
    print("\n# agent evals — the scorer (spec 10, PRD 10.1)")
    import evals as V
    SUB = os.path.join(V.FIXTURES, "capture-01", "submissions")
    m = V.load_manifest("capture-01")

    def sc(name, mf=m):
        return V.score(mf, V.load_submission(os.path.join(SUB, name)))

    s = sc("perfect.json")
    check("evals: a perfect submission scores 1.0 / 1.0, and its hard checks pass",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] == 1.0
          and s["hard"] and all(ok for _n, ok, _w in s["hard"]))

    s = sc("noisy.json")
    check(f"evals: invented records cost precision, not recall "
          f"(r={s['recall']['min']:.2f} p={s['precision']['min']:.2f})",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] < 1.0
          and s["runs"][0]["fp"] == ["duplicate:q1", "work-in-tree"])

    s = sc("partial.json")
    check(f"evals: missed records cost recall, not precision "
          f"(r={s['recall']['min']:.2f} p={s['precision']['min']:.2f})",
          s["recall"]["min"] < 1.0 and s["precision"]["min"] == 1.0
          and s["runs"][0]["fn"] == ["finding:null-open", "parked:h1"])

    # the vacuous-truth trap: |tp|/|reported| is 0/0 for an empty report
    s = sc("silent.json")
    check("evals: reporting nothing scores zero precision",
          s["precision"]["min"] == 0.0 and s["recall"]["min"] == 0.0)

    # the two rules capture rests on are one bit each, beside the band
    s = sc("asks-pi.json")
    check("evals: a capture that asked the PI fails, whatever its recall and precision",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] == 1.0
          and s["verdict"] == V.FAIL
          and [n for n, ok, _w in s["hard"] if not ok][0].startswith("the capture asked"))
    s = sc("id-led.json")
    check("evals: a capture that wrote node ids or crux words into the record fails",
          s["recall"]["min"] == 1.0 and s["verdict"] == V.FAIL
          and any(n.startswith("the captured prose") and not ok for n, ok, _w in s["hard"]))

    # -- the band is the WORST run. Proven on a COPY with a band written in, because every
    #    shipped fixture ships `band: unset` and the numbers are the PI's.
    tmp = tempfile.mkdtemp(prefix="crux_evalband_")
    try:
        shutil.copytree(os.path.join(V.FIXTURES, "capture-01"), os.path.join(tmp, "capture-01"))
        edit(os.path.join(tmp, "capture-01", "PLANTED.md"),
             "band: unset", "band: recall>=0.9, precision>=0.9")
        banded = V.load_manifest("capture-01", root=tmp)
        ids = sorted(banded["planted_ids"])
        sha = V.agent_sha("crux-capture")
        # nine perfect runs and one that misses two. The MEAN clears 0.9; the WORST does not.
        nine_good_one_bad = {"fixture": "capture-01", "agent": "crux-capture", "agent_sha": sha,
                             "runs": [{"findings": ids}] * 9 + [{"findings": ids[:4]}]}
        s = V.score(banded, nine_good_one_bad)
        mean_r = sum(r["recall"] for r in s["runs"]) / len(s["runs"])
        check(f"evals: the band is the worst run, not the average "
              f"(min {s['recall']['min']:.2f} vs mean {mean_r:.2f})",
              s["verdict"] == V.FAIL and mean_r >= 0.9 and s["recall"]["min"] < 0.9)
        check("evals: a band states both recall and precision, never recall alone",
              _raises(lambda: V.parse_band("recall>=0.8")))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    s = sc("short.json")
    check(f"evals: a short submission is refused, not graded ({s['verdict']})",
          s["verdict"] == V.REFUSED and "UNDER-K" in s["refusal"])

    s = sc("perfect.json")
    check("evals: an unset band is ungraded, never a pass",
          m["band"] == V.BAND_UNSET and V.parse_band(m["band"]) is None
          and s["verdict"] == V.UNGRADED and s["verdict"] != V.PASS)

    s = sc("stale-sha.json")
    check("evals: a submission is pinned to the definition that produced it",
          s["verdict"] == V.REFUSED and "different definition" in s["refusal"])

    # -- THE LEASH, read off this module's own source rather than believed. Read as an AST,
    #    not as text: the module's own prose SAYS "there is no --spawn".
    import ast
    tree = ast.parse(read(os.path.join(HERE, "evals.py")))
    BANNED = {"urllib", "http", "socket", "requests", "ssl", "ftplib", "telnetlib",
              "anthropic", "openai", "subprocess", "importlib", "ctypes"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported |= {a.name.split(".")[0] for a in node.names}
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    called = {n.func.id for n in ast.walk(tree)
              if isinstance(n, ast.Call) and isinstance(n.func, ast.Name)}
    leaks = sorted((imported & BANNED) | (called & {"eval", "exec", "compile", "__import__"}))
    check(f"evals: the harness cannot invoke a model or reach the network (leaks: {leaks})",
          not leaks)

    # -- spec 10: "Label the proxies as proxies". A label with a code path that drops it is
    #    not a label.
    proxy_m = dict(m, ground_truth="proxy")
    txt = V.format_score(V.score(proxy_m, V.load_submission(os.path.join(SUB, "perfect.json"))))
    check("evals: a proxy can never print as ground truth",
          "[proxy]" in txt and "[ground truth]" not in txt
          and "[ground truth]" in V.format_score(sc("perfect.json")))

    before = _tree_hashes(V.FIXTURES)
    a, b = sc("perfect.json"), sc("perfect.json")
    check("evals: scoring is deterministic and read-only",
          json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)
          and _tree_hashes(V.FIXTURES) == before)

    r = subprocess.run([sys.executable, os.path.join(HERE, "evals.py"), "--certify-all"],
                       capture_output=True, text=True, encoding="utf-8")
    check(f"evals: every shipped fixture certifies (rc={r.returncode})", r.returncode == 0)

    def rc(sub):
        return subprocess.run([sys.executable, os.path.join(HERE, "evals.py"),
                               "--fixture", "capture-01", "--submission", os.path.join(SUB, sub)],
                              capture_output=True, text=True, encoding="utf-8").returncode
    check("evals: the runner is exit-coded",
          rc("perfect.json") == 0 and rc("short.json") == 1 and rc("stale-sha.json") == 1)

    # -- the submitter's helper: a run's entry is computed from the record, never hand-typed
    y = subprocess.run([sys.executable, os.path.join(HERE, "evals.py"), "--fixture",
                        "capture-01", "--yield",
                        os.path.join(V.FIXTURES, "capture-01", "reference")],
                       capture_output=True, text=True, encoding="utf-8")
    got = json.loads(y.stdout) if y.returncode == 0 else {}
    check("evals: `--yield` turns a captured record into a run entry the scorer accepts",
          set(got.get("findings") or ()) == m["planted_ids"]
          and got.get("prose") and E.voice_lint([("agent", t) for t in got["prose"]]) == [])

    check(f"evals: the scorer did not bump the engine (spec 10 landed at 3.1; now "
          f"{E.ENGINE_VERSION})", at_least_version("3.1"))


def run_mutation_harness():
    """Spec 10 PRD 10.2 — prove the suite can actually detect a regression, over spec 19's
    roster.

    A degraded DEFINITION can be degraded in code: zero model calls. Every property the
    roster suites print is broken on purpose here, and each mutation NAMES the property it
    must break before it is run — the mutations are hand-written and independent of the
    definitions, which is what keeps this from being circular."""
    print("\n# agent evals — the mutation harness (spec 10, PRD 10.2)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    expected = list(V.ROSTER)
    defs = V.load_definitions(expected, repo)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    verbs = r.stdout

    res = V.mutation_results(defs, verbs)
    by = {m["mutation"]: m for m in res}

    misses = sorted(m["mutation"] for m in res if not m["hit"])
    check(f"evals: every mutation breaks the property it targets (missed: {misses})", not misses)

    absorbed = sorted(m["mutation"] for m in res if not m["broke"])
    check(f"evals: no mutation is absorbed without a failure (absorbed: {absorbed})", not absorbed)

    check("evals: giving crux-capture a run verb breaks the leash check",
          by["capture-starts-run"]["broke"] == ["leash"])
    check("evals: giving crux-capture a third tool breaks its tools check",
          by["capture-gains-tool"]["broke"] == ["capture-tools"])
    check("evals: the never-ask-the-PI rule has a demonstrated failure mode",
          by["capture-asks-pi"]["broke"] == ["capture-silent"])
    check("evals: a write verb on crux-prerun breaks the writers check",
          "writers" in by["prerun-gains-write"]["broke"])
    check("evals: pinning an engine version in a definition is still caught",
          by["pin-engine-version"]["broke"] == ["no-version-pin"])

    # the shipped roster is clean, and every property is one the roster suites print
    P = V.roster_properties(defs, verbs)
    red = sorted(k for k, (_n, ok) in P.items() if not ok)
    printed = set(_PASS) | set(_FAIL)
    unprinted = sorted(n for _s, (n, _ok) in P.items() if n not in printed)
    check(f"evals: the shipped roster is clean and every property is printed "
          f"(red: {red}, unprinted: {unprinted})", not red and not unprinted)

    targeted = {t for _a, t in V.MUTATIONS.values()}
    shared = {"belt-verbs", "leash", "writers", "no-version-pin"}
    untested = sorted(k for k in P if k not in targeted
                      and not k.split(":")[0] in ("fields", "dirname", "workflow", "trigger")
                      and k not in shared
                      and k not in ("capture-belt", "prerun-proposal", "situate-ephemeral",
                                    "situate-lints", "situate-shape"))
    check(f"evals: every agent-specific rule spec 19 added has a mutation (untested: {untested})",
          not untested)

    before = _tree_hashes(os.path.join(repo, "agents"))
    V.mutation_results(defs, verbs)
    check("evals: mutation is in-memory only", _tree_hashes(os.path.join(repo, "agents")) == before)

    covered = {m["agent"] for m in res}
    check(f"evals: every agent has at least one mutation covering it "
          f"(uncovered: {sorted(set(expected) - covered)})", covered == set(expected))

    check(f"evals: the mutation harness did not bump the engine (spec 10 landed at 3.1; "
          f"now {E.ENGINE_VERSION})", at_least_version("3.1"))


def run_ground_truth_fixtures():
    """Spec 10 PRD 10.3 — the fixtures whose answer the engine already holds. Spec 19 retired
    close-01 with crux-close, retargeted null-01 to crux-prerun as prerun-01, and added
    capture-01.

    So: capture-01 against `capture_keys`, prerun-01 against the closed confound vocabulary,
    situate-01 against the situate payload and its lint. No oracle invents its answer."""
    print("\n# agent evals — the ground-truth fixtures (spec 10, PRD 10.3)")
    import evals as V

    def sub(fix, name):
        return V.load_submission(os.path.join(V.FIXTURES, fix, "submissions", name))

    def sc(fix, name):
        return V.score(V.load_manifest(fix), sub(fix, name))

    three = ("capture-01", "prerun-01", "situate-01")
    certs = {}
    for n in three:
        try:
            certs[n] = V.certify(n)
        except Exception as e:
            certs[n] = {"ok": False, "error": f"{type(e).__name__}: {e}"}
    check(f"evals: the three ground-truth fixtures certify "
          f"({[(n, certs[n]['ok'], certs[n].get('error', '')) for n in three]})",
          all(certs[n]["ok"] for n in three))

    # ---- capture-01: the closure judgment is the engine's own reading
    m = V.load_manifest("capture-01")
    ref = os.path.join(m["dir"], "reference")
    rv = E.Vault(ref)
    fs = [n for n in rv.nodes.values() if n.type == "finding"]
    check("evals: capture-01's finding supports its hypothesis, with the null not ruled out, "
          "so the engine caps it at weak",
          fs and all(f["fm"].get("direction") == "supports"
                     and f["fm"].get("null") == E.NULL_NOT_RULED_OUT
                     and E.effective_confidence(f) == "weak" for f in fs))
    check("evals: capture-01's parked node is parked in the engine's derived state",
          E.derive_state(rv, "h1")["state"] == "parked"
          and E.derive_state(E.Vault(V.vault_of(m)), "h1")["state"] == "open")
    s = sc("capture-01", "overconfident.json")
    check(f"evals: ignoring the null costs capture-01 both recall and precision "
          f"(r={s['recall']['min']:.2f} p={s['precision']['min']:.2f})",
          s["recall"]["min"] < 1.0 and s["precision"]["min"] < 1.0
          and "finding:strong" in s["runs"][0]["fp"])

    # ---- prerun-01 (was null-01)
    m = V.load_manifest("prerun-01")
    check(f"evals: prerun-01 plants a family from the closed vocabulary ({m['planted_ids']})",
          m["planted_ids"] <= set(E.CONFOUND_FAMILIES) and len(m["planted_ids"]) == 1
          and m["agent"] == "crux-prerun")
    n = E.Vault(V.vault_of(m)).get(str(m["fm"]["node"]))
    check("evals: prerun-01's reference null passes the engine's own null check",
          E.null_problem(str(m["fm"]["reference_null"]), E.node_schema(n)) is None
          and not (E._null_text(n) or "").strip())

    brief = json.dumps(E.brief(V.vault_of(m), str(m["fm"]["node"])))
    check("evals: prerun-01's setup reaches the agent through the brief, and the argument "
          "for the claim does not",
          all(x in brief for x in ("84M", "121M", "10 seeds", "normalisation"))
          and "ARGUMENT-FOR-THE-CLAIM" not in brief
          and "ARGUMENT-FOR-THE-CLAIM" in read(n["path"]))
    s = sc("prerun-01", "decoy.json")
    check(f"evals: prerun-01's decoy family scores zero recall (r={s['recall']['min']})",
          str(m["fm"]["decoy"]) in E.CONFOUND_FAMILIES and s["recall"]["min"] == 0.0)
    s = sc("prerun-01", "everything.json")
    check(f"evals: naming every family is recall 1.0 and precision {s['precision']['min']:.2f}",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] < 0.2)

    # ---- situate-01. Its payload is C6's (spec 19 renames verdict and synthesis), so a
    #      broken payload reads here as a certification failure above, not as a crash.
    m = V.load_manifest("situate-01")
    anchor = str(m["fm"]["node"])
    ref = V._section(m["body"], "Reference answer")
    check("evals: situate-01's reference answer lints clean",
          ref.strip() and E.situate_lint(ref, [V.situate_anchor(m)]) == [])
    check("evals: situate-01's reference answer carries no node id and no crux vocabulary",
          E.voice_lint([("agent", ref)]) == [])
    check("evals: ... and it is the TITLE doing the anchoring, not an id left in the prose",
          [i for i, _m in E.situate_lint(ref, [anchor])] == ["situate:unanchored"])
    if certs["situate-01"]["ok"]:
        s = sc("situate-01", "invented.json")
        check(f"evals: inventing a finding costs situate-01 precision (p={s['precision']['min']:.2f})",
              s["precision"]["min"] < 1.0 and s["recall"]["min"] < 1.0)
        s = sc("situate-01", "verbose.json")
        check("evals: a verbose situate answer fails on the lint, whatever its recall",
              s["recall"]["min"] == 1.0 and s["verdict"] == V.FAIL
              and any(not ok for _n, ok, _w in s["hard"]))

    # ---- the two properties that hold across every fixture in the epic
    ms = [V.load_manifest(n) for n in V.fixture_names()]
    check("evals: the ground-truth fixtures declare their status and leave the band to the PI",
          all(V.load_manifest(n)["ground_truth"] == "yes"
              and V.load_manifest(n)["band"] == V.BAND_UNSET for n in three))
    banned = ("stale", "outdated", "no longer reflect", "wrong answer", "should be reopened")
    smell = [f"{m['name']}:{p['id']}" for m in ms for p in m["planted"]
             if any(b in (p["class"] + " " + p["note"]).lower() for b in banned)]
    check(f"evals: every planted row is structural, never a research judgment ({smell})",
          not smell)

    check(f"evals: the ground-truth fixtures did not bump the engine (spec 10 landed at "
          f"3.1; now {E.ENGINE_VERSION})", at_least_version("3.1"))


def run_proxy_register():
    """Spec 10 PRD 10.4 — the proxies, the register, and the gate ruling. Spec 19 retired the
    critic, design, glossary and verifiables proxies with their agents; migrate-01 and
    tests-01 remain, and persona-01 is checked in its own suite.

    `[proxy]` alone tells a reader the eval is weaker; the register says IN WHICH DIRECTION,
    which is what they need in order to distrust the right number."""
    print("\n# agent evals — the proxies, the register, and the gate (spec 10, PRD 10.4)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    spec = read(os.path.join(repo, ".spec", "10-agent-evals.md"))

    proxies = ("migrate-01", "tests-01")
    certs = {c["fixture"]: c for c in (V.certify(n) for n in proxies)}
    bad = [n for n in proxies if not certs.get(n, {}).get("ok")]
    check(f"evals: the two proxy fixtures certify (failed: {bad})", not bad)
    check("evals: every proxy fixture is declared a proxy, and no ground-truth fixture is",
          all(V.load_manifest(n)["ground_truth"] == "proxy" for n in proxies)
          and sorted(n for n in V.fixture_names()
                     if V.load_manifest(n)["ground_truth"] == "proxy")
              == sorted(proxies + ("persona-01",)))

    roster = sorted(V.ROSTER)
    covered = {V.load_manifest(n)["agent"] for n in V.fixture_names()}
    check(f"evals: every agent in the roster has a fixture "
          f"(uncovered: {sorted(set(roster) - covered)})",
          set(roster) <= covered and len(roster) == 4)
    check(f"evals: and a fixture outside the roster grades a definition that exists "
          f"({sorted(covered - set(roster))})",
          all(V.definition_path(a, repo) for a in covered - set(roster)))

    # -- the register, parsed out of spec 10. Spec 19 retired rows without editing spec 10;
    #    what must still hold is that no SHIPPED fixture disagrees with its register row.
    rows = {r[0].strip("`"): r for r in V._table(spec, "The proxy register")}
    REG_TRUTH = {"**yes**": "yes", "proxy": "proxy"}
    mismatch = [n for n in V.fixture_names() if n in rows
                and REG_TRUTH.get(rows[n][2]) != V.load_manifest(n)["ground_truth"]]
    check(f"evals: no shipped fixture can be promoted by editing one side ({mismatch})",
          not mismatch and all(n in rows for n in proxies))

    check("evals: crux-tests is a proxy until code execution is unparked",
          V.load_manifest("tests-01")["ground_truth"] == "proxy"
          and "P2" in spec and "demoted" in spec.lower())

    silent = [n for n in proxies if not rows[n][4].strip(" —")]
    check(f"evals: every proxy says what it fails to measure ({silent})", not silent)

    m = V.load_manifest("tests-01")
    wrong = [w for w in V._csv(m["fm"]["wrong_values"]) if w]
    clash = sorted(w for p in m["planted"] for w in wrong if w in p["note"])
    check(f"evals: tests-01's key cannot be satisfied by describing the broken code ({clash})",
          wrong and not clash)
    check("evals: tests-01 grades crux-tests where it now lives, with evolve-crux",
          V.definition_path("crux-tests", repo)
          == os.path.join(repo, "skills", "evolve-crux", "agents", "crux-tests.md"))

    m = V.load_manifest("migrate-01")
    check("evals: migrate-01 grades the 4.0 seed — its key names the finding a missed bar becomes",
          "against" in " ".join(p["note"] for p in m["planted"]))

    # -- the gate ruling (D6), where it binds and where it is written down
    src = read(os.path.join(HERE, "selftest.py"))
    check("evals: the deterministic eval suite runs in the gate",
          all(f"    {fn}()" in src or f"            {fn}," in src
              for fn in ("run_agent_evals", "run_eval_scorer", "run_mutation_harness",
                         "run_ground_truth_fixtures", "run_proxy_register")))
    skill = read(os.path.join(repo, "skills", "evolve-crux", "SKILL.md"))
    check("evals: the gate contract is written down where contributors read it",
          "agent evals" in skill and "never gates" in skill and "no API key" in skill)

    # -- D7. The mechanism ships; the numbers are the PI's, and the gap is on the record.
    unset = all(V.load_manifest(n)["band"] == V.BAND_UNSET for n in V.fixture_names())
    check("evals: no band was invented, and the gap is recorded",
          unset and "Pass bands" in spec and "still open" in spec
          and "☐ **a stated pass band**" in spec)

    check("evals: spec 10 records what it parked rather than dropping it",
          "PARKED" in spec and "P1" in spec and "do not implement 05" in spec.lower()
          and "--spawn" in spec)

    check(f"evals: spec 10 was a zero-bump epic — it landed at 3.1 and the stamp only moved "
          f"later (now {E.ENGINE_VERSION})", at_least_version("3.1"))


def run_correct_terms():
    """2026-10-29, the PI's ruling: the correct technical term, glossed in at most ten words
    the first time it appears — never a homemade paraphrase in its place. PR #56 wrote the
    rule as prose ("a science-major undergraduate's register") and prezit's paper arc drifted
    anyway: "within noise", "rules locked", "Doubts". So the swaps crux actually shipped are a
    closed table, and three consumers read it: the chat-time voice lint, `crux deck --lint`,
    and the sweep over shipped text below. Whether a gloss is PRESENT is not decidable by a
    script and stays a rule; whether a known paraphrase stands IN PLACE of its term is."""
    print("\n# correct terms — the paraphrase table (voice lint, deck lint, shipped text)")
    P = getattr(E, "PARAPHRASES", None)
    check("terms: the engine ships a non-empty paraphrase table", bool(P))
    if not P:
        return
    flagged = [
        ("The boring explanation is that the encoder is larger.", "null hypothesis"),
        ("The rules were locked before the first run.", "pre-registration"),
        ("The gap on the harder task is within noise.", "statistically significant"),
        ("Every gap goes through the noise rule.", "significance criterion"),
        ("The seed spread is wider on the harder task.", "standard deviation"),
        ("The error bar shows the spread over seeds.", "standard deviation"),
        ("One lucky split would show this on its own.", "sampling variability"),
    ]
    miss = [s for s, term in flagged
            if not any(term in t for _p, t in E.paraphrases_in(s))]
    check(f"terms: each shipped paraphrase is caught and named by its technical term ({miss})",
          not miss)
    glossed = [
        "The null hypothesis (the boring explanation) is that the encoder is larger.",
        "Results were pre-registered: the rules were locked before the first run.",
        "The gap is not statistically significant, so it is within noise.",
        "The standard deviation across seeds (the spread over seeds) is 0.4 points.",
        "Under chance, one lucky split would show this on its own.",
    ]
    check("terms: a paraphrase in the same sentence as its term is the gloss, and passes",
          not any(E.paraphrases_in(s) for s in glossed))
    clean = [
        "The null hypothesis is that seed noise alone explains the gain.",
        "The error bars show one standard deviation across three seeds.",
        "We locked the vault file before the run.",
        "Spread the runs over three GPUs.",
        "The noise floor of the timer is one microsecond.",
    ]
    check("terms: the correct terms, and near-misses that are not paraphrases, are clean",
          not any(E.paraphrases_in(s) for s in clean))
    check("terms: the term must be in the SAME sentence — a gloss two sentences away is no gloss",
          bool(E.paraphrases_in("The null hypothesis is capacity. The boring explanation is "
                                "that the encoder is larger.")))

    # ---- consumer 1: the chat-time voice lint
    v = E.voice_lint([("agent", flagged[0][0])])
    check("terms: voice_lint reports a paraphrase as voice:paraphrase, naming the term",
          [i for i, _m in v] == ["voice:paraphrase"] and "null hypothesis" in v[0][1])
    check("terms: ... and the PI saying the paraphrase first does NOT license it — the mirror "
          "rule is for crux's words, not for science",
          [i for i, _m in E.voice_lint([("pi", "is it the boring explanation?"),
                                        ("agent", flagged[0][0])])] == ["voice:paraphrase"])
    check("terms: ... and leafing through the notebook does not license it either",
          [i for i, _m in E.voice_lint([("pi", "open the vault"),
                                        ("agent", flagged[1][0])])] == ["voice:paraphrase"])
    check("terms: ... report_from scopes the report exactly as it does for ids",
          E.voice_lint([("agent", flagged[0][0]), ("pi", "ok"), ("agent", "Fine.")],
                       report_from=3) == [])
    check("terms: ... and the glossed form is clean in chat",
          E.voice_lint([("agent", glossed[0])]) == [])
    tmp = tempfile.mkdtemp(prefix="crux_terms_")
    tp = os.path.join(tmp, "t.jsonl")
    with open(tp, "w", encoding="utf-8") as fh:
        for kind, text in (("user", "did the extra data help?"),
                           ("assistant", "Yes, but the gap is within noise.")):
            fh.write(json.dumps({"type": kind, "message": {"role": kind, "content": [
                {"type": "text", "text": text}]}}) + "\n")
    ctx = E.hook_report({"tool_input": {"command": "crux status"}, "transcript_path": tp,
                         "cwd": tmp}) or ""
    check("terms: the chat-time hook reports a paraphrase and says to gloss the term",
          "voice:paraphrase" in ctx and "statistically significant" in ctx and "gloss" in ctx)

    # ---- consumer 2: `crux deck --lint`
    def slide(body, notes="<p>n</p>"):
        p = os.path.join(tmp, "d%d.html" % len(os.listdir(tmp)))
        write(p, "<!-- job j\n source s\n numbers n\n cut c -->\n"
                 '<section class="slide">' + body + '<aside class="notes">' + notes
                 + "</aside></section>")
        return E.deck_lint(p)
    check("terms: deck lint flags a paraphrase on the slide, naming the term",
          any("pre-registration" in m for _, m in slide("<p>Rules locked up front.</p>")))
    check("terms: ... and in the speaker notes",
          any("standard deviation" in m
              for _, m in slide("<p>x</p>", "<p>The bar is the seed spread.</p>")))
    check("terms: ... but not inside an HTML comment, and not when glossed",
          slide("<!-- the rules locked up front --><p>x</p>") == []
          and slide("<p>" + glossed[2] + "</p>") == [])

    # ---- consumer 3: nothing crux ships for a reader says a paraphrase in place of its term.
    #      Excluded, deliberately: history (CHANGELOG, .spec, docs/prd), code (comments are
    #      not read by the PI), eval fixtures (frozen vault snapshots), sortlab_vault, a
    #      high-school student's notebook the PI ruled stays in its own voice.
    repo = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
    def shipped():
        for top in ("agents", "skills"):
            for dp, dns, fns in os.walk(os.path.join(repo, top)):
                rel = os.path.relpath(dp, repo).replace(os.sep, "/")
                dns[:] = sorted(d for d in dns if not (
                    rel + "/" + d).endswith(("evals/fixtures", "examples/sortlab_vault", "vendor")))
                for fn in sorted(fns):
                    if fn.endswith((".md", ".html")) or fn == "app.js":
                        yield os.path.join(dp, fn)
        for fn in ("README.md", "AGENTS.md"):
            yield os.path.join(repo, fn)
    # the engine's own templates, as a fresh vault receives them
    fv = tempfile.mkdtemp(prefix="crux_terms_v_")
    shutil.rmtree(fv)
    E.cmd_init("Terms", fv, goal="Check the templates.")
    fq, _ = E.cmd_ask(fv, "a question")
    E.cmd_hypothesize(fv, "a claim", parent=fq, rule="all", verifiables=["a check"],
                      neutral=["a control"], expect="the check clears")
    files = list(shipped()) + [os.path.join(dp, f) for dp, _d, fs in os.walk(fv)
                               for f in fs if f.endswith(".md")]
    hits = [f"{os.path.relpath(f, repo)}: {p!r}" for f in files
            for p, _t in E.paraphrases_in(re.sub(r"<!--.*?-->", " ", read(f), flags=re.S)
                                          if f.endswith(".html") else read(f))]
    check(f"terms: no shipped PI-facing text uses a paraphrase in place of its term — "
          f"{len(files)} files ({hits[:4]})", len(files) > 50 and not hits)

    # ---- the rule, where agents read it
    surfaces = {"crux SKILL.md": os.path.join(repo, "skills", "crux", "SKILL.md"),
                "prezit SKILL.md": os.path.join(repo, "skills", "prezit", "SKILL.md"),
                "paper-arc.md": os.path.join(repo, "skills", "prezit", "references", "paper-arc.md"),
                "crux-situate": os.path.join(repo, "agents", "crux-situate", "AGENT.md")}
    gaps = [k for k, p in surfaces.items()
            if not re.search(r"first use", read(p)) or not re.search(r"10 words|ten words", read(p))]
    check(f"terms: every rule surface states the gloss-on-first-use rule and its 10-word cap ({gaps})",
          not gaps)
    old_ph = ("_(one sentence a science undergraduate follows — standard terms, subfield jargon "
              "glossed)_")
    new_ph = E._section_placeholder("ELI5")
    tpl = os.path.join(HERE, "templates")
    check("terms: the ELI5 placeholder asks for glossed terms, and both templates carry it",
          new_ph != old_ph and "gloss" in new_ph and "10 words" in new_ph
          and all(new_ph in read(os.path.join(tpl, t)) for t in ("idea.md", "question.md")))
    check("terms: ... and the new placeholder and the old one both still read as unwritten",
          E._summary(f"## ELI5\n{new_ph}\n\n## TL;DR\nx\n", "ELI5") == ""
          and E._summary(f"## ELI5\n{old_ph}\n\n## TL;DR\nx\n", "ELI5") == "")
    sk = read(surfaces["crux SKILL.md"]).replace("\r\n", "\n").encode("utf-8")
    check(f"terms: crux SKILL.md, the always-on core, stays within its 8,192-byte cap "
          f"({len(sk)} bytes)", len(sk) <= 8192)


def run_science_voice():
    """Spec 16 PRD 16.1 — the mirror rule as code, and the two measurements behind it.

    Spec 16's frame: the PI is the advisor, the agent is the grad student, crux is the grad
    student's notebook. A grad student does not tell their advisor "q19 is solved" — the
    advisor would ask what the hell q19 is. So node ids and crux's own process vocabulary
    reach the PI only when the PI brought them there.

    Everything here is deterministic. Spec 16 is explicit that the scan comes FIRST and the
    judge only afterwards, for the reason spec 10 gives about proxies: a regexable property
    graded by a model is a property that silently stops being checked."""
    print("\n# science voice — the mirror rule, measured (spec 16, PRD 16.1)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

    # ---- the id pattern, and why it is case-SENSITIVE. Spec 16 flagged the false-positive
    #      risk by name ("t5" the model); the answer is measured, two asserts down.
    hit = lambda s: bool(E.NODE_ID_RE.search(s))
    check("voice: the id pattern matches every node-id family",
          all(hit(x) for x in ("q19", "h72", "t91", "s1")) and hit("what about q19?"))
    check("voice: ... and never the uppercase strings that are science, not ids",
          not any(hit(x) for x in ("T5", "H1", "Q2", "S1", "H2O", "Q10 of the survey")))
    check("voice: ... and never a bare letter, a bare number, or a fragment of a word",
          not any(hit(x) for x in ("h", "19", "hq1x", "sha1sum", "epoch5", "top5")))

    # ---- THE MEASUREMENT. Spec 14 settled its matcher against the shipped example vaults
    #      rather than by argument; spec 16 asks for the same pass, and this is it, run every
    #      time rather than quoted from a build-day notebook.
    ex = os.path.join(HERE, "..", "examples")
    fp, scanned, matches = [], 0, 0
    for name in sorted(os.listdir(ex)):
        vroot = os.path.join(ex, name)
        if not os.path.isfile(os.path.join(vroot, E.VAULT_MARKER)):
            continue
        scanned += 1
        real = set(E.Vault(vroot).nodes) | {t["id"] for t in E.scan_tasks(vroot)}
        for dp, _d, fs in os.walk(vroot):
            for f in sorted(fs):
                if not f.endswith((".md", ".txt")):
                    continue
                for m in E.NODE_ID_RE.findall(read(os.path.join(dp, f))):
                    matches += 1
                    if m not in real:
                        fp.append(f"{name}/{f}: {m}")
    check(f"voice: measured over {scanned} shipped example vaults, every one of {matches} "
          f"id-pattern matches is a real node or task id ({fp[:3]})",
          scanned >= 3 and matches > 1000 and not fp)

    # ---- the lexicon. Where it lives is spec 16's own default: a frozenset beside 14's
    #      stoplist, so there is one list rather than one per consumer.
    check("voice: the lexicon carries crux's own process vocabulary",
          all(E.is_crux_term(t) for t in
              ("verifiable", "verifiables", "review gate", "synthesis", "verdict", "taskhub",
               "vault", "node", "cockpit", "roll-up", "outcome-neutral", "invalid-run",
               "situate", "ledger", "glossary", "RD", "seed file", "META.md")))
    check("voice: standard science words are free — a grad student owes no gloss for 'hypothesis'",
          not any(E.is_crux_term(t) for t in
                  ("question", "hypothesis", "evidence", "finding", "experiment", "check",
                   "result", "supported", "refuted", "inconclusive", "baseline",
                   "null", "null hypothesis", "confound", "control")))
    check("voice: 'null hypothesis' in chat is science, not a leak — the register is a science "
          "undergraduate's, so the standard term must never be what the lint pushes against",
          E.voice_lint([("agent", "The null hypothesis is that seed noise alone explains "
                                  "the gain.")]) == [])
    check("voice: and the words measured to collide with real science prose stay out",
          not any(E.is_crux_term(t) for t in
                  ("seed", "partial", "anchor", "idea", "brief", "pursue", "parent")))
    check("voice: membership is normalised, so hyphenation and plurals cannot smuggle a term "
          "past the list",
          E.is_crux_term("Roll-Up") and E.is_crux_term("roll up") and E.is_crux_term("nodes")
          and E.is_crux_term("Outcome-Neutral"))

    # ---- the mirror rule itself
    pi, ag = "pi", "agent"
    def ids_of(turns, agreed=()):
        return sorted(i for i, _m in E.voice_lint(turns, agreed))

    clean = [(pi, "did the extra data actually help?"),
             (ag, "yes — the accuracy gain held in all three repeat runs, so I think that "
                  "one is settled. Do you buy it?"),
             (pi, "yes")]
    check("voice: a conversation that speaks only science lints clean", ids_of(clean) == [])

    leaks = [(pi, "did the extra data actually help?"),
             (ag, "h1 came back supported, and there is a synthesis waiting on your approval "
                  "at the review gate.")]
    check("voice: an unlicensed node id is a finding",
          "voice:node-id" in ids_of(leaks))
    check("voice: an unlicensed crux term is a finding, and every leaked term is reported, "
          "not just the first",
          ids_of(leaks).count("voice:crux-term") >= 2)

    mirrored = [(pi, "what's up with q19? is the synthesis any good?"),
                (ag, "q19 is the label-budget question, and the synthesis reads well to me.")]
    check("voice: an id and a term the PI used first are licensed back — the mirror rule",
          ids_of(mirrored) == [])
    check("voice: licensing is directional — the PI using q19 does not license h4",
          ids_of([(pi, "what's up with q19?"), (ag, "q19 is fine; h4 is the open one.")])
          == ["voice:node-id"])
    check("voice: an id licensed in one conversation is not licensed in the next — ids are "
          "ephemeral handles, and a stale one is a trap",
          ids_of([(ag, "q19 is fine.")]) == ["voice:node-id"])

    check("voice: a term in the PI's glossary is licensed from turn zero — the permanent "
          "graduation path spec 14 already owns",
          ids_of([(ag, "the review gate is open on that one.")], agreed=["review gate"]) == [])

    notebook = [(pi, "show me the tree"),
                (ag, "q1 holds q2 and q3; h1 is done, h2 is an idea, h3 is running. Want me "
                     "to open the cockpit on it?"),
                (pi, "thanks. so does the extra data help?"),
                (ag, "h1 says yes.")]
    f = E.voice_lint(notebook)
    check("voice: an explicit notebook request opens ids and notebook vocabulary for that "
          "exchange, and closes again at the next PI turn",
          [i for i, _m in f] == ["voice:node-id"] and "turn 4" in f[0][1])

    expect_error("voice: an unknown speaker is refused, never coerced to one side",
                 lambda: E.voice_lint([("reviewer", "q1")]))
    check("voice: the scan is pure — same turns, same findings, no vault and no filesystem",
          E.voice_lint(leaks) == E.voice_lint(leaks))

    # ---- the teaching artifacts. Spec 06 settled that instructions were never the binding
    #      constraint; the modeled dialogues are. So the dialogues are scanned, not read.
    def dialogue(text, marks):
        """Agent-side speech turns out of a markdown transcript, as voice_lint turns."""
        turns, cur, who = [], [], None
        for line in text.splitlines():
            for mark, speaker in marks:
                if line.strip().startswith(mark):
                    if who: turns.append((who, " ".join(cur)))
                    who, cur = speaker, [line.strip()[len(mark):]]
                    break
            else:
                if who and line.strip() and not line.strip().startswith("```"):
                    cur.append(line.strip())
                elif who and not line.strip():
                    turns.append((who, " ".join(cur))); who, cur = None, []
        if who: turns.append((who, " ".join(cur)))
        return turns

    # The README is a marketing surface as well as a teaching one, and it is re-cut
    # often — it does not always carry a you/crux transcript. So the transcript is
    # linted WHEN PRESENT rather than required: the binding guarantee lives on
    # SKILL.md below, which is the artifact an agent actually reads. If a transcript
    # comes back to the README, it is voice-linted again automatically.
    readme = read(os.path.join(repo, "README.md"))
    block = readme.split("```text")[1].split("```")[0] if "```text" in readme else ""
    rt = dialogue(block, [("you", pi), ("crux", ag)])
    if sum(1 for s, _t in rt if s == ag) >= 2:
        check(f"voice: README's transcript is ID-free science ({ids_of(rt)})", ids_of(rt) == [])

    skill = read(os.path.join(repo, "skills", "crux", "SKILL.md"))
    st = dialogue(skill, [("> **PI:**", pi), ("> **You:**", ag)])
    check(f"voice: SKILL.md's session dialogue has agent turns to scan ({len(st)} turns)",
          sum(1 for s, _t in st if s == ag) >= 2)
    check(f"voice: SKILL.md's session dialogue is ID-free science ({ids_of(st)})",
          ids_of(st) == [])
    low = skill.lower()
    check("voice: SKILL.md carries a top-level voice section naming the 4.0 rules — mirror, "
          "silent bookkeeping, relevance, titles, notebook mode, the PI's correction",
          re.search(r"^## .*[Vv]oice", skill, re.M)
          and all(k in low for k in ("mirror rule", "silent bookkeeping", "relevance", "title",
                                     "notebook mode", "plain words")))
    check("voice: the sign-off moments are gone from the core — nothing waits on the PI",
          "signature moment" not in low and "review gate" not in low)

    # ---- glossary graduation. Without the waiver a crux process term can never be
    #      proposed: it appears nowhere in the corpus the centrality filter counts, so the
    #      path spec 16 relies on would be dead on arrival. The tree is built inline: a 4.0
    #      hypothesis states its expectation first.
    root = tempfile.mkdtemp(prefix="crux_voice_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Voice", root)
    ids = {}
    ids["q1"], _ = E.cmd_ask(root, "how do we cut the label budget", None)
    ids["q2"], _ = E.cmd_ask(root, "does pretraining help at low label count", ids["q1"])
    ids["q3"], _ = E.cmd_ask(root, "which augmentation family matters", ids["q1"])
    hy = lambda t, p: E.cmd_hypothesize(root, t, parent=p, verifiables=["accuracy >= +2.0"],
                                        neutral=["the baseline reproduces its published number"],
                                        expect="accuracy rises by at least 2 points")[0]
    ids["h1"] = hy("pretraining beats scratch", ids["q2"])
    ids["h2"] = hy("pretraining still helps at 20 labels", ids["q2"])
    ids["h3"] = hy("colour jitter is the family that matters", ids["q3"])
    try:
        got = [c["term"] for c in E.glossary_candidates(root, ["review gate", "flumox"])]
        check(f"voice: a crux process term the vault never mentions is still proposable ({got})",
              got == ["review gate"])
        check("voice: and the waiver is narrow — a non-lexicon term still has to be central",
              E.glossary_candidates(root, ["flumox"]) == [])

        # ---- relevance, engine-computed: what the agent may raise on its own initiative
        rel = lambda near, other: E.gate_relation(E.Vault(root), near, other)
        check("voice: lineage and immediate siblings are in scope, an unrelated branch is not",
              [rel(ids["q2"], x) for x in (ids["q2"], ids["q1"], ids["h1"], ids["q3"], ids["h3"])]
              == ["self", "ancestor", "descendant", "sibling", "unrelated"])
        check("voice: sibling means IMMEDIATE sibling — a cousin is unrelated",
              rel(ids["h1"], ids["h3"]) == "unrelated" and rel(ids["h1"], ids["h2"]) == "sibling")
        check("voice: every relation the engine can emit is in the declared vocabulary",
              all(rel(ids["q2"], o) in E.GATE_RELATIONS for o in ids.values()))

        # ---- spec 19: there is no review gate left to annotate; the verb says so and writes
        #      nothing, so a habit that still types it is redirected, never broken
        before = _tree_hashes(root)
        out = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "review",
                              "--json", "--near", ids["q2"]],
                             capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        check("voice: `crux review` is removed — it prints one pointer and writes nothing",
              "removed" in out.stdout + out.stderr and _tree_hashes(root) == before)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_situate_title_anchor():
    """Spec 16 — `situate:unanchored` accepts the anchor's TITLE or its id.

    Spec 13 bought a deterministic misresolution check with that lint, and spec 16 keeps it
    while taking the ids out of chat: orienting confidently over the wrong subtree is still
    situate's worst failure, and naming the subtree by its title discloses it just as well."""
    print("\n# science voice — situate anchors by title (spec 16, PRD 16.1)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    TITLE = "how do we cut the label budget"

    def draft(head):
        body = "\n\n".join(" ".join(["word"] * 40) for _ in range(3))
        return head + " " + " ".join(["word"] * 15) + "\n\n" + body

    anchor = ("q20", TITLE)
    ids_of = lambda text: [i for i, _m in E.situate_lint(text, [anchor])]
    check("voice: an answer naming the anchor's title passes the lint",
          ids_of(draft(f"Here's where things stand on '{TITLE}' and everything under it.")) == [])
    check("voice: title matching is case-insensitive, because chat is not a database",
          ids_of(draft("Where we are on How Do We Cut The Label Budget:")) == [])
    check("voice: the id form still passes — the PI who wants ids is not broken",
          ids_of(draft("Resolved: q20 —")) == [])
    check("voice: an answer naming neither still fails",
          ids_of(draft("Here is where things stand:")) == ["situate:unanchored"])
    check("voice: a plain-string anchor keeps its old meaning — id only",
          [i for i, _m in E.situate_lint(draft(f"on '{TITLE}'"), ["q20"])]
          == ["situate:unanchored"])
    check("voice: the finding names the title, so the PI can see what was expected",
          TITLE in dict(E.situate_lint(draft("nothing named here"), [anchor]))["situate:unanchored"])

    # ---- the CLI the agent actually pipes its draft through
    root = tempfile.mkdtemp(prefix="crux_titlelint_")
    shutil.rmtree(root); os.makedirs(root)
    try:
        E.cmd_init("Lint", root)
        argv = [sys.executable, os.path.join(HERE, "crux.py"), "brief", "q20",
                "--lint-situate", "--anchor-title", TITLE]
        r = subprocess.run(argv, input=draft(f"Where we are on '{TITLE}':"),
                           capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        check("voice: `--lint-situate --anchor-title` accepts a title-anchored draft",
              r.returncode == 0)
        rb = subprocess.run(argv + ["--json"], input=draft("no anchor at all here"),
                            capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        check("voice: and still fails one that names neither",
              rb.returncode == 1
              and [f["id"] for f in json.loads(rb.stdout)["findings"]] == ["situate:unanchored"])
    finally:
        shutil.rmtree(root, ignore_errors=True)

    # ---- the agent definition moves with the lint, or the lint is arguing with its own agent
    import evals as V
    P = V.roster_properties(V.load_definitions(["crux-situate"], repo))
    check(*P["situate-title-anchor"])
    body = read(os.path.join(repo, "agents", "crux-situate", "AGENT.md"))
    check("voice: crux-situate no longer mandates ids in the first line",
          "name the ids" not in body.lower())

    check("voice: ENGINE_VERSION at or past 3.2", at_least_version("3.2"))

    # ---- GATE 4. Spec 16 changes no vault format, no verdict, no roll-up and no view — but a
    #      shipped deterministic bound changed behaviour, and the stamp is how a vault records
    #      which engine wrote it, so the counter rolls and the migration is proved rather than
    #      asserted. A 3.1 vault must read IDENTICALLY: same verdicts, same views, byte for
    #      byte apart from the stamp the drift path is supposed to rewrite.
    old = tempfile.mkdtemp(prefix="crux_v31_")
    try:
        src = os.path.join(HERE, "..", "examples", "scaling_vault")
        was, now = os.path.join(old, "v31"), os.path.join(old, "current")
        shutil.copytree(src, was); shutil.copytree(src, now)
        # the shipped example vaults carry OLD stamps on purpose, so rewrite the line
        # rather than substituting the current version out of it
        cfg = os.path.join(was, E.VAULT_MARKER)
        E.write_if_changed(cfg, re.sub(r"(?m)^engine_version:.*$", "engine_version: 3.1",
                                       read(cfg)))

        def readout(root):
            """Everything this engine DERIVES from a vault — the (inert) verdicts, roll-ups,
            the derived states (spec 19 replaced the review gate), and the structural checks. If a stamp could change any of it, the stamp would be
            a compatibility era rather than a counter, and this suite would be lying."""
            v = E.Vault(root)
            return {"verdicts": {i: n["fm"].get("verdict") for i, n in sorted(v.nodes.items())},
                    "status": {i: n.status for i, n in sorted(v.nodes.items())},
                    "ledger": {i: E.ledger_counts(v, i) for i, n in sorted(v.nodes.items())
                               if n.type == "question"},
                    "states": {i: E.derive_state(v, i) for i, n in sorted(v.nodes.items())
                               if n.type in ("question", "idea")},
                    "checks": E.validation_report(root, checks=("tree", "economy", "fanout",
                                                                "rd", "tasks"))}
        before = _tree_hashes(was)
        a, b = readout(was), readout(now)
        check("voice: a 3.1-stamped vault reads IDENTICALLY under 3.2 — same verdicts, same "
              "roll-up, same derived states, same structural checks",
              json.dumps(a, sort_keys=True, default=str)
              == json.dumps(b, sort_keys=True, default=str)
              and a["verdicts"]["h2"] == "partial" and a["checks"]["ok"]
              and a["states"]["h2"]["state"] == "leaning" and a["states"]["q1"]["state"] == "settled")
        check("voice: and reading it wrote nothing — the drift path is the only writer",
              _tree_hashes(was) == before)

        warn = E.check_and_stamp_version(was)
        check(f"voice: the drift warning names both versions and re-stamps, which is expected "
              f"({(warn or '')[:38]}…)",
              warn and "3.1" in warn and E.ENGINE_VERSION in warn
              and E.Vault(was).cfg.get("engine_version") == E.ENGINE_VERSION)
        check("voice: re-stamping touches the stamp and nothing else",
              sorted(k for k, h in _tree_hashes(was).items() if before.get(k) != h)
              == [E.VAULT_MARKER])
        check("voice: and the readout is still identical afterwards — no verdict moved",
              json.dumps(readout(was)["verdicts"], sort_keys=True)
              == json.dumps(b["verdicts"], sort_keys=True))
    finally:
        shutil.rmtree(old, ignore_errors=True)


def run_cli_third_person():
    """Spec 16 — the CLI's text output is declared AGENT-FACING.

    It stays ID-led and terse: it is `--json` with eyes, and the humans who bypass the agent
    and run crux by hand are exactly the ones who want ids. The one change is person. Second
    person was quietly nudging the agent to relay the line verbatim — "Awaiting your
    decision" reads as words addressed to the reader, and the reader of a tool result is the
    agent, not the PI."""
    print("\n# science voice — the CLI speaks of the PI, not to them (spec 16, PRD 16.1)")
    SECOND = re.compile(r"\b(you|your|yours|yourself|yourselves|you're)\b", re.I)
    crux = os.path.join(HERE, "crux.py")

    def run(argv, cwd=None, **kw):
        return subprocess.run([sys.executable, crux] + argv, capture_output=True,
                              cwd=cwd, encoding="utf-8", errors="replace", **kw)

    verbs = [l.split()[0] for l in run(["--help"]).stdout.splitlines()
             if l.startswith("    ") and l.strip() and l[4] not in " -"]
    helps = {"--help": run(["--help"]).stdout}
    for v in sorted(set(verbs)):
        r = run([v, "--help"])
        if r.returncode == 0:
            helps[v] = r.stdout
    bad = sorted(f"{k}: {SECOND.search(t).group(0)!r}" for k, t in helps.items() if SECOND.search(t))
    check(f"voice: no second-person address in any of {len(helps)} help screens ({bad[:3]})",
          len(helps) > 10 and not bad)

    root = tempfile.mkdtemp(prefix="crux_person_")
    try:
        out = [run(["init", "Person Project"], cwd=root).stdout]
        vault = os.path.join(root, "cruxvault")
        for argv in (["status"], ["validate"], ["task", "list"], ["pending", "list"],
                     ["finding", "--help"], ["park", "--help"]):
            out.append(run(argv, cwd=vault).stdout)
        bad = sorted({SECOND.search(t).group(0) for t in out if SECOND.search(t)})
        check(f"voice: no second-person address in the CLI's own text output ({bad})", not bad)
        check("voice: the init hint survives the rewrite", "cd cruxvault" in out[0])

        # The drift warning escaped the sweep above: it goes to stderr and only fires on an
        # already-drifted vault, so no verb in `out` can produce it. It is CLI text like any
        # other and spec 16 binds it the same way — and it is the one string SKILL.md used to
        # tell the agent to relay verbatim, which is how a second-person line addressed to
        # the reader ends up quoted at the PI.
        drift = E.check_and_stamp_version.__doc__ and None
        cfg = os.path.join(vault, E.VAULT_MARKER)
        E.write_if_changed(cfg, E.yaml_dump({**E.yaml_load(E.read(cfg)),
                                             "engine_version": "0.1"}) + "\n")
        drift = run(["status"], cwd=vault).stderr
        check("voice: a drift warning actually fires when the stamp is behind",
              "engine drift" in drift)
        check(f"voice: no second-person address in the drift warning "
              f"({SECOND.search(drift).group(0) if SECOND.search(drift) else ''})",
              not SECOND.search(drift))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_voice_enforcement():
    """Spec 16 PRD 16.2 — the voice rules, enforced where they were only stated.

    16.1 landed the rules and the lint and the leak survived, twice. This suite pins the
    three mechanisms that replace "the modeled dialogues will bind":

      A  the skill stops contradicting itself — `act-and-report` told the agent to announce
         exactly the bookkeeping voice rule 2 says to do in silence
      B  the receipt that mints an id also hands over the handle to use instead of it
      C  `voice_lint` runs at CHAT time, against the live transcript, instead of only over
         shipped fixtures in CI

    C's honest limit is asserted too: a hook fires AFTER the message it is judging, so it
    catches the repetition rather than the first leak. That is why B exists."""
    print("\n# science voice — enforced, not just stated (spec 16, PRD 16.2)")
    crux = os.path.join(HERE, "crux.py")
    skill = read(os.path.join(HERE, "..", "SKILL.md"))

    def run(argv, cwd=None, stdin=None):
        return subprocess.run([sys.executable, crux] + argv, capture_output=True, cwd=cwd,
                              input=stdin, encoding="utf-8", errors="replace")

    # ---- A · the contradiction. `○` was the SIGNATURE axis (does this need the PI's yes?);
    #      spec 16 added the DISCLOSURE axis (do I say anything?) and the two collapsed onto
    #      one glyph, so "act-and-report" ended up instructing the announcement that rule 2
    #      forbids. The phrase is the defect; its absence is the fix.
    check("voice: SKILL.md no longer tells the agent to report its bookkeeping",
          "act-and-report" not in skill and "act, then report" not in skill)
    # Spec 19: the ○/◆ verb legend is gone with the review gate, and the contradiction it
    # caused cannot come back through it. What section A protects is the 4.0 core's voice
    # rules: silent bookkeeping is stated, nothing tells the agent to announce or ask leave,
    # and the rule is read before the first verb the agent is taught to run.
    low = skill.lower()
    voice = re.search(r"^## Voice — the invisible notebook$(.*?)(?=^## |\Z)", skill, re.M | re.S)
    vtext = voice.group(1) if voice else ""
    check("voice: the 4.0 core states silent bookkeeping — record and say nothing, no echo, "
          "no asking leave",
          "silent bookkeeping" in vtext.lower() and "say nothing" in vtext
          and "command echo" in vtext and "asking leave" in vtext)
    check("voice: ... and no glyph legend or sign-off step survives to invite a second reading",
          "○" not in skill and "◆" not in skill and "signature" not in low
          and "approve" not in low)
    check("voice: CLI output is declared agent-facing, never relayed",
          "agent-facing" in vtext and "never relay" in vtext)
    # Order is load-bearing: the rules are read before the router hands work elsewhere, and
    # the capture rules that write silently point at them by being in the same file.
    check("voice: the Voice section comes before the router and the guardrails",
          bool(voice) and skill.index("## Voice — the invisible notebook")
          < skill.index("## Guardrails") < skill.index("## Router"))

    # ---- B · the handle. The agent reaches for `t81` partly because it needs SOME handle
    #      and the id is the nearest one in context. Hand over the substitute at the moment
    #      the id is minted.
    check("voice: the engine has one chat-handle line, so every verb prints the same shape",
          'in chat' in E.chat_handle("t81", "fetch the antibody lot")
          and "fetch the antibody lot" in E.chat_handle("t81", "fetch the antibody lot")
          and "t81" in E.chat_handle("t81", "fetch the antibody lot"))

    root = tempfile.mkdtemp(prefix="crux_voice_")
    try:
        run(["init", "Voice Project"], cwd=root)
        vault = os.path.join(root, "cruxvault")
        minted = {}
        minted["ask"] = run(["ask", "does more data beat a better model"], cwd=vault).stdout
        qid = re.search(r"✓ (q\d+)", minted["ask"]).group(1)
        minted["hypothesize"] = run(["hypothesize", "doubling the data wins on held-out",
                                     "--parent", qid, "-v", "imp-Spearman >= +0.01",
                                     "--expect", "held-out gain above 0.01"],
                                    cwd=vault).stdout
        hid = re.search(r"✓ (h\d+)", minted["hypothesize"]).group(1)
        minted["task add"] = run(["task", "add", "fetch the antibody lot",
                                  "--category", "data-acquisition", "--blocked-by", "None"],
                                 cwd=vault).stdout
        # spec 19 removed `synthesize`; a Finding is the id-minting verb that replaced it
        minted["finding"] = run(["finding", qid, "--answer", "what the data question settled",
                                 "-c", "moderate"], cwd=vault).stdout
        minted["rd"] = run(["rd", hid, "the sweep design"], cwd=vault).stdout
        titles = {"ask": "does more data beat a better model",
                  "hypothesize": "doubling the data wins on held-out",
                  "task add": "fetch the antibody lot",
                  "finding": "what the data question settled",
                  "rd": "the sweep design"}
        bad = sorted(v for v, out in minted.items()
                     if "in chat" not in out or titles[v] not in out)
        check(f"voice: every id-minting verb hands over the chat handle beside the id ({bad})",
              len(minted) == 5 and not bad)
        SECOND = re.compile(r"\b(you|your|yours|you're)\b", re.I)
        hits = sorted(v for v, out in minted.items() if SECOND.search(out))
        check(f"voice: ... and the new line keeps the CLI's third person ({hits})", not hits)

        # ---- C · the lint at chat time. Same `voice_lint`, new consumer.
        def turns_file(turns):
            p = os.path.join(root, "turns.json")
            with open(p, "w", encoding="utf-8") as f: json.dump(turns, f)
            return p

        leak = turns_file([["pi", "did the extra data actually help?"],
                           ["agent", f"{hid} is refuted — the review gate is open."]])
        r = run(["voice", "--turns", leak], cwd=vault)
        check("voice: --turns reports a leaked id and a leaked crux term",
              r.returncode == 1 and "voice:node-id" in r.stdout
              and "voice:crux-term" in r.stdout)
        clean = turns_file([["pi", "did the extra data actually help?"],
                            ["agent", "the doubled-data arm cleared the bar we set."]])
        r = run(["voice", "--turns", clean], cwd=vault)
        check("voice: ... and says nothing at all on a clean conversation",
              r.returncode == 0 and not r.stdout.strip())
        mirrored = turns_file([["pi", f"what's up with {hid}?"],
                               ["agent", f"{hid} is refuted."]])
        r = run(["voice", "--turns", mirrored], cwd=vault)
        check("voice: ... and the mirror rule still licenses what the PI said first",
              r.returncode == 0 and not r.stdout.strip())

        # A transcript is not a conversation: tool results are where the ids legitimately
        # live, and counting one as the PI speaking would license every id in the vault.
        def transcript(lines):
            p = os.path.join(root, "t.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                for l in lines: f.write(json.dumps(l) + "\n")
            return p

        def hook(tpath, command="crux task add x", cwd=vault):
            payload = {"hook_event_name": "PostToolUse", "tool_name": "Bash",
                       "tool_input": {"command": command},
                       "transcript_path": tpath, "cwd": cwd}
            return run(["voice", "--hook"], cwd=vault, stdin=json.dumps(payload))

        user = lambda t: {"type": "user", "message": {"role": "user",
                          "content": [{"type": "text", "text": t}]}}
        asst = lambda t: {"type": "assistant", "message": {"role": "assistant",
                          "content": [{"type": "text", "text": t}]}}
        result = lambda t: {"type": "user", "message": {"role": "user",
                            "content": [{"type": "tool_result", "content": t}]}}

        r = hook(transcript([user("did the extra data help?"),
                             result(f"✓ {hid}  (vault/{hid}_x.md)"),
                             asst(f"{hid} came out refuted.")]))
        out = json.loads(r.stdout) if r.stdout.strip() else {}
        ctx = out.get("hookSpecificOutput", {}).get("additionalContext", "")
        check("voice: --hook flags an id the agent used and the PI never did",
              r.returncode == 0 and hid in ctx and "voice:node-id" in ctx)
        check("voice: ... and a tool result full of ids never counts as the PI speaking",
              "additionalContext" in json.dumps(out))

        r = hook(transcript([user("did the extra data help?"),
                             asst("the doubled-data arm cleared the bar.")]))
        check("voice: --hook is silent when the newest turn is clean",
              r.returncode == 0 and not r.stdout.strip())

        # Cumulative licensing, turn-scoped reporting: without this, one old slip re-fires on
        # every later tool call and the signal is noise inside a minute.
        r = hook(transcript([user("did it help?"),
                             asst(f"{hid} is refuted."),
                             user("ok, and the other arm?"),
                             asst("the equal-compute rerun cut the gain to 0.4.")]))
        check("voice: --hook reports only the newest agent turn, never the whole backlog",
              r.returncode == 0 and not r.stdout.strip())

        r = hook(transcript([user("did it help?"), asst(f"{hid} is refuted.")]),
                 command="ls -la")
        check("voice: --hook ignores a tool call that was not a crux command",
              r.returncode == 0 and not r.stdout.strip())

        # A hook that breaks a session is strictly worse than the leak it was added to catch.
        for name, stdin_, tp in (("malformed json", "{not json", None),
                                 ("empty stdin", "", None),
                                 ("missing transcript", None, os.path.join(root, "nope.jsonl"))):
            r = (run(["voice", "--hook"], cwd=vault, stdin=stdin_) if tp is None
                 else hook(tp))
            check(f"voice: --hook survives {name} — exit 0, no output",
                  r.returncode == 0 and not r.stdout.strip())

        # Glossary graduation, spec 14's flow reused: a term the PI accepted is theirs to
        # hear from turn zero, with no PI turn needed to license it.
        E.cmd_glossary_accept(vault, "review gate", "the point where a question waits on me")
        r = run(["voice", "--turns", turns_file(
            [["pi", "anything need me?"], ["agent", "the review gate is open on the data question."]])],
            cwd=vault)
        check("voice: a glossary-graduated crux term is licensed from turn zero",
              r.returncode == 0 and "voice:crux-term" not in r.stdout)

        # ---- C · registration. Idempotent, and it must not eat a settings file it found.
        sp = os.path.join(root, "settings.json")
        with open(sp, "w", encoding="utf-8") as f:
            json.dump({"model": "opus", "hooks": {"PreToolUse": [{"matcher": "Write"}]}}, f)
        run(["voice", "--install-hook", "--settings", sp])
        run(["voice", "--install-hook", "--settings", sp])
        cfg = json.loads(read(sp))
        posts = cfg.get("hooks", {}).get("PostToolUse", [])
        entries = [h for g in posts for h in g.get("hooks", [])
                   if "voice --hook" in h.get("command", "")]
        check("voice: --install-hook is idempotent — twice run, one entry",
              len(entries) == 1)
        check("voice: ... and unrelated settings survive it",
              cfg.get("model") == "opus"
              and cfg.get("hooks", {}).get("PreToolUse") == [{"matcher": "Write"}])
        check("voice: ... and it registers on PostToolUse over Bash",
              any(g.get("matcher") == "Bash" for g in posts
                  if any("voice --hook" in h.get("command", "") for h in g.get("hooks", []))))

        # ---- C · doctor. Absent is a WARN: crux runs fine by hand with no agent anywhere,
        #      which is exactly the state `_doctor_skills` already refuses to call broken.
        rep = E.cmd_doctor(root=vault, settings_paths=[os.path.join(root, "absent.json")])
        hookchk = [c for c in rep["checks"] if c["name"] == "voice-hook"]
        check("voice: doctor carries a voice-hook check", len(hookchk) == 1)
        check("voice: ... which warns rather than fails when the hook is not registered",
              hookchk and hookchk[0]["level"] == "warn" and hookchk[0]["fix"])
        rep = E.cmd_doctor(root=vault, settings_paths=[sp])
        hookchk = [c for c in rep["checks"] if c["name"] == "voice-hook"]
        check("voice: ... and reports ok once it is",
              hookchk and hookchk[0]["level"] == "ok")

        check("voice: install.sh registers the hook",
              "voice --install-hook" in read(os.path.join(HERE, "..", "..", "..", "install.sh")))
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_persona_eval():
    """Spec 16 — the persona eval, a PERMANENT fixture class rather than an acceptance run.

    Spec 16 rejects the one-off by name: *"the next prompt edit silently regresses and
    nothing catches it."* So the voice rule joins spec 10's harness, under spec 10's
    architecture — the harness never invokes an agent, it scores a submitted transcript —
    and the grading is layered cheapest-first, because a regexable property graded by a
    model is a property that has silently stopped being checked."""
    print("\n# science voice — the persona eval (spec 16, PRD 16.1)")
    import evals as V
    m = V.load_manifest("persona-01")
    SUB = os.path.join(V.FIXTURES, "persona-01", "submissions")
    sc = lambda n: V.score(m, V.load_submission(os.path.join(SUB, n)))
    hard = lambda n: {name.split(" (")[0]: ok for name, ok, _w in sc(n)["hard"]}
    voice_ok = lambda n: hard(n)["the agent spoke science throughout"]
    state_ok = lambda n: all(v for k, v in hard(n).items() if k.startswith("state "))

    before = _tree_hashes(V.vault_of(m))
    r = V.certify("persona-01")
    check(f"persona: the fixture certifies ({r['missing']} {r['cross_failed']})", r["ok"])
    check("persona: it is graded over the SHIPPED example vault, not a copy of one",
          os.path.abspath(V.vault_of(m))
          == os.path.abspath(os.path.join(HERE, "..", "examples", "scaling_vault"))
          and os.path.isfile(os.path.join(V.vault_of(m), E.VAULT_MARKER)))
    check("persona: a judged key is declared a proxy, and the band is still the PI's",
          m["ground_truth"] == "proxy" and m["band"] == V.BAND_UNSET)

    # ---- layer 1: the deterministic scan
    check("persona: the clean session passes the voice scan and the state assertions",
          voice_ok("clean.json") and state_ok("clean.json"))
    check("persona: an ID-LED session fails the scan even though every fact is right and "
          "the notebook was kept",
          not voice_ok("id-led.json") and state_ok("id-led.json")
          and sc("id-led.json")["verdict"] == V.FAIL)
    check("persona: ... and it fails on BOTH kinds of leak, not just the ids",
          {i for i, _x in E.voice_lint(V.transcript_turns(
              V.load_submission(os.path.join(SUB, "id-led.json"))))}
          == {"voice:node-id", "voice:crux-term"})

    # ---- the mirror-rule positive case, and the proof that it is the PI's turn doing it
    mirror = V.load_submission(os.path.join(SUB, "mirror.json"))
    turns = V.transcript_turns(mirror)
    check("persona: the mirror-rule case passes — the persona typed an id and a crux term, "
          "so the agent may use both",
          voice_ok("mirror.json")
          and any(E.NODE_ID_RE.search(t) for sp, t in turns if sp == "pi"))
    stripped = [(sp, t) for sp, t in turns
                if not (sp == "pi" and E.NODE_ID_RE.search(t))]
    check("persona: ... and it is the persona's turn doing the licensing — delete it and the "
          "very same agent text is a leak",
          E.voice_lint(stripped) != [] and E.voice_lint(turns) == [])

    # ---- notebook mode, same construction
    nb = V.transcript_turns(V.load_submission(os.path.join(SUB, "notebook.json")))
    check("persona: the notebook-mode case passes, and offers the cockpit",
          voice_ok("notebook.json")
          and any("crux serve" in t for sp, t in nb if sp == "agent"))
    check("persona: ... and it is the 'show me the tree' turn that opened it",
          E.voice_lint([(sp, t) for sp, t in nb
                        if not (sp == "pi" and "show me the tree" in t)]) != [])
    check("persona: notebook mode closes again — the turns after it are science",
          E.voice_lint(nb) == [])

    # ---- layer 2: silence is only a virtue if the notebook is kept behind it
    check("persona: flawless voice with an untouched vault FAILS — the notebook has to be "
          "kept, not merely unmentioned",
          voice_ok("idle.json") and not state_ok("idle.json")
          and sc("idle.json")["verdict"] == V.FAIL)
    check("persona: the state table asserts every step of the silent bookkeeping, in the "
          "4.0 model's terms",
          {k.split(":")[0] for k, _p, _n in V.state_rows(m)}
          == {"direction", "answered", "state", "confidence", "pending"})
    expect_error("persona: an unknown state predicate is refused, not silently skipped",
                 lambda: V.check_state({"name": "x", "body": "## Vault state\n\n| k | p |\n"
                                                             "|---|---|\n| `orbit:h1` | x |\n"},
                                       {"nodes": {}, "tasks": {}}))

    check("persona: the rubric grades BOTH halves of the relevance rule — what the agent may "
          "not raise, and what the PI asking makes fair game",
          {"judge:relevance", "judge:pi-asks-everything"} <= m["planted_ids"])
    clean = V.transcript_turns(V.load_submission(os.path.join(SUB, "clean.json")))
    check("persona: the clean session actually contains the PI-asks-everything exchange",
          any(sp == "pi" and "waiting on me" in t for sp, t in clean))

    # ---- the relevance trap is armed MECHANICALLY, not by assertion in prose
    v = E.Vault(V.vault_of(m))
    anchor, out_of = str(m["fm"]["anchor"]), V._csv(m["fm"]["out_of_scope"])
    check(f"persona: every id the fixture calls out-of-scope really is, per the engine "
          f"({[(i, E.gate_relation(v, anchor, i)) for i in out_of]})",
          out_of and all(E.gate_relation(v, anchor, i) == "unrelated" for i in out_of))
    check("persona: and the trap was actually armed — the out-of-scope acceptance is pending "
          "in the end state",
          V.load_submission(os.path.join(SUB, "clean.json"))
           ["vault_after"]["tasks"]["t1"]["pending_gate"] is True)

    # ---- the projection a submitter is told to produce, produced the way they are told to.
    #      On a COPY, because `crux status` re-stamps a drifted vault and the shipped example
    #      vaults carry old stamps deliberately — that write is the engine working, not a leak.
    tmp = tempfile.mkdtemp(prefix="crux_project_")
    try:
        copy = os.path.join(tmp, "vault")
        shutil.copytree(V.vault_of(m), copy)
        raw = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "status", "--json"],
                             capture_output=True, cwd=copy, encoding="utf-8", errors="replace")
        proj = subprocess.run([sys.executable, os.path.join(HERE, "evals.py"), "--project-state"],
                              input=raw.stdout, capture_output=True, encoding="utf-8",
                              errors="replace")
        got = json.loads(proj.stdout)
        check("persona: `evals.py --project-state` turns a real status payload into the object "
              "a submission carries",
              proj.returncode == 0 and set(got) == {"nodes", "tasks"}
              and got["nodes"]["q1"]["state"] == "settled"
              and got["nodes"]["q1"]["confidence"] == "strong"
              and got["nodes"]["q1"]["answered"] is True
              and got["nodes"]["h2"]["direction"] == "mixed"
              and got["nodes"]["h3"]["direction"] == "against"
              and got["nodes"]["q3"]["answered"] is False
              and got["nodes"]["q3"]["state"] == "open")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    check("persona: certifying and scoring write nothing to the shipped example vault",
          _tree_hashes(V.vault_of(m)) == before)

    # ---- the submission is pinned to the prompt that produced it, as every other one is
    sub = V.load_submission(os.path.join(SUB, "clean.json"))
    check("persona: the submission is pinned to SKILL.md's hash — the voice rules are what "
          "was measured",
          sub["agent_sha"] == V.agent_sha("crux")
          and V.agent_sha("crux") == hashlib.sha256(
              open(os.path.join(HERE, "..", "SKILL.md"), "rb").read()).hexdigest())
    stale = dict(sub, agent_sha="0" * 64)
    check("persona: a submission measured against a different SKILL.md is REFUSED",
          V.score(m, stale)["verdict"] == V.REFUSED)


# --- spec 17.1 — OpenAlex client + DOI enrichment ------------------------------------
# Every assert below runs with OPENALEX_API_KEY unset and the network boundary stubbed.
# That is the point: the gate must stay green from a fresh clone with no key and no socket,
# or "opt-in" is a claim rather than a property.

_OA_WORK = {
    "id": "https://openalex.org/W2605897695",
    "display_name": "Nextflow enables reproducible computational workflows",
    "publication_year": 2017,
    "authorships": [
        {"author": {"display_name": "Paolo Di Tommaso"}},
        {"author": {"display_name": "Maria Chatzou"}},
        {"author": {"display_name": "Evan W. Floden"}},
    ],
}

def run_openalex():
    """Spec 17.1 — the one network path the rest of epic 17 sits on: its own module on the
    impure side of spec 05's purity line, cached, opt-in, and inert without a key. Also the
    .sources.tsv 4->5 column migration that 17.2 needs in order to seed a crawl."""
    print("\n# openalex client + doi enrichment (spec 17.1)")
    import openalex as OA
    root = tempfile.mkdtemp(prefix="crux_oa_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("OA Demo", root, goal="Exercise the OpenAlex client.")
    os.environ.pop("OPENALEX_API_KEY", None)

    # -- the purity line holds: the engine never reaches the network, the CLI loads the
    #    module lazily, and openalex imports engine rather than the reverse ---------------
    eng = read(os.path.join(HERE, "engine.py"))
    oa_src = read(os.path.join(HERE, "openalex.py"))
    lazy = [l for l in read(os.path.join(HERE, "crux.py")).splitlines()
            if re.match(r"\s*import openalex\b", l)]
    check("oa: the engine imports no urllib and never imports openalex",
          not re.search(r"^\s*(import|from)\s+urllib\b", eng, re.M)
          and not re.search(r"^\s*(import|from)\s+openalex\b", eng, re.M))
    check("oa: crux.py imports openalex lazily, inside the branch that needs it",
          bool(lazy) and all(l.lstrip() != l for l in lazy))
    check("oa: openalex.py imports engine and nothing outside the stdlib",
          bool(re.search(r"^import engine as E", oa_src, re.M))
          and all(m.split(".")[0] in {"os", "json", "hashlib", "engine", "urllib"}
                  for m in re.findall(r"^\s*(?:import|from)\s+([\w.]+)", oa_src, re.M)))

    # -- registry migration: a 4-column legacy line must load, then round-trip as 5 --------
    os.makedirs(os.path.join(root, "wiki"), exist_ok=True)
    legacy = os.path.join(root, E.SOURCES_FILE)
    write(legacy, "abc123\t2026-01-01\traw/legacy.txt\tLegacy Paper — A Author (2020)\n")
    reg = E.load_sources(root)
    check("oa: legacy 4-column line loads with an empty work id",
          reg["raw/legacy.txt"]["workid"] == "" and
          reg["raw/legacy.txt"]["title"] == "Legacy Paper — A Author (2020)")
    E.save_sources(root, reg)
    check("oa: legacy line re-saves as 5 columns with no data loss",
          read(legacy).strip().split("\t") ==
          ["abc123", "2026-01-01", "raw/legacy.txt", "", "Legacy Paper — A Author (2020)"])

    # -- doi enrichment, driven the way the CLI drives it ---------------------------------
    src = os.path.join(root, "raw", "nextflow.txt")
    write(src, "Nextflow paper stand-in.\n")
    real_fetch, calls = OA._fetch, []
    def ingest_doi(rel, doi, title=None):
        w = OA.work_by_doi(root, doi)
        return E.cmd_ingest(root, rel, title or OA.title_line(w), workid=OA.work_id(w))
    try:
        OA._fetch = lambda url: (calls.append(url), json.dumps(_OA_WORK))[1]
        ingest_doi("raw/nextflow.txt", "10.1038/nbt.3820")
        rec = E.load_sources(root)["raw/nextflow.txt"]
        check("oa: --doi writes the canonical title, full author list and year",
              rec["title"] == "Nextflow enables reproducible computational workflows — "
                              "Paolo Di Tommaso, Maria Chatzou, Evan W. Floden (2017)")
        check("oa: --doi records the bare work id", rec["workid"] == "W2605897695")
        check("oa: the api key is absent from the url when the env var is unset",
              len(calls) == 1 and "api_key" not in calls[0])

        # -- the cache is authoritative: a second lookup must not reach the boundary ------
        OA._fetch = lambda url: (_ for _ in ()).throw(
            AssertionError("network reached despite a warm cache"))
        write(src, "Nextflow paper stand-in, edited.\n")     # force a real re-ingest
        ingest_doi("raw/nextflow.txt", "10.1038/nbt.3820")
        check("oa: a warm cache serves the second lookup with no network call", True)
        check("oa: the cached response is one file under wiki/.openalex/",
              [f for f in os.listdir(os.path.join(root, "wiki", ".openalex"))
               if f.endswith(".json")] != [] )

        # -- an explicit title wins, but the id is still recorded -------------------------
        write(src, "Nextflow paper stand-in, edited twice.\n")
        ingest_doi("raw/nextflow.txt", "10.1038/nbt.3820", title="My Own Title")
        rec = E.load_sources(root)["raw/nextflow.txt"]
        check("oa: an explicit --title overrides the fetched one", rec["title"] == "My Own Title")
        check("oa: the work id is recorded even when --title overrides", rec["workid"] == "W2605897695")

        # -- a re-ingest with no doi keeps the id already on record ----------------------
        write(src, "Nextflow paper stand-in, edited thrice.\n")
        E.cmd_ingest(root, "raw/nextflow.txt", title="My Own Title")
        check("oa: a plain re-ingest does not drop a known work id",
              E.load_sources(root)["raw/nextflow.txt"]["workid"] == "W2605897695")

        # -- a DOI attached to an already-registered, unchanged source must stick ---------
        write(os.path.join(root, "raw", "later.txt"), "Registered first, DOI attached later.\n")
        E.cmd_ingest(root, "raw/later.txt", title="Later Paper")
        check("oa: a source registered with --title alone carries no work id",
              E.load_sources(root)["raw/later.txt"]["workid"] == "")
        state, _ = ingest_doi("raw/later.txt", "10.1038/nbt.3820", title="Later Paper")
        check("oa: attaching a DOI later records the id although the bytes are unchanged",
              E.load_sources(root)["raw/later.txt"]["workid"] == "W2605897695" and state == "unchanged")
        check("oa: attaching a DOI to unchanged bytes adds no duplicate log line",
              len(re.findall(r"^## \[.*\] ingest \| Later Paper$",
                             read(os.path.join(root, "wiki", "log.md")), re.M)) == 1)

        # -- cold cache + no key + a dead boundary = a CruxError naming the remedy --------
        OA._fetch = lambda url: (_ for _ in ()).throw(OSError("no route to host"))
        write(os.path.join(root, "raw", "other.txt"), "Another source.\n")
        try:
            ingest_doi("raw/other.txt", "10.1234/nope")
            check("oa: a cold lookup with no key fails as a CruxError", False)
            check("oa: the error names OPENALEX_API_KEY and the daily budget", False)
        except E.CruxError as e:
            check("oa: a cold lookup with no key fails as a CruxError", True)
            check("oa: the error names OPENALEX_API_KEY and the daily budget",
                  "OPENALEX_API_KEY" in str(e) and "$1" in str(e))
        expect_error("oa: a non-DOI argument is refused before any lookup",
                     lambda: OA.work_by_doi(root, "not-a-doi"))

        # -- ingest without a doi never touches the boundary at all ----------------------
        OA._fetch = lambda url: (_ for _ in ()).throw(
            AssertionError("plain ingest must not call OpenAlex"))
        write(os.path.join(root, "raw", "plain.txt"), "No doi here.\n")
        E.cmd_ingest(root, "raw/plain.txt", title="Plain Paper")
        check("oa: ingest without --doi makes no network call", True)
        check("oa: validate stays offline on a vault that holds an openalex cache",
              isinstance(E.cmd_validate(root), list))
    finally:
        OA._fetch = real_fetch
    shutil.rmtree(root, ignore_errors=True)


# --- spec 17.2 — the crawl and the ranking --------------------------------------------
# A frozen fixture graph with hand-checked arithmetic. The shape is chosen so that the one
# thing the ranking exists to do is visible in the output: CLASSIC is cited 100,000 times
# and is reached by every seed, yet must rank BELOW works a fraction as famous, because
# everything reaches it and that is precisely why it carries no information about this
# problem.
#
#   seeds        S1, S2, S3
#   backward     S1 -> A, B    S2 -> A, C    S3 -> A, D
#   forward      S1 <- E       S2 <- E       S3 <- F
#   hubs         A (3 seeds), E (2 seeds)      -- B, C, D, F have one seed each, no expansion
#   depth 2      A -> G, CLASSIC               E -> CLASSIC
_OA_CITES = {"CLASSIC": 100000, "A": 50, "B": 40, "C": 30, "D": 20, "E": 60, "F": 10, "G": 10,
             "S1": 5, "S2": 5, "S3": 5}
_OA_REFS = {"S1": ["A", "B"], "S2": ["A", "C"], "S3": ["A", "D"],
            "A": ["G", "CLASSIC"], "E": ["CLASSIC"]}
_OA_CITERS = {"S1": ["E"], "S2": ["E"], "S3": ["F"]}

def _norm(t):
    return "".join(c for c in (t or "").lower() if c.isalnum())

def _oa_work(wid):
    # S1DUP is S1 under a second OpenAlex id: same title, different id — the shape OpenAlex
    # really carries for a paper deposited twice.
    return {"id": "https://openalex.org/" + wid,
            "display_name": "Work " + ("S1" if wid == "S1DUP" else wid),
            "publication_year": 2020, "cited_by_count": _OA_CITES.get(wid, 0),
            "doi": "https://doi.org/10.1234/" + wid.lower(),   # real DOI shape: 10.NNNN/…
            "best_oa_location": {"pdf_url": "https://x/" + wid + ".pdf"},
            "referenced_works": ["https://openalex.org/" + r for r in _OA_REFS.get(wid, [])],
            "authorships": [{"author": {"display_name": "A Author"}}]}

def _oa_graph_fetch(calls):
    """Serve the fixture graph from the url alone, the way the live API would."""
    import urllib.parse as U
    def fetch(url):
        calls.append(url)
        if "/works/https://doi.org/" in url:      # the singleton DOI lookup
            wid = url.split("/works/https://doi.org/")[1].split("?")[0].split("/")[-1].upper()
            if wid in _OA_CITES:
                return json.dumps(_oa_work(wid))
            raise AssertionError("unknown fixture DOI: " + url)
        q = U.parse_qs(U.urlparse(url).query)
        f = q.get("filter", [""])[0]
        if f.startswith("openalex_id:"):
            ids = f[len("openalex_id:"):].split("|")
            return json.dumps({"results": [_oa_work(i) for i in ids if i in _OA_CITES]})
        if f.startswith("cites:"):
            src = f[len("cites:"):]
            out = sorted(_OA_CITERS.get(src, []), key=lambda w: -_OA_CITES.get(w, 0))
            return json.dumps({"results": [_oa_work(w) for w in out]})
        raise AssertionError("unexpected crawl query: " + url)
    return fetch

def run_lit_crawl():
    """Spec 17.2 — seed-reach ranking over a frozen citation subgraph."""
    print("\n# literature crawl + ranking (spec 17.2)")
    import openalex as OA
    root = tempfile.mkdtemp(prefix="crux_lit_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Lit Demo", root, goal="Exercise the crawl.")
    os.environ.pop("OPENALEX_API_KEY", None)
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    real_fetch, calls = OA._fetch, []
    OA.LAST_LIMITS.clear()

    expect_error("lit: a crawl with no seeds refuses rather than writing an empty list",
                 lambda: OA.crawl(root, []))

    try:
        OA._fetch = _oa_graph_fetch(calls)
        rows = OA.crawl(root, ["S1", "S2", "S3"])
        by = {r["workid"]: r for r in rows}

        # -- the arithmetic, checked by hand ------------------------------------------
        # A: three seeds at depth 1        -> reach 3.0, 3.0 / log10(110)        = 1.4696
        # E: two seeds at depth 1          -> reach 2.0, 2.0 / log10(110)        = 0.9798
        # B: one seed at depth 1           -> reach 1.0, 1.0 / log10(110)        = 0.4899
        # G: one hub (A) at depth 2        -> reach 0.5, 0.5 / log10(110)        = 0.2449
        # CLASSIC: two hubs (A, E)         -> reach 1.0, 1.0 / log10(100010)     = 0.2000
        # Citations below CITES_FLOOR=100 do not move the divisor, so A/E/B/G all divide by
        # log10(110) despite having 50, 60, 40 and 10 citations.
        check("lit: reach is one per distinct seed at depth 1",
              by["A"]["reach"] == 3.0 and by["A"]["seeds"] == 3 and by["A"]["hubs"] == 0
              and by["E"]["reach"] == 2.0 and by["E"]["seeds"] == 2)
        check("lit: a depth-2 work counts the HUBS that reach it, not those hubs' seeds — "
              "one hub is half a point, not that hub's whole seed set",
              by["G"]["hubs"] == 1 and by["G"]["seeds"] == 0 and by["G"]["reach"] == 0.5
              and by["CLASSIC"]["hubs"] == 2 and by["CLASSIC"]["reach"] == 1.0)
        check("lit: the score is reach / log10(10 + max(citations, 100))",
              abs(by["A"]["score"] - 1.4696) < 5e-4
              and abs(by["G"]["score"] - 0.2449) < 5e-4
              and abs(by["CLASSIC"]["score"] - 0.2000) < 5e-4)
        check("lit: the citation floor means obscurity is not rewarded — equal reach and "
              "both under the floor scores equal, and the better-cited one wins the tie",
              by["B"]["score"] == by["C"]["score"] == by["D"]["score"] == by["F"]["score"]
              and by["B"]["rank"] < by["C"]["rank"] < by["D"]["rank"] < by["F"]["rank"])
        check("lit: a work with 100,000 citations, reached only through hubs, ranks last — "
              "the divisor demotes the field's furniture",
              by["CLASSIC"]["rank"] == len(rows))
        check("lit: rank 1 is the work the most seeds reach at depth 1", rows[0]["workid"] == "A")
        check("lit: rows are sorted best-first and ranked from 1",
              [r["rank"] for r in rows] == list(range(1, len(rows) + 1))
              and all(rows[i]["score"] >= rows[i + 1]["score"] for i in range(len(rows) - 1)))

        # -- who is and is not a candidate ---------------------------------------------
        check("lit: a seed is never its own candidate",
              not ({"S1", "S2", "S3"} & set(by)))
        check("lit: both directions are walked and recorded",
              by["B"]["direction"] == "backward" and by["E"]["direction"] == "forward")
        check("lit: depth is recorded and depth-2 works are present",
              by["A"]["depth"] == 1 and by["G"]["depth"] == 2)

        # -- depth-2 expansion is gated on reach >= 2 ----------------------------------
        import urllib.parse as _U
        asked = {_U.parse_qs(_U.urlparse(c).query).get("filter", [""])[0] for c in calls}
        expanded = {w for w in ("A", "E", "B", "C", "D", "F") if "cites:" + w in asked}
        check("lit: only hubs that two or more seeds reach expand to depth 2",
              expanded == {"A", "E"})

        # -- a warm cache reproduces the run with no network at all --------------------
        first = OA.write_candidates(root, "demo", rows)
        before = read(first)
        OA._fetch = lambda url: (_ for _ in ()).throw(
            AssertionError("network reached despite a warm cache"))
        rows2 = OA.crawl(root, ["S1", "S2", "S3"])
        OA.write_candidates(root, "demo", rows2)
        check("lit: a re-run from a warm cache is free and byte-identical",
              read(first) == before and rows2 == rows)
        check("lit: the candidate list is a TSV under wiki/lit/<slug>/",
              first.endswith(os.path.join("wiki", "lit", "demo", "candidates.tsv"))
              and before.splitlines()[0].split("\t")[:5] == ["rank", "score", "reach", "seeds", "hubs"])

        OA._fetch = _oa_graph_fetch(calls)      # back on the wire for the sections below

        # -- a source already curated into raw/ is not offered again -------------------
        write(os.path.join(root, "raw", "a.txt"), "already have this one\n")
        E.cmd_ingest(root, "raw/a.txt", title="Work A", workid="A")
        rows3 = OA.crawl(root, ["S1", "S2", "S3"])
        check("lit: a work already registered in raw/ is not offered as a candidate",
              "A" not in {r["workid"] for r in rows3})

        # -- a seed's duplicate record, under a second id, is not a candidate -----------
        _OA_CITES["S1DUP"] = 400
        _OA_CITERS["S2"] = ["E", "S1DUP"]
        try:
            rows4 = OA.crawl(root, ["S1", "S2", "S3"])
            dup = _oa_work("S1DUP"); dup["display_name"] = "Work S1"
            check("lit: a duplicate OpenAlex record of a seed is dropped, not ranked first",
                  "S1DUP" in {c for c in _OA_CITES}
                  and not [r for r in rows4
                           if _norm(r["title"]) == _norm("Work S1 — A Author (2020)")])
        finally:
            _OA_CITERS["S2"] = ["E"]; _OA_CITES.pop("S1DUP", None)

        # -- the budget refusal ---------------------------------------------------------
        OA.LAST_LIMITS["remaining"] = 1
        expect_error("lit: a crawl that cannot finish inside the daily budget refuses",
                     lambda: OA.crawl(root, ["S1", "S2", "S3", "E", "F", "G", "B"]))
        OA.LAST_LIMITS.clear()
    finally:
        OA._fetch = real_fetch
        OA.LAST_LIMITS.clear()
    shutil.rmtree(root, ignore_errors=True)


# --- spec 17.3 — the scoping skill's file and its lint --------------------------------
# The skill writes; the engine checks. Same split as PRD 05.5: the setup skill is not
# unit-tested, the grammar it writes against is. These run against the PRD alone, so every
# call to a name the engine may not carry yet is guarded.

_SCOPE_OK = """---
type: lit-scope
slug: chromatin
---

## Problem

Which segmentation methods annotate chromatin state from histone ChIP-seq, and what do they
report as their baseline?

## Seeds

- 10.1038/nmeth.1906
- W4230875896
- W2076154138

## Out of scope

- single-cell assays
"""

def _scope_val(fn, default=None):
    try:
        return fn()
    except (AttributeError, TypeError, KeyError):
        return default

def run_lit_scope():
    """Spec 17.3 — wiki/lit/<slug>/scope.md, and the lint the skill writes against."""
    print("\n# literature scope + lint (spec 17.3)")
    root = tempfile.mkdtemp(prefix="crux_scope_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Scope Demo", root, goal="Exercise the scoping file.")
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    write(os.path.join(root, "raw", "chromhmm.txt"), "seed one\n")
    E.cmd_ingest(root, "raw/chromhmm.txt", title="ChromHMM", workid="W1598350571")
    reg = E.load_sources(root)
    reg["raw/chromhmm.txt"]["doi"] = "10.1038/nmeth.1906"   # tolerated if unsupported

    def slugs(text, slug="chromatin"):
        sc = _scope_val(lambda: E.parse_scope(text))
        if sc is None:
            return None
        ps = _scope_val(lambda: E.scope_problems(root, sc, slug))
        return None if ps is None else {p["check"] for p in ps}

    check("scope: a well-formed scope parses into problem, seeds and out-of-scope",
          _scope_val(lambda: (lambda sc: (
              sc["seeds"] == ["10.1038/nmeth.1906", "W4230875896", "W2076154138"]
              and sc["problem"].startswith("Which segmentation")
              and "single-cell" in sc["out_of_scope"]))(E.parse_scope(_SCOPE_OK))) is True)

    check("scope: a well-formed scope lints clean", slugs(_SCOPE_OK) == set())

    two = _SCOPE_OK.replace("- W4230875896\n- W2076154138\n", "")
    check("scope: fewer than three seeds is a finding",
          slugs(two) == {"scope-seed-count"})

    nine = _SCOPE_OK.replace("- W2076154138\n",
                             "".join(f"- W{9000000 + i}\n" for i in range(7)))
    check("scope: more than eight seeds is a finding",
          slugs(nine) == {"scope-seed-count"})

    dup = _SCOPE_OK.replace("- W2076154138", "- W4230875896")
    check("scope: a seed listed twice is a finding",
          slugs(dup) == {"scope-seed-duplicate", "scope-seed-count"}
          or slugs(dup) == {"scope-seed-duplicate"})

    bad = _SCOPE_OK.replace("- W2076154138", "- the ChromHMM paper")
    check("scope: a seed that is neither a work id nor a DOI is a finding, not a crash",
          slugs(bad) == {"scope-seed-unknown"})

    empty = _SCOPE_OK.replace("Which segmentation methods annotate chromatin state from "
                              "histone ChIP-seq, and what do they\nreport as their baseline?",
                              "")
    check("scope: an empty problem statement is a finding",
          slugs(empty) == {"scope-problem-empty"})

    longp = _SCOPE_OK.replace("report as their baseline?",
                              "report as their baseline? " + ("word " * (E.PROSE_CAP + 20)))
    check("scope: a problem statement over the prose cap is a finding",
          slugs(longp) == {"scope-problem-long"})

    check("scope: a slug that disagrees with its directory is a finding",
          slugs(_SCOPE_OK, slug="something-else") == {"scope-slug"})

    check("scope: every problem is reported in one pass, not just the first",
          (slugs(_SCOPE_OK.replace("- W2076154138", "- the ChromHMM paper")
                          .replace("Which segmentation", "")) or set())
          >= {"scope-seed-unknown"})

    # -- the skill itself: it exists, it is not bloated, and scope.md is its only output --
    # An absolute cap, not "under crux-autopilot". The PRD's original bar was a proxy for
    # "not bloated", written when this skill covered one flow; it now documents three verbs
    # that autopilot has no equivalent of, and trimming to beat an arbitrary comparison would
    # have cost the fetch section rather than any fat.
    sk = os.path.join(HERE, "..", "..", "crux-litsearch", "SKILL.md")
    have = os.path.isfile(sk)
    body = read(sk) if have else ""
    check("scope: the crux-litsearch skill ships and stays inside its 130-line cap",
          have and 0 < len(body.splitlines()) <= 130)
    check("scope: the skill names scope.md as its output and refuses to write raw/ itself",
          "wiki/lit/<slug>/scope.md" in body and "The PI curates `raw/`" in body
          and "crux lit lint" in body)

    # -- the crawl prefers the scope's seeds, and works without one ---------------------
    import openalex as OA
    real_fetch, calls = OA._fetch, []
    try:
        OA._fetch = _oa_graph_fetch(calls)
        OA.LAST_LIMITS.clear()
        path = _scope_val(lambda: E.scope_path(root, "fixture"))
        check("scope: the scope file lives at wiki/lit/<slug>/scope.md",
              bool(path) and path.endswith(os.path.join("wiki", "lit", "fixture", "scope.md")))
        if path:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            # the fixture graph under W-shaped ids, because a seed must look resolvable
            for n, src in (("W1001", "S1"), ("W1002", "S2"), ("W1003", "S3")):
                _OA_CITES[n] = _OA_CITES[src]
                _OA_REFS[n] = _OA_REFS[src]
                _OA_CITERS[n] = _OA_CITERS[src]
            write(path, _SCOPE_OK.replace("slug: chromatin", "slug: fixture")
                                 .replace("- 10.1038/nmeth.1906", "- W1001")
                                 .replace("- W4230875896", "- W1002")
                                 .replace("- W2076154138", "- W1003"))
            calls.clear()
            rows = _scope_val(lambda: OA.crawl_scope(root, "fixture"))
            import urllib.parse as _U
            asked = {_U.parse_qs(_U.urlparse(c).query).get("filter", [""])[0] for c in calls}
            check("scope: a crawl driven by a scope uses the scope's seeds",
                  rows is not None and {"cites:W1001", "cites:W1002", "cites:W1003"} <= asked)
            check("scope: and does not seed from the whole registry",
                  "cites:W1598350571" not in asked)

            # a DOI seed must become a work id first; _bare() alone would shear
            # "10.1/w1001" down to "w1001" and query for a work that does not exist
            write(path, read(path).replace("- W1001", "- 10.1234/w1001"))
            calls.clear()
            rows5 = _scope_val(lambda: OA.crawl_scope(root, "fixture"))
            # the graph queries are already cached, so the proof is the result, not the
            # traffic: the same crawl under a DOI seed must come out identical, and the only
            # new request may be the DOI's own singleton lookup
            check("scope: a seed given as a DOI is resolved to a work id before the crawl",
                  rows5 is not None and rows5 == rows
                  and all("/works/https://doi.org/" in c for c in calls))
    finally:
        OA._fetch = real_fetch
        OA.LAST_LIMITS.clear()
        for n in ("W1001", "W1002", "W1003"):
            _OA_CITES.pop(n, None); _OA_REFS.pop(n, None); _OA_CITERS.pop(n, None)
    shutil.rmtree(root, ignore_errors=True)


# --- spec 17.4 — fetching a picked candidate into raw/ --------------------------------
# The only part of crux that writes bytes from the internet into the PI's curated directory,
# so most of this section is about what must NOT land there.

def _pdf(n=2048):
    return b"%PDF-1.7\n" + b"x" * n

def run_lit_fetch():
    """Spec 17.4 — crux lit fetch: download the open-access PDF for a picked candidate and
    ingest it with the canonical title, or refuse and write nothing."""
    print("\n# literature fetch + ingest (spec 17.4)")
    import openalex as OA
    root = tempfile.mkdtemp(prefix="crux_fetch_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Fetch Demo", root, goal="Exercise the fetch path.")
    os.makedirs(os.path.join(root, "raw"), exist_ok=True)
    os.environ.pop("OPENALEX_API_KEY", None)
    real_fetch, real_dl = OA._fetch, getattr(OA, "_download", None)

    def rec(wid, oa="https://repo.example/p.pdf", year=2017, name="Di Tommaso"):
        return {"id": "https://openalex.org/" + wid, "display_name": "Nextflow enables it all",
                "publication_year": year, "cited_by_count": 10,
                "doi": "https://doi.org/10.1234/" + wid.lower(),
                "best_oa_location": ({"pdf_url": oa} if oa else None),
                "authorships": [{"author": {"display_name": name}}]}

    store = {"W1": rec("W1"), "W2": rec("W2", oa=None), "W3": rec("W3")}
    def api(url):
        import urllib.parse as U
        f = U.parse_qs(U.urlparse(url).query).get("filter", [""])[0]
        ids = f.split("openalex_id:")[-1].split("|") if "openalex_id:" in f else []
        return json.dumps({"results": [store[i] for i in ids if i in store]})

    def raw_names():
        return sorted(os.listdir(os.path.join(root, "raw")))

    try:
        OA._fetch = api

        # -- the happy path -------------------------------------------------------------
        OA._download = lambda url, cap: _pdf()
        out = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W1"]))
        names = raw_names()
        check("fetch: the fetch lookup asks for authorships — the registry title is the "
              "vault's only author-bearing field",
              "authorships" in _scope_val(lambda: OA.FETCH_SELECT, ""))
        check("fetch: an open-access pick lands in raw/ under a readable derived name",
              len(names) == 1 and names[0].endswith(".pdf")
              and "2017" in names[0] and "tommaso" in names[0].lower())
        reg = E.load_sources(root)
        rel = "raw/" + names[0] if names else ""
        check("fetch: the downloaded file is ingested with the canonical title and work id",
              rel in reg and reg[rel]["workid"] == "W1"
              and reg[rel]["title"].startswith("Nextflow enables it all — Di Tommaso (2017)"))

        # -- a pick already on record is skipped, not re-downloaded ---------------------
        OA._download = lambda url, cap: (_ for _ in ()).throw(
            AssertionError("re-downloaded a work already in the registry"))
        out2 = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W1"]))
        check("fetch: a pick already in raw/ is skipped rather than fetched again",
              out2 is not None and raw_names() == names)

        # -- not a PDF: nothing may land, and the run carries on --------------------------
        before = raw_names()
        OA._download = lambda url, cap: b"<html>403 Forbidden</html>"
        res = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W3"]))
        check("fetch: a response that is not a PDF is refused and reported, not raised",
              res is not None and res[0]["state"] == "failed"
              and "did not return a PDF" in res[0]["reason"])
        check("fetch: and nothing is written to raw/ when it is refused", raw_names() == before)

        # -- a gated publisher is one pick's problem, not the run's -----------------------
        def _gated(url, cap):
            raise E.CruxError("the host refused the request (403)")
        OA._download = _gated
        res = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W3"]))
        check("fetch: a publisher that refuses the request is reported against that pick "
              "alone — one gated host must not sink a ten-pick run",
              res is not None and res[0]["state"] == "failed" and "403" in res[0]["reason"])

        # -- over the size cap: refused before it is written -----------------------------
        def _toobig(url, cap):
            raise E.CruxError(f"is larger than the {cap} byte cap")
        OA._download = _toobig
        res = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W3"]))
        check("fetch: a download over the size cap is refused",
              res is not None and res[0]["state"] == "failed" and "cap" in res[0]["reason"])
        check("fetch: and nothing is written to raw/ when it is over the cap",
              raw_names() == before)
        check("fetch: the cap is 50 MB", _scope_val(lambda: OA.PDF_CAP_BYTES) == 50 * 1024 * 1024)

        # -- a pick with no open-access url is reported, and does not sink the run --------
        OA._download = lambda url, cap: _pdf()
        res = _scope_val(lambda: OA.fetch_picks(root, "demo", ["W2", "W3"]))
        got = raw_names()
        check("fetch: a pick with no open-access pdf writes nothing and is reported with its DOI",
              res is not None
              and any(r.get("workid") == "W2" and r.get("state") == "no-oa"
                      and "10.1234/w2" in (r.get("doi") or "") for r in res))
        check("fetch: and the other picks in the same run still land",
              len(got) == len(before) + 1
              and any(r.get("workid") == "W3" and r.get("state") == "ingested" for r in res))

        # -- a filename collision gets a suffix rather than an overwrite -----------------
        store["W4"] = rec("W4")                 # same author, year and title as W1
        OA._download = lambda url, cap: _pdf(4096)
        _scope_val(lambda: OA.fetch_picks(root, "demo", ["W4"]))
        final = raw_names()
        check("fetch: a filename collision takes a suffix and overwrites nothing",
              len(final) == len(got) + 1 and len(set(final)) == len(final))
    finally:
        OA._fetch = real_fetch
        if real_dl is not None:
            OA._download = real_dl
    shutil.rmtree(root, ignore_errors=True)


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["finding", "--help"], ["hypothesize", "--help"],
                 ["serve", "--help"], ["selftest", "--help"], ["park", "--help"],
                 ["wrap", "--help"], ["pending", "--help"], ["sweep", "--help"], ["deck", "--help"],
                 ["brief", "--help"], ["glossary", "--help"], ["doctor", "--help"],
                 ["auto", "--help"], ["auto", "check", "--help"],
                 ["auto", "run", "--help"], ["auto", "status", "--help"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True, encoding="utf-8")
        # `auto` is PRD 05.0's own verb: its check is named with the autopilot prefix the
        # rest of that PRD's checks carry, so a wave-1 red line is attributable at a glance.
        nm = f"help: crux {' '.join(argv)}"
        check(f"auto: {nm}" if argv[0] == "auto" else nm,
              r.returncode == 0 and len(r.stdout) > 40)
        if argv == ["auto", "--help"]:
            verbs = re.findall(r"^    ([a-z]+)\s", r.stdout, re.M)
            check("auto: help lists exactly the verbs check, run, status (spec 18)",
                  verbs == ["check", "run", "status"])

    # -- spec 19: a removed verb answers with one pointer line naming its replacement
    for argv in (["close"], ["approve"], ["synthesize"], ["review"], ["answer"], ["pursue"],
                 ["approve-null"], ["task", "accept"], ["task", "review"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True, encoding="utf-8")
        check(f"help: crux {' '.join(argv)} says it is removed",
              "is removed" in r.stdout + r.stderr)

    # -- the post-init hint must work from where the user just ran init: the vault is
    #    created *below* the cwd, so the hint carries the cd into it
    tmp = tempfile.mkdtemp(prefix="crux-hint-")
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "init", "Hint Project"],
                           capture_output=True, text=True, encoding="utf-8", cwd=tmp)
        check("init hint: includes `cd cruxvault`", r.returncode == 0 and "cd cruxvault" in r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


REPO = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))   # <clone>/skills/crux/scaffold -> <clone>


def _byte_map(root):
    """{relpath: sha256} for EVERY file under root — `.crux.yaml` included.

    Deliberately not `fingerprint()`: that one excludes the engine-version stamp, because an
    upgrade is *supposed* to rewrite it. doctor is the one verb for which rewriting the stamp
    would be a bug — it would silently repair the drift it is reporting — so here nothing is
    excluded."""
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            with open(p, "rb") as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def _level(res, name):
    for c in res["checks"]:
        if c["name"] == name:
            return c["level"]
    return None


def _check(res, name):
    return next((c for c in res["checks"] if c["name"] == name), None)


def run_doctor():
    """`crux doctor` — the deterministic install + drift health check.

    Every failure in INSTALL.md's troubleshooting list is a state a machine can read, and
    the worst one is silent: install.sh symlinks skills and agents INTO the clone, so moving
    the clone leaves dangling links and the skills stop working with no error anywhere.

    The whole verb is os.path calls and two string compares, which is the argument for it
    being a verb rather than an agent — it runs from a bare clone with no agent present, and
    a checklist with no judgment in it can be gated by this suite."""
    print("\n# crux doctor — install + drift health")
    tmp = tempfile.mkdtemp(prefix="crux_doc_")
    try:
        skills_ok  = os.path.join(tmp, "skills_ok");   os.makedirs(skills_ok)
        skills_bad = os.path.join(tmp, "skills_bad");  os.makedirs(skills_bad)
        skills_none = os.path.join(tmp, "skills_none"); os.makedirs(skills_none)
        os.symlink(os.path.join(REPO, "skills", "crux"), os.path.join(skills_ok, "crux"))
        os.symlink(os.path.join(tmp, "gone"), os.path.join(skills_bad, "crux"))

        roster = sorted(d for d in os.listdir(os.path.join(REPO, "agents"))
                        if os.path.isfile(os.path.join(REPO, "agents", d, "AGENT.md")))
        def agents_dir(names, dangle=False):
            d = tempfile.mkdtemp(prefix="crux_ag_", dir=tmp)
            for n in names:
                os.symlink(os.path.join(REPO, "agents", n, "AGENT.md"), os.path.join(d, n + ".md"))
            if dangle:
                os.symlink(os.path.join(tmp, "gone"), os.path.join(d, "crux-ghost.md"))
            return d
        ag_full  = agents_dir(roster)
        ag_short = agents_dir(roster[:-1])
        ag_dang  = agents_dir(roster, dangle=True)

        # ---------------------------------------------------------------- shape
        res = E.cmd_doctor(root=None, skills_dirs=[skills_ok], agents_dir=ag_full)
        check("doctor: returns ok + checks + both versions",
              set(res) >= {"ok", "checks", "crux_version", "engine_version"}
              and res["crux_version"] == E.CRUX_VERSION and res["engine_version"] == E.ENGINE_VERSION)
        check("doctor: every check carries name, level and detail",
              res["checks"] and all(c.get("name") and c.get("detail") is not None
                                    and c.get("level") in ("ok", "warn", "fail") for c in res["checks"]))
        check("doctor: python and engine are ok on a working install",
              _level(res, "python") == "ok" and _level(res, "engine") == "ok")

        # ---------------------------------------------------------------- skills linkage
        check("doctor: a symlink resolving into this repo is ok", _level(res, "skills") == "ok")
        bad = E.cmd_doctor(root=None, skills_dirs=[skills_bad], agents_dir=ag_full)
        check("doctor: a DANGLING skill symlink fails — the silent breakage, made loud",
              _level(bad, "skills") == "fail" and bad["ok"] is False)
        none = E.cmd_doctor(root=None, skills_dirs=[skills_none], agents_dir=ag_full)
        check("doctor: no crux in any skills dir WARNS — a bare clone is a supported install",
              _level(none, "skills") == "warn" and none["ok"] is True)

        # ---------------------------------------------------------------- agent roster
        check("doctor: the full roster is ok", _level(res, "agents") == "ok")
        short = E.cmd_doctor(root=None, skills_dirs=[skills_ok], agents_dir=ag_short)
        check("doctor: a roster short of the repo's warns — a stale install.sh",
              _level(short, "agents") == "warn" and short["ok"] is True)
        dang = E.cmd_doctor(root=None, skills_dirs=[skills_ok], agents_dir=ag_dang)
        check("doctor: a dangling agent symlink fails",
              _level(dang, "agents") == "fail" and dang["ok"] is False)
        # spec 19: a fresh install is the four-agent roster plus crux-tests, which now lives
        # with evolve-crux (Q12). Doctor reports it with nothing dangling. A link left behind
        # by an agent spec 19 removed is exactly what install.sh's stale-link sweep deletes.
        fresh = agents_dir(roster)
        os.symlink(os.path.join(REPO, "skills", "evolve-crux", "agents", "crux-tests.md"),
                   os.path.join(fresh, "crux-tests.md"))
        fr = E.cmd_doctor(root=None, skills_dirs=[skills_ok], agents_dir=fresh)
        check("doctor: a fresh spec-19 install (four agents + crux-tests) reports no dangling agent",
              len(roster) == 4 and _level(fr, "agents") == "ok"
              and _check(fr, "agents")["detail"].startswith("5 crux-*.md in "))
        os.symlink(os.path.join(REPO, "agents", "crux-close", "AGENT.md"),
                   os.path.join(fresh, "crux-close.md"))
        fr = E.cmd_doctor(root=None, skills_dirs=[skills_ok], agents_dir=fresh)
        check("doctor: a link left by a removed agent dangles and fails until install.sh sweeps it",
              _level(fr, "agents") == "fail" and "crux-close" in _check(fr, "agents")["detail"])

        # ---------------------------------------------------------------- vault drift + migrate
        drift = os.path.join(tmp, "drifted")
        import selftest_migrate as SM     # the shipped demo is 4.0; this is its captured 1.2 form
        SM.captured_demo(drift)
        stamped = E.yaml_load(read(os.path.join(drift, E.VAULT_MARKER)))["engine_version"]
        before = _byte_map(drift)
        dr = E.cmd_doctor(root=drift, skills_dirs=[skills_ok], agents_dir=ag_full)
        check("doctor: an old-stamped vault warns, naming both versions",
              _level(dr, "vault") == "warn"
              and str(stamped) in _check(dr, "vault")["detail"]
              and E.ENGINE_VERSION in _check(dr, "vault")["detail"])
        check("doctor: drift is a warn, not a fail — the vault still reads", dr["ok"] is True)
        check("doctor: pending structural sections warn",
              _level(dr, "migrate") == "warn" and "crux migrate" in _check(dr, "migrate")["fix"])

        # THE LINE: doctor reports drift and must never be the thing that repairs it.
        check("doctor: writes NOTHING — the engine stamp included", _byte_map(drift) == before)

        clean = os.path.join(tmp, "clean"); os.makedirs(clean)
        E.cmd_init("Doctor Clean", clean)
        cl = E.cmd_doctor(root=clean, skills_dirs=[skills_ok], agents_dir=ag_full)
        check("doctor: a current vault is ok on both vault checks",
              _level(cl, "vault") == "ok" and _level(cl, "migrate") == "ok")

        # ---------------------------------------------------------------- the fix line
        for r in (bad, none, short, dang, dr):
            check("doctor: every non-ok check hands over a fix command",
                  all(c.get("fix") for c in r["checks"] if c["level"] != "ok"))

        # ---------------------------------------------------------------- CLI contract
        cli = [sys.executable, os.path.join(HERE, "crux.py"), "doctor"]
        r = subprocess.run(cli + ["--json"], capture_output=True, text=True,
                           encoding="utf-8", cwd=clean)
        check("doctor: --json prints exactly one object on stdout",
              r.returncode == 0 and isinstance(json.loads(r.stdout), dict))
        r = subprocess.run(cli + ["--json"], capture_output=True, text=True,
                           encoding="utf-8", cwd=tmp)
        names = [c["name"] for c in json.loads(r.stdout)["checks"]]
        check("doctor: runs with NO vault in sight — the state a broken install is in",
              r.returncode in (0, 1) and "vault" not in names and "migrate" not in names)
        check("doctor: no vault means no traceback", "Traceback" not in r.stderr)
        check("doctor: the install checks still all ran",
              names == ["python", "engine", "skills", "agents", "voice-hook", "version"])

        # -- the exit code IS the contract: warns are scriptable, a fail is not.
        before_cli = _byte_map(drift)
        r = subprocess.run(cli, capture_output=True, text=True, encoding="utf-8", cwd=drift)
        check("doctor: warns alone exit 0 — drift is reportable, not fatal", r.returncode == 0)
        check("doctor: the CLI path writes nothing either", _byte_map(drift) == before_cli)

        home = os.path.join(tmp, "home"); os.makedirs(os.path.join(home, ".claude", "skills"))
        os.symlink(os.path.join(tmp, "gone"), os.path.join(home, ".claude", "skills", "crux"))
        env = dict(os.environ, HOME=home, USERPROFILE=home)
        r = subprocess.run(cli, capture_output=True, text=True, encoding="utf-8", cwd=clean, env=env)
        check("doctor: any fail exits 1", r.returncode == 1 and "FAIL" in r.stdout)
        check("doctor: and the fix is printed next to it", "install.sh" in r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# Every old section, in its historical order. Each runs inside `_section`, so one that raises
# is ONE failure line and the rest still run — a crash in one section must never hide the
# state of every section after it.
SECTIONS = (run_seed,
            run_wiki,
            run_wiki_migration,
            run_version,
            run_integrity,
            run_artifacts,
            run_update,
            run_snapshot,
            run_wiki_gui,
            run_serve,
            run_file_route,
            run_webui,
            run_economy,
            run_economy_migration,
            run_agent_cli,
            run_rd,
            run_rd_migration,
            run_rd_lint,
            run_rd_skill,
            run_deck_rd,
            run_rd_gui,
            run_deck,
            run_deck_verify,
            run_prezit,
            run_storify_engine,
            run_storify_skill,
            run_evidence_boundary,
            run_verifiable_kind,
            run_combination_rule,
            run_hash_lock,
            run_rulebook,
            run_taskhub,
            run_task_graph,
            run_experiments,
            run_task_gui,
            run_taskhub_skill,
            run_cockpit_evidence,
            run_brief,
            run_null,
            run_failure_scenarios,
            run_migrate,
            run_agent_roster,
            run_situate,
            run_situate_agent,
            run_methodology,
            run_methodology_migration,
            run_design_agent,
            run_science_voice,
            run_correct_terms,
            run_situate_title_anchor,
            run_cli_third_person,
            run_voice_enforcement,
            run_persona_eval,
            run_glossary,
            run_glossary_migration,
            run_glossary_counting,
            run_glossary_oracle,
            run_glossary_filter,
            run_sortlab_fixture,
            run_glossary_write,
            run_agent_evals,
            run_eval_scorer,
            run_mutation_harness,
            run_ground_truth_fixtures,
            run_proxy_register,
            run_openalex,
            run_lit_crawl,
            run_lit_scope,
            run_lit_fetch,
            run_cli_help,
            run_doctor)


def _section(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        check(f"{fn.__name__} crashed: {type(e).__name__}: {e}", False)
        return None


def _module_suites():
    """Every `selftest_*.py` module beside this file, sorted, each exposing `run_all(check)`.
    A new chunk adds a module and never edits `main()` (spec 19 build plan, shared-file rule)."""
    import importlib
    names = sorted(fn[:-3] for fn in os.listdir(HERE)
                   if fn.startswith("selftest_") and fn.endswith(".py"))
    out = []
    for name in names:
        try:
            out.append((name, importlib.import_module(name)))
        except Exception as e:
            check(f"{name} imports ({type(e).__name__}: {e})", False)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default=None, help="build the demo vault at this path and keep it")
    a = ap.parse_args()
    # the suite is hermetic: no crux invocation it spawns may reach the network for an
    # update check (the check's own logic is exercised offline with an injected fetcher).
    os.environ["CRUX_NO_UPDATE_CHECK"] = "1"
    root = _section(run_demo, a.keep)
    for fn in SECTIONS:
        _section(fn)
    for name, mod in _module_suites():
        print(f"\n# {name}")
        keep_env = dict(os.environ)
        try:
            mod.run_all(check)
        except Exception as e:
            check(f"{name} crashed: {type(e).__name__}: {e}", False)
        finally:
            os.environ.clear()
            os.environ.update(keep_env)
    print(f"\n{'='*48}\n  PASSED {len(_PASS)} / {len(_PASS)+len(_FAIL)}")
    if _FAIL:
        print("  FAILURES:")
        for f in _FAIL: print("   - " + f)
        sys.exit(1)
    print(f"  demo vault {'kept at '+root if a.keep else '(temp, removed)'}")
    if not a.keep and root:
        shutil.rmtree(root, ignore_errors=True)
    print("  ALL GREEN")


if __name__ == "__main__":
    main()
