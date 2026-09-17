#!/usr/bin/env python3
"""autopilot — the impure half of crux autopilot (spec 05, slice 05.1).

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
  * per-attempt worktrees under `<git common dir>/crux-auto/<qid>/<hid>`;
  * the frozen-path diff and the manifest over shared roots — both DETECT AND REPORT ONLY;
  * retention over the workspace alone, never over the record;
  * the scorer contract: stdout is one JSON object, and the DRIVER writes it verbatim to
    `results/<hid>/metrics.json`. The engine only ever reads that file.

What 05.1 is NOT: the loop, the agent, a verdict, a close, either of the two run-log files
05.2 owns, or any write to `main`. Nothing below checks out a branch, merges, or commits on
the PI's behalf.
"""
import os, sys, json, time, shlex, socket, subprocess, shutil, tempfile, contextlib

import engine as E


# ------------------------------------------------------------------ names, constants, paths
HOST                   = socket.gethostname()
LOCK_NAME              = ".lock"                 # <root>/auto/.lock
RESERVED_FILE          = "reserved.json"         # <root>/auto/<qid>/reserved.json
MANIFESTS_DIR          = "manifests"             # <root>/auto/<qid>/manifests/<hid>.json
WORKTREES_DIR          = "crux-auto"             # <git common dir>/crux-auto/<qid>/<hid>
REF_PREFIX             = "refs/crux/auto"
BRANCH_PREFIX          = "crux/auto"
LOCK_WAIT              = 60.0                    # seconds a caller waits before refusing
LOCK_STALE             = 900.0                   # seconds after which any lock is stale by age
LOCK_POLL              = 0.05                    # seconds between attempts
SCORER_TIMEOUT_DEFAULT = E.AUTO_SCORER_TIMEOUT_DEFAULT
STDERR_TAIL            = 2000                    # characters kept from a failing scorer's stderr
STDOUT_HEAD            = 200                     # characters quoted from a non-JSON stdout
RESERVATION_STATES     = ("reserved", "materialized", "abandoned")

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
SIGKILL = 9                   # the number, so this module need not import `signal`


