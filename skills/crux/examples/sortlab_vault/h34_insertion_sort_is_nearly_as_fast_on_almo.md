---
id: h34
type: idea
schema: 2
title: Insertion sort is nearly as fast on almost-sorted as on sorted
parent: q13
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Fully sorted 0.23 ms, almost-sorted 0.26 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: f6fca9771aaf0197
lock: 1381cc40c3d5f4a5
locked: "2026-08-16T16:06:49"
lock_at: running
---

# h34 — Insertion sort is nearly as fast on almost-sorted as on sorted

Parent:: [[q13_what_happens_when_the_list_is_almost_sor]]

## ELI5

Insertion sort is fast when the list is almost sorted.

## TL;DR

Insertion sort was nearly as fast on almost-sorted lists as on fully sorted lists. The algorithm adapts to existing order by skipping shifts for items already in place.

Background:: [[wiki/nearly-sorted-input]]

## Null
selection - almost-sorted was defined so close to sorted that no gap could appear

## Problem Statement

Real-world data is often nearly sorted. I wanted to see how much insertion sort could adapt to partial order.

## Idea / Hypothesis

Insertion sort is nearly as fast on almost-sorted as on sorted

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Almost-sorted was faster than ten percent slower than fully sorted. (found: Fully sorted 0.23 ms, almost-sorted 0.26 ms at n=10000)
      fails-if:: Almost-sorted was twenty percent or slower.
      discriminates:: true
- [x] Both shapes showed linear or near-linear scaling with size.
      fails-if:: Time quadrupled when size doubled.
- [x] [outcome-neutral] Both outputs were correctly sorted. (found: Both outputs verified as sorted)
      fails-if:: Either output was not in order.

## Planned Intervention

Insertion sort on sorted and almost-sorted lists, where almost-sorted had one percent of items out of place. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h34/ and link at least the report:
     - [Report](results/h34/report.md)   - results/h34/curve.png -->
_(none yet)_

## Findings

Insertion sort was nearly as fast on almost-sorted lists as on fully sorted lists. The cost of inserting the few out-of-place items was small. Existing order gave insertion a big advantage.
