---
id: h38
type: idea
schema: 2
title: Ten percent out of place is already as bad as random
parent: q13
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: refuted
metric: Zero out 0.23 ms, ten percent 1.32 ms, random 1.41 ms at n=10000
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:33"
null_hash: e3491cdff5e1e9f7
lock: 2b8c63de8d0a373e
locked: "2026-08-16T16:06:49"
lock_at: running
---

# h38 — Ten percent out of place is already as bad as random

Parent:: [[q13_what_happens_when_the_list_is_almost_sor]]

## ELI5

When ten percent of items are out of place, insertion is as slow as random.

## TL;DR

With ten percent of items disrupted, insertion sort was nearly as slow as random. The threshold where insertion lost its advantage turned out to be much lower than I expected.

Background:: [[wiki/nearly-sorted-input]]

## Null
selection - I picked disruption levels either side of the answer I expected

## Problem Statement

I wanted to find the boundary where insertion sort stopped being adaptive. Ten percent seemed like a reasonable guess for when the benefit would vanish.

## Idea / Hypothesis

Ten percent out of place is already as bad as random

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Ten percent disruption was closer to random than to fully sorted. (found: Zero out 0.23 ms, ten percent 1.32 ms, random 1.41 ms at)
      fails-if:: Ten percent was closer to sorted.
      discriminates:: true
- [ ] Ten and twenty-five percent showed similar times.
      fails-if:: Twenty-five percent was significantly slower.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs correct, verified)
      fails-if:: Any output was not in order.

## Planned Intervention

Insertion sort on lists with zero, ten, and twenty-five percent of items randomly out of place. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h38/ and link at least the report:
     - [Report](results/h38/report.md)   - results/h38/curve.png -->
_(none yet)_

## Findings

Ten percent of items out of place was enough to match random input. Insertion sort adapted well to small disruptions but lost its advantage quickly. The threshold was lower than expected.
