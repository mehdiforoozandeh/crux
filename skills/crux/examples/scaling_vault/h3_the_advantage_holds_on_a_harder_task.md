---
id: h3
type: idea
title: The advantage holds on a harder task
parent: q1
status: done
verdict: refuted
metric: -1.3 points
created: "2026-07-31T14:45:03"
updated: "2026-07-31T14:45:03"
---

# h3 — The advantage holds on a harder task

Parent:: [[q1_does_more_data_beat_a_better_model]]

## Problem Statement

The h1 task sits where convolutional inductive bias still pays and transformer capacity does not ([[wiki/imagenet]], [[wiki/vision-transformer]]). If the data advantage is real it should not depend on being measured at the easy end of that crossover, so we rerun on a task with a higher irreducible error ([[wiki/irreducible-error]]).

## Idea / Hypothesis

The advantage holds on a harder task

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] beats the better model on the harder task
- [ ] still beats it there at equal compute
- [ ] the gain holds in all 3 repeat runs

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

- job 4055

## Artifacts

<!-- what the run produced. Keep files under results/h3/ and link at least the report:
     - [Report](results/h3/report.md)   - results/h3/curve.png -->
_(none yet)_

## Findings

On the harder task the data arm lost outright (-1.3), and lost by more at equal compute (-5.1). No bar was met. Kept on record: this rules the easy-task reading out rather than leaving it untested.
