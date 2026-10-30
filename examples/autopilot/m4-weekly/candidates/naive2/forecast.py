"""M4 Naive2 for Weekly series: repeat the last observed value 13 times.

M4-info.csv gives Weekly series Frequency 1, so the M4 benchmark code applies no seasonal
adjustment and Naive2 equals Naive1. Its OWA is 1.000 by definition. Stdlib only."""
import csv, sys

H = 13
train, out = sys.argv[1], sys.argv[2]
with open(train, newline="") as f, open(out, "w", newline="") as g:
    rows, w = csv.reader(f), csv.writer(g)
    next(rows)
    w.writerow(["id"] + [f"F{i}" for i in range(1, H + 1)])
    for r in rows:
        y = [x for x in r[1:] if x != ""]
        w.writerow([r[0]] + [y[-1]] * H)
