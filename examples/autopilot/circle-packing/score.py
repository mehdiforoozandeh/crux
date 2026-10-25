#!/usr/bin/env python3
"""Frozen scorer: pack 26 circles in the unit square, maximize the sum of radii.

    python3 score.py CANDIDATE        # a directory holding pack.py, or the pack.py file
    CRUX_CANDIDATE=CANDIDATE python3 score.py
    python3 score.py                  # under crux auto: CANDIDATE is the cwd (CRUX_WORKSPACE set)

The candidate is ONE program, CANDIDATE/pack.py. The scorer copies it into a fresh temp
directory and runs it with work/venv's python (numpy available) in a subprocess, with a
wall-time cap, an address-space cap, an output-size cap, one BLAS thread and -- when the
kernel allows it -- no network (`unshare -rn`). It reads ONLY the program's stdout, which must
be exactly one JSON object:

    {"circles": [[x, y, r], ... 26 triples ...]}

and nothing else: any other key, a second JSON value, or any other text on stdout fails the
candidate. stderr is the program's own log: never parsed, and its tail is returned only
when the candidate fails.

The check is EXACT. Every printed number is read as the exact rational value of its decimal
text (never through a float), and the scorer checks, with zero tolerance:
  exactly 26 triples; every value a finite JSON number; r > 0;
  r <= x <= 1 - r and r <= y <= 1 - r;
  (xi - xj)^2 + (yi - yj)^2 >= (ri + rj)^2 for every pair.
Touching is allowed; overlap by any amount, however small, is not. A candidate that runs a
float optimizer should shrink its radii by ~1e-12 before printing: that costs at most 26e-12
of score and makes rounding irrelevant. The score is the exact sum of the printed radii,
computed here; nothing the candidate reports is trusted.

Output (crux `run_scorer` contract): stdout is exactly one JSON object. On success, exit 0;
the objective is the leaf `sum_radii` ({"value": ...}); HIGHER IS BETTER, so the plan uses
`address:: sum_radii` and `direction:: max`. A score above the best known value is flagged
`"suspicious": true`. On a wrong candidate, exit 1; stdout is {"passed": false, "reason": ...}
with no `sum_radii` leaf, and the reason is also on stderr.

This parent process uses only the standard library and never imports the candidate.
"""
import decimal, hashlib, json, os, resource, shutil, signal, subprocess, sys, tempfile, time
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
VENV_PY = os.path.join(HERE, "work", "venv", "bin", "python")
PROGRAM = "pack.py"
WORKLOAD = "circle-packing-n26-unit-square-sum-radii"
N = 26
TIMEOUT_S = 60                 # wall-time cap on the candidate program (README: time cap)
MEM_BYTES = 4 * 1024 ** 3      # address-space cap on the candidate (RLIMIT_AS)
OUT_BYTES = 1 << 20            # stdout cap: the program's stdout file may not grow past 1 MiB
MAX_NUM_CHARS = 64             # a printed number longer than this is refused
MIN_EXP, MAX_EXP = -60, 1      # decimal exponent window of a printed number (stops 1e-99999999)
# Best known (README: the record). Packomania csqv, N=26, credited to Haowei Lin, 2026-08-01:
# 2.635983084919. AlphaEvolve's published construction sums to 2.6359830849176 but overlaps
# by ~1e-18 under this exact check. Anything above BEST_KNOWN is flagged, not refused.
BEST_KNOWN = Fraction("2.635983084919")
PRIOR_RECORD = Fraction("2.634")        # pre-AlphaEvolve record (AlphaEvolve paper; Friedman)


def fail(msg, **extra):
    sys.stderr.write(f"FAIL: {msg}\n")
    out = {"passed": False, "reason": msg[:2000], "workload": WORKLOAD}
    out.update(extra)
    sys.stdout.write(json.dumps(out) + "\n")
    sys.exit(1)


