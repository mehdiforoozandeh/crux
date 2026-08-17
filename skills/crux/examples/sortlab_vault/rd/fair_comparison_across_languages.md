---
type: rd
node: q6
title: Fair comparison across languages
status: active
supersedes: 
created: 2026-08-16T16:06:40
updated: 2026-08-16T16:06:40
---

# Fair comparison across languages

RD for [[q6_does_the_programming_language_change_the]] — `q6`

## Context

I wrote my five sorts in Python and wanted to try them in JavaScript to see if the language changed the answer. But comparing Python and JavaScript is tricky because the runtimes are so different. I needed to ensure both languages timed only the sort, not the overhead of reading the list or printing results.

Background:: [[wiki/python-vs-javascript]], [[wiki/micro-benchmarking-pitfalls]]

## Out of scope

This design does not account for differences in garbage collection, JIT compilation timing, or how the two languages schedule background threads.

## Design

For each language, I write a harness that reads the same list from a file (written by the Python generator), times only the sort call itself, and records the result using that language's best timer. Python uses [[wiki/perf-counter]], JavaScript uses console.time(). Both run the sort 30 times, discard the first, and report the median. The list is written to a JSON file so both languages read the identical numbers.

## Considered options

I could have rewritten the list generator in JavaScript, but that risks subtle differences. I could have used the same timer for both, but each language has its own best choice. I chose JSON for the list format because both languages parse it easily.

## Consequences and known distortions

The comparison is still not perfectly fair because Python is interpreted and JavaScript has a JIT compiler. The results show which is faster overall on my laptop, but they do not show why. I have to remember that these are runtime differences, not algorithmic differences.

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
