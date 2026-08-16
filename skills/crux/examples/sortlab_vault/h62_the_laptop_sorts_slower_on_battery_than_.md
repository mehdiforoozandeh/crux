---
id: h62
type: idea
schema: 2
title: The laptop sorts slower on battery than plugged in
parent: q21
status: done
rule: m-of-n
measurement: Time for one sort pass on 10000 items, with perf_counter.
replicates: 20 repeats plugged in, 20 repeats on battery.
verdict: supported
metric: "Plugged in: 8.7 ms. Battery: 9.6 ms. Ratio: 1.10x slower on battery."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
rule_m: 2
null_approved: "2026-08-16T16:06:36"
null_hash: 577ccc5810693ece
lock: 6aed5b6dfa1b3583
locked: "2026-08-16T16:06:54"
lock_at: running
---

# h62 — The laptop sorts slower on battery than plugged in

Parent:: [[q21_does_running_on_battery_change_the_numbe]]

## ELI5

My laptop sorts slower when it is running on battery than when it is plugged in.

## TL;DR

Laptops save power on batteries by slowing the CPU. If the built-in power-saver kicks in, sorts will be slower. The run times sorts plugged in and on battery, and checks if battery is slower. Since different things affect different runs, the verdict is true if at least two of the test conditions show the difference.

Background:: [[wiki/power-management]]

## Null
instrumentation - power mode switching caused a stall or lag, not a real speed difference

## Problem Statement

I do most of my timing work on battery power. But if the laptop is actually slower on battery, all my numbers are wrong. I need to know if battery power changes the result.

## Idea / Hypothesis

The laptop sorts slower on battery than plugged in

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Median time on battery is at least ten percent slower than plugged in. (found: Plugged in: 8.7 ms median. Battery: 9.6 ms median. Difference: 10.3 percent)
      fails-if:: Battery time is less than ten percent slower.
      discriminates:: true
- [x] The spread of times is larger on battery than plugged in. (found: Plugged in: 7.8 to 9.1 ms. Battery: 8.4 to 11.2 ms. Battery has wider range)
      fails-if:: Plugged in has more spread than battery.
- [ ] The battery penalty is bigger on the longer sorts than on the short ones (found: Same ten percent at every size)
      fails-if:: The battery penalty is the same share of time at every size
- [x] [outcome-neutral] The same shuffled list is sorted each time. (found: Verified: same random list in both blocks)
      fails-if:: Lists differ or get accidentally pre-sorted.

## Planned Intervention

Insertion sort on 10000 random items. Twenty repeats plugged in with performance mode on, then twenty repeats on battery with default power settings. Both used perf_counter. Same laptop temperature for both blocks.

## Run Links

- SortLab notebook, week 4

## Artifacts

- [Report](results/h62/report.md)

## Findings

Battery power is definitely slower. The sort is 10 percent slower on battery. The times are also more spread out on battery, which suggests the CPU is throttling to save power. I will need to control for this.
