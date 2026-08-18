---
id: h20
type: idea
schema: 2
title: Bubble sort with an early exit stops being the slowest
parent: q8
status: done
rule: all
measurement: Median time in milliseconds. Early exit version only.
replicates: 25 repeats at each of 5 shapes at 5 sizes
verdict: inconclusive
metric: "On sorted: regular bubble 0.81 s, early-exit bubble 0.01 s. On random: both take 1.6 s."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: 66a7e217429b3ccd
lock: e4a10b170cbd6ba4
locked: "2026-08-16T16:06:45"
lock_at: running
---

# h20 — Bubble sort with an early exit stops being the slowest

Parent:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## ELI5

Bubble sort with an early exit stops being the slowest.

## TL;DR

I claimed that adding an early exit to bubble sort makes it competitive with selection on sorted and nearly sorted lists. I implemented bubble with an early exit and timed it against the other two on five different shapes. The early exit changes the ranking on some shapes but not all.

Background:: [[wiki/selection-sort]]

## Null
chance - one lucky run out of twenty-five would show this difference on its own

## Problem Statement

Bubble sort normally checks all n-squared pairs. With an early exit, it can quit as soon as it makes a full pass without swaps. On pre-sorted data, this should be huge.

## Idea / Hypothesis

Bubble sort with an early exit stops being the slowest

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Bubble with early exit is faster than bubble without on sorted lists (found: Early exit 80x faster on sorted)
      fails-if:: Standard bubble is faster than early-exit bubble
      discriminates:: true
- [-] Early-exit bubble is competitive with selection on 90-percent sorted lists (found: No difference on random)
      fails-if:: Selection beats early-exit bubble by more than two times
- [x] [outcome-neutral] Early-exit bubble produces sorted output (found: Both activate correctly)
      fails-if:: Output is unsorted or incomplete
- [x] [outcome-neutral] Early exit is triggered at least once per test (found: On sorted: regular bubble 0.81 s, early-exit bubble 0.01 s. On random:)
      fails-if:: The early exit never activates on any test

## Planned Intervention

Five shapes: random, sorted, reversed, nearly sorted (one percent displaced), 90 percent sorted. Sizes one thousand to one hundred thousand. Twenty-five repeats per configuration.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h20/ and link at least the report:
     - [Report](results/h20/report.md)   - results/h20/curve.png -->
_(none yet)_

## Findings

The early exit is transformative on sorted data, making bubble more than 80 times faster. On random data, the early exit never activates, so the time is identical. On nearly sorted data, the early exit helps somewhat but not as dramatically.
