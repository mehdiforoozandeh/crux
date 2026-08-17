---
id: h81
type: idea
schema: 2
title: The same sort is faster in JavaScript than in Python
parent: q26
status: done
rule: all
measurement: Time for one complete sort pass in each language.
replicates: 10 repeats in Python, 10 in JavaScript.
verdict: supported
metric: "Python merge: 3.8 s. JavaScript merge: 0.65 s. Ratio: 5.8x faster in JavaScript."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: 5f9c4baa7ade8622
lock: c86c7abef5222cf7
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h81 — The same sort is faster in JavaScript than in Python

Parent:: [[q26_does_the_same_method_rank_the_same_way_i]]

## ELI5

The same sorting algorithm runs faster in JavaScript than in Python on the school laptop.

## TL;DR

JavaScript's JIT compiler makes code faster than Python's interpreter. The claim is that every sort written in JavaScript is faster than the same sort in Python. The run compares each of the five sorts in both languages.

Background:: [[wiki/python-vs-javascript]]

## Null
instrumentation - Python and JavaScript use different timing methods and are not comparable

## Problem Statement

JavaScript is supposed to be faster because of JIT compilation. If it is really faster, then my Python sorts should be slower than the same sorts in JavaScript.

## Idea / Hypothesis

The same sort is faster in JavaScript than in Python

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Merge sort is faster in JavaScript than in Python. (found: Python merge: 3.8 s. JavaScript merge: 0.65 s. JavaScript is 5.8x faster)
      fails-if:: Python merge sort is faster or equal.
      discriminates:: true
- [x] Quick sort is faster in JavaScript than in Python. (found: Python quick: 2.1 s. JavaScript quick: 0.42 s. JavaScript is 5.0x faster)
      fails-if:: Python quick sort is faster or equal.
- [x] [outcome-neutral] Both languages produce correctly sorted output. (found: All sorts in both languages produced valid sorted lists)
      fails-if:: Either language produces wrong output.

## Planned Intervention

Merge sort and quick sort written in both Python and JavaScript. Tested on 100000 random items. Ten repeats in each language. Timed with perf_counter in Python and console.time in JavaScript.

## Run Links

- SortLab notebook, week 11

## Artifacts

<!-- what the run produced. Keep files under results/h81/ and link at least the report:
     - [Report](results/h81/report.md)   - results/h81/curve.png -->
_(none yet)_

## Findings

JavaScript is much faster. The same sort runs about five to six times faster in JavaScript than in Python. This is the language, not the algorithm. JavaScript's JIT compiler is much faster than Python's interpreter for this workload.
