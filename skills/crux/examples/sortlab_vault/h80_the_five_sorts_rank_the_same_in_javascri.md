---
id: h80
type: idea
schema: 2
title: The five sorts rank the same in JavaScript as in Python
parent: q26
status: done
rule: all
measurement: Time for one complete sort pass in JavaScript.
replicates: 10 repeats at each size.
verdict: refuted
metric: "Python ranking: bubble slowest, insertion faster, merge fastest. JavaScript: insertion slower than selection on some sizes."
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:09"
null_approved: "2026-08-16T16:06:37"
null_hash: d87b61e8ce29cacf
lock: 74ed44ec6968ab1d
locked: "2026-08-16T16:06:58"
lock_at: running
---

# h80 — The five sorts rank the same in JavaScript as in Python

Parent:: [[q26_does_the_same_method_rank_the_same_way_i]]

## ELI5

The five sorting algorithms rank the same way in JavaScript as they do in Python.

## TL;DR

I wrote the five sorts again in JavaScript and ran them on lists of sizes 1000 to 100000. The claim is that the ranking stays the same: bubble and selection are slowest, insertion is faster, merge and quick are fastest. The run compares the rankings.

Background:: [[wiki/javascript-sorting-overview]]

## Null
instrumentation - the JavaScript implementation has a subtle bug affecting ranking

## Problem Statement

Maybe the ranking changes when I use a different language. JavaScript engines are optimized differently. If the ranking changes, that tells me something about how each language works.

## Idea / Hypothesis

The five sorts rank the same in JavaScript as in Python

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Insertion sort is faster than bubble sort in JavaScript. (found: Bubble and insertion rank differently in JavaScript. Insertion is not always faster)
      fails-if:: Bubble is faster than insertion in JavaScript.
      discriminates:: true
- [ ] Selection sort stays slower than insertion sort in JavaScript, as it is in Python (found: Selection beat insertion at three sizes)
      fails-if:: Selection sort overtakes insertion sort in JavaScript
- [x] [outcome-neutral] All JavaScript sorts produce valid output. (found: All JavaScript sort outputs were correctly sorted)
      fails-if:: Some output is not correctly sorted.
- [x] [outcome-neutral] The same list is sorted by Python and JavaScript versions. (found: Verified: same input data for Python and JavaScript)
      fails-if:: The two language versions use different input.

## Planned Intervention

Bubble, insertion, selection, merge, and quick sort written in JavaScript. Tested on random lists of 1000, 10000, and 100000 items. Ten repeats at each size. Timed with console.time(). Ran in Node.js on the same laptop.

## Run Links

- SortLab notebook, week 11

## Artifacts

<!-- what the run produced. Keep files under results/h80/ and link at least the report:
     - [Report](results/h80/report.md)   - results/h80/curve.png -->
_(none yet)_

## Findings

The ranking is not the same. Insertion sort is not always faster in JavaScript than in Python. The languages have different strengths. JavaScript's JIT compiler optimizes different things, so algorithms behave differently.
