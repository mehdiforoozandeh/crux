---
type: wiki
title: Average case
summary: Average case analysis predicts how an algorithm performs on typical, randomly distributed input data.
category: concept
sources: raw/handout-ch09-growth-rates.txt
---

# Average case

Average case assumes the input is a random permutation and counts the expected number of operations.

## Background

When analyzing algorithms, best and worst cases tell you the extremes. But what about typical runs? Average case analysis assumes the input is a random arrangement of distinct items and counts how many operations you expect. For bubble sort, the average case is still O(n^2): even on random data, the algorithm makes many comparisons. For quick sort with a random pivot, the average case is O(n log n), which is why quick sort is popular despite its bad worst case. For insertion sort, the average case is O(n^2) because on random data, each item is typically about halfway through the sorted portion when inserted. Average case analysis uses probability: what is the expected position of the first unsorted item, the second, and so on. This requires mathematical reasoning and often assumes a specific probability distribution. The key assumption is that the input is random. Real data often deviates from random: it might be partially sorted, contain duplicates, or have structure. When this happens, actual performance might differ from the average case prediction. Some algorithms adapt to non-random data and perform better. Understanding average case helps predict performance on typical inputs, but it is only a prediction. Code should be tested on realistic data, not just theoretical average cases.

## See also

Related:: [[algorithm-analysis-overview]], [[comparison-count]]
