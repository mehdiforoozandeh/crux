---
id: t138
type: task
title: Run the doubling ladder for insertion sort and bubble sort
category: benchmarking
parent: 
blocked_by: t101, t68
refs: q15
hypothesis_refs: "h43:supported, h44:inconclusive"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t138 — Run the doubling ladder for insertion sort and bubble sort

Refs:: [[q15_if_i_double_the_list_does_the_time_doubl\|q15]]

## Why

I wanted to compare how all three slow sorts scale with size.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t138.csv

## Evidence

Doubling was supported for insertion sort; the time quadrupled consistently. For bubble sort, results were inconclusive. The slowdown ranged from three point eight to four point five. No single pattern emerged.
