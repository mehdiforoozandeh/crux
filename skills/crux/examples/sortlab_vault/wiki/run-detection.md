---
type: wiki
title: Finding runs
summary: Run detection identifies stretches of data that are already sorted, then uses them to speed up sorting.
category: concept
sources: raw/docs-note-python-list-sort.txt
---

# Finding runs

A run is a maximal sequence of items already in order. Detecting runs enables algorithms like timsort to skip redundant work.

## Background

A run is a sequence of consecutive items that are already in sorted order. If your data is [1, 2, 3, 7, 4, 5, 6, 8], it contains runs: [1, 2, 3, 7] and [4, 5, 6, 8]. Detecting runs allows sorting algorithms to skip sorting parts that are already done. Instead of sorting each part independently, you can merge the runs together, which is faster than sorting. Run detection is the key idea behind [[timsort]]. The algorithm scans the input to find runs, extends short runs to a minimum size using insertion sort, then merges the runs using a merge-sort-like process. On data with long runs, this is much faster than sorting from scratch. On random data with no runs, run detection adds overhead but the merge process still achieves O(n log n) performance. Run detection also works with reverse runs—sequences in reverse order. Extending a reverse run to ascending takes a simple reversal. This is why timsort is good on many kinds of real data: it adapts to both forward and reverse structure. Understanding run detection reveals a key principle: before applying a general algorithm, check whether the input has special structure you can exploit. This is why inspection and measurement are important. Your data might not be random.

## See also

Related:: [[algorithm-analysis-overview]], [[curve-fitting-basics]]
