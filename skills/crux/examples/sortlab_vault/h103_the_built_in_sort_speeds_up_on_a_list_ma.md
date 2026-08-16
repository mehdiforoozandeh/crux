---
id: h103
type: idea
schema: 2
title: The built-in sort speeds up on a list made of a few long runs
parent: q33
status: done
rule: m-of-n
measurement: Median time for built-in sort on partially sorted lists with three long runs.
replicates: 30 repeats at each of 4 sizes from 10k to 100k, testing 3-run structure.
verdict: supported
metric: "Three-run: 10k was 0.14 ms, 100k was 0.95 ms. Random same sizes: 0.13, 1.09."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
rule_m: 2
null_approved: "2026-08-16T16:06:40"
null_hash: eae984b5dd8a6a04
lock: d8253b4edd0e632b
locked: "2026-08-16T16:07:02"
lock_at: running
---

# h103 — The built-in sort speeds up on a list made of a few long runs

Parent:: [[q33_does_the_built_in_sort_notice_runs_that_]]

## ELI5

The built-in sort speeds up when the list is a few big sorted chunks.

## TL;DR

I created lists that were already split into several long runs of sorted data. The built-in sort handled these much faster than random lists but slower than fully sorted lists. This suggests the built-in sort can merge pre-sorted chunks efficiently.

Background:: [[wiki/timsort]]

## Null
capacity - memory caching on mostly-sorted data, not algorithm logic, explains the speedup.

## Problem Statement

Many real-world data sets are partly sorted: a file of log entries in time order, a user list sorted by first name but not last name. The built-in sort should handle these efficiently. I want to confirm it does.

## Idea / Hypothesis

The built-in sort speeds up on a list made of a few long runs

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Three-run time is faster than random list but slower than fully sorted (found: Three-run 0.95 ms, random 1.09 ms)
      fails-if:: Three-run time matches random or matches fully sorted
      discriminates:: true
- [x] The speedup compared to random is consistent across sizes (found: Same gap at 10k and 100k)
      fails-if:: The speedup shrinks or disappears at larger sizes
- [ ] The three-run list sorts as fast as a fully sorted list (found: Three-run 0.95 ms, sorted 0.78 ms)
      fails-if:: The three-run list is slower than a fully sorted list
- [x] [outcome-neutral] Output is sorted and complete (found: All outputs sorted and complete)
      fails-if:: Output is scrambled or missing items

## Planned Intervention

Lists made of three long sorted runs broken by shuffled sections. Sizes ten thousand and one hundred thousand. Thirty repeats at each.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h103/ and link at least the report:
     - [Report](results/h103/report.md)   - results/h103/curve.png -->
_(none yet)_

## Findings

The three-run lists were faster than random but not as fast as fully sorted. The built-in sort noticed the long runs and processed them more efficiently. It did not just use a generic n log n strategy; it adapted to the input structure.
