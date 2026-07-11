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
          set(snap.keys()) == {"engine_version", "project", "nodes", "tree", "queue"})
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


def run_serve():
    print("\n# serve (crux serve — stdlib browser cockpit host)")
    import json, socket, threading, urllib.request
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
        for path, ctype in (("/app.js", "javascript"), ("/style.css", "css")):
            try:
                with urllib.request.urlopen(base + path, timeout=5) as r:
                    ok = ctype in (r.headers.get("Content-Type") or "")
            except Exception:
                ok = False
            check(f"webui: serves {path}", ok)
    finally:
        httpd.shutdown(); httpd.server_close()
    shutil.rmtree(root, ignore_errors=True)

    # -- pure-read at the browser layer: the cockpit only ever GETs the snapshot, never mutates
    #    the vault (single read endpoint, no fetch method override). Mirrors the engine invariant.
    check("webui: app.js is pure-read (one GET of snapshot.json, no write verbs)",
          app_js.count("fetch(") == 1 and 'fetch("snapshot.json"' in app_js and "method:" not in app_js)

    # -- issue #1 regression guard: capturing the pointer on the tree <svg> retargets the
    #    follow-up `click` to the svg itself, so node/toggle hit-testing (e.target.closest)
    #    silently no-ops and the whole tree goes dead. Never reintroduce it there.
    check("webui: app.js never setPointerCapture on the tree (issue #1 regression)",
          "setPointerCapture(" not in app_js)


def run_cli_help():
    print("\n# CLI --help smoke")
    for argv in (["--help"], ["ask", "--help"], ["close", "--help"], ["hypothesize", "--help"], ["serve", "--help"]):
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
    run_snapshot()
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
