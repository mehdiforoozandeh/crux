---
type: wiki
title: Reverse-sorted input
summary: A test list where items are in order from largest to smallest, the opposite of what the sort expects.
category: dataset
sources: raw/handout-ch07-sorting-basics.txt
---

# Reverse-sorted input

Reverse-sorted input is often the worst case for comparison sorts. Code must do maximum work to fix the order.

## Background

If sorted input is the best case, reverse-sorted input is often close to the worst case. Every item is as far from its correct position as it can be. Many algorithms have to do a lot of comparisons and swaps to fix this. Bubble sort has to bubble items all the way to the opposite end, which takes many passes. Insertion sort has to shift items one by one through the entire array. Selection sort does not care about order and takes the same time as always, but other algorithms suffer. Quick sort with a bad pivot strategy can split reverse-sorted data in a bad way and take a long time. Testing with reverse-sorted input shows you whether an algorithm has built-in defenses against its worst case. Coupled with random and sorted input, reverse-sorted data completes a basic picture of how the algorithm scales.

## See also

Related:: [[benchmarking-practice-overview]], [[nearly-sorted-input]]
