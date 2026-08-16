# h37 — run report

**Claim.** One item out of place costs insertion sort almost nothing

**Measured.** Zero out 0.23 ms, one out 0.24 ms at n=10000

**What the run showed.** One item out of place barely slowed insertion sort. The cost was absorbed in the noise. But ten items out of place was starting to show a measurable penalty.
