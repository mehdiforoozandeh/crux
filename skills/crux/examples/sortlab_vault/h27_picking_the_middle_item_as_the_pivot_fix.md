---
id: h27
type: idea
schema: 2
title: Picking the middle item as the pivot fixes the sorted-list blow-up
parent: q10
status: running
rule: all
measurement: Median milliseconds for one quick-sort pass on a sorted list
replicates: 20 repeats at each of 6 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:06:47"
null_approved: "2026-08-16T16:06:32"
null_hash: 560b637cd45c4d6e
lock: 7d80080f0eddc5e0
locked: "2026-08-16T16:06:47"
lock_at: running
---

# h27 — Picking the middle item as the pivot fixes the sorted-list blow-up

Parent:: [[q10_does_my_quick_sort_break_on_a_list_that_]]

## ELI5

Picking the middle item as the pivot fixes the sorted-list blow-up.

## TL;DR

Quick sort's worst case on sorted data is because it always picks the first or last element as the pivot. If I pick the middle element instead, I can avoid the bad pivot chain and keep quick sort from blowing up. I plan to implement this median-of-three pivot strategy and test it on sorted lists up to one hundred thousand items.

Background:: [[wiki/recursion-depth]]

## Null
chance - one lucky pivot draw out of twenty would show this difference on its own

## Problem Statement

Quick sort is so much faster than merge sort on random data that losing it to the sorted list pathology is a shame. If I can fix the pathology with a smarter pivot choice, quick sort becomes much more reliable.

## Idea / Hypothesis

Picking the middle item as the pivot fixes the sorted-list blow-up

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The middle-item pivot sorts a sorted list at least ten times faster than the first-item pivot
      fails-if:: The middle-item pivot is under ten times faster on a sorted list
      discriminates:: true
- [ ] The middle-item pivot's time on sorted lists grows like n log n, not like n squared
      fails-if:: The middle-item pivot still quadruples its time when the sorted list doubles
- [ ] [outcome-neutral] Both pivot rules return a correctly ordered list at every size
      fails-if:: Either pivot rule returns a list that is not in order

## Planned Intervention

Quick sort with a first-item pivot and with a middle-item pivot, both on sorted lists from one thousand to one hundred thousand items. Twenty repeats per size. Counter clock, warm-up discarded.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h27/ and link at least the report:
     - [Report](results/h27/report.md)   - results/h27/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
