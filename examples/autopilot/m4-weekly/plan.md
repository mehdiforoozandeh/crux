---
anchor: @ANCHOR@
repo: @REPO@
base: HEAD
editable: forecast.py
scorer: python3 @BENCH@/score.py
objective: val_owa min 0.739
mode: explore
budget_hours: 3
attempt_minutes: 10
---
Forecast 13 weeks ahead for the 359 M4 Weekly series. `forecast.py TRAIN_CSV OUT_CSV` writes `id,F1,...,F13`, one row per id, all finite; it runs twice (val and test), each under 110 s on 4 CPUs.
The score is OWA against Naive2 (repeat the last value), which scores 1.000. numpy, pandas, scipy, statsmodels and scikit-learn are available; there is no torch, and deep nets trained from scratch mostly do not fit in the time.
Runs are deterministic (one BLAS thread, CRUX_SEED); a program may use multiprocessing over M4_CPUS.
