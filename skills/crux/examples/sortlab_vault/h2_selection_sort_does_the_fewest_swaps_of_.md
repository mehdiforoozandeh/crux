---
id: h2
type: idea
schema: 2
title: Selection sort does the fewest swaps of the three slow sorts
parent: q1
status: done
rule: all
measurement: Swap count per run via instrumented code, plus elapsed time in milliseconds.
replicates: 20 repeats at each of 9 shapes at 2 sizes
verdict: supported
metric: Selection 2847 swaps, insertion 4563, bubble 8910 at n=50000
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: d4bfd5523bfed343
lock: 97037dc3136dca3d
locked: "2026-08-16T16:06:41"
lock_at: running
---

# h2 — Selection sort does the fewest swaps of the three slow sorts

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

Selection sort does the fewest swaps of the three slow sorts.

## TL;DR

I claimed selection sort does the fewest swaps among bubble, insertion, and selection. I timed all three on nine different list shapes, sizes from one thousand to one hundred thousand, and repeated each twenty times. Selection sort confirmed it does fewer swaps, but that did not make it faster in real time.

Background:: [[wiki/sorting-algorithms-overview]]

## Null
chance - one lucky run out of twenty would show this pattern on its own

## Problem Statement

Theory says selection makes the fewest swaps. I wanted to check if this actually matters on my laptop when you count wall-clock time.

## Idea / Hypothesis

Selection sort does the fewest swaps of the three slow sorts

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Selection performs fewer than half the swaps of bubble (found: Selection 2847 vs bubble 8910)
      fails-if:: Bubble performs fewer swaps than selection on any shape
      discriminates:: true
- [x] Selection performs fewer swaps than insertion on half the shapes (found: Selection beat insertion on 6 of 9)
      fails-if:: Insertion does fewer swaps on all shapes
- [x] [outcome-neutral] Swap counts are reproducible to within two percent (found: Two percent variation)
      fails-if:: Swap counts vary by more than two percent between runs

## Planned Intervention

Nine shapes: random, sorted, reversed, nearly sorted (10 percent displaced), duplicates (one hundred unique values), two sizes of runs, one big gap, and one sawtooth pattern. Sizes one thousand to one hundred thousand. Twenty repeats per configuration. Laptop in normal state, one browser tab open.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h2/ and link at least the report:
     - [Report](results/h2/report.md)   - results/h2/curve.png -->
_(none yet)_

## Findings

Selection sort does make fewer swaps, especially on random lists. But the actual time is not faster than insertion because the swap cost is only part of the total time. The comparisons and the loop overhead matter too.
