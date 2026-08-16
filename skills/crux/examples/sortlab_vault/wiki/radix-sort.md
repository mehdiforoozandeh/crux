---
type: wiki
title: Radix sort
summary: Radix sort sorts numbers by examining one digit at a time, from least significant to most significant.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Radix sort

Radix sort breaks numbers into digits and sorts them repeatedly, processing one digit position at a time using a stable sub-sort.

## Background

Radix sort is clever. To sort large numbers, it sorts by the ones place first, then the tens place, then the hundreds place, and so on. Each pass uses a stable sort (like counting sort) on just the current digit. After all digit positions have been processed, the list is fully sorted. The algorithm takes O(d × (n + k)) time, where d is the number of digit positions, n is the number of items, and k is the base (10 for decimal numbers, 2 for binary). Radix sort can be faster than comparison-based sorting if numbers have few digit positions relative to the number of items. It is stable. The main limitation is that radix sort is specialized: it only works well for integer data or other data that can be decomposed into digit-like positions. It does not work for sorting arbitrary text or complex objects. Radix sort is rarely taught in beginner courses, but it is useful in specific applications like sorting integers in a range, or sorting network addresses. Understanding radix sort reveals that comparison-based sorting is not the only way: sometimes breaking a problem into smaller sorting problems (by digit) is faster.

## See also

Related:: [[sorting-algorithms-overview]], [[bucket-sort]]
