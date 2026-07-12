---
id: h15
type: idea
title: Dense contrastive (DenseCL/PixPro) + Segmenter decoder improves ACDC robustness
parent: q5
status: idea
verdict:
metric:
created: 2026-07-11T19:38:55
updated: 2026-07-11T19:38:55
---

# h15 — Dense contrastive (DenseCL/PixPro) + Segmenter decoder improves ACDC robustness

Parent:: [[q5_does_ssl_pretraining_confer_robustness_t]]

## Problem Statement

Dense/pixel-level contrastive objectives (DenseCL, PixPro; see [[wiki/densecl]], [[wiki/pixpro]]) enforce local region-to-region correspondence invariance under augmentation, rather than pooling to a single global embedding like MoCo or DINO. Paired with a Segmenter-style mask-transformer decoder (see [[wiki/segmentation-decoders]]) that reads out dense tokens directly into class queries, this may better preserve fine-grained boundary robustness under weather corruption than a global-pooled encoder feeding a linear or UPerNet head.

## Idea / Hypothesis

Dense contrastive (DenseCL/PixPro) + Segmenter decoder improves ACDC robustness

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] ACDC-mean mIoU gain over the best global-contrastive (MoCo) arm ≥ +2.5 mIoU
- [ ] Boundary-region mIoU (within 5px of GT edges) gain on ACDC-fog ≥ +3.0 mIoU
- [ ] ACDC-mean mIoU gain over the H1 MAE arm ≥ +2.0 mIoU

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
