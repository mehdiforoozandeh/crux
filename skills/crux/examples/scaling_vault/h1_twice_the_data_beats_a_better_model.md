---
id: h1
type: idea
title: Twice the data beats a better model
parent: q1
status: done
verdict: supported
metric: +3.3 points
created: "2026-07-31T14:45:03"
updated: "2026-07-31T14:45:03"
---

# h1 — Twice the data beats a better model

Parent:: [[q1_does_more_data_beat_a_better_model]]

## Problem Statement

Generalisation error falls as a power law in both training-set size and parameter count ([[wiki/scaling-laws]]), so which lever pays more is an empirical question about where a programme currently sits, not a general fact ([[wiki/data-vs-model-scaling]]). We double the training set for the smaller model ([[wiki/resnet]]) and compare against the higher-capacity model ([[wiki/vision-transformer]]) on the original data, holding everything downstream fixed.

## Idea / Hypothesis

Twice the data beats a better model

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] accuracy improves by >= 2.0 points
- [x] the gain also holds on a second task
- [x] the gain holds in all 3 repeat runs

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- job 4012

## Artifacts

<!-- what the run produced. Keep files under results/h1/ and link at least the report:
     - [Report](results/h1/report.md)   - results/h1/curve.png -->
_(none yet)_

## Findings

Doubling the training set beat the higher-capacity model by 3.3 points (49.6 vs 46.3), held on the second task (+1.5), and no repeat run regressed. All three pre-registered bars were met.
