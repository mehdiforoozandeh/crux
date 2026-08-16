---
id: t80
type: task
title: Fix the seed so lists repeat exactly
category: data-acquisition
parent: 
blocked_by: t75
refs: q2
hypothesis_refs: 
status: done
created: "2026-08-16T16:07:23"
updated: "2026-08-16T16:07:47"
---

# t80 — Fix the seed so lists repeat exactly

Refs:: [[q2_does_the_shape_of_the_list_change_which_\|q2]]

## Why

A fixed seed means every test run uses identical lists, so differences in timing are real.

## Output

<!-- required before `done`, and the engine checks it resolves. Either form:
     - [Deduped table](results/dedupe/table.tsv)   - [[wiki/candi-datasets]] -->
- data/t80_fix_the_seed_so_lists_re.csv

## Evidence

_(experiments only: what this run showed, in prose. The structured fact is
`hypothesis_refs` in the frontmatter; this is the narrative beside it, and the
engine never parses it.)_
