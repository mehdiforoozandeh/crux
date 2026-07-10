#!/usr/bin/env python3
"""End-to-end self-test for crux — builds a dummy vault and asserts every
invariant. No GPU / tokens / SLURM; pure file ops. Exit non-zero on any failure.

    python selftest.py [--keep DIR]   # --keep leaves the demo vault for inspection
"""
import os, sys, shutil, tempfile, subprocess, argparse
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
