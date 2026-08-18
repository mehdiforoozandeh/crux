---
id: h35
type: idea
schema: 2
title: Merge sort gains nothing from an almost-sorted list
parent: q13
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median reported.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Random 0.67 ms, almost-sorted 0.66 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: efd09eb8d230eb44
lock: a775871e647fcce5
locked: "2026-08-16T16:06:49"
lock_at: running
---

# h35 — Merge sort gains nothing from an almost-sorted list

Parent:: [[q13_what_happens_when_the_list_is_almost_sor]]

## ELI5

Merge sort does not go faster on almost-sorted lists.

## TL;DR

Merge sort took the same time on almost-sorted and random lists. The algorithm does not detect or exploit existing runs of sorted data.

Background:: [[wiki/run-detection]]

## Null
selection - I chose an almost-sorted shape too close to random to tell apart

## Problem Statement

Merge sort divides the same way regardless of order, so partial sorting should not help. But I wanted to verify that it truly got no benefit.

## Idea / Hypothesis

Merge sort gains nothing from an almost-sorted list

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Merge time on random and almost-sorted differed by less than five percent. (found: Random 0.67 ms, almost-sorted 0.66 ms at n=10000)
      fails-if:: Almost-sorted was more than ten percent faster.
      discriminates:: true
- [x] Both shapes showed the same scaling, roughly proportional to n log n.
      fails-if:: One shape scaled much faster than the other.
- [x] [outcome-neutral] Both outputs were correctly sorted. (found: Both outputs correct, verified against a reference sort)
      fails-if:: Either output was not in ascending order.
- [x] [outcome-neutral] The almost-sorted list actually had one percent disruption. (found: Verified disruption rate before each run)
      fails-if:: The disruption was not applied or verified correctly.

## Planned Intervention

Merge sort on random and almost-sorted lists, where almost-sorted had one percent of items out of place. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h35/ and link at least the report:
     - [Report](results/h35/report.md)   - results/h35/curve.png -->
_(none yet)_

## Findings

Merge sort showed no advantage on almost-sorted lists. The algorithm treated both inputs identically, dividing and merging without detecting runs or exploiting partial order.
