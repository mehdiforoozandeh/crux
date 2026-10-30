#!/usr/bin/env python3
"""crux auto — the lean autopilot (spec 18).

One loop, seven rules. Each attempt: pick a parent (PUCT: c_puct 0 = climb, 1.0 = explore),
cut a detached worktree from its commit, run the worker (no web tools, brief on stdin), check
the allowlist, run the frozen scorer, file one hypothesis node under the anchor and close it on
its derived verdict, append one ledger line. The ledger `auto/<anchor>/ledger.jsonl` is the
whole run state: a second `run` continues from it.

  1 allowlist     only `editable` paths may change, else the attempt is discarded
  2 fail          a crash, timeout or missing number is one failed attempt; the run goes on
  3 rejected      `passed: false` rejects once; only a scorer that cannot start is retried, once
  4 time          one deadline per attempt covers the worker and the scorer
  5 keep          every valid attempt is kept; the parent comes from PUCT over the kept ones
  6 setup         the base must score, the score must respond, the worker must commit
  7 budget        `budget_hours` is read between attempts; a rate limit waits, never fails

Stdlib only, and only the core of `engine` (nodes, verdicts): nothing from the old autopilot."""
import os, sys, re, json, math, time, shlex, shutil, signal, subprocess, datetime
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

PLAN_FIELDS = ("anchor", "repo", "base", "editable", "scorer", "objective", "mode",
               "budget_hours", "attempt_minutes", "worker", "min_gain", "guidance")
REQUIRED = ("anchor", "repo", "base", "editable", "scorer", "objective")
MODES = {"climb": 0.0, "explore": 1.0}                  # mode -> c_puct
EFFORTS = ("low", "medium", "high", "xhigh", "max")
STATUSES = ("kept", "rejected", "failed", "discarded")
GIT = ["git", "-c", "user.name=crux-auto", "-c", "user.email=auto@crux.invalid"]
NULL = "chance: the score moved by scorer noise, not by the change"
CONTROL = "the scorer accepted the candidate and printed the objective"

# Provider limits, read case-insensitively off a FAILED worker's output only. Copied from the
# spec-05 driver: the bare word "limit" is never enough, a program may print it about itself.
RATE_LIMIT_PATTERNS = (r"5-?hour limit", r"usage limit", r"rate limit", r"limit reached",
                       r"too many requests", r"reset[s]? at", r"please try again later",
                       r"overloaded", r"service unavailable", r"internal server error",
                       r"\b529\b", r"api_error", r"hit your [^\n]{0,40}limit", r"session limit",
                       r"reset[s]? (?:at\s+)?\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?",
                       r"reset[s]? (?:at\s+)?\d{1,2}:\d{2}")


def rate_limited(text):
    return bool(re.search("|".join(RATE_LIMIT_PATTERNS), str(text or ""), re.I))


def run_dir(root, qid):
    return os.path.join(root, "auto", qid)


def ledger_path(root, qid):
    return os.path.join(run_dir(root, qid), "ledger.jsonl")


# --------------------------------------------------------------------------------- the plan
def _split_doc(text):
    """(frontmatter lines, body) — or (None, text) when there is no `---` block."""
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return lines[1:i], "\n".join(lines[i + 1:])
    return None, text


def _read_head(head):
    raw, problems = {}, []
    for line in head:
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        k, sep, v = line.partition(":")
        k = k.strip()
        if not sep or not k:
            problems.append(f"cannot read line {line.strip()!r} (expected `key: value`)")
            continue
        if k in raw:
            problems.append(f"field '{k}' appears twice")
        raw[k] = v.strip()
    return raw, problems


def _pos_float(raw, key, default, problems):
    try:
        x = float(raw.get(key) or default)
        if x > 0 and math.isfinite(x):
            return x
    except ValueError:
        pass
    problems.append(f"'{key}' must be a positive number (got {raw.get(key)!r})")
    return float(default)


