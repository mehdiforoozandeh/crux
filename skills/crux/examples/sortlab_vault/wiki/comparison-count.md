---
type: wiki
title: Counting comparisons
summary: Counting comparisons is a way to measure algorithm efficiency without running code or assuming a specific computer.
category: concept
sources: raw/handout-ch09-growth-rates.txt
---

# Counting comparisons

Instead of timing algorithms, counting the number of comparisons they make predicts which will be faster.

## Background

When comparing sorting algorithms, one approach is to measure how fast they run. But this depends on the computer, the programming language, and many details. A better way to compare algorithms is to count how many times they compare two items. This is a measurement that depends only on the algorithm and the data, not on the hardware. Bubble sort on a list of n items makes roughly n squared comparisons in the worst case. Merge sort makes roughly n log n comparisons. Quick sort makes roughly n log n comparisons on average. By counting comparisons, you can predict that merge sort will be faster than bubble sort on a large list, without needing to time either one. Comparison counting assumes that comparing two items takes roughly the same time for all algorithms, which is usually true. It ignores other operations like swaps or bookkeeping, which is a simplification but usually a reasonable one. Comparison counting makes analysis easier mathematically and makes predictions more portable—the prediction works whether you use Python, C, or another language. Of course, some algorithms do things besides comparisons, and the simplified count might not tell the whole story. But for sorting algorithms, comparison count is a reliable way to predict relative performance.

## See also

Related:: [[algorithm-analysis-overview]], [[growth-rate-curves]]
