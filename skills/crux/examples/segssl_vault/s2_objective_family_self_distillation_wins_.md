---
id: s2
type: synthesis
title: Objective family — self-distillation wins dense transfer, dense-contrastive is shelved
approved: "2026-07-24T15:26:44"
created: "2026-07-24T15:26:44"
updated: "2026-07-24T15:26:44"
---

# Synthesis — Objective family — self-distillation wins dense transfer, dense-contrastive is shelved

Related:: [[q2_which_ssl_objective_family_contrastive_v]]

## Headline conclusions

- **Self-distillation beats both alternatives at their own game.** iBOT/DINO led MAE by +1.5 mIoU and DenseCL by +2.6 mIoU on ADE20K under UPerNet, and held the margin under Cityscapes→ACDC shift.
- **The 'dense pretext ⇒ dense transfer' intuition was wrong.** DenseCL/PixPro trailed everywhere and degraded worst under domain shift.
- **MAE is a conditional fallback.** Within 1.5–1.9 mIoU of iBOT under full FT, but 9.4 mIoU behind when frozen.

## Cross-run table

| id | hypothesis | verdict | headline metric |
|----|------------|---------|-----------------|
| `h4` | [[h4_self_distillation_ibot_dino_transfers_be\|Self-distillation (iBOT/DINO) transfers best to dense prediction under UPerNet]] | **supported** | +2.6 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs best rival family, UPerNet) |
| `h5` | [[h5_dense_pixel_contrastive_densecl_pixpro_t\|Dense-pixel contrastive (DenseCL/PixPro) transfers best to dense prediction]] | **refuted** | -2.6 mIoU ADE20K vs iBOT (DenseCL, UPerNet) |
| `h6` | [[h6_mae_mim_matches_self_distillation_only_u\|MAE (MIM) matches self-distillation only under full fine-tuning, not linear probe]] | **partial** | -1.5 UPerNet / -9.4 linear-probe mIoU gap (MAE vs iBOT) |

## Implications for next batch

Standardize the pretraining recipe on iBOT/DINO for dense prediction; keep MAE only where a full fine-tuning budget exists; stop investing in dense-contrastive pretext design for this program.
