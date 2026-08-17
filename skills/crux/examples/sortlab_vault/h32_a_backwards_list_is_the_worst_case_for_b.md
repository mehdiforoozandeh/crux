---
id: h32
type: idea
schema: 2
title: A backwards list is the worst case for bubble sort too
parent: q12
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: inconclusive
metric: Bubble-with-exit 1.89 ms, without exit 1.94 ms at n=10000
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:33"
null_hash: 2461d34c9da40861
lock: 139315162a26d72f
locked: "2026-08-16T16:06:48"
lock_at: running
---

# h32 — A backwards list is the worst case for bubble sort too

Parent:: [[q12_what_happens_on_a_list_that_is_sorted_ba]]

## ELI5

Bubble sort is also slow on a reversed list.

## TL;DR

Bubble sort was slow on a reversed list too, though perhaps not quite as bad as insertion. The early-exit could not help because the list had to be re-ordered to the opposite state.

Background:: [[wiki/reverse-sorted-input]]

## Null
selection - reversed input is the one shape that cannot reward an early exit

## Problem Statement

After seeing insertion struggle with reversed lists, I wanted to know if bubble would too. The early-exit would not trigger, so bubble would have to do all its passes.

## Idea / Hypothesis

A backwards list is the worst case for bubble sort too

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Bubble-with-exit on reversed input was slower than on sorted input. (found: Bubble-with-exit 1.89 ms, without exit 1.94 ms at n=10000)
      fails-if:: Reversed was faster or equal to sorted.
      discriminates:: true
- [-] Bubble and bubble-with-exit performed similarly on reversed input.
      fails-if:: The early-exit made a big difference on reversed input.
- [x] [outcome-neutral] The reversed input stayed reversed throughout testing. (found: All runs used the correct reversed list)
      fails-if:: Input got corrupted or changed between runs.

## Planned Intervention

Bubble with and without early-exit on reversed lists of ten thousand items. Thirty repeats from one thousand to one hundred thousand. Counter clock.

## Run Links

- SortLab notebook, week 5

## Artifacts

<!-- what the run produced. Keep files under results/h32/ and link at least the report:
     - [Report](results/h32/report.md)   - results/h32/curve.png -->
_(none yet)_

## Findings

Bubble sort was slow on reversed lists. The early-exit could not help because the list was as far from sorted as possible. Both versions took similar time, showing the cost was in the comparisons and swaps, not the exit check.
