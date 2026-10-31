#!/usr/bin/env python3
"""Self-test for the lean autopilot (spec 18, `auto.py`).

    python3 selftest_auto.py          # standalone: prints PASSED a / b, exits 1 on any failure

`run_all(check)` takes selftest.py's `check(name, cond)`, so the counts aggregate there. Every
test runs in a temp dir: a stub worker (via CRUX_AUTO_CLAUDE) and stub scorers in temp git
repos. No network, no tokens."""
import os, sys, json, shlex, shutil, subprocess, tempfile, time
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t", "GIT_COMMITTER_NAME": "t",
           "GIT_COMMITTER_EMAIL": "t@t"}

# The stub worker. Reads its brief on stdin, logs argv + brief, then acts out the k-th mode of
# CRUX_STUB_MODES (the last mode repeats). `prog.txt`'s first line is the program's number.
STUB = r'''import os, sys, json, subprocess, time
tmp = os.environ["CRUX_STUB_DIR"]
brief = sys.stdin.buffer.read().decode("utf-8")
cf = os.path.join(tmp, "stub_count")
k = int(open(cf).read()) if os.path.exists(cf) else 0
open(cf, "w").write(str(k + 1))
with open(os.path.join(tmp, "stub_log"), "a") as f:
    f.write(json.dumps({"argv": sys.argv[1:], "brief": brief}) + "\n")
modes = os.environ.get("CRUX_STUB_MODES", "up").split(",")
mode = modes[min(k, len(modes) - 1)]
def commit(msg):
    subprocess.check_call(["git", "add", "-A"], stdout=subprocess.DEVNULL)
    subprocess.check_call(["git", "commit", "-q", "--allow-empty-message", "-m", msg])
def setv(x):
    open("prog.txt", "w").write(x + "\n")
cur = open("prog.txt").read().split("\n")[0]
if mode == "up":
    setv(repr(float(cur) + 1)); commit("raise the number by one")
elif mode == "tiny":
    setv(repr(float(cur) + 0.25)); commit("nudge the number by 0.25")
elif mode == "down":
    setv(repr(float(cur) - 1)); commit("lower the number by one")
elif mode == "same":
    open("prog.txt", "a").write("# a comment\n"); commit("")
elif mode == "empty":
    subprocess.check_call(["git", "commit", "-q", "--allow-empty", "-m", "no change"])
elif mode == "frozen":
    open("frozen.txt", "a").write("x\n"); commit("touch the frozen file")
elif mode in ("bad", "garbage", "nokey", "die"):
    setv(mode); commit("try " + mode)
elif mode == "none":
    pass
elif mode == "crash":
    sys.exit(3)
elif mode == "rate":
    print("You've hit your session limit - resets 9:10pm"); sys.exit(1)
elif mode == "slow":
    time.sleep(30)
elif mode == "mv":
    os.makedirs("src", exist_ok=True)
    subprocess.check_call(["git", "mv", "frozen.txt", "src/frozen.txt"])
    commit("move the frozen file")
elif mode == "ignore":
    open("prog.local", "w").write("50\n")
    setv(repr(float(cur) + 1)); commit("raise and leave an ignored file")
elif mode == "sleep":
    setv("sleep"); commit("make the scorer sleep")
elif mode == "rateslow":
    time.sleep(4); print("You've hit your session limit"); sys.exit(1)
elif mode == "nap":
    time.sleep(1.5); setv(repr(float(cur) + 1)); commit("raise after a nap")
'''

# The stub scorer: reads prog.txt from its cwd, counts its calls, and obeys the contract.
SCORER = r'''import os, sys, json
tmp = os.environ["CRUX_STUB_DIR"]
cf = os.path.join(tmp, "score_count")
k = len(open(cf).read().splitlines()) if os.path.exists(cf) else 0
jit = [float(j) for j in os.environ.get("CRUX_STUB_JITTER", "").split(",") if j]
open(cf, "a").write(os.environ.get("CRUX_ATTEMPT", "") + "|" + os.environ.get("CRUX_WORKSPACE", "") + "\n")
import time
first = (open("prog.txt").read().split("\n") or [""])[0].strip()
if os.path.exists("prog.local"):
    first = open("prog.local").read().strip()
if first == "sleep":
    time.sleep(30)
if first == "garbage":
    print("not json"); sys.exit(0)
if first == "nokey":
    print(json.dumps({"passed": True})); sys.exit(0)
if first == "die":
    sys.exit(2)
try:
    v = float(first)
except ValueError:
    print(json.dumps({"passed": False, "reason": "not a number"})); sys.exit(1)
print(json.dumps({"x": {"value": v + (jit[k] if k < len(jit) else 0.0)}, "passed": True}))
'''
HANG = 'import time\ntime.sleep(30)\n'
CONST = 'import json\nprint(json.dumps({"x": {"value": 5.0}, "passed": True}))\n'


def _sh(argv, cwd):
    subprocess.check_call(argv, cwd=cwd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                          env=dict(os.environ, **GIT_ENV))


