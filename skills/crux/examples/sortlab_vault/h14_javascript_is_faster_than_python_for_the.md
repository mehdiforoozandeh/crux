---
id: h14
type: idea
schema: 2
title: JavaScript is faster than Python for the same written sort
parent: q6
status: idea
rule: all
measurement: Median milliseconds for one insertion-sort pass in each language
replicates: 30 repeats at each of 10 sizes
verdict: 
metric: 
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:06:23"
---

# h14 — JavaScript is faster than Python for the same written sort

Parent:: [[q6_does_the_programming_language_change_the]]

## ELI5

JavaScript is faster than Python for the same written sort.

## TL;DR

I want to check whether the same sort code runs faster in JavaScript than in Python. I will implement insertion sort identically in both languages and time it on the same list sizes, with thirty repeats per size.

Background:: [[wiki/python-vs-javascript]]

## Null
instrumentation - the two languages' clocks do not measure the same thing

## Problem Statement

JavaScript and Python felt different when I was typing them. JavaScript might just be faster at running loops and comparisons, which would affect all my sorts.

## Idea / Hypothesis

JavaScript is faster than Python for the same written sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] Node's insertion sort is faster than Python's at every size from ten thousand up
      fails-if:: Python's insertion sort is faster at any size from ten thousand up
      discriminates:: true
- [ ] The speed-up is at least a factor of five at one hundred thousand items
      fails-if:: The speed-up at one hundred thousand items is under a factor of five
- [ ] [outcome-neutral] A known one-second sleep times as one second in both languages
      fails-if:: Either language times the one-second sleep as something other than a second

## Planned Intervention

Identical insertion sort implementation in both languages. Ten thousand to one hundred thousand items in steps of ten thousand. Thirty repeats per size. Same laptop, same morning. Warm-up run discarded in both.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h14/ and link at least the report:
     - [Report](results/h14/report.md)   - results/h14/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
