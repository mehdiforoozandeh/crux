---
id: h22
type: idea
schema: 2
title: My merge sort beats my quick sort on random lists
parent: q9
status: done
rule: all
measurement: Median time in milliseconds.
replicates: 30 repeats at each of 10 sizes
verdict: refuted
metric: Quick sort 11 ms, merge sort 18 ms at 100k random.
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: 19a8bc7edd4a2e9b
locked: "2026-08-16T16:06:46"
lock_at: running
---

# h22 — My merge sort beats my quick sort on random lists

Parent:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr]]

## ELI5

My merge sort beats my quick sort on random lists.

## TL;DR

I claimed merge sort is faster than quick sort on random lists across a range of sizes. I implemented both algorithms and timed them on random lists from one thousand to one hundred thousand items with thirty repeats per size. The results show quick sort is actually faster.

Background:: [[wiki/merge-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

Quick sort has a reputation for speed, but merge sort has more predictable performance. I wanted to know which one wins on my hardware.

## Idea / Hypothesis

My merge sort beats my quick sort on random lists

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Merge sort time is less than quick sort time at all sizes (found: Quick 11 ms vs merge 18 ms)
      fails-if:: Quick sort is faster than merge on any size
      discriminates:: true
- [ ] At 100k items, merge is within 10 percent of quick (found: Quick faster at all sizes)
      fails-if:: Quick is more than 20 percent faster than merge
- [x] [outcome-neutral] Quick sort and merge sort are given the same list at each size (found: Same list file used for both)
      fails-if:: The two sorts are given different lists at any size

## Planned Intervention

Geometric ladder from one thousand to one hundred thousand. Thirty repeats per size. Random input. High-resolution timer. Warm-up run discarded.

## Run Links

- SortLab notebook, week 4

## Artifacts

- [Report](results/h22/report.md)

## Findings

Quick sort actually beat merge sort at every size. I think the early pivot heuristic and cache locality of quick sort give it an advantage over the more methodical merge sort, even though both are O of n log n. The gap is not huge but it is consistent.
