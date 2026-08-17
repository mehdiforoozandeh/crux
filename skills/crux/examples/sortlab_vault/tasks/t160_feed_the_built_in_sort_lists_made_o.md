---
id: t160
type: task
title: Feed the built-in sort lists made of long runs
category: benchmarking
parent: 
blocked_by: t101
refs: q33
hypothesis_refs: "h102:supported, h103:supported"
status: done
created: "2026-08-16T16:07:33"
updated: "2026-08-16T16:07:56"
---

# t160 — Feed the built-in sort lists made of long runs

Refs:: [[q33_does_the_built_in_sort_notice_runs_that_\|q33]]

## Why

I tested the built-in sort on lists made of long sorted runs.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- results/runs/t160.csv

## Evidence

Both hypotheses were supported. On one sorted run, it finished in one millisecond. On lists of a few long runs, it stayed fast. It recognizes structure.
