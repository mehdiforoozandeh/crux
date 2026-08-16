# h1 — run report

**Claim.** Insertion sort beats bubble sort on every list I test

**Measured.** Insertion 0.34 s, bubble 1.62 s at n=100000 random

**What the run showed.** Insertion sort is faster on random lists across all sizes tested. On pre-sorted lists, however, the early-exit version of bubble sort nearly catches up to insertion. This surprised me because I did not expect bubble to be competitive at anything.
