---
id: h54
type: idea
schema: 2
title: Timing a list of one hundred items is below my timer's floor
parent: q18
status: done
rule: all
measurement: Time in milliseconds reported by the counter clock.
replicates: 30 repeats at each of 8 sizes
verdict: supported
metric: "n=100: 0.00 ms; n=1000: 0.012 ms; n=10000: 0.23 ms"
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 586734d92f436c43
lock: 63c0c7d81f3681f2
locked: "2026-08-16T16:06:52"
lock_at: running
---

# h54 — Timing a list of one hundred items is below my timer's floor

Parent:: [[q18_how_small_a_gap_can_my_timer_see]]

## ELI5

Sorting one hundred items runs so fast that my timer reads zero.

## TL;DR

Sorting a list of one hundred items took less than one millisecond, so the timer reported zero. I had to sort lists of at least one thousand items to get meaningful times.

Background:: [[wiki/timer-resolution]]

## Null
instrumentation - the timer resolution simply did not reach that small

## Problem Statement

Some of my early tests used small lists. The times came back as zero or near zero, making the data useless.

## Idea / Hypothesis

Timing a list of one hundred items is below my timer's floor

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] One hundred items reported as zero or sub-millisecond time. (found: n=100: 0.00 ms; n=1000: 0.012 ms; n=10000: 0.23 ms)
      fails-if:: Even one hundred items showed measurable time above one millisecond.
      discriminates:: true
- [x] One thousand items showed consistent times above zero.
      fails-if:: Times were still too close to zero to be reliable.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs correct despite the timing issues)
      fails-if:: Any output was not in order.

## Planned Intervention

Sort lists from one hundred to ten thousand items, timing each run. Thirty repeats at each size to find the threshold where time became measurable.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h54/ and link at least the report:
     - [Report](results/h54/report.md)   - results/h54/curve.png -->
_(none yet)_

## Findings

Sorting one hundred items was below the timer's resolution. Starting from one thousand items gave reliable times. This set a floor on the useful measurement range and explained why my early data had so much noise.
