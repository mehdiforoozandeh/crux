---
id: h3
type: idea
title: DenseCL dense-contrastive pretraining beats supervised init on VOC2012 transfer
parent: q1
status: done
verdict: refuted
metric: -1.3 mIoU, -2.6 boundary-mIoU VOC2012 (DenseCL vs supervised, Segmenter)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h3 — DenseCL dense-contrastive pretraining beats supervised init on VOC2012 transfer

Parent:: [[q1_does_self_supervised_pretraining_beat_su]]

## Problem Statement

Dense/pixel-level contrastive pretext (DenseCL, [[wiki/densecl]]), an instance of contrastive learning ([[wiki/contrastive-learning]]), optimizes spatial correspondence and is claimed to transfer best to dense prediction; we test whether it beats supervised ImageNet-1k init with a Segmenter head ([[wiki/segmentation-decoders]]) on the object-centric Pascal VOC 2012 benchmark and with UPerNet on ADE20K.

## Idea / Hypothesis

DenseCL dense-contrastive pretraining beats supervised init on VOC2012 transfer

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] DenseCL+Segmenter VOC2012 val mIoU >= supervised+Segmenter VOC2012 val mIoU + 1.0
- [ ] DenseCL+Segmenter VOC2012 boundary-mIoU >= supervised+Segmenter VOC2012 boundary-mIoU
- [ ] DenseCL+UPerNet ADE20K val mIoU >= supervised+UPerNet ADE20K val mIoU + 1.0

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 83788 (wandb segssl/q1-densecl-vs-sup)

## Findings

DenseCL+Segmenter underperformed supervised init on Pascal VOC 2012 by 1.3 mIoU (76.9 vs 78.2) and 2.6 boundary-mIoU (62.1 vs 64.7), and on ADE20K it edged supervised by only +0.7 mIoU (47.0 vs 46.3), below the +1.0 bar. None of the three pre-registered bars were met. Despite optimizing pixel-level correspondence, dense-contrastive pretraining gave no reliable transfer advantage over supervised init in the full-label regime, echoing Q2's finding that DenseCL trailed both iBOT and MAE.
