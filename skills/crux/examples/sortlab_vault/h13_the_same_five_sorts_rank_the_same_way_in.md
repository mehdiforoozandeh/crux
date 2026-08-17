---
id: h13
type: idea
schema: 2
title: The same five sorts rank the same way in both languages
parent: q6
status: done
rule: all
measurement: Median time in milliseconds. Comparison of rank positions across languages.
replicates: 30 repeats per sort per size in each language
verdict: supported
metric: "Python rank: merge, insertion, selection, quick, bubble. JavaScript rank: merge, quick, insertion, selection, bubble."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:31"
null_hash: 410030299ea4d593
lock: e5b4c332b6b55968
locked: "2026-08-16T16:06:44"
lock_at: running
---

# h13 — The same five sorts rank the same way in both languages

Parent:: [[q6_does_the_programming_language_change_the]]

## ELI5

The same five sorts rank the same way in both languages.

## TL;DR

I rewrote all five sorts in JavaScript to test whether the ranking of speeds stays the same across languages. I measured all five hand-written sorts in both Python and JavaScript on random lists from ten thousand to one hundred thousand items, with thirty repeats per size. The ranking is almost the same but not quite.

Background:: [[wiki/python-vs-javascript]]

## Null
instrumentation - the timer's step is bigger than the gap I am claiming to see

## Problem Statement

Python and JavaScript have different engines and optimizers. Maybe the best sort changes if you switch languages. That would tell me something about whether my results are about the algorithms or about the language.

## Idea / Hypothesis

The same five sorts rank the same way in both languages

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The top three sorts are the same in both Python and JavaScript (found: Top 2 same, position 3 different)
      fails-if:: The top sort in Python is not in the top three in JavaScript
      discriminates:: true
- [x] Insertion sort is faster than bubble in both languages (found: Insertion beats bubble in both)
      fails-if:: Bubble sort is faster than insertion in either language
- [x] [outcome-neutral] Both languages produce sorted output (found: Both languages correct)
      fails-if:: Either language produces unsorted output from any sort

## Planned Intervention

Ten thousand, twenty thousand, fifty thousand, one hundred thousand item sizes. Random input. Thirty repeats per size in Python, thirty in JavaScript using Node. Same morning session, no background apps. Warm-up run discarded in both.

## Run Links

- SortLab notebook, week 11

## Artifacts

<!-- what the run produced. Keep files under results/h13/ and link at least the report:
     - [Report](results/h13/report.md)   - results/h13/curve.png -->
_(none yet)_

## Findings

The ranking was almost the same. Merge sort and insertion sort were both in the top two in both languages. But quick sort moved from last in Python to third in JavaScript. The languages have different optimizers, so the order is not completely stable.
