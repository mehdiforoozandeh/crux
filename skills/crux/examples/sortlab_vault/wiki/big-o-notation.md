---
type: wiki
title: Big-O notation
summary: Big-O notation describes how the time or space requirements of an algorithm grow with input size.
category: concept
sources: raw/handout-ch09-growth-rates.txt
---

# Big-O notation

Big-O gives a simple way to compare algorithms: O(n) means time grows with size, O(n^2) means time grows as the square of size, etc.

## Background

When analyzing algorithms, we want to know how they slow down as the input grows. Big-O notation is a shorthand for this. If an algorithm takes O(n) time, then doubling the input roughly doubles the time. If it takes O(n^2) time, doubling the input roughly quadruples the time. If it takes O(n log n), doubling the input increases time by a bit more than double. The Big-O notation drops constant factors and lower-order terms. An algorithm that takes 3n plus 5 comparisons is still O(n). An algorithm that takes n^2 plus n is still O(n^2) for large n, because n^2 dominates. This matters because constant factors matter less than the growth rate. An O(n^2) algorithm might be faster than an O(n log n) algorithm for tiny inputs, but for large inputs the O(n log n) algorithm wins decisively. Big-O is useful for comparing algorithms before implementing them. It is a theoretical tool based on counting operations and ignoring constant factors. Real computers have caches, memory, and other complications that can change the practical picture. But Big-O gives a good first approximation. Common complexities from fastest to slowest: O(1) constant, O(log n), O(n), O(n log n), O(n^2), O(n^3), O(2^n). Understanding Big-O is essential for choosing algorithms wisely.

## See also

Related:: [[algorithm-analysis-overview]], [[best-case-worst-case]]
