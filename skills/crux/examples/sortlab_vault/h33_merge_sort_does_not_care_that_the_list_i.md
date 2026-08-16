---
id: h33
type: idea
schema: 2
title: Merge sort does not care that the list is backwards
parent: q12
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Sorted 0.64 ms, reversed 0.63 ms, random 0.67 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: 0a5e9613c294a7f5
lock: effac2651469a15d
locked: "2026-08-16T16:06:48"
lock_at: running
---

# h33 — Merge sort does not care that the list is backwards

Parent:: [[q12_what_happens_on_a_list_that_is_sorted_ba]]

## ELI5

Merge sort does not notice whether the list is sorted or backwards.

## TL;DR

Merge sort took the same time on sorted and reversed lists. The algorithm divides the list the same way regardless of order, so input shape did not matter.

Background:: [[wiki/reverse-sorted-input]]

## Null
selection - the three shapes I picked all happen to look alike to merge sort

## Problem Statement

Merge sort does not scan for order, it just divides and recombines. I wanted to verify that list shape was truly irrelevant for merge.

## Idea / Hypothesis

Merge sort does not care that the list is backwards

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Merge time on sorted and reversed lists differed by less than ten percent. (found: Sorted 0.64 ms, reversed 0.63 ms, random 0.67 ms at n=10000)
      fails-if:: One was more than twenty percent faster than the other.
      discriminates:: true
- [x] Merge was slower on random lists than on sorted or reversed.
      fails-if:: Random was faster or equal.
- [x] [outcome-neutral] All three outputs were sorted correctly. (found: All outputs correct, verified by checking sorted property)
      fails-if:: Any output list was not in order.

## Planned Intervention

Merge sort on sorted, reversed, and random lists of ten thousand items. Thirty repeats from one thousand to one hundred thousand. Counter clock.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h33/ and link at least the report:
     - [Report](results/h33/report.md)   - results/h33/curve.png -->
_(none yet)_

## Findings

Merge sort took nearly identical time on sorted, reversed, and random lists. The divide-and-merge structure does not adapt to existing order. Shape of input did not matter to the algorithm.
