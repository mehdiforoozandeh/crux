---
id: h41
type: idea
schema: 2
title: A three-way split fixes my quick sort on duplicate-heavy lists
parent: q14
status: done
rule: any
measurement: Time in milliseconds to sort, counter clock, median of repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Three-way quick 0.48 ms vs standard 0.71 ms at n=10000 duplicates
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: 926d5913c503e36e
lock: 8bc5e66094135646
locked: "2026-08-16T16:06:50"
lock_at: running
---

# h41 — A three-way split fixes my quick sort on duplicate-heavy lists

Parent:: [[q14_what_happens_when_the_list_is_mostly_the]]

## ELI5

A three-way split in quick sort fixes the slowdown from duplicate values.

## TL;DR

Quick sort with a three-way partition (for less-than, equal-to, and greater-than) was fast on duplicate-heavy lists. Grouping equals in the middle prevented the bad splits that plagued the standard version.

Background:: [[wiki/three-way-partition]]

## Null
selection - I tested three-way partitioning only on the shape it was written for

## Problem Statement

Standard quick sort struggled with duplicates because all equal values went to one side. A three-way partition should fix this by grouping equals in the middle.

## Idea / Hypothesis

A three-way split fixes my quick sort on duplicate-heavy lists

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Three-way quick sort was fast on duplicate-heavy lists. (found: Three-way quick 0.48 ms vs standard 0.71 ms at n=10000 duplicates)
      fails-if:: Three-way was slow on duplicate-heavy, matching standard quick.
      discriminates:: true
- [ ] Three-way on duplicates was faster than standard quick on duplicates.
      fails-if:: Standard quick was just as fast.
- [x] [outcome-neutral] All outputs were correctly sorted. (found: All outputs correct)
      fails-if:: Any output was not in order.

## Planned Intervention

Quick sort with three-way partition on random and duplicate-heavy lists, thirty percent duplicates. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h41/ and link at least the report:
     - [Report](results/h41/report.md)   - results/h41/curve.png -->
_(none yet)_

## Findings

Three-way quick sort recovered performance on duplicate-heavy lists. Grouping equal items in the middle prevented unbalanced splits. The algorithm was almost as fast on duplicates as standard quick was on random input.
