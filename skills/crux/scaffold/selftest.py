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
    check("ui: the tab list is tree, wiki and the taskhub — RD merged in, not beside",
          set(tabs) == {"tree", "wiki", "tasks"})
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


# The roster as it stood before 05.3, so the criterion can say the list grew by exactly two
# rather than merely that it now holds twelve names.
AG_ROSTER_052 = ("crux-null", "crux-verifiables", "crux-critic", "crux-migrate",
                 "crux-close", "crux-audit", "crux-tests", "crux-glossary",
                 "crux-situate", "crux-design")

# `crux doctor` warnings that are facts about the MACHINE the suite runs on, not about the
# repository: `cmd_doctor` reads `~/.claude/settings.json` for the chat-time voice lint, and
# that warning is in `origin/main`'s engine, so it predates this slice. PRD-1's "no new
# warning" is about warnings 05.3 could cause, and this is not one.
AG_DOCTOR_PRE_WARNS = ("voice-hook",)


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
    # AMENDED by spec 13, not replaced: 09.4's assert exists to stop a roster that describes
    # agents nobody shipped and a directory of agents nobody described. 13 is the first spec
    # to add to the directory, so the list grows and `.spec/09`'s roster grows with it.
    # AMENDED AGAIN by spec 05 (PRD 05.3): autopilot is the second spec to add to the
    # directory. The worker and the steward are roster agents like any other — they carry the
    # same five fields, the same dirname rule and the same `no-version-pin` property — so the
    # list grows by two and every per-definition property is computed for them too.
    expected = list(AG_ROSTER_052) + ["crux-auto-worker", "crux-auto-steward"]

    # The definition-derived properties live in `evals.roster_properties` (spec 10, PRD 10.2),
    # so that ONE source of truth is both printed here and broken on purpose by the mutation
    # harness. The assert names below are unchanged by that extraction — `run_mutation_harness`
    # pins that, because the evolve-crux gate counts asserts.
    import evals as V
    defs = V.load_definitions(expected, repo)
    missing = [n for n in expected if n not in defs]
    check(f"agents: every roster entry has a definition file (missing: {missing})", not missing)

    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "--help"],
                       capture_output=True, text=True, encoding="utf-8")
    P = V.roster_properties(defs, r.stdout)
    for slug in ([f"{k}:{n}" for n in sorted(defs) for k in ("fields", "dirname", "workflow")]
                 + ["belt-verbs", "critic-isolated", "verifiables-exclusion"]):
        check(*P[slug])
    check("agents: and the brief really does enforce it (cross-checked, not just declared)",
          "problem" not in E.brief(*_probe_vault()))
    for slug in ("leash", "close-says-so", "glossary-contract"):
        check(*P[slug])

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
    check(*P["no-version-pin"])

    # ---------------------------------------------------- spec 05 PRD 05.3 §A — the two agents
    # The roster grew, so three things have to be true at once: the directory holds twelve
    # definitions, `crux doctor` counts twelve and says nothing new, and the four definitions
    # 05.3 REUSES are byte-identical. The last is the one worth the trouble: `crux-close` is
    # wired into the driver in this slice, and the whole claim of PRD §F is that it is wired in
    # UNCHANGED — an agent quietly reworded to suit the driver would pass every other check
    # here while turning a reused reviewer into a driver-shaped one.
    ag_links = tempfile.mkdtemp(prefix="crux_ag53_")
    try:
        on_disk = sorted(d for d in os.listdir(adir)
                         if os.path.isfile(os.path.join(adir, d, "AGENT.md")))
        for n in on_disk:
            os.symlink(os.path.join(adir, n, "AGENT.md"), os.path.join(ag_links, n + ".md"))
        doc = _auto_val(lambda: E.cmd_doctor(root=None, skills_dirs=None,
                                             agents_dir=ag_links), {})
        check("agents: the two autopilot agent definitions join the roster and doctor counts twelve with no new warning",
              _auto_ok(lambda: (
                  sorted(defs) == sorted(expected) and len(expected) == 12
                  and "crux-auto-worker" in defs and "crux-auto-steward" in defs
                  and on_disk == sorted(expected)
                  and _level(doc, "agents") == "ok"
                  and _check(doc, "agents")["detail"].startswith("12 crux-*.md in ")
                  # the roster grew by exactly these two and nothing else
                  and sorted(set(expected) - set(AG_ROSTER_052))
                      == ["crux-auto-steward", "crux-auto-worker"]
                  and len(AG_ROSTER_052) == 10
                  # NO NEW warning. `voice-hook` is not one: `cmd_doctor` reads
                  # `~/.claude/settings.json`, so that warning is a fact about the machine the
                  # suite runs on, it is in origin/main's engine, and it predates this slice
                  # entirely. What this slice owns is that no warning is attributable to it.
                  and [c["name"] for c in doc["checks"] if c["level"] == "warn"
                       and c["name"] not in AG_DOCTOR_PRE_WARNS] == []
                  and not [c for c in doc["checks"] if c["level"] != "ok"
                           and ("crux-auto-worker" in json.dumps(c)
                                or "crux-auto-steward" in json.dumps(c))]
                  and [c["name"] for c in doc["checks"] if c["level"] == "error"] == [])))
    finally:
        shutil.rmtree(ag_links, ignore_errors=True)

    # PRD-2. The instruction and the validator cannot be allowed to drift: the body a model
    # reads has to print the SAME key list the engine refuses outside of. Two renderings are
    # legal — a JSON object in a fenced block, or the keys as backticked tokens — and both are
    # asserted as set EQUALITY against the engine constant, so a body that forgot `controls`
    # and a body that invited `verdict` are each caught.
    _SCHEMA_WORDS = {"claim", "controls", "fails_if", "text", "guidance", "island", "title",
                     "problem", "ticks", "findings", "report", "verdict", "value", "score"}

    def _prints_schema(name, top, nested):
        body = defs.get(name, ({}, ""))[1] or ""      # load_definitions gives (frontmatter, body)
        want_top, want_nested = set(top or ()), set(nested or ())
        if not body or not want_top:
            return False
        blocks = re.findall(r"```[a-zA-Z0-9]*\n(.*?)```", body, re.S)
        for b in blocks:
            obj = _auto_val(lambda t=b: json.loads(t))
            if not isinstance(obj, dict) or set(obj) != want_top:
                continue
            for v in obj.values():                  # the nested object, wherever it is written
                if isinstance(v, list) and v:
                    v = v[0]
                if isinstance(v, dict) and set(v) == want_nested:
                    return True
        ticked = set(re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)`", body)) & _SCHEMA_WORDS
        return ticked == (want_top | want_nested)

    check("agents: each autopilot agent body names the closed proposal schema the engine validator reads",
          _auto_ok(lambda: (
              _prints_schema("crux-auto-worker", E.AUTO_PROPOSAL_KEYS, E.AUTO_CONTROL_KEYS)
              and _prints_schema("crux-auto-steward", E.AUTO_STEWARD_KEYS, E.AUTO_ISLAND_KEYS)
              and set(E.AUTO_PROPOSAL_KEYS) == {"claim", "controls"}
              and set(E.AUTO_CONTROL_KEYS) == {"fails_if", "text"}
              and set(E.AUTO_STEWARD_KEYS) == {"guidance", "island"}
              and set(E.AUTO_ISLAND_KEYS) == {"title", "problem"})))

    # PRD-3. The shas were read off disk at the base commit of this slice. A literal here is
    # the point: `git diff --stat` proves nothing to a reader six months from now, and these
    # four files are the ones the slice is most tempted to edit.
    REUSED_SHA = {
        "crux-close": "24c0121a494c54d8fdfb18e661325f6ed58c5cfbb27079a7eac4f25ee5edad0d",
        "crux-null": "26f1c5ee36bb6a2fbcdaa438d1c524017ab512c0b1a547200b19665cc07507d6",
        "crux-verifiables": "307daa3e363358ea26b3a037596345fb0b2e6cc55219c862bd999fb18c0f7d2a",
        "crux-design": "01a9d2d7bb4f92e21aac04800a3f6edfc99b914b027458fd49fa2b6d3c9a5584"}
    drifted = sorted(
        n for n, want in REUSED_SHA.items()
        if _auto_val(lambda p=os.path.join(adir, n, "AGENT.md"):
                     hashlib.sha256(open(p, "rb").read()).hexdigest()) != want)
    check(f"agents: crux-close, crux-null, crux-verifiables and crux-design are byte-identical by sha (drifted: {drifted})",
          not drifted)


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
                                    neutral=["the control"])
    hidea, _, _ = E.cmd_hypothesize(root, "the untried claim", parent=qmid, rule="all",
                                    verifiables=["gamma check"], neutral=["the control"])
    hrun, _, _ = E.cmd_hypothesize(root, "the claim in flight", parent=qmid, rule="all",
                                   verifiables=["delta check"], neutral=["the control"])
    for h in (hdone, hrun):
        declare_null(root, h)
    edit(node_path(root, hdone), "- [ ] alpha check", "- [x] alpha check")
    edit(node_path(root, hdone), "- [ ] [outcome-neutral] the control",
                                 "- [x] [outcome-neutral] the control")
    E.cmd_test(root, hdone, to="running")
    E.cmd_close(root, hdone, findings="the settled claim held at the declared threshold")
    E.cmd_test(root, hrun, to="running")
    # the parent's answer-so-far: "where we are" usually needs it
    edit(node_path(root, qtop), "_(interpretation — written by the PI/agent; auto-flagged stale when new evidence lands)_",
         "So far the direction looks right, on one settled claim.")
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
                      sentinel=SENTINEL)


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
    check("situate: findings travel only with a closed hypothesis",
          s["subtree"][0]["findings"] and s["subtree"][1]["findings"] is None
          and s["subtree"][2]["findings"] is None)

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
          ph["anchor"]["id"] == hdone and ph["subtree"] == [] and ph["synthesis"] is None
          and ph["anchor"]["findings"])
    whole = E.brief(root, None, mode="situate")
    check("situate: no argument means the whole programme",
          whole["anchor"]["id"] == "root"
          and [c["id"] for c in whole["subtree"]] == [ids["qtop"], ids["qout"]])
    expect_error("situate: a synthesis anchor is refused",
                 lambda: E.brief(root, E.cmd_synthesize(root, "x", [qmid])[0], mode="situate"))

    # ---- only an APPROVED synthesis is an answer
    syn, _ = E.cmd_synthesize(root, "what the mid question settled", [qmid])
    check("situate: an unapproved synthesis stays out of the payload",
          E.brief(root, qmid, mode="situate")["synthesis"] is None)
    E.cmd_approve(root, syn)
    check("situate: only an approved synthesis reaches the payload",
          E.brief(root, qmid, mode="situate")["synthesis"]["id"] == syn)

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
          os_["subtree"][0]["verdict"] is None and os_["subtree"][0]["schema"] == 0
          and os_["anchor"]["schema"] == 0)
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
                 "situate-lints", "situate-shape"):
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
                                 replicates="5 seeds x 3 folds; n = 15 per arm")
    h2, _, _ = E.cmd_hypothesize(root, "the undeclared claim", parent=q1, rule="all",
                                 verifiables=["beta"], neutral=["the control"])
    hidea, _, _ = E.cmd_hypothesize(root, "a raw idea nobody has staged", parent=q1,
                                    rule="all", verifiables=["gamma"], neutral=["the control"])
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
    for h in (h1, h2):
        declare_null(root, h)
    E.cmd_test(root, h2, to="staged")
    rep = E.validation_report(root)
    ids = {i["id"]: i for i in rep["info"]}
    check("design: a staged hypothesis with no measurement is reported as info",
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

    # ---- and they never touch the verdict
    edit(node_path(root, h1), "- [ ] alpha", "- [x] alpha")
    edit(node_path(root, h1), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    E.cmd_close(root, h1)
    E.cmd_test(root, h2, to="running")
    edit(node_path(root, h2), "- [ ] beta", "- [x] beta")
    edit(node_path(root, h2), "- [ ] [outcome-neutral] the control",
                              "- [x] [outcome-neutral] the control")
    E.cmd_close(root, h2)
    vv = E.Vault(root)
    check("design: the slots never touch the verdict",
          vv.get(h1)["fm"]["verdict"] == vv.get(h2)["fm"]["verdict"] == "supported")
    check("design: a closed hypothesis is not retro-flagged — its design is history",
          not [i for i in E.validation_report(root)["info"]
               if i["id"].startswith("design:") and i["count"] > 1])

    # ---- the CLI
    r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize",
                        "from the CLI", "-p", q1, "-v", "delta", "-n", "the control",
                        "--rule", "all", "--measurement", "a named instrument",
                        "--replicates", "3 seeds", "--json"],
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
    re-verdicts, nothing goes red."""
    print("\n# design — the pre-13 boundary (spec 13, PRD 13.2)")
    src = os.path.join(HERE, "..", "examples", "demo_vault")
    dst = tempfile.mkdtemp(prefix="crux_dmig_")
    shutil.rmtree(dst); shutil.copytree(src, dst)

    before, vbefore, sbefore = fingerprint(dst)
    E.check_and_stamp_version(dst)
    E.refresh(dst); E.snapshot(dst); E.cmd_validate(dst); E.status_text(dst); E.cmd_review(dst)
    after, vafter, safter = fingerprint(dst)
    check("dmig: a pre-13 vault is byte-identical after the bump", before == after)
    check("dmig: no recorded verdict moved", vbefore == vafter and sbefore == safter)
    rep = E.validation_report(dst)
    check("dmig: a pre-13 vault reports no new problems and no new warnings",
          rep["problems"] == [] and rep["warnings"] == [] and rep["ok"] is True)
    check("dmig: no command retro-writes a methodology slot",
          all(x["fm"].get("measurement") in (None, "") for x in E.Vault(dst).nodes.values()))
    check("dmig: drift re-stamps to the current ENGINE_VERSION",
          E.Vault(dst).cfg.get("engine_version") == E.ENGINE_VERSION)
    shutil.rmtree(dst, ignore_errors=True)


def run_design_agent():
    """Spec 13 PRD 13.3 — `crux-design`, and the three-disease taxonomy into the skill.

    Spec 15 supplies the schema that makes a partial answer DETECTABLE after the run. Nothing
    applied it BEFORE. This agent does, around one question — *is there any plausible outcome
    of this run from which we would conclude nothing?*

    It checks all three causes, because a partial answer does not announce which one it has,
    and it FIXES only the third: (a) a compound claim is `crux-critic`'s, (b) a non-entailed
    check is `crux-verifiables`'. Absorbing either would violate 09's one-job rule and rebuild
    the bias problem those agents exist to solve.

    Doc-only: no engine change, no version bump."""
    print("\n# design — the crux-design agent and the taxonomy (spec 13, PRD 13.3)")
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    fm, body = E.parse_doc(read(os.path.join(repo, "agents", "crux-design", "AGENT.md")))
    import evals as V
    P = V.roster_properties(V.load_definitions(["crux-design"], repo))
    for slug in ("design-isolated", "design-excludes", "design-readonly", "design-taskhub",
                 "design-question", "design-taxonomy", "design-handoff", "design-proposal"):
        check(*P[slug])
    check("agents: crux-design fills the slots spec 13 gave the engine",
          E.MEASUREMENT_FIELD in body and E.REPLICATES_FIELD in body)

    # ---- the taxonomy, into the skill (the rulebook sentence shipped with spec 15's 15.5)
    skill = read(os.path.join(HERE, "..", "SKILL.md"))
    check("skill: the three-disease taxonomy is in SKILL.md, with its owners",
          all(x in skill for x in ("compound claim", "crux-critic", "crux-verifiables",
                                   "crux-design"))
          and "could not discriminate" in skill)
    check("skill: the taxonomy states the question that makes it operational",
          "conclude nothing" in skill)
    check("skill: the separability rulebook sentence spec 15 froze is still there",
          "anything less means you ran one experiment with many labels, not many"
          in re.sub(r"\s+", " ", skill.replace("**", "")).lower())
    check("skill: SKILL.md tells the PI where a declared design lives",
          "measurement:" in skill and "replicates:" in skill)

    # ---- the spec, flipped, with the roster amendment recorded where a reader will find it
    spec13 = read(os.path.join(repo, ".spec", "13-situate-and-design.md"))
    check("agents: spec 13 is flipped to done", "**Status:** ☑" in spec13)
    check("agents: spec 13's work items are ticked", spec13.count("- ☑ ") >= 7)
    check("agents: spec 13 records the roster amendment it owes spec 09",
          "09-specialized-agents.md" in spec13 and "roster" in spec13.lower()
          and "crux-design" in spec13)
    check("agents: spec 13 records what it PARKED rather than quietly dropping it",
          "PARKED" in spec13 and "separability" in spec13.lower())
    spec09 = read(os.path.join(repo, ".spec", "09-specialized-agents.md"))
    check("agents: spec 09's roster carries both of spec 13's agents",
          "crux-situate" in spec09 and "crux-design" in spec09)
    readme = read(os.path.join(repo, ".spec", "README.md"))
    check("agents: the backlog index shows 13 done",
          re.search(r"\|\s*13\s*\|[^|]*\|[^|]*\|\s*☑\s*\|", readme) is not None)


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


def run_sortlab_fixture():
    """The committed sortlab_vault, pinned so it cannot rot silently (the stale-fixture
    lesson from spec 08).

    SortLab is the worked example a newcomer reads before they touch a vault of their own:
    150 nodes, 200 tasks, 60 wiki pages, and exactly two drifted locks that are the point
    rather than a defect. Three things are asserted, and each one is a way the fixture could
    go quietly wrong:

      - the SHAPE: if a later engine change renumbers, drops or duplicates a node, a task or
        a wiki page, the counts move and this fails before anyone reads a wrong example.
      - the LINT: exactly two problems, both DRIFT, on h9 and h65, and ZERO warnings. Naming
        the two ids is what makes a third problem visible instantly; a bare "2 problems"
        would let one drift heal and another appear without a sound.
      - the IDEMPOTENCE: `refresh()` on the committed bytes must write nothing. A fixture
        that reformats itself on every command produces a dirty tree for every contributor
        and trains everyone to ignore the diff."""
    print("\n# sortlab_vault — the worked example, pinned")
    root = os.path.join(HERE, "..", "examples", "sortlab_vault")
    check("sortlab: the vault is committed", os.path.isfile(os.path.join(root, ".crux.yaml")))
    v = E.Vault(root)
    kinds = collections.Counter(n.type for n in v.nodes.values())
    check(f"sortlab: 150 nodes (got {len(v.nodes)})", len(v.nodes) == 150)
    check(f"sortlab: 1 project / 35 questions / 108 hypotheses / 6 syntheses (got "
          f"{kinds['project']}/{kinds['question']}/{kinds['idea']}/{kinds['synthesis']})",
          (kinds["project"], kinds["question"], kinds["idea"], kinds["synthesis"])
          == (1, 35, 108, 6))
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
                                 problem="only here: capacity certificate", verifiables=["x"])
    h2, _, _ = E.cmd_hypothesize(root, "another claim", parent=q1, problem="plain", verifiables=["y"])

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
    E.cmd_hypothesize(root, "h", parent=q1, problem="data pruning again", verifiables=["x"])
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
    E.cmd_hypothesize(root, "h-mixed", parent=q1, problem="a kernel trick node", verifiables=["x"])
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
    E.cmd_hypothesize(root, "h", parent=q1, problem="the kernel trick again", verifiables=["x"])
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
                      verifiables=["x"])
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
    E.cmd_hypothesize(root, "h", parent=q1, problem="the kernel trick again", verifiables=["x"])
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
                                 neutral=["the control reproduces the known value"])
    declare_null(root, h9)
    E.cmd_test(root, h9, to="running")
    edit(node_path(root, h9), "- [ ] z", "- [x] z")
    edit(node_path(root, h9), "- [ ] [outcome-neutral] the control reproduces the known value",
                              "- [x] [outcome-neutral] the control reproduces the known value")
    E.cmd_close(root, h9)
    E.cmd_review(root); E.cmd_validate(root); E.snapshot(root); E.refresh(root)
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

    Ten agent definitions ship. `run_agent_roster` checks they are well-formed and leashed;
    nothing checked that any of them DOES ITS JOB, which is spec 10's opening line — *"the
    agent roster is unfalsifiable and drifts silently."*

    Measuring one needs ground truth, and spec 10 is uncompromising about where it may come
    from: *"the planted defects must be authored independently of the agent that finds them."*
    Easy to write, easy to break by accident — a hand-authored fixture drifts the moment
    someone edits the vault and forgets the manifest, and then the eval grades against a
    ground truth that describes a vault which no longer exists.

    So the ENGINE certifies the fixture: `validation_report` on the fixture vault must emit
    exactly the planted id set. The manifest is written by a human; a program with no
    knowledge of any agent says whether it is true.

    No engine change, no version bump — a new sibling module and a tree of fixture data."""
    print("\n# agent evals — the fixture contract (spec 10, PRD 10.0)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

    names = V.fixture_names()
    check(f"evals: the audit-01 fixture exists and its vault loads (found: {names})",
          "audit-01" in names and len(E.Vault(os.path.join(V.FIXTURES, "audit-01", "vault")).nodes) > 3)

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

    # a fixture's `agent` resolves to a real definition — one of the isolated ten under
    # `agents/`, or (spec 16's persona eval) the orchestrating skill whose voice rules are
    # what it measures. Either way the score is pinned to a prompt that exists.
    ghosts = [n for n in names
              if not (os.path.isfile(os.path.join(repo, "agents",
                                                  V.load_manifest(n)["agent"], "AGENT.md"))
                      or os.path.isfile(os.path.join(repo, "skills",
                                                     V.load_manifest(n)["agent"], "SKILL.md")))]
    check(f"evals: every fixture names a real definition (ghosts: {ghosts})", not ghosts)

    # -- the checks list is the MANIFEST's, never a default. `gate` is opt-in: a certifier
    #    running the defaults decides audit-01 has no gate backlog, and then scores a CORRECT
    #    finding on q2 as an invention — precision 0.0 for the right answer.
    m = V.load_manifest("audit-01")
    check("evals: certification runs the manifest's declared checks, not the defaults",
          "gate" in m["checks"] and "gate" not in E.CHECKS and "gate" in E.OPT_CHECKS
          and "q2" in V.emitted_ids(m)
          and "q2" not in {e["id"] for t in ("problems", "warnings")
                           for e in E.validation_report(V.vault_of(m))[t]})

    r = V.certify("audit-01")
    check(f"evals: audit-01 certifies — the engine finds exactly what was planted "
          f"(missing {r['missing']}, extra {r['extra']})", r["ok"])

    # -- the two ways a fixture rots, each proven on a COPY (the shipped tree is never touched)
    tmp = tempfile.mkdtemp(prefix="crux_evalfix_")
    try:
        shutil.copytree(os.path.join(V.FIXTURES, "audit-01"), os.path.join(tmp, "audit-01"))
        vault = os.path.join(tmp, "audit-01", "vault")
        h2 = [p for p in os.listdir(vault) if p.startswith("h2_")][0]
        edit(os.path.join(vault, h2), "- [Report](results/h2/report.md)", "")
        c = V.certify("audit-01", root=tmp)
        check(f"evals: a fixture that drifts from its manifest fails certification "
              f"(missing {c['missing']})", not c["ok"] and c["missing"] == ["h2"])

        shutil.rmtree(os.path.join(tmp, "audit-01"))
        shutil.copytree(os.path.join(V.FIXTURES, "audit-01"), os.path.join(tmp, "audit-01"))
        vault = os.path.join(tmp, "audit-01", "vault")
        h1 = [p for p in os.listdir(vault) if p.startswith("h1_")][0]
        edit(os.path.join(vault, h1), "## Idea / Hypothesis",
             "## Idea / Hypothesis\n\n" + ("an unplanted flood of prose. " * 220))
        c = V.certify("audit-01", root=tmp)
        check(f"evals: an unplanted defect fails certification as extra (extra {c['extra']})",
              not c["ok"] and c["extra"] == ["h1"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # -- one defect per id is what buys exact scoring with no engine change; load_manifest
    #    refuses a duplicate, so this is a property of every fixture that parses at all
    dupes = []
    for n in names:
        ids = [p["id"] for p in V.load_manifest(n)["planted"]]
        dupes += [f"{n}:{i}" for i in set(ids) if ids.count(i) > 1]
    check(f"evals: at most one planted defect per emitted id (dupes: {dupes})", not dupes)

    before = _tree_hashes(V.FIXTURES)
    V.certify_all()
    check("evals: certification is read-only", _tree_hashes(V.FIXTURES) == before)

    # -- spec 10 names five defect families for crux-audit; all five are here, and the
    #    ambiguous one is resolved in the fixture rather than in the reader's head (M4)
    classes = " ".join(p["class"] for p in m["planted"])
    check(f"evals: audit-01 plants every defect family the spec names ({classes})",
          all(c in classes for c in ("economy:over-cap", "task:dangling-ref",
                                     "artifact:missing", "gate:backlog", "tree:parent-cycle"))
          and "parent cycle" in V.load_manifest("audit-01")["body"].lower())

    # -- THE GATE-4 ARGUMENT, asserted rather than asserted-in-prose. Spec 10 alters no vault
    #    format, no verdict/roll-up logic and no view, so the stamp does not move. Precedents:
    #    09.4 and 13.3, both doc-only, both explicitly no-bump.
    #
    #    Written as `>= 3.1` rather than `== 3.1`: the claim is "spec 10 did not move the
    #    stamp", and a literal equality restates it as "the stamp has never moved since",
    #    which is a different claim that a LATER spec falsifies. Spec 16 falsified it — see
    #    `at_least_version`'s own docstring, which predicted this exact failure.
    check(f"evals: the fixture contract did not bump the engine (spec 10 landed at 3.1; "
          f"now {E.ENGINE_VERSION})", at_least_version("3.1"))

    # -- gate 3 of the evolve-crux gate walks examples/ and asks "did anything break". These
    #    vaults are validate-RED BY CONSTRUCTION, so putting them there would make the one
    #    gate whose job is 'nothing broke' unreadable.
    ex = os.path.join(HERE, "..", "examples")
    check("evals: the fixture tree is outside the example-vault gate",
          not os.path.isdir(os.path.join(ex, "audit-01"))
          and os.path.abspath(V.FIXTURES) != os.path.abspath(ex)
          and "evals/fixtures" in read(os.path.join(ex, "README.md")))


def run_eval_scorer():
    """Spec 10 PRD 10.1 — precision and recall, banded over K runs, with no model call.

    Spec 10 is blunt about the pair: *"'Did it find things' is not a result"*, and in its
    rejected alternatives, *"Recall-only scoring. An agent optimizing recall alone learns to
    report everything."* So both are computed or neither is.

    THE STRUCTURAL DECISION: the scorer reads a SUBMITTED findings file and never invokes an
    agent. A program that launches an agent K times, decides when to stop and caps what it
    spends is spec 05's three unbuilt work items pointed at a fixture — and `.spec/README.md`
    says do not implement 05. The loop is the risk, not the target. That is not a promise
    here; it is the assert below that reads evals.py's own source."""
    print("\n# agent evals — the scorer (spec 10, PRD 10.1)")
    import evals as V
    SUB = os.path.join(V.FIXTURES, "audit-01", "submissions")
    m = V.load_manifest("audit-01")

    def sc(name, mf=m):
        return V.score(mf, V.load_submission(os.path.join(SUB, name)))

    s = sc("perfect.json")
    check("evals: a perfect submission scores 1.0 / 1.0",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] == 1.0)

    s = sc("noisy.json")
    check(f"evals: invented findings cost precision, not recall "
          f"(r={s['recall']['min']:.2f} p={s['precision']['min']:.2f})",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] < 1.0
          and s["runs"][0]["fp"] == ["h1", "q1", "wiki:linear-probes"])

    s = sc("partial.json")
    check(f"evals: missed defects cost recall, not precision "
          f"(r={s['recall']['min']:.2f} p={s['precision']['min']:.2f})",
          s["recall"]["min"] < 1.0 and s["precision"]["min"] == 1.0
          and s["runs"][0]["fn"] == ["q4", "wiki:detection-floor"])

    # the vacuous-truth trap: |tp|/|reported| is 0/0 for an empty report. Reading that as 1.0
    # hands a perfect precision to an agent that did nothing.
    s = sc("silent.json")
    check("evals: reporting nothing scores zero precision",
          s["precision"]["min"] == 0.0 and s["recall"]["min"] == 0.0)

    # -- the band is the WORST run. Proven on a COPY with a band written in, because every
    #    shipped fixture ships `band: unset` and the numbers are the PI's.
    tmp = tempfile.mkdtemp(prefix="crux_evalband_")
    try:
        shutil.copytree(os.path.join(V.FIXTURES, "audit-01"), os.path.join(tmp, "audit-01"))
        edit(os.path.join(tmp, "audit-01", "PLANTED.md"),
             "band: unset", "band: recall>=0.9, precision>=0.9")
        banded = V.load_manifest("audit-01", root=tmp)
        ids = sorted(banded["planted_ids"])
        sha = V.agent_sha("crux-audit")
        # four perfect runs and one that misses two. The MEAN clears 0.9; the WORST does not.
        four_good_one_bad = {"fixture": "audit-01", "agent": "crux-audit", "agent_sha": sha,
                             "runs": [{"findings": ids}] * 4 + [{"findings": ids[:5]}]}
        s = V.score(banded, four_good_one_bad)
        mean_r = sum(r["recall"] for r in s["runs"]) / 5
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

    # -- THE LEASH, read off this module's own source rather than believed. P1 (the
    #    model-invoking runner) and P3 (an agent write path) are parked, and a parked item
    #    that is only parked in prose is a preference.
    #    Read as an AST, not as text: the module's own prose SAYS "there is no --spawn", and a
    #    grep over prose would flag the sentence that promises the property it is checking.
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

    # -- spec 10: "Label the proxies as proxies… an eval that overstates its own rigour is the
    #    same failure mode this whole backlog exists to fix." A label with a code path that
    #    drops it is not a label.
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
                               "--fixture", "audit-01", "--submission", os.path.join(SUB, sub)],
                              capture_output=True, text=True, encoding="utf-8").returncode
    check("evals: the runner is exit-coded",
          rc("perfect.json") == 0 and rc("short.json") == 1 and rc("stale-sha.json") == 1)

    check(f"evals: the scorer did not bump the engine (spec 10 landed at 3.1; now "
          f"{E.ENGINE_VERSION})", at_least_version("3.1"))


def run_mutation_harness():
    """Spec 10 PRD 10.2 — prove the suite can actually detect a regression.

    Spec 10's fourth acceptance criterion is the only one a passing suite cannot fake:
    *"A deliberately degraded agent prompt fails its eval — i.e. the suite can actually detect
    regression."* Every other criterion is satisfiable by a suite that returns green on
    anything. It is also the cheapest, because a degraded DEFINITION can be degraded in code:
    zero model calls.

    The need is concrete. `crux-design`'s handoff rule is guarded by
    `"never invoke" in body.lower()`. Reword that sentence — *"you do not call `crux-critic`
    yourself"* — and the property stops being checked while the suite stays green. A prose
    assert with no demonstrated failure mode is a comment with a `check()` around it.

    Not circular, for the same reason spec 10's own fixtures are not: the mutations are
    hand-written, independent of the definitions, and each NAMES the property it must break
    before it is run."""
    print("\n# agent evals — the mutation harness (spec 10, PRD 10.2)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    expected = ["crux-null", "crux-verifiables", "crux-critic", "crux-migrate", "crux-close",
                "crux-audit", "crux-tests", "crux-glossary", "crux-situate", "crux-design"]
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

    check("evals: a toolbelt gaining a verdict verb breaks the leash check",
          by["belt-adds-close"]["broke"] == ["leash"])
    check("evals: giving the critic a toolbelt breaks its isolation check",
          "critic-isolated" in by["critic-gains-belt"]["broke"])

    # the two PROSE asserts, each now carrying a demonstrated failure mode (D9). A structural
    # equivalent is preferred where one exists — the leash reads the toolbelt, not the prose —
    # but "hand off by naming, never by invoking" has no frontmatter field, and inventing one
    # to make it structural would be schema design driven by test convenience.
    check("evals: the crux-close prose assert has a demonstrated failure mode",
          by["close-drops-never-run"]["broke"] == ["close-says-so"])
    check("evals: the crux-design handoff assert has a demonstrated failure mode",
          by["design-drops-never-invoke"]["broke"] == ["design-handoff"])
    check("evals: pinning an engine version in a definition is still caught",
          by["pin-engine-version"]["broke"] == ["no-version-pin"])

    # the shipped roster is clean, and the extraction that made this harness possible changed
    # no assert: every name `roster_properties` returns is one the roster suites print.
    P = V.roster_properties(defs, verbs)
    red = sorted(k for k, (_n, ok) in P.items() if not ok)
    printed = set(_PASS) | set(_FAIL)
    unprinted = sorted(n for _s, (n, _ok) in P.items() if n not in printed)
    check(f"evals: the shipped roster is clean and the extraction preserved every assert "
          f"(red: {red}, unprinted: {unprinted})", not red and not unprinted)

    before = _tree_hashes(os.path.join(repo, "agents"))
    V.mutation_results(defs, verbs)
    check("evals: mutation is in-memory only", _tree_hashes(os.path.join(repo, "agents")) == before)

    covered = {m["agent"] for m in res}
    check(f"evals: every agent has at least one mutation covering it "
          f"(uncovered: {sorted(set(expected) - covered)})", covered == set(expected))

    check(f"evals: the mutation harness did not bump the engine (spec 10 landed at 3.1; "
          f"now {E.ENGINE_VERSION})", at_least_version("3.1"))


def run_ground_truth_fixtures():
    """Spec 10 PRD 10.3 — the three fixtures whose answer the engine already holds.

    Spec 10 divides its fixtures into genuine ground truth and proxies, and is blunt about why:
    *"an eval that overstates its own rigour is the same failure mode this whole backlog exists
    to fix."* Two things moved since it was written. `crux-tests` LOSES its ground truth — its
    oracle needs executing model-written code, which is parked — and `crux-situate` GAINS one,
    because PRD 13.1 shipped `situate_lint` saying in as many words that *"spec 10 inherits an
    oracle instead of inventing one."*

    So: close-01 against `derive_verdict_15`, null-01 against the closed confound vocabulary,
    situate-01 against the situate payload and its lint. No new oracle is written; three are
    inherited."""
    print("\n# agent evals — the ground-truth fixtures (spec 10, PRD 10.3)")
    import evals as V

    def sub(fix, name):
        return V.load_submission(os.path.join(V.FIXTURES, fix, "submissions", name))

    def sc(fix, name):
        return V.score(V.load_manifest(fix), sub(fix, name))

    certs = {c["fixture"]: c for c in V.certify_all()}
    three = ("close-01", "null-01", "situate-01")
    check(f"evals: the three ground-truth fixtures certify "
          f"({[(n, certs[n]['ok']) for n in three if n in certs]})",
          all(n in certs and certs[n]["ok"] for n in three))

    # ---- close-01: the verdict is the ENGINE's, so the fixture cannot disagree with it.
    #      `certify` derives it from the manifest's own tick vector and compares.
    m = V.load_manifest("close-01")
    hid = str(m["fm"]["node"])
    node = E.Vault(V.vault_of(m)).get(hid)
    lines = E._verifiable_lines(node["body"])
    ticks = {p.partition("=")[0]: p.partition("=")[2] for p in m["planted_ids"]}
    by = {k: [] for k in E.VERIFIABLE_KINDS}
    for i, (_t, text) in enumerate(lines, 1):
        by[E.verifiable_kind(text)[0]].append(V.TICKS[ticks[f"{hid}:v{i}"]])
    tal = {k: E._tally(v) for k, v in by.items()}
    derived = E.derive_verdict_15(tal[E.DEFAULT_KIND], tal[E.NEUTRAL_KIND],
                                  str(node["fm"].get(E.RULE_FIELD)))
    check(f"evals: close-01's known verdict is the engine's own ({derived})",
          derived == str(m["fm"]["verdict_read"]) == "invalid-run")
    check("evals: close-01 discriminates invalid-run from refuted",
          tal[E.NEUTRAL_KIND][1] == 1 and tal[E.DEFAULT_KIND][:2] == (2, 0))

    s = sc("close-01", "refuted-misread.json")
    check("evals: reading an invalid run as refuted fails close-01",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] == 1.0
          and s["verdict"] == V.FAIL
          and any(not ok for _n, ok, _w in s["hard"]))

    # ---- null-01
    m = V.load_manifest("null-01")
    check(f"evals: null-01 plants a family from the closed vocabulary ({m['planted_ids']})",
          m["planted_ids"] <= set(E.CONFOUND_FAMILIES) and len(m["planted_ids"]) == 1)
    n = E.Vault(V.vault_of(m)).get(str(m["fm"]["node"]))
    check("evals: null-01's reference null passes the engine's own null check",
          E.null_problem(str(m["fm"]["reference_null"]), E.node_schema(n)) is None
          and not (E._null_text(n) or "").strip())

    s = sc("null-01", "decoy.json")
    check(f"evals: null-01's decoy family scores zero recall (r={s['recall']['min']})",
          str(m["fm"]["decoy"]) in E.CONFOUND_FAMILIES and s["recall"]["min"] == 0.0)
    # and the shape spec 10 rejects by name: recall-only scoring would call this perfect
    s = sc("null-01", "everything.json")
    check(f"evals: naming every family is recall 1.0 and precision {s['precision']['min']:.2f}",
          s["recall"]["min"] == 1.0 and s["precision"]["min"] < 0.2)

    # ---- situate-01
    m = V.load_manifest("situate-01")
    anchor = str(m["fm"]["node"])
    ref = V._section(m["body"], "Reference answer")
    check("evals: situate-01's reference answer lints clean",
          ref.strip() and E.situate_lint(ref, [V.situate_anchor(m)]) == [])
    # spec 16: the gold answer is the thing that trains hardest, so it is scanned as speech
    # too. It must anchor by TITLE and carry no crux vocabulary — an id-led reference would
    # keep teaching the voice the anchor rule no longer forces.
    check("evals: situate-01's reference answer carries no node id and no crux vocabulary",
          E.voice_lint([("agent", ref)]) == [])
    check("evals: ... and it is the TITLE doing the anchoring, not an id left in the prose",
          [i for i, _m in E.situate_lint(ref, [anchor])] == ["situate:unanchored"])

    payload = E.brief(V.vault_of(m), anchor, mode="situate")
    check(f"evals: situate-01 plants both a gap and an invention trap ({sorted(m['planted_ids'])})",
          any(i.startswith("untested:") for i in m["planted_ids"])
          and any(i.startswith("inflight:") for i in m["planted_ids"])
          and any(i.startswith("gap:") for i in m["planted_ids"])
          and payload["untested"]["unrun_ideas"])

    s = sc("situate-01", "invented.json")
    check(f"evals: inventing a finding costs situate-01 precision (p={s['precision']['min']:.2f})",
          s["precision"]["min"] < 1.0 and s["recall"]["min"] < 1.0)
    # brevity is situate's stated acceptance criterion, so it is one bit beside the band
    s = sc("situate-01", "verbose.json")
    check("evals: a verbose situate answer fails on the lint, whatever its recall",
          s["recall"]["min"] == 1.0 and s["verdict"] == V.FAIL
          and any(not ok for _n, ok, _w in s["hard"]))

    # ---- the two properties that hold across every fixture in the epic
    ms = [V.load_manifest(n) for n in V.fixture_names()]
    check("evals: the ground-truth fixtures declare their status and leave the band to the PI",
          all(V.load_manifest(n)["ground_truth"] == "yes"
              and V.load_manifest(n)["band"] == V.BAND_UNSET for n in three))
    # P7: no fixture may make a scientific judgment a deterministic predicate by fiat. Spec 09's
    # staleness warning is a PI ruling — a claim that recorded answers no longer reflect what we
    # know is on the footing of `answer` and `pursue`, gated one node at a time.
    banned = ("stale", "outdated", "no longer reflect", "wrong answer", "should be reopened")
    smell = [f"{m['name']}:{p['id']}" for m in ms for p in m["planted"]
             if any(b in (p["class"] + " " + p["note"]).lower() for b in banned)]
    check(f"evals: every planted defect is structural, never a research judgment ({smell})",
          not smell)

    check(f"evals: the ground-truth fixtures did not bump the engine (spec 10 landed at "
          f"3.1; now {E.ENGINE_VERSION})", at_least_version("3.1"))


def run_proxy_register():
    """Spec 10 PRD 10.4 — the six proxies, the register, and the gate ruling.

    Spec 10 is firm about what a proxy obliges: *"Label the proxies as proxies… an eval that
    overstates its own rigour is the same failure mode this whole backlog exists to fix."* A
    label in prose decays, so here it is a field, a register, and an assert.

    The register's last column is the one that earns its place. `[proxy]` alone tells a reader
    the eval is weaker; it does not tell them IN WHICH DIRECTION, which is what they need in
    order to distrust the right number."""
    print("\n# agent evals — the proxies, the register, and the gate (spec 10, PRD 10.4)")
    import evals as V
    repo = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    spec = read(os.path.join(repo, ".spec", "10-agent-evals.md"))

    # GROWN by spec 05 (PRD 05.3): the tuple is eight, and the check NAME says eight. A name
    # that still said "six" while the tuple held eight would be a false statement printed by a
    # passing check — the one kind of green line nobody re-reads.
    proxies = ("verifiables-01", "critic-01", "migrate-01", "tests-01", "glossary-01",
               "design-01", "worker-01", "steward-01")
    certs = {c["fixture"]: c for c in V.certify_all()}
    bad = [n for n in proxies if not certs.get(n, {}).get("ok")]
    check(f"evals: the eight proxy fixtures certify (failed: {bad})", not bad)

    roster = sorted(os.listdir(os.path.join(repo, "agents")))
    covered = {V.load_manifest(n)["agent"] for n in V.fixture_names()}
    # every roster agent is covered, and the set may be a SUPERSET: spec 16's persona-01
    # grades the orchestrating skill, which is not a roster agent and never will be.
    check(f"evals: every agent in the roster has a fixture "
          f"(uncovered: {sorted(set(roster) - covered)})",
          set(roster) <= covered and len(roster) == 12)
    check(f"evals: and a fixture outside the roster grades a definition that exists "
          f"({sorted(covered - set(roster))})",
          all(os.path.isfile(os.path.join(repo, "skills", a, "SKILL.md"))
              for a in covered - set(roster)))

    # -- the register, parsed out of the spec and diffed against the manifests both ways
    rows = {r[0].strip("`"): r for r in V._table(spec, "The proxy register")}
    check(f"evals: the proxy register and the fixture tree agree "
          f"({sorted(set(rows) ^ set(V.fixture_names()))})",
          set(rows) == set(V.fixture_names()))

    REG_TRUTH = {"**yes**": "yes", "proxy": "proxy"}
    mismatch = [n for n, r in rows.items()
                if REG_TRUTH.get(r[2]) != V.load_manifest(n)["ground_truth"]]
    check(f"evals: no fixture can be promoted by editing one side ({mismatch})", not mismatch)

    check("evals: crux-tests is a proxy until code execution is unparked",
          V.load_manifest("tests-01")["ground_truth"] == "proxy"
          and "P2" in spec and "demoted" in spec.lower())

    silent = [n for n, r in rows.items()
              if V.load_manifest(n)["ground_truth"] == "proxy" and not r[4].strip(" —")]
    check(f"evals: every proxy says what it fails to measure ({silent})", not silent)

    # -- M3: the h59 this spec named lives in the PI's own vault. No real research data enters
    #    this repo, so the fixture is WRITTEN and bands against its own declared N.
    m = V.load_manifest("verifiables-01")
    leaked = sorted(f"{n}:{p['id']}" for n in V.fixture_names()
                    for p in V.load_manifest(n)["planted"]
                    if "h59" in p["id"] or "h59" in p["note"])
    leaked += sorted(os.path.join(dp, f) for n in V.fixture_names()
                     for dp, _d, fs in os.walk(os.path.join(V.FIXTURES, n, "vault"))
                     for f in fs if "h59" in read(os.path.join(dp, f)))
    check(f"evals: verifiables-01 is self-contained, not lifted from an absent vault "
          f"(leaked: {leaked})",
          str(m["fm"].get("reference_n") or "").strip() != "" and not leaked)

    m = V.load_manifest("design-01")
    pairs = [p["id"].split(":") for p in m["planted"]]
    check(f"evals: design-01 plants one disease per node ({[':'.join(x) for x in pairs]})",
          len({d for d, _n in pairs}) == len(pairs) == len({n for _d, n in pairs}) == 3)

    m = V.load_manifest("tests-01")
    wrong = [w for w in V._csv(m["fm"]["wrong_values"]) if w]
    clash = sorted(w for p in m["planted"] for w in wrong if w in p["note"])
    check(f"evals: tests-01's key cannot be satisfied by describing the broken code ({clash})",
          wrong and not clash)

    # -- the gate ruling (D6), where it binds and where it is written down
    src = read(os.path.join(HERE, "selftest.py"))
    check("evals: the deterministic eval suite runs in the gate",
          all(f"    {fn}()" in src for fn in ("run_agent_evals", "run_eval_scorer",
                                              "run_mutation_harness",
                                              "run_ground_truth_fixtures", "run_proxy_register")))
    skill = read(os.path.join(repo, "skills", "evolve-crux", "SKILL.md"))
    check("evals: the gate contract is written down where contributors read it",
          "agent evals" in skill and "never gates" in skill and "no API key" in skill)

    # -- D7. The mechanism ships; the numbers are the PI's, and the gap is on the record.
    unset = all(V.load_manifest(n)["band"] == V.BAND_UNSET for n in V.fixture_names())
    check("evals: no band was invented, and the gap is recorded",
          unset and "Pass bands" in spec and "still open" in spec
          and "☐ **a stated pass band**" in spec)

    check("evals: spec 10 is flipped, amended, and indexed",
          "**Status:** ☑" in spec and spec.count("- ☑ ") >= 7
          and all(a in spec for a in ("crux-glossary", "crux-situate", "crux-design"))
          and re.search(r"\|\s*10\s*\|[^|]*\|[^|]*\|\s*☑\s*\|",
                        read(os.path.join(repo, ".spec", "README.md"))) is not None)

    check("evals: spec 10 records what it parked rather than dropping it",
          "PARKED" in spec and "P1" in spec and "do not implement 05" in spec.lower()
          and "--spawn" in spec)

    check(f"evals: spec 10 was a zero-bump epic — it landed at 3.1 and the stamp only moved "
          f"later, for spec 16's changed lint (now {E.ENGINE_VERSION})",
          at_least_version("3.1"))


def _voice_vault():
    """A tiny tree with two branches, for the relevance gate: q1 -> (q2 -> h1,h2 ; q3 -> h3).

    Two branches is the minimum that can tell `sibling` from `unrelated`, which is the only
    distinction the gate actually turns on."""
    root = tempfile.mkdtemp(prefix="crux_voice_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Voice", root)
    q1, _ = E.cmd_ask(root, "how do we cut the label budget", None)
    q2, _ = E.cmd_ask(root, "does pretraining help at low label count", q1)
    q3, _ = E.cmd_ask(root, "which augmentation family matters", q1)
    hy = lambda t, p: E.cmd_hypothesize(root, t, parent=p, verifiables=["accuracy >= +2.0"],
                                        neutral=["the baseline reproduces its published number"])[0]
    h1 = hy("pretraining beats scratch", q2)
    h2 = hy("pretraining still helps at 20 labels", q2)
    h3 = hy("colour jitter is the family that matters", q3)
    return root, {"q1": q1, "q2": q2, "q3": q3, "h1": h1, "h2": h2, "h3": h3}


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
               "situate", "null", "ledger", "glossary", "RD", "seed file", "META.md")))
    check("voice: plain science words are free — a grad student owes no gloss for 'hypothesis'",
          not any(E.is_crux_term(t) for t in
                  ("question", "hypothesis", "evidence", "finding", "experiment", "check",
                   "result", "supported", "refuted", "inconclusive", "baseline")))
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
    check("voice: SKILL.md carries a top-level voice section naming all six rules",
          re.search(r"^## .*[Vv]oice", skill, re.M)
          and all(k in skill for k in ("mirror rule", "Silent bookkeeping", "Signature",
                                       "relevance", "title", "Notebook mode")))

    # ---- glossary graduation. Without the waiver a crux process term can never be
    #      proposed: it appears nowhere in the corpus the centrality filter counts, so the
    #      path spec 16 relies on would be dead on arrival.
    root, ids = _voice_vault()
    try:
        got = [c["term"] for c in E.glossary_candidates(root, ["review gate", "flumox"])]
        check(f"voice: a crux process term the vault never mentions is still proposable ({got})",
              got == ["review gate"])
        check("voice: and the waiver is narrow — a non-lexicon term still has to be central",
              E.glossary_candidates(root, ["flumox"]) == [])

        # ---- the relevance gate, engine-computed (09's rule 1, and spec 16's own default)
        rel = lambda near, other: E.gate_relation(E.Vault(root), near, other)
        check("voice: lineage and immediate siblings are in scope, an unrelated branch is not",
              [rel(ids["q2"], x) for x in (ids["q2"], ids["q1"], ids["h1"], ids["q3"], ids["h3"])]
              == ["self", "ancestor", "descendant", "sibling", "unrelated"])
        check("voice: sibling means IMMEDIATE sibling — a cousin is unrelated",
              rel(ids["h1"], ids["h3"]) == "unrelated" and rel(ids["h1"], ids["h2"]) == "sibling")
        check("voice: every relation the engine can emit is in the declared vocabulary",
              all(rel(ids["q2"], o) in E.GATE_RELATIONS for o in ids.values()))

        # trip a real gate, then read it back through the CLI the agent actually uses
        for hid in (ids["h3"],):
            declare_null(root, hid)
            E.cmd_test(root, hid, "staged"); E.cmd_test(root, hid, "running", run="job 1")
            n = E.Vault(root).get(hid)
            E.write_if_changed(n["path"], E.render_doc(n["fm"], n["body"].replace("- [ ]", "- [x]")))
            E.cmd_close(root, hid, metric="+2.1", findings="it held")
        pend = E.cmd_review(root)
        check(f"voice: the fixture actually trips a gate to annotate ({[p[0] for p in pend]})",
              [p[0] for p in pend] == [ids["q3"]])

        out = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "review",
                              "--json", "--near", ids["q2"]],
                             capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        rows = json.loads(out.stdout)
        check("voice: `crux review --json --near` annotates every pending gate with its "
              "relation and whether it is in scope",
              out.returncode == 0 and rows
              and all({"relation", "in_scope"} <= set(r) for r in rows)
              and rows[0]["relation"] == "sibling" and rows[0]["in_scope"] is True)
        far = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "review",
                              "--json", "--near", ids["h1"]],
                             capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        check("voice: a gate outside the lineage reads out-of-scope — the agent never raises "
              "it on its own initiative",
              json.loads(far.stdout)[0]["in_scope"] is False)
        plain = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "review", "--json"],
                               capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        check("voice: without --near nothing is annotated — a PI asking what is pending gets "
              "everything, and the restriction binds agent initiative only",
              "relation" not in json.loads(plain.stdout)[0])
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
            """Everything this engine DERIVES from a vault — verdicts, roll-ups, the gate,
            and the structural checks. If a stamp could change any of it, the stamp would be
            a compatibility era rather than a counter, and this suite would be lying."""
            v = E.Vault(root)
            return {"verdicts": {i: n["fm"].get("verdict") for i, n in sorted(v.nodes.items())},
                    "status": {i: n.status for i, n in sorted(v.nodes.items())},
                    "ledger": {i: E.ledger_counts(v, i) for i, n in sorted(v.nodes.items())
                               if n.type == "question"},
                    "gate": E.cmd_review(root),
                    "checks": E.validation_report(root, checks=("tree", "economy", "fanout",
                                                                "rd", "tasks"))}
        before = _tree_hashes(was)
        a, b = readout(was), readout(now)
        check("voice: a 3.1-stamped vault reads IDENTICALLY under 3.2 — same verdicts, same "
              "roll-up, same gate, same structural checks",
              json.dumps(a, sort_keys=True, default=str)
              == json.dumps(b, sort_keys=True, default=str)
              and a["verdicts"]["h2"] == "partial" and a["checks"]["ok"])
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
        for argv in (["review"], ["task", "review"], ["status"], ["validate"]):
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
    check("voice: ... and the ○ legend denies the second reading it used to invite",
          re.search(r"`○`\s*=\s*act without asking", skill)
          and re.search(r"not.{0,40}announc", skill, re.I))
    # Order is load-bearing: the rule has to be read before the table that contradicted it.
    check("voice: the Voice section is read before the first ○ in the file",
          skill.index("## Voice — the invisible notebook") < skill.index("○"))

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
                                     "--parent", qid, "-v", "imp-Spearman >= +0.01"],
                                    cwd=vault).stdout
        hid = re.search(r"✓ (h\d+)", minted["hypothesize"]).group(1)
        minted["task add"] = run(["task", "add", "fetch the antibody lot",
                                  "--category", "data-acquisition", "--blocked-by", "None"],
                                 cwd=vault).stdout
        minted["synthesize"] = run(["synthesize", "what the data question settled",
                                    "--for", qid], cwd=vault).stdout
        minted["rd"] = run(["rd", hid, "the sweep design"], cwd=vault).stdout
        titles = {"ask": "does more data beat a better model",
                  "hypothesize": "doubling the data wins on held-out",
                  "task add": "fetch the antibody lot",
                  "synthesize": "what the data question settled",
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
    check("persona: the state table asserts every step of the silent bookkeeping",
          {k.split(":")[0] for k, _p, _n in V.state_rows(m)}
          == {"verdict", "answered", "synthesis", "approved", "pending"})
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
              and got["nodes"]["q1"]["synthesis"] == "s1"
              and got["nodes"]["s1"]["approved"] is True
              and got["nodes"]["q3"]["answered"] is False)
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


# ======================================================================= autopilot 05.0
# Spec 05 / PRD docs/prd/05.0-flight-plan-and-brief.md — the pure side of autopilot: the
# flight plan document at auto/<qid>/plan.md, the `builds_on:` lineage field, flat PUCT
# selection ported from ERA's futs.py, and the engine-assembled worker brief. Nothing here
# starts a process, and the engine never writes results/<hid>/metrics.json — the TEST does,
# because scoring is the harness' job in every one of these fixtures.
#
# These sections were written against the PRD's 22 acceptance criteria and the interface
# contract ALONE, before the implementation existed. That is the point: a test written from
# the code passes for the code that exists rather than for the thing that was asked for.


def _auto_val(fn, default=None):
    """fn()'s value, or `default` when it raises anything at all.

    Written-first tests call names the engine may not carry yet. Without this, the first
    absent name costs the whole section (one FAIL line saying nothing); with it, an absent
    name costs exactly the checks that depend on it, and the rest of the section still
    reports."""
    try:
        return fn()
    except Exception:
        return default


def _auto_msg(fn):
    """The CruxError text fn raises, "" when it raises nothing, and a marker otherwise.

    `_err_text` with the wave-1 AttributeError/TypeError caught, so a missing interface reads
    as a failed message assert rather than as a crash."""
    try:
        fn()
        return ""
    except E.CruxError as e:
        return str(e)
    except Exception as e:
        return f"<not implemented: {e!r}>"


def _plan_path(root, qid):
    """`auto/<qid>/plan.md` — from the engine when it has `flight_plan_path`, from the
    contract's literal (§1) when it does not, so the FIXTURE exists either way. That the two
    agree is itself a check, made once in run_flight_plan rather than assumed here."""
    return _auto_val(lambda: E.flight_plan_path(root, qid),
                     os.path.join(root, "auto", qid, "plan.md"))


# The plan's two checks, in the node's own format (§2: no new parser). The claim-directed one
# names the objective address `eval.loss` as a token, which is what check 14 looks for.
AUTO_PLAN_VERIFIABLES = (
    "- [ ] eval.loss <= 0.85 on the held-out split\n"
    "      fails-if:: the median of three seeds stays above 0.85\n"
    "      discriminates:: true\n"
    "- [ ] [outcome-neutral] baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01\n"
    "      fails-if:: the baseline re-run lands outside 0.01\n")
AUTO_PLAN_GUIDANCE = ("_(the PI's standing instructions to workers — appended with "
                      "`crux auto guide`, never edited)_\n")
AUTO_PLAN_NULL = "capacity — the extra parameters alone explain the gain"
AUTO_PLAN_GOAL = "the held-out loss can be driven below 0.85 without touching the frozen scorer"


def _plan_fm(anchor, baseline, islands):
    """§2's frontmatter, in the template's order. Flat `key: value`, multi-valued fields as
    one comma-separated scalar — exactly `task_categories` in .crux.yaml."""
    return [("type", "flight-plan"), ("anchor", anchor), ("mode", "climb"),
            ("baseline", baseline), ("islands", islands), ("island_cap", "3"),
            ("budget_attempts", "40"), ("budget_hours", "8"), ("budget_model_calls", "400"),
            ("parallel_total", "1"), ("parallel_island", "1"), ("retries", "2"),
            ("retention", "failed"), ("scorer", "python score.py"), ("run", "python train.py"),
            ("frozen", "score.py, data/"), ("writable", "work/, results/"),
            ("agent", 'claude -p "{brief}"'), ("agent_failover", ""), ("steward", "false"),
            ("steward_every", "10"), ("stall_attempts", "8"), ("abort_invalid_runs", "3"),
            ("replicates", "3 seeds"), ("rule", "all"), ("rule_m", ""),
            ("created", "2026-09-16T00:00:00"), ("updated", "2026-09-16T00:00:00")]


def _plan_text(anchor, baseline, islands="", drop=(), drop_sections=(), goal=None,
               objective=None, address="eval.loss", direction="min", bar="0.85", null=None,
               verifiables=None, guidance=None, extra=(), **fm):
    """§2's template with ids filled. One defect per call: `drop` removes frontmatter lines,
    `**fm` overrides their values, `drop_sections` removes whole sections, and any section
    passed as "" is present but empty. A plan built with no argument but the ids is CLEAN —
    which is what makes each refusal test a test of one thing.

    `extra` appends (key, value) rows after `updated`. `**fm` can only override a row the
    template already carries, so a field 05.0 never had — `repo:`, `scorer_timeout:` — has to
    come in this way."""
    rows = [(k, fm.get(k, v)) for k, v in _plan_fm(anchor, baseline, islands) if k not in drop]
    rows += [(k, v) for k, v in extra]
    head = "---\n"
    for k, v in rows:
        s = "" if v is None else str(v)
        head += f"{k}: {s}\n" if s != "" else f"{k}:\n"
    head += "---\n"
    goal = AUTO_PLAN_GOAL if goal is None else goal
    objective = (f"address:: {address}\ndirection:: {direction}\nbar:: {bar}\n"
                 if objective is None else objective)
    null = AUTO_PLAN_NULL if null is None else null
    verifiables = AUTO_PLAN_VERIFIABLES if verifiables is None else verifiables
    guidance = AUTO_PLAN_GUIDANCE if guidance is None else guidance
    body = f"\n# Flight plan — {anchor}\n"
    for name, text in (("Goal", goal + "\n"), ("Objective", objective), ("Null", null + "\n"),
                       ("Verifiables", verifiables), ("Guidance", guidance)):
        if name in drop_sections:
            continue
        body += f"\n## {name}\n\n{text}"
    return head + body


def _plan_msgs(root, text, path=None):
    """Every message §3 reports for this plan text — [] when it is clean, and a one-element
    marker when the engine has no `flight_plan_problems` yet."""
    try:
        return [p["message"] for p in
                E.flight_plan_problems(root, E.parse_flight_plan(text), path)]
    except Exception as e:
        return [f"<not implemented: {e!r}>"]


def _set_builds_on(root, hid, target):
    """Write (or, with target None, remove) `builds_on:` in a node's frontmatter by hand.

    Deliberately not through `cmd_hypothesize(..., builds_on=)`: that writer is itself under
    test, and a fixture built with the thing it is testing proves nothing."""
    p = node_path(root, hid)
    t = re.sub(r"^builds_on:.*\n", "", read(p), flags=re.M)
    if target:
        t = t.replace("\ntype: idea\n", f"\ntype: idea\nbuilds_on: {target}\n", 1)
    write(p, t)


def _auto_attempt(root, parent, title, score=None, verdict="supported", findings="the run finished",
                  builds_on=None, close=True):
    """One attempt, the way autopilot will leave them: a hypothesis with the plan's two
    checks, ticked to the wanted verdict, closed with findings, and scored by the HARNESS
    writing results/<hid>/metrics.json. The engine never writes that file (§0), so a fixture
    that waited for it would wait forever."""
    hid, _, _ = E.cmd_hypothesize(
        root, title, parent=parent, rule="all",
        verifiables=["eval.loss <= 0.85 on the held-out split"],
        neutral=["baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01"],
        fails_if=["the median of three seeds stays above 0.85",
                  "the baseline re-run lands outside 0.01"],
        discriminates=[True, False])
    if close:
        p = node_path(root, hid)
        if verdict != "invalid-run":                       # a failed control is an invalid run
            edit(p, "- [ ] [outcome-neutral]", "- [x] [outcome-neutral]")
        if verdict == "supported":                         # an unticked claim check is unmet
            edit(p, "- [ ] eval.loss", "- [x] eval.loss")
        declare_null(root, hid)
        E.cmd_close(root, hid, findings=findings)
    if score is not None:
        write(os.path.join(root, "results", hid, "metrics.json"),
              json.dumps({"eval": {"loss": {"value": score}}}))
    if builds_on:
        _set_builds_on(root, hid, builds_on)
    return hid


def run_flight_plan():
    """Spec 05 PRD 05.0 — the flight plan as a crux document (`auto/<qid>/plan.md`).

    The plan is the file the PI signs before a run of 140 attempts starts, so every way it
    can be wrong has to be refused BY NAME at the moment it is written, not discovered at two
    in the morning by a worker that read a field that was not there.

    The reuse is the design: the one nested part of a plan — checks with kinds, failure
    scenarios and a combination rule — is already a format crux parses, so the plan's
    `## Verifiables` is byte-for-byte the node's and goes through `_verifiables()` and
    `verifiable_scenarios()` unchanged. Nothing here is a second parser."""
    print("\n# autopilot — the flight plan (spec 05, PRD 05.0)")
    root = tempfile.mkdtemp(prefix="crux_plan_")
    shutil.rmtree(root); os.makedirs(root)
    try:
        E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")
        qa, _ = E.cmd_ask(root, "the anchor question")
        qi, _ = E.cmd_ask(root, "island one", parent=qa)
        qo, _ = E.cmd_ask(root, "an unrelated question")
        hb = _auto_attempt(root, qa, "the baseline attempt", score=0.90)
        hv = _auto_attempt(root, qi, "an open attempt", close=False)
        rel = f"auto/{qa}/plan.md"
        good = _plan_text(qa, hb, islands=qi)

        # ------------------------------------------------------------- paths and the canary
        check("plan: the flight plan lives at auto/<qid>/plan.md",
              _auto_val(lambda: E.flight_plan_path(root, qa))
              == os.path.join(root, "auto", qa, "plan.md")
              and _auto_val(lambda: (E.AUTO_DIR, E.PLAN_FILE, E.AUTO_STATE_FILE, E.AUTO_LEDGER_FILE))
              == ("auto", "plan.md", "state.json", "ledger.jsonl"))
        check("plan: a well-formed plan carries no problems at all",
              _plan_msgs(root, good, rel) == [])
        check("plan: parse_flight_plan is total — garbage in, no exception out",
              isinstance(_auto_val(lambda: E.parse_flight_plan("not a document at all")), dict)
              and isinstance(_auto_val(lambda: E.parse_flight_plan("")), dict))

        # ------------------------------------------------------- criterion 1: missing fields
        req = _auto_val(lambda: list(E.AUTO_REQUIRED_FIELDS), [])
        named = bool(req) and len(req) == 22
        for name in req:
            if (f"flight plan missing required field: {name}"
                    not in _plan_msgs(root, _plan_text(qa, hb, islands=qi, drop=(name,)), rel)):
                named = False
        check("plan: refuses a plan missing a required field, naming it", named)
        check("plan: an empty field value is missing too, the same test `validate` uses",
              "flight plan missing required field: scorer"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, scorer=""), rel)
              and "flight plan missing required field: steward"
              not in _plan_msgs(root, _plan_text(qa, hb, islands=qi), rel))
        check("plan: a non-integer budget field is refused, naming the field and the value",
              "flight plan field 'budget_attempts' must be a non-negative integer (got 'many')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, budget_attempts="many"), rel))
        check("plan: a negative integer field is refused",
              any(m.startswith("flight plan field 'retries' must be a non-negative integer")
                  for m in _plan_msgs(root, _plan_text(qa, hb, islands=qi, retries="-1"), rel)))
        check("plan: budget_hours must be a number, steward must be a boolean",
              "flight plan field 'budget_hours' must be a non-negative number (got 'soon')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, budget_hours="soon"), rel)
              and "flight plan field 'steward' must be true or false (got 'maybe')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, steward="maybe"), rel))
        check("plan: an unknown mode is refused, naming the two that exist",
              "flight plan mode must be one of climb, explore (got 'drift')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, mode="drift"), rel))
        check("plan: a rule that is not a combination rule is refused",
              "flight plan rule 'vibes' is not a combination rule. Use one of all, any, m-of-n."
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, rule="vibes"), rel))
        check("plan: m-of-n without a usable rule_m is refused, naming the range",
              any(m.startswith("flight plan rule 'm-of-n' needs rule_m set to an integer in 1..")
                  for m in _plan_msgs(root, _plan_text(qa, hb, islands=qi, rule="m-of-n"), rel)))

        # ------------------------------------------------- anchor, islands and the baseline
        check("plan: an anchor that does not exist is refused",
              f"flight plan anchor 'q99' does not exist"
              in _plan_msgs(root, _plan_text("q99", hb), "auto/q99/plan.md"))
        check("plan: an anchor that is not a question is refused",
              f"flight plan anchor '{hb}' is a 'idea', not a question"
              in _plan_msgs(root, _plan_text(hb, hb), f"auto/{hb}/plan.md"))
        check("plan: a directory that disagrees with the anchor is refused",
              f"flight plan at auto/{qo}/plan.md declares anchor '{qa}'; the directory and "
              f"the anchor must agree"
              in _plan_msgs(root, good, f"auto/{qo}/plan.md"))
        check("plan: an island outside the anchor's subtree is refused",
              f"flight plan island '{qo}' is not under the anchor '{qa}'"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qo), rel))
        check("plan: more islands than island_cap is refused",
              f"flight plan names 2 islands, over island_cap 1"
              in _plan_msgs(root, _plan_text(qa, hb, islands=f"{qa}, {qi}", island_cap="1"), rel))
        check("plan: a baseline with no metrics.json is refused",
              f"flight plan baseline '{hv}' has no results/{hv}/metrics.json"
              in _plan_msgs(root, _plan_text(qa, hv, islands=qi), rel))
        check("plan: a baseline that is not a hypothesis, or missing, is refused",
              f"flight plan baseline '{qi}' is a 'question', not a hypothesis"
              in _plan_msgs(root, _plan_text(qa, qi, islands=qi), rel)
              and "flight plan baseline 'h99' does not exist"
              in _plan_msgs(root, _plan_text(qa, "h99", islands=qi), rel))

        # ------------------------------------------------------------- sections and the null
        secs = True
        for name in ("Goal", "Objective", "Null", "Verifiables"):
            gone = _plan_msgs(root, _plan_text(qa, hb, islands=qi, drop_sections=(name,)), rel)
            if f"flight plan section '{name}' is missing or empty" not in gone:
                secs = False
        check("plan: a missing or empty section is refused, naming the section",
              secs
              and "flight plan section 'Goal' is missing or empty"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, goal=""), rel)
              and "flight plan section 'Guidance' is missing"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, drop_sections=("Guidance",)), rel))
        check("plan: a Guidance section holding only its placeholder is present but empty",
              _auto_val(lambda: E.parse_flight_plan(good)["guidance"], None) == []
              and _auto_val(lambda: E.parse_flight_plan(good)["guidance_bad"], None) == []
              and "flight plan section 'Guidance' is missing" not in _plan_msgs(root, good, rel))
        check("plan: a null that the existing null gate rejects is refused, quoting it",
              any(m.startswith("flight plan null: ")
                  for m in _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                                       null="it works better"), rel)))

        # ----------------------------------------------------------------------- the objective
        check("plan: an objective missing a line is refused, naming the line",
              "flight plan objective is missing 'bar::'"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                             objective="address:: eval.loss\ndirection:: min\n"), rel))
        check("plan: an objective direction that is not min or max is refused",
              "flight plan objective direction must be min or max (got 'down')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, direction="down"), rel))
        check("plan: an objective bar that is not a number is refused",
              "flight plan objective bar must be a number (got 'low')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, bar="low"), rel))
        check("plan: an objective address carrying a hid or a slash is refused",
              "flight plan objective address must be a dotted key path into metrics.json "
              f"(got '{hb}#eval.loss')"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi, address=f"{hb}#eval.loss"), rel))

        # ------------------------------------------------- criteria 2, 3, 4: the three refusals
        check("plan: refuses verifiables with no outcome-neutral control",
              "flight plan verifiables carry no outcome-neutral control"
              in _plan_msgs(root, _plan_text(
                  qa, hb, islands=qi,
                  verifiables=("- [ ] eval.loss <= 0.85 on the held-out split\n"
                               "      fails-if:: the median of three seeds stays above 0.85\n"
                               "      discriminates:: true\n")), rel))
        check("plan: refuses an objective no discriminating check names",
              "flight plan objective 'eval.loss' does not correspond to a discriminating "
              "check: no verifiable marked discriminates:: true names it"
              in _plan_msgs(root, _plan_text(
                  qa, hb, islands=qi,
                  verifiables=("- [ ] eval.score <= 0.85 — the held-out score lands at or below the bar\n"
                               "      fails-if:: the median of three seeds stays above the bar\n"
                               "      discriminates:: true\n"
                               "- [ ] [outcome-neutral] baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01\n"
                               "      fails-if:: the baseline re-run lands outside 0.01\n")), rel))
        check("plan: refuses an objective address that does not resolve in the baseline metrics",
              any(m.startswith(f"flight plan objective 'eval.nosuch' does not resolve in "
                               f"results/{hb}/metrics.json: ")
                  for m in _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                                       address="eval.nosuch"), rel)))
        # One spelling, not four: the contract normpaths both sides and strips the trailing
        # slash before comparing, so 'work/' and 'work' are the same path and the message
        # says so exactly once, however the PI spelled it in the plan.
        check("plan: refuses overlapping frozen and writable paths",
              "flight plan frozen path 'work' overlaps writable root 'work'"
              in _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                             frozen="score.py, work/"), rel))
        check("plan: a frozen path inside a writable root overlaps too",
              any("overlaps writable root" in m
                  for m in _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                                       frozen="score.py, work/data"), rel)))
        check("plan: a verifiable with no failure scenario is refused, naming its ordinal",
              "flight plan verifiable(s) 1 have no failure scenario"
              in _plan_msgs(root, _plan_text(
                  qa, hb, islands=qi,
                  verifiables=("- [ ] eval.loss <= 0.85 on the held-out split\n"
                               "      discriminates:: true\n"
                               "- [ ] [outcome-neutral] baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01\n"
                               "      fails-if:: the baseline re-run lands outside 0.01\n")), rel))
        check("plan: every problem carries the check slug that found it",
              set(_auto_val(lambda: {p["check"] for p in E.flight_plan_problems(
                  root, E.parse_flight_plan(_plan_text(qa, hb, islands=qi, mode="drift",
                                                       budget_attempts="many")), rel)}, set()))
              == {"mode", "field-type"})

        # --------------------------------------------- criterion 6: one parser, two documents
        nb = E.Vault(root).get(hv)["body"]
        parsed = _auto_val(lambda: E.parse_flight_plan(good), {})
        check("plan: verifiables parse identically on a plan and on a node",
              parsed.get("verifiables") == E._verifiables(nb)
              and parsed.get("scenarios") == E.verifiable_scenarios(nb)
              and len(E._verifiables(nb)) == 2
              and [x["kind"] for x in E._verifiables(nb)] == [E.DEFAULT_KIND, E.NEUTRAL_KIND]
              and E.count_verifiables_by_kind(parsed.get("body", ""))
              == E.count_verifiables_by_kind(nb))
        check("plan: the parse carries the sections, the goal, the null and the objective",
              parsed.get("goal") == AUTO_PLAN_GOAL
              and parsed.get("null") == AUTO_PLAN_NULL
              and parsed.get("objective") == {"address": "eval.loss", "direction": "min",
                                              "bar": "0.85"}
              and [s for s in parsed.get("sections", [])] ==
              ["## Goal", "## Objective", "## Null", "## Verifiables", "## Guidance"])

        # --------------------------------------------------------------------- auto_check
        ppath = _plan_path(root, qa)
        write(ppath, good)
        before = _byte_map(root)
        res = _auto_val(lambda: E.auto_check(root, rel), {})
        check("plan: auto_check reports ok, the vault-relative path, the anchor and the mode",
              res == {"ok": True, "plan": rel, "anchor": qa, "mode": "climb", "problems": []})
        check("plan: auto_check takes an absolute path too, and reports the same relative one",
              res.get("ok") is True and _auto_val(lambda: E.auto_check(root, ppath), {}) == res)
        check("plan: auto_check is a pure read — it re-stamps nothing, not even .crux.yaml",
              res.get("ok") is True and _byte_map(root) == before)
        check("plan: auto_check on a missing plan names the path it looked at",
              _auto_msg(lambda: E.auto_check(root, f"auto/{qo}/plan.md"))
              == f"no flight plan at auto/{qo}/plan.md")
        write(ppath, _plan_text(qa, hb, islands=qi, mode="drift"))
        bad = _auto_val(lambda: E.auto_check(root, rel), {})
        check("plan: auto_check on a bad plan is not ok and returns every problem",
              bad.get("ok") is False
              and [p["message"] for p in bad.get("problems", [])]
              == ["flight plan mode must be one of climb, explore (got 'drift')"])

        # ------------------------------------------------------------------ load_flight_plan
        write(ppath, good)
        lp = _auto_val(lambda: E.load_flight_plan(root, rel), {})
        check("plan: load_flight_plan carries the fields selection and the brief will read",
              lp.get("anchor") == qa and lp.get("mode") == "climb" and lp.get("baseline") == hb
              and lp.get("islands") == [qi] and lp.get("direction") == "min"
              and lp.get("address") == "eval.loss" and lp.get("bar") == 0.85
              and lp.get("rule") == "all" and lp.get("rule_m") is None
              and lp.get("path") == rel)
        check("plan: climb IS c_puct 0 and explore is the futs default — no greedy code path",
              lp.get("c_puct") == 0.0
              and _auto_val(lambda: E.AUTO_C_PUCT) == {"climb": 0.0, "explore": 1.0}
              and _auto_val(lambda: tuple(E.AUTO_MODES)) == ("climb", "explore"))
        write(ppath, _plan_text(qa, hb, islands=qi, mode="explore"))
        check("plan: an explore plan carries c_puct 1.0",
              _auto_val(lambda: E.load_flight_plan(root, rel), {}).get("c_puct") == 1.0)
        write(ppath, _plan_text(qa, hb))
        check("plan: an empty islands field means the anchor alone is the island",
              _auto_val(lambda: E.load_flight_plan(root, rel), {}).get("islands") == [qa])
        write(ppath, _plan_text(qa, hb, islands=qi, mode="drift"))
        check("plan: load_flight_plan refuses with the first problem's message",
              _auto_msg(lambda: E.load_flight_plan(root, rel))
              == "flight plan mode must be one of climb, explore (got 'drift')")

        # --------------------------------------------- criterion 7: guidance is append-only
        write(ppath, good)
        head_before = read(ppath).split("## Guidance")[0]
        e1 = _auto_val(lambda: E.append_guidance(root, rel, "prefer   small diffs", "pi"), "")
        after_one = read(ppath)
        e2 = _auto_val(lambda: E.append_guidance(root, rel, "keep the scorer frozen", "pi"), "")
        after_two = read(ppath)
        stamped = re.fullmatch(r"- \[\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d\] pi: prefer small diffs",
                               e1 or "")
        entries = _auto_val(lambda: E.parse_flight_plan(after_two)["guidance"], [])
        check("plan: guidance is append-only, stamped with time and author",
              bool(stamped)
              and e1 in after_one and e1 in after_two          # the first entry, verbatim
              and after_two.split("## Guidance")[0] == head_before
              and after_two.rstrip().endswith(e2 or "\x00")
              and [g["text"] for g in entries] == ["prefer small diffs",
                                                   "keep the scorer frozen"]
              and [g["author"] for g in entries] == ["pi", "pi"]
              and all(g["at"] for g in entries))
        check("plan: the first entry displaces the placeholder, and nothing else moves",
              "the PI's standing instructions" not in after_two
              and after_two.count("## Guidance") == 1
              and read(ppath).index(e1 or "\x00") < read(ppath).index(e2 or "\x00"))
        check("plan: a malformed guidance entry is refused, naming its ordinal",
              "flight plan guidance entry 2 is not stamped "
              "(expected '- [<timestamp>] <author>: <text>')"
              in _plan_msgs(root, _plan_text(
                  qa, hb, islands=qi,
                  guidance="- [2026-09-16T10:00:00] pi: the first entry\nfreehand note\n"), rel))
        check("plan: empty guidance text or author is refused, and so is a plan with no section",
              _auto_msg(lambda: E.append_guidance(root, rel, "   ", "pi"))
              == "guidance text is empty"
              and _auto_msg(lambda: E.append_guidance(root, rel, "a note", " "))
              == "guidance author is empty")
        write(ppath, _plan_text(qa, hb, islands=qi, drop_sections=("Guidance",)))
        check("plan: appending to a plan with no Guidance section is refused",
              _auto_msg(lambda: E.append_guidance(root, rel, "a note", "pi"))
              == "flight plan has no ## Guidance section to append to")
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"plan: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_builds_on():
    """Spec 05 PRD 05.0 §B — `builds_on:`, lineage that does not bend the tree.

    An attempt branched from another attempt is not a sub-question of it. Tree depth tracks
    QUESTIONS; if iteration count went into the tree, a 140-attempt run would bury the one
    question being asked under 140 levels of nothing. So the lineage is a field, the attempts
    stay flat siblings, and `validate` carries the four ways the field can lie.

    The fixtures set the field by hand (`_set_builds_on`) rather than through the writer that
    is under test."""
    print("\n# autopilot — builds_on lineage (spec 05, PRD 05.0)")
    root = tempfile.mkdtemp(prefix="crux_lineage_")
    shutil.rmtree(root); os.makedirs(root)
    try:
        E.cmd_init("Lineage", root, goal="keep lineage out of the tree")
        q1, _ = E.cmd_ask(root, "the island question")
        q2, _ = E.cmd_ask(root, "another question")
        h1 = _auto_attempt(root, q1, "the first attempt", score=0.90)
        h2 = _auto_attempt(root, q1, "the second attempt", score=0.80)
        h3 = _auto_attempt(root, q2, "an attempt elsewhere", score=0.70)
        bo = lambda: sorted(m for _, m in E.cmd_validate(root) if "builds_on" in m)

        # ------------------------------------- criterion 9: the field's ABSENCE is the norm
        clean_probs = sorted(m for _, m in E.cmd_validate(root))
        clean_report = json.dumps(_auto_val(lambda: E.validation_report(root), {}), sort_keys=True)
        clean_snap = json.dumps(_auto_val(lambda: E.snapshot(E.Vault(root)), {}), sort_keys=True)
        _set_builds_on(root, h2, h1)
        with_field = json.dumps(_auto_val(lambda: E.validation_report(root), {}), sort_keys=True)
        with_probs = sorted(m for _, m in E.cmd_validate(root))
        with_snap = json.dumps(_auto_val(lambda: E.snapshot(E.Vault(root)), {}), sort_keys=True)
        # The comparison is WITH-field against WITHOUT-field, never the clean vault against
        # itself: removing the field and re-reading the same bytes would agree whatever the
        # new code does. h1 and h3 never carry the field, so what they report is the 3.2
        # behaviour, and it must survive h2 acquiring a lineage.
        check("builds_on: a node without the field validates exactly as today",
              bo() == []
              and with_probs == clean_probs
              and with_snap == clean_snap
              and _auto_val(lambda: E.node_builds_on(E.Vault(root).get(h1))) is None
              and _auto_val(lambda: E.node_builds_on(E.Vault(root).get(h3))) is None)
        _set_builds_on(root, h2, None)
        check("builds_on: a lineage that is sound adds no problem either",
              with_field == clean_report)

        # -------------------------------------------- criterion 8: the four ways it can lie
        _set_builds_on(root, h2, "h99")
        check("builds_on: a target that does not exist is reported by validate",
              bo() == [f"hypothesis '{h2}': builds_on 'h99' does not exist"])
        _set_builds_on(root, h2, q1)
        check("builds_on: a target that is not a hypothesis is reported by validate",
              bo() == [f"hypothesis '{h2}': builds_on '{q1}' is a 'question', not a hypothesis"])
        _set_builds_on(root, h2, h3)
        check("builds_on: a target under another question is reported by validate",
              bo() == [f"hypothesis '{h2}': builds_on '{h3}' sits under '{q2}', "
                       f"not under '{q1}'"])
        _set_builds_on(root, h1, h2); _set_builds_on(root, h2, h1)
        check("builds_on: a cycle is reported by validate, on every node of it, as a walk",
              bo() == sorted([f"hypothesis '{h1}': builds_on cycle: {h1} -> {h2} -> {h1}",
                              f"hypothesis '{h2}': builds_on cycle: {h2} -> {h1} -> {h2}"]))
        _set_builds_on(root, h1, None); _set_builds_on(root, h2, h2)
        check("builds_on: a self reference is a cycle of one hop",
              bo() == [f"hypothesis '{h2}': builds_on cycle: {h2} -> {h2}"])
        _set_builds_on(root, h2, None)

        # ------------------------------------------------------------- the writer and the CLI
        check("builds_on: node_builds_on reads the field, and None when it is absent",
              _auto_val(lambda: E.node_builds_on(E.Vault(root).get(h2))) is None
              and _auto_val(lambda: E.BUILDS_ON_FIELD) == "builds_on")
        made = _auto_val(lambda: E.cmd_hypothesize(
            root, "a branched attempt", parent=q1, rule="all",
            verifiables=["eval.loss <= 0.85 on the held-out split"],
            neutral=["baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01"],
            fails_if=["the median of three seeds stays above 0.85",
                      "the baseline re-run lands outside 0.01"],
            discriminates=[True, False], builds_on=h1))
        check("builds_on: cmd_hypothesize writes the field and returns its shape unchanged",
              isinstance(made, tuple) and len(made) == 3
              and _auto_val(lambda: E.node_builds_on(E.Vault(root).get(made[0]))) == h1
              and f"builds_on: {h1}" in read(node_path(root, made[0]))
              and bo() == [])
        check("builds_on: cmd_hypothesize refuses a bad target before writing the node",
              _auto_msg(lambda: E.cmd_hypothesize(
                  root, "a doomed attempt", parent=q1, rule="all",
                  verifiables=["eval.loss <= 0.85 on the held-out split"],
                  neutral=["baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01"],
                  fails_if=["a world", "another world"], discriminates=[True, False],
                  builds_on="h99")) == "builds_on 'h99' does not exist"
              and _auto_msg(lambda: E.cmd_hypothesize(
                  root, "another doomed attempt", parent=q1, rule="all",
                  verifiables=["eval.loss <= 0.85 on the held-out split"],
                  neutral=["baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01"],
                  fails_if=["a world", "another world"], discriminates=[True, False],
                  builds_on=h3)) == f"builds_on '{h3}' sits under '{q2}', not under '{q1}'")
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "hypothesize",
                            "a CLI branched attempt", "-p", q1, "--builds-on", h1,
                            "-v", "eval.loss <= 0.85 on the held-out split",
                            "--fails-if", "the median of three seeds stays above 0.85",
                            "--discriminates",
                            "-n", "baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01",
                            "--fails-if", "the baseline re-run lands outside 0.01",
                            "--rule", "all", "--json"],
                           capture_output=True, cwd=root, encoding="utf-8", errors="replace")
        made2 = _auto_val(lambda: json.loads(r.stdout).get("id"))
        check("builds_on: the CLI carries --builds-on onto the node",
              r.returncode == 0 and made2
              and _auto_val(lambda: E.node_builds_on(E.Vault(root).get(made2))) == h1)
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"builds_on: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# The shared PUCT fixture (interface contract §5): six attempts, a lineage two levels deep,
# 14 visits in total. Built so the exploration bonus and the raw score order DISAGREE — a
# fixture where the best score also has the fewest visits would pass with the bonus deleted.
AUTO_PUCT_FIXTURE = [{"id": "h1", "score": 0.50, "builds_on": None, "visits": 5},
                     {"id": "h2", "score": 0.80, "builds_on": "h1", "visits": 4},
                     {"id": "h3", "score": 0.78, "builds_on": "h1", "visits": 1},
                     {"id": "h4", "score": 0.60, "builds_on": "h2", "visits": 2},
                     {"id": "h5", "score": 0.62, "builds_on": "h2", "visits": 1},
                     {"id": "h6", "score": 0.61, "builds_on": "h4", "visits": 1}]


def _futs_puct(rows, c_puct, direction="max", virtual=()):
    """futs.py's arithmetic, written out HERE from the ERA source
    (~/.claude/skills/era/scaffold/futs.py — compute_rank_scores, compute_pucts,
    backpropagate_visit), so the engine's port is measured against the thing it was ported
    from rather than against itself."""
    visits = {r["id"]: r["visits"] for r in rows}
    parent = {r["id"]: r["builds_on"] for r in rows}
    for vid in virtual:
        cur = vid
        while cur in visits:
            visits[cur] += 1
            cur = parent.get(cur)
    eff = {r["id"]: (r["score"] if direction == "max" else -r["score"]) for r in rows}
    n = len(rows)
    # Ties: crux breaks them by E.natkey, lower id ranking HIGHER — so on a worst-first rank
    # list, equal scores sort by natkey DESCENDING. futs.py ties on the list order it was
    # handed; crux pins the order so the same vault always selects the same attempt.
    order = sorted(rows, key=lambda r: E.natkey(r["id"]), reverse=True)
    order.sort(key=lambda r: eff[r["id"]])
    rank = {r["id"]: (i / (n - 1) if n > 1 else 0.5) for i, r in enumerate(order)}
    return {r["id"]: rank[r["id"]] + c_puct * (1.0 / n) * math.sqrt(sum(visits.values()))
            / (1 + visits[r["id"]]) for r in rows}


def _puct_ids(rows, c_puct, **kw):
    return [x["id"] for x in _auto_val(lambda: E.puct_rank(rows, c_puct, **kw), [])]


def _puct_close(rows, c_puct, expected, **kw):
    got = {x["id"]: x["puct"] for x in _auto_val(lambda: E.puct_rank(rows, c_puct, **kw), [])}
    return (set(got) == set(expected)
            and all(abs(got[k] - v) <= 1e-6 for k, v in expected.items()))


def run_puct():
    """Spec 05 PRD 05.0 §C — flat PUCT selection, ported from ERA's futs.py.

    Selection is arithmetic over vault state with no side effects, which is the whole
    argument for it living in the engine: it can be tested without a repository, a GPU or a
    model. The `1/N` prior is load-bearing — a constant prior makes the exploration term grow
    without bound and the search never settles — so the fixture pins the numbers, not just
    the order.

    `c_puct = 0` IS Climb. There is no separate greedy path to drift away from this one."""
    print("\n# autopilot — flat PUCT selection (spec 05, PRD 05.0)")
    root = tempfile.mkdtemp(prefix="crux_puct_")
    shutil.rmtree(root); os.makedirs(root)
    try:
        f = AUTO_PUCT_FIXTURE
        # Taken BEFORE the first call: a snapshot read after the fixture has been through
        # puct_rank records whatever damage was already done and then compares it to itself.
        snapshot_in = json.dumps(f, sort_keys=True)
        ranks = {x["id"]: x.get("rank_score")
                 for x in _auto_val(lambda: E.puct_rank(f, 0.0), [])}
        check("puct: c_puct = 0 returns the highest-scoring attempt on every call",
              [_auto_val(lambda: E.puct_select(f, 0.0)) for _ in range(5)] == ["h2"] * 5
              and _puct_ids(f, 0.0) == ["h2", "h3", "h5", "h6", "h4", "h1"]
              and _puct_close(f, 0.0, {"h1": 0.0, "h4": 0.2, "h6": 0.4, "h5": 0.6,
                                       "h3": 0.8, "h2": 1.0}))
        check("puct: reproduces the futs.py ranking on the fixture",
              ranks == {"h1": 0.0, "h4": 0.2, "h6": 0.4, "h5": 0.6, "h3": 0.8, "h2": 1.0}
              and _puct_close(f, 2.0, {"h3": 1.4236095645, "h2": 1.2494438258,
                                       "h5": 1.2236095645, "h6": 1.0236095645,
                                       "h4": 0.6157397097, "h1": 0.2078698548})
              and _puct_ids(f, 2.0) == ["h3", "h2", "h5", "h6", "h4", "h1"]
              and _auto_val(lambda: E.puct_select(f, 2.0)) == "h3")
        check("puct: the fixture's numbers are the futs formula recomputed in the test",
              _puct_close(f, 2.0, _futs_puct(f, 2.0))
              and _puct_close(f, 1.0, _futs_puct(f, 1.0))
              and _puct_close(f, 0.0, _futs_puct(f, 0.0))
              and _puct_close(f, 1.0, _futs_puct(f, 1.0, virtual=("h2",)), virtual=("h2",))
              and _puct_close(f, 1.0, _futs_puct(f, 1.0, direction="min"), direction="min"))
        check("puct: a virtual visit flips the selection",
              _auto_val(lambda: E.puct_select(f, 1.0)) == "h2"
              and _puct_close(f, 1.0, {"h2": 1.1247219129, "h3": 1.1118047823,
                                       "h5": 0.9118047823, "h6": 0.7118047823,
                                       "h4": 0.4078698548, "h1": 0.1039349274})
              and _auto_val(lambda: E.puct_select(f, 1.0, virtual=("h2",))) == "h3")
        check("puct: the virtual visit's two numbers are the ones the flip turns on",
              abs(_auto_val(lambda: {x["id"]: x["puct"] for x in
                                     E.puct_rank(f, 1.0, virtual=("h2",))}, {}).get("h3", 0)
                  - 1.1333333333) <= 1e-6
              and abs(_auto_val(lambda: {x["id"]: x["puct"] for x in
                                         E.puct_rank(f, 1.0, virtual=("h2",))}, {}).get("h2", 0)
                      - 1.1111111111) <= 1e-6)
        check("puct: a virtual visit back-propagates to every builds_on ancestor",
              _auto_val(lambda: {x["id"]: x["visits"] for x in
                                 E.puct_rank(f, 1.0, virtual=("h6",))}, {})
              == {"h1": 6, "h2": 5, "h3": 1, "h4": 3, "h5": 1, "h6": 2})
        _auto_val(lambda: E.puct_rank(f, 1.0, virtual=("h2", "h6")))
        check("puct: the caller's attempt list is never mutated",
              len(_auto_val(lambda: E.puct_rank(f, 1.0), [])) == 6
              and json.dumps(f, sort_keys=True) == snapshot_in)
        check("puct: direction min ranks the LOWEST score first",
              _puct_ids(f, 0.0, direction="min") == ["h1", "h4", "h6", "h5", "h3", "h2"]
              and _auto_val(lambda: E.puct_select(f, 0.0, direction="min")) == "h1")
        check("puct: a lone attempt gets rank score 0.5, as futs does",
              _auto_val(lambda: E.puct_rank([{"id": "h1", "score": 0.5, "builds_on": None,
                                              "visits": 0}], 0.0), [{}])[0].get("rank_score")
              == 0.5)
        check("puct: ties break by natural id order, so h10 follows h9",
              _puct_ids([{"id": f"h{i}", "score": 0.5, "builds_on": None, "visits": 0}
                         for i in (10, 9, 2)], 0.0) == ["h2", "h9", "h10"])
        check("puct: an empty attempt list and a bad direction are refused",
              _auto_msg(lambda: E.puct_select([], 0.0)) == "puct: no scored attempts to rank"
              and _auto_msg(lambda: E.puct_select(f, 0.0, direction="sideways"))
              == "puct: direction must be min or max (got 'sideways')")

        # ------------------------------------------------- the vault-facing wrappers (§5)
        E.cmd_init("Selection", root, goal="pick the next attempt")
        qa, _ = E.cmd_ask(root, "the anchor question")
        qi, _ = E.cmd_ask(root, "island one", parent=qa)
        qx, _ = E.cmd_ask(root, "not an island", parent=qa)
        hb = _auto_attempt(root, qa, "the baseline attempt", score=0.90)
        a1 = _auto_attempt(root, qi, "attempt one", score=0.80, builds_on=hb)
        a2 = _auto_attempt(root, qi, "attempt two", score=0.70, builds_on=a1)
        a3 = _auto_attempt(root, qi, "attempt three", score=0.75, builds_on=a1)
        bad = _auto_attempt(root, qi, "an invalid run", score=0.10, verdict="invalid-run")
        open_one = _auto_attempt(root, qi, "still open", close=False)
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi))
        plan = _auto_val(lambda: E.load_flight_plan(root, f"auto/{qa}/plan.md"), {})
        rows = _auto_val(lambda: E.auto_island_attempts(root, plan, qi), [])
        by = {r["id"]: r for r in rows}
        check("puct: the island's candidates are the baseline plus its done attempts",
              [r["id"] for r in rows] == sorted([hb, a1, a2, a3, bad], key=E.natkey)
              and open_one not in by)
        check("puct: a candidate is scored from the objective address, an invalid run is not",
              by.get(a2, {}).get("score") == 0.70 and by.get(hb, {}).get("score") == 0.90
              and by.get(bad, {}).get("score") is None
              and by.get(bad, {}).get("verdict") == "invalid-run")
        check("puct: a report is a visit, whatever its verdict, and it reaches the ancestors",
              by.get(a1, {}).get("visits") == 3          # a2, a3 and its own report
              and by.get(a2, {}).get("visits") == 1
              and by.get(hb, {}).get("visits") == 3)     # a1, a2, a3 pass through it
        check("puct: a climb plan on min selects the lowest-scoring attempt of the island",
              _auto_val(lambda: E.auto_select(root, f"auto/{qa}/plan.md", island=qi)) == a2)
        check("puct: an island the flight plan never named is refused",
              _auto_msg(lambda: E.auto_select(root, f"auto/{qa}/plan.md", island=qx))
              == f"auto select: '{qx}' is neither the anchor nor an island of the flight plan")
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"puct: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# The anchor's private reasoning. A worker that reads it is told which way to lean, which is
# the whole reason the brief is assembled by the engine and not written by the parent agent.
ABRIEF_ANCHOR_PS = ("ANCHOR-ADVOCACY-LIVES-HERE. The PI believes the wider encoder is the "
                    "answer and this anchor exists to prove it.")
ABRIEF_SIBLING = "SIBLING-ISLAND-PRIVATE"
ABRIEF_LONG_FINDINGS = " ".join(f"word{i}" for i in range(1, 214))     # exactly 213 words


def _abrief_vault(prefix="crux_abrief_"):
    """The brief fixture: an anchor with two islands, a baseline, a parent attempt with a
    lineage, more supported siblings and refuted siblings than the budget allows, twelve
    guidance entries, and a sibling island whose non-best nodes carry sentinels that must
    never reach the brief. Direction is `min`, so the best is the LOWEST value."""
    root = tempfile.mkdtemp(prefix=prefix)
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")
    qa, _ = E.cmd_ask(root, "the anchor question")
    qi, _ = E.cmd_ask(root, "island one", parent=qa)
    qs, _ = E.cmd_ask(root, "island two", parent=qa)
    qt = read(node_path(root, qa))
    write(node_path(root, qa),
          qt.replace(E.LEDGER_START, f"## Problem Statement\n\n{ABRIEF_ANCHOR_PS}\n\n"
                     + E.LEDGER_START, 1))
    ids = {"qa": qa, "qi": qi, "qs": qs}
    ids["hb"] = _auto_attempt(root, qa, "the baseline attempt", score=0.90,
                              findings="the baseline run finished")
    ids["hp"] = _auto_attempt(root, qi, "the parent attempt", score=0.80,
                              builds_on=ids["hb"], findings=ABRIEF_LONG_FINDINGS)
    ids["best"] = _auto_attempt(root, qi, "the best attempt on this island", score=0.62,
                                builds_on=ids["hp"], findings="the best run finished")
    ids["insp"] = [_auto_attempt(root, qi, f"a supported sibling {i}", score=0.70 + i / 100.0,
                                 builds_on=ids["hp"], findings="a supported run finished")
                   for i in range(7)]
    ids["ref"] = [_auto_attempt(root, qi, f"a refuted sibling {i}", score=0.95 + i / 100.0,
                                verdict="refuted", builds_on=ids["hp"],
                                findings="a refuted run finished") for i in range(6)]
    ids["sib"] = [_auto_attempt(root, qs, f"{ABRIEF_SIBLING}-{i}", score=0.75 - i / 10.0,
                                findings=f"{ABRIEF_SIBLING}-FINDINGS-{i}") for i in range(3)]
    ids["sib_best"] = ids["sib"][2]                                   # 0.55, the lowest
    qz, _ = E.cmd_ask(root, "a question no flight plan covers")       # outside the anchor
    ids["qz"] = qz
    ids["hz"] = _auto_attempt(root, qz, "an attempt outside the anchor", score=0.50)
    guidance = "".join(f"- [2026-09-16T10:00:{i:02d}] pi: guidance number {i}\n"
                       for i in range(12))
    write(_plan_path(root, qa),
          _plan_text(qa, ids["hb"], islands=f"{qi}, {qs}", guidance=guidance))
    ids["rel"] = f"auto/{qa}/plan.md"
    return root, ids


def run_auto_brief():
    """Spec 05 PRD 05.0 §D — the brief the engine assembles for each worker.

    A worker must get the shared factual record and nothing else. The anchor's own advocacy,
    a sibling island's dead ends, and a number that was true an hour ago are all ways to tell
    a fresh agent which answer to come back with. So the six checks are part of ASSEMBLY, not
    a separate linter: a brief that fails one is never produced, not merely reported on.

    The check that carries the most weight is the fifth — every number resolves to a live
    vault address, reusing the contract behind `crux deck --verify`. Without it the brief can
    carry a stale "current best" that no reader would ever catch."""
    print("\n# autopilot — the worker brief (spec 05, PRD 05.0)")
    root, ids = _abrief_vault()
    try:
        hp, hb, qa, qi, qs = ids["hp"], ids["hb"], ids["qa"], ids["qi"], ids["qs"]
        pay = _auto_val(lambda: E.auto_brief(root, hp), {})
        blob = json.dumps(pay, sort_keys=True, ensure_ascii=False)
        text = _auto_val(lambda: E.auto_brief_text(pay), "")

        # ------------------------------------------------------ criterion 13: byte-stability
        other = tempfile.mkdtemp(prefix="crux_abrief2_")
        shutil.rmtree(other); shutil.copytree(root, other)
        check("abrief: byte-identical across two assemblies",
              bool(pay)
              and json.dumps(_auto_val(lambda: E.auto_brief(root, hp), {}), sort_keys=True)
              == json.dumps(pay, sort_keys=True)
              and json.dumps(_auto_val(lambda: E.auto_brief(other, hp), {}), sort_keys=True)
              == json.dumps(pay, sort_keys=True)
              and _auto_val(lambda: E.auto_brief_text(E.auto_brief(other, hp)), "") == text)
        shutil.rmtree(other, ignore_errors=True)

        # -------------------------------------------------------- criterion 14: no advocacy
        # Not just the two planted sentinels: EVERY prose-bearing line of the anchor's own
        # ## Problem Statement, as the vault holds it. A sentinel proves the exact string was
        # excluded; the line sweep proves nothing else from that section came along with it.
        anchor_ps = _auto_val(
            lambda: E._section(E.Vault(root).get(qa)["body"], "Problem Statement"), "")
        ps_lines = [ln.strip() for ln in (anchor_ps or "").splitlines()
                    if _auto_val(lambda ln=ln: E._prose_tokens(ln), "")]
        check("abrief: no substring of the anchor problem statement leaks",
              bool(pay) and ABRIEF_ANCHOR_PS.strip() not in blob
              and "ANCHOR-ADVOCACY-LIVES-HERE" not in blob
              and "ANCHOR-ADVOCACY-LIVES-HERE" not in text
              and len(ps_lines) >= 1
              and all(ln not in blob and ln not in text for ln in ps_lines))

        # ----------------------------------------------- criterion 15: the sibling island
        others = [n for n in ids["sib"] if n != ids["sib_best"]]
        check("abrief: a sibling island contributes only its best",
              [m["island"]["id"] for m in pay.get("migration", [])] == [qs]
              and [m["best"]["id"] for m in pay.get("migration", [])] == [ids["sib_best"]]
              and all(f'"{n}"' not in blob for n in others)
              and f'"{ids["sib_best"]}"' in blob
              and blob.count(ABRIEF_SIBLING) == 1                  # the best's claim, once
              and f"{ABRIEF_SIBLING}-FINDINGS" not in blob)        # not even its findings

        # --------------------------------------------------- criterion 16: the empty slot
        broken = tempfile.mkdtemp(prefix="crux_abrief3_")
        shutil.rmtree(broken); shutil.copytree(root, broken)
        # `edit` is str.replace: if templates/idea.md ever stops putting the claim directly
        # above `## Verifiables`, the edit is a silent no-op and this criterion would be
        # testing an INTACT vault. So the fixture asserts it actually emptied the slot.
        before = read(node_path(broken, hp))
        edit(node_path(broken, hp), "\n\nthe parent attempt\n\n## Verifiables",
             "\n\n\n## Verifiables")
        emptied = read(node_path(broken, hp)) != before
        check("abrief: assembly fails naming an empty slot",
              emptied
              and _auto_msg(lambda: E.auto_brief(broken, hp))
              == "auto brief: required slot 'parent.claim' is absent or empty"
              and len(_auto_val(lambda: E.AUTO_BRIEF_SLOTS, ())) == 14)

        # ----------------------------------------------------- criterion 17: the budget cuts
        cut = pay.get("cut", [])
        nwords = len(_auto_val(
            lambda: E._deck_text(E.Vault(root).get(hp)["body"], "Findings"), "").split())
        last = [ln for ln in text.splitlines() if ln.strip()][-1] if text else ""
        check("abrief: over-budget sections are cut by the declared rule and the brief says so",
              len(pay.get("inspirations", [])) == 3
              and len(pay.get("refuted", [])) == 5
              and len(pay.get("guidance", [])) == 10
              and len(pay.get("parent", {}).get("findings", "").split()) == 81
              and pay.get("parent", {}).get("findings", "").endswith(" …")
              and "refuted: kept 5 of 6 (newest by id)" in cut
              and "guidance: kept 10 of 12 (newest)" in cut
              and f"findings {hp}: kept 80 of {nwords} words (leading words)" in cut
              and nwords == 213
              and any(re.fullmatch(r"inspirations: kept 3 of \d+ \(top by score\)", c)
                      for c in cut)
              and last.startswith(_auto_val(lambda: E.AUTO_CUT_PREFIX, "Cut to budget:"))
              and all(c in last for c in cut))
        # The inspirations clause pins the IDS, not the sortedness: the three WORST are also
        # sorted among themselves, so "== sorted(itself)" passes on exactly the list the cut
        # is supposed to throw away. Direction is min, so the top three are the three lowest
        # scores in the pool of eight (the seven supported siblings plus the baseline).
        check("abrief: the cuts keep the declared end of each list, not an arbitrary one",
              [g["text"] for g in pay.get("guidance", [])]
              == [f"guidance number {i}" for i in range(2, 12)]
              and [r["id"] for r in pay.get("refuted", [])]
              == sorted(ids["ref"], key=E.natkey, reverse=True)[:5]
              and [i["id"] for i in pay.get("inspirations", [])] == ids["insp"][:3]
              and [i["score"]["value"] for i in pay.get("inspirations", [])]
              == [0.70, 0.71, 0.72]
              and not any(i["id"] in ids["insp"][-3:]
                          for i in pay.get("inspirations", [])))

        # ------------------------------------------- criterion 18: every number is an address
        stale = json.loads(json.dumps(pay)) if pay else {}
        live = pay.get("best", {}).get("score", {}).get("value")
        addr = pay.get("best", {}).get("score", {}).get("addr")
        if stale:
            stale["best"]["score"]["value"] = (live or 0) + 1.0
        reports = _auto_val(lambda: E.auto_brief_verify(root, stale), None)
        check("abrief: every number resolves, and a stale best is rejected",
              _auto_val(lambda: E.auto_brief_verify(root, pay), None) == []
              and addr == f'{pay.get("best", {}).get("id")}#eval.loss'
              and isinstance(reports, list) and len(reports) == 1
              and reports[0]["addr"] == addr and reports[0]["live"] == live
              and reports[0]["message"]
              == f"{addr}: brief carries {(live or 0) + 1.0}, vault has {live}")

        # ------------------------------------------ criterion 19: the empty case, said aloud
        quiet = _auto_val(lambda: E.auto_brief(root, ids["sib"][1]), {})
        qtext = _auto_val(lambda: E.auto_brief_text(quiet), "")
        check("abrief: no refuted siblings is said explicitly",
              quiet.get("refuted") == []
              and _auto_val(lambda: E.AUTO_NO_REFUTED) in (qtext or "\x00")
              and _auto_val(lambda: E.AUTO_NO_REFUTED)
              == "No refuted attempts on this island yet.")

        # -------------------------------------------------------------- shape and discovery
        check("abrief: the payload carries the plan, the anchor and the island it came from",
              pay.get("plan") == ids["rel"] and pay.get("mode") == "auto"
              and pay.get("engine_version") == E.ENGINE_VERSION
              and pay.get("anchor") == {"id": qa, "title": "the anchor question"}
              and pay.get("island") == {"id": qi, "title": "island one"}
              and pay.get("goal") == AUTO_PLAN_GOAL
              and pay.get("objective") == {"address": "eval.loss", "direction": "min",
                                           "bar": 0.85})
        check("abrief: every metric travels as a value and the address it came from",
              pay.get("parent", {}).get("score") == {"value": 0.80, "addr": f"{hp}#eval.loss"}
              and pay.get("best", {}).get("id") == ids["best"]
              and pay.get("best", {}).get("score", {}).get("value") == 0.62
              and all(set(i["score"]) == {"value", "addr"} for i in pay.get("inspirations", [])))
        check("abrief: the parent's verdict, claim and findings travel with it",
              pay.get("parent", {}).get("id") == hp
              and pay.get("parent", {}).get("claim") == "the parent attempt"
              and pay.get("parent", {}).get("verdict") == "supported")
        check("abrief: inspirations exclude the parent and the best, and are supported only",
              len(pay.get("inspirations", [])) == 3
              and all(i["id"] not in (hp, ids["best"]) for i in pay.get("inspirations", []))
              and all(i["id"] not in ids["ref"] for i in pay.get("inspirations", [])))
        check("abrief: a refuted sibling travels with the checks that failed it",
              all(r["failed_checks"] and all(set(c) == {"text", "fails_if"}
                                             for c in r["failed_checks"])
                  for r in pay.get("refuted", []))
              and pay.get("refuted", [{}])[0].get("failed_checks", [{}])[0].get("fails_if")
              == "the median of three seeds stays above 0.85")
        check("abrief: the inherited bar is the plan's null, checks and rule",
              pay.get("null") == AUTO_PLAN_NULL and pay.get("rule") == "all"
              and pay.get("rule_m") is None
              and [v["kind"] for v in pay.get("verifiables", [])]
              == [E.DEFAULT_KIND, E.NEUTRAL_KIND]
              and pay.get("verifiables", [{}])[0].get("discriminates") is True)
        v = E.Vault(root)
        under = sum(1 for n in v.nodes.values() if n.type == "idea"
                    and qa in [m.id for m in E.ancestor_chain(v, n)])
        check("abrief: the budget counts the attempts already spent under the anchor",
              pay.get("budget", {}).get("attempts", {}).get("total") == 40
              and under == 19 and under + 1 == sum(1 for n in v.nodes.values()
                                                   if n.type == "idea")
              and pay.get("budget", {}).get("attempts", {}).get("used") == under
              and pay.get("budget", {}).get("attempts", {}).get("remaining") == 40 - under)
        check("abrief: the rendering names the island, the bar and the current best",
              text.startswith(f"# Autopilot brief — next attempt on {qi}")
              and ids["rel"] in text
              and all(h in text for h in ("## Goal", "## Objective", "## Island",
                                          "## Parent attempt", "## Inspirations",
                                          "## Refuted attempts", "## Other islands",
                                          "## Inherited bar", "## Guidance", "## Budget"))
              and f"{ids['best']}#eval.loss" in text)
        check("abrief: a plan is found on the nearest ancestor question of the attempt",
              _auto_val(lambda: E.auto_brief(root, ids["insp"][0]), {}).get("plan")
              == ids["rel"])
        check("abrief: an attempt with no flight plan above it is refused, naming the gap",
              _auto_msg(lambda: E.auto_brief(root, ids["hz"]))
              == f"no flight plan covers {ids['hz']}: none of its ancestor questions has "
                 f"auto/<qid>/plan.md")
        # The anchor carries the plan itself, and plan discovery walks ANCESTORS — so unless
        # the type check runs first, the anchor is told no plan covers it, which is a fact
        # about the walk and not about the vault.
        check("abrief: the brief is per-attempt — a question is refused",
              _auto_msg(lambda: E.auto_brief(root, qi))
              == f"auto brief is per-attempt (got a 'question' for '{qi}')"
              and _auto_msg(lambda: E.auto_brief(root, qa))
              == f"auto brief is per-attempt (got a 'question' for '{qa}')")

        # ---------------------------------------------- criterion 6 of §6: the lint report
        rep = _auto_val(lambda: E.auto_brief_lint(root, hp), {})
        names = _auto_val(lambda: list(E.AUTO_BRIEF_CHECKS), [])
        check("abrief: the lint report runs every check, in the declared order",
              names == ["schema", "budget", "stable", "leakage", "addresses"]
              and rep.get("ok") is True and rep.get("id") == hp
              and [c["name"] for c in rep.get("checks", [])] == names
              and all(c["ok"] for c in rep.get("checks", []))
              and rep.get("text") == text and rep.get("brief") == pay)
        brep = _auto_val(lambda: E.auto_brief_lint(broken, hp), {})
        check("abrief: a brief that cannot be assembled reports schema failing, rest not run",
              brep.get("ok") is False and brep.get("brief") is None and brep.get("text") == ""
              and [c["name"] for c in brep.get("checks", [])] == names
              and brep.get("checks", [{}])[0].get("detail")
              == "auto brief: required slot 'parent.claim' is absent or empty"
              and all(c["detail"] == "not run" and c["ok"] is False
                      for c in brep.get("checks", [])[1:]))
        shutil.rmtree(broken, ignore_errors=True)

        # --------------------------------------------------- the empty case: no guidance yet
        quiet_root = tempfile.mkdtemp(prefix="crux_abrief4_")
        shutil.rmtree(quiet_root); shutil.copytree(root, quiet_root)
        write(_plan_path(quiet_root, qa), _plan_text(qa, hb, islands=f"{qi}, {qs}"))
        empty = _auto_val(lambda: E.auto_brief(quiet_root, hp), {})
        check("abrief: a plan with no guidance renders the no-guidance line, not a blank",
              empty.get("guidance") == []
              and "No guidance yet." in _auto_val(lambda: E.auto_brief_text(empty), "")
              and not any(c.startswith("guidance:") for c in empty.get("cut", [])))
        shutil.rmtree(quiet_root, ignore_errors=True)

        # ------------- the baseline under a SIBLING island, and an island nobody has worked
        # Two shapes the main fixture cannot make. The baseline is a candidate of every island
        # (§5) and the PI's own starting point, so a brief must not treat it as another
        # island's private product — it reaches this island as an inspiration, findings and
        # all, and banning it would make a valid plan fail its own lint. And an island with no
        # attempts of its own must not report the shared baseline as "its best": that tells a
        # worker an island has produced something when it has produced nothing.
        side = tempfile.mkdtemp(prefix="crux_abrief5_")
        shutil.rmtree(side); os.makedirs(side)
        E.cmd_init("Autopilot", side, goal="drive the held-out loss below the bar")
        sa, _ = E.cmd_ask(side, "the anchor question")
        s1, _ = E.cmd_ask(side, "island one", parent=sa)
        s2, _ = E.cmd_ask(side, "island two", parent=sa)
        s3, _ = E.cmd_ask(side, "island three", parent=sa)          # nobody has worked it
        sb = _auto_attempt(side, s2, "the baseline attempt", score=0.90,
                           findings="the baseline run finished")
        sp = _auto_attempt(side, s1, "the parent attempt", score=0.80, builds_on=sb)
        write(_plan_path(side, sa), _plan_text(sa, sb, islands=f"{s1}, {s2}, {s3}"))
        srep = _auto_val(lambda: E.auto_brief_lint(side, sp), {})
        spay = srep.get("brief") or {}
        check("abrief: a baseline sitting under another island is not that island's secret",
              srep.get("ok") is True
              and [c["name"] for c in srep.get("checks", []) if not c["ok"]] == []
              and sb in [i["id"] for i in spay.get("inspirations", [])])
        check("abrief: an island nobody has worked contributes no best of its own",
              [m["island"]["id"] for m in spay.get("migration", [])] == [s2]
              and [m["best"]["id"] for m in spay.get("migration", [])] == [sb])
        shutil.rmtree(side, ignore_errors=True)
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"abrief: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_auto_cli():
    """Spec 05 PRD 05.0 §7 — `crux auto check | brief | guide`.

    Three verbs, all read-only or append-only, none of which starts a process. That last
    clause is the whole seam this PRD sits on: the loop that spawns workers is 05.2, and the
    way to keep the engine pure until then is a test that FAILS if a subprocess is spawned —
    which is why the no-spawn assert monkeypatches the spawn primitives and calls `main()`
    in-process rather than trusting a code review."""
    print("\n# autopilot — the CLI (spec 05, PRD 05.0)")
    root = tempfile.mkdtemp(prefix="crux_autocli_")
    shutil.rmtree(root); os.makedirs(root)
    try:
        E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")
        qa, _ = E.cmd_ask(root, "the anchor question")
        qi, _ = E.cmd_ask(root, "island one", parent=qa)
        hb = _auto_attempt(root, qa, "the baseline attempt", score=0.90)
        hp = _auto_attempt(root, qi, "the parent attempt", score=0.80, builds_on=hb)
        _auto_attempt(root, qi, "a supported sibling", score=0.70, builds_on=hp)
        rel = f"auto/{qa}/plan.md"
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi))

        def cli(*argv, cwd=root):
            return subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + list(argv),
                                  capture_output=True, cwd=cwd, encoding="utf-8",
                                  errors="replace")

        check("auto: ENGINE_VERSION at or past 3.3", at_least_version("3.3"))

        # ------------------------------------------------------------------- check and guide
        # `--static` is 05.1's flag for what 05.0's bare `auto check` did: engine checks and
        # nothing else. The default now runs the PI's scorer, which this fixture's vault — a
        # bare temp directory inside no repository — has no repository to run it in, so every
        # 05.0 assert about the engine-only result moves to the flag that still means it.
        ok = cli("auto", "check", rel, "--static")
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi, mode="drift"))
        bad = cli("auto", "check", rel)
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi))
        check("auto: check passes a good plan naming the anchor and the mode, exit 0",
              ok.returncode == 0 and rel in ok.stdout and qa in ok.stdout
              and "climb" in ok.stdout)
        check("auto: check fails a bad plan with one line per problem, exit 1",
              bad.returncode == 1
              and "flight plan mode must be one of climb, explore (got 'drift')" in
              (bad.stdout + bad.stderr))
        g = cli("auto", "guide", rel, "--author", "pi", "prefer small diffs")
        check("auto: guide appends the PI's words and reports the entry count",
              g.returncode == 0 and "guidance appended" in g.stdout and rel in g.stdout
              and "prefer small diffs" in read(_plan_path(root, qa)))
        none = cli("auto")
        check("auto: a missing sub-verb names the three that exist",
              none.returncode == 1
              and "auto needs a sub-verb — check / brief / guide" in (none.stderr + none.stdout))
        plain = cli("auto", "brief", hp)
        check("auto: a bare brief prints the worker's text and never JSON",
              plain.returncode == 0 and plain.stdout.lstrip().startswith("# Autopilot brief")
              and not plain.stdout.lstrip().startswith("{"))

        # ------------------------------------------------------- criterion 20: brief --lint
        names = _auto_val(lambda: list(E.AUTO_BRIEF_CHECKS), [])
        lint = cli("auto", "brief", hp, "--lint")
        broken = tempfile.mkdtemp(prefix="crux_autocli2_")
        shutil.rmtree(broken); shutil.copytree(root, broken)
        before = read(node_path(broken, hp))          # the no-op guard, as in criterion 16
        edit(node_path(broken, hp), "\n\nthe parent attempt\n\n## Verifiables",
             "\n\n\n## Verifiables")
        emptied = read(node_path(broken, hp)) != before
        blint = cli("auto", "brief", hp, "--lint", cwd=broken)
        check("auto: brief --lint prints the brief and every check and exits non-zero on failure",
              emptied
              and len(names) == 5
              and lint.returncode == 0
              and "# Autopilot brief" in lint.stdout
              and "auto brief checks:" in lint.stdout
              and all(f"ok   {n}" in lint.stdout for n in names)
              and blint.returncode == 1
              and all(n in blint.stdout for n in names)
              and "FAIL schema" in blint.stdout)
        shutil.rmtree(broken, ignore_errors=True)

        # ------------------------------------------------- criterion 22: --json on every verb
        j1 = cli("auto", "check", rel, "--static", "--json")
        j2 = cli("auto", "brief", hp, "--json")
        j3 = cli("auto", "brief", hp, "--lint", "--json")
        j4 = cli("auto", "guide", rel, "--author", "pi", "keep the scorer frozen", "--json")
        d = [_auto_val(lambda r=r: json.loads(r.stdout)) for r in (j1, j2, j3, j4)]
        check("auto: every new verb emits JSON under --json",
              all(r.returncode == 0 for r in (j1, j2, j3, j4))
              and all(isinstance(x, dict) for x in d)
              and set(d[0]) == {"ok", "plan", "anchor", "mode", "problems"}
              and set(d[1]) >= {"engine_version", "mode", "plan", "anchor", "goal", "objective",
                                "island", "parent", "best", "inspirations", "refuted",
                                "migration", "null", "verifiables", "rule", "rule_m",
                                "guidance", "budget", "cut"}
              and set(d[2]) == {"ok", "id", "brief", "text", "checks"}
              and set(d[3]) == {"plan", "entry", "entries"}
              and d[3]["entries"] == 2)
        jbad = cli("auto", "check", f"auto/{qi}/plan.md", "--json")
        check("auto: a CruxError from any auto verb is the usual one-line refusal, exit 1",
              jbad.returncode == 1 and jbad.stderr.startswith("crux: no flight plan at"))

        # ------------------------------------- criterion 21: validated without a single spawn
        sys.path.insert(0, HERE)
        import crux as C
        spawned = []

        def boom(*a, **k):
            spawned.append(a)
            raise AssertionError("process spawned")

        patched = [(m, n) for m, n in ((subprocess, "Popen"), (subprocess, "run"),
                                       (os, "system"), (os, "popen"), (os, "fork"),
                                       (os, "posix_spawn"), (os, "posix_spawnp"),
                                       (os, "spawnv"), (os, "spawnvp"), (os, "execv"),
                                       (os, "execvp")) if hasattr(m, n)]
        saved = [(m, n, getattr(m, n)) for m, n in patched]
        cwd = os.getcwd()

        def in_process(argv):
            out = io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
                    rc = C.main(argv)
            except SystemExit as e:
                rc = e.code
            except Exception as e:
                rc = repr(e)
            return rc, out.getvalue()

        try:
            for m, n, _ in saved:
                setattr(m, n, boom)
            os.chdir(root)
            rc_ok, out_ok = in_process(["auto", "check", rel, "--static", "--json"])
            write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi, mode="drift"))
            rc_bad, out_bad = in_process(["auto", "check", rel, "--static", "--json"])
        finally:
            for m, n, fn in saved:
                setattr(m, n, fn)
            os.chdir(cwd)
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi))
        payload_ok = _auto_val(lambda: json.loads(out_ok))
        payload_bad = _auto_val(lambda: json.loads(out_bad))
        check("auto: check --static validates a plan without spawning any process",
              spawned == [] and rc_ok == 0 and rc_bad == 1
              and isinstance(payload_ok, dict) and payload_ok.get("ok") is True
              and set(payload_ok) == {"ok", "plan", "anchor", "mode", "problems"}
              and isinstance(payload_bad, dict) and payload_bad.get("ok") is False
              and not re.search(r"^\s*(import|from)\s+(subprocess|threading|socket|urllib)",
                                read(os.path.join(HERE, "engine.py")), re.M))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"auto: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


# ------------------------------------------------- 05.1: the git and workspace layer, fixtures
# Everything below is written against the PRD and the interface contract alone — the module it
# exercises did not exist when these asserts were written, which is the point: a test that has
# read the implementation asserts what the code does, not what was asked for.
GIT_ID = ["-c", "user.name=crux-selftest", "-c", "user.email=selftest@crux.invalid",
          "-c", "commit.gpgsign=false", "-c", "core.hooksPath=", "-c", "core.excludesFile=",
          "-c", "init.defaultBranch=main"]


def _git(cwd, *args, check=True):
    """git, carrying the suite's own identity.

    The machine running this may have no `user.name`, no `init.defaultBranch` and a signing key
    that prompts — none of which is the subject of any test here — so every fixture git pins its
    own identity and names its branch by hand. The hooks path and the excludes file are emptied
    for the same reason one step further out: a developer whose global config points every
    repository at a `pre-commit` hook, or hides `work/` from every `git add`, would otherwise
    see these fixtures fail for a reason that has nothing to do with crux."""
    r = subprocess.run(["git"] + GIT_ID + list(args), cwd=cwd, capture_output=True,
                       encoding="utf-8", errors="replace")
    if check and r.returncode != 0:
        raise RuntimeError(f"git {' '.join(args)}: {r.stderr}")
    return r.stdout.strip()


# The scorer's whole contract in six lines: stdout is one JSON object, stderr is free text.
# Each variant below breaks exactly one clause of it, so each failure name has a witness.
SCORE_PY = '''import json, os, sys
sys.stderr.write("scoring\\n")
print(json.dumps({"eval": {"loss": {"value": 0.80}},
                  "env": {"attempt": {"value": os.environ.get("CRUX_ATTEMPT", "")},
                          "workspace": {"value": os.environ.get("CRUX_WORKSPACE", "")}}}))
'''
SCORE_EXIT = '''import sys
sys.stderr.write("boom: the dataset is missing\\n")
sys.exit(3)
'''
SCORE_SLOW = '''import time
time.sleep(30)
print("{}")
'''
SCORE_TEXT = '''print("loss 0.8")
'''
SCORE_TWO = '''import json
print(json.dumps({"eval": {"loss": {"value": 0.8}}}))
print(json.dumps({"eval": {"loss": {"value": 0.7}}}))
'''
SCORE_NUM = '''print(0.8)
'''
SCORE_NOADDR = '''import json
print(json.dumps({"eval": {"acc": {"value": 0.5}}}))
'''
SCORE_STR = '''import json
print(json.dumps({"eval": {"loss": {"value": "not a number"}}}))
'''
SCORE_NOISY = '''import sys
sys.stderr.write("head-marker " + "x" * 5000 + " tail-marker\\n")
sys.exit(1)
'''
SCORERS = (("score.py", SCORE_PY), ("score_exit.py", SCORE_EXIT), ("score_slow.py", SCORE_SLOW),
           ("score_text.py", SCORE_TEXT), ("score_two.py", SCORE_TWO), ("score_num.py", SCORE_NUM),
           ("score_noaddr.py", SCORE_NOADDR), ("score_str.py", SCORE_STR),
           ("score_noisy.py", SCORE_NOISY))


_AUTO_TRASH = []      # every fixture repository made below, so none can outlive its section


def _auto_sweep():
    """Remove every fixture repository made since the last sweep. Each section calls this in
    its `finally`, rather than removing the name it got back: `_auto_repo` can raise after the
    directory exists — `git init` on a full disk, a vault that will not build — and a name that
    was never returned is a temp directory nobody will ever delete.

    Removal goes through `_loop_rmtree`: nearly every fixture here is a git repository, git
    writes its loose objects read-only, and on Windows a read-only file cannot be unlinked."""
    while _AUTO_TRASH:
        _loop_rmtree(_AUTO_TRASH.pop())


def _auto_repo(scorer="python3 score.py", extra=(), retention="failed", islands=True):
    """A throwaway git repository with a crux vault tracked inside it — the normal shape, where
    the notebook records the project it sits in. Returns (repo, root, qa, qi, hb, rel).

    `main` is pinned by hand because `init.defaultBranch` is unset on plenty of machines, and
    the repository is realpath'd because macOS hands out `/var/...` for a directory whose real
    name is `/private/var/...` — a difference every path comparison below would trip over.

    Plan defaults: frozen `score.py, data/`, writable `work/, results/` — so the workspace is
    `<repo>/work/<hid>`, the shared roots are `<repo>/work` and `<repo>/results`, and the
    effective frozen set adds `cruxvault`. Objective `eval.loss`, min, bar 0.85."""
    repo = os.path.realpath(tempfile.mkdtemp(prefix="crux_arepo_"))
    _AUTO_TRASH.append(repo)                     # registered BEFORE anything can raise
    _git(repo, "init", "-q")
    _loop_name_main(repo)
    for name, text in SCORERS:
        write(os.path.join(repo, name), text)
    write(os.path.join(repo, "train.py"), "print('train')\n")
    write(os.path.join(repo, "data", "train.txt"), "1 2 3\n")
    root = os.path.join(repo, "cruxvault")
    E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")
    qa, _ = E.cmd_ask(root, "the anchor question")
    qi, _ = E.cmd_ask(root, "island one", parent=qa)
    hb = _auto_attempt(root, qa, "the baseline attempt", score=0.90)
    rel = f"auto/{qa}/plan.md"
    write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi if islands else "",
                                           scorer=scorer, retention=retention, extra=extra))
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo, root, qa, qi, hb, rel


def _auto_mod():
    """`autopilot` when it imports, and a stand-in whose every name raises when it does not.

    These asserts were written before the module existed. A bare `import autopilot` at the top
    of a section would cost the whole section one red line saying nothing about which criterion
    is unmet; the stand-in costs each criterion its own line, which is the only reason to write
    the tests first. Imported inside the section body, never at module scope, for the same
    reason: a top-level import of an absent module kills the suite."""
    try:
        import autopilot
        return autopilot
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        class _Absent(object):
            def __getattr__(self, name):
                raise E.CruxError(f"autopilot.{name} is not implemented ({e})")
        return _Absent()


def _auto_ok(fn):
    """`bool(fn())`, and False when fn raises — one red line per criterion, never a dead section."""
    return bool(_auto_val(fn, False))


def run_auto_lock():
    """Spec 05 PRD 05.1 §C — the one vault-level lock at `auto/.lock`.

    Two runs in one vault share one id counter and one set of index files, so the lock is
    vault-level rather than per-anchor. What is asserted is the part a human has to trust at
    3 a.m.: a held lock refuses the second caller by pid rather than hanging, and a lock whose
    owner died is reclaimed once instead of waited out for the full sixty seconds."""
    print("\n# autopilot — the vault lock (spec 05, PRD 05.1)")
    root = tempfile.mkdtemp(prefix="crux_alock_")
    try:
        A = _auto_mod()
        shutil.rmtree(root); os.makedirs(root)
        E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")

        # ------------------------------------------------- criterion 11: the second acquirer
        st = {}
        try:
            st["first"] = A.acquire_lock(root, "test")
            t0 = time.monotonic()
            st["msg"] = _auto_msg(lambda: A.acquire_lock(root, "second", wait=0.3))
            st["elapsed"] = time.monotonic() - t0
            st["held"] = A.read_lock(root)
            A.release_lock(root)
            st["gone"] = not os.path.exists(A.lock_path(root))
            st["after"] = A.read_lock(root)
            st["twice"] = _auto_val(lambda: A.release_lock(root), "raised") is None
        except Exception as e:                               # pragma: no cover - wave-1 guard
            st["oops"] = repr(e)
        check("alock: a second acquirer fails after the stated wait, naming the holder's pid",
              _auto_ok(lambda: (
                  f"pid {os.getpid()}" in st["msg"] and "gave up after 0.3s" in st["msg"]
                  and "auto/.lock" in st["msg"] and "test" in st["msg"]
                  and 0.3 <= st["elapsed"] < 5.0
                  and st["first"] == A.lock_path(root)
                  and st["held"]["op"] == "test" and st["held"]["host"] == A.HOST
                  and st["held"]["pid"] == os.getpid()
                  and st["gone"] and st["after"] is None and st["twice"])))

        # ------------------------------------------------------ criterion 12: the stale lock
        s2 = {}
        try:
            p = subprocess.Popen([sys.executable, "-c", "pass"])
            p.wait()                                         # reaped, so os.kill(pid, 0) fails
            write(A.lock_path(root), json.dumps({"pid": p.pid, "host": A.HOST,
                                                 "time": E.now(), "op": "ghost"}))
            s2["got"] = A.acquire_lock(root, "reclaim", wait=1.0)
            s2["rec"] = A.read_lock(root)
            s2["again"] = _auto_msg(lambda: A.acquire_lock(root, "third", wait=0.2))
            A.release_lock(root)
            write(A.lock_path(root), json.dumps({"pid": os.getpid(), "host": A.HOST,
                                                 "time": E.now(), "op": "aged"}))
            old = time.time() - 1000
            os.utime(A.lock_path(root), (old, old))
            s2["aged"] = A.acquire_lock(root, "byage", wait=0.5)
            s2["aged_rec"] = A.read_lock(root)
            A.release_lock(root)
        except Exception as e:                               # pragma: no cover - wave-1 guard
            s2["oops"] = repr(e)
        check("alock: a lock left by a dead pid on this host is reclaimed once and the reclaimer holds it",
              _auto_ok(lambda: (
                  s2["got"] == A.lock_path(root)
                  and s2["rec"]["pid"] == os.getpid() and s2["rec"]["op"] == "reclaim"
                  and s2["rec"]["host"] == A.HOST
                  and f"pid {os.getpid()}" in s2["again"]
                  and "gave up after 0.2s" in s2["again"])))
        check("alock: a lock past stale_after is reclaimed by age even when its pid is alive",
              _auto_ok(lambda: s2["aged"] == A.lock_path(root)
                       and s2["aged_rec"]["op"] == "byage"))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"alock: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)


def run_auto_reserve():
    """Spec 05 PRD 05.1 §D — ids reserved centrally, before any node exists.

    The counter in `.crux.yaml` is a plain read-modify-write, so two workers that ask at the
    same moment get one id and one of them silently overwrites the other's node. The assert is
    four real processes rather than four threads: the thing under test is a file on disk, and
    threads inside one interpreter would never contend for it."""
    print("\n# autopilot — id reservation (spec 05, PRD 05.1)")
    root = tempfile.mkdtemp(prefix="crux_aid_")
    root2 = tempfile.mkdtemp(prefix="crux_aid2_")
    try:
        A = _auto_mod()
        for r in (root, root2):
            shutil.rmtree(r); os.makedirs(r)

        def _counter(r):
            m = re.search(r"^counter_h:\s*(\d+)", read(os.path.join(r, ".crux.yaml")), re.M)
            return int(m.group(1)) if m else -1

        # ----------------------------------------- criterion 9: twenty ids, four processes
        E.cmd_init("Autopilot", root, goal="drive the held-out loss below the bar")
        qa, _ = E.cmd_ask(root, "the anchor question")
        st = {}
        try:
            st["before"] = _counter(root)
            procs = [subprocess.Popen([sys.executable, os.path.join(HERE, "autopilot.py"),
                                       "reserve", root, qa, "5"],
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                      encoding="utf-8", errors="replace") for _ in range(4)]
            # Bounded: the thing under test is a lock, and the way a lock fails is by never
            # letting go. Without the timeout that failure hangs the suite instead of failing it.
            outs = [p.communicate(timeout=30) for p in procs]
            st["rcs"] = [p.returncode for p in procs]
            st["ids"] = [l.strip() for out, _ in outs for l in out.splitlines() if l.strip()]
            st["after"] = _counter(root)
            st["rec"] = A.reservations(root, qa)
            st["file"] = os.path.isfile(os.path.join(root, "auto", qa, "reserved.json"))
        except Exception as e:                               # pragma: no cover - wave-1 guard
            st["oops"] = repr(e)
        check("aid: twenty ids from four concurrent processes are distinct and every one is in reserved.json",
              _auto_ok(lambda: (
                  len(st["ids"]) == 20 and len(set(st["ids"])) == 20
                  and all(re.fullmatch(r"h\d+", x) for x in st["ids"])
                  and st["rcs"] == [0, 0, 0, 0] and st["file"]
                  and set(st["rec"]) >= set(st["ids"])
                  and all(st["rec"][i]["state"] == "reserved" for i in st["ids"])
                  and all(st["rec"][i]["island"] == qa for i in st["ids"])
                  and st["after"] - st["before"] == 20)))

        # -------------------------------- criterion 10: a reservation that never became a node
        E.cmd_init("Autopilot", root2, goal="drive the held-out loss below the bar")
        qb, _ = E.cmd_ask(root2, "the anchor question")
        s2 = {}
        try:
            s2["before"] = E.cmd_validate(root2)
            s2["h"] = A.reserve_id(root2, qb)
            s2["mid"] = E.cmd_validate(root2)
            h2, _, _ = E.cmd_hypothesize(
                root2, "next", parent=qb, rule="all",
                verifiables=["eval.loss <= 0.85 on the held-out split"],
                neutral=["baseline.drift <= 0.01 — the baseline re-run reproduces to within 0.01"],
                fails_if=["the median of three seeds stays above 0.85",
                          "the baseline re-run lands outside 0.01"],
                discriminates=[True, False])
            s2["h2"] = h2
            s2["rec"] = A.reservations(root2, qb)
            s2["node"] = _auto_val(lambda: E.Vault(root2).get(s2["h"]))
            s2["after"] = E.cmd_validate(root2)
        except Exception as e:                               # pragma: no cover - wave-1 guard
            s2["oops"] = repr(e)
        check("aid: a reserved id with no node stays reserved, is never handed out again, and validate is unchanged",
              _auto_ok(lambda: (
                  s2["h2"] != s2["h"] and E.natkey(s2["h2"]) > E.natkey(s2["h"])
                  and s2["rec"][s2["h"]]["state"] == "reserved"
                  and s2["node"] is None
                  and s2["mid"] == s2["before"] and s2["after"] == s2["before"]
                  and not any(s2["h"] in m for _, m in s2["after"]))))

        # ------------------- a reservation file that will not parse is the record, damaged
        s3 = {}
        try:
            p = A.reserved_path(root2, qb)
            s3["was"] = read(p)
            write(p, "{not json")
            s3["counter"] = _counter(root2)
            s3["msg"] = _auto_msg(lambda: A.reserve_id(root2, qb))
            s3["still"] = read(p)
            s3["counter_after"] = _counter(root2)
            s3["locked"] = os.path.exists(A.lock_path(root2))
            write(p, s3["was"])
        except Exception as e:                               # pragma: no cover - wave-1 guard
            s3["oops"] = repr(e)
        check("aid: a reserved.json that will not parse is refused, not silently reset",
              _auto_ok(lambda: (
                  f"auto/{qb}/reserved.json" in s3["msg"]
                  and s3["still"] == "{not json"            # the damaged file is left alone
                  and s3["counter_after"] == s3["counter"]  # and the refusal costs no id
                  and not s3["locked"])))                   # and the lock is not left behind
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aid: section ran without crashing ({e!r})", False)
    finally:
        shutil.rmtree(root, ignore_errors=True)
        shutil.rmtree(root2, ignore_errors=True)


def run_auto_git():
    """Spec 05 PRD 05.1 §E — refs, branches and worktrees.

    An attempt is a commit under `refs/crux/auto/<qid>/<hid>`, which is what lets the worktree
    go the moment the commit is recorded. The two failures this guards against are a ref that
    dies with its worktree — losing the run — and a branch layout git refuses halfway through,
    since a reference cannot also be a directory of references. `main` is checked after every
    single step rather than at the end: a run that moves the PI's branch and moves it back is
    still a run that moved it."""
    print("\n# autopilot — refs, branches and worktrees (spec 05, PRD 05.1)")
    repo = None
    try:
        A = _auto_mod()
        repo, root, qa, qi, hb, rel = _auto_repo()
        plan = _auto_val(lambda: E.load_flight_plan(root, rel), {})
        main0 = _git(repo, "rev-parse", "main")
        clean = []

        def snap(label):
            """`main`, HEAD and the main working tree, after one step. Vault writes and the
            workspace are by design — nothing else may appear."""
            clean.append((label, (
                _git(repo, "rev-parse", "main") == main0
                and _git(repo, "symbolic-ref", "HEAD") == "refs/heads/main"
                and _git(repo, "rev-parse", "HEAD") == main0
                and _git(repo, "status", "--porcelain", "--", ".", ":(exclude)cruxvault",
                         ":(exclude)work", ":(exclude)results") == "")))

        st = {}
        try:
            # Before anything is open: the only thing that tells `add_worktree` where to cut
            # from is the base ref, and in this fixture base, HEAD and `main` are the same
            # commit — so without this line "cut from base" is also satisfied by code that
            # never reads the ref at all.
            st["notopen"] = _auto_msg(lambda: A.add_worktree(root, plan, "h900"))
            st["info"] = A.open_run(root, plan); snap("open")
            st["reopen"] = _auto_msg(lambda: A.open_run(root, plan))
            st["base"] = _git(repo, "rev-parse", A.base_ref(qa))
            st["made"] = sorted(_git(repo, "for-each-ref", "--format=%(refname:short)",
                                     "refs/heads/crux/auto/").splitlines())
            h1 = A.reserve_id(root, qa, island=qi); st["h1"] = h1; snap("reserve")
            wt1 = A.add_worktree(root, plan, h1); st["wt1"] = wt1; snap("worktree")
            st["wt1_at"] = _git(wt1, "rev-parse", "HEAD")
            st["wt1_where"] = os.path.join(A.git_common_dir(repo), "crux-auto", qa, h1)
            write(os.path.join(wt1, "work_notes.txt"), "one\n")
            _git(wt1, "add", "-A"); _git(wt1, "commit", "-q", "-m", "attempt 1"); snap("commit")
            st["head1"] = _git(wt1, "rev-parse", "HEAD")
            st["sha1"] = A.record_attempt(root, plan, h1); snap("record")
            st["ref1"] = _git(repo, "rev-parse", A.attempt_ref(qa, h1))
            st["again"] = A.record_attempt(root, plan, h1)     # same sha: idempotent, not a refusal
            h2 = A.reserve_id(root, qa, island=qi, parent=h1); st["h2"] = h2
            st["wt2_at"] = _git(A.add_worktree(root, plan, h2, parent=h1), "rev-parse", "HEAD")
            h3 = A.reserve_id(root, qa, island=qi); st["h3"] = h3
            st["wt3_at"] = _git(A.add_worktree(root, plan, h3), "rev-parse", "HEAD")
            st["dup"] = _auto_msg(lambda: A.add_worktree(root, plan, h3))
            st["noparent"] = _auto_msg(lambda: A.add_worktree(root, plan, "h999", parent="h998"))
            A.make_workspace(root, plan, h1)
            A.write_manifest(root, plan, h1); snap("manifest")
            st["rm1"] = A.remove_worktree(root, plan, h1)
            st["rm1_gone"] = not os.path.isdir(wt1)
            st["ref1_after"] = _git(repo, "rev-parse", A.attempt_ref(qa, h1))
            st["rm_twice"] = A.remove_worktree(root, plan, h1)
            A.apply_retention(root, plan, h1); snap("retention")
            # "a directory is there" and "git holds a worktree there" come apart in both
            # directions, and a driver that treats either as the other loses a run: one way it
            # refuses to clean up, the other it reports a checkout nobody can open.
            stray = os.path.join(A.git_common_dir(repo), "crux-auto", qa, "h901")
            os.makedirs(stray)
            st["stray"] = A.remove_worktree(root, plan, "h901")
            st["stray_kept"] = os.path.isdir(stray)
            hv = A.reserve_id(root, qa, island=qi); st["hv"] = hv
            shutil.rmtree(A.add_worktree(root, plan, hv))   # deleted behind git's back
            st["listed"] = [w["id"] for w in A.auto_refs(root, qa)["worktrees"]]
            hn = _auto_attempt(root, qi, "the promoted attempt", score=0.70)
            wtn = A.add_worktree(root, plan, hn)
            write(os.path.join(wtn, "work_notes.txt"), "n\n")
            _git(wtn, "add", "-A"); _git(wtn, "commit", "-q", "-m", "attempt n")
            st["shan"] = A.record_attempt(root, plan, hn)
            A.remove_worktree(root, plan, hn)
            st["promo"] = A.promote(root, hn); snap("promote")
        except Exception as e:                               # pragma: no cover - wave-1 guard
            st["oops"] = repr(e)
        bs = _auto_val(lambda: [st["info"]["run_branch"]]
                       + list(st["info"]["island_branches"].values()), [])

        check("agit: record_attempt sets refs/crux/auto/<qid>/<hid> to the worktree HEAD and the ref survives worktree removal",
              _auto_ok(lambda: (
                  A.attempt_ref(qa, st["h1"]) == f"refs/crux/auto/{qa}/{st['h1']}"
                  and st["sha1"] == st["head1"] and st["ref1"] == st["head1"]
                  and st["head1"] != main0 and st["again"] == st["sha1"]
                  and st["rm1"] is True and st["rm1_gone"] and st["rm_twice"] is False
                  and st["ref1_after"] == st["sha1"])))
        check("agit: a worktree is cut from its parent attempt's commit, and an island's first from base",
              _auto_ok(lambda: (
                  st["wt1"] == st["wt1_where"] and st["wt1_at"] == main0
                  and st["wt2_at"] == st["sha1"] and st["wt3_at"] == main0
                  and st["base"] == main0
                  and f"auto run for {qa} is not open" in st["notopen"]
                  and f"refs/crux/auto/{qa}/base does not exist" in st["notopen"])))
        check("agit: a leftover directory is not a worktree, and one whose directory vanished is not listed",
              _auto_ok(lambda: (
                  st["stray"] is False and st["stray_kept"]
                  and st["hv"] not in st["listed"])))
        check("agit: add_worktree refuses a path already in use and a parent with no ref",
              _auto_ok(lambda: (
                  "already exists" in st["dup"]
                  and f"has no ref refs/crux/auto/{qa}/h998" in st["noparent"])))
        check("agit: open_run creates the run branch and one island branch per island at base, none a prefix-directory of another",
              _auto_ok(lambda: (
                  st["info"]["anchor"] == qa and st["info"]["base"] == main0
                  and os.path.realpath(st["info"]["repo"]) == repo
                  and st["info"]["run_branch"] == f"crux/auto/{qa}/run"
                  and set(st["info"]["island_branches"]) == {qi}
                  and st["info"]["island_branches"][qi] == f"crux/auto/{qa}/island/{qi}"
                  and _git(repo, "rev-parse", A.run_branch(qa)) == main0
                  and _git(repo, "rev-parse", A.island_branch(qa, qi)) == main0
                  and len(bs) == 2 and sorted(bs) == st["made"]
                  and not any(b != c and c.startswith(b + "/") for b in bs for c in bs)
                  and "already open" in st["reopen"])))
        check("agit: main and the main working tree are untouched across open, reserve, worktree, commit, record, manifest, retention and promote",
              _auto_ok(lambda: (
                  [l for l, _ in clean] == ["open", "reserve", "worktree", "commit", "record",
                                            "manifest", "retention", "promote"]
                  and all(o for _, o in clean)
                  and _git(repo, "rev-parse", "main") == main0
                  and _git(repo, "symbolic-ref", "HEAD") == "refs/heads/main")))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"agit: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_workspace():
    """Spec 05 PRD 05.1 §F, §G — the three path sets, and the manifest over the shared ones.

    Frozen paths and the manifest answer two halves of one question: what did this attempt
    touch that it had no business touching. Git answers it for tracked files; the manifest
    answers it for the scratch and dataset directories git cannot see. 05.1 only reports —
    the `invalid-run` close is 05.2's — so every assert here also checks that nothing closed."""
    print("\n# autopilot — frozen paths, workspace and manifest (spec 05, PRD 05.1)")
    repo = flat = None
    try:
        A = _auto_mod()
        repo, root, qa, qi, hb, rel = _auto_repo()
        plan = _auto_val(lambda: E.load_flight_plan(root, rel), {})
        main0 = _git(repo, "rev-parse", "main")

        # ------------------------------------------- criteria 16 and 17: the frozen path set
        st = {}
        try:
            A.open_run(root, plan)
            ho = _auto_attempt(root, qi, "the open attempt", close=False)
            st["node_before"] = read(node_path(root, ho))
            st["status_before"] = E.Vault(root).get(ho).status
            h1 = A.reserve_id(root, qa, island=qi)
            wt1 = A.add_worktree(root, plan, h1)
            write(os.path.join(wt1, "work_notes.txt"), "one\n")
            _git(wt1, "add", "-A"); _git(wt1, "commit", "-q", "-m", "attempt 1")
            sha1 = A.record_attempt(root, plan, h1)

            h2 = A.reserve_id(root, qa, island=qi, parent=h1)   # touches the PI's scorer
            wt2 = A.add_worktree(root, plan, h2, parent=h1)
            write(os.path.join(wt2, "score.py"), SCORE_PY + "# tuned\n")
            _git(wt2, "add", "-A"); _git(wt2, "commit", "-q", "-m", "touch the scorer")
            st["v_frozen"] = A.frozen_violations(root, plan, sha1, _git(wt2, "rev-parse", "HEAD"))

            h3 = A.reserve_id(root, qa, island=qi)              # touches its own notebook
            wt3 = A.add_worktree(root, plan, h3)
            vrel = os.path.relpath(node_path(root, hb), repo).replace(os.sep, "/")
            write(os.path.join(wt3, vrel), read(os.path.join(wt3, vrel)) + "\nedited\n")
            _git(wt3, "add", "-A"); _git(wt3, "commit", "-q", "-m", "touch the vault")
            st["vrel"] = vrel
            st["v_vault"] = A.frozen_violations(root, plan, main0, _git(wt3, "rev-parse", "HEAD"))

            h5 = A.reserve_id(root, qa, island=qi)              # renames the PI's scorer away
            wt5 = A.add_worktree(root, plan, h5)
            _git(wt5, "mv", "score.py", "scorer_renamed.py")
            _git(wt5, "commit", "-q", "-m", "rename the scorer")
            st["v_moved"] = A.frozen_violations(root, plan, main0,
                                                _git(wt5, "rev-parse", "HEAD"))

            h4 = A.reserve_id(root, qa, island=qi)              # touches only what it may
            wt4 = A.add_worktree(root, plan, h4)
            write(os.path.join(wt4, "train.py"), "print('train harder')\n")
            _git(wt4, "add", "-A"); _git(wt4, "commit", "-q", "-m", "train only")
            st["v_clean"] = A.frozen_violations(root, plan, main0, _git(wt4, "rev-parse", "HEAD"))

            st["eff"] = A.effective_frozen(root, plan)
            st["node_after"] = read(node_path(root, ho))
            st["status_after"] = E.Vault(root).get(ho).status
            st["verdict_after"] = E.Vault(root).get(ho)["fm"].get("verdict")
            st["rec"] = A.reservations(root, qa)
        except Exception as e:                               # pragma: no cover - wave-1 guard
            st["oops"] = repr(e)
        check("awork: a commit touching an effective frozen path is reported naming the path and the attempt stays open",
              _auto_ok(lambda: (
                  st["v_frozen"] == ["score.py"] and st["v_clean"] == []
                  and st["node_after"] == st["node_before"]
                  and st["status_after"] == st["status_before"]
                  and not st["verdict_after"]
                  and st["rec"] and all(r["state"] == "reserved" for r in st["rec"].values()))))
        check("awork: a frozen file moved away is reported under the frozen name, not the new one",
              _auto_ok(lambda: st["v_moved"] == ["score.py"]))
        check("awork: the vault's own path is frozen when it lies inside the repository",
              _auto_ok(lambda: (
                  st["eff"] == ["cruxvault", "data", "score.py"]
                  and st["v_vault"] == [st["vrel"]]
                  and st["vrel"].startswith("cruxvault/"))))

        # a vault that IS the repository has no separable notebook path to freeze
        flat = os.path.realpath(tempfile.mkdtemp(prefix="crux_aflat_"))
        _git(flat, "init", "-q")
        _git(flat, "symbolic-ref", "HEAD", "refs/heads/main")
        E.cmd_init("Flat", flat, goal="drive the held-out loss below the bar")
        qf, _ = E.cmd_ask(flat, "the anchor question")
        hf = _auto_attempt(flat, qf, "the baseline attempt", score=0.90)
        write(_plan_path(flat, qf), _plan_text(qf, hf))
        fplan = _auto_val(lambda: E.load_flight_plan(flat, f"auto/{qf}/plan.md"), {})
        check("awork: a vault that is the repository toplevel adds no vault path to the frozen set",
              _auto_ok(lambda: A.effective_frozen(flat, fplan) == ["data", "score.py"]))

        # ------------------------------------------------------ criterion 18: the manifest
        s2 = {}
        try:
            hm = A.reserve_id(root, qa, island=qi); s2["hm"] = hm
            ws = A.make_workspace(root, plan, hm); s2["ws"] = ws
            write(os.path.join(repo, "work", "other", "shared.txt"), "a")
            s2["paths"] = [f["path"] for f in A.write_manifest(root, plan, hm)["files"]]
            write(os.path.join(repo, "work", "other", "shared.txt"), "abcd")   # size, not mtime
            write(os.path.join(repo, "results", "new.csv"), "x")
            write(os.path.join(ws, "mine.txt"), "y")
            s2["r1"] = A.recheck_manifest(root, plan, hm)
            s2["r2"] = A.recheck_manifest(root, plan, hm)
            s2["doc"] = json.loads(read(A.manifest_path(root, qa, hm)))
            hu = A.reserve_id(root, qa, island=qi)             # untouched between the two walks
            A.make_workspace(root, plan, hu)
            A.write_manifest(root, plan, hu)
            s2["clean"] = A.recheck_manifest(root, plan, hu)
            s2["none"] = _auto_msg(lambda: A.recheck_manifest(root, plan, "h999"))
            os.makedirs(os.path.join(repo, "work", "target"))
            write(os.path.join(repo, "work", "target", "deep.txt"), "z")
            os.symlink(os.path.join(repo, "work", "target"), os.path.join(repo, "work", "link"))
            hs = A.reserve_id(root, qa, island=qi)
            A.make_workspace(root, plan, hs)
            s2["sym"] = [f["path"] for f in A.write_manifest(root, plan, hs)["files"]]
        except Exception as e:                               # pragma: no cover - wave-1 guard
            s2["oops"] = repr(e)
        check("awork: the manifest re-check reports added and changed under shared roots, nothing inside the workspace, clean when untouched",
              _auto_ok(lambda: (
                  "work/other/shared.txt" in s2["paths"]
                  and not any(p.startswith("work/%s/" % s2["hm"]) for p in s2["paths"])
                  and s2["r1"]["changed"] == ["work/other/shared.txt"]
                  and s2["r1"]["added"] == ["results/new.csv"]
                  and s2["r1"]["removed"] == []
                  # the recorded files are the BEFORE-picture and are never refreshed, so a
                  # second re-check over the same change reports the same change again
                  and {k: s2["r2"][k] for k in ("added", "removed", "changed")}
                  == {k: s2["r1"][k] for k in ("added", "removed", "changed")}
                  and s2["clean"]["added"] == [] and s2["clean"]["changed"] == []
                  and s2["clean"]["removed"] == []
                  and len(s2["doc"]["rechecks"]) == 2
                  and s2["doc"]["attempt"] == s2["hm"]
                  and s2["doc"]["workspace"] == "work/%s" % s2["hm"]
                  and s2["doc"]["excluded"] == ["work/%s" % s2["hm"]]
                  and s2["doc"]["roots"] == ["work", "results"])))
        check("awork: a symlink under a shared root is one entry and its target is not walked",
              _auto_ok(lambda: (
                  "work/link" in s2["sym"] and "work/target/deep.txt" in s2["sym"]
                  and "work/link/deep.txt" not in s2["sym"]
                  and "no manifest for h999" in s2["none"])))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"awork: section ran without crashing ({e!r})", False)
    finally:
        if flat:
            shutil.rmtree(flat, ignore_errors=True)
        _auto_sweep()


def run_auto_retention():
    """Spec 05 PRD 05.1 §G — retention spares the record.

    `retention:` decides what happens to a workspace that may hold sixty gigabytes of
    checkpoints. What it must never decide is whether the run can still be read afterwards, so
    the assert is as much about what survives — the ref, the node, the metrics file, the
    manifest — as about what goes. The worktree goes in every setting: it is a checkout, and
    the commit it held is already in a ref."""
    print("\n# autopilot — retention (spec 05, PRD 05.1)")
    repo = None
    try:
        A = _auto_mod()
        repo, root, qa, qi, hb, rel = _auto_repo()
        rows = []
        try:
            A.open_run(root, E.load_flight_plan(root, rel))
            for retention in ("none", "all", "failed"):
                write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi, retention=retention))
                plan = E.load_flight_plan(root, rel)
                for verdict, close in (("supported", True), ("refuted", True),
                                       ("invalid-run", True), ("supported", False)):
                    h = _auto_attempt(root, qi, f"the {retention} {verdict} attempt",
                                      score=0.70, verdict=verdict, close=close)
                    wt = A.add_worktree(root, plan, h)
                    ws = A.make_workspace(root, plan, h)
                    write(os.path.join(ws, "checkpoint.bin"), "0" * 16)
                    A.write_manifest(root, plan, h)
                    sha = A.record_attempt(root, plan, h)
                    res = A.apply_retention(root, plan, h)
                    got = E.Vault(root).get(h)["fm"].get("verdict") or None
                    rows.append({
                        "retention": retention, "verdict": got, "res": res,
                        "kept": os.path.isdir(ws), "worktree": os.path.isdir(wt),
                        "ref": _git(repo, "rev-parse", A.attempt_ref(qa, h), check=False),
                        "sha": sha, "node": os.path.isfile(node_path(root, h)),
                        "metrics": os.path.isfile(os.path.join(root, "results", h,
                                                               "metrics.json")),
                        "manifest": os.path.isfile(A.manifest_path(root, qa, h))})
        except Exception as e:                               # pragma: no cover - wave-1 guard
            rows.append({"oops": repr(e)})

        def _want(row):
            """The PRD's table: none deletes every workspace, all keeps every one, failed keeps
            what there is something to debug."""
            if row["retention"] == "none":
                return False
            if row["retention"] == "all":
                return True
            return row["verdict"] != "supported"

        check("aret: none deletes the workspace, all keeps it, failed keeps refuted and deletes supported; ref, node, metrics and manifest survive and no worktree remains",
              _auto_ok(lambda: (
                  len(rows) == 12
                  and {r["verdict"] for r in rows} == {"supported", "refuted", "invalid-run", None}
                  and all(r["kept"] is _want(r) for r in rows)
                  and all(r["res"]["retention"] == r["retention"] for r in rows)
                  and all(r["res"]["workspace_removed"] is (not _want(r)) for r in rows)
                  and all(r["res"]["worktree_removed"] is True for r in rows)
                  and all(r["res"]["verdict"] == r["verdict"] for r in rows)
                  and all(r["ref"] == r["sha"] for r in rows)
                  and all(r["node"] and r["metrics"] and r["manifest"] for r in rows)
                  and not any(r["worktree"] for r in rows))))
        bad = _auto_msg(lambda: A.apply_retention(
            root, dict(E.load_flight_plan(root, rel), retention="keep"), hb))
        check("aret: apply_retention refuses a retention value outside all, failed, none",
              "flight plan retention must be one of all, failed, none (got 'keep')" in bad)
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aret: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_scorer():
    """Spec 05 PRD 05.1 §B — the scorer prints one JSON object, and the driver writes it.

    The number that decides a verdict comes from the command's standard output, never from a
    file a worker could rewrite — so `metrics.json` is written by the driver, verbatim, and the
    engine only ever reads it. `auto check` is where a PI finds out the contract is broken
    before forty attempts run against it, which is why each of the four failures is named
    rather than reported as one 'the scorer did not work'."""
    print("\n# autopilot — the scorer contract (spec 05, PRD 05.1)")
    repo = bare = None
    try:
        A = _auto_mod()
        repo, root, qa, qi, hb, rel = _auto_repo()

        def checked(scorer="python3 score.py", **kw):
            """`auto check` over a plan rewritten with these fields — one defect per call, and
            a vault write rather than a repository one, so the repo stays the PI's."""
            write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi, scorer=scorer, **kw))
            return _auto_val(lambda: A.auto_check(root, rel), {})

        def names(res):
            return [p.get("check") for p in (res.get("problems") or [])] if isinstance(res, dict) else None

        def first(res):
            p = (res.get("problems") or []) if isinstance(res, dict) else []
            return p[0].get("message", "") if p and isinstance(p[0], dict) else ""

        r_exit = checked(scorer="python3 score_exit.py")
        r_start = checked(scorer="no_such_binary_crux score.py")
        r_noisy = checked(scorer="python3 score_noisy.py")
        t0 = time.monotonic()
        r_slow = checked(scorer="python3 score_slow.py", extra=(("scorer_timeout", "1"),))
        slow_s = time.monotonic() - t0
        r_text = checked(scorer="python3 score_text.py")
        r_two = checked(scorer="python3 score_two.py")
        r_num = checked(scorer="python3 score_num.py")
        r_noaddr = checked(scorer="python3 score_noaddr.py")
        r_str = checked(scorer="python3 score_str.py")
        r_ok = checked()
        results_now = sorted(_auto_val(lambda: os.listdir(os.path.join(root, "results")), []))

        check("ascore: check names scorer-exit with a bounded stderr tail when the scorer exits non-zero or cannot start",
              _auto_ok(lambda: (
                  names(r_exit) == ["scorer-exit"]
                  and "scorer exited 3" in first(r_exit)
                  and "boom: the dataset is missing" in first(r_exit)
                  and r_exit["ok"] is False and r_exit["scorer"]["ran"] is True
                  and names(r_start) == ["scorer-exit"]
                  and first(r_start).startswith("scorer cannot start:")
                  and names(r_noisy) == ["scorer-exit"]
                  and "tail-marker" in first(r_noisy)
                  and "head-marker" not in first(r_noisy)
                  and len(first(r_noisy)) <= 2600)))
        check("ascore: check names scorer-timeout when the scorer runs past scorer_timeout",
              _auto_ok(lambda: names(r_slow) == ["scorer-timeout"]
                       and "scorer_timeout 1s" in first(r_slow) and slow_s < 3))
        check("ascore: check names scorer-output when stdout is not exactly one JSON object",
              _auto_ok(lambda: (
                  names(r_text) == ["scorer-output"]
                  and "not one JSON object" in first(r_text) and "loss 0.8" in first(r_text)
                  and r_text["ok"] is False
                  and names(r_two) == ["scorer-output"]
                  and names(r_num) == ["scorer-output"])))
        check("ascore: check names scorer-address when the objective does not resolve to a number in the output",
              _auto_ok(lambda: (
                  names(r_noaddr) == ["scorer-address"]
                  and "objective 'eval.loss' does not resolve in the scorer's output"
                  in first(r_noaddr)
                  and r_noaddr["scorer"]["ran"] is True and r_noaddr["scorer"]["value"] is None
                  and names(r_str) == ["scorer-address"]
                  and "is not a number" in first(r_str))))
        check("ascore: check passes a plan whose scorer prints a metrics object the objective resolves in",
              _auto_ok(lambda: (
                  r_ok["ok"] is True and r_ok["problems"] == []
                  and os.path.realpath(r_ok["repo"]) == repo
                  and set(r_ok) >= {"ok", "plan", "anchor", "mode", "problems", "repo", "scorer"}
                  and r_ok["scorer"]["ran"] is True and r_ok["scorer"]["value"] == 0.8
                  and r_ok["scorer"]["cmd"] == "python3 score.py"
                  and os.path.realpath(r_ok["scorer"]["cwd"]) == repo
                  and r_ok["scorer"]["address"] == "eval.loss"
                  and isinstance(r_ok["scorer"]["seconds"], float)
                  and r_ok["scorer"]["seconds"] >= 0
                  and results_now == [hb])))              # a dry run writes nothing anywhere

        # The complement of criterion 5: `--static` starts nothing, and the bare verb starts the
        # scorer on purpose — that is the whole of what this slice added to `auto check`.
        spawn, s5 = [], {}
        saved = _auto_val(lambda: A._run)
        try:
            if saved is not None:
                def rec5(argv, *a, **k):
                    spawn.append(list(argv))
                    return saved(argv, *a, **k)
                A._run = rec5
            s5["live"] = _auto_val(lambda: A.auto_check(root, rel), {})
            s5["ran"] = list(spawn)
            del spawn[:]
            s5["static"] = _auto_val(lambda: A.auto_check(root, rel, static=True), {})
            s5["still"] = list(spawn)
        finally:
            if saved is not None:
                A._run = saved
        check("ascore: check without --static reaches the scorer, and with --static starts nothing",
              _auto_ok(lambda: (
                  any("score.py" in " ".join(a) for a in s5["ran"])
                  and s5["still"] == []
                  and set(s5["static"]) == {"ok", "plan", "anchor", "mode", "problems"})))

        # ------------------------------ criterion 6: no repository, and no git attempted after
        bare = tempfile.mkdtemp(prefix="crux_abare_")
        shutil.rmtree(bare); os.makedirs(bare)
        E.cmd_init("Autopilot", bare, goal="drive the held-out loss below the bar")
        qb, _ = E.cmd_ask(bare, "the anchor question")
        hbb = _auto_attempt(bare, qb, "the baseline attempt", score=0.90)
        brel = f"auto/{qb}/plan.md"
        write(_plan_path(bare, qb), _plan_text(qb, hbb, scorer="python3 score.py"))
        seen, s6 = [], {}
        saved_run = _auto_val(lambda: A._run)
        saved_ceiling = os.environ.get("GIT_CEILING_DIRECTORIES")
        try:
            if saved_run is not None:
                def rec(argv, *a, **k):
                    seen.append(list(argv))
                    return saved_run(argv, *a, **k)
                A._run = rec
            os.environ["GIT_CEILING_DIRECTORIES"] = os.path.dirname(os.path.realpath(bare))
            s6["res"] = _auto_val(lambda: A.auto_check(bare, brel), {})
        finally:
            if saved_run is not None:
                A._run = saved_run
            if saved_ceiling is None:
                os.environ.pop("GIT_CEILING_DIRECTORIES", None)
            else:
                os.environ["GIT_CEILING_DIRECTORIES"] = saved_ceiling
        check("ascore: check names repo when nothing encloses the vault and runs no git afterwards",
              _auto_ok(lambda: (
                  s6["res"]["ok"] is False
                  and [p["check"] for p in s6["res"]["problems"]] == ["repo"]
                  and "set repo: in the flight plan" in s6["res"]["problems"][0]["message"]
                  and s6["res"]["repo"] is None
                  and len(seen) == 1 and "rev-parse" in seen[0]
                  and not any("score" in " ".join(a) for a in seen))))

        # ------------------------- criterion 7: the two new fields are optional, and checked
        base_msgs = _plan_msgs(root, _plan_text(qa, hb, islands=qi), rel)
        empties = _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                              extra=(("repo", ""), ("scorer_timeout", ""))), rel)
        bad_t = _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                            extra=(("scorer_timeout", "soon"),)), rel)
        bad_z = _plan_msgs(root, _plan_text(qa, hb, islands=qi,
                                            extra=(("scorer_timeout", "0"),)), rel)
        bad_r = _plan_msgs(root, _plan_text(qa, hb, islands=qi, retention="keep"), rel)
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi, scorer="python3 score.py"))
        p05 = _auto_val(lambda: E.load_flight_plan(root, rel), {})
        check("ascore: a 05.0 plan without repo: or scorer_timeout: validates unchanged",
              _auto_ok(lambda: (
                  base_msgs == [] and empties == []
                  and p05["scorer_timeout"] == 600.0 and p05["repo"] is None
                  and p05["scorer"] == "python3 score.py" and p05["retention"] == "failed"
                  and sorted(p05["frozen"]) == ["data", "score.py"]
                  and p05["writable"] == ["work", "results"]
                  and bad_t == ["flight plan field 'scorer_timeout' must be a positive number (got 'soon')"]
                  and bad_z == ["flight plan field 'scorer_timeout' must be a positive number (got '0')"]
                  and bad_r == ["flight plan retention must be one of all, failed, none (got 'keep')"])))

        # -------------------------------- criterion 8: the driver writes, the engine reads
        s8 = {}
        try:
            plan = E.load_flight_plan(root, rel)
            A.open_run(root, plan)
            h = A.reserve_id(root, qa, island=qi); s8["h"] = h
            A.add_worktree(root, plan, h)
            s8["obj"] = A.score_attempt(root, plan, h)
            s8["file"] = json.loads(read(os.path.join(root, "results", h, "metrics.json")))
            s8["ws"] = A.workspace_path(root, plan, h)
            s8["nowt"] = _auto_msg(lambda: A.score_attempt(root, plan, "h999"))
        except Exception as e:                               # pragma: no cover - wave-1 guard
            s8["oops"] = repr(e)
        eng = "\n".join(l for l in read(os.path.join(HERE, "engine.py")).splitlines()
                        if not l.lstrip().startswith("#"))
        check("ascore: score_attempt writes the scorer's object verbatim to results/<hid>/metrics.json and engine.py never writes that path",
              _auto_ok(lambda: (
                  s8["file"] == s8["obj"]
                  and s8["obj"]["eval"]["loss"]["value"] == 0.80
                  and s8["obj"]["env"]["attempt"]["value"] == s8["h"]
                  and s8["obj"]["env"]["workspace"]["value"] == s8["ws"]
                  and "no worktree for h999" in s8["nowt"]
                  and not re.search(r"(write_if_changed|open)\([^\n]*(METRICS_FILE|metrics\.json)", eng)
                  and not re.search(r"(METRICS_FILE|metrics\.json)[^\n]*['\"]w['\"]", eng))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"ascore: section ran without crashing ({e!r})", False)
    finally:
        if bare:
            shutil.rmtree(bare, ignore_errors=True)
        _auto_sweep()


def run_auto_verbs():
    """Spec 05 PRD 05.1 §H — `crux auto promote` and `crux auto refs`.

    `promote` is the only new verb that writes, and everything it writes is a branch of the
    PI's choosing at a commit the run already recorded: no checkout, no merge, and `main`
    untouched. `refs` answers the one question a PI has after a run — what does this own right
    now — and answers it without creating so much as a directory."""
    print("\n# autopilot — promote, refs and the JSON surface (spec 05, PRD 05.1)")
    repo = tmp = None
    try:
        A = _auto_mod()
        repo, root, qa, qi, hb, rel = _auto_repo()
        plan = _auto_val(lambda: E.load_flight_plan(root, rel), {})
        main0 = _git(repo, "rev-parse", "main")

        def cli(*argv, **kw):
            return subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + list(argv),
                                  capture_output=True, cwd=kw.get("cwd") or root,
                                  encoding="utf-8", errors="replace")

        st = {}
        try:
            A.open_run(root, plan)
            h1 = _auto_attempt(root, qi, "the recorded attempt", score=0.70); st["h1"] = h1
            wt1 = A.add_worktree(root, plan, h1)
            write(os.path.join(wt1, "work_notes.txt"), "one\n")
            _git(wt1, "add", "-A"); _git(wt1, "commit", "-q", "-m", "attempt 1")
            st["sha1"] = A.record_attempt(root, plan, h1)
            A.remove_worktree(root, plan, h1)
            h0 = _auto_attempt(root, qi, "the unrecorded attempt", score=0.80); st["h0"] = h0
            st["wt0"] = A.add_worktree(root, plan, h0)        # a worktree with no recorded ref
        except Exception as e:                               # pragma: no cover - wave-1 guard
            st["oops"] = repr(e)

        p1 = cli("auto", "promote", st.get("h1", "h404"), "--json")
        p2 = cli("auto", "promote", st.get("h1", "h404"))
        p3 = cli("auto", "promote", st.get("h1", "h404"), "--branch", "keep/h1", "--json")
        p4 = cli("auto", "promote", "h99")
        p5 = cli("auto", "promote", st.get("h0", "h404"))
        p6 = cli("auto", "promote", qa)
        j1 = _auto_val(lambda: json.loads(p1.stdout), {})
        j3 = _auto_val(lambda: json.loads(p3.stdout), {})
        check("apromote: promote branches at the attempt ref and refuses an unknown id, an unrecorded id and a taken branch name",
              _auto_ok(lambda: (
                  p1.returncode == 0
                  and set(j1) == {"id", "anchor", "ref", "commit", "branch", "repo"}
                  and j1["id"] == st["h1"] and j1["anchor"] == qa
                  and j1["ref"] == "refs/crux/auto/%s/%s" % (qa, st["h1"])
                  and j1["commit"] == st["sha1"]
                  and j1["branch"] == "crux/auto/%s/promoted/%s" % (qa, st["h1"])
                  and _git(repo, "rev-parse", j1["branch"]) == st["sha1"]
                  and p2.returncode == 1
                  and p2.stderr.strip() == "crux: auto promote: branch 'crux/auto/%s/promoted/%s' already exists" % (qa, st["h1"])
                  and p3.returncode == 0 and j3["branch"] == "keep/h1"
                  and _git(repo, "rev-parse", "keep/h1") == st["sha1"]
                  and p4.returncode == 1 and p4.stderr.strip() == "crux: no node with id 'h99'"
                  and p5.returncode == 1 and "has no ref refs/crux/auto/" in p5.stderr
                  and _git(repo, "rev-parse", "main") == main0)))
        check("apromote: promote refuses a node that is not an attempt",
              _auto_ok(lambda: p6.returncode == 1 and "auto promote is per-attempt" in p6.stderr))

        r1 = cli("auto", "refs", "--json")
        r2 = cli("auto", "refs", qa)
        c1 = cli("auto", "check", rel, "--json")
        c2 = cli("auto", "check", rel, "--static", "--json")
        jr = _auto_val(lambda: json.loads(r1.stdout), {})
        jc = _auto_val(lambda: json.loads(c1.stdout), {})
        js = _auto_val(lambda: json.loads(c2.stdout), {})
        # §11 prints a branch without `refs/heads/` and nothing else: the FULL name, the way
        # `git branch --list` prints it, because the tail alone is not a name a PI can paste
        # into a git command.
        want = _auto_val(lambda: ["crux/auto/%s/run" % qa, "crux/auto/%s/island/%s" % (qa, qi),
                                  "crux/auto/%s/promoted/%s" % (qa, st["h1"])], [])
        check("acli: promote and refs emit JSON under --json, and check --json keeps every 05.0 key",
              _auto_ok(lambda: (
                  r1.returncode == 0
                  and set(jr) == {"anchor", "repo", "refs", "branches", "worktrees"}
                  and jr["anchor"] == qa and os.path.realpath(jr["repo"]) == repo
                  and all(set(x) == {"name", "id", "commit"} for x in jr["refs"])
                  and {x["id"] for x in jr["refs"]} >= {"base", st["h1"]}
                  and jr["refs"][0]["id"] == "base"
                  and bool(want) and {n["name"] for n in jr["branches"]} == set(want)
                  and jr["branches"][0]["name"] == "crux/auto/%s/run" % qa
                  and all(set(x) == {"name", "commit"} for x in jr["branches"])
                  and [x["id"] for x in jr["worktrees"]] == [st["h0"]]
                  and all(set(x) == {"id", "path", "commit"} for x in jr["worktrees"])
                  and os.path.realpath(jr["worktrees"][0]["path"]) == os.path.realpath(st["wt0"])
                  and r2.returncode == 0 and "refs/crux/auto/%s/" % qa in r2.stdout
                  and c1.returncode == 0
                  and set(jc) >= {"ok", "plan", "anchor", "mode", "problems", "repo", "scorer"}
                  and jc["ok"] is True and jc["scorer"]["ran"] is True
                  and jc["scorer"]["value"] == 0.8
                  and c2.returncode == 0
                  and set(js) == {"ok", "plan", "anchor", "mode", "problems"})))

        # Both verbs ACT on the plan rather than report on it, so both inherit the engine's own
        # field checks. What is asserted is the shape of the refusal: one line a PI can read,
        # the same line from both verbs, and nothing created on the way out.
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi,
                                               extra=(("scorer_timeout", "soon"),)))
        b1 = cli("auto", "refs", "--json")
        b2 = cli("auto", "promote", st.get("h1", "h404"), "--branch", "later/h1")
        write(_plan_path(root, qa), _plan_text(qa, hb, islands=qi))
        want_msg = ("crux: flight plan field 'scorer_timeout' must be a positive number "
                    "(got 'soon')")
        check("acli: refs and promote refuse a flight plan whose field will not parse, with one line and no traceback",
              _auto_ok(lambda: (
                  b1.returncode == 1 and b2.returncode == 1
                  and b1.stderr.strip() == want_msg and b2.stderr.strip() == want_msg
                  and "Traceback" not in b1.stderr and "Traceback" not in b2.stderr
                  and _git(repo, "branch", "--list", "later/h1") == "")))

        # ------------------------- criterion 24: a vault written before any of this still loads
        tmp = tempfile.mkdtemp(prefix="crux_anoauto_")
        dst = os.path.join(tmp, "demo")
        shutil.copytree(os.path.join(REPO, "skills", "crux", "examples", "demo_vault"), dst)
        runs = [cli("status", cwd=dst), cli("validate", "--json", cwd=dst),
                cli("review", cwd=dst), cli("status", "--json", cwd=dst)]
        vj = _auto_val(lambda: json.loads(runs[1].stdout), {})
        norefs = cli("auto", "refs", cwd=dst)
        check("acli: a vault with no auto/ directory loads, validates and renders unchanged, drift warning aside",
              _auto_ok(lambda: (
                  all(r.returncode == 0 for r in runs)
                  and all("engine drift" in l for r in runs for l in r.stderr.splitlines()
                          if l.strip())
                  and set(vj) >= {"ok", "problems"}
                  and not any(s in runs[1].stdout for s in ("auto/", ".lock", "reserved"))
                  and norefs.returncode == 1
                  and norefs.stderr.strip()
                  == "crux: auto refs: no flight plan in this vault (auto/<qid>/plan.md)"
                  and not os.path.isdir(os.path.join(dst, "auto")))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"acli: section ran without crashing ({e!r})", False)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        _auto_sweep()


def run_auto_purity():
    """Spec 05 PRD 05.1, D19 — the line between the engine and the driver.

    The engine is the part a reader has to be able to trust by reading it: no process, no
    network, no clock-dependent branch. That is a property of the source text, so it is checked
    as source text rather than by hoping no test happens to spawn anything. The import
    direction is one-way — `autopilot` imports `engine`, never the reverse — and `crux.py`
    imports `autopilot` inside the function that needs it, so the verbs that start nothing
    never load the module that can."""
    print("\n# autopilot — the purity line (spec 05, PRD 05.1)")
    try:
        eng = "\n".join(l for l in read(os.path.join(HERE, "engine.py")).splitlines()
                        if not l.lstrip().startswith("#"))
        ap = os.path.join(HERE, "autopilot.py")
        auto = read(ap) if os.path.isfile(ap) else ""
        allowed = {"os", "sys", "re", "json", "time", "shlex", "socket", "subprocess", "shutil",
                   "tempfile", "datetime", "contextlib", "errno", "stat", "ctypes", "signal",
                   "engine"}
        imports = [m.group(1).split(".")[0] for m in
                   re.finditer(r"^\s*(?:import|from)\s+([\w.]+)", auto, re.M)]
        cl = read(os.path.join(HERE, "crux.py")).splitlines()
        lazy = [l for l in cl if re.match(r"\s*import autopilot\b", l)]
        check("apure: engine.py imports nothing impure and names no git command; autopilot.py imports only stdlib and engine; engine never imports autopilot",
              not re.search(r"^\s*(import|from)\s+(subprocess|threading|socket|urllib|fcntl|"
                            r"multiprocessing|asyncio|signal)\b", eng, re.M)
              and not re.search(r"\bos\.(system|popen|fork|exec\w*|spawn\w*|posix_spawn\w*)\s*\(",
                                eng)
              and not re.search(r"""["']git["']""", eng)
              and not re.search(r"^\s*(import|from)\s+autopilot\b", eng, re.M)
              and os.path.isfile(ap)
              and bool(re.search(r"^import engine as E", auto, re.M))
              and bool(imports) and all(x in allowed for x in imports)
              and bool(lazy) and all(l.lstrip() != l for l in lazy)
              and not any(re.match(r"^import subprocess\b", l) for l in cl))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"apure: section ran without crashing ({e!r})", False)


# --------------------------------------------------- 05.2: the driver loop, fixtures and golden
# Everything from here to `run_cli_help` was written against PRD 05.2 and that slice's interface
# contract ALONE — `auto_run`, the ledger, the comparison grammar and the approval hash did not
# exist when these asserts were written. That is the point of writing them first: a test with the
# implementation in front of it asserts what the code does, and the only question worth asking is
# whether the code does what was asked for.

# The node a hypothesis closed BY HAND leaves, captured from the engine as it stood BEFORE 05.2.
# Stored as lines rather than one triple-quoted block because three frontmatter lines end in a
# space, and an editor that strips trailing whitespace would move the golden silently.
HAND_CLOSE_GOLDEN = "\n".join((
    '---',
    'id: h1',
    'type: idea',
    'schema: 2',
    'title: x = 3',
    'parent: q1',
    'status: done',
    'rule: all',
    'measurement: ',
    'replicates: ',
    'verdict: supported',
    'metric: ',
    'created: "2026-01-01T00:00:00"',
    'updated: "2026-01-01T00:00:00"',
    'null_approved: "2026-01-01T00:00:00"',
    'null_hash: f286200254531a1e',
    'lock: c4befb40dbab3840',
    'locked: "2026-01-01T00:00:00"',
    'lock_at: running',
    '---',
    '',
    '# h1 — x = 3',
    '',
    'Parent:: [[q1_does_x_reach_3]]',
    '',
    '## ELI5',
    '',
    '_(one sentence, plain language, no jargon)_',
    '',
    '## TL;DR',
    '',
    '_(one paragraph: what this claims, and what would settle it)_',
    '',
    '## Null',
    'chance — seed noise alone lifts the score past the bar',
    '',
    '## Problem Statement',
    '',
    '_(why this is worth testing)_',
    '',
    '## Idea / Hypothesis',
    '',
    'x = 3',
    '',
    '## Verifiables',
    '',
    '<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->',
    '- [x] obj.score >= -0.5 on the frozen scorer (found: 0.0)',
    '      fails-if:: x stays two or more steps away from 3',
    '      discriminates:: true',
    '- [x] [outcome-neutral] obj.score <= 0 — the objective is never positive (found: 0.0)',
    '      fails-if:: the scorer adds a positive offset',
    '',
    '## Planned Intervention',
    '',
    '_(how this hypothesis will be tested)_',
    '',
    '## Run Links',
    '',
    '_(none yet)_',
    '',
    '## Artifacts',
    '',
    '<!-- what the run produced. Keep files under results/h1/ and link at least the report:',
    '     - [Report](results/h1/report.md)   - results/h1/curve.png -->',
    '_(none yet)_',
    '',
    '## Findings',
    '',
    'closed by hand',
    '',
))

# The leash, pinned byte-for-byte at the commit 05.2 branched from. 05.2 is the slice that first
# lets a machine close a hypothesis, so the four bullets that say a human decides are exactly the
# text most at risk of being softened while nobody is looking — and a softened bullet would pass
# every other check in this suite.
LEASH_BULLETS = "\n".join((
    '- **Read-only / bookkeeping** (`status`, `review`, `validate`, `test --to staged`): act',
    '  without asking, and say what it means for the science rather than that you ran it.',
    '- **Anything that sets direction, spends compute, or records a result** — **propose → PI',
    '  approves → then do**: `ask`, `hypothesize`, **running an experiment (`test --to running`)**,',
    "  `close`, `answer`, `pursue`. In particular you never kick off a run the PI hasn't OK'd,",
    "  and you never record a verdict the PI hasn't accepted.",
    '- **Taskhub**: ordinary task bookkeeping is silent; **completing an experiment is PI-gated**',
    '  (`crux task accept`) because its output is evidence. See *The taskhub* above.',
    "- **`review` gate + `synthesize` → `approve` → `answer`**: always the PI's. Surface the",
    '  gate, draft the synthesis, then stop — `approve` is their signature, not yours.',
))
CLOSE_ROW = ('| `close` | ◆ | derives the verdict from your ticks — never tick a box the evidence '
             'does not support |')


# ------------------------------------------------------------------------------- tier zero
# The whole experiment is one number in `params.json`. The scorer reports `-(x - 3)**2` with a
# seeded jitter below a millionth, so the objective is deterministic per seed, never positive, and
# improved only by moving x toward 3 — which is what the stub agent does. A full search therefore
# runs in seconds, and every invariant the PRD promises (a crash closes `invalid-run`, a killed run
# resumes, `main` is never written) is provable here rather than argued.
LOOP_SCORE_PY = '''import json, os, random, sys
if "--fail-always" in sys.argv:
    sys.stderr.write("scorer broken on purpose\\n")
    sys.exit(4)
if os.path.exists("crash_scorer"):
    sys.stderr.write("scorer crashed on purpose\\n")
    sys.exit(3)
with open("params.json", encoding="utf-8") as f:
    x = json.load(f)["x"]
seed = int(os.environ.get("CRUX_SEED") or 0)
tiny = random.Random(seed).random() * 1e-6
value = -(x - 3) ** 2 - tiny
if "--miss-confirm" in sys.argv and seed != 0:
    value = -9.0 - tiny
print(json.dumps({"obj": {"score": {"value": value}}}))
'''

# The stub worker. `mode` is the single argument the plan's `agent:` carries, and each mode breaks
# exactly one clause of the worker contract — so every refusal below has a witness that differs
# from the working case in one thing only.
LOOP_AGENT_PY = '''import json, os, subprocess, sys
mode = sys.argv[1] if len(sys.argv) > 1 else "step"
GIT = ["git", "-c", "user.name=crux-stub", "-c", "user.email=stub@crux.invalid",
       "-c", "commit.gpgsign=false", "-c", "core.hooksPath="]
with open(os.environ["CRUX_BRIEF"], encoding="utf-8") as f:
    if "## Objective" not in f.read():
        sys.exit(7)
if mode == "exit1":
    sys.stderr.write("stub failed on purpose\\n")
    sys.exit(1)
with open("params.json", encoding="utf-8") as f:
    x = json.load(f)["x"]
if mode != "still":
    x = x + (1 if x < 3 else (-1 if x > 3 else 0))
with open("params.json", "w", encoding="utf-8") as f:
    json.dump({"x": x}, f)
if mode == "frozen":
    with open("score.py", "a", encoding="utf-8") as f:
        f.write("\\n# touched by the worker\\n")
if mode == "shared":
    shared = os.path.join(os.path.dirname(os.environ["CRUX_WORKSPACE"]), "shared")
    os.makedirs(shared, exist_ok=True)
    with open(os.path.join(shared, "x"), "a", encoding="utf-8") as f:
        f.write(os.environ["CRUX_ATTEMPT"] + "\\n")
if mode == "crashscore":
    with open("crash_scorer", "w", encoding="utf-8") as f:
        f.write("1\\n")
subprocess.run(GIT + ["add", "-A"], check=True)
subprocess.run(GIT + ["commit", "-q", "--allow-empty", "-m", "attempt " + os.environ["CRUX_ATTEMPT"]], check=True)
proposal = {"claim": "x = %s" % x}
if mode == "longclaim":
    proposal["claim"] = " ".join(["word"] * 401)
if mode == "extrakey":
    proposal["verdict"] = "supported"
if mode == "taggedcontrol":
    proposal["controls"] = [{"text": "[hypothesis] obj.score <= 1 the value stays small", "fails_if": "the scorer drifts upward"}]
if mode == "control":
    proposal["controls"] = [{"text": "obj.score <= 1 — the value stays at most one", "fails_if": "the scorer drifts upward"}]
with open(os.environ["CRUX_PROPOSAL"], "w", encoding="utf-8") as f:
    json.dump(proposal, f)
'''

LOOP_NULL = "chance — seed noise alone lifts the score past the bar"
LOOP_GOAL = "x can be moved to the optimum of the frozen objective"
LOOP_VERIFIABLES = ("- [ ] obj.score >= -0.5 on the frozen scorer\n"
                    "      fails-if:: x stays two or more steps away from 3\n"
                    "      discriminates:: true\n"
                    "- [ ] [outcome-neutral] obj.score <= 0 — the objective is never positive\n"
                    "      fails-if:: the scorer adds a positive offset\n")

# Every tier-zero plan field, so each fixture below names only what it changes. A variant that has
# to restate nineteen fields to change one is a variant nobody can read.
LOOP_PLAN = dict(mode="climb", island_cap="3", budget_attempts="8", budget_hours="1",
                 budget_model_calls="40", parallel_total="1", parallel_island="1", retries="1",
                 retention="failed", scorer="python3 score.py", run="python3 train.py",
                 frozen="score.py", writable="work/", agent="python3 agent.py step",
                 steward="false", stall_attempts="2", abort_invalid_runs="2",
                 replicates="2 seeds", rule="all")


def _loop_name_main(repo):
    """Make sure the fixture repository is on `main`, spending a subprocess only if it is not.

    `init.defaultBranch=main` is pinned in GIT_ID, so a git new enough to honour it has already
    named the branch and `.git/HEAD` — a file read, not a process — says so. The explicit
    `symbolic-ref` stays for a git that ignores the setting, because a machine whose git names
    the branch `master` is not the subject of any test here."""
    head = os.path.join(repo, ".git", "HEAD")
    try:
        named = read(head).strip() == "ref: refs/heads/main"
    except (IOError, OSError):
        named = False
    if not named:
        _git(repo, "symbolic-ref", "HEAD", "refs/heads/main")


def _loop_rmtree(path):
    """`shutil.rmtree` that survives a git object directory.

    git writes its loose objects read-only, and on Windows a read-only file cannot be unlinked —
    so the obvious `rmtree` leaves a fixture repository behind on exactly the platform where a
    leftover temp directory is hardest to notice."""
    def retry(fn, p, _exc):
        try:
            os.chmod(p, 0o700)
            fn(p)
        except OSError:
            pass
    shutil.rmtree(path, onerror=retry)


# The four 05.3 fields the 05.0 template never carried. `_plan_text` builds its frontmatter from
# `_plan_fm`'s rows and silently DROPS any `**fm` key that list lacks, so `closer=`,
# `agent_cooldown=`, `agent_probe=` and `agent_probe_timeout=` never reached a plan on disk.
# They travel as `extra` rows instead, and only when a caller names one — so a plan that mentions
# none of them is byte-identical to the 05.2 text.
_LOOP_EXTRA_FIELDS = ("closer", "agent_cooldown", "agent_probe", "agent_probe_timeout")


def _loop_plan_text(qa, hb, isl=(), verifiables=None, **plan):
    """The tier-zero flight plan as text, for the checks that want a plan and no repository."""
    fields = dict(LOOP_PLAN)
    fields.update(plan)
    extra = [("scorer_timeout", "20")]
    extra += [(k, fields.pop(k)) for k in _LOOP_EXTRA_FIELDS if k in fields]
    return _plan_text(qa, hb, islands=", ".join(isl), goal=LOOP_GOAL, address="obj.score",
                      direction="max", bar="-0.5", null=LOOP_NULL,
                      verifiables=LOOP_VERIFIABLES if verifiables is None else verifiables,
                      extra=tuple(extra), **fields)


def _loop_write_plan(root, qa, hb, name="plan.md", **kw):
    """Write a tier-zero plan into the vault and return its vault-relative path."""
    rel = f"{E.AUTO_DIR}/{qa}/{name}"
    write(os.path.join(root, E.AUTO_DIR, qa, name), _loop_plan_text(qa, hb, **kw))
    return rel


def _loop_load_plan(root, qa):
    """The plan on disk as the driver will read it, or None while `load_flight_plan` refuses."""
    return _auto_val(lambda: E.load_flight_plan(root, f"{E.AUTO_DIR}/{qa}/plan.md"))


def _loop_repo(x0=0, islands=0, **plan):
    """A tier-zero repository with an approved flight plan on it.
    Returns (repo, root, qa, isl, hb, rel).

    `x0` is where the search starts — the baseline scores `-(x0 - 3)**2`, so `x0=0` is three steps
    from the optimum and `x0=2` is one. `islands` is how many island questions hang under the
    anchor; zero means the anchor is its own island, which is the ordinary Climb shape. `**plan`
    overrides any flight-plan field, and `_approve=False` leaves the plan unsigned.

    The baseline is closed BY HAND — `cmd_approve_null`, `cmd_test --to running`, the ticks, then
    `cmd_close` — because the thing under test is the driver doing exactly that, and a fixture
    built with the code it is testing proves nothing."""
    approve = plan.pop("_approve", True)
    verifiables = plan.pop("verifiables", None)
    # `_files` is written into the repository BEFORE the one commit this builder makes, so a
    # caller that needs its own programs committed does not have to add a second add/commit
    # pair. Two git subprocesses per fixture, across every fixture in the suite, is real wall.
    extra_files = plan.pop("_files", None) or {}
    repo = os.path.realpath(tempfile.mkdtemp(prefix="crux_aloop_"))
    _AUTO_TRASH.append(repo)                     # registered BEFORE anything can raise
    _git(repo, "init", "-q")
    _loop_name_main(repo)
    write(os.path.join(repo, "score.py"), LOOP_SCORE_PY)
    write(os.path.join(repo, "agent.py"), LOOP_AGENT_PY)
    write(os.path.join(repo, "train.py"), "print('train')\n")
    write(os.path.join(repo, "params.json"), json.dumps({"x": x0}))
    root = os.path.join(repo, "cruxvault")
    E.cmd_init("Tier zero", root, goal=LOOP_GOAL)
    qa, _ = E.cmd_ask(root, "can x reach the optimum")
    isl = [E.cmd_ask(root, f"island {k}", parent=qa)[0] for k in "ab"[:islands]]
    hb, _, _ = E.cmd_hypothesize(
        root, f"x = {x0}", parent=qa, rule="all", null=LOOP_NULL,
        verifiables=["obj.score >= -0.5 on the frozen scorer"],
        neutral=["obj.score <= 0 — the objective is never positive"],
        fails_if=["x stays two or more steps away from 3",
                  "the scorer adds a positive offset"],
        discriminates=[True, False])
    base = -(x0 - 3) ** 2
    write(os.path.join(root, E.RESULTS_DIR, hb, E.METRICS_FILE),
          json.dumps({"obj": {"score": {"value": base}}}))
    E.cmd_approve_null(root, hb)
    E.cmd_test(root, hb, to="running")
    p = node_path(root, hb)
    edit(p, "- [ ] [outcome-neutral]", "- [x] [outcome-neutral]")
    if base >= -0.5:
        edit(p, "- [ ] obj.score >= -0.5", "- [x] obj.score >= -0.5")
    E.cmd_close(root, hb, findings="the baseline, closed by hand before any run")
    rel = _loop_write_plan(root, qa, hb, isl=isl, verifiables=verifiables, **plan)
    if approve:
        E.cmd_auto_approve(root, rel)
    for name, text in extra_files.items():
        write(os.path.join(repo, name), text)
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "initial")
    return repo, root, qa, isl, hb, rel


def _loop_fixture(**kw):
    """`_loop_repo(**kw)`, or six Nones when building it raises.

    The builder signs the plan with `crux auto approve`, a verb that did not exist when this was
    written — so in wave one every build fails, and every criterion that needed a fixture has to
    fail on its own line rather than take the whole section down with it."""
    return _auto_val(lambda: _loop_repo(**kw), (None, None, None, None, None, None))


def _loop_copy(fx):
    """A byte copy of an already-built tier-zero repository, as a fresh 6-tuple.

    `cmd_init` plus `git init` plus a hand-closed baseline cost more than a whole tier-zero search
    does, so a section that wants the same fixture six times builds it once. Copied BEFORE any
    run, so no worktree, lock, reservation or ref is ever copied along with it."""
    repo, root, qa, isl, hb, rel = fx
    if not repo:
        return fx
    dst = os.path.realpath(tempfile.mkdtemp(prefix="crux_aloop_"))
    _AUTO_TRASH.append(dst)
    _loop_rmtree(dst)
    shutil.copytree(repo, dst, symlinks=True)
    return dst, os.path.join(dst, os.path.relpath(root, repo)), qa, isl, hb, rel


_LOOP_RUNS = {}          # fixture name -> everything one `auto run` left behind
_LOOP_CLOSED = []        # (attempt id, the verdict on the node, the verdict the engine derives)


def _loop_state_path(root, qa):
    # "" for a fixture that was never built, so a wave-1 section reports every criterion
    # rather than dying on the first os.path.join(None, ...)
    return os.path.join(root, E.AUTO_DIR, qa, E.AUTO_STATE_FILE) if root and qa else ""


def _loop_ledger_path(root, qa):
    return os.path.join(root, E.AUTO_DIR, qa, E.AUTO_LEDGER_FILE) if root and qa else ""


def _loop_note_verdicts(root, ids):
    """Remember, for every closed attempt, what its file says the verdict is and what the engine's
    own truth table says about the same ticks.

    Captured here rather than at the end of the suite because the section that built the fixture
    deletes it, and the criterion that compares the two is asserted after every fixture is gone."""
    for hid in (ids or ()) if root else ():
        n = _auto_val(lambda h=hid: E.Vault(root).get(h))
        if not n:
            continue
        by = _auto_val(lambda: E.count_verifiables_by_kind(n["body"]), {})
        want = _auto_val(lambda: E.derive_verdict_15(by[E.DEFAULT_KIND], by[E.NEUTRAL_KIND],
                                                     *E.node_rule(n)))
        _LOOP_CLOSED.append((hid, n["fm"].get("verdict"), want))


def _loop_run(name, root, qa, rel, **kw):
    """One `auto run`, and everything it left on disk: the state it returned, the state file, the
    ledger's parsed events, and the refusal when it refused.

    Every criterion below reads this dict rather than starting the driver again. A tier-zero search
    is cheap but not free, and two sections asking the same question of two different runs are not
    asking the same question."""
    A = _auto_mod()
    out = {"name": name, "root": root, "anchor": qa, "error": "", "returned": None,
           "state": None, "events": [], "raw": ""}
    if not root:                                             # pragma: no cover - wave-1 guard
        out["error"] = "<no fixture: the plan could not be built or signed>"
        _LOOP_RUNS[name] = out
        return out
    try:
        out["returned"] = A.auto_run(root, rel, **kw)
    except E.CruxError as e:
        out["error"] = str(e)
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        out["error"] = f"<not implemented: {e!r}>"
    out["state"] = _auto_val(lambda: json.loads(read(_loop_state_path(root, qa))))
    lp = _loop_ledger_path(root, qa)
    if os.path.isfile(lp):
        out["raw"] = read(lp)
        for line in out["raw"].splitlines():
            ev = _auto_val(lambda l=line: json.loads(l))
            if isinstance(ev, dict):
                out["events"].append(ev)
    _LOOP_RUNS[name] = out
    _loop_note_verdicts(root, (out["state"] or {}).get("closed") or [])
    return out


def _ev(run, event):
    """Every ledger event of one kind, in the order the driver appended them."""
    return [e for e in (run or {}).get("events", []) if e.get("event") == event]


def _loop_stop(run):
    return ((run or {}).get("state") or {}).get("stop") or {}


def _since_resume(run):
    """Only the events the LAST resume appended. `ledger.jsonl` is append-only across runs, so
    a resumed run's file still opens with everything the driver that died wrote."""
    evs = (run or {}).get("events", [])
    for i in range(len(evs) - 1, -1, -1):
        if evs[i].get("event") == "resumed":
            return {"events": evs[i:]}
    return {"events": list(evs)}


def _loop_untouched(repo, root, qa):
    """Nothing on disk from a refused run — no state, no ledger, no reservation, no base ref.

    The whole weight of "before any reservation" is here: a refusal that had already reserved an id
    would have burned a hypothesis number that can never be handed out again."""
    if not repo or not root:                                 # pragma: no cover - wave-1 guard
        return False
    d = os.path.join(root, E.AUTO_DIR, qa)
    res = _auto_val(lambda: _auto_mod().reserved_path(root, qa),
                    os.path.join(d, "reserved.json"))
    return (not os.path.exists(os.path.join(d, E.AUTO_STATE_FILE))
            and not os.path.exists(os.path.join(d, E.AUTO_LEDGER_FILE))
            and not os.path.exists(res)
            and _git(repo, "rev-parse", "--verify", "--quiet",
                     f"refs/crux/auto/{qa}/base", check=False) == "")


def _loop_lock_free(A, root):
    """True when the vault's one lock can be taken right now — so an `auto run` that died did
    not die holding it."""
    A.acquire_lock(root, "probe", wait=0.3)
    A.release_lock(root)
    return True


# Everything in a brief that a search legitimately moves. `budget.attempts.used` counts the
# attempts under the anchor, and `migration` reports every other island's best — both are what
# a run produces, and neither says anything about whether `island=None` still behaves as 05.0.
_BRIEF_MOVES = ("budget", "migration")


def _brief_fixed(payload):
    return {k: v for k, v in (payload or {}).items() if k not in _BRIEF_MOVES}


# The same, plus what a finished RUN changes by definition. A 05.3 compat check compares a run's
# brief against the same call on a byte copy the driver never touched, so the island's best
# attempt, the refuted list and the inspirations drawn out of them necessarily differ — moving
# them is the whole purpose of the search. 05.2's own `island=None` check compares two briefs
# that agree on all three, so it keeps the narrower list above and loses nothing.
_BRIEF_RUN_MOVES = _BRIEF_MOVES + ("best", "refuted", "inspirations")


def _brief_fixed_run(payload):
    return {k: v for k, v in (payload or {}).items() if k not in _BRIEF_RUN_MOVES}


def _skip_first_materialize(A):
    """Drop the FIRST `materialized` reservation write a run makes, exactly as a kill landing
    between the node-filed write and that out-of-lock call would. Returns (restore, skipped).

    §2 pins `materialized` right after filing, and no resume rule re-enters the filing step
    once the node exists — so unless a later step sets it again, one unlucky kill leaves a
    closed attempt reading `reserved` for good."""
    orig = _auto_val(lambda: A.set_reservation_state)
    skipped = []
    if orig is None:                                         # pragma: no cover - wave-1 guard
        return (lambda: None), skipped

    def patched(root, qid, hid, state):
        if state == "materialized" and not skipped:
            skipped.append(hid)
            return {"state": state}
        return orig(root, qid, hid, state)

    A.set_reservation_state = patched

    def restore():
        A.set_reservation_state = orig
    return restore, skipped


# §2's three nested records inside state.json. Spelled out here rather than derived from the
# implementation: a key set a test reads back off the object it is checking asserts nothing.
_ISLAND_KEYS = {"branch", "pointer", "best", "best_score", "seen_score", "stall"}
_BEST_KEYS = {"id", "score"}
_IN_FLIGHT_KEYS = {"island", "parent", "from", "phase", "worker_tries", "scorer_tries",
                   "pid", "failure", "started"}


def _record_probe(A, root, qa):
    """Watch `autopilot._record`, so the state and the ledger are inspected after EVERY event
    rather than once at the end. Returns (restore, findings).

    A run that leaves a well-formed `state.json` at its stop says nothing about the twenty moments
    in between — and those are the moments a crash actually lands in. `findings` is the list of
    what was not true, each line tagged with the criterion it belongs to, so the assert is on an
    empty list rather than on a boolean nobody can debug."""
    bad, prev = [], {"raw": b""}
    orig = _auto_val(lambda: A._record)
    if orig is None:
        return (lambda: None), bad
    sp, lp = _loop_state_path(root, qa), _loop_ledger_path(root, qa)

    def look():
        st = json.loads(read(sp))                            # parses, after every event
        if set(st) != set(E.AUTO_STATE_KEYS):
            bad.append(f"state: keys {sorted(set(st) ^ set(E.AUTO_STATE_KEYS))}")
        # the three nested records §2 pins, checked WHILE they exist: `in_flight` is empty by
        # the time the run stops, so the stop's own state file can say nothing about its shape
        for i, rec in (st.get("islands") or {}).items():
            if set(rec) != _ISLAND_KEYS:
                bad.append(f"state: islands[{i}] keys {sorted(set(rec) ^ _ISLAND_KEYS)}")
        if set(st.get("best") or {}) != _BEST_KEYS:
            bad.append(f"state: best keys {sorted(set(st.get('best') or {}) ^ _BEST_KEYS)}")
        for hid, rec in (st.get("in_flight") or {}).items():
            if set(rec) != _IN_FLIGHT_KEYS:
                bad.append(f"state: in_flight[{hid}] keys "
                           f"{sorted(set(rec) ^ _IN_FLIGHT_KEYS)}")
        raw = b""
        if os.path.isfile(lp):
            with open(lp, "rb") as fh:
                raw = fh.read()
        if not raw.startswith(prev["raw"]):                  # append-only, byte for byte
            bad.append("ledger: an earlier line changed")
        prev["raw"] = raw
        lines = [json.loads(l) for l in raw.decode("utf-8", "replace").splitlines()
                 if l.strip().startswith("{")]
        if st.get("events") != len(lines):
            bad.append(f"state: events {st.get('events')} for {len(lines)} ledger lines")
        for ev in lines:
            if ev.get("event") not in E.AUTO_LEDGER_EVENTS:
                bad.append(f"ledger: '{ev.get('event')}' is not a ledger event")
        for nid, nd in E.Vault(root).nodes.items():          # nothing left proposed and unrun
            if nd.type == "idea" and nd.status == "idea":
                bad.append(f"unrun: {nid} is still an idea between events")

    def probe(ctx, event, fields, work=None):
        out = orig(ctx, event, fields, work=work)
        try:
            look()
        except Exception as e:                               # pragma: no cover - wave-1 guard
            bad.append(f"state: probe could not read what {event} wrote ({e!r})")
        return out

    A._record = probe

    def restore():
        A._record = orig
    return restore, bad


def run_auto_grammar():
    """Spec 05 PRD 05.2 §1.2/§1.3 — the comparison grammar and the tick vector.

    This bounds what the driver is allowed to conclude from a number. A check written as prose
    cannot be ticked by a machine without the machine deciding what the prose meant, so the plan
    refuses prose at the moment it is written and every check in a run is a comparison the engine
    can evaluate. The tick is then arithmetic, the `(found: …)` note is the evidence, and neither
    may move the lock hash — a ticked box is not a re-registration."""
    print("\n# autopilot — the comparison grammar and the ticks (spec 05, PRD 05.2)")
    root = os.path.realpath(tempfile.mkdtemp(prefix="crux_agrade_"))
    _AUTO_TRASH.append(root)
    try:
        E.cmd_init("Tier zero", root, goal=LOOP_GOAL)
        qa, _ = E.cmd_ask(root, "can x reach the optimum")
        hb, _, _ = E.cmd_hypothesize(
            root, "x = 0", parent=qa, rule="all", null=LOOP_NULL,
            verifiables=["obj.score >= -0.5 on the frozen scorer"],
            neutral=["obj.score <= 0 — the objective is never positive"],
            fails_if=["x stays two or more steps away from 3",
                      "the scorer adds a positive offset"],
            discriminates=[True, False])
        write(os.path.join(root, E.RESULTS_DIR, hb, E.METRICS_FILE),
              json.dumps({"obj": {"score": {"value": -9.0}}}))
        rel = _loop_write_plan(root, qa, hb)

        def cc(text):
            # `<absent>` rather than None: "the grammar refused this" and "the grammar is not
            # written yet" are different answers, and half of these asserts want None.
            return _auto_val(lambda: E.auto_check_comparison(text), "<absent>")

        check("agrade: the grammar reads key, operator and number, and keeps the rest as prose",
              cc("obj.value >= -0.5") == {"key": "obj.value", "op": ">=", "number": -0.5,
                                          "rest": ""}
              and cc("[outcome-neutral] eval.loss ≤ 0.85 on the held-out split (found: 0.8)")
                  == {"key": "eval.loss", "op": "<=", "number": 0.85,
                      "rest": "on the held-out split"})
        check("agrade: the grammar refuses a missing space, prose, an empty key component and a number that is not finite",
              all(cc(t) is None for t in
                  ("obj.value>=-0.5", "the baseline reproduces", "obj..value <= 1",
                   "obj.value <= nan", "obj.value <= inf", "obj.value <= -inf",
                   "eval/loss <= 1", "eval\\loss <= 1", "eval#loss <= 1", "eval. <= 1",
                   ".value <= 1", "obj.value <=", "obj.value", "", "   ")))
        check("agrade: the operator vocabulary and the three aliases are the pinned ones",
              _auto_val(lambda: E.AUTO_COMPARISON_OPS) == ("<=", "<", ">=", ">", "==", "!=")
              and _auto_val(lambda: E.AUTO_OP_ALIASES) == {"≤": "<=", "≥": ">=", "≠": "!="})

        # --------------------------------------------------------- the two new plan checks
        prose = _loop_plan_text(qa, hb, verifiables=(
            "- [ ] obj.score >= -0.5 on the frozen scorer\n"
            "      fails-if:: x stays two or more steps away from 3\n"
            "      discriminates:: true\n"
            "- [ ] [outcome-neutral] the baseline reproduces\n"
            "      fails-if:: the scorer adds a positive offset\n"))
        alias = _loop_plan_text(qa, hb, verifiables=(
            "- [ ] obj.score ≥ -0.5 on the frozen scorer\n"
            "      fails-if:: x stays two or more steps away from 3\n"
            "      discriminates:: true\n"
            "- [ ] [outcome-neutral] obj.score ≤ 0 — the objective is never positive\n"
            "      fails-if:: the scorer adds a positive offset\n"))
        want5 = ("flight plan verifiable 2 is not a metric comparison: it must begin "
                 "'<key.path> <op> <number>' with <op> one of <=, <, >=, >, ==, != "
                 "(got 'the baseline reproduces')")

        def slugs(text):
            return _auto_val(lambda: {p["check"] for p in E.flight_plan_problems(
                root, E.parse_flight_plan(text), rel)}, set())

        check("agrade: a plan check that is not a metric comparison is refused under check-grammar, and ≤ ≥ ≠ read as <= >= !=",
              _auto_ok(lambda: (
                  want5 in _plan_msgs(root, prose, rel)
                  and "check-grammar" in slugs(prose)
                  and "check-grammar" not in slugs(alias)
                  and not any("is not a metric comparison" in m
                              for m in _plan_msgs(root, alias, rel))
                  and E.auto_check_comparison("eval.loss ≤ 0.85 on x")["op"] == "<="
                  and E.auto_check_comparison("eval.loss ≥ 0.85 on x")["op"] == ">="
                  and E.auto_check_comparison("eval.loss ≠ 0.85 on x")["op"] == "!=")))
        check("agrade: replicates must name a whole number of seeds, under field-type",
              _auto_ok(lambda: (
                  "flight plan field 'replicates' must name a whole number of seeds, 1 or "
                  "more (got 'some seeds')"
                  in _plan_msgs(root, _loop_plan_text(qa, hb, replicates="some seeds"), rel)
                  and "field-type" in slugs(_loop_plan_text(qa, hb, replicates="some seeds"))
                  and "field-type" in slugs(_loop_plan_text(qa, hb, replicates="0 seeds"))
                  and "field-type" not in slugs(_loop_plan_text(qa, hb, replicates="2 seeds")))))
        check("agrade: parallel_total and parallel_island must be one attempt or more, under field-type",
              _auto_ok(lambda: (
                  all(f"flight plan field '{f}' must be a whole number of attempts, 1 or more "
                      f"(got '0')" in _plan_msgs(root, _loop_plan_text(qa, hb, **{f: "0"}), rel)
                      and "field-type" in slugs(_loop_plan_text(qa, hb, **{f: "0"}))
                      for f in ("parallel_total", "parallel_island"))
                  # and the shape every plan in this suite already has stays clean
                  and "field-type" not in slugs(_loop_plan_text(qa, hb))
                  and _plan_msgs(root, _loop_plan_text(qa, hb, parallel_total="2",
                                                       parallel_island="2"), rel) == [])))
        check("agrade: the shipped flight-plan template leaves the comparison to the PI rather than hard-coding one direction",
              _auto_ok(lambda: (
                  "\n- [ ] <<verifiable>>\n"
                  in read(os.path.join(HERE, "templates", "flight_plan.md"))
                  and "<= <<bar>>" not in read(os.path.join(HERE, "templates",
                                                            "flight_plan.md")))))
        p = _loop_load_plan(root, qa)
        check("agrade: load_flight_plan carries the driver's fields and every check's key, op and number",
              _auto_ok(lambda: (
                  p["replicates"] == 2 and p["steward"] is False and p["retries"] == 1
                  and p["budget_attempts"] == 8 and p["budget_model_calls"] == 40
                  and p["parallel_total"] == 1 and p["parallel_island"] == 1
                  and p["stall_attempts"] == 2 and p["abort_invalid_runs"] == 2
                  and p["agent"] == "python3 agent.py step" and p["run"] == "python3 train.py"
                  and isinstance(p["budget_hours"], float)
                  and [c["index"] for c in p["checks"]] == [1, 2]
                  and [c["kind"] for c in p["checks"]] == [E.DEFAULT_KIND, E.NEUTRAL_KIND]
                  and [c["key"] for c in p["checks"]] == ["obj.score", "obj.score"]
                  and [c["op"] for c in p["checks"]] == [">=", "<="]
                  and [c["number"] for c in p["checks"]] == [-0.5, 0.0]
                  and p["checks"][0]["discriminates"] is True
                  and p["checks"][0]["fails_if"] == "x stays two or more steps away from 3")))

        # ------------------------------------------------------ the tick, and its found note
        check("agrade: auto_tick is arithmetic over the metrics document, and n/a whenever it cannot be",
              _auto_val(lambda: E.auto_tick({"obj": {"score": {"value": 0.0}}},
                                            "obj.score >= -0.5", "m")) == ("x", "0.0")
              and _auto_val(lambda: E.auto_tick({"obj": {"score": {"value": -9.0}}},
                                                "obj.score >= -0.5", "m")) == (" ", "-9.0")
              and _auto_val(lambda: E.auto_tick({"obj": {"other": 1.0}}, "obj.score >= -0.5",
                                                "m"), ("?", ""))[0] == "-"
              and _auto_val(lambda: E.auto_tick(None, "obj.score >= -0.5", "m"))
                  == ("-", "n/a — no m")
              and _auto_val(lambda: E.auto_tick({"obj": {"score": {"value": 0.0}}},
                                                "the baseline reproduces", "m"))
                  == ("-", "n/a — not a metric comparison"))

        hv, _, _ = E.cmd_hypothesize(
            root, "the tick fixture", parent=qa, rule="all", null=LOOP_NULL,
            verifiables=["obj.score >= -0.5 on the frozen scorer"],
            neutral=["obj.score <= 0 — the objective is never positive"],
            fails_if=["x stays two or more steps away from 3",
                      "the scorer adds a positive offset"],
            discriminates=[True, False])
        E.cmd_approve_null(root, hv)
        E.cmd_test(root, hv, to="running")
        before = read(node_path(root, hv))
        t0 = _auto_val(lambda: E.cmd_auto_ticks(root, hv, {"obj": {"score": {"value": 0.0}}}))
        a0 = read(node_path(root, hv))
        d0 = _auto_val(lambda: E.lock_drift(E.Vault(root).get(hv)), "<absent>")
        t1 = _auto_val(lambda: E.cmd_auto_ticks(root, hv, {"obj": {"score": {"value": -9.0}}}))
        a1 = read(node_path(root, hv))
        d1 = _auto_val(lambda: E.lock_drift(E.Vault(root).get(hv)), "<absent>")

        def stamp(t):
            return [l for l in t.splitlines() if l.startswith("updated:")]

        check("agrade: obj.score >= -0.5 ticks [x] at 0.0 and [ ] at -9.0 with a found note and no lock drift",
              _auto_ok(lambda: (
                  t0 == [("x", "0.0"), ("x", "0.0")]
                  and "- [x] obj.score >= -0.5 on the frozen scorer (found: 0.0)" in a0
                  and ("- [x] [outcome-neutral] obj.score <= 0 — the objective is never "
                       "positive (found: 0.0)") in a0
                  and d0 is False
                  and t1 == [(" ", "-9.0"), ("x", "-9.0")]
                  and "- [ ] obj.score >= -0.5 on the frozen scorer (found: -9.0)" in a1
                  and a1.count("(found:") == 2          # the note is replaced, never stacked
                  and d1 is False
                  # the continuation lines are not the driver's to touch
                  and "\n      fails-if:: x stays two or more steps away from 3\n" in a1
                  and "\n      discriminates:: true\n" in a1
                  and "\n      fails-if:: the scorer adds a positive offset\n" in a1
                  and stamp(a1) == stamp(before))))
        check("agrade: ticking is idempotent, refuses a count that does not match, and applies to a hypothesis only",
              _auto_ok(lambda: (
                  E.cmd_auto_ticks(root, hv, {"obj": {"score": {"value": -9.0}}}) == t1
                  and read(node_path(root, hv)) == a1
                  and _auto_msg(lambda: E.auto_tick_body(E.Vault(root).get(hv)["body"],
                                                         [("x", "0.0")]))
                      == "auto ticks: 1 ticks for 2 verifiables"
                  and _auto_msg(lambda: E.cmd_auto_ticks(root, qa, {}))
                      == f"auto ticks apply to a hypothesis (got a 'question' for '{qa}')")))
        check("agrade: findings name the objective, every check and the failure, with no backslash left in them",
              _auto_val(lambda: E.auto_findings("obj.score", -9.0,
                                                [("x", "-9.0"), (" ", "-9.0")]))
                  == ("Autopilot close. Objective obj.score = -9.0. "
                      "Check 1: met, found -9.0. Check 2: unmet, found -9.0.")
              and _auto_val(lambda: E.auto_findings("obj.score", None, [("-", "n/a — no m")],
                                                    failure="worker-exit: a\\b\n   c"))
                  == ("Autopilot close. Objective obj.score = n/a. "
                      "Check 1: n/a, found n/a — no m. Failure: worker-exit: a/b c."))
        check("agrade: crossing the bar and improving on the best each read the direction",
              _auto_val(lambda: (E.auto_crosses(-0.4, -0.5, "max"),
                                 E.auto_crosses(-0.6, -0.5, "max"),
                                 E.auto_crosses(None, -0.5, "max"),
                                 E.auto_crosses(0.4, 0.5, "min"))) == (True, False, False, True)
              and _auto_val(lambda: (E.auto_improves(0.0, None, "max"),
                                     E.auto_improves(-1.0, -0.5, "max"),
                                     E.auto_improves(-0.5, -0.5, "max"),
                                     E.auto_improves(0.4, 0.5, "min"))) == (True, False, False,
                                                                            True))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"agrade: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_approve():
    """Spec 05 PRD 05.2 §1.4/§4.3 — `crux auto approve`, the PI's signature on a plan.

    A run spends compute unattended against a bar nobody re-reads while it runs, so the bar has to
    be signed once and provably unchanged afterwards. The signature is a hash of what was approved,
    and the one region deliberately outside it is `## Guidance` — the PI is meant to keep talking to
    the workers mid-run, and having that clear the approval would make the feature useless.
    Everything else — a field, the goal, the bar itself — clears it."""
    print("\n# autopilot — the plan's approval (spec 05, PRD 05.2)")
    try:
        A = _auto_mod()
        repo, root, qa, isl, hb, rel = _loop_fixture(_approve=False)
        p = _plan_path(root, qa) if root else None
        r1 = _auto_val(lambda: E.cmd_auto_approve(root, rel), {})
        t1 = read(p) if p and os.path.isfile(p) else ""
        fm1 = _auto_val(lambda: E.parse_doc(t1)[0], {})
        r2 = _auto_val(lambda: E.cmd_auto_approve(root, rel), {})
        t2 = read(p) if p and os.path.isfile(p) else ""

        def state(t):
            return _auto_val(lambda: E.auto_approval(t), {}).get("state")

        def variant(fn):
            """The approval state after one edit to the approved plan, then put back."""
            saved = read(p)
            try:
                fn()
                return state(read(p))
            finally:
                write(p, saved)

        guided = variant(lambda: _auto_val(
            lambda: E.append_guidance(root, rel, "try smaller steps", "pi"))) if p else None
        restamped = variant(lambda: write(p, re.sub(
            r"^updated:.*$", "updated: 2027-02-02T00:00:00", read(p), count=1,
            flags=re.M))) if p else None
        refielded = variant(lambda: edit(p, "budget_attempts: 8",
                                         "budget_attempts: 9")) if p else None
        rebodied = variant(lambda: edit(p, LOOP_GOAL, LOOP_GOAL + " quickly")) if p else None
        reordered = _auto_val(
            lambda: E.flight_plan_hash("---\nmode: climb\ntype: flight-plan\n---\n\nbody\n"),
            "<a>") == _auto_val(
            lambda: E.flight_plan_hash("---\ntype: flight-plan\nmode: climb\n---\n\nbody\n"),
            "<b>")
        badrel = _auto_val(lambda: _loop_write_plan(root, qa, hb, name="bad.md", mode="drift"))
        badplan = _auto_msg(lambda: E.cmd_auto_approve(root, badrel))
        check("aapprove: auto approve stamps approved and approved_hash once, guidance keeps the approval, and any other edit clears it",
              _auto_ok(lambda: (
                  r1["already"] is False and r1["plan"] == rel
                  and fm1.get("approved") == r1["approved"]
                  # quoted on the way out, so an all-digit hash never becomes an int
                  and isinstance(fm1.get("approved_hash"), str)
                  and fm1["approved_hash"] == r1["approved_hash"] == E.flight_plan_hash(t1)
                  and len(r1["approved_hash"]) == 16
                  and state(t1) == "approved"
                  and r2["already"] is True and r2["approved"] == r1["approved"] and t2 == t1
                  and guided == "approved" and restamped == "approved"
                  and refielded == "edited" and rebodied == "edited"
                  and reordered is True
                  and badplan.startswith(f"cannot approve {E.AUTO_DIR}/{qa}/bad.md: ")
                  and state(read(p)) == "approved")))
        check("aapprove: an unsigned plan reads unapproved, and approving refuses a plan that is not there",
              _auto_ok(lambda: (
                  E.auto_approval(_loop_plan_text(qa, hb))["state"] == "unapproved"
                  and E.auto_approval(_loop_plan_text(qa, hb))["approved"] is None
                  and E.auto_approval(_loop_plan_text(qa, hb))["approved_hash"] is None
                  and _auto_msg(lambda: E.cmd_auto_approve(root, f"{E.AUTO_DIR}/{qa}/gone.md"))
                      == f"no flight plan at {E.AUTO_DIR}/{qa}/gone.md")))

        # ------------------------------------------ what `auto run` refuses to start, and why
        ur, uroot, uqa, _, _, urel = _loop_fixture(_approve=False)
        umsg = _auto_msg(lambda: A.auto_run(uroot, urel))
        uclean = _auto_val(lambda: _loop_untouched(ur, uroot, uqa), False)
        er, eroot, eqa, _, _, erel = _loop_fixture()
        estamp = _auto_val(lambda: E.auto_approval(read(_plan_path(eroot, eqa)))["approved"])
        if eroot:
            edit(_plan_path(eroot, eqa), "bar:: -0.5", "bar:: -0.4")
        emsg = _auto_msg(lambda: A.auto_run(eroot, erel))
        eclean = _auto_val(lambda: _loop_untouched(er, eroot, eqa), False)
        check("aapprove: auto run refuses an unapproved plan and a plan edited after approval, before any reservation",
              umsg == (f"auto run: {urel} is not approved — the PI approves a flight plan "
                       f"with crux auto approve {urel}")
              and uclean
              and emsg == (f"auto run: {erel} was edited after it was approved at {estamp}, "
                           f"so the approval no longer stands — the PI re-approves it with "
                           f"crux auto approve {erel}")
              and eclean)
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aapprove: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_loop():
    """Spec 05 PRD 05.2 §5 — one attempt, end to end, and everything a run writes down.

    The driver is the one role that lives for the whole run and calls no model. What it may
    conclude is bounded on every side: a worker that fails is retried and then closed
    `invalid-run`, a worker that cheats — a frozen path, a shared root, a proposal outside the
    schema — is not retried at all, and in neither case does a node ever read `refuted`. A
    refutation is a claim about the world; a broken apparatus is a claim about nothing."""
    print("\n# autopilot — the loop, one attempt at a time (spec 05, PRD 05.2)")
    try:
        A = _auto_mod()

        # --------------------------------------- the search that works, watched at every event
        repo, root, qa, isl, hb, rel = _loop_fixture(x0=0)
        main0 = _git(repo, "rev-parse", "main") if repo else ""
        head0 = _git(repo, "rev-parse", "HEAD") if repo else ""
        sym0 = _git(repo, "symbolic-ref", "HEAD") if repo else ""
        # Every copy is taken HERE, before the first run. A copy taken afterwards carries that
        # run's state.json, ledger, reservations and refs, so `auto run` on it resumes or
        # refuses — and refuses before it reaches the thing each check below is about.
        lockfx = _loop_copy((repo, root, qa, isl, hb, rel))
        killfx = _loop_copy((repo, root, qa, isl, hb, rel))
        filefx = _loop_copy((repo, root, qa, isl, hb, rel))
        restore, probe_bad = (lambda: None), []
        unmark, skipped = (lambda: None), []
        if root:
            restore, probe_bad = _record_probe(A, root, qa)
            unmark, skipped = _skip_first_materialize(A)
        try:
            ok = _loop_run("success", root, qa, rel)
        finally:
            restore()
            unmark()
        st = ok["state"] or {}
        closed = st.get("closed") or []
        msgs = _auto_val(lambda: E.cmd_validate(root), [])
        res = _auto_val(lambda: A.reservations(root, qa), {})
        counter = int(_auto_val(lambda: E.Vault(root).cfg.get("counter_h"), 0) or 0)

        check("astate: state.json parses after every ledger event and carries exactly the pinned keys",
              _auto_ok(lambda: (
                  bool(E.AUTO_STATE_KEYS) and set(st) == set(E.AUTO_STATE_KEYS)
                  and not [b for b in probe_bad if b.startswith("state:")]
                  and st["events"] == len(ok["events"]) and st["events"] > 0
                  and st["budget"]["attempts"]["used"] == len(closed)
                  and st["in_flight"] == {}
                  and set(st["stop"]) == {"reason", "axis", "detail", "attempt", "at"}
                  and set(st["driver"]) == {"pid", "host"}
                  and set(st["tasks"]) == {"run", "exceptions"}
                  and set(st["budget"]) == {"attempts", "hours", "model_calls"}
                  and bool(st["islands"])
                  and all(set(r) == _ISLAND_KEYS for r in st["islands"].values())
                  and set(st["best"]) == _BEST_KEYS
                  and ok["returned"] == st)))
        check("astate: ledger.jsonl is append-only and every event is in the pinned vocabulary",
              _auto_ok(lambda: (
                  # EXTENDED IN PLACE by 05.3 (PRD-12): the seventeen 05.2 names keep their
                  # order, and the slice's four are appended. A vocabulary pinned as a literal
                  # is the only way a driver that invented an event gets caught — `_record`
                  # itself refuses an unpinned name, so the literal is what proves the
                  # constant grew on purpose rather than to fit whatever the driver emitted.
                  E.AUTO_LEDGER_EVENTS == (
                      "run-opened", "attempt-reserved", "worker-started", "worker-done",
                      "worker-failed", "node-filed", "scored", "violation", "retry", "closed",
                      "confirm", "island-best", "stall", "escalated", "abandoned", "resumed",
                      "stop",
                      "failover", "cooldown", "closer", "steward")
                  and not [b for b in probe_bad if b.startswith("ledger:")]
                  and bool(ok["events"]) and ok["raw"].endswith("\n")
                  and all(e.get("event") in E.AUTO_LEDGER_EVENTS for e in ok["events"])
                  and all("at" in e for e in ok["events"])
                  and [e["event"] for e in ok["events"][:1]] == ["run-opened"]
                  and [e["event"] for e in ok["events"][-1:]] == ["stop"]
                  and _auto_msg(lambda: E.auto_ledger_line("not-an-event", {}))
                      == "'not-an-event' is not an autopilot ledger event")))
        check("arun: no question ever holds an unrun hypothesis during a tier-0 run, and validate reports no fan-out problem",
              _auto_ok(lambda: (
                  not [b for b in probe_bad if b.startswith("unrun:")]
                  and bool(closed)
                  and not any("unrun hypothes" in m or "none of them run" in m
                              for _, m in msgs)
                  and all(E.Vault(root).get(h).status != "idea" for h in closed))))
        check("arun: main, HEAD and the working tree outside the vault and writable roots are unchanged after a full tier-0 search",
              _auto_ok(lambda: (
                  bool(closed)
                  and _git(repo, "rev-parse", "main") == main0
                  and _git(repo, "rev-parse", "HEAD") == head0
                  and _git(repo, "symbolic-ref", "HEAD") == sym0 == "refs/heads/main"
                  and _git(repo, "status", "--porcelain", "--", ".", ":(exclude)cruxvault",
                           ":(exclude)work") == "")))
        heads = _git(repo, "for-each-ref", "--format=%(refname)", "refs/heads") if repo else ""
        bests = _ev(ok, "island-best")
        check("arun: the island branch moves by compare-and-swap only when a supported attempt improves the island's best, and no other refs/heads write happens",
              _auto_ok(lambda: (
                  len(bests) == 1 and bests[0]["attempt"] == st["confirmed"]
                  and set(bests[0]) >= {"attempt", "island", "branch", "from", "to", "score"}
                  and bests[0]["branch"] == f"crux/auto/{qa}/island/{qa}"
                  and bests[0]["from"] == st["base"]
                  and _git(repo, "rev-parse",
                           f"refs/crux/auto/{qa}/{bests[0]['attempt']}") == bests[0]["to"]
                  and _git(repo, "rev-parse", f"crux/auto/{qa}/island/{qa}") == bests[0]["to"]
                  and st["islands"][qa]["pointer"] == bests[0]["to"]
                  and st["islands"][qa]["pointer"] == _git(
                      repo, "rev-parse", f"refs/heads/crux/auto/{qa}/island/{qa}")
                  and set(heads.split()) == {"refs/heads/main",
                                             f"refs/heads/crux/auto/{qa}/run",
                                             f"refs/heads/crux/auto/{qa}/island/{qa}"}
                  and _git(repo, "rev-parse", f"crux/auto/{qa}/run") == st["base"])))
        check("arun: the driver files each attempt at its reserved id through hypothesize, approve-null, test --to running and close",
              _auto_ok(lambda: (
                  bool(closed)
                  and all(E.Vault(root).get(h)["fm"].get("null_approved") for h in closed)
                  and all(E.Vault(root).get(h)["fm"].get("lock") for h in closed)
                  and all(E.Vault(root).get(h)["fm"].get("lock_at") == "running"
                          for h in closed)
                  and all(E.Vault(root).get(h)["fm"].get("verdict") for h in closed)
                  and all(E._null_text(E.Vault(root).get(h)).strip() == LOOP_NULL
                          for h in closed)
                  and all(res[h]["state"] == "materialized" for h in closed)
                  and counter == max(E.natkey(h)[1] for h in res))))
        check("arun: cmd_hypothesize files at a reserved id and refuses one never allocated, without moving the counter",
              _auto_ok(lambda: (
                  _auto_msg(lambda: E.cmd_hypothesize(root, "t", parent=qa, nid="h999"))
                      == f"hypothesis id 'h999' was never allocated (counter_h is {counter})"
                  and _auto_msg(lambda: E.cmd_hypothesize(root, "t", parent=qa, nid=hb))
                      == f"hypothesis id '{hb}' is already in use"
                  and _auto_msg(lambda: E.cmd_hypothesize(root, "t", parent=qa, nid="x1"))
                      == "hypothesis id 'x1' is not a hypothesis id (h<number>)"
                  and int(E.Vault(root).cfg.get("counter_h") or 0) == counter
                  and counter > 0)))

        check("arun: a reservation the filing step left unmarked is marked materialized when the attempt retires",
              _auto_ok(lambda: (
                  len(skipped) == 1 and skipped[0] in closed
                  and bool(closed)
                  and all(res[h]["state"] == "materialized" for h in closed))))

        # ------------------------------------- the lock the driver has to take before it writes
        lrepo, lroot, lqa, _, _, lrel = lockfx
        lmsg, lclean = "", False
        if lroot and lroot != root:
            _auto_val(lambda: A.acquire_lock(lroot, "test"))
            try:
                lmsg = _auto_msg(lambda: A.auto_run(lroot, lrel, lock_wait=0.3))
                lclean = _auto_val(lambda: _loop_untouched(lrepo, lroot, lqa), False)
            finally:
                _auto_val(lambda: A.release_lock(lroot))

        # ------------------------- the way out of the loop that is NOT a stop: an exception
        _, kroot, kqa, _, _, krel = killfx
        kpid, kalive, kfree, kraised = [], True, False, False
        if kroot:
            korig = _auto_val(lambda: A._step_record)

            def wreck(ctx, hid):
                """A worker still in the driver's hands the moment the loop path blows up."""
                p = A._spawn([sys.executable, "-c", "import time; time.sleep(120)"],
                             kroot, dict(os.environ), os.path.join(kroot, "hold.log"))
                ctx["procs"]["probe"] = p
                kpid.append(p.pid)
                raise RuntimeError("the loop path blew up")

            if korig is not None:
                A._step_record = wreck
                try:
                    A.auto_run(kroot, krel)
                except RuntimeError:
                    kraised = True
                except Exception:                    # pragma: no cover - wave-1 guard
                    kraised = False
                finally:
                    A._step_record = korig
                kalive = _auto_val(lambda: A._pid_alive(kpid[0]), True) if kpid else True
                if kalive and kpid:                  # never leak the child the fix should kill
                    _auto_val(lambda: os.kill(kpid[0], 9))
                kfree = _auto_val(lambda: _loop_lock_free(A, kroot), False)
        check("arun: an error on the loop path kills every worker still running and leaves the vault lock free",
              _auto_ok(lambda: kraised and len(kpid) == 1 and kalive is False and kfree))

        # ------------------- a filing refusal on a node the engine has already written down
        _, fnroot, fnqa, _, _, fnrel = filefx
        fn, fired = {"state": None, "events": []}, []
        if fnroot:
            forig = _auto_val(lambda: E.cmd_approve_null)

            def refuse(root_, hid_, *a, **k):
                if not fired:
                    fired.append(hid_)
                    raise E.CruxError("approve-null refused on purpose")
                return forig(root_, hid_, *a, **k)

            if forig is not None:
                E.cmd_approve_null = refuse
                try:
                    fn = _loop_run("filing-refusal", fnroot, fnqa, fnrel)
                finally:
                    E.cmd_approve_null = forig
        fnclosed = (fn["state"] or {}).get("closed") or []
        check("arun: a filing refusal on a node the engine already wrote closes it invalid-run rather than abandoning it",
              _auto_ok(lambda: (
                  len(fired) == 1 and fnclosed == fired
                  and E.Vault(fnroot).get(fnclosed[0])["fm"]["verdict"] == "invalid-run"
                  and len(_ev(fn, "closed")) == 1
                  and _ev(fn, "node-filed") == [] and _ev(fn, "abandoned") == []
                  and not [n for n in E.Vault(fnroot).nodes.values()
                           if n.type == "idea" and n.status == "idea"]
                  and _loop_stop(fn)["reason"] == "abort"
                  and _loop_stop(fn)["detail"].startswith(
                      f"the engine refused to file {fnclosed[0]}: "))))

        # ---------------------------------------- two islands, two workers, one brief for each
        erepo, eroot, eqa, eisl, ehb, erel = _loop_fixture(
            x0=0, islands=2, mode="explore", parallel_total="2", parallel_island="1",
            budget_attempts="4", stall_attempts="0")
        unrun = _loop_copy((erepo, eroot, eqa, eisl, ehb, erel))
        brief0 = _auto_val(lambda: E.auto_brief(eroot, ehb))
        ex = _loop_run("explore", eroot, eqa, erel)
        est = ex["state"] or {}
        eclosed = est.get("closed") or []
        eres = _auto_val(lambda: A.reservations(eroot, eqa), {})
        filed = {e["attempt"]: e for e in _ev(ex, "node-filed")}
        order = [e["event"] for e in ex["events"]
                 if e["event"] in ("worker-started", "worker-done")]
        meta = read(os.path.join(eroot, "META.md")) if eroot else ""
        check("astate: a held vault lock refuses the driver's first write after the stated wait, and two attempts in flight leave META.md listing both",
              _auto_ok(lambda: (
                  "gave up after 0.3s" in lmsg and lmsg.startswith("auto lock ") and lclean
                  and order[:2] == ["worker-started", "worker-started"]
                  and len(eclosed) >= 2
                  and all(f"`{h}`" in meta for h in eclosed)
                  and E.refresh(eroot) is False)))
        firsts = _auto_val(lambda: [min((h for h in eclosed if eres[h]["island"] == i),
                                        key=E.natkey) for i in eisl], [])
        check("arun: an Explore attempt whose parent sits under another question is filed under its island without builds_on, cut from the parent's commit",
              _auto_ok(lambda: (
                  len(eisl) == 2 and len(firsts) == 2
                  and all(E.Vault(eroot).get(h).parent == eres[h]["island"] for h in eclosed)
                  and all(eres[h]["parent"] == ehb for h in firsts)
                  and all(E.node_builds_on(E.Vault(eroot).get(h)) is None for h in firsts)
                  and all(filed[h]["parent"] == ehb and filed[h]["builds_on"] is None
                          for h in firsts)
                  and all(_git(erepo, "rev-parse", f"refs/crux/auto/{eqa}/{h}^")
                          == est["base"] for h in firsts)
                  and all(E.node_builds_on(E.Vault(eroot).get(h))
                          == min((o for o in eclosed
                                  if eres[o]["island"] == eres[h]["island"]), key=E.natkey)
                          for h in eclosed if h not in firsts)
                  # island None is still 05.0: the call succeeds, the island it picks is the
                  # baseline's own question, and every slot that does not COUNT the run reads
                  # exactly as it does on a copy of this vault that was never run at all.
                  # (`budget.attempts.used` and `migration` are what a search is for.)
                  and E.auto_brief(eroot, ehb)["island"]["id"] == eqa
                  and _brief_fixed(E.auto_brief(eroot, ehb))
                      == _brief_fixed(E.auto_brief(unrun[1], ehb)) == _brief_fixed(brief0)
                  and set(E.auto_brief(eroot, ehb)) == set(brief0))))

        # -------------------------------------- the worker that fails and the scorer that dies
        _, xroot, xqa, _, _, xrel = _loop_fixture(x0=0, agent="python3 agent.py exit1",
                                                  retries="1", abort_invalid_runs="2")
        x = _loop_run("exit1", xroot, xqa, xrel)
        xclosed = (x["state"] or {}).get("closed") or []
        _, croot, cqa, _, chb, crel = _loop_fixture(x0=0, agent="python3 agent.py crashscore",
                                                    retries="1", abort_invalid_runs="1")
        c = _loop_run("crashscore", croot, cqa, crel)
        cclosed = (c["state"] or {}).get("closed") or []
        check("arun: a failing worker and a crashing scorer are each retried retries times, then close invalid-run, never refuted",
              _auto_ok(lambda: (
                  len(xclosed) == 2
                  and len(_ev(x, "worker-started")) == 4        # two attempts, two tries each
                  and [e["reason"] for e in _ev(x, "worker-failed")] == ["worker-exit"] * 4
                  and [e["step"] for e in _ev(x, "retry")] == ["worker"] * 2
                  and all(E.Vault(xroot).get(h)["fm"]["verdict"] == "invalid-run"
                          for h in xclosed)
                  and len(cclosed) == 1
                  and len(_ev(c, "worker-started")) == 1
                  and [e["step"] for e in _ev(c, "retry")] == ["scorer"]
                  and [e["reason"] for e in _ev(c, "retry")] == ["scorer-exit"]
                  and E.Vault(croot).get(cclosed[0])["fm"]["verdict"] == "invalid-run"
                  and not any(E.Vault(r).get(h)["fm"]["verdict"] == "refuted"
                              for r, ids in ((xroot, xclosed), (croot, cclosed))
                              for h in ids))))
        cn = _auto_val(lambda: E.Vault(croot).get(cclosed[0]), None)
        check("arun: an attempt with no metrics file ticks every check [-] and closes invalid-run as derive_verdict_15 says",
              _auto_ok(lambda: (
                  not os.path.exists(os.path.join(croot, E.RESULTS_DIR, cclosed[0],
                                                  E.METRICS_FILE))
                  and [t for t, _ in E._verifiable_lines(cn["body"])] == ["-", "-"]
                  and _ev(c, "scored") == []
                  and cn["fm"]["verdict"] == E.derive_verdict_15(
                      E.count_verifiables_by_kind(cn["body"])[E.DEFAULT_KIND],
                      E.count_verifiables_by_kind(cn["body"])[E.NEUTRAL_KIND],
                      *E.node_rule(cn))
                  and cn["fm"]["verdict"] == "invalid-run"
                  and "n/a" in E._section(cn["body"], "Findings"))))

        # ------------------------------------------ the two ways a worker steps out of bounds
        _, froot, fqa, _, _, frel = _loop_fixture(x0=0, agent="python3 agent.py frozen",
                                                  abort_invalid_runs="1")
        f = _loop_run("frozen", froot, fqa, frel)
        _, shroot, shqa, _, _, shrel = _loop_fixture(x0=0, agent="python3 agent.py shared",
                                                     abort_invalid_runs="1")
        sh = _loop_run("shared", shroot, shqa, shrel)
        fv, shv = _ev(f, "violation"), _ev(sh, "violation")
        check("arun: a frozen-path commit and a shared-root write each close invalid-run unretried with one violation event naming the path",
              _auto_ok(lambda: (
                  E.AUTO_VIOLATION_KINDS == ("frozen", "manifest", "proposal")
                  and len(fv) == 1 and fv[0]["kind"] == "frozen"
                  and fv[0]["paths"] == ["score.py"] and "score.py" in fv[0]["detail"]
                  and len(_ev(f, "worker-started")) == 1 and _ev(f, "retry") == []
                  and len(shv) == 1 and shv[0]["kind"] == "manifest"
                  and shv[0]["paths"] == ["work/shared/x"]
                  and "work/shared/x" in shv[0]["detail"]
                  and len(_ev(sh, "worker-started")) == 1 and _ev(sh, "retry") == []
                  and all(E.Vault(r).get(h)["fm"]["verdict"] == "invalid-run"
                          for r, run in ((froot, f), (shroot, sh))
                          for h in (run["state"] or {}).get("closed") or [])
                  and _loop_stop(f).get("reason") == _loop_stop(sh).get("reason") == "abort")))

        # ------------------------------------------------- what a proposal is allowed to carry
        _, gcroot, gcqa, _, _, gcrel = _loop_fixture(x0=0, agent="python3 agent.py longclaim",
                                                     retries="1", abort_invalid_runs="1")
        lg = _loop_run("longclaim", gcroot, gcqa, gcrel)
        lgc = (lg["state"] or {}).get("closed") or []
        check("arun: an over-cap claim is retried, then closes invalid-run, and no node carries a truncated claim",
              _auto_ok(lambda: (
                  [e["reason"] for e in _ev(lg, "worker-failed")] == ["claim-over-cap"] * 2
                  and [e["step"] for e in _ev(lg, "retry")] == ["worker"]
                  and len(lgc) == 1
                  and E._section(E.Vault(gcroot).get(lgc[0])["body"],
                                 "Idea / Hypothesis").strip()
                      == E.AUTO_NO_CLAIM.format(hid=lgc[0], reason="claim-over-cap")
                  and "word word" not in read(node_path(gcroot, lgc[0]))
                  and len(E._prose_tokens(E.Vault(gcroot).get(lgc[0])["body"])) <= E.PROSE_CAP
                  and E.Vault(gcroot).get(lgc[0])["fm"]["verdict"] == "invalid-run")))
        _, kroot, kqa, _, _, krel = _loop_fixture(x0=0, agent="python3 agent.py extrakey",
                                                  abort_invalid_runs="1")
        k = _loop_run("extrakey", kroot, kqa, krel)
        _, troot, tqa, _, _, trel = _loop_fixture(x0=0, agent="python3 agent.py taggedcontrol",
                                                  abort_invalid_runs="1")
        t = _loop_run("taggedcontrol", troot, tqa, trel)
        _, groot, gqa, _, _, grel = _loop_fixture(x0=2, agent="python3 agent.py control",
                                                  budget_attempts="1")
        g = _loop_run("control", groot, gqa, grel)
        gc = (g["state"] or {}).get("closed") or []
        check("arun: a proposal key outside claim and controls, or a tagged control, closes invalid-run unretried; a good control is filed outcome-neutral",
              _auto_ok(lambda: (
                  all(len(_ev(r, "violation")) == 1
                      and _ev(r, "violation")[0]["kind"] == "proposal"
                      and _ev(r, "violation")[0]["paths"] == []
                      and _ev(r, "retry") == []
                      and len(_ev(r, "worker-started")) == 1
                      for r in (k, t))
                  and "claim, controls: verdict" in _ev(k, "violation")[0]["detail"]
                  and "the driver tags every control outcome-neutral"
                      in _ev(t, "violation")[0]["detail"]
                  and all(E.Vault(rt).get(h)["fm"]["verdict"] == "invalid-run"
                          for rt, run in ((kroot, k), (troot, t))
                          for h in (run["state"] or {}).get("closed") or [])
                  and len(gc) == 1
                  and ("- [x] [outcome-neutral] obj.score <= 1 — the value stays at most one "
                       "(found: ") in read(node_path(groot, gc[0]))
                  and [i["kind"] for i in E._verifiables(E.Vault(groot).get(gc[0])["body"])]
                      == [E.DEFAULT_KIND, E.NEUTRAL_KIND, E.NEUTRAL_KIND]
                  and "the scorer drifts upward" in read(node_path(groot, gc[0])))))

        # -------------------------------------------- the two plans a run will not open at all
        # REWRITTEN by 05.3 (PRD-26): this check bundled THREE refusals under one name, and
        # 05.3 ships the steward, so `steward: true` is now accepted rather than refused. The
        # name loses that clause and the assertion loses its fixture; the acceptance half is
        # asserted in `run_auto_steward` instead. The other two refusals keep every byte.
        rr, rroot, rqa, _, _, rrel = _loop_fixture(x0=0, replicates="some seeds",
                                                   _approve=False)
        rmsg = _auto_msg(lambda: A.auto_run(rroot, rrel))
        pr, proot, pqa, _, _, prel = _loop_fixture(x0=0, _approve=False, verifiables=(
            "- [ ] obj.score >= -0.5 on the frozen scorer\n"
            "      fails-if:: x stays two or more steps away from 3\n"
            "      discriminates:: true\n"
            "- [ ] [outcome-neutral] the baseline reproduces\n"
            "      fails-if:: the scorer adds a positive offset\n"))
        pmsg = _auto_msg(lambda: A.auto_run(proot, prel))
        check("arun: auto run refuses a replicates with no integer and a plan auto check rejects, before any reservation",
              _auto_ok(lambda: (
                  rmsg == (f"auto run: {rrel} does not pass auto check: flight plan field "
                           f"'replicates' must name a whole number of seeds, 1 or more "
                           f"(got 'some seeds')")
                  and pmsg.startswith(f"auto run: {prel} does not pass auto check: flight plan "
                                      f"verifiable")
                  and _loop_untouched(rr, rroot, rqa)
                  and _loop_untouched(pr, proot, pqa))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"arun: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_resume():
    """Spec 05 PRD 05.2 §6 — a run killed at any point, resumed from what is on disk.

    The driver keeps no memory: everything it knows is a node, a ref, a metrics file, a
    reservation or a ledger line, and resume is the function that reads those five and works out
    what each half-finished attempt still needs. `CRUX_AUTO_CRASH_AT` kills the process at a named
    phase, which is the only honest way to assert this — a resume tested by asking the driver
    nicely to stop is a resume from a clean shutdown, and a clean shutdown is not the case that
    ever happens at three in the morning."""
    print("\n# autopilot — resume from on-disk evidence (spec 05, PRD 05.2)")
    try:
        A = _auto_mod()
        built = _loop_fixture(x0=2)
        control = _loop_copy(built)
        base = _loop_run("resume-control", control[1], control[2], control[5])
        phases = _auto_val(lambda: E.AUTO_PHASES, ())
        rows = []
        for ph in phases:
            repo, root, qa, isl, hb, rel = _loop_copy(built)
            row = {"phase": ph, "root": root, "repo": repo, "anchor": qa}
            r = _auto_val(lambda: subprocess.run(
                [sys.executable, os.path.join(HERE, "crux.py"), "auto", "run", rel, "--json"],
                cwd=root, env=dict(os.environ, CRUX_AUTO_CRASH_AT=ph), capture_output=True,
                encoding="utf-8", errors="replace", timeout=120))
            row["rc"] = getattr(r, "returncode", 0)
            mid = _auto_val(lambda: json.loads(read(_loop_state_path(root, qa))), {}) or {}
            hit = [h for h, fl in (mid.get("in_flight") or {}).items()
                   if fl.get("phase") == ph]
            h = row["id"] = hit[0] if hit else None
            plan = _loop_load_plan(root, qa)
            res = _auto_val(lambda: A.reservations(root, qa), {}) or {}
            wt = _auto_val(lambda: A.worktree_path(root, plan, h))
            row["reserved"] = h in res
            row["node"] = _auto_val(lambda: E.Vault(root).get(h)) is not None
            row["wt"] = bool(wt) and os.path.isdir(wt)
            row["wt_head"] = _auto_val(lambda: _git(wt, "rev-parse", "HEAD")) if row["wt"] \
                else None
            row["from"] = (mid.get("in_flight") or {}).get(h, {}).get("from")
            row["ref"] = _auto_val(lambda: _git(repo, "rev-parse", "--verify", "--quiet",
                                                f"refs/crux/auto/{qa}/{h}", check=False), "")
            row["metrics"] = bool(h) and os.path.isfile(
                os.path.join(root, E.RESULTS_DIR, h, E.METRICS_FILE))
            row["verdict"] = _auto_val(
                lambda: E.Vault(root).get(h)["fm"].get("verdict")) if row["node"] else None
            row["after"] = _loop_run(f"resume-{ph}", root, qa, rel)
            row["res_after"] = _auto_val(lambda: A.reservations(root, qa), {}) or {}
            rows.append(row)

        def verdicts(root, ids):
            return [_auto_val(lambda h=h: E.Vault(root).get(h)["fm"].get("verdict"))
                    for h in ids or []]

        want = verdicts(control[1], (base["state"] or {}).get("closed") or [])
        check("aresume: a run killed at each of the five phases resumes to the same closed set, no commit dropped, no id closed twice",
              _auto_ok(lambda: (
                  len(rows) == 5
                  and phases == ("reserved", "drafted", "committed", "scored", "closed")
                  and bool(want) and all(v == "supported" for v in want)
                  and all(r["rc"] != 0 and r["id"] for r in rows)
                  and all(_loop_stop(r["after"]).get("reason")
                          == _loop_stop(base).get("reason") == "success" for r in rows)
                  and all(verdicts(r["root"], (r["after"]["state"] or {}).get("closed"))
                          == want for r in rows)
                  and all(len(_ev(r["after"], "closed"))
                          == len({e["attempt"] for e in _ev(r["after"], "closed")})
                          for r in rows)
                  and all(len(_ev(r["after"], "resumed")) == 1 for r in rows))))

        by = {r["phase"]: r for r in rows}
        check("aresume: resume records a commit with no ref, scores a ref with no metrics, closes metrics with no verdict, and abandons a bare reserved id for good",
              _auto_ok(lambda: (
                  # reserved: a bare id, no worktree, no node — abandoned, and never handed out
                  by["reserved"]["reserved"] and not by["reserved"]["node"]
                  and not by["reserved"]["wt"]
                  and by["reserved"]["res_after"][by["reserved"]["id"]]["state"] == "abandoned"
                  and _auto_val(lambda: E.Vault(by["reserved"]["root"])
                                .get(by["reserved"]["id"])) is None
                  and [e["reason"] for e in _ev(by["reserved"]["after"], "abandoned")]
                      == ["resume"]
                  and all(E.natkey(h) > E.natkey(by["reserved"]["id"])
                          for h in (by["reserved"]["after"]["state"] or {}).get("closed") or [])
                  # committed: a commit in the worktree and no ref yet — the ref is recorded
                  and by["committed"]["wt_head"]
                  and by["committed"]["wt_head"] != by["committed"]["from"]
                  and by["committed"]["ref"] == ""
                  and by["committed"]["id"]
                      in ((by["committed"]["after"]["state"] or {}).get("closed") or [])
                  and _git(by["committed"]["repo"], "rev-parse",
                           f"refs/crux/auto/{by['committed']['anchor']}/"
                           f"{by['committed']['id']}") == by["committed"]["wt_head"]
                  # scored: a ref and a node, no metrics — the attempt is scored, then closed
                  and by["scored"]["ref"] and by["scored"]["node"]
                  and not by["scored"]["metrics"]
                  and by["scored"]["id"]
                      in ((by["scored"]["after"]["state"] or {}).get("closed") or [])
                  and os.path.isfile(os.path.join(by["scored"]["root"], E.RESULTS_DIR,
                                                  by["scored"]["id"], E.METRICS_FILE))
                  # closed: metrics on disk and no verdict — closed exactly once
                  and by["closed"]["metrics"] and not by["closed"]["verdict"]
                  and _auto_val(lambda: E.Vault(by["closed"]["root"])
                                .get(by["closed"]["id"])["fm"].get("verdict"))
                  and len([e for e in _ev(by["closed"]["after"], "closed")
                           if e["attempt"] == by["closed"]["id"]]) == 1)))

        # ----------- the ref is the commit of record: an attempt already at one is not re-run
        r4repo, r4root, r4qa, _, _, r4rel = _loop_copy(built)
        r4, r4h, r4head, r4ref = {"state": None, "events": []}, None, "", ""
        if r4root:
            _auto_val(lambda: subprocess.run(
                [sys.executable, os.path.join(HERE, "crux.py"), "auto", "run", r4rel, "--json"],
                cwd=r4root, env=dict(os.environ, CRUX_AUTO_CRASH_AT="committed"),
                capture_output=True, encoding="utf-8", errors="replace", timeout=120))
            mid = _auto_val(lambda: json.loads(read(_loop_state_path(r4root, r4qa))), {}) or {}
            hit = [h for h, fl in (mid.get("in_flight") or {}).items()
                   if fl.get("phase") == "committed"]
            r4h = hit[0] if hit else None
            r4plan = _loop_load_plan(r4root, r4qa)
            if r4h and r4plan:
                # The kill is moved one step later by hand: past `record_attempt`, before the
                # filing, with the worker's proposal gone. Now the ref names the commit and
                # nothing else on disk does — the one window where a retry would leave the
                # node describing a commit its own ref does not name.
                r4head = _auto_val(lambda: _git(A.worktree_path(r4root, r4plan, r4h),
                                                "rev-parse", "HEAD"), "")
                _auto_val(lambda: A.record_attempt(r4root, r4plan, r4h))
                pp = os.path.join(A.workspace_path(r4root, r4plan, r4h), A.PROPOSAL_NAME)
                if os.path.isfile(pp):
                    os.remove(pp)
                r4 = _loop_run("resume-recorded", r4root, r4qa, r4rel, max_attempts=1)
                r4ref = _auto_val(lambda: _git(r4repo, "rev-parse",
                                               f"refs/crux/auto/{r4qa}/{r4h}"), "")
        check("aresume: an attempt already recorded at its ref is never handed to a second worker, and closes on the commit the ref names",
              _auto_ok(lambda: (
                  bool(r4head) and r4ref == r4head
                  and _ev(_since_resume(r4), "worker-started") == []
                  and _ev(_since_resume(r4), "retry") == []
                  and _ev(r4, "scored") == []
                  and [e["reason"] for e in _ev(_since_resume(r4), "worker-failed")]
                      == ["proposal-missing"]
                  and ((r4["state"] or {}).get("closed") or []) == [r4h]
                  and len(_ev(r4, "closed")) == 1
                  and E.Vault(r4root).get(r4h)["fm"]["verdict"] == "invalid-run")))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aresume: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_stops():
    """Spec 05 PRD 05.2 §1.7/§7 — the four ways a run ends, and only those four.

    A run that spends compute unattended needs every exit written down before it starts:
    `success` only after the winning commit re-scores at fresh seeds, `budget` per axis, `abort`
    when the apparatus itself is broken, `stall` when the search has stopped learning.
    Confirmation is the one that matters most — a single crossing of the bar is the result most
    likely to be noise, which is exactly what this null says out loud."""
    print("\n# autopilot — the four stops (spec 05, PRD 05.2)")
    try:
        A = _auto_mod()
        repo, root, qa, isl, hb, rel = _loop_fixture(x0=0)
        ok = _loop_run("success-stop", root, qa, rel)
        st = ok["state"] or {}
        w = (st.get("best") or {}).get("id")
        conf = _ev(ok, "confirm")
        _, mroot, mqa, _, _, mrel = _loop_fixture(
            x0=2, agent="python3 agent.py control", budget_attempts="2",
            scorer="python3 score.py --miss-confirm")
        m = _loop_run("confirm-miss", mroot, mqa, mrel)
        mconf = _ev(m, "confirm")
        check("astop: success stops only after the winning commit re-scores at replicates new seeds, and a missed seed continues the run",
              _auto_ok(lambda: (
                  _loop_stop(ok)["reason"] == "success" and st["confirmed"] == w
                  and _loop_stop(ok)["attempt"] == w and _loop_stop(ok)["axis"] is None
                  and len(conf) == 1 and conf[0]["attempt"] == w
                  and conf[0]["seeds"] == [1, 2] and conf[0]["passed"] is True
                  and all(os.path.isfile(os.path.join(root, E.RESULTS_DIR, w, "confirm",
                                                      str(s), E.METRICS_FILE))
                          for s in (1, 2))
                  and not os.path.exists(os.path.join(root, E.RESULTS_DIR, w, "confirm", "0"))
                  # the winner's own seed-0 document, unchanged by the confirmation: the LAST
                  # `scored` event is the winner's, it carries seed 0, and the file still holds
                  # that value. A confirmation that wrote over it would be a run that could
                  # never be re-read.
                  and _ev(ok, "scored")[-1]["attempt"] == w
                  and _ev(ok, "scored")[-1]["seed"] == 0
                  and _ev(ok, "scored")[-1]["value"] == E.metrics_value(
                      E.load_metrics(root, w), "obj.score", "the winner")
                  and E.Vault(root).get(w)["fm"]["verdict"] == "supported"
                  # a seed that misses is not a stop: the run keeps going to its budget
                  and len(mconf) == 2 and all(e["passed"] is False for e in mconf)
                  # and the seed-0 file is NOT the seed that missed: it still crosses the bar
                  # that every confirmation seed failed to reach
                  and all(E.auto_crosses(E.metrics_value(E.load_metrics(mroot, e["attempt"]),
                                                         "obj.score", "the seed-0 document"),
                                         -0.5, "max")
                          and all(v is not None and not E.auto_crosses(v, -0.5, "max")
                                  for v in e["values"])
                          for e in mconf)
                  and (m["state"] or {})["confirmed"] is None
                  and _loop_stop(m)["reason"] == "budget"
                  and _loop_stop(m)["axis"] == "attempts"
                  and len(_ev(m, "island-best")) == 1)))

        axes = {}
        for name, field, axis in (("budget-attempts", "budget_attempts", "attempts"),
                                  ("budget-hours", "budget_hours", "hours"),
                                  ("budget-calls", "budget_model_calls", "model_calls")):
            _, broot, bqa, _, _, brel = _loop_fixture(
                x0=0, **{field: "0" if axis == "hours" else "1"})
            axes[axis] = _loop_run(name, broot, bqa, brel)
        check("astop: each budget axis stops its own fixture budget, naming the axis",
              _auto_ok(lambda: (
                  E.AUTO_BUDGET_AXES == ("attempts", "hours", "model_calls")
                  and all(_loop_stop(axes[a])["reason"] == "budget"
                          and _loop_stop(axes[a])["axis"] == a for a in E.AUTO_BUDGET_AXES)
                  and len((axes["attempts"]["state"] or {})["closed"]) == 1
                  and _ev(axes["hours"], "attempt-reserved") == []
                  and len(_ev(axes["model_calls"], "worker-started")) == 1
                  # each axis names ITSELF in the detail, in its own units — a stop the PI
                  # reads in the morning has to say which budget ran out, not that one did
                  and _loop_stop(axes["attempts"])["detail"] == "1 of 1 attempts closed"
                  # 05.3 (PRD-6): the axis now counts three roles — the worker, the closer and
                  # the steward — so "worker invocations" would be a false statement in a line
                  # the PI reads in the morning. Only this literal moves.
                  and _loop_stop(axes["model_calls"])["detail"]
                      == "1 of 1 model calls used"
                  and _loop_stop(axes["hours"])["detail"].endswith("driver hours used")
                  and _loop_stop(axes["hours"])["detail"].startswith("0.0")
                  and " of 0 " in _loop_stop(axes["hours"])["detail"]
                  and all(" of " in _loop_stop(axes[a])["detail"]
                          for a in E.AUTO_BUDGET_AXES))))

        _, iroot, iqa, _, _, irel = _loop_fixture(x0=0, agent="python3 agent.py exit1",
                                                  retries="1", abort_invalid_runs="2")
        inv = _loop_run("abort-invalid", iroot, iqa, irel)
        _, oroot, oqa, _, _, orel = _loop_fixture(x0=0,
                                                  scorer="python3 score.py --fail-always")
        opn = _loop_run("fail-open", oroot, oqa, orel)
        ores = _auto_val(lambda: A.reservations(oroot, oqa), {})
        check("astop: consecutive invalid runs, and a scorer failing at run open, each stop the run abort",
              _auto_ok(lambda: (
                  E.AUTO_STOP_REASONS == ("success", "budget", "abort", "stall")
                  and _loop_stop(inv)["reason"] == "abort"
                  and _loop_stop(inv)["axis"] is None
                  and (inv["state"] or {})["consecutive_invalid"] == 2
                  and _loop_stop(inv)["detail"]
                      == "2 invalid runs in a row (abort_invalid_runs 2)"
                  and (inv["state"] or {})["tasks"]["run"]
                  and len((inv["state"] or {})["tasks"]["exceptions"]) == 3
                  and E.AUTO_TASK_CATEGORY in E.task_categories(iroot)
                  and _loop_stop(opn)["reason"] == "abort"
                  and _loop_stop(opn)["detail"].startswith(
                      "the scorer failed on the base commit at run open:")
                  and _ev(opn, "attempt-reserved") == []
                  and not ores
                  and (opn["state"] or {})["closed"] == [])))

        _, nroot, nqa, _, _, nrel = _loop_fixture(x0=0, agent="python3 agent.py still",
                                                  stall_attempts="2", budget_attempts="8")
        n = _loop_run("still", nroot, nqa, nrel)
        nst = n["state"] or {}
        check("astop: a stall escalates exactly once, and a second stall stops the run stall",
              _auto_ok(lambda: (
                  len(_ev(n, "stall")) == 2
                  and [e["count"] for e in _ev(n, "stall")] == [1, 2]
                  and [e["attempts"] for e in _ev(n, "stall")] == [2, 2]
                  and len(_ev(n, "escalated")) == 1
                  and _ev(n, "escalated")[0]["c_puct"] == E.AUTO_C_PUCT["explore"]
                  and nst["c_puct"] == E.AUTO_C_PUCT["explore"]
                  and nst["escalated"] is True and nst["stalls"] == 2
                  and len(nst["closed"]) == 4
                  and _loop_stop(n)["reason"] == "stall"
                  and _loop_stop(n)["detail"]
                      == "no improvement in 2 closed attempts, twice")))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"astop: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_leash():
    """Spec 05 PRD 05.2 §12 — the one place the leash reads differently, and the proof that
    nothing else moved.

    Inside an approved run the driver performs four acts that are the PI's everywhere else. The
    argument for that is narrow and has to stay narrow: what the PI signs is the bar, and in a run
    the bar is signed once, in the flight plan. So the ruling is asserted as text in SKILL.md, and
    the four leash bullets and the `close` row are asserted BYTE-identical — a slice that widened
    the leash by rewording a bullet would pass every other check in this suite."""
    print("\n# autopilot — the leash inside a run (spec 05, PRD 05.2)")
    root = None
    try:
        skill = read(os.path.join(REPO, "skills", "crux", "SKILL.md"))
        flat = " ".join(skill.split())
        fourth = ("gate, draft the synthesis, then stop — `approve` is their signature, not "
                  "yours.")
        ruling = [
            "**Inside an approved autopilot run** — the one place the leash reads differently "
            "(spec 05 §12).",
            "the driver performs four acts per attempt that are the PI's everywhere else: "
            "`hypothesize` (at the id it reserved), `approve-null` (on the plan's null, "
            "verbatim), `test --to running`, and `close`.",
            "The plan's approval covers all four: each attempt closes on its derived verdict "
            "with no per-attempt signature, because what the PI signs is the bar, and in a run "
            "the bar is signed once, in the flight plan, and inherited by every attempt.",
            "Outside an approved autopilot run, nothing changes.",
            "Inside one, `answer`, `approve` on a synthesis, and merging into `main` stay the "
            "PI's.",
        ]
        check("aleash: SKILL.md carries the autopilot ruling naming the four acts, and the close row and four leash bullets are byte-identical",
              all(s in flat for s in ruling)
              and LEASH_BULLETS in skill and CLOSE_ROW in skill
              and flat.find(ruling[0]) > flat.find(fourth)
              and flat.find(ruling[0]) < flat.find("## Setting up a vault (first run)")
              and "| `auto status` | ○ |" in skill
              and "| `auto approve` | ◆ |" in skill
              and "| `auto run` | ◆ |" in skill
              and "Never run this without the PI's yes" in skill
              and "per-attempt signature" in flat)

        # ---------------------------------------- spec 05 PRD 05.3 §H — the fifth act, ruled in
        # The PI ruled the fifth act IN at sign-off, so the leash widens for the first time
        # since 05.2 — and a leash that widens is the one edit in this repo that must be read
        # sentence by sentence rather than diffed. The 05.2 anchor sentences are asserted
        # present AND IN ORDER with the new one between them, because the paragraph is
        # soft-wrapped in the file: the edit re-wraps it, so byte-identity holds
        # sentence-for-sentence, never line-for-line. The four bullets and the `close` row are
        # asserted byte-identical in the ordinary way, since nothing re-wraps them.
        fifth = [
            "In Explore, the approval also covers a fifth act that is not per attempt: `ask` "
            "— opening one new island (a sub-question under the anchor) when the steward "
            "proposes it, up to the plan's `island_cap`, which the PI signed.",
            "It is safe for the reason spec 05 D14 gives: the objective, bar and checks are "
            "frozen, so a new island is another angle on a fixed target.",
        ]
        order = [flat.find(s) for s in ruling[:3] + fifth + ruling[3:]]
        check("aleash: SKILL.md carries the fifth act sentence for sentence, and the four bullets and the close row are byte-identical",
              all(s in flat for s in ruling) and all(s in flat for s in fifth)
              and all(i >= 0 for i in order) and order == sorted(order)
              and LEASH_BULLETS in skill and CLOSE_ROW in skill
              and flat.find(fifth[0]) > flat.find(fourth)
              and flat.find(fifth[-1]) < flat.find("## Setting up a vault (first run)")
              # the probe joins the ○ row rather than becoming a verb of its own: it starts a
              # process, so the row that promises `auto check` starts only the PI's scorer had
              # to say so or stop being true
              and "| `auto check` · `auto brief` | ○ |" in skill
              and "`agent_probe`" in skill
              and "probes each agent command once" in flat
              and "sends no prompt and spends no model call" in flat
              and "`auto check --static` is the lint alone and starts nothing" in flat)

        # --------------------------------------- the hand path, byte for byte, still the same
        base = os.path.realpath(tempfile.mkdtemp(prefix="crux_aleash_"))
        _AUTO_TRASH.append(base)
        root = os.path.join(base, "vault")
        real, out = E.now, {}
        try:
            E.now = lambda: "2026-01-01T00:00:00"
            E.cmd_init("Hand close", root, goal="g")
            q, _ = E.cmd_ask(root, "does x reach 3")
            h, _, _ = E.cmd_hypothesize(
                root, "x = 3", parent=q, rule="all", null=LOOP_NULL,
                verifiables=["obj.score >= -0.5 on the frozen scorer"],
                neutral=["obj.score <= 0 — the objective is never positive"],
                fails_if=["x stays two or more steps away from 3",
                          "the scorer adds a positive offset"],
                discriminates=[True, False])
            E.cmd_approve_null(root, h)
            E.cmd_test(root, h, to="running")
            p, ticked = node_path(root, h), []
            for line in read(p).split("\n"):
                m = re.match(r"^(\s*- \[)(.)(\]\s*)(.*)$", line)
                ticked.append(m.group(1) + "x" + m.group(3) + m.group(4).rstrip()
                              + " (found: 0.0)" if m else line)
            write(p, "\n".join(ticked))
            out["verdict"] = E.cmd_close(root, h, findings="closed by hand")
            out["text"] = read(node_path(root, h))
        finally:
            E.now = real
        check("aleash: a hypothesis closed by hand is byte-identical to the pre-05.2 engine and writes no auto/ file",
              out.get("verdict") == "supported"
              and out.get("text") == HAND_CLOSE_GOLDEN
              and not os.path.isdir(os.path.join(root, E.AUTO_DIR)))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aleash: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_loop_purity():
    """Spec 05 PRD 05.2 §0 — the driver concludes nothing, and the engine still starts nothing.

    Two properties, asserted two ways. The verdict is the engine's: `autopilot.py` may not contain
    a verdict token it assigns, and every attempt a run closed has to carry exactly the verdict
    `derive_verdict_15` gives for its own ticks — a driver that reached the same answer by its own
    route would still be a driver with an opinion. And the 05.1 purity line holds after the loop
    lands: the engine names no git command and starts no process, the driver imports stdlib and the
    engine and nothing else, and `crux auto status` reads a run without loading the module that
    can start one."""
    print("\n# autopilot — the driver has no opinion (spec 05, PRD 05.2)")
    tmp = None
    try:
        ap = os.path.join(HERE, "autopilot.py")
        auto = "\n".join(l for l in read(ap).splitlines()
                         if not l.lstrip().startswith("#")) if os.path.isfile(ap) else ""
        eng = "\n".join(l for l in read(os.path.join(HERE, "engine.py")).splitlines()
                        if not l.lstrip().startswith("#"))
        blind = (r"""["']verdict["']\s*\]\s*=(?!=)""",
                 r"""\bverdict\s*=(?!=)\s*["'](supported|refuted|inconclusive|invalid-run|partial)["']""",
                 r"""["']verdict["']\s*:\s*["'](supported|refuted|inconclusive|invalid-run|partial)["']""",
                 r"\bderive_verdict(_15)?\s*\(", r"\brender_doc\s*\(",
                 r"\bwrite_if_changed\s*\(")
        check("apure: autopilot.py assigns no verdict and every closed attempt's verdict equals derive_verdict_15 over its own node",
              bool(auto)
              and not any(re.search(p, auto) for p in blind)
              and bool(re.search(r"\bcmd_close\s*\(", auto))
              and set(_LOOP_RUNS) >= {"success", "still", "exit1", "crashscore", "frozen"}
              and bool(_LOOP_CLOSED)
              and all(v is not None and v == want for _, v, want in _LOOP_CLOSED))
        allowed = {"os", "sys", "re", "json", "time", "shlex", "socket", "subprocess", "shutil",
                   "tempfile", "datetime", "contextlib", "errno", "stat", "ctypes", "signal",
                   "engine"}
        imports = [m.group(1).split(".")[0] for m in
                   re.finditer(r"^\s*(?:import|from)\s+([\w.]+)", auto, re.M)]
        verbs = (r"""["'](checkout|commit|reset|merge|rebase|push|switch|stash|symbolic-ref|"""
                 r"""cherry-pick)["']""")
        check("apure: engine.py still starts no process and names no git; autopilot.py imports only stdlib (plus signal) and engine",
              bool(auto)
              and not re.search(r"^\s*(import|from)\s+(subprocess|threading|socket|urllib|"
                                r"fcntl|multiprocessing|asyncio|signal)\b", eng, re.M)
              and not re.search(r"\bos\.(system|popen|fork|exec\w*|spawn\w*|posix_spawn\w*)\s*\(",
                                eng)
              and not re.search(r"""["']git["']""", eng)
              and not re.search(r"^\s*(import|from)\s+autopilot\b", eng, re.M)
              and bool(imports) and all(x in allowed for x in imports)
              and not re.search(verbs, auto)
              and "shell=True" not in auto
              and not re.search(r"^(import|from) autopilot",
                                read(os.path.join(HERE, "crux.py")), re.M))
        kills = re.findall(r"os\.killpg\([^\n]*?,\s*([\w.]+)\s*\)", auto)
        check("apure: every process-group kill names the SIGKILL module constant, so a platform without one has no attribute to miss",
              bool(auto) and len(kills) >= 2 and set(kills) == {"SIGKILL"}
              and bool(re.search(r'^SIGKILL\s*=\s*getattr\(signal, "SIGKILL", 9\)',
                                 auto, re.M)))

        # ------------------------------------------------ the JSON surface of the three verbs
        repo, root, qa, isl, hb, rel = _loop_fixture(x0=0, budget_attempts="1")
        _, uroot, uqa, _, _, urel = _loop_fixture(x0=0, _approve=False)

        def cli(*argv, **kw):
            return _auto_val(lambda: subprocess.run(
                [sys.executable, os.path.join(HERE, "crux.py")] + list(argv),
                capture_output=True, cwd=kw.get("cwd") or root, encoding="utf-8",
                errors="replace", timeout=180))

        def j(r):
            return _auto_val(lambda: json.loads(getattr(r, "stdout", "")), {})

        capp = cli("auto", "approve", urel, "--json", cwd=uroot)
        crun = cli("auto", "run", rel, "--json")
        cs1 = cli("auto", "status", "--json")
        cs2 = cli("auto", "status", qa, "--json")
        cs3 = cli("auto", "status")

        sys.path.insert(0, HERE)
        import crux as C
        spawned = []

        def boom(*a, **k):
            spawned.append(a)
            raise AssertionError("process spawned")

        patched = [(m, n) for m, n in ((subprocess, "Popen"), (subprocess, "run"),
                                       (os, "system"), (os, "popen"), (os, "fork"),
                                       (os, "posix_spawn"), (os, "posix_spawnp"),
                                       (os, "spawnv"), (os, "spawnvp"), (os, "execv"),
                                       (os, "execvp")) if hasattr(m, n)]
        saved = [(m, n, getattr(m, n)) for m, n in patched]
        cwd = os.getcwd()
        before = _auto_val(lambda: _byte_map(root), {})
        rc, out = None, ""
        try:
            for m, n, _ in saved:
                setattr(m, n, boom)
            if root:
                os.chdir(root)
            buf = io.StringIO()
            try:
                with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
                    rc = C.main(["auto", "status", "--json"])
            except SystemExit as e:
                rc = e.code
            except Exception as e:                           # pragma: no cover - wave-1 guard
                rc = repr(e)
            out = buf.getvalue()
        finally:
            for m, n, fn in saved:
                setattr(m, n, fn)
            os.chdir(cwd)
        after = _auto_val(lambda: _byte_map(root), {})
        check("acli: auto run, auto status and auto approve emit JSON under --json, and auto status starts no process and writes nothing",
              _auto_ok(lambda: (
                  capp.returncode == 0
                  and set(j(capp)) == {"plan", "approved", "approved_hash", "already"}
                  and crun.returncode == 0 and set(j(crun)) == set(E.AUTO_STATE_KEYS)
                  and j(crun)["stop"]["reason"] == "budget"
                  and cs1.returncode == 0 and cs2.returncode == 0
                  and set(j(cs1)) == set(j(cs2)) == {"anchor", "state", "events", "last_event"}
                  and j(cs1)["anchor"] == qa
                  and j(cs1)["events"] == j(cs1)["state"]["events"]
                  and j(cs1)["last_event"]["event"] == "stop"
                  and cs3.returncode == 0
                  and f"{E.AUTO_DIR}/{qa}/{E.AUTO_STATE_FILE}" in cs3.stdout
                  and spawned == [] and rc == 0
                  and _auto_val(lambda: json.loads(out), {}).get("anchor") == qa
                  and bool(before) and before == after)))

        # ------------------------------- a vault that never met autopilot, left exactly alone
        tmp = tempfile.mkdtemp(prefix="crux_anoauto2_")
        dst = os.path.join(tmp, "demo")
        shutil.copytree(os.path.join(REPO, "skills", "crux", "examples", "demo_vault"), dst)
        ns = cli("auto", "status", cwd=dst)
        check("acli: auto status on a vault with no auto/ directory refuses and creates nothing",
              _auto_ok(lambda: (
                  ns.returncode == 1
                  # the LAST line: `auto status` is a read-only verb and warns about engine
                  # drift above its refusal exactly as every other read-only verb does
                  and ns.stderr.strip().splitlines()[-1]
                      == ("crux: auto status: no autopilot run in this vault "
                          "(auto/<qid>/state.json)")
                  and all("engine drift" in l for l in ns.stderr.strip().splitlines()[:-1])
                  and not os.path.isdir(os.path.join(dst, E.AUTO_DIR)))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"apure: section ran without crashing ({e!r})", False)
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)
        _auto_sweep()


# ===========================================================================================
# spec 05 PRD 05.3 — the agents. Written BLIND, against the PRD and the interface contract,
# before any of it existed. Every fixture here is a tier-zero repository plus ONE stub agent
# committed under several names: the command list is shared by all three roles, so the only
# honest way to make one role unable to start is to give the list a filename that exists for
# some roles and not for others.
# ===========================================================================================

# The one stub. It reads `CRUX_AGENT` to learn which role the driver is invoking and REFUSES a
# role the engine does not name — a driver that forgot the variable fails loudly here instead
# of quietly running a worker where a closer was meant. Its three mode arguments are positional
# (worker, closer, steward) so one `agent:` field configures all three roles at once.
AG_STUB_PY = '''import json, os, subprocess, sys
GIT = ["git", "-c", "user.name=crux-stub", "-c", "user.email=stub@crux.invalid",
       "-c", "commit.gpgsign=false", "-c", "core.hooksPath="]
argv = sys.argv[1:]
if "--version" in argv:                 # the probe: no prompt, no CRUX_* variable, exit 0
    sys.stdout.write("crux stub agent 1.0\\n")
    sys.exit(0)
role = os.environ.get("CRUX_AGENT") or ""
LIMIT = "You have reached your 5-hour limit\\n"


def arg(i, d):
    return argv[i] if len(argv) > i else d


def brief_has(*words):
    with open(os.environ["CRUX_BRIEF"], encoding="utf-8") as f:
        t = f.read()
    return all(w in t for w in words)


def put(obj):
    with open(os.environ["CRUX_PROPOSAL"], "w", encoding="utf-8") as f:
        json.dump(obj, f)


def put_raw(b):                         # bytes a model wrote, not text the harness encoded
    with open(os.environ["CRUX_PROPOSAL"], "wb") as f:
        f.write(b)


if role == "crux-auto-worker":
    mode = arg(0, "step")
    if not brief_has("## Objective"):
        sys.exit(7)
    if mode in ("limited", "limitedok"):
        sys.stderr.write(LIMIT)
        if mode == "limited":
            sys.exit(1)
    if mode == "boom":                  # fails, and says NOTHING about any rate limit
        sys.stderr.write("Traceback (most recent call last): a short unrelated failure\\n")
        sys.exit(3)
    with open("params.json", encoding="utf-8") as f:
        x = json.load(f)["x"]
    if mode != "still":
        x = x + (1 if x < 3 else (-1 if x > 3 else 0))
    with open("params.json", "w", encoding="utf-8") as f:
        json.dump({"x": x}, f)
    subprocess.run(GIT + ["commit", "-a", "-q", "--allow-empty", "-m",
                          "attempt " + os.environ["CRUX_ATTEMPT"]], check=True)
    put({"claim": "x = %s" % x})
    sys.exit(0)

if role == "crux-close":
    mode = arg(1, "valid")
    if not brief_has("## Checks", "## Results", "## Attempt"):
        sys.exit(7)
    if not os.path.isdir(os.environ.get("CRUX_RESULTS") or ""):
        sys.exit(8)
    if mode == "silent":
        sys.exit(0)
    if mode == "limited":
        sys.stderr.write(LIMIT)
        sys.exit(1)
    if mode == "bytes":                 # one byte that is not valid UTF-8
        put_raw(b'{"ticks": {"2": "x"}, "findings": "the caf\\xe9 control reproduced", '
                b'"report": "# r"}')
        sys.exit(0)
    prop = {"ticks": {"1": "x", "2": "x"},
            "findings": "the change moved the objective to the bar, and the baseline re-ran "
                        "to the same number, so the control held",
            "report": "# the closer's report\\n\\nthe closer wrote this line\\n"}
    if mode == "malformed":
        prop["verdict"] = "supported"
    if mode == "contradicting":
        prop["ticks"] = {"1": " ", "2": "x"}
    put(prop)
    sys.exit(0)

if role == "crux-auto-steward":
    mode = arg(2, "guidance")
    if not brief_has("## Islands", "## Budget", "## Ledger"):
        sys.exit(7)
    n = os.path.basename(os.environ["CRUX_WORKSPACE"].rstrip("/\\\\"))
    if mode == "alternate":                    # bad schema first, then nothing at all
        mode = "badkey" if n == "1" else "silent"
    if mode == "silent":
        sys.exit(0)
    if mode == "bytes":                 # one byte that is not valid UTF-8
        put_raw(b'{"guidance": "prefer caf\\xe9 one-step moves near the bar"}')
        sys.exit(0)
    prop = {}
    if mode in ("guidance", "badkey"):
        prop["guidance"] = ("prefer one-step moves once the objective is within a step of "
                            "the bar")
    if mode == "badkey":
        prop["verdict"] = "supported"
    if mode == "island":
        prop["island"] = {
            "title": "a cheaper surrogate for the frozen objective",
            "problem": "the scorer dominates the cost of every attempt, so a surrogate that "
                       "ranks candidates the same way would let the search take more steps "
                       "for the same budget"}
    put(prop)
    sys.exit(0)

sys.stderr.write("CRUX_AGENT is %r\\n" % role)
sys.exit(9)
'''

# One prose control, so the plan carries a check no number can grade. This is the plan 05.2
# refuses under `check-grammar` and 05.3 accepts when — and only when — a closer is on.
AG_PROSE_VERIFIABLES = ("- [ ] obj.score >= -0.5 on the frozen scorer\n"
                        "      fails-if:: x stays two or more steps away from 3\n"
                        "      discriminates:: true\n"
                        "- [ ] [outcome-neutral] the baseline reproduces\n"
                        "      fails-if:: the scorer adds a positive offset\n")

# `dispatch.py` is the name a command list uses for every role, and `probe.py` is the same
# program under the name the probe criteria read. A role that cannot START is not made so by a
# missing file — `python3 <missing>.py` starts — but by `_ag_no_start`.
AG_ALL_STUBS = ("dispatch.py", "probe.py")
AG_STUB_ARGS = "step valid guidance"          # worker, closer, steward — all three positional

# A command that CANNOT START is one whose argv[0] is not a program on this machine. `python3
# no_such.py` is not one of those: `python3` exists, so the child starts and exits 2, and §3.1
# says the exit code is not read.
AG_NO_SUCH_BINARY = "no_such_agent_binary"

# Two commands that the PROBE can start and the WORKER cannot: scripts in the repository's
# working tree that were never committed. The probe runs with the repository as its cwd, and an
# attempt worktree is cut from a commit — so the same relative argv[0] resolves for one and not
# for the other. This is the only shape that reaches §3.3's abort, because `auto_probe_argv` and
# `auto_agent_argv` share argv[0] and §3.9 otherwise aborts the run first.
AG_UNCOMMITTED = ("./uncommitted_a.sh", "./uncommitted_b.sh")
AG_UNCOMMITTED_SH = "#!/bin/sh\nexit 0\n"


def _ag_uncommitted(repo):
    """Write `AG_UNCOMMITTED` into the repository's working tree and leave them uncommitted."""
    for name in AG_UNCOMMITTED:
        if not repo:                                         # pragma: no cover - wave-1 guard
            return
        p = os.path.join(repo, name.lstrip("./"))
        write(p, AG_UNCOMMITTED_SH)
        os.chmod(p, 0o755)


def _ag_fixture(stubs=AG_ALL_STUBS, **kw):
    """A tier-zero fixture with the stub agent COMMITTED under each name in `stubs`.

    Committed, not merely written: the worker runs in a git worktree cut from the base commit,
    so a file that only the repository's working tree carries does not exist where the worker
    runs. The closer and the steward run in the repository itself and would not have noticed —
    which is exactly the kind of difference a fixture must not hide."""
    return _loop_fixture(_files={n: AG_STUB_PY for n in stubs}, **kw)


def _ag_spawns(A):
    """Watch `_spawn`, so every child the driver starts is recorded with its argv and its whole
    environment. Returns (restore, records).

    §0 promises `_spawn` is resolved by module-global name at call time for exactly this
    reason. The alternative — having the stub write its environment down — cannot see a role
    that never started, which is half of what this slice is about."""
    seen = []
    orig = _auto_val(lambda: A._spawn)
    if orig is None:                                         # pragma: no cover - wave-1 guard
        return (lambda: None), seen

    def rec(argv, cwd, env, log_path, *a, **k):
        seen.append({"argv": list(argv), "env": dict(env or {}), "cwd": cwd})
        return orig(argv, cwd, env, log_path, *a, **k)

    A._spawn = rec

    def restore():
        A._spawn = orig
    return restore, seen


def _ag_no_start(A, role):
    """Make every spawn for ONE role fail the way the kernel does when argv[0] is not a program.

    No command string can do this. `auto_probe_argv` and `auto_agent_argv` share argv[0], so a
    command the closer or the steward cannot start is one the run-open probe cannot start
    either, and §3.9 aborts the whole run before any agent walks — a different criterion. §0
    makes `_spawn` replaceable by module-global name for exactly this injection, and everything
    downstream of it — the walk, the failover, the retry, the give-up — is the driver's own."""
    orig = _auto_val(lambda: A._spawn)
    if orig is None:                                         # pragma: no cover - wave-1 guard
        return lambda: None

    def rec(argv, cwd, env, log_path, *a, **k):
        if (env or {}).get("CRUX_AGENT") == role:
            raise OSError(2, "No such file or directory")
        return orig(argv, cwd, env, log_path, *a, **k)

    A._spawn = rec

    def restore():
        A._spawn = orig
    return restore


def _ag_role(seen, role):
    """Every recorded spawn whose `CRUX_AGENT` names one role, in the order it was started."""
    return [s for s in seen if s["env"].get("CRUX_AGENT") == role]


def _ag_env_names(rec):
    """The `CRUX_*` names the DRIVER put in a child's environment — added, or given a value of
    its own.

    Every child env is built from `dict(os.environ)`, and this suite's own process carries
    `CRUX_NO_UPDATE_CHECK` (set in `main()`), so a bare `startswith("CRUX_")` reports a
    harness variable as if the driver had set it. Comparing each value against the suite's own
    environment is what makes this a statement about the driver and not about the machine."""
    return sorted(k for k, v in (rec or {}).get("env", {}).items()
                  if k.startswith("CRUX_") and os.environ.get(k) != v)


def _ag_derived(root, hid):
    """`derive_verdict_15` over one closed node's OWN ticks — the engine's truth table applied
    to the file, never the verdict the driver wrote into it. The driver supplies ticks and
    never a verdict, and this is the only way to say so about a merged tick vector."""
    n = E.Vault(root).get(hid)
    by = E.count_verifiables_by_kind(n["body"])
    return E.derive_verdict_15(by[E.DEFAULT_KIND], by[E.NEUTRAL_KIND], *E.node_rule(n))


def _ag_ticked(root, hid, text):
    """The one `- [t] … (found: …)` line of a closed node whose verifiable text contains
    `text`, or "" — so a test can say which tick a check carries and where it came from."""
    for line in read(node_path(root, hid)).splitlines():
        if text in line and re.match(r"^\s*- \[.\]", line):
            return line.strip()
    return ""


def run_auto_agents():
    """Spec 05 PRD 05.3 §B/§C — one command list, walked once per try.

    `agent:` and `agent_failover:` stop being two fields and become one ordered list, and the
    unit of a try stops being a command. That distinction is the whole feature: a command that
    never became a process cannot have spent a token and cannot have produced a wrong answer,
    so walking past it charges neither a model call nor a retry. Charge it either way and a
    machine with a misspelled failover burns its retry budget on typing."""
    print("\n# autopilot — the command list and the walk (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # ------------------------------------------------ the list, the argv, the eight names
        cl = _auto_val(lambda: E.auto_command_list(
            {"agent": "a one", "agent_failover": ["b two", "c three"]}), [])
        cl1 = _auto_val(lambda: E.auto_command_list({"agent": "a one", "agent_failover": []}), [])
        cl0 = _auto_val(lambda: E.auto_command_list({"agent": "a one"}), [])
        sub = _auto_val(lambda: E.auto_agent_argv(
            'claude -p --agent {agent} "{brief}"', "crux-close", "read this"), [])
        # `{agent}` substitutes BEFORE `{brief}`, so a brief that happens to contain the token
        # is not re-scanned. The brief is text a model wrote; treating it as a template is how
        # an agent talks the driver into running a different agent.
        order = _auto_val(lambda: E.auto_agent_argv(
            "run {brief}", "crux-auto-worker", "mind the {agent} token"), [])
        empty = _auto_val(lambda: E.auto_agent_argv("", "crux-auto-worker", "b"), None)
        raised = []
        try:
            E.auto_agent_argv('python3 "unclosed', "crux-auto-worker", "b")
        except ValueError:
            raised.append("ValueError")
        except Exception as e:                               # pragma: no cover - wave-1 guard
            raised.append(repr(e))

        # One fixture, all three roles, every child's environment recorded. `budget_attempts=2`
        # so the steward's window can close between two attempts and still be inside budget.
        tr = _ag_fixture(x0=0, mode="explore", closer="true", steward="true",
                         steward_every="1", budget_attempts="2", retention="all",
                         agent="python3 dispatch.py " + AG_STUB_ARGS,
                         verifiables=AG_PROSE_VERIFIABLES)
        trestore, trseen = (lambda: None), []
        if tr[0]:
            trestore, trseen = _ag_spawns(A)
        try:
            three = _loop_run("three-roles", tr[1], tr[2], tr[5])
        finally:
            trestore()
        wk = _ag_role(trseen, "crux-auto-worker")
        cw, sw = _ag_role(trseen, "crux-close"), _ag_role(trseen, "crux-auto-steward")

        check("aagent: the command list is agent then agent_failover, {brief} and {agent} substitute anywhere, and the seven worker variables are byte-identical",
              _auto_ok(lambda: (
                  E.AUTO_AGENTS == ("crux-auto-worker", "crux-close", "crux-auto-steward")
                  and cl == ["a one", "b two", "c three"]
                  and cl1 == ["a one"] and cl0 == ["a one"]
                  and sub == ["claude", "-p", "--agent", "crux-close", "read this"]
                  and order == ["run", "mind the {agent} token"]
                  and empty == []
                  and raised == ["ValueError"]
                  # 05.2's seven, byte-identical in NAME, plus exactly one more
                  and _ag_env_names(wk[0]) == ["CRUX_AGENT", "CRUX_ATTEMPT", "CRUX_BRIEF",
                                               "CRUX_PROPOSAL", "CRUX_RUN", "CRUX_SEED",
                                               "CRUX_WORKSPACE", "CRUX_WORKTREE"]
                  and wk[0]["env"]["CRUX_AGENT"] == "crux-auto-worker"
                  and wk[0]["env"]["CRUX_SEED"] == "0"
                  and wk[0]["env"]["CRUX_RUN"] == "python3 train.py"
                  and wk[0]["env"]["CRUX_ATTEMPT"] in (three["state"] or {}).get("closed", [])
                  and wk[0]["env"]["CRUX_BRIEF"]
                      == os.path.join(wk[0]["env"]["CRUX_WORKSPACE"], A.BRIEF_NAME)
                  and os.path.realpath(wk[0]["cwd"])
                      == os.path.realpath(wk[0]["env"]["CRUX_WORKTREE"]))))

        # ------------------------------------- the first command cannot start, the second can
        # `python3 no_such_agent.py` STARTS — `python3` exists, and §3.1 says a command that
        # started is reachable whatever it then exits with. A command that cannot start is one
        # whose argv[0] is not a program on this machine.
        fs = _ag_fixture(x0=0, budget_attempts="1",
                         agent=AG_NO_SUCH_BINARY + " step",
                         agent_failover="python3 dispatch.py " + AG_STUB_ARGS)
        start = _loop_run("failover-start", fs[1], fs[2], fs[5])
        fo = _ev(start, "failover")
        sst = start["state"] or {}
        check("aagent: a first command that cannot start runs the next one, logging one failover, and the attempt closes on the second command's commit",
              _auto_ok(lambda: (
                  bool(sst.get("closed"))
                  and len(fo) == len(_ev(start, "worker-started"))
                  and all(set(e) >= {"at", "event", "role", "command", "reason", "detail",
                                     "next"} for e in fo)
                  and all(e["role"] == "crux-auto-worker" for e in fo)
                  and all(e["command"] == AG_NO_SUCH_BINARY + " step" for e in fo)
                  and all(e["reason"] == "start" for e in fo)
                  and all(e["next"] == "python3 dispatch.py " + AG_STUB_ARGS for e in fo)
                  and all("worker cannot start" in e["detail"] for e in fo)
                  and all(AG_NO_SUCH_BINARY in e["detail"] for e in fo)
                  and _ev(start, "retry") == []
                  and all(E.Vault(fs[1]).get(h)["fm"].get("verdict")
                          for h in sst["closed"]))))

        # the charging rule, on the fixture that ran all three roles
        calls = _ag_fixture(x0=0, budget_model_calls="1",
                            agent="python3 dispatch.py " + AG_STUB_ARGS)
        cax = _loop_run("calls-axis", calls[1], calls[2], calls[5])
        check("aagent: a failover charges no model call and no retry, a spawned try charges both, a closer and a steward charge one each, and the axis detail reads model calls used",
              _auto_ok(lambda: (
                  # a walk past a command that never became a process costs nothing
                  bool(fo) and _ev(start, "retry") == []
                  and sst["budget"]["model_calls"]["used"]
                      == len(_ev(start, "worker-started"))
                  # one charge per child actually spawned, across all three roles
                  and len(wk) >= 1 and len(cw) >= 1 and len(sw) >= 1
                  and len(cw) == len(wk)
                  and (three["state"] or {})["budget"]["model_calls"]["used"]
                      == len(wk) + len(cw) + len(sw)
                  and len(_ev(three, "closer")) == len(cw)
                  and len(_ev(three, "steward")) == len(sw)
                  and _loop_stop(cax)["reason"] == "budget"
                  and _loop_stop(cax)["axis"] == "model_calls"
                  # the literal lives once, in `astop:`; here it is DERIVED from the axis name
                  # so the foreman's one-literal grep stays true of this file
                  and _loop_stop(cax)["detail"]
                      == "1 of 1 %s used" % E.AUTO_BUDGET_AXES[2].replace("_", " "))))

        # ------------------------------------------------ every command in the list is broken
        # §3.3's abort has exactly one live path. `auto_probe_argv` and `auto_agent_argv` share
        # argv[0], so a command the run-open probe cannot start aborts the run under §3.9
        # first, with no walk and no failover at all. The command that reaches the walk is one
        # whose argv[0] resolves where the PROBE runs — the repository — and not where the
        # WORKER runs: a script written into the repository's working tree and never committed.
        # An attempt worktree is cut from a commit, so it does not carry the file.
        fa = _ag_fixture(x0=0, abort_invalid_runs="1", agent_probe_timeout="2",
                         agent=AG_UNCOMMITTED[0] + " step",
                         agent_failover=AG_UNCOMMITTED[1] + " step")
        _ag_uncommitted(fa[0])
        allbad = _loop_run("failover-all", fa[1], fa[2], fa[5])
        afo, ab = _ev(allbad, "failover"), _ev(allbad, "abandoned")
        check("aagent: every command failing to start stops the run abort, naming each command and its reason",
              _auto_ok(lambda: (
                  len(afo) == 2
                  and [e["command"] for e in afo] == [AG_UNCOMMITTED[0] + " step",
                                                      AG_UNCOMMITTED[1] + " step"]
                  and [e["next"] for e in afo] == [AG_UNCOMMITTED[1] + " step", None]
                  and _loop_stop(allbad)["reason"] == "abort"
                  and _loop_stop(allbad)["axis"] is None
                  and _loop_stop(allbad)["detail"].startswith(
                      "every agent command failed to start: ")
                  and all(c + " step" in _loop_stop(allbad)["detail"]
                          for c in AG_UNCOMMITTED)
                  # a list that cannot start is not a worker that failed: no node is filed,
                  # nothing is retried, and the in-flight attempt is abandoned by the stop
                  and _ev(allbad, "node-filed") == []
                  and _ev(allbad, "retry") == []
                  and (allbad["state"] or {})["closed"] == []
                  and len(ab) == 1 and ab[0]["reason"] == "stop")))

        # ----------------------------------------- PRD-33: a 05.2 plan, untouched, still runs
        # The unrun COPY is the control, not a capture taken before the run: `auto_brief`'s
        # payload legitimately moves as a search progresses (`budget.attempts.used`, and every
        # other island's `migration` row), so the only honest comparison is the same call on a
        # fixture the driver never touched.
        cf = _loop_fixture(x0=0)
        ccopy = _loop_copy(cf)
        compat = _loop_run("compat", cf[1], cf[2], cf[5])
        cst = compat["state"] or {}
        pl = _loop_load_plan(cf[1], cf[2]) or {}
        b_run = _auto_val(lambda: E.auto_brief(cf[1], cf[4]))
        b_unrun = _auto_val(lambda: E.auto_brief(ccopy[1], ccopy[4]))
        check("arun: a 05.2 flight plan with no closer, no cooldown and no probe validates, runs and closes exactly as before",
              _auto_ok(lambda: (
                  # the four new fields default without being written down anywhere
                  pl["closer"] is False
                  and pl["agent_failover"] == []
                  and pl["agent_cooldown"] == E.AUTO_COOLDOWN_DEFAULT
                  and pl["agent_probe"] == E.AUTO_PROBE_DEFAULT
                  and pl["agent_probe_timeout"] == E.AUTO_PROBE_TIMEOUT_DEFAULT
                  and _plan_msgs(cf[1], _loop_plan_text(cf[2], cf[4]), cf[5]) == []
                  # and the run is a 05.2 run: nothing new in the ledger, nothing new on disk
                  and bool(cst.get("closed"))
                  and _loop_stop(compat)["reason"] in E.AUTO_STOP_REASONS
                  and _ev(compat, "failover") == [] and _ev(compat, "cooldown") == []
                  and _ev(compat, "closer") == [] and _ev(compat, "steward") == []
                  and cst["agents"] == {}
                  and cst["steward"] == {"guidance": [], "invocations": 0, "islands": [],
                                         "last_closed": 0}
                  and all(E.Vault(cf[1]).get(h)["fm"].get("verdict")
                          == _ag_derived(cf[1], h) for h in cst["closed"])
                  # `auto_brief(root, hid)` with no island is byte-identical to 05.2's
                  and b_run is not None and b_unrun is not None
                  and b_run["island"]["id"] == cf[2]
                  and b_run["steward"] == [] and b_unrun["steward"] == []
                  and set(b_run) == set(b_unrun)
                  and _brief_fixed_run(b_run) == _brief_fixed_run(b_unrun))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aagent: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_cooldown():
    """Spec 05 PRD 05.3 §C — a rate limit is a wait, not a failure.

    The distinction the driver has to get right is between an agent that is broken and an agent
    that is merely out of quota for the next hour. A broken agent should be walked past; a
    limited one should be come back to, and the run should still be there when it is. So the
    read is on a FAILED try's log only — an agent that mentions a rate limit in a transcript it
    then commits over must not be able to move the driver — and the wait re-evaluates the stop
    on every poll, so a night lost entirely to limits ends on the budget rather than hanging."""
    print("\n# autopilot — the rate-limit cooldown (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # ----------------------------------------------------- the pattern read, on its own
        lim = [_auto_val(lambda: E.auto_rate_limited(t), "<absent>") for t in (
            "You have reached your 5-hour limit", "5hour limit", "Usage Limit exceeded",
            "resets at 3pm", "Please try again later.")]
        neg = [_auto_val(lambda: E.auto_rate_limited(t), "<absent>")
               for t in ("limit", "", None)]
        check("acool: the rate-limit read is the era skill's seven patterns, case-insensitive, and total",
              _auto_ok(lambda: (
                  len(E.AUTO_RATE_LIMIT_PATTERNS) == 7
                  and E.AUTO_RATE_LIMIT_PATTERNS == (
                      r"5-?hour limit", r"usage limit", r"rate limit", r"limit reached",
                      r"too many requests", r"reset[s]? at", r"please try again later")
                  and lim == [True] * 5 and neg == [False] * 3
                  and E.AUTO_COOLDOWN_DEFAULT == 1800.0)))

        # --------------------------------- a failed try whose tail matches: cool, then walk on
        cf = _ag_fixture(x0=0, retries="1", agent_cooldown="0.2", budget_attempts="1",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py " + AG_STUB_ARGS)
        fail = _loop_run("cool-fail", cf[1], cf[2], cf[5])
        cool, fo = _ev(fail, "cooldown"), _ev(fail, "failover")
        fst = fail["state"] or {}
        head = "python3 dispatch.py limited valid guidance"
        check("acool: a failed try whose log tail matches a rate-limit pattern cools that command and re-runs the try on the next, with cooldown then failover",
              _auto_ok(lambda: (
                  len(cool) == 1 and cool[0]["command"] == head
                  and cool[0]["role"] == "crux-auto-worker"
                  and set(cool[0]) >= {"at", "event", "role", "command", "until", "seconds",
                                       "detail"}
                  and float(cool[0]["seconds"]) == 0.2
                  and "rate-limit pattern" in cool[0]["detail"]
                  and cool[0]["until"] == fst["agents"][head]["cooling_until"]
                  and fst["agents"][head]["hits"] == 1
                  # the order is the whole point: the cooldown is written, and only then does
                  # the retry walk past the command it just put to sleep
                  and [e["event"] for e in fail["events"]
                       if e["event"] in ("cooldown", "failover")][:2]
                      == ["cooldown", "failover"]
                  and len(fo) == 1 and fo[0]["command"] == head
                  # a command walked past because it is cooling is a failover of its own kind,
                  # so the two lines read as one story rather than as two unrelated events
                  and fo[0]["reason"] == "cooldown"
                  and fo[0]["next"] == "python3 dispatch.py " + AG_STUB_ARGS
                  and "cooling until" in fo[0]["detail"]
                  and len(_ev(fail, "retry")) == 1
                  and bool(fst.get("closed")))))

        # ------------------------------------------ the negative case: a SUCCESSFUL try's log
        ok = _ag_fixture(x0=0, budget_attempts="1", agent_cooldown="0.2",
                         agent="python3 dispatch.py limitedok valid guidance")
        good = _loop_run("cool-ok", ok[1], ok[2], ok[5])
        gst = good["state"] or {}
        check("acool: a successful try whose log carries the same pattern closes normally, with no cooldown and no failover",
              _auto_ok(lambda: (
                  _ev(good, "cooldown") == [] and _ev(good, "failover") == []
                  and gst["agents"] == {}
                  and len(gst["closed"]) == 1
                  and _ev(good, "retry") == []
                  and E.Vault(ok[1]).get(gst["closed"][0])["fm"].get("verdict")
                      not in (None, "", "invalid-run"))))

        # ------------------------------- after the window lapses, the head of the list is back
        lp = _ag_fixture(x0=0, budget_attempts="2", retries="1", agent_cooldown="0.2",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py " + AG_STUB_ARGS)
        lapse = _loop_run("cool-lapse", lp[1], lp[2], lp[5])
        starts = _ev(lapse, "worker-started")
        # the cooldown is absolute wall-clock in state.json, so it has to survive the process
        kf = _ag_fixture(x0=0, budget_attempts="1", retries="1", agent_cooldown="600",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py " + AG_STUB_ARGS)
        killed = _loop_run("cool-kill", kf[1], kf[2], kf[5])
        kst = killed["state"] or {}
        reread = _auto_val(lambda: json.loads(read(_loop_state_path(kf[1], kf[2]))), {})
        check("acool: after a cooldown lapses the next try starts at the head of the list, and a cooldown survives a kill and resume",
              _auto_ok(lambda: (
                  # every try walks the list from the top, so the preferred command comes back
                  # by itself the moment its window lapses — there is no probe schedule
                  len(starts) >= 2
                  and len(_ev(lapse, "cooldown")) >= 1
                  and len((lapse["state"] or {})["closed"]) >= 1
                  # the stamp is absolute and on disk, so a second reader agrees with the first
                  and reread.get("agents") == kst["agents"]
                  and all(isinstance(r.get("cooling_until"), str)
                          and len(r["cooling_until"]) >= 19
                          and r["cooling_until"] > "2026-"
                          for r in kst["agents"].values())
                  and bool(kst["agents"]))))

        # ------------------------------------------- every command cooling: wait, never abort
        # `abort_invalid_runs` is lifted clear of the way: LOOP_PLAN's 2 aborts the run on two
        # failed tries BEFORE the driver ever has to wait, so the criterion would pass on a
        # driver that never waited at all.
        wt = _ag_fixture(x0=0, retries="0", budget_hours="1", budget_attempts="2",
                         abort_invalid_runs="9", agent_cooldown="0.2",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py limited valid guidance")
        # A spy on the wait itself: `cooldown >= 1` and `reason != abort` hold on a driver that
        # walked past both commands and never waited, so neither is evidence of a wait.
        waits = []
        worig = _auto_val(lambda: A._wait_for_cooldown)
        if worig is not None:
            def _wrec(ctx, commands, _o=worig):
                waits.append(list(commands))
                return _o(ctx, commands)
            A._wait_for_cooldown = _wrec
        try:
            wait = _loop_run("cool-wait", wt[1], wt[2], wt[5])
        finally:
            if worig is not None:
                A._wait_for_cooldown = worig
        bt = _ag_fixture(x0=0, retries="0", budget_hours="0", agent_cooldown="600",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py limited valid guidance")
        bud = _loop_run("cool-budget", bt[1], bt[2], bt[5])
        check("acool: every command cooling makes the driver wait rather than abort, and a cooldown outlasting budget_hours stops budget",
              _auto_ok(lambda: (
                  # a rolling limit is the interruption this feature exists to survive, so the
                  # driver waits; the ONLY way out of the wait is a stop it re-evaluates
                  len(_ev(wait, "cooldown")) >= 1
                  # the wait was ENTERED, over the whole list, and the walk then recorded the
                  # command it stepped past because that command was cooling
                  and len(waits) >= 1
                  and all(len(c) == 2 for c in waits)
                  and _loop_stop(wait)["reason"] != "abort"
                  and _loop_stop(wait)["reason"] in E.AUTO_STOP_REASONS
                  and _loop_stop(bud)["reason"] == "budget"
                  and _loop_stop(bud)["axis"] == "hours"
                  and _loop_stop(bud)["detail"].endswith("driver hours used")
                  and _loop_lock_free(A, wt[1]))))

        # ------------------- the tail a cooldown reads is the one THIS try wrote, and no more
        lt = os.path.realpath(tempfile.mkdtemp(prefix="crux_ltail_"))
        _AUTO_TRASH.append(lt)
        with open(os.path.join(lt, A.WORKER_LOG), "wb") as f:
            f.write(b"You have reached your 5-hour limit\n")
        loff = os.path.getsize(os.path.join(lt, A.WORKER_LOG))
        with open(os.path.join(lt, A.WORKER_LOG), "ab") as f:
            f.write(b"Traceback: a short unrelated failure\n")
        whole = _auto_val(lambda: A._log_tail(lt), "")
        mine = _auto_val(lambda: A._log_tail(lt, since=loff), "")
        # try 1 is rate-limited on the head command and cools it; the retry walks past it and
        # runs the OTHER command, which fails for a reason of its own — a short one, well
        # inside the window try 1 left behind in the same appended log
        sl = _ag_fixture(x0=0, retries="1", agent_cooldown="600", budget_attempts="1",
                         abort_invalid_runs="9",
                         agent="python3 dispatch.py limited valid guidance",
                         agent_failover="python3 dispatch.py boom valid guidance")
        stale = _loop_run("cool-stale-tail", sl[1], sl[2], sl[5])
        sast = (stale["state"] or {}).get("agents") or {}
        check("acool: a cooldown reads only the output of the try that failed, so an earlier try's limit never cools a later command",
              _auto_ok(lambda: (
                  "5-hour limit" in whole and "unrelated failure" in whole
                  and "5-hour limit" not in mine and "unrelated failure" in mine
                  and E.auto_rate_limited(whole) and not E.auto_rate_limited(mine)
                  # the healthy failover command is NOT asleep on evidence that belongs to
                  # the command before it
                  and list(sast) == ["python3 dispatch.py limited valid guidance"]
                  and "python3 dispatch.py boom valid guidance" not in sast
                  and len(_ev(stale, "cooldown")) == 1
                  and len(_ev(stale, "worker-started")) == 2)))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"acool: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_probe():
    """Spec 05 PRD 05.3 §D — is the agent even there, asked before anything is spent.

    A misspelled agent command is the cheapest possible failure to find and the most expensive
    one to find late: found at run open it costs nothing, found after the first reservation it
    has burned a hypothesis number that can never be handed out again. So `auto check` probes
    each command once with a prompt-free argument, and `auto run` does the same before it
    reserves any id. Two slugs, because the two faults are different in kind: a command that
    does not parse is a static fact about the plan text, and a command that will not start is
    a fact about this machine right now."""
    print("\n# autopilot — the agent probe (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # ------------------------------------------- the argv rule, as its five pinned rows
        rows = (('claude -p --agent {agent} "{brief}"', ["claude", "-p", "--version"]),
                ('claude -p "{brief}"', ["claude", "-p", "--version"]),
                ("python3 agent.py step", ["python3", "agent.py", "step", "--version"]),
                ("claude -p --agent {agent} --file {brief}", ["claude", "-p", "--version"]),
                ("", ["--version"]))
        got = [_auto_val(lambda c=c: E.auto_probe_argv(c, "--version"), "<absent>")
               for c, _w in rows]
        for i, (c, want) in enumerate(rows):
            check(f"aprobe: the probe argv of {c!r} under --version is {want}",
                  got[i] == want)
        check("aprobe: the probe defaults are --version and twenty seconds, and an unparseable command propagates ValueError",
              _auto_ok(lambda: (
                  E.AUTO_PROBE_DEFAULT == "--version"
                  and E.AUTO_PROBE_TIMEOUT_DEFAULT == 20.0
                  and _auto_val(lambda: E.auto_probe_argv('a "unclosed', "--version"),
                                "<raised>") == "<raised>")))

        # ---------------------------------------- one row per command, with the argv it ran
        # `'one two'` is one argv element holding a space, so the same fixture serves the
        # row's CONTENT here and the row's QUOTING below
        PROBE_CMD = "python3 probe.py 'one two' valid guidance"
        pf = _ag_fixture(x0=0, budget_attempts="1", agent_probe_timeout="2",
                         agent=PROBE_CMD)
        pres = _auto_val(lambda: A.auto_check(pf[1], pf[5]), {})
        prestore, pseen = (lambda: None), []
        if pf[0]:
            prestore, pseen = _ag_spawns(A)
        try:
            prun = _loop_run("probe", pf[1], pf[2], pf[5])
        finally:
            prestore()
        check("aprobe: auto check reports one agents row per command with the probe argv it ran, spends no model call, and drops placeholder-bearing elements",
              _auto_ok(lambda: (
                  len(pres["agents"]) == 1
                  and set(pres["agents"][0]) == {"command", "probe", "reachable", "seconds",
                                                 "detail"}
                  and pres["agents"][0]["command"] == PROBE_CMD
                  and pres["agents"][0]["probe"] == ["python3", "probe.py", "one two",
                                                     "valid", "guidance", "--version"]
                  and pres["agents"][0]["reachable"] is True
                  and isinstance(pres["agents"][0]["seconds"], float)
                  and pres["agents"][0]["seconds"] >= 0
                  and pres["agents"][0]["detail"] == "exited 0"
                  and pres["ok"] is True
                  and [p["check"] for p in pres["problems"]] == []
                  # the probe sends no prompt, so it is not a model call and not a worker: the
                  # run's own accounting is untouched by having been probed
                  and len(_ev(prun, "worker-started")) == len(_ag_role(pseen,
                                                                       "crux-auto-worker"))
                  and (prun["state"] or {})["budget"]["model_calls"]["used"]
                      == len(_ev(prun, "worker-started")))))

        # ------------------------------- one unreachable beside a reachable one is no problem
        mx = _ag_fixture(x0=0, agent_probe_timeout="2", agent=AG_NO_SUCH_BINARY + " step",
                         agent_failover="python3 probe.py " + AG_STUB_ARGS)
        mres = _auto_val(lambda: A.auto_check(mx[1], mx[5]), {})
        nn = _ag_fixture(x0=0, agent_probe_timeout="2", agent=AG_NO_SUCH_BINARY + " step",
                         agent_failover=AG_NO_SUCH_BINARY + "2 step")
        nres = _auto_val(lambda: A.auto_check(nn[1], nn[5]), {})
        check("aprobe: agent-reach fires only when no command is reachable, and one unreachable entry beside a reachable one is no problem",
              _auto_ok(lambda: (
                  len(mres["agents"]) == 2
                  and [r["reachable"] for r in mres["agents"]] == [False, True]
                  and mres["agents"][0]["seconds"] is None
                  and "cannot start" in mres["agents"][0]["detail"]
                  and "agent-reach" not in [p["check"] for p in mres["problems"]]
                  and mres["ok"] is True
                  # a failover list exists precisely so one dead entry is survivable; only a
                  # list with no live entry in it is a fault
                  and [p["check"] for p in nres["problems"]] == ["agent-reach"]
                  and nres["ok"] is False
                  and nres["problems"][0]["message"].startswith(
                      "no agent command in the flight plan is reachable: ")
                  and all(c in nres["problems"][0]["message"]
                          for c in (AG_NO_SUCH_BINARY + " step",
                                    AG_NO_SUCH_BINARY + "2 step")))))

        # ------------------------------------- a command that cannot parse is a STATIC fault
        sf = _ag_fixture(x0=0, _approve=False, agent='python3 "unclosed')
        bmsgs = [m for m in _plan_msgs(
            sf[1], _loop_plan_text(sf[2], sf[4], agent='python3 "unclosed'), sf[5])
            if "agent command" in m]
        empty_msgs = _plan_msgs(sf[1], _loop_plan_text(sf[2], sf[4], agent="   "), sf[5])
        spawn, sres = [], {}
        saved = _auto_val(lambda: A._run)
        try:
            if saved is not None:
                def rec(argv, *a, **k):
                    spawn.append(list(argv))
                    return saved(argv, *a, **k)
                A._run = rec
            sres = _auto_val(lambda: A.auto_check(sf[1], sf[5], static=True), {})
        finally:
            if saved is not None:
                A._run = saved
        check("aprobe: a command that does not parse or is empty is refused under agent-command by auto check --static, which starts nothing and keeps the pinned key set",
              _auto_ok(lambda: (
                  len(bmsgs) == 1
                  and bmsgs[0].startswith('flight plan agent command 1 does not parse under '
                                          'shlex: python3 "unclosed (')
                  and bmsgs[0].endswith(")")
                  and "flight plan agent command 1 is empty" in empty_msgs
                  and "agent-command" in [p["check"] for p in sres["problems"]]
                  and sres["ok"] is False
                  # --static is the lint alone: the key set is the 05.1 one, `agents` is NOT
                  # in it, and nothing was started
                  and set(sres) == {"ok", "plan", "anchor", "mode", "problems"}
                  and spawn == [])))

        # ------------------------------------------ and the same probe again, at run open
        op = _ag_fixture(x0=0, agent_probe_timeout="2", agent=AG_NO_SUCH_BINARY + " step")
        opn = _loop_run("probe-open", op[1], op[2], op[5])
        ores = _auto_val(lambda: A.reservations(op[1], op[2]), {})
        check("aprobe: auto run probes the list at run open and stops abort before reserving any id when nothing is reachable",
              _auto_ok(lambda: (
                  _loop_stop(opn)["reason"] == "abort"
                  and _loop_stop(opn)["axis"] is None
                  and _loop_stop(opn)["attempt"] is None
                  and _loop_stop(opn)["detail"].startswith(
                      "no agent command is reachable: ")
                  and AG_NO_SUCH_BINARY + " step" in _loop_stop(opn)["detail"]
                  and _ev(opn, "attempt-reserved") == []
                  and _ev(opn, "worker-started") == []
                  and not ores
                  and (opn["state"] or {})["closed"] == []
                  and (opn["state"] or {})["budget"]["model_calls"]["used"] == 0)))

        # ------------------------------ the row the PI reads has to be pasteable as a command
        # in process, with the vault as cwd: the text path is crux.py's, and a second
        # interpreter start would buy nothing this criterion needs
        qout, qbuf, qcwd = "", io.StringIO(), os.getcwd()
        if pf[0]:
            import crux as C
            try:
                os.chdir(pf[1])
                with contextlib.redirect_stdout(qbuf):
                    _auto_val(lambda: C.main(["auto", "check", pf[5]]))
            finally:
                os.chdir(qcwd)
            qout = qbuf.getvalue()
        check("aprobe: the agents row prints its probe argv shlex-joined, so an element holding a space is quoted",
              _auto_ok(lambda: (
                  "agent reachable:" in qout
                  # space-joined, the line reads as five arguments where four were run
                  and "'one two'" in qout
                  and ("probe: python3 probe.py 'one two' valid guidance --version"
                       in qout))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"aprobe: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


AG_LEAK = ("the anchor's own prose, which argues for the claim and which no brief the engine "
           "assembles may ever quote")
AG_LEAK_PS = ("ANCHOR-PROBLEM-STATEMENT-LIVES-HERE. The PI believes this angle is the answer "
              "and this anchor exists to prove it.")


def _ag_plant_leak(root, qid):
    """Plant BOTH advocacy markers in the anchor, and say whether both landed.

    The PRD says the brief carries no string from the anchor's `## Problem Statement`. A
    question node has no such section — `PROSE_SECTIONS["question"]` is ELI5 / TL;DR /
    Question / Answer so far — so the advocacy prose a PI actually writes lands in
    `## Answer so far`. The 05.0 brief tests settle this the other way and greener: they
    INJECT a `## Problem Statement` section into the anchor, and the leak check reads that
    heading whatever the node's prose schema is. Both markers are planted, so a brief that
    quoted either would be caught — a brief that quotes the argument FOR a claim has told the
    reader what to conclude, and a reader told what to conclude is not a check on anything."""
    p = node_path(root, qid)
    edit(p, "_(interpretation — written by the PI/agent; auto-flagged stale when new "
            "evidence lands)_", AG_LEAK)
    t = read(p)
    if E.LEDGER_START in t and AG_LEAK_PS not in t:
        write(p, t.replace(E.LEDGER_START,
                           f"## Problem Statement\n\n{AG_LEAK_PS}\n\n" + E.LEDGER_START, 1))
    t = read(p)
    return AG_LEAK in t and AG_LEAK_PS in t and "## Problem Statement" in t


def run_auto_closer():
    """Spec 05 PRD 05.3 §E–§G — `crux-close` wired in, byte-unchanged, behind one switch.

    The reason this is opt-in and the reason it is safe are the same reason: the closer reads
    prose and proposes ticks, so it can say something the scorer's number cannot — and must
    never be able to say something the scorer's number contradicts. So the engine grades first,
    the closer fills only what the engine left `[-]`, and a proposed tick that disagrees with a
    graded comparison refuses the whole proposal rather than half of it. A reporter whose
    answer is its own act is not retried; only a failure to START is."""
    print("\n# autopilot — the closer (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # -------------------------------------------- closer: true is what lifts check-grammar
        # `closer="true"` on the FIXTURE's own plan, or the file on disk carries a prose
        # check with no closer, `load_flight_plan` refuses it under check-grammar, and every
        # branch below reads an empty plan dict.
        gf = _ag_fixture(x0=2, _approve=False, closer="true",
                         verifiables=AG_PROSE_VERIFIABLES)
        off = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4],
                                                verifiables=AG_PROSE_VERIFIABLES), gf[5])
        on = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4], closer="true",
                                               verifiables=AG_PROSE_VERIFIABLES), gf[5])
        plain = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4]), gf[5])
        plain_on = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4], closer="true"), gf[5])
        bad_bool = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4], closer="maybe"), gf[5])
        bad_cool = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4], closer="true",
                                                     agent_cooldown="soon"), gf[5])
        bad_pto = _plan_msgs(gf[1], _loop_plan_text(gf[2], gf[4], closer="true",
                                                    agent_probe_timeout="0"), gf[5])
        check("acloser: closer true lets a prose check validate, and without it check-grammar refuses it exactly as in 05.2",
              _auto_ok(lambda: (
                  any("the baseline reproduces" in m for m in off)
                  and on == []
                  # a plan with NO prose check has the same problem list either way, which is
                  # what makes every shipped fixture's list byte-identical to 05.2's
                  and plain == [] and plain_on == []
                  and bad_bool == ["flight plan field 'closer' must be true or false "
                                   "(got 'maybe')"]
                  and bad_cool == ["flight plan field 'agent_cooldown' must be a non-negative "
                                   "number of seconds (got 'soon')"]
                  and bad_pto == ["flight plan field 'agent_probe_timeout' must be a positive "
                                  "number of seconds (got '0')"])))

        # ------------------------------------------------------- the proposal, branch by branch
        cplan = _loop_load_plan(gf[1], gf[2]) or {}
        eng = [("x", "-1e-06"), ("-", "the check names no number the scorer printed")]

        def _cp(raw, tk=None):
            return _auto_val(lambda: E.auto_close_proposal(raw, cplan, tk or eng), {})

        long_findings = " ".join(["word"] * (E.AUTO_CLOSE_FINDINGS_WORDS + 1))
        valid = {"ticks": {"2": "x"}, "findings": "the control held", "report": "# r\n"}
        branches = (
            ("no file at all is closer-missing", None, None, "closer-missing",
             "the closer left no close.json in its workspace"),
            ("a JSON array is closer-unparseable", "[1, 2]", None, "closer-unparseable",
             "close.json is not one JSON object (got list)"),
            ("a key outside the schema is closer-schema", json.dumps(
                dict(valid, verdict="supported")), None, "closer-schema",
             "close.json carries keys outside ticks, findings, report: verdict"),
            ("ticks that are not an object is closer-schema", json.dumps(
                dict(valid, ticks=["x"])), None, "closer-schema",
             "close.json ticks is not an object keyed by check index"),
            ("a tick key naming no check is closer-schema", json.dumps(
                dict(valid, ticks={"0": "x"})), None, "closer-schema",
             "close.json ticks name no check: 0"),
            ("a tick outside the alphabet is closer-schema", json.dumps(
                dict(valid, ticks={"2": "y"})), None, "closer-schema",
             "close.json tick for check 2 is not one of 'x', ' ', '-' (got 'y')"),
            ("no findings is closer-schema", json.dumps(
                {"ticks": {"2": "x"}, "findings": "   ", "report": "# r\n"}), None,
             "closer-schema", "close.json carries no findings"),
            ("findings over the prose cap is closer-findings", json.dumps(
                dict(valid, findings=long_findings)), None, "closer-findings",
             f"the findings run to {E.AUTO_CLOSE_FINDINGS_WORDS + 1} words, over the "
             f"{E.AUTO_CLOSE_FINDINGS_WORDS}-word cap"),
            ("no report is closer-schema", json.dumps(
                {"ticks": {"2": "x"}, "findings": "held", "report": ""}), None,
             "closer-schema", "close.json carries no report"),
            ("a tick contradicting a graded comparison is closer-contradiction", json.dumps(
                dict(valid, ticks={"1": " ", "2": "x"})), None, "closer-contradiction",
             "close.json ticks check 1 ' ' where the scorer's number grades it 'x' "
             "(found: -1e-06)"),
        )
        for label, raw, tk, reason, msg in branches:
            r = _cp(raw, tk)
            check(f"acloser: {label}",
                  r.get("ok") is False and r.get("reason") == reason
                  and r.get("detail") == msg and r.get("ticks") == {}
                  and r.get("findings") is None and r.get("report") is None)
        unparse = _cp("{not json")
        cap = _auto_val(lambda: E.AUTO_REPORT_BYTES, 0)
        big = _cp(json.dumps(dict(valid, report="r" * (cap + 50) if cap else "r")))
        okp = _cp(json.dumps(valid))
        check("acloser: a close proposal that is not one JSON object is refused closer-unparseable, and a valid one truncates its report rather than refusing it",
              _auto_ok(lambda: (
                  unparse["ok"] is False and unparse["reason"] == "closer-unparseable"
                  and unparse["detail"].startswith("close.json is not one JSON object (")
                  and unparse["detail"].endswith(")")
                  and okp["ok"] is True and okp["reason"] is None
                  and okp["ticks"] == {2: "x"} and okp["findings"] == "the control held"
                  and okp["report"] == "# r"
                  # §G caps the report in bytes; a report that ran long is a long report, not a
                  # broken proposal, so it is cut rather than thrown away
                  and big["ok"] is True
                  and len(big["report"]) == E.AUTO_REPORT_BYTES
                  and E.AUTO_CLOSE_KEYS == ("ticks", "findings", "report")
                  and E.AUTO_TICK_ALPHABET == ("x", " ", "-")
                  and E.AUTO_REPORT_FILE == "report.md")))

        m_fill = _auto_val(lambda: E.auto_merge_ticks(eng, {2: "x"}))
        m_agree = _auto_val(lambda: E.auto_merge_ticks(eng, {1: "x", 2: " "}))
        m_none = _auto_val(lambda: E.auto_merge_ticks(eng, {}))
        check("acloser: the merge fills only what the engine left ungraded, and an engine tick stands verbatim",
              _auto_ok(lambda: (
                  m_fill == [("x", "-1e-06"), ("x", "graded by crux-close")]
                  # an AGREEING proposal is ignored, not applied: the found string still says
                  # where the tick came from, and it came from the scorer's number
                  and m_agree == [("x", "-1e-06"), (" ", "graded by crux-close")]
                  and m_none == eng
                  and len(m_fill) == len(eng))))

        # ------------------------------------------------- one run, with a working closer
        vf = _ag_fixture(x0=2, closer="true", budget_attempts="1", retention="all",
                         verifiables=AG_PROSE_VERIFIABLES,
                         agent="python3 dispatch.py " + AG_STUB_ARGS)
        leaked = _auto_val(lambda: _ag_plant_leak(vf[1], vf[2]), False)
        vplan0 = _auto_val(lambda: read(os.path.join(vf[1], vf[5])), "")
        vrestore, vseen = (lambda: None), []
        if vf[0]:
            vrestore, vseen = _ag_spawns(A)
        try:
            good = _loop_run("closer-valid", vf[1], vf[2], vf[5])
        finally:
            vrestore()
        gst = good["state"] or {}
        gclosed = (gst.get("closed") or [""])[0]
        gev = [e["event"] for e in good["events"]]
        cspawn = (_ag_role(vseen, "crux-close") or [{}])[0]
        vplan = _loop_load_plan(vf[1], vf[2]) or {}
        # `cmd_auto_ticks` both computes AND WRITES. Asking it for the engine's own vector —
        # which is what a close brief is built over — therefore overwrites the MERGED vector
        # the run just landed, and the criterion below asserts on exactly that vector. So the
        # node is captured first and restored after: the probe must not erase its own subject.
        gnode0 = _auto_val(lambda: read(node_path(vf[1], gclosed)), "")
        gticks = _auto_val(lambda: E.cmd_auto_ticks(
            vf[1], gclosed, json.loads(read(os.path.join(
                vf[1], E.RESULTS_DIR, gclosed, E.METRICS_FILE)))), [])
        if gnode0:
            write(node_path(vf[1], gclosed), gnode0)
        brief = _auto_val(lambda: E.auto_close_brief(vf[1], gclosed, vplan, gticks), {})
        brief2 = _auto_val(lambda: E.auto_close_brief(vf[1], gclosed, vplan, gticks), {})
        btext = _auto_val(lambda: E.auto_close_brief_text(brief), "")
        btext2 = _auto_val(lambda: E.auto_close_brief_text(brief2), "")

        check("acloser: the closer runs after scoring and before cmd_close through the same command list, with CRUX_AGENT, CRUX_RESULTS and CRUX_PROPOSAL set, charged one model call",
              _auto_ok(lambda: (
                  len(_ag_role(vseen, "crux-close")) == 1
                  and gev.index("scored") < gev.index("closer") < gev.index("closed")
                  # the SAME list, so the same command string the worker ran
                  and cspawn["argv"][:2] == _ag_role(vseen, "crux-auto-worker")[0]["argv"][:2]
                  and _ag_env_names(cspawn) == ["CRUX_AGENT", "CRUX_ATTEMPT", "CRUX_BRIEF",
                                                "CRUX_PROPOSAL", "CRUX_RESULTS",
                                                "CRUX_WORKSPACE"]
                  and cspawn["env"]["CRUX_AGENT"] == "crux-close"
                  and cspawn["env"]["CRUX_ATTEMPT"] == gclosed
                  and os.path.realpath(cspawn["env"]["CRUX_RESULTS"])
                      == os.path.realpath(os.path.join(vf[1], E.RESULTS_DIR, gclosed))
                  and cspawn["env"]["CRUX_PROPOSAL"].endswith("close.json")
                  and cspawn["env"]["CRUX_BRIEF"].endswith("close-brief.md")
                  # the closer's cwd is the REPOSITORY, never a worktree that resume may have
                  # already removed
                  and os.path.realpath(cspawn["cwd"]) == os.path.realpath(vf[0])
                  and gst["budget"]["model_calls"]["used"] == 2
                  and len(_ev(good, "closer")) == 1
                  and _ev(good, "closer")[0]["ok"] is True
                  and _ev(good, "closer")[0]["reason"] is None
                  and set(_ev(good, "closer")[0]) >= {"at", "event", "attempt", "ok",
                                                      "reason", "detail"})))

        check("acloser: the close brief is byte-identical over unchanged run state and carries no string from the anchor's problem statement",
              _auto_ok(lambda: (
                  bool(btext) and btext == btext2 and brief == brief2
                  and leaked
                  and AG_LEAK not in btext and AG_LEAK not in json.dumps(brief)
                  and AG_LEAK_PS not in btext and AG_LEAK_PS not in json.dumps(brief)
                  and brief["mode"] == "close"
                  and brief["engine_version"] == E.ENGINE_VERSION
                  and brief["attempt"]["id"] == gclosed
                  and brief["results"] == f"{E.RESULTS_DIR}/{gclosed}/"
                  and not os.path.isabs(brief["results"])
                  # amendment (T): the findings paragraph lands in the NODE, where
                  # `prose_words` sums every prose section against ONE PROSE_CAP budget, so a
                  # findings cap of PROSE_CAP would put every closed attempt over cap
                  and brief["schema"] == {"keys": list(E.AUTO_CLOSE_KEYS),
                                          "ticks": list(E.AUTO_TICK_ALPHABET),
                                          "findings_words": E.AUTO_CLOSE_FINDINGS_WORDS,
                                          "report_bytes": E.AUTO_REPORT_BYTES}
                  and E.AUTO_CLOSE_FINDINGS_WORDS == E.AUTO_BRIEF_BUDGET["findings_words"]
                  and E.AUTO_CLOSE_FINDINGS_WORDS < E.PROSE_CAP
                  and [c["graded"] for c in brief["checks"]] == [True, False]
                  and _auto_msg(lambda: E.auto_close_brief(vf[1], vf[2], vplan, gticks))
                      == f"auto close brief is per-attempt (got a 'question' for '{vf[2]}')"
                  and _auto_msg(lambda: E.auto_close_brief(vf[1], gclosed, vplan, gticks[:1]))
                      == f"auto close brief: 1 ticks for {len(vplan['checks'])} checks")))

        check("acloser: the close brief instructs the JSON write as an addition to crux-close's table, suppressing nothing, and that agent is byte-identical",
              _auto_ok(lambda: (
                  "and also write that same proposal as one JSON object" in btext
                  # the closer is a REUSED agent: the brief may add an output, never replace
                  # the one the agent's own definition promises
                  and re.search(r"do not (print|show|output)|instead of (printing|the table)"
                                r"|skip the table|no table", btext, re.I) is None
                  and "## Output" in btext and "## Checks" in btext and "## Results" in btext
                  and str(E.AUTO_CLOSE_FINDINGS_WORDS) in btext
                  and str(E.AUTO_REPORT_BYTES) in btext
                  and "There is no verdict field: the verdict is derived." in btext
                  and hashlib.sha256(read(os.path.join(
                      REPO, "agents", "crux-close", "AGENT.md")).encode("utf-8")).hexdigest()
                      == "24c0121a494c54d8fdfb18e661325f6ed58c5cfbb27079a7eac4f25ee5edad0d")))

        check("acloser: a valid close proposal ticks the prose checks while the engine's comparison ticks stand, and the verdict equals derive_verdict_15 over the merged vector",
              _auto_ok(lambda: (
                  len(gst["closed"]) == 1
                  and "(found: graded by crux-close)"
                      in _ag_ticked(vf[1], gclosed, "the baseline reproduces")
                  and _ag_ticked(vf[1], gclosed, "the baseline reproduces").startswith("- [x]")
                  # the engine's own comparison keeps ITS found string — the number, not the
                  # agent — even though the proposal agreed with it
                  and "graded by crux-close"
                      not in _ag_ticked(vf[1], gclosed, "obj.score >= -0.5")
                  and _ag_ticked(vf[1], gclosed, "obj.score >= -0.5").startswith("- [x]")
                  and E.Vault(vf[1]).get(gclosed)["fm"]["verdict"]
                      == _ag_derived(vf[1], gclosed)
                  and E.Vault(vf[1]).get(gclosed)["fm"]["verdict"] == "supported"
                  # the closer's findings REPLACED the engine's fixed template, rather
                  # than being appended beside it
                  and "Autopilot close. Objective"
                      not in read(node_path(vf[1], gclosed))
                  and "the baseline re-ran to the same number"
                      in read(node_path(vf[1], gclosed))
                  # and the whole node still fits the one prose budget it has (amendment T)
                  and E.prose_words(E.Vault(vf[1]).get(gclosed)["body"], "idea")
                      <= E.PROSE_CAP)))

        # --------------------------------- the three ways a closer's answer is its own fault
        cf = _ag_fixture(x0=2, closer="true", budget_attempts="1",
                         agent="python3 dispatch.py step contradicting guidance")
        contra = _loop_run("closer-contradict", cf[1], cf[2], cf[5])
        mf = _ag_fixture(x0=2, closer="true", budget_attempts="1",
                         agent="python3 dispatch.py step malformed guidance")
        mal = _loop_run("closer-malformed", mf[1], mf[2], mf[5])
        # the closer alone cannot start. `python3 stub_{agent}.py` would not do it — `python3`
        # exists, so the child STARTS and exits 2, which is `closer-exit`, not `closer-start`.
        # The one role's spawn is failed at the kernel boundary instead.
        nf = _ag_fixture(x0=2, closer="true", retries="2", budget_attempts="1",
                         agent="python3 dispatch.py " + AG_STUB_ARGS)
        nrestore = _ag_no_start(A, "crux-close") if nf[0] else (lambda: None)
        try:
            nostart = _loop_run("closer-nostart", nf[1], nf[2], nf[5])
        finally:
            nrestore()
        cret = [e for e in _ev(contra, "retry") if e.get("step") == "closer"]
        nret = [e for e in _ev(nostart, "retry") if e.get("step") == "closer"]

        check("acloser: a proposed tick contradicting a graded comparison refuses the proposal unretried, and an agreeing one is ignored",
              _auto_ok(lambda: (
                  len(_ev(contra, "closer")) == 1
                  and _ev(contra, "closer")[0]["ok"] is False
                  and _ev(contra, "closer")[0]["reason"] == "closer-contradiction"
                  and "where the scorer's number grades it"
                      in _ev(contra, "closer")[0]["detail"]
                  and cret == []
                  # refused WHOLE: the agreeing tick in the same file is not applied either
                  and "graded by crux-close" not in read(
                      node_path(contra["root"], (contra["state"] or {})["closed"][0]))
                  and m_agree[0] == eng[0])))

        check("acloser: a malformed close proposal is refused unretried, and a closer that cannot start is retried and then gives up",
              _auto_ok(lambda: (
                  len(_ev(mal, "closer")) == 1
                  and _ev(mal, "closer")[0]["reason"] == "closer-schema"
                  and [e for e in _ev(mal, "retry") if e.get("step") == "closer"] == []
                  # only a failure to START is retried, under the plan's own `retries`
                  and len(nret) == 2
                  and [e["reason"] for e in nret] == ["closer-start", "closer-start"]
                  and len(_ev(nostart, "closer")) == 1
                  and _ev(nostart, "closer")[0]["reason"] == "closer-start"
                  and _ev(nostart, "closer")[0]["detail"].startswith(
                      "every agent command failed to start: ")
                  and len(_ev(nostart, "failover")) >= 1
                  and bool((nostart["state"] or {})["closed"]))))

        check("acloser: every closer failure closes the attempt on the engine's vector with the template findings, never invalid-run for that reason alone",
              _auto_ok(lambda: all(
                  len((r["state"] or {})["closed"]) == 1
                  and (r["state"] or {})["consecutive_invalid"] == 0
                  and _ev(r, "violation") == []
                  and E.Vault(r["root"]).get((r["state"] or {})["closed"][0])["fm"]["verdict"]
                      == _ag_derived(r["root"], (r["state"] or {})["closed"][0])
                  and E.Vault(r["root"]).get((r["state"] or {})["closed"][0])["fm"]["verdict"]
                      != "invalid-run"
                  and "graded by crux-close" not in read(
                      node_path(r["root"], (r["state"] or {})["closed"][0]))
                  # the findings are the engine's fixed template, never the words of a
                  # proposal the engine refused
                  and "the baseline re-ran to the same number" not in read(
                      node_path(r["root"], (r["state"] or {})["closed"][0]))
                  and E._section(E.Vault(r["root"]).get(
                      (r["state"] or {})["closed"][0])["body"], "Findings").strip() != ""
                  for r in (contra, mal, nostart))))

        # `cmd_auto_ticks` grew one optional keyword and nothing else: the merged vector has to
        # reach the node, and the driver may not be the second writer of a node file.
        tf = gf                 # any tier-zero baseline serves, and gf is already built
        tm = {"obj": {"score": {"value": -0.25}}}
        t_auto = _auto_val(lambda: E.cmd_auto_ticks(tf[1], tf[4], tm), "<absent>")
        t_none = _auto_val(lambda: E.cmd_auto_ticks(tf[1], tf[4], tm, ticks=None), "<absent>")
        t_given = _auto_val(lambda: E.cmd_auto_ticks(
            tf[1], tf[4], tm, ticks=[("x", "handed in"), ("x", "handed in")]), "<absent>")
        check("acloser: cmd_auto_ticks with ticks=None is byte-identical to 05.2, and a vector handed in is written without recomputation",
              _auto_ok(lambda: (
                  t_auto == t_none and t_auto != "<absent>"
                  and t_given == [("x", "handed in"), ("x", "handed in")]
                  and "(found: handed in)" in read(node_path(tf[1], tf[4]))
                  and _auto_msg(lambda: E.cmd_auto_ticks(
                      tf[1], tf[4], tm, ticks=[("x", "one only")]))
                      != "")))

        # ------------- the close brief is INSIDE the failure contract, not in front of it
        # `auto_close_brief` refuses a tick vector that does not match the plan's checks. The
        # property `_closer_try` states is absolute — in every failure case the attempt closes
        # on the engine's own vector — so a refusal here has to be a closer failure, never an
        # exception unwinding the close and taking the run with it.
        cctx = {"root": vf[1], "plan": vplan, "state": (good["state"] or {}), "qid": vf[2],
                "repo": vf[0], "procs": {}, "lock_wait": 0.5, "t0": time.monotonic()}
        shortticks = gticks[:1] if len(gticks) > 1 else [("-", "n/a")] * 9
        badbrief = _auto_val(lambda: A._closer_try(cctx, gclosed, shortticks), {})
        check("acloser: a close brief that cannot be assembled is a closer failure, never an exception out of the close",
              _auto_ok(lambda: (
                  badbrief.get("ok") is False
                  and badbrief.get("reason") == "closer-brief"
                  and "could not be assembled" in (badbrief.get("detail") or "")
                  and badbrief.get("ticks") == {}
                  and badbrief.get("findings") is None and badbrief.get("report") is None
                  # and nothing was started for it
                  and cctx["procs"] == {})))

        # ------------- one byte of a child's output that is not UTF-8 must not end the run
        bd = os.path.realpath(tempfile.mkdtemp(prefix="crux_bytes_"))
        _AUTO_TRASH.append(bd)
        bp = os.path.join(bd, "close.json")
        with open(bp, "wb") as f:
            f.write(b'{"ticks": {}, "findings": "caf\xe9", "report": "r"}')
        soft = _auto_val(lambda: A._agent_file(bp), None)
        hard = "did not raise"
        try:
            E.read(bp)
        except ValueError as e:                # UnicodeDecodeError IS a ValueError
            hard = type(e).__name__
        except Exception as e:                 # pragma: no cover - wave-1 guard
            hard = repr(e)
        # both roles at once: the closer and the steward each write a proposal holding one
        # byte that is not valid UTF-8, and the run has to finish anyway
        yf = _ag_fixture(x0=0, mode="explore", closer="true", steward="true",
                         steward_every="1", budget_attempts="2", retention="all",
                         verifiables=AG_PROSE_VERIFIABLES,
                         agent="python3 dispatch.py step bytes bytes")
        ybytes = _loop_run("agent-bytes", yf[1], yf[2], yf[5])
        yst = ybytes["state"] or {}
        check("acloser: a proposal holding a byte that is not UTF-8 is read with replacement, so neither the closer nor the steward can end the run",
              _auto_ok(lambda: (
                  # the engine's own reader is strict, which is exactly why the driver may
                  # not use it on anything a model wrote
                  hard == "UnicodeDecodeError"
                  and isinstance(soft, str) and "\ufffd" in soft
                  and A._agent_file(os.path.join(bd, "no-such-file.json")) is None
                  # the run reached its own stop, with both roles logged and attempts closed
                  and ybytes["error"] == ""
                  and bool(yst.get("closed"))
                  and (yst.get("stop") or {}).get("reason") in E.AUTO_STOP_REASONS
                  and len(_ev(ybytes, "closer")) >= 1
                  and len(_ev(ybytes, "steward")) >= 1)))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"acloser: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_steward():
    """Spec 05 PRD 05.3 §H — the fifth act, and the one agent that advises rather than acts.

    The steward is the only role whose output is not per attempt, which is why the PI had to
    rule its fifth act in by hand at sign-off. Everything about it is built so that it cannot
    cost a run: it never writes the vault except through `ask`, never edits the plan the PI
    signed, never stops a run, and a steward that cannot start, says nothing, or says something
    outside its two-key schema is logged and walked past. Advice a run can die for want of is
    worse than no advice."""
    print("\n# autopilot — the steward (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # ------------------------------------------------------- the proposal, branch by branch
        sp = {"islands": {"q2": {}, "q3": {}}}
        p3, p2 = {"island_cap": 3}, {"island_cap": 2}

        def _sp(raw, plan=None, state=None):
            return _auto_val(lambda: E.auto_steward_proposal(raw, plan or p3, state or sp), {})

        isl = {"title": "a cheaper surrogate", "problem": "the scorer dominates the cost"}
        over_t = " ".join(["word"] * (E.AUTO_TITLE_WORDS + 1))
        over_p = " ".join(["word"] * (E.PROSE_CAP + 1))
        sbranches = (
            ("no file at all is steward-missing", None, p3,
             "steward-missing", "the steward left no proposal.json in its workspace"),
            ("a JSON array is steward-unparseable", "[1]", p3,
             "steward-unparseable", "proposal.json is not one JSON object (got list)"),
            ("a key outside the schema is steward-schema", json.dumps(
                {"guidance": "go slower", "verdict": "supported"}), p3, "steward-schema",
             "proposal.json carries keys outside guidance, island: verdict"),
            ("an empty object is steward-empty", "{}", p3,
             "steward-empty", "proposal.json proposes neither guidance nor an island"),
            ("blank guidance is steward-schema", json.dumps({"guidance": "   "}), p3,
             "steward-schema", "proposal.json guidance is not a non-empty string"),
            ("guidance over the prose cap is steward-schema", json.dumps(
                {"guidance": over_p}), p3, "steward-schema",
             f"the guidance runs to {E.PROSE_CAP + 1} words, over the {E.PROSE_CAP}-word cap"),
            ("an island of the wrong shape is steward-schema", json.dumps(
                {"island": {"title": "t"}}), p3, "steward-schema",
             "proposal.json island must be an object with exactly title and problem, both "
             "non-empty strings"),
            ("an island title over its cap is steward-schema", json.dumps(
                {"island": dict(isl, title=over_t)}), p3, "steward-schema",
             f"the island title runs to {E.AUTO_TITLE_WORDS + 1} words, over the "
             f"{E.AUTO_TITLE_WORDS}-word cap"),
            ("an island problem over the prose cap is steward-schema", json.dumps(
                {"island": dict(isl, problem=over_p)}), p3, "steward-schema",
             f"the island problem statement runs to {E.PROSE_CAP + 1} words, over the "
             f"{E.PROSE_CAP}-word cap"),
            ("an island at island_cap is steward-cap", json.dumps({"island": isl}), p2,
             "steward-cap", "the run already holds 2 islands, at island_cap 2"),
        )
        for label, raw, plan, reason, msg in sbranches:
            r = _sp(raw, plan)
            check(f"asteward: {label}",
                  r.get("ok") is False and r.get("reason") == reason
                  and r.get("detail") == msg
                  and r.get("guidance") is None and r.get("island") is None)
        sok = _sp(json.dumps({"guidance": "prefer  one-step\nmoves", "island": isl}))
        check("asteward: a proposal inside the schema normalizes its whitespace and carries only the two keys",
              _auto_ok(lambda: (
                  sok["ok"] is True and sok["reason"] is None
                  and sok["guidance"] == "prefer one-step moves"
                  and sok["island"] == {"title": "a cheaper surrogate",
                                        "problem": "the scorer dominates the cost"}
                  and E.AUTO_STEWARD_KEYS == ("guidance", "island")
                  and E.AUTO_ISLAND_KEYS == ("title", "problem")
                  and E.AUTO_NO_STEWARD == "No steward guidance yet."
                  and E.AUTO_BRIEF_BUDGET["steward"] == 10
                  and E.AUTO_BRIEF_BUDGET["ledger"] == 40
                  and len(E.AUTO_BRIEF_SLOTS) == 14
                  and len(E.AUTO_BRIEF_CHECKS) == 5)))

        # -------------------------- the switch is legal on a Climb plan, and simply never fires
        cl = _ag_fixture(x0=0, mode="climb", steward="true", steward_every="1",
                         budget_attempts="1", agent="python3 dispatch.py " + AG_STUB_ARGS)
        climb = _loop_run("steward-climb", cl[1], cl[2], cl[5])
        cst = climb["state"] or {}
        check("asteward: auto run accepts steward true, and a Climb plan with the switch on completes with no steward invocation and no steward event",
              _auto_ok(lambda: (
                  climb["error"] == ""
                  and bool(cst.get("closed"))
                  and _loop_stop(climb)["reason"] in E.AUTO_STOP_REASONS
                  # a run may be moved from Climb to Explore mid-flight, so the switch being
                  # on is not a mistake to refuse — it is advice nobody asked for yet
                  and _ev(climb, "steward") == []
                  and cst["steward"]["invocations"] == 0
                  and cst["steward"]["guidance"] == []
                  and cst["steward"]["islands"] == []
                  and not os.path.isdir(os.path.join(cl[1], E.AUTO_DIR, cl[2], "steward")))))

        # ---------------------------------------------- when it runs, in Explore, and how often
        ef = _ag_fixture(x0=0, mode="explore", islands=2, steward="true", steward_every="2",
                         stall_attempts="2", budget_attempts="6", retention="all",
                         agent="python3 dispatch.py still guidance guidance")
        eleak = _auto_val(lambda: _ag_plant_leak(ef[1], ef[2]), False)
        erestore, eseen = (lambda: None), []
        if ef[0]:
            erestore, eseen = _ag_spawns(A)
        try:
            exp = _loop_run("steward-explore", ef[1], ef[2], ef[5])
        finally:
            erestore()
        est = exp["state"] or {}
        sev = _ev(exp, "steward")
        sdir = os.path.join(ef[1] or "", E.AUTO_DIR, ef[2] or "", "steward")
        check("asteward: in Explore the steward runs on steward_requested and otherwise every steward_every closed attempts, never twice in one window and never two at once",
              _auto_ok(lambda: (
                  len(sev) >= 1
                  and len(sev) == est["steward"]["invocations"]
                  and len(sev) == len(_ag_role(eseen, "crux-auto-steward"))
                  # the workspaces are numbered 1..n with no gaps and no collision, which is
                  # what "never two at once" looks like on disk: two live stewards would both
                  # be invocation n
                  and sorted(os.listdir(sdir), key=lambda s: int(s)) == [
                      str(i) for i in range(1, est["steward"]["invocations"] + 1)]
                  # the window closes whether the steward ran or not, so it can never fire
                  # twice for the same batch of closed attempts
                  and est["steward"]["last_closed"] <= len(est["closed"])
                  and len(est["closed"]) - est["steward"]["last_closed"] < 2
                  and est["steward_requested"] is False
                  and len(_ev(exp, "escalated")) >= 1
                  and A.PROC_STEWARD == "steward"
                  and A.PROC_CLOSE == "{hid}:close")))

        eplan = _loop_load_plan(ef[1], ef[2]) or {}
        sb = _auto_val(lambda: E.auto_steward_brief(ef[1], eplan, est, exp["events"]))
        sb2 = _auto_val(lambda: E.auto_steward_brief(ef[1], eplan, est, exp["events"]))
        stext = _auto_val(lambda: E.auto_steward_brief_text(sb), "")
        stext2 = _auto_val(lambda: E.auto_steward_brief_text(sb2), "")
        check("asteward: the steward brief is byte-stable over unchanged run state and carries no problem statement and no attempt diff",
              _auto_ok(lambda: (
                  bool(stext) and stext == stext2 and sb == sb2
                  and eleak
                  and AG_LEAK not in stext and AG_LEAK not in json.dumps(sb)
                  and AG_LEAK_PS not in stext and AG_LEAK_PS not in json.dumps(sb)
                  and sb["mode"] == "steward"
                  and sb["anchor"]["id"] == ef[2]
                  and sb["island_cap"] == eplan["island_cap"]
                  and sb["islands_open"] == len(est["islands"])
                  and sb["schema"] == {"keys": list(E.AUTO_STEWARD_KEYS),
                                       "island": list(E.AUTO_ISLAND_KEYS),
                                       "title_words": E.AUTO_TITLE_WORDS,
                                       "problem_words": E.PROSE_CAP}
                  # every score is carried as the address it came from, and NOTHING else is
                  # read from a node body — no findings prose, no diff, no code
                  and all(r["best"]["score"] is None
                          or set(r["best"]["score"]) == {"value", "addr"}
                          for r in sb["islands"])
                  and "diff --git" not in stext and "params.json" not in stext
                  and len(sb["ledger"]) <= E.AUTO_BRIEF_BUDGET["ledger"]
                  and all(s in stext for s in ("## Goal", "## Objective", "## Islands",
                                               "## Budget", "## The PI's guidance",
                                               "## Earlier steward guidance", "## Ledger",
                                               "## Output"))
                  and E.auto_brief_verify(ef[1], sb) == []
                  and _auto_msg(lambda: E.auto_steward_brief(
                      ef[1], dict(eplan, island_cap=None), est, exp["events"]))
                      == "auto steward brief: required slot 'island_cap' is absent or empty")))

        # --------------------------- guidance: recorded in state, rendered in every later brief
        gf = _ag_fixture(x0=0, mode="explore", steward="true", steward_every="1",
                         budget_attempts="3", retention="all",
                         agent="python3 dispatch.py still valid guidance")
        gplan0 = _auto_val(lambda: read(os.path.join(gf[1], gf[5])), "")
        # The steward's success path records NO event until the steward exits, so the window
        # bookkeeping and the model call charged at the spawn would live in memory alone: a
        # kill between the two re-opens the same window on resume and pays for it twice.
        gtrace = []
        gsave, gspawn = _auto_val(lambda: A._save_state), _auto_val(lambda: A._spawn)
        grec = _auto_val(lambda: A._record)
        if None not in (gsave, gspawn, grec):
            def _gsv(ctx, _o=gsave):
                gtrace.append("save")
                return _o(ctx)

            def _grc(ctx, event, fields, work=None, _o=grec):
                gtrace.append("record:" + str(event))
                return _o(ctx, event, fields, work=work)

            def _gsp(argv, cwd, env, log_path, *aa, _o=gspawn, **kk):
                if (env or {}).get("CRUX_AGENT") == "crux-auto-steward":
                    gtrace.append("steward-spawn")
                return _o(argv, cwd, env, log_path, *aa, **kk)
            A._save_state, A._spawn, A._record = _gsv, _gsp, _grc
        try:
            gr = _loop_run("steward-guidance", gf[1], gf[2], gf[5])
        finally:
            if None not in (gsave, gspawn, grec):
                A._save_state, A._spawn, A._record = gsave, gspawn, grec
        gst = gr["state"] or {}
        gplan = _loop_load_plan(gf[1], gf[2]) or {}
        briefs = []
        for h in (gst.get("closed") or []):
            p = _auto_val(lambda hh=h: os.path.join(
                A.workspace_path(gf[1], gplan, hh), A.BRIEF_NAME))
            if p and os.path.isfile(p):
                briefs.append(read(p))
        WORDS = "prefer one-step moves once the objective is within a step of the bar"
        check("asteward: a guidance proposal is recorded in state.json, appears in every later brief in its own labelled section, and leaves the plan byte-unchanged",
              _auto_ok(lambda: (
                  bool(gst["steward"]["guidance"])
                  and all(set(g) == {"at", "author", "text"}
                          for g in gst["steward"]["guidance"])
                  and all(g["author"] == "crux-auto-steward"
                          for g in gst["steward"]["guidance"])
                  and gst["steward"]["guidance"][0]["text"] == WORDS
                  and any(e["ok"] is True and e["guidance"] == WORDS
                          for e in _ev(gr, "steward"))
                  # its OWN labelled section, attributed and stamped: a worker has to be able
                  # to see who said what, because the PI's guidance and an agent's advice are
                  # not the same kind of instruction
                  and len(briefs) >= 2
                  and any("## Steward guidance" in b and WORDS in b
                          and "crux-auto-steward" in b for b in briefs)
                  and briefs[0].index("## Steward guidance") > briefs[0].index("## Guidance")
                  # `auto guide` is the PI's verb: the plan document stays theirs alone
                  and read(os.path.join(gf[1], gf[5])) == gplan0
                  and E.auto_approval(gplan0)["state"] == "approved")))

        # ---------------------------- and the three ways it fails without costing the run a thing
        bf = _ag_fixture(x0=0, mode="explore", steward="true", steward_every="1",
                         budget_attempts="3",
                         agent="python3 dispatch.py still valid alternate")
        bad = _loop_run("steward-bad", bf[1], bf[2], bf[5])
        # `python3 stub_{agent}.py` would not do it: `python3` exists, so the steward
        # STARTS and exits 2. The one role's spawn is failed at the kernel boundary.
        nf = _ag_fixture(x0=0, mode="explore", steward="true", steward_every="1",
                         budget_attempts="3",
                         agent="python3 dispatch.py still valid guidance")
        nrest = _ag_no_start(A, "crux-auto-steward") if nf[0] else (lambda: None)
        try:
            nos = _loop_run("steward-nostart", nf[1], nf[2], nf[5])
        finally:
            nrest()
        ctl = _ag_fixture(x0=0, mode="explore", steward="false", budget_attempts="3",
                          agent="python3 dispatch.py still valid guidance")
        control = _loop_run("steward-control", ctl[1], ctl[2], ctl[5])
        reasons = sorted({e["reason"] for e in _ev(bad, "steward") + _ev(nos, "steward")
                          if not e["ok"]})
        check("asteward: a proposal outside the schema, a steward that cannot start and a steward that returns nothing are each logged and the run continues",
              _auto_ok(lambda: (
                  len(_ev(bad, "steward")) >= 2
                  and all(e["ok"] is False and e["guidance"] is None and e["island"] is None
                          for e in _ev(bad, "steward"))
                  and reasons == ["steward-missing", "steward-schema", "steward-start"]
                  and all(e["detail"] for e in _ev(bad, "steward") + _ev(nos, "steward"))
                  # a run that dies for want of advice is worse than a run without it
                  and len((bad["state"] or {})["closed"])
                      == len((control["state"] or {})["closed"])
                  and len((nos["state"] or {})["closed"])
                      == len((control["state"] or {})["closed"])
                  and _loop_stop(bad)["reason"] == _loop_stop(control)["reason"]
                  and _loop_stop(nos)["reason"] == _loop_stop(control)["reason"]
                  and (bad["state"] or {})["stop"]["reason"] != "abort")))

        # ------------------------------------------------------------- the fifth act, exercised
        # two plan islands plus the steward's third: `budget_attempts="4"` stops the run
        # before the round-robin ever reaches the new one, so the brief that names it is
        # never written and the criterion tests nothing.
        isf = _ag_fixture(x0=0, mode="explore", islands=2, steward="true", steward_every="1",
                          island_cap="3", budget_attempts="5", stall_attempts="20",
                          retention="all",
                          agent="python3 dispatch.py still valid island")
        iplan0 = _auto_val(lambda: read(os.path.join(isf[1], isf[5])), "")
        island = _loop_run("steward-island", isf[1], isf[2], isf[5])
        ist = island["state"] or {}
        iplan = _loop_load_plan(isf[1], isf[2]) or {}
        opened = (ist.get("steward") or {}).get("islands") or []
        qi = opened[0] if opened else ""
        ibriefs = [read(p) for p in (
            _auto_val(lambda: [os.path.join(A.workspace_path(isf[1], iplan, h), A.BRIEF_NAME)
                               for h in ist["closed"]], []) or []) if os.path.isfile(p)]
        check("asteward: an island proposal is refused at island_cap and below it files a sub-question, cuts its branch at base, joins the round-robin and gets an attempt whose brief names it",
              _auto_ok(lambda: (
                  len(opened) == 1
                  and E.Vault(isf[1]).get(qi).type == "question"
                  and E.Vault(isf[1]).get(qi).parent == isf[2]
                  and list(ist["islands"])[-1] == qi
                  and ist["islands"][qi]["branch"] == A.island_branch(isf[2], qi)
                  # cut at `base`, exactly as `open_run` cuts the plan's own islands
                  and _git(isf[0], "rev-parse", A.island_branch(isf[2], qi)) == ist["base"]
                  and ist["islands"][qi]["pointer"] == ist["base"]
                  and set(ist["islands"][qi]) == _ISLAND_KEYS
                  and len([e for e in _ev(island, "steward")
                           if e["ok"] and e["island"] == qi]) == 1
                  # it joins the round-robin, so a later attempt's brief is written FOR it
                  and any(qi in b for b in ibriefs)
                  # the plan's `islands:` field is hashed, so writing it would clear the PI's
                  # signature mid-run — the island lives in state.json instead
                  and read(os.path.join(isf[1], isf[5])) == iplan0
                  and qi not in iplan["islands"]
                  and E.auto_approval(iplan0)["state"] == "approved"
                  # and the very brief that island needs is one 05.2 refused
                  and _auto_val(lambda: E.auto_brief(
                      isf[1], isf[4], island=qi,
                      islands=list(ist["islands"])))["island"]["id"] == qi
                  and _auto_msg(lambda: E.auto_brief(isf[1], isf[4], island=qi))
                      == (f"auto brief: '{qi}' is neither the anchor nor an island of the "
                          f"flight plan"))))

        check("asteward: the window and the charge reach state.json at the spawn, not at the next event",
              _auto_ok(lambda: (
                  "steward-spawn" in gtrace
                  # the VERY next thing the driver does — before any further ledger event —
                  # is write the state, so a kill in between cannot re-open the window
                  and gtrace[gtrace.index("steward-spawn") + 1] == "save"
                  and any(t.startswith("record:") for t in gtrace))))

        # ---------------- a steward that comes due while every command is cooling waits a pass
        # `_wait_for_cooldown` polls WITHOUT dispatching exits, so a steward that entered it
        # would hold the whole loop for up to `agent_cooldown` while finished workers sat
        # unclosed. For the worker walk that wait is unavoidable; for advice it is pure loss.
        scmds = _auto_val(lambda: E.auto_command_list(gplan), [])
        soon = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(time.time() + 5))
        sctx = {"root": gf[1], "plan": gplan, "state": json.loads(json.dumps(gst)),
                "qid": gf[2], "repo": gf[0], "procs": {}, "lock_wait": 0.5,
                "t0": time.monotonic()}
        sctx["state"]["agents"] = {c: {"cooling_until": soon, "hits": 1} for c in scmds}
        sinv = ((sctx["state"].get("steward") or {}).get("invocations") or 0)
        t_cool = time.monotonic()
        _auto_val(lambda: A._steward_try(sctx))
        t_cool = time.monotonic() - t_cool
        check("asteward: a steward that comes due while every command is cooling is skipped rather than held in the cooldown wait",
              _auto_ok(lambda: (
                  bool(scmds)
                  and all(A._cooling(sctx, c) for c in scmds)
                  and t_cool < 2.0
                  and sctx.get("steward_proc") is None
                  and sctx["procs"] == {}
                  # untouched, so it simply comes due again on the next pass
                  and ((sctx["state"].get("steward") or {}).get("invocations") or 0) == sinv
                  and not os.path.isdir(os.path.join(gf[1], E.AUTO_DIR, gf[2],
                                                     A.STEWARD_DIR, str(sinv + 1))))))

        # ---------------------------- and a git that refuses the island branch is logged, not
        # allowed to unwind the record and leave an orphan question under the anchor
        iws = os.path.realpath(tempfile.mkdtemp(prefix="crux_stwd_"))
        _AUTO_TRASH.append(iws)
        write(os.path.join(iws, A.STEWARD_PROPOSAL_NAME), json.dumps(
            {"island": {"title": "a branch that cannot be cut",
                        "problem": "the island act has to survive a git that refuses"}}))
        # room under the cap, or the proposal is refused before the git is ever reached
        ictx = {"root": isf[1], "plan": dict(iplan, island_cap=9),
                "state": json.loads(json.dumps(ist)),
                "qid": isf[2], "repo": isf[0], "procs": {}, "lock_wait": 0.5,
                "t0": time.monotonic(), "steward_proc": None, "steward_ws": iws,
                "steward_command": "python3 dispatch.py still valid island"}
        iorig, iraised = _auto_val(lambda: A._git), ""
        if iorig is not None:
            def _gbad(cwd, *aa, _o=iorig, **kk):
                if aa and aa[0] == "branch":
                    raise E.CruxError(f"git branch failed in {cwd}: a refusing git")
                return _o(cwd, *aa, **kk)
            A._git = _gbad
        try:
            A._steward_apply(ictx)
        except Exception as e:                               # pragma: no cover - the defect
            iraised = repr(e)
        finally:
            if iorig is not None:
                A._git = iorig
        ilast = _auto_val(lambda: json.loads(
            read(_loop_ledger_path(isf[1], isf[2])).strip().splitlines()[-1]), {})
        check("asteward: a git that refuses the island branch is logged and the run carries on, rather than unwinding the record",
              _auto_ok(lambda: (
                  iraised == ""
                  and ilast.get("event") == "steward"
                  and ilast.get("ok") is False
                  and ilast.get("reason") == "steward-island"
                  and "could not be cut" in (ilast.get("detail") or "")
                  and ilast.get("island") is None
                  # no half-open island: the state the driver carries on with has exactly the
                  # islands it had before
                  and list(ictx["state"]["islands"]) == list(ist["islands"]))))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"asteward: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def run_auto_report():
    """Spec 05 PRD 05.3 §G — every attempt leaves a report, and the node links it.

    `crux validate` already complains when a hypothesis has files under `results/` and no
    report linked under `## Artifacts`. Before this slice an autopilot run produced exactly
    that shape for every attempt it closed, so a clean vault and a finished run were mutually
    exclusive. The fix is the report, written before `cmd_close` runs and linked in the same
    lock hold — a link written afterwards is a second writer of a node the engine just
    finished with."""
    print("\n# autopilot — the run report (spec 05, PRD 05.3)")
    try:
        A = _auto_mod()

        # ------------------------------------------------- the fixed template, byte for byte
        rplan = {"address": "obj.score", "direction": "max", "bar": -0.5}
        tk = [("x", "-0.25"), (" ", "0.5"), ("-", "no number")]
        want = ("# Attempt h9\n"
                "\n"
                "Objective obj.score = -0.25 (direction max, bar -0.5).\n"
                "\n"
                "## Checks\n"
                "\n"
                "- [x] check 1: met, found -0.25.\n"
                "- [ ] check 2: unmet, found 0.5.\n"
                "- [-] check 3: n/a, found no number.\n")
        got = _auto_val(lambda: E.auto_report_text(rplan, "h9", -0.25, tk), "")
        na = _auto_val(lambda: E.auto_report_text(rplan, "h9", None, tk), "")
        fail = _auto_val(lambda: E.auto_report_text(rplan, "h9", -0.25, tk,
                                                    failure="the worker\n exited   1"), "")
        check("areport: the no-closer report is a fixed template, byte for byte, and speaks the failure when there was one",
              _auto_ok(lambda: (
                  got == want
                  and "Objective obj.score = n/a (direction max, bar -0.5)." in na
                  and "## Failure" not in got
                  and fail == want.rstrip("\n") + "\n\n## Failure\n\nthe worker exited 1.\n"
                  and E.AUTO_REPORT_BYTES == 20000)))

        # -------------------------------------------------- one run each way, and the link
        onf = _ag_fixture(x0=2, closer="true", budget_attempts="1",
                          agent="python3 dispatch.py " + AG_STUB_ARGS)
        on = _loop_run("report-on", onf[1], onf[2], onf[5])
        off = _ag_fixture(x0=2, budget_attempts="1",
                          agent="python3 dispatch.py " + AG_STUB_ARGS)
        offr = _loop_run("report-off", off[1], off[2], off[5])

        def _linked(run, root):
            closed = (run["state"] or {}).get("closed") or []
            if not closed:
                return False
            for h in closed:
                arts = E.parse_artifacts(E.Vault(root).get(h)["body"])
                rel = f"{E.RESULTS_DIR}/{h}/{E.AUTO_REPORT_FILE}"
                if not [a for a in arts if a["path"] == rel and a["kind"] == "report"]:
                    return False
                if not os.path.isfile(os.path.join(root, rel)):
                    return False
                if os.path.getsize(os.path.join(root, rel)) > E.AUTO_REPORT_BYTES:
                    return False
            return True

        msgs_on = _auto_val(lambda: E.cmd_validate(onf[1]), [])
        msgs_off = _auto_val(lambda: E.cmd_validate(off[1]), [])

        def _missing(msgs, run):
            """`no report is linked` on an attempt THIS RUN closed.

            Every tier-zero fixture also carries a baseline closed BY HAND, with metrics under
            `results/` and no report — deliberately, because a fixture built with the code
            under test proves nothing. PRD-25 is about the attempts the driver closed, so the
            baseline's own standing problem is not this criterion's to answer."""
            closed = set((run["state"] or {}).get("closed") or [])
            return [m for nid, m in msgs
                    if "no report is linked" in m and nid in closed]
        check("areport: every attempt node links results/<hid>/report.md under Artifacts with and without a closer, and validate reports no missing-report problem",
              _auto_ok(lambda: (
                  _linked(on, onf[1]) and _linked(offr, off[1])
                  and _missing(msgs_on, on) == []
                  and _missing(msgs_off, offr) == []
                  # and the run did close attempts, so the two lines above are not vacuous
                  and bool((on["state"] or {}).get("closed"))
                  and bool((offr["state"] or {}).get("closed"))
                  # with a closer the report is the closer's words; without one it is the
                  # engine's template — either way the file is there and the node points at it
                  and "the closer wrote this line" in read(os.path.join(
                      onf[1], E.RESULTS_DIR, (on["state"] or {})["closed"][0],
                      E.AUTO_REPORT_FILE))
                  and read(os.path.join(
                      off[1], E.RESULTS_DIR, (offr["state"] or {})["closed"][0],
                      E.AUTO_REPORT_FILE)).startswith("# Attempt "))))

        # the link is idempotent and touches nothing else on the node — a resume runs
        # `_step_close` again, so linking twice has to be a no-op rather than two bullets
        h1 = ((offr["state"] or {}).get("closed") or [""])[0]
        rel1 = _auto_val(lambda: f"{E.RESULTS_DIR}/{h1}/{E.AUTO_REPORT_FILE}",
                         f"{E.RESULTS_DIR}/{h1}/report.md")
        before = _auto_val(lambda: read(node_path(off[1], h1)), "")
        line1 = _auto_val(lambda: E.auto_link_report(off[1], h1, rel1), "")
        again = _auto_val(lambda: read(node_path(off[1], h1)), "")
        drift = _auto_val(lambda: E.lock_drift(E.Vault(off[1]).get(h1)), "<absent>")
        noart = _auto_val(lambda: _ag_strip_artifacts(off[1], off[4]), False)
        check("areport: linking the same report twice rewrites nothing, leaves the lock undrifted, and refuses a node that cannot hold a link",
              _auto_ok(lambda: (
                  bool(line1) and line1 == f"- [Report]({rel1})"
                  and before == again and before != ""
                  and not drift
                  and _auto_msg(lambda: E.auto_link_report(off[1], off[2], rel1))
                      == f"auto link report applies to a hypothesis (got a 'question' "
                         f"for '{off[2]}')"
                  and noart
                  and _auto_msg(lambda: E.auto_link_report(off[1], off[4], rel1))
                      == f"{off[4]} has no ## Artifacts section to link into")))
    except Exception as e:                                   # pragma: no cover - wave-1 guard
        check(f"areport: section ran without crashing ({e!r})", False)
    finally:
        _auto_sweep()


def _ag_strip_artifacts(root, hid):
    """Remove a node's whole `## Artifacts` section, and say whether it is gone.

    The refusal for a node with nowhere to link is otherwise untestable: every node the engine
    writes carries the section, so the only witness is one a test took it away from."""
    p = node_path(root, hid)
    t = read(p)
    t = re.sub(r"\n## Artifacts\n.*?(?=\n## |\n<!-- crux:ledger:start -->|\Z)", "\n", t,
               flags=re.S)
    write(p, t)
    return "## Artifacts" not in read(p)


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["close", "--help"], ["hypothesize", "--help"], ["serve", "--help"],
                 ["selftest", "--help"], ["approve", "--help"], ["synthesize", "--help"], ["deck", "--help"],
                 ["brief", "--help"], ["glossary", "--help"], ["doctor", "--help"],
                 ["auto", "--help"], ["auto", "check", "--help"],
                 ["auto", "promote", "--help"], ["auto", "refs", "--help"],
                 ["auto", "approve", "--help"], ["auto", "run", "--help"],
                 ["auto", "status", "--help"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True, encoding="utf-8")
        # `auto` is PRD 05.0's own verb: its check is named with the autopilot prefix the
        # rest of that PRD's checks carry, so a wave-1 red line is attributable at a glance.
        nm = f"help: crux {' '.join(argv)}"
        check(f"auto: {nm}" if argv[0] == "auto" else nm,
              r.returncode == 0 and len(r.stdout) > 40)

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

        # ---------------------------------------------------------------- vault drift + migrate
        drift = os.path.join(tmp, "drifted")
        shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), drift)
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
    run_situate()
    run_situate_agent()
    run_methodology()
    run_methodology_migration()
    run_design_agent()
    run_science_voice()
    run_situate_title_anchor()
    run_cli_third_person()
    run_voice_enforcement()
    run_persona_eval()
    run_glossary()
    run_glossary_migration()
    run_glossary_counting()
    run_glossary_oracle()
    run_glossary_filter()
    run_sortlab_fixture()
    run_glossary_write()
    run_agent_evals()
    run_eval_scorer()
    run_mutation_harness()
    run_ground_truth_fixtures()
    run_proxy_register()
    run_flight_plan()
    run_builds_on()
    run_puct()
    run_auto_brief()
    run_auto_cli()
    run_auto_lock()
    run_auto_reserve()
    run_auto_git()
    run_auto_workspace()
    run_auto_retention()
    run_auto_scorer()
    run_auto_verbs()
    run_auto_purity()
    run_auto_grammar()
    run_auto_approve()
    run_auto_loop()
    run_auto_resume()
    run_auto_stops()
    run_auto_leash()
    run_auto_loop_purity()
    run_auto_agents()
    run_auto_cooldown()
    run_auto_probe()
    run_auto_closer()
    run_auto_steward()
    run_auto_report()
    run_cli_help()
    run_doctor()
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
