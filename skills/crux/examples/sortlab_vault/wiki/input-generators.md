---
type: wiki
title: Input generators
summary: Programs that create lists for testing, choosing what kind of list to make based on the test design.
category: method
sources: raw/teacher-note-fair-comparisons.txt
---

# Input generators

Different lists trigger different behaviors in sorting algorithms. An input generator creates the right test data automatically.

## Background

To test a sorting algorithm fairly, you need lists that represent different real situations. A random list is one kind of test. A sorted list is another. A list with many duplicates is another. If you hand-code each test list, you might accidentally favor one algorithm. An input generator writes code to create the test lists automatically, following rules you specify. You tell it the size of the list, what pattern to use (random, sorted, reverse, duplicates), and whether to use a fixed seed so you get the same list every time. The generator then creates that list. This ensures every algorithm gets exactly the same input, so differences in timing come from the algorithm, not from testing errors. When you scale up from 1,000 items to 10,000, the generator makes lists of both sizes with the same pattern, so you can see how the algorithm scales. Using a generator is more work at the start but much cleaner than managing lists by hand.

## See also

Related:: [[benchmarking-practice-overview]], [[random-permutations]]
