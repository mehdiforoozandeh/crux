---
id: h98
type: idea
schema: 2
title: The counter clock has a finer step than the wall clock
parent: q31
status: done
rule: all
measurement: "Measured step size of each clock: smallest non-zero time interval it can report."
replicates: 30 repeats of one-hundred-millisecond sleep measured by both clocks.
verdict: supported
metric: Counter clock step was 0.001 ms. Wall clock step was 0.050 ms. Counter was 50 times finer.
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:39"
null_hash: c96d871b127bf102
lock: c2d436b423d63ddc
locked: "2026-08-16T16:07:01"
lock_at: running
---

# h98 — The counter clock has a finer step than the wall clock

Parent:: [[q31_does_it_matter_which_clock_function_i_ca]]

## ELI5

The counter clock measures time more finely than the wall clock.

## TL;DR

I switched to the counter clock in week three. I want to confirm it is actually better: finer step size, meaning it can measure shorter time spans accurately. I timed a known-length sleep and compared the two clocks.

Background:: [[wiki/monotonic-clocks]]

## Null
instrumentation - both clocks might be limited by the operating system's actual time-keeping resolution.

## Problem Statement

Just because the counter clock does not go backward does not mean it is better. I need to verify it actually has better resolution.

## Idea / Hypothesis

The counter clock has a finer step than the wall clock

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Counter clock step size is smaller than wall clock step size. (found: Counter clock step was 0.001 ms. Wall clock step was 0.050 ms)
      fails-if:: Counter clock has the same step size or a larger one.
      discriminates:: true
- [x] Both clocks measure the one-hundred-millisecond sleep within five percent.
      fails-if:: Either clock reports a time off by more than five percent.
- [x] [outcome-neutral] Sleep duration is consistent across repeats.
      fails-if:: Sleep times vary wildly between repeats.

## Planned Intervention

Sleep for exactly one hundred milliseconds. Measure with both clocks. Repeat thirty times. Check that counter clock step size is smaller than wall clock step size.

## Run Links

- SortLab notebook, week 3

## Artifacts

- [Report](results/h98/report.md)

## Findings

The counter clock has a step size about fifty times smaller than the wall clock. This means it can measure gaps that the wall clock would round to zero. Both clocks measured the one-hundred-millisecond sleep accurately, within one percent.
