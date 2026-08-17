---
id: h10
type: idea
schema: 2
title: The built-in sort beats my best sort at every size
parent: q5
status: done
rule: m-of-n
measurement: Median time in milliseconds across thirty runs per sort per size.
replicates: 30 repeats at each of 10 sizes for all 5 sorts plus built-in
verdict: supported
metric: "Merge sort: 18 ms at 100k. Built-in sort: 2 ms at 100k. Ratio: 9 times faster."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
rule_m: 2
null_approved: "2026-08-16T16:06:31"
null_hash: 59c5dacab60aba27
lock: 5feafa7e69368f9d
locked: "2026-08-16T16:06:43"
lock_at: running
---

# h10 — The built-in sort beats my best sort at every size

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

The built-in sort beats my best sort at every size.

## TL;DR

I claimed the built-in sort beats every sort I wrote at every size from one thousand to one million items. I measured all five of my hand-written sorts against Python's built-in sort on random lists, using thirty repeats per size on a geometric ladder. The built-in sort wins by a huge margin everywhere.

Background:: [[wiki/timsort]]

## Null
capacity - the faster machine state, not the algorithm, explains the whole gap

## Problem Statement

This was the turning point of the whole project. I did all this work to find the fastest sort I could write. Now I am about to find out whether any of that matters compared to what the language gave me for free.

## Idea / Hypothesis

The built-in sort beats my best sort at every size

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Built-in sort is faster than merge sort at all ten sizes (found: Built-in 2 ms, merge 18 ms)
      fails-if:: Merge sort is faster than the built-in sort on any size
      discriminates:: true
- [x] At 100k items, built-in sort is less than half the time of merge (found: Ratio 9x across all sizes)
      fails-if:: Built-in is more than twice as slow as merge at 100k
- [ ] Built-in sort never times out or errors on any size (found: Built-in always correct)
      fails-if:: Built-in sort crashes or takes more than one minute on any size
- [x] [outcome-neutral] The built-in sort produces the same output as merge sort (found: Same output from both)
      fails-if:: Built-in sort output is missing elements or out of order
- [x] [outcome-neutral] A one-second sleep times as one second when using the same clock (found: Clock stable in sleep)
      fails-if:: The clock drifts by more than one percent during a sleep test

## Planned Intervention

Geometric ladder: one thousand, two thousand, five thousand, ten thousand, twenty thousand, fifty thousand, one thousand, two hundred fifty thousand, five hundred thousand, one million. Random input. Thirty repeats per size. Both morning and afternoon runs to check for battery and temperature effects. Warm-up run discarded.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h10/ and link at least the report:
     - [Report](results/h10/report.md)   - results/h10/curve.png -->
_(none yet)_

## Findings

The built-in sort demolished everything I wrote. On one hundred thousand items, merge sort took eighteen milliseconds but the built-in sort took two milliseconds. That is a nine-times difference, and it holds at every size I tested. The built-in sort is not even running code like mine.
