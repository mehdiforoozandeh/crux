---
id: h3
type: idea
schema: 2
title: the reranker improves relevance by at least 0.005 NDCG
parent: q1
status: idea
rule: all
measurement: NDCG@10 on a 40-query panel; the panel's own run-to-run spread is 0.02
replicates: 1 pass over 40 queries
verdict: 
metric: 
created: "2026-08-16T14:15:51"
updated: "2026-08-16T14:15:51"
null_approved: "2026-08-16T14:15:51"
null_hash: 448e9a9c7b39f823
---

# h3 — the reranker improves relevance by at least 0.005 NDCG

Parent:: [[q1_how_should_the_ranker_be_evaluated]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
chance — 40 queries cannot separate a 0.005 effect from noise

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

the reranker improves relevance by at least 0.005 NDCG

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] NDCG@10 rises by >= 0.005 on the 40-query panel
      fails-if:: the 40-query panel shows no rise
      discriminates:: true
- [ ] [outcome-neutral] the panel reproduces the production NDCG within 0.01
      fails-if:: the panel does not reproduce production, so it is not representative

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h3/ and link at least the report:
     - [Report](results/h3/report.md)   - results/h3/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
