---
id: h16
type: idea
title: DINOv2 pretraining preserves its low-label advantage under ACDC-fog domain shift
parent: q5
status: done
verdict: inconclusive
metric: n/a — no scored submission returned
created: "2026-07-24T15:46:27"
updated: "2026-07-24T15:46:27"
---

# h16 — DINOv2 pretraining preserves its low-label advantage under ACDC-fog domain shift

Parent:: [[q5_does_ssl_pretraining_confer_robustness_t]]

## Problem Statement

q3 showed DINOv2 delays low-label collapse and q5 asks whether SSL confers robustness; the two together predict that a 1%-label DINOv2 segmenter should keep its margin over supervised init when evaluated on ACDC-fog. This is the cell where the label-efficiency and robustness tracks intersect.

## Idea / Hypothesis

DINOv2 pretraining preserves its low-label advantage under ACDC-fog domain shift

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [-] ACDC-fog mIoU gain over supervised init >= +5.0 at 1% labels
- [-] Relative clear->fog degradation no worse than the 100%-label DINOv2 arm
- [-] Result reproduces across 3 seeds

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 92610 (submission queue: acdc-benchmark)

## Artifacts

<!-- what the run produced. Keep files under results/h16/ and link at least the report:
     - [Report](results/h16/report.md)   - results/h16/curve.png -->
_(none yet)_

## Findings

Could not evaluate. ACDC withholds the fog split's test annotations behind its benchmark server, and our three submissions were rate-limited past the evaluation window, so no scored result came back for any seed. The hypothesis is neither supported nor refuted — it is untested, and recorded as such so the next batch re-queues it early rather than re-deriving the plan.
