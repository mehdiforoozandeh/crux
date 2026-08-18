---
type: wiki
title: Sorting algorithms overview
summary: Sorting algorithms arrange data in order using different strategies and speeds.
category: overview
sources: raw/handout-ch07-sorting-basics.txt, raw/handout-ch08-divide-and-conquer.txt
---

# Sorting algorithms overview

A sorting algorithm is a step-by-step method that takes unsorted data and puts it in order. Different algorithms trade off simplicity for speed.

## Background

A sorting algorithm is a set of instructions that arranges items—like numbers or names—in order from smallest to largest, or alphabetically. Some algorithms work by repeatedly comparing pairs of items and swapping them. Others divide the items into smaller chunks, sort those, and merge them back together. The choice of algorithm matters because some are much faster than others, especially when you have many items to sort. A [[bubble-sort]] keeps swapping neighboring items until everything is in order, which works but takes a long time for large lists. Other algorithms like [[merge-sort]] use a divide-and-conquer strategy: break the list in half, sort each half, then combine them. No single algorithm is best for every situation. Some are simple to write and understand. Others are more complex but faster. Some work well when data is already partially sorted, while others do not notice such patterns. Understanding how different sorting algorithms work helps explain why some programs feel fast and others feel slow.

## See also

Related:: [[bubble-sort]], [[algorithm-analysis-overview]]
