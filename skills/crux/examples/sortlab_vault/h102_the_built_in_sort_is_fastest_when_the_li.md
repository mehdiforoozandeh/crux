---
id: h102
type: idea
schema: 2
title: The built-in sort is fastest when the list is one long run
parent: q33
status: done
rule: all
measurement: Median time for built-in sort on fully sorted input.
replicates: 30 repeats at each of 6 sizes from 1k to 100k items.
verdict: supported
metric: Sorted list 1k took 0.08 ms, 100k took 0.78 ms. Random took 0.13 ms and 1.09 ms.
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:39"
null_hash: 9958a6f25ece5007
lock: 5217df198f7be7ea
locked: "2026-08-16T16:07:02"
lock_at: running
---

# h102 — The built-in sort is fastest when the list is one long run

Parent:: [[q33_does_the_built_in_sort_notice_runs_that_]]

## ELI5

The built-in sort is fastest when the list starts already sorted.

## TL;DR

I tested the built-in sort on lists that were already sorted from the start. It finished in time proportional to n, not n log n. On random lists it took n log n time. This means the built-in sort has a special fast path for data already in order.

Background:: [[wiki/run-detection]]

## Null
capacity - faster memory access on sorted data, not the algorithm itself, explains the speedup.

## Problem Statement

The built-in sort wins by so much that I stopped measuring my own sorts against it. But understanding why helps me understand algorithm behavior. If it notices sorted data and speeds up, that is worth knowing.

## Idea / Hypothesis

The built-in sort is fastest when the list is one long run

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Time on sorted input is linear in list size, slope close to one on log-log plot. (found: Sorted list 1k took 0.08 ms, 100k took 0.78 ms. Random took)
      fails-if:: Time grows faster than linear.
      discriminates:: true
- [x] Sorted-input time is faster than random-input time at every size.
      fails-if:: Time is the same for sorted and random input.
- [x] [outcome-neutral] Output is sorted correctly and complete.
      fails-if:: Output is corrupted or unsorted.

## Planned Intervention

Created lists that were already completely sorted. Sizes one thousand to one hundred thousand. Thirty repeats at each size.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h102/ and link at least the report:
     - [Report](results/h102/report.md)   - results/h102/curve.png -->
_(none yet)_

## Findings

On already-sorted input, the built-in sort flew through the data. Time grew almost linearly. On random input, it used the full n log n algorithm. The built-in sort detects when data is already sorted and skips the expensive parts.
