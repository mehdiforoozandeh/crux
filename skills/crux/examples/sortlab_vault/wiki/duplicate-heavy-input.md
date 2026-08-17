---
type: wiki
title: Duplicate-heavy input
summary: A test list where many items have the same value, not all different as most algorithm examples assume.
category: dataset
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Duplicate-heavy input

Real data often has duplicates. Sorting with many repeated values behaves differently from sorting all-unique data.

## Background

Many algorithm textbooks show examples where all items are different. But real data often has many copies of the same value. A list of student grades might have many 85s and 90s. A list of country names has many instances of common ones. Sorting data with duplicates uses the same basic steps as sorting unique data, but comparison counts can differ. Quick sort with three-way partitioning can skip items equal to the pivot, making it faster. Bubble sort does not get this advantage. Insertion sort with a stable variant preserves the original order of duplicates, which sometimes costs extra time. Testing with duplicate-heavy input reveals these differences. It also tells you whether the test data is realistic. In benchmarking, you want test data that resembles real use, and many real lists have many duplicates. A good test suite includes this case alongside random and sorted lists.

## See also

Related:: [[benchmarking-practice-overview]], [[seeded-randomness]]
