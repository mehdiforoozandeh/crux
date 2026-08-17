---
id: q6
type: question
schema: 2
title: Does the programming language change the answer?
parent: root
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:40"
---

# q6 — Does the programming language change the answer?

Parent:: [[sortlab]]
RD:: [[rd/fair_comparison_across_languages]] — Fair comparison across languages

## ELI5

Does switching to JavaScript change which sort is fastest?

## TL;DR

I rewrote the same five sorts in JavaScript and ran them in a browser. The times are all faster because JavaScript engines are fast. But does insertion still beat bubble? Does the ranking stay the same?

Background:: [[wiki/python-vs-javascript]]

## Question

Different languages have different speeds. I want to know if the ranking of my five sorts changes when I code them in JavaScript instead of Python. The answer tells me if the rank order is real or just about the language.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

In JavaScript on 10,000 random items, insertion took 2.8 milliseconds versus 5.2 in Python. Bubble took 31 milliseconds in JavaScript versus 40 in Python. The ranking is mostly the same, but one run had the lists get mixed up between sides, so that run does not count.

<!-- crux:ledger:start -->
**4 children** · ideas 1/2 done (supported 1, partial 0, refuted 0, inconclusive 0, invalid-run 0) · sub-questions 1/2 resolved

- `h13` [[h13_the_same_five_sorts_rank_the_same_way_in|The same five sorts rank the same way in both languages]] — *done* — verdict **supported**, metric `Python rank: merge, insertion, selection, quick, bubble. JavaScript rank: merge, quick, insertion, selection, bubble.`
- `h14` [[h14_javascript_is_faster_than_python_for_the|JavaScript is faster than Python for the same written sort]] — *idea*
- `q26` _(Q)_ [[q26_does_the_same_method_rank_the_same_way_i|Does the same method rank the same way in JavaScript?]] — *resolved*
- `q27` _(Q)_ [[q27_does_the_javascript_engine_speed_up_whil|Does the JavaScript engine speed up while it runs?]] — *open*
<!-- crux:ledger:end -->
