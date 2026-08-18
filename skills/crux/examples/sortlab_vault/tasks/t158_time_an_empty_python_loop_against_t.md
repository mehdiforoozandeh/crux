---
id: t158
type: task
title: Time an empty Python loop against the whole built-in sort
category: benchmarking
parent: 
blocked_by: t101, t78
refs: q23
hypothesis_refs: "h70:supported, h69:supported"
status: done
created: "2026-08-16T16:07:33"
updated: "2026-08-16T16:07:56"
---

# t158 — Time an empty Python loop against the whole built-in sort

Refs:: [[q23_is_the_built_in_sort_written_in_a_faster\|q23]]

## Why

I timed an empty loop to understand what the built-in sort really is.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t158.csv

## Evidence

A counting loop being slower than the whole sort was supported. The built-in not running my kind of Python was also supported. It runs at native speed.