def _write(path, text):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def fixture(tmp, scorer="score.py", modes="up", jitter="", **fields):
    """A vault with one question, a program repo, a plan at auto/<qid>/plan.md. Returns
    (root, plan_path, qid, repo)."""
    repo = os.path.join(tmp, "repo")
    os.makedirs(repo)
    _write(os.path.join(repo, "prog.txt"), "1.0\n")
    _write(os.path.join(repo, "frozen.txt"), "frozen\n")
    _write(os.path.join(repo, ".gitignore"), "*.local\n")
    _sh(["git", "init", "-q"], repo)
    _sh(["git", "add", "-A"], repo)
    _sh(["git", "commit", "-q", "-m", "base"], repo)
    base = subprocess.check_output(["git", "-C", repo, "rev-parse", "HEAD"]).decode().strip()
    _write(os.path.join(tmp, "score.py"), SCORER)
    _write(os.path.join(tmp, "const.py"), CONST)
    _write(os.path.join(tmp, "hang.py"), HANG)
    _write(os.path.join(tmp, "stub.py"), STUB)
    root = os.path.join(tmp, "vault")
    E.cmd_init("Auto Test", root)
    qid, _fn = E.cmd_ask(root, "Can the number go up?")
    plan = {"anchor": qid, "repo": repo, "base": base, "editable": "prog.txt",
            "scorer": f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(tmp, scorer))}",
            "objective": "x max 100", "mode": "climb", "budget_hours": "8",
            "attempt_minutes": "1", "worker": "opus high"}
    plan.update(fields)
    guidance = plan.pop("guidance", "Try making the number bigger.")
    path = os.path.join(root, "auto", qid, "plan.md")
    _write(path, "---\n" + "".join(f"{k}: {v}\n" for k, v in plan.items() if v is not None)
           + "---\n\n" + guidance + "\n")
    # run through sys.executable, never as a #! script: Windows cannot execute one
    stub = f"{shlex.quote(sys.executable)} {shlex.quote(os.path.join(tmp, 'stub.py'))}"
    os.environ.update({"CRUX_AUTO_CLAUDE": stub, "CRUX_STUB_DIR": tmp,
                       "CRUX_STUB_MODES": modes, "CRUX_AUTO_RATE_WAIT": "0",
                       "CRUX_STUB_JITTER": jitter})
    os.environ.update(GIT_ENV)
    return root, path, qid, repo


def finding(root, hid):
    """The one Finding filed on attempt node `hid`, as finding_json, or {}."""
    v = E.Vault(root)
    fs = E.node_findings(v, hid)
    return E.finding_json(fs[0]) if len(fs) == 1 else {}


def ledger(root, qid):
    p = os.path.join(root, "auto", qid, "ledger.jsonl")
    if not os.path.exists(p):
        return []
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]


def attempts(root, qid):
    return [l for l in ledger(root, qid) if l.get("event") == "attempt"]


def lines(path):
    return open(path).read().splitlines() if os.path.exists(path) else []


def raises(fn, *needles):
    try:
        fn()
    except E.CruxError as e:
        return all(n in str(e) for n in needles)
    return False


def run_all(check):
    try:
        import auto as A
    except ImportError as e:
        check(f"auto.py imports ({e})", False)
        return
    keep_env = dict(os.environ)
    try:
        for section in (_plan_tests, _unit_tests, _finding_tests, _run_tests,
                        _bench_plan_tests):
            try:
                section(check, A)
            except Exception as e:  # an unexpected result is a FAIL line, never a traceback
                check(f"{section.__name__} crashed: {type(e).__name__}: {e}", False)
    finally:
        os.environ.clear()
        os.environ.update(keep_env)


