---
id: h12
type: idea
schema: 2
title: I can close the gap by translating my merge sort line by line
parent: q5
status: running
rule: all
measurement: Median milliseconds for one merge-sort pass in Python and in Node
replicates: 20 repeats at each of 6 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:06:44"
null_approved: "2026-08-16T16:06:31"
null_hash: f6ce61bf910088c4
lock: 9418ad4c9695d27e
locked: "2026-08-16T16:06:44"
lock_at: running
---

# h12 — I can close the gap by translating my merge sort line by line

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

I can close the gap by translating my merge sort line by line to JavaScript.

## TL;DR

I want to test whether the gap between my merge sort and the built-in sort closes if I translate my code directly to JavaScript and run it in Node. If JavaScript's engine is just faster, then the gap should stay roughly the same. If it closes, I will know that Python's implementation details are the bottleneck.

Background:: [[wiki/timsort]]

## Null
capacity - the JavaScript engine simply has more speed to spend, whatever code I write

## Problem Statement

The built-in sort in Python is written in C. My merge sort is pure Python. Maybe the language itself is the constraint, not my algorithm. If I write the same merge sort in JavaScript, I can test that theory.

## Idea / Hypothesis

I can close the gap by translating my merge sort line by line

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] My Node merge sort lands within twenty percent of Python's built-in sort at every size
      fails-if:: My Node merge sort stays more than twenty percent behind the built-in sort
      discriminates:: true
- [ ] The Python-to-Node gain on my merge sort is larger than the gain on the built-in sort
      fails-if:: My merge sort and the built-in sort gain the same factor from Node
- [ ] [outcome-neutral] Both languages sort the same list read from the same file
      fails-if:: The two languages sort different lists or different orderings

## Planned Intervention

Translate my Python merge sort line by line to JavaScript. Test on random lists from one thousand to one hundred thousand items. Twenty repeats per size. Node runtime. Same afternoon session.

## Run Links

- SortLab notebook, week 9

## Artifacts

<!-- what the run produced. Keep files under results/h12/ and link at least the report:
     - [Report](results/h12/report.md)   - results/h12/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
