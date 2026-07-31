---
id: h2
type: idea
title: The advantage survives at equal compute
parent: q1
status: done
verdict: partial
metric: +1.8 at equal data; -4.6 at equal compute
created: "2026-07-31T14:45:03"
updated: "2026-07-31T14:45:03"
---

# h2 — The advantage survives at equal compute

Parent:: [[q1_does_more_data_beat_a_better_model]]

## Problem Statement

Doubling the training set also roughly doubles the training compute, so the h1 result is consistent with both 'more data helps' and 'more budget helps' and distinguishes neither ([[wiki/compute-budget]]). Matching total training FLOPs across the two arms separates them. This is the exact confound behind the [[wiki/compute-optimal-training]] correction, so it is tested rather than discussed.

## Idea / Hypothesis

The advantage survives at equal compute

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] beats the better model at equal data
- [ ] beats the better model at equal compute
- [ ] the gap stays under 1 point on the second task

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- job 4031

## Artifacts

<!-- what the run produced. Keep files under results/h2/ and link at least the report:
     - [Report](results/h2/report.md)   - results/h2/curve.png -->
_(none yet)_

## Findings

At equal data the gain replicates (+1.8). Matched on training FLOPs it reverses (-4.6). Exactly one of three bars was met: most of the h1 advantage was the extra budget, not the extra data.
