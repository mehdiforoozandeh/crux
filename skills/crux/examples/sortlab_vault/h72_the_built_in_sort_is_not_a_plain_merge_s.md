---
id: h72
type: idea
schema: 2
title: The built-in sort is not a plain merge sort
parent: q24
status: done
rule: all
measurement: Time for one sort pass, with perf_counter.
replicates: 5 repeats at each of 3 shapes.
verdict: supported
metric: "Built-in on sorted: 0.0082 s. On random: 0.81 s. Merge: both around 6.7 s."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 66e3c32adb505657
lock: 21f239fc74bc7f63
locked: "2026-08-16T16:06:57"
lock_at: running
---

# h72 — The built-in sort is not a plain merge sort

Parent:: [[q24_does_the_built_in_sort_use_a_smarter_met]]

## ELI5

Python's built-in sort does more than just merge two halves; it does something smarter.

## TL;DR

A plain merge sort on a sorted or nearly-sorted list is still O(n log n). But the built-in sort should be much faster on such lists. The claim is that the built-in uses a hybrid strategy that detects order and adapts. The run times lists that are already sorted, reversed, and random.

Background:: [[wiki/timsort]]

## Null
capacity - both sorts handle all shapes the same; differences are noise

## Problem Statement

If the built-in is just a merge sort, it should take the same time on a sorted list and a random list. But I suspect it is smarter and notices when data is already in order.

## Idea / Hypothesis

The built-in sort is not a plain merge sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Built-in sort is much faster on sorted data than on random data. (found: Built-in on sorted: 0.0082 s. On random: 0.81 s. 99x faster on sorted)
      fails-if:: Built-in takes similar time on sorted and random.
      discriminates:: true
- [x] Merge sort takes similar time on sorted and random data. (found: Merge on sorted: 6.8 s. On random: 6.6 s. No significant difference)
      fails-if:: Merge sort is faster on sorted data.
- [x] [outcome-neutral] The input lists are actually in the claimed shapes. (found: Verified: sorted list is sorted, reversed list is reverse sorted, random list is shuffled)
      fails-if:: The lists are not properly ordered or shuffled.

## Planned Intervention

Built-in sort and my merge sort on 100000 items in three shapes: sorted, reversed, and random. Five repeats of each. Timed with perf_counter. Plugged in.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h72/ and link at least the report:
     - [Report](results/h72/report.md)   - results/h72/curve.png -->
_(none yet)_

## Findings

The built-in sort is not a plain merge sort. It detects sorted data and runs much faster. My merge sort takes the same time regardless of order. The built-in must have special logic to handle partially sorted lists.
