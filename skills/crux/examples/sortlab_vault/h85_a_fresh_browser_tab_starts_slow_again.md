---
id: h85
type: idea
schema: 2
title: A fresh browser tab starts slow again
parent: q27
status: running
rule: all
measurement: Elapsed time in milliseconds for the first sort run on fresh and on warm browser tabs.
replicates: First run only on fresh tab, then fifty runs on same tab to warm up, then first run on new tab.
verdict: 
metric: 
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:06:59"
null_approved: "2026-08-16T16:06:38"
null_hash: 8abf4621eac4eb17
lock: 918a94c6b4e82078
locked: "2026-08-16T16:06:59"
lock_at: running
---

# h85 — A fresh browser tab starts slow again

Parent:: [[q27_does_the_javascript_engine_speed_up_whil]]

## ELI5

A new browser tab starts fresh without the warm-up benefit.

## TL;DR

I want to test whether closing the browser tab and opening a new one resets the warm-up clock. If it does, the first run on a fresh tab would be slow again. This test is still running and has not reached a conclusion yet.

Background:: [[wiki/warm-up-effects]]

## Null
instrumentation - the browser's background processes might vary between page loads, making timing unreliable.

## Problem Statement

Understanding warm-up helps me understand which measurements are real and which are just engine startup noise. If I need to close the tab between runs, every run might be starting cold.

## Idea / Hypothesis

A fresh browser tab starts slow again

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The first run in a fresh tab is at least twice as slow as a warm run
      fails-if:: The first run in a fresh tab matches the warm run
      discriminates:: true
- [ ] The fresh tab's slow start disappears again within twenty runs
      fails-if:: The fresh tab stays slow past twenty runs
- [ ] [outcome-neutral] Every tab sorts the same list and returns it correctly ordered
      fails-if:: A tab sorts a different list or returns it out of order

## Planned Intervention

Open a fresh tab, run the sort twenty times, measure the first run. Close the tab. Open a new tab and repeat. Compare the first run on a new tab to the first run in a warm tab.

## Run Links

- SortLab notebook, week 12

## Artifacts

<!-- what the run produced. Keep files under results/h85/ and link at least the report:
     - [Report](results/h85/report.md)   - results/h85/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
