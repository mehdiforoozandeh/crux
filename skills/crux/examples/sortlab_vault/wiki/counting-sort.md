---
type: wiki
title: Counting sort
summary: Counting sort counts how many items have each value, then reconstructs the sorted list from these counts.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Counting sort

Counting sort is fundamentally different from comparison-based sorts. It works only for data where you know the range of values in advance.

## Background

Comparison-based sorting algorithms like bubble sort or merge sort determine order by comparing pairs of items. Counting sort takes a different approach: it counts how many items have each value. This only works if the values are limited—like if you know all values are between 1 and 1000. The algorithm creates a temporary array with one slot for each possible value. It then passes through the input list once and counts how many items have each value. From these counts, it reconstructs the sorted list. This takes O(n + k) time, where n is the number of items and k is the range of values. If k is small relative to n, counting sort can be faster than comparison-based methods. The catch is that counting sort needs extra memory equal to the range of values. It does not help if you want to sort words alphabetically, or if values can be any number. Counting sort is stable: equal items maintain their original order. It is rarely used on its own but is a building block for [[radix-sort]], which handles larger values by sorting digit-by-digit.

## See also

Related:: [[sorting-algorithms-overview]], [[radix-sort]]
