---
id: t137
type: task
title: Run the doubling ladder for merge sort
category: benchmarking
parent: 
blocked_by: t101, t81
refs: q15
hypothesis_refs: "h42:refuted"
status: done
created: "2026-08-16T16:07:30"
updated: "2026-08-16T16:08:02"
accepted: "2026-08-16T16:08:02"
---

# t137 — Run the doubling ladder for merge sort

Refs:: [[q15_if_i_double_the_list_does_the_time_doubl\|q15]]

## Why

I ran the doubling test to see how merge sort scales.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t137.csv

## Evidence

Doubling the list refuted my prediction. I thought the time would double. It actually grew by two point three times. That was more than expected.
