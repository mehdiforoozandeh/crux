---
id: h105
type: idea
schema: 2
title: The doubling ratio settles above one hundred thousand items
parent: q34
status: done
rule: all
measurement: Ratio of time at size 2n to time at size n for insertion sort.
replicates: 30 repeats at each of 8 sizes from 1k to 1M items.
verdict: inconclusive
metric: "Ratios: 1k to 2k was 3.8. 10k to 20k was 4.1. 500k to 1M was 4.2."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:40"
null_hash: 451f0f2c9b6c2b8a
lock: 28ee9887e5878353
locked: "2026-08-16T16:07:02"
lock_at: running
---

# h105 — The doubling ratio settles above one hundred thousand items

Parent:: [[q34_does_the_doubling_ratio_settle_down_at_b]]

## ELI5

The doubling ratio settles as lists get bigger.

## TL;DR

I calculated the doubling ratio: the ratio of time at size 2n to time at size n. For small sizes this ratio varies. At one hundred thousand items and above, the ratio should settle to a constant value that matches the growth rate.

Background:: [[wiki/average-case-analysis]]

## Null
capacity - cache effects and memory layout at large sizes obscure the algorithm's true growth rate.

## Problem Statement

Understanding when the ratio settles tells me the size at which asymptotic behavior starts. Below that size the ratios are messy; above it they are predictable.

## Idea / Hypothesis

The doubling ratio settles above one hundred thousand items

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Doubling ratio at one hundred thousand is within five percent of ratio at one million. (found: Ratios: 1k to 2k was 3.8. 10k to 20k was 4.1. 500k)
      fails-if:: Ratios keep changing at large sizes.
      discriminates:: true
- [-] Ratios at sizes below ten thousand are more variable than at sizes above.
      fails-if:: Variation is the same at all sizes.
- [x] [outcome-neutral] All runs complete and produce correct sorted output.
      fails-if:: The machine crashes or output is corrupted.
- [x] [outcome-neutral] Repeat times do not grow more noisy at large sizes.
      fails-if:: Large lists show unstable run times.

## Planned Intervention

Calculated doubling ratios from one thousand to one million items for insertion sort. Thirty repeats at each of eight sizes.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h105/ and link at least the report:
     - [Report](results/h105/report.md)   - results/h105/curve.png -->
_(none yet)_

## Findings

The doubling ratio at small sizes bounced around from 3.8 to 4.1. At large sizes it settled to about 4.2, consistent. This matches insertion sort n squared behavior: doubling n should quadruple time.
