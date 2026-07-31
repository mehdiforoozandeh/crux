---
id: q1
type: question
title: Does more data beat a better model?
parent: root
status: resolved
stale: false
created: "2026-07-31T14:45:03"
updated: "2026-07-31T14:45:03"
synthesis: s1
---

# q1 — Does more data beat a better model?

Parent:: [[more_data_or_a_better_model]]

## Question

The comparison is made constantly and controlled almost never: each arm is run at whatever budget suited it, so 'more data won' and 'more compute won' predict the same result ([[wiki/controlled-comparison]]). The field has already paid for this once — [[wiki/compute-optimal-training]] is the record of a generation of models built far larger than their budgets justified. We fix the architecture family, the adaptation protocol ([[wiki/fine-tuning]]) and the seed count ([[wiki/seeds-and-variance]]), and run every comparison twice: once at equal data, once at equal compute ([[wiki/compute-budget]]).

## Answer so far

Not on a level budget. Doubling the data beats the better model when each arm is run at its own cost, and that is the comparison the literature usually reports. Matched on training compute the advantage reverses, and on a harder task it is gone before matching. The honest reading is that we measured a budget difference and very nearly published it as a data result.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 1, refuted 1, inconclusive 0)

- `h1` [[h1_twice_the_data_beats_a_better_model|Twice the data beats a better model]] — *done* — verdict **supported**, metric `+3.3 points`
- `h2` [[h2_the_advantage_survives_at_equal_compute|The advantage survives at equal compute]] — *done* — verdict **partial**, metric `+1.8 at equal data; -4.6 at equal compute`
- `h3` [[h3_the_advantage_holds_on_a_harder_task|The advantage holds on a harder task]] — *done* — verdict **refuted**, metric `-1.3 points`
<!-- crux:ledger:end -->
