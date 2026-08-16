---
id: h5
type: idea
schema: 2
title: Shuffling the same numbers twice gives the same ranking
parent: q2
status: idea
rule: all
measurement: Median time in milliseconds across twenty runs per shuffle.
replicates: 20 repeats per sort per shuffle per test set
verdict: 
metric: 
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:06:22"
---

# h5 — Shuffling the same numbers twice gives the same ranking

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

Shuffling the same numbers twice gives the same ranking.

## TL;DR

I want to test whether the ranking of sorts is stable across two different random shuffles of the same numbers. If the ranking changes with the shuffle, that means the randomness of the input matters more than I thought. I plan to use six different sets of one thousand numbers, shuffle each set twice in different ways, and time all five sorts on both shuffles.

Background:: [[wiki/adaptive-sorting]]

## Null
selection - I only tested the shuffle patterns where the result was already going to hold

## Problem Statement

One thing I noticed: different random runs sometimes gave different times. If shuffling changes the ranking significantly, that changes what I can say about which sort is best.

## Idea / Hypothesis

Shuffling the same numbers twice gives the same ranking

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The ranking of the five sorts is identical on both shuffles of all six sets
      fails-if:: Any set ranks the five sorts differently on its two shuffles
      discriminates:: true
- [ ] No sort's median time moves by more than five percent between the two shuffles
      fails-if:: A sort's median moves by more than five percent between the two shuffles
- [ ] [outcome-neutral] Both shuffles of a set hold exactly the same numbers as the original set
      fails-if:: A shuffle drops, repeats or changes a number from the original set

## Planned Intervention

Six test sets of unique integers one thousand to nine thousand nine hundred ninety-nine. Each set shuffled twice independently using Fisher-Yates. Five sorts on each shuffled version. Twenty repeats per sort per shuffle. Warm-up run discarded. Normal laptop state.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h5/ and link at least the report:
     - [Report](results/h5/report.md)   - results/h5/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
