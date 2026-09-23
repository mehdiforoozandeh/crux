#!/usr/bin/env python3
"""autopilot — the impure half of crux autopilot (spec 05, slices 05.1 and 05.2).

Everything that starts a process, takes a lock, or touches a git repository lives HERE, and
nothing else in crux does any of it. `engine.py` stays a pure function of the vault's text:
it can be read top to bottom and trusted without asking what was running at the time. That
line is the whole design of this file, and it is one-way — this module imports the engine,
the engine never imports this module.

What 05.1 is:
  * one vault-level lock at `auto/.lock`, so two runs in one vault cannot both take id h44;
  * ids reserved CENTRALLY, before a node exists, recorded in `auto/<qid>/reserved.json`;
  * the ref namespace `refs/crux/auto/<qid>/{base,<hid>}` — an attempt is a ref, never a
    branch, which is what lets its worktree be thrown away the moment the commit is recorded;
  * the branches `crux/auto/<qid>/run` and `crux/auto/<qid>/island/<island>`, plus the one
    `crux/auto/<qid>/promoted/<hid>` the PI asks for by name;
  * per-attempt worktrees under `<repo>.crux-auto/<qid>/<hid>`;
  * the frozen-path diff and the manifest over shared roots — both DETECT AND REPORT ONLY;
  * retention over the workspace alone, never over the record;
  * the scorer contract: stdout is one JSON object, and the DRIVER writes it verbatim to
    `results/<hid>/metrics.json`. The engine only ever reads that file.

What 05.2 adds is `auto_run` — the driver:
  * one polled worker subprocess per attempt, `parallel_total` of them at a time, and the
    post-worker pipeline (frozen diff, manifest re-check, proposal) run synchronously;
  * the four engine acts the plan's approval covers, per attempt: `hypothesize` at the
    reserved id, `approve-null`, `test --to running`, `close` — every node write goes through
    an engine function, and NO verdict is ever assigned here;
  * `auto/<qid>/state.json` (rewritten whole, under the lock, after every event) and
    `auto/<qid>/ledger.jsonl` (appended, flushed, fsynced, never rewritten);
  * the five phases and the resume that reconciles them against what is actually on disk;
  * the four stops of §11, the confirmation seeds, the stall escalation, and the island-best
    pointer moved by compare-and-swap.

`CRUX_AUTO_CRASH_AT=<phase>` makes the driver kill itself the instant that phase is first
recorded. It exists for ONE caller — the tier-zero fixture in `selftest.py` that proves a
killed run resumes — and a real kill is the point: a resume tested by asking the driver
nicely to stop is a resume from a clean shutdown, which is not the case that happens at
three in the morning.

What is still NOT here: the worker and steward agents (05.3), the cockpit (05.4), a commit
on any branch, and any write to `main`. Nothing below checks out a branch, merges, or commits
on the PI's behalf; vault writes stay uncommitted.
"""
import os, sys, json, time, shlex, signal, socket, subprocess, shutil, tempfile, contextlib

import engine as E


# ------------------------------------------------------------------ names, constants, paths
HOST                   = socket.gethostname()
LOCK_NAME              = ".lock"                 # <root>/auto/.lock
RESERVED_FILE          = "reserved.json"         # <root>/auto/<qid>/reserved.json
MANIFESTS_DIR          = "manifests"             # <root>/auto/<qid>/manifests/<hid>.json
WORKTREES_DIR          = "crux-auto"             # <repo>.crux-auto/<qid>/<hid> — see worktrees_root
REF_PREFIX             = "refs/crux/auto"
BRANCH_PREFIX          = "crux/auto"
LOCK_WAIT              = 60.0                    # seconds a caller waits before refusing
LOCK_STALE             = 900.0                   # seconds after which any lock is stale by age
LOCK_POLL              = 0.05                    # seconds between attempts
SCORER_TIMEOUT_DEFAULT = E.AUTO_SCORER_TIMEOUT_DEFAULT
STDERR_TAIL            = 2000                    # characters kept from a failing scorer's stderr
STDOUT_HEAD            = 200                     # characters quoted from a non-JSON stdout
RESERVATION_STATES     = ("reserved", "materialized", "abandoned")
# 05.2, the driver.
POLL                   = 0.05                    # seconds between polls of a live worker
BRIEF_NAME             = "brief.md"              # <workspace>/brief.md
PROPOSAL_NAME          = "proposal.json"         # <workspace>/proposal.json — the worker's
WORKER_LOG             = "worker.log"            # <workspace>/worker.log — stdout + stderr
BASE_WORKTREE          = "base"                  # the throwaway checkout the run-open scorer
                                                 # check runs in, so the PI's tree stays clean
CRASH_ENV              = "CRUX_AUTO_CRASH_AT"    # test-only; see the module docstring
OUTPUT_TAIL            = 500                     # characters of worker.log quoted on a failure
# 05.3, the agents. Two more spawn sites reach the SAME command list the worker walks, so the
# keys they register under `ctx["procs"]` have to be names no attempt id can collide with: a
# hid never holds a `:` and is never the literal `steward`, and `auto_run`'s `finally` kills
# whatever is in that dict. A worker never outlives its driver, and neither does a closer.
PROC_CLOSE             = "{hid}:close"           # ctx["procs"] key for one closer
PROC_STEWARD           = "steward"               # ctx["procs"] key for the steward
CLOSE_BRIEF_NAME       = "close-brief.md"        # <workspace>/close-brief.md — CRUX_BRIEF
CLOSE_PROPOSAL_NAME    = "close.json"            # <workspace>/close.json — CRUX_PROPOSAL
CLOSER_LOG             = "closer.log"            # <workspace>/closer.log
STEWARD_DIR            = "steward"               # auto/<qid>/steward/<n>/ — NOT a writable root
STEWARD_BRIEF_NAME     = "brief.md"
STEWARD_PROPOSAL_NAME  = "proposal.json"
STEWARD_LOG            = "steward.log"

# Pinned on every call rather than left to the machine: a run may start on a box with no
# global identity at all, and a driver that fails for that reason fails at 3 a.m.
# `core.quotePath=false` for the same reason one step down: with it on, a path holding a
# non-ASCII byte comes back as `"sc\303\266re.py"` — quoted and escaped — and a frozen-path
# comparison against it silently never matches.
GIT_IDENTITY = ["-c", "user.name=crux-autopilot", "-c", "user.email=autopilot@crux.invalid",
                "-c", "commit.gpgsign=false", "-c", "core.quotePath=false"]

# `plan_repo` and `git_common_dir` are asked for by nearly every function below, and each ask
# is a process. Both answers are a function of arguments that do not change inside one call
# chain, so they are remembered — and re-checked against the filesystem before reuse, because
# a remembered path to a directory that has since gone is worse than no memory at all.
_TOPLEVEL_CACHE = {}          # (vault root, the plan's raw repo: field) -> repository toplevel
_COMMON_DIR_CACHE = {}        # repository toplevel -> its shared git directory


def lock_path(root):
    return os.path.join(root, E.AUTO_DIR, LOCK_NAME)


def reserved_path(root, qid):
    return os.path.join(root, E.AUTO_DIR, qid, RESERVED_FILE)


def manifest_path(root, qid, hid):
    return os.path.join(root, E.AUTO_DIR, qid, MANIFESTS_DIR, hid + ".json")


def state_path(root, qid):
    return os.path.join(root, E.AUTO_DIR, qid, E.AUTO_STATE_FILE)


def ledger_path(root, qid):
    return os.path.join(root, E.AUTO_DIR, qid, E.AUTO_LEDGER_FILE)


def base_ref(qid):
    return f"{REF_PREFIX}/{qid}/base"


def attempt_ref(qid, hid):
    """`base` is not a legal hypothesis id, so this can never collide with `base_ref`."""
    return f"{REF_PREFIX}/{qid}/{hid}"


def run_branch(qid):
    return f"{BRANCH_PREFIX}/{qid}/run"


def island_branch(qid, island):
    return f"{BRANCH_PREFIX}/{qid}/island/{island}"


def promoted_branch(qid, hid):
    return f"{BRANCH_PREFIX}/{qid}/promoted/{hid}"


def _rel_posix(base, path):
    return os.path.relpath(path, base).replace(os.sep, "/")


def _write_json(path, obj, sort_keys=False):
    """Write the document, or leave the old one exactly as it was.

    Through a temporary file in the same directory and one `os.replace`, because every file
    written here is a RECORD: a reservation the next run reads to know which ids are spent, a
    manifest that is the before-picture of the shared roots, the metrics a verdict is read
    from. Truncate-in-place turns a crash mid-write into half a file, and half a reservation
    file parses as no reservations at all."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    text = json.dumps(obj, indent=2, sort_keys=sort_keys, ensure_ascii=False) + "\n"
    tmp = path + ".tmp"
    try:
        with open(tmp, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            try:
                os.unlink(tmp)
            except OSError:
                pass


# ------------------------------------------------------------------- the process primitives
SIGKILL = getattr(signal, "SIGKILL", 9)    # Windows has no SIGKILL; nothing there uses it


def _run(argv, cwd=None, env=None, timeout=None):
    """The ONE place this module starts a process.

    One spawn site is what makes "did this verb start anything?" a question a test can answer
    by replacing a single name — and what makes the no-shell rule checkable by reading four
    lines rather than forty. No shell is ever interposed: the scorer command is the PI's, and
    a shell between it and the driver is one more thing that can rewrite it.

    The child gets its OWN session, so a timeout can kill the whole tree. A training scorer is
    `python train.py` that forks eight dataloader workers and a CUDA server; killing the one
    process named in the command leaves those eight running on the PI's GPUs for as long as
    the machine is up. `subprocess.TimeoutExpired` and `OSError` propagate — only `run_scorer`
    has anything to say about either."""
    p = subprocess.Popen(list(argv), cwd=cwd, env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         encoding="utf-8", errors="replace", start_new_session=True)
    try:
        out, err = p.communicate(timeout=timeout)
    except subprocess.TimeoutExpired:
        # Kill the whole session where the platform has one; Windows has no process groups
        # in this sense (no getpgid/killpg), so the direct child is what gets killed there.
        try:
            os.killpg(os.getpgid(p.pid), SIGKILL)
        except (OSError, AttributeError):
            p.kill()
        p.communicate()
        raise
    except BaseException:
        p.kill()
        p.communicate()
        raise
    return subprocess.CompletedProcess(list(argv), p.returncode, out, err)


def _spawn(argv, cwd, env, log_path):
    """The SECOND and last place this module starts a process: one worker, left running.

    `_run` waits; this one does not, because the driver polls several workers at once from a
    single thread. Everything the child says goes to `worker.log` in its own workspace —
    binary append, so two tries of the same attempt stack rather than overwrite, and a
    non-UTF-8 byte from somebody's CUDA stack cannot take the driver down.

    stdin is `/dev/null`: an agent that reads it and a driver that never writes it deadlock,
    and a deadlock at 3 a.m. looks exactly like a slow model. The child gets its own session
    so `_kill_tree` can take the whole tree with it."""
    d = os.path.dirname(log_path)
    if d:
        os.makedirs(d, exist_ok=True)
    log = open(log_path, "ab")
    try:
        return subprocess.Popen(list(argv), cwd=cwd, env=env, stdin=subprocess.DEVNULL,
                                stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    finally:
        log.close()               # the child holds its own descriptor; the parent's is done


def _kill_tree(p):
    """Kill a worker and everything it forked, then reap it. Total: a process that is already
    gone is not an error, and a platform with no process groups gets the direct child."""
    try:
        os.killpg(os.getpgid(p.pid), SIGKILL)
    except (OSError, AttributeError):
        p.kill()
    p.wait()


def _git_argv(cwd, args):
    return ["git"] + GIT_IDENTITY + ["-C", cwd] + [str(a) for a in args]


def _git(cwd, *args):
    """git, refused loudly. stdout stripped; a non-zero exit is a CruxError naming the verb."""
    r = _run(_git_argv(cwd, args), cwd=cwd)
    if r.returncode != 0:
        tail = (r.stderr or "").strip()[-500:] or "(no stderr)"
        raise E.CruxError(f"git {args[0]} failed in {cwd}: {tail}")
    return (r.stdout or "").strip()


def rev_parse(repo, ref):
    """The 40-hex commit `ref` names in `repo`, or None. TOTAL: an absent ref, a bad repo and
    a git that will not start all read the same — "there is no commit there"."""
    try:
        r = _run(_git_argv(repo, ["rev-parse", "--verify", "--quiet", str(ref) + "^{commit}"]),
                 cwd=repo)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    return (r.stdout or "").strip() or None


def git_toplevel(path):
    """The working tree enclosing `path`, realpath'd — or None when nothing does.

    Realpath'd because macOS hands out `/var/...` for a directory whose real name is
    `/private/var/...`, and every path comparison below would trip over the difference."""
    if not os.path.isdir(path):
        return None
    try:
        r = _run(_git_argv(path, ["rev-parse", "--show-toplevel"]), cwd=path)
    except OSError:
        return None
    if r.returncode != 0:
        return None
    out = (r.stdout or "").strip()
    return os.path.realpath(out) if out else None


def git_common_dir(repo):
    """The repository's shared git directory.

    Shared rather than per-worktree on purpose: every attempt resolves the same one, whichever
    checkout asks. The per-attempt checkouts themselves live OUTSIDE it — see `worktrees_root`,
    which explains why."""
    hit = _COMMON_DIR_CACHE.get(repo)
    if hit and os.path.isdir(hit):
        return hit
    out = _git(repo, "rev-parse", "--git-common-dir")
    got = os.path.realpath(out if os.path.isabs(out) else os.path.join(repo, out))
    _COMMON_DIR_CACHE[repo] = got
    return got


def worktrees_root(repo):
    """Where this repository's per-attempt checkouts live: `<repo>.crux-auto/`, a SIBLING of
    the repository and deliberately not inside `.git/`.

    They used to hang off the shared git directory, which reads well and does not work: a
    coding agent refuses to write anything under `.git/`, treating it as a protected path, so
    every worker could draft a candidate and none could save it. The checkout has to be an
    ordinary directory the worker may edit. A sibling keeps it out of the working tree too, so
    it never shows up as untracked noise in the PI's `git status`."""
    full = os.path.realpath(repo)
    return full.rstrip(os.sep) + "." + WORKTREES_DIR


def plan_repo(root, plan):
    """The repository this plan's run happens in, realpath'd.

    The vault is the notebook; the repository is the work. Usually the notebook sits inside
    the work, and `repo:` is how a PI says otherwise. Asked of git rather than guessed from
    the presence of a `.git` entry: a worktree's `.git` is a file, a submodule's points
    elsewhere, and guessing gets both wrong."""
    raw = plan.get("repo")
    key = (root, raw)
    hit = _TOPLEVEL_CACHE.get(key)
    if hit and os.path.isdir(hit):
        return hit
    if raw:
        p = raw if os.path.isabs(raw) else os.path.join(root, raw)
        top = git_toplevel(p)
        if top is None:
            raise E.CruxError(f"flight plan repo '{raw}' is not a git working tree")
    else:
        top = git_toplevel(root)
        if top is None:
            raise E.CruxError(f"no git repository encloses the vault at {root}; "
                              f"set repo: in the flight plan")
    _TOPLEVEL_CACHE[key] = top
    return top


# -------------------------------------------------------------------------------- the lock
def _pid_alive(pid):
    """Whether this host still has that process. A PermissionError means it exists and belongs
    to somebody else — which is very much alive.

    On Windows `os.kill(pid, 0)` is not a probe: signal 0 is CTRL_C_EVENT, and it is delivered
    to every process on the console, this one included. The probe there is OpenProcess."""
    try:
        pid = int(pid)
    except (TypeError, ValueError, OverflowError):
        return True
    if os.name == "nt":
        return _pid_alive_windows(pid)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        return True
    return True


def _pid_alive_windows(pid):
    """OpenProcess with query-only rights; an exit code other than STILL_ACTIVE is a dead pid.
    Access denied means the process exists and is somebody else's — alive. Any other failure
    to open is read as gone."""
    import ctypes                                   # stdlib; loaded on Windows only
    k32 = ctypes.WinDLL("kernel32", use_last_error=True)
    PROCESS_QUERY_LIMITED_INFORMATION, STILL_ACTIVE, ERROR_ACCESS_DENIED = 0x1000, 259, 5
    handle = k32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not handle:
        return ctypes.get_last_error() == ERROR_ACCESS_DENIED
    try:
        code = ctypes.c_ulong()
        if not k32.GetExitCodeProcess(handle, ctypes.byref(code)):
            return True
        return code.value == STILL_ACTIVE
    finally:
        k32.CloseHandle(handle)


