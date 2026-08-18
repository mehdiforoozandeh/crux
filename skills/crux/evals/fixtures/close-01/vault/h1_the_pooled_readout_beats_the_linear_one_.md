---
id: h1
type: idea
schema: 2
title: the pooled readout beats the linear one by at least 0.02 mIoU
parent: q1
status: running
rule: all
measurement: mIoU on the held-out split, same evaluator for both arms
replicates: 5 seeds, one held-out split
verdict: 
metric: 
created: "2026-08-16T14:15:13"
updated: "2026-08-16T14:15:13"
null_approved: "2026-08-16T14:15:13"
null_hash: 3c291718842fc113
lock: 514eefb8ca76ff08
locked: "2026-08-16T14:15:13"
lock_at: running
---

# h1 — the pooled readout beats the linear one by at least 0.02 mIoU

Parent:: [[q1_does_the_pooled_readout_beat_the_linear_]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
chance — one lucky split would show the same gap at this sample size

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

the pooled readout beats the linear one by at least 0.02 mIoU

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] pooled beats linear by >= 0.02 mIoU on the held-out split
      fails-if:: the two readouts land within noise of each other on the held-out split
      discriminates:: true
- [ ] the gap holds on at least 4 of the 5 seeds
      fails-if:: the gap is carried by one seed and absent in the rest
- [ ] [outcome-neutral] both readouts score at chance on shuffled labels
      fails-if:: a shuffled-label arm scores above chance, so the split leaks into training

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- local run 2026-08-16

## Artifacts

<!-- what the run produced. Keep files under results/h1/ and link at least the report:
     - [Report](results/h1/report.md)   - results/h1/curve.png -->
- [Report](results/h1/report.md)
- results/h1/metrics.txt the claim-directed numbers
- results/h1/shuffled_labels.txt the control arm

## Findings

_(written by the PI/agent when the case is closed)_
