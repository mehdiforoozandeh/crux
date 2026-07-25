---
id: s1
type: synthesis
title: SSL vs supervised init — adopt SSL, but standardize on self-distillation
approved: "2026-07-24T15:26:44"
created: "2026-07-24T15:26:44"
updated: "2026-07-24T15:26:44"
---

# Synthesis — SSL vs supervised init — adopt SSL, but standardize on self-distillation

Related:: [[q1_does_self_supervised_pretraining_beat_su]]

## Headline conclusions

- **Self-distillation is the only clean win.** iBOT+UPerNet beat supervised ImageNet-1k init by +3.3 mIoU on ADE20K and +1.5 on Cityscapes, in all three seeds — every pre-registered bar met.
- **MAE's advantage is fine-tuning-only.** It clears supervised under full FT (+1.8 ADE20K) but trails it by 6.7 mIoU frozen, so it is not evidence of better encoder quality.
- **Dense contrastive is out.** DenseCL underperformed supervised init on VOC2012 (−1.3 mIoU) and missed its bar on ADE20K.

## Cross-run table

| id | hypothesis | verdict | headline metric |
|----|------------|---------|-----------------|
| `h1` | [[h1_ibot_upernet_beats_supervised_imagenet_i\|iBOT+UPerNet beats supervised ImageNet init on ADE20K and Cityscapes under full FT]] | **supported** | +3.3 mIoU ADE20K, +1.5 mIoU Cityscapes (iBOT vs supervised, UPerNet, full FT) |
| `h2` | [[h2_mae_beats_supervised_init_only_under_ful\|MAE beats supervised init only under full fine-tuning, not frozen linear-probe transfer]] | **partial** | +1.8 mIoU ADE20K (full FT); -6.7 mIoU frozen linear-probe vs supervised |
| `h3` | [[h3_densecl_dense_contrastive_pretraining_be\|DenseCL dense-contrastive pretraining beats supervised init on VOC2012 transfer]] | **refuted** | -1.3 mIoU, -2.6 boundary-mIoU VOC2012 (DenseCL vs supervised, Segmenter) |

## Implications for next batch

Adopt SSL pretraining program-wide, with iBOT/DINO as the default init. Do not treat the SSL families as interchangeable — the family, not the label 'self-supervised', is what carries the gain. Next batch inherits iBOT as the baseline to beat.