def read_lock(root):
    """The holder's record: a dict, `{}` when the file is there but unreadable, None when it
    is not there at all. The three cases are distinct because the caller treats them so."""
    p = lock_path(root)
    try:
        with open(p, encoding="utf-8") as f:
            raw = f.read()
    except (IOError, OSError):
        return None
    try:
        obj = json.loads(raw)
    except ValueError:
        return {}
    return obj if isinstance(obj, dict) else {}


def acquire_lock(root, op, wait=LOCK_WAIT, stale_after=LOCK_STALE):
    """Take the vault's one lock, or refuse by NAMING THE HOLDER.

    A lock that hangs is worse than a lock that refuses: at 3 a.m. the useful output is "pid
    8123 on this host has held it for 40s doing reserve", not a cursor. The exclusive create
    is the whole mechanism — `O_CREAT | O_EXCL` is atomic on every filesystem crux runs on,
    and the record inside is only ever read to write that message.

    A lock whose owner died is reclaimed ONCE per call, never in a loop: a single reclaim is
    what recovers a crash, and a loop of them is two processes stealing from each other."""
    os.makedirs(os.path.join(root, E.AUTO_DIR), exist_ok=True)
    path = lock_path(root)
    start = time.monotonic()
    reclaimed = False
    while True:
        try:
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o644)
        except FileExistsError:
            pass
        except PermissionError:
            # Windows only. A name whose last handle has not closed yet is DELETE PENDING:
            # the holder has released it, some reader still has it open, and O_CREAT|O_EXCL
            # on that name answers ERROR_ACCESS_DENIED rather than "it exists". That is the
            # same "somebody else has it" the line above waits out, a few microseconds
            # earlier, so it is waited out the same way. On POSIX a PermissionError here is a
            # directory this process may not write, which is not a thing to spin on.
            if os.name != "nt":
                raise
        else:
            # A lock file that exists but holds nothing is the worst of both: it blocks every
            # other caller and names no holder, so nobody can be asked to let go. If the write
            # fails, the file goes with it.
            try:
                with os.fdopen(fd, "w") as f:
                    f.write(json.dumps({"pid": os.getpid(), "host": HOST, "time": E.now(),
                                        "op": op}))
            except BaseException:
                try:
                    os.unlink(path)
                except OSError:
                    pass
                raise
            return path
        holder = read_lock(root) or {}
        try:
            age = time.time() - os.stat(path).st_mtime
        except OSError:
            age = 0.0
        pid = holder.get("pid")
        mine = (holder.get("host") == HOST and isinstance(pid, int)
                and not isinstance(pid, bool))
        stale = (mine and not _pid_alive(pid)) or age > stale_after
        if stale and not reclaimed:
            reclaimed = True
            try:
                os.unlink(path)
            except FileNotFoundError:
                pass
            continue
        if time.monotonic() - start >= wait:
            rel = f"{E.AUTO_DIR}/{LOCK_NAME}"
            raise E.CruxError(
                f"auto lock {rel} is held by pid {holder.get('pid', '?')} on "
                f"{holder.get('host', '?')} ({holder.get('op', '?')}, {age:.0f}s old); "
                f"gave up after {wait:g}s")
        time.sleep(LOCK_POLL)


def release_lock(root):
    """Drop the lock, if it is still ours. A lock that is already gone is not an error — the
    caller's intent was "do not hold this", and it does not.

    Ownership is checked because a reclaim makes the two events possible in this order: this
    process is declared dead and its lock taken by another, then this process wakes up and
    releases. Without the check that release deletes the NEW holder's lock, and two writers
    run at once — the one failure the lock exists to prevent.

    The unlink is RETRIED on a Windows sharing violation. CPython opens a file for reading
    without FILE_SHARE_DELETE, so while any contender is inside `read_lock` — every one of
    them, every LOCK_POLL — deleting the same name fails with PermissionError. Letting that
    out of a `finally` turns a microsecond of overlap into a crashed writer; swallowing it
    leaves a lock nobody holds standing until LOCK_STALE, which is worse still. The reader
    closes within microseconds, so the retry is the honest answer."""
    rec = read_lock(root)
    if rec and (rec.get("pid") != os.getpid() or rec.get("host") != HOST):
        return None
    deadline = time.monotonic() + 5.0
    while True:
        try:
            os.unlink(lock_path(root))
        except (FileNotFoundError, IsADirectoryError):
            return None
        except PermissionError:
            if os.name != "nt" or time.monotonic() >= deadline:
                raise
            time.sleep(LOCK_POLL)
        else:
            return None


@contextlib.contextmanager
def vault_lock(root, op, wait=LOCK_WAIT, stale_after=LOCK_STALE):
    """The lock as a scope. NOT re-entrant: the functions below that take it take it once,
    and none of them calls another that does."""
    p = acquire_lock(root, op, wait=wait, stale_after=stale_after)
    try:
        yield p
    finally:
        release_lock(root)


# ------------------------------------------------------------------------- id reservation
def reservations(root, qid):
    """`auto/<qid>/reserved.json`, parsed — `{}` when there is none. Read-only, no lock.

    A file that is there but will not parse is REFUSED rather than read as `{}`. The two look
    the same to a reader and are opposites to a writer: treating a damaged file as empty makes
    the very next `reserve_id` overwrite every reservation in it, which is how a run loses the
    record of which ids it already spent."""
    p = reserved_path(root, qid)
    if not os.path.isfile(p):
        return {}
    try:
        obj = json.loads(E.read(p))
    except ValueError as e:
        raise E.CruxError(f"{E.AUTO_DIR}/{qid}/{RESERVED_FILE} is damaged and was not "
                          f"overwritten: {e}")
    if not isinstance(obj, dict):
        raise E.CruxError(f"{E.AUTO_DIR}/{qid}/{RESERVED_FILE} is damaged and was not "
                          f"overwritten: the file is not an object keyed by id")
    return obj


def reserve_id(root, qid, island=None, parent=None):
    """The next hypothesis id, taken ONCE, under the lock.

    The counter in `.crux.yaml` is a plain read-modify-write, so two workers that ask at the
    same instant get the same id and one silently overwrites the other's node. Reserving is
    how that stops being possible: one writer at a time, and the id is spent the moment it is
    handed out — an attempt that never becomes a node leaves a gap, and a gap costs nothing."""
    with vault_lock(root, "reserve"):
        data = reservations(root, qid)     # read first: a damaged file must not cost an id
        v = E.Vault(root)
        hid = E._new_id(v, "idea")
        data[hid] = {"at": E.now(), "pid": os.getpid(), "host": HOST,
                     "island": island or qid, "parent": parent, "state": "reserved"}
        _write_json(reserved_path(root, qid), data, sort_keys=True)
        return hid


def set_reservation_state(root, qid, hid, state):
    """Move one reservation between `reserved`, `materialized` and `abandoned`. Returns the
    record. 05.1 writes the field; 05.2's resumed run is what reads it."""
    if state not in RESERVATION_STATES:
        raise E.CruxError(f"reservation state must be one of {', '.join(RESERVATION_STATES)} "
                          f"(got '{state}')")
    with vault_lock(root, "reserve"):
        data = reservations(root, qid)
        if hid not in data:
            raise E.CruxError(f"{hid} is not reserved under {E.AUTO_DIR}/{qid}/{RESERVED_FILE}")
        rec = dict(data[hid])
        rec["state"] = state
        rec["updated"] = E.now()
        data[hid] = rec
        _write_json(reserved_path(root, qid), data, sort_keys=True)
        return rec


# ------------------------------------------------------------- refs, branches and worktrees
def open_run(root, plan):
    """Pin the run's starting commit and cut its branches. Touches no checkout at all.

    `base` is a REF rather than a branch because nothing may ever move it: every attempt is
    diffed against it and every island starts from it. The island branches are cut here, at
    base, so the prefix-directory rule (`refs/heads/a/b` and `refs/heads/a` cannot coexist)
    is discovered now rather than halfway through a run.

    A branch this run wants that ALREADY points at base is adopted rather than refused, and
    one pointing elsewhere is refused by name with the command that clears it."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    head = rev_parse(repo, "HEAD")
    if head is None:
        raise E.CruxError(f"repository at {repo} has no commits to start a run from")
    if rev_parse(repo, base_ref(qid)) is not None:
        raise E.CruxError(f"auto run for {qid} is already open ({base_ref(qid)} exists)")
    rb = run_branch(qid)
    wanted = [rb] + [island_branch(qid, i) for i in (plan.get("islands") or [qid])]

    # A previous run's branches are the NORMAL state of a repository the PI has decided to
    # start over in: clearing the vault's run record clears `base`, and nothing clears these.
    # `git branch` refuses a name that exists, so the run used to die on its first git call
    # with `fatal: a branch named 'crux/auto/q1/run' already exists` and no word about which
    # of them to delete. A branch already AT base is where this run wants it and is adopted; a
    # branch pointing anywhere else is somebody's work, and every one of them is named at once
    # with the command that removes them — a PI who deletes one only to be refused on the next
    # is reading the same error four times.
    stale = [b for b in wanted
             if rev_parse(repo, "refs/heads/" + b) not in (None, head)]
    if stale:
        raise E.CruxError(
            f"auto run for {qid} cannot open: {len(stale)} branch(es) from an earlier run "
            f"point somewhere other than this run's base commit {head[:12]}: "
            f"{', '.join(stale)}. Check that nothing there is worth keeping, then: "
            f"git -C {repo} branch -D {' '.join(stale)}")

    islands = {}
    made = []
    try:
        _git(repo, "update-ref", base_ref(qid), head)
        made.append(("ref", base_ref(qid)))
        for b in wanted:
            if rev_parse(repo, "refs/heads/" + b) is None:
                _git(repo, "branch", b, head)
                made.append(("branch", b))
        for island in (plan.get("islands") or [qid]):
            islands[island] = island_branch(qid, island)
    except BaseException:
        # All of it, or none of it. The prefix-directory rule means island two can be refused
        # after island one was cut; leaving base behind would make every retry of this call
        # fail with "already open" instead, and the PI would have to know what to delete.
        for kind, name in reversed(made):
            try:
                if kind == "ref":
                    _git(repo, "update-ref", "-d", name)
                else:
                    _git(repo, "branch", "-D", name)
            except E.CruxError:
                pass
        raise
    return {"anchor": qid, "repo": repo, "base": head, "run_branch": rb,
            "island_branches": islands}


def worktree_path(root, plan, hid):
    return os.path.join(worktrees_root(plan_repo(root, plan)), plan["anchor"], hid)


def add_worktree(root, plan, hid, parent=None):
    """A detached checkout for one attempt, cut from the commit it builds on.

    Detached rather than on a branch: an attempt is a ref, and a branch per attempt would
    leave a hundred of them in the PI's repository for a run that produced one answer."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    if parent:
        commit = rev_parse(repo, attempt_ref(qid, parent))
        if commit is None:
            raise E.CruxError(f"parent attempt {parent} has no ref {attempt_ref(qid, parent)}")
    else:
        commit = rev_parse(repo, base_ref(qid))
        if commit is None:
            raise E.CruxError(f"auto run for {qid} is not open: {base_ref(qid)} does not exist")
    path = os.path.join(worktrees_root(repo), qid, hid)
    if os.path.exists(path):
        raise E.CruxError(f"worktree for {hid} already exists at {path}")
    _git(repo, "worktree", "add", "--detach", path, commit)
    return path


def record_attempt(root, plan, hid):
    """Pin the attempt's commit under `refs/crux/auto/<qid>/<hid>` and return the sha.

    This is the step that makes the worktree disposable, and it is idempotent: recording the
    same commit twice is a no-op, while recording a DIFFERENT one is refused — a ref that
    silently moves is a run whose history cannot be read back."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    path = os.path.join(worktrees_root(repo), qid, hid)
    if not os.path.isdir(path):
        raise E.CruxError(f"no worktree for {hid} at {path}")
    sha = rev_parse(path, "HEAD")
    if sha is None:
        raise E.CruxError(f"worktree for {hid} at {path} has no commit to record")
    ref = attempt_ref(qid, hid)
    old = rev_parse(repo, ref)
    if old is not None and old != sha:
        raise E.CruxError(f"attempt {hid} is already recorded at {ref} ({old[:12]}), "
                          f"not {sha[:12]}")
    if old is None:
        _git(repo, "update-ref", ref, sha)
    return sha


def remove_worktree(root, plan, hid):
    """Throw the checkout away. True when there was one, False when there was not.

    Pruning first, and asking git what it actually has second, because "there is a directory
    at that path" and "git holds a worktree there" come apart in both directions: a killed run
    leaves a directory git never registered, and a directory deleted by hand leaves a
    registration with nothing behind it. Neither is an error the caller can act on — retention
    runs this for every attempt, and a run that dies because a cleanup found nothing to clean
    is a worse outcome than the leftover."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    path = os.path.join(worktrees_root(repo), qid, hid)
    _git(repo, "worktree", "prune")                  # registrations whose directory is gone
    if not os.path.isdir(path):
        return False
    real = os.path.realpath(path)
    known = any(os.path.realpath(b.get("worktree") or "") == real
                for b in _worktree_blocks(repo) if b.get("worktree"))
    if not known:
        return False                                 # a plain directory, not git's to remove
    _git(repo, "worktree", "remove", "--force", path)
    shutil.rmtree(path, ignore_errors=True)
    return True


# ------------------------------------------------------------------------- the frozen paths
def effective_frozen(root, plan):
    """The plan's frozen paths, plus the vault itself when it lives inside the repository.

    The notebook is frozen without the PI having to say so, and saying so would not be enough
    anyway: an attempt that edits its own verdict is not a result. A vault that IS the
    repository toplevel adds nothing — there is no separable notebook path to name."""
    out = list(plan.get("frozen") or [])
    repo = plan_repo(root, plan)
    rel = _rel_posix(repo, os.path.realpath(root))
    if rel != "." and not rel.startswith("../"):
        out.append(E._auto_norm_path(rel))
    return sorted(set(out))


def frozen_violations(root, plan, base_commit, head_commit):
    """Which frozen paths this attempt's commits touched. REPORTS ONLY.

    05.1 detects and names; closing the attempt `invalid-run` is 05.2's, and it is a verdict,
    which means it is the PI's rule rather than the driver's reflex.

    `--no-renames` is the whole guardrail. With rename detection on — git's default — an
    attempt that runs `git mv score.py scorer.py` produces a diff naming only the NEW path,
    the frozen entry `score.py` never appears, and the one thing this function exists to
    catch walks straight past it. Off, a rename is a delete and an add, and the delete of a
    frozen path is reported like any other."""
    repo = plan_repo(root, plan)
    frozen = effective_frozen(root, plan)
    out = _git(repo, "diff", "--name-only", "--no-renames", base_commit, head_commit)
    hits = set()
    for line in out.splitlines():
        p = line.strip().replace("\\", "/")
        if not p:
            continue
        for f in frozen:
            if p == f or p.startswith(f + "/"):
                hits.add(p)
                break
    return sorted(hits)


# ------------------------------------------------------------- the workspace and the manifest
def workspace_path(root, plan, hid):
    """`<repo>/<first writable root>/<hid>` — the one directory this attempt owns.

    Resolved against the REPOSITORY, not the worktree: a checkpoint written into a throwaway
    checkout dies with it, and the workspace has to outlive the worktree for retention to
    mean anything."""
    repo = plan_repo(root, plan)
    writable = plan.get("writable") or []
    if not writable:
        raise E.CruxError("flight plan names no writable root to put the workspace in")
    return os.path.join(repo, writable[0], hid)


def make_workspace(root, plan, hid):
    """The attempt's own directory, created. The failure here is reported in the plan's own
    vocabulary, never in the filesystem's.

    A plan reading `writable: train.py` passed every pre-flight gate and then died at the
    first attempt with a bare `NotADirectoryError: <repo>/train.py/<hid>` — a message that
    names a path nobody wrote and never says the word `writable`. `writable_problems` refuses
    that plan before a run opens; this is the backstop for every other way a writable root can
    fail to be a directory by the time an attempt needs one."""
    p = workspace_path(root, plan, hid)
    try:
        os.makedirs(p, exist_ok=True)
    except OSError as e:
        first = (plan.get("writable") or [None])[0]
        raise E.CruxError(f"the workspace for {hid} could not be created at {p}: "
                          f"{e.strerror or e}. The flight plan's first writable root is "
                          f"'{first}', and every attempt's workspace is made inside it, so it "
                          f"must be a directory in the repository")
    return p