# ------------------------------------------------------------------------------------- plan
def _plan_tests(check, A):
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp)
        p = A.load_plan(path)
        check("plan: a full plan loads with every field",
              p["anchor"] == qid and p["address"] == "x" and p["direction"] == "max"
              and p["bar"] == 100.0 and p["editable"] == ["prog.txt"] and p["mode"] == "climb"
              and p["model"] == "opus" and p["effort"] == "high"
              and p["guidance"].startswith("Try making"))
        check("plan: PLAN_FIELDS is the 12 names; min_gain is optional and defaults to 0",
              len(A.PLAN_FIELDS) == 12 and "guidance" in A.PLAN_FIELDS
              and "min_gain" in A.PLAN_FIELDS and p.get("min_gain") == 0.0)

    for bad in ("-0.5", "tiny"):
        with tempfile.TemporaryDirectory() as tmp:
            root, path, qid, repo = fixture(tmp, min_gain=bad)
            check(f"plan: a min_gain of {bad!r} is refused with a message naming min_gain",
                  raises(lambda: A.load_plan(path), "min_gain", ">= 0"))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, mode=None, budget_hours=None, attempt_minutes=None,
                                        worker=None)
        p = A.load_plan(path)
        check("plan: defaults fill mode, budget, attempt time and worker",
              p["mode"] == "climb" and p["budget_hours"] == 8.0
              and p["attempt_minutes"] == 20.0 and (p["model"], p["effort"]) == ("opus", "high"))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, island_cap="3", budget_attempts="40",
                                        agent='claude -p "{brief}"')
        check("plan: an old spec-05 plan is refused with a message naming the new fields",
              raises(lambda: A.load_plan(path), "island_cap", "budget_attempts", "agent",
                     *A.PLAN_FIELDS))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, extra_knob="1")
        check("plan: a plan with more than the allowed fields is refused",
              raises(lambda: A.load_plan(path), "extra_knob"))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, objective="x sideways one",
                                        mode="wander", worker="opus high --verbose")
        _write(path, open(path).read().replace("scorer: ", "scorer_gone: "))
        try:
            A.load_plan(path)
            msg = ""
        except E.CruxError as e:
            msg = str(e)
        check("plan: every problem is listed at once",
              all(s in msg for s in ("objective", "mode", "worker", "scorer_gone", "'scorer' is required")))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, worker="opus high --dangerously-skip")
        check("plan: a worker field with any extra token is refused",
              raises(lambda: A.load_plan(path), "worker"))


# ------------------------------------------------------------------------------------- units
def _unit_tests(check, A):
    os.environ.pop("CRUX_AUTO_CLAUDE", None)
    plan = {"model": "sonnet", "effort": "medium"}
    argv = A.worker_argv(plan)
    check("worker: the command is claude -p with model, effort and no web tools",
          argv == ["claude", "-p", "--model", "sonnet", "--effort", "medium",
                   "--permission-mode", "bypassPermissions",
                   "--disallowedTools", "WebFetch", "WebSearch"])
    os.environ["CRUX_AUTO_CLAUDE"] = "/x/stub"
    check("worker: CRUX_AUTO_CLAUDE replaces the binary", A.worker_argv(plan)[0] == "/x/stub")
    check("worker: web_denied is true only when both web tools are denied",
          A.web_denied(argv) and not A.web_denied(argv[:-1])
          and not A.web_denied(argv[:-3]))

    check("rule 1: an editable directory admits its files, nothing else",
          A.editable_ok("src/a.py", ["src/"]) and A.editable_ok("prog.txt", ["prog.txt"])
          and not A.editable_ok("src2/a.py", ["src/"])
          and not A.editable_ok("prog.txt.bak", ["prog.txt"]))

    rows = [{"id": "h1", "score": 1.0, "visits": 5}, {"id": "h2", "score": 3.0, "visits": 9},
            {"id": "h3", "score": 2.0, "visits": 0}]
    check("rule 5: climb (c_puct 0) picks the best every time, max and min",
          all(A.puct_select(rows, 0.0, "max") == "h2" for _ in range(5))
          and A.puct_select(rows, 0.0, "min") == "h1")
    check("rule 5: explore (c_puct 1.0) can pick a non-best parent",
          A.puct_select(rows, 1.0, "max") != "h2")
    check("rule 5: PUCT keeps the ERA arithmetic (rank + c/N*sqrt(total)/(1+visits))",
          abs(A.puct_rank(rows, 1.0, "max")[0]["puct"]
              - (0.5 + 1.0 / 3 * 14 ** 0.5 / 1)) < 1e-12)

    check("rate limit: provider limits match, a program's own 'limit' does not",
          A.rate_limited("You've hit your session limit - resets 9pm")
          and A.rate_limited("Error 529 overloaded") and not A.rate_limited("iteration limit 5"))
    check("objective: a {value: n} leaf resolves; a missing or non-numeric one raises",
          A.metrics_value({"a": {"b": {"value": 2}}}, "a.b") == 2.0
          and _bad(A, {"a": {}}, "a.b") and _bad(A, {"a": {"value": "x"}}, "a")
          and _bad(A, {"a": {"value": float("nan")}}, "a"))


def _bad(A, tree, addr):
    try:
        A.metrics_value(tree, addr)
    except ValueError:
        return True
    return False


