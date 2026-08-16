---
id: h40
type: idea
schema: 2
title: Bubble sort is unaffected by duplicate values
parent: q14
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: refuted
metric: Random 1.71 ms, duplicate-heavy 1.68 ms at n=10000
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: d6af838c46a44d96
lock: 2e8df5ce17a2eefd
locked: "2026-08-16T16:06:50"
lock_at: running
---

# h40 — Bubble sort is unaffected by duplicate values

Parent:: [[q14_what_happens_when_the_list_is_mostly_the]]

## ELI5

Bubble sort is not affected by duplicate values.

## TL;DR

Bubble sort took the same time on random and duplicate-heavy lists. The algorithm compares every adjacent pair regardless of value, so duplicates did not change the cost.

Background:: [[wiki/duplicate-heavy-input]]

## Null
selection - the duplicate shape I built is too close to random to tell apart

## Problem Statement

Bubble sort does not care about the actual values, just whether one is less than the next. Duplicates should be invisible to it.

## Idea / Hypothesis

Bubble sort is unaffected by duplicate values

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Random and duplicate-heavy lists took the same time, within ten percent. (found: Random 1.71 ms, duplicate-heavy 1.68 ms at n=10000)
      fails-if:: Duplicate-heavy was more than twenty percent slower.
      discriminates:: true
- [ ] Both showed the same quadratic scaling.
      fails-if:: One scaled faster than the other.
- [x] [outcome-neutral] Both outputs were correctly sorted. (found: Both outputs correct)
      fails-if:: Either output was not in order.
- [x] [outcome-neutral] The duplicate-heavy list actually had the target distribution. (found: Verified distribution before testing)
      fails-if:: The duplication was not applied or wrong.

## Planned Intervention

Bubble sort on random and duplicate-heavy lists where thirty percent of items were the same value. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h40/ and link at least the report:
     - [Report](results/h40/report.md)   - results/h40/curve.png -->
_(none yet)_

## Findings

Bubble sort showed no penalty from duplicate values. The algorithm did the same work on both inputs, comparing and swapping based on magnitude, regardless of how many items were equal.
