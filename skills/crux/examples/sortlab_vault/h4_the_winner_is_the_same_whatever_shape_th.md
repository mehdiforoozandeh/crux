---
id: h4
type: idea
schema: 2
title: The winner is the same whatever shape the list has
parent: q2
status: done
rule: all
measurement: Median elapsed time in milliseconds across thirty runs.
replicates: 30 repeats at each of 5 shapes at 5 sizes
verdict: refuted
metric: "Random: insertion 0.23 s; sorted: insertion 0.01 s; reversed: insertion 0.24 s"
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: 19217f852bd3886a
lock: 61a9b7a984dea1d0
locked: "2026-08-16T16:06:42"
lock_at: running
---

# h4 — The winner is the same whatever shape the list has

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

The winner is the same no matter what shape the list has.

## TL;DR

I claimed the fastest sort never changes, no matter whether the list is random, sorted, reversed, or anything in between. I tested all five sorts on five different list shapes and sizes from ten thousand to one million items, using thirty repeats per shape. The results show clearly that the winner does depend on the shape.

Background:: [[wiki/input-generators]]

## Null
selection - I only tested the list shapes where this sort was always going to win

## Problem Statement

My first theory was that one sort would win across all conditions. This seemed simple. But after sorting different shaped lists, I started noticing that insertion was faster on pre-sorted data.

## Idea / Hypothesis

The winner is the same whatever shape the list has

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The fastest sort changes between at least two of the five shapes (found: Insertion first on sorted, third on random)
      fails-if:: The same sort ranks first on all five shapes
      discriminates:: true
- [ ] Insertion is fastest on the sorted list (found: Insertion 0.01 s sorted vs 0.23 random)
      fails-if:: Bubble or selection are faster than insertion on the sorted list
- [x] [outcome-neutral] The output lists are identical for both input shapes (found: Same values in all outputs)
      fails-if:: One shape produces a different output order than another

## Planned Intervention

Five shapes: random shuffled, already sorted ascending, sorted descending (reversed), nearly sorted with one percent of items displaced, and one hundred unique values repeated many times. Sizes: ten thousand, fifty thousand, one hundred thousand, five hundred thousand, one million. Thirty repeats per size per shape. Normal machine state.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h4/ and link at least the report:
     - [Report](results/h4/report.md)   - results/h4/curve.png -->
_(none yet)_

## Findings

The winner definitely changes with the input shape. Insertion sort crushes everything on pre-sorted lists. On random lists, merge sort starts to pull ahead at larger sizes. This makes sense because pre-sorted lists trigger the early-exit or best-case behavior in insertion.
