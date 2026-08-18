---
id: t149
type: task
title: Compare warm-up on small and large lists
category: benchmarking
parent: 
blocked_by: t101, t81
refs: q19
hypothesis_refs: "h58:inconclusive"
status: done
created: "2026-08-16T16:07:31"
updated: "2026-08-16T16:08:04"
accepted: "2026-08-16T16:08:04"
---

# t149 — Compare warm-up on small and large lists

Refs:: [[q19_does_the_first_run_take_longer_than_the_\|q19]]

## Why

I wondered if warm-up matters more for small lists than big ones.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t149.csv

## Evidence

This hypothesis was inconclusive. On one thousand items, warm-up cost two milliseconds. On one million, it cost four. The ratio did not favor small lists.
