---
id: h45
type: idea
schema: 2
title: The built-in sort doubles a little more than twice
parent: q15
status: running
rule: all
measurement: Ratio of built-in sort time at size 2n to time at n
replicates: 30 repeats at each of 11 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:06:51"
null_approved: "2026-08-16T16:06:34"
null_hash: ab5598127c7264a7
lock: 6db797735de44218
locked: "2026-08-16T16:06:51"
lock_at: running
---

# h45 — The built-in sort doubles a little more than twice

Parent:: [[q15_if_i_double_the_list_does_the_time_doubl]]

## ELI5

The built-in sort time increases by a bit more than double when size doubles.

## TL;DR

The built-in sort scaled better than my manual sorts but not as fast as linear. Doubling the list increased time by a factor between two and three, typical of n log n algorithms.

Background:: [[wiki/big-o-notation]]

## Null
capacity - a warm machine or background processes could mask real scaling

## Problem Statement

The built-in sort dominated all my hand-written sorts. I wanted to understand its scaling to see if it was truly log-linear or something else.

## Idea / Hypothesis

The built-in sort doubles a little more than twice

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Every doubling raises the built-in sort's time by a factor between two and three
      fails-if:: Any doubling raises the time by a factor outside two to three
      discriminates:: true
- [ ] The doubling factor stays flat rather than climbing as the list grows
      fails-if:: The doubling factor climbs steadily as the list grows
- [ ] [outcome-neutral] The built-in sort returns a correctly ordered list at every size
      fails-if:: The built-in sort returns a list that is not in order

## Planned Intervention

Built-in sort on lists from one thousand to one million items, doubling at each step. Thirty repeats at each size. Counter clock, first run out.

## Run Links

- SortLab notebook, week 7

## Artifacts

<!-- what the run produced. Keep files under results/h45/ and link at least the report:
     - [Report](results/h45/report.md)   - results/h45/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