def load_plan(path):
    """The parsed plan with defaults filled. Raises E.CruxError naming every problem at once,
    and always naming the fields a plan may carry."""
    fields = ("A plan has these fields: " + ", ".join(PLAN_FIELDS)
              + " (guidance is the free text after the closing ---).")
    try:
        with open(path, encoding="utf-8") as f:
            text = f.read()
    except OSError as e:
        raise E.CruxError(f"cannot read plan {path}: {e.strerror or e}")
    head, body = _split_doc(text)
    if head is None:
        raise E.CruxError(f"plan {path} has no `---` frontmatter. {fields}")
    raw, problems = _read_head(head)
    unknown = [k for k in raw if k not in PLAN_FIELDS]
    if unknown:
        problems.append(f"unknown field(s): {', '.join(unknown)}. An old (spec-05) plan is "
                        f"refused, not migrated: rewrite it with the new fields")
    for k in REQUIRED:
        if not raw.get(k):
            problems.append(f"'{k}' is required")
    p = {"path": os.path.abspath(path), "anchor": raw.get("anchor", ""),
         "repo": raw.get("repo", ""), "base": raw.get("base", ""),
         "scorer": raw.get("scorer", ""), "mode": raw.get("mode") or "climb",
         "guidance": body.strip() or raw.get("guidance", "")}
    if p["anchor"] and not re.fullmatch(r"q\d+", p["anchor"]):
        problems.append(f"'anchor' must be a question id like q3 (got {p['anchor']!r})")
    p["editable"] = [e.strip() for e in raw.get("editable", "").split(",") if e.strip()]
    for e in p["editable"]:
        if os.path.isabs(e) or ".." in e.split("/"):
            problems.append(f"editable path {e!r} must be relative to the repo, without '..'")
    if p["scorer"]:
        try:
            if not shlex.split(p["scorer"]):
                problems.append("'scorer' is empty")
        except ValueError as e:
            problems.append(f"'scorer' does not parse: {e}")
    obj = raw.get("objective", "").split()
    p["address"], p["direction"], p["bar"] = None, None, None
    if raw.get("objective"):
        try:
            if len(obj) != 3 or obj[1] not in ("min", "max"):
                raise ValueError
            p["address"], p["direction"], p["bar"] = obj[0], obj[1], float(obj[2])
        except ValueError:
            problems.append(f"'objective' must be `<address> <min|max> <bar>` "
                            f"(got {raw.get('objective')!r})")
    if p["mode"] not in MODES:
        problems.append(f"'mode' must be climb or explore (got {p['mode']!r})")
    p["budget_hours"] = _pos_float(raw, "budget_hours", 8, problems)
    p["attempt_minutes"] = _pos_float(raw, "attempt_minutes", 20, problems)
    try:
        p["min_gain"] = float(raw.get("min_gain") or 0)
        if not (p["min_gain"] >= 0 and math.isfinite(p["min_gain"])):
            raise ValueError
    except ValueError:
        problems.append(f"'min_gain' must be a number >= 0 (got {raw.get('min_gain')!r})")
    w = (raw.get("worker") or "opus high").split()
    if len(w) != 2 or not re.fullmatch(r"[A-Za-z][\w.\-]*", w[0]) or w[1] not in EFFORTS:
        problems.append(f"'worker' must be `<model> <effort>`, effort one of "
                        f"{', '.join(EFFORTS)}, and nothing else (got {raw.get('worker')!r})")
        w = ["opus", "high"]
    p["model"], p["effort"] = w
    if problems:
        raise E.CruxError(f"plan {path} is refused:\n  - " + "\n  - ".join(problems)
                          + f"\n{fields}")
    return p


def _raw_plan(root, qid):
    """The plan's frontmatter as plain strings, never refused: status reads old runs too."""
    try:
        with open(os.path.join(run_dir(root, qid), "plan.md"), encoding="utf-8") as f:
            head, _ = _split_doc(f.read())
    except OSError:
        return {}
    return _read_head(head or [])[0]


def _repo(root, plan):
    return os.path.abspath(os.path.join(root, plan["repo"]))


