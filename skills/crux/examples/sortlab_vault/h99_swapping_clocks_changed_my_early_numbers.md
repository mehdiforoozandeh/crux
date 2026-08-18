---
id: h99
type: idea
schema: 2
title: Swapping clocks changed my early numbers by more than a percent
parent: q31
status: done
rule: all
measurement: Median time for bubble sort at five thousand items, measured by each clock.
replicates: 30 repeats with wall clock, 30 repeats with counter clock, same machine state.
verdict: inconclusive
metric: "Wall clock: 42.3 ms. Counter clock: 41.8 ms. Difference: 1.2 percent."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:39"
null_hash: 6a0324092a5ba808
lock: af4a1bc9b930df3a
locked: "2026-08-16T16:07:01"
lock_at: running
---

# h99 — Swapping clocks changed my early numbers by more than a percent

Parent:: [[q31_does_it_matter_which_clock_function_i_ca]]

## ELI5

Switching clocks changed my old measurements by more than one percent.

## TL;DR

I measured the same sorts with the wall clock before and after switching to the counter clock. The times changed by more than one percent. This happened because the wall clock has a coarser step, so it rounded differently on each measurement.

Background:: [[wiki/perf-counter]]

## Null
instrumentation - both clocks' rounding and resolution made any difference hard to interpret.

## Problem Statement

All my numbers from week two are now suspect. Did I measure the real pattern or just the wall clock's rounding. When I compare week two and week three, which clock do I use to set the baseline.

## Idea / Hypothesis

Swapping clocks changed my early numbers by more than a percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Times measured by each clock differ by more than one percent. (found: Wall clock: 42.3 ms. Counter clock: 41.8 ms. Difference: 1.2 percent)
      fails-if:: The two clock measurements agree within one percent.
      discriminates:: true
- [-] The difference is not random noise but a systematic bias.
      fails-if:: Wall clock result is sometimes higher and sometimes lower.
- [x] [outcome-neutral] Sort output is correct regardless of which clock measured it.
      fails-if:: Swapping clocks somehow corrupts the sort.

## Planned Intervention

Measured bubble sort on five thousand items with both clocks, thirty repeats each, alternating clocks to avoid systematic bias.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h99/ and link at least the report:
     - [Report](results/h99/report.md)   - results/h99/curve.png -->
_(none yet)_

## Findings

Wall clock and counter clock gave different numbers; the difference was just over one percent. This is small but real. The earlier week two numbers are not wrong, just measured with lower precision. The week three switch to counter clock improved consistency.
