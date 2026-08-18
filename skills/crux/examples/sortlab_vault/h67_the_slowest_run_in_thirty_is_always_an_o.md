---
id: h67
type: idea
schema: 2
title: The slowest run in thirty is always an outlier
parent: q22
status: done
rule: all
measurement: Time for one sort pass on 5000 items, with perf_counter.
replicates: 30 repeats of insertion sort.
verdict: refuted
metric: Max 3.4 ms is 3.75 standard deviations above mean of 3.1 ms.
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: 4814d7cbdc42feca
lock: 816bbd3a92e83dfc
locked: "2026-08-16T16:06:56"
lock_at: running
---

# h67 — The slowest run in thirty is always an outlier

Parent:: [[q22_how_many_repeats_do_i_need_before_the_nu]]

## ELI5

In any set of 30 repeats, the slowest one is always an outlier unusually far from the rest.

## TL;DR

The slowest run is often much slower than the second-slowest. That suggests it is a fluke, not part of the normal spread. The run looks at the gap between the max and second-max times and checks if the slowest is unusually far away.

Background:: [[wiki/outlier-trimming]]

## Null
instrumentation - the slowest run is just the natural tail; not an outlier worth removing

## Problem Statement

Some runs are just slow for no good reason. If I can identify them as flukes, I can ignore them. The question is whether the slowest run is a real outlier or just the natural tail of the distribution.

## Idea / Hypothesis

The slowest run in thirty is always an outlier

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The slowest run is more than two standard deviations from the mean. (found: Mean: 3.1 ms, std dev: 0.08 ms. Max: 3.4 ms. Difference: 3.75 sigma. Very far out)
      fails-if:: The max is less than two sigma from the mean.
      discriminates:: true
- [ ] The slowest run of the thirty takes more than twice the median time (found: Max 3.4 ms against median 3.1)
      fails-if:: The slowest run stays under twice the median time
- [x] [outcome-neutral] The input list is the same for all runs. (found: Verified: same shuffled list for all 30 runs)
      fails-if:: The list changes or is accidentally pre-sorted.

## Planned Intervention

Insertion sort on 5000 random items, run 30 times. I looked at the times and identified the max and second-max. I calculated how many standard deviations the max was from the mean.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h67/ and link at least the report:
     - [Report](results/h67/report.md)   - results/h67/curve.png -->
_(none yet)_

## Findings

The slowest run is a true outlier. It is way too slow to be a normal run. The second-slowest is at 3.3 ms, which is much closer to the pack. The outlier probably caught a background event. But it happened on runs I counted, so I cannot just ignore it.
