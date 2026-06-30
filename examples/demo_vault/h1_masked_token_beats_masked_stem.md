---
id: h1
type: idea
title: masked-token beats masked-stem
parent: q2
status: done
verdict: supported
metric: imp +0.012
created: "2026-06-29T17:36:39"
updated: "2026-06-29T17:36:39"
---

# h1 — masked-token beats masked-stem

Parent:: [[q2_how_to_design_the_jepa_encoder]]

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

masked-token beats masked-stem

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] imp-Spearman ≥ +0.01 vs stem baseline
- [x] no NaN over 5 eval epochs

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- job 40012

## Findings

mask_token clearly wins; stem path underperforms across folds.
