# h11 — run report

**Claim.** The gap to the built-in sort shrinks as the list grows

**Measured.** At 1k: built-in 0.2 ms, merge 0.8 ms, ratio 4x. At 1m: built-in 2.5 ms, merge 22 ms, ratio 8.8x.

**What the run showed.** The gap actually grew, not shrank. At one thousand items the ratio was four times, and at one million it was eight point eight times. This means the overhead is not the issue. The built-in sort just has a fundamentally better algorithm. The ratio settles at roughly eight to ten times across the range.
