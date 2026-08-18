---
type: wiki
title: Growth-rate curves
summary: Growth-rate curves are graphs showing how an algorithm's runtime increases as input size grows.
category: concept
sources: raw/handout-ch09-growth-rates.txt, raw/teacher-note-reading-a-graph.txt
---

# Growth-rate curves

Plotting runtime against input size reveals the shape of an algorithm's growth: linear, quadratic, logarithmic, etc.

## Background

One way to understand algorithm complexity is to plot it. On a graph with input size on the horizontal axis and time on the vertical axis, different algorithms make different shapes. An O(n) algorithm makes a straight line. An O(n^2) algorithm makes a steep curve that gets steeper as n grows. An O(n log n) algorithm makes a curve between these. An O(1) algorithm makes a flat line. By plotting the actual measured times for different input sizes, you can see which curve your algorithm follows. If the curve matches the shape predicted by Big-O analysis, you have verified the analysis. If it does not, something unexpected is happening. Growth-rate curves are useful for visualizing how an algorithm scales. You can see at a glance that an O(n^2) algorithm will become impossible to use for large data. You can also spot when an algorithm is faster than another up to a certain size, then slower beyond that size. This is called a crossover point. Understanding curves helps build intuition about why Big-O matters: two algorithms that are equally fast for 1000 items might be dramatically different for 1 million items. Plotting curves is also a good way to spot mistakes: if a measured curve does not match the theoretical prediction, the analysis or the measurement might be wrong.

## See also

Related:: [[algorithm-analysis-overview]], [[doubling-experiments]]
