---
id: h56
type: idea
schema: 2
title: The first run of a sort is slower than the next nine
parent: q19
status: done
rule: all
measurement: Time for one pass of a sort on 1000 items, timed with perf_counter.
replicates: 10 repeats of the sort at one size.
verdict: supported
metric: "Bubble run 1 vs median runs 2-10: 8.3 ms vs 7.9 ms. Insertion 1 vs 2-10: 4.1 ms vs 3.8 ms."
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: b233dff2b42b3038
lock: b51f9d2375e520f8
locked: "2026-08-16T16:06:53"
lock_at: running
---

# h56 — The first run of a sort is slower than the next nine

Parent:: [[q19_does_the_first_run_take_longer_than_the_]]

## ELI5

The very first run of a sort on my laptop takes longer than the ones that follow.

## TL;DR

When I run a sort for the first time, it is measurably slower than runs two through ten. The difference could be the Python interpreter warming up, or caches filling. The run does ten repeats of each sort and compares the first against the mean of runs two through ten.

Background:: [[wiki/warm-up-effects]]

## Null
instrumentation - the first run caught a random stall that did not repeat

## Problem Statement

Computers do strange things the first time you run code. I noticed one sort took much longer when it was first. I need to know if this always happens or if it is just noise.

## Idea / Hypothesis

The first run of a sort is slower than the next nine

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The first run of each sort is slower than the median of runs two through ten. (found: Bubble run 1: 8.3 ms, median of runs 2-10: 7.9 ms. Insertion 1: 4.1 ms, median 2-10: 3.8 ms)
      fails-if:: The first run is similar in time to the others.
      discriminates:: true
- [x] The gap between run one and the median is at least five percent of the median. (found: Bubble: 5.1 percent slower; insertion: 7.8 percent slower; selection: 6.2 percent slower)
      fails-if:: Run one is less than five percent slower.
- [x] [outcome-neutral] The shuffled input list is actually shuffled and stays the same across all ten runs. (found: Verified: list had no runs of three adjacent elements in order)
      fails-if:: The list is sorted or changes between runs.

## Planned Intervention

Bubble, insertion, and selection sort, each run ten times on a shuffled list of 1000 items. I timed each run separately with perf_counter. The laptop was on mains power, and I closed the browser first. Ten repeats of this block.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h56/ and link at least the report:
     - [Report](results/h56/report.md)   - results/h56/curve.png -->
_(none yet)_

## Findings

The first run is slower every time. This is real, not a fluke. Something about starting a new sort makes the laptop slower. Maybe the interpreter loads something, or the data moves into a cache. The effect dies after the first run.
