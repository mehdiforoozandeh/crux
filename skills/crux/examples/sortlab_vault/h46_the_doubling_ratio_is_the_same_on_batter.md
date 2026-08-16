---
id: h46
type: idea
schema: 2
title: The doubling ratio is the same on battery and plugged in
parent: q15
status: staged
rule: all
measurement: Doubling ratio for each sort on battery and on mains power
replicates: 20 repeats at each of 4 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:06:51"
null_approved: "2026-08-16T16:06:34"
null_hash: 6ae342de888b76ec
---

# h46 — The doubling ratio is the same on battery and plugged in

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

The doubling ratio does not change whether the laptop is running on battery or plugged in.

## TL;DR

I wanted to test whether the laptop's power mode affected the scaling ratio. Doubling ratio should be the same whether on battery or AC power.

Background:: [[wiki/doubling-experiments]]

## Null
capacity - machine state change, not the algorithm, explains any difference

## Problem Statement

Battery mode can throttle the CPU. If that happened, it should affect timing but not the scaling ratio. I wanted to verify both inputs showed the same doubling pattern.

## Idea / Hypothesis

The doubling ratio is the same on battery and plugged in

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Each sort's doubling ratio on battery is within five percent of its ratio on mains
      fails-if:: A sort's doubling ratio on battery differs from mains by over five percent
      discriminates:: true
- [ ] The absolute times are slower on battery even though the ratio holds
      fails-if:: Battery and mains give the same absolute times as well as the same ratio
- [ ] [outcome-neutral] The laptop stays on the declared power source for every run in its block
      fails-if:: The power source changes part-way through a block of runs

## Planned Intervention

Run all five sorts on battery and plugged-in modes at a few sizes. Compare the doubling ratios between modes.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h46/ and link at least the report:
     - [Report](results/h46/report.md)   - results/h46/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
