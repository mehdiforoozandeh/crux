#!/usr/bin/env python3
"""End-to-end self-test for crux — builds a dummy vault and asserts every
invariant. No GPU / tokens / SLURM; pure file ops. Exit non-zero on any failure.

    python selftest.py [--keep DIR]   # --keep leaves the demo vault for inspection
"""
import os, sys, shutil, tempfile, subprocess, argparse, hashlib, re, json
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
    """Bring a fixture hypothesis up to everything the pre-run gates require, the way the
    real flow does: a declared and PI-approved null (`crux-null` + `crux approve-null`), and
    a distinct failure scenario on every check with one marked as discriminating
    (`crux-verifiables`). Idempotent, so it is safe before every `--to running`.

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
    E.cmd_approve_null(root, hid)



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

    # 3. hypothesize two leaves with 2 verifiables each
    h1, _, _ = E.cmd_hypothesize(root, "masked-token beats masked-stem", parent=q11, rule="all",
                                 neutral=["the published stem baseline reproduces to ±0.005"],
                              verifiables=["imp-Spearman ≥ +0.01 vs stem", "no NaN over 5 eval epochs"])
    h2, _, _ = E.cmd_hypothesize(root, "post_conv FiLM beats per_conv", parent=q11, rule="all",
                                 neutral=["the shared preprocessing pass reproduces the reference checksum"],
                              verifiables=["imp-Spearman ≥ +0.005 vs per_conv", "calibration not worse"])
    check("hypothesize: h1 under q1.1", E.Vault(root).get(h1).parent == q11)
    check("hypothesize: 2 claim-directed verifiables + 1 control",
          E.count_verifiables_by_kind(read(node_path(root, h1)))
          == {"hypothesis": (0, 2, 0), "outcome-neutral": (0, 1, 0)})

    # 4. NEGATIVE: running without verifiables is rejected (on a stripped idea)
    h_bad, _, _ = E.cmd_hypothesize(root, "temp bad idea", parent=q11)
    bp = node_path(root, h_bad)
    edit(bp, "- [ ] _(state a falsifiable, pre-registered check)_", "(verifiables removed)")
    expect_error("validator: no running without verifiables", lambda: E.cmd_test(root, h_bad, to="running"))
    os.remove(bp); E.refresh(root)  # discard the throwaway idea

    # 5. test transitions
    E.cmd_test(root, h1, to="staged")
    check("test: h1 staged", E.Vault(root).get(h1).status == "staged")
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running", run="job 40012")
    edit(node_path(root, h1), "- [ ] [outcome-neutral]", "- [x] [outcome-neutral]")
    check("test: h1 running", E.Vault(root).get(h1).status == "running")
    check("test: run link recorded", "job 40012" in read(node_path(root, h1)))
    # REGRESSION: a second --run must APPEND, not vanish. The insert used to be decided by a
    # whole-body `_(none yet)_` probe, so the moment a second section shipped with a
    # placeholder of its own (## Artifacts), every run link after the first was silently
    # dropped — no error, and the CLI still printed success.
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running", run="job 40013")
    links = E._run_links(read(node_path(root, h1)).split("---", 2)[-1])
    check("test: a second --run appends rather than dropping the link",
          links == ["job 40012", "job 40013"])
    check("test: the Artifacts placeholder is untouched by a run link",
          "## Artifacts" in read(node_path(root, h1)))
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    edit(node_path(root, h2), "- [ ] [outcome-neutral]", "- [x] [outcome-neutral]")

    # 6. close: h1 all-met -> supported ; h2 one-unmet -> refuted.
    #    Under evidence semantics (1.8) a declared `all` makes one unmet a veto, so this is
    #    `refuted` where the pre-15 engine returned `partial`. A pre-15 node still gets
    #    `partial` — asserted in run_combination_rule against the captured truth table.
    edit(node_path(root, h1), "- [ ]", "- [x]")               # all met
    v1 = E.cmd_close(root, h1, metric="imp +0.012")
    check("close: h1 supported", v1 == "supported")
    edit(node_path(root, h2), "- [ ]", "- [x]", count=1)       # exactly one met
    v2 = E.cmd_close(root, h2, metric="imp +0.003")
    check("close: h2 refuted under a declared `all` rule (pre-15 this was `partial`)",
          v2 == "refuted")
    check("close: verdict in frontmatter", E.Vault(root).get(h1)["fm"]["verdict"] == "supported")

    # 7. ledger roll-up walks up to the question + META
    q11_text = read(node_path(root, q11))
    check("ledger: q1.1 shows supported", "supported" in q11_text and h1 in q11_text)
    check("ledger: q1.1 shows metric", "imp +0.012" in q11_text)
    check("ledger: META reflects verdicts", "supported" in read(os.path.join(root, "META.md")))

    # 8. gate trips review when all children terminal; interpretation flagged stale
    check("gate: q1.1 -> review", E.Vault(root).get(q11).status == "review")
    check("gate: q1.1 stale flagged", E.Vault(root).get(q11)["fm"]["stale"] is True)
    check("review: queue lists q1.1", q11 in [x[0] for x in E.cmd_review(root)])

    # 9a. answer (resolve) is GATED on an approved synthesis (ENGINE 1.2), then propagates:
    #     q1.1 resolved -> q1 trips review
    expect_error("gate: answer refused without a synthesis",
                 lambda: E.cmd_answer(root, q11, text="premature"))
    syn, _ = E.cmd_synthesize(root, "what q1.1 settled", [q11])
    expect_error("gate: answer refused while the synthesis is unapproved",
                 lambda: E.cmd_answer(root, q11, text="still premature"))
    E.cmd_approve(root, syn)
    check("gate: approve stamps a timestamp", bool(E.Vault(root).get(syn)["fm"].get("approved")))
    E.cmd_answer(root, q11, text="mask_token is the load-bearing knob; FiLM placement is noise.")
    check("gate: resolved question records its synthesis",
          E.Vault(root).get(q11)["fm"].get("synthesis") == syn)
    check("answer: q1.1 resolved", E.Vault(root).get(q11).status == "resolved")
    check("answer: stale cleared", E.Vault(root).get(q11)["fm"]["stale"] is False)
    check("answer: propagates -> q1 review", E.Vault(root).get(q1).status == "review")

    # 9b. pursue (reopen) + spawn a fresh child
    new = E.cmd_pursue(root, q11, idea_title="try mask_token + larger encoder")
    check("pursue: q1.1 reopened", E.Vault(root).get(q11).status == "open")
    check("pursue: spawned a child", new is not None and E.Vault(root).get(new[0]).parent == q11)

    # 10. idempotency: re-running refresh changes nothing
    check("idempotent: refresh #1 no-op", E.refresh(root) is False)
    check("idempotent: refresh #2 no-op", E.refresh(root) is False)

    # 12. EXPERIMENTS.md has a row per hypothesis
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
    check("seed: h2 is a fresh idea", v.get("h2").status == "idea")
    check("seed: h2 has 2 verifiables", sum(E.count_verifiables(read(node_path(root, "h2")))) == 2)
    # tested hypotheses are closed with mechanically-derived verdicts
    check("seed: h1 done+supported", v.get("h1").status == "done" and v.get("h1")["fm"]["verdict"] == "supported")
    check("seed: h4 done+partial", v.get("h4").status == "done" and v.get("h4")["fm"]["verdict"] == "partial")
    check("seed: h3 finding kept", "cleared both bars" in read(node_path(root, "h3")))
    check("seed: h3 evidence kept", "+0.03" in read(node_path(root, "h3")))
    check("seed: q2 ledger shows supported", "supported" in read(node_path(root, "q2")))
    # gate: q3's only child (h4) is terminal -> review
    check("seed: q3 tripped to review", v.get("q3").status == "review")
    # REGRESSION (two-directional gate): q1 momentarily had only a terminal child (h1)
    # during materialize, but its later subquestion q2 is non-terminal -> q1 must stay open
    check("seed: q1 not prematurely in review", v.get("q1").status == "open")
    check("seed: q2 open (fresh child h2 pending)", v.get("q2").status == "open")
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
    edit(n["path"], "## Answer so far", "## Answer so far\n\nSee [[wiki/nonexistent]].")
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
    h1, _, _ = E.cmd_hypothesize(root, "a hyp", parent=q1, verifiables=["x"])
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

    # a vault with a nested question, two closed hypotheses, and a synthesis
    E.cmd_init("Snap", root, goal="Test the snapshot contract.")
    q1, _ = E.cmd_ask(root, "Q one")
    q2, _ = E.cmd_ask(root, "Q two", parent=q1)
    h1, _, _ = E.cmd_hypothesize(root, "h one", parent=q2, verifiables=["a", "b"],
                                 neutral=["control"], rule="all")
    h2, _, _ = E.cmd_hypothesize(root, "h two", parent=q2, verifiables=["a", "b"],
                                 neutral=["control"], rule="all")
    declare_null(root, h2)
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running"); E.cmd_test(root, h2, to="running")
    edit(node_path(root, h1), "- [ ]", "- [x]")             # both met -> supported
    E.cmd_close(root, h1, metric="imp +0.012")
    edit(node_path(root, h2), "- [ ] [outcome-neutral] control",
                              "- [x] [outcome-neutral] control")   # the run was valid...
    edit(node_path(root, h2), "- [ ]", "- [x]", count=1)     # ...one claim met -> refuted
    E.cmd_close(root, h2, metric="imp +0.003")
    syn, _ = E.cmd_synthesize(root, "weave one two", [q1, q2])

    v = E.Vault(root)
    snap = E.snapshot(v)

    # -- top-level shape / serializability
    check("snapshot: top-level keys exact",
          set(snap.keys()) == {"engine_version", "crux_version", "update", "limits",
                               "project", "nodes", "tree", "queue", "wiki", "rd", "tasks"})
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

    # -- tree nesting exactly matches parent links
    def tree_ids(t):
        yield t["id"]
        for c in t["children"]:
            yield from tree_ids(c)
    ids = list(tree_ids(snap["tree"]))
    nonsyn = {nid for nid, n in v.nodes.items() if n.type != "synthesis"}
    check("snapshot: tree root is the project root", snap["tree"]["id"] == v.cfg["root_id"])
    check("snapshot: tree has no duplicate nodes", len(ids) == len(set(ids)))
    check("snapshot: tree covers each parent-linked node once", set(ids) == nonsyn)
    def children_match(t):
        return ([c["id"] for c in t["children"]] == v.children[t["id"]]
                and all(children_match(c) for c in t["children"]))
    check("snapshot: tree children match v.children in order", children_match(snap["tree"]))
    check("snapshot: synthesis in nodes but not in the tree",
          syn in snap["nodes"] and syn not in ids)
    check("snapshot: synthesis relates to q1,q2 in order", snap["nodes"][syn]["related"] == [q1, q2])

    # -- queue == cmd_review
    check("snapshot: queue ids == cmd_review output",
          [r["id"] for r in snap["queue"]] == [x[0] for x in E.cmd_review(root)])
    check("snapshot: queue is exactly [q2]", [r["id"] for r in snap["queue"]] == [q2])
    check("snapshot: queue rows carry title + summary",
          bool(snap["queue"][0]["title"]) and bool(snap["queue"][0]["summary"]))
    check("snapshot: question node surfaces its own statement ('detail')", "detail" in snap["nodes"][q2])

    # -- idea nodes carry status; done ideas carry a consistent verdict + metric
    h1n = snap["nodes"][h1]
    met, unmet, na = E.count_verifiables(read(node_path(root, h1)))
    check("snapshot: h1 status is done", h1n["status"] == "done")
    check("snapshot: h1 verdict consistent with derive_verdict",
          h1n["verdict"] == E.derive_verdict(met, unmet, na) and h1n["verdict"] in E.VERDICTS)
    check("snapshot: h1 metric carried", h1n["metric"] == "imp +0.012")
    check("snapshot: h2 verdict refuted", snap["nodes"][h2]["verdict"] == "refuted")

    # -- question nodes carry a ledger whose counts match ledger_block / ledger_counts
    q2n = snap["nodes"][q2]
    lc = E.ledger_counts(v, q2)
    lb = E.ledger_block(v, q2)
    check("snapshot: q2 ledger == ledger_counts", q2n["ledger"] == lc)
    check("snapshot: q2 counts (2 children, 2 done, 1 supported, 1 refuted)",
          lc["children"] == 2 and lc["ideas_done"] == 2 and lc["supported"] == 1
          and lc["refuted"] == 1)
    check("snapshot: ledger_counts consistent with ledger_block text",
          f"**{lc['children']} children**" in lb
          and f"supported {lc['supported']}" in lb and f"refuted {lc['refuted']}" in lb)

    # -- pure read: constructing a snapshot mutates nothing on disk
    before = _dir_bytes(root)
    E.snapshot(E.Vault(root))
    check("snapshot: pure read (byte-for-byte identical vault)", _dir_bytes(root) == before)

    check("snapshot: source vault validates clean", E.cmd_validate(root) == [])
    # a non-VERDICT verdict string in frontmatter must never reach the snapshot verbatim
    # (clean data contract + defense-in-depth against attribute injection in the GUI)
    edit(node_path(root, h1), "verdict: supported", "verdict: bogus")
    check("snapshot: non-VERDICT verdict is clamped to None",
          E.snapshot(E.Vault(root))["nodes"][h1]["verdict"] is None)
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
    h1, _, _ = E.cmd_hypothesize(root, "it works", parent=q1, verifiables=["metric up"])

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
             if "## Artifacts" not in t else re.sub(r"## Artifacts\n\n.*?(?=\n## )",
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

    # -- close still WARNS rather than blocking when the report is missing
    h2, _, _ = E.cmd_hypothesize(root, "second", parent=q1, verifiables=["x"], neutral=["control"])
    write(os.path.join(root, E.RESULTS_DIR, h2, "out.log"), "log\n")
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    edit(node_path(root, h2), "- [ ]", "- [x]")
    verdict = E.cmd_close(root, h2)
    check("artifacts: close still closes without a report (warn, not block)",
          verdict == "supported" and E.Vault(root).get(h2).status == "done")
    check("artifacts: close surfaces a warning about the unlinked results",
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


def run_close_gate():
    """The question close-gate (§I): a question resolves only through an APPROVED
    synthesis, and pre-1.2 vaults that resolved questions the old way still validate."""
    print("\n# close-gate (synthesize -> approve -> answer)")
    root = tempfile.mkdtemp(prefix="crux_gate_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Gated", root)
    q1, _ = E.cmd_ask(root, "the question")
    q2, _ = E.cmd_ask(root, "another question")
    h1, _, _ = E.cmd_hypothesize(root, "a hyp", parent=q1, verifiables=["x"], neutral=["control"])
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    edit(node_path(root, h1), "- [ ]", "- [x]")
    E.cmd_close(root, h1)

    expect_error("gate: no synthesis -> answer refused", lambda: E.cmd_answer(root, q1))
    s1, _ = E.cmd_synthesize(root, "s for q1", [q1])
    expect_error("gate: unapproved synthesis -> answer refused", lambda: E.cmd_answer(root, q1))
    # the error must be actionable: it names the approve verb
    try:
        E.cmd_answer(root, q1)
        msg = ""
    except E.CruxError as e:
        msg = str(e)
    check("gate: refusal names `crux approve`", "approve" in msg)

    ts = E.cmd_approve(root, s1)
    check("gate: approve returns/stamps an ISO timestamp",
          bool(ts) and E.Vault(root).get(s1)["fm"]["approved"] == ts)
    again = E.cmd_approve(root, s1)
    check("gate: approve is idempotent (first timestamp stands)", again == ts)
    expect_error("gate: approve rejects a non-synthesis id", lambda: E.cmd_approve(root, q1))
    expect_error("gate: approve rejects an unknown id", lambda: E.cmd_approve(root, "s404"))

    E.cmd_answer(root, q1, text="settled")
    v = E.Vault(root)
    check("gate: question resolved", v.get(q1).status == "resolved")
    check("gate: question stamped with its synthesis", v.get(q1)["fm"]["synthesis"] == s1)
    # the cockpit has to be able to SHOW what closed a question, so the snapshot carries the
    # link from the question and the synthesis' own text + approval stamp
    snap = E.snapshot(root)
    check("gate: snapshot links the question to its synthesis",
          snap["nodes"][q1]["synthesis"] == s1)
    check("gate: snapshot carries the synthesis' approval stamp",
          snap["nodes"][s1]["approved"] == ts)
    check("gate: snapshot carries the synthesis body without the Related:: line",
          "Headline conclusions" in snap["nodes"][s1]["body"]
          and "Related::" not in snap["nodes"][s1]["body"])
    check("gate: an unresolved question has no synthesis link",
          snap["nodes"][q2]["synthesis"] is None)
    check("gate: an approved synthesis for q1 does not unlock q2",
          _refused(lambda: E.cmd_answer(root, q2)))
    check("gate: gated vault validates clean", E.cmd_validate(root) == [])

    # -- grandfathering: a question resolved by a pre-1.2 engine has no `synthesis:` field
    #    and no synthesis node. It must keep its status and never be flagged.
    old = tempfile.mkdtemp(prefix="crux_gate_old_")
    shutil.rmtree(old); os.makedirs(old)
    E.cmd_init("Legacy", old)
    oq, _ = E.cmd_ask(old, "legacy question")
    edit(node_path(old, oq), "status: open", "status: resolved")
    edit(os.path.join(old, E.VAULT_MARKER), f"engine_version: {E.ENGINE_VERSION}", "engine_version: 1.1")
    E.refresh(old)
    check("gate: pre-1.2 resolved question keeps its status",
          E.Vault(old).get(oq).status == "resolved")
    check("gate: pre-1.2 resolved question is not flagged (grandfathered)",
          E.cmd_validate(old) == [])
    shutil.rmtree(old, ignore_errors=True)
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
    bad = mods - stdlib - {"engine", "render"}
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
        check("serve: /snapshot.json == engine.snapshot", snap == E.snapshot(root))
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
    h1, _, _ = E.cmd_hypothesize(root, "h", parent=q1, verifiables=["x"])
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
    #    lazy wiki-page route, and the artifact/report file route — each relaxation
    #    pre-registered in a PRD), never mutates the vault (no fetch method override).
    check("webui: app.js is pure-read (three GETs: snapshot + wiki page + file, no write verbs)",
          app_js.count("fetch(") == 3 and 'fetch("snapshot.json"' in app_js
          and "/wiki/" in app_js and "/file/" in app_js and "method:" not in app_js)

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
    expected = (["q-" + s for s in E.QUESTION_STATUS]
                + ["h-" + s for s in E.IDEA_STATUS if s != E.TERMINAL_IDEA]
                + ["h-" + x for x in E.VERDICTS])
    missing = [k for k in expected if f'"{k}"' not in legend_src]
    check(f"webui: legend covers the engine's whole vocabulary (missing: {missing})", not missing)
    check("webui: legend includes the inconclusive verdict", '"h-inconclusive"' in legend_src)
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
    check("webui: a resolved question links the synthesis that closed it",
          '"Closed on synthesis"' in app_js)
    check("webui: the synthesis reader renders its body and approval state",
          re.search(r"function synthesisDetail\([^)]*\)\s*\{.*?bodyOr\(n\.body", app_js, re.S) is not None)
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
          and between.strip().startswith('section("Null'))
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
    sq_src = fn_src("showQueue")
    check("webui: showQueue never rebuilds — no renderTree()/layout() in its body",
          bool(sq_src) and "renderTree(" not in sq_src and "layout(" not in sq_src
          and "applyCosmeticState(" in sq_src)
    cos_src = fn_src("applyCosmeticState")
    check("webui: the cosmetic helper toggles dim / hit / selected on existing elements",
          '"dim"' in cos_src and '"hit"' in cos_src and '"selected"' in cos_src
          and "classList.toggle" in cos_src)
    check("webui: the in-place swap keeps the ARIA selection truthful (PR #13 contract)",
          "aria-selected" in cos_src and "aria-activedescendant" in cos_src)
    check("webui: the helper derives dim/hit from the SAME predicates nodeSVG bakes in",
          "matchNode(" in cos_src and "statusClass(" in cos_src and "state.filter" in cos_src)
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
                       ("nodeSVG", "computeGeom", "statusClass", "verifDots",
                        "vBadgeClass", "bodyLabel", "rootLabel"))
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
    h1, _, _ = E.cmd_hypothesize(root, "it holds", parent=q1, verifiables=["x"])

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
        hid, _, warn = E.cmd_hypothesize(root, f"idea {i}", parent=q2)
        ids.append(hid); quiet = quiet and warn is None
    check("economy: no back-pressure while under the cap", quiet)
    check("economy: exactly 5 unrun hypotheses is within the cap",
          [w for w in E.validation_report(root)["warnings"] if w["id"] == q2] == [])
    h6, _, warn6 = E.cmd_hypothesize(root, "idea 6", parent=q2)
    check("economy: hypothesize warns when the new node breaches the cap", warn6 is not None)
    check("economy: the back-pressure names the cap", warn6 is not None and "5" in warn6)
    check("economy: 6 unrun hypotheses trips one fan-out warning",
          len([w for w in E.validation_report(root)["warnings"] if w["id"] == q2]) == 1)
    E.cmd_test(root, ids[0], "staged")
    E.cmd_test(root, ids[1], "staged")
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
    check("economy: the check registry is the six documented names",
          tuple(E.CHECKS) == ("tree", "wiki", "economy", "fanout", "rd", "tasks"))

    # -- 8. the cockpit contract
    snap = E.snapshot(root)
    check("economy: snapshot exposes eli5 on a question", "eli5" in snap["nodes"][q1])
    check("economy: snapshot exposes tldr on a question", "tldr" in snap["nodes"][q1])
    check("economy: snapshot exposes eli5 on an idea", "eli5" in snap["nodes"][h1])
    check("economy: snapshot exposes tldr on an idea", "tldr" in snap["nodes"][h1])
    check("economy: an unwritten summary reads empty, not as the placeholder",
          snap["nodes"][q1]["eli5"] == "")
    edit(node_path(root, q1), "_(one sentence, plain language, no jargon)_",
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
    h1, _, _ = E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"])
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
    check("emig: review still runs", isinstance(E.cmd_review(root), list))
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
            "--null", "chance — the payload happened to parse", "--json")
    h1 = as_json(r)
    check("json: hypothesize emits parseable JSON", isinstance(h1, dict) and "id" in h1)
    check("json: hypothesize reports its fan-out headroom", isinstance(h1, dict) and "warning" in h1)

    rn = cli("approve-null", h1["id"], "--json")
    check("json: approve-null emits parseable JSON",
          isinstance(as_json(rn), dict) and as_json(rn).get("null_approved"))
    r = cli("test", h1["id"], "--to", "running", "--json")
    t = as_json(r)
    check("json: test emits parseable JSON", isinstance(t, dict) and t.get("status") == "running")

    edit(node_path(root, h1["id"]), "- [ ] stdout parses", "- [x] stdout parses")
    edit(node_path(root, h1["id"]), "- [ ] [outcome-neutral]", "- [x] [outcome-neutral]")
    r = cli("close", h1["id"], "--json")
    cl = as_json(r)
    check("json: close emits parseable JSON", isinstance(cl, dict) and cl.get("verdict") == "supported")

    r = cli("review", "--json")
    rv = as_json(r)
    check("json: review emits a JSON list", isinstance(rv, list))

    r = cli("synthesize", "what it settled", "--for", q1["id"], "--json")
    sy = as_json(r)
    check("json: synthesize emits parseable JSON", isinstance(sy, dict) and "id" in sy)

    r = cli("approve", sy["id"], "--json")
    ap = as_json(r)
    check("json: approve emits parseable JSON", isinstance(ap, dict) and "approved" in ap)

    r = cli("answer", q1["id"], "--json")
    an = as_json(r)
    check("json: answer emits parseable JSON", isinstance(an, dict) and an.get("status") == "resolved")

    r = cli("pursue", q1["id"], "--json")
    pu = as_json(r)
    check("json: pursue emits parseable JSON", isinstance(pu, dict) and pu.get("status") == "open")

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
                                 discriminates=[True, False, False])
    h2, _, _ = E.cmd_hypothesize(root, "second hyp", parent=qmid)
    # the optional ## Protocol section (new in 1.4) — fill it on the anchor
    edit(node_path(root, qmid), DECK_PROTOCOL_PLACEHOLDER, "Rules locked up front.")
    # close h1 with a (found: …) parenthetical on the first bar
    edit(node_path(root, h1), "- [ ] bar one", "- [x] bar one   (found: +0.02)")
    edit(node_path(root, h1), "- [ ] bar two", "- [x] bar two")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] control", "- [x] [outcome-neutral] control")
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    E.cmd_close(root, h1, metric="imp +0.02")
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
    check("deck: closed child carries verdict + metric",
          k1["verdict"] == "supported" and k1["metric"] == "imp +0.02")
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
    check("deck: scope counts executed vs parked",
          p1["scope"]["executed"] == 1 and p1["scope"]["parked"] == 1
          and p1["scope"]["by_state"]["done"] == 1 and p1["scope"]["by_state"]["idea"] == 1)

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

    # synthesis: only an APPROVED one enters the payload
    syn, _ = E.cmd_synthesize(root, "what qmid settled", [qmid])
    check("deck: unapproved synthesis stays out of the payload",
          E.deck_payload(root, qmid)["synthesis"] is None)
    E.cmd_approve(root, syn)
    ps = E.deck_payload(root, qmid)["synthesis"]
    check("deck: approved synthesis lands with its text",
          bool(ps) and ps["id"] == syn and bool(ps["approved"]) and "Related::" not in ps["text"])

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
    check("deck: hypothesis anchor — no children, no synthesis",
          ph["children"] == [] and ph["synthesis"] is None)
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
    hv, _, _ = E.cmd_hypothesize(root, "checked hyp", parent=qv, verifiables=["bar"])
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
    h1, _, _ = E.cmd_hypothesize(root, "it holds", parent=q1, verifiables=["x"])

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
    s1, _ = E.cmd_synthesize(root, "a synthesis", [q1])
    expect_error("rd: an RD may not attach to a synthesis", lambda: E.cmd_rd(root, s1, "nope"))

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
    st_before = E.Vault(root).get(q1).status
    E.cmd_rd(root, h1, "third cut", supersedes=slug2)
    E.refresh(root)
    check("rd: an RD does not move ledger_counts", E.ledger_counts(E.Vault(root), q1) == led_before)
    check("rd: an RD does not trip the review gate", E.Vault(root).get(q1).status == st_before)

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
    E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"])
    check("rdmig: a pre-07 vault has no rd/", not os.path.isdir(os.path.join(root, "rd")))
    check("rdmig: a pre-07 vault grows no RD.md", not os.path.exists(os.path.join(root, "RD.md")))
    check("rdmig: status still renders on a pre-07 vault", "an old question" in E.status_text(root))
    check("rdmig: review still runs on a pre-07 vault", isinstance(E.cmd_review(root), list))

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
    h1, _, _ = E.cmd_hypothesize(root, "a hypothesis", parent=q1, verifiables=["x"])

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
    crux_skill = os.path.abspath(os.path.join(HERE, "..", "SKILL.md"))
    check("rdskill: the crux verb table lists rd",
          os.path.isfile(crux_skill) and "| `rd` |" in read(crux_skill))
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
    h1, _, _ = E.cmd_hypothesize(root, "the descendant", parent=q2, verifiables=["x"])

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
    h1, _, _ = E.cmd_hypothesize(root, "a hypothesis", parent=q1, verifiables=["x"])

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

    # the pane must hide by CSS as well as by the hidden attribute: an ID selector outranks
    # the UA's [hidden] rule, and the first live walk of this tab found the rail rendering
    # underneath the tree because of it
    css = read(os.path.join(HERE, "webui", "style.css"))
    check("rdgui: the RD pane opts back in to [hidden]", "#rd-pane[hidden]" in css)
    idx = read(os.path.join(HERE, "webui", "index.html"))
    check("rdgui: the RD pane ships hidden", 'id="rd-pane" hidden' in idx)
    check("rdgui: the RD tab is registered", 'data-tab="rd"' in idx)

    # the node -> RD pointer has to be reachable from the pane, or it is a snapshot key
    # nothing uses. Absent on a node with no RD, so it never becomes chrome.
    check("rdgui: the node pane offers a way into the design",
          "function rdSection" in read(os.path.join(HERE, "webui", "app.js"))
          and "if (!n.rd) return \"\";" in read(os.path.join(HERE, "webui", "app.js")))

    # the rail must reuse the wiki rail's DOM contract, or it inherits none of its styling
    # (the first live walk rendered the rail as a horizontal run of text because of this)
    app = read(os.path.join(HERE, "webui", "app.js"))
    check("rdgui: the RD rail reuses the wiki rail's DOM classes",
          'class="wr-folder"' in app and '"wr-items"' in app)
    check("rdgui: the rail's scroll rule is shared, not restated",
          "#wiki-rail-body, #rd-rail-body" in css)
    # opening a SUPERSEDED design by default is the one thing this lifecycle exists to prevent
    check("rdgui: the reader defaults to a live design",
          'p.status === "active"' in app)

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
                                verifiables=["first check", "second check"])
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
    h1, _, _ = E.cmd_hypothesize(root, "a stamped hypothesis", parent=q1, verifiables=["a"])

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
                "    - H: a seeded hypothesis\n      - v: a check\n")
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
    old, oq, oh = pre15_vault("crux_bmig_")
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
    E.check_and_stamp_version(old); E.snapshot(old); E.status_text(old); E.cmd_review(old)
    E.cmd_close(old, oh)
    after_v = E.Vault(old)
    check("evmig: no command retro-stamps an existing node",
          all("schema" not in n["fm"] for n in after_v.nodes.values()))
    shutil.rmtree(old, ignore_errors=True)

    # -- the captured pre-upgrade fixture: byte-identical after the version bump
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    dst = tempfile.mkdtemp(prefix="crux_bdemo_")
    shutil.rmtree(dst); shutil.copytree(src, dst)
    f0, v0, s0 = fingerprint(dst)
    g0 = generated_verdicts(dst)
    warn = E.check_and_stamp_version(dst)
    E.refresh(dst); E.snapshot(dst); E.cmd_validate(dst); E.status_text(dst)
    f1, v1, s1 = fingerprint(dst)
    check("evmig: pre-15 vault — every node's authored content is byte-identical after upgrade",
          f0 == f1)
    check("evmig: pre-15 vault — no verdict is re-labelled or lost in anything generated",
          generated_verdicts(dst) == g0)
    check("evmig: pre-15 vault — every recorded verdict is unchanged after upgrade",
          v0 == v1 and v0["h1"] == "supported" and v0["h2"] == "partial")
    check("evmig: pre-15 vault — every status is unchanged after upgrade", s0 == s1)
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
                        "-n", "the positive control"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    hc = E.Vault(root).get("h1")
    check("kind: the CLI -n flag writes an outcome-neutral verifiable",
          r.returncode == 0 and "- [ ] [outcome-neutral] the positive control" in hc["body"]
          and "- [ ] the claim check" in hc["body"])

    # -- the gate: a stamped hypothesis needs a control, or a written opt-out
    h2, _, _ = E.cmd_hypothesize(root, "no control at all", parent=q1, verifiables=["only a claim check"])
    expect_error("kind: running is refused with no outcome-neutral check",
                 lambda: E.cmd_test(root, h2, to="running"))
    check("kind: the refusal names the opt-out route",
          "opt-out" in _err_text(lambda: E.cmd_test(root, h2, to="running")))
    check("kind: validate flags a stamped node with no control and no opt-out",
          any("outcome-neutral" in m for _, m in E.cmd_validate(root)) is False)  # not yet running

    n2 = E.Vault(root).get(h2)
    n2["fm"]["neutral_optout"] = ""
    E.write_if_changed(n2["path"], E.render_doc(n2["fm"], n2["body"]))
    expect_error("kind: an empty opt-out does not unblock running",
                 lambda: E.cmd_test(root, h2, to="running"))
    n2 = E.Vault(root).get(h2)
    n2["fm"]["neutral_optout"] = "the assay IS the claim; a positive control would beg the question"
    E.write_if_changed(n2["path"], E.render_doc(n2["fm"], n2["body"]))
    declare_null(root, h2)
    check("kind: a written opt-out unblocks running",
          E.cmd_test(root, h2, to="running") == "running")

    declare_null(root, "h1")
    check("kind: a hypothesis WITH a control runs with no opt-out",
          E.cmd_test(root, "h1", to="running") == "running")

    # -- an unknown tag is a validate problem on a stamped node
    hb, _, _ = E.cmd_hypothesize(root, "bad tag", parent=q1, verifiables=["[banana] a check"])
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
                "    - H: genuinely new work\n      - v: a check\n")
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
    old, oq, oh = pre15_vault("crux_kmig_")
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

    # -- the roll-up and the views survive a new verdict
    root = tempfile.mkdtemp(prefix="crux_rule_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Rules", root)
    q1, _ = E.cmd_ask(root, "does the rule bind?")
    h1, _, _ = E.cmd_hypothesize(root, "all rule", parent=q1,
                                 verifiables=["c one", "c two"], neutral=["control"])
    n = E.Vault(root).get(h1); n["fm"]["rule"] = "all"
    E.write_if_changed(n["path"], E.render_doc(n["fm"], n["body"]))
    edit(node_path(root, h1), "- [ ] c one", "- [x] c one")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] control", "- [x] [outcome-neutral] control")
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    check("rule: all with one unmet closes refuted (was partial before 1.8)",
          E.cmd_close(root, h1) == "refuted")

    h2, _, _ = E.cmd_hypothesize(root, "broken apparatus", parent=q1,
                                 verifiables=["c one"], neutral=["control"])
    n = E.Vault(root).get(h2); n["fm"]["rule"] = "all"
    E.write_if_changed(n["path"], E.render_doc(n["fm"], n["body"]))
    edit(node_path(root, h2), "- [ ] c one", "- [x] c one")
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    check("rule: a failed control closes invalid-run end to end",
          E.cmd_close(root, h2) == "invalid-run")

    lc = E.ledger_counts(E.Vault(root), q1)
    check("rule: ledger_counts is generated from VERDICTS",
          all(x in lc for x in E.VERDICTS) and lc["invalid-run"] == 1 and lc["refuted"] == 1)
    check("rule: _ledger_summary survives a new verdict",
          "1 invalid-run" in E._ledger_summary(lc))
    meta = R.render_meta(E.Vault(root))
    check("rule: the META dashboard covers the whole verdict vocabulary",
          all(f"{x} " in meta.split("**Verdicts**")[1].split("\n")[0] for x in E.VERDICTS))
    exp = R.render_experiments(E.Vault(root))
    check("rule: EXPERIMENTS carries a rule column",
          "| rule |" in exp and "| all |" in exp)

    snap = E.snapshot(root)
    check("rule: snapshot exposes the combination rule",
          snap["nodes"][h1]["rule"] == "all" and snap["nodes"][h1]["rule_m"] is None
          and snap["nodes"][h1]["verdict"] == "refuted")
    check("rule: snapshot exposes the per-kind tallies",
          snap["nodes"][h1]["tally"] == {"hypothesis": [1, 1, 0], "outcome-neutral": [1, 0, 0]})
    dp = E.deck_payload(root, q1)
    check("rule: the deck payload carries the combination rule",
          [c["rule"] for c in dp["children"]] == ["all", "all"])

    # -- the gate: a stamped multi-check hypothesis must declare how they add up
    h3, _, _ = E.cmd_hypothesize(root, "no rule", parent=q1,
                                 verifiables=["c one", "c two"], neutral=["control"])
    expect_error("rule: running is refused with no combination rule",
                 lambda: E.cmd_test(root, h3, to="running"))
    h4, _, _ = E.cmd_hypothesize(root, "single check", parent=q1,
                                 verifiables=["only one"], neutral=["control"])
    declare_null(root, h4)
    check("rule: a single claim-directed check needs no declaration",
          E.cmd_test(root, h4, to="running") == "running")
    n = E.Vault(root).get(h3); n["fm"]["rule"] = "ordered"
    E.write_if_changed(n["path"], E.render_doc(n["fm"], n["body"]))
    check("rule: validate refuses a reserved rule on a stamped node",
          any("ordered" in m for _, m in E.cmd_validate(root)))

    check("rule: ENGINE_VERSION at or past 1.8", at_least_version("1.8"))
    shutil.rmtree(root, ignore_errors=True)

    # ------------------------------------------------------------------ the boundary holds
    old, oq, oh = pre15_vault("crux_rmig_")
    edit(node_path(old, oh), "- [ ] first check", "- [x] first check")
    check("evmig: a pre-15 node closes through the LEGACY function",
          E.cmd_close(old, oh) == "partial")
    check("evmig: re-closing a pre-15 node still yields its legacy verdict",
          E.cmd_close(old, oh) == "partial")
    check("evmig: a pre-15 node needs no rule to run",
          E.cmd_test(old, oh, to="running") == "running")
    check("evmig: a pre-15 vault raises no rule problem", E.cmd_validate(old) == [])
    shutil.rmtree(old, ignore_errors=True)

    # the committed pre-15 fixture keeps its recorded partial through every view
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    dst = tempfile.mkdtemp(prefix="crux_rdemo_")
    shutil.rmtree(dst); shutil.copytree(src, dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    dv = E.Vault(dst)
    check("evmig: partial survives in the vocabulary and every view",
          dv.get("h2")["fm"]["verdict"] == "partial"
          and E.snapshot(dst)["nodes"]["h2"]["verdict"] == "partial"
          and "partial 1" in R.render_meta(dv)
          and E.ledger_counts(dv, "q2")["partial"] == 1
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
        hid, _, _ = E.cmd_hypothesize(root, title, parent=q1, **kw)
        return hid

    h1 = mk("locked at running")
    check("lock: an unrun hypothesis carries no lock",
          E.Vault(root).get(h1)["fm"].get("lock") is None)
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    n = E.Vault(root).get(h1)
    first_lock, first_at = n["fm"].get("lock"), n["fm"].get("locked")
    check("lock: running takes the lock",
          bool(first_lock) and bool(first_at) and n["fm"].get("lock_at") == "running")
    declare_null(root, h1)
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

    # -- the hole `running` alone leaves: cmd_close has no status precondition
    h2 = mk("closed straight from idea")
    declare_null(root, h2)
    edit(node_path(root, h2), "- [ ] alpha check", "- [x] alpha check")
    edit(node_path(root, h2), "- [ ] beta check", "- [x] beta check")
    edit(node_path(root, h2), "- [ ] [outcome-neutral] the control", "- [x] [outcome-neutral] the control")
    check("lock: closing straight from idea still yields a verdict",
          E.cmd_close(root, h2) == "supported")
    n2 = E.Vault(root).get(h2)
    check("lock: closing without running locks and marks lock_at",
          bool(n2["fm"].get("lock")) and n2["fm"].get("lock_at") == "close")
    check("lock: a close-time lock is a warning, not a problem",
          any("never pre-registered" in w["message"]
              for w in E.validation_report(root)["warnings"])
          and E.cmd_validate(root) == [])

    # -- surfaces
    snap = E.snapshot(root)
    check("lock: snapshot exposes lock state and drift",
          snap["nodes"][h1]["locked"] is True and snap["nodes"][h1]["drift"] is False)
    edit(node_path(root, h1), "an entirely", "an entirely")  # no-op, keep the file settled
    dp = E.deck_payload(root, q1)
    check("lock: the deck payload exposes drift on every child",
          all("drift" in c for c in dp["children"]))

    # -- D7: drift warns loudly and blocks NOTHING
    edit(node_path(root, h1), "beta   check", "a rewritten check")
    check("lock: drift is a validate problem",
          any(i == h1 and "DRIFT" in m for i, m in E.cmd_validate(root)))
    E.cmd_close(root, h1)
    check("lock: drift does not block close", E.Vault(root).get(h1).status == "done")
    check("lock: review flags the question holding a drifted child",
          any(qid == q1 and drift for qid, _, drift in E.cmd_review(root)))
    s, _ = E.cmd_synthesize(root, "what q1 settled", [q1])
    E.cmd_approve(root, s)
    check("lock: drift does not block answer (the engine flags; the PI decides)",
          E.cmd_answer(root, q1) == q1
          and E.Vault(root).get(q1).status == "resolved")
    check("lock: and the flag survives the answer — it is permanent",
          any(i == h1 and "DRIFT" in m for i, m in E.cmd_validate(root)))
    check("lock: no verb clears a drift flag",
          not any(hasattr(E, x) for x in ("cmd_unflag", "cmd_relock", "cmd_acknowledge")))

    # -- CRLF. The wiki source registry hashes raw BYTES (`_sha256_file`), which is why a
    #    Windows checkout with autocrlf broke demo_vault's `.sources.tsv` on CI. The lock
    #    must never inherit that class of bug: it hashes lock_material(), a string built from
    #    a body that `read()` already normalized in text mode. Pinned here so a future change
    #    to byte-hashing fails loudly instead of on someone else's runner.
    lf = E.Vault(root).get(h2)
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
    old, oq, oh = pre15_vault("crux_lmig_")
    declare_null(old, oh)
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
    """Spec 15 PRD 15.5 — the separability rulebook sentence into the crux skill, and the
    skill's account of a verdict brought in line with what the engine now does.

    All greps, in the style the suite already uses for the cockpit legend: the point is that
    the docs cannot silently drift from the constants."""
    print("\n# evidence semantics — the rulebook and the skill (spec 15, PRD 15.5)")
    skill = read(os.path.join(HERE, "..", "SKILL.md"))
    spec = read(os.path.join(HERE, "..", "..", "..", ".spec", "15-evidence-semantics.md"))

    def sentence(text):
        """The rulebook blockquote, unwrapped and whitespace-collapsed, with markdown
        emphasis stripped — so the two copies are compared on CONTENT, and a re-wrap or a
        bolded clause cannot make them look different when they are not."""
        head = "One experiment settles several hypotheses separately only when"
        # the two copies are wrapped differently and the skill bolds two clauses, so the
        # comparison is on CONTENT: unwrap, drop blockquote markers and emphasis, collapse
        # whitespace. Anything short of identical wording still fails.
        flat = " ".join(text.replace(">", " ").replace("*", "").split())
        i = flat.find(head)
        if i < 0:
            return None
        j = flat.find("answers.", i)
        return flat[i:j + len("answers.")] if j > 0 else None

    a, b = sentence(spec), sentence(skill)
    check("rulebook: the separability sentence is in the skill", b is not None)
    check("rulebook: the separability sentence matches the spec word for word", a and a == b)
    check("rulebook: the three separability lines are in the skill",
          all(x in skill for x in ("**Different lever.**", "**Different failure.**",
                                   "**Different verdict.**")))
    check("rulebook: the skill says a shared control is the fix, not the flaw",
          "the fix, not the" in skill)

    check("rulebook: the skill no longer teaches the retired verdict rule",
          "→ `refuted`/`partial`" not in skill)
    check("rulebook: the skill covers the whole verdict vocabulary",
          all(f"`{x}`" in skill for x in E.VERDICTS))
    check("rulebook: the skill says invalid-run is not a refutation",
          "never a refutation" in skill)
    check("rulebook: the skill states the boundary is permanent",
          "boundary is permanent" in skill and "schema: 1" in skill
          and 'Do not "fix" an old node' in skill)
    check("rulebook: the skill names the combination rule and its CLI flag",
          "rule: all | any | m-of-n" in skill and "--rule" in skill)
    check("rulebook: the skill explains inconclusive is derived, never chosen",
          "derived, never chosen" in skill)
    check("rulebook: the skill carries the drift rule and says it blocks nothing",
          "drift" in skill and "blocks nothing" in skill)

    joint = "64% joint power"
    check("rulebook: the joint-power cost is stated with its constraint",
          joint in skill and "may\n  not be loosened" in skill.replace("\n  ", "\n  "))

    spec09 = read(os.path.join(HERE, "..", "..", "..", ".spec", "09-specialized-agents.md"))
    check("rulebook: spec 09 carries the crux-verifiables amendment",
          "`crux-verifiables` gains a job" in spec09 and joint in spec09
          and "Choose the combination rule" in spec09)
    check("rulebook: spec 15's work items are ticked for what shipped",
          spec.count("- \u2611 ") >= 10 and "**Status:** \u25d0" in spec)


def _task_vault(prefix="crux_task_"):
    """A small vault with one question and one hypothesis — the substrate every taskhub
    test needs before it can ref anything."""
    root = tempfile.mkdtemp(prefix=prefix)
    E.cmd_init("Task Demo", root, goal="Ship the taskhub.")
    q, _ = E.cmd_ask(root, "Can the taskhub hold months of work?")
    h, _, _ = E.cmd_hypothesize(root, "one file per task survives churn", parent=q,
                                verifiables=["ids never renumber"])
    return root, q, h


def run_taskhub():
    print("\n# taskhub — the task store (spec 08, PRD 08.0)")
    root, q, h = _task_vault()

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
    E.snapshot(root); E.status_text(root); E.cmd_review(root)
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
    old, _, _ = _task_vault("crux_task_pre08_")
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
    E.refresh(dst); E.snapshot(dst); E.status_text(dst); E.cmd_review(dst)
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
    root, q, h = _task_vault("crux_taskdep_")

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
                                 verifiables=["alpha", "beta"], neutral=["the control"])
    h2, _, _ = E.cmd_hypothesize(root, "broken apparatus", parent=q1, rule="all",
                                 verifiables=["alpha"], neutral=["the control"])
    declare_null(root, h2)
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running"); E.cmd_test(root, h2, to="running")
    edit(node_path(root, h1), "- [ ] alpha", "- [x] alpha")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    edit(node_path(root, h1), "- [ ] beta", "- [x] a check nobody registered")   # -> DRIFT
    edit(node_path(root, h2), "- [x] alpha", "- [x] alpha")
    edit(node_path(root, h2), "- [ ] alpha", "- [x] alpha")
    E.cmd_close(root, h1); E.cmd_close(root, h2)
    snap = E.snapshot(root)
    idea = snap["nodes"][h1]

    # Fields a reader legitimately never needs on screen. Small and justified on purpose —
    # this allowlist is the only place a field can hide, so it must stay embarrassing to add to.
    NOT_RENDERED = {
        "id", "type", "parent",        # structural: the tree already says all three
        "tally",                       # redundant: `verifiables` carries kind+state per item
        "schema",                      # the boundary is narrated by its ABSENCE of rule/kind
        "words",                       # already surfaced by economyBadge()
    }
    def referenced(key):
        return any(p in app_js for p in (f'"{key}"', f".{key}", f"['{key}']"))
    unrendered = sorted(k for k in idea if k not in NOT_RENDERED and not referenced(k))
    check(f"webui: every published idea field is consumed by the cockpit (missing: {unrendered})",
          not unrendered)
    vitem = idea["verifiables"][0]
    vmissing = sorted(k for k in vitem if f'v.{k}' not in app_js and f'"{k}"' not in app_js)
    check(f"webui: every published verifiable field is consumed (missing: {vmissing})",
          not vmissing)

    # ---- the three findings, each asserted directly
    check("webui: the drift flag is rendered",
          "drift" in app_js and "n.drift" in app_js)
    check("webui: drift is called drift in the UI, not something softer",
          "drift" in re.sub(r"//.*", "", app_js).lower().split("badges +=")[-1][:0] + "drift"
          and 'class="badge drift"' in app_js)
    check("webui: the combination rule is rendered beside the verdict",
          "n.rule" in app_js and "rule_m" in app_js)
    check("webui: whether the commitment was pre-registered is rendered",
          "lock_at" in app_js and "n.locked" in app_js)
    check("webui: an outcome-neutral verifiable is marked in the pane",
          "v.kind" in app_js and "outcome-neutral" in app_js)

    # ---- a drifted node must be distinguishable in the TREE, not only in the pane. The
    # PLATO failure is a reader skimming past a node and never opening it, so a flag that
    # only exists in the detail pane is a flag that did nothing.
    svg = app_js.split("function nodeSVG")[-1][:4000]
    check("webui: the tree renderer emits a drift mark on the node",
          "n.drift" in svg and "drift-mark" in svg and "drifted" in svg)
    check("webui: the drift mark is styled in the stylesheet",
          ".box.drifted" in style and ".drift-mark" in style)
    check("webui: drift is drawn WITHOUT overriding the verdict fill",
          # the two facts are orthogonal — "what was concluded" and "was the commitment
          # edited" must stay separately readable, so drift takes the stroke, not the fill
          "fill" not in style.split(".box.drifted")[1].split("}")[0])
    check("webui: a drift flip repaints the node in the in-place recolor path",
          'n.drift ? "D"' in app_js)

    # ---- any new colour must exist in BOTH themes (the rule the legend guard already applies)
    _blk = lambda sel: (re.search(sel + r"\s*\{(.*?)\n\}", style, re.S | re.M) or [None, ""])[1]
    dark, light = _blk(r"^:root"), _blk(r'^:root\[data-theme="light"\]')
    newvars = sorted(set(re.findall(r"var\((--drift[a-z-]*)\)", app_js + style)))
    unstyled = [v for v in newvars if f"{v}:" not in dark or f"{v}:" not in light]
    check(f"webui: every new drift colour is defined in both themes (missing: {unstyled})",
          not unstyled)

    # ---- and the engine still publishes what the cockpit now claims to read
    check("webui: the fixture really carries drift, a rule, and an outcome-neutral check",
          idea["drift"] is True and idea["rule"] == "m-of-n" and idea["rule_m"] == 2
          and any(v["kind"] == "outcome-neutral" for v in idea["verifiables"])
          and snap["nodes"][h2]["verdict"] == "invalid-run")
    # 15.6 itself bumped nothing: it was webui-only, and at its own tip this read
    # `== "1.9"`. That is the literal-equality form this file documents as expiring on the
    # next PRD — spec 08 stacks on top and takes the engine to 2.x, so the claim is kept as
    # the floor it was always making. What 15.6 guarantees is that the cockpit needs no
    # engine support beyond 1.9, which the field checks above prove directly.
    check("webui: the cockpit narration needs no engine support past 1.9",
          at_least_version("1.9"))
    shutil.rmtree(root, ignore_errors=True)


def run_experiments():
    print("\n# taskhub — experiments are tasks (spec 08, PRD 08.2)")
    root, q, h1 = _task_vault("crux_exp_")
    h2, _, _ = E.cmd_hypothesize(root, "the pilot separates the arms", parent=q,
                                 verifiables=["separation at n=3"])

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

    check("exp: ENGINE_VERSION bumped to 2.2", at_least_version("2.2"))
    shutil.rmtree(root, ignore_errors=True)


def run_experiment_gate():
    print("\n# taskhub — the gating split: work never creates direction (spec 08, PRD 08.3)")
    root, q, h1 = _task_vault("crux_gate_")
    # h2/h3 are moved to `running` below, so they carry the outcome-neutral control spec 15
    # requires of a stamped hypothesis — the taskhub consumes that gate, it does not bypass it
    h2, _, _ = E.cmd_hypothesize(root, "the arm separates", parent=q, verifiables=["sep at n=3"],
                                 neutral=["the known-good encoder reproduces 0.46"])
    q2, _ = E.cmd_ask(root, "Does the loader matter?")
    h3, _, _ = E.cmd_hypothesize(root, "the loader is the bottleneck", parent=q2,
                                 verifiables=["throughput +20%"],
                                 neutral=["the profiler reports a known baseline"])

    # -- 1. an ordinary task is ACT-AND-REPORT. Ticking "fetched the antibody lot" sets no
    #       direction, spends no compute and records no scientific result, so the PI needn't
    #       be concerned with it — which is legal rather than a leash violation.
    t1, _ = E.cmd_task_add(root, "Fetch the antibody lot", category="data-acquisition",
                           blocked_by=None)
    E.cmd_task_done(root, t1, outputs=[f"[[{q}]]"])
    check("gate: completing a chore is not PI-gated",
          E.cmd_task_review(root) == [] and E.task_by_id(root)[t1]["status"] == "done")

    # -- 2/3. an experiment decomposes through the EXISTING parent link, and the gate fires
    #         ONCE, on the parent — not once per sub-task. That is what keeps the layer's
    #         founding promise (view it, never manage it) intact after the merge.
    e1, _ = E.cmd_task_add(root, "Run the pilot", category="implementation", blocked_by=None,
                           hypothesis_refs=[(h1, "supported"), (h3, "refuted")])
    for i, sub in enumerate(("Acquire the data", "Implement the arm", "Make the figures")):
        s, _ = E.cmd_task_add(root, sub, category="implementation", blocked_by=None, parent=e1)
        E.cmd_task_done(root, s, outputs=[f"[[{q}]]"])
    check("gate: sub-tasks do not inherit the role",
          not any(E.task_is_experiment(t) for t in E.scan_tasks(root) if t["parent"] == e1)
          and E.cmd_task_review(root) == [])
    E.cmd_task_done(root, e1, outputs=[f"[[{q}]]"])
    queue = E.cmd_task_review(root)
    check("gate: completing an experiment enters the acceptance queue",
          [x[0] for x in queue] == [e1])
    check("gate: one experiment with three sub-tasks fires one gate", len(queue) == 1)

    # -- 4/5/6. THE LEASH, proven as three negatives and one positive.
    v0 = E.Vault(root)
    verdicts0 = {k: n["fm"].get("verdict") for k, n in v0.nodes.items()}
    ledger0 = {x: E.ledger_counts(v0, x) for x in (q, q2)}
    nodes0 = {n: read(node_path(root, n)) for n in (q, q2, h1, h2, h3)}
    E.cmd_task_accept(root, e1)
    v1 = E.Vault(root)
    check("gate: accepting writes no verdict",
          {k: n["fm"].get("verdict") for k, n in v1.nodes.items()} == verdicts0)
    check("gate: acceptance never enters the ledger roll-up",
          {x: E.ledger_counts(v1, x) for x in (q, q2)} == ledger0)
    changed = [n for n, b in nodes0.items() if read(node_path(root, n)) != b]
    check("gate: accepting edits only the stale flag, and only on the refed questions",
          set(changed) == {q, q2}
          and all(read(node_path(root, n)).replace("stale: true", "stale: false") == nodes0[n]
                  for n in changed))
    check("gate: acceptance stales every refed hypothesis's question",
          v1.get(q)["fm"]["stale"] is True and v1.get(q2)["fm"]["stale"] is True)
    check("gate: an accepted experiment leaves the queue", E.cmd_task_review(root) == [])
    check("gate: accepting twice keeps the first signature",
          E.cmd_task_accept(root, e1) == E.task_by_id(root)[e1]["fm"]["accepted"])
    expect_error("gate: accept is refused on an ordinary task",
                 lambda: E.cmd_task_accept(root, t1))

    # -- 8. DRIFT: spec 15's ruling D7 is that drift warns loudly and blocks NOTHING. 08 adds
    #       a SECOND PI touchpoint 15 could not have known about; blocking here would
    #       reintroduce the block D7 declined, going around 15.3's own guard assert. This is
    #       08's copy of that guard.
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    hp = node_path(root, h2)
    edit(hp, "- [ ] sep at n=3", "- [ ] a totally different check")
    check("gate: the refed hypothesis really is drifted", E.lock_drift(E.Vault(root).get(h2)))
    e2, _ = E.cmd_task_add(root, "Run the drifted arm", category="implementation",
                           blocked_by=None, hypothesis_refs=[(h2, "supported")])
    E.cmd_task_done(root, e2, outputs=[f"[[{q}]]"])
    row = [x for x in E.cmd_task_review(root) if x[0] == e2][0]
    check("gate: the queue carries the drift flag of every refed hypothesis", row[3] == [h2])
    stamp = E.cmd_task_accept(root, e2)
    check("gate: drift is printed at accept and never blocks",
          bool(stamp) and E.task_by_id(root)[e2]["fm"].get("accepted")
          and E.lock_drift(E.Vault(root).get(h2)))

    # -- 9. tasks are outside the roll-up, so an open experiment does not hold its question
    #       out of review. Pinned because the opposite is a plausible later "fix".
    declare_null(root, h3)
    E.cmd_test(root, h3, to="running")
    edit(node_path(root, h3), "- [ ]", "- [x]")          # claim + control both met
    E.cmd_close(root, h3)
    E.cmd_task_add(root, "Still running the sweep", category="implementation",
                   blocked_by=None, hypothesis_refs=[(h3, "inconclusive")])
    E.refresh(root)
    check("gate: an open experiment does not hold a question open",
          E.Vault(root).get(q2).status == "review")

    # -- 10. dropping an unaccepted experiment: leaves the queue, keeps its conclusions,
    #        propagates nothing, and is reported as info so it never reads as accepted.
    e3, _ = E.cmd_task_add(root, "Abandoned half-run", category="implementation",
                           blocked_by=None, hypothesis_refs=[(h1, "inconclusive")])
    E.cmd_task_done(root, e3, outputs=[f"[[{q}]]"])
    v2 = E.Vault(root)
    verdicts2 = {k: n["fm"].get("verdict") for k, n in v2.nodes.items()}
    E.cmd_task_drop(root, e3)
    info = {x["id"]: x for x in E.validation_report(root)["info"]}
    check("gate: dropping an unaccepted experiment propagates nothing",
          e3 not in [x[0] for x in E.cmd_task_review(root)]
          and E.task_hypothesis_refs(E.task_by_id(root)[e3]) == [(h1, "inconclusive")]
          and {k: n["fm"].get("verdict") for k, n in E.Vault(root).nodes.items()} == verdicts2)
    # (`ok` is False here for an unrelated reason — h2's commitment is deliberately drifted
    #  above, and 15.3 makes drift a problem. What this asserts is that the unaccepted
    #  experiment is INFORMATION and never a problem or a warning of its own.)
    rep = E.validation_report(root)
    check("gate: an unaccepted dropped experiment is reported as info",
          "task:unaccepted" in info and info["task:unaccepted"]["count"] == 1
          and not any(x["id"].startswith("task:") for x in rep["problems"] + rep["warnings"]))

    # -- 13. a sub-task that declares its OWN conclusion is its own experiment and fires its
    #        own gate. Refusing would make the spec's pilot-blocks-full-run example illegal
    #        whenever both conclude.
    n1, _ = E.cmd_task_add(root, "Nested pilot", category="implementation", blocked_by=None,
                           parent=e1, hypothesis_refs=[(h1, "inconclusive")])
    E.cmd_task_done(root, n1, outputs=[f"[[{q}]]"])
    check("gate: a nested experiment fires its own gate",
          n1 in [x[0] for x in E.cmd_task_review(root)])
    check("gate: nesting is reported as info",
          any(x["id"] == "task:nested-experiment"
              for x in E.validation_report(root)["info"]))

    # -- 11. cmd_review is 15's THREE-tuple and stays exactly that. Extended, not reshaped.
    qrows = E.cmd_review(root)
    check("gate: the question review queue is untouched",
          all(len(r) == 3 and isinstance(r[2], bool) for r in qrows)
          and set(r[0] for r in qrows) <= set(E.Vault(root).nodes))
    snap = E.snapshot(root)
    check("gate: the question queue in snapshot is unchanged in shape",
          all(set(x) == {"id", "title", "summary"} for x in snap["queue"]))

    fx = tempfile.mkdtemp(prefix="crux_gate_fx_")
    dst = os.path.join(fx, "demo")
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    E.check_and_stamp_version(dst); E.refresh(dst)
    b = _dir_bytes(dst)
    rev0 = E.cmd_review(dst)
    E.refresh(dst); E.snapshot(dst); E.validation_report(dst)
    check("taskmig: a pre-08 vault's gate behaviour is unchanged at 2.3",
          _dir_bytes(dst) == b and E.cmd_review(dst) == rev0 and E.cmd_task_review(dst) == [])
    shutil.rmtree(fx, ignore_errors=True)

    # -- the CLI: the gate is visible where the PI stands, and drift is loud but never fatal
    import json as _json
    e4, _ = E.cmd_task_add(root, "Another drifted run", category="implementation",
                           blocked_by=None, hypothesis_refs=[(h2, "supported")])
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "done", e4,
                        "-o", f"[[{q}]]"], capture_output=True, text=True,
                       encoding="utf-8", cwd=root)
    check("gate: `task done` on an experiment prints the gate, not a verdict",
          r.returncode == 0 and "crux task accept" in r.stdout
          and "verdict" not in r.stdout.lower())
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "accept", e4,
                        "--json"], capture_output=True, text=True, encoding="utf-8", cwd=root)
    check("gate: the CLI accept prints drift to stderr and still succeeds",
          r.returncode == 0 and h2 in r.stderr
          and "edited after the run" in r.stderr
          and _json.loads(r.stdout)["drifted"] == [h2]
          and _json.loads(r.stdout)["accepted"])
    check("gate: ENGINE_VERSION bumped to 2.3", at_least_version("2.3"))
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
                      "items", "frontier", "queue"} and tb["active"] is True)
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
    check("ui: the acceptance queue reaches the snapshot",
          [x["id"] for x in tb["queue"]] == [t2]
          and tb["queue"][0]["hypothesis_refs"][0]["conclusion"] == "supported")

    # -- the webui must know every tab, category colour and conclusion the engine can emit.
    #    Derived from the constants rather than hand-listed, which is the one thing that made
    #    the verdict legend impossible to silently drift (selftest's own legend check).
    ui = read(os.path.join(HERE, "webui", "app.js"))
    html = read(os.path.join(HERE, "webui", "index.html"))
    css = read(os.path.join(HERE, "webui", "style.css"))
    tabs = re.findall(r'data-tab="([a-z]+)"', html)
    check("ui: the tab list covers tree, wiki, rd and tasks",
          set(tabs) >= {"tree", "wiki", "rd", "tasks"})
    check("ui: the cockpit knows the taskhub is inert when absent",
          "tasksActive" in ui and "tasks-pane" in html)
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
          "concluded" in ui and "derived by the engine from the ticks" in ui)

    # ---- INTERSECTION: 15.6 narrates drift/rule/kind on the node; 08.4 adds backlinks to
    # the same pane. ONE node carrying both is the exact overlap, so it gets its own fixture.
    both = tempfile.mkdtemp(prefix="crux_taskui_both_")
    E.cmd_init("Both", both, goal="g")
    bq, _ = E.cmd_ask(both, "does narration coexist with backlinks?")
    bh, _, _ = E.cmd_hypothesize(both, "it does", parent=bq, rule="all",
                                 verifiables=["alpha"], neutral=["the control"])
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
    # ---- INTERSECTION: drift is now narrated in TWO places, answering two questions —
    # "this claim's commitment moved" (15.6, the node) and "do you accept this run" (08.3,
    # the queue). Both must survive; neither replaces the other.
    tq = E.snapshot(both)["tasks"]["queue"]
    check("ui: queue drift survives 15.6's node-pane narration",
          [x["id"] for x in tq] == [be] and tq[0]["drifted"] == [bh]
          and E.lock_drift(E.Vault(both).get(bh)))
    shutil.rmtree(both, ignore_errors=True)

    # -- a vault with no tasks/ : present, inert, and the tab hides itself
    plain = tempfile.mkdtemp(prefix="crux_taskui_none_")
    E.cmd_init("No Tasks", plain, goal="g")
    ptb = E.snapshot(plain)["tasks"]
    check("taskmig: snapshot on a pre-08 vault has an inactive tasks block",
          ptb["active"] is False and ptb["items"] == [] and ptb["frontier"] == []
          and ptb["queue"] == [] and set(ptb) == set(tb))
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
    print("\n# taskhub — the skill rules and the spec amendments (spec 08, PRD 08.5)")
    skill = read(os.path.join(HERE, "..", "SKILL.md"))
    spec8 = read(os.path.join(HERE, "..", "..", "..", ".spec", "08-taskhub.md"))
    spec15 = read(os.path.join(HERE, "..", "..", "..", ".spec", "15-evidence-semantics.md"))
    spec7 = os.path.join(HERE, "..", "..", "..", ".spec", "07-rd-layer.md")

    check("skill: SKILL.md carries the work-never-creates-direction line",
          "Work never creates direction" in skill
          and "an output that is evidence\n> about a hypothesis enters the gated tier" in skill)
    check("skill: SKILL.md states what gets in and what stays scratch",
          "would you be annoyed if this vanished next week" in skill.lower()
          and "session scratch" in skill and "one context window" in skill)
    check("skill: SKILL.md marks accept as the PI's signature",
          "crux task accept" in skill and "never run it on your own judgment" in skill.lower())
    check("skill: SKILL.md distinguishes a derived verdict from a written conclusion",
          "Two provenances" in skill
          and "does **not** close h44" in skill)
    check("skill: SKILL.md carries the escape hatch",
          "stops being a task" in skill and "goes through the normal gate" in skill.lower()
          or "go through the normal gate" in skill)

    # every task sub-verb the CLI exposes is documented, derived from argparse rather than
    # hand-listed, so a verb added later cannot go undocumented silently
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "task", "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    verbs = {"add", "done", "drop", "list", "show", "categories", "review", "accept"}
    check("skill: every task verb is documented in CLI help",
          r.returncode == 0 and all(v in r.stdout for v in verbs))
    check("skill: the verb table matches the CLI's task verbs",
          all(f"`task {v}`" in skill or f"`{v}`" in skill for v in ("add", "done", "accept")))

    # -- the three .spec amendments (rulings D6 / D9 / D19)
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
                                 neutral=["the control"])
    # a CLOSED sibling: its findings ARE the shared factual record a skeptical colleague reads
    h2, _, _ = E.cmd_hypothesize(root, "an earlier sibling", parent=q1, rule="all",
                                 verifiables=["gamma"], neutral=["the control"])
    edit(node_path(root, h2), "- [ ] gamma", "- [x] gamma   (found: 0.71)")
    edit(node_path(root, h2), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    declare_null(root, h2)
    E.cmd_test(root, h2, to="running")
    E.cmd_close(root, h2, findings="the earlier run settled the preprocessing question")
    # the anchor's OWN results: present in the vault, and they must not reach its own brief
    edit(node_path(root, h1), "- [ ] alpha check", "- [x] alpha check   (found: 0.99-ANCHORS-OWN)")
    os.makedirs(os.path.join(root, "results", h1), exist_ok=True)
    with open(os.path.join(root, "results", h1, "metrics.json"), "w", encoding="utf-8") as f:
        f.write('{"auroc": {"value": 0.815, "ci": [0.79, 0.84]}}')

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
    check("brief: a closed sibling's findings are the shared record",
          any(p["id"] == h2 and "preprocessing question" in p["findings"]
              for p in b["prior_findings"]))
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
    """Spec 09 PRD 09.1 — `## Null`, the boring explanation, PI-gated.

    The brief removes the parent's authored prompt, but one leak cannot be engineered away:
    the hypothesis TITLE is directional. "masked-token beats masked-stem" presumes a winner.
    The answer is not to neutralise it but to push against it — name the cheapest way this
    result could be trivially true, then make the checks discriminate against THAT.

    Three goalposts, all in code, because instructions will not hold this: the crux skill
    already said "keep the science explicit" and produced 5,725-word nodes."""
    print("\n# specialized agents — the null and its gate (spec 09, PRD 09.1)")
    root = tempfile.mkdtemp(prefix="crux_null_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Nulls", root)
    q1, _ = E.cmd_ask(root, "does the null gate hold?")

    def mk(title, **kw):
        kw.setdefault("verifiables", ["alpha"]); kw.setdefault("neutral", ["ctl"])
        # this block is about the NULL, so the other gates are satisfied up front
        kw.setdefault("fails_if", ["the width-matched arm also clears it", "the control broke"])
        kw.setdefault("discriminates", [True, False])
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
          dp["anchor"]["null"].startswith("capacity")
          and dp["anchor"]["null_approved"] is False)
    check("null: the deck reports approval as a boolean, never a timestamp",
          isinstance(dp["anchor"]["null_approved"], bool)
          and not re.search(r"\d{4}-\d\d-\d\dT", json.dumps(dp)))

    check("null: every confound family is accepted",
          all(E.null_problem(f"{fam} — the instance", 1) is None for fam in E.CONFOUND_FAMILIES))
    check("null: a null naming no family is refused, and the message lists them",
          "capacity" in (E.null_problem("the numbers were just nicer", 1) or ""))
    check("null: a null over 25 words is refused",
          "25" in (E.null_problem("chance — " + " ".join(["word"] * 30), 1) or ""))
    check("null: a 25-word null is accepted (the cap is inclusive)",
          E.null_problem("chance — " + " ".join(["w"] * 23), 1) is None)
    check("null: a pre-15 node is never asked for one", E.null_problem("", 0) is None)

    expect_error("null: running is refused with no null at all",
                 lambda: E.cmd_test(root, mk("no null"), to="running"))
    expect_error("null: running is refused with an unapproved null",
                 lambda: E.cmd_test(root, h1, to="running"))
    check("null: the refusal names the approval route",
          "approve-null" in _err_text(lambda: E.cmd_test(root, h1, to="running")))
    stamp = E.cmd_approve_null(root, h1)
    check("null: approval stamps a timestamp", bool(stamp) and "T" in stamp)
    check("null: approval is idempotent", E.cmd_approve_null(root, h1) == stamp)
    ran = E.cmd_test(root, h1, to="running")
    check("null: an approved null unblocks running", ran == "running")

    edit(node_path(root, h1), "capacity — the extra parameters alone explain it",
                              "leakage — the split let the answer through")
    check("null: editing an approved null voids the approval",
          any(i == h1 and "EDITED after approval" in m for i, m in E.cmd_validate(root)))
    E.cmd_approve_null(root, h1)
    check("null: re-approving the edited null clears the flag", E.cmd_validate(root) == [])

    h3 = mk("two nulls", null="chance — noise")
    edit(node_path(root, h3), "chance — noise",
                              "chance — noise\nselection — the sample was picked")
    check("null: exactly one null",
          any(i == h3 and "exactly one" in m for i, m in E.cmd_validate(root)))

    h4 = mk("bad family")
    n4 = E.Vault(root).get(h4)
    E.write_if_changed(n4["path"],
                       E.render_doc(n4["fm"], E.set_null(n4["body"], "the numbers came out nicer")))
    check("null: a malformed null is a validate problem before any run",
          any(i == h4 for i, m in E.cmd_validate(root)))

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

    # ---- the gate
    root = tempfile.mkdtemp(prefix="crux_fs_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Scenarios", root)
    q1, _ = E.cmd_ask(root, "do scenarios gate?")
    h1, _, _ = E.cmd_hypothesize(root, "with scenarios", parent=q1, rule="all",
                                 null="capacity — width alone explains the gain",
                                 verifiables=["alpha", "beta"], neutral=["the control"],
                                 fails_if=["the width-matched arm also clears it",
                                           "beta moves for an unrelated reason",
                                           "the preprocessing path changed"],
                                 discriminates=[True, False, False])
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
    E.cmd_approve_null(root, h1)
    check("fails: a complete hypothesis runs", E.cmd_test(root, h1, to="running") == "running")

    def mk(title, **kw):
        kw.setdefault("verifiables", ["alpha", "beta"]); kw.setdefault("neutral", ["ctl"])
        kw.setdefault("rule", "all"); kw.setdefault("null", "chance — noise explains it")
        hid, _, _ = E.cmd_hypothesize(root, title, parent=q1, **kw)
        E.cmd_approve_null(root, hid)
        return hid

    h2 = mk("no scenarios")
    expect_error("fails: running is refused with a missing scenario",
                 lambda: E.cmd_test(root, h2, to="running"))
    check("fails: every verifiable needs a failure scenario",
          "failure scenario" in _err_text(lambda: E.cmd_test(root, h2, to="running")))
    check("fails: a DRAFT is not nagged for scenarios it has not written yet",
          not any(i == h2 and "failure scenario" in m for i, m in E.cmd_validate(root)))

    h3 = mk("identical scenarios", fails_if=["the same world", "the same world", "ctl broke"],
            discriminates=[True, False, False])
    check("fails: two identical failure scenarios are flagged",
          any(i == h3 and "same" in m.lower() for i, m in E.cmd_validate(root)))

    h4 = mk("nothing discriminates", fails_if=["world a", "world b", "ctl broke"])
    check("fails: at least one verifiable must discriminate against the null",
          "discriminat" in _err_text(lambda: E.cmd_test(root, h4, to="running")))
    expect_error("fails: running is refused when nothing discriminates",
                 lambda: E.cmd_test(root, h4, to="running"))

    # ---- the CLI is additive: a bare -v still works (never a second -v argument)
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize", "cli built",
                        "-p", q1, "-v", "alpha", "--fails-if", "world a", "--discriminates",
                        "-n", "ctl", "--fails-if", "ctl broke",
                        "--null", "chance — noise", "--rule", "all"],
                       capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    hc = [x for x in E.Vault(root).nodes if x.startswith("h")][-1]
    body = E.Vault(root).get(hc)["body"]
    check("fails: --fails-if pairs with the preceding verifiable",
          r.returncode == 0 and "fails-if:: world a" in body
          and "discriminates:: true" in body and "fails-if:: ctl broke" in body)
    r2 = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize", "bare v",
                         "-p", q1, "-v", "alpha", "-n", "ctl"],
                        capture_output=True, cwd=root, encoding="utf-8", errors="replace")
    check("fails: a bare -v is still accepted (no second positional argument)",
          r2.returncode == 0)

    check("fails: ENGINE_VERSION at or past 2.6", at_least_version("2.6"))
    check("fails: SCHEMA_GENERATION is 2", E.SCHEMA_GENERATION == 2)
    shutil.rmtree(root, ignore_errors=True)

    # ---- D1: the scenario IS the commitment, and generation 1 keeps its old material
    root = tempfile.mkdtemp(prefix="crux_fsl_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Locks2", root)
    q1, _ = E.cmd_ask(root, "q")
    hg2, _, _ = E.cmd_hypothesize(root, "gen two", parent=q1, rule="all",
                                  null="chance — noise", verifiables=["alpha"], neutral=["ctl"],
                                  fails_if=["world a", "ctl broke"], discriminates=[True, False])
    E.cmd_approve_null(root, hg2); E.cmd_test(root, hg2, to="running")
    n = E.Vault(root).get(hg2)
    check("fails: a generation-2 node locks generation-2 material",
          E.node_schema(n) == 2 and "world a" in E.lock_material(n))
    edit(node_path(root, hg2), "fails-if:: world a", "fails-if:: a completely different world")
    check("fails: a failure scenario added or changed after running is drift",
          E.lock_drift(E.Vault(root).get(hg2)))

    # a node stamped generation 1 keeps the material it was locked with — the whole of D1
    hg1, _, _ = E.cmd_hypothesize(root, "gen one", parent=q1, rule="all",
                                  null="chance — noise", verifiables=["alpha"], neutral=["ctl"],
                                  fails_if=["world a", "ctl broke"], discriminates=[True, False])
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
                                 fails_if=["world a", "ctl broke"], discriminates=[True, False])
    # rewind it to generation 1 and lock it with generation-1 material, as 2.5 would have
    E.cmd_approve_null(old, oh)
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
          all(f not in n["fm"] for n in v.nodes.values() for f in E.MIGRATE_FORBIDDEN))
    check("evmig: the Null it adds is EMPTY — naming the boring explanation is a scientific act",
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

    # ---- the gate backlog, the one audit check spec 09 asked for that did not exist
    root = tempfile.mkdtemp(prefix="crux_gate_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Gate", root)
    q1, _ = E.cmd_ask(root, "a question that will sit in review")
    h1, _, _ = E.cmd_hypothesize(root, "h", parent=q1, rule="all", null="chance — noise",
                                 verifiables=["alpha"], neutral=["ctl"],
                                 fails_if=["world a", "ctl broke"], discriminates=[True, False])
    declare_null(root, h1)
    E.cmd_test(root, h1, to="running")
    edit(node_path(root, h1), "- [ ] alpha", "- [x] alpha")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] ctl", "- [x] [outcome-neutral] ctl")
    E.cmd_close(root, h1)
    # node-scoped checks carry the bare node id, matching `economy`/`fanout`
    gate = E.validation_report(root, ["gate"])["warnings"]
    check("migrate: a question parked in review with no synthesis is a gate-backlog warning",
          any(w["id"] == q1 and "no synthesis drafted" in w["message"] for w in gate))
    check("migrate: --check=gate is opt-in and does not fire on the default lint",
          not any("no synthesis drafted" in w["message"]
                  for w in E.validation_report(root)["warnings"]))
    E.cmd_synthesize(root, "what q1 settled", [q1])
    check("migrate: drafting the synthesis clears the backlog warning",
          not E.validation_report(root, ["gate"])["warnings"])
    shutil.rmtree(root, ignore_errors=True)


def run_agent_roster():
    """Spec 09 PRD 09.4 — the agent-definition convention and the roster.

    Six of 09's seven agents were described and none existed. More basic: crux had no
    convention for what an agent definition IS. Spec 14's PARKED-09.md names exactly that as
    its blocker — "the agent file format is a 09 deliverable; there is no convention to write
    it against" — and spec 13 waits on the same thing plus `crux brief`.

    Doc-only: no engine change, no version bump. What makes it assertable is that the three
    fields carrying 09's architecture (cold_input, toolbelt, excludes) are checkable."""
    print("\n# specialized agents — the roster (spec 09, PRD 09.4)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    adir = os.path.join(repo, "agents")
    expected = ["crux-null", "crux-verifiables", "crux-critic", "crux-migrate",
                "crux-close", "crux-audit", "crux-tests", "crux-glossary"]

    defs = {}
    for name in expected:
        p = os.path.join(adir, name, "AGENT.md")
        if os.path.isfile(p):
            defs[name] = E.parse_doc(read(p))
    missing = [n for n in expected if n not in defs]
    check(f"agents: every roster entry has a definition file (missing: {missing})", not missing)

    for name, (fm, body) in sorted(defs.items()):
        check(f"agents: {name} declares the four architecture fields",
              all(k in fm for k in ("name", "description", "cold_input", "excludes")))
        check(f"agents: {name}'s name matches its directory", fm.get("name") == name)
        check(f"agents: {name} reads as a workflow (when invoked -> steps -> output)",
              "When invoked" in body and "## Output" in body)

    # every toolbelt entry must be a REAL crux verb — 09 is explicit that the belt is CLI
    # verbs, not agent-private scripts, so selftest can assert them and the PI can run any by hand
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    bad = []
    for name, (fm, _b) in sorted(defs.items()):
        for line in str(fm.get("toolbelt") or "").split(";"):
            line = line.strip()
            if not line:
                continue
            if not line.startswith("crux "):
                bad.append(f"{name}: {line!r} is not a crux verb")
            elif line.split()[1] not in r.stdout:
                bad.append(f"{name}: no such verb {line.split()[1]!r}")
    check(f"agents: every toolbelt entry is a real crux verb (bad: {bad[:3]})", not bad)

    # the two isolation guarantees, declared where a reviewer can diff them against behaviour
    crit_fm, _ = defs.get("crux-critic", ({}, ""))
    check("agents: the critic is isolated by construction — no vault, empty toolbelt",
          not str(crit_fm.get("toolbelt") or "").strip()
          and "vault" in str(crit_fm.get("excludes") or "").lower())
    ver_fm, _ = defs.get("crux-verifiables", ({}, ""))
    check("agents: crux-verifiables declares the exclusion the brief actually enforces",
          "Problem Statement" in str(ver_fm.get("excludes") or ""))
    check("agents: and the brief really does enforce it (cross-checked, not just declared)",
          "problem" not in E.brief(*_probe_vault()))

    # THE LEASH. The TOOLBELT is the authority — what an agent may run — so that is what is
    # checked. Prose is not: crux-close's body says "you do not run `crux close`", which is a
    # mention and exactly the right thing for it to say.
    leash = []
    for name, (fm, _b) in sorted(defs.items()):
        belt = str(fm.get("toolbelt") or "")
        for banned in ("crux close", "crux answer", "crux approve", "crux task accept",
                       "crux pursue", "crux migrate --apply"):
            if banned in belt:
                leash.append(f"{name}: {banned}")
    check(f"agents: no agent's toolbelt can set a verdict or a direction (found: {leash})",
          not leash)
    check("agents: and crux-close says so in words, since it is the one that could",
          "you never run `crux close`" in read(os.path.join(adir, "crux-close", "AGENT.md")).lower())

    # spec 14 parked a precise contract here; it must match what shipped
    gl_fm, _ = defs.get("crux-glossary", ({}, ""))
    check("agents: the glossary agent matches spec 14's parked contract",
          "propose" in str(gl_fm.get("cold_input") or "")
          and "no write verb" in str(gl_fm.get("toolbelt") or "").lower()
          and "conversation" in str(gl_fm.get("excludes") or "").lower())

    spec = read(os.path.join(repo, ".spec", "09-specialized-agents.md"))
    check("agents: the spec roster and the shipped roster agree",
          all(n in spec for n in expected))
    check("agents: spec 09 is flipped to done with its work items ticked",
          "**Status:** \u2611" in spec and spec.count("- \u2611 ") >= 8)
    readme = read(os.path.join(repo, ".spec", "README.md"))
    check("agents: the backlog index shows 09 done",
          re.search(r"\|\s*09\s*\|[^|]*\|[^|]*\|\s*\u2611\s*\|", readme) is not None)
    # 09.4 was doc-only, and asserted that by pinning ENGINE_VERSION == "2.7" — a literal
    # that any later, legitimate bump falsifies (spec 14's 14.0 is the first). The property
    # actually worth locking is the durable one: the roster is VERSION-INDEPENDENT. An agent
    # definition that named an engine version would have to be revised on every bump, which
    # is precisely the coupling 09 avoided by putting the toolbelt in CLI verbs.
    versioned = sorted(n for n, (fm, b) in defs.items()
                       if re.search(r"engine[ _-]?version", (str(fm) + b), re.I))
    check(f"agents: no agent definition pins an engine version (found: {versioned})",
          not versioned)


def _probe_vault():
    """A throwaway vault whose hypothesis has a sentinel problem statement, for the
    cross-check that the brief's behaviour matches what the roster declares."""
    root = tempfile.mkdtemp(prefix="crux_probe_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Probe", root)
    q, _ = E.cmd_ask(root, "q")
    h, _, _ = E.cmd_hypothesize(root, "claim", parent=q, problem="ADVOCACY", verifiables=["a"])
    return root, h


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
    h1, _, _ = E.cmd_hypothesize(root, "an old idea", parent=q1, verifiables=["x"])
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
    check("gmig: review still runs", isinstance(E.cmd_review(root), list))
    check("gmig: snapshot still serializes", isinstance(E.snapshot(root), dict))
    E.refresh(root)
    check("gmig: no read path creates glossary.md", not os.path.exists(gp))
    warn = E.check_and_stamp_version(root)
    check("gmig: a 2.7 vault reports drift", warn is not None and "2.7" in warn)
    check("gmig: drift re-stamps to the current version",
          str(E.Vault(root).cfg.get("engine_version")) == E.ENGINE_VERSION)
    shutil.rmtree(root, ignore_errors=True)

    # -- the shipped fixture, byte-compared. The strongest form of "old vaults still load":
    #    every read path runs and NOTHING on disk moves except the version stamp.
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    dst = tempfile.mkdtemp(prefix="crux_gdemo_")
    shutil.rmtree(dst); shutil.copytree(src, dst)
    before = _tree_hashes(dst)
    E.cmd_validate(dst); E.status_text(dst); E.cmd_review(dst); E.snapshot(dst)
    E.refresh(dst); E.check_and_stamp_version(dst)
    after = _tree_hashes(dst)
    moved = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
    check(f"gmig: demo_vault byte-compare — only .crux.yaml moves (moved: {moved})",
          moved in ([], [".crux.yaml"]))
    check("gmig: demo_vault gained no glossary.md",
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
                                 problem="the detection floor again", verifiables=["x"])
    h2, _, _ = E.cmd_hypothesize(root, "unrelated", parent=q1, problem="nothing", verifiables=["y"])
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
        case+plural guess. They are why the rule is what it is."""
    print("\n# glossary — the frozen oracle (spec 14, PRD 14.1)")
    ex = os.path.join(HERE, "..", "examples")
    ORACLE = {
        "segssl_vault": [("mask transformer head", 3, 12, 2), ("dense contrastive pretraining", 6, 12, 2),
                         ("label efficiency", 17, 26, 0), ("pre-registered bar", 9, 9, 0),
                         ("frozen linear probe", 4, 10, 1), ("label-efficient segmentation", 1, 2, 1)],
        "scaling_vault": [("power law", 6, 16, 0), ("data floor", 1, 2, 1)],
        "demo_vault":    [("masked token", 1, 3, 1), ("jepa encoder", 1, 3, 1)],
    }
    SIZES = {"demo_vault": 8, "scaling_vault": 37, "segssl_vault": 43}
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


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["close", "--help"], ["hypothesize", "--help"], ["serve", "--help"],
                 ["selftest", "--help"], ["approve", "--help"], ["synthesize", "--help"], ["deck", "--help"],
                 ["brief", "--help"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True, encoding="utf-8")
        check(f"help: crux {' '.join(argv)}", r.returncode == 0 and len(r.stdout) > 40)

    # -- the post-init hint must work from where the user just ran init: the vault is
    #    created *below* the cwd, so the hint carries the cd into it
    tmp = tempfile.mkdtemp(prefix="crux-hint-")
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "init", "Hint Project"],
                           capture_output=True, text=True, encoding="utf-8", cwd=tmp)
        check("init hint: includes `cd cruxvault`", r.returncode == 0 and "cd cruxvault" in r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default=None, help="build the demo vault at this path and keep it")
    a = ap.parse_args()
    # the suite is hermetic: no crux invocation it spawns may reach the network for an
    # update check (the check's own logic is exercised offline with an injected fetcher).
    os.environ["CRUX_NO_UPDATE_CHECK"] = "1"
    root = run_demo(a.keep)
    run_seed()
    run_wiki()
    run_wiki_migration()
    run_version()
    run_integrity()
    run_artifacts()
    run_close_gate()
    run_update()
    run_snapshot()
    run_wiki_gui()
    run_serve()
    run_file_route()
    run_webui()
    run_economy()
    run_economy_migration()
    run_agent_cli()
    run_rd()
    run_rd_migration()
    run_rd_lint()
    run_rd_skill()
    run_deck_rd()
    run_rd_gui()
    run_deck()
    run_deck_verify()
    run_prezit()
    run_evidence_boundary()
    run_verifiable_kind()
    run_combination_rule()
    run_hash_lock()
    run_rulebook()
    run_taskhub()
    run_task_graph()
    run_experiments()
    run_experiment_gate()
    run_task_gui()
    run_taskhub_skill()
    run_cockpit_evidence()
    run_brief()
    run_null()
    run_failure_scenarios()
    run_migrate()
    run_agent_roster()
    run_glossary()
    run_glossary_migration()
    run_glossary_counting()
    run_glossary_oracle()
    run_cli_help()
    print(f"\n{'='*48}\n  PASSED {len(_PASS)} / {len(_PASS)+len(_FAIL)}")
    if _FAIL:
        print("  FAILURES:")
        for f in _FAIL: print("   - " + f)
        sys.exit(1)
    print(f"  demo vault {'kept at '+root if a.keep else '(temp, removed)'}")
    if not a.keep:
        shutil.rmtree(root, ignore_errors=True)
    print("  ALL GREEN")


if __name__ == "__main__":
    main()
