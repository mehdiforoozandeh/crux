---
id: h107
type: idea
schema: 2
title: The median of thirty repeats moves less than the mean
parent: q35
status: done
rule: all
measurement: Spread in mean times versus spread in median times across repeat experiments.
replicates: 30 repeats at 5k items, done twice, four hours apart, same machine state.
verdict: supported
metric: "First run: median 0.514 ms, mean 0.523 ms. Second run: median 0.508 ms, mean 0.548 ms."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:40"
null_hash: 3c022b878e65943f
lock: 1eda3a13609a18ad
locked: "2026-08-16T16:07:03"
lock_at: running
---

# h107 — The median of thirty repeats moves less than the mean

Parent:: [[q35_is_the_median_of_repeats_steadier_than_t]]

## ELI5

The median run time varies less than the mean run time.

## TL;DR

I ran thirty repeats of the same sort at the same size. I calculated both the mean and median times. The median stayed much more stable from one test to the next. The mean jumped around because one or two slow runs pulled it up.

Background:: [[wiki/outlier-trimming]]

## Null
instrumentation - noise in the timer made both mean and median equally noisy.

## Problem Statement

Choosing between mean and median matters for curve-fitting. If median is steadier, I should use it. If both are equally noisy, it does not matter.

## Idea / Hypothesis

The median of thirty repeats moves less than the mean

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Median of first thirty runs is within three percent of median of second thirty. (found: First run: median 0.514 ms, mean 0.523 ms. Second run: median 0.508)
      fails-if:: The two medians differ by more than three percent.
      discriminates:: true
- [x] Mean of first thirty differs from mean of second thirty by more than the median difference.
      fails-if:: Means are as stable as medians.
- [x] [outcome-neutral] No runs are negative or missing.
      fails-if:: Any run time is negative or corrupted.

## Planned Intervention

Thirty repeats of insertion sort at five thousand items, done twice on the same day. Calculated mean and median for each run of thirty. Compared how much the medians changed between runs.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h107/ and link at least the report:
     - [Report](results/h107/report.md)   - results/h107/curve.png -->
_(none yet)_

## Findings

The median changed from 0.514 to 0.508 milliseconds, a change of one percent. The mean changed from 0.523 to 0.548, a change of five percent. Median was four times more stable. This is because one or two outlier runs can pull the mean high but cannot move the median as much.
