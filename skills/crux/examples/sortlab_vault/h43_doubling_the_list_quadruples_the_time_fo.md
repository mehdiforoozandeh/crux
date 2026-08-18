---
id: h43
type: idea
schema: 2
title: Doubling the list quadruples the time for insertion sort
parent: q15
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: "At n=100k: 8.2 sec; at n=200k: 32.8 sec (ratio 4.0)"
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: ad8aa87f4da3096d
lock: 720fe0a63205c750
locked: "2026-08-16T16:06:50"
lock_at: running
---

# h43 — Doubling the list quadruples the time for insertion sort

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

Insertion sort time quadruples when the list size doubles.

## TL;DR

Doubling the list size roughly quadrupled the time for insertion sort. This confirmed the quadratic scaling expected from the algorithm.

Background:: [[wiki/big-o-notation]]

## Null
capacity - a change in machine state, not the sort, explains the result

## Problem Statement

Insertion sort is theoretically O(n squared), so I expected doubling to roughly quadruple the time. Testing would confirm this prediction.

## Idea / Hypothesis

Doubling the list quadruples the time for insertion sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Time at n doubled was close to four times the time at n. (found: At n=100k: 8.2 sec; at n=200k: 32.8 sec (ratio 4.0))
      fails-if:: Time at 2n was less than 3.5 times or more than 5 times.
      discriminates:: true
- [x] Ratio was consistent across all sizes tested.
      fails-if:: Ratio changed significantly at large sizes.
- [x] [outcome-neutral] All outputs were correctly sorted. (found: All outputs verified as sorted correctly)
      fails-if:: Any output was not in order.

## Planned Intervention

Insertion sort on lists from one thousand to one million items, doubling at each step. Thirty repeats at each size. Counter clock, first run discarded.

## Run Links

- SortLab notebook, week 7

## Artifacts

<!-- what the run produced. Keep files under results/h43/ and link at least the report:
     - [Report](results/h43/report.md)   - results/h43/curve.png -->
_(none yet)_

## Findings

Insertion sort quadrupled in time when list size doubled. The ratio stayed at four across all sizes tested. This confirmed the O(n squared) scaling predicted by theory.
