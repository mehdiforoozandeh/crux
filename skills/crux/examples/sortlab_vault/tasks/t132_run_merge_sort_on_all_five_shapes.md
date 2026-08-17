---
id: t132
type: task
title: Run merge sort on all five shapes
category: benchmarking
parent: 
blocked_by: t101, t62
refs: q12, q13
hypothesis_refs: "h33:supported, h35:supported"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t132 — Run merge sort on all five shapes

Refs:: [[q12_what_happens_on_a_list_that_is_sorted_ba\|q12]], [[q13_what_happens_when_the_list_is_almost_sor\|q13]]

## Why

Tests merge sort on all five shapes to confirm that it does not care about the order of the data.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t132.csv

## Evidence

Merge sort ran at nearly the same speed on a reversed list, an almost-sorted list, and a random one. It simply did not care.
