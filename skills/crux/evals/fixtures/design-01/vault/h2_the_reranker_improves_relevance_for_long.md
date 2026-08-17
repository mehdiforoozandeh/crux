---
id: h2
type: idea
schema: 2
title: the reranker improves relevance for long-tail queries
parent: q1
status: idea
rule: all
measurement: NDCG@10 on the long-tail slice
replicates: 1 sweep
verdict: 
metric: 
created: "2026-08-16T14:15:50"
updated: "2026-08-16T14:15:51"
null_approved: "2026-08-16T14:15:51"
null_hash: d5c6930da5299702
---

# h2 — the reranker improves relevance for long-tail queries

Parent:: [[q1_how_should_the_ranker_be_evaluated]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
selection — the long-tail slice was chosen after the results were seen

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

the reranker improves relevance for long-tail queries

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] NDCG@10 on the long-tail slice rises by >= 0.02
      fails-if:: long-tail NDCG@10 does not move
      discriminates:: true
- [ ] mean training loss falls below 0.31
      fails-if:: training loss stays above 0.31
- [ ] [outcome-neutral] the head slice is unchanged by the reranker swap
      fails-if:: the head slice moves, so the swap changed more than the reranker

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h2/ and link at least the report:
     - [Report](results/h2/report.md)   - results/h2/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
