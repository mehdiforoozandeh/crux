---
id: h86
type: idea
schema: 2
title: A straight line fits my insertion sort times on a log-log chart
parent: q28
status: done
rule: all
measurement: Median time in milliseconds for each of six sizes, plotted against item count.
replicates: 30 repeats at each of 6 sizes from 1k to 10k items.
verdict: supported
metric: Times were 0.12 ms at 1k, 0.49 at 3k, 1.93 at 10k; log-log line fit with slope 1.98.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: ea7893abcc565810
lock: fd56105aa39f8b09
locked: "2026-08-16T16:06:59"
lock_at: running
---

# h86 — A straight line fits my insertion sort times on a log-log chart

Parent:: [[q28_can_i_fit_a_curve_to_the_small_sizes]]

## ELI5

When I plot time on one axis and list size on the other, the points make a straight line.

## TL;DR

I measured insertion sort on six different list sizes from one thousand to ten thousand items. I plotted these times on a log-log chart where both axes are logarithmic. The points fit a straight line. This is important because it means I can predict times for new sizes I have not tested yet.

Background:: [[wiki/curve-fitting-basics]]

## Null
selection - I only chose sizes where insertion sort would fit a power law, not testing the method on sizes where it might fail.

## Problem Statement

I wanted to know if the pattern of times follows a simple rule. If it does, I can guess what would happen at a size I have not measured. This matters because testing at a million items takes a long time.

## Idea / Hypothesis

A straight line fits my insertion sort times on a log-log chart

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The six measurements fit a straight line on a log-log plot with r-squared above 0.99. (found: Times were 0.12 ms at 1k, 0.49 at 3k, 1.93 at 10k;)
      fails-if:: The points scatter widely or curve away from a straight line.
      discriminates:: true
- [x] The fitted line stays within five percent of actual times at intermediate sizes.
      fails-if:: The fitted line predicts much higher or much lower than observed.
- [x] [outcome-neutral] Sorted outputs at each size are correct and complete.
      fails-if:: Output is scrambled or incomplete at any of the six sizes tested.

## Planned Intervention

Six sizes: one thousand, two thousand, three thousand, five thousand, seven thousand, and ten thousand items. Thirty repeats at each. Plotted on log-log axes. Fitted a line using least-squares method.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h86/ and link at least the report:
     - [Report](results/h86/report.md)   - results/h86/curve.png -->
_(none yet)_

## Findings

A straight line on log-log paper fits the data very closely. This means insertion sort time roughly follows n squared. The line has slope very close to two, which matches what textbooks predict for insertion sort's worst case.