def editable_ok(path, editable):
    return any(path.startswith(e) if e.endswith("/") else path == e for e in editable)


# ------------------------------------------------------------------------- processes and git
def _run(argv, cwd=None, env=None, timeout=None, stdin=None):
    """(rc, stdout, stderr). No shell. The child gets its own session, so a timeout kills the
    whole tree; TimeoutExpired and OSError propagate."""
    p = subprocess.Popen(list(argv), cwd=cwd, env=env,
                         stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                         encoding="utf-8", errors="replace", start_new_session=True)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired:
        try:
            os.killpg(os.getpgid(p.pid), signal.SIGKILL)
        except (OSError, AttributeError):
            p.kill()
        p.communicate()
        raise
    except BaseException:
        p.kill()
        p.communicate()
        raise
    return p.returncode, out or "", err or ""


def _git(cwd, *args):
    rc, out, err = _run(GIT + ["-C", cwd] + [str(a) for a in args])
    if rc != 0:
        raise E.CruxError(f"git {args[0]} failed in {cwd}: {err.strip()[-500:] or '(no stderr)'}")
    return out.strip()


def _rev(cwd, ref):
    """The commit `ref` names, or None."""
    try:
        rc, out, _ = _run(GIT + ["-C", cwd, "rev-parse", "--verify", "--quiet",
                                 f"{ref}^{{commit}}"])
    except OSError:
        return None
    return (out.strip() or None) if rc == 0 else None


def _add_worktree(repo, path, commit):
    _drop_worktree(repo, path)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    _git(repo, "worktree", "add", "--detach", path, commit)


def _drop_worktree(repo, path):
    if os.path.isdir(path):
        _run(GIT + ["-C", repo, "worktree", "remove", "--force", path])
        shutil.rmtree(path, ignore_errors=True)
    _run(GIT + ["-C", repo, "worktree", "prune"])


def _tail(text, n=400):
    return " ".join(str(text or "").split())[-n:] or "(empty)"


# ---------------------------------------------------------------------------------- worker
def worker_argv(plan):
    # CRUX_AUTO_CLAUDE is a command line, split like the scorer's, so a test can run a Python
    # stub through sys.executable: Windows cannot execute a #! script directly.
    return shlex.split(os.environ.get("CRUX_AUTO_CLAUDE") or "claude") + ["-p",
            "--model", plan["model"], "--effort", plan["effort"],
            "--permission-mode", "bypassPermissions",
            "--disallowedTools", "WebFetch", "WebSearch"]


def web_denied(argv):
    denied, on = set(), False
    for a in argv:
        if a == "--disallowedTools":
            on = True
        elif a.startswith("-"):
            on = False
        elif on:
            denied.update(a.replace(",", " ").split())
    return {"WebFetch", "WebSearch"} <= denied


def _work(plan, wt, brief, deadline, parent, log):
    """Run the worker in `wt`, brief on stdin, killed at the monotonic `deadline`. A failure
    that reads as a provider limit (rule 7) waits, resets the worktree and tries again; the
    wait moves the deadline, the time already worked does not come back.
    Returns (rc, timed_out, seconds spent waiting)."""
    waited = 0.0
    while True:
        left = deadline + waited - time.monotonic()
        try:
            if left <= 0:
                raise subprocess.TimeoutExpired("worker", 0)
            rc, out, err = _run(worker_argv(plan), cwd=wt, timeout=left, stdin=brief)
            timed_out = False
        except subprocess.TimeoutExpired:
            rc, out, err, timed_out = None, "", "", True
        except OSError as e:
            rc, out, err, timed_out = 127, "", f"worker cannot start: {e}", False
        with open(log, "a", encoding="utf-8") as f:
            f.write(out + err + f"\n[crux auto] worker exit {rc}, timed out {timed_out}\n")
        if timed_out or rc == 0 or _rev(wt, "HEAD") != parent or not rate_limited(out + err):
            return rc, timed_out, waited
        wait = float(os.environ.get("CRUX_AUTO_RATE_WAIT") or 300)
        time.sleep(wait)
        waited += wait
        _git(wt, "reset", "--hard", "-q", parent)
        _git(wt, "clean", "-fdxq")


