---
id: t139
type: task
title: Run the doubling ladder past one hundred thousand items
category: benchmarking
parent: 
blocked_by: t101
refs: q34
hypothesis_refs: "h105:inconclusive, h106:supported"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:03"
accepted: "2026-08-16T16:08:03"
---

# t139 — Run the doubling ladder past one hundred thousand items

Refs:: [[q34_does_the_doubling_ratio_settle_down_at_b\|q34]]

## Why

I needed to check if the scaling held true at very large sizes.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t139.csv

## Evidence

The settling hypothesis was inconclusive; the ratio never stabilized. Insertion sort's ratio being closer to four was supported. At one million items it held.
