---
type: wiki
title: Fitting a curve
summary: Drawing a line or curve through data points to guess a formula that predicts performance at sizes you have not tested.
category: method
sources: raw/teacher-note-reading-a-graph.txt, raw/handout-ch09-growth-rates.txt
---

# Fitting a curve

When you plot times against list sizes, the points often follow a pattern. A curve fitted to that pattern lets you predict future performance.

## Background

Suppose you time a sort on lists of size 1,000, 2,000, 4,000, and 8,000 items. You get four times. You can plot these as points on a graph. If you draw a line through these points, you can estimate the time for size 16,000 by reading the line, even though you never tested that size. This is curve fitting. The simplest fit is a straight line, but some data follows other patterns. Many sorting algorithms follow a pattern like n times log n, where time is proportional to the list size times the logarithm of the size. You can fit that pattern to your data using mathematical techniques. Once you have the fit, you can plug in any future size and predict the time. This is useful for planning: if your sort takes 10 milliseconds on 1,000 items and follows n log n, how long will it take on 1 million items? But curve fitting has risks. [[extrapolation-risks]] discusses why predictions outside your data range are unreliable.

## See also

Related:: [[algorithm-analysis-overview]], [[extrapolation-risks]]
