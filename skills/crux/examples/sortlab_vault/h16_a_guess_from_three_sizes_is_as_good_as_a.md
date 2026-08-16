---
id: h16
type: idea
schema: 2
title: A guess from three sizes is as good as a guess from six
parent: q7
status: running
rule: all
measurement: Percent prediction error at the held-out sizes for each fitted line
replicates: 30 repeats at each of 6 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:06:44"
null_approved: "2026-08-16T16:06:31"
null_hash: a1275e4a58108c40
lock: 12009a3c2bb7d6eb
locked: "2026-08-16T16:06:44"
lock_at: running
---

# h16 — A guess from three sizes is as good as a guess from six

Parent:: [[q7_can_i_guess_the_time_before_i_run_the_te]]

## ELI5

A guess from three sizes is as good as a guess from six.

## TL;DR

I want to test whether I need six measured data points to fit a reliable prediction line, or whether three is enough. I will measure insertion sort on six sizes from one thousand to thirty thousand items, fit lines using either three or six points, and compare how far off my predictions are for held-out sizes.

Background:: [[wiki/curve-fitting-basics]]

## Null
selection - the three sizes I kept happen to be the three that carry the line

## Problem Statement

Fitting a line takes time. If three points are enough, I can save time in future tests.

## Idea / Hypothesis

A guess from three sizes is as good as a guess from six

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The three-size line and the six-size line predict the held-out sizes within five percent of each other
      fails-if:: The two lines' predictions differ by more than five percent at a held-out size
      discriminates:: true
- [ ] Both lines report a slope within one tenth of each other
      fails-if:: The two slopes differ by more than one tenth
- [ ] [outcome-neutral] The six measured sizes lie on a straight log-log line with r-squared above 0.99
      fails-if:: The six measured sizes do not fall on a straight log-log line

## Planned Intervention

Measure insertion sort at six sizes from one thousand to thirty thousand items, thirty repeats each. Fit one line on three of the sizes and another on all six. Predict two held-out sizes with each.

## Run Links

- SortLab notebook, week 13

## Artifacts

<!-- what the run produced. Keep files under results/h16/ and link at least the report:
     - [Report](results/h16/report.md)   - results/h16/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
