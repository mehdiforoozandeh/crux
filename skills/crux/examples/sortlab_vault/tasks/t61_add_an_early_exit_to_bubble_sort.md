---
id: t61
type: task
title: Add an early exit to bubble sort
category: implementation
parent: 
blocked_by: t56
refs: 
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:20"
updated: "2026-08-16T16:07:45"
---

# t61 — Add an early exit to bubble sort

Refs:: _(none)_

## Why

Bubble sort can stop early if nothing moved in a pass, and that saves time on sorted lists.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- code/t61_add_an_early_exit_to_bub.py

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