# ------------------------------------------------------------------------- Findings (spec 19)
def _finding_tests(check, A):
    src = open(os.path.join(HERE, "auto.py"), encoding="utf-8").read()
    check("findings: auto.py calls no approve_null, cmd_close or cmd_test (grep)",
          "approve_null" not in src and "cmd_close" not in src and "cmd_test" not in src)
    eps = getattr(A, "DETERMINISTIC_MIN_GAIN", None)
    check("Q10: a deterministic scorer's min_gain defaults to a tiny epsilon (0 < eps <= 1e-6)",
          isinstance(eps, float) and 0 < eps <= 1e-6)
    emg = getattr(A, "effective_min_gain", None)
    check("Q10: spread 0 and no min_gain -> the epsilon; a noisy scorer keeps the plan's 0; "
          "a plan min_gain always wins",
          emg is not None and emg(0, 0.0) == eps and emg(0, None) == eps
          and emg(0, 0.5) == 0.0 and emg(1.5, 0.0) == 1.5 and emg(1.5, 0.5) == 1.5)
    af = getattr(A, "attempt_finding", None)
    if af is None:
        check("findings: attempt_finding exists", False)
        return
    # (status, value, parent, direction, min_gain, noise) -> (direction, confidence)
    cases = [
        (("kept", 2.0, 1.0, "max", 0.0, 0.5), ("supports", "strong")),     # margin 1 > 0.5
        (("kept", 1.5, 1.0, "max", 0.0, 0.5), ("supports", "moderate")),   # margin = noise
        (("kept", 1.3, 1.0, "max", 0.0, 0.5), ("supports", "moderate")),   # margin < noise
        (("kept", 1.0, 1.0, "max", 0.0, 0.5), ("against", "moderate")),    # not better
        (("kept", 0.0, 1.0, "max", 0.0, 0.5), ("against", "moderate")),
        (("kept", 0.0, 1.0, "min", 0.0, 0.5), ("supports", "strong")),     # min direction
        (("kept", 0.5, 1.0, "min", 0.0, 0.5), ("supports", "moderate")),
        (("kept", 2.0, 1.0, "max", 0.25, 0.0), ("supports", "strong")),    # spread 0: min_gain
        (("kept", 1.5, 1.0, "max", 0.25, 0.0), ("supports", "moderate")),  # margin 0.25 = mg
        (("kept", 1.25, 1.0, "max", 0.25, 0.0), ("against", "moderate")),  # gain = mg: not better
        (("kept", 1.0 + 1e-6, 1.0, "max", eps or 0.0, 0.0), ("supports", "strong")),  # marginal
        (("rejected", None, 1.0, "max", 0.0, 0.5), (E.NO_ANSWER, "weak")),
        (("failed", None, 1.0, "max", 0.0, 0.5), (E.NO_ANSWER, "weak")),
        (("discarded", None, 1.0, "max", 0.0, 0.5), (E.NO_ANSWER, "weak")),
    ]
    bad = [(c, af(*c)[:2], want) for c, want in cases if tuple(af(*c)[:2]) != want]
    check(f"findings: the mapping table (kept/better, noise, min_gain, rejected/failed){bad or ''}",
          not bad)

    # the strong/moderate boundary by a second method: exact rational arithmetic on a grid,
    # written from the ruling ("strong when the gain beats the bar by more than noise; spread
    # 0 -> min_gain"), never from auto.py's formula
    from fractions import Fraction as Fr
    miss = []
    for d in ("max", "min"):
        for mg in (Fr(0), Fr(1, 4), Fr(1, 2)):
            for nz in (Fr(0), Fr(1, 4), Fr(3, 4)):
                for k in range(-12, 13):
                    p, val = Fr(1), Fr(1) + Fr(k, 8) * (1 if d == "max" else -1)
                    gain = (val - p) if d == "max" else (p - val)
                    g = mg if (mg > 0 or nz > 0) else Fr(0)   # epsilon handled below
                    if mg == 0 and nz == 0:
                        continue                              # the epsilon case: own assert
                    beyond = gain - g                          # how far past the bar
                    want = ("against", "moderate") if beyond <= 0 else \
                        ("supports", "strong" if beyond > (nz if nz else mg) else "moderate")
                    got = tuple(af("kept", float(val), float(p), d, float(mg), float(nz))[:2])
                    if got != want:
                        miss.append((d, str(mg), str(nz), str(val), got, want))
    check(f"findings: the strong/moderate boundary agrees with exact arithmetic "
          f"({len(miss)} disagree{': ' + str(miss[:3]) if miss else ''})", not miss)

    # integration: a noisy scorer (baseline 1.0, 1.5, 1.0 -> spread 0.5)
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,up,tiny,same,down", jitter="0,0.5")
        A.run(root, path, max_attempts=4)             # setup scores calls 0-3, worker mode 0
        r = next((l for l in ledger(root, qid) if l["event"] == "setup"), {})
        check("Q10: a noisy scorer: setup records the spread of 3 baseline scores as noise",
              r.get("ok") and abs((r.get("noise") or 0) - 0.5) < 1e-12 and r["baseline"] == 1.0)
        at = attempts(root, qid)
        fs = [(finding(root, a["id"]).get("direction"), finding(root, a["id"]).get("confidence"))
              for a in at]
        check(f"Q10: noisy run: margin 1 > 0.5 strong, 0.25 <= 0.5 moderate, tie and loss "
              f"against ({fs})",
              [a.get("score") for a in at] == [2.0, 2.25, 2.25, 1.25]
              and fs == [("supports", "strong"), ("supports", "moderate"),
                         ("against", "moderate"), ("against", "moderate")])


