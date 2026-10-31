---
id: q26
type: question
schema: 2
title: Does the same method rank the same way in JavaScript?
parent: q6
status: resolved
stale: false
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:07:13"
---

# q26 — Does the same method rank the same way in JavaScript?

Parent:: [[q6_does_the_programming_language_change_the]]

## ELI5

In JavaScript, do the same sorts stay ranked the same way?

## TL;DR

I wrote the five sorts in JavaScript. On 10,000 random items in JavaScript, insertion is still faster than bubble, and merge is faster than insertion. The ranking stayed mostly the same.

Background:: [[wiki/javascript-sorting-overview]], [[wiki/python-vs-javascript]]

## Question

JavaScript is a different language from Python. Maybe the ranking changes because JavaScript engines work differently. The answer tells me if the algorithm itself or the language implementation matters more.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

In JavaScript, insertion took 2.8 milliseconds, merge took 2.1 milliseconds, and bubble took 31 milliseconds on 10,000 random items. The ranking is mostly the same as Python. Language does not change which sort is best.

<!-- crux:ledger:start -->
**3 children** · open 1, leaning 0, settled 2, parked 0 · 1 finding(s) on this question

- `h80` [[h80_the_five_sorts_rank_the_same_in_javascri|The five sorts rank the same in JavaScript as in Python]] — *settled · strong*
- `h81` [[h81_the_same_sort_is_faster_in_javascript_th|The same sort is faster in JavaScript than in Python]] — *settled · strong*
- `h82` [[h82_the_built_in_sort_wins_in_javascript_too|The built-in sort wins in JavaScript too]] — *open*
- `f97` finding (strong) [[f97_what_the_javascript_detour_settled|What the JavaScript detour settled]]
<!-- crux:ledger:end -->
