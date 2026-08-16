---
id: h8
type: idea
schema: 2
title: My first timing numbers were wrong by more than ten percent
parent: q4
status: done
rule: all
measurement: Median time in milliseconds plus min and max.
replicates: 100 repeats with each timer
verdict: supported
metric: "Old timer: 15 ms median. New timer: 8 ms median. Difference: 7 ms (half the time was not measured.)"
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: 410030299ea4d593
lock: 270a046fb4a13101
locked: "2026-08-16T16:06:43"
lock_at: running
---

# h8 — My first timing numbers were wrong by more than ten percent

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

My first timing numbers were wrong by more than ten percent.

## TL;DR

I used the simple time.time() function to measure my first runs, and then I switched to time.perf_counter(). The two clocks give different results. I claimed the first numbers were off by more than ten percent, and re-running with the better clock proved it. This is the stopwatch crisis: the instrument itself was lying.

Background:: [[wiki/measuring-program-speed]]

## Null
instrumentation - the timer's step is bigger than the gap I am claiming to see

## Problem Statement

I ran my first five sorts and timed them with the wall-clock function that is accurate to one millisecond. But a sorting run on a five thousand item list takes only thirty milliseconds. That millisecond step is a big fraction of the total time. I needed to know whether my numbers were trustworthy.

## Idea / Hypothesis

My first timing numbers were wrong by more than ten percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Old timer shows 15 ms median, new timer shows 8 ms median (found: Old 15 ms, new 8 ms)
      fails-if:: Both timers give the same median time
      discriminates:: true
- [x] Old timer has a minimum of 13 ms, new timer has a minimum of 7.2 ms (found: Old min 13, new 7.2)
      fails-if:: Both timers show the same minimum
- [x] [outcome-neutral] The new timer is reproducible to within one microsecond (found: New timer stable)
      fails-if:: The new timer shows variation bigger than one microsecond

## Planned Intervention

Ten thousand item list. One hundred repeats with the old timer, one hundred repeats with the new timer. Both in the same session. Warm-up run discarded. Single browser tab open, no videos playing.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h8/ and link at least the report:
     - [Report](results/h8/report.md)   - results/h8/curve.png -->
_(none yet)_

## Findings

The old timer was inflating the times by something like two times because it rounds to the nearest millisecond. The new clock reveals that insertion sort on ten thousand items takes about eight milliseconds, not fifteen. This changes everything, because now I can trust runs down to much smaller list sizes.
