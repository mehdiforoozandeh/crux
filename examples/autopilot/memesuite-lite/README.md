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
- **Baseline** (the pinned code, this machine): **9.11 s** (median of 5 scorer runs; medians 8.98-9.17 s)
- **Bar** (PR #21 as a candidate, this machine): **2.32 s** (median of 4 scorer runs; medians 2.30-2.43 s), so 3.9x faster

The numbers above come from an Apple M1 with Python 3.11.5. The PR measured 7.8x on an AMD
EPYC 9575F, and its kernels were tuned on that CPU. Times on other machines differ, so score
the baseline again on the machine that runs the search.

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
- **Runtime:** about 140 s for the baseline and 175 s for PR #21 on the M1. Numba compiles the candidate with an empty cache each run, which
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
python3 score.py work/cand-baseline         # the baseline
python3 score.py work/cand-pr21             # the known answer (PR #21 merged)
```

`setup.sh` makes everything under `work/`, which git ignores: the clone, the frozen export,
two candidate checkouts, and a venv with the exact versions in `requirements.lock`
(taken from the repo's own `uv.lock`). It installs nothing outside `work/`. It records the
versions in `work/versions.txt`.

## Noise

Measured on the M1:

- Baseline, 5 scorer runs: medians 8.98-9.17 s (2.1%). Two single calls were slow
  outliers (9.53 s and 10.34 s); the median absorbed both.
- PR #21, 4 scorer runs: medians 2.30-2.43 s (5.6%). One run had a 3.05 s first call.
- A candidate that sleeps 0.3 s per call scored 9.47 s, worse than every baseline run.

The scorer uses 5 repeats: a sixth call costs 2-9 s more and does not remove a slow run.
Treat a change under about 6% as noise, and confirm a small gain with a second scorer run.

