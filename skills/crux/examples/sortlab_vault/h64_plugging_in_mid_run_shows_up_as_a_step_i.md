---
id: h64
type: idea
schema: 2
title: Plugging in mid-run shows up as a step in the numbers
parent: q21
status: done
rule: all
measurement: Time for one sort pass, with perf_counter.
replicates: 10 repeats on battery, then 10 with power plugged in mid-block.
verdict: invalid-run
metric: Cannot compute; run was void.
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: 8a5933464ad33690
lock: 025f3895f6f64000
locked: "2026-08-16T16:06:55"
lock_at: running
---

# h64 — Plugging in mid-run shows up as a step in the numbers

Parent:: [[q21_does_running_on_battery_change_the_numbe]]

## ELI5

Plugging the laptop in during a timing run causes a sudden jump in speed halfway through.

## TL;DR

If the power adapter connects while a sort is running, the CPU might speed up right away. That would show up as a jump in time: one cluster of slow runs, then suddenly a cluster of fast runs. The run tries to capture this by plugging in mid-way through a block of repeats.

Background:: [[wiki/power-management]]

## Null
instrumentation - the power change is too slow to show up mid-run

## Problem Statement

I am worried about power state changes breaking my measurements. What happens if I accidentally plug in during a run? Does it show up as a glitch?

## Idea / Hypothesis

Plugging in mid-run shows up as a step in the numbers

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Runs one through ten on battery are slower than runs eleven through twenty on mains (found: Battery 9.6 ms, mains 8.7 ms before the crash)
      fails-if:: The two blocks have similar times
      discriminates:: true
- [ ] The step between the two blocks lands exactly at run eleven (found: Crash cut the block at run nine)
      fails-if:: The times drift gradually instead of stepping at run eleven
- [ ] [outcome-neutral] Each run completes and produces a valid sorted list. (found: The sort crashed when I plugged in the adapter. Run is void)
      fails-if:: The sort aborts, hangs, or produces invalid output.

## Planned Intervention

Insertion sort on 10000 items, run 20 times on battery. Midway through (after ten runs) I plugged in the power adapter. I timed each run separately with perf_counter.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h64/ and link at least the report:
     - [Report](results/h64/report.md)   - results/h64/curve.png -->
_(none yet)_

## Findings

The experiment failed. Plugging in the power adapter during a run crashed the sort. The laptop did not handle the power state change gracefully. This run taught me nothing about the effect but showed me not to plug in during a timing run.
