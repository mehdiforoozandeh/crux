---
id: s4
type: synthesis
title: Decoder head — mask-transformer for frozen DINO-family encoders
approved: "2026-07-24T15:26:44"
created: "2026-07-24T15:26:44"
updated: "2026-07-24T15:26:44"
---

# Synthesis — Decoder head — mask-transformer for frozen DINO-family encoders

Related:: [[q4_which_decoder_head_design_best_exploits_]]

## Headline conclusions

- **Head capacity gates frozen-encoder performance.** Linear probing trails full fine-tuning by 18–19 mIoU (24.7 for MAE) — it is not a usable proxy for encoder quality on segmentation.
- **UPerNet is a partial fix.** Within ~1.4 mIoU of fine-tuning for self-distillation and contrastive encoders, but 6.8 mIoU short for MAE.
- **The mask-transformer head wins on frozen DINOv2** — 49.5 vs 48.5 mIoU against UPerNet at ~55% of the decoder params, within 0.3 mIoU of full fine-tuning.

## Cross-run table

| id | hypothesis | verdict | headline metric |
|----|------------|---------|-----------------|
| `h10` | [[h10_upernet_decoder_on_frozen_features_close\|UPerNet decoder on frozen features closes the fine-tuning gap to <=2 mIoU on ADE20K]] | **partial** | ADE20K mIoU (frozen UPerNet vs fine-tuned UPerNet): DINO 46.8 vs 48.2 (-1.4), DINOv2 48.5 vs 49.8 (-1.3), MoCo v3 43.6 vs 45.1 (-1.5), MAE 41.3 vs 48.1 (-6.8) |
| `h11` | [[h11_segmenter_style_mask_transformer_head_be\|Segmenter-style mask-transformer head best exploits frozen DINOv2/iBOT tokens]] | **supported** | ADE20K mIoU: mask-transformer+frozen DINOv2 49.5 vs UPerNet+frozen DINOv2 48.5 (+1.0), vs full fine-tune 49.8 (-0.3 gap); decoder params 12M vs UPerNet's 22M (55%) |
| `h12` | [[h12_linear_probe_on_frozen_encoders_reaches_\|Linear probe on frozen encoders reaches within 5 mIoU of fine-tuning on Cityscapes]] | **refuted** | Cityscapes mIoU (linear probe vs full fine-tune): DINO 61.2 vs 79.4 (-18.2, 77%), MAE 52.1 vs 76.8 (-24.7, 68%), DenseCL 58.7 vs 78.1 (-19.4, 75%) |

## Implications for next batch

Mask-transformer heads become the default for DINO-family frozen encoders; UPerNet stays the fallback for MAE/MIM encoders; linear probing is dropped from the frozen-eval protocol except as a cheap sanity check.
