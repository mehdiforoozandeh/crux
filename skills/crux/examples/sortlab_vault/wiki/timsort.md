---
type: wiki
title: Timsort
summary: Timsort is a hybrid algorithm combining merge sort and insertion sort, designed to handle partially sorted real-world data efficiently.
category: method
sources: raw/docs-note-python-list-sort.txt, raw/magazine-column-why-builtins-win.txt
---

# Timsort

Timsort adapts to the structure of real data by detecting sorted runs and using them to guide a hybrid approach.

## Background

Timsort is the sorting algorithm used by Python's built-in sort function. It is a hybrid designed to be fast on real data, which is often partially sorted rather than random. The algorithm begins by detecting runs—stretches of data that are already sorted or reverse-sorted. Small runs are extended to a minimum length using insertion sort. These runs are then merged together using a merge-sort-like process. This design makes timsort very fast on nearly-sorted data. If you sort data that is already 90 percent sorted, timsort will recognize the existing sorted sections and take advantage of them. On random data, timsort falls back to merge-sort-like behavior with O(n log n) performance. Timsort is stable and uses a reasonable amount of extra memory. It is more complex to implement than simpler algorithms, but the complexity is worth it for general-purpose use. The design of timsort teaches an important lesson: the best algorithm depends on the data. Rather than always using the same approach, timsort observes the data and adapts its strategy. This is why Python and other languages use sophisticated algorithms in their built-in sort functions instead of simple ones. Understanding timsort requires understanding [[hybrid-sorts]] and the idea that detecting patterns in data can lead to smarter algorithms.

## See also

Related:: [[sorting-algorithms-overview]], [[hybrid-sorts]]
