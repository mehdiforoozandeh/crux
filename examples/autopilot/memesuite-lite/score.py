#!/usr/bin/env python3
"""Frozen scorer: wall time of memesuite-lite's tomtom on a fixed all-vs-all workload.

    python3 score.py CANDIDATE          # or: CRUX_CANDIDATE=CANDIDATE python3 score.py

CANDIDATE is a memesuite-lite checkout. Only CANDIDATE/memelite/tomtom.py is read from it;
every other file (the rest of the package, the tests, this scorer, reference/) is frozen.

Success: exit 0, and the last stdout line is one number, the median seconds of REPEATS timed
runs. LOWER IS BETTER. Failure: exit 1, nothing on stdout, the reason on stderr. A candidate
fails when the frozen pytest suite fails, or when any output differs by one bit from the
reference made by the pinned pre-PR-#21 code (reference/expected.json), or when it returns
where the reference raised (or the other way round).

The parent (this file, stdlib only, any python3) never imports the candidate. A child worker
in work/venv runs the candidate and writes every output to .npy; the parent hashes those files
itself and times each run with its own clock, so the candidate can patch neither the clock
nor the hash.

`--make-reference` regenerates reference/expected.json from work/cand-baseline (the pinned
code). Run it only on purpose; it is how the reference was made.
"""
import hashlib, json, os, shutil, signal, statistics, subprocess, sys, tempfile, time

HERE = os.path.dirname(os.path.abspath(__file__))
WORK = os.path.join(HERE, "work")
FROZEN = os.path.join(WORK, "frozen")
VENV_PY = os.path.join(WORK, "venv", "bin", "python")
REFERENCE = os.path.join(HERE, "reference", "expected.json")

N_MOTIFS = 1000          # all-vs-all, query set == target set (as PR #21's JASPAR benchmark)
REPEATS = 5              # timed runs; the median is the score (see README for the noise data)
WARM_SEED = 100          # one untimed full-size run first, so every numba kernel is compiled
BENCH_SEEDS = list(range(REPEATS))
REF_SEEDS = list(range(10))   # reference covers up to 10 repeats
CASE_THREADS = (1, 4)    # golden/edge cases must be identical at both thread counts
TIMEOUT = 290            # seconds, whole scorer

# ----------------------------------------------------------------------------- worker
# Runs inside work/venv with the staged package on sys.path. Its own stdout is the
# protocol channel; anything the candidate prints is sent to stderr.

def _motifs(n, seed):
    """JASPAR-like count matrices: widths 6-17, 10-59 sites per column, so columns repeat."""
    import numpy
    s = numpy.random.RandomState(seed)
    out = []
    for _ in range(n):
        w = s.randint(6, 18); k = s.randint(10, 60)
        P = s.dirichlet(numpy.full(4, 0.4), size=w)
        C = numpy.array([s.multinomial(k, p) for p in P], dtype="float64")
        out.append(numpy.ascontiguousarray((C / k).T))
    return out


def _edge_cases():
    """Small and bad inputs. Each returns (Qs, Ts, kwargs). Kept only where the pinned code
    is deterministic; inputs that read uninitialised or out-of-bounds memory are excluded."""
    import numpy
    s = numpy.random.RandomState(7)
    def r(w, a=0.5):
        return numpy.ascontiguousarray(s.dirichlet(numpy.ones(4) * a, size=w).T)
    Q = [r(8), r(5), r(12)]; T = [r(10), r(6), r(15), r(4)]
    nanq = r(6); nanq[:, 2] = numpy.nan
    neg = r(6); neg[0, 1] = -0.5
    zcol = numpy.concatenate([r(3), numpy.zeros((4, 2)), r(3)], axis=1)
    return {
        "edge/empty_query_list": ([], T, {}),
        "edge/all_zero_query": ([numpy.zeros((4, 6))], T, {}),
        "edge/all_zero_targets": (Q, [numpy.zeros((4, 6))], {}),
        "edge/nan_column": ([nanq], T, {}),
        "edge/one_d_query": ([numpy.ones(4) / 4], T, {}),
        "edge/n_target_bins_1": (Q, T, {"n_target_bins": 1}),
        "edge/zero_column": ([zcol], T, {}),
        "edge/negative_entry": ([neg], T, {}),
        "edge/int_pwm": ([(r(6) > 0.3).astype("int64")], T, {}),
        "edge/n_nearest_0": (Q, T, {"n_nearest": 0}),
        "edge/n_nearest_big": (Q, T, {"n_nearest": 100}),
        "edge/n_median_bins_1": (Q, T, {"n_median_bins": 1}),
        "edge/n_cache_1": (Q, T, {"n_cache": 1}),
        "edge/identical_motifs": ([Q[0]] * 5, [Q[0]] * 3, {}),
        "edge/uniform_motifs": ([numpy.full((4, 7), 0.25)], [numpy.full((4, 5), 0.25), r(5)], {}),
        "edge/long_query": ([r(120)], T, {}),
    }


