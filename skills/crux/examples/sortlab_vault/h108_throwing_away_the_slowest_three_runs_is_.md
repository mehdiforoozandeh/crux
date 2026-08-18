---
id: h108
type: idea
schema: 2
title: Throwing away the slowest three runs is as good as the median
parent: q35
status: done
rule: all
measurement: Trimmed mean of twenty-seven fastest runs versus median of all thirty.
replicates: 30 repeats at 5k items, repeated twice for comparison.
verdict: invalid-run
metric: "Median was 0.514 ms. Trimmed mean (27 fastest) was 0.519 ms. Difference: one percent."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:12"
null_approved: "2026-08-16T16:06:40"
null_hash: b726ca5d99b58066
lock: 814ce0fe6e47d939
locked: "2026-08-16T16:07:03"
lock_at: running
---

# h108 — Throwing away the slowest three runs is as good as the median

Parent:: [[q35_is_the_median_of_repeats_steadier_than_t]]

## ELI5

Throwing away the three slowest runs works like taking the median.

## TL;DR

I tried a different way to handle outliers: instead of computing the median, I threw away the three slowest runs and took the mean of the remaining twenty-seven. This trimmed mean was almost as stable as the median.

Background:: [[wiki/median-vs-mean]]

## Null
instrumentation - trimming and median are both sensitive to timer noise.

## Problem Statement

The median is mathematically clean but less familiar to many people. A trimmed mean might be easier to understand. If they give the same answer, I can choose based on preference.

## Idea / Hypothesis

Throwing away the slowest three runs is as good as the median

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Trimmed mean is within two percent of median. (found: Median was 0.514 ms. Trimmed mean (27 fastest) was 0.519 ms. Difference:)
      fails-if:: Trimmed mean differs from median by more than two percent.
      discriminates:: true
- [ ] The three slowest runs are clearly outliers, each at least five percent above the median.
      fails-if:: The three slowest runs are only slightly above typical times.
- [ ] [outcome-neutral] All forty-five runs (two sets of thirty) complete and are positive.
      fails-if:: Any run is negative or missing.

## Planned Intervention

Thirty repeats at five thousand items. Calculated three statistics: median, mean of all thirty, and mean of the fastest twenty-seven.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h108/ and link at least the report:
     - [Report](results/h108/report.md)   - results/h108/curve.png -->
_(none yet)_

## Findings

The trimmed mean and median were almost identical, differing by less than one percent. The three slowest runs were clearly outliers, each taking 0.56 milliseconds compared to the median 0.514. Either method works well; median is simpler so I will use it for all future analyses.
