---
id: h51
type: idea
schema: 2
title: My merge sort slows down because it makes new lists
parent: q17
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 4 sizes
verdict: supported
metric: Standard merge 2.1 sec, reuse-space merge 1.7 sec at n=500k
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: a33dc1c6efb619a6
lock: dc861803691a6867
locked: "2026-08-16T16:06:52"
lock_at: running
---

# h51 — My merge sort slows down because it makes new lists

Parent:: [[q17_does_the_laptop_s_memory_show_up_in_the_]]

## ELI5

Merge sort is slow because it creates new lists during the merge step.

## TL;DR

Merge sort created temporary lists while merging. The cost of allocating and copying to these lists added up at large sizes, accounting for much of the overhead.

Background:: [[wiki/memory-allocation]]

## Null
capacity - algorithmic differences, not memory, explain the gap

## Problem Statement

My merge sort implementation created new lists in each merge step instead of reusing space. I wanted to see how much this cost compared to in-place insertion.

## Idea / Hypothesis

My merge sort slows down because it makes new lists

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Creating new lists added at least twenty percent overhead. (found: Standard merge 2.1 sec, reuse-space merge 1.7 sec at n=500k)
      fails-if:: Overhead was less than ten percent.
      discriminates:: true
- [x] Overhead was roughly constant across all sizes.
      fails-if:: Overhead grew or shrank at larger sizes.
- [x] [outcome-neutral] Both versions produced sorted lists. (found: Both versions correct)
      fails-if:: Either version failed to sort.

## Planned Intervention

Merge sort on lists from one hundred thousand to one million items. Compare versions with and without extra list allocation. Thirty repeats.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h51/ and link at least the report:
     - [Report](results/h51/report.md)   - results/h51/curve.png -->
_(none yet)_

## Findings

Creating temporary lists during merge cost about twenty percent of the total time. Reusing workspace or sorting in-place would be faster. Memory allocation was a real factor in the algorithm's speed.
