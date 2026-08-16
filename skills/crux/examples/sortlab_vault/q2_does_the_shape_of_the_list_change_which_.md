---
id: q2
type: question
schema: 2
title: Does the shape of the list change which sort wins?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:40"
---

# q2 — Does the shape of the list change which sort wins?

Parent:: [[sortlab]]
RD:: [[rd/how_the_test_lists_are_made]] — How the test lists are made

## ELI5

Does the shape of the list change which sort wins?

## TL;DR

I test each sort on five different shapes of list: random, sorted, reversed, nearly sorted, and mostly the same value. The one that wins might not be insertion every time. Testing all five shapes tells me if one sort is best for all cases or just random.

Background:: [[wiki/input-generators]], [[wiki/adaptive-sorting]]

## Question

The list I sort might already be sorted, or backwards, or nearly sorted. Does the same sort still win? The answer is whether one sort beats all others on every shape, or if the winner changes.

## Protocol

Test on 10,000 items. Run each sort thirty times on each shape. Use the counter clock. Report the median time. A win means lowest median time.

## Answer so far

I tested sorted and reversed lists. On a sorted list, insertion is almost instant, about 0.8 milliseconds. On a reversed list, bubble takes forever, over 40 milliseconds. On nearly sorted, insertion wins again. The shape really matters.

<!-- crux:ledger:start -->
**6 children** · ideas 1/2 done (supported 0, partial 0, refuted 1, inconclusive 0, invalid-run 0) · sub-questions 3/4 resolved

- `h4` [[h4_the_winner_is_the_same_whatever_shape_th|The winner is the same whatever shape the list has]] — *done* — verdict **refuted**, metric `Random: insertion 0.23 s; sorted: insertion 0.01 s; reversed: insertion 0.24 s`
- `h5` [[h5_shuffling_the_same_numbers_twice_gives_t|Shuffling the same numbers twice gives the same ranking]] — *idea*
- `q11` _(Q)_ [[q11_what_happens_on_a_list_that_is_already_s|What happens on a list that is already sorted?]] — *resolved*
- `q12` _(Q)_ [[q12_what_happens_on_a_list_that_is_sorted_ba|What happens on a list that is sorted backwards?]] — *resolved*
- `q13` _(Q)_ [[q13_what_happens_when_the_list_is_almost_sor|What happens when the list is almost sorted?]] — *review*
- `q14` _(Q)_ [[q14_what_happens_when_the_list_is_mostly_the|What happens when the list is mostly the same value?]] — *resolved*
<!-- crux:ledger:end -->
