---
id: h88
type: idea
schema: 2
title: The slope for merge sort is close to one
parent: q28
status: done
rule: all
measurement: Median time in milliseconds for merge sort at six sizes from 1k to 10k.
replicates: 30 repeats at each of 6 sizes from 1k to 10k items.
verdict: refuted
metric: Merge sort slope was 1.12; times were 0.24 ms at 1k, 2.18 at 10k.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: 006954e7ea2094bb
lock: 232fd62df7d40d18
locked: "2026-08-16T16:07:00"
lock_at: running
---

# h88 — The slope for merge sort is close to one

Parent:: [[q28_can_i_fit_a_curve_to_the_small_sizes]]

## ELI5

Merge sort's times fit a line with slope one, not two.

## TL;DR

I fitted the same log-log line to merge sort times on the same six sizes. The slope came out 1.12, much closer to one than to two. Theory says merge sort takes n log n time. On a log-log plot, n log n curves slightly but looks almost like slope 1 plus a gentle curve upward.

Background:: [[wiki/curve-fitting-basics]]

## Null
selection - I only tested one algorithm on sizes where log-linear scaling would be hard to see on this laptop.

## Problem Statement

Merge sort should grow slower than insertion sort. The slope on a log-log plot should be closer to one than to two. Testing this checks if my merge sort implementation actually is merge sort and not something else.

## Idea / Hypothesis

The slope for merge sort is close to one

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The fitted slope for merge sort is less than 1.5. (found: Merge sort slope was 1.12; times were 0.24 ms at 1k, 2.18)
      fails-if:: Merge sort slope is 1.5 or higher, resembling insertion sort.
      discriminates:: true
- [ ] Merge sort is faster than insertion at ten thousand items.
      fails-if:: Insertion sort is faster or equal to merge sort at n=10k.
- [x] [outcome-neutral] Merge sort output is sorted correctly at all sizes.
      fails-if:: Output is not in order or is missing values.

## Planned Intervention

Same six sizes as before. Thirty repeats at each. Plotted merge sort times on log-log axes. Fitted the same least-squares line.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h88/ and link at least the report:
     - [Report](results/h88/report.md)   - results/h88/curve.png -->
_(none yet)_

## Findings

The slope was 1.12 and the times grew slowly compared to insertion sort. But the slope was not one; the curve showed gentle upward bending. This is what n log n should do on a log-log plot, though the effect is subtle at these sizes.
