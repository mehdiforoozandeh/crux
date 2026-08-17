---
id: t124
type: task
title: Count swaps for the three slow sorts
category: benchmarking
parent: 
blocked_by: t101
refs: q1
hypothesis_refs: "h2:supported"
status: done
created: "2026-08-16T16:07:28"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t124 — Count swaps for the three slow sorts

Refs:: [[q1_which_sort_that_i_wrote_myself_is_fastes\|q1]]

## Why

Counts the swap operations each sort makes to understand why they have different speeds.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t124.csv

## Evidence

I counted the swaps each sort made. Selection won by a mile, doing about half as many as the others.
