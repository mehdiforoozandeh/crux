---
type: wiki
title: Selection sort
summary: Selection sort finds the smallest unsorted item and moves it to the front, repeatedly.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Selection sort

Selection sort divides the list into a sorted front portion and an unsorted back portion. It repeatedly finds the smallest unsorted item and moves it to the end of the sorted portion.

## Background

Selection sort works by dividing the list into two regions: sorted items at the front and unsorted items at the back. It then repeatedly searches through the unsorted region to find the smallest item, and moves that item to the sorted region. On the first pass, it finds the smallest item in the whole list and swaps it to position zero. On the next pass, it finds the smallest item in the remaining unsorted part and swaps it to position one. This continues until the entire list is sorted. Like bubble and insertion sort, selection sort makes roughly n squared comparisons. But it has a different property: it makes far fewer swaps. If moving items is expensive, selection sort might be faster than bubble sort even though both make the same number of comparisons. Selection sort is not stable: if two items compare equal, selection sort may change their order. It does not adapt well to data that is already sorted or nearly sorted—it will still take the same time. Because of these limitations, selection sort is rarely used in practice. It is primarily taught as a way to introduce the idea that different algorithms have different trade-offs in comparisons, swaps, and adaptability.

## See also

Related:: [[sorting-algorithms-overview]], [[merge-sort]]
