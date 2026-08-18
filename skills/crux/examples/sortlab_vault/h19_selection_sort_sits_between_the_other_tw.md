---
id: h19
type: idea
schema: 2
title: Selection sort sits between the other two on random lists
parent: q8
status: done
rule: all
measurement: Median time in milliseconds.
replicates: 30 repeats at each of 5 sizes
verdict: refuted
metric: "At 50k: insertion 0.12 s, selection 0.45 s, bubble 0.81 s"
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: 1f9e1358543391f2
locked: "2026-08-16T16:06:45"
lock_at: running
---

# h19 — Selection sort sits between the other two on random lists

Parent:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## ELI5

Selection sort sits between the other two on random lists.

## TL;DR

I claimed selection sort is faster than bubble but slower than insertion on random lists. I ran all three on random lists from one thousand to one hundred thousand items with thirty repeats per size. Selection does sit in the middle, but the margins vary with size.

Background:: [[wiki/insertion-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

Selection has fewer swaps than bubble but the same big-O as bubble. I wondered whether the reduction in swaps actually buys it a faster time, and whether that advantage holds across all sizes.

## Idea / Hypothesis

Selection sort sits between the other two on random lists

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Selection is slower than insertion at all five sizes (found: Insertion < selection < bubble at all 5)
      fails-if:: Insertion is slower than selection at any size
      discriminates:: true
- [ ] Selection is faster than bubble at all five sizes (found: All correct orderings)
      fails-if:: Bubble is faster than selection at any size
- [x] [outcome-neutral] Selection on 100k completes in under two seconds (found: 100k under 2 seconds)
      fails-if:: Selection on 100k takes more than five seconds

## Planned Intervention

Random lists only, five sizes: one thousand, ten thousand, twenty thousand, fifty thousand, one hundred thousand. Thirty repeats per size. High-resolution timer. Normal laptop state.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h19/ and link at least the report:
     - [Report](results/h19/report.md)   - results/h19/curve.png -->
_(none yet)_

## Findings

Selection sits firmly between bubble and insertion on random lists across all sizes. The gap between insertion and selection is about three times to four times, and the gap between selection and bubble is about two times. These ratios hold fairly steady as size grows.
