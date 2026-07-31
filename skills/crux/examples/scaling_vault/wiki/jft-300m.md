---
type: wiki
title: JFT-300M and large weakly labelled corpora
summary: The 300M-image internal corpus behind the 'performance grows logarithmically with data' result — and the qualification that is usually dropped when it is cited.
category: dataset
sources: raw/sun2017_revisiting_data.pdf, raw/kolesnikov2019_bit.pdf
created: 2026-07-31
updated: 2026-07-31
---

# JFT-300M and large weakly labelled corpora

## What it is

An internal Google corpus of roughly 300 million images with noisy, algorithmically
assigned labels across some 18,000 classes — two orders of magnitude beyond
[[imagenet]]-1k, at the cost of substantial label noise.

## The result it produced

Sun et al. (2017) trained across the full range and found representation quality growing
roughly logarithmically with data volume, with no plateau at the scales reachable. This
is the most cited evidence for "data is the binding constraint".

The qualification, usually omitted when it is cited: the gains required model capacity
to grow with the data. Held at fixed capacity the curve flattens. The paper is evidence
for a *joint* scaling claim, not a data-only one ([[data-vs-model-scaling]]).

Kolesnikov et al. (2019) built on the same corpus and reported that once pretraining is
large enough, downstream tuning complexity largely disappears
([[transfer-learning]]).

## Why it is not directly usable

JFT is not public, so results on it cannot be reproduced or audited from outside. It is
cited here as prior evidence about the *shape* of data scaling, never as a baseline this
vault's numbers are compared against. Where a public analogue is needed,
[[web-scale-image-text]] corpora serve instead.
