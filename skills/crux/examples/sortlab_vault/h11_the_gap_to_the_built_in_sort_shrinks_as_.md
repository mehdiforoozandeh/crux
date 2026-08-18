---
id: h11
type: idea
schema: 2
title: The gap to the built-in sort shrinks as the list grows
parent: q5
status: done
rule: m-of-n
measurement: Ratio of merge sort time to built-in sort time at each size.
replicates: 30 repeats at each of 10 sizes
verdict: refuted
metric: "At 1k: built-in 0.2 ms, merge 0.8 ms, ratio 4x. At 1m: built-in 2.5 ms, merge 22 ms, ratio 8.8x."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
rule_m: 2
null_approved: "2026-08-16T16:06:31"
null_hash: 59c5dacab60aba27
lock: 42834fe4cdcdcfef
locked: "2026-08-16T16:06:43"
lock_at: running
---

# h11 — The gap to the built-in sort shrinks as the list grows

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

The gap to the built-in sort shrinks as the list grows.

## TL;DR

I claimed the gap between merge sort and the built-in sort gets smaller as the list gets bigger. If this were true, the built-in sort would eventually become only twice as fast instead of nine times as fast. I tested all sizes from one thousand to one million and looked at the ratio.

Background:: [[wiki/python-sorting-overview]]

## Null
capacity - the faster machine state, not the algorithm, explains the whole gap

## Problem Statement

The built-in sort was so much faster that I wondered whether the gap came from overhead that does not scale. Maybe at huge sizes, my merge sort would catch up.

## Idea / Hypothesis

The gap to the built-in sort shrinks as the list grows

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The ratio is smaller at one million than at one thousand (found: Ratio grew from 4 to 8.8x)
      fails-if:: The ratio stays the same or grows from one thousand to one million
      discriminates:: true
- [ ] The gap shrinks by at least twenty percent from 10k to 1m (found: Gap did not shrink)
      fails-if:: The gap shrinks by less than ten percent
- [ ] The ratio at one million is at least 2 times (found: All times under one second)
      fails-if:: The gap closes to less than 1.5 times
- [x] [outcome-neutral] All runs complete in less than one second (found: At 1k: built-in 0.2 ms, merge 0.8 ms, ratio 4x. At 1m:)
      fails-if:: Any run times out or takes more than ten seconds

## Planned Intervention

Geometric ladder: one thousand to one million. Thirty repeats per size. Random input. High-resolution timer. Same morning session to avoid battery and thermal effects.

## Run Links

- SortLab notebook, week 9

## Artifacts

- [Report](results/h11/report.md)

## Findings

The gap actually grew, not shrank. At one thousand items the ratio was four times, and at one million it was eight point eight times. This means the overhead is not the issue. The built-in sort just has a fundamentally better algorithm. The ratio settles at roughly eight to ten times across the range.
