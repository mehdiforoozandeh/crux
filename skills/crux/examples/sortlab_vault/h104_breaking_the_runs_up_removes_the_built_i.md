---
id: h104
type: idea
schema: 2
title: Breaking the runs up removes the built-in sort's advantage
parent: q33
status: done
rule: all
measurement: Median time for built-in sort on shuffled three-run lists.
replicates: 30 repeats at 100k items with broken run structure.
verdict: inconclusive
metric: "Three-run: 0.95 ms. Broken: 1.07 ms. Random: 1.09 ms."
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:40"
null_hash: 9fbdb4b7aedad70d
lock: f9a7024c7918dbc5
locked: "2026-08-16T16:07:02"
lock_at: running
---

# h104 — Breaking the runs up removes the built-in sort's advantage

Parent:: [[q33_does_the_built_in_sort_notice_runs_that_]]

## ELI5

Breaking up the sorted runs destroys the built-in sort's advantage.

## TL;DR

I took the three-run structure and shuffled it more, breaking the long sorted chunks into smaller pieces. I predicted this would remove the speedup because the algorithm could no longer use the run-detection optimization. The result was inconclusive; the time did fall but within the normal noise.

Background:: [[wiki/run-detection]]

## Null
capacity - the random shuffles did not actually break the pattern in memory.

## Problem Statement

If run detection is the key, I can predict when the built-in sort will speed up. Breaking the runs should hurt it. But my numbers were close enough to random-input times that I cannot be sure.

## Idea / Hypothesis

Breaking the runs up removes the built-in sort's advantage

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Broken-run time is closer to random-input time than to three-run time. (found: Three-run: 0.95 ms. Broken: 1.07 ms. Random: 1.09 ms)
      fails-if:: Broken-run time remains as fast as three-run time.
      discriminates:: true
- [-] At least two of three runs remain detectable after shuffling.
      fails-if:: The shuffling completely destroyed run structure.
- [x] [outcome-neutral] The sorted-then-shuffled list produces correct output.
      fails-if:: Output is incorrect.

## Planned Intervention

Started with three-run lists. Added random shuffles to break the runs every few items. Thirty repeats at one hundred thousand items.

## Run Links

- SortLab notebook, week 10

## Artifacts

<!-- what the run produced. Keep files under results/h104/ and link at least the report:
     - [Report](results/h104/report.md)   - results/h104/curve.png -->
_(none yet)_

## Findings

Breaking the runs increased the time slightly, from 0.95 to 1.07 milliseconds. But it did not reach the random-input time of 1.09. The effect was real but subtle, buried in the normal spread of timing noise.
