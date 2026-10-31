"""Capture plumbing (spec 19, chunk C3): the SessionStart hook, the catch-up sweep, the
per-transcript sweep mark, the pending list, and the data behind `crux wrap`.

The sweep reads only transcript text written after its stored mark, cuts it to a hard token
cap, and hands it to ONE detached `claude -p` capture run on a small model. It never asks the
PI anything: the capture run records what it is sure of and appends the rest to the pending
list, which the next `/crux-wrap` shows. There is no periodic sweep; it runs only from the
SessionStart hook (source `startup` or `clear`) and from `crux sweep` / `crux wrap`.

Machine-local state lives in `<vault>/.crux/`, a folder that ignores itself in git
(transcript paths are machine-local):

    .crux/sweep.json     {"marks": {"<transcript path>": <byte offset swept>},
                          "capture_runs": ["<transcript path of a capture run>", ...]}
    .crux/pending        the pending list, one JSON object per line (below)
    .crux/sweep-input-<stamp>.txt   the capped text handed to a capture run
    .crux/sweep.log      the capture run's own stdout/stderr

Every read-modify-write of `sweep.json` goes through `update_marks`, which holds the same
`id_lock` as the pending list, so concurrent session starts never lose a mark.

Pending record shape — one JSON object per line, UTF-8, appended (never rewritten except by
`pending_clear`). Every append and every rewrite holds the O_EXCL lock `.crux/.crux.lock`
(engine `id_lock` on the state folder); another writer (C2's migration) must take it too.
Required: `kind`, `parent`, `text`, `source`; a line without all four, or
not a JSON object, is skipped on read.

    {"id": "p1a2b3c4",            # optional; when absent, a stable id is derived from the line
     "kind": "question" | "hypothesis" | "finding" | <any short word>,
     "parent": "q3" | null,       # the node it would hang under
     "text": "the candidate, in plain words",
     "source": "sweep" | "wrap" | "migrate" | ...,
     "created": "2026-10-31T12:00:00Z",   # optional
     ...}                         # any extra keys are kept and shown as-is

Transcripts are Claude Code JSONL under `~/.claude/projects/<cwd-slug>/<session-id>.jsonl`:
one record per line, `type` user|assistant, `message.content` a string or a list of blocks
(`text`, `tool_use` with `input.command` for Bash, `tool_result`), `isSidechain`, `isMeta`.

Recursion guard (risk R3): the capture run carries `CRUX_SWEEP=1`. Under it the hook emits
nothing, starts nothing, and lists its own transcript as a capture run; the run's session id
is also pre-assigned and listed before launch. Capture-run transcripts are never swept.

Every hook path is silent on failure: a hook that breaks a session is worse than a sweep that
did not happen. Stdlib only."""
import os, re, sys, json, time, uuid, shlex, shutil, hashlib, subprocess

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

CORE_PATH = os.path.abspath(os.path.join(HERE, "..", "SKILL.md"))
CRUX_PY = os.path.join(HERE, "crux.py")
#: The capture subagent's brief. Its content is chunk C7's; this module only points at it.
CAPTURE_BRIEF = os.path.abspath(os.path.join(HERE, "..", "..", "..", "agents", "crux-capture",
                                             "AGENT.md"))

STATE_DIR = ".crux"
MARKS_FILE = "sweep.json"
PENDING_FILE = "pending"
LOCK_FILE = "sweep.lock"
LOCK_STALE_S = 120
KEEP_INPUTS = 5

CHARS_PER_TOKEN = 4
TOKEN_CAP = 20000
CHAR_CAP = TOKEN_CAP * CHARS_PER_TOKEN
SWEEP_MODEL = "haiku"
SWEEP_MAX_TURNS = 25
SWEEP_ENV = "CRUX_SWEEP"
CLAUDE_ENV = "CRUX_SWEEP_CLAUDE"   # a command line run instead of `claude` (a test stub)
VAULT_ENV = "CRUX_VAULT"     # engine find_vault falls back to it (a vault one level down)
SWEEP_SOURCES = ("startup", "clear")
SWEEP_TOOLS = "Bash,Read"
SWEEP_ALLOWED = ("Bash(crux:*)", "Bash(python3 %s:*)" % CRUX_PY, "Read")
SWEEP_PERMISSION_MODE = "dontAsk"

