---
id: t60
type: task
title: Fix quick sort crashing on a sorted list
category: implementation
parent: 
blocked_by: t55
refs: q10
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:20"
updated: "2026-08-16T16:07:45"
---

# t60 — Fix quick sort crashing on a sorted list

Refs:: [[q10_does_my_quick_sort_break_on_a_list_that_\|q10]]

## Why

Quick sort crashed when the list was already sorted, and that ruined a whole timing run.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- code/t60_fix_quick_sort_crashing.py

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
