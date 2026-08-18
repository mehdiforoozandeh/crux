---
type: wiki
title: Pooled readouts
summary: A readout that aggregates over positions before scoring, trading resolution for stability.
category: method
sources: raw/pooled-readouts.txt
---

# Pooled readouts

A pooled readout averages or max-reduces over positions before the score is computed. It is
more stable than a per-position readout on small samples, and it discards positional detail by
construction.

Contrast with [[linear-probes]], which keeps the positional structure and pays for it in
variance.
