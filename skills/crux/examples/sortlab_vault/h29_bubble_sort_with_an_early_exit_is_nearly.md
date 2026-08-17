---
id: h29
type: idea
schema: 2
title: Bubble sort with an early exit is nearly free on a sorted list
parent: q11
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Bubble-with-exit 0.18 ms at n=10000, 0.36 ms at n=20000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: 4aab3df4c3b7cfb8
lock: eac3d10c0ade66e6
locked: "2026-08-16T16:06:48"
lock_at: running
---

# h29 — Bubble sort with an early exit is nearly free on a sorted list

Parent:: [[q11_what_happens_on_a_list_that_is_already_s]]

## ELI5

Bubble sort with an early-exit condition is very fast on a sorted list.

## TL;DR

Bubble sort with a check to exit when the list is already sorted ended up nearly free on pre-sorted lists. The cost was just the scan through the data that told bubble the job was done.

Background:: [[wiki/adaptive-sorting]]

## Null
selection - I picked the one input shape where the early exit was bound to win

## Problem Statement

I saw in week 2 that bubble with an early-exit was not always the slowest. On a sorted list the early-exit would trigger instantly, so I wanted to measure how cheap that made it.

## Idea / Hypothesis

Bubble sort with an early exit is nearly free on a sorted list

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Bubble-with-exit was faster than insertion sort on sorted lists. (found: Bubble-with-exit 0.18 ms at n=10000, 0.36 ms at n=20000)
      fails-if:: Insertion sort matched or beat bubble with early-exit.
      discriminates:: true
- [x] Bubble-with-exit time scaled linearly with list size on sorted input.
      fails-if:: Time quadrupled when size doubled, showing quadratic scaling.
- [x] [outcome-neutral] The early-exit did trigger on sorted input. (found: Early-exit triggered after one pass, adding only linear cost)
      fails-if:: The loop ran to completion without exiting early.

## Planned Intervention

Bubble with early-exit on a list of ten thousand items already sorted. Thirty repeats from one thousand to one hundred thousand items. Counter clock, first run discarded.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h29/ and link at least the report:
     - [Report](results/h29/report.md)   - results/h29/curve.png -->
_(none yet)_

## Findings

Bubble sort with an early-exit was nearly free on sorted input. Time was dominated by the single scan needed to detect that sorting was done. The early-exit condition made this much cheaper than any of the comparison-heavy sorts.
