# h69 — run report

**Claim.** The built-in sort is not running my kind of Python code

**Measured.** Merge sort at n=100000: 6.7 s. Built-in: 0.81 s. Ratio: 8.3x.

**What the run showed.** The built-in sort is not running my kind of code. It is at least eight times faster than my best sort on large lists. No pure-Python sorting algorithm is that much better. The built-in must be written in C or another compiled language.
