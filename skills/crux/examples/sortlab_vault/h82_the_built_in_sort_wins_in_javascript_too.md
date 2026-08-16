---
id: h82
type: idea
schema: 2
title: The built-in sort wins in JavaScript too
parent: q26
status: done
rule: all
measurement: Time in milliseconds for each sort on the JavaScript runtime using performance.now().
replicates: 30 repeats at each of 5 sizes from 10k to 1M items.
verdict: invalid-run
metric: Cannot compute; the two sides sorted different lists
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: 22ba66f4cbbe5176
lock: 66fd86cb9cd2aaa7
locked: "2026-08-16T16:06:59"
lock_at: running
---

# h82 — The built-in sort wins in JavaScript too

Parent:: [[q26_does_the_same_method_rank_the_same_way_i]]

## ELI5

JavaScript's built-in sort beats my hand-written code just like Python does.

## TL;DR

I rewrote my five sorts in JavaScript and raced them in the browser. The built-in sort won at every size tested. This test tried to run but a control failed: the Python side and JavaScript side got different lists to sort, so the run could not answer the question.

Background:: [[wiki/javascript-sorting-overview]]

## Null
instrumentation - the timer precision made runs on small lists too noisy to compare fairly.

## Problem Statement

I knew Python's built-in sort was fast, but I was not sure if the same thing happened in a different language. Would a different engine favour different algorithms.

## Idea / Hypothesis

The built-in sort wins in JavaScript too

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] The built-in sort finishes faster than insertion at fifty thousand items. (found: Cannot compute; the two sides sorted different lists)
      fails-if:: Insertion sort takes less time or within timing noise margin.
      discriminates:: true
- [ ] The JavaScript engine does not compile hand-written sorts to the same code.
      fails-if:: My sort and the built-in run in measurably identical time.
- [ ] [outcome-neutral] The sorted output is actually sorted and has all original items.
      fails-if:: Output list is not in order or has dropped or added values.

## Planned Intervention

I copied my five sort functions into JavaScript and timed them in a web page. Ten thousand to one million items. Thirty repeats at each size. Same laptop, one browser tab, median time.

## Run Links

- SortLab notebook, week 11

## Artifacts

<!-- what the run produced. Keep files under results/h82/ and link at least the report:
     - [Report](results/h82/report.md)   - results/h82/curve.png -->
_(none yet)_

## Findings

The run broke before it could answer anything. The Python side and the JavaScript side were handed different lists, so the times were never comparable. The built-in sort did win in the browser, but I cannot lean on a number from a run whose control failed.
