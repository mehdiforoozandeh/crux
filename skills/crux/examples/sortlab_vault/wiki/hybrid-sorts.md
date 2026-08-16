---
type: wiki
title: Hybrid sorts
summary: Hybrid sorts combine multiple sorting strategies, switching between them based on data size or other conditions.
category: method
sources: raw/club-handout-hybrid-sorts.txt
---

# Hybrid sorts

A hybrid sort uses different algorithms for different situations. Large datasets might use quick sort, small datasets might use insertion sort.

## Background

No single sorting algorithm is best for every situation. Small lists are fast to sort with almost any method. Large lists benefit from algorithms like merge sort or quick sort that have O(n log n) behavior. Data that is already partially sorted benefits from algorithms that notice this structure. Hybrid sorting takes advantage of these insights by using multiple algorithms and choosing between them. A common approach is to use quick sort for large partitions, but switch to insertion sort for small partitions (perhaps under 20 items). Insertion sort is simpler and has less overhead on small lists. Another hybrid approach is to detect sorted runs (stretches of data that are already in order) and use a merge process that respects these runs, as [[timsort]] does. Some hybrid algorithms use random sampling to check if data is random or partially sorted, and choose the algorithm accordingly. Hybrid approaches are more complex to implement than single-algorithm approaches. But they often outperform simple algorithms on real data. Most modern programming languages use hybrid or adaptive algorithms in their built-in sort functions. Understanding hybrid sorts shows that engineering involves trade-offs: complexity for performance, or simplicity for understandability.

## See also

Related:: [[sorting-algorithms-overview]], [[pivot-choice]]