# --------------------------------------------------------------------------------- the loop
def _run_tests(check, A):
    # rule 6: the setup check scores the base, checks that the score responds, runs the worker
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp)
        r = A.check(root, path)
        check("rule 6: a sound setup passes with the baseline and the scorer's seconds",
              r["ok"] and r["baseline"] == 1.0 and r["scorer_seconds"] > 0
              and r["problems"] == [])
        log = [json.loads(l) for l in lines(os.path.join(tmp, "stub_log"))]
        check("rule 6: the setup check runs the worker once, brief on stdin, web denied",
              len(log) == 1 and "prog.txt" in log[0]["brief"]
              and A.web_denied(["x"] + log[0]["argv"]))
        check("check --static reads the plan only", A.check(root, path, static=True)["ok"]
              and len(lines(os.path.join(tmp, "stub_log"))) == 1)
        sc0 = [l for l in lines(os.path.join(tmp, "score_count")) if l.split("|")[0] == "0"]
        check("rule 6 (Q10): check scores the baseline 3 times (plus one response check)",
              len(sc0) == 4)
        check("rule 6 (Q10): a deterministic scorer records noise 0 in the check result",
              r.get("noise") == 0.0)
        check("setup leaves no worktree behind", not os.path.exists(
            os.path.join(root, "auto", qid, "work", "setup")))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, scorer="const.py")
        r = A.check(root, path)
        check("rule 6: a scorer that does not respond to the program is refused",
              not r["ok"] and any("respond" in p for p in r["problems"]))

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="none")
        r = A.check(root, path)
        check("rule 6: a worker that cannot commit is refused",
              not r["ok"] and any("commit" in p for p in r["problems"]))
        stop = A.run(root, path)
        check("rule 6: run stops at setup and files nothing",
              stop["reason"] == "setup" and not attempts(root, qid)
              and [l["event"] for l in ledger(root, qid)] == ["setup", "stop"])

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp)
        real = A.worker_argv
        A.worker_argv = lambda plan: [x for x in real(plan) if x not in
                                      ("--disallowedTools", "WebFetch", "WebSearch")]
        try:
            r = A.setup_check(root, A.load_plan(path), worker=False)
        finally:
            A.worker_argv = real
        check("a worker with web tools enabled is refused at setup",
              not r["ok"] and any("web" in p.lower() for p in r["problems"]))

    # climb: keep-or-reset on the best; nodes filed and closed on derived verdicts
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,up,up,same,up")
        stop = A.run(root, path, max_attempts=3)
        at = attempts(root, qid)
        v = E.Vault(root)
        check("run: three attempts, then a max_attempts stop",
              stop["event"] == "stop" and stop["reason"] == "max_attempts" and len(at) == 3
              and [a["n"] for a in at] == [1, 2, 3])
        check("ledger: every line has event and at; attempt lines carry the pinned keys",
              all("event" in l and "at" in l for l in ledger(root, qid))
              and all(set(("n", "id", "parent", "commit", "score", "status", "reason",
                           "seconds", "finding", "direction", "confidence")) <= set(a)
                      for a in at))
        setup_line = next(l for l in ledger(root, qid) if l["event"] == "setup")
        check("ledger (Q10): the setup line records the baseline spread as noise",
              setup_line.get("noise") == 0.0)
        check("rule 5: climb builds attempt 1 on base, then always on the best",
              len(at) == 3 and at[0]["parent"] == "base" and at[1]["parent"] == at[0]["id"]
              and at[2]["parent"] == at[1]["id"])
        check("rule 5: every valid attempt is kept with its score",
              [a["status"] for a in at] == ["kept"] * 3
              and [a["score"] for a in at] == [2.0, 3.0, 3.0])
        if len(at) != 3:
            check("run: the attempt checks need three attempts (got %d)" % len(at), False)
            return
        h1, h2, h3 = (v.get(a["id"]) for a in at)
        f1, f2, f3 = (finding(root, h.id) for h in (h1, h2, h3))
        check("nodes: each attempt is a hypothesis under the anchor with exactly one Finding",
              all(h.type == "idea" and h.parent == qid for h in (h1, h2, h3))
              and all(f.get("parent") == h.id for f, h in ((f1, h1), (f2, h2), (f3, h3))))
        check("findings: kept and better -> supports",
              f1.get("direction") == "supports" and f2.get("direction") == "supports")
        check("findings: deterministic scorer, a gain of 1 beats the near-zero min_gain -> strong",
              f1.get("confidence") == "strong" and f2.get("confidence") == "strong"
              and E.derive_state(v, h1.id)["state"] == "settled")
        check("findings: kept and not better -> against, moderate",
              f3.get("direction") == "against" and f3.get("confidence") == "moderate")
        check("findings: the ledger line names the attempt's Finding",
              [a["finding"] for a in at] == [f1.get("id"), f2.get("id"), f3.get("id")]
              and [a["direction"] for a in at] == ["supports", "supports", "against"])
        check("nodes: a hypothesis states its expectation before the Finding (no verdict field)",
              all(not h["fm"].get("verdict") for h in (h1, h2, h3)))
        check("nodes: builds_on is the parent node, none for base",
              not h1["fm"].get(E.BUILDS_ON_FIELD) and h2["fm"].get(E.BUILDS_ON_FIELD) == h1.id)
        check("nodes: the check is the objective against the parent's score (strict >)",
              "x > 1.0" in h1["body"] and "x > 2.0" in h2["body"])
        check("nodes: the title is the commit subject; empty subject is a no-claim title",
              h1.title == "raise the number by one" and h3.title == "Autopilot attempt 3 (no claim)")
        check("git: a committed attempt keeps its commit at refs/crux/auto/<anchor>/<n>",
              subprocess.check_output(["git", "-C", repo, "rev-parse",
                                       f"refs/crux/auto/{qid}/2"]).decode().strip()
              == at[1]["commit"])
        check("git: no worktree and no branch left behind",
              not os.listdir(os.path.join(root, "auto", qid, "work"))
              and subprocess.check_output(["git", "-C", repo, "branch"]).decode().count("\n") == 1)
        log = [json.loads(l) for l in lines(os.path.join(tmp, "stub_log"))]
        b = log[-1]["brief"]
        check("brief: objective, editable, guidance, parent and best score, last outcomes",
              "x" in b and "prog.txt" in b and "Try making the number bigger." in b
              and "3.0" in b and "kept" in b and "web" in b.lower() and "commit" in b.lower())
        sc = [l.split("|") for l in lines(os.path.join(tmp, "score_count"))]
        check("scorer: cwd is the worktree; CRUX_ATTEMPT is n and CRUX_WORKSPACE is set",
              [s[0] for s in sc[-3:]] == ["1", "2", "3"] and all(s[1] for s in sc[-3:]))

        stop2 = A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("run: a second run continues from the ledger",
              len(at) == 4 and at[3]["n"] == 4 and at[3]["parent"] == at[1]["id"]
              and sum(1 for l in ledger(root, qid) if l["event"] == "setup") == 1)

        st = A.status(root, qid)
        check("status: the pinned payload",
              set(("anchor", "mode", "address", "direction", "bar", "baseline", "best",
                   "attempts", "attempts_per_hour", "elapsed_hours", "budget_hours", "live",
                   "stop")) <= set(st)
              and st["best"] == {"id": at[3]["id"], "score": 4.0} and st["baseline"] == 1.0
              and len(st["attempts"]) == 4 and st["stop"]["reason"] == "max_attempts"
              and st["live"] is False and st["mode"] == "climb")
        check("status: every attempt shows its Finding (id, direction, confidence)",
              all(a.get("finding") and a.get("direction") in E.DIRECTIONS
                  and a.get("confidence") in E.CONFIDENCES for a in st["attempts"])
              and st.get("noise") == 0.0)
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "auto", "status",
                            qid, "--json"], cwd=root, capture_output=True, text=True)
        try:
            cj = json.loads(r.stdout)
        except ValueError:
            cj = {}
        r2 = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "validate"],
                            cwd=root, capture_output=True, text=True)
        check("findings: the run's vault validates (each attempt report is linked evidence)",
              r2.returncode == 0)
        check("status: `crux auto status --json` on the stub run shows the Findings",
              r.returncode == 0 and [a.get("finding") for a in cj.get("attempts", [])]
              == [a["finding"] for a in at])
        cp = A.cockpit(root)
        check("cockpit: one run per ledger, read only",
              cp["active"] is False and len(cp["runs"]) == 1 and cp["runs"][0]["anchor"] == qid)

    # explore with c_puct 1.0: the population is every kept attempt
    with tempfile.TemporaryDirectory() as tmp:
        # base 1 -> 2, then every child scores 1: the best (2) gathers visits until the
        # exploration term hands the sixth attempt to a non-best parent
        root, path, qid, repo = fixture(tmp, mode="explore", modes="up,up,down")
        A.run(root, path, max_attempts=6)
        at = attempts(root, qid)
        ids = [a["id"] for a in at]
        best_then = [None] + [max((b for b in at[:i]), key=lambda b: b["score"])["id"]
                              for i in range(1, len(at))]
        check("rule 5: explore picks parents among kept attempts, sometimes a non-best one",
              len(at) == 6 and all(a["parent"] in ["base"] + ids for a in at)
              and any(a["parent"] != best_then[i] for i, a in enumerate(at) if i > 0))

    # rule 1: a change outside editable discards the attempt
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,frozen,up")
        A.run(root, path, max_attempts=2)
        at = attempts(root, qid)
        check("rule 1: a frozen-path change is discarded and the run continues",
              at[0]["status"] == "discarded" and "frozen.txt" in at[0]["reason"]
              and at[1]["status"] == "kept")
        f0 = finding(root, at[0]["id"])
        check("rule 1: a discarded attempt is never scored; its Finding is no-answer-yet",
              at[0]["score"] is None and f0.get("direction") == E.NO_ANSWER)

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,empty,up")
        A.run(root, path, max_attempts=2)
        at = attempts(root, qid)
        check("empty commit: an attempt with no file change is discarded, never scored",
              at[0]["status"] == "discarded" and at[0]["score"] is None
              and at[0]["reason"] == "empty commit: no file changed")
        check("empty commit: it never becomes a parent or the best",
              at[1]["parent"] == "base" and at[1]["status"] == "kept"
              and A.status(root, qid)["best"]["id"] == at[1]["id"])

    # the base is the starting best: a kept attempt worse than the base never leads climb
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,down,up")
        A.run(root, path, max_attempts=1)
        best1 = A.status(root, qid)["best"]
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("baseline: an attempt worse than the base is kept but is not the best",
              at[0]["status"] == "kept" and at[0]["score"] == 0.0 and best1 is None)
        check("baseline: climb then builds on the base, not on the worse attempt",
              at[1]["parent"] == "base" and at[1]["score"] == 2.0
              and A.status(root, qid)["best"]["id"] == at[1]["id"])

    # min_gain: a gain of 1 per step is not more than 1.5, so nothing counts as better
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up", min_gain="1.5")
        A.run(root, path, max_attempts=3)
        at = attempts(root, qid)
        v = E.Vault(root)
        check("min_gain: a gain not above min_gain is kept but its Finding is against",
              [a["status"] for a in at] == ["kept"] * 3
              and finding(root, at[1]["id"]).get("direction") == "against"
              and "x > 2.5" in v.get(at[1]["id"])["body"])
        check("min_gain: best and climb's parent move only on a gain above min_gain",
              at[1]["parent"] == "base" and at[2]["parent"] == "base"
              and A.status(root, qid)["best"] is None)

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,mv,up", editable="prog.txt, src/")
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 1: moving a frozen file into an editable dir is discarded (no rename bypass)",
              at[0]["status"] == "discarded" and "frozen.txt" in at[0]["reason"]
              and "src/" not in at[0]["reason"])

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,ignore")
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 1: a gitignored file the worker leaves is cleaned before scoring",
              at[0]["status"] == "kept" and at[0]["score"] == 2.0)

    # rule 2: crash / no number / timeout are failed attempts; the run continues
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,crash,garbage,nokey,up")
        stop = A.run(root, path, max_attempts=4)
        at = attempts(root, qid)
        check("rule 2: a worker crash, a scorer with no JSON and a missing leaf are failed",
              [a["status"] for a in at] == ["failed", "failed", "failed", "kept"]
              and stop["reason"] == "max_attempts")
        fs = [finding(root, a["id"]) for a in at[:3]]
        check("rule 2: a failed attempt's Finding is no-answer-yet, weak",
              all(f.get("direction") == E.NO_ANSWER and f.get("confidence") == "weak"
                  for f in fs))
        ev = [f.get("evidence") or [] for f in fs]
        check("rule 2: a failed attempt's Finding links its worker log as evidence",
              all(len(e) == 1 and e[0].startswith(E.RESULTS_DIR + "/")
                  and os.path.isfile(os.path.join(root, e[0]))
                  and "[crux auto] worker exit" in open(os.path.join(root, e[0])).read()
                  for e in ev))
        check("rule 2: no-answer-yet Findings leave the hypothesis open",
              all(E.derive_state(E.Vault(root), a["id"])["state"] == "open" for a in at[:3]))
        check("rule 2: a failed attempt is never a parent", at[3]["parent"] == "base")

    # rule 3: rejected once, no retry; a scorer that cannot start gets one retry
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,bad,die")
        A.run(root, path, max_attempts=2)
        at = attempts(root, qid)
        calls = [l.split("|")[0] for l in lines(os.path.join(tmp, "score_count"))]
        check("rule 3: passed: false is rejected, scored once, no retry",
              at[0]["status"] == "rejected" and calls.count("1") == 1
              and "not a number" in at[0]["reason"])
        check("rule 3: a scorer that cannot run is a machine fault: one retry, then failed",
              at[1]["status"] == "failed" and calls.count("2") == 2)
        f0 = finding(root, at[0]["id"])
        check("rule 3: a rejected attempt's Finding is no-answer-yet with the log as evidence",
              f0.get("direction") == E.NO_ANSWER and len(f0.get("evidence") or []) == 1
              and "not a number" in (f0.get("why") or ""))

    # rule 4: one time limit per attempt
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,slow", attempt_minutes="0.05")
        t0 = time.monotonic()
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 4: a worker past attempt_minutes is a failed attempt, killed in time",
              at[0]["status"] == "failed" and "time" in at[0]["reason"]
              and at[0]["seconds"] < 10 and time.monotonic() - t0 < 25)

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,sleep", attempt_minutes="0.05")
        t0 = time.monotonic()
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 4: a slow scorer is killed at the attempt deadline; the attempt is failed",
              at[0]["status"] == "failed" and "scorer" in at[0]["reason"]
              and at[0]["seconds"] < 10 and time.monotonic() - t0 < 25)

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,rateslow,slow", attempt_minutes="0.1")
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 4: a rate-limit retry gets only what is left of the attempt's time",
              len(at) == 1 and at[0]["status"] == "failed" and at[0]["seconds"] < 8.5)

    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, scorer="hang.py", attempt_minutes="0.05")
        t0 = time.monotonic()
        stop = A.run(root, path)
        led = ledger(root, qid)
        check("rule 6: a hung base scorer fails setup cleanly, with a ledger line",
              stop["reason"] == "setup" and time.monotonic() - t0 < 20
              and led[0]["event"] == "setup" and led[0]["ok"] is False
              and any("time" in p for p in led[0]["problems"]))

    # rule 7: budget checked only between attempts; a rate limit waits and retries
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,nap", budget_hours="0.0001")
        stop = A.run(root, path)
        at = attempts(root, qid)
        check("rule 7: the attempt in flight finishes; the budget stops the run after it",
              len(at) == 1 and at[0]["status"] == "kept" and stop["reason"] == "budget")
    with tempfile.TemporaryDirectory() as tmp:
        root, path, qid, repo = fixture(tmp, modes="up,rate,rate,up")
        A.run(root, path, max_attempts=1)
        at = attempts(root, qid)
        check("rule 7: a rate-limited worker waits and retries; it is never a failure",
              len(at) == 1 and at[0]["status"] == "kept"
              and int(open(os.path.join(tmp, "stub_count")).read()) == 4)

    # an old spec-05 vault still loads
    with tempfile.TemporaryDirectory() as tmp:
        root = os.path.join(tmp, "vault")
        E.cmd_init("Old Auto", root)
        qid, _ = E.cmd_ask(root, "anchor")
        h1, _, _ = E.cmd_hypothesize(root, "Autopilot attempt h1 left no usable claim (worker).",
                                     parent=qid, verifiables=["eval.loss < 0.85"],
                                     require_expect=False)
        h2, _, _ = E.cmd_hypothesize(root, "an attempt", parent=qid,
                                     verifiables=["eval.loss < 0.85"], builds_on=h1,
                                     require_expect=False)
        _write(os.path.join(root, "auto", qid, "plan.md"),
               "---\ntype: flight-plan\nanchor: " + qid + "\nisland_cap: 3\nbaseline: h1\n---\n")
        _write(os.path.join(root, "auto", qid, "state.json"), "{}")
        _write(os.path.join(root, "auto", qid, "ledger.jsonl"),
               json.dumps({"event": "closed", "attempt": h2, "verdict": "refuted",
                           "at": "2026-09-23T01:02:03"}) + "\n")
        ok = len(E.Vault(root).nodes) >= 4
        r = subprocess.run([sys.executable, os.path.join(HERE, "crux.py"), "status"],
                           cwd=root, capture_output=True, text=True)
        cp = A.cockpit(root)
        check("old vault: spec-05 autopilot nodes still load (Vault and crux status)",
              ok and r.returncode == 0 and h2 in r.stdout)
        check("old vault: the cockpit payload reads an old ledger without crashing",
              len(cp["runs"]) == 1 and cp["runs"][0]["attempts"] == [] and not cp["active"])


