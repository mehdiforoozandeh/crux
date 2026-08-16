---
id: h52
type: idea
schema: 2
title: Sorting a million items makes the laptop swap to disk
parent: q17
status: staged
rule: all
measurement: Median seconds per sort pass, plus peak memory and disk reads
replicates: 20 repeats at each of 5 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:06:52"
null_approved: "2026-08-16T16:06:35"
null_hash: 503a25bf5708e75b
---

# h52 — Sorting a million items makes the laptop swap to disk

Parent:: [[q17_does_the_laptop_s_memory_show_up_in_the_]]

## ELI5

Sorting a million items forces the laptop to use disk space for memory.

## TL;DR

At one million items, the laptop might have started swapping to disk. I designed the test to check if disk access showed up in the timings.

Background:: [[wiki/cache-locality]]

## Null
capacity - the laptop simply runs out of speed at that size, with no disk involved

## Problem Statement

The laptop has limited RAM. Very large lists might cause swapping to disk, which would be catastrophically slow. I wanted to test whether this happened.

## Idea / Hypothesis

Sorting a million items makes the laptop swap to disk

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Disk reads rise sharply at one million items while they stay near zero below that
      fails-if:: Disk reads stay near zero at one million items
      discriminates:: true
- [ ] The time per item jumps at the same size the disk reads jump
      fails-if:: The time per item climbs smoothly with no jump at that size
- [ ] [outcome-neutral] Every run returns a correctly ordered list of the right length
      fails-if:: A run returns a list of the wrong length or out of order

## Planned Intervention

Merge sort on lists from one hundred thousand to two million items. Watch memory use and disk activity while each run goes. Twenty repeats per size, mains power, nothing else open.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h52/ and link at least the report:
     - [Report](results/h52/report.md)   - results/h52/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
