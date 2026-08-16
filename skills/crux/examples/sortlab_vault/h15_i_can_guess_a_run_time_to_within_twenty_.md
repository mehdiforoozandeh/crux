---
id: h15
type: idea
schema: 2
title: I can guess a run time to within twenty percent
parent: q7
status: idea
rule: all
measurement: Percent difference between the predicted time and the measured time
replicates: 30 repeats at each of 6 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:06:23"
---

# h15 — I can guess a run time to within twenty percent

Parent:: [[q7_can_i_guess_the_time_before_i_run_the_te]]

## ELI5

I can guess a run time to within twenty percent.

## TL;DR

I want to test whether I can fit a line to my time measurements and use it to predict the time for a new size I have not tested yet. I will take measurements from several sizes, fit a line on a log-log plot, and then predict the time for a size in the middle of my tested range. If the prediction is off by less than twenty percent, I can call it a win.

Background:: [[wiki/curve-fitting-basics]]

## Null
selection - I only predict the sizes where the fitted line was already going to work

## Problem Statement

If I understand the scaling pattern, I should be able to guess the time without running the test. That would be useful for planning whether a test is worth my time.

## Idea / Hypothesis

I can guess a run time to within twenty percent

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The predicted time for an untested size inside the range is within twenty percent of the measured time
      fails-if:: The prediction misses the measured time by more than twenty percent
      discriminates:: true
- [ ] The prediction holds for three different untested sizes inside the range
      fails-if:: The prediction misses at any of the three untested sizes
- [ ] [outcome-neutral] The fitted line passes within five percent of the six sizes it was fitted on
      fails-if:: The fitted line misses one of its own six sizes by over five percent

## Planned Intervention

Measure insertion sort at six sizes from one thousand to thirty thousand items, thirty repeats each. Fit a straight line on a log-log chart. Predict a size inside that range, then run it.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h15/ and link at least the report:
     - [Report](results/h15/report.md)   - results/h15/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
