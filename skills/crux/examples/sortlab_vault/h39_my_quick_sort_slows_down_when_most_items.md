---
id: h39
type: idea
schema: 2
title: My quick sort slows down when most items are equal
parent: q14
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Random 0.46 ms, duplicate-heavy 0.71 ms at n=10000
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:33"
null_hash: 412880b936ba2368
lock: 65c191da69617dfa
locked: "2026-08-16T16:06:50"
lock_at: running
---

# h39 — My quick sort slows down when most items are equal

Parent:: [[q14_what_happens_when_the_list_is_mostly_the]]

## ELI5

Quick sort slows down when most items are the same value.

## TL;DR

Quick sort was much slower on lists with many duplicates. The algorithm's partitioning created unbalanced splits when most items were equal, making it quadratic instead of log-linear.

Background:: [[wiki/three-way-partition]]

## Null
selection - my duplicate-heavy shape happens to be the one pivot choice hates

## Problem Statement

Quick sort can degrade to quadratic time when the pivot does a bad job of splitting. Duplicate values should make pivots do badly.

## Idea / Hypothesis

My quick sort slows down when most items are equal

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Duplicate-heavy was at least thirty percent slower than random. (found: Random 0.46 ms, duplicate-heavy 0.71 ms at n=10000)
      fails-if:: Duplicate-heavy was faster or equal to random.
      discriminates:: true
- [x] Duplicate-heavy showed worse scaling than random as size doubled.
      fails-if:: Both lists showed the same scaling ratio.
- [x] [outcome-neutral] Both outputs were correctly sorted. (found: Both outputs verified as sorted)
      fails-if:: Either output was not in order.

## Planned Intervention

Quick sort on random and duplicate-heavy lists where thirty percent of items have the same value. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h39/ and link at least the report:
     - [Report](results/h39/report.md)   - results/h39/curve.png -->
_(none yet)_

## Findings

Quick sort was slower on duplicate-heavy lists. The pivot often chose a value that appeared many times, creating unbalanced splits. The algorithm had to do more work than on random input.
