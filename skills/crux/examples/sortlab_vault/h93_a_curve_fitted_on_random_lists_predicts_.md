---
id: h93
type: idea
schema: 2
title: A curve fitted on random lists predicts almost-sorted lists
parent: q30
status: idea
rule: all
measurement: Prediction error when applying random-list curve to nearly-sorted list.
replicates: Not yet planned. Awaiting approval before proceeding.
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:06:29"
---

# h93 — A curve fitted on random lists predicts almost-sorted lists

Parent:: [[q30_can_i_predict_the_time_for_a_shape_i_hav]]

## ELI5

A curve fitted to random lists works for nearly-sorted lists too.

## TL;DR

I fit my curve using random-order lists. Now I want to know if that same curve predicts time for a nearly-sorted list at a size I have not tested. Lists that are almost in order might sort faster, but maybe the same curve still works. This test is in the idea stage; it has not been planned yet.

Background:: [[wiki/adaptive-sorting]]

## Null
selection - nearly-sorted lists are the easiest shape to sort; I chose a case unlikely to break the curve.

## Problem Statement

Different list shapes sort at different speeds. If I have to fit a separate curve for each shape, testing all shapes at all sizes would take forever. A single curve that works for all shapes would be powerful.

## Idea / Hypothesis

A curve fitted on random lists predicts almost-sorted lists

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The random-list curve predicts an 8k almost-sorted list within twenty percent
      fails-if:: The random-list curve misses the almost-sorted time by over twenty percent
      discriminates:: true
- [ ] The same curve holds for almost-sorted lists at two further untested sizes
      fails-if:: The curve misses at either of the two further untested sizes
- [ ] [outcome-neutral] The almost-sorted lists really carry the share of out-of-place items I asked for
      fails-if:: The generator produced a shape other than the one it promised

## Planned Intervention

Fit a curve to random lists at six sizes. Then test a nearly-sorted list at a new size like 8k and see if the curve predicts its time.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h93/ and link at least the report:
     - [Report](results/h93/report.md)   - results/h93/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
