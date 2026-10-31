---
id: q27
type: question
schema: 2
title: Does the JavaScript engine speed up while it runs?
parent: q6
status: open
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q27 — Does the JavaScript engine speed up while it runs?

Parent:: [[q6_does_the_programming_language_change_the]]

## ELI5

Does the JavaScript engine speed up while it runs the sort?

## TL;DR

JavaScript engines have JIT compilation, which means they speed up as they run. The first call to a function is slow, later calls are fast. I want to know if that changes my timing results.

Background:: [[wiki/jit-compilation]], [[wiki/warm-up-effects]]

## Question

If the engine speeds up during the sort, the time would be lower than if I just compiled the sort once. The answer tells me if I need special warmup steps for JavaScript tests.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

I ran insertion sort twenty times in a loop in JavaScript. The first run took 3.2 milliseconds and the tenth run took 2.6 milliseconds. The engine does speed up. I now run sorts ten times and ignore the first one.

<!-- crux:ledger:start -->
**3 children** · open 1, leaning 1, settled 1, parked 0

- `h83` [[h83_javascript_gets_faster_after_the_first_f|JavaScript gets faster after the first few hundred runs]] — *settled · strong*
- `h84` [[h84_the_speed_up_is_bigger_for_my_sorts_than|The speed-up is bigger for my sorts than for the built-in one]] — *leaning · weak*
- `h85` [[h85_a_fresh_browser_tab_starts_slow_again|A fresh browser tab starts slow again]] — *open*
<!-- crux:ledger:end -->
