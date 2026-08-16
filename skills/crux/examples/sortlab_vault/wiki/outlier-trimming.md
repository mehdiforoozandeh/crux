---
type: wiki
title: Trimming outliers
summary: Removing the slowest and fastest times to ignore random bad luck before calculating a summary.
category: method
sources: raw/club-talk-benchmark-mistakes.txt
---

# Trimming outliers

Sometimes a run is so slow or so fast that it probably was not a fair test. Trimming the extremes gives you a cleaner picture.

## Background

When you have thirty runs and one of them is three times slower than the rest, that run was probably interrupted. Throwing it away before you compute the median or mean gives a fairer answer. This is called trimming or clipping. A common trim is to remove the fastest ten percent and the slowest ten percent before calculating your answer. This removes the lucky runs where nothing interfered and the unlucky runs where something did. The question is: how much do you trim? If you trim too much, you lose real data. If you trim too little, one bad run still ruins everything. Some researchers trim five percent, some trim ten, some trim twenty-five. The choice is a judgment call. You should decide your trim rule before you run the test, not after, because changing it to get a better answer is cheating. This connects to [[measuring-program-speed]] because you want your final number to represent typical performance, and [[repeated-trials]] because trimming only makes sense when you have enough runs to lose a few and still have a solid middle.

## See also

Related:: [[measuring-program-speed]], [[micro-benchmarking-pitfalls]]