def _run(argv, cwd=None, env=None, timeout=None):
    """The ONE place this module starts a process.

    One spawn site is what makes "did this verb start anything?" a question a test can answer
    by replacing a single name — and what makes the no-shell rule checkable by reading four
    lines rather than forty. `shell=True` never appears: the scorer command is the PI's, and
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
        try:
            os.killpg(os.getpgid(p.pid), SIGKILL)
        except OSError:
            p.kill()
        p.communicate()
        raise
    except BaseException:
        p.kill()
        p.communicate()
        raise
    return subprocess.CompletedProcess(list(argv), p.returncode, out, err)


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
    """The repository's shared git directory — where the per-attempt worktrees live.

    Shared rather than per-worktree on purpose: every attempt's checkout hangs off the one
    directory, so a single `crux-auto/<qid>/` subtree holds the whole run."""
    hit = _COMMON_DIR_CACHE.get(repo)
    if hit and os.path.isdir(hit):
        return hit
    out = _git(repo, "rev-parse", "--git-common-dir")
    got = os.path.realpath(out if os.path.isabs(out) else os.path.join(repo, out))
    _COMMON_DIR_CACHE[repo] = got
    return got


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
    run at once — the one failure the lock exists to prevent."""
    rec = read_lock(root)
    if rec and (rec.get("pid") != os.getpid() or rec.get("host") != HOST):
        return None
    try:
        os.unlink(lock_path(root))
    except (FileNotFoundError, IsADirectoryError):
        pass
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
    is discovered now rather than halfway through a run."""
    qid = plan["anchor"]
    repo = plan_repo(root, plan)
    head = rev_parse(repo, "HEAD")
    if head is None:
        raise E.CruxError(f"repository at {repo} has no commits to start a run from")
    if rev_parse(repo, base_ref(qid)) is not None:
        raise E.CruxError(f"auto run for {qid} is already open ({base_ref(qid)} exists)")
    rb = run_branch(qid)
    islands = {}
    made = []
    try:
        _git(repo, "update-ref", base_ref(qid), head)
        made.append(("ref", base_ref(qid)))
        _git(repo, "branch", rb, head)
        made.append(("branch", rb))
        for island in (plan.get("islands") or [qid]):
            b = island_branch(qid, island)
            _git(repo, "branch", b, head)
            made.append(("branch", b))
            islands[island] = b
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
    return os.path.join(git_common_dir(plan_repo(root, plan)), WORKTREES_DIR,
                        plan["anchor"], hid)


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
    path = os.path.join(git_common_dir(repo), WORKTREES_DIR, qid, hid)
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
    path = os.path.join(git_common_dir(repo), WORKTREES_DIR, qid, hid)
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
    path = os.path.join(git_common_dir(repo), WORKTREES_DIR, qid, hid)
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
    p = workspace_path(root, plan, hid)
    os.makedirs(p, exist_ok=True)
    return p


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


def run_scorer(cmd, cwd, attempt, workspace, timeout):
    """Run the PI's scorer once and return `(the metrics object, seconds)`.

    The contract, entire: stdout is ONE JSON object, stderr is free text, and the two
    variables the command needs are added to the inherited environment. No shell — the
    command is split by `shlex` and handed to the kernel, so nothing between the plan and the
    process can expand, glob or reinterpret it."""
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


def score_attempt(root, plan, hid, cwd=None):
    """Score one recorded attempt and write the object VERBATIM to results/<hid>/metrics.json.

    Verbatim, and written by the driver: the number that decides a verdict comes from the
    command's stdout, never from a file a worker could have rewritten. The file is written
    BEFORE the address is checked, so a scorer whose objective key is wrong still leaves the
    evidence on disk for the PI to look at."""
    if cwd is None:
        cwd = worktree_path(root, plan, hid)
    if not os.path.isdir(cwd):
        raise E.CruxError(f"no worktree for {hid} at {cwd}")
    obj, _ = run_scorer(plan["scorer"], cwd, hid, workspace_path(root, plan, hid),
                        plan["scorer_timeout"])
    out = os.path.join(root, E.RESULTS_DIR, hid, E.METRICS_FILE)
    _write_json(out, obj)
    where = f"{E.RESULTS_DIR}/{hid}/{E.METRICS_FILE}"
    try:
        E.metrics_value(obj, plan["address"], where)
    except E.AddressError as e:
        raise ScorerError("scorer-address",
                          f"objective '{plan['address']}' does not resolve in {where}: {e}")
    return obj


def auto_check(root, path, static=False):
    """`auto check`, with the scorer dry-run added. `--static` is 05.0's verb, unchanged.

    A flight plan that passes every engine check and then cannot produce a number is a plan
    that fails at attempt one of a hundred and forty. So the default runs the PI's scorer
    ONCE, in the repository, against a throwaway workspace, and writes nothing anywhere —
    the baseline's own metrics file is the PI's, and a dry run does not get to touch it."""
    res = E.auto_check(root, path)
    if static:
        return res
    res["repo"] = None
    res["scorer"] = {"ran": False, "cmd": None, "cwd": None, "address": None,
                     "value": None, "seconds": None}
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
    res["ok"] = not res["problems"]
    return res


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
    return {"id": hid, "anchor": qid, "ref": ref, "commit": sha, "branch": branch,
            "repo": repo}


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
    if qid is None:
        qid = _sole_anchor(root)
    ppath = f"{E.AUTO_DIR}/{qid}/{E.PLAN_FILE}"
    if not os.path.isfile(os.path.join(root, E.AUTO_DIR, qid, E.PLAN_FILE)):
        raise E.CruxError(f"no flight plan at {ppath}")
    plan = E.load_flight_plan(root, ppath)
    repo = plan_repo(root, plan)

    refs = []
    for sha, name in _for_each_ref(repo, f"{REF_PREFIX}/{qid}/"):
        refs.append({"name": name, "id": name.rsplit("/", 1)[-1], "commit": sha})
    refs.sort(key=lambda r: (0, ("", 0)) if r["id"] == "base" else (1, E.natkey(r["id"])))

    branches = []
    for sha, name in _for_each_ref(repo, f"refs/heads/{BRANCH_PREFIX}/{qid}/"):
        branches.append({"name": name[len("refs/heads/"):], "commit": sha})
    rb = run_branch(qid)
    branches.sort(key=lambda b: (0 if b["name"] == rb else 1, b["name"]))

    base_dir = os.path.join(git_common_dir(repo), WORKTREES_DIR, qid)
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
        worktrees.append({"id": os.path.basename(rp), "path": p,
                          "commit": block.get("HEAD")})
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
