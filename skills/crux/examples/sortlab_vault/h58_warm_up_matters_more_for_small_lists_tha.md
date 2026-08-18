---
id: h58
type: idea
schema: 2
title: Warm-up matters more for small lists than for big ones
parent: q19
status: done
rule: all
measurement: Time for one sort pass at each size, with perf_counter.
replicates: 10 repeats at each of 4 sizes.
verdict: inconclusive
metric: Warm-up at 50 items is 12 percent; at 10000 items is 3 percent.
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 5b6010a08cf0b3f2
lock: 848b5f7f1e62fb17
locked: "2026-08-16T16:06:53"
lock_at: running
---

# h58 — Warm-up matters more for small lists than for big ones

Parent:: [[q19_does_the_first_run_take_longer_than_the_]]

## ELI5

Warm-up is more noticeable when I sort a small list than when I sort a large one.

## TL;DR

If the laptop has to load code or fill caches, that overhead might matter more on a tiny list than on a huge one. The run times small and large lists and checks whether the percent difference between run one and runs two through ten is bigger for small lists.

Background:: [[wiki/warm-up-effects]]

## Null
instrumentation - the warm-up effect is the same fraction of time at all sizes, so it just looks different

## Problem Statement

Maybe on a really small list, run one is so fast that any overhead shows up as a huge percent jump. But on a big list, the sort itself takes so long that the overhead is lost in the noise.

## Idea / Hypothesis

Warm-up matters more for small lists than for big ones

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] At 50 items the warm-up is bigger than at 10000 items. (found: At 50 items: 12 percent slower; at 10000 items: 3 percent slower)
      fails-if:: The warm-up effect is the same percentage at small and large sizes.
      discriminates:: true
- [-] The warm-up penalty falls steadily as the list gets longer, across all six sizes (found: Middle sizes too noisy to call)
      fails-if:: The warm-up penalty does not fall steadily across the six sizes
- [x] [outcome-neutral] Larger lists take longer to sort than smaller ones. (found: 50 items: 0.3 ms median; 10000 items: 9.1 ms median)
      fails-if:: Time does not scale with list size.

## Planned Intervention

Bubble sort on lists of 50, 100, 1000, and 10000 items. Each size run 10 times. I measured the percent difference between run one and the median of runs two through ten. Same laptop state as before.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h58/ and link at least the report:
     - [Report](results/h58/report.md)   - results/h58/curve.png -->
_(none yet)_

## Findings

The warm-up does hurt more on small lists. But the data is too noisy to be sure. The effect is real at 50 items but almost invisible at 10000 items. This could be a real difference, or it could be that I need more runs to see a clear answer.
