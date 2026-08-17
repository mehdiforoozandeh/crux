---
id: h3
type: idea
schema: 2
title: My merge sort is the fastest thing I wrote
parent: q1
status: running
rule: all
measurement: Elapsed time in milliseconds. Median of thirty runs per size.
replicates: 30 repeats at each of 10 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:06:42"
null_approved: "2026-08-16T16:06:31"
null_hash: 1b53c973f9a296aa
lock: a4c439ec270e1435
locked: "2026-08-16T16:06:42"
lock_at: running
---

# h3 — My merge sort is the fastest thing I wrote

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

My merge sort is the fastest thing I wrote.

## TL;DR

I set out to test whether merge sort beats all the other four sorts I implemented. To settle this, I need to compare wall-clock times on ten different list sizes from one thousand to one million items, with thirty repeats per size. The test will run both hand-written sorts and the merge sort side by side on the same machine state.

Background:: [[wiki/bubble-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

Merge sort has a better big-O than the slow sorts. I want to know if this theoretical advantage shows up in real time on my school laptop.

## Idea / Hypothesis

My merge sort is the fastest thing I wrote

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Merge sort posts the lowest median of my five sorts at every size above ten thousand
      fails-if:: Another sort I wrote posts a lower median at any size above ten thousand
      discriminates:: true
- [ ] Merge sort's lead over insertion sort grows as the list gets longer
      fails-if:: The lead over insertion stays flat or shrinks as the list grows
- [ ] [outcome-neutral] Every sort returns the same items in order that it was given
      fails-if:: Any sort returns a list out of order or with items missing

## Planned Intervention

Ten sizes on a geometric ladder: one thousand, two thousand, five thousand, ten thousand, twenty thousand, fifty thousand, one hundred thousand, two hundred fifty thousand, five hundred thousand, one million. Thirty repeats per size. Random input lists. High-resolution timer. Warm-up run discarded.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h3/ and link at least the report:
     - [Report](results/h3/report.md)   - results/h3/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
