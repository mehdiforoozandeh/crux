---
type: wiki
title: Merge sort
summary: Merge sort divides a list in half recursively, then merges the sorted halves back together.
category: method
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Merge sort

Merge sort uses a divide-and-conquer strategy. It repeatedly splits the list into smaller pieces, sorts them, and combines them back together.

## Background

Merge sort is a classic example of divide-and-conquer algorithm design. The idea is simple: if you have a hard problem (sorting a big list), break it into easier problems (sorting two smaller lists), solve those, then combine the answers. Merge sort divides the list in half. It then recursively divides each half in half again, and again, until each piece has just one item. A list with one item is already sorted. Then the algorithm merges pairs of sorted lists back together. Merging two sorted lists is efficient: you compare the first item of each list, take the smaller one, and repeat. Merge sort makes roughly n log n comparisons. This is much better than the n squared behavior of simpler algorithms. For a list of 1 million items, merge sort is thousands of times faster than bubble sort. The trade-off is that merge sort needs extra memory to hold the merged temporary lists. It also has slightly more overhead because of the bookkeeping involved in dividing and recursing. Merge sort is stable, and it performs consistently no matter what the data looks like. It is often used in practice and is the basis for many faster algorithms like [[quick-sort]].

## See also

Related:: [[sorting-algorithms-overview]], [[quick-sort]]
