---
type: wiki
title: Masked modeling
summary: Self-supervision by reconstructing masked inputs; token vs stem targets.
category: concept
sources: raw/he2021_mae.txt
created: 2026-06-29T17:36:39
updated: 2026-06-29T17:36:39
---

# Masked modeling

Mask part of the input and predict it. The reconstruction *target* — raw token vs a learned stem — shapes the encoder, and motivates [[jepa]]. Metadata can be injected via [[film-conditioning]].

Related:: [[jepa]], [[film-conditioning]]
