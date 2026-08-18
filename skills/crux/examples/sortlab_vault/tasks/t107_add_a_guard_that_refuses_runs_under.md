---
id: t107
type: task
title: Add a guard that refuses runs under the timer floor
category: benchmarking
parent: 
blocked_by: t101
refs: rd/timing_harness_v2
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:26"
updated: "2026-08-16T16:07:50"
---

# t107 — Add a guard that refuses runs under the timer floor

Refs:: [[rd/timing_harness_v2]]

## Why

If a run is shorter than the clock's smallest step, the number is noise, so I reject it outright.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- [[rd/timing_harness_v2]]

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
