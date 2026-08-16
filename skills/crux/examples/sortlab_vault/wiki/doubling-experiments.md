---
type: wiki
title: Doubling experiments
summary: A doubling experiment repeatedly measures an algorithm on lists twice as large, revealing the growth pattern.
category: method
sources: raw/handout-ch09-growth-rates.txt, raw/teacher-note-reading-a-graph.txt
---

# Doubling experiments

By running an algorithm on a list, then on a list twice as large, and observing how the time changes, you can infer the Big-O complexity.

## Background

Doubling experiments are a practical way to find the growth rate of an algorithm without complex analysis. You measure the time to sort a list of size n. Then you measure the time to sort a list of size 2n. If the time roughly doubles, the algorithm is O(n). If the time roughly quadruples, the algorithm is O(n^2). If the time increases by a factor of about 2.3, the algorithm is roughly O(n log n). By repeating this (size 2n, then 4n, then 8n, and so on), you can build confidence in the growth pattern. Doubling experiments have practical advantages: you do not need to analyze the algorithm mathematically. You just measure it. You see real data, not theoretical predictions. However, doubling experiments have limitations. For small sizes, noise and variation in measurement can mask the pattern. You need to ensure the input data is consistent across runs. You need enough doubling steps to see the pattern emerge. The ratios might not be perfect at small sizes but should stabilize at larger sizes. Doubling experiments are often used to verify theoretical analysis or to find the complexity of an algorithm you do not fully understand. They bridge measurement and theory: you predict a Big-O based on experiments, then use Big-O to predict behavior at much larger sizes than you could test.

## See also

Related:: [[algorithm-analysis-overview]], [[crossover-points]]
