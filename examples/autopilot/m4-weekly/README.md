# M4 Weekly: an autopilot benchmark where whole forecasting programs compete

**Task.** Write one program that forecasts the next 13 weeks of each of the 359 M4 Weekly
series. Any method family may compete: statistical, tree-based or neural. The score is M4's
official OWA against the held-out M4 test values. Lower is better.

This is an Explore problem in the style of Google's ERA: the search agent writes the whole
program. The data and every published forecast come from
[Mcompetitions/M4-methods](https://github.com/Mcompetitions/M4-methods) at commit `6c1067e`
(master, 2020-03-20). That repository has **no license file**. We download the data at setup
time and never commit it.

## Data (verified at the pinned commit)

- `Dataset/Train/Weekly-train.csv`: 359 series. `Dataset/Test/Weekly-test.csv`: 359 x 13.
- `Dataset/M4-info.csv`: all 359 Weekly ids have `Frequency` 1 and `Horizon` 13.
- `setup.sh` pins each file by sha256 and puts it in `work/secret/`. The scorer checks the
  train and test hashes again on every call.

## Metric (M4's own definitions)

The reference is `Benchmarks and Evaluation.R` in the same repository.

- sMAPE = mean of 200·|y − f| / (|y| + |f|) over all 359 × 13 points.
- MASE = mean of |y − f| / scale, where scale is the in-sample mean of |x_t − x_{t−m}|. The
  scale uses `m` = the M4-info `Frequency`, which is **1 for Weekly**.
- Naive2 is the naive forecast of the seasonally adjusted series. With frequency 1, the M4
  code applies no seasonal adjustment, so for Weekly, Naive2 repeats the last value.
- OWA = ½ (sMAPE / sMAPE_Naive2 + MASE / MASE_Naive2). Naive2 has OWA 1.000 by definition.

**Reproduction.** `score.py --forecasts FILE` scores the published point forecasts that
`setup.sh` extracts from the official submission archives. The results match the published
table (`Evaluation and Ranks.xlsx`, sheet *Point Forecasts-Frequency*):

| method | our sMAPE / MASE / OWA | published sMAPE / MASE / OWA |
|---|---|---|
| Naive2 (benchmark) | 9.1613 / 2.7773 / 1.0000 | 9.161 / 2.777 / 1 |
| Theta (benchmark) | 9.0930 / 2.6371 / 0.97104 | 9.093 / 2.637 / 0.97104 |
| **118 Smyl** (winner of M4 overall) | 7.8171 / 2.3559 / 0.85078 | 7.817 / 2.356 / 0.85084 |
| **235 Darin & Stellwagen** (best Weekly) | 6.5816 / 2.1070 / 0.73853 | 6.582 / 2.107 / 0.73863 |

The last digits of OWA differ because the spreadsheet computes OWA from sMAPE and MASE
rounded to 3 decimals. Other published Weekly OWAs: 036 Petropoulos & Svetunkov 0.751,
237 Pawlikowski 0.766, Damped 0.917, Comb 0.926. We could not open the M4 paper
(Makridakis et al. 2020, IJF; the publisher returned 403), so we did not check its table
directly. The spreadsheet is the organisers' own file.

**Bar.** 0.739 (235, best on Weekly). Smyl, who won M4 overall, scored 0.851 on Weekly.

## Candidate contract

A candidate is a directory that contains `forecast.py`. The scorer copies the directory
(without `.git`) into a new stage, then runs it with the venv's Python:

```
python forecast.py TRAIN_CSV OUT_CSV          # cwd = the staged copy
```

- `TRAIN_CSV`: the header is `id,y1,y2,...`. Each row is one series, oldest value first.
  Rows have different lengths, from 80 to 2,597 values. Ids are anonymised (`s001`...) in a
  fixed shuffled order.
- `OUT_CSV`: the header must be exactly `id,F1,...,F13`. Write one row per input id, with 13
  finite numbers. A missing, extra or duplicate id fails the candidate, and so does a NaN, an
  inf or a wrong column count.
- Environment: `M4_HORIZON=13`, `M4_CPUS` (the CPUs of the job), `CRUX_SEED` (default `0`),
  `PYTHONHASHSEED=0`. The BLAS and OpenMP thread variables are 1, which keeps a run
  deterministic; a program may use `multiprocessing` over `M4_CPUS`.
- Packages in `work/venv`: numpy, pandas, scipy, statsmodels, scikit-learn
  (`requirements.lock`). There is no torch and no lightgbm. Neural methods use scikit-learn's
  MLP, or numpy written by hand.
- The program runs **twice**. The **val** run gets each series minus its last 13 values and
  is scored against those 13 values (`val_owa`). The **test** run gets the full train series
  and is scored against the official test file (`owa`). Each run has a **110 s** wall-time
  cap. The whole scorer stops itself at 280 s.

What fits in 110 s on 4 CPUs (Fir): the M4 Theta benchmark takes 1.3 s. The shipped
ensemble (SES, damped Holt and Theta, three statsmodels fits per series) takes 3 s. So
per-series ETS or ARIMA model selection fits, and so do global tree models and small MLPs
over all series. Deep nets trained from scratch (an N-BEATS- or ES-RNN-sized model) on CPU
mostly do not fit.

## Output

- **Pass:** exit 0. stdout is one JSON object: `owa` (the objective: `value`, `smape`,
  `mase`, and the Naive2 terms), `val_owa` (the same fields), `passed`, `workload`, `bar`,
  `checks` (copy shares, sandbox), `runs` (seconds per run), `candidate`, `scorer_wall_s`.
  Plan: `address:: owa`, `direction:: min`.
- **Fail:** exit 1. stdout is `{"passed": false, "reason": ...}`, and the reason also goes
  to stderr. crux treats `scorer-exit` as a machine fault and retries it `retries:` times.
- **Candidate:** a path argument, else `CRUX_CANDIDATE`, else the working directory, but only
  when `CRUX_WORKSPACE` is set. The plan needs no adapter: `scorer: python3 <abs>/score.py`.
  The stage goes inside `CRUX_WORKSPACE` when it is set.

## How the test values are protected

1. **Sandbox.** Each run is under bubblewrap (`bwrap`, which exists on Fir compute nodes):
   no network (a new network namespace with only a down loopback), a read-only filesystem,
   and new pid, ipc and uts namespaces. `/home`, `/scratch`, `/project` and `/nearline` are
   replaced by empty tmpfs. Only this directory (read-only) and the stage (writable) are
   bound back in, and then `work/secret/` (the test file and the published forecasts) is
   replaced by an empty tmpfs. A candidate therefore cannot see the crux vault, other copies
   of M4 on the cluster, or the test file, and it cannot edit `score.py`.
2. **Ordering.** The parent process reads the test file only after both runs have ended.
3. **Replay check.** The scorer fails a candidate when 25% or more of its values equal
   (relative tolerance 1e-6) the test values, the val truth, or the published forecasts of
   118 (Smyl) or 235 (best Weekly). This catches an answer table that was put into the
   program while it was written.
4. **Anonymised ids.** The ids are anonymised, so a program cannot look up a downloaded
   answer by its M4 id.

**Residual risk (cannot be blocked here).** The test set and every published forecast are
public on GitHub. An agent that has web access *while it writes* the program can download
them and put a perturbed copy into the program (for example, Smyl's forecasts times 1.001).
The replay check catches exact copies only. That route is closed only when the search
workers have no web access. A second, statistical concern: a long search that reads `owa`
after every attempt adapts to the test set, which M4 entrants never saw. `val_owa` is a
held-out-in-time signal; choose `address:: val_owa` to search without reading the test, and
read `owa` once at the end.

## Validation (Fir, `selfcheck.py`, jobs 429125 and 431252, 4 CPUs)

| candidate | expected | result |
|---|---|---|
| `candidates/naive2` (the baseline) | OWA 1 | owa 1.000000, val_owa 1.000000; scorer 0.6 s |
| `candidates/theta` (M4 Theta) | ≈ 0.971 | owa 0.971011 (published 0.97104), val_owa 0.906 |
| `candidates/ensemble` | better | owa 0.944181, val_owa 0.885; scorer 7 s |
| same candidates again | same | bit-identical owa and val_owa |
| 12 columns / one NaN | fail | fail: header / "NaN or infinite forecast" |
| sleeps forever | fail | fail at the 110 s cap |
| reads `work/secret/*.csv`, writes `score.py`'s directory | no gain | file not found, write refused (read-only); owa 1.000 |
| scans `/scratch`, `/home` for other `Weekly-test.csv` | no gain | none visible (one existed on `/scratch`) |
| downloads the test set from GitHub | no gain | network refused; owa 1.000 |
| carries the test values / Smyl's forecasts as a table | fail | fail: "reproduce val_truth 100%" / "submission_118 99.4%" |

## How to run (Fir)

```
module load python/3.11.5
./setup.sh                                    # data, published forecasts, work/venv (~3.5 min)
python3 score.py candidates/naive2            # inside a SLURM job
python3 selfcheck.py                          # every check above (~2.5 min)
```
