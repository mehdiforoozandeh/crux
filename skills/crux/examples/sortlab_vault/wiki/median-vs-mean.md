---
type: wiki
title: Median or mean
summary: Using the middle value instead of the average to describe typical performance when one slow run throws off the average.
category: method
sources: raw/club-talk-benchmark-mistakes.txt, raw/teacher-note-reading-a-graph.txt
---

# Median or mean

The average is pulled upward by any single slow run, but the median ignores extremes. For timing, the median is more honest.

## Background

Imagine you run a test five times and get these times: 10, 10, 11, 10, 50 milliseconds. The average is 18 milliseconds. But four out of five runs were around 10 milliseconds. That one 50-millisecond run happened because your laptop started updating software in the background. Using the average of 18 as the typical time tells a lie about what your code usually does. The median is the middle value when you sort all your numbers. Here it is 10 milliseconds. The median ignores that one slow outlier. For [[measuring-program-speed]] and [[repeated-trials]], the median is almost always better than the mean because a single interruption can make one run much slower without affecting the others. However, the mean and median tell different stories when the times cluster in two distinct groups, which sometimes happens if the code takes a different path depending on the input. Always report both and explain what you see. The median is what most benchmarking tools report by default.

## See also

Related:: [[measuring-program-speed]], [[outlier-trimming]]