def brief_text(plan, n, parent, pscore, best, last):
    better = "lower" if plan["direction"] == "min" else "higher"
    lines = [f"- attempt {r.get('n')} ({r.get('id')}, from {r.get('parent')}): "
             f"{r.get('status')}, score {r.get('score')}"
             + (f" ({r.get('reason')})" if r.get("reason") else "") for r in last]
    return "\n".join([
        f"You are attempt {n} of a crux autopilot search. Improve the program in this git "
        f"worktree (your current directory).",
        "",
        f"Objective: `{plan['address']}` in the scorer's JSON, {better} is better. "
        f"The threshold is {plan['bar']}.",
        f"The scorer is frozen; the driver runs it after you finish: {plan['scorer']}",
        f"You start from {parent}, which scores {pscore}. The best score so far is {best}.",
        *([f"A score counts as better only if it beats the parent by more than "
           f"{plan['min_gain']:g}."] if plan.get("min_gain") else []),
        "Last outcomes:", *(lines or ["- none yet"]),
        "",
        "Rules:",
        f"- Edit only these paths: {', '.join(plan['editable'])}. Any other change "
        f"discards the attempt.",
        "- Do not use the web.",
        f"- You have about {plan['attempt_minutes']:g} minutes, scoring included.",
        "- Finish with ONE git commit. Its subject line is your claim: what you changed and "
        "why it should move the objective.",
        "",
        "Guidance from the PI:",
        plan["guidance"] or "(none)",
    ]) + "\n"


# ---------------------------------------------------------------------------------- scorer
def metrics_value(tree, address):
    """One dotted address through the scorer's JSON, at a `{"value": n}` leaf, as a float.
    Raises ValueError when it does not resolve to a finite number."""
    node = tree
    for part in str(address).split("."):
        if not isinstance(node, dict) or part not in node:
            raise ValueError(f"objective '{address}' does not resolve in the scorer output")
        node = node[part]
    raw = node.get("value") if isinstance(node, dict) else None
    if isinstance(raw, bool) or not isinstance(raw, (int, float)) or not math.isfinite(raw):
        raise ValueError(f"objective '{address}' is not a {{\"value\": <number>}} leaf")
    return float(raw)


def score(plan, cwd, n, workspace, deadline=None):
    """(status, score, reason), status in kept|rejected|failed. Rule 3: `passed: false` is
    rejected with no retry; a scorer that cannot start (spawn error, signal, non-zero exit with
    no JSON) is retried once. Rule 2: timeout or a missing number is failed."""
    argv = shlex.split(plan["scorer"])
    env = dict(os.environ, CRUX_WORKSPACE=workspace, CRUX_ATTEMPT=str(n))
    os.makedirs(workspace, exist_ok=True)
    fault = ""
    for _ in range(2):
        left = None if deadline is None else deadline - time.monotonic()
        if left is not None and left <= 0:
            return "failed", None, "the attempt's time ran out before scoring"
        try:
            rc, out, err = _run(argv, cwd=cwd, env=env, timeout=left)
        except subprocess.TimeoutExpired:
            return "failed", None, "the scorer ran past the attempt's time limit"
        except OSError as e:
            fault = f"scorer cannot start: {e.strerror or e}"
            continue
        try:
            obj = json.loads(out.strip())
        except ValueError:
            obj = None
        if isinstance(obj, dict) and obj.get("passed") is False:
            return "rejected", None, _tail(obj.get("reason") or "passed: false", 300)
        if rc != 0 and not isinstance(obj, dict):
            fault = f"scorer exited {rc} with no JSON: {_tail(err)}"
            continue
        if rc != 0:
            return "failed", None, f"scorer exited {rc}: {_tail(err)}"
        if not isinstance(obj, dict):
            return "failed", None, f"scorer stdout is not one JSON object: {_tail(out, 200)}"
        try:
            return "kept", metrics_value(obj, plan["address"]), ""
        except ValueError as e:
            return "failed", None, str(e)
    return "failed", None, fault + " (after one retry)"


