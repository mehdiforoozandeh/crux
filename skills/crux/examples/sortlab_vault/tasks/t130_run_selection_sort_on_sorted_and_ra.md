---
id: t130
type: task
title: Run selection sort on sorted and random lists side by side
category: benchmarking
parent: 
blocked_by: t101
refs: q11
hypothesis_refs: "h30:supported"
status: done
created: "2026-08-16T16:07:29"
updated: "2026-08-16T16:08:01"
accepted: "2026-08-16T16:08:01"
---

# t130 — Run selection sort on sorted and random lists side by side

Refs:: [[q11_what_happens_on_a_list_that_is_already_s\|q11]]

## Why

Tests whether selection sort takes the same time on a random list and a sorted list.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/h30/report.md

## Evidence

Selection took almost exactly the same time on a sorted list and a random one. The shape of the list made no difference.
