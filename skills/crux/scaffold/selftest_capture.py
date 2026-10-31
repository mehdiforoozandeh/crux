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
    _write(old, _turns("Can a smaller batch improve accuracy?", "A smaller batch may help."))
    _write(cur, _turns("hello", "CURRENT-SESSION-TEXT", "s-cur"))

    def start(source="startup", extra_env=None, transcript=cur):
        e = dict(env, **(extra_env or {}))
        return _hook(repo, {"hook_event_name": "SessionStart", "source": source, "cwd": repo,
                            "session_id": os.path.basename(transcript)[:-6],
                            "transcript_path": transcript}, e)

    r = start()
    runs = _launches(log, expect=1)
    m = _marks(vault)
    check("capture: new transcript text starts exactly one capture run",
          r.returncode == 0 and len(runs) == 1)
    check("capture: the sweep mark stores the per-transcript byte offset",
          m.get("marks", {}).get(old) == os.path.getsize(old))
    check("capture: the current session's own transcript is not swept",
          cur not in m.get("marks", {}))
    inp = [a for a in (runs[0]["argv"] if runs else []) if S.STATE_DIR in a and "input" in a]
    text = _read(inp[0]) if inp and os.path.isfile(inp[0]) else ""
    if not text and runs:
        joined = " ".join(runs[0]["argv"])
        cands = [w for w in joined.split() if w.endswith(".txt") and os.path.isfile(w)]
        text = _read(cands[0]) if cands else ""
    check("capture: the run's input carries the new transcript text",
          "smaller batch" in text and "CURRENT-SESSION-TEXT" not in text)
    argv = runs[0]["argv"] if runs else []
    check("capture: the run is `claude -p` on a small model with a turn cap",
          "-p" in argv and "--model" in argv and "--max-turns" in argv)
    check("capture: the run is limited to crux commands",
          "--allowedTools" in argv
          and all("crux" in t or t == "Read"
                  for t in argv[argv.index("--allowedTools") + 1].split()))
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

    # ---- recursion guard (R3): the capture run's own SessionStart.
    capt = os.path.join(proj, "s-capt.jsonl")
    _write(capt, _turns("SWEEP-PROMPT", "CAPTURE-RUN-TEXT", "s-capt"))
    _write(old, _turns("A third question?", "Maybe."), mode="a")
    r = start(extra_env={"CRUX_SWEEP": "1"}, transcript=capt)
    check("capture: with CRUX_SWEEP=1 the hook starts no sweep",
          r.returncode == 0 and len(_launches(log)) == 2)
    check("capture: ... and emits no core into the capture run", r.stdout.strip() == "")
    check("capture: ... and lists that transcript as a capture run",
          capt in _marks(vault).get("capture_runs", []))
    start()
    runs = _launches(log, expect=3)
    argv = runs[-1]["argv"] if len(runs) == 3 else []
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
    runs = _launches(log, expect=4)
    argv = runs[-1]["argv"] if len(runs) == 4 else []
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
          out.get("launched") is True and len(_launches(log, expect=5)) == 5)

    # ---- no claude binary: silent, nothing launched, marks not advanced.
    _write(old, _turns("A fifth one?", "Yes."), mode="a")
    before = _marks(vault)["marks"][old]
    r = start(extra_env={"PATH": BASE_PATH})
    check("capture: a missing claude binary is silent",
          r.returncode == 0 and r.stderr.strip() == "" and len(_launches(log)) == 5)
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


def run_all(check):
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="crux_capture_"))
    try:
        for section in (_discovery_tests, _hook_core_tests, _sweep_tests, _pending_tests,
                        _wrap_tests, _install_tests):
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
