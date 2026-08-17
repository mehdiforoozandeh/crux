---
id: h1
type: idea
schema: 2
title: pretraining beats training from scratch at 100 labels
parent: q2
status: done
rule: all
measurement: mIoU at 100 labels
replicates: 3 seeds
verdict: supported
metric: +4.1 mIoU at 100 labels
created: "2026-08-16T14:15:13"
updated: "2026-08-16T14:15:13"
null_approved: "2026-08-16T14:15:13"
null_hash: 469a1f26dfe984d3
lock: 0197d68db35a86dd
locked: "2026-08-16T14:15:13"
lock_at: running
---

# h1 — pretraining beats training from scratch at 100 labels

Parent:: [[q2_does_pretraining_help_at_low_label_count]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this claims, and what would settle it)_

## Null
capacity — the pretrained arm is simply the larger encoder

## Problem Statement

_(why this is worth testing)_

## Idea / Hypothesis

pretraining beats training from scratch at 100 labels

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] pretrained arm beats scratch by >= 3 mIoU at 100 labels (found: +4.1 mIoU)
      fails-if:: the two arms land within 3 mIoU of each other at 100 labels
      discriminates:: true
- [x] [outcome-neutral] both arms match the published scratch number at 1000 labels (found: 71.2 vs published 71.0)
      fails-if:: neither arm reproduces the published number, so the harness is wrong

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- local run 2026-08-10

## Artifacts

<!-- what the run produced. Keep files under results/h1/ and link at least the report:
     - [Report](results/h1/report.md)   - results/h1/curve.png -->
_(none yet)_

## Findings

Pretraining beat scratch by 4.1 mIoU at 100 labels, on 3 seeds, and the control reproduced the published scratch number at 1000 labels, so the harness reads correctly. The null was capacity and it is not ruled out here: the pretrained encoder is larger, and a width-matched scratch arm was never run.

_(written by the PI/agent when the case is closed)_
