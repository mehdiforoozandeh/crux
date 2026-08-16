# h22 — run report

**Claim.** My merge sort beats my quick sort on random lists

**Measured.** Quick sort 11 ms, merge sort 18 ms at 100k random.

**What the run showed.** Quick sort actually beat merge sort at every size. I think the early pivot heuristic and cache locality of quick sort give it an advantage over the more methodical merge sort, even though both are O of n log n. The gap is not huge but it is consistent.
