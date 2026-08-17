# h30 — run report

**Claim.** Selection sort takes the same time sorted or not

**Measured.** Sorted 1.82 ms, random 1.85 ms at n=10000

**What the run showed.** Selection sort took essentially the same time on sorted and random lists. The algorithm cannot skip the scan for the minimum in each pass, so list order did not matter. Time scaled quadratically in both cases.
