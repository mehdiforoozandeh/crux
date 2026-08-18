---
id: h55
type: idea
schema: 2
title: Timing one thousand repeats gets me under the floor
parent: q18
status: done
rule: all
measurement: Total time for 1000 back-to-back sort runs, measured with perf_counter.
replicates: 30 repeats of the block at one size.
verdict: supported
metric: "Total time for 1000 repeats: bubble 0.15 ms, insertion 0.09 ms, selection 0.12 ms."
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 410030299ea4d593
lock: 7d724014913f4c72
locked: "2026-08-16T16:06:53"
lock_at: running
---

# h55 — Timing one thousand repeats gets me under the floor

Parent:: [[q18_how_small_a_gap_can_my_timer_see]]

## ELI5

A very large number of runs reveals time gaps too small for the timer to catch alone.

## TL;DR

When I run a sort a thousand times and measure the total, I can see timing differences smaller than what my timer can normally resolve. The run counts how many gaps the thousand repeats reveals, and whether the result is actually smaller than the timer's step size.

Background:: [[wiki/monotonic-clocks]]

## Null
instrumentation - the timer's step is bigger than the gap I am claiming to see

## Problem Statement

My stopwatch has a minimum step size. If the gap is smaller than that step, I will not see it. I need to know whether running the sort over and over can get me below that floor.

## Idea / Hypothesis

Timing one thousand repeats gets me under the floor

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Total time for 1000 repeats lands below 0.5 ms. (found: All 30 blocks finished between 0.08 ms and 0.19 ms)
      fails-if:: All thirty repeats exceed 0.5 ms or most cluster above it.
      discriminates:: true
- [x] Bubble sort takes notably longer than insertion sort at this scale. (found: Bubble: 0.15 ms median, insertion: 0.09 ms median over 30 runs)
      fails-if:: Bubble and insertion run in the same time to within noise.
- [x] [outcome-neutral] Each sort on a shuffled input is slower than on an already-sorted list. (found: All three sorts took 1.2 to 1.8 times longer on random data)
      fails-if:: A sort is faster on shuffled data than on sorted data.
- [x] [outcome-neutral] The same sort takes similar time across repeated runs. (found: Spread from min to max was less than 2x in all cases)
      fails-if:: Run times swing more than 3x between repeats.

## Planned Intervention

One thousand repeats of each of three sorts on lists of 10 items. I measured the total time with perf_counter. The run happened on battery power with no other apps. Thirty of these big-repeat blocks were timed.

## Run Links

- SortLab notebook, week 3

## Artifacts

- [Report](results/h55/report.md)

## Findings

I can see the sorts differ when I stack them. Bubble is clearly slower than insertion even over just 10 items. The timer is not getting in the way at this scale. But a thousand repeats takes less than a millisecond total, which means I have to be very careful about what I am actually timing.
