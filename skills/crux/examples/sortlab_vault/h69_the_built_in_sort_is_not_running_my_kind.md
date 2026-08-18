---
id: h69
type: idea
schema: 2
title: The built-in sort is not running my kind of Python code
parent: q23
status: done
rule: all
measurement: Time for one complete sort pass, with perf_counter.
replicates: 10 repeats at each of 3 sizes.
verdict: supported
metric: "Merge sort at n=100000: 6.7 s. Built-in: 0.81 s. Ratio: 8.3x."
created: "2026-08-16T16:06:27"
updated: "2026-08-16T16:07:08"
null_approved: "2026-08-16T16:06:36"
null_hash: 4b2d80706cd697a8
lock: bbe7812bae7063dc
locked: "2026-08-16T16:06:56"
lock_at: running
---

# h69 — The built-in sort is not running my kind of Python code

Parent:: [[q23_is_the_built_in_sort_written_in_a_faster]]

## ELI5

Python's built-in sort is not written in the same Python language I wrote my sorts in.

## TL;DR

Python's sort is much faster than anything I can write in Python. The claim is that the built-in sort must be written in a lower-level language like C, not in Python. The run compares my fastest sort (merge sort) to the built-in sort across many sizes.

Background:: [[wiki/python-vs-c-speed]]

## Null
capacity - the faster machine state, not the language, explains the whole gap

## Problem Statement

I wrote five sorts and the built-in sort beats them all by a lot. The difference is too big to be just a smarter algorithm. It might be that the built-in sort is written in C, not Python.

## Idea / Hypothesis

The built-in sort is not running my kind of Python code

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Built-in sort is faster than merge sort at all three sizes. (found: Built-in faster at 1000, 10000, and 100000 items. Min ratio 8.2x at n=100000)
      fails-if:: Merge sort wins at any size.
      discriminates:: true
- [x] The gap is bigger than what I can explain by better algorithm design. (found: At n=100000, built-in: 0.81 s, merge: 6.7 s. Ratio: 8.3x)
      fails-if:: The gap is less than 2x.
- [x] [outcome-neutral] Both sorts produce correct output. (found: Both merge and built-in produced valid sorted lists)
      fails-if:: Either sort fails to sort or returns garbage.

## Planned Intervention

My merge sort and Python's built-in sorted() function on random lists of 1000, 10000, and 100000 items. Ten repeats at each size. Timed with perf_counter. Plugged in, no background load.

## Run Links

- SortLab notebook, week 9

## Artifacts

- [Report](results/h69/report.md)

## Findings

The built-in sort is not running my kind of code. It is at least eight times faster than my best sort on large lists. No pure-Python sorting algorithm is that much better. The built-in must be written in C or another compiled language.
