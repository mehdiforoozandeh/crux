---
id: h95
type: idea
schema: 2
title: The shape changes the slope, not just the height
parent: q30
status: idea
rule: all
measurement: Slope of log-log line for each shape.
replicates: Not yet planned. Awaiting approval before proceeding.
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:06:29"
---

# h95 — The shape changes the slope, not just the height

Parent:: [[q30_can_i_predict_the_time_for_a_shape_i_hav]]

## ELI5

The shape changes how fast the time grows, not just the height.

## TL;DR

Different list shapes might have different slopes, not just different intercepts. A reversed list might grow as n squared while a nearly-sorted list grows as n log n. If slopes are different, it explains why the same curve does not work for all shapes.

Background:: [[wiki/adaptive-sorting]]

## Null
selection - reversed is the most extreme shape change; I did not test intermediates.

## Problem Statement

Understanding the shape effect on growth rate would help me predict for new shapes and new sizes at once. It would show me how much of the speed difference is fundamental to the shape.

## Idea / Hypothesis

The shape changes the slope, not just the height

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The random slope and the reversed slope differ by more than one tenth
      fails-if:: The two slopes agree within one tenth
      discriminates:: true
- [ ] Shifting one curve up or down cannot make it match the other
      fails-if:: A pure up-or-down shift makes the two curves match
- [ ] [outcome-neutral] Each shape's fit has r-squared above 0.99 before the slopes are compared
      fails-if:: A shape's fit has r-squared below 0.99

## Planned Intervention

Fit slopes separately to random and reversed lists. Compare the slopes.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h95/ and link at least the report:
     - [Report](results/h95/report.md)   - results/h95/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
