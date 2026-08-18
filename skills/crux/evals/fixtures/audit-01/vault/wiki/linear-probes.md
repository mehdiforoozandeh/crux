---
type: wiki
title: Linear probes
summary: A linear readout fitted on frozen features, used to measure what those features already carry.
category: method
sources: raw/linear-probes.txt
---

# Linear probes

A linear probe fits a linear model on top of features that are held fixed. Because the probe
has almost no capacity of its own, what it recovers is attributed to the features rather than
to the probe.

The standard caution is that a probe's score confounds two things: how much information the
features carry, and how linearly that information is laid out. See [[pooled-readouts]] for the
comparison this vault cares about.