def writable_problems(root, plan):
    """[{check, message}] — every writable root that exists and is NOT a directory.

    The one fact about `writable:` that no amount of reading the plan can settle, so it is
    checked against the repository instead. A root that does not exist yet is fine: the driver
    makes it. A root that is a FILE is the plan that reached attempt one of a hundred and
    forty and crashed there.

    Reported for every root rather than the first, because the manifest walks all of them —
    and because a PI who fixes one line only to be refused on the next has reviewed one plan
    twice."""
    out = []
    repo = plan_repo(root, plan)
    for w in (plan.get("writable") or []):
        p = os.path.join(repo, w)
        if os.path.exists(p) and not os.path.isdir(p):
            out.append({"check": "writable",
                        "message": f"flight plan writable root '{w}' is not a directory "
                                   f"({p}). Every attempt's workspace is made inside it, so a "
                                   f"file there is a run that dies at its first attempt"})
    return out


def shared_roots(root, plan):
    """Every writable root, absolute, in plan order. Shared because every attempt in flight
    can write into them — which is exactly why they need a manifest."""
    repo = plan_repo(root, plan)
    return [os.path.join(repo, w) for w in (plan.get("writable") or [])]


def _entry(abs_path, rel):
    """One manifest row. `lstat`, so a symlink is recorded as the link rather than as
    whatever it points at — the point is what this attempt did, not what is on the far end."""
    st = os.lstat(abs_path)
    return {"path": rel, "size": st.st_size, "mtime_ns": st.st_mtime_ns}


def _walk_roots(repo, roots, excluded):
    """Every file under the given repo-relative roots, minus the excluded subtrees.

    Symlinks are recorded and never followed: a link into a dataset would otherwise pull a
    terabyte into the manifest, and a link cycle would never finish."""
    ex = [e for e in (excluded or []) if e]

    def blocked(rel):
        return any(rel == e or rel.startswith(e + "/") for e in ex)

    files = []
    for rel_root in (roots or []):
        abs_root = os.path.join(repo, rel_root)
        if not os.path.isdir(abs_root) or os.path.islink(abs_root):
            continue
        for dirpath, dirnames, filenames in os.walk(abs_root, followlinks=False):
            drel = _rel_posix(repo, dirpath)
            keep = []
            for d in sorted(dirnames):
                sub = d if drel == "." else f"{drel}/{d}"
                full = os.path.join(dirpath, d)
                if blocked(sub):
                    continue
                if os.path.islink(full):
                    try:
                        files.append(_entry(full, sub))
                    except OSError:
                        pass
                    continue
                keep.append(d)
            dirnames[:] = keep
            for fn in sorted(filenames):
                frel = fn if drel == "." else f"{drel}/{fn}"
                if blocked(frel):
                    continue
                try:
                    files.append(_entry(os.path.join(dirpath, fn), frel))
                except OSError:
                    pass
    files.sort(key=lambda e: e["path"])
    return files


def write_manifest(root, plan, hid, exclude=()):
    """The BEFORE-picture of every shared root, written once, at the start of an attempt.

    Git cannot see these directories — they are scratch and datasets, not tracked files — so
    without this there is no way to answer "did this attempt write outside its own workspace".
    The attempt's own workspace is excluded because writing there is the whole point; a
    caller sequencing siblings in parallel passes THEIR workspaces in `exclude` for the same
    reason."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    roots = list(plan.get("writable") or [])
    ws = _rel_posix(repo, workspace_path(root, plan, hid))
    excluded = [ws] + sorted(exclude or ())
    doc = {"attempt": hid, "at": E.now(), "repo": repo, "roots": roots, "workspace": ws,
           "excluded": excluded, "files": _walk_roots(repo, roots, excluded), "rechecks": []}
    _write_json(manifest_path(root, qid, hid), doc)
    return doc


def recheck_manifest(root, plan, hid):
    """Walk the same roots again and report the difference from the before-picture.

    The recorded `files` are never rewritten: they are the BEFORE, and a re-check that
    refreshed them would answer "what changed since the last time anyone looked", which is
    not the question. So two re-checks after one change report that change twice — which is
    what makes the answer a fact about the attempt rather than about the polling."""
    qid = plan["anchor"]
    p = manifest_path(root, qid, hid)
    if not os.path.isfile(p):
        raise E.CruxError(f"no manifest for {hid} at "
                          f"{E.AUTO_DIR}/{qid}/{MANIFESTS_DIR}/{hid}.json")
    try:
        doc = json.loads(E.read(p))
    except ValueError as e:
        raise E.CruxError(f"malformed manifest for {hid}: {e}")
    repo = plan_repo(root, plan)
    now_files = _walk_roots(repo, doc.get("roots") or [], doc.get("excluded") or [])
    diff = E.manifest_diff(doc.get("files") or [], now_files)
    entry = {"at": E.now(), "added": diff["added"], "removed": diff["removed"],
             "changed": diff["changed"]}
    rechecks = doc.get("rechecks")
    if not isinstance(rechecks, list):
        rechecks = []
    rechecks.append(entry)
    doc["rechecks"] = rechecks
    _write_json(p, doc)
    return entry


# ------------------------------------------------------------------------------- retention
def apply_retention(root, plan, hid):
    """What survives the attempt. The workspace is the only thing this may delete.

    A workspace can hold sixty gigabytes of checkpoints, so `retention:` exists; what it must
    never decide is whether the run can still be READ afterwards, so the ref, the node, the
    metrics and the manifest are out of its reach by construction. The worktree goes under
    every setting: it is a checkout, and the commit it held is already in a ref."""
    retention = plan.get("retention")
    if retention not in E.AUTO_RETENTIONS:
        raise E.CruxError(f"flight plan retention must be one of "
                          f"{', '.join(E.AUTO_RETENTIONS)} (got '{retention}')")
    verdict = None
    try:
        n = E.Vault(root).nodes.get(hid)
    except Exception:
        n = None
    if n is not None:
        verdict = n["fm"].get("verdict") or None
    ws = workspace_path(root, plan, hid)
    drop = retention == "none" or (retention == "failed" and verdict == "supported")
    removed = False
    if drop and os.path.isdir(ws):
        shutil.rmtree(ws, ignore_errors=True)
        removed = not os.path.isdir(ws)
    worktree_removed = remove_worktree(root, plan, hid)
    return {"retention": retention, "verdict": verdict, "workspace": ws,
            "workspace_removed": removed, "worktree_removed": worktree_removed}


# ---------------------------------------------------------------------------- the scorer
class ScorerError(E.CruxError):
    """A scorer that did not honour its contract, with the clause it broke in `.check`.

    Four names rather than one "the scorer did not work": a PI who has to find out which of
    the four it was by reading a traceback will not run `auto check` twice."""
    def __init__(self, check, msg, started=True):
        super().__init__(msg)
        self.check = check
        self.started = started        # False when no process was ever created


def run_scorer(cmd, cwd, attempt, workspace, timeout, seed=None):
    """Run the PI's scorer once and return `(the metrics object, seconds)`.

    The contract, entire: stdout is ONE JSON object, stderr is free text, and the two
    variables the command needs are added to the inherited environment. No shell — the
    command is split by `shlex` and handed to the kernel, so nothing between the plan and the
    process can expand, glob or reinterpret it.

    `seed` (05.2) adds `CRUX_SEED`, which is how the confirmation re-scores the SAME commit
    at seeds the attempt itself never saw."""
    try:
        argv = shlex.split(cmd or "")
    except ValueError as e:
        raise ScorerError("scorer-exit", f"scorer command does not parse: {cmd} ({e})",
                          started=False)
    if not argv:
        raise ScorerError("scorer-exit", "scorer command is empty", started=False)
    env = dict(os.environ)
    env["CRUX_ATTEMPT"] = str(attempt or "")
    env["CRUX_WORKSPACE"] = str(workspace or "")
    if seed is not None:
        env["CRUX_SEED"] = str(seed)
    t0 = time.monotonic()
    try:
        r = _run(argv, cwd=cwd, env=env, timeout=timeout)
    except subprocess.TimeoutExpired:
        raise ScorerError("scorer-timeout",
                          f"scorer ran past scorer_timeout {float(timeout):g}s: {cmd}")
    except OSError as e:
        raise ScorerError("scorer-exit",
                          f"scorer cannot start: {cmd} ({e.strerror or e})", started=False)
    seconds = time.monotonic() - t0
    if r.returncode != 0:
        tail = (r.stderr or "").strip()[-STDERR_TAIL:] or "(empty)"
        raise ScorerError("scorer-exit",
                          f"scorer exited {r.returncode}: {cmd} — stderr tail: {tail}")
    out = (r.stdout or "").strip()
    try:
        obj = json.loads(out)
    except ValueError:
        obj = None
    if not isinstance(obj, dict):
        raise ScorerError("scorer-output",
                          f"scorer stdout is not one JSON object: {out[:STDOUT_HEAD] or '(empty)'}")
    return obj, seconds


def score_attempt(root, plan, hid, cwd=None, seed=None, dest=None):
    """Score one recorded attempt and write the object VERBATIM to results/<hid>/metrics.json.

    Verbatim, and written by the driver: the number that decides a verdict comes from the
    command's stdout, never from a file a worker could have rewritten. The file is written
    BEFORE the address is checked, so a scorer whose objective key is wrong still leaves the
    evidence on disk for the PI to look at.

    `dest` (05.2) sends the document somewhere else — `results/<hid>/confirm/<seed>/` — so a
    confirmation run never touches the attempt's own `metrics.json`, which stays the
    byte-exact object the scorer printed at seed 0."""
    if cwd is None:
        cwd = worktree_path(root, plan, hid)
    if not os.path.isdir(cwd):
        raise E.CruxError(f"no worktree for {hid} at {cwd}")
    obj, _ = run_scorer(plan["scorer"], cwd, hid, workspace_path(root, plan, hid),
                        plan["scorer_timeout"], seed=seed)
    where = dest or f"{E.RESULTS_DIR}/{hid}/{E.METRICS_FILE}"
    out = os.path.join(root, *str(where).split("/"))
    _write_json(out, obj)
    try:
        E.metrics_value(obj, plan["address"], where)
    except E.AddressError as e:
        raise ScorerError("scorer-address",
                          f"objective '{plan['address']}' does not resolve in {where}: {e}")
    return obj


def _scorer_own_paths(repo, cmd):
    """The repository paths the scorer COMMAND itself names, relative to the repo.

    Everything else in a checkout is the candidate's program and may be taken away to see
    whether the scorer notices. The scorer's own file may not: a probe that deletes the
    scorer is measuring whether a missing program can be executed, which is a different and
    much less interesting question."""
    keep = set()
    try:
        argv = shlex.split(cmd or "")
    except ValueError:
        return keep
    for a in argv:
        p = a if os.path.isabs(a) else os.path.join(repo, a)
        if not os.path.exists(p):
            continue
        rel = _rel_posix(repo, os.path.realpath(p))
        if rel != "." and not rel.startswith("../"):
            keep.add(rel)
    return keep


def probe_scorer_responds(root, plan, base_value, repo=None):
    """Does the scorer READ the candidate's checkout, or does it score the baseline every
    time? Writes nothing the caller can see.

    `{responds, detail}`, where `responds` is True, False, or None for NOT ESTABLISHED — a
    probe that could not be set up has learned nothing, and reporting that as a pass is the
    one outcome that makes a check worthless. Only False is a problem.

    This is the probe that was missing on 2026-09-21, and its absence is the most expensive
    defect this driver has had. A flight plan named `score.py` by ABSOLUTE path; `score.py`
    does `sys.path.insert(0, HERE)` with HERE its own directory, so `import train` resolved to
    the main repository's baseline `train.py` and never to the candidate's. Every attempt of a
    thirty-attempt run would have scored the baseline. `auto check` could not see it: its one
    scorer run printed `0.0`, and `0.0` reads exactly like "the baseline scores zero by
    construction". A candidate with seventy-five changed lines scored byte-identical to the
    baseline before anybody thought to check by hand.

    The probe is a deliberate perturbation, because responsiveness is not a property of the
    scorer's text — it is a property of the pair (scorer, checkout) and only an experiment
    settles it. A throwaway worktree at HEAD has its tracked files taken away, everything the
    scorer command itself names excepted, and the scorer is run in it. A scorer that reads the
    checkout then either fails or returns a different number, and BOTH count as responsive: a
    scorer that crashes because the program is gone has proved it was reading the program. The
    one answer that fails is the objective coming back bit-for-bit what the intact checkout
    gave, which means the candidate's code was never on the path at all.

    `base_value` is the objective from the unperturbed run the caller already paid for, so
    this costs one extra scorer run and not two."""
    def out(responds, detail):
        return {"responds": responds, "detail": detail}

    repo = repo or plan_repo(root, plan)
    keep = _scorer_own_paths(repo, plan["scorer"])
    wt = tempfile.mkdtemp(prefix="crux_auto_probe_")
    shutil.rmtree(wt, ignore_errors=True)         # git wants to create it itself
    ws = tempfile.mkdtemp(prefix="crux_auto_probe_ws_")
    try:
        try:
            _git(repo, "worktree", "add", "--detach", wt, "HEAD")
        except E.CruxError as e:
            return out(None, f"the probe checkout could not be made: {e}")
        try:
            tracked = _git(wt, "ls-files", "-z").split("\0")
        except E.CruxError as e:
            return out(None, f"the probe checkout could not be listed: {e}")
        removed = 0
        for rel in tracked:
            rel = rel.strip()
            if not rel or rel in keep:
                continue
            # A kept path may be a directory the scorer named; nothing under it is touched.
            if any(rel.startswith(k + "/") for k in keep):
                continue
            try:
                os.unlink(os.path.join(wt, *rel.split("/")))
                removed += 1
            except OSError:
                pass
        if not removed:
            # Nothing was takeable, so nothing was tested. Saying so is the honest answer; a
            # probe that reports "responsive" after perturbing nothing is worse than no probe.
            return out(None, "the checkout holds no tracked file the scorer does not name, "
                             "so there was nothing to take away")
        try:
            obj, _s = run_scorer(plan["scorer"], wt, plan["baseline"], ws,
                                 plan["scorer_timeout"])
        except ScorerError as e:
            return out(True, f"the scorer failed on the perturbed checkout, so it reads "
                             f"it: {e}")
        try:
            value = E.metrics_value(obj, plan["address"], "the scorer's output on the probe")
        except E.AddressError as e:
            return out(True, f"the objective stopped resolving on the perturbed checkout, "
                             f"so the scorer reads it: {e}")
        if value != base_value:
            return out(True, f"{plan['address']} moved {base_value} -> {value} when "
                             f"{removed} tracked file(s) were taken away")
        return out(False,
                   f"the scorer does not read the candidate: with {removed} tracked file(s) "
                   f"taken out of a throwaway checkout it still returned "
                   f"{plan['address']} = {value}, the same number the intact checkout gave. "
                   f"Every attempt of this run would score the baseline. The usual cause is a "
                   f"scorer named by ABSOLUTE path that resolves the program against its own "
                   f"directory rather than the working directory it is run in — name the "
                   f"scorer by a path relative to the repository, and have it import what is "
                   f"beside it in the checkout it was started in")
    finally:
        try:
            _git(repo, "worktree", "remove", "--force", wt)
        except E.CruxError:
            pass
        shutil.rmtree(wt, ignore_errors=True)
        shutil.rmtree(ws, ignore_errors=True)


def probe_agents(root, plan, repo=None):
    """One row per command of the plan's list: `{command, probe, reachable, seconds, detail}`.

    A misspelled agent command is the cheapest failure to find and the most expensive to find
    late — found at run open it costs nothing, found after the first reservation it has burned
    a hypothesis number that can never be handed out again.

    The probe is the command with the placeholders taken out plus `agent_probe`, so it sends
    no prompt and therefore spends NO model call: `env=None`, so the child inherits the
    environment and gets no `CRUX_*` variable at all. Reachable means the program STARTED and
    exited inside the timeout — the exit code is not read, because not every CLI answers
    `--version` and refusing a plan over that is a check about a flag."""
    plan_cwd = repo or plan_repo(root, plan)
    rows = []
    for command in E.auto_command_list(plan):
        row = {"command": command, "probe": [], "reachable": False, "seconds": None,
               "detail": ""}
        try:
            argv = E.auto_probe_argv(command, plan["agent_probe"])
        except ValueError as e:
            row["detail"] = (f"the agent command does not parse under shlex: "
                             f"{command} ({e})")
            rows.append(row)
            continue
        row["probe"] = argv
        if not argv:
            row["detail"] = "the agent command is empty"
            rows.append(row)
            continue
        t0 = time.monotonic()
        try:
            r = _run(argv, cwd=plan_cwd, env=None, timeout=plan["agent_probe_timeout"])
        except OSError as e:
            row["detail"] = (f"the agent command cannot start: {command} "
                             f"({e.strerror or e})")
        except subprocess.TimeoutExpired:
            row["seconds"] = time.monotonic() - t0
            row["detail"] = (f"the agent command ran past agent_probe_timeout "
                             f"{float(plan['agent_probe_timeout']):g}s: {command}")
        else:
            row["reachable"] = True
            row["seconds"] = time.monotonic() - t0
            row["detail"] = f"exited {r.returncode}"
        rows.append(row)
    return rows


def auto_check(root, path, static=False):
    """`auto check`, with the scorer dry-run added. `--static` is 05.0's verb, unchanged.

    A flight plan that passes every engine check and then cannot produce a number is a plan
    that fails at attempt one of a hundred and forty. So the default runs the PI's scorer
    ONCE, in the repository, against a throwaway workspace, and writes nothing anywhere —
    the baseline's own metrics file is the PI's, and a dry run does not get to touch it.

    It runs the scorer a SECOND time, against a deliberately perturbed checkout, because a
    scorer that produces a number is not yet a scorer that produces the CANDIDATE's number —
    see `probe_scorer_responds` for the run that was lost to the difference. `responds` is
    reported alongside `ran` for the same reason `ran` exists: they are two facts and a reader
    should not have to infer one from the other."""
    res = E.auto_check(root, path)
    if static:
        return res
    res["repo"] = None
    res["scorer"] = {"ran": False, "cmd": None, "cwd": None, "address": None,
                     "value": None, "seconds": None, "responds": None}
    res["agents"] = []                  # present on EVERY non-static return, the early ones
                                        # included, so a reader never has to test for the key
    if res["problems"]:
        return res                      # a plan that fails statically is not dry-run
    plan = E.load_flight_plan(root, path)
    try:
        repo = plan_repo(root, plan)
    except E.CruxError as e:
        res["problems"].append({"check": "repo", "message": str(e)})
        res["ok"] = False
        return res                      # and no further process of any kind
    res["repo"] = repo
    res["problems"].extend(writable_problems(root, plan))
    res["scorer"].update({"cmd": plan["scorer"], "cwd": repo, "address": plan["address"]})
    ws = tempfile.mkdtemp(prefix="crux_auto_dry_")
    t0 = time.monotonic()
    try:
        obj, seconds = run_scorer(plan["scorer"], repo, plan["baseline"], ws,
                                  plan["scorer_timeout"])
    except ScorerError as e:
        # `ran` is a fact about the machine, not an intention: a command that could not be
        # found never became a process, and a report saying it ran sends the PI looking at the
        # scorer's own code for a fault that is in the plan's `scorer:` line.
        res["scorer"]["ran"] = getattr(e, "started", True)
        if res["scorer"]["ran"]:
            res["scorer"]["seconds"] = time.monotonic() - t0
        res["problems"].append({"check": e.check, "message": str(e)})
    else:
        res["scorer"]["ran"] = True
        res["scorer"]["seconds"] = seconds
        try:
            res["scorer"]["value"] = E.metrics_value(obj, plan["address"], "scorer output")
        except E.AddressError as e:
            res["problems"].append(
                {"check": "scorer-address",
                 "message": f"objective '{plan['address']}' does not resolve in the "
                            f"scorer's output: {e}"})
    finally:
        shutil.rmtree(ws, ignore_errors=True)
    # Only when there IS a number to compare against: perturbing a checkout to see whether a
    # scorer that already failed fails differently answers nothing.
    if res["scorer"]["value"] is not None:
        probe = probe_scorer_responds(root, plan, res["scorer"]["value"], repo)
        res["scorer"]["responds"] = probe["responds"]
        if probe["responds"] is False:
            res["problems"].append({"check": "scorer-responds", "message": probe["detail"]})
    # The probe runs whether or not the scorer added a problem: two faults in one plan are two
    # findings, and reporting one at a time turns one review into two.
    res["agents"] = probe_agents(root, plan, repo)
    if res["agents"] and not any(r["reachable"] for r in res["agents"]):
        res["problems"].append(
            {"check": "agent-reach",
             "message": "no agent command in the flight plan is reachable: "
                        + "; ".join(f"{r['command']} ({r['detail']})"
                                    for r in res["agents"])})
    res["ok"] = not res["problems"]
    return res


# ============================================================== 05.2: the driver loop (§5–§8)
# One process, no threads: up to `parallel_total` workers in flight, each held as a `Popen`
# and polled every 50 ms, while scoring, filing and every git call happen synchronously on the
# way through. Vault writes are serialised behind the one lock, so concurrency touches no file
# two attempts share — which is also what keeps `META.md` from being torn by two attempts
# finishing at once.
class _Stopped(Exception):
    """The run has stopped. Raised from wherever the stop was decided so the unwind is one
    path rather than a return value threaded through nine steps."""


def _charge_hours(ctx):
    """Move the wall clock since the last charge onto the run's hours budget.

    Charged in HOURS, which is what `budget_hours:` is written in, and only while this driver
    is actually running — a night spent dead is not the PI's compute."""
    now = time.monotonic()
    ctx["state"]["budget"]["hours"]["used"] += (now - ctx["t0"]) / 3600.0
    ctx["t0"] = now


