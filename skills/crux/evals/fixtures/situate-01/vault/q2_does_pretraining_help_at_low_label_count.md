---
id: q2
type: question
schema: 2
title: Does pretraining help at low label counts?
parent: q1
status: open
stale: true
created: "2026-08-16T14:15:13"
updated: "2026-08-16T14:15:13"
---

# q2 — Does pretraining help at low label counts?

Parent:: [[q1_how_do_we_cut_the_label_budget]]

## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this asks, and what would settle it)_

## Question

Does pretraining help at low label counts?

See [[wiki/pretraining|Pretraining for dense prediction]] for what the literature already claims here.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

_(interpretation — written by the PI/agent; auto-flagged stale when new evidence lands)_

<!-- crux:ledger:start -->
**3 children** · ideas 1/3 done (supported 1, partial 0, refuted 0, inconclusive 0, invalid-run 0)

- `h1` [[h1_pretraining_beats_training_from_scratch_|pretraining beats training from scratch at 100 labels]] — *done* — verdict **supported**, metric `+4.1 mIoU at 100 labels`
- `h2` [[h2_pretraining_still_helps_at_20_labels|pretraining still helps at 20 labels]] — *idea*
- `h3` [[h3_a_longer_pretraining_schedule_widens_the|a longer pretraining schedule widens the gap]] — *running*
<!-- crux:ledger:end -->
