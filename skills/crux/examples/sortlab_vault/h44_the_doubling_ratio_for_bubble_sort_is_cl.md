---
id: h44
type: idea
schema: 2
title: The doubling ratio for bubble sort is close to four
parent: q15
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 6 sizes
verdict: inconclusive
metric: "Ratios: 3.87, 4.12, 3.94, 4.08, 3.82 across five doublings"
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: 9c8556e61e284f73
lock: a18bd44e4243ad96
locked: "2026-08-16T16:06:51"
lock_at: running
---

# h44 — The doubling ratio for bubble sort is close to four

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

When you double the list, bubble sort time roughly quadruples.

## TL;DR

Bubble sort on random lists scaled quadratically, with the doubling ratio staying close to four. But there was enough noise in the measurements to call it inconclusive.

Background:: [[wiki/doubling-experiments]]

## Null
capacity - measurement noise or machine state explains the scatter

## Problem Statement

Bubble sort should also scale quadratically. I wanted to measure its actual ratio to see if it matched insertion sort's four.

## Idea / Hypothesis

The doubling ratio for bubble sort is close to four

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Doubling ratio was between three point five and four point five. (found: Ratios: 3.87, 4.12, 3.94, 4.08, 3.82 across five doublings)
      fails-if:: Ratio was outside this range, suggesting inconsistent scaling.
      discriminates:: true
- [-] Ratio did not trend upward or downward across sizes.
      fails-if:: Ratio changed systematically at larger sizes.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs verified as sorted)
      fails-if:: Any output was not in order.

## Planned Intervention

Bubble sort on lists from one thousand to one million items, doubling each time. Thirty repeats at each size. Counter clock, first run out.

## Run Links

- SortLab notebook, week 7

## Artifacts

- [Report](results/h44/report.md)

## Findings

Bubble sort's doubling ratio hovered around four, but with enough variability in the measurements to make the trend unclear. At large sizes the ratio seemed to drift slightly, suggesting either growing noise or real changes in scaling.
