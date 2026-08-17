---
id: h66
type: idea
schema: 2
title: Thirty repeats bring the spread under five percent
parent: q22
status: done
rule: m-of-n
measurement: Time for one sort pass on 10000 items, with perf_counter.
replicates: 30 repeats of each sort.
verdict: inconclusive
metric: "Bubble IQR: 4.7 percent of median. Insertion: 4.2 percent."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
rule_m: 2
null_approved: "2026-08-16T16:06:36"
null_hash: e070ed1be61dd388
lock: 51e81d15e4cc999d
locked: "2026-08-16T16:06:56"
lock_at: running
---

# h66 — Thirty repeats bring the spread under five percent

Parent:: [[q22_how_many_repeats_do_i_need_before_the_nu]]

## ELI5

Thirty repeats of a sort bring the spread of times down to under five percent.

## TL;DR

More repeats reduce the scatter. The claim is that thirty repeats will give a tight enough spread that the median is reliable. The run checks whether the interquartile range of thirty runs is under five percent of the median.

Background:: [[wiki/repeated-trials]]

## Null
instrumentation - the spread stays the same fraction no matter how many repeats; more runs do not help

## Problem Statement

I need to know how many repeats I actually need to get a number I can trust. Is 30 enough, or should I do more?

## Idea / Hypothesis

Thirty repeats bring the spread under five percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Interquartile range is less than five percent of the median. (found: Bubble: IQR 0.41 ms, median 8.8 ms, ratio 4.7 percent. Just under)
      fails-if:: IQR is five percent or more of the median.
      discriminates:: true
- [-] At least two-thirds of the runs fall within 10 percent of the median. (found: Bubble: 21 of 30 runs within 10 percent. Insertion: 24 of 30)
      fails-if:: Fewer than two-thirds of runs land in that band.
- [ ] Thirty repeats bring the spread under five percent for all five sorts, not just two (found: Only bubble and insertion measured)
      fails-if:: A sort still shows a spread of five percent or more at thirty repeats
- [x] [outcome-neutral] All 30 runs complete with valid output. (found: All 30 runs of both sorts completed normally)
      fails-if:: Some runs crash or fail.

## Planned Intervention

Insertion and bubble sort on 10000 items, each run 30 times. I calculated the interquartile range (middle 50 percent of values) as a percent of the median. The laptop was plugged in with defaults.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h66/ and link at least the report:
     - [Report](results/h66/report.md)   - results/h66/curve.png -->
_(none yet)_

## Findings

Thirty repeats are almost enough. The spread for both sorts is just barely under five percent. Most runs cluster nicely around the median. Thirty might be the minimum, but I feel safer with more.
