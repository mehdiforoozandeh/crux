---
id: q16
type: question
schema: 2
title: Where does merge sort overtake insertion sort?
parent: q3
status: open
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q16 — Where does merge sort overtake insertion sort?

Parent:: [[q3_how_does_the_time_grow_when_the_list_get]]

## ELI5

At what size does merge sort start beating insertion?

## TL;DR

For small lists, insertion is fast. Merge has overhead that only pays off on big lists. At some point, merge takes over as the winner. I want to find the crossover size where merge first beats insertion.

Background:: [[wiki/crossover-points]], [[wiki/hybrid-sorts]]

## Question

Insertion is fast on small lists but gets slow on big lists. Merge starts slow but grows more slowly. There is a crossover point where merge wins. The answer is what size that is on my laptop.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On 1,000 items, insertion is faster. On 10,000 items, merge is faster. The crossover is somewhere in between. I think it is around 4,000 or 5,000 items, but I have not pinned it down exactly yet.

<!-- crux:ledger:start -->
**3 children** · ideas 2/3 done (supported 1, partial 0, refuted 1, inconclusive 0, invalid-run 0)

- `h47` [[h47_merge_sort_overtakes_insertion_sort_belo|Merge sort overtakes insertion sort below one thousand items]] — *done* — verdict **refuted**, metric `At n=500: insertion 0.021 ms, merge 0.022 ms`
- `h48` [[h48_the_crossover_size_moves_when_the_list_i|The crossover size moves when the list is almost sorted]] — *done* — verdict **supported**, metric `Random crossover n=500; almost-sorted crossover n=3200`
- `h49` [[h49_a_hybrid_that_switches_at_the_crossover_|A hybrid that switches at the crossover beats both]] — *staged*
<!-- crux:ledger:end -->
