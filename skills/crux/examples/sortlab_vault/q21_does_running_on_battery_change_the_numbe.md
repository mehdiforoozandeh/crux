---
id: q21
type: question
schema: 2
title: Does running on battery change the number?
parent: q4
status: review
stale: true
created: "2026-08-16T16:06:21"
updated: "2026-08-16T16:06:21"
---

# q21 — Does running on battery change the number?

Parent:: [[q4_is_my_stopwatch_telling_me_the_truth]]

## ELI5

Does running on battery power change the time?

## TL;DR

Laptops slow themselves down on battery to save power. My laptop has a battery. I ran sorts plugged in and on battery and saw if the times changed.

Background:: [[wiki/power-management]], [[wiki/thermal-throttling]]

## Question

Power saving might make the processor run slower. If that is true, sorts will take longer on battery. The answer tells me whether I need to be plugged in for fair tests.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On plugged-in power, insertion on 10,000 items took 5.2 milliseconds. On battery, the same test took 6.1 milliseconds. The battery is slower, but only by about fifteen percent. I still try to use power when I can.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 0, refuted 0, inconclusive 1, invalid-run 1)

- `h62` [[h62_the_laptop_sorts_slower_on_battery_than_|The laptop sorts slower on battery than plugged in]] — *done* — verdict **supported**, metric `Plugged in: 8.7 ms. Battery: 9.6 ms. Ratio: 1.10x slower on battery.`
- `h63` [[h63_the_battery_gap_is_bigger_when_the_batte|The battery gap is bigger when the battery is nearly empty]] — *done* — verdict **inconclusive**, metric `Full: 8.8 ms. Half: 9.1 ms. Empty: 9.3 ms.`
- `h64` [[h64_plugging_in_mid_run_shows_up_as_a_step_i|Plugging in mid-run shows up as a step in the numbers]] — *done* — verdict **invalid-run**, metric `Cannot compute; run was void.`
<!-- crux:ledger:end -->
