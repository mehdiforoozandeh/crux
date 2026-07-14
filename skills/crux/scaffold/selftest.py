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
    h1, _ = E.cmd_hypothesize(root, "h one", parent=q2, verifiables=["a", "b"])
    h2, _ = E.cmd_hypothesize(root, "h two", parent=q2, verifiables=["a", "b"])
    E.cmd_test(root, h1, to="running"); E.cmd_test(root, h2, to="running")
    edit(node_path(root, h1), "- [ ]", "- [x]")             # both met -> supported
    E.cmd_close(root, h1, metric="imp +0.012")
    edit(node_path(root, h2), "- [ ]", "- [x]", count=1)     # one met -> partial
    E.cmd_close(root, h2, metric="imp +0.003")
    syn, _ = E.cmd_synthesize(root, "weave one two", [q1, q2])

    v = E.Vault(root)
    snap = E.snapshot(v)

    # -- top-level shape / serializability
    check("snapshot: top-level keys exact",
          set(snap.keys()) == {"engine_version", "project", "nodes", "tree", "queue", "wiki"})
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
          [r["id"] for r in snap["queue"]] == [nid for nid, _ in E.cmd_review(root)])
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
    check("snapshot: h2 verdict partial", snap["nodes"][h2]["verdict"] == "partial")

    # -- question nodes carry a ledger whose counts match ledger_block / ledger_counts
    q2n = snap["nodes"][q2]
    lc = E.ledger_counts(v, q2)
    lb = E.ledger_block(v, q2)
    check("snapshot: q2 ledger == ledger_counts", q2n["ledger"] == lc)
    check("snapshot: q2 counts (2 children, 2 done, 1 supported, 1 partial)",
          lc["children"] == 2 and lc["ideas_done"] == 2 and lc["supported"] == 1 and lc["partial"] == 1)
    check("snapshot: ledger_counts consistent with ledger_block text",
          f"**{lc['children']} children**" in lb
          and f"supported {lc['supported']}" in lb and f"partial {lc['partial']}" in lb)

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
    finally:
        httpd.shutdown(); httpd.server_close()

    # -- the real CLI prints the URL promptly (flushed) while the server is still running, and
    # serve stays READ-ONLY even on a drifted vault (version-stamping would be a forbidden write).
    # A reader thread consumes stdout so we catch the banner even though the server then blocks.
    cfg_path = os.path.join(root, ".crux.yaml")
    edit(cfg_path, f"engine_version: {E.ENGINE_VERSION}", "engine_version: 0.9")
    cfg_before = read(cfg_path)
    cli_port = S.find_free_port("127.0.0.1", 8940)
    proc = subprocess.Popen(
        [sys.executable, os.path.join(HERE, "crux.py"), "serve", "--no-open", "--port", str(cli_port)],
        cwd=root, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    lines = []
    def _read_banner():
        for line in proc.stdout:
            lines.append(line)
            if "http://localhost:" in line:
                break
    tr = threading.Thread(target=_read_banner, daemon=True); tr.start()
    tr.join(timeout=10)
    try:
        proc.terminate()
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
    buf = "".join(lines)
    check("serve: `crux serve` CLI prints the URL promptly (flushed to a pipe)",
          f"http://localhost:{cli_port}" in buf and buf.count("http://localhost:") == 1)
    check("serve: read-only on a drifted vault (.crux.yaml never re-stamped)",
          read(cfg_path) == cfg_before)

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

    # -- pure-read at the browser layer: the cockpit only ever GETs (the snapshot poll plus
    #    the lazy wiki-page route — relaxation pre-registered in docs/prd/gui-wiki-tab.md),
    #    never mutates the vault (no fetch method override). Mirrors the engine invariant.
    check("webui: app.js is pure-read (two GETs: snapshot + wiki page, no write verbs)",
          app_js.count("fetch(") == 2 and 'fetch("snapshot.json"' in app_js
          and "/wiki/" in app_js and "method:" not in app_js)

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


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["close", "--help"], ["hypothesize", "--help"], ["serve", "--help"],
                 ["selftest", "--help"]):
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py")] + argv,
                           capture_output=True, text=True)
        check(f"help: crux {' '.join(argv)}", r.returncode == 0 and len(r.stdout) > 40)

    # -- the post-init hint must work from where the user just ran init: the vault is
    #    created *below* the cwd, so the hint carries the cd into it
    tmp = tempfile.mkdtemp(prefix="crux-hint-")
    try:
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "init", "Hint Project"],
                           capture_output=True, text=True, cwd=tmp)
        check("init hint: includes `cd cruxvault`", r.returncode == 0 and "cd cruxvault" in r.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
    run_snapshot()
    run_wiki_gui()
    run_serve()
    run_webui()
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