def _bench_plan_tests(check, A):
    """Every examples/autopilot/*/plan.md, with run-fir.sh's placeholders filled, loads and
    uses at most 10 frontmatter rows (repo and base count as one). Skipped outside a checkout."""
    ex = os.path.join(HERE, "..", "..", "..", "examples", "autopilot")
    if not os.path.isdir(ex):
        return
    names = sorted(d for d in os.listdir(ex) if os.path.isfile(os.path.join(ex, d, "plan.md")))
    bad = []
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            with open(os.path.join(ex, name, "plan.md"), encoding="utf-8") as f:
                text = f.read()
            text = (text.replace("@BENCH@", "/b/" + name).replace("@ANCHOR@", "q1")
                    .replace("@REPO@", "/r/" + name))
            path = os.path.join(tmp, name + ".md")
            _write(path, text)
            try:
                A.load_plan(path)
                head, _ = A._split_doc(text)
                keys = [l.partition(":")[0].strip() for l in head
                        if l.strip() and not l.lstrip().startswith("#")]
                if len(set(keys) - {"base"}) > 10 or "@" in text:
                    bad.append(name + ": too many rows or a placeholder left")
            except E.CruxError as e:
                bad.append(f"{name}: {e}")
    check(f"bench plans: every examples/autopilot plan loads with <= 10 rows ({len(names)} found"
          + (f"; {bad}" if bad else "") + ")", len(names) == 4 and not bad)


def main():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)
        print(("  ok   " if cond else "  FAIL ") + name)
    run_all(check)
    print(f"\n  PASSED {len(passed)} / {len(passed) + len(failed)}")
    if failed:
        print("  FAILED:\n" + "\n".join("    " + f for f in failed))
        sys.exit(1)
    print("  ALL GREEN")


if __name__ == "__main__":
    main()
