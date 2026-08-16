---
id: h2
type: idea
schema: 2
title: the pooled readout beats the linear one
parent: q3
status: idea
rule: 
measurement: 
replicates: 
verdict: 
metric: 
created: "2026-08-16T14:14:11"
updated: "2026-08-16T14:14:11"
---

# h2 — the pooled readout beats the linear one

Parent:: [[q3_which_readout_is_the_right_one]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
chance — one lucky split would show the same gap at this sample size

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

the pooled readout beats the linear one

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] pooled beats linear on the held-out split by at least 0.02
      fails-if:: pooled and linear land within noise of each other on the held-out split
      discriminates:: true
- [ ] [outcome-neutral] both readouts score at chance on shuffled labels
      fails-if:: a shuffled-label arm scores above chance, so the split leaks

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h2/ and link at least the report:
     - [Report](results/h2/report.md)   - results/h2/curve.png -->
- [Report](results/h2/report.md)

## Findings

_(written by the PI/agent when the case is closed)_
