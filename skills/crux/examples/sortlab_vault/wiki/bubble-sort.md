---
type: wiki
title: Bubble sort
summary: Bubble sort repeatedly compares neighboring items and swaps them until everything is sorted.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Bubble sort

Bubble sort is one of the simplest sorting algorithms but also one of the slowest. It passes through the list multiple times, comparing adjacent items.

## Background

Bubble sort works by repeatedly stepping through the list and comparing each pair of neighboring items. If the first item is bigger than the second, they swap places. After each full pass through the list, the largest unsorted item has moved all the way to the end—like a bubble floating up. Then you do another pass, and the second-largest item floats up. You keep doing this until no more swaps are needed. The algorithm is easy to understand and to write, which is why it appears in many beginner textbooks. But it is slow. If you have 1000 items, bubble sort might make around 500,000 comparisons in the worst case. For 10,000 items, that number grows much larger. As the list size increases, the time grows as the square of the size. An improvement called bubble-sort-with-early-exit stops a pass early if no swaps happened—this means the list is sorted. This can make bubble sort faster on data that is already sorted or nearly sorted, but it does not change the worst-case behavior. Bubble sort is almost never used in real programs, except as a teaching tool to explain how sorting works.

## See also

Related:: [[sorting-algorithms-overview]], [[insertion-sort]]
