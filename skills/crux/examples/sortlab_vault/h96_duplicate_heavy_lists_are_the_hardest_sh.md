---
id: h96
type: idea
schema: 2
title: Duplicate-heavy lists are the hardest shape to predict
parent: q30
status: staged
rule: all
measurement: Error when random-list curve predicts time for duplicate-heavy list.
replicates: Not yet planned. Staged and ready to go.
verdict: 
metric: 
created: "2026-08-16T16:06:29"
updated: "2026-08-16T16:07:01"
null_approved: "2026-08-16T16:06:39"
null_hash: bfcfa62c16aeaac1
---

# h96 — Duplicate-heavy lists are the hardest shape to predict

Parent:: [[q30_can_i_predict_the_time_for_a_shape_i_hav]]

## ELI5

Duplicate-heavy lists are the hardest to predict.

## TL;DR

I have tested random, sorted, and reversed. A list with many duplicates might behave differently because some sorts can exploit the duplicates for speedup. My fitted curves from unique-value tests might predict these times poorly. This test is staged and ready to run when I choose.

Background:: [[wiki/input-generators]]

## Null
selection - I chose an extreme case of high duplication; medium levels might be more predictable.

## Problem Statement

If I cannot predict duplicate-heavy lists, those become a special case I need to handle separately in my final analysis.

## Idea / Hypothesis

Duplicate-heavy lists are the hardest shape to predict

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The random-list curve misses duplicate-heavy times by more than it misses any other shape
      fails-if:: Some other shape is predicted worse than the duplicate-heavy one
      discriminates:: true
- [ ] The miss on duplicate-heavy lists is over twenty percent at all three sizes
      fails-if:: The miss stays under twenty percent at any of the three sizes
- [ ] [outcome-neutral] The generated lists really hold seventy percent duplicate or near-duplicate values
      fails-if:: The generator produced a share of duplicates other than seventy percent

## Planned Intervention

Create lists where seventy percent of values are the same or within five numbers of each other. Test at three sizes with thirty repeats each. See if random-list curve predicts well.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h96/ and link at least the report:
     - [Report](results/h96/report.md)   - results/h96/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
