---
id: h101
type: idea
schema: 2
title: Closing the browser makes the spread smaller
parent: q32
status: staged
rule: all
measurement: Standard deviation of run times with closed and open browser.
replicates: Not yet measured. Staged and ready.
verdict: 
metric: 
created: "2026-08-16T16:06:30"
updated: "2026-08-16T16:07:01"
null_approved: "2026-08-16T16:06:39"
null_hash: f0302884cca36728
---

# h101 — Closing the browser makes the spread smaller

Parent:: [[q32_does_closing_the_browser_change_the_numb]]

## ELI5

Closing the browser makes run times more consistent.

## TL;DR

Even if closing the browser does not change the median time, it might reduce the spread. When background noise is low, all runs might be very similar. When background noise is high, some runs might spike. This test is staged and ready to run.

Background:: [[wiki/background-load]]

## Null
instrumentation - both scenarios have enough noise that spread does not differ meaningfully.

## Problem Statement

The consistency of measurements matters when I am trying to fit curves. If the spread changes, my fitted curve might be misleading. A shape that looks like n squared might actually be n squared plus noise.

## Idea / Hypothesis

Closing the browser makes the spread smaller

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The spread of thirty runs is at least a third smaller with the browser closed
      fails-if:: The spread with the browser closed is within a third of the open spread
      discriminates:: true
- [ ] The median time barely moves while the spread shrinks
      fails-if:: The median moves as much as the spread does
- [ ] [outcome-neutral] All thirty runs in each block complete and return correctly ordered lists
      fails-if:: A run in either block fails or returns an unordered list

## Planned Intervention

Measure the spread (standard deviation) of thirty runs with and without background.

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/h101/ and link at least the report:
     - [Report](results/h101/report.md)   - results/h101/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
