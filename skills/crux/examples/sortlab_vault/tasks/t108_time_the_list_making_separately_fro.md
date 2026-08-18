---
id: t108
type: task
title: Time the list-making separately from the sorting
category: benchmarking
parent: 
blocked_by: t101
refs: rd/timing_harness_v2
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:26"
updated: "2026-08-16T16:07:50"
---

# t108 — Time the list-making separately from the sorting

Refs:: [[rd/timing_harness_v2]]

## Why

Building the test list takes time, so timing that separately shows what the sort itself actually costs.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- [[rd/timing_harness_v2]]

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
