---
id: h97
type: idea
schema: 2
title: The clock I started with jumps backwards sometimes
parent: q31
status: done
rule: all
measurement: Count of backward jumps in wall-clock time over one hundred consecutive readings.
replicates: One hundred sequential time readings with no gaps.
verdict: inconclusive
metric: Wall clock went backward 5 times in 100 reads. Counter clock went backward 0 times.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:39"
null_hash: fd32e4bac20cb159
lock: 7c575cb169095c86
locked: "2026-08-16T16:07:01"
lock_at: running
---

# h97 — The clock I started with jumps backwards sometimes

Parent:: [[q31_does_it_matter_which_clock_function_i_ca]]

## ELI5

The wall-clock time function went backward sometimes.

## TL;DR

I used the wall-clock time function to measure sorts. I discovered that sometimes it reported a time earlier than the last measurement, as if time had run backward. This is a problem because negative times are nonsense. I switched to the monotonic counter clock for all later measurements.

Background:: [[wiki/perf-counter]]

## Null
instrumentation - the clock stepping behavior made it impossible to measure time correctly.

## Problem Statement

If my stopwatch is broken, all my early numbers are useless. I need to know whether to trust the measurements from weeks one and two.

## Idea / Hypothesis

The clock I started with jumps backwards sometimes

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Wall-clock time goes backward at least once in one hundred readings. (found: Wall clock went backward 5 times in 100 reads. Counter clock went)
      fails-if:: All one hundred readings stay in strictly increasing order.
      discriminates:: true
- [-] The backward jump is larger than the timer's resolution, not noise.
      fails-if:: Jumps are tiny, within the measurement uncertainty.
- [x] [outcome-neutral] The counter clock shows only forward time over the same readings.
      fails-if:: Counter clock also goes backward.

## Planned Intervention

Checked the time before and after known-length operations. Searched for instances where new_time less than old_time. Found five such events in one hundred readings.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h97/ and link at least the report:
     - [Report](results/h97/report.md)   - results/h97/curve.png -->
_(none yet)_

## Findings

The wall-clock function skipped backward occasionally. It happened five times in a hundred reads. The counter clock never did this. This explains why I was seeing negative times and weird numbers in weeks one through two. I switched to counter clock for week three onward.
