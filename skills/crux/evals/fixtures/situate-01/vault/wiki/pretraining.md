---
type: wiki
title: Pretraining for dense prediction
summary: Training on a large unlabelled corpus first, then fine-tuning on the labelled task.
category: method
sources: raw/pretraining.txt
---

# Pretraining for dense prediction

Pretraining fits a model on a large unlabelled corpus and then fine-tunes it on the labelled
task. The reported benefit is largest where labels are scarce, and it shrinks as the labelled
set grows.

Two things are routinely confounded with the benefit: the pretrained encoder is often larger,
and the pretraining corpus often overlaps the evaluation set.
