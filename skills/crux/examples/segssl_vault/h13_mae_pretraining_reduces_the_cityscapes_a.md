---
id: h13
type: idea
title: MAE pretraining reduces the Cityscapes→ACDC mIoU drop vs. the supervised baseline
parent: q5
status: done
verdict: refuted
metric: +0.4 mIoU ACDC-mean (ns); −0.5 mIoU ACDC-night vs. supervised
created: "2026-07-11T19:38:55"
updated: "2026-07-11T19:38:55"
---

# h13 — MAE pretraining reduces the Cityscapes→ACDC mIoU drop vs. the supervised baseline

Parent:: [[q5_does_ssl_pretraining_confer_robustness_t]]

## Problem Statement

Reconstruction-based MIM pretraining (MAE; see [[wiki/mae]], [[wiki/masked-image-modeling]]) forces the encoder to infer masked patches from heavily corrupted context, which could yield representations that are invariant to low-level photometric variation. If so, a Cityscapes-trained MAE+UPerNet segmenter should degrade less than a supervised-ImageNet-1k+UPerNet segmenter when evaluated zero-shot on ACDC's fog/night/rain/snow splits.

## Idea / Hypothesis

MAE pretraining reduces the Cityscapes→ACDC mIoU drop vs. the supervised baseline

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] ACDC-mean mIoU gain over supervised ImageNet-1k baseline ≥ +3.0 mIoU
- [ ] ACDC-night mIoU gain over supervised baseline ≥ +2.0 mIoU
- [ ] Relative clear→ACDC-mean degradation reduced by ≥15% relative vs. supervised baseline's 34.7% drop

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- slurm 91847 (wandb seg-h5-mae-acdc)

## Findings

MAE+UPerNet (ViT-B/16, see [[wiki/vision-transformer]]; MAE 1600ep IN1k, Cityscapes fine-tune) beats supervised by +0.7 mIoU on clean Cityscapes val (79.8 vs 79.1) but the gain nearly vanishes OOD: ACDC-mean is 51.6 vs 51.2 (+0.4, bar was +3.0), and ACDC-night is actually worse (31.0 vs 31.5, −0.5 mIoU). Relative clear→ACDC degradation is 35.3% for MAE vs 35.3% for supervised — statistically unchanged. Reconstruction pretext improves clean-domain representation quality but does not transfer to photometric/weather robustness.
