---
id: q32
type: question
schema: 2
title: Does closing the browser change the number?
parent: q20
status: open
stale: true
created: "2026-08-16T16:06:22"
updated: "2026-08-16T16:06:22"
---

# q32 — Does closing the browser change the number?

Parent:: [[q20_do_background_apps_change_the_number]]

## ELI5

Does closing the browser change how fast the sort runs?

## TL;DR

Background apps slow down my laptop. The browser is a big consumer of power. If I close the browser, does the sort get faster?

Background:: [[wiki/background-load]]

## Question

My laptop is old and closing one app might free up a lot of resources. The answer tells me if closing the browser is worth the trouble.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

Insertion on 10,000 items took 6.8 milliseconds with the browser open and video running, and 5.2 milliseconds with the browser closed. That is a noticeable difference. I close the browser before running important tests now.

<!-- crux:ledger:start -->
**2 children** · ideas 1/2 done (supported 0, partial 0, refuted 1, inconclusive 0, invalid-run 0)

- `h100` [[h100_closing_the_browser_makes_the_median_run|Closing the browser makes the median run faster]] — *done* — verdict **refuted**, metric `With background, median 2.16 s at 100k items. Closed, median 2.19 s. No improvement.`
- `h101` [[h101_closing_the_browser_makes_the_spread_sma|Closing the browser makes the spread smaller]] — *staged*
<!-- crux:ledger:end -->
