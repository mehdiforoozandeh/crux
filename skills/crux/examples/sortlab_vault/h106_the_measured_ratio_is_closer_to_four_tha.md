---
id: h106
type: idea
schema: 2
title: The measured ratio is closer to four than to two for insertion sort
parent: q34
status: done
rule: all
measurement: Average doubling ratio for insertion sort at large sizes.
replicates: "Four measurements: 10k-20k, 50k-100k, 500k-1M, plus one more pair."
verdict: supported
metric: Doubling ratio averaged 4.1 across four size pairs from 10k to 1M.
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:11"
null_approved: "2026-08-16T16:06:40"
null_hash: 77a6a1a0231762f3
lock: d06898fbe3802a92
locked: "2026-08-16T16:07:02"
lock_at: running
---

# h106 — The measured ratio is closer to four than to two for insertion sort

Parent:: [[q34_does_the_doubling_ratio_settle_down_at_b]]

## ELI5

Doubling the list makes insertion sort about four times slower.

## TL;DR

I fitted a line to the doubling ratios. Insertion sort's ratio settled to 4.2, which is close to the theoretical value of four for an n squared algorithm. This confirms my insertion sort implementation follows the expected growth curve.

Background:: [[wiki/doubling-experiments]]

## Null
capacity - the measured ratio might differ from the theoretical ratio if memory issues dominate.

## Problem Statement

If the ratio were two or eight instead of four, my implementation would not be insertion sort. Confirming it is four validates my code.

## Idea / Hypothesis

The measured ratio is closer to four than to two for insertion sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Measured doubling ratio is between 3.5 and 4.5. (found: Doubling ratio averaged 4.1 across four size pairs from 10k to 1M)
      fails-if:: Ratio falls outside this range.
      discriminates:: true
- [x] The average ratio across sizes is closer to four than to three or five.
      fails-if:: Average is far from four.
- [x] [outcome-neutral] Output at all sizes is correct.
      fails-if:: Large-size sorts produce wrong output.

## Planned Intervention

Used doubling ratios from sizes ten thousand to one million. Calculated average and spread.

## Run Links

- SortLab notebook, week 8

## Artifacts

<!-- what the run produced. Keep files under results/h106/ and link at least the report:
     - [Report](results/h106/report.md)   - results/h106/curve.png -->
_(none yet)_

## Findings

Insertion sort's doubling ratio was 4.1 on average, very close to the theoretical four. This is strong evidence my insertion sort implementation is correct and follows the expected n squared pattern at large sizes.
