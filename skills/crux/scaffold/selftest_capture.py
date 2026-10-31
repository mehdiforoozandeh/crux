#!/usr/bin/env python3
"""Self-test for capture plumbing (spec 19, chunk C3): vault discovery one level down, the
SessionStart hook (core injection + catch-up sweep), the per-transcript sweep mark, the hard
token cap, the recursion guard, the pending list, `crux wrap --json`, and install.sh.

    python3 selftest_capture.py        # standalone: prints PASSED a / b, exits 1 on any failure

`run_all(check)` takes selftest.py's `check(name, cond)`. Every test runs in a temp dir with
HOME pointed into it and a STUB `claude` on PATH: no test ever launches a real model run."""
import os, sys, json, shutil, subprocess, tempfile, time, stat
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E
import sweep as S

CLI = os.path.join(HERE, "crux.py")
REPO = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
BASE_PATH = "/usr/bin:/bin"


# ------------------------------------------------------------------------------- helpers
def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _write(p, text, mode="w"):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, mode, encoding="utf-8") as f:
        f.write(text)


def _stub(tmp):
    """A fake `claude` that logs one JSON line per launch: its argv and CRUX_SWEEP."""
    d = os.path.join(tmp, "stubbin")
    log = os.path.join(tmp, "stub.log")
    os.makedirs(d, exist_ok=True)
    p = os.path.join(d, "claude")
    _write(p, "#!%s\nimport sys, os, json\n"
              "with open(%r, 'a') as f:\n"
              "    f.write(json.dumps({'argv': sys.argv[1:], 'sweep': os.environ.get('CRUX_SWEEP'),"
              " 'cwd': os.getcwd()}) + '\\n')\n" % (sys.executable, log))
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    return d, log


def _launches(log, expect=None, wait=4.0):
    """The stub's launch records. The run is detached, so poll until `expect` lines exist
    (or, with expect=None, wait a short fixed time so a stray launch would have landed)."""
    deadline = time.time() + (wait if expect else 0.8)
    while True:
        lines = _read(log).splitlines() if os.path.isfile(log) else []
        if expect is not None and len(lines) >= expect:
            break
        if time.time() >= deadline:
            break
        time.sleep(0.05)
    return [json.loads(x) for x in lines]


def _env(home, path, **kw):
    env = dict(os.environ, HOME=home, PATH=path, CRUX_NO_UPDATE_CHECK="1")
    env.pop("CRUX_SWEEP", None)
    env.update(kw)
    return env


def _cli(cwd, argv, env, stdin=None):
    return subprocess.run([sys.executable, CLI] + list(argv), cwd=cwd, env=env, input=stdin,
                          capture_output=True, text=True, encoding="utf-8")


def _hook(cwd, payload, env):
    raw = payload if isinstance(payload, str) else json.dumps(payload)
    return _cli(cwd, ["hook", "session-start"], env, stdin=raw)


def _rec(kind, content, session="s-old", **extra):
    r = {"type": kind, "sessionId": session, "isSidechain": False,
         "message": {"role": kind, "content": content}}
    r.update(extra)
    return json.dumps(r) + "\n"


def _turns(pi, agent, session="s-old"):
    return _rec("user", pi, session) + _rec("assistant", [{"type": "text", "text": agent}], session)


def _vault(tmp, name):
    root = os.path.join(tmp, name)
    E.cmd_init("Capture test", root)
    return root


def _marks(vault):
    p = os.path.join(vault, S.STATE_DIR, S.MARKS_FILE)
    return json.loads(_read(p)) if os.path.isfile(p) else {}


def _tool_list(val):
    """Split a comma list, keeping commas inside parentheses (a path may hold anything)."""
    out, depth, cur = [], 0, ""
    for ch in val:
        if ch == "," and depth == 0:
            out.append(cur); cur = ""
            continue
        depth += (ch == "(") - (ch == ")")
        cur += ch
    return out + [cur]


def _restricted(argv):
    """True when a capture run can use crux and Read and nothing else."""
    def val(flag):
        return argv[argv.index(flag) + 1] if flag in argv and argv.index(flag) + 1 < len(argv) else None
    allowed = val("--allowedTools")
    ok = {"Bash(crux:*)", "Bash(python3 %s:*)" % S.CRUX_PY, "Read"}
    return (allowed is not None and all(t in ok for t in _tool_list(allowed))
            and val("--tools") == "Bash,Read" and val("--permission-mode") == "dontAsk")


