---
id: h1
type: idea
schema: 2
title: the linear readout recovers the planted effect
parent: q2
status: done
rule: all
measurement: recovered effect size, linear probe on frozen features
replicates: 5 seeds x 3 folds
verdict: supported
metric: recovered 0.094 of a planted 0.100
created: "2026-08-16T14:14:11"
updated: "2026-08-16T14:14:11"
null_approved: "2026-08-16T14:14:11"
null_hash: 49a5c9df1bddb437
lock: 1ed5b4377389c79e
locked: "2026-08-16T14:14:11"
lock_at: running
---

# h1 — the linear readout recovers the planted effect

Parent:: [[q2_how_should_the_probe_be_normalised]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
capacity — the wider arm would clear the same bar without the readout

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

the linear readout recovers the planted effect

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] recovered effect is within 10 percent of the planted size (found: recovered 0.094 vs planted 0.100)
      fails-if:: the readout is fitted but the recovered size misses the planted one
      discriminates:: true
- [x] [outcome-neutral] the permuted-label arm recovers nothing (found: AUC 0.502 on shuffled labels)
      fails-if:: the harness scores signal on shuffled labels, so the pipeline leaks

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- local run 2026-08-16

## Artifacts

<!-- what the run produced. Keep files under results/h1/ and link at least the report:
     - [Report](results/h1/report.md)   - results/h1/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
