---
type: wiki
title: Random permutations
summary: A test list where the items are in random order, with every position equally likely to have any value.
category: dataset
sources: raw/teacher-note-fair-comparisons.txt
---

# Random permutations

Random input is the most basic test case. It does not favor any pattern that an algorithm might detect.

## Background

When you shuffle a deck of cards thoroughly, you get a random permutation. Every position has an equal chance of holding any card. A random list for testing is similar: the items are in unpredictable order. No part of the list is already sorted, no items cluster together, no pattern is obvious. Random input is the hardest test case for most sorting algorithms because the algorithms cannot exploit any structure. If an algorithm has special code for already-sorted data or nearly-sorted data, random input bypasses all of that. This is why random input is a good baseline test. However, real data in the world is often not random. It often has patterns and structure. So a good [[measuring-program-speed]] plan includes random input but also other kinds like sorted data and nearly sorted data. The question of what kinds of input represent real use is itself a research question.

## See also

Related:: [[benchmarking-practice-overview]], [[sorted-input]]