def _widen(argv):
    argv = list(argv)
    if "--allowedTools" in argv:
        i = argv.index("--allowedTools") + 1
        argv[i] = argv[i] + ",Edit"
    return argv


# ------------------------------------------------------------------------------- sections
def _discovery_tests(check, tmp):
    base = os.path.join(tmp, "disc")
    repo = os.path.join(base, "repo")
    vault = _vault(repo, "cruxvault")
    deep = os.path.join(vault, "sub", "deeper")
    os.makedirs(deep)
    bare = os.path.join(base, "bare")
    os.makedirs(bare)
    check("capture: a vault at the cwd is found", S.find_vault_near(vault) == vault)
    check("capture: a vault at an ancestor is found", S.find_vault_near(deep) == vault)
    check("capture: a vault one level down (./cruxvault) is found",
          S.find_vault_near(repo) == vault)
    check("capture: no vault anywhere near → None, not an error", S.find_vault_near(bare) is None)
    check("capture: the projects-folder slug matches Claude Code's",
          S.project_slug("/Users/a/x.y@z_w") == "-Users-a-x-y-z-w")


def _hook_core_tests(check, tmp):
    home = os.path.join(tmp, "hhome")
    stubdir, log = _stub(os.path.join(tmp, "hstub"))
    env = _env(home, stubdir + ":" + BASE_PATH)
    repo = os.path.join(tmp, "hrepo")
    vault = _vault(repo, "cruxvault")
    core = _read(S.CORE_PATH)
    for label, cwd in (("at the cwd", vault), ("one level down", repo),
                       ("at an ancestor", os.path.join(vault, "results"))):
        os.makedirs(cwd, exist_ok=True)
        r = _hook(cwd, {"hook_event_name": "SessionStart", "source": "resume", "cwd": cwd}, env)
        try:
            out = json.loads(r.stdout)["hookSpecificOutput"]
        except Exception:
            out = {}
        check(f"capture: hook with a vault {label} injects the core as additionalContext",
              r.returncode == 0 and out.get("hookEventName") == "SessionStart"
              and out.get("additionalContext") == core)
    bare = os.path.join(tmp, "hbare")
    os.makedirs(bare)
    r = _hook(bare, {"hook_event_name": "SessionStart", "source": "startup", "cwd": bare}, env)
    check("capture: hook with no vault prints nothing and exits 0",
          r.returncode == 0 and r.stdout.strip() == "" and r.stderr.strip() == "")
    r = _hook(bare, "this is {not json", env)
    check("capture: hook on garbage stdin exits 0, silent",
          r.returncode == 0 and r.stdout.strip() == "" and r.stderr.strip() == "")
    # an internal error in the sweep (the state folder is a FILE) must not break the session
    v2 = _vault(tmp, "hbroken")
    _write(os.path.join(v2, S.STATE_DIR), "not a folder")
    proj = os.path.join(home, ".claude", "projects", S.project_slug(v2))
    _write(os.path.join(proj, "old.jsonl"), _turns("does it work", "it might"))
    r = _hook(v2, {"source": "startup", "cwd": v2,
                   "transcript_path": os.path.join(proj, "cur.jsonl")}, env)
    check("capture: hook exits 0 and silent on stderr on an internal sweep error",
          r.returncode == 0 and r.stderr.strip() == "")
    check("capture: ... and still injects the core",
          '"additionalContext"' in r.stdout)


