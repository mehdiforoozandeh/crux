---
id: h79
type: idea
schema: 2
title: A bucket sort beats the built-in sort on evenly spread numbers
parent: q25
status: running
rule: m-of-n
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats of each (planned).
verdict: 
metric: 
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:06:58"
rule_m: 2
null_approved: "2026-08-16T16:06:37"
null_hash: 057d21f5aa2652da
lock: caf2751e28ae4b21
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h79 — A bucket sort beats the built-in sort on evenly spread numbers

Parent:: [[q25_can_i_beat_the_built_in_sort_on_any_list]]

## ELI5

A bucket sort could beat the built-in sort on numbers that are evenly spread across a range.

## TL;DR

Bucket sort distributes numbers into buckets, then sorts each bucket. On evenly spread data, buckets have few items and the sort is very fast. The run tests bucket sort against the built-in on uniformly distributed numbers.

Background:: [[wiki/radix-sort]]

## Null
capacity - bucket sort does the same work regardless of distribution

## Problem Statement

I have tried many sorts. Maybe bucket sort, which relies on distribution, can win on a special kind of data. I am about to test this.

## Idea / Hypothesis

A bucket sort beats the built-in sort on evenly spread numbers

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Bucket sort is faster than the built-in sort on one hundred thousand evenly spread numbers
      fails-if:: The built-in sort is faster on evenly spread numbers
      discriminates:: true
- [ ] Bucket sort's lead holds at every size from ten thousand upward
      fails-if:: Bucket sort loses its lead at any size from ten thousand upward
- [ ] Bucket sort loses to the built-in sort on clustered numbers
      fails-if:: Bucket sort also wins on clustered numbers
- [ ] [outcome-neutral] Both sorts return the same ordered list from the same input
      fails-if:: The two sorts return different orderings of the same input

## Planned Intervention

Bucket sort and built-in sort on 100000 numbers uniformly distributed in range 0 to 100000. I have not run this yet. I plan to do ten repeats of each.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h79/ and link at least the report:
     - [Report](results/h79/report.md)   - results/h79/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