def _append_ledger(path, line):
    """Append one ledger line, flushed and fsynced. APPEND-ONLY by construction: nothing here
    ever opens the file for writing, so every earlier byte survives every later event.

    A file whose last write was torn gets a newline in front of this one, so the torn tail
    stays its own unparseable line rather than swallowing the next event."""
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tail = ""
    if os.path.isfile(path) and os.path.getsize(path) > 0:
        with open(path, "rb") as f:
            f.seek(-1, os.SEEK_END)
            tail = f.read(1).decode("utf-8", "replace")
    with open(path, "a", encoding="utf-8", newline="\n") as f:
        if tail and tail != "\n":
            f.write("\n")
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def _record(ctx, event, fields, work=None):
    """Do the work, log it, and rewrite the state — all inside ONE hold of the vault lock.

    The ledger line and the state file describe the same act, so they are written in the same
    critical section as the act itself. That is what makes `state.json` readable mid-flight:
    every event that happened is in the ledger, and the count in the state matches it.

    `fields` may be a callable, which is handed the work's result — a `closed` event carries
    the verdict `cmd_close` derived, and the driver has no way to know it in advance."""
    if event not in E.AUTO_LEDGER_EVENTS:
        raise E.CruxError(f"'{event}' is not an autopilot ledger event")
    root, qid, st = ctx["root"], ctx["qid"], ctx["state"]
    with vault_lock(root, "auto-run", wait=ctx["lock_wait"]):
        result = work() if work else None
        f = fields(result) if callable(fields) else fields
        _append_ledger(ledger_path(root, qid), E.auto_ledger_line(event, f))
        st["events"] = int(st.get("events") or 0) + 1
        _charge_hours(ctx)
        st["updated"] = E.now()
        _write_json(state_path(root, qid), st)
    return result


def _save_state(ctx):
    """`state.json`, rewritten whole, under the lock. Never half a document: through a
    temporary file and one `os.replace`, because the file a crash is most likely to be
    writing is the file resume most needs to read."""
    with vault_lock(ctx["root"], "auto-run", wait=ctx["lock_wait"]):
        _charge_hours(ctx)
        ctx["state"]["updated"] = E.now()
        _write_json(state_path(ctx["root"], ctx["qid"]), ctx["state"])


def _crash(ctx, phase):
    """The test-only hook. A real kill — `SIGKILL`, or `SIGTERM` where the platform has no
    `SIGKILL` — the instant `phase` is first recorded, so the resume under test recovers the
    failure that actually happens. See the module docstring."""
    if ctx.get("crash_at") == phase:
        os.kill(os.getpid(), signal.SIGKILL if hasattr(signal, "SIGKILL") else signal.SIGTERM)


def _fl(ctx, hid):
    return ctx["state"]["in_flight"][hid]


def _wk(ctx, hid):
    """The transient side-table for one attempt: its worktree, workspace, brief, commit and
    proposal. Deliberately NOT in `state.json` — that file has a pinned key set a reader can
    trust, and none of this survives a crash anyway. Resume rebuilds it from disk."""
    return ctx["work"].setdefault(hid, {})


def _seen(ctx):
    """{event: {attempt ids}} from the ledger as it stood when this driver started.

    Read once, so an id this run closes is never in it — and a RESUMED id whose `closed`,
    `confirm` or `island-best` event is already on disk never gets a second one."""
    if ctx.get("seen") is None:
        seen = {}
        p = ledger_path(ctx["root"], ctx["qid"])
        if os.path.isfile(p):
            for line in E.read(p).splitlines():
                try:
                    o = json.loads(line)
                except ValueError:
                    continue
                if isinstance(o, dict) and o.get("attempt"):
                    seen.setdefault(o.get("event"), set()).add(o["attempt"])
        ctx["seen"] = seen
    return ctx["seen"]


def _log_tail(ws, name=WORKER_LOG, since=0):
    """The last of an agent's own output, for the failure the PI reads in the morning.

    `name` (05.3) is the log to read: the worker's by default, and the closer's or the
    steward's when one of those is the agent that failed. One reader, so a tail cannot be
    quoted three subtly different ways.

    `since` is the byte offset this try's own output starts at. `_spawn` opens the log in
    APPEND mode, so one file accumulates every try of an attempt: without an offset, try 1's
    rate-limit line is still inside the 500-character window when try 2 — on a DIFFERENT
    command — fails for an unrelated reason, and the cooldown lands on a healthy command.
    Read in binary so the offset is the byte count the caller measured, then decode with
    `errors="replace"` because the bytes are a child's."""
    p = os.path.join(ws, name)
    if not os.path.isfile(p):
        return "(empty)"
    try:
        with open(p, "rb") as f:
            if since:
                f.seek(int(since))
            data = f.read()
    except (IOError, OSError, ValueError):
        return "(empty)"
    return data.decode("utf-8", "replace")[-OUTPUT_TAIL:].strip() or "(empty)"


def _log_size(ws, name=WORKER_LOG):
    """How many bytes an agent's log already holds, so the next try can scan only its own."""
    try:
        return os.path.getsize(os.path.join(ws, name))
    except (IOError, OSError):
        return 0


def _agent_file(path):
    """The text an agent left in its workspace, or None. The ONE reader for every such file.

    `E.read` opens utf-8 with no `errors=`, so a single byte of a model's output that is not
    valid UTF-8 raises `UnicodeDecodeError` — a `ValueError`, which `auto_run`'s loop does not
    catch, so the whole run would die on one bad byte with no event and no stop record. A
    steward never stops a run and neither does a closer: this reads with `errors="replace"`
    and turns every I/O failure into None, which the proposal validators already report as
    `closer-missing` / `steward-missing` / `proposal-missing`."""
    if not path or not os.path.isfile(path):
        return None
    try:
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    except (IOError, OSError):
        return None


# ------------------------------------------------------- 05.3: the walk and the cooldown (§B, §C)
# `agent:` and `agent_failover:` are ONE ordered command list, and one try walks it once. A
# command that cannot become a process is a `failover`, which charges neither a retry nor a
# model call — a command that never started cannot have spent a token, and waiting cannot fix
# a misspelling. A command whose failed try reads as a provider limit goes on COOLDOWN, held
# as an absolute wall-clock stamp in `state.json` so a resume does not forget it.

def _cooling(ctx, command):
    """Is `command` inside its cooldown window right now?

    The stamp is absolute and in `E.now()`'s format, so the comparison is a lexicographic one
    on iso strings — which is exactly why the stamp is absolute: a remaining-seconds count
    would be wrong the moment the driver was killed and resumed an hour later."""
    rec = (ctx["state"].get("agents") or {}).get(command)
    if not rec or not rec.get("cooling_until"):
        return False
    return E.now() < rec["cooling_until"]


def _cool(ctx, role, command):
    """Put one command on cooldown and say so in the ledger."""
    plan, st = ctx["plan"], ctx["state"]
    secs = float(plan["agent_cooldown"])
    # E.now()'s own format, plus a microsecond fraction, so the two stamps still compare
    # lexicographically and the engine's clock and the driver's stay one clock. The fraction
    # is what makes a sub-second window mean anything at all: `E.now()` is truncated to the
    # second, so a stamp truncated the same way is already in the past the moment it is
    # written. It errs on the side of cooling a fraction of a second too long, which is the
    # harmless direction — the point of a cooldown is to come back later, not exactly then.
    at = time.time() + secs
    until = (time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(at))
             + ".%06d" % int((at % 1) * 1000000))
    prior = ((st.get("agents") or {}).get(command) or {}).get("hits") or 0
    st.setdefault("agents", {})[command] = {"cooling_until": until, "hits": prior + 1}
    _record(ctx, "cooldown", {"role": role, "command": command, "until": until,
                              "seconds": secs,
                              "detail": f"the output tail matched a rate-limit pattern; "
                                        f"{command} is cooling until {until}"})


def _wait_for_cooldown(ctx, commands):
    """Wait until the earliest cooldown lapses. It does NOT abort.

    A rolling provider limit is the interruption this whole feature exists to survive, so the
    driver waits it out rather than throwing the night away. `auto_stop` is re-evaluated on
    EVERY pass: a blocking wait would suspend `budget_hours` accounting for as long as a hung
    agent lives, and a thirty-minute cooldown under a one-minute budget would overrun by
    twenty-nine. A night lost entirely to limits therefore ends on the `budget` stop.

    Live workers are polled — `.poll()`, which reaps — but an exit is NOT dispatched here: the
    main loop owns that, and finishing an attempt from inside another attempt's start would
    re-enter the whole step machine."""
    st, plan = ctx["state"], ctx["plan"]
    while True:
        _charge_hours(ctx)
        stop = E.auto_stop(st, plan)
        if stop:
            _stop_run(ctx, stop)
        for _hid, pr in list(ctx["procs"].items()):
            if pr is not None:
                pr.poll()
        if any(not _cooling(ctx, c) for c in commands):
            return
        time.sleep(POLL)


def _walk_detail(ctx):
    """"every agent command failed to start: …", from the last walk's own failures."""
    return ("every agent command failed to start: "
            + "; ".join(f"{c} ({d})" for c, d in (ctx.get("walk_failures") or [])))


def _agent_walk(ctx, role, brief, env, log_path, cwd, hid=None):
    """One try, walking the command list once: `(p, command)`, or None when none started.

    Every try starts at the HEAD of the list, so the preferred command comes back by itself
    the moment its window lapses — there is no probe schedule and nothing to reset. Within one
    try each command is attempted at most once, and a cooling command is skipped rather than
    attempted.

    The model call is charged HERE, at the moment a child is actually spawned, and nowhere
    else: a walk is ONE try over several commands, so a failover charges neither a retry nor a
    call."""
    commands = E.auto_command_list(ctx["plan"])
    while True:
        if commands and all(_cooling(ctx, c) for c in commands):
            _wait_for_cooldown(ctx, commands)
            continue
        failures = []
        ctx["walk_failures"] = failures
        for pos, c in enumerate(commands):
            if _cooling(ctx, c):
                # A command walked past because it is cooling is a failover too: the ledger
                # reads `cooldown` then `failover`, which is the whole story of a rolling
                # limit in two lines. It is not a start failure, so it says so.
                rec = (ctx["state"].get("agents") or {}).get(c) or {}
                _record(ctx, "failover",
                        {"role": role, "command": c, "reason": "cooldown",
                         "detail": f"{c} is cooling until {rec.get('cooling_until')}",
                         "next": next((o for o in commands[pos + 1:]
                                       if not _cooling(ctx, o)), None)})
                continue
            try:
                argv = E.auto_agent_argv(c, role, brief)
            except ValueError as e:
                failures.append((c, f"the agent command does not parse under shlex: "
                                    f"{c} ({e})"))
            else:
                if not argv:
                    failures.append((c, "the flight plan names no agent command"))
                else:
                    try:
                        p = _spawn(argv, cwd, env, log_path)
                    except OSError as e:
                        failures.append((c, f"worker cannot start: {c} "
                                            f"({e.strerror or e})"))
                    else:
                        ctx["state"]["budget"]["model_calls"]["used"] += 1
                        return (p, c)
            nxt = next((o for o in commands[pos + 1:] if not _cooling(ctx, o)), None)
            _record(ctx, "failover", {"role": role, "command": c, "reason": "start",
                                      "detail": failures[-1][1], "next": nxt})
        return None


