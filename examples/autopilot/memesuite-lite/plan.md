---
anchor: @ANCHOR@
repo: @REPO@
base: HEAD
editable: memelite/tomtom.py
scorer: python3 @BENCH@/score.py
objective: seconds min 1.62
mode: climb
budget_hours: 4
attempt_minutes: 20
---
Make `tomtom(X, X, n_jobs=1)` faster on all 2,346 JASPAR motifs. The score is the median wall time of 5 calls, one thread.
Only `memelite/tomtom.py` counts: the scorer takes the rest of the package and the tests from a frozen copy.
Every output must stay bit-identical to the reference, and the frozen pytest suite must pass; any difference fails the attempt.
Each timed call shuffles the motifs, so caching an answer across calls does not help. Times move about 2% between runs.
