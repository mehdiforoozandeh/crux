---
id: h31
type: idea
schema: 2
title: A backwards list is the worst case for insertion sort
parent: q12
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Sorted 0.23 ms, reversed 3.12 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: c208abf3f7f032f6
lock: aaed1da8a4d90e44
locked: "2026-08-16T16:06:48"
lock_at: running
---

# h31 — A backwards list is the worst case for insertion sort

Parent:: [[q12_what_happens_on_a_list_that_is_sorted_ba]]

## ELI5

A backwards list is the slowest input for insertion sort.

## TL;DR

Insertion sort was slowest on a reversed list because it had to shift items all the way to the front with every insertion. This was the worst-case scenario for the algorithm.

Background:: [[wiki/reverse-sorted-input]]

## Null
selection - I chose the two shapes furthest apart, so a gap was guaranteed

## Problem Statement

Insertion sort should struggle most when items arrive in the worst order. A reversed list forces maximum insertions of each item.

## Idea / Hypothesis

A backwards list is the worst case for insertion sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Insertion was faster on sorted than on reversed by at least fifty percent. (found: Sorted 0.23 ms, reversed 3.12 ms at n=10000)
      fails-if:: Reversed input was not significantly slower.
      discriminates:: true
- [x] Time on reversed input scaled quadratically.
      fails-if:: Time did not quadruple when list size doubled.
- [x] [outcome-neutral] The reversed list was truly backwards. (found: Verified backwards order before and confirmed correctness after)
      fails-if:: The reversed input was not actually in descending order.

## Planned Intervention

Insertion sort on random, sorted, and reversed lists of ten thousand items. Thirty repeats from one thousand to one hundred thousand. Counter clock, first run out.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h31/ and link at least the report:
     - [Report](results/h31/report.md)   - results/h31/curve.png -->
_(none yet)_

## Findings

Insertion sort was dramatically slower on a reversed list. Each new item had to shift all the way to the front, multiplying the cost. Sorted input was more than ten times faster than reversed.
