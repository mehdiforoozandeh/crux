---
id: q30
type: question
schema: 2
title: Can I predict the time for a shape I have not run?
parent: q7
status: open
stale: false
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q30 — Can I predict the time for a shape I have not run?

Parent:: [[q7_can_i_guess_the_time_before_i_run_the_te]]

## ELI5

Can I predict the time for a different input shape?

## TL;DR

I have data for insertion on random lists of many sizes. Can I use that data to predict the time on a sorted or reversed list? Does the shape follow a predictable pattern?

Background:: [[wiki/input-generators]], [[wiki/adaptive-sorting]]

## Question

If insertion on random 10,000 items takes 5 milliseconds, does insertion on a sorted 10,000 items follow a pattern? The answer tells me if I can predict one shape from another.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

Insertion on random 10,000 items takes 5.2 milliseconds. On sorted it takes 0.8 milliseconds, about one sixth. On reversed it takes 24 milliseconds, about four times. The shape does not follow a simple pattern. I cannot predict one from the other.

<!-- crux:ledger:start -->
**4 children** · ideas 0/4 done (supported 0, partial 0, refuted 0, inconclusive 0, invalid-run 0)

- `h93` [[h93_a_curve_fitted_on_random_lists_predicts_|A curve fitted on random lists predicts almost-sorted lists]] — *idea*
- `h94` [[h94_each_shape_needs_its_own_curve|Each shape needs its own curve]] — *idea*
- `h95` [[h95_the_shape_changes_the_slope_not_just_the|The shape changes the slope, not just the height]] — *idea*
- `h96` [[h96_duplicate_heavy_lists_are_the_hardest_sh|Duplicate-heavy lists are the hardest shape to predict]] — *staged*
<!-- crux:ledger:end -->
