---
id: h92
type: idea
schema: 2
title: A prediction from the median is better than one from the mean
parent: q29
status: running
rule: all
measurement: Prediction error at 15k items using median-fitted curve versus mean-fitted curve.
replicates: Existing thirty repeats at each of 1k, 3k, 5k, 7k, 10k used for fitting.
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:00"
null_approved: "2026-08-16T16:06:39"
null_hash: c177854d38d11c55
lock: 8aa307e8d85931df
locked: "2026-08-16T16:07:00"
lock_at: running
---

# h92 — A prediction from the median is better than one from the mean

Parent:: [[q29_can_i_predict_the_time_for_a_size_i_have]]

## ELI5

Using the middle value predicts better than using the average.

## TL;DR

When I fit a curve, should I use the mean or the median of my thirty repeats at each size. If I fit to medians and predict, will the prediction be better than if I fit to means. This test is still running and not yet closed.

Background:: [[wiki/extrapolation-risks]]

## Null
selection - I might have unconsciously chosen sizes where median wins, not testing cases where mean would be better.

## Problem Statement

Outliers can pull the mean away from the typical value. The median ignores outliers. If I fit to medians, my curve should track the typical case better. For a 15k item prediction, that might matter.

## Idea / Hypothesis

A prediction from the median is better than one from the mean

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The median-fitted line predicts 15k items with a smaller error than the mean-fitted line
      fails-if:: The mean-fitted line predicts 15k items at least as well
      discriminates:: true
- [ ] The median-fitted line wins at three other held-out sizes too
      fails-if:: The mean-fitted line wins at any of the three other held-out sizes
- [ ] [outcome-neutral] Both lines are fitted to the same thirty repeats at the same five sizes
      fails-if:: The two lines are fitted to different repeats or different sizes

## Planned Intervention

Take the thirty repeats at each size. Calculate both mean and median. Fit two separate lines, one to means and one to medians. Use each to predict 15k items. Compare prediction errors.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h92/ and link at least the report:
     - [Report](results/h92/report.md)   - results/h92/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
