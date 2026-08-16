# h76 — run report

**Claim.** Radix sort beats the built-in sort on fixed-width numbers

**Measured.** Radix: 0.34 s. Built-in: 0.82 s. Ratio: 2.4x.

**What the run showed.** Radix sort wins, but just barely. The Python implementation is slow, and the built-in is very fast. Even a linear-time algorithm can barely beat the built-in when both are written in interpreted code versus compiled code.
