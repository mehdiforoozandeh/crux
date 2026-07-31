---
type: wiki
title: Data quality and deduplication
summary: Corpus size counts examples, not information — duplicates, near-duplicates and train-test overlap all inflate the apparent value of more data.
category: concept
sources: raw/lee2021_dedup.pdf, raw/gao2020_the_pile.pdf
created: 2026-07-31
updated: 2026-07-31
---

# Data quality and deduplication

## Why raw size is the wrong axis

A data-scaling claim is stated in examples, but what the model receives is information.
Web-scraped corpora contain substantial duplication and near-duplication, so a corpus
twice the size may carry considerably less than twice the signal. Any measured data
exponent is therefore a joint statement about volume and quality, not about volume
alone.

## The deduplication result

Lee et al. (2021) deduplicated language-model training corpora and reported several
effects at once: models emitted memorised training text an order of magnitude less
often, reached the same perplexity in fewer training steps, and — the finding that
matters most here — evaluation was distorted before deduplication, because a nontrivial
fraction of validation examples also appeared in the training set. Train-test overlap
does not merely add noise; it biases in a known direction.

## Consequences for this programme

Two arms with the same nominal data volume can differ in effective volume if they were
filtered differently. Deduplication is therefore applied identically to both arms before
any comparison, and the deduplicated counts are what get reported — not the raw ones.

Overlap between the training corpus and the held-out set is checked rather than assumed
([[held-out-evaluation]]).

## Curation as a design choice

The Pile ([[text-corpora]]) is the clearest case of quality treated as a design variable
rather than an afterthought: it is assembled from twenty-two deliberately chosen
sub-corpora rather than scraped indiscriminately, on the argument that diversity of
source is itself a quality axis.
