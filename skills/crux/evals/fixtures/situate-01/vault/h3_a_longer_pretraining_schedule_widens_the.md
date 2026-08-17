---
id: h3
type: idea
schema: 2
title: a longer pretraining schedule widens the gap
parent: q2
status: running
rule: all
measurement: mIoU at 100 labels
replicates: 3 seeds
verdict: 
metric: 
created: "2026-08-16T14:15:14"
updated: "2026-08-16T14:15:14"
null_approved: "2026-08-16T14:15:14"
null_hash: 40c107fbed0c3f8d
lock: 69c1af0b8120e2df
locked: "2026-08-16T14:15:14"
lock_at: running
---

# h3 — a longer pretraining schedule widens the gap

Parent:: [[q2_does_pretraining_help_at_low_label_count]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
chance — three seeds cannot separate schedules this close together

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

a longer pretraining schedule widens the gap

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] the 2x schedule beats the 1x schedule by >= 1 mIoU at 100 labels
      fails-if:: the two schedules land within 1 mIoU of each other
      discriminates:: true
- [ ] [outcome-neutral] the 1x schedule reproduces h1's number
      fails-if:: the rerun does not reproduce h1, so the harness drifted

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- cluster job 8812

## Artifacts

<!-- what the run produced. Keep files under results/h3/ and link at least the report:
     - [Report](results/h3/report.md)   - results/h3/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
