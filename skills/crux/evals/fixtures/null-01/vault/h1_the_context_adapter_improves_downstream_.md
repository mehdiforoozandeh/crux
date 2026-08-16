---
id: h1
type: idea
schema: 2
title: the context adapter improves downstream accuracy
parent: q1
status: idea
rule:
measurement:
replicates:
verdict:
metric:
created: 2026-08-16T14:15:13
updated: 2026-08-16T14:15:13
---

# h1 — the context adapter improves downstream accuracy

Parent:: [[q1_does_the_context_adapter_improve_downstr]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null

<!-- spec 09: the BORING explanation — the cheapest way this result could be trivially
     true. One line, <=25 words, naming a family. Your checks must discriminate against it.
     The PI approves it before checks are written: `crux approve-null <id>`. -->
_(one line: the cheapest way this result could be trivially true — name a family from capacity, chance, leakage, selection, normalization, instrumentation)_

## Problem Statement

The adapter was added to the encoder and both arms were then trained under the same recipe, on the same corpus, for the same number of steps. Reported sizes: base arm 84M parameters, adapter arm 121M parameters. Both arms use the same input normalisation (per-channel z-scoring fitted on the training split), the same evaluator and the same fixed split, which was drawn before either arm was trained. Accuracy is averaged over 10 seeds; the 95% interval is +/- 0.2 points.

## Idea / Hypothesis

the context adapter improves downstream accuracy

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] adapter arm beats the base arm by >= 1.0 accuracy points
      fails-if:: the adapter arm lands within 1.0 points of the base arm

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h1/ and link at least the report:
     - [Report](results/h1/report.md)   - results/h1/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
