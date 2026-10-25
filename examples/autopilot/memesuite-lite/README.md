# memesuite-lite tomtom: an autopilot benchmark with a known answer

**Task.** Make `tomtom` in memesuite-lite run faster, and keep every output bit-identical.

The problem comes from [jmschrei/memesuite-lite](https://github.com/jmschrei/memesuite-lite)
(MIT). The start point is commit `dd413f6`, the first parent of the merge of
[PR #21](https://github.com/jmschrei/memesuite-lite/pull/21) (`45549db`). PR #21 is the known
answer. An automated search found it, and it changed only `memelite/tomtom.py`. On its own
benchmark (JASPAR 2024 all-vs-all, 2,346 motifs, one thread, AMD EPYC 9575F) it cut the time
from 5.455 s to 0.7004 s (7.8x), with bit-identical output.

## Metric

- **Metric:** the median wall time, in seconds, of 5 timed calls of
  `tomtom(X, X, n_jobs=1)`. `X` is 1,000 synthetic motifs, and each call uses a new seed.
- **Direction:** lower is better.
- **Baseline** (the pinned code, this machine): **2.68 s** (median of 6 scorer runs; range 2.65-2.87 s)
- **Bar** (PR #21 as a candidate, this machine): **0.978 s** (median of 4 scorer runs; range 0.975-0.981 s), so 2.74x faster

The numbers above come from an Apple M1 with Python 3.11.5. Times on other machines differ.
Score the baseline again on the machine that runs the search.

The motifs are synthetic count matrices: widths 6-17, and 10-59 sites per column, so some
columns repeat, as in JASPAR. The benchmark does not use JASPAR itself: setup downloads no data
set, so the workload is generated from fixed seeds. On this workload PR #21 is about 2.7x faster, not 7.8x. The PR reports
smaller gains on synthetic motifs too (about 5x), and its kernels were tuned on a different
CPU.

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
- **Pass:** exit 0, and the last stdout line is one number (seconds; lower is better).
- **Fail:** exit 1, no number, and the reason on stderr. The candidate fails when one of
  these is true:
  1. The repo's frozen pytest suite fails. (`tests/test_cli.py` is skipped: it needs the
     `ttl` console script, and the scorer does not install the package.)
  2. Any output is not bit-identical to `reference/expected.json`. The scorer checks the 36
     golden cases of the repo (at 1 and 4 threads), 16 edge and bad inputs, the warm-up
     call, and every timed call.
  3. The candidate returns where the pinned code raised, or raises where the pinned code
     returned. The exception type does not have to match.
- **Runtime:** about 1.5 to 2 minutes. Most of it is numba compiling the candidate with an
  empty cache. The scorer stops itself after 290 s.

How the scorer protects the number:

- The parent process uses only the standard library and never imports the candidate.
- A worker process in `work/venv` runs the candidate. It writes each output to an `.npy`
  file, and the parent hashes the file. The candidate cannot change the hash.
- The parent times each call with its own clock. The candidate cannot patch it.
- Each timed call uses a new input, and the parent checks each output. A candidate that
  caches results, or that returns early, fails.

## How to run

```
./setup.sh                                  # clone at dd413f6, build work/venv
python3 score.py work/cand-baseline         # the baseline
python3 score.py work/cand-pr21             # the known answer (PR #21 merged)
```

`setup.sh` makes everything under `work/`, which git ignores: the clone, the frozen export,
two candidate checkouts, and a venv with the exact versions in `requirements.lock`
(taken from the repo's own `uv.lock`). It installs nothing outside `work/`. It records the
versions in `work/versions.txt`.

## Noise

Measured on the M1, with the baseline:

- Inside one scorer run, the 5 timed calls differ by about 3% (largest over smallest).
- Over 6 scorer runs, 5 medians fell inside 2.65-2.68 s (1%). One fell at 2.87 s (+7%). In
  that run all 5 calls were slow, so the cause was the machine, not the input.
- For PR #21, 4 scorer runs fell inside 0.975-0.981 s (0.6%).
- A candidate that sleeps 0.3 s per call scored 2.98 s, worse than every baseline run.

The scorer uses 5 repeats. More calls in one run do not remove a slow run, and they cost
time. So treat a change under about 8% as noise, and confirm a small gain with a second
scorer run.
