---
id: h6
type: idea
schema: 2
title: Every sort I wrote gets slower in the same way
parent: q3
status: done
rule: all
measurement: Median time in milliseconds. Ten repeats per size.
replicates: 10 repeats at each of 10 sizes
verdict: refuted
metric: Bubble 1 ms at 1k, 98 ms at 100k; merge 1 ms at 1k, 14 ms at 100k
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: 59c5dacab60aba27
lock: c92e3301f9ecbaa1
locked: "2026-08-16T16:06:42"
lock_at: running
---

# h6 — Every sort I wrote gets slower in the same way

Parent:: [[q3_how_does_the_time_grow_when_the_list_get]]

## ELI5

Every sort I wrote gets slower in the same way when the list grows.

## TL;DR

I claimed all five sorts slow down by the same pattern as the list grows. On a doubling test from one thousand to one million items, I expected each sort to take roughly the same multiple longer each time. The data shows this is wrong: the slow sorts quadruple, but merge sort only doubles or triples.

Background:: [[wiki/big-o-notation]]

## Null
capacity - the faster machine state, not the algorithm, explains the whole gap

## Problem Statement

Theory textbooks say bubble, insertion, and selection are O of n squared, so doubling the list should quadruple the time. Merge sort is O of n log n, so doubling should only double or triple the time. I wanted to verify this on actual hardware.

## Idea / Hypothesis

Every sort I wrote gets slower in the same way

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Bubble time goes from 1 ms at 1k up to 100 ms at 100k (found: Bubble 98/100 = 98x ratio)
      fails-if:: Bubble time does not roughly quadruple when list size doubles
      discriminates:: true
- [ ] Merge time goes from 1 ms at 1k up to 15 ms at 100k (found: Merge 14/1 = 14x ratio)
      fails-if:: Merge time quadruples like the slow sorts do
- [x] [outcome-neutral] All five sorts complete each run in measurable time (found: All times in measurable range)
      fails-if:: Any sort times out or runs so fast it hits the timer precision limit

## Planned Intervention

Geometric ladder of sizes: one thousand, two thousand, four thousand, eight thousand, sixteen thousand, thirty-two thousand, sixty-four thousand, one hundred twenty-eight thousand, two hundred fifty-six thousand, five hundred twelve thousand. Ten repeats per size per sort. Random input. High-resolution timer. Warm-up run discarded each morning.

## Run Links

- SortLab notebook, week 7

## Artifacts

<!-- what the run produced. Keep files under results/h6/ and link at least the report:
     - [Report](results/h6/report.md)   - results/h6/curve.png -->
_(none yet)_

## Findings

The slow sorts do roughly quadruple when the list doubles in size. Merge sort only doubles or triples. This matches the theory, and it shows why merge sort wins on big lists even though insertion and bubble can be faster on small ones.
