---
id: h71
type: idea
schema: 2
title: Most of my sort's time goes on comparing, not on moving
parent: q23
status: done
rule: all
measurement: Time per comparison and time per move, calculated by dividing total time by operation count.
replicates: 10 repeats of each sort.
verdict: refuted
metric: "Insertion comparison time: 0.41 microsec. Move time: 0.08 microsec."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: a48fa22d81ba81ba
lock: 057b14fe9e54f678
locked: "2026-08-16T16:06:57"
lock_at: running
---

# h71 — Most of my sort's time goes on comparing, not on moving

Parent:: [[q23_is_the_built_in_sort_written_in_a_faster]]

## ELI5

Comparing two numbers takes much more time than moving a number from one place to another in my sorts.

## TL;DR

A comparison in Python might involve function calls and type checking. A move is just a simple assignment. The claim is that most of my sort's time goes into comparisons, not moves. The run instruments the sorts to count both and measures the time per operation.

Background:: [[wiki/python-vs-c-speed]]

## Null
capacity - moves and comparisons take similar time in Python, so counting one tells you nothing about the other

## Problem Statement

I want to understand where my sorts spend their time. Is it in the actual comparisons, or in the moves?

## Idea / Hypothesis

Most of my sort's time goes on comparing, not on moving

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Moves are faster than comparisons in Python. (found: Insertion: 0.41 microseconds per comparison, 0.08 microseconds per move. Moves 5x faster)
      fails-if:: Comparisons and moves take similar time.
      discriminates:: true
- [ ] Comparisons account for more than three quarters of insertion sort's total time (found: Comparisons were about two thirds)
      fails-if:: Comparisons account for three quarters or less of the total time
- [x] [outcome-neutral] The counters correctly track operations. (found: Verified: insertion sort on n items does between n-1 and n^2/2 comparisons. Counts matched)
      fails-if:: Counts do not match the algorithm's logic.

## Planned Intervention

Insertion and selection sort on 5000 random items, each run ten times. I added counters to count the number of comparisons and the number of moves. I measured total time and divided by the count of each operation.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h71/ and link at least the report:
     - [Report](results/h71/report.md)   - results/h71/curve.png -->
_(none yet)_

## Findings

Comparisons are the expensive part. Each comparison takes much longer than each move. My sorts are spending most of their time on comparisons, not on shuffling the list around. Faster comparisons would help more than faster moves.