def worker(stage, outdir):
    import numpy
    proto = os.fdopen(os.dup(1), "w", buffering=1)
    os.dup2(2, 1)                                   # candidate prints go to stderr
    sys.path.insert(0, stage)
    import importlib
    mod = importlib.import_module("memelite.tomtom")
    if not os.path.realpath(mod.__file__).startswith(os.path.realpath(stage) + os.sep):
        raise SystemExit(f"imported tomtom from {mod.__file__}, not from the stage")
    sys.path.insert(0, os.path.join(stage, "tests"))
    from tests._golden_inputs import TOMTOM_CASES, build_tomtom

    def emit(**kw):
        proto.write(json.dumps(kw) + "\n")

    def save(name, out):
        path = os.path.join(outdir, name.replace("/", "__") + ".npy")
        numpy.save(path, numpy.ascontiguousarray(numpy.stack(out)))
        return path

    import numba
    threads = sorted({min(n, numba.config.NUMBA_NUM_THREADS) for n in CASE_THREADS})
    cases = {"golden/" + c[0]: build_tomtom(c) for c in TOMTOM_CASES}
    cases.update(_edge_cases())
    for name, (Qs, Ts, kw) in cases.items():
        for nj in threads:
            try:
                out = mod.tomtom(Qs, Ts, n_jobs=nj, **kw)
            except Exception as e:                  # failure behaviour is part of the output
                emit(case=name, threads=nj, raised=type(e).__name__)
                continue
            emit(case=name, threads=nj, file=save(f"{name}@{nj}", out))

    X = _motifs(N_MOTIFS, WARM_SEED)
    emit(warm=WARM_SEED, file=save("warm", mod.tomtom(X, X, n_jobs=1)))
    for line in sys.stdin:                          # "gen SEED" then "go"
        cmd = line.split()
        if cmd[0] == "gen":
            seed = int(cmd[1]); X = _motifs(N_MOTIFS, seed)
            emit(ready=seed)
        elif cmd[0] == "go":
            out = mod.tomtom(X, X, n_jobs=1)
            emit(done=seed)
            emit(seed=seed, file=save(f"bench_{seed}", out))
            del out
        elif cmd[0] == "quit":
            break

# ----------------------------------------------------------------------------- parent

PROCS = []


def fail(msg):
    for p in PROCS:
        if p.poll() is None:
            p.kill()
    sys.stderr.write(f"FAIL: {msg}\n")
    sys.exit(1)


def sha(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def tree_digest(root):
    """sha256 over every frozen file except memelite/tomtom.py (the editable one)."""
    rels = []
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x != "__pycache__"]
        rels += [os.path.relpath(os.path.join(d, f), root) for f in files]
    h = hashlib.sha256()
    for rel in sorted(rels):
        if rel != os.path.join("memelite", "tomtom.py"):
            h.update(rel.encode() + b"\0" + sha(os.path.join(root, rel)).encode() + b"\n")
    return h.hexdigest()


def stage_candidate(cand, tmp):
    src = os.path.join(cand, "memelite", "tomtom.py")
    if not os.path.isfile(src):
        fail(f"no memelite/tomtom.py under candidate {cand}")
    stage = os.path.join(tmp, "stage")
    ign = shutil.ignore_patterns("__pycache__")
    shutil.copytree(os.path.join(FROZEN, "memelite"), os.path.join(stage, "memelite"), ignore=ign)
    shutil.copytree(os.path.join(FROZEN, "tests"), os.path.join(stage, "tests"), ignore=ign)
    shutil.copyfile(src, os.path.join(stage, "memelite", "tomtom.py"))
    return stage


