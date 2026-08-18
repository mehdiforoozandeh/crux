---
id: t119
type: task
title: Run the three slow sorts on random lists at five sizes
category: benchmarking
parent: 
blocked_by: t101, t75
refs: q8
hypothesis_refs: "h17:supported, h18:refuted"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:00"
accepted: "2026-08-16T16:08:00"
---

# t119 — Run the three slow sorts on random lists at five sizes

Refs:: [[q8_which_of_the_three_slow_sorts_is_least_s\|q8]]

## Why

Compares the three slow sorts to find which one is actually fastest at multiple sizes.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t119.csv

## Evidence

Insertion came out fastest of the three. Bubble was not always slowest—something else beat it sometimes.
