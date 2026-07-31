---
type: wiki
title: Text corpora — The Pile and C4
summary: Two large public text corpora built on opposite philosophies — deliberate diversity versus filtered scale — and what that difference does to a scaling measurement.
category: dataset
sources: raw/gao2020_the_pile.pdf, raw/raffel2019_t5.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Text corpora — The Pile and C4

## C4

Introduced with T5 (Raffel et al., 2019): Common Crawl, cleaned by a set of heuristic
filters — drop pages without terminal punctuation, drop boilerplate, drop
placeholder and offensive text, deduplicate. It is scale plus a filter, and its size
after filtering is on the order of hundreds of gigabytes of English text.

## The Pile

Gao et al. (2020): roughly 825 GiB assembled from twenty-two deliberately selected
sub-corpora — academic papers, code, legal text, subtitles and more — on the explicit
argument that source diversity is itself a quality axis rather than something to be
averaged out by scale.

## Why the contrast matters here

The two encode opposite answers to the question this vault is asking, one level down.
C4 treats data as a quantity to be filtered; The Pile treats composition as a design
variable. A scaling exponent measured on one is not a property of "text" — it is a
property of that corpus's composition ([[data-quality]]).

## Consequence for the design

Corpus composition is fixed and identical across arms here, and stated. Where a data
volume is reported, it is the post-deduplication count, since duplication silently
converts extra volume into extra epochs ([[data-repetition]]).
