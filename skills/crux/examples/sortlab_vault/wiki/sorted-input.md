---
type: wiki
title: Already-sorted input
summary: A test list where items are already in order from smallest to largest.
category: dataset
sources: raw/handout-ch07-sorting-basics.txt
---

# Already-sorted input

Sorted input is the best-case scenario for many algorithms. Code that detects order runs very fast.

## Background

When input is already sorted, many algorithms can sense this and skip work. Insertion sort, for example, does almost no work on sorted input because it checks if each item is already in the right place and leaves it alone. Quick sort still has to partition but can finish early. Bubble sort with an early-exit flag notices that no swaps happen and stops immediately. Testing with sorted input reveals whether an algorithm has optimizations for easy cases. It also tells you the best-case time, which is useful to know. Sorted input is not realistic for many real problems, but it is worth measuring because it shows the algorithm at its best. The combination of sorted input, random input, and reverse-sorted input gives you three anchors on algorithm performance, and [[measuring-program-speed]] benefits from seeing the full range.

## See also

Related:: [[benchmarking-practice-overview]], [[reverse-sorted-input]]