def child_env(tmp):
    env = {k: v for k, v in os.environ.items() if not k.startswith(("PYTHON", "NUMBA_"))}
    env["NUMBA_CACHE_DIR"] = os.path.join(tmp, "numba-cache")   # shared by tests and worker
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def run_tests(stage, env):
    p = subprocess.Popen([VENV_PY, "-m", "pytest", "-q", "-x", "-p", "no:cacheprovider",
                          "tests", "--ignore=tests/test_cli.py"],
                         cwd=stage, env=dict(env, PYTHONPATH=stage),
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    PROCS.append(p)
    out, _ = p.communicate()
    if p.returncode != 0:
        fail("frozen test suite failed:\n" + out[-3000:])


def check_bench(bench, ref_bench):
    """Fail at the first benchmark output that is not bit-identical (no-op when making the
    reference)."""
    for k, v in (bench.items() if ref_bench else ()):
        if ref_bench[k] != v:
            fail(f"benchmark seed {k}: output is not bit-identical to the reference")


def run_worker(stage, tmp, env, seeds, ref_bench=None):
    outdir = os.path.join(tmp, "out"); os.makedirs(outdir)
    p = subprocess.Popen([VENV_PY, os.path.abspath(__file__), "--worker", stage, outdir],
                         cwd=tmp, env=env, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                         text=True, bufsize=1)
    PROCS.append(p)

    def recv():
        line = p.stdout.readline()
        if not line:
            p.wait()
            fail(f"candidate worker died (exit {p.returncode}); see stderr above")
        return json.loads(line)

    def send(s):
        p.stdin.write(s + "\n"); p.stdin.flush()

    cases, bench, times = {}, {}, []
    while True:
        m = recv()
        if "case" in m:
            v = {"raises": True} if "raised" in m else {"sha256": sha(m["file"])}
            key = m["case"]
            if key in cases and cases[key] != v:
                fail(f"{key}: output differs between {CASE_THREADS} threads")
            cases[key] = v
            if "file" in m:
                os.unlink(m["file"])
        elif "warm" in m:
            bench[str(m["warm"])] = sha(m["file"]); os.unlink(m["file"])
            check_bench(bench, ref_bench)
            break
    for seed in seeds:
        send(f"gen {seed}"); recv()
        t0 = time.perf_counter(); send("go"); m = recv(); t1 = time.perf_counter()
        assert m.get("done") == seed
        times.append(t1 - t0)
        m = recv(); bench[str(seed)] = sha(m["file"]); os.unlink(m["file"])
        check_bench(bench, ref_bench)
    send("quit"); p.wait()
    return cases, bench, times


def main():
    args = sys.argv[1:]
    if args[:1] == ["--worker"]:
        return worker(args[1], args[2])
    make_ref = args[:1] == ["--make-reference"]
    if make_ref:
        cand = os.path.join(WORK, "cand-baseline")
    else:
        cand = (args[0] if args else "") or os.environ.get("CRUX_CANDIDATE")
        if not cand:
            fail("no candidate: pass a path, or set CRUX_CANDIDATE")
    cand = os.path.abspath(cand)
    if not os.path.exists(VENV_PY):
        fail("work/venv missing: run setup.sh first")

    signal.signal(signal.SIGALRM, lambda *_: fail(f"scorer timed out after {TIMEOUT}s"))
    signal.alarm(TIMEOUT)
    started = time.perf_counter()
    tmp = tempfile.mkdtemp(prefix="msl_score_")
    try:
        frozen = tree_digest(FROZEN)
        if not make_ref:
            with open(REFERENCE) as f:
                ref = json.load(f)
            if frozen != ref["frozen_tree"]:
                fail("work/frozen does not match the reference; re-run setup.sh")
        stage = stage_candidate(cand, tmp)
        env = child_env(tmp)
        run_tests(stage, env)
        seeds = REF_SEEDS if make_ref else BENCH_SEEDS
        cases, bench, times = run_worker(stage, tmp, env, seeds,
                                         None if make_ref else ref["bench"])
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    if make_ref:
        doc = {"pinned_commit": "dd413f654eb9fb9b095fe61edd69b37c53962367",
               "frozen_tree": frozen, "n_motifs": N_MOTIFS, "case_threads": CASE_THREADS,
               "versions": open(os.path.join(WORK, "versions.txt")).read().split("\n"),
               "cases": cases, "bench": bench,
               "baseline_seconds": {str(s): round(t, 4) for s, t in zip(seeds, times)}}
        with open(REFERENCE, "w") as f:
            json.dump(doc, f, indent=1, sort_keys=True)
        sys.stderr.write(f"wrote {REFERENCE}\n")
        return

    if set(cases) != set(ref["cases"]):
        fail("case set differs from the reference")
    for k, v in ref["cases"].items():
        if cases[k] != v:
            want = "raise" if v.get("raises") else "return the reference output"
            fail(f"{k}: candidate does not {want}")
    for k, v in bench.items():
        if ref["bench"][k] != v:
            fail(f"benchmark seed {k}: output is not bit-identical to the reference")
    med = statistics.median(times)
    sys.stderr.write(f"times {[round(t, 4) for t in times]}  median {med:.4f}s  "
                     f"scorer wall {time.perf_counter() - started:.1f}s\n")
    print(f"{med:.6f}")


if __name__ == "__main__":
    main()