# ------------------------------------------------------------------------------ selection
# Ported from google-research/era implementation/futs.py (Apache-2.0); the arithmetic is
# theirs verbatim: rank score + c_puct * (1/N) * sqrt(total visits) / (1 + visits). The 1/N
# prior is load-bearing: with a constant prior exploration grows without bound.
def puct_rank(attempts, c_puct, direction="max"):
    rows = list(attempts or [])
    if not rows:
        raise E.CruxError("puct: no scored attempts to rank")
    visits = {r["id"]: int(r.get("visits") or 0) for r in rows}
    eff = {r["id"]: (float(r["score"]) if direction == "max" else -float(r["score"]))
           for r in rows}
    n = len(rows)
    # worst first; equal scores sort by natural id descending, so ties go to the lowest id
    order = sorted(rows, key=lambda r: E.natkey(r["id"]), reverse=True)
    order.sort(key=lambda r: eff[r["id"]])
    rank = {r["id"]: (i / (n - 1) if n > 1 else 0.5) for i, r in enumerate(order)}
    total = sum(visits.values())
    out = [{"id": r["id"], "score": float(r["score"]), "visits": visits[r["id"]],
            "rank_score": rank[r["id"]],
            "puct": rank[r["id"]] + c_puct * (1.0 / n) * math.sqrt(total)
                    / (1 + visits[r["id"]])} for r in rows]
    out.sort(key=lambda d: (-d["puct"], E.natkey(d["id"])))
    return out


def puct_select(attempts, c_puct, direction="max"):
    """c_puct 0 is climb: the best attempt on every call."""
    return puct_rank(attempts, c_puct, direction)[0]["id"]


def _beats(value, ref, direction, min_gain=0.0):
    """Better than `ref` by MORE than min_gain, in the objective's direction."""
    return value < ref - min_gain if direction == "min" else value > ref + min_gain


def _best(kept, direction, min_gain=0.0, baseline=None):
    """The base (when its score is known) starts as the best; in attempt order, a kept attempt
    replaces the best only if it beats it by more than min_gain."""
    best = None if baseline is None else {"id": "base", "score": baseline}
    for r in sorted(kept, key=lambda r: r.get("n") or 0):
        if best is None or _beats(r["score"], best["score"], direction, min_gain):
            best = r
    return best


# ------------------------------------------------------------------------------ the vault
def _tick(root, nid, ticks):
    """Tick the node's checks in order, each noted `(found: …)`."""
    n = E.Vault(root).get(nid)
    lines, k, sec = n["body"].split("\n"), 0, False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            sec = line[3:].strip().lower() == "verifiables"
            continue
        m = re.match(r"^(\s*- \[).(\]\s*)(.*)$", line)
        if sec and m and k < len(ticks):
            lines[i] = f"{m.group(1)}{ticks[k][0]}{m.group(2)}{m.group(3)} (found: {ticks[k][1]})"
            k += 1
    E.write_if_changed(n["path"], E.render_doc(n["fm"], "\n".join(lines)))


def file_node(root, plan, n, parent, pscore, status, value, reason, claim):
    """One attempt as one hypothesis under the anchor, filed and closed: hypothesize,
    approve the null, running, tick, close. The verdict is the engine's. Returns the id."""
    op, g = ("<" if plan["direction"] == "min" else ">"), plan.get("min_gain") or 0
    bar = pscore if not g else (pscore - g if op == "<" else pscore + g)
    claim = " ".join((claim or "").split()) or f"Autopilot attempt {n} (no claim)"
    nid, _fn, _w = E.cmd_hypothesize(
        root, " ".join(claim.split()[:12]), parent=plan["anchor"],
        verifiables=[f"{plan['address']} {op} {bar!r}"], neutral=[CONTROL], null=NULL,
        fails_if=["the candidate does not beat its parent's score",
                  "the scorer rejected the candidate, failed, or never ran"],
        discriminates=[True, False], builds_on=None if parent == "base" else parent,
        claim=claim)
    E.cmd_approve_null(root, nid)
    E.cmd_test(root, nid, to="running")
    if status == "kept":
        better = _beats(value, pscore, plan["direction"], g)
        _tick(root, nid, [("x" if better else " ", repr(value)), ("x", "passed")])
    else:
        _tick(root, nid, [("-", "n/a"), (" ", status)])
    findings = (f"Autopilot attempt {n}: {status}. {plan['address']} = "
                f"{'n/a' if value is None else repr(value)}, parent {parent} at {pscore!r}."
                + (f" Reason: {reason}." if reason else ""))
    E.cmd_close(root, nid, metric=None if value is None else repr(value),
                findings=findings.replace("\\", "/"))
    return nid


