---
id: q1
type: question
title: Does more data beat a better model?
parent: root
status: resolved
stale: false
created: "2026-07-31T14:45:03"
updated: "2026-07-31T14:45:03"
---

# q1 — Does more data beat a better model?

Parent:: [[more_data_or_a_better_model]]

## Question

The comparison is made constantly and controlled almost never: each arm is run at whatever budget suited it, so 'more data won' and 'more compute won' predict the same result ([[wiki/controlled-comparison]]). The field has already paid for this once — [[wiki/compute-optimal-training]] is the record of a generation of models built far larger than their budgets justified. We fix the architecture family, the adaptation protocol ([[wiki/fine-tuning]]) and the seed count ([[wiki/seeds-and-variance]]), and run every comparison twice: once at equal data, once at equal compute ([[wiki/compute-budget]]).

## Protocol

Architecture family, adaptation protocol and seed count fixed before any run. Every comparison executed twice — once at equal data, once at equal compute. Verifiable thresholds pre-registered on all three hypotheses; verdicts derived mechanically from the ticks.

## Answer so far

Not on a level budget. Doubling the data beats the better model when each arm is run at its own cost, and that is the comparison the literature usually reports. Matched on training compute the advantage reverses, and on a harder task it is gone before matching. The honest reading is that we measured a budget difference and very nearly published it as a data result.

<!-- crux:ledger:start -->
**3 children** · open 0, leaning 1, settled 2, parked 0 · 1 finding(s) on this question

- `h1` [[h1_twice_the_data_beats_a_better_model|Twice the data beats a better model]] — *settled · strong*
- `h2` [[h2_the_advantage_survives_at_equal_compute|The advantage survives at equal compute]] — *leaning · weak*
- `h3` [[h3_the_advantage_holds_on_a_harder_task|The advantage holds on a harder task]] — *settled · strong*
- `f6` finding (strong) [[f6_more_data_wins_on_paper_and_loses_on_a_l|More data wins on paper and loses on a level budget]]
<!-- crux:ledger:end -->
