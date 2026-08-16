---
id: t59
type: task
title: Fix the off-by-one bug in merge sort
category: implementation
parent: 
blocked_by: t54
refs: 
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:20"
updated: "2026-08-16T16:07:45"
---

# t59 — Fix the off-by-one bug in merge sort

Refs:: _(none)_

## Why

Merge sort was copying items to the wrong positions, and the checker caught that.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- code/t59_fix_the_off-by-one_bug_i.py

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
