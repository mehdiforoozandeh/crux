---
type: wiki
title: Quick sort
summary: Quick sort picks a pivot item and partitions the list around it, then recursively sorts the partitions.
category: method
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Quick sort

Quick sort uses divide-and-conquer by choosing a pivot value and splitting items into smaller and larger groups. It is often faster in practice than merge sort.

## Background

Quick sort is a divide-and-conquer algorithm that works differently from merge sort. Instead of dividing the list in half blindly, quick sort picks one item as a pivot. It then partitions the list so that all items smaller than the pivot are on the left and all items larger are on the right. Then it recursively sorts the left and right partitions. On average, this strategy does about n log n comparisons, matching merge sort. But the constant factors are smaller: quick sort does less extra work and needs less extra memory than merge sort. However, quick sort has a weakness: if the pivot is chosen poorly, the partitions can be very uneven. In the worst case, this degenerates to n squared comparisons. Choosing the pivot well is crucial. Simple approaches like always picking the first item can be disastrous on certain data. Better approaches pick the pivot more carefully or randomly. Some variants use the median of three items as the pivot. Quick sort is not stable, but it is memory-efficient. Because of its good average-case speed and low memory use, quick sort is popular in practice. Many programming languages use variants of quick sort in their built-in sort functions, though modern approaches often use [[sorting-algorithms-overview]] hybrid algorithms that switch between quick sort and insertion sort depending on data size.

## See also

Related:: [[sorting-algorithms-overview]], [[heap-sort]]
