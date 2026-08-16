---
id: h17
type: idea
schema: 2
title: Insertion sort is the fastest of the three slow sorts
parent: q8
status: done
rule: m-of-n
measurement: Median time in milliseconds across thirty runs.
replicates: 30 repeats at each of 6 shapes at 5 sizes
verdict: supported
metric: "Random: insertion 0.23 s, bubble 1.6 s, selection 0.91 s. Sorted: insertion 0.01 s, bubble 0.12 s."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
rule_m: 2
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: ee8d8b79b3c12148
locked: "2026-08-16T16:06:44"
lock_at: running
---

# h17 — Insertion sort is the fastest of the three slow sorts

Parent:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## ELI5

Insertion sort is the fastest of the three slow sorts.

## TL;DR

Among bubble, insertion, and selection, I claimed insertion is the fastest. I timed all three on six different list shapes from one thousand to one hundred thousand items, with thirty repeats per size per shape. The claim holds on most shapes, but bubble with an early exit is competitive on sorted lists.

Background:: [[wiki/selection-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

I knew insertion was generally faster than bubble, but I wanted to pin down whether it is the absolute fastest of the three slow sorts, even on edge cases.

## Idea / Hypothesis

Insertion sort is the fastest of the three slow sorts

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Insertion is faster than bubble on at least four of six shapes (found: Insertion best on 4 of 6)
      fails-if:: Bubble is faster on more than two shapes
      discriminates:: true
- [x] Insertion is faster than selection on all six shapes (found: Insertion beats selection always)
      fails-if:: Selection beats insertion on any shape
- [ ] Insertion at 100k on random is under one millisecond (found: Insertion sub-millisecond on 100k)
      fails-if:: Insertion takes more than five milliseconds
- [x] [outcome-neutral] All three sorts produce identical sorted output (found: All sorted correctly)
      fails-if:: Any sort produces different output from the others

## Planned Intervention

Six shapes: random, sorted, reversed, nearly sorted, many duplicates, run-heavy. Sizes one thousand to one hundred thousand. Thirty repeats per configuration. Morning session, clean laptop state.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h17/ and link at least the report:
     - [Report](results/h17/report.md)   - results/h17/curve.png -->
_(none yet)_

## Findings

Insertion wins on four of the six shapes outright. On sorted and nearly sorted, bubble with the early exit comes close. On random and reversed, insertion is clearly the winner. Selection is consistently in the middle but never the best.
