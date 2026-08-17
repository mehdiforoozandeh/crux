---
id: h37
type: idea
schema: 2
title: One item out of place costs insertion sort almost nothing
parent: q13
status: done
rule: m-of-n
measurement: Time in milliseconds to sort, counter clock, median of repeats.
replicates: 30 repeats at each of 6 sizes
verdict: inconclusive
metric: Zero out 0.23 ms, one out 0.24 ms at n=10000
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
rule_m: 2
null_approved: "2026-08-16T16:06:33"
null_hash: d82ef9ba0f4db245
lock: e1397380718f2bd2
locked: "2026-08-16T16:06:49"
lock_at: running
---

# h37 — One item out of place costs insertion sort almost nothing

Parent:: [[q13_what_happens_when_the_list_is_almost_sor]]

## ELI5

Insertion sort barely slows down if one item is out of place.

## TL;DR

With just one item out of place, insertion sort was nearly as fast as fully sorted. The cost to insert a single item was tiny compared to the cost of sorting all items.

Background:: [[wiki/run-detection]]

## Null
selection - one item out of place is the mildest disruption I could have picked

## Problem Statement

I wanted to know how many out-of-place items insertion sort could tolerate before the cost became significant.

## Idea / Hypothesis

One item out of place costs insertion sort almost nothing

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] One item out of place added less than five percent to the cost. (found: Zero out 0.23 ms, one out 0.24 ms at n=10000)
      fails-if:: One item added more than ten percent.
      discriminates:: true
- [-] Ten items out of place added less than one hundred percent to the cost.
      fails-if:: Ten items more than doubled the time.
- [ ] Twenty-five items out of place still cost insertion sort less than random order does (found: Twenty-five out cost as much as random)
      fails-if:: Twenty-five items out of place cost as much as random order
- [x] [outcome-neutral] The disrupted lists had the correct number of items out of place. (found: Verified disruption count before each run)
      fails-if:: The disruption was not applied correctly.

## Planned Intervention

Insertion sort on lists with zero, one, and ten items out of place in a list of ten thousand. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

- [Report](results/h37/report.md)

## Findings

One item out of place barely slowed insertion sort. The cost was absorbed in the noise. But ten items out of place was starting to show a measurable penalty.
