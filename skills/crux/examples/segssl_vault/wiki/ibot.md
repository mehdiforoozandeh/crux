---
type: wiki
title: iBOT
summary: Unifies masked image modeling and self-distillation via an online tokenizer (a momentum teacher) supplying targets for masked-patch prediction, bridging BEiT-style MIM and DINO-style distillation.
category: method
sources: raw/zhou2021_ibot.pdf
created: 2026-07-11
updated: 2026-07-11
---

# iBOT

iBOT (Zhou et al., ICLR 2022) observes that [[beit]]'s masked-image-modeling loss and [[dino]]'s self-distillation loss are the same knowledge-distillation objective with different tokenizers, then closes the gap by making the tokenizer an online, jointly-trained network instead of a pre-fixed offline one.

## The unifying move: MIM and self-distillation are both KD

BEiT's MIM loss (Eq. 1) minimizes −Σ m_i·P_φ(x_i)ᵀ log P_θ(x̂_i): a student θ predicts masked tokens against targets from a discrete VAE tokenizer with parameters φ, pre-trained offline on a DALL-E dVAE and frozen before MIM starts. DINO's self-distillation loss (Eq. 2) minimizes −P_θ'^[CLS](v)ᵀ log P_θ^[CLS](u): a student θ matches a teacher θ′ that is an EMA of the student's own past weights — no fixed φ, no separate pretraining stage. iBOT notes these are formally identical KD losses differing only in whether the "tokenizer" is external and frozen (φ) or the model's own online, momentum-updated self (θ′). Substituting θ′ for φ turns [[masked-image-modeling]] into a single-stage, jointly-optimized objective and dispenses with BEiT's two-stage pipeline (train dVAE, then train ViT).

## Framework

Two augmented views u, v of image x are formed; the student gets blockwise-masked versions û, v̂ (masking scheme from BEiT), the teacher sees the unmasked views. Two losses are summed unscaled: L_[CLS], DINO's exact cross-view class-token cross-entropy between teacher/student [CLS] outputs; and L_MIM = −Σ m_i·P_θ'^patch(u_i)ᵀ log P_θ^patch(û_i), an in-view patch-level cross-entropy where the teacher's patch tokens from the unmasked view supervise the student's masked-token predictions. Both losses are symmetrized over swapped views. The teacher's backbone-plus-head (h_t^patch ∘ f_t) is thus the online visual tokenizer — jointly learned via EMA, needing no separate pretraining, no fixed architecture, and no extra dataset. Projection heads for [CLS] and patch tokens are tied (h^[CLS] = h^patch) — found empirically to outperform separate heads — and targets are softmax token *distributions* (not one-hot IDs), since patch semantics are more ambiguous than discrete word tokens. Masking ratio r is 0 with probability 0.5 (pure DINO-style step) and uniform in [0.1, 0.5] otherwise.

## Results and emergent semantics

Pretrained on ImageNet-1K/22K with ViT-S/B/L/16 and Swin-T, iBOT reaches 82.3% linear probing / 87.8% fine-tuning on ImageNet-1K (ViT-L/16, IN-22K pretrain, 512px), and improves DINO's k-NN/linear/fine-tune by 1.0/1.3/0.4 points at matched ViT-B/16 scale. It transfers strongly: COCO detection/instance-seg (ViT-B/16: 51.2 AP^b, 44.2 AP^m vs. DINO 50.1/43.4), ADE20K semantic segmentation (+3.2 mIoU over DINO with UperNet; BEiT's linear-head mIoU trails badly at 27.4 vs. iBOT's 38.3, evidencing BEiT's tokens lack local semantics), label-efficient semi-supervised classification (+1.6/+0.8 over DINO at 1%/10% labels), and robustness (IN-A 13.8 vs. DINO 12.3, lower IN-C mCE). Patch-token visualizations show clusters with genuine part semantics (headlights, dog ears) unlike BEiT's texture-level dVAE tokens. DINOv2 later adopts L_MIM directly as its patch-level term alongside DINO's image-level loss, untying the shared head iBOT ties.

## See also

Related:: [[masked-image-modeling]] [[self-distillation]] [[dino]] [[beit]] [[dinov2]] [[vision-transformer]] [[label-efficiency]] [[mae]] [[segmentation-decoders]]
