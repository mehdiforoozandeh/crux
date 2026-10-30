#!/usr/bin/env python3
"""Frozen scorer: M4 Weekly point-forecast accuracy (OWA) of a candidate forecasting program.

    python3 score.py CANDIDATE        # explicit path
    CRUX_CANDIDATE=CANDIDATE python3 score.py
    python3 score.py                  # under crux auto: CANDIDATE is the cwd (CRUX_WORKSPACE set)
    python3 score.py --forecasts FILE # score a forecast CSV in M4 format (ids W1..W359) directly

CANDIDATE is a directory holding `forecast.py`. The scorer copies the directory (minus .git)
into a fresh stage and runs, in work/venv, inside a sandbox:

    python forecast.py TRAIN_CSV OUT_CSV

TRAIN_CSV: header `id,y1,y2,...`; one row per series, oldest value first; rows have different
lengths. OUT_CSV: header `id,F1,...,F13`; one row per input id; 13 finite numbers each.
The program runs twice: once on each series minus its last 13 values (the `val_owa` run), and
once on the full train series (the `owa` run, scored against the official M4 test file).

Output (crux `run_scorer` contract): stdout is exactly one JSON object. On success, exit 0;
the search objective is the leaf `val_owa` (LOWER IS BETTER; Naive2 = 1.000 by definition),
so the plan uses `address:: val_owa` and `direction:: min`. The leaf `owa` (the official M4
test set) is in the same object and is read once, at the end of a search, never steered on.
On a wrong candidate, exit 1; stdout is {"passed": false, "reason": ...} with no metric
leaves, and the reason is also on stderr.

The parent (this file) is stdlib-only and never imports the candidate. It reads the test file
only after both candidate runs have ended. The candidate runs under bubblewrap: no network,
the filesystem read-only, /home, /scratch, /project and /nearline hidden except this
directory (read-only) and its own stage, and work/secret (test file, published forecasts)
hidden.
"""
import csv, hashlib, json, math, os, random, shutil, signal, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.realpath(__file__))   # real path: the sandbox hides symlinks
WORK = os.path.join(HERE, "work")
SECRET = os.path.join(WORK, "secret")
VENV_PY = os.path.join(WORK, "venv", "bin", "python")
TRAIN = os.path.join(SECRET, "Weekly-train.csv")
TEST = os.path.join(SECRET, "Weekly-test.csv")
PUBLISHED = os.path.join(SECRET, "published")
SHA = {"Weekly-train.csv": "d478d3f6ed673e6ed3c2cb0fbed5425f72eedd51318ebebeb0b5ecfcefc37714",
       "Weekly-test.csv": "3b2bc4be8e636e802260dcd843ca3c5da40536a1fbe1ecb3229a97dae4f44688"}
H = 13                 # M4 Weekly horizon
N_SERIES = 359
ID_SEED = 20180101     # fixed shuffle of the anonymised ids given to the candidate
RUN_TIMEOUT = 110      # seconds of wall time per candidate run (two runs per scorer call)
TIMEOUT = 280          # seconds, whole scorer
COPY_TOL = 1e-6        # relative: a forecast value "equals" a reference value
COPY_FRAC = 0.25       # fail when this share of all values equals the truth or a submission
COPY_REFS = ("118", "235")   # published submissions a candidate must not replay
WORKLOAD = "m4-weekly-359x13"
# Published M4 Weekly OWA (M4-methods "Evaluation and Ranks.xlsx", sheet Point
# Forecasts-Frequency, at the pinned commit). See README.
BAR = {"235_darin_stellwagen_best_weekly": 0.739, "036_petropoulos_svetunkov": 0.751,
       "118_smyl_overall_winner": 0.851, "Theta": 0.971, "Naive2": 1.0}

PROCS = []


def fail(msg):
    for p in PROCS:
        if p.poll() is None:
            try:
                os.killpg(p.pid, signal.SIGKILL)
            except OSError:
                pass
    sys.stderr.write(f"FAIL: {msg}\n")
    sys.stdout.write(json.dumps({"passed": False, "reason": msg[:2000],
                                 "workload": WORKLOAD}) + "\n")
    sys.exit(1)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def read_m4(path):
    """{id: [floats]} from an M4 wide CSV (first column the id, trailing cells empty)."""
    out = {}
    with open(path, newline="") as f:
        rows = csv.reader(f)
        next(rows)
        for r in rows:
            vals = [float(x) for x in r[1:] if x not in ("", "NA")]
            out[r[0]] = vals
    return out


