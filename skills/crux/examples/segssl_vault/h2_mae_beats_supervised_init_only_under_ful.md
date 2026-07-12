---
id: h2
type: idea
title: MAE beats supervised init only under full fine-tuning, not frozen linear-probe transfer
parent: q1
status: done
verdict: partial
metric: +1.8 mIoU ADE20K (full FT); -6.7 mIoU frozen linear-probe vs supervised
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h2 — MAE beats supervised init only under full fine-tuning, not frozen linear-probe transfer

Parent:: [[q1_does_self_supervised_pretraining_beat_su]]

## Problem Statement

MAE ([[wiki/mae]]) fine-tunes strongly despite weak linear separability of its frozen features, an objective rooted in masked-image-modeling ([[wiki/masked-image-modeling]]); we test whether its win over supervised init is a general encoder-quality gain (holding under frozen linear probing and on Cityscapes ([[wiki/cityscapes]])) or an artifact of full fine-tuning on ADE20K only.

## Idea / Hypothesis

MAE beats supervised init only under full fine-tuning, not frozen linear-probe transfer

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] MAE+UPerNet ADE20K val mIoU >= supervised+UPerNet ADE20K val mIoU + 1.5
- [ ] MAE+UPerNet Cityscapes val mIoU >= supervised+UPerNet Cityscapes val mIoU + 2.0
- [ ] MAE frozen linear-probe ADE20K mIoU >= supervised frozen linear-probe ADE20K mIoU

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 83705 (wandb segssl/q1-mae-vs-sup)

## Findings

Under full fine-tuning MAE beat supervised on ADE20K by 1.8 mIoU (48.1 vs 46.3), meeting the first bar, but its Cityscapes margin was only +1.5 (80.6 vs 79.1), short of the +2.0 bar, and its frozen linear-probe ADE20K features collapsed to 24.1 mIoU versus supervised's 30.8 (-6.7), failing the frozen-transfer bar. Exactly one of three pre-registered bars was met. MAE's advantage is therefore a fine-tuning-only effect, not evidence that MIM yields generally better encoder features than supervised init.