# ----------------------------------------------------------------------------- the ledger
def _now():
    return datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")


def _append(path, event, **fields):
    line = dict({"event": event, "at": _now()}, **fields)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
    return line


def _read(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for l in f:
                try:
                    obj = json.loads(l)
                except ValueError:
                    continue
                if isinstance(obj, dict):
                    out.append(obj)
    except OSError:
        pass
    return out


def _attempt_rows(lines):
    return [l for l in lines if l.get("event") == "attempt" and l.get("status") in STATUSES
            and isinstance(l.get("n"), int)]


# --------------------------------------------------------------------------- setup (rule 6)
def setup_check(root, plan, worker=True):
    problems, baseline, secs = [], None, 0.0
    if not web_denied(worker_argv(plan)):
        problems.append("the worker command does not deny the web tools WebFetch and WebSearch")
    a = E.Vault(root).nodes.get(plan["anchor"])
    if a is None or a.type != "question":
        problems.append(f"anchor '{plan['anchor']}' is not a question in this vault")
    repo, d = _repo(root, plan), run_dir(root, plan["anchor"])
    base = _rev(repo, plan["base"])
    if base is None:
        problems.append(f"base '{plan['base']}' is not a commit in {repo}")
        return {"ok": False, "problems": problems, "baseline": None, "scorer_seconds": None}
    wt, ws = os.path.join(d, "work", "setup"), os.path.join(d, "scratch", "setup")
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    try:
        _add_worktree(repo, wt, base)
        t0 = time.monotonic()
        st, baseline, why = score(plan, wt, 0, ws, t0 + plan["attempt_minutes"] * 60)
        secs = time.monotonic() - t0
        target = next((f for e in plan["editable"] for f in
                       _git(wt, "ls-files", "--", e).splitlines()), None)
        if st != "kept":
            problems.append(f"the base does not score ({st}): {why}")
        elif target is None:
            problems.append("no editable path names a file tracked at base")
        else:
            open(os.path.join(wt, target), "w").close()
            st2, s2, _ = score(plan, wt, 0, ws,
                               time.monotonic() + plan["attempt_minutes"] * 60)
            if st2 == "kept" and s2 == baseline:
                problems.append(f"the score does not respond: with {target} emptied it still "
                                f"scores {s2!r}")
        if worker and target is not None:
            _add_worktree(repo, wt, base)
            text = (f"This is the setup check of a crux autopilot run. Append one comment "
                    f"line to `{target}` in this git worktree, in that file's comment syntax, "
                    f"then make ONE git commit with the subject `crux setup check`. Change "
                    f"nothing else and do not use the web.\n")
            rc, timed_out, _ = _work(plan, wt, text,
                                     time.monotonic() + plan["attempt_minutes"] * 60, base,
                                     os.path.join(d, "logs", "setup.log"))
            if _rev(wt, "HEAD") == base:
                problems.append(f"the worker made no commit (exit {rc}, timed out "
                                f"{timed_out}); see {os.path.join(d, 'logs', 'setup.log')}")
    finally:
        _drop_worktree(repo, wt)
        shutil.rmtree(ws, ignore_errors=True)
    return {"ok": not problems, "problems": problems, "baseline": baseline,
            "scorer_seconds": secs}


def check(root, plan_path, static=False):
    try:
        plan = load_plan(plan_path)
    except E.CruxError as e:
        return {"ok": False, "problems": [str(e)], "baseline": None, "scorer_seconds": None}
    if static:
        return {"ok": True, "problems": [], "baseline": None, "scorer_seconds": None}
    return setup_check(root, plan, worker=True)


# ---------------------------------------------------------------------------- one attempt
def _attempt(root, plan, setup, rows, n, lp):
    anchor, repo, d = plan["anchor"], _repo(root, plan), run_dir(root, plan["anchor"])
    kept = [r for r in rows if r["status"] == "kept"]
    best = _best(kept, plan["direction"], plan["min_gain"], setup["baseline"])
    pid = best["id"]                                   # climb: the best, possibly the base
    if kept and plan["mode"] != "climb":
        pop = [{"id": r["id"], "score": r["score"],
                "visits": sum(1 for x in rows if x.get("parent") == r["id"])} for r in kept]
        pid = puct_select(pop, MODES[plan["mode"]], plan["direction"])
    if pid != "base":
        prow = next(r for r in kept if r["id"] == pid)
        pcommit, pscore = prow["commit"], prow["score"]
    else:
        pcommit, pscore = _rev(repo, plan["base"]), setup["baseline"]
        if pcommit is None:
            raise E.CruxError(f"base '{plan['base']}' is not a commit in {repo}")
    text = brief_text(plan, n, pid, pscore, best["score"],
                      rows[-5:])
    wt, ws = os.path.join(d, "work", str(n)), os.path.join(d, "scratch", str(n))
    os.makedirs(os.path.join(d, "logs"), exist_ok=True)
    attempt_s = plan["attempt_minutes"] * 60
    start = time.monotonic()
    commit, value, claim = None, None, ""
    _add_worktree(repo, wt, pcommit)
    try:
        rc, timed_out, waited = _work(
            plan, wt, text, start + attempt_s - 1.5 * float(setup["scorer_seconds"] or 0),
            pcommit, os.path.join(d, "logs", f"{n}.log"))
        deadline = start + waited + attempt_s
        _git(wt, "reset", "--hard", "-q")              # the scorer reads the commit, only
        _git(wt, "clean", "-fdxq")
        head = _rev(wt, "HEAD")
        if head and head != pcommit:
            commit = head
            _git(repo, "update-ref", f"refs/crux/auto/{anchor}/{n}", head)
            claim = _git(wt, "log", "-1", "--format=%s")
        if timed_out:
            status, reason = "failed", "the worker ran past the attempt's time limit"
        elif commit is None:
            status, reason = "failed", f"the worker made no commit (exit {rc})"
        else:
            # --no-renames: a move lists both paths, so a frozen file cannot leave unseen
            diff = _git(wt, "diff", "--name-only", "--no-renames", pcommit, head)
            bad = [p for p in diff.splitlines() if p and not editable_ok(p, plan["editable"])]
            if not diff.strip():
                status, reason = "discarded", "empty commit: no file changed"
            elif bad:
                status, reason = "discarded", "changed non-editable path(s): " + ", ".join(bad)
            else:
                status, value, reason = score(plan, wt, n, ws, deadline)
    finally:
        _drop_worktree(repo, wt)
        shutil.rmtree(ws, ignore_errors=True)
    nid = file_node(root, plan, n, pid, pscore, status, value, reason, claim)
    return _append(lp, "attempt", n=n, id=nid, parent=pid, commit=commit, score=value,
                   status=status, reason=reason, seconds=round(time.monotonic() - start, 3))


def run(root, plan_path, max_attempts=None):
    """Run (or continue) the search until the budget, `max_attempts` or a failed setup stops
    it. Returns the stop line. An engine fault writes a `crash` stop and re-raises."""
    plan = load_plan(plan_path)
    d = run_dir(root, plan["anchor"])
    os.makedirs(d, exist_ok=True)
    lp = ledger_path(root, plan["anchor"])
    lines = _read(lp)
    rows, done = _attempt_rows(lines), 0
    try:
        setup = next((l for l in reversed(lines) if l.get("event") == "setup" and l.get("ok")),
                     None)
        if setup is None:
            res = setup_check(root, plan, worker=True)
            setup = _append(lp, "setup", **res)
            if not res["ok"]:
                return _append(lp, "stop", reason="setup", detail="; ".join(res["problems"]))
        while True:
            if max_attempts is not None and done >= max_attempts:
                return _append(lp, "stop", reason="max_attempts", detail=f"{done} attempts")
            spent = sum(float(r.get("seconds") or 0) for r in rows) / 3600
            if spent >= plan["budget_hours"]:
                return _append(lp, "stop", reason="budget",
                               detail=f"{spent:.3f} of {plan['budget_hours']:g} hours")
            n = max([r["n"] for r in rows] or [0]) + 1
            rows.append(_attempt(root, plan, setup, rows, n, lp))
            done += 1
    except Exception as e:
        _append(lp, "stop", reason="crash", detail=f"{type(e).__name__}: {e}")
        raise


# ------------------------------------------------------------------------ status (read only)
def _ts(s):
    try:
        return datetime.datetime.strptime(str(s), "%Y-%m-%dT%H:%M:%SZ")
    except ValueError:
        return None


def _runs(root):
    base = os.path.join(root, "auto")
    return sorted(q for q in (os.listdir(base) if os.path.isdir(base) else [])
                  if os.path.isfile(ledger_path(root, q)))


def status(root, qid=None):
    if qid is None:
        runs = _runs(root)
        if not runs:
            raise E.CruxError("no autopilot run in this vault (no auto/<qid>/ledger.jsonl)")
        qid = max(runs, key=lambda q: os.path.getmtime(ledger_path(root, q)))
    if not os.path.isfile(ledger_path(root, qid)):
        raise E.CruxError(f"no autopilot run for {qid} (no {ledger_path(root, qid)})")
    lines, raw = _read(ledger_path(root, qid)), _raw_plan(root, qid)
    obj = (raw.get("objective") or "").split()
    direction = obj[1] if len(obj) > 1 else None
    try:
        bar = float(obj[2]) if len(obj) > 2 else None
    except ValueError:
        bar = None
    def num(k, default):
        try:
            return float(raw.get(k) or default)
        except ValueError:
            return float(default)
    keys = ("n", "id", "parent", "score", "status", "seconds", "at")
    atts = [{k: r.get(k) for k in keys} for r in _attempt_rows(lines)]
    kept = [a for a in atts if a["status"] == "kept" and isinstance(a["score"], (int, float))]
    setup = next((l for l in reversed(lines) if l.get("event") == "setup"), {})
    best = _best(kept, direction, num("min_gain", 0), setup.get("baseline"))
    times = [t for t in (_ts(l.get("at")) for l in lines) if t]
    elapsed = (times[-1] - times[0]).total_seconds() / 3600 if len(times) > 1 else 0.0
    stop = lines[-1] if lines and lines[-1].get("event") == "stop" else None

    live = (stop is None and bool(times) and (datetime.datetime.utcnow() - times[-1])
            .total_seconds() < 2 * num("attempt_minutes", 20) * 60)
    return {"anchor": qid, "mode": raw.get("mode") or "climb",
            "address": obj[0] if obj else None, "direction": direction, "bar": bar,
            "baseline": setup.get("baseline"),
            "best": ({"id": best["id"], "score": best["score"]}
                     if best and best["id"] != "base" else None),
            "attempts": atts,
            "attempts_per_hour": round(len(atts) / elapsed, 3) if elapsed > 0 else 0.0,
            "elapsed_hours": round(elapsed, 4), "budget_hours": num("budget_hours", 8),
            "live": live, "stop": stop}


def cockpit(root):
    runs = [status(root, q) for q in _runs(root)]
    return {"active": any(r["live"] for r in runs), "runs": runs}
