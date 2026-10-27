# memesuite-lite tomtom: an autopilot benchmark with a known answer

**Task.** Make `tomtom` in memesuite-lite run faster, and keep every output bit-identical.

The problem comes from [jmschrei/memesuite-lite](https://github.com/jmschrei/memesuite-lite)
(MIT). The start point is commit `dd413f6`, the first parent of the merge of
[PR #21](https://github.com/jmschrei/memesuite-lite/pull/21) (`45549db`). PR #21 is the known
answer. An automated search found it, and it changed only `memelite/tomtom.py`. On its own
benchmark (JASPAR 2024 all-vs-all, 2,346 motifs, one thread, AMD EPYC 9575F) it cut the time
from 5.455 s to 0.7004 s (7.8x), with bit-identical output.

## Metric

- **Workload:** the PR's own benchmark. `tomtom(X, X, n_jobs=1)`, with `X` all 2,346 motifs
  of JASPAR 2024 CORE non-redundant (`JASPAR2024_CORE_non-redundant_pfms_meme.txt`, the file
  memelite's CLI downloads). `setup.sh` downloads it into `work/data/` and checks a pinned
  sha256. The scorer refuses to run when the file is missing or its hash differs.
- **Metric:** the median wall time, in seconds, of 5 timed calls. Each timed call uses the
  same motifs in a different seeded order, so a candidate cannot replay a cached answer.
- **Direction:** lower is better.
- **Baseline** (the pinned code, Fir): **6.02 s** (median of 5 scorer runs; medians
  5.92-6.06 s)
- **Bar** (PR #21 as a candidate, Fir): **1.62 s** (median of 4 scorer runs; medians
  1.617-1.624 s), so 3.7x faster

These numbers come from a Fir compute node (AMD EPYC 9655, Zen 5), 8 CPUs, not exclusive,
Python 3.11.5, SLURM job 342272. An Apple M1 gave 9.11 s and 2.32 s (3.9x). The PR measured
5.455 s and 0.7004 s (7.8x) on an AMD EPYC 9575F. The baseline on Fir is close to the PR's
baseline, but PR #21 on Fir is 2.3x slower than the PR's own number, and we do not know why.
Times differ between machines, so score the baseline again on the machine that runs the
search.

## What the agent may edit, and what is frozen

- **Editable:** `memelite/tomtom.py` in the candidate checkout. The scorer reads no other
  file from the candidate.
- **Frozen:** the rest of the `memelite` package, the repo's tests, `score.py`, `setup.sh`,
  `requirements.lock` and `reference/`. The scorer takes all of them from `work/frozen/`
  (an export of `dd413f6`), never from the candidate. A candidate that edits a test file
  therefore changes nothing.

## The scorer contract

```
python3 score.py CANDIDATE                  # or: CRUX_CANDIDATE=CANDIDATE python3 score.py
```

- `CANDIDATE` is a memesuite-lite checkout. The scorer has no default path.
- **Candidate:** a path argument, else `CRUX_CANDIDATE`, else the working directory, but
  only when `CRUX_WORKSPACE` is set. crux's `run_scorer` sets the working directory to the
  attempt's worktree and sets `CRUX_WORKSPACE`, so the plan needs no adapter:
  `scorer: python3 <abs path>/score.py`. The scorer stages its temp files inside
  `CRUX_WORKSPACE` when it is set.
- **Pass:** exit 0, and stdout is exactly one JSON object. The objective is the leaf
  `seconds`, so the plan sets `address:: seconds` and `direction:: min`. Example:
  `{"seconds": {"value": 2.33, "direction": "min", "unit": "s", "repeats": [...], "min": ...,
  "max": ..., "spread_pct": ...}, "passed": true, "workload": {...}, "checks": {...},
  "candidate": {...}, "scorer_wall_s": ...}`.
- **Fail:** exit 1. stdout is `{"passed": false, "reason": "..."}` with no `seconds` leaf,
  and the reason is also on stderr. `run_scorer` reports this as `scorer-exit` with the tail
  of stderr. Note that the driver treats `scorer-exit` as a machine fault and retries it up
  to `retries:` times, so a wrong candidate costs `1 + retries` scorer runs before it is
  recorded as failed. The candidate fails when one of these is true:
  1. The repo's frozen pytest suite fails. (`tests/test_cli.py` is skipped: it needs the
     `ttl` console script, and the scorer does not install the package.)
  2. Any output is not bit-identical to `reference/expected.json`. The scorer checks the 36
     golden cases of the repo (at 1 and 4 threads), 16 edge and bad inputs, the warm-up
     call, and every timed call.
  3. The candidate returns where the pinned code raised, or raises where the pinned code
     returned. The exception type does not have to match.
- **Runtime:** about 115-120 s for the baseline and 135 s for PR #21 on Fir (140 s and
  175 s on the M1). Numba compiles the candidate with an empty cache each run, which
  takes most of the time that is not the 5 timed calls. The scorer stops itself after 290 s.

How the scorer protects the number:

- The parent process uses only the standard library and never imports the candidate.
- A worker process in `work/venv` runs the candidate. It writes each output to an `.npy`
  file, and the parent hashes the file. The candidate cannot change the hash.
- The parent times each call with its own clock. The candidate cannot patch it.
- Each timed call uses a new motif order, and the parent checks each output. A candidate that
  caches results, or that returns early, fails.

## How to run

```
./setup.sh                                  # clone at dd413f6, build work/venv
                                            # on Fir: module load python/3.11.5 first, and
                                            # run setup and scorer inside a SLURM job
python3 score.py work/cand-baseline         # the baseline
python3 score.py work/cand-pr21             # the known answer (PR #21 merged)
```

`setup.sh` makes everything under `work/`, which git ignores: the clone, the frozen export,
two candidate checkouts, and a venv with the exact versions in `requirements.lock`
(taken from the repo's own `uv.lock`). On an Alliance cluster (`CC_CLUSTER` set), it uses
`requirements.alliance.lock`: the cluster's Python refuses PyPI wheels, and its wheelhouse
lacks three of the pins, so numpy 2.4.2, pandas 3.0.5 and pytest 9.0.2 replace them. The
outputs on Fir were bit-identical to the reference made on the Mac. It installs nothing outside `work/`. It records the
versions in `work/versions.txt`.

## Noise

Measured on Fir (EPYC 9655, 8 CPUs, `--cpus-per-task=8`):

| | not exclusive (job 342272) | `--exclusive` (job 342273) |
|---|---|---|
| baseline, 5 scorer runs | medians 5.92-6.06 s (2.3%) | medians 5.93-6.01 s (1.3%) |
| baseline, spread inside one run | 0.3-3.1% | 0.3-0.8% |
| PR #21, 4 scorer runs | medians 1.617-1.624 s (0.4%) | medians 1.600-1.609 s (0.6%) |

- Sharing the node roughly doubled the noise of the baseline, but the effect is small. An
  exclusive node costs a whole 192-core node for a one-thread benchmark.
- Another node, in a separate job (345325), timed the baseline at about 6.4 s per call. Compare
  candidates on the same node, or score the baseline again in the same job.
- A candidate that sleeps 0.3 s per call scored 6.36 s, worse than every baseline run.
- On the M1, the baseline medians spread 2.1% and the PR #21 medians 5.6%.

The scorer uses 5 repeats: a sixth call costs 2-6 s more and does not remove a slow run.
Treat a change under about 3% on one node as noise, and confirm a small gain with a second
scorer run.

## Results (lean autopilot run)

SLURM job 735113 on Fir (2026-10-27): climb mode, `budget_hours: 4`, 8 CPUs.
Run directory: `~/scratch/crux-runs/memesuite-lite-735113`.

- **Stop:** `budget` (4.022 of 4 hours). The driver did not crash.
- **Wall time:** 4 h 04 min 05 s for the job. The ledger covers 4.022 h, from setup to stop.
- **Attempts:** 31, which is **7.707 per hour**. The median attempt took about 7.6 min.
- **Outcomes:** 22 kept, 4 rejected (each failed the same frozen-test assert on the p-value
  background tables in `_p_value_backgrounds`), 3 failed (one worker ran past the time limit, two workers made no commit), 2 discarded
  (the worker committed `memelite/__pycache__/*.pyc`).
- **Baseline:** 7.25493 s. This node was slow: other Fir nodes time the baseline at 5.9-6.4 s.
- **Best:** **2.835755 s** (attempt 30, node h30), 2.56 times faster than the baseline on the
  same node. This passes the bar of <= 5.4.
- **Best program:** All the speed-up is in the numba kernels of `memelite/tomtom.py` (286
  lines added, 34 removed). The gains came from fused 4-row distance passes, loops bounded to
  each row's non-zero span, an integer-count median, and then (attempt 27, 3.37 s to 2.90 s) a
  square root through the `llvm.sqrt` intrinsic, so that the distance loop vectorizes.
  Attempts 28 and 30 are empty commits whose messages say "no change". So the best *code* is
  attempt 27's, and the 2.90 s to 2.84 s step is noise (about 2%).
- **Notes:** In climb mode, every kept attempt counts as a candidate parent, so empty "no
  change" commits are kept and can become the best by noise. The search stayed on parent h6
  for attempts 7-25: most children of h6 scored 3.6-4.6 s, slower than h6 (3.59 s).
