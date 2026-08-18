---
id: h7
type: idea
schema: 2
title: Doubling the list never more than quadruples the time
parent: q3
status: idea
rule: all
measurement: Ratio of time at size n versus time at size n divided by 2.
replicates: 10 repeats at each of 5 pairs of sizes
verdict: 
metric: 
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:06:22"
---

# h7 — Doubling the list never more than quadruples the time

Parent:: [[q3_how_does_the_time_grow_when_the_list_get]]

## ELI5

Doubling the list never more than quadruples the time.

## TL;DR

I want to test whether the slowdown from the three slow sorts caps out at roughly four times when you double the list size. If I find cases where doubling produces more than a 4.5 times slowdown, that means something unexpected is happening, like cache misses or memory swapping.

Background:: [[wiki/growth-rate-curves]]

## Null
capacity - the faster machine state, not the algorithm, explains the whole gap

## Problem Statement

My current theory is that doubling produces at most a quadruple slowdown for O of n squared algorithms. If that holds on my laptop even at the biggest sizes, it gives me a bound on performance.

## Idea / Hypothesis

Doubling the list never more than quadruples the time

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Every doubling of the list raises the time by at most four and a half times
      fails-if:: Any doubling raises the time by more than four and a half times
      discriminates:: true
- [ ] The quiet machine and the busy machine give the same doubling ratio
      fails-if:: The busy machine gives a doubling ratio more than half a step higher
- [ ] [outcome-neutral] Each sort returns a correctly ordered list at every size in the ladder
      fails-if:: A sort returns an unordered list at any size in the ladder

## Planned Intervention

Sizes from ten thousand up to five hundred thousand, doubling each step. Five consecutive doublings. Two different machine states: quiet and with one background video call. Ten repeats per size per state.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h7/ and link at least the report:
     - [Report](results/h7/report.md)   - results/h7/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
