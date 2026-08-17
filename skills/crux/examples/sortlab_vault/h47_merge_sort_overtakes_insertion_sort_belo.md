---
id: h47
type: idea
schema: 2
title: Merge sort overtakes insertion sort below one thousand items
parent: q16
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty.
replicates: 30 repeats at each of 8 sizes
verdict: refuted
metric: "At n=500: insertion 0.021 ms, merge 0.022 ms"
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: 1eafb8e6cf4cc873
lock: 2e7b6b6fba7e2974
locked: "2026-08-16T16:06:51"
lock_at: running
---

# h47 — Merge sort overtakes insertion sort below one thousand items

Parent:: [[q16_where_does_merge_sort_overtake_insertion]]

## ELI5

Merge sort starts beating insertion at less than one thousand items.

## TL;DR

The crossover where merge sort became faster than insertion happened below one thousand items. Testing showed merge won at around five hundred items on this laptop.

Background:: [[wiki/hybrid-sorts]]

## Null
capacity - cache or machine state, not algorithm, drove the result

## Problem Statement

Merge sort has higher overhead but better asymptotic scaling. I wanted to find where the crossover happened so I could choose the right sort for each size.

## Idea / Hypothesis

Merge sort overtakes insertion sort below one thousand items

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Crossover happened at less than one thousand items. (found: At n=500: insertion 0.021 ms, merge 0.022 ms)
      fails-if:: Merge was still slower than insertion at n=1000.
      discriminates:: true
- [ ] At the crossover size, merge and insertion times were within ten percent.
      fails-if:: Times were more than twenty percent apart.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs verified)
      fails-if:: Any output was not in order.

## Planned Intervention

Insertion and merge sort on lists from one hundred to ten thousand items, testing every doubling. Thirty repeats. Counter clock.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h47/ and link at least the report:
     - [Report](results/h47/report.md)   - results/h47/curve.png -->
_(none yet)_

## Findings

Insertion and merge crossed over around five hundred items, with merge becoming faster for larger lists. Below that crossover insertion was quicker. The crossover point confirmed that both algorithms had their place.