def _sweep_tests(check, tmp):
    home = os.path.join(tmp, "shome")
    stubdir, log = _stub(os.path.join(tmp, "sstub"))
    env = _env(home, stubdir + ":" + BASE_PATH)
    repo = os.path.join(tmp, "srepo")
    vault = _vault(repo, "cruxvault")
    proj = os.path.join(home, ".claude", "projects", S.project_slug(repo))
    old = os.path.join(proj, "s-old.jsonl")
    cur = os.path.join(proj, "s-cur.jsonl")
    _write(old, _turns("OLD-HISTORY-TEXT from before install", "noted"))
    _write(cur, _turns("hello", "CURRENT-SESSION-TEXT", "s-cur"))

    def start(source="startup", extra_env=None, transcript=cur):
        e = dict(env, **(extra_env or {}))
        return _hook(repo, {"hook_event_name": "SessionStart", "source": source, "cwd": repo,
                            "session_id": os.path.basename(transcript)[:-6],
                            "transcript_path": transcript}, e)

    def run_text(run):
        cands = [w for w in (run or {}).get("argv", []) if w.endswith(".txt") and os.path.isfile(w)]
        if not cands:
            cands = [w for w in " ".join((run or {}).get("argv", [])).split()
                     if w.endswith(".txt") and os.path.isfile(w)]
        return _read(cands[0]) if cands else ""

    # ---- first sight (cheap first run): history from before install is baselined, not swept.
    r = start()
    m = _marks(vault)
    check("capture: first sight of an old transcript starts no run",
          r.returncode == 0 and len(_launches(log)) == 0)
    check("capture: ... and sets its mark to the transcript's current end",
          m.get("marks", {}).get(old) == os.path.getsize(old))
    check("capture: the current session is registered from byte 0",
          m.get("marks", {}).get(cur) == 0)

    _write(old, _turns("Can a smaller batch improve accuracy?", "A smaller batch may help."),
           mode="a")
    r = start()
    runs = _launches(log, expect=1)
    m = _marks(vault)
    check("capture: new transcript text starts exactly one capture run",
          r.returncode == 0 and len(runs) == 1)
    check("capture: the sweep mark stores the per-transcript byte offset",
          m.get("marks", {}).get(old) == os.path.getsize(old))
    text = run_text(runs[0] if runs else None)
    check("capture: the run's input carries only the new transcript text",
          "smaller batch" in text and "OLD-HISTORY-TEXT" not in text)
    check("capture: the current session's own transcript is not swept",
          "CURRENT-SESSION-TEXT" not in text and m.get("marks", {}).get(cur) == 0)
    argv = runs[0]["argv"] if runs else []
    check("capture: the run is `claude -p` on a small model with a turn cap",
          "-p" in argv and "--model" in argv and "--max-turns" in argv)
    check("capture: the run is limited to crux commands", _restricted(argv))
    check("capture: ... and the predicate rejects an argv with an extra Edit entry",
          not _restricted(_widen(argv)))
    check("capture: the run carries CRUX_SWEEP=1", runs and runs[0]["sweep"] == "1")
    check("capture: the run is handed the capture brief",
          any(S.CAPTURE_BRIEF in a for a in argv))
    check("capture: the state folder is git-ignored",
          _read(os.path.join(vault, S.STATE_DIR, ".gitignore")).strip() == "*")

    r = start()
    check("capture: a second session start with no new bytes starts nothing",
          r.returncode == 0 and len(_launches(log)) == 1)

    _write(old, _turns("And a larger one?", "Larger hurt in our last run."), mode="a")
    start(source="resume")
    start(source="compact")
    check("capture: resume and compact never sweep", len(_launches(log)) == 1)
    start()
    check("capture: new bytes start exactly one more run", len(_launches(log, expect=2)) == 2)
    cur2 = os.path.join(proj, "s-cur2.jsonl")
    start(transcript=cur2)
    runs = _launches(log, expect=3)
    check("capture: a session started since install is swept from byte 0 at the next start",
          len(runs) == 3 and "CURRENT-SESSION-TEXT" in run_text(runs[-1]))

    # ---- recursion guard (R3): the capture run's own SessionStart.
    capt = os.path.join(proj, "s-capt.jsonl")
    _write(capt, _turns("SWEEP-PROMPT", "CAPTURE-RUN-TEXT", "s-capt"))
    _write(old, _turns("A third question?", "Maybe."), mode="a")
    r = start(extra_env={"CRUX_SWEEP": "1"}, transcript=capt)
    check("capture: with CRUX_SWEEP=1 the hook starts no sweep",
          r.returncode == 0 and len(_launches(log)) == 3)
    check("capture: ... and emits no core into the capture run", r.stdout.strip() == "")
    check("capture: ... and lists that transcript as a capture run",
          capt in _marks(vault).get("capture_runs", []))
    start()
    runs = _launches(log, expect=4)
    argv = runs[-1]["argv"] if len(runs) == 4 else []
    cands = [w for w in " ".join(argv).split() if w.endswith(".txt") and os.path.isfile(w)]
    text = _read(cands[0]) if cands else ""
    check("capture: a capture run's transcript is never swept",
          "A third question" in text and "CAPTURE-RUN-TEXT" not in text)
    sid = argv[argv.index("--session-id") + 1] if "--session-id" in argv else None
    check("capture: the run's own session id is pre-listed as a capture run",
          sid and os.path.join(proj, sid + ".jsonl") in _marks(vault).get("capture_runs", []))

    # ---- hard token cap: the input is cut, the newest text kept.
    big = "x" * (S.CHAR_CAP * 2)
    _write(old, _turns("OLDEST-MARK " + big, "ok") + _turns("NEWEST-MARK", "ok"), mode="a")
    start()
    runs = _launches(log, expect=5)
    argv = runs[-1]["argv"] if len(runs) == 5 else []
    cands = [w for w in " ".join(argv).split() if w.endswith(".txt") and os.path.isfile(w)]
    text = _read(cands[0]) if cands else ""
    check("capture: the text handed to the capture run is truncated to the hard cap",
          text and len(text) <= S.CHAR_CAP and S.CHAR_CAP == S.TOKEN_CAP * S.CHARS_PER_TOKEN)
    check("capture: ... keeping the newest text", "NEWEST-MARK" in text)

    # ---- `crux sweep` by hand reports, and refuses under CRUX_SWEEP=1.
    _write(old, _turns("A fourth one?", "Yes."), mode="a")
    r = _cli(repo, ["sweep", "--json"], dict(env, CRUX_SWEEP="1"))
    check("capture: `crux sweep` under CRUX_SWEEP=1 launches nothing",
          r.returncode == 0 and json.loads(r.stdout or "{}").get("launched") is False)
    r = _cli(repo, ["sweep", "--json"], env)
    out = json.loads(r.stdout or "{}")
    check("capture: `crux sweep --json` launches one run and says so",
          out.get("launched") is True and len(_launches(log, expect=6)) == 6)

    # ---- no claude binary: silent, nothing launched, marks not advanced.
    _write(old, _turns("A fifth one?", "Yes."), mode="a")
    before = _marks(vault)["marks"][old]
    r = start(extra_env={"PATH": BASE_PATH})
    check("capture: a missing claude binary is silent",
          r.returncode == 0 and r.stderr.strip() == "" and len(_launches(log)) == 6)
    check("capture: ... and the mark is not advanced", _marks(vault)["marks"][old] == before)

    r = _cli(vault, ["validate", "--json"], env)
    check("capture: the state folder does not upset validate",
          "\\.crux" not in r.stdout and ".crux/" not in r.stdout)


