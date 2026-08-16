---
type: wiki
title: Crossover points
summary: A crossover point is the input size where one algorithm becomes faster than another.
category: concept
sources: raw/club-handout-hybrid-sorts.txt
---

# Crossover points

Two algorithms might have different complexity but vary in their constant factors. One is faster on small inputs, another on large inputs.

## Background

Two algorithms with different Big-O complexity intersect at some input size, called the crossover point. For example, insertion sort is O(n^2) but has very small constant factors. Quick sort is O(n log n) but has more overhead. For very small lists (say, 10 items), insertion sort might be faster. For medium lists (say, 100 items), they might be similar. For large lists (say, 10,000 items), quick sort is decisively faster. The crossover point is the input size where quick sort first becomes faster. Finding crossover points is useful for hybrid algorithms. If you know that insertion sort is faster for lists under 20 items, you can use quick sort for larger partitions but switch to insertion sort for small partitions, getting the best of both worlds. Crossover points depend on constant factors in the code, which depend on the programming language, the computer, and implementation details. The same algorithm might have different crossover points in Python versus C. This is why pure Big-O analysis can be misleading: two O(n log n) algorithms might have very different crossover points with other algorithms. Predicting crossover points requires either doing doubling experiments or having deep understanding of the implementations. Practical engineering often finds crossover points by measurement, then uses that knowledge to optimize.

## See also

Related:: [[algorithm-analysis-overview]], [[stability]]
