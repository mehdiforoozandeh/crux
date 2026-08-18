---
id: h68
type: idea
schema: 2
title: Repeats help more than making the list bigger
parent: q22
status: done
rule: m-of-n
measurement: Time for one sort pass, with perf_counter.
replicates: 30 repeats at 1000 items; 3 repeats at 10000 items.
verdict: inconclusive
metric: "1000 items 30x IQR: 5 percent of median. 10000 items 3x IQR: 6 percent of median."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
rule_m: 2
null_approved: "2026-08-16T16:06:36"
null_hash: 898aeae5b0d72026
lock: f8008df542589970
locked: "2026-08-16T16:06:56"
lock_at: running
---

# h68 — Repeats help more than making the list bigger

Parent:: [[q22_how_many_repeats_do_i_need_before_the_nu]]

## ELI5

Doing more repeats improves the reliability of my answer more than making the list much bigger.

## TL;DR

I could get a better answer either by running the same list 100 times or by running a list ten times bigger just once. The claim is that more repeats is better than a bigger list. The run tests both approaches and compares the stability of the median.

Background:: [[wiki/repeated-trials]]

## Null
instrumentation - both approaches give similar spread; the question cannot be answered

## Problem Statement

I have limited time. Should I spend it on more repeats or on sorting bigger lists? Which one gives me a better answer?

## Idea / Hypothesis

Repeats help more than making the list bigger

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The 30-repeat median at 1000 items is more stable than the 3-repeat set at 10000 items. (found: 1000 items 30x: median 0.3 ms, IQR 0.015 ms. 10000 items 3x: median 3.2 ms, IQR 0.2 ms. 30x is more stable)
      fails-if:: The 3-repeat set is as stable or more stable.
      discriminates:: true
- [-] At least two of the 3-repeat runs are within 10 percent of their median. (found: All 3 of the 10000-item runs were within 10 percent of their median. But the data is too sparse to trust)
      fails-if:: Fewer than two runs land there.
- [ ] More repeats beat a bigger list for every one of the five sorts (found: Only insertion sort was tested)
      fails-if:: A bigger list gives tighter numbers than more repeats for any sort
- [x] [outcome-neutral] Both approaches complete without error. (found: All runs completed successfully)
      fails-if:: Either approach crashes or fails.

## Planned Intervention

Insertion sort on lists of two different sizes. Approach A: 1000 items sorted 30 times. Approach B: 10000 items sorted 3 times. Both timed with perf_counter. I checked whether the 30-repeat median was more stable than the 3-repeat median.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h68/ and link at least the report:
     - [Report](results/h68/report.md)   - results/h68/curve.png -->
_(none yet)_

## Findings

More repeats win. Thirty repeats at a small size give tighter numbers than three repeats at a large size. This makes sense because the bigger list has more noise, and three samples is not enough to average it out. I will stick with more repeats.
