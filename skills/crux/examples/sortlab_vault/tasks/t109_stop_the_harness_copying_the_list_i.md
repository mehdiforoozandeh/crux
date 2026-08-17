---
id: t109
type: task
title: Stop the harness copying the list inside the timed part
category: benchmarking
parent: 
blocked_by: t101
refs: rd/timing_harness_v2
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:26"
updated: "2026-08-16T16:07:50"
---

# t109 — Stop the harness copying the list inside the timed part

Refs:: [[rd/timing_harness_v2]]

## Why

If the code copies the list inside the timed section, the copy cost gets mixed in with the sort cost.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- [[rd/timing_harness_v2]]

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
