#!/usr/bin/env python3
"""End-to-end self-test for crux — builds a dummy vault and asserts every
invariant. No GPU / tokens / SLURM; pure file ops. Exit non-zero on any failure.

    python selftest.py [--keep DIR]   # --keep leaves the demo vault for inspection
"""
import os, sys, shutil, tempfile, subprocess, argparse, hashlib, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E
import render as R

_PASS, _FAIL = [], []
def check(name, cond):
    (_PASS if cond else _FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name)

def expect_error(name, fn):
    try:
        fn(); check(name, False)
    except E.CruxError:
        check(name, True)

def read(p):
    with open(p) as f: return f.read()

def edit(p, old, new, count=-1):
    with open(p) as f: t = f.read()
    with open(p, "w") as f: f.write(t.replace(old, new) if count < 0 else t.replace(old, new, count))

def node_path(root, nid):
    return E.Vault(root).get(nid)["path"]


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
    h1, _ = E.cmd_hypothesize(root, "masked-token beats masked-stem", parent=q11,
                              verifiables=["imp-Spearman ≥ +0.01 vs stem", "no NaN over 5 eval epochs"])
    h2, _ = E.cmd_hypothesize(root, "post_conv FiLM beats per_conv", parent=q11,
                              verifiables=["imp-Spearman ≥ +0.005 vs per_conv", "calibration not worse"])
    check("hypothesize: h1 under q1.1", E.Vault(root).get(h1).parent == q11)
    check("hypothesize: 2 verifiables", E.count_verifiables(read(node_path(root, h1)))[1] == 2)

    # 4. NEGATIVE: running without verifiables is rejected (on a stripped idea)
    h_bad, _ = E.cmd_hypothesize(root, "temp bad idea", parent=q11)
    bp = node_path(root, h_bad)
    edit(bp, "- [ ] _(state a falsifiable, pre-registered check)_", "(verifiables removed)")
    expect_error("validator: no running without verifiables", lambda: E.cmd_test(root, h_bad, to="running"))
    os.remove(bp); E.refresh(root)  # discard the throwaway idea

    # 5. test transitions
    E.cmd_test(root, h1, to="staged")
    check("test: h1 staged", E.Vault(root).get(h1).status == "staged")
    E.cmd_test(root, h1, to="running", run="job 40012")
    check("test: h1 running", E.Vault(root).get(h1).status == "running")
    check("test: run link recorded", "job 40012" in read(node_path(root, h1)))
    E.cmd_test(root, h2, to="running")

    # 6. close: h1 all-met -> supported ; h2 one-unmet -> partial
    edit(node_path(root, h1), "- [ ]", "- [x]")               # all met
    v1 = E.cmd_close(root, h1, metric="imp +0.012")
    check("close: h1 supported", v1 == "supported")
    edit(node_path(root, h2), "- [ ]", "- [x]", count=1)       # exactly one met
    v2 = E.cmd_close(root, h2, metric="imp +0.003")
    check("close: h2 partial", v2 == "partial")
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

    # 9a. answer (resolve) propagates: q1.1 resolved -> q1 trips review
    E.cmd_answer(root, q11, text="mask_token is the load-bearing knob; FiLM placement is noise.")
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
    with open(seed_path, "w") as f: f.write(SEED)
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
    with open(bad_seed, "w") as f: f.write("- Project: Half\n  - Q: ok\n  - H: floating under project\n    - v: y\n")
    expect_error("seed: malformed seed rejected", lambda: E.cmd_init_from(bad_seed, os.path.join(base, "vault2")))
    check("seed: no partial vault left behind", not os.path.exists(os.path.join(base, "vault2", ".crux.yaml")))
    shutil.rmtree(base, ignore_errors=True)


def write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
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
    want_sha = hashlib.sha256(read(src1).encode()).hexdigest()
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
    check("wmig: ENGINE_VERSION bumped to 1.1", E.ENGINE_VERSION == "1.1")
    shutil.rmtree(root, ignore_errors=True)


def run_version():
    print("\n# engine-version stamp + drift")
    root = tempfile.mkdtemp(prefix="crux_ver_")
    shutil.rmtree(root); os.makedirs(root)
    E.cmd_init("Versioned", root)
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
    h1, _ = E.cmd_hypothesize(root, "a hyp", parent=q1, verifiables=["x"])
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


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["close", "--help"], ["hypothesize", "--help"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True)
        check(f"help: crux {' '.join(argv)}", r.returncode == 0 and len(r.stdout) > 40)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", default=None, help="build the demo vault at this path and keep it")
    a = ap.parse_args()
    root = run_demo(a.keep)
    run_seed()
    run_wiki()
    run_wiki_migration()
    run_version()
    run_integrity()
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