# ----------------------------------------------------------------------------- metric
# M4's own definitions ("Benchmarks and Evaluation.R" in Mcompetitions/M4-methods). Weekly
# series have Frequency 1 in M4-info.csv, so MASE scales by the in-sample one-step naive
# error (m = 1), and Naive2 (naive on the seasonally adjusted series) has no seasonal
# adjustment: it repeats the last observed value.

def errors(fc, truth, insample):
    """Lists of per-point sMAPE and MASE terms over every series and horizon."""
    sm, ms = [], []
    for k, y in truth.items():
        x = insample[k]
        scale = math.fsum(abs(x[j] - x[j - 1]) for j in range(1, len(x))) / (len(x) - 1)
        for a, f in zip(y, fc[k]):
            d = abs(a) + abs(f)
            sm.append(0.0 if d == 0 else 200.0 * abs(a - f) / d)
            ms.append(abs(a - f) / scale)
    return sm, ms


def owa(fc, truth, insample):
    sm, ms = errors(fc, truth, insample)
    n2 = {k: [insample[k][-1]] * H for k in truth}
    sm2, ms2 = errors(n2, truth, insample)
    s, m = math.fsum(sm) / len(sm), math.fsum(ms) / len(ms)
    s2, m2 = math.fsum(sm2) / len(sm2), math.fsum(ms2) / len(ms2)
    return {"value": round((s / s2 + m / m2) / 2, 6), "direction": "min",
            "unit": "OWA (Naive2 = 1)", "smape": round(s, 4), "mase": round(m, 4),
            "naive2_smape": round(s2, 4), "naive2_mase": round(m2, 4)}


def copy_share(fc, ref):
    """Share of all forecast values equal (to COPY_TOL, relative) to the reference's."""
    hit = tot = 0
    for k, f in fc.items():
        for a, b in zip(f, ref[k]):
            tot += 1
            hit += abs(a - b) <= COPY_TOL * max(1.0, abs(b))
    return hit / tot


# ----------------------------------------------------------------------------- candidate run

def sandbox_argv(stage):
    """bubblewrap: no network; the filesystem read-only; /home, /scratch, /project and
    /nearline (and $HOME) replaced by empty tmpfs, with only this scorer's directory (read-only)
    and the stage (writable) bound back in; work/secret replaced by an empty tmpfs last.
    Returns (argv prefix, description)."""
    if os.environ.get("M4_NO_SANDBOX") == "1":
        return [], "none (M4_NO_SANDBOX=1)"
    bwrap = shutil.which("bwrap")
    if not bwrap:
        fail("bwrap (bubblewrap) not found: the candidate cannot run without its sandbox "
             "(set M4_NO_SANDBOX=1 only for a local, trusted run)")
    argv = [bwrap, "--ro-bind", "/", "/", "--dev", "/dev", "--proc", "/proc", "--tmpfs", "/tmp",
            "--unshare-net", "--unshare-pid", "--unshare-ipc", "--unshare-uts",
            "--die-with-parent", "--new-session"]
    hidden = []
    for d in ("/home", "/scratch", "/project", "/nearline", os.path.expanduser("~")):
        r = os.path.realpath(d)
        if os.path.isdir(r) and r != "/" and not any(r.startswith(h + os.sep) for h in hidden):
            argv += ["--tmpfs", r]
            hidden.append(r)
    here, stage, secret = (os.path.realpath(p) for p in (HERE, stage, SECRET))
    argv += ["--ro-bind", here, here, "--bind", stage, stage, "--tmpfs", secret]
    return argv + ["--"], ("bwrap: no network; read-only fs; hidden " + ", ".join(hidden)
                           + f"; then bound back: {here} (ro), stage (rw); hidden {secret}")