HOOK_EVENT = "SessionStart"
CUT_NOTE = "[earlier text was cut to the sweep's token cap]\n"

#: crux verbs that write a record, by alias → canonical name. Read-only verbs are absent.
WRITE_VERBS = {}
for _canon, _aliases in (("ask", ("ask", "question", "q", "meta")),
                         ("hypothesize", ("hypothesize", "hypothesis", "idea")),
                         ("finding", ("finding", "record", "conclude", "land")),
                         ("park", ("park", "shelve")),
                         ("test", ("test", "experiment", "run", "stage", "launch"))):
    for _a in _aliases:
        WRITE_VERBS[_a] = _canon
TASK_VERBS = ("task", "todo", "work")
TASK_WRITES = ("add", "done", "drop")


# ------------------------------------------------------------------------------- discovery
def find_vault_near(start=None):
    """The vault at `start`, at an ancestor, or one level down (e.g. `./cruxvault`); None if
    none. One level down prefers `cruxvault`, then the first by name."""
    d = os.path.abspath(start or os.getcwd())
    try:
        return E.find_vault(d)
    except E.CruxError:
        pass
    try:
        subs = sorted(os.listdir(d))
    except OSError:
        return None
    subs.sort(key=lambda n: n != "cruxvault")
    for n in subs:
        p = os.path.join(d, n)
        if os.path.isfile(os.path.join(p, E.VAULT_MARKER)):
            return p
    return None


def project_slug(cwd):
    """Claude Code's projects-folder name for a cwd: every non-alphanumeric char → '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", cwd)


def project_dir(cwd):
    """`~/.claude/projects/<slug>` for this cwd, trying the path as given and its realpath."""
    base = os.path.join(os.path.expanduser("~"), ".claude", "projects")
    cands = [os.path.join(base, project_slug(c)) for c in (cwd, os.path.realpath(cwd))]
    for c in cands:
        if os.path.isdir(c):
            return c
    return cands[0]


def _key(path):
    """A transcript path as a marks key: absolute and normalised, so one transcript is one key
    whether it arrived with `/` or `\\` separators (Windows hands out both)."""
    return os.path.abspath(path) if path else path


def claude_argv():
    """The capture run's binary as an argv prefix, or None when there is none. CRUX_SWEEP_CLAUDE
    is a command line, split like auto's CRUX_AUTO_CLAUDE, so a test can run a Python stub
    through sys.executable: Windows cannot execute a #! script."""
    cmd = os.environ.get(CLAUDE_ENV)
    if cmd:
        return shlex.split(cmd)
    found = shutil.which("claude")
    return [found] if found else None


# ------------------------------------------------------------------------------- state
def _state(vault):
    d = os.path.join(vault, STATE_DIR)
    os.makedirs(d, exist_ok=True)
    gi = os.path.join(d, ".gitignore")
    if not os.path.isfile(gi):
        with open(gi, "w", encoding="utf-8") as f:
            f.write("*\n")
    return d


def load_marks(vault):
    p = os.path.join(vault, STATE_DIR, MARKS_FILE)
    try:
        with open(p, encoding="utf-8") as f:
            m = json.load(f)
    except Exception:
        m = {}
    if not isinstance(m, dict):
        m = {}
    if not isinstance(m.get("marks"), dict):
        m["marks"] = {}
    if not isinstance(m.get("capture_runs"), list):
        m["capture_runs"] = []
    return m


def save_marks(vault, m):
    p = os.path.join(_state(vault), MARKS_FILE)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(m, f, indent=1, sort_keys=True)
    os.replace(tmp, p)


def update_marks(vault, change):
    """Read-modify-write the marks under the state lock (the pending store's `id_lock`), so
    concurrent session starts, sweeps and wraps never lose each other's marks. `change(m)`
    edits `m` in place and returns False to skip the write."""
    with E.id_lock(_state(vault)):
        m = load_marks(vault)
        if change(m) is not False:
            save_marks(vault, m)
        return m


