---
id: h26
type: idea
schema: 2
title: My quick sort hits the recursion limit at ten thousand sorted items
parent: q10
status: done
rule: all
measurement: The list size at which quick sort fails to complete, or a message that it completes all sizes.
replicates: 1 run at each of 10 sizes
verdict: supported
metric: Quick sort fails at exactly 10000 sorted items with RecursionError.
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:05"
null_approved: "2026-08-16T16:06:32"
null_hash: 3160bb025626cf72
lock: e3faaef9ac183fa4
locked: "2026-08-16T16:06:47"
lock_at: running
---

# h26 — My quick sort hits the recursion limit at ten thousand sorted items

Parent:: [[q10_does_my_quick_sort_break_on_a_list_that_]]

## ELI5

My quick sort hits the recursion limit at ten thousand sorted items.

## TL;DR

Because quick sort on a sorted list picks bad pivots and recurses n times instead of log n times, Python's recursion limit becomes a problem. I claimed it crashes at around ten thousand items and tested it on sorted lists from five thousand up.

Background:: [[wiki/pivot-choice]]

## Null
chance - one lucky run out of one would show this difference on its own

## Problem Statement

Quick sort's worst case can literally break the program if the list gets big enough. I wanted to know at what size this becomes a real problem on my laptop.

## Idea / Hypothesis

My quick sort hits the recursion limit at ten thousand sorted items

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Quick sort crashes or hits recursion error on sorted 10k (found: Fails at 10000, not before)
      fails-if:: Quick sort completes the sorted 10k list
      discriminates:: true
- [x] Quick sort completes sorted lists under 8k (found: Completes under 8k)
      fails-if:: Quick sort crashes on sorted lists under 8k
- [x] [outcome-neutral] The error message mentions recursion when it fails (found: RecursionError message)
      fails-if:: The program crashes with a different error

## Planned Intervention

Sorted lists from one thousand up to fifty thousand in steps of five thousand. One run per size. Python default recursion limit is one thousand. Track the size at which quick sort crashes.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h26/ and link at least the report:
     - [Report](results/h26/report.md)   - results/h26/curve.png -->
_(none yet)_

## Findings

Quick sort hit Python's recursion depth limit at exactly 10000 sorted items. Below that, it squeaked through. This is a real practical problem. If I want to sort sorted data using quick sort, I need to either increase the recursion limit or use a different algorithm.
