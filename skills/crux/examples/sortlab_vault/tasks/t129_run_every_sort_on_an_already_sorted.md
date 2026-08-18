---
id: t129
type: task
title: Run every sort on an already sorted list
category: benchmarking
parent: 
blocked_by: t101, t59
refs: q11
hypothesis_refs: "h28:refuted, h29:supported"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t129 — Run every sort on an already sorted list

Refs:: [[q11_what_happens_on_a_list_that_is_already_s\|q11]]

## Why

Races all five sorts on an already sorted list to find which ones handle this edge case well.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t129.csv

## Evidence

Bubble sort with the early exit was much faster than insertion on a sorted list. Insertion was not the winner I expected.