# ------------------------------------------------------------------------- one attempt (§5)
def _start_attempt(ctx, island):
    """S1–S5: select a parent, reserve an id, cut a worktree, write the brief, start a worker."""
    root, plan, st, qid = ctx["root"], ctx["plan"], ctx["state"], ctx["qid"]
    rows = [r for r in E.auto_island_attempts(root, plan, island) if r["score"] is not None]
    # every in-flight attempt's parent is a VIRTUAL visit, so a lineage already being worked
    # stops looking cheap to the next selection (05.0 built the argument for this)
    virtual = tuple(f["parent"] for f in st["in_flight"].values() if f["island"] == island)
    parent = E.puct_select(rows, st["c_puct"], plan["direction"], virtual)

    hid = reserve_id(root, qid, island=island, parent=parent)
    st["in_flight"][hid] = {"island": island, "parent": parent, "from": None,
                            "phase": "reserved", "worker_tries": 0, "scorer_tries": 0,
                            "pid": None, "failure": None, "provider": False,
                            "started": E.now()}
    _record(ctx, "attempt-reserved", {"attempt": hid, "island": island, "parent": parent})
    _crash(ctx, "reserved")

    fl = _fl(ctx, hid)
    fl["from"] = st["base"] if parent == plan["baseline"] \
        else rev_parse(ctx["repo"], attempt_ref(qid, parent))
    fl["phase"] = "drafted"
    _save_state(ctx)
    _crash(ctx, "drafted")

    w = _wk(ctx, hid)
    w["wt"] = add_worktree(root, plan, hid,
                           parent=None if parent == plan["baseline"] else parent)
    w["ws"] = make_workspace(root, plan, hid)
    write_manifest(root, plan, hid)
    try:
        # the brief is assembled for the ISLAND, not for the parent's question: the first
        # attempt on an Explore island builds on the baseline, which sits under the anchor
        w["brief"] = E.auto_brief_text(
            E.auto_brief(root, parent, island=island, islands=list(st["islands"]),
                         steward=((st.get("steward") or {}).get("guidance") or []),
                         # the run's own counter — the same one `auto_stop` reads, so the
                         # worker and the stop condition cannot disagree about what is left
                         budget=st["budget"]["attempts"]))
    except E.CruxError as e:
        _abandon(ctx, hid, "brief")
        _stop_run(ctx, {"reason": "abort", "axis": None, "attempt": None,
                        "detail": f"the brief for {hid} could not be assembled: {e}"})
    with open(os.path.join(w["ws"], BRIEF_NAME), "w", encoding="utf-8") as f:
        f.write(w["brief"])
    _worker_try(ctx, hid)


