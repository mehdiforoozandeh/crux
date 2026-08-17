---
id: h63
type: idea
schema: 2
title: The battery gap is bigger when the battery is nearly empty
parent: q21
status: done
rule: all
measurement: Time for one sort pass, with perf_counter.
replicates: 8 repeats at full battery, 8 at half, 8 near empty.
verdict: inconclusive
metric: "Full: 8.8 ms. Half: 9.1 ms. Empty: 9.3 ms."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: 06ce2a3812071668
lock: 78cfe80ff69ad6d6
locked: "2026-08-16T16:06:55"
lock_at: running
---

# h63 — The battery gap is bigger when the battery is nearly empty

Parent:: [[q21_does_running_on_battery_change_the_numbe]]

## ELI5

The slowdown from battery power is even worse when the battery is almost empty.

## TL;DR

Laptops might cut power even more aggressively when the battery is low. The claim is that the battery-induced slowdown gets bigger as the battery gets closer to empty. The run times sorts at three battery levels: full, half, and nearly empty.

Background:: [[wiki/thermal-throttling]]

## Null
instrumentation - the battery level and sort speed are uncorrelated; any trend is random

## Problem Statement

Battery power is a problem. But maybe the problem gets worse as the battery drains. If so, I should do my timing when the battery is fresh.

## Idea / Hypothesis

The battery gap is bigger when the battery is nearly empty

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Median time near empty is slower than at full battery. (found: Full: 8.8 ms. Half: 9.1 ms. Empty: 9.3 ms. Trend present but small)
      fails-if:: Empty battery is not slower, or speeds up.
      discriminates:: true
- [-] The gap grows steadily as the battery drains, not just at the empty end (found: Only three levels; trend unreadable)
      fails-if:: The gap does not grow steadily as the battery drains
- [x] [outcome-neutral] Battery level is actually at the claimed points. (found: Timed battery drain and ran tests at the planned levels)
      fails-if:: Battery level drifts or does not match the test.

## Planned Intervention

Insertion sort on 10000 items, timed at three battery levels. Eight repeats at each level. Laptop in default power mode each time. I measured times with perf_counter.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h63/ and link at least the report:
     - [Report](results/h63/report.md)   - results/h63/curve.png -->
_(none yet)_

## Findings

There is a slight trend: the sort gets slower as the battery empties. But the differences are so small that I am not sure it is real. More data would be needed to be certain.
