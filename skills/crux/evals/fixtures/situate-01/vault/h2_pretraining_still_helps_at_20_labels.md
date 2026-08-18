---
id: h2
type: idea
schema: 2
title: pretraining still helps at 20 labels
parent: q2
status: idea
rule:
measurement:
replicates:
verdict:
metric:
created: 2026-08-16T14:15:14
updated: 2026-08-16T14:15:14
---

# h2 — pretraining still helps at 20 labels

Parent:: [[q2_does_pretraining_help_at_low_label_count]]

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

_(why this is worth testing)_

## Idea / Hypothesis

pretraining still helps at 20 labels

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] pretrained arm beats scratch by >= 3 mIoU at 20 labels
      fails-if:: the two arms land within 3 mIoU of each other at 20 labels

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
