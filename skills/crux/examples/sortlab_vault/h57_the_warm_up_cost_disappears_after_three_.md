---
id: h57
type: idea
schema: 2
title: The warm-up cost disappears after three runs
parent: q19
status: done
rule: all
measurement: Time for one pass, timed with perf_counter.
replicates: 15 repeats of each sort.
verdict: inconclusive
metric: "Bubble: run 1 = 8.4 ms, run 3 = 7.8 ms, runs 4-15 mean = 7.7 ms."
created: "2026-08-16T16:06:26"
updated: "2026-08-16T16:07:07"
null_approved: "2026-08-16T16:06:35"
null_hash: 93e530a7b7316a59
lock: a180139da39a928d
locked: "2026-08-16T16:06:53"
lock_at: running
---

# h57 — The warm-up cost disappears after three runs

Parent:: [[q19_does_the_first_run_take_longer_than_the_]]

## ELI5

The warm-up cost goes away completely after exactly three runs.

## TL;DR

If the first run is a warm-up, maybe it fades after a few more runs. The claim is that by run three, the sort has settled and runs four through ten are all similar to each other. The run checks whether run three matches runs four through ten.

Background:: [[wiki/interpreter-overhead]]

## Null
instrumentation - the slowness and speed are just random noise, not a real trend

## Problem Statement

I know run one is slow. But I do not know how many runs it takes for the slowness to stop. Is it just run one, or does it linger for a few runs?

## Idea / Hypothesis

The warm-up cost disappears after three runs

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Run three finishes in time similar to runs four through fifteen. (found: Bubble run 3: 7.8 ms, median of 4-15: 7.7 ms. Within noise)
      fails-if:: Run three is noticeably slower than later runs.
      discriminates:: true
- [-] Runs four through fifteen show similar times to each other. (found: Coefficient of variation for runs 4-15 was under 2 percent for both sorts)
      fails-if:: Times drift up or down across runs four to fifteen.
- [x] [outcome-neutral] Each run uses the same shuffled list. (found: Verified: same list used for all 15 runs of each sort)
      fails-if:: The list is different across runs or is sorted by accident.

## Planned Intervention

Insertion and bubble sort, each run 15 times on 1000 items. Same laptop state as before. I looked at whether runs 1-3 are noticeably slower than runs 4-15.

## Run Links

- SortLab notebook, week 3

## Artifacts

<!-- what the run produced. Keep files under results/h57/ and link at least the report:
     - [Report](results/h57/report.md)   - results/h57/curve.png -->
_(none yet)_

## Findings

Run three is already at the steady-state speed. The slowness is only in runs one and two. But the pattern is not perfectly clean, so I cannot say for certain that three is the magic number.
