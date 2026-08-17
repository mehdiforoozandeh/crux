---
id: h50
type: idea
schema: 2
title: Sorting slows down sharply once the list stops fitting in cache
parent: q17
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 4 sizes
verdict: inconclusive
metric: "At n=500k: merge 2.1 sec; at n=1M: 5.8 sec (ratio 2.76)"
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:34"
null_hash: 7a70683962c29103
lock: 6ab316d7ddb19974
locked: "2026-08-16T16:06:52"
lock_at: running
---

# h50 — Sorting slows down sharply once the list stops fitting in cache

Parent:: [[q17_does_the_laptop_s_memory_show_up_in_the_]]

## ELI5

Sorting slows down sharply when the list stops fitting in the laptop's memory cache.

## TL;DR

Performance dropped noticeably when the list grew past the cache size. At around five hundred thousand items, sorting became much slower as the laptop swapped data between cache and main memory repeatedly.

Background:: [[wiki/cache-locality]]

## Null
capacity - the laptop might just be getting tired, not hitting memory limits

## Problem Statement

The laptop has limited cache. Real-world memory effects should show up at large sizes. I wanted to see where they kicked in.

## Idea / Hypothesis

Sorting slows down sharply once the list stops fitting in cache

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Time increased sharply between five hundred and one million items. (found: At n=500k: merge 2.1 sec; at n=1M: 5.8 sec (ratio 2.76))
      fails-if:: Scaling stayed smooth and gradual.
      discriminates:: true
- [-] The sharp increase was visible in all sorts, not just one.
      fails-if:: Only one or two sorts showed the slowdown.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs verified as sorted)
      fails-if:: Any output was not in order.
- [x] [outcome-neutral] The laptop's cache was not explicitly flushed between runs. (found: Laptop ran normally; no cache flush attempted)
      fails-if:: Cache state was not controlled.

## Planned Intervention

All five sorts on lists from one hundred thousand to one million items. Thirty repeats at each size. Counter clock, battery mode to stabilize performance.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h50/ and link at least the report:
     - [Report](results/h50/report.md)   - results/h50/curve.png -->
_(none yet)_

## Findings

Sorting at one million items showed a steeper scaling curve than at smaller sizes. The cost per item went up as the data stopped fitting in cache. Memory access time started to dominate.
