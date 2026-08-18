---
type: wiki
title: Best case and worst case
summary: Every algorithm behaves differently depending on the input. Best case is when input cooperates, worst case is when it does not.
category: concept
sources: raw/handout-ch09-growth-rates.txt
---

# Best case and worst case

An algorithm's speed depends on the data. Worst case describes the slowest possible input, best case the fastest, and average case is typical.

## Background

When we analyze an algorithm, different inputs can lead to very different performance. Consider bubble sort with an early-exit optimization: if a pass through the data makes no swaps, the data is sorted and the algorithm stops. If you give it data that is already sorted, each pass makes no swaps, and the algorithm finishes quickly. This is the best case. If you give bubble sort data in reverse order (the opposite of what it wants), then every pass makes many swaps, and the algorithm takes the longest time. This is the worst case. Most real data falls somewhere in between, in the average case. Quick sort is a good example of best, average, and worst cases. In the best case, the pivot is always near the middle, creating balanced partitions. This leads to O(n log n) behavior. In the average case with random data, this often happens, and quick sort performs well. In the worst case, if pivots are always at the edge (for instance, if you always pick the first item as pivot and the data is already sorted), one partition gets all remaining items, and you get O(n^2) behavior. Knowing the difference between best, average, and worst case matters for choosing algorithms. Some algorithms (like merge sort) have consistent O(n log n) behavior in all cases. Others (like quick sort) are fast on average but can be slow in worst cases. Some adapt to the data. Real systems often optimize for the average case and hope the worst case does not happen, but if you are sorting critical data, worst-case guarantees matter more.

## See also

Related:: [[algorithm-analysis-overview]], [[average-case-analysis]]