def sha(path):
    with open(path, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def tail(path, n=600):
    """The end of the candidate's stderr, for the worker to debug with. Never parsed."""
    try:
        with open(path, "rb") as f:
            f.seek(0, 2)
            f.seek(max(0, f.tell() - n))
            return f.read().decode("utf-8", "replace")
    except OSError:
        return ""


class Refuse(Exception):
    pass


def _refuse_constant(name):            # NaN, Infinity, -Infinity
    raise Refuse(f"non-finite number {name} in the output")


def _number(text):
    """A JSON number token -> its exact rational value. Text, not a float: the value checked
    is the value printed, with no rounding anywhere."""
    if len(text) > MAX_NUM_CHARS:
        raise Refuse(f"number token longer than {MAX_NUM_CHARS} characters")
    d = decimal.Decimal(text)
    if not d.is_finite():
        raise Refuse(f"non-finite number {text}")
    if d != 0 and not (MIN_EXP <= d.adjusted() <= MAX_EXP):
        raise Refuse(f"number {text} is outside the range this problem can use")
    return Fraction(d)


def parse(stdout_bytes):
    try:
        text = stdout_bytes.decode("utf-8")
    except UnicodeDecodeError:
        raise Refuse("stdout is not UTF-8")
    try:
        # json.loads refuses trailing text, so a second value or a printed "score" fails here.
        obj = json.loads(text, parse_float=_number, parse_int=_number,
                         parse_constant=_refuse_constant)
    except Refuse:
        raise
    except ValueError as e:
        raise Refuse(f"stdout is not exactly one JSON object ({e})")
    if not isinstance(obj, dict):
        raise Refuse("stdout JSON is not an object")
    if set(obj) != {"circles"}:
        raise Refuse(f"stdout object must have exactly one key 'circles'; got {sorted(obj)}")
    circles = obj["circles"]
    if not isinstance(circles, list):
        raise Refuse("'circles' is not a list")
    if len(circles) != N:
        raise Refuse(f"expected exactly {N} circles, got {len(circles)}")
    out = []
    for i, c in enumerate(circles):
        if not isinstance(c, list) or len(c) != 3:
            raise Refuse(f"circle {i} is not an [x, y, r] triple")
        if not all(isinstance(v, Fraction) for v in c):   # bools, strings, nulls land here
            raise Refuse(f"circle {i} holds a value that is not a JSON number")
        out.append(tuple(c))
    return out


def check(circles):
    """Exact feasibility. Returns (sum of radii, min containment slack, min pair slack)."""
    wall = None
    for i, (x, y, r) in enumerate(circles):
        if not r > 0:
            raise Refuse(f"circle {i}: radius {float(r)!r} is not > 0")
        s = min(x - r, 1 - r - x, y - r, 1 - r - y)
        if s < 0:
            raise Refuse(f"circle {i} at ({float(x)!r}, {float(y)!r}) r={float(r)!r} leaves "
                         f"the unit square by {float(-s):.3e}")
        wall = s if wall is None else min(wall, s)
    pair = None
    for i in range(N):
        xi, yi, ri = circles[i]
        for j in range(i + 1, N):
            xj, yj, rj = circles[j]
            gap2 = (xi - xj) ** 2 + (yi - yj) ** 2 - (ri + rj) ** 2
            if gap2 < 0:
                raise Refuse(f"circles {i} and {j} overlap (squared-distance shortfall "
                             f"{float(-gap2):.3e})")
            pair = gap2 if pair is None else min(pair, gap2)
    return sum(c[2] for c in circles), wall, pair


def network_blocker():
    """`unshare -rn` if this kernel lets an unprivileged user make a user+network namespace
    (README: network). Probed every run, never assumed."""
    exe = shutil.which("unshare")
    if not exe:
        return []
    try:
        r = subprocess.run([exe, "-rn", "true"], capture_output=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired):
        return []
    return [exe, "-rn"] if r.returncode == 0 else []


def limits():
    resource.setrlimit(resource.RLIMIT_FSIZE, (OUT_BYTES, OUT_BYTES))
    resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    if sys.platform.startswith("linux"):       # macOS refuses RLIMIT_AS; the cap is Linux-only
        resource.setrlimit(resource.RLIMIT_AS, (MEM_BYTES, MEM_BYTES))


def main():
    args = sys.argv[1:]
    workspace = os.environ.get("CRUX_WORKSPACE") or None
    # An argument, else CRUX_CANDIDATE, else -- only when crux auto started us, which it marks
    # by setting CRUX_WORKSPACE -- the cwd, which run_scorer sets to the worktree.
    cand = ((args[0] if args else "") or os.environ.get("CRUX_CANDIDATE")
            or (os.getcwd() if workspace else ""))
    if not cand:
        fail("no candidate: pass a path, set CRUX_CANDIDATE, or run under crux auto")
    cand = os.path.abspath(cand)
    prog = cand if os.path.isfile(cand) else os.path.join(cand, PROGRAM)
    if not os.path.isfile(prog):
        fail(f"no program: {prog} does not exist")
    if not os.access(VENV_PY, os.X_OK):
        fail(f"scorer not set up: {VENV_PY} missing (run setup.sh)")
    t_start = time.monotonic()
    prog_sha = sha(prog)
    blocker = network_blocker()

    base = workspace if workspace and os.path.isdir(workspace) else None
    tmp = tempfile.mkdtemp(prefix="circpack-", dir=base)
    try:
        run_dir = os.path.join(tmp, "run")
        os.mkdir(run_dir)
        shutil.copyfile(prog, os.path.join(run_dir, PROGRAM))
        out_path, err_path = os.path.join(tmp, "stdout"), os.path.join(tmp, "stderr")
        env = {"PATH": "/usr/bin:/bin", "HOME": run_dir, "TMPDIR": run_dir, "LANG": "C.UTF-8",
               "PYTHONHASHSEED": "0", "OMP_NUM_THREADS": "1", "OPENBLAS_NUM_THREADS": "1",
               "MKL_NUM_THREADS": "1", "FLEXIBLAS_NUM_THREADS": "1"}
        argv = blocker + [VENV_PY, "-I", PROGRAM]
        t0 = time.monotonic()
        with open(out_path, "wb") as out, open(err_path, "wb") as err:
            try:
                p = subprocess.Popen(argv, cwd=run_dir, env=env, stdin=subprocess.DEVNULL,
                                     stdout=out, stderr=err, preexec_fn=limits,
                                     start_new_session=True)
            except (OSError, subprocess.SubprocessError) as e:
                fail(f"scorer could not start the candidate: {e}")
            try:
                rc = p.wait(timeout=TIMEOUT_S)
            except subprocess.TimeoutExpired:
                os.killpg(p.pid, signal.SIGKILL)
                p.wait()
                fail(f"candidate ran past the {TIMEOUT_S}s time cap", candidate_sha256=prog_sha,
                     candidate_stderr_tail=tail(err_path))
            finally:
                try:                                 # nothing the candidate spawned survives
                    os.killpg(p.pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass
        cand_s = time.monotonic() - t0
        if rc != 0:
            why = (f"killed by signal {-rc}" if rc < 0 else f"exited {rc}")
            if rc == -signal.SIGXFSZ:
                why += f" (stdout passed the {OUT_BYTES}-byte cap)"
            fail(f"candidate program {why}", candidate_sha256=prog_sha,
                 candidate_stderr_tail=tail(err_path))
        with open(out_path, "rb") as f:
            raw = f.read(OUT_BYTES + 1)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    try:
        circles = parse(raw)
        total, wall, pair = check(circles)
    except Refuse as e:
        fail(str(e), candidate_sha256=prog_sha)
    value = float(total)
    result = {
        "sum_radii": {"value": value, "direction": "max", "unit": "sum of radii",
                      "exact": f"{total.numerator}/{total.denominator}"},
        "passed": True,
        "suspicious": total > BEST_KNOWN,
        "best_known": float(BEST_KNOWN),
        "gap_to_best_known": float(BEST_KNOWN - total),
        "workload": WORKLOAD,
        "checks": {"n": N, "tolerance": 0, "arithmetic": "exact rational of printed decimals",
                   "min_wall_slack": float(wall), "min_pair_sq_slack": float(pair)},
        "sandbox": {"timeout_s": TIMEOUT_S, "mem_bytes": MEM_BYTES if sys.platform.startswith("linux") else None, "stdout_cap": OUT_BYTES,
                    "network": "blocked (unshare -rn)" if blocker else "open"},
        "candidate": {"program": prog, "sha256": prog_sha, "run_s": round(cand_s, 3)},
        "scorer_wall_s": round(time.monotonic() - t_start, 3),
    }
    if result["suspicious"]:
        sys.stderr.write(f"WARNING: sum {value!r} beats the best known {float(BEST_KNOWN)!r}; "
                         "inspect the program before believing it\n")
    sys.stdout.write(json.dumps(result) + "\n")


if __name__ == "__main__":
    main()
