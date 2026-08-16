---
id: h18
type: idea
schema: 2
title: Bubble sort is the slowest of the three at every size
parent: q8
status: done
rule: all
measurement: Median time in milliseconds.
replicates: 30 repeats at each of 6 shapes at 5 sizes
verdict: refuted
metric: "Bubble vs insertion: 1.62 s vs 0.34 s at 100k random. Bubble vs selection: 1.62 s vs 0.91 s."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: 912718fb72e79867
locked: "2026-08-16T16:06:45"
lock_at: running
---

# h18 — Bubble sort is the slowest of the three at every size

Parent:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## ELI5

Bubble sort is the slowest of the three at every size.

## TL;DR

I claimed bubble sort is always the slowest among bubble, insertion, and selection at every size I tested. I measured all three on the same six sizes and six shapes. The data shows bubble is slow, but not always the absolute slowest.

Background:: [[wiki/bubble-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

Bubble sort has a bad reputation. I wanted to confirm it is actually the worst of the three, but I was starting to suspect the early exit made it faster on some inputs.

## Idea / Hypothesis

Bubble sort is the slowest of the three at every size

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Bubble is slower than insertion on all six shapes (found: Bubble slowest vs insertion always)
      fails-if:: Insertion is slower than bubble on any shape
      discriminates:: true
- [ ] Bubble is slower than selection on at least four shapes (found: Bubble slower than selection on 5 of 6)
      fails-if:: Selection is slower on more than one shape
- [x] [outcome-neutral] Bubble sort terminates within five seconds on all tests (found: All within time limit)
      fails-if:: Bubble sort times out or takes more than ten seconds

## Planned Intervention

Six shapes and five sizes, same as the insertion sort test. Thirty repeats per configuration. Same morning session.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h18/ and link at least the report:
     - [Report](results/h18/report.md)   - results/h18/curve.png -->
_(none yet)_

## Findings

Bubble is slower than insertion on every shape tested. But on sorted lists, bubble with the early exit becomes competitive with selection. It is not always the absolute slowest, but it is consistently in last place on random and nearly random lists.
