---
id: h90
type: idea
schema: 2
title: My fitted curve predicts a new size to within twenty percent
parent: q29
status: done
rule: all
measurement: Predicted time from fitted line; measured actual median time at fifteen thousand items.
replicates: 30 repeats at fifteen thousand items to get the actual time.
verdict: refuted
metric: Predicted 3.1 ms for 15k items, actual was 4.8 ms. Error was 55 percent.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:39"
null_hash: 5744a1162036705b
lock: 9b84081546a8eeea
locked: "2026-08-16T16:07:00"
lock_at: running
---

# h90 — My fitted curve predicts a new size to within twenty percent

Parent:: [[q29_can_i_predict_the_time_for_a_size_i_have]]

## ELI5

I can predict the time for a new size I have not tested.

## TL;DR

I fitted a curve to sizes one thousand through ten thousand and then asked the curve to predict time at fifteen thousand items. I ran fifteen thousand items and measured the actual time. The prediction was off by more than twenty percent. The curve worked between the tested sizes but broke when I extrapolated beyond them.

Background:: [[wiki/extrapolation-risks]]

## Null
selection - I chose to extrapolate upward, which is harder than interpolating between known sizes.

## Problem Statement

If predicting past the end of the data fails, I cannot skip measuring big sizes. I would have to measure all the way up to one million items, which is slow and heats the laptop.

## Idea / Hypothesis

My fitted curve predicts a new size to within twenty percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Actual time at fifteen thousand is within twenty percent of predicted. (found: Predicted 3.1 ms for 15k items, actual was 4.8 ms. Error was)
      fails-if:: Actual time differs from predicted by more than twenty percent.
      discriminates:: true
- [ ] The prediction is not systematically high or low, just off.
      fails-if:: Predicted time is always higher or always lower than actual.
- [x] [outcome-neutral] The fifteen-thousand-item list is fully sorted and intact.
      fails-if:: Output is incorrect or incomplete.
- [x] [outcome-neutral] The machine stayed responsive and did not crash.
      fails-if:: The sort ran into memory issues or the system stopped.

## Planned Intervention

Fitted line to sizes 1k, 3k, 5k, 7k, 10k. Used that line to predict time at 15k. Ran fifteen thousand items thirty times. Compared predicted to actual.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h90/ and link at least the report:
     - [Report](results/h90/report.md)   - results/h90/curve.png -->
_(none yet)_

## Findings

The prediction was very wrong. I predicted 3.1 milliseconds but measured 4.8. The fitted line underestimated what would happen at a bigger size. My curve fit well between the tested sizes but extrapolating beyond them failed badly.
