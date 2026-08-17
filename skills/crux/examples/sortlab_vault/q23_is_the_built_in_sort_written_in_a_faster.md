---
id: q23
type: question
schema: 2
title: Is the built-in sort written in a faster language?
parent: q5
status: resolved
stale: false
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:07:13"
synthesis: s4
---

# q23 — Is the built-in sort written in a faster language?

Parent:: [[q5_why_is_the_built_in_sort_so_hard_to_beat]]

## ELI5

Is the built-in sort written in a faster language?

## TL;DR

The built-in sort is much faster than mine. Maybe it is because it is written in C, not Python. Python calling C code is very fast. I want to know if that is the reason.

Background:: [[wiki/interpreter-overhead]], [[wiki/python-vs-c-speed]]

## Question

My sorts are pure Python. The built-in sort is written in C and just called from Python. C is a faster language than Python. Does that explain why the built-in sort wins by so much?

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

An empty Python loop is slower than the entire built-in sort on ten thousand items. That tells me it is not just about language. The built-in sort is using a smarter method, not just faster code.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 2, partial 0, refuted 1, inconclusive 0, invalid-run 0)

- `h69` [[h69_the_built_in_sort_is_not_running_my_kind|The built-in sort is not running my kind of Python code]] — *done* — verdict **supported**, metric `Merge sort at n=100000: 6.7 s. Built-in: 0.81 s. Ratio: 8.3x.`
- `h70` [[h70_a_python_loop_that_only_counts_is_slower|A Python loop that only counts is slower than the whole built-in sort]] — *done* — verdict **supported**, metric `Counting loop: 0.92 s. Built-in sort: 0.81 s. Ratio: 1.14x.`
- `h71` [[h71_most_of_my_sort_s_time_goes_on_comparing|Most of my sort's time goes on comparing, not on moving]] — *done* — verdict **refuted**, metric `Insertion comparison time: 0.41 microsec. Move time: 0.08 microsec.`
<!-- crux:ledger:end -->