def run_candidate(cand, tmp, name, series):
    """Stage a fresh copy of the candidate, give it `series`, return ({id: 13 floats}, s)."""
    stage = os.path.join(tmp, name)
    shutil.copytree(cand, os.path.join(stage, "cand"), symlinks=True,
                    ignore=shutil.ignore_patterns(".git", "__pycache__"))
    os.makedirs(os.path.join(stage, "home"))
    inp, out = os.path.join(stage, "train.csv"), os.path.join(stage, "forecast.csv")
    width = max(len(v) for v in series.values())
    with open(inp, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id"] + [f"y{i}" for i in range(1, width + 1)])
        for k, v in series.items():
            w.writerow([k] + [repr(x) for x in v])
    ncpu = len(os.sched_getaffinity(0)) if hasattr(os, "sched_getaffinity") else os.cpu_count()
    env = {"PATH": "/usr/bin:/bin", "LANG": "C.UTF-8", "HOME": os.path.join(stage, "home"),
           "TMPDIR": stage, "PYTHONHASHSEED": "0", "PYTHONDONTWRITEBYTECODE": "1",
           "MPLCONFIGDIR": os.path.join(stage, "home"), "M4_HORIZON": str(H),
           "M4_CPUS": str(ncpu), "CRUX_SEED": os.environ.get("CRUX_SEED", "0")}
    for v in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS",
              "FLEXIBLAS_NUM_THREADS", "NUMEXPR_NUM_THREADS"):
        env[v] = "1"
    prefix, desc = sandbox_argv(stage)
    log = open(os.path.join(stage, "log.txt"), "w+")
    t0 = time.perf_counter()
    p = subprocess.Popen(prefix + [VENV_PY, "forecast.py", inp, out],
                         cwd=os.path.join(stage, "cand"), env=env, stdin=subprocess.DEVNULL,
                         stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    PROCS.append(p)
    try:
        p.wait(timeout=RUN_TIMEOUT)
    except subprocess.TimeoutExpired:
        os.killpg(p.pid, signal.SIGKILL); p.wait()
        fail(f"{name} run: candidate exceeded the {RUN_TIMEOUT}s wall-time cap")
    secs = time.perf_counter() - t0
    log.seek(0); tail = log.read()[-1500:]; log.close()
    if tail:
        sys.stderr.write(f"--- candidate {name} run output (tail) ---\n{tail}\n")
    if p.returncode != 0:
        fail(f"{name} run: forecast.py exited {p.returncode}: {tail[-600:]}")
    return parse_forecasts(out, set(series), name), secs, desc


def parse_forecasts(path, ids, name):
    if not os.path.isfile(path):
        fail(f"{name} run: no forecast file written")
    fc = {}
    with open(path, newline="") as f:
        rows = csv.reader(f)
        head = next(rows, None)
        if head is None or [c.strip() for c in head] != ["id"] + [f"F{i}" for i in range(1, H + 1)]:
            fail(f"{name} run: header must be id,F1,...,F{H}; got {head}")
        for r in rows:
            if not r:
                continue
            if len(r) != H + 1:
                fail(f"{name} run: row {r[:1]} has {len(r) - 1} values, want {H}")
            k = r[0].strip()
            if k not in ids:
                fail(f"{name} run: unknown series id {k!r}")
            if k in fc:
                fail(f"{name} run: series {k} appears twice")
            try:
                v = [float(x) for x in r[1:]]
            except ValueError:
                fail(f"{name} run: series {k} has a value that is not a number")
            if not all(math.isfinite(x) for x in v):
                fail(f"{name} run: series {k} has a NaN or infinite forecast")
            fc[k] = v
    if len(fc) != len(ids):
        fail(f"{name} run: forecasts for {len(fc)} of {len(ids)} series")
    return fc


# ----------------------------------------------------------------------------- main

def check_data():
    if not os.path.exists(VENV_PY):
        fail("work/venv missing: run setup.sh first")
    for p in (TRAIN, TEST):
        if not os.path.isfile(p) or sha(p) != SHA[os.path.basename(p)]:
            fail(f"{os.path.basename(p)} missing or its sha256 differs: run setup.sh")


def score_file(path):
    """--forecasts: score an M4-format forecast CSV (ids W1..W359) against the test file."""
    train, test = read_m4(TRAIN), read_m4(TEST)
    fc = {k: v[:H] for k, v in read_m4(path).items() if k in test}
    if set(fc) != set(test) or any(len(v) != H for v in fc.values()):
        fail(f"{path}: needs {H} values for each of the {len(test)} Weekly ids")
    doc = {"owa": owa(fc, test, train), "passed": True, "workload": WORKLOAD,
           "forecasts": {"path": os.path.abspath(path), "sha256": sha(path)}}
    sys.stdout.write(json.dumps(doc) + "\n")


def main():
    args = sys.argv[1:]
    if args[:1] == ["--forecasts"] and len(args) == 2:
        check_data()
        return score_file(args[1])
    workspace = os.environ.get("CRUX_WORKSPACE") or None
    # An argument, else CRUX_CANDIDATE, else -- only when crux auto started us, which it
    # marks by setting CRUX_WORKSPACE -- the cwd, which run_scorer sets to the worktree.
    cand = ((args[0] if args else "") or os.environ.get("CRUX_CANDIDATE")
            or (os.getcwd() if workspace else ""))
    if not cand:
        fail("no candidate: pass a path, set CRUX_CANDIDATE, or run under crux auto")
    cand = os.path.abspath(cand)
    if not os.path.isfile(os.path.join(cand, "forecast.py")):
        fail(f"no forecast.py under candidate {cand}")
    check_data()
    signal.signal(signal.SIGALRM, lambda *_: fail(f"scorer timed out after {TIMEOUT}s"))
    signal.alarm(TIMEOUT)
    started = time.perf_counter()

    train = read_m4(TRAIN)
    if len(train) != N_SERIES:
        fail(f"train has {len(train)} series, want {N_SERIES}")
    order = sorted(train, key=lambda k: int(k[1:]))
    random.Random(ID_SEED).shuffle(order)
    anon = {k: f"s{i:03d}" for i, k in enumerate(order, 1)}       # M4 id -> given id
    back = {v: k for k, v in anon.items()}
    val_in = {anon[k]: train[k][:-H] for k in order}
    full_in = {anon[k]: train[k] for k in order}

    if workspace:
        os.makedirs(workspace, exist_ok=True)
    tmp = os.path.realpath(tempfile.mkdtemp(prefix="m4w_score_", dir=workspace))
    try:
        val_fc, val_s, desc = run_candidate(cand, tmp, "val", val_in)
        test_fc, test_s, _ = run_candidate(cand, tmp, "test", full_in)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # Only now, with no candidate process alive, does the parent read the test file.
    test = read_m4(TEST)
    val_fc = {back[k]: v for k, v in val_fc.items()}
    test_fc = {back[k]: v for k, v in test_fc.items()}
    val_truth = {k: train[k][-H:] for k in train}
    val_ins = {k: train[k][:-H] for k in train}
    copies = {"val_truth": copy_share(val_fc, val_truth), "test_truth": copy_share(test_fc, test)}
    for name in COPY_REFS:
        ref = read_m4(os.path.join(PUBLISHED, f"{name}.csv"))
        copies[f"submission_{name}"] = copy_share(test_fc, ref)
    for name, share in copies.items():
        if share >= COPY_FRAC:
            fail(f"forecasts reproduce {name}: {100 * share:.1f}% of values are equal")

    wall = time.perf_counter() - started
    doc = {
        "owa": owa(test_fc, test, train),
        "val_owa": owa(val_fc, val_truth, val_ins),
        "passed": True,
        "workload": {"id": WORKLOAD, "series": N_SERIES, "horizon": H,
                     "train_sha256": SHA["Weekly-train.csv"],
                     "test_sha256": SHA["Weekly-test.csv"],
                     "val": f"each train series minus its last {H} values"},
        "bar": BAR,
        "checks": {"format": "pass", "copy_share": {k: round(v, 4) for k, v in copies.items()},
                   "sandbox": desc},
        "runs": {"val_s": round(val_s, 2), "test_s": round(test_s, 2),
                 "cap_s": RUN_TIMEOUT},
        "candidate": {"path": cand, "forecast_py_sha256": sha(os.path.join(cand, "forecast.py"))},
        "scorer_wall_s": round(wall, 1),
    }
    sys.stderr.write(f"owa {doc['owa']['value']}  val_owa {doc['val_owa']['value']}  "
                     f"runs {val_s:.1f}s + {test_s:.1f}s  scorer wall {wall:.1f}s\n")
    sys.stdout.write(json.dumps(doc) + "\n")


if __name__ == "__main__":
    main()
