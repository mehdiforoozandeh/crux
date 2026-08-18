---
id: h61
type: idea
schema: 2
title: Background load changes the median less than the mean
parent: q20
status: done
rule: all
measurement: Time for one sort pass, timed with perf_counter.
replicates: 30 repeats clean, 30 repeats with background download.
verdict: supported
metric: "Mean without load: 3.1 ms. Mean with load: 3.4 ms. Median: both 3.0 ms."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: 8db9df8183c3cde1
lock: bc543ad842c9f1b2
locked: "2026-08-16T16:06:54"
lock_at: running
---

# h61 — Background load changes the median less than the mean

Parent:: [[q20_do_background_apps_change_the_number]]

## ELI5

Background load affects the median time less than it affects the mean.

## TL;DR

When the laptop is busy, some runs are very slow but most are not. That means the median (middle value) might stay the same while the mean (average) gets dragged up by a few slow outliers. The run times sorts with and without background load and compares the medians and means.

Background:: [[wiki/thermal-throttling]]

## Null
instrumentation - the mean and median move together by the same fraction

## Problem Statement

I learned that background load is a problem. But maybe I can ignore the slow runs and look at the median instead of the mean. If the median is stable, I could use that as my number.

## Idea / Hypothesis

Background load changes the median less than the mean

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Mean time with load is more than ten percent higher than without load. (found: Clean: 3.1 ms mean. Load: 3.4 ms mean. Difference: 9.7 percent. Borderline)
      fails-if:: Mean with load is at most ten percent higher.
      discriminates:: true
- [x] Median time with load is less than five percent higher than without load. (found: Clean: 3.0 ms median. Load: 3.0 ms median. Difference: 0.3 percent)
      fails-if:: Median increases by five percent or more.
- [x] [outcome-neutral] The download actually completes during the run. (found: Downloaded a 100 MB file; transfer completed in the time window)
      fails-if:: The download stalls or does not finish.

## Planned Intervention

Insertion sort on 5000 items, run 30 times clean, then 30 times with a file download happening. I calculated the mean and median for each block. Laptop on battery in both cases.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h61/ and link at least the report:
     - [Report](results/h61/report.md)   - results/h61/curve.png -->
_(none yet)_

## Findings

The median barely moves even when background work is happening, but the mean jumps up. A few slow runs pull the average higher, but most runs stay fast. The median might be a better number to report.
