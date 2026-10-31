---
id: q11
type: question
schema: 2
title: What happens on a list that is already sorted?
parent: q2
status: resolved
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:07:13"
---

# q11 — What happens on a list that is already sorted?

Parent:: [[q2_does_the_shape_of_the_list_change_which_]]

## ELI5

When the list is already sorted, which sort wins?

## TL;DR

A sorted list is a special case. Some sorts notice that it is already sorted and give up. Others have to check every pair anyway. I tested all five sorts on a 10,000-item sorted list.

Background:: [[wiki/sorted-input]], [[wiki/adaptive-sorting]]

## Question

Insertion sort should be very fast on a sorted list. Bubble should be slow. The winner tells me which sorts are smart about the input shape.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

Insertion was instant, 0.8 milliseconds. Merge took 2.0 milliseconds. Quick took 18 milliseconds because of the pivot choice. Bubble was fast too, only 3.1 milliseconds, because the early exit triggered right away. Shape really changes the game.

<!-- crux:ledger:start -->
**3 children** · open 0, leaning 0, settled 3, parked 0 · 1 finding(s) on this question

- `h28` [[h28_insertion_sort_is_fastest_of_my_sorts_on|Insertion sort is fastest of my sorts on an already sorted list]] — *settled · strong*
- `h29` [[h29_bubble_sort_with_an_early_exit_is_nearly|Bubble sort with an early exit is nearly free on a sorted list]] — *settled · strong*
- `h30` [[h30_selection_sort_takes_the_same_time_sorte|Selection sort takes the same time sorted or not]] — *settled · strong*
- `f89` finding (strong) [[f89_what_the_shape_of_the_list_settled|What the shape of the list settled]]
<!-- crux:ledger:end -->
