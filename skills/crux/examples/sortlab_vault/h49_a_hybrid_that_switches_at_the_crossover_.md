---
id: h49
type: idea
schema: 2
title: A hybrid that switches at the crossover beats both
parent: q16
status: staged
rule: m-of-n
measurement: Median milliseconds for one sort pass, hybrid against pure insertion and pure merge
replicates: 20 repeats at each of 8 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:06:51"
rule_m: 2
null_approved: "2026-08-16T16:06:34"
null_hash: 822cd5504971d8b0
---

# h49 — A hybrid that switches at the crossover beats both

Parent:: [[q16_where_does_merge_sort_overtake_insertion]]

## ELI5

A hybrid sort that switches between insertion and merge at the crossover beats both.

## TL;DR

A hybrid sort that used insertion for small lists and merged for large ones was faster than either pure algorithm on its whole range. Switching at the crossover point minimized the total time.

Background:: [[wiki/hybrid-sorts]]

## Null
capacity - the hybrid only wins because it ran on a quieter machine than the two pure sorts

## Problem Statement

Since the two sorts had different strengths at different sizes, a hybrid that picked the right one at each size should win overall.

## Idea / Hypothesis

A hybrid that switches at the crossover beats both

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The hybrid is fastest of the three at every size from one hundred to one million
      fails-if:: A pure sort beats the hybrid at any size in the range
      discriminates:: true
- [ ] The hybrid matches pure insertion below three thousand items
      fails-if:: The hybrid is slower than pure insertion below three thousand items
- [ ] The hybrid matches pure merge above three thousand items
      fails-if:: The hybrid is slower than pure merge above three thousand items
- [ ] [outcome-neutral] All three sorts return correctly ordered lists at every size
      fails-if:: Any of the three returns a list that is not in order

## Planned Intervention

Write a hybrid sort that picks insertion for n less than three thousand and merge for larger sizes. Race it against both pure versions on the full size range.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h49/ and link at least the report:
     - [Report](results/h49/report.md)   - results/h49/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
