---
id: t136
type: task
title: Run the three-way split quick sort on the duplicate-heavy list
category: benchmarking
parent: 
blocked_by: t101
refs: q14
hypothesis_refs: "h41:supported"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t136 — Run the three-way split quick sort on the duplicate-heavy list

Refs:: [[q14_what_happens_when_the_list_is_mostly_the\|q14]]

## Why

Tests a three-way split partitioning on quick sort to see if it fixes the duplicate-value problem.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t136.csv

## Evidence

The three-way split partitioning fixed the duplicate problem. Quick sort on the duplicate-heavy list ran much faster with that change.
