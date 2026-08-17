---
id: h84
type: idea
schema: 2
title: The speed-up is bigger for my sorts than for the built-in one
parent: q27
status: done
rule: all
measurement: Time in milliseconds for first and final runs of each sort on a ten-thousand-item list.
replicates: 300 consecutive runs of each sort in one browser session.
verdict: inconclusive
metric: Insertion sped up 4.1 times; built-in sped up 1.8 times; ratio difference was 2.3.
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: 1a460d1e99b03438
lock: 04e8fd06570c0579
locked: "2026-08-16T16:06:59"
lock_at: running
---

# h84 — The speed-up is bigger for my sorts than for the built-in one

Parent:: [[q27_does_the_javascript_engine_speed_up_whil]]

## ELI5

The JavaScript engine helps my sorts more than it helps the built-in one.

## TL;DR

I compared how much faster each sort got as the engine warmed up. My insertion sort sped up about four times; the built-in sort only sped up about two times. This suggests the JavaScript engine optimizes hand-written code differently than code already built into the language.

Background:: [[wiki/jit-compilation]]

## Null
instrumentation - noise in individual run times could make ratios look bigger than they really are.

## Problem Statement

The warm-up effect was real, but was it the same for all code. If the built-in sort was already optimized, maybe the engine could not speed it up as much as my code.

## Idea / Hypothesis

The speed-up is bigger for my sorts than for the built-in one

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] My insertion sort gets at least twice as fast from start to end. (found: Insertion sped up 4.1 times; built-in sped up 1.8 times; ratio difference)
      fails-if:: Insertion sort does not improve by two times or improves less.
      discriminates:: true
- [-] The built-in sort does not speed up as much as insertion sort does.
      fails-if:: Built-in speed improvement equals or exceeds hand-written sort improvement.
- [x] [outcome-neutral] The output stays sorted and complete across all runs.
      fails-if:: Output becomes scrambled or loses items as the engine warms up.

## Planned Intervention

Measured the ratio of run-one time to run-three-hundred time for each sort. Did this at one size to keep it simple. Three hundred repeats in one session.

## Run Links

- SortLab notebook, week 12

## Artifacts

- [Report](results/h84/report.md)

## Findings

Insertion sort improved a lot as the engine warmed up, but the built-in sort barely improved. The engine probably compiles hand-written loops more aggressively than built-in optimized code that is already fast from the start.
