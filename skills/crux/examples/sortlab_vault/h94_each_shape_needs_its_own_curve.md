---
id: h94
type: idea
schema: 2
title: Each shape needs its own curve
parent: q30
status: idea
rule: all
measurement: Whether each shape-specific curve is more accurate than a combined curve.
replicates: Not yet planned. Awaiting approval before proceeding.
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:06:29"
---

# h94 — Each shape needs its own curve

Parent:: [[q30_can_i_predict_the_time_for_a_shape_i_hav]]

## ELI5

Each shape needs a separate curve, not one curve for all.

## TL;DR

I want to test whether the same fitted line works for all list shapes or if each shape needs its own line. If each shape needs its own curve, I will need to measure several times as much data to cover all shapes at all sizes.

Background:: [[wiki/input-generators]]

## Null
selection - I only tested two shapes; shapes I did not try might behave differently.

## Problem Statement

Knowing this changes what is possible to test. If one curve works, I can test a hundred shapes quickly. If each needs its own curve, I can only test a few.

## Idea / Hypothesis

Each shape needs its own curve

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] A shape's own curve predicts that shape at an untested size better than the combined curve
      fails-if:: The combined curve predicts each shape as well as the shape's own curve
      discriminates:: true
- [ ] The random curve and the reversed curve disagree by more than twenty percent at the untested size
      fails-if:: The two shape curves agree within twenty percent at the untested size
- [ ] [outcome-neutral] Both shapes are timed at the same sizes with the same repeat count
      fails-if:: The two shapes are timed at different sizes or different repeat counts

## Planned Intervention

Fit curves to random and reversed lists separately. At a size neither was tested on, do both curves predict accurately.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h94/ and link at least the report:
     - [Report](results/h94/report.md)   - results/h94/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
