---
id: h83
type: idea
schema: 2
title: JavaScript gets faster after the first few hundred runs
parent: q27
status: done
rule: all
measurement: Elapsed time in milliseconds per run, sampled at intervals within the loop.
replicates: One continuous session with three hundred iterations of each sort.
verdict: supported
metric: Insertion sort run 1 was 14.2 ms, run 100 was 3.8 ms, settling there.
created: "2026-08-16T16:06:28"
updated: "2026-08-16T16:07:10"
null_approved: "2026-08-16T16:06:38"
null_hash: 69b478d23f57b53e
lock: 8c7995185856f0f6
locked: "2026-08-16T16:06:59"
lock_at: running
---

# h83 — JavaScript gets faster after the first few hundred runs

Parent:: [[q27_does_the_javascript_engine_speed_up_whil]]

## ELI5

The JavaScript engine gets faster the more code it runs.

## TL;DR

I ran each sort many times in a loop within one page load. The first few runs took longer, then times settled down. The engine compiles and optimizes code as it runs, a process called just-in-time compilation. All five sorts showed this pattern.

Background:: [[wiki/warm-up-effects]]

## Null
instrumentation - the timer's resolution made early runs too noisy to tell apart.

## Problem Statement

I wanted to know if the startup cost of the browser mattered. If the engine warmed up, the time you measured depended on when you started counting.

## Idea / Hypothesis

JavaScript gets faster after the first few hundred runs

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Run number fifty is faster than run number one by at least five percent. (found: Insertion sort run 1 was 14.2 ms, run 100 was 3.8 ms)
      fails-if:: Early and late runs take the same time or get slower.
      discriminates:: true
- [x] The speed increase happens before run one hundred, not gradually throughout.
      fails-if:: Times keep improving linearly through all three hundred runs.
- [x] [outcome-neutral] The same list data produces the same output order every time.
      fails-if:: Correctness degrades or the output becomes corrupted after many runs.

## Planned Intervention

One page load, one sort, three hundred runs in a tight loop. Same input at each run. Recorded the time for run number one, fifty, one hundred, and three hundred.

## Run Links

- SortLab notebook, week 12

## Artifacts

<!-- what the run produced. Keep files under results/h83/ and link at least the report:
     - [Report](results/h83/report.md)   - results/h83/curve.png -->
_(none yet)_

## Findings

The engine starts slow and then gets much faster, sometimes three or four times quicker. This speedup happened within the first hundred runs for all sorts. After that the times were stable.
