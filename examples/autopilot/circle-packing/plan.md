---
anchor: @ANCHOR@
repo: @REPO@
base: HEAD
editable: pack.py
scorer: python3 @BENCH@/score.py
objective: sum_radii max 2.635983084919
mode: explore
budget_hours: 2
attempt_minutes: 10
---
Pack 26 circles in the unit square to maximize the sum of their radii. `pack.py` prints exactly one JSON object `{"circles": [[x, y, r], ...]}` (26 triples) and nothing else on stdout. It runs alone in a sandbox for at most 60 s, with numpy and scipy and no network.
The scorer checks containment and overlap in exact arithmetic with zero tolerance: float rounding that puts two circles 1e-17 too close fails the whole packing. Shrink every radius by about 1e-12 before printing.
