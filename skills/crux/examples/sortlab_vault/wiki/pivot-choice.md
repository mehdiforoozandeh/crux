---
type: wiki
title: Choosing a pivot
summary: The decision of which item to use as the pivot in quick sort, which can make the sort much faster or slower.
category: concept
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Choosing a pivot

Quick sort divides the list using a pivot. Choosing a good pivot is crucial. A bad choice can make the algorithm slow.

## Background

Quick sort picks an item called a pivot and splits the list into items less than the pivot and items greater. Then it recursively sorts both halves. The quality of the sort depends on how evenly the pivot splits the list. If the pivot is close to the smallest or largest item, one half is huge and the other is tiny, and the sort takes much longer. If the pivot is close to the middle, both halves are similar in size, and the sort is fast. This is why quick sort is quick. But bad pivot choices make it slow. If you always pick the first item as the pivot, and the list is already sorted, every pivot ends up near one end, and the sort becomes as slow as bubble sort. This is called the worst case. To avoid this, quick sort can pick the pivot more carefully. The median-of-three strategy is one fix: look at the first, middle, and last items, find the one in the middle by value, and use that as the pivot. This nearly guarantees a reasonable split even on sorted or reverse-sorted input. Understanding pivot choice shows that the same algorithm can have very different speeds depending on small choices.

## See also

Related:: [[sorting-algorithms-overview]], [[median-of-three]]
