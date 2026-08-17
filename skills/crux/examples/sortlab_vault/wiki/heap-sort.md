---
type: wiki
title: Heap sort
summary: Heap sort uses a data structure called a heap to sort by repeatedly extracting the smallest item.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Heap sort

Heap sort rearranges the list into a special structure where parent items are always smaller than their children. It then repeatedly removes the smallest item.

## Background

A heap is a tree-shaped data structure where each parent node is smaller than its children. This property makes it easy to find the smallest item: it is always at the root. Heap sort first rearranges the input list into a heap—this takes O(n) time. Then it repeatedly removes the smallest item from the root and restructures the heap. Each removal takes O(log n) time, and there are n removals, so total time is O(n log n). Heap sort has consistent performance: it always does about n log n comparisons, regardless of the input data shape. It does not adapt to nearly-sorted data. Heap sort is not stable. It also requires careful bookkeeping, making it more complex to implement correctly than quick or merge sort. Heap sort uses very little extra memory compared to the input size. Because heap sort guarantees O(n log n) performance even in the worst case, it is sometimes used as a fallback when quick sort might be too slow. But in practice, hybrid algorithms and other methods often outperform pure heap sort because they adapt better to real data.

## See also

Related:: [[sorting-algorithms-overview]], [[counting-sort]]
