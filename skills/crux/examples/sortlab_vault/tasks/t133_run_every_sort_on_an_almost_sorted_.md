---
id: t133
type: task
title: Run every sort on an almost-sorted list
category: benchmarking
parent: 
blocked_by: t101
refs: q13
hypothesis_refs: "h34:supported, h36:supported"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t133 — Run every sort on an almost-sorted list

Refs:: [[q13_what_happens_when_the_list_is_almost_sor\|q13]]

## Why

Tests all five sorts on an almost-sorted list, since many real-world lists come out nearly in order.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t133.csv

## Evidence

Insertion sort loved the almost-sorted list, running at nearly sorted-list speeds. The built-in sort ran even faster on almost-sorted data.
