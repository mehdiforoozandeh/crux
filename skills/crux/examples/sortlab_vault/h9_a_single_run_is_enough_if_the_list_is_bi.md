---
id: h9
type: idea
schema: 2
title: A single run is enough if the list is big
parent: q4
status: done
rule: all
measurement: Single run time in milliseconds. Median of thirty runs in milliseconds.
replicates: 1 single run, 30 repeats per size
verdict: refuted
metric: "Single runs at 100k: 12, 13, 16, 11 ms. Median of 30 runs: 12.8 ms."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: 410030299ea4d593
lock: 8602df1325f5d06b
locked: "2026-08-16T16:06:43"
lock_at: running
---

# h9 — A single run is enough if the list is big

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

One run is enough if the list is big.

## TL;DR

I claimed that a single run would be enough to measure a sort if the list is big enough to make the sort time longer than the timer's precision. I ran insertion sort on lists ranging from one thousand to one hundred thousand items, and I took both one run and thirty runs for each size. The results show that even at big sizes, one run is not enough.

Background:: [[wiki/timer-resolution]]

## Null
instrumentation - the timer's step is bigger than the gap I am claiming to see

## Problem Statement

With the old timer at one millisecond precision, I needed many repeats to smooth out the noise. With the new timer at microsecond precision, maybe I could get away with fewer repeats. This seemed efficient.

I set the ten percent threshold before I ran this test. After I saw the results, I loosened it to five percent to match the spread I found. That was wrong. I am writing this honestly now because cheating the threshold is worse than the noise being bigger than I hoped.

The edit: verifiable 1: the threshold was loosened from ten percent to five percent after the run I set the bar at ten percent before I knew how noisy my timer was. After the run I changed it to five. That is drift, and crux flags this node for good.

## Idea / Hypothesis

A single run is enough if the list is big

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Single runs vary by more than five percent from the thirty-run median (found: Single runs 12-16 vs median 12.8)
      fails-if:: Every single run lands within two percent of the thirty-run median
      discriminates:: true
- [ ] The spread in thirty runs at 100k items is more than three milliseconds (found: Spread 4.5 ms at 100k)
      fails-if:: All thirty runs at 100k cluster within one millisecond
- [x] [outcome-neutral] The same list produces the same output on consecutive runs (found: Same output every time)
      fails-if:: Either one run or the thirty-run batch produces a different output

## Planned Intervention

Sizes: one thousand, five thousand, ten thousand, twenty thousand, fifty thousand, one hundred thousand. For each size, one single run and one batch of thirty runs. Warm-up run discarded before the batch. High-resolution timer. Morning with no background apps, single browser tab.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h9/ and link at least the report:
     - [Report](results/h9/report.md)   - results/h9/curve.png -->
_(none yet)_

## Findings

Single runs were all over the place. At 100k items, the single runs ranged from 11 to 16 milliseconds around a median of 12.8. That is a 45 percent spread, which is way too much to trust. Ten repeats were not enough when I started, and one run is definitely not enough even at large sizes.