def _pending_tests(check, tmp):
    home = os.path.join(tmp, "phome")
    env = _env(home, BASE_PATH)
    vault = _vault(tmp, "pvault")
    r = _cli(vault, ["pending", "--json"], env)
    check("capture: an empty pending list is []",
          r.returncode == 0 and json.loads(r.stdout).get("pending") == [])
    r = _cli(vault, ["pending", "add", "--kind", "hypothesis", "--parent", "q1",
                     "--text", "batch size drives the gain", "--source", "sweep", "--json"], env)
    added = json.loads(r.stdout or "{}")
    check("capture: `pending add` appends a record with an id", r.returncode == 0 and added.get("id"))
    # C2's migration writes raw JSON lines with no id; a malformed line must be skipped.
    _write(os.path.join(vault, S.STATE_DIR, S.PENDING_FILE),
           json.dumps({"kind": "finding", "parent": "h2", "text": "unaccepted task conclusion",
                       "source": "migrate"}) + "\n{broken\n" + json.dumps({"kind": "x"}) + "\n",
           mode="a")
    items = json.loads(_cli(vault, ["pending", "--json"], env).stdout)["pending"]
    check("capture: records with {kind, parent, text, source} are accepted, bad lines skipped",
          [i["text"] for i in items] == ["batch size drives the gain", "unaccepted task conclusion"])
    check("capture: every listed record has a stable id",
          all(i.get("id") for i in items)
          and items == json.loads(_cli(vault, ["pending", "--json"], env).stdout)["pending"])
    r = _cli(vault, ["pending", "clear", items[1]["id"], "--json"], env)
    left = json.loads(_cli(vault, ["pending", "--json"], env).stdout)["pending"]
    check("capture: `pending clear <id>` removes exactly that record",
          r.returncode == 0 and [i["id"] for i in left] == [items[0]["id"]])

    # ---- a rewrite racing appends must not drop a line: both hold the same lock.
    import threading
    v3 = _vault(tmp, "prace")
    keep = S.pending_add(v3, "question", None, "kept", "sweep")["id"]
    added = []

    def adder():
        for i in range(150):
            added.append(S.pending_add(v3, "question", None, "race %d" % i, "sweep")["id"])

    def clearer():
        for _ in range(150):
            S.pending_clear(v3, ["p-not-there"])
    ts = [threading.Thread(target=adder), threading.Thread(target=clearer)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    got = {i["id"] for i in S.pending_list(v3)}
    check("capture: concurrent appends survive a racing pending rewrite",
          got == set(added) | {keep} and len(added) == 150)


def _wrap_tests(check, tmp):
    home = os.path.join(tmp, "whome")
    env = _env(home, BASE_PATH)
    repo = os.path.join(tmp, "wrepo")
    vault = _vault(repo, "cruxvault")
    proj = os.path.join(home, ".claude", "projects", S.project_slug(repo))
    sess = os.path.join(proj, "s-now.jsonl")

    def call(tid, cmd):
        return _rec("assistant", [{"type": "tool_use", "id": tid, "name": "Bash",
                                   "input": {"command": cmd}}], "s-now")

    def result(tid, text, err=False):
        return _rec("user", [{"type": "tool_result", "tool_use_id": tid, "content": text,
                              "is_error": err}], "s-now")

    body = (_turns("Does batch size matter?", "Let me note that.", "s-now")
            + call("a1", 'crux ask "Does batch size matter?" --json')
            + result("a1", '{"id": "q2", "file": "q2_batch.md"}')
            + call("a2", 'cd cruxvault && ./crux hypothesize "Small batches help" -p q2 '
                         '--expect "higher accuracy"')
            + result("a2", "✓ h1  (h1_small.md)")
            + call("a3", "ls -la")
            + result("a3", "total 0")
            + call("a4", 'crux finding h9 -c strong -w "x"')
            + result("a4", "crux: no such node h9", err=True)
            + call("a5", "crux status")
            + result("a5", "tree"))
    _write(sess, body)
    S.pending_add(vault, "question", "root", "is the gain real", "sweep")
    r = _cli(repo, ["wrap", "--json", "--transcript", sess], env)
    out = json.loads(r.stdout or "{}")
    recs = out.get("records", [])
    check("capture: wrap --json lists the records this session wrote",
          r.returncode == 0 and [x.get("id") for x in recs] == ["q2", "h1"])
    check("capture: ... naming the verb of each",
          [x.get("verb") for x in recs] == ["ask", "hypothesize"])
    check("capture: ... skipping failed calls and read-only verbs",
          all(x.get("id") != "h9" for x in recs) and len(recs) == 2)
    check("capture: ... plus the pending list",
          [p["text"] for p in out.get("pending", [])] == ["is the gain real"])
    check("capture: ... plus this session's new text for the capture agent",
          "Does batch size matter?" in out.get("text", ""))
    check("capture: wrap advances this session's sweep mark",
          _marks(vault).get("marks", {}).get(sess) == os.path.getsize(sess))
    # default transcript: the newest one in this cwd's projects folder
    r = _cli(repo, ["wrap", "--json"], env)
    out = json.loads(r.stdout or "{}")
    check("capture: wrap finds this session's transcript by itself",
          out.get("transcript") == sess and [x.get("id") for x in out.get("records", [])]
          == ["q2", "h1"])


def _capture_cwd_tests(check, tmp):
    """The capture run, launched exactly as the hook launches it, must reach the vault when
    the vault sits one level down (`./cruxvault`), not only when it is the cwd."""
    home = os.path.join(tmp, "chome")
    d = os.path.join(tmp, "cstub", "stubbin")
    log = os.path.join(tmp, "cstub", "run.log")
    os.makedirs(d)
    p = os.path.join(d, "claude")
    # This stub does what the brief tells the capture agent: run a crux write verb, as given.
    _write(p, "#!%s\nimport sys, os, json, subprocess\n"
              "r = subprocess.run([sys.executable, %r, 'ask', 'Does the stub reach the vault?',"
              " '--json'], capture_output=True, text=True)\n"
              "with open(%r, 'a') as f:\n"
              "    f.write(json.dumps({'rc': r.returncode, 'out': r.stdout, 'err': r.stderr,"
              " 'cwd': os.getcwd()}) + '\\n')\n" % (sys.executable, CLI, log))
    os.chmod(p, os.stat(p).st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
    env = _env(home, d + ":" + BASE_PATH)
    repo = os.path.join(tmp, "crepo")
    vault = _vault(repo, "cruxvault")
    proj = os.path.join(home, ".claude", "projects", S.project_slug(repo))
    old, cur = os.path.join(proj, "s-old.jsonl"), os.path.join(proj, "s-cur.jsonl")
    _write(old, _turns("old", "old"))
    _write(cur, _turns("hi", "hi", "s-cur"))
    pay = {"hook_event_name": "SessionStart", "source": "startup", "cwd": repo,
           "session_id": "s-cur", "transcript_path": cur}
    _hook(repo, pay, env)                        # first sight: baselines s-old
    _write(old, _turns("Is the gain real?", "Maybe."), mode="a")
    r = _hook(repo, pay, env)
    runs = _launches(log, expect=1, wait=10.0)
    ok = bool(runs) and runs[0]["rc"] == 0
    check("capture: a capture run launched from the repo root runs a crux verb against "
          "./cruxvault", r.returncode == 0 and ok)
    titles = [E.Vault(vault).get(i)["fm"].get("title") or "" for i in ("q1",)
              if ok and os.path.isfile(os.path.join(vault, E.VAULT_MARKER))]
    check("capture: ... and the question lands in that vault",
          ok and any("stub reach" in t for t in titles))
    rw = _cli(repo, ["wrap", "--json"], _env(home, BASE_PATH))
    check("capture: `crux wrap --json` from the repo root finds ./cruxvault",
          rw.returncode == 0 and json.loads(rw.stdout or "{}").get("vault") == vault)


def _marks_lock_tests(check, tmp):
    """register_session's read-modify-write holds the state lock: N concurrent session starts
    keep all N marks."""
    vault = _vault(tmp, "mlock")
    n = 12
    code = ("import sys; sys.path.insert(0, %r); import sweep as S\n"
            "for i in range(15):\n"
            "    S.register_session(%r, %r %% (int(sys.argv[1]), i), 'startup')\n"
            % (HERE, vault, os.path.join(tmp, "mlock-t%d-%d.jsonl")))
    ps = [subprocess.Popen([sys.executable, "-c", code, str(k)]) for k in range(n)]
    rcs = [x.wait() for x in ps]
    got = set(_marks(vault).get("marks", {}))
    want = {os.path.join(tmp, "mlock-t%d-%d.jsonl" % (k, i)) for k in range(n) for i in range(15)}
    check("capture: %d processes registering sessions at once lose no mark" % n,
          all(c == 0 for c in rcs) and got == want)


def _install_tests(check, tmp):
    sp = os.path.join(tmp, "isettings.json")
    _write(sp, json.dumps({"model": "opus", "hooks": {
        "PreToolUse": [{"matcher": "Write"}],
        "SessionStart": [{"hooks": [{"type": "command", "command": "other-tool start"}]}]}}))
    S.install_session_hook(sp)
    state = S.install_session_hook(sp)
    cfg = json.loads(_read(sp))
    ss = cfg["hooks"]["SessionStart"]
    ours = [h for g in ss for h in g.get("hooks", []) if "hook session-start" in h.get("command", "")]
    check("capture: the SessionStart hook installs idempotently", len(ours) == 1 and state == "present")
    check("capture: ... and keeps unrelated keys and hooks",
          cfg.get("model") == "opus" and cfg["hooks"]["PreToolUse"] == [{"matcher": "Write"}]
          and any("other-tool" in h.get("command", "") for g in ss for h in g.get("hooks", [])))
    check("capture: the hook command is this engine's crux.py",
          ours and ours[0]["command"] == S.session_hook_command())

    # ---- the real install.sh, into scratch dirs, twice.
    sk, ag, home = (os.path.join(tmp, x) for x in ("isk", "iag", "ihome"))
    os.makedirs(ag)
    _write(os.path.join(home, ".claude", "settings.json"),
           json.dumps({"theme": "dark", "hooks": {"Stop": [{"hooks": []}]}}))
    os.symlink(os.path.join(tmp, "gone", "AGENT.md"), os.path.join(ag, "crux-removed.md"))
    os.symlink(os.path.join(tmp, "gone", "x.md"), os.path.join(ag, "other-agent.md"))
    _write(os.path.join(ag, "crux-mine.md"), "a real file")
    env = dict(os.environ, SKILLS_DIR=sk, AGENTS_DIR=ag, HOME=home, CRUX_NO_UPDATE_CHECK="1")
    rs = [subprocess.run(["bash", os.path.join(REPO, "install.sh")], env=env,
                         capture_output=True, text=True) for _ in range(2)]
    cfg = json.loads(_read(os.path.join(home, ".claude", "settings.json")))
    ss = cfg.get("hooks", {}).get("SessionStart", [])
    check("capture: install.sh twice → exactly one SessionStart entry",
          all(r.returncode == 0 for r in rs) and len(ss) == 1)
    check("capture: ... and keeps the unrelated settings keys",
          cfg.get("theme") == "dark" and cfg["hooks"].get("Stop") == [{"hooks": []}]
          and cfg["hooks"].get("PostToolUse"))
    check("capture: install.sh removes a dangling crux-*.md agent link",
          not os.path.lexists(os.path.join(ag, "crux-removed.md")))
    check("capture: ... but leaves other links and real files alone",
          os.path.lexists(os.path.join(ag, "other-agent.md"))
          and os.path.isfile(os.path.join(ag, "crux-mine.md")))

    # ---- evolve-crux's own agents (crux-tests builds crux, not research: spec 19 decision 9)
    #      are linked flat beside the roster. A scratch copy of the repo carries a stub, so
    #      the assert holds whether or not this checkout ships the file yet.
    def scratch_repo(name, with_agents):
        r = os.path.join(tmp, name)
        os.makedirs(os.path.join(r, "skills", "evolve-crux"))
        shutil.copy(os.path.join(REPO, "install.sh"), r)
        os.symlink(os.path.join(REPO, "skills", "crux"), os.path.join(r, "skills", "crux"))
        _write(os.path.join(r, "skills", "evolve-crux", "SKILL.md"), "stub\n")
        if with_agents:
            _write(os.path.join(r, "skills", "evolve-crux", "agents", "crux-tests.md"), "stub\n")
        return r
    for name, with_agents in (("irepo", True), ("irepo_bare", False)):
        r = scratch_repo(name, with_agents)
        sk2, ag2, home2 = (os.path.join(tmp, name + x) for x in ("_sk", "_ag", "_home"))
        env2 = dict(env, SKILLS_DIR=sk2, AGENTS_DIR=ag2, HOME=home2)
        rs2 = [subprocess.run(["bash", os.path.join(r, "install.sh")], env=env2,
                              capture_output=True, text=True) for _ in range(2)]
        link = os.path.join(ag2, "crux-tests.md")
        if with_agents:
            check("capture: install.sh links evolve-crux's crux-tests.md, idempotently on a "
                  "second run",
                  all(x.returncode == 0 for x in rs2) and os.path.islink(link)
                  and os.path.realpath(link) == os.path.realpath(
                      os.path.join(r, "skills", "evolve-crux", "agents", "crux-tests.md"))
                  and "crux-tests" not in rs2[1].stderr)
        else:
            check("capture: ... and is a no-op when evolve-crux ships no agents folder",
                  all(x.returncode == 0 for x in rs2) and not os.path.lexists(link))


def run_all(check):
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="crux_capture_"))
    try:
        for section in (_discovery_tests, _hook_core_tests, _sweep_tests, _pending_tests,
                        _wrap_tests, _capture_cwd_tests, _marks_lock_tests, _install_tests):
            try:
                section(check, tmp)
            except Exception as e:      # an unexpected result is a FAIL line, never a traceback
                check(f"capture: {section.__name__} crashed: {type(e).__name__}: {e}", False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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
