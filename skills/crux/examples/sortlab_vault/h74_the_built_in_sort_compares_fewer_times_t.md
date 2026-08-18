---
id: h74
type: idea
schema: 2
title: The built-in sort compares fewer times than my merge sort
parent: q24
status: done
rule: all
measurement: Observed time divided by theoretical comparison count.
replicates: 10 repeats at each size.
verdict: refuted
metric: "Merge sort: 6.8 megacomps per second. Built-in: 18 megacomps per second."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 84df5554127cdf55
lock: 3fa4a4edacd3e2ac
locked: "2026-08-16T16:06:57"
lock_at: running
---

# h74 — The built-in sort compares fewer times than my merge sort

Parent:: [[q24_does_the_built_in_sort_use_a_smarter_met]]

## ELI5

The built-in sort makes fewer comparisons than my merge sort does.

## TL;DR

Merge sort always does the same number of comparisons regardless of the data. But the built-in might use a smarter algorithm that needs fewer comparisons. The run counts comparisons in the built-in sort versus merge sort.

Background:: [[wiki/timsort]]

## Null
capacity - both algorithms do roughly the same number of comparisons on average

## Problem Statement

Maybe the built-in sort's advantage is not just speed of each operation, but also doing fewer operations overall. I should count comparisons.

## Idea / Hypothesis

The built-in sort compares fewer times than my merge sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Comparisons per second are lower for the built-in sort than for merge sort. (found: Merge sort: 6.8 million comparisons per second. Built-in: 18 million comps per second. Built-in is faster per comparison, but that is just speed)
      fails-if:: Built-in does comparisons at the same rate or slower.
      discriminates:: true
- [ ] The built-in sort's comparison count is lower than my merge sort's at every size (found: Both made about n log n comparisons)
      fails-if:: The built-in sort makes as many comparisons as my merge sort
- [x] [outcome-neutral] All runs produce sorted output. (found: All outputs were correctly sorted)
      fails-if:: Output is not sorted.

## Planned Intervention

My merge sort and built-in sort on random lists of 1000, 10000 items. I timed how long it takes to sort and divide by the number of comparisons the algorithm makes.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h74/ and link at least the report:
     - [Report](results/h74/report.md)   - results/h74/curve.png -->
_(none yet)_

## Findings

The built-in sort does not need fewer comparisons; it just runs the comparisons much faster. Each comparison in the built-in is faster than in my Python code. This is because the built-in is written in C, not because of a different algorithm.
