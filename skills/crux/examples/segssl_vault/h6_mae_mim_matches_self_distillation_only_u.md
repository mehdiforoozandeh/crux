---
id: h6
type: idea
title: MAE (MIM) matches self-distillation only under full fine-tuning, not linear probe
parent: q2
status: done
verdict: partial
metric: -1.5 UPerNet / -9.4 linear-probe mIoU gap (MAE vs iBOT)
created: "2026-07-11T19:38:54"
updated: "2026-07-11T19:38:54"
---

# h6 — MAE (MIM) matches self-distillation only under full fine-tuning, not linear probe

Parent:: [[q2_which_ssl_objective_family_contrastive_v]]

## Problem Statement

Test whether MAE's masked-patch reconstruction closes the dense-prediction transfer gap to self-distillation (iBOT), and whether that gap is decoder/protocol-dependent (full fine-tune + UPerNet vs. frozen linear probe) (background: [[wiki/mae]], [[wiki/masked-image-modeling]], [[wiki/ibot]]).

## Idea / Hypothesis

MAE (MIM) matches self-distillation only under full fine-tuning, not linear probe

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] MAE+UPerNet ADE20K mIoU >= iBOT+UPerNet ADE20K mIoU - 1.5
- [ ] MAE+UPerNet Cityscapes->ACDC domain-shift mIoU >= iBOT+UPerNet domain-shift mIoU - 2.5
- [ ] MAE+linear-probe ADE20K mIoU >= iBOT+linear-probe ADE20K mIoU - 3.0

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- wandb segssl/q2-h3-mae-decoder-ablation

## Findings

With full fine-tuning against UPerNet, MAE nearly matched iBOT on ADE20K (48.1 vs 49.6, -1.5) and Cityscapes->ACDC domain shift (40.1 vs 42.0, -1.9), meeting both near-parity bars. Under frozen linear probing, however, MAE collapsed to 24.1 mIoU vs iBOT's 33.5 mIoU, a 9.4-point gap over triple the 3.0-point tolerance, showing MIM features need decoder-side nonlinear recombination to become usable. The decoder-dependence portion of the hypothesis holds; the claim that the gap stays small regardless of decoder does not.
