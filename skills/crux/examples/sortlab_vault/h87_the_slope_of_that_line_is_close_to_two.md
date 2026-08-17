---
id: h87
type: idea
schema: 2
title: The slope of that line is close to two
parent: q28
status: done
rule: all
measurement: Slope of the log-log fitted line calculated by least-squares regression.
replicates: Same six sizes used in the previous fitting test.
verdict: inconclusive
metric: Fitted slope was 1.98 with 95 percent confidence interval 1.84 to 2.12.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: dd832dfbc12f0703
lock: 539b3d0b8eafdc5a
locked: "2026-08-16T16:07:00"
lock_at: running
---

# h87 — The slope of that line is close to two

Parent:: [[q28_can_i_fit_a_curve_to_the_small_sizes]]

## ELI5

The slope of the line is two, matching what algorithms textbooks say.

## TL;DR

I fitted a line to the log-log plot and calculated its slope. The slope came out close to two. According to algorithm theory, insertion sort takes time proportional to n squared in the worst case, which would show as slope two on a log-log plot. My measured slope was 1.98.

Background:: [[wiki/growth-rate-curves]]

## Null
selection - I chose the one size range where insertion sort fits a power law, not proving it works everywhere.

## Problem Statement

If my implementation is correct, the slope should match the theory. A different slope would mean either my code is not insertion sort, or the theory breaks down in practice.

## Idea / Hypothesis

The slope of that line is close to two

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The slope is between 1.80 and 2.20, close to the theoretical value of two. (found: Fitted slope was 1.98 with 95 percent confidence interval 1.84 to 2.12)
      fails-if:: The slope is outside this range, suggesting different growth rate.
      discriminates:: true
- [-] The slope does not change much if I drop the largest or smallest data point.
      fails-if:: Removing one size makes the slope jump by more than 0.3.
- [x] [outcome-neutral] The linear fit has no obvious outliers when plotted.
      fails-if:: One or more points deviate from the line by more than ten percent.

## Planned Intervention

Used the least-squares fitted line from the previous test. Calculated slope as rise over run on the log-log plot. Took the six measurement points and their fitted line.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h87/ and link at least the report:
     - [Report](results/h87/report.md)   - results/h87/curve.png -->
_(none yet)_

## Findings

The slope came out 1.98, almost exactly two. This matched the textbook prediction. However confidence range was fairly wide, from 1.84 to 2.12. Within that range I cannot say if slope is truly two or just close.
