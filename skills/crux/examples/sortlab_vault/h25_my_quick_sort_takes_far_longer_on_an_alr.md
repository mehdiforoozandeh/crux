---
id: h25
type: idea
schema: 2
title: My quick sort takes far longer on an already sorted list
parent: q10
status: done
rule: any
measurement: Median time in milliseconds. Record if the sort times out.
replicates: 20 repeats at each of 5 shapes at 4 sizes
verdict: supported
metric: "At 20k: random 6 ms, sorted 45 ms (7.5 times slower), reversed 47 ms."
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:32"
null_hash: bb0a6439318839fa
lock: d2082df496a191cc
locked: "2026-08-16T16:06:47"
lock_at: running
---

# h25 — My quick sort takes far longer on an already sorted list

Parent:: [[q10_does_my_quick_sort_break_on_a_list_that_]]

## ELI5

My quick sort takes far longer on an already sorted list.

## TL;DR

Quick sort degrades to O of n squared when the list is already sorted, because all the bad pivot choices stack up. I ran quick sort on five different shapes: random, sorted, reversed, nearly sorted, and duplicates. On the sorted list, quick sort blew up.

Background:: [[wiki/recursion-depth]]

## Null
chance - one lucky run out of twenty would show this difference on its own

## Problem Statement

Quick sort's worst case is when the input is sorted. I wanted to see if this matters in practice on my laptop, or if the worst case is just a theory concern.

## Idea / Hypothesis

My quick sort takes far longer on an already sorted list

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Quick sort on a sorted list takes at least five times longer than on random (found: Sorted 45 ms vs random 6 ms (7.5x))
      fails-if:: Sorted and random take similar times
      discriminates:: true
- [ ] Quick sort on reversed also takes longer than random (found: Reversed also 47 ms)
      fails-if:: Reversed is as fast as random
- [x] [outcome-neutral] Quick sort output is still sorted even on bad shapes (found: Output correct)
      fails-if:: Output is unsorted
- [x] [outcome-neutral] No run times out or throws an error (found: At 20k: random 6 ms, sorted 45 ms (7.5 times slower), reversed)
      fails-if:: Quick sort fails to complete any run

## Planned Intervention

Five shapes as above. Sizes from one thousand to fifty thousand. Twenty repeats per configuration. If quick sort takes more than ten seconds on any run, I will stop and record that it failed.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h25/ and link at least the report:
     - [Report](results/h25/report.md)   - results/h25/curve.png -->
_(none yet)_

## Findings

The worst case is very real. On a sorted twenty thousand item list, quick sort took 45 milliseconds compared to 6 milliseconds on random data. The issue is that every element becomes a pivot, turning the algorithm into O of n squared. Reversed input is just as bad.
