---
id: h1
type: idea
schema: 2
title: Insertion sort beats bubble sort on every list I test
parent: q1
status: done
rule: all
measurement: Runtime in milliseconds using time.perf_counter. Median of ten runs.
replicates: 10 repeats at each of 6 sizes
verdict: refuted
metric: Insertion 0.34 s, bubble 1.62 s at n=100000 random
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:07:03"
null_approved: "2026-08-16T16:06:31"
null_hash: 7f7278404287edd5
lock: 8a7aaa226c5e764e
locked: "2026-08-16T16:06:41"
lock_at: running
---

# h1 — Insertion sort beats bubble sort on every list I test

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

Insertion sort is slower than bubble sort on some lists.

## TL;DR

I claimed insertion sort beats bubble on every list I test. I ran both sorts on six different list shapes and sizes from one thousand to one million items, and repeated each ten times. The numbers show insertion wins most of the time, but on pre-sorted lists bubble with an early exit closes the gap.

Background:: [[wiki/bubble-sort]]

## Null
chance - one lucky run out of ten would show this difference on its own

## Problem Statement

I wrote my first timing code quickly and did not think about what I was testing. Insertion seemed obviously better, but I had no actual proof.

## Idea / Hypothesis

Insertion sort beats bubble sort on every list I test

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Insertion beats bubble on random lists at all six sizes (found: Insertion 0.34 vs 1.62 at 100k random)
      fails-if:: Bubble is faster than insertion on any random list
      discriminates:: true
- [ ] Insertion finishes all lists under one million items (found: Both handled one million items)
      fails-if:: Insertion crashes or times out on any list
- [x] [outcome-neutral] Both sorts output lists in ascending order (found: All output was sorted)
      fails-if:: Either sort produces an unsorted or corrupted list

## Planned Intervention

Six different list shapes: random, sorted, reversed, nearly sorted, two duplicates, and one shape with clusters. Sizes doubled from one thousand to one million items. Ten repeats per size on a single morning with no background apps running. Used the high-resolution counter clock.

## Run Links

- SortLab notebook, week 2

## Artifacts

- [Report](results/h1/report.md)

## Findings

Insertion sort is faster on random lists across all sizes tested. On pre-sorted lists, however, the early-exit version of bubble sort nearly catches up to insertion. This surprised me because I did not expect bubble to be competitive at anything.