def _lock(vault):
    """An O_EXCL lock so two sessions starting at once launch one run, not two."""
    p = os.path.join(_state(vault), LOCK_FILE)
    try:
        if time.time() - os.path.getmtime(p) > LOCK_STALE_S:
            os.unlink(p)
    except OSError:
        pass
    try:
        os.close(os.open(p, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
        return p
    except (FileExistsError, PermissionError):     # Windows: a delete-pending lock file
        return None


def mark_capture_run(vault, transcript):
    transcript = _key(transcript)

    def change(m):
        if not transcript or transcript in m["capture_runs"]:
            return False
        m["capture_runs"].append(transcript)
    update_marks(vault, change)


# ------------------------------------------------------------------------------- transcripts
def _blocks_text(content):
    if isinstance(content, str):
        return content
    return "\n".join(str(b.get("text") or "") for b in (content or ())
                     if isinstance(b, dict) and b.get("type") == "text")


def _records(raw):
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if isinstance(rec, dict):
            yield rec


def _crux_calls(cmd):
    """Every crux invocation in a shell command: (verb, args) pairs."""
    try:
        lx = shlex.shlex(cmd, posix=True, punctuation_chars=True)
        lx.whitespace_split = True
        toks = list(lx)
    except Exception:
        return []
    out, i = [], 0
    while i < len(toks):
        if os.path.basename(toks[i]) in ("crux", "crux.py") and i + 1 < len(toks):
            j = i + 1
            args = []
            while j < len(toks) and not set(toks[j]) <= set("&|;()<>"):
                args.append(toks[j]); j += 1
            if args:
                out.append((args[0], args[1:]))
            i = j
        else:
            i += 1
    return out


def text_since(path, start):
    """The readable text of a transcript from byte `start` to its last complete line.
    Returns (text, end_offset)."""
    with open(path, "rb") as f:
        f.seek(start)
        raw = f.read()
    cut = raw.rfind(b"\n")
    if cut < 0:
        return "", start
    raw = raw[:cut + 1]
    lines = []
    for rec in _records(raw.decode("utf-8", errors="replace")):
        if rec.get("isSidechain") or rec.get("isMeta"):
            continue
        kind = rec.get("type")
        msg = rec.get("message") if isinstance(rec.get("message"), dict) else {}
        content = msg.get("content")
        if kind == "user":
            t = E._INJECTED_RE.sub(" ", _blocks_text(content)).strip()
            if t:
                lines.append("PI: " + t)
        elif kind == "assistant":
            t = _blocks_text(content).strip()
            if t:
                lines.append("AGENT: " + t)
            for b in content if isinstance(content, list) else ():
                if isinstance(b, dict) and b.get("type") == "tool_use":
                    c = (b.get("input") or {}).get("command") if isinstance(b.get("input"), dict) else None
                    if c and _crux_calls(str(c)):
                        lines.append("AGENT ran: " + str(c))
    return "\n".join(lines), start + len(raw)


def _complete_end(path):
    """The byte offset just past the transcript's last complete line."""
    with open(path, "rb") as f:
        raw = f.read()
    return raw.rfind(b"\n") + 1


def register_session(vault, transcript, source):
    """Give the current session's transcript a mark if it has none: 0 for a fresh start or a
    clear (all of it is new), its current end on a resume or compact of an older session."""
    if not transcript:
        return
    transcript = _key(transcript)

    def change(m):
        if transcript in m["marks"] or transcript in m["capture_runs"]:
            return False
        fresh = source in SWEEP_SOURCES or not os.path.isfile(transcript)
        m["marks"][transcript] = 0 if fresh else _complete_end(transcript)
    update_marks(vault, change)


def cap_text(text):
    """Cut to CHAR_CAP, keeping the newest text. Returns (text, truncated)."""
    if len(text) <= CHAR_CAP:
        return text, False
    return CUT_NOTE + text[-(CHAR_CAP - len(CUT_NOTE)):], True


# ------------------------------------------------------------------------------- sweep
def _launch_cmd(claude, input_path, session_id):
    prompt = ("You are the crux capture run. Read your brief first: %s\n"
              "The new conversation text to capture is in the file: %s\n"
              "Run crux as: python3 %s <verb> ...\n"
              "Record what you are sure of. Append anything uncertain with `pending add`. "
              "Never ask anyone anything.\n" % (CAPTURE_BRIEF, input_path, CRUX_PY))
    # --tools is what EXISTS (Bash and Read only); --allowedTools pre-approves the crux
    # patterns; dontAsk denies anything else instead of prompting, so the PI's own
    # permissions.allow or defaultMode cannot widen a run no one is watching.
    return list(claude) + ["-p", prompt, "--model", SWEEP_MODEL, "--max-turns", str(SWEEP_MAX_TURNS),
            "--tools", SWEEP_TOOLS, "--allowedTools", ",".join(SWEEP_ALLOWED),
            "--permission-mode", SWEEP_PERMISSION_MODE, "--disallowedTools", "AskUserQuestion",
            "--session-id", session_id]


def run_sweep(vault, proj_dir, current=None, cwd=None):
    """Sweep every transcript in `proj_dir` past its mark, except `current` and capture runs.
    Launches at most one detached capture run. Returns a report dict."""
    rep = {"launched": False, "transcripts": [], "chars": 0, "truncated": False, "reason": ""}
    if os.environ.get(SWEEP_ENV) == "1":
        rep["reason"] = "inside a capture run"
        return rep
    claude = claude_argv()
    if not claude:
        rep["reason"] = "no claude binary"
        return rep
    lock = _lock(vault)
    if not lock:
        rep["reason"] = "another sweep is starting"
        return rep
    try:
        m = load_marks(vault)
        proj_dir = _key(proj_dir)
        skip = {_key(p) for p in m["capture_runs"]} | ({_key(current)} if current else set())
        try:
            names = sorted(fn for fn in os.listdir(proj_dir) if fn.endswith(".jsonl"))
        except OSError:
            names = []
        paths = [os.path.join(proj_dir, fn) for fn in names]
        paths = [p for p in paths if p not in skip]
        paths.sort(key=lambda p: os.path.getmtime(p))
        parts, new_marks = [], {}
        for p in paths:
            if p not in m["marks"]:
                # First sight: a session from before background capture. Baseline it at its
                # end and sweep nothing, so an install never triggers a capped run over old
                # history. (A session started since has its mark set to 0 by the hook.)
                new_marks[p] = _complete_end(p)
                continue
            start = m["marks"][p]
            if os.path.getsize(p) <= start:
                continue
            text, end = text_since(p, start)
            if end > start:
                new_marks[p] = end
            if text:
                parts.append("### session %s\n%s" % (os.path.basename(p)[:-6], text))
                rep["transcripts"].append(p)
        if not parts:
            if new_marks:
                update_marks(vault, lambda cur: cur["marks"].update(new_marks))
            rep["reason"] = "nothing new"
            return rep
        text, rep["truncated"] = cap_text("\n\n".join(parts))
        rep["chars"] = len(text)
        if text:
            d = _state(vault)
            inp = os.path.join(d, "sweep-input-%s.txt" % time.strftime("%Y%m%dT%H%M%S"))
            if os.path.exists(inp):
                inp = inp[:-4] + "-%s.txt" % uuid.uuid4().hex[:6]
            with open(inp, "w", encoding="utf-8") as f:
                f.write(text)
            sid = str(uuid.uuid4())

            def change(cur):
                cur["capture_runs"].append(os.path.join(proj_dir, sid + ".jsonl"))
                cur["marks"].update(new_marks)
            update_marks(vault, change)
            # CRUX_VAULT: the run's cwd is the repo, and the vault may sit one level down
            # (`./cruxvault`); the engine's find_vault falls back to it, so every crux verb
            # the capture agent runs resolves this vault.
            env = dict(os.environ, **{SWEEP_ENV: "1", VAULT_ENV: vault})
            with open(os.path.join(d, "sweep.log"), "ab") as log:
                subprocess.Popen(_launch_cmd(claude, inp, sid), cwd=cwd or os.path.dirname(vault),
                                 env=env, stdin=subprocess.DEVNULL, stdout=log,
                                 stderr=subprocess.STDOUT, start_new_session=True)
            rep["launched"] = True
            olds = sorted(fn for fn in os.listdir(d) if fn.startswith("sweep-input-"))
            for fn in olds[:-KEEP_INPUTS]:
                os.unlink(os.path.join(d, fn))
        else:
            update_marks(vault, lambda cur: cur["marks"].update(new_marks))
            rep["reason"] = "no conversation text in the new bytes"
        return rep
    finally:
        try:
            os.unlink(lock)
        except OSError:
            pass


# ------------------------------------------------------------------------------- hook
def session_hook_command():
    """The literal command the SessionStart hook runs, absolutely pathed."""
    return "%s %s hook session-start" % (shlex.quote(sys.executable), shlex.quote(CRUX_PY))


def session_start(payload):
    """The hook's whole job. Returns the context string to inject, or None. Never raises."""
    try:
        if not isinstance(payload, dict):
            payload = {}
        cwd = payload.get("cwd") or os.getcwd()
        transcript = payload.get("transcript_path")
        transcript = os.path.expanduser(str(transcript)) if transcript else None
        vault = find_vault_near(cwd)
        if not vault:
            return None
        if os.environ.get(SWEEP_ENV) == "1":
            try:
                mark_capture_run(vault, transcript)
            except Exception:
                pass
            return None
        with open(CORE_PATH, encoding="utf-8") as f:
            core = f.read()
    except Exception:
        return None
    try:
        register_session(vault, transcript, payload.get("source"))
        if payload.get("source") in SWEEP_SOURCES:
            proj = os.path.dirname(transcript) if transcript else project_dir(cwd)
            run_sweep(vault, proj, current=transcript, cwd=cwd)
    except Exception:
        pass
    return core


def install_session_hook(settings_path):
    """Register the SessionStart hook in a Claude Code settings file. Idempotent by search:
    an existing `hook session-start` entry is repaired in place, never duplicated. Every
    unrelated key and hook is kept. No matcher: the core is injected on every source; the
    sweep itself checks the source."""
    path = os.path.expanduser(settings_path)
    cfg = {}
    if os.path.isfile(path):
        try:
            cfg = json.loads(E.read(path) or "{}")
        except Exception as e:
            raise E.CruxError(f"{path} is not valid JSON ({e}) — fix or move it, then re-run")
    if not isinstance(cfg, dict) or not isinstance(cfg.setdefault("hooks", {}), dict):
        raise E.CruxError(f"{path}: not a JSON object with an object 'hooks' — fix it, then re-run")
    groups = cfg["hooks"].setdefault(HOOK_EVENT, [])
    if not isinstance(groups, list):
        raise E.CruxError(f"{path}: 'hooks.{HOOK_EVENT}' is not a list — fix it, then re-run")
    cmd = session_hook_command()
    for g in groups:
        for h in (g.get("hooks") or []) if isinstance(g, dict) else ():
            if isinstance(h, dict) and "hook session-start" in str(h.get("command") or ""):
                if h["command"] == cmd:
                    return "present"
                h["command"] = cmd
                E._write_settings(path, cfg)
                return "repaired"
    groups.append({"hooks": [{"type": "command", "command": cmd}]})
    E._write_settings(path, cfg)
    return "installed"


# ------------------------------------------------------------------------------- pending
def _pending_path(vault):
    return os.path.join(vault, STATE_DIR, PENDING_FILE)


def pending_list(vault):
    """Every well-formed pending record, in file order, each with an `id`."""
    try:
        with open(_pending_path(vault), encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    out = []
    for line in lines:
        try:
            rec = json.loads(line)
        except Exception:
            continue
        if not isinstance(rec, dict) or not all(k in rec for k in ("kind", "parent", "text",
                                                                    "source")):
            continue
        if not rec.get("id"):
            rec["id"] = "p" + hashlib.sha1(line.strip().encode()).hexdigest()[:8]
        out.append(rec)
    return out


def pending_add(vault, kind, parent, text, source):
    rec = {"id": "p" + uuid.uuid4().hex[:8], "kind": kind, "parent": parent, "text": text,
           "source": source, "created": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    with E.id_lock(_state(vault)):
        with open(_pending_path(vault), "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return rec


def pending_clear(vault, ids):
    """Remove the records with these ids (malformed lines are kept as they are)."""
    with E.id_lock(_state(vault)):
        return _pending_clear(vault, set(ids))


def _pending_clear(vault, ids):
    p = _pending_path(vault)
    try:
        with open(p, encoding="utf-8") as f:
            lines = f.read().splitlines()
    except OSError:
        return []
    keep, gone = [], []
    for line in lines:
        try:
            rec = json.loads(line)
        except Exception:
            rec = None
        rid = None
        if isinstance(rec, dict):
            rid = rec.get("id") or "p" + hashlib.sha1(line.strip().encode()).hexdigest()[:8]
        if rid in ids:
            gone.append(rid)
        else:
            keep.append(line)
    with open(p + ".tmp", "w", encoding="utf-8") as f:
        f.write("".join(x + "\n" for x in keep))
    os.replace(p + ".tmp", p)
    return gone


# ------------------------------------------------------------------------------- wrap
def _result_text(content):
    if isinstance(content, list):
        return "\n".join(str(b.get("text") or "") for b in content if isinstance(b, dict))
    return str(content or "")


def _result_id(text):
    try:
        obj = json.loads(text)
        if isinstance(obj, dict) and obj.get("id"):
            return str(obj["id"])
    except Exception:
        pass
    m = re.search(r"✓\s+([A-Za-z]+\d+)\b", text)
    return m.group(1) if m else None


def session_records(path):
    """The records a session wrote, read from its own successful crux tool calls."""
    with open(path, encoding="utf-8", errors="replace") as f:
        recs = list(_records(f.read()))
    calls, results = [], {}
    for rec in recs:
        if rec.get("isSidechain"):
            continue
        content = (rec.get("message") or {}).get("content") if isinstance(rec.get("message"), dict) else None
        for b in content if isinstance(content, list) else ():
            if not isinstance(b, dict):
                continue
            if b.get("type") == "tool_use" and isinstance(b.get("input"), dict):
                cmd = b["input"].get("command")
                if cmd:
                    calls.append((b.get("id"), str(cmd)))
            elif b.get("type") == "tool_result":
                results[b.get("tool_use_id")] = (bool(b.get("is_error")),
                                                 _result_text(b.get("content")))
    out = []
    for tid, cmd in calls:
        err, text = results.get(tid, (True, ""))
        if err:
            continue
        for verb, args in _crux_calls(cmd):
            if verb in WRITE_VERBS:
                canon = WRITE_VERBS[verb]
            elif verb in TASK_VERBS and args and args[0] in TASK_WRITES:
                canon, args = "task " + args[0], args[1:]
            else:
                continue
            out.append({"verb": canon, "args": args, "id": _result_id(text),
                        "result": text.strip().splitlines()[0] if text.strip() else ""})
    return out


def newest_transcript(proj_dir, vault=None):
    skip = {_key(p) for p in load_marks(vault)["capture_runs"]} if vault else set()
    proj_dir = _key(proj_dir)
    try:
        ps = [os.path.join(proj_dir, fn) for fn in os.listdir(proj_dir) if fn.endswith(".jsonl")]
    except OSError:
        return None
    ps = [p for p in ps if p not in skip]
    return max(ps, key=os.path.getmtime) if ps else None


def wrap(vault, transcript):
    """`/crux-wrap`'s data: this session's records, the pending list, and the session's text
    since its mark (capped). Advances this session's mark, so the next session start does not
    sweep what the wrap already covered."""
    out = {"vault": vault, "transcript": transcript, "records": [], "text": "",
           "truncated": False, "pending": pending_list(vault), "review": []}
    if not transcript or not os.path.isfile(transcript):
        return out
    transcript = _key(transcript)
    out["records"] = session_records(transcript)
    # spec 20: each record's path to the top question, and the questions this session moved
    # that no strong finding settles yet — the candidates for the stalled-line check
    v = E.Vault(vault)
    seen = set()
    for rec in out["records"]:
        rec["path"] = E.bears_path(v, rec["id"]) if rec["id"] in v.nodes else []
        if rec["verb"] not in ("ask", "hypothesize", "finding") or rec["id"] not in v.nodes:
            continue
        q = next((a for a in E._ancestors(v, rec["id"]) if v.nodes[a].type == "question"), None)
        if q is None or q in seen:
            continue
        seen.add(q)
        under = [q] + [c for c in v.children.get(q, ()) if v.nodes[c].type == "idea"]
        if v.nodes[q]["fm"].get(E.PARKED_FIELD) is True or any(
                E.effective_confidence(f) == "strong" for x in under for f in E.node_findings(v, x)):
            continue
        out["review"].append({"id": q, "title": v.nodes[q].title, "path": E.bears_path(v, q)})
    start = load_marks(vault)["marks"].get(transcript, 0)
    text, end = text_since(transcript, start)
    out["text"], out["truncated"] = cap_text(text)

    def change(m):
        if end <= m["marks"].get(transcript, 0):
            return False
        m["marks"][transcript] = end
    update_marks(vault, change)
    return out
