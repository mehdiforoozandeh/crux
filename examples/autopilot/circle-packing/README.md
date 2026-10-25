# circle packing, n=26: an Explore-mode autopilot benchmark with a hard-to-fool scorer

**Task.** Write one program, `pack.py`, that places 26 non-overlapping circles inside the unit
square and makes the sum of their radii as large as possible. The search agent writes whole
candidate programs (Google ERA / AlphaEvolve style). The program may run its own optimizer.

The problem is AlphaEvolve's ([arXiv 2506.13131](https://arxiv.org/abs/2506.13131)). It was chosen because OpenEvolve's evaluator for this problem accepted impossible
packings (see "Why this scorer is strict").

## The record

| sum of radii | who | source |
|---|---|---|
| 2.634 | prior record before AlphaEvolve | AlphaEvolve paper; AlphaEvolve problem repository notebook |
| 2.6359830849176 | AlphaEvolve (2025) | [alphaevolve_repository_of_problems](https://github.com/google-deepmind/alphaevolve_repository_of_problems/blob/30f8c3ecda318e3ac31ff2c3290884316ac7d0ed/experiments/packing_circles_max_sum_of_radii/packing_circles_max_sum_of_radii.ipynb), "Construction 1" (paper rounds it to 2.635) |
| 2.635977394754 | Yiping Wang | [Packomania csqv](https://packomania.com/csqv/) history |
| **2.635983084919** | Haowei Lin, credited 2026-08-01 | [Packomania csqv](https://packomania.com/csqv/); [Friedman](https://erich-friedman.github.io/packing/cirRsqu/) lists 2.63598+ |

The scorer uses `BEST_KNOWN = 2.635983084919`. The AlphaEvolve construction and the current
record agree to about 1e-12, so the problem is close to solved; a real gain now is tiny.

AlphaEvolve's published decimals **fail** this scorer: circle 1 leaves the square by 1e-17,
and three pairs overlap by about 1e-18 in squared distance (exact arithmetic). The same
construction with every radius shrunk by 1e-12 passes and scores 2.6359830848916.

## Metric

- **Objective:** the leaf `sum_radii` (`address:: sum_radii`, `direction:: max`).
- **Baseline** (`baseline/pack.py`: a 5x5 grid of radius 0.1, plus one circle in a gap):
  **2.5414213562363** on Fir, scorer wall time 0.16-0.42 s.
- **Bar:** the record, 2.635983084919. A score above it is flagged `"suspicious": true`, and
  the scorer warns on stderr. It is not refused, because the check is exact and a higher valid
  packing would be a real new record. Read the program before you believe it.
- **Deterministic:** the score is an exact rational sum; the same printed output gives the
  same score bit for bit (5 of 5 repeats on Fir). A candidate that uses randomness without a
  fixed seed can print different packings on different runs; that is the candidate's
  noise, not the scorer's.

## The scorer contract

```
python3 score.py CANDIDATE         # CANDIDATE: a directory holding pack.py, or the file
```

- **Candidate:** a path argument, else `CRUX_CANDIDATE`, else the working directory, but only
  when `CRUX_WORKSPACE` is set. crux's `run_scorer` sets both, so the plan needs no adapter:
  `scorer: python3 <abs path>/score.py`. Temp files go inside `CRUX_WORKSPACE` when it is set.
- **The program's output:** exactly one JSON object on stdout, and nothing else:
  `{"circles": [[x, y, r], ...]}` with 26 triples. Any other key (for example a reported
  score), any other text on stdout, or a second JSON value fails the candidate. stderr is the
  program's own log; the scorer returns its tail only when the candidate fails.
- **Pass:** exit 0, one JSON object:
  `{"sum_radii": {"value": 2.54..., "direction": "max", "exact": "p/q"}, "passed": true,
  "suspicious": false, "best_known": ..., "checks": {...}, "sandbox": {...}, "candidate":
  {"sha256": ..., "run_s": ...}, "scorer_wall_s": ...}`.
- **Fail:** exit 1, `{"passed": false, "reason": "..."}` with no `sum_radii` leaf; the reason
  is also on stderr. `run_scorer` reports this as `scorer-exit`, which the driver retries up
  to `retries:` times.

### The checks (exact, zero tolerance)

The scorer reads each printed number as the exact rational value of its decimal text. It
never converts to a float first. Then it checks:

1. exactly 26 triples, and every value is a finite JSON number (`NaN`, `Infinity`, strings,
   `true`, `null` fail; a number longer than 64 characters or with a decimal exponent outside
   -60..1 fails);
2. `r > 0`;
3. `r <= x <= 1 - r` and `r <= y <= 1 - r`;
4. `(xi - xj)^2 + (yi - yj)^2 >= (ri + rj)^2` for every pair. Touching is allowed.

The score is the exact sum of the printed radii, computed by the scorer.

**Why zero tolerance, in exact arithmetic.** Any tolerance is free score: with a tolerance t,
each of the 26 radii can grow by about t. OpenEvolve used t = 1e-6 (about 1.3e-5 of free
score), ten million times more than the record has moved since AlphaEvolve (about
1e-12). Exact rationals remove the question of float rounding: the packing checked is exactly the packing printed. The cost to an honest float optimizer is one line: shrink every
radius by about 1e-12 before printing, which loses at most 2.6e-11. The baseline shows the
trap: `0.1 + 0.2*k` in floats puts two grid circles 4e-17 too close, so it uses literals.

### The sandbox

The scorer copies `pack.py` alone into a fresh temp directory and runs
`work/venv/bin/python -I pack.py` there, with:

- a **60 s** wall-time cap (the scorer kills the program's whole process group);
- a 4 GiB address-space cap (Linux only; macOS refuses `RLIMIT_AS`);
- a 1 MiB stdout cap, a scrubbed environment, one BLAS/OpenMP thread, `PYTHONHASHSEED=0`;
- **no network**: `unshare -rn` (a new user and network namespace) when the kernel allows
  it. The scorer probes this on every run and records `sandbox.network` in its output. On
  Fir compute nodes it works (jobs 428996, 429491): a fetch inside it fails, while the same
  fetch outside it succeeds.

Why 60 s: the scorer's own checks take milliseconds, so the cap is all candidate time, and
one minute keeps the search loop fast. AlphaEvolve gave its programs 1000 s; we have not
measured how far a numpy optimizer gets in 60 s. Raise `TIMEOUT_S` if the search
stalls for lack of optimizer time; the scorer then stays under `TIMEOUT_S` + 1 s.

## Why this scorer is strict: how OpenEvolve was fooled

OpenEvolve's `examples/circle_packing/evaluator.py` imported the candidate in a subprocess,
took back `(centers, radii, sum_radii)` through a pickle, and checked walls and pairs with
`x - r < -1e-6` and `dist < ri + rj - 1e-6`.

- **Issue #183, sum 4.0145:** the evolved program produced NaN centres. Every comparison with
  NaN is `False`, so no wall or pair test could fail, and radii near 0.15 each passed. PR
  #184 then added an explicit centre-NaN check.
- **Issue #285, "hard-coded radii":** a program set every centre to NaN and returned fixed
  radii summing to 2.637, the published record. It passed on the reporter's copy, which
  lacked the NaN checks of PR #134 (radii) and PR #184 (centres).
- **The 1e-6 tolerance** let every radius grow by about 5e-7 (issue #183 also names it).

Here, NaN never reaches a comparison: the JSON reader refuses it. There is no tolerance. The
candidate cannot report its own sum, its own validity, or anything but the 26 triples.

`validate.py` rebuilds all of these as candidate programs. It also runs OpenEvolve's check
logic (as of issue #183) on each, to show that it accepted them.

## Validation (Fir, AMD EPYC 9655, Python 3.11.5, numpy 2.4.2)

`work/venv/bin/python validate.py --repeats 5` (SLURM jobs 428996 and 429491): all cases
behave as expected.

| case | this scorer | OpenEvolve logic |
|---|---|---|
| baseline | pass, 2.5414213562363 | accept |
| AlphaEvolve, radii shrunk 1e-12 | pass, 2.6359830848916 | accept |
| AlphaEvolve as published | fail: leaves square by 1e-17 | accept |
| NaN centre | fail | accept |
| NaN centres, sum 4.0145 (#183) | fail | accept |
| NaN centres, hard-coded radii 2.637 (#285) | fail | accept |
| every radius +5e-7 (tolerance exploit) | fail | accept |
| overlap by 1e-15 / outside by 1e-13 | fail | accept |
| zero radius | fail | accept |
| `"nan"` strings, `true`, `Infinity`, negative radius, 25 or 27 circles | fail | refuse or n/a |
| extra `sum_radii` key; a printed score line; two JSON objects | fail | n/a |
| `1e-99999999` (exponent bomb) | fail in 0.1 s | n/a |
| sleeps 120 s | fail at 60 s | n/a |
| forks a child that sleeps 300 s | pass; the child is killed | n/a |
| allocates 8 GB; prints 10 MB; exits 3 | fail | n/a |
| downloads the AlphaEvolve record at run time | fail (no network) | n/a |
| same candidate scored 5 times (baseline, AlphaEvolve) | identical exact sums | |

## Residual risks

- **A copied record.** The record coordinates are public. A program can contain them as
  literals, and the search agent (which has web access while it writes code) can paste them
  in. The no-network sandbox stops only a download at score time. The `suspicious` flag
  catches only scores above the record, not a copy of it. A score within ~1e-9 of 2.635983 is
  most likely a copy or a rediscovery; read the program.
- **Files on disk.** The sandbox does not hide the file system. A candidate can read
  `work/reference/` (the AlphaEvolve notebook, kept for `validate.py`) or any other readable
  file.
- **Escaping the cap.** A candidate that calls `setsid` leaves the scorer's process group and
  can outlive the scorer (inside SLURM, the job's cgroup still ends it).
- **Only numpy.** The venv holds numpy and nothing else. AlphaEvolve's own program used scipy
  (SLSQP) and numba.

## How to run

```
./setup.sh                        # work/venv (numpy) + the AlphaEvolve notebook, sha256-pinned
                                  # on Fir: module load python/3.11.5 first, inside a SLURM job
python3 score.py baseline         # the baseline
work/venv/bin/python validate.py  # every case above; exit 0 when all behave
```

`setup.sh` makes everything under `work/`, which git ignores. It installs numpy from
`requirements.lock`; on an Alliance cluster it uses the cluster wheelhouse (`pip --no-index`).
