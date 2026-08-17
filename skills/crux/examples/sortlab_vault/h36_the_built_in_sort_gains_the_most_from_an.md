---
id: h36
type: idea
schema: 2
title: The built-in sort gains the most from an almost-sorted list
parent: q13
status: done
rule: all
measurement: Time in milliseconds, counter clock, median of thirty repeats.
replicates: 30 repeats at each of 6 sizes
verdict: supported
metric: Random 0.031 ms, almost-sorted 0.009 ms at n=10000
created: "2026-08-16T16:06:25"
updated: "2026-08-16T16:07:06"
null_approved: "2026-08-16T16:06:33"
null_hash: ae3cbd009f92c9bf
lock: cbe30997a3f16d9c
locked: "2026-08-16T16:06:49"
lock_at: running
---

# h36 — The built-in sort gains the most from an almost-sorted list

Parent:: [[q13_what_happens_when_the_list_is_almost_sor]]

## ELI5

The built-in sort is fastest when the list is almost sorted.

## TL;DR

The built-in sort gained the biggest speed boost on almost-sorted lists. It detected runs of existing order and skipped work, making it much faster than on random lists.

Background:: [[wiki/nearly-sorted-input]]

## Null
selection - almost-sorted was built out of long runs the built-in sort already likes

## Problem Statement

The built-in sort was already so fast that I expected it to dominate all inputs. But I wanted to see if it could adapt even further on nearly sorted data.

## Idea / Hypothesis

The built-in sort gains the most from an almost-sorted list

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Almost-sorted was at least fifty percent faster than random. (found: Random 0.031 ms, almost-sorted 0.009 ms at n=10000)
      fails-if:: Almost-sorted was not significantly faster.
      discriminates:: true
- [x] Fully sorted was faster than almost-sorted.
      fails-if:: Almost-sorted and fully sorted took the same time.
- [x] [outcome-neutral] All outputs were sorted correctly. (found: All outputs correct and verified as sorted)
      fails-if:: Any output was not in order.

## Planned Intervention

Built-in sort on random, fully sorted, and almost-sorted lists of ten thousand items each. Thirty repeats from one thousand to one hundred thousand.

## Run Links

- SortLab notebook, week 6

## Artifacts

<!-- what the run produced. Keep files under results/h36/ and link at least the report:
     - [Report](results/h36/report.md)   - results/h36/curve.png -->
_(none yet)_

## Findings

The built-in sort gained the most from almost-sorted input. It detected runs and skipped work on sorted stretches, making it three times faster than on random lists. Existing order was a huge win for this algorithm.
