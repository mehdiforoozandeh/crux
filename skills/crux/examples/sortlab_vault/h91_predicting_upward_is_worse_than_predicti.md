---
id: h91
type: idea
schema: 2
title: Predicting upward is worse than predicting between known sizes
parent: q29
status: done
rule: all
measurement: Prediction error as a percentage for interpolated and extrapolated sizes.
replicates: 30 repeats at 4k items (interpolation test) and 20k items (extrapolation test).
verdict: inconclusive
metric: Interpolation error at 4k was 7 percent. Extrapolation error at 20k was 48 percent.
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:39"
null_hash: 2cd7ce300764e5de
lock: 5265c9d27caa0888
locked: "2026-08-16T16:07:00"
lock_at: running
---

# h91 — Predicting upward is worse than predicting between known sizes

Parent:: [[q29_can_i_predict_the_time_for_a_size_i_have]]

## ELI5

Guessing upward past the data is harder than guessing between known sizes.

## TL;DR

I used my fitted curve to predict sizes I had not tested by two methods: interpolation (guessing between sizes I had measured) and extrapolation (guessing past the end). Interpolation worked better. When I predicted the time at a size between my measurements, the error was small. When I predicted past the largest size, the error was much bigger.

Background:: [[wiki/doubling-experiments]]

## Null
selection - I tested a best case for interpolation and a worst case for extrapolation.

## Problem Statement

If interpolation is reliable but extrapolation is not, I can use this to plan my tests. I should measure a range of sizes and interpolate, not try to guess what happens at a million items from data at ten thousand.

## Idea / Hypothesis

Predicting upward is worse than predicting between known sizes

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Interpolation error at four thousand is less than ten percent. (found: Interpolation error at 4k was 7 percent. Extrapolation error at 20k was)
      fails-if:: Interpolated prediction misses by more than ten percent.
      discriminates:: true
- [-] Extrapolation error at twenty thousand is larger than interpolation error.
      fails-if:: Extrapolated prediction is as accurate as interpolated one.
- [x] [outcome-neutral] Both test sizes produce correct sorted output.
      fails-if:: Output is corrupted or unsorted at either test size.

## Planned Intervention

Fitted line to sizes 1k through 10k. Predicted time at 4k (between 3k and 5k measured) and at 20k (beyond 10k). Ran both sizes and checked errors.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h91/ and link at least the report:
     - [Report](results/h91/report.md)   - results/h91/curve.png -->
_(none yet)_

## Findings

Interpolating to 4k was close; the actual time was within seven percent of the prediction. Extrapolating to 20k was wrong by almost half. This shows I need to be careful about trusting predictions past the edge of measured data.
