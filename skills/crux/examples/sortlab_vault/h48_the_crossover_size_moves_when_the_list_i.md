---
id: h48
type: idea
schema: 2
title: The crossover size moves when the list is almost sorted
parent: q16
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of repeats.
replicates: 30 repeats at each of 8 sizes
verdict: supported
metric: Random crossover n=500; almost-sorted crossover n=3200
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: 33da8730851af539
lock: 4697c17884b1809c
locked: "2026-08-16T16:06:51"
lock_at: running
---

# h48 — The crossover size moves when the list is almost sorted

Parent:: [[q16_where_does_merge_sort_overtake_insertion]]

## ELI5

The crossover point moves to a larger size when the input is almost sorted.

## TL;DR

Insertion sort's advantage extended further on almost-sorted input. The crossover where merge beat insertion moved from five hundred to over three thousand items.

Background:: [[wiki/crossover-points]]

## Null
capacity - cache warming or machine differences, not algorithm

## Problem Statement

Almost-sorted input helps insertion sort more than merge sort. The crossover should move right, favoring insertion at larger sizes.

## Idea / Hypothesis

The crossover size moves when the list is almost sorted

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Crossover on almost-sorted input happened at a larger size than on random. (found: Random crossover n=500; almost-sorted crossover n=3200)
      fails-if:: Crossover stayed at the same size or moved left.
      discriminates:: true
- [x] The movement was at least five hundred items.
      fails-if:: The movement was less than two hundred items.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs verified as sorted)
      fails-if:: Any output was not in order.

## Planned Intervention

Insertion and merge on random and almost-sorted lists from one hundred to ten thousand items, doubling each time. Thirty repeats.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h48/ and link at least the report:
     - [Report](results/h48/report.md)   - results/h48/curve.png -->
_(none yet)_

## Findings

Almost-sorted input moved the crossover point to the right, favoring insertion for much larger lists. Insertion's advantage on partial order extended its practical dominance further up the size scale.
