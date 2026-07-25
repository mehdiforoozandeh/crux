#!/usr/bin/env python3
"""crux update check — is a newer crux published?

**It never installs anything.** crux tells you a new version exists and hands you the exact
command for your install; applying it is your call (or your agent's). An engine that
rewrites itself under a running research program is precisely the wrong shape for a lab
notebook — a vault records the engine version its verdicts were produced with, and that
should change because someone decided so, not because a background thread did.

Deliberately timid. Three properties matter more than freshness:

1. **It never blocks.** The notice a user sees is printed FROM THE CACHE — it reports what
   a previous invocation learned. The network call runs in a daemon thread with a short
   timeout, purely to refresh the cache for next time. A hung endpoint costs nothing.
2. **It never fails a command.** Every path swallows its exceptions; a broken network, a
   read-only home directory, or garbage in the cache all degrade to silence.
3. **It is easy to switch off.** CRUX_NO_UPDATE_CHECK=1 disables both the request and
   the notice.

At most one request per day, to one endpoint. Stdlib only, like the rest of the engine.
"""
import os, re, json, time, threading, urllib.request

LATEST_URL = "https://api.github.com/repos/mehdiforoozandeh/crux/releases/latest"
INTERVAL   = 86400          # seconds between checks
TIMEOUT    = 1.5            # seconds before the request is abandoned
OPT_OUT    = "CRUX_NO_UPDATE_CHECK"


# ----------------------------------------------------------------------------- pure logic
def parse_version(s):
    """('v0.5.0' | '0.5.0') -> (0, 5, 0); anything unparseable -> None."""
    m = re.match(r"^v?(\d+)\.(\d+)\.(\d+)", str(s or "").strip())
    return tuple(int(x) for x in m.groups()) if m else None


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    return bool(a and b and a > b)


# ----------------------------------------------------------------------------- install shape
# crux NEVER updates itself. It says a new version exists and hands over the exact command
# for THIS install — a self-mutating engine is the last thing a research notebook should be,
# and a `git pull` fired mid-project could land an engine change under a live vault without
# anyone deciding to. Updating stays the human's (or their agent's) call.
def detect_install(engine_dir=None):
    """('clone', repo_root) | ('skills', skills_dir) | ('unknown', path).

    realpath first: `install.sh` symlinks the skills into a clone, so the import path is the
    symlink while the thing you'd actually `git pull` is its target."""
    here = os.path.realpath(engine_dir or os.path.dirname(os.path.abspath(__file__)))
    # <root>/skills/crux/scaffold  ->  <root>
    root = os.path.dirname(os.path.dirname(os.path.dirname(here)))
    if os.path.isdir(os.path.join(root, ".git")):
        return "clone", root
    if os.path.basename(os.path.dirname(os.path.dirname(here))) == "skills":
        return "skills", os.path.dirname(os.path.dirname(here))
    return "unknown", here


def update_command(kind, path):
    """The one command that updates THIS install."""
    if kind == "clone":
        return f"git -C {path} pull --ff-only"
    if kind == "skills":
        return "npx skills update"
    return "npx skills update   (or `git pull` in your crux clone)"


def notice(current, latest, install=None):
    kind, path = install or detect_install()
    return (f"crux: v{latest} is available (you have v{current}). Ask your agent to update "
            f"crux, or run:  {update_command(kind, path)}   ·   silence: {OPT_OUT}=1")


def pending_notice(current, cache, install=None):
    """What to print, decided from the cache alone — no network, so this never blocks.
    The opt-out is enforced by the caller (maybe_check), not here."""
    latest = (cache or {}).get("latest")
    return notice(current, latest, install) if latest and is_newer(latest, current) else None


def should_check(now_ts, cache, env=None):
    """Is a fresh request due? Opted out -> never. No usable timestamp -> yes."""
    env = os.environ if env is None else env
    if env.get(OPT_OUT):
        return False
    try:
        return (now_ts - float((cache or {}).get("checked"))) >= INTERVAL
    except (TypeError, ValueError):
        return True


# ----------------------------------------------------------------------------- cache
def cache_path(env=None):
    env = os.environ if env is None else env
    base = env.get("XDG_CACHE_HOME") or os.path.join(os.path.expanduser("~"), ".cache")
    return os.path.join(base, "crux", "update.json")


def read_cache(path=None):
    try:
        with open(path or cache_path(), encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}   # missing / unreadable / corrupt all mean the same thing: we know nothing


def write_cache(data, path=None):
    """Atomic: write a sibling temp file, then rename over the target. Two crux processes can
    easily overlap (a `serve` in one terminal, a `close` in another), and an in-place truncate
    lets the other one read a half-written file — which read_cache would treat as 'we know
    nothing', silently re-arming the check."""
    path = path or cache_path()
    tmp = path + ".tmp%d" % os.getpid()
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, path)
    except Exception:
        try:
            os.remove(tmp)
        except OSError:
            pass
        # a cache we cannot write is a cache we do without


# ----------------------------------------------------------------------------- network
def fetch_latest(timeout=TIMEOUT, opener=None):
    """The published release tag, or None. NEVER raises — that is the whole contract.
    `opener` is the injection point the selftest uses so no test ever hits the network."""
    try:
        if opener is not None:
            return opener(timeout=timeout)
        req = urllib.request.Request(LATEST_URL, headers={
            "Accept": "application/vnd.github+json", "User-Agent": "crux-update-check"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return (json.loads(r.read().decode("utf-8")) or {}).get("tag_name")
    except Exception:
        return None


def check_now(current, path=None, fetcher=None, timeout=TIMEOUT):
    """Run one check and record the outcome. Returns the cache dict; never raises.
    A failed fetch still stamps `checked`, so a flaky network can't turn into a request
    on every single invocation."""
    tag = fetch_latest(timeout=timeout, opener=fetcher)
    pv = parse_version(tag) if tag else None
    latest = ".".join(str(x) for x in pv) if pv else None
    data = {"checked": time.time(), "current": current, "latest": latest,
            "available": bool(latest and is_newer(latest, current))}
    write_cache(data, path)
    return data


def maybe_check(current, env=None, path=None, fetcher=None):
    """Called once per CLI invocation. Returns the notice to print (from the cache, so the
    command is never waiting on a network round-trip) and, when a check is due, refreshes
    that cache in the background.

    Two details are load-bearing:

    * The 24h window is CLAIMED FIRST, before the request goes out. If the stamp were only
      written by a successful fetch, a short command that exits before the reply lands would
      leave `checked` unset — and every single `crux` invocation would fire another request
      that it then abandons. Claiming up front bounds it to one attempt per day, come what may.
    * The worker is NOT a daemon thread. A daemon dies the moment the main thread returns,
      which for a fast command is essentially always — so the answer would never be recorded
      and the notice would never appear. A normal thread lets the interpreter wait for it,
      bounded by the request's own short timeout, and only on the day the check is due. The
      command's output is already printed by then; only process exit waits.
    """
    env = os.environ if env is None else env
    if env.get(OPT_OUT):
        return None
    path = path or cache_path(env)
    cache = read_cache(path)
    if should_check(time.time(), cache, env):
        claimed = dict(cache)
        claimed["checked"] = time.time()
        write_cache(claimed, path)
        threading.Thread(target=check_now, args=(current, path, fetcher)).start()
    return pending_notice(current, cache)