def _worker_try(ctx, hid):
    """S5: one walk of the plan's command list, and nothing else.

    The proposal is deleted first, so a retry can never read the previous try's answer. Every
    command is `shlex.split` and handed to the kernel — no shell between the PI's plan and the
    process — with `{agent}` and `{brief}` substituted in any argv element and eight variables
    added. The model call is charged inside the walk, at the spawn.

    A walk that started NOTHING is not retried: one try already attempted every command, so
    there is nothing left to try and waiting cannot fix a misspelling. The run stops `abort`
    instead, naming each command and its reason."""
    plan, st = ctx["plan"], ctx["state"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    ws, wt = w["ws"], w["wt"]
    proposal = os.path.join(ws, PROPOSAL_NAME)
    try:
        os.unlink(proposal)
    except OSError:
        pass
    fl["worker_tries"] += 1
    # `_spawn` APPENDS to worker.log, so this try's own output starts here. `_fail` scans from
    # this offset and no earlier: an earlier try's rate-limit line must never cool the command
    # a later try ran.
    w["log_from"] = _log_size(ws, WORKER_LOG)
    env = dict(os.environ)
    env.update({"CRUX_ATTEMPT": hid, "CRUX_WORKSPACE": ws, "CRUX_WORKTREE": wt,
                "CRUX_BRIEF": os.path.join(ws, BRIEF_NAME), "CRUX_PROPOSAL": proposal,
                "CRUX_SEED": "0", "CRUX_RUN": str(plan["run"] or ""),
                "CRUX_AGENT": E.AUTO_AGENTS[0]})
    res = _agent_walk(ctx, E.AUTO_AGENTS[0], w["brief"], env,
                      os.path.join(ws, WORKER_LOG), wt, hid=hid)
    if res is None:
        return _stop_run(ctx, {"reason": "abort", "axis": None, "attempt": None,
                               "detail": _walk_detail(ctx)})
    p, c = res
    ctx["procs"][hid] = p            # _spawn does NOT register its child; every caller does
    w["command"] = c
    fl["pid"] = p.pid
    _record(ctx, "worker-started", {"attempt": hid, "pid": p.pid, "try": fl["worker_tries"]})


def _rescue_commit(ctx, hid):
    """Commit what the worker left uncommitted in its own worktree, on its behalf. The new
    head, or None when there was nothing to rescue or the rescue would preserve a cheat.

    A worker that does the work and exits 0 without committing used to lose ALL of it: the
    attempt failed `no-commit`, retention removed the worktree `--force`, and the changes were
    gone — while the retention rule that permits the removal reasons that "the commit it held
    is already in a ref", which is exactly the thing that is not true here. Committing is
    bookkeeping, not science, and the brief now says so in as many words; where the engine can
    do the bookkeeping itself rather than hope, it does.

    The two integrity checks are re-run on what is about to be committed, and a rescue that
    would trip either is REFUSED rather than recorded. A worker that both forgot to commit and
    touched a frozen path is a double fault, and the safe direction is not to launder it into
    a scorable commit.

    Built out of PLUMBING — `write-tree`, `commit-tree`, `update-ref` — and never `git
    commit`. The driver is held to a list of git verbs it may not run (see the purity section
    of the suite) and the porcelain ones are on it, because a driver that can `commit`,
    `checkout` or `reset` can rewrite a history it is only supposed to read. None of these
    three touches a file in the working tree: they write an object and move a detached HEAD,
    which is the same thing `record_attempt` already does one step later."""
    root, plan, qid = ctx["root"], ctx["plan"], ctx["qid"]
    w, fl = _wk(ctx, hid), _fl(ctx, hid)
    wt = w.get("wt")
    if w.get("recorded") or not wt or not os.path.isdir(wt):
        return None
    if not fl.get("from") or rev_parse(wt, "HEAD") != fl["from"]:
        return None                      # it committed after all; there is nothing to rescue
    try:
        if not _git(wt, "status", "--porcelain"):
            return None                  # it changed nothing; there is nothing to preserve
        _git(wt, "add", "-A")
        tree = _git(wt, "write-tree")
        head = _git(wt, "commit-tree", tree, "-p", fl["from"], "-m",
                    f"crux autopilot: work rescued from attempt {hid}, which exited without "
                    f"recording it")
        _git(wt, "update-ref", "HEAD", head)
    except E.CruxError:
        return None                      # a rescue that cannot happen is not a run-ending fault
    if head is None or head == fl.get("from"):
        return None
    if frozen_violations(root, plan, fl["from"], head):
        return None
    if E.auto_manifest_violations(recheck_manifest(root, plan, hid),
                                  plan["writable"] or [""],
                                  list(reservations(root, qid))):
        return None
    w["head"] = head
    return head


def _fail(ctx, hid, reason, detail):
    """A failure that is the MACHINE's: retried while `retries` and the call budget allow, and
    otherwise carried into the close as the finding that explains an `invalid-run`.

    On the LAST try, whatever the worker left on disk is committed on its behalf before the
    attempt is carried into the close — see `_rescue_commit`. The failure still stands and the
    attempt still closes `invalid-run` when it named no hypothesis; what changes is that the
    program and its number survive, which is the whole of "preserve and measure everything,
    grade only what carries a claim"."""
    plan, st = ctx["plan"], ctx["state"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    _record(ctx, "worker-failed", {"attempt": hid, "reason": reason, "detail": detail,
                                   "try": fl["worker_tries"]})
    # 05.3. Only a FAILED try's log is ever scanned: an agent that merely mentions a rate
    # limit in a transcript it then commits over must not be able to move the driver. The
    # cooldown lands before the retry decision, so the retry's own walk skips the cooling
    # command and the ledger reads `cooldown` then `failover`, in that order.
    if w.get("command") and E.auto_rate_limited(_log_tail(w["ws"], since=w.get("log_from") or 0)):
        _cool(ctx, E.AUTO_AGENTS[0], w["command"])
        # ...and this try was lost to the PROVIDER rather than to the worker. Recorded on
        # `fl`, not on the side-table, so it reaches `state.json` and survives a resume. One
        # matcher decides the cooldown, the failover and this — a second one would drift.
        fl["provider"] = True
    if (not w.get("recorded")
            and fl["worker_tries"] <= plan["retries"]
            and st["budget"]["model_calls"]["used"] < st["budget"]["model_calls"]["total"]):
        _record(ctx, "retry", {"attempt": hid, "step": "worker",
                               "try": fl["worker_tries"] + 1, "reason": reason})
        return _worker_try(ctx, hid)
    # The last try is over, so whatever is on disk is all there will ever be. Rescue it BEFORE
    # the attempt is carried into the close, because `_step_retire` removes the worktree under
    # every retention setting and takes an uncommitted program with it.
    _rescue_commit(ctx, hid)
    fl["failure"] = f"{reason}: {detail}"
    fl["phase"] = "committed"
    w["reason"], w["exhausted"] = reason, True
    _save_state(ctx)
    _crash(ctx, "committed")
    _finish(ctx, hid, w.get("stage") or "record")


def _violate(ctx, hid, kind, paths, detail):
    """A failure that is the WORKER's act — a frozen path, a shared root, a proposal outside
    the schema. Never retried: the same agent would simply repeat it at cost."""
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    fl["failure"] = f"{kind}: {detail}"
    fl["phase"] = "committed"
    w["reason"] = kind
    _record(ctx, "violation", {"attempt": hid, "kind": kind, "paths": paths,
                               "detail": detail})
    _crash(ctx, "committed")
    _finish(ctx, hid, w.get("stage") or "record")


def _after_worker(ctx, hid, rc):
    """W1–W2, then the three checks. `rc` is taken as 0 on resume: a worker the driver never
    saw exit left a commit or it did not, and the commit is the fact that matters."""
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    ctx["procs"].pop(hid, None)
    if rc != 0:
        return _fail(ctx, hid, "worker-exit",
                     f"worker exited {rc} — output tail: {_log_tail(w['ws'])}")
    head = rev_parse(w["wt"], "HEAD")
    if head == fl["from"]:
        return _fail(ctx, hid, "no-commit", "the worker exited 0 and left no commit")
    return _worker_checks(ctx, hid, head)


def _worker_checks(ctx, hid, head):
    """W3–W5: the frozen diff, the manifest over the shared roots, and the proposal."""
    root, plan, qid = ctx["root"], ctx["plan"], ctx["qid"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    w["head"] = head
    paths = frozen_violations(root, plan, fl["from"], head)
    if paths:
        return _violate(ctx, hid, "frozen", paths,
                        f"the commit touches frozen path(s): {', '.join(paths)}")
    paths = E.auto_manifest_violations(recheck_manifest(root, plan, hid),
                                       plan["writable"] or [""],
                                       list(reservations(root, qid)))
    if paths:
        return _violate(ctx, hid, "manifest",
                        paths, f"the attempt changed shared-root path(s) outside every "
                               f"workspace: {', '.join(paths)}")
    raw = _agent_file(os.path.join(w["ws"], PROPOSAL_NAME))
    prop = w["prop"] = E.auto_proposal(raw, plan)
    if not prop["ok"]:
        if prop["retry"]:
            return _fail(ctx, hid, prop["reason"], prop["detail"])
        return _violate(ctx, hid, "proposal", [], prop["detail"])
    fl["phase"] = "committed"
    _record(ctx, "worker-done",
            dict(attempt=hid, commit=head, warnings=prop.get("warnings") or []))
    _crash(ctx, "committed")
    _finish(ctx, hid, w.get("stage") or "record")


# ---------------------------------------------------------------- S6–S13, and where resume joins
_FINISH_STEPS = ("record", "file", "score", "close", "post")


_UNSCORABLE_KINDS = ("frozen", "manifest", "filing")


def _integrity_failed(fl):
    """Is this a failure whose commit must NOT be measured?

    `frozen` and `manifest` are integrity: the commit exists, but a number taken from it would
    be a reward for touching frozen data or for writing into ground another attempt shares.

    `filing` is the third and is not integrity — it is a refusal from the engine part-way
    through the three acts that write the node, so the node is in a state no verdict is a
    reading of, and the run is already aborting behind it. Measuring it would spend a scorer
    run to decorate a record nobody will trust.

    Read off `fl["failure"]`, which `_violate` and `_step_file` write as `"<kind>: <detail>"`
    and which lives in `state.json` — so a resumed attempt reaches the same answer as a fresh
    one even though the side-table that held the kind died with the driver. That is the whole
    reason it is read from here and not from `_wk`."""
    f = fl.get("failure") or ""
    return any(f.startswith(k + ": ") for k in _UNSCORABLE_KINDS)


def _scorable(ctx, hid):
    """May this attempt's commit be scored?

    The rule, and it is one rule for both halves of the run: PRESERVE AND MEASURE EVERYTHING,
    GRADE ONLY WHAT CARRIES A CLAIM. A commit exists and it passed both integrity checks, so
    it gets measured — whatever the worker's REPORT looked like. A faulty report is not a
    reason to throw away a measurement that was already taken; that is `3751491`'s argument
    one step later, and it used to cost an attempt its number for a claim one word over a cap.

    The two exclusions are integrity, not form, and they are why this is not simply "is there
    a commit". An attempt that touched a frozen path or wrote into ground another attempt
    shares has a commit whose number would be a reward for the cheat, so it is never scored.

    Keyed on the ref rather than on the worktree: the ref is the commit of record, it survives
    the worktree being thrown away, and it is what makes this answer the same before and after
    a crash."""
    if _integrity_failed(_fl(ctx, hid)):
        return False
    return rev_parse(ctx["repo"], attempt_ref(ctx["qid"], hid)) is not None


def _no_claim(ctx, hid):
    """Did this attempt report a hypothesis at all?

    Asked of the NODE, not of the driver's side-table. `auto_proposal` hands back a `claim`
    only when there is a usable one, and `_step_file` writes either that claim or the
    AUTO_NO_CLAIM placeholder — so the node carries the answer for exactly the four faults
    that leave nothing to grade (missing, unparseable, absent, over-cap) and for the attempts
    that never produced a proposal at all. The side-table would answer the same for a FRESH
    attempt and wrongly for a resumed one, because it is rebuilt from disk and holds no
    proposal for a worker whose driver has died."""
    return E.auto_is_no_claim(ctx["root"], hid)


def _finish(ctx, hid, stage="record"):
    """Everything after the worker, entered at whichever step the evidence on disk says is
    next. One path, so a resumed attempt and a fresh one cannot diverge."""
    k = _FINISH_STEPS.index(stage)
    root, plan = ctx["root"], ctx["plan"]
    fl = _fl(ctx, hid)
    if k <= 0:
        _step_record(ctx, hid)
    if k <= 1:
        _step_file(ctx, hid)
    if k <= 2 and _scorable(ctx, hid):
        _step_score(ctx, hid)
    metrics = E.load_metrics(root, hid)
    value = _address_value(plan, metrics, hid)
    if k <= 3:
        verdict = _step_close(ctx, hid, metrics, value)
        _step_counters(ctx, hid, verdict, value)
    else:
        verdict = E.Vault(root).get(hid)["fm"].get("verdict")
        if hid not in _seen(ctx).get("closed", set()):
            _record(ctx, "closed", {"attempt": hid, "verdict": verdict, "value": value,
                                    "island": fl["island"], "task": None})
            _step_counters(ctx, hid, verdict, value)
    if hid not in _seen(ctx).get("confirm", set()):
        _step_confirm(ctx, hid, verdict, value)
    if hid not in _seen(ctx).get("island-best", set()):
        _step_pointer(ctx, hid, verdict, value)
    _step_retire(ctx, hid)
    pending = ctx.pop("pending_stop", None)
    if pending:                     # a filing refusal: the attempt is closed, now the run ends
        _stop_run(ctx, pending)


def _address_value(plan, metrics, hid):
    """The objective out of a metrics document, or None. None is a fact, not an error: the
    ticks already say `[-]`, and the verdict follows from them."""
    if metrics is None:
        return None
    try:
        return E.metrics_value(metrics, plan["address"],
                               f"{E.RESULTS_DIR}/{hid}/{E.METRICS_FILE}")
    except E.AddressError:
        return None


def _step_record(ctx, hid):
    """S6. Pin the attempt's commit under its ref — the step that makes the worktree
    disposable. A failed attempt that still produced a commit is recorded too: the evidence is
    worth more than the tidiness."""
    w, fl = _wk(ctx, hid), _fl(ctx, hid)
    head = w.get("head")
    if head is None and w.get("wt") and os.path.isdir(w["wt"]):
        head = w["head"] = rev_parse(w["wt"], "HEAD")
    if head and head != fl["from"]:
        record_attempt(ctx["root"], ctx["plan"], hid)


def _step_file(ctx, hid):
    """S7. The four acts the plan's approval covers, `hypothesize` · `approve-null` ·
    `test --to running`, in ONE hold of the lock — so no node is ever left at status `idea`,
    which is the only status `unrun_children` counts.

    An attempt that failed or cheated is filed too, with `AUTO_NO_CLAIM` where the claim
    should be: a run's record is every attempt it made, not every attempt that worked."""
    root, plan, st, qid = ctx["root"], ctx["plan"], ctx["state"], ctx["qid"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    prop = w.get("prop") or {}
    claim = prop.get("claim") or E.AUTO_NO_CLAIM.format(hid=hid,
                                                        reason=w.get("reason") or "unknown")
    spec = E.auto_node_spec(plan, claim, prop.get("controls") if prop.get("ok") else [])
    island, parent = fl["island"], fl["parent"]
    pn = E.Vault(root).nodes.get(parent)
    # `builds_on` is refused across questions (05.0), and the first attempt on an island
    # builds on the baseline, which sits under the anchor. The parent is still recorded — in
    # reserved.json and in the ledger — and the worktree is still cut from its commit.
    builds_on = parent if (pn is not None and pn.parent == island) else None

    def act():
        if hid not in E.Vault(root).nodes:
            E.cmd_hypothesize(root, spec["title"], parent=island,
                              verifiables=spec["verifiables"], neutral=spec["neutral"],
                              rule=spec["rule"], rule_m=spec["rule_m"], null=spec["null"],
                              fails_if=spec["fails_if"], discriminates=spec["discriminates"],
                              builds_on=builds_on, nid=hid, claim=spec["claim"])
        E.cmd_approve_null(root, hid)
        if E.Vault(root).get(hid).status in ("idea", "staged"):
            E.cmd_test(root, hid, to="running")

    try:
        _record(ctx, "node-filed",
                lambda _r: {"attempt": hid, "island": island, "parent": parent,
                            "builds_on": builds_on, "title": spec["title"]},
                work=act)
    except E.CruxError as e:
        stop = {"reason": "abort", "axis": None, "attempt": None,
                "detail": f"the engine refused to file {hid}: {e}"}
        if hid not in E.Vault(root).nodes:
            _abandon(ctx, hid, "filing")
            _stop_run(ctx, stop)
        # The three acts share one lock hold but are not one transaction: a refusal from
        # `approve-null` or `test` lands with the node already written, and an abandoned id
        # that IS a node would stay at status `idea` — the one status `unrun_children` counts.
        # So the attempt is carried into the close instead, and the run aborts after it.
        fl["failure"] = f"filing: {e}"
        w["reason"] = "filing"
        ctx["pending_stop"] = stop
    set_reservation_state(root, qid, hid, "materialized")


def _step_score(ctx, hid):
    """S8. The scorer, retried while it is the MACHINE that failed. A scorer whose output
    parses but whose objective does not resolve is NOT retried: the document is on disk, and
    the ticks decide from there.

    Reached now with a failure ALREADY set — an attempt whose report was faulty is still
    measured — so the first failure is the one kept. It is the one that explains the close,
    and overwriting "the claim ran to 412 words" with a scorer's message would leave the
    findings describing the wrong fault."""
    root, plan = ctx["root"], ctx["plan"]
    fl = _fl(ctx, hid)
    fl["phase"] = "scored"
    _save_state(ctx)
    _crash(ctx, "scored")
    while True:
        fl["scorer_tries"] += 1
        try:
            score_attempt(root, plan, hid, seed=0)
        except ScorerError as e:
            if e.check in E.AUTO_SCORER_RETRY_CHECKS and fl["scorer_tries"] <= plan["retries"]:
                _record(ctx, "retry", {"attempt": hid, "step": "scorer",
                                       "try": fl["scorer_tries"] + 1, "reason": e.check})
                continue
            if fl["failure"] is None:
                fl["failure"] = f"{e.check}: {e}"
            if e.check in E.AUTO_SCORER_RETRY_CHECKS:
                _wk(ctx, hid)["exhausted"] = True
                _wk(ctx, hid)["reason"] = e.check
        break
    metrics = E.load_metrics(root, hid)
    if metrics is not None:
        _record(ctx, "scored", {"attempt": hid, "seed": 0,
                                "value": _address_value(plan, metrics, hid)})


def _closer_try(ctx, hid, ticks):
    """Invoke `crux-close` through the same command list, and read what it proposed.

    Synchronous inside phase `closed`, and awaited by POLLING rather than by a timeout: a
    blocking wait would suspend `budget_hours` accounting for as long as a hung agent lives.
    No phase is added to `AUTO_PHASES` — the crash fixture iterates that tuple — so a kill
    during the closer resumes through 05.2's R2: the metrics are on disk, `_step_close` runs
    again, and the closer is invoked (and charged) again.

    Only a failure to START is retried. Missing, unparseable, malformed, contradicting,
    over-cap and non-zero-exit are the agent's own act, and the same agent handed the same
    brief would repeat it. `cwd` is the REPOSITORY, never the attempt's worktree: on resume
    that worktree may already be gone, and everything the closer needs reaches it through
    `CRUX_RESULTS` and the brief."""
    root, plan, st = ctx["root"], ctx["plan"], ctx["state"]
    key = PROC_CLOSE.format(hid=hid)

    def bad(reason, detail):
        return {"ok": False, "reason": reason, "detail": detail,
                "ticks": {}, "findings": None, "report": None}

    # The brief assembly is INSIDE the failure contract. `auto_close_brief` refuses a
    # tick/checks length mismatch with a CruxError, and the property this function states is
    # absolute: in every failure case the attempt closes on the engine's own vector. An
    # exception here would instead unwind `_step_close` and take the run with it.
    try:
        ws = make_workspace(root, plan, hid)
        brief = E.auto_close_brief_text(E.auto_close_brief(root, hid, plan, ticks))
        with open(os.path.join(ws, CLOSE_BRIEF_NAME), "w", encoding="utf-8") as f:
            f.write(brief)
    except (E.CruxError, IOError, OSError) as e:
        return bad("closer-brief", f"the close brief for {hid} could not be assembled: {e}")
    prop_path = os.path.join(ws, CLOSE_PROPOSAL_NAME)
    env = dict(os.environ)
    env.update({"CRUX_AGENT": "crux-close", "CRUX_ATTEMPT": hid, "CRUX_WORKSPACE": ws,
                "CRUX_BRIEF": os.path.join(ws, CLOSE_BRIEF_NAME),
                "CRUX_PROPOSAL": prop_path,
                "CRUX_RESULTS": os.path.join(root, E.RESULTS_DIR, hid)})

    tries = 0
    while True:
        tries += 1
        try:
            os.unlink(prop_path)
        except OSError:
            pass
        log_from = _log_size(ws, CLOSER_LOG)      # this try's own output starts here
        res = _agent_walk(ctx, "crux-close", brief, env,
                          os.path.join(ws, CLOSER_LOG), ctx["repo"])
        if res is None:
            if tries <= plan["retries"]:
                _record(ctx, "retry", {"attempt": hid, "step": "closer",
                                       "try": tries + 1, "reason": "closer-start"})
                continue
            return bad("closer-start", _walk_detail(ctx))
        p, c = res
        ctx["procs"][key] = p
        while p.poll() is None:
            _charge_hours(ctx)
            stop = E.auto_stop(st, plan)
            if stop:
                try:
                    _kill_tree(p)
                except OSError:
                    pass
                ctx["procs"].pop(key, None)
                # The stop itself fires at the top of the next loop pass; this attempt closes
                # on the engine's own vector first, so nothing the scorer measured is lost.
                return bad("stop", stop.get("detail"))
            time.sleep(POLL)
        ctx["procs"].pop(key, None)
        if p.returncode != 0:
            tail = _log_tail(ws, CLOSER_LOG, since=log_from)
            if E.auto_rate_limited(tail):
                _cool(ctx, "crux-close", c)
            return bad("closer-exit", f"the closer exited {p.returncode} — "
                                      f"output tail: {tail}")
        return E.auto_close_proposal(_agent_file(prop_path), plan, ticks)


def _step_report(ctx, hid, report):
    """Write `results/<hid>/report.md` and link it under the node's `## Artifacts`.

    The DRIVER writes it, never the engine — the engine never writes anything under
    `results/`. Idempotent both halves, so a resumed close is a no-op. Called only from inside
    `_step_close`'s single lock hold, and BEFORE `cmd_close`, so `artifact_warnings` sees the
    link and `validate` reports no 'files but no report is linked' problem."""
    root = ctx["root"]
    d = os.path.join(root, E.RESULTS_DIR, hid)
    os.makedirs(d, exist_ok=True)
    with open(os.path.join(d, E.AUTO_REPORT_FILE), "w", encoding="utf-8") as f:
        f.write(str(report or "")[:E.AUTO_REPORT_BYTES])
    return E.auto_link_report(root, hid, f"{E.RESULTS_DIR}/{hid}/{E.AUTO_REPORT_FILE}")


def _step_close(ctx, hid, metrics, value):
    """S9. Tick from the metrics, let the closer propose the rest, then `cmd_close` — the
    unchanged close path, reached by a new caller. The driver supplies the ticks and never a
    verdict.

    Every closer failure closes the attempt on the ENGINE's own vector, with the fixed-template
    findings and report, and is deliberately NOT `invalid-run` for that reason alone: the run
    happened and the scorer's document is on disk, and a reporting agent's flakiness must not
    be able to manufacture a streak of invalid runs that trips the `abort` stop.

    An attempt that reported NO CLAIM is the other half of that rule and cuts the other way.
    It is measured like any other — the number is on the ledger and the program is at its ref
    — but the fact that it stated no hypothesis is reported to `cmd_close`, which withholds
    the reading of the vector. The driver names the fact; the engine still names the verdict."""
    root, plan, st = ctx["root"], ctx["plan"], ctx["state"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    fl["phase"] = "closed"
    _save_state(ctx)
    _crash(ctx, "closed")
    ticks = E.cmd_auto_ticks(root, hid, metrics)
    prop = _closer_try(ctx, hid, ticks) if plan["closer"] else None
    if prop is not None:
        _record(ctx, "closer", {"attempt": hid, "ok": prop["ok"],
                                "reason": prop["reason"], "detail": prop["detail"]})
    if prop and prop["ok"]:
        merged = E.auto_merge_ticks(ticks, prop["ticks"])
        findings, report = prop["findings"], prop["report"]
    else:
        merged = ticks
        findings = E.auto_findings(plan["address"], value, ticks, fl["failure"])
        report = E.auto_report_text(plan, hid, value, ticks, fl["failure"])
    if merged != ticks:
        # The engine writes the vector it was handed; the driver may not call `render_doc`.
        E.cmd_auto_ticks(root, hid, metrics, ticks=merged)

    def act():
        _step_report(ctx, hid, report)
        out = E.cmd_close(root, hid, metric=repr(value) if value is not None else None,
                          findings=findings, no_claim=_no_claim(ctx, hid))
        tid = None
        if w.get("exhausted"):
            # an attempt that burned every retry is an exception, and an exception belongs in
            # the frontier where somebody will see it — not in a log nobody reads
            if E.AUTO_TASK_CATEGORY not in E.task_categories(root):
                E.cmd_task_categories(root, add=E.AUTO_TASK_CATEGORY)
            tid, _fn = E.cmd_task_add(root, f"autopilot attempt {hid} exhausted its retries: "
                                            f"{w.get('reason')}",
                                      E.AUTO_TASK_CATEGORY, refs=[hid])
            st["tasks"]["exceptions"].append(tid)
        return (out, tid)

    verdict, _task = _record(ctx, "closed",
                             lambda r: {"attempt": hid, "verdict": r[0], "value": value,
                                        "island": fl["island"], "task": r[1]},
                             work=act)
    return verdict


def _step_counters(ctx, hid, verdict, value):
    """S10. The two counters a stop reads: invalid runs in a row, and the island's stall.

    Stalling is measured by SCORE over the attempts that measured something, not by verdict: a
    Climb toward a bar refutes every attempt until the last one, and a verdict-based rule
    would call that a stall on the second try."""
    plan, st = ctx["plan"], ctx["state"]
    fl = _fl(ctx, hid)
    island = fl["island"]
    isl = st["islands"][island]
    # An attempt the PROVIDER killed is NEUTRAL to the streak: it neither advances it nor
    # clears it. `abort_invalid_runs` exists to catch a worker behaving badly, and an outage
    # or a session limit is not a worker act — the first run of one search ended on this stop
    # with 25 attempts of budget left, five workers killed by a limit and a run of 529s and
    # every one of them counted against the worker. Clearing the streak would be the opposite
    # error: an outage in the middle of three genuinely bad attempts would hide them.
    #
    # Only what `auto_rate_limited` positively identifies is excused. A worker that exits
    # non-zero because the PROGRAM is broken is a worker act and still counts, which is why
    # `worker-exit` is not excluded wholesale.
    if not fl.get("provider"):
        st["consecutive_invalid"] = (st["consecutive_invalid"] + 1
                                     if verdict == "invalid-run" else 0)
    if verdict != "invalid-run" and E.auto_improves(value, isl["seen_score"],
                                                    plan["direction"]):
        isl["seen_score"], isl["stall"] = value, 0
    else:
        isl["stall"] += 1
    if plan["stall_attempts"] > 0 and isl["stall"] >= plan["stall_attempts"]:
        st["stalls"] += 1
        isl["stall"] = 0
        _record(ctx, "stall", {"island": island, "attempts": plan["stall_attempts"],
                               "count": st["stalls"]})
        if st["stalls"] == 1:
            # ONE self-escalation per run: Climb raises c_puct to the Explore value — recorded
            # in state.json, so selection stays reproducible from the file — and Explore asks
            # for the steward 05.3 brings. A second stall ends the run.
            if plan["mode"] == "climb":
                st["c_puct"] = E.AUTO_C_PUCT["explore"]
            else:
                st["steward_requested"] = True
            st["escalated"] = True
            _record(ctx, "escalated", {"mode": plan["mode"], "c_puct": st["c_puct"],
                                       "steward_requested": st["steward_requested"]})


def _step_confirm(ctx, hid, verdict, value):
    """S11. The confirmation: the SAME commit re-scored at `replicates` fresh seeds, none of
    them the attempt's own seed 0, all of which must cross the bar.

    A single crossing of the bar is the result most likely to be noise, which is exactly what
    the plan's null says out loud. A seed that misses is a failed confirmation, never a
    changed verdict: the run simply carries on."""
    root, plan, st = ctx["root"], ctx["plan"], ctx["state"]
    if verdict != "supported" or not E.auto_crosses(value, plan["bar"], plan["direction"]):
        return
    seeds, values = [], []
    for s in range(1, int(plan["replicates"]) + 1):
        where = f"{E.RESULTS_DIR}/{hid}/confirm/{s}/{E.METRICS_FILE}"
        p = os.path.join(root, *where.split("/"))
        v = None
        try:
            obj = json.loads(E.read(p)) if os.path.isfile(p) \
                else score_attempt(root, plan, hid, seed=s, dest=where)
            v = E.metrics_value(obj, plan["address"], where)
        except (ValueError, E.CruxError):
            v = None
        seeds.append(s)
        values.append(v)
    passed = bool(values) and all(E.auto_crosses(v, plan["bar"], plan["direction"])
                                  for v in values)
    _record(ctx, "confirm", {"attempt": hid, "seeds": seeds, "values": values,
                             "passed": passed})
    if passed:
        st["confirmed"] = hid


def _step_pointer(ctx, hid, verdict, value):
    """S12. The island's best, moved by compare-and-swap. These branches, `open_run`'s and
    `promote`'s are the ONLY `refs/heads/` writes this module makes."""
    plan, st, repo, qid = ctx["plan"], ctx["state"], ctx["repo"], ctx["qid"]
    island = _fl(ctx, hid)["island"]
    isl = st["islands"][island]
    if verdict != "supported" or not E.auto_improves(value, isl["best_score"],
                                                     plan["direction"]):
        return
    branch = isl["branch"]
    old = rev_parse(repo, "refs/heads/" + branch)
    new = rev_parse(repo, attempt_ref(qid, hid))
    if new is None:
        return
    _record(ctx, "island-best",
            {"attempt": hid, "island": island, "branch": branch, "from": old, "to": new,
             "score": value},
            work=lambda: _git(repo, "update-ref", "refs/heads/" + branch, new, old or ""))
    isl["pointer"], isl["best"], isl["best_score"] = new, hid, value
    if E.auto_improves(value, st["best"]["score"], plan["direction"]):
        st["best"] = {"id": hid, "score": value}


def _step_retire(ctx, hid):
    """S13. Retention over the workspace, the worktree thrown away, the attempt closed out."""
    st = ctx["state"]
    apply_retention(ctx["root"], ctx["plan"], hid)
    # §2 pins `materialized` right after the node is filed, but that write sits OUTSIDE the
    # lock and no resume rule re-enters `_step_file` once the node exists — so a kill in that
    # window would leave a closed attempt reading `reserved` for good. Every closed attempt
    # passes here exactly once, which is where it heals.
    if hid in E.Vault(ctx["root"]).nodes:
        try:
            set_reservation_state(ctx["root"], ctx["qid"], hid, "materialized")
        except E.CruxError:
            pass
    st["in_flight"].pop(hid, None)
    ctx["work"].pop(hid, None)
    ctx["procs"].pop(hid, None)
    if hid not in st["closed"]:
        st["closed"].append(hid)
    st["budget"]["attempts"]["used"] = len(st["closed"])
    _save_state(ctx)


def _abandon(ctx, hid, reason):
    """Give an id back to nobody: the worker killed, the worktree gone, the reservation marked
    `abandoned` so it is never handed out again. A gap in the numbering costs nothing."""
    root, plan, qid, st = ctx["root"], ctx["plan"], ctx["qid"], ctx["state"]
    p = ctx["procs"].pop(hid, None)
    if p is not None:
        try:
            _kill_tree(p)
        except OSError:
            pass
    phase = (st["in_flight"].get(hid) or {}).get("phase") or "reserved"
    try:
        remove_worktree(root, plan, hid)
    except E.CruxError:
        pass
    try:
        set_reservation_state(root, qid, hid, "abandoned")
    except E.CruxError:
        pass
    st["in_flight"].pop(hid, None)
    ctx["work"].pop(hid, None)
    _record(ctx, "abandoned", {"attempt": hid, "phase": phase, "reason": reason})


# ------------------------------------------------------------------- resume (§6), and the stop
def _reconcile(ctx):
    """Reconcile `state.json` against the five facts on disk, rather than trusting it: the
    kill may have landed between the fact and the write.

    An id that is only in `reserved.json` is reconciled too — it may have been reserved by a
    driver that died before it could record the reservation in its own state."""
    root, qid, st = ctx["root"], ctx["qid"], ctx["state"]
    res = reservations(root, qid)
    ids = set(st["in_flight"])
    for hid, rec in res.items():
        if rec.get("state") == "reserved" and hid not in st["closed"]:
            ids.add(hid)
    for hid in sorted(ids, key=E.natkey):
        if hid not in st["in_flight"]:
            rec = res.get(hid) or {}
            st["in_flight"][hid] = {"island": rec.get("island") or qid,
                                    "parent": rec.get("parent"), "from": None,
                                    "phase": "reserved", "worker_tries": 0, "scorer_tries": 0,
                                    "pid": None, "failure": None, "provider": False,
                                    "started": rec.get("at") or E.now()}
        _resume_one(ctx, hid)


def _resume_one(ctx, hid):
    """R0–R6 for one half-finished attempt, first rule that holds."""
    root, plan, qid, repo = ctx["root"], ctx["plan"], ctx["qid"], ctx["repo"]
    fl, w = _fl(ctx, hid), _wk(ctx, hid)
    w["wt"] = worktree_path(root, plan, hid)
    w["ws"] = workspace_path(root, plan, hid)
    brief = os.path.join(w["ws"], BRIEF_NAME)
    w["brief"] = E.read(brief) if os.path.isfile(brief) else ""
    w["reason"] = "resume"

    # R0 — a worker the dead driver started may still be running. It owns this worktree, so
    # nothing may be concluded about the attempt until it is gone.
    pid = fl.get("pid")
    if pid and ctx.get("prior_host") == HOST:
        while _pid_alive(pid):
            time.sleep(POLL)

    n = E.Vault(root).nodes.get(hid)
    if n is not None:
        if n["fm"].get("verdict"):
            return _finish(ctx, hid, "post")                            # R1
        if E.load_metrics(root, hid) is not None:
            return _finish(ctx, hid, "close")                           # R2
        # R3. It enters at `score` unconditionally now, and `_finish`'s own `_scorable` gate
        # decides. It used to branch on `fl["failure"]`, which was right only while the fresh
        # path skipped scoring on any failure at all; now that the fresh path measures a
        # commit whose REPORT was faulty, a resumed attempt branching the old way would be
        # graded differently from an identical fresh one — and one path for both is the
        # property `_finish` exists to hold. One rule, read from `state.json`, in both places.
        return _finish(ctx, hid, "score")                              # R3
    head = rev_parse(repo, attempt_ref(qid, hid))
    if head is not None:                                                # R4
        w["stage"] = "file"
        # The ref is the commit of record (§2), and `_finish` from `file` never records one
        # again. So a RETRYABLE failure here — a proposal the dead driver never got to read —
        # is EXHAUSTED rather than retried: a second worker run would leave the node and its
        # metrics describing a commit the ref does not name.
        w["recorded"] = True
        return _worker_checks(ctx, hid, head)
    if (os.path.isdir(w["wt"]) and fl.get("from")
            and rev_parse(w["wt"], "HEAD") != fl["from"]):              # R5
        w["stage"] = "record"
        return _after_worker(ctx, hid, 0)
    _abandon(ctx, hid, "resume")                                        # R6


def _stop_subject(ctx):
    """The attempt the run's one task is about: the run's best, else the best-scoring closed
    attempt that measured something, else the last one closed, else none at all."""
    root, plan, st = ctx["root"], ctx["plan"], ctx["state"]
    if st["best"]["id"]:
        return st["best"]["id"]
    v = E.Vault(root)
    rows = []
    for hid in st["closed"]:
        n = v.nodes.get(hid)
        if n is None or n["fm"].get("verdict") == "invalid-run":
            continue
        try:
            rows.append((hid, float(E.resolve_address(root,
                                                      f"{hid}#{plan['address']}")["value"])))
        except (E.CruxError, TypeError, ValueError):
            continue
    if rows:
        return sorted(rows, key=lambda r: (r[1] if plan["direction"] == "min" else -r[1],
                                           E.natkey(r[0])))[0][0]
    return st["closed"][-1] if st["closed"] else None


def _stop_run(ctx, stop):
    """End the run: kill what is in flight, record the stop, and file the run's one task.

    The task is filed HERE rather than at run open because `experiment` is a computed
    category — a task is one when it says what it concluded about a hypothesis — and a task
    filed before the first attempt could only be an ordinary chore. Filed at the stop it lands
    in `crux task review`, where accepting it pairs with the merge decision the PI makes in
    the morning."""
    root, st, qid = ctx["root"], ctx["state"], ctx["qid"]
    for hid in sorted(list(st["in_flight"]), key=E.natkey):
        _abandon(ctx, hid, "stop")
    st["stop"] = {"reason": stop["reason"], "axis": stop.get("axis"),
                  "detail": stop.get("detail"), "attempt": stop.get("attempt"),
                  "at": E.now()}

    def file_tasks():
        if E.AUTO_TASK_CATEGORY not in E.task_categories(root):
            E.cmd_task_categories(root, add=E.AUTO_TASK_CATEGORY)
        title = f"autopilot run on {qid} stopped: {stop['reason']}"
        h = _stop_subject(ctx)
        if h:
            concl = E.Vault(root).get(h)["fm"].get("verdict")
            tid, _fn = E.cmd_task_add(root, title, E.AUTO_TASK_CATEGORY, refs=[qid],
                                      hypothesis_refs=[(h, concl)])
            E.cmd_task_done(root, tid, outputs=[f"[[{h}]]"])
        else:
            tid, _fn = E.cmd_task_add(root, title, E.AUTO_TASK_CATEGORY, refs=[qid])
            E.cmd_task_done(root, tid, outputs=[f"[[{qid}]]"])
        st["tasks"]["run"] = tid
        if stop["reason"] == "abort":
            xid, _x = E.cmd_task_add(root, f"autopilot run on {qid} aborted: "
                                           f"{stop.get('detail')}",
                                     E.AUTO_TASK_CATEGORY, refs=[qid])
            st["tasks"]["exceptions"].append(xid)
        return tid

    _record(ctx, "stop",
            lambda tid: {"reason": stop["reason"], "axis": stop.get("axis"),
                         "detail": stop.get("detail"), "attempt": stop.get("attempt"),
                         "task": tid},
            work=file_tasks)
    raise _Stopped()


# ------------------------------------------------------------------------ the run itself (§4)
def _base_scorer_check(ctx):
    """Run the PI's scorer once against the base commit, in a THROWAWAY worktree, writing
    nothing under `results/`. Returns the failure text, or None.

    A scorer that cannot produce a number on the commit the run starts from is a run that
    fails at attempt one of a hundred and forty — and the throwaway checkout is what keeps the
    PI's own working tree clean while finding that out.

    It then asks the harder question, the one `probe_scorer_responds` exists for: does that
    number have anything to do with the CANDIDATE? `auto run` gates on the STATIC engine check
    and never calls `autopilot.auto_check`, so a PI who approves a plan and runs it without
    ever typing `crux auto check` would otherwise reach this point with the scorer's
    responsiveness untested — which is exactly how a thirty-attempt run came to score the
    baseline thirty times. It costs one more scorer run, once, at run open."""
    root, plan = ctx["root"], ctx["plan"]
    remove_worktree(root, plan, BASE_WORKTREE)
    tmp = tempfile.mkdtemp(prefix="crux_auto_base_")
    try:
        wt = add_worktree(root, plan, BASE_WORKTREE)
        obj, _s = run_scorer(plan["scorer"], wt, plan["baseline"], tmp,
                             plan["scorer_timeout"], seed=0)
        value = E.metrics_value(obj, plan["address"], "the scorer's output at run open")
    except (ScorerError, E.AddressError) as e:
        return str(e)
    finally:
        remove_worktree(root, plan, BASE_WORKTREE)
        shutil.rmtree(tmp, ignore_errors=True)
    probe = probe_scorer_responds(root, plan, value, ctx["repo"])
    if probe["responds"] is False:
        return probe["detail"]
    return None


def _open_base(ctx, ap):
    """Adopt the run's base commit, or cut it plus the run and island branches."""
    root, plan, st, qid = ctx["root"], ctx["plan"], ctx["state"], ctx["qid"]
    base = rev_parse(ctx["repo"], base_ref(qid))
    if base is None:
        base = open_run(root, plan)["base"]
    st["base"] = base
    for i in st["islands"]:
        st["islands"][i]["pointer"] = base
    _record(ctx, "run-opened", {"run": st["run"], "mode": plan["mode"],
                                "c_puct": st["c_puct"], "islands": list(plan["islands"]),
                                "plan_hash": st["plan_hash"], "base": base})


# ------------------------------------------------------------------ 05.3: the steward (§H)
# It reads the RUN's own record — the ledger, the island table, the budget — and proposes
# standing guidance or ONE new island under the anchor, up to `island_cap`. It is advice: a
# steward that cannot start, fails, returns nothing or proposes outside the schema is logged
# and the run carries on, because a run that dies for want of advice is worse than a run
# without it. No attempt is ever lost to it.

def _seen_events(ctx):
    """The run's ledger objects, oldest first, unparseable lines skipped.

    The engine never reads `ledger.jsonl` — that file is the driver's — so the driver reads it
    and hands the objects over, the same read `_seen` already does."""
    out = []
    pth = ledger_path(ctx["root"], ctx["qid"])
    if os.path.isfile(pth):
        for line in E.read(pth).splitlines():
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if isinstance(o, dict):
                out.append(o)
    return out


def _steward_due(ctx):
    """Is the steward due right now? Every clause, and no fifth reason.

    On a Climb plan the switch is legal and the steward simply never runs: a run may be
    moved from Climb to Explore mid-flight, so the switch being on is not a mistake to
    refuse."""
    plan, st = ctx["plan"], ctx["state"]
    if not plan["steward"] or plan["mode"] != "explore":
        return False
    if ctx.get("steward_proc") is not None:
        return False
    if st["budget"]["model_calls"]["used"] >= st["budget"]["model_calls"]["total"]:
        return False
    if st["confirmed"] is not None or st["stop"] is not None:
        return False
    if st.get("steward_requested"):
        return True
    every = plan["steward_every"]
    last = ((st.get("steward") or {}).get("last_closed") or 0)
    return every > 0 and len(st["closed"]) - last >= every


def _steward_try(ctx):
    """Spawn the steward. Asynchronous: it blocks nothing, and a brief assembled while it runs
    simply predates its advice.

    Its scratch lives at `auto/<qid>/steward/<n>/`, NEVER under a writable root: a steward
    workspace under `<writable>/…` would show up as a shared-root write in every in-flight
    attempt's manifest recheck and close honest attempts `invalid-run`. `auto/<qid>/manifests/`
    sets the precedent. `cwd` is the repository, for the same reason the closer's is."""
    root, plan, st, qid = ctx["root"], ctx["plan"], ctx["state"], ctx["qid"]
    # Every command cooling: the walk would sit in `_wait_for_cooldown`, which polls without
    # dispatching exits, so the driver would stall for up to `agent_cooldown` while finished
    # workers went unclosed. For the WORKER walk that wait is unavoidable — nothing can start.
    # For the steward it is pure loss: advice can wait a pass. `invocations`/`last_closed` are
    # left untouched, so it comes due again on the next pass.
    commands = E.auto_command_list(plan)
    if commands and all(_cooling(ctx, c) for c in commands):
        return
    n = ((st.get("steward") or {}).get("invocations") or 0) + 1
    ws = os.path.join(root, E.AUTO_DIR, qid, STEWARD_DIR, str(n))
    os.makedirs(ws, exist_ok=True)
    brief = E.auto_steward_brief_text(
        E.auto_steward_brief(root, plan, st, _seen_events(ctx)))
    with open(os.path.join(ws, STEWARD_BRIEF_NAME), "w", encoding="utf-8") as f:
        f.write(brief)
    prop_path = os.path.join(ws, STEWARD_PROPOSAL_NAME)
    try:
        os.unlink(prop_path)
    except OSError:
        pass
    env = dict(os.environ)
    env.update({"CRUX_AGENT": "crux-auto-steward", "CRUX_WORKSPACE": ws,
                "CRUX_BRIEF": os.path.join(ws, STEWARD_BRIEF_NAME),
                "CRUX_PROPOSAL": prop_path})
    res = _agent_walk(ctx, "crux-auto-steward", brief, env,
                      os.path.join(ws, STEWARD_LOG), ctx["repo"])
    # The window closes whether it ran or not: a steward that cannot start must not be retried
    # on every pass of the loop for the rest of the night.
    st.setdefault("steward", {"guidance": [], "invocations": 0, "islands": [],
                              "last_closed": 0})
    st["steward"]["invocations"] = n
    st["steward"]["last_closed"] = len(st["closed"])
    st["steward_requested"] = False
    if res is None:
        _record(ctx, "steward", {"ok": False, "reason": "steward-start",
                                 "detail": _walk_detail(ctx),
                                 "guidance": None, "island": None})
        return
    p, c = res
    ctx["steward_proc"], ctx["steward_ws"], ctx["steward_command"] = p, ws, c
    ctx["procs"][PROC_STEWARD] = p
    # The success path records no event until the steward exits, so without this the window
    # bookkeeping and the model call charged at the spawn live in memory alone: a kill here
    # would re-open the same window on resume and spawn — and charge — a second steward for it.
    _save_state(ctx)


def _steward_apply(ctx):
    """Read what the exited steward proposed, and act on it — or log why not."""
    root, plan, st, qid = ctx["root"], ctx["plan"], ctx["state"], ctx["qid"]
    p = ctx.get("steward_proc")
    ws, command = ctx.get("steward_ws"), ctx.get("steward_command")
    ctx["procs"].pop(PROC_STEWARD, None)
    ctx["steward_proc"] = None
    rc = p.returncode if p is not None else 0
    if rc != 0 and command and E.auto_rate_limited(_log_tail(ws, STEWARD_LOG)):
        _cool(ctx, "crux-auto-steward", command)
    raw = _agent_file(os.path.join(ws, STEWARD_PROPOSAL_NAME) if ws else None)
    res = E.auto_steward_proposal(raw, plan, st)
    if not res["ok"]:
        _record(ctx, "steward", {"ok": False, "reason": res["reason"],
                                 "detail": res["detail"],
                                 "guidance": None, "island": None})
        return
    if res["guidance"]:
        # The plan's `## Guidance` is NOT written: `auto guide` is the PI's verb, and the plan
        # document stays theirs alone. Every later worker brief carries the steward's words in
        # its own labelled section instead, attributed and stamped, so a worker sees who said
        # what.
        st["steward"]["guidance"].append({"at": E.now(), "author": "crux-auto-steward",
                                          "text": res["guidance"]})
    if not res["island"]:
        _record(ctx, "steward", {"ok": True, "reason": None, "detail": None,
                                 "guidance": res["guidance"], "island": None})
        return

    def act():
        qi, _fn = E.cmd_ask(root, res["island"]["title"], parent=plan["anchor"],
                            body_text=res["island"]["problem"])
        branch = island_branch(qid, qi)
        try:
            _git(ctx["repo"], "branch", branch, st["base"])
        except (E.CruxError, OSError) as e:
            # §3.8 is absolute: a steward never stops a run. An existing ref, an `index.lock`
            # or a read-only object store must not unwind this record — that would leave the
            # new question node orphaned under the anchor with no island record pointing at
            # it, no `steward` event, and a resume that files a SECOND one. An existing ref
            # that already resolves is the resume case and is not a failure.
            if rev_parse(ctx["repo"], branch) is None:
                return (None, f"the island branch {branch} could not be cut: {e}")
        try:
            score = float(E.resolve_address(
                root, f"{plan['baseline']}#{plan['address']}")["value"])
        except (E.CruxError, TypeError, ValueError):
            score = None
        # APPENDED, never inserted: `st["next_island"]`'s existing indices have to stay valid.
        # The plan's `islands:` frontmatter is not edited, because that field IS hashed and
        # writing it would clear the PI's approval mid-run.
        st["islands"][qi] = {"branch": branch, "pointer": st["base"],
                             "best": plan["baseline"], "best_score": score,
                             "seen_score": score, "stall": 0}
        st["steward"]["islands"].append(qi)
        return (qi, None)

    _record(ctx, "steward",
            lambda r: {"ok": r[0] is not None,
                       "reason": None if r[0] is not None else "steward-island",
                       "detail": r[1],
                       "guidance": res["guidance"], "island": r[0]},
            work=act)


def _next_island(ctx):
    """The island to start the next attempt on, round-robin from where the last one left, or
    None when nothing may start right now."""
    plan, st = ctx["plan"], ctx["state"]
    if st["confirmed"] is not None:
        return None
    if len(st["in_flight"]) >= plan["parallel_total"]:
        return None
    if len(st["closed"]) + len(st["in_flight"]) >= st["budget"]["attempts"]["total"]:
        return None
    if st["budget"]["model_calls"]["used"] >= st["budget"]["model_calls"]["total"]:
        return None
    islands = list(st["islands"])
    for k in range(len(islands)):
        idx = (int(st["next_island"] or 0) + k) % len(islands)
        i = islands[idx]
        if sum(1 for f in st["in_flight"].values()
               if f["island"] == i) < plan["parallel_island"]:
            st["next_island"] = (idx + 1) % len(islands)
            return i
    return None


def auto_run(root, path, max_attempts=None, lock_wait=LOCK_WAIT):
    """Run an approved flight plan until one of §11's four stops, and return the final state.

    There is no `--resume`: a vault that already carries `auto/<qid>/state.json` is reconciled
    and continued, because the alternative to resuming is a SECOND run over one run's refs and
    reserved ids — and a flag is how that happens at three in the morning."""
    res = E.auto_check(root, path)
    rel = res["plan"]
    if res["problems"]:
        raise E.CruxError(f"auto run: {rel} does not pass auto check: "
                          f"{res['problems'][0]['message']}")
    plan = E.load_flight_plan(root, path)
    qid = plan["anchor"]
    ap = E.auto_approval(E.read(os.path.join(root, *rel.split("/"))))
    if ap["state"] == "unapproved":
        raise E.CruxError(f"auto run: {rel} is not approved — the PI approves a flight plan "
                          f"with crux auto approve {rel}")
    if ap["state"] == "edited":
        raise E.CruxError(f"auto run: {rel} was edited after it was approved at "
                          f"{ap['approved']}, so the approval no longer stands — the PI "
                          f"re-approves it with crux auto approve {rel}")

    prior = None
    sp = state_path(root, qid)
    if os.path.isfile(sp):
        try:
            prior = json.loads(E.read(sp))
        except ValueError as e:
            raise E.CruxError(f"{E.AUTO_DIR}/{qid}/{E.AUTO_STATE_FILE} is damaged: {e}")
    if prior:
        if prior.get("stop"):
            raise E.CruxError(f"auto run: the run on {qid} already stopped "
                              f"({prior['stop']['reason']}) at {prior['stop']['at']}; its "
                              f"record is {E.AUTO_DIR}/{qid}/{E.AUTO_STATE_FILE}")
        drv = prior.get("driver") or {}
        if (drv.get("host") == HOST and drv.get("pid") != os.getpid()
                and _pid_alive(drv.get("pid"))):
            raise E.CruxError(f"auto run: a driver for {qid} is already running "
                              f"(pid {drv.get('pid')} on {drv.get('host')})")
        if prior.get("plan_hash") != ap["approved_hash"]:
            raise E.CruxError(f"auto run: {rel} was approved again with different content "
                              f"after this run opened, so this run cannot resume under it")
    repo = plan_repo(root, plan)

    ctx = {"root": root, "qid": qid, "rel": rel, "plan": plan, "repo": repo, "state": None,
           "lock_wait": lock_wait, "crash_at": os.environ.get(CRASH_ENV),
           "t0": time.monotonic(), "procs": {}, "work": {}, "seen": None,
           "steward_proc": None, "steward_ws": None, "steward_command": None,
           "walk_failures": [],
           "prior_host": (prior or {}).get("driver", {}).get("host")}
    _seen(ctx)                       # the ledger as it stands BEFORE this driver writes to it

    try:
        if prior is None:
            base_score = float(E.resolve_address(
                root, f"{plan['baseline']}#{plan['address']}")["value"])
            run_id = f"{qid}-{E.now().replace('-', '').replace(':', '')}"
            st = E.auto_new_state(plan, run_id, E.now(), os.getpid(), HOST, base_score,
                                  max_attempts)
            st["plan_hash"] = ap["approved_hash"]
            ctx["state"] = st
            # the FIRST locked write. A held lock refuses HERE, leaving no state, no ledger,
            # no reservation and no ref behind.
            _save_state(ctx)
            _open_base(ctx, ap)
        else:
            st = ctx["state"] = prior
            # A state.json written by 05.2 has neither key. Both are defaulted BEFORE the
            # first `_record`, so the key-set invariant holds from the `resumed` event on.
            st.setdefault("agents", {})
            st.setdefault("steward", {"guidance": [], "invocations": 0, "islands": [],
                                      "last_closed": 0})
            st["driver"] = {"pid": os.getpid(), "host": HOST}
            st["budget"]["attempts"]["total"] = plan["budget_attempts"] \
                if max_attempts is None else min(plan["budget_attempts"], int(max_attempts))
            if st.get("base") is None:
                _open_base(ctx, ap)
            _record(ctx, "resumed", {"in_flight": sorted(st["in_flight"], key=E.natkey),
                                     "pid": os.getpid()})

        if not st["in_flight"] and not st["closed"] and not reservations(root, qid):
            # 05.3: the probe FIRST. A misspelled agent is cheaper to find than a scorer run,
            # and the stop happens before any id is reserved — a reserved hypothesis number
            # can never be handed out again.
            # `auto run` gates on the STATIC check, which cannot see the filesystem — so the
            # one thing `auto check` learned about the repository has to be re-learned here or
            # a plan that was never `auto check`ed dies at `make_workspace` instead.
            bad = writable_problems(root, plan)
            if bad:
                _stop_run(ctx, {"reason": "abort", "axis": None, "attempt": None,
                                "detail": bad[0]["message"]})
            rows = probe_agents(root, plan, ctx["repo"])
            if rows and not any(r["reachable"] for r in rows):
                _stop_run(ctx, {"reason": "abort", "axis": None, "attempt": None,
                                "detail": "no agent command is reachable: "
                                          + "; ".join(f"{r['command']} ({r['detail']})"
                                                      for r in rows)})
            failed = _base_scorer_check(ctx)
            if failed:
                _stop_run(ctx, {"reason": "abort", "axis": None, "attempt": None,
                                "detail": f"the scorer failed on the base commit at run "
                                          f"open: {failed}"})
        if prior is not None:
            _reconcile(ctx)

        while True:
            _charge_hours(ctx)
            stop = E.auto_stop(st, plan)
            if stop:
                _stop_run(ctx, stop)
            if _steward_due(ctx):
                _steward_try(ctx)
            while True:
                island = _next_island(ctx)
                if island is None:
                    break
                _start_attempt(ctx, island)
            # A live steward counts as activity: it is the one thing in flight that is not an
            # attempt, and a run waiting on it has not run out of things to do.
            if not st["in_flight"] and ctx.get("steward_proc") is None:
                raise E.CruxError("auto run: nothing is in flight and nothing may start, yet "
                                  "no stop applies")
            exited = []
            for hid in sorted(st["in_flight"], key=E.natkey):
                p = ctx["procs"].get(hid)
                if p is None:
                    exited.append((hid, 0))
                elif p.poll() is not None:
                    exited.append((hid, p.returncode))
            if (ctx.get("steward_proc") is not None
                    and ctx["steward_proc"].poll() is not None):
                _steward_apply(ctx)
            if not exited:
                time.sleep(POLL)
                continue
            for hid, rc in exited:
                if hid in st["in_flight"]:
                    _after_worker(ctx, hid, rc)
    except _Stopped:
        pass
    finally:
        # §7 kills what is in flight on the STOP path. Every other way out of the loop — a
        # refusal from an engine act, a git failure, a keyboard interrupt — leaves the workers
        # in their own sessions, writing into the vault's shared roots with no driver left to
        # read what they wrote. A worker never outlives its driver.
        for hid in list(ctx["procs"]):
            p = ctx["procs"].pop(hid, None)
            if p is not None:
                try:
                    _kill_tree(p)
                except OSError:                          # already gone is not a failure
                    pass
    return ctx["state"]


# --------------------------------------------------------------------- promote, and refs
def promote(root, hid, branch=None):
    """Give one recorded attempt a branch name in the PI's repository.

    The only new verb that writes, and all it writes is a ref: no checkout, no merge, nothing
    on `main`. A run leaves a hundred commits under `refs/crux/auto/`, and this is how the
    one the PI wants stops being an implementation detail."""
    v = E.Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise E.CruxError(f"auto promote is per-attempt (got a '{n.type}' for '{hid}')")
    qid, ppath = E.auto_plan_for(root, v, hid)
    if qid is None:
        raise E.CruxError(f"no flight plan covers {hid}: none of its ancestor questions has "
                          f"{E.AUTO_DIR}/<qid>/{E.PLAN_FILE}")
    plan = E.load_flight_plan(root, ppath)
    repo = plan_repo(root, plan)
    ref = attempt_ref(qid, hid)
    sha = rev_parse(repo, ref)
    if sha is None:
        raise E.CruxError(f"auto promote: {hid} has no ref {ref}; the attempt was never "
                          f"recorded")
    branch = branch or promoted_branch(qid, hid)
    if rev_parse(repo, "refs/heads/" + branch) is not None:
        raise E.CruxError(f"auto promote: branch '{branch}' already exists")
    _git(repo, "branch", branch, sha)
    return dict(id=hid, anchor=qid, ref=ref, commit=sha, branch=branch, repo=repo)


def _sole_anchor(root):
    """The one anchor with a flight plan, or a refusal naming what it found. Creates nothing
    — not even `auto/` — so a vault written before any of this reads exactly as it did."""
    d = os.path.join(root, E.AUTO_DIR)
    ids = []
    if os.path.isdir(d):
        ids = sorted([x for x in os.listdir(d)
                      if os.path.isfile(os.path.join(d, x, E.PLAN_FILE))], key=E.natkey)
    if not ids:
        raise E.CruxError(f"auto refs: no flight plan in this vault "
                          f"({E.AUTO_DIR}/<qid>/{E.PLAN_FILE})")
    if len(ids) > 1:
        raise E.CruxError(f"auto refs: several flight plans ({', '.join(ids)}); "
                          f"name the anchor")
    return ids[0]


def _for_each_ref(repo, pattern):
    out = _git(repo, "for-each-ref", "--format=%(objectname) %(refname)", pattern)
    rows = []
    for line in out.splitlines():
        sha, _, name = line.strip().partition(" ")
        if sha and name:
            rows.append((sha, name.strip()))
    return rows


def auto_refs(root, qid=None):
    """What this run owns right now: its refs, its branches and its live worktrees.

    Read-only, and read-only all the way down — it creates no directory, no ref and no file,
    because the one question a PI asks after a run is not a reason to write to the vault."""
    qid = E.auto_qid_arg(qid)
    if qid is None:
        qid = _sole_anchor(root)
    ppath = f"{E.AUTO_DIR}/{qid}/{E.PLAN_FILE}"
    if not os.path.isfile(os.path.join(root, E.AUTO_DIR, qid, E.PLAN_FILE)):
        raise E.CruxError(f"no flight plan at {ppath}")
    plan = E.load_flight_plan(root, ppath)
    repo = plan_repo(root, plan)

    refs = []
    for sha, name in _for_each_ref(repo, f"{REF_PREFIX}/{qid}/"):
        refs.append(dict(name=name, id=name.rsplit("/", 1)[-1], commit=sha))
    refs.sort(key=lambda r: (0, ("", 0)) if r["id"] == "base" else (1, E.natkey(r["id"])))

    branches = []
    for sha, name in _for_each_ref(repo, f"refs/heads/{BRANCH_PREFIX}/{qid}/"):
        branches.append(dict(name=name[len("refs/heads/"):], commit=sha))
    rb = run_branch(qid)
    branches.sort(key=lambda b: (0 if b["name"] == rb else 1, b["name"]))

    base_dir = os.path.join(worktrees_root(repo), qid)
    worktrees = []
    for block in _worktree_blocks(repo):
        p = block.get("worktree")
        if not p or "prunable" in block:
            # git still lists a worktree whose directory somebody deleted. Listing it here
            # would report a checkout that is not there — and this verb may not prune, because
            # it may not write. `remove_worktree` is where the registration goes.
            continue
        rp = os.path.realpath(p)
        if rp != base_dir and not rp.startswith(base_dir + os.sep):
            continue
        worktrees.append(dict(id=os.path.basename(rp), path=p,
                             commit=block.get("HEAD")))
    worktrees.sort(key=lambda w: E.natkey(w["id"]))
    return {"anchor": qid, "repo": repo, "refs": refs, "branches": branches,
            "worktrees": worktrees}


def _worktree_blocks(repo):
    """`git worktree list --porcelain` as [{key: value}] — one dict per blank-line block."""
    out = _git(repo, "worktree", "list", "--porcelain")
    blocks, cur = [], {}
    for line in out.splitlines():
        if not line.strip():
            if cur:
                blocks.append(cur)
                cur = {}
            continue
        k, _, val = line.strip().partition(" ")
        cur[k] = val.strip()
    if cur:
        blocks.append(cur)
    return blocks


# ------------------------------------------------------------- the hidden maintenance entry
def _main(argv):
    """`autopilot.py reserve <vault-root> <qid> <n>` — not a crux verb, not in any help screen.

    It exists because the only honest test of a file lock is several real processes, and a
    test cannot spawn a function. Deliberately undocumented: a PI who reserves ids by hand
    has a vault whose counter has moved for no attempt."""
    if len(argv) != 4 or argv[0] != "reserve":
        sys.stderr.write("usage: autopilot.py reserve <vault-root> <qid> <n>\n")
        return 2
    _, root, qid, n = argv
    try:
        count = int(n)
    except ValueError:
        sys.stderr.write("usage: autopilot.py reserve <vault-root> <qid> <n>\n")
        return 2
    try:
        for _i in range(count):
            sys.stdout.write(reserve_id(root, qid) + "\n")
            sys.stdout.flush()
    except E.CruxError as e:
        sys.stderr.write(f"crux: {e}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(_main(sys.argv[1:]))
