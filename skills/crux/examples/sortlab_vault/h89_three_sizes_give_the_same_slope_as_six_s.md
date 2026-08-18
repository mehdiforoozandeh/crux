---
id: h89
type: idea
schema: 2
title: Three sizes give the same slope as six sizes
parent: q28
status: staged
rule: all
measurement: Slope of log-log line fitted to three carefully-chosen sizes.
replicates: "30 repeats at each of 3 sizes: 1k, 3k, and 10k items."
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:00"
null_approved: "2026-08-16T16:06:38"
null_hash: ad4af3b58b5efe99
---

# h89 — Three sizes give the same slope as six sizes

Parent:: [[q28_can_i_fit_a_curve_to_the_small_sizes]]

## ELI5

Using three sizes to fit a line gives the same slope as using six sizes.

## TL;DR

I want to test whether I need six measurements to get a stable slope estimate. If I can get the same answer using just three sizes, I can save time. I will fit the line to sizes 1k, 3k, and 10k only and see if the slope matches the slope from all six sizes.

Background:: [[wiki/growth-rate-curves]]

## Null
selection - I only tested the largest three sizes, which might miss what happens at intermediate points.

## Problem Statement

Measuring takes time and the laptop gets hot. If three sizes are enough, I can test more list shapes and algorithms instead of measuring fewer shapes thoroughly.

## Idea / Hypothesis

Three sizes give the same slope as six sizes

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The slope from 1k, 3k and 10k is within one twentieth of the six-size slope
      fails-if:: The three-size slope differs from the six-size slope by more than one twentieth
      discriminates:: true
- [ ] The three-size fit has r-squared above 0.99, like the six-size fit
      fails-if:: The three-size fit has r-squared below 0.99
- [ ] [outcome-neutral] All thirty repeats at each of the three sizes return correctly ordered lists
      fails-if:: A repeat at one of the three sizes returns an unordered list

## Planned Intervention

Use the three sizes 1k, 3k, and 10k with thirty repeats each. Fit a line. Compare slope to slope from six sizes.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h89/ and link at least the report:
     - [Report](results/h89/report.md)   - results/h89/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
