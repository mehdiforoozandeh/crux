---
type: wiki
title: Web-scale image-text corpora
summary: Hashtag- and caption-supervised corpora at billions of examples — the largest public evidence on data scaling, and the clearest case of returns depending on what the data is *of*.
category: dataset
sources: raw/radford2021_clip.pdf, raw/mahajan2018_weakly_supervised.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Web-scale image-text corpora

## Two forms

**Hashtag supervision.** Mahajan et al. (2018) pretrained on billions of public
Instagram images using hashtags as noisy labels, and reported that the benefit depended
strongly on how well the hashtag vocabulary matched the target task — matched
vocabularies transferred well, mismatched ones much less so. Scale alone did not
guarantee transfer.

**Caption supervision.** Radford et al. (2021) trained CLIP on around 400 million
image-text pairs with a contrastive objective, producing a model that transfers to many
classification tasks with no task-specific training at all.

## What they contribute to this question

They are the largest public data points on the data lever, and they carry the same
qualification twice over: returns depend on what the data is *of*, not only how much of
it there is. A billion mismatched examples can be worth less than a million matched
ones, which is a statement about [[data-quality]] and [[sample-efficiency]] rather than
about volume.

## Why they are not a baseline here

Both were trained at compute budgets this programme cannot match, and neither was run
against a capacity-matched control ([[controlled-comparison]]). They inform the shape of
the expected result and bound what is plausible. They do not settle anything, which is
the whole reason for running the comparison at a size that can actually be controlled.
