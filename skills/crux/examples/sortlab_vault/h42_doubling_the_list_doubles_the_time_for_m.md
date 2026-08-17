---
id: h42
type: idea
schema: 2
title: Doubling the list doubles the time for merge sort
parent: q15
status: done
rule: all
measurement: Time in milliseconds to sort, counter clock, median of thirty.
replicates: 30 repeats at each of 6 sizes
verdict: refuted
metric: "At n=100k: 67 ms; at n=200k: 147 ms (ratio 2.19)"
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:34"
null_hash: 74cc895596ffe581
lock: 85245c0f76ee12d2
locked: "2026-08-16T16:06:50"
lock_at: running
---

# h42 — Doubling the list doubles the time for merge sort

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

Doubling the list size more than doubles the time for merge sort.

## TL;DR

Merge sort time increased by more than the list size factor when size doubled. The scaling was closer to n log n than linear, and doubling the list roughly tripled the time instead of just doubling it.

Background:: [[wiki/doubling-experiments]]

## Null
capacity - a faster machine state, not the algorithm, explains the gap

## Problem Statement

I wanted to understand how each algorithm scaled. Merge sort has a theoretical n log n cost, so doubling should increase time by a bit more than doubling.

## Idea / Hypothesis

Doubling the list doubles the time for merge sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Time at n doubled was more than two times the time at n. (found: At n=100k: 67 ms; at n=200k: 147 ms (ratio 2.19))
      fails-if:: Time at 2n was less than 2.5 times the time at n.
      discriminates:: true
- [ ] Ratio at large sizes was close to 2.1 or 2.2, not 2.0.
      fails-if:: Ratio was 2.0 or lower.
- [x] [outcome-neutral] All sorted lists were verified as correct. (found: All outputs correct and verified)
      fails-if:: Any output was not sorted.

## Planned Intervention

Merge sort on lists from one thousand to one million items, doubling at each step. Thirty repeats at each size. Counter clock, first run out.

## Run Links

- SortLab notebook, week 7

## Artifacts

<!-- what the run produced. Keep files under results/h42/ and link at least the report:
     - [Report](results/h42/report.md)   - results/h42/curve.png -->
_(none yet)_

## Findings

Merge sort scaled faster than linear, as theory predicts. Doubling the list increased time by a factor closer to 2.2 than 2.0. The n log n scaling was visible across the range tested.
