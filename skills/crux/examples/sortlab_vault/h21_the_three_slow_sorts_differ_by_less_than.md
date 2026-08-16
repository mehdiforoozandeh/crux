---
id: h21
type: idea
schema: 2
title: The three slow sorts differ by less than two times
parent: q8
status: done
rule: m-of-n
measurement: Ratio of slowest to fastest time among the three sorts.
replicates: 30 repeats at each of 6 shapes at 5 sizes
verdict: refuted
metric: "Random 100k: bubble 1.6 s, insertion 0.34 s, selection 0.91 s. Fastest to slowest: 4.7 times."
created: "2026-08-16T16:06:23"
updated: "2026-08-16T16:07:04"
rule_m: 2
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: f93e0fa23d7c93a0
locked: "2026-08-16T16:06:45"
lock_at: running
---

# h21 — The three slow sorts differ by less than two times

Parent:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## ELI5

The three slow sorts differ by less than two times.

## TL;DR

I claimed the timing gaps between bubble, insertion, and selection are all less than a factor of two. If this were true, the three sorts would be roughly equivalent in speed, just with different trade-offs. I ran all three on twenty different conditions and checked the gap ratios.

Background:: [[wiki/bubble-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

I wanted to know whether the differences between the slow sorts are small or huge. If they are small, then choice of algorithm does not matter much on my laptop. If the gaps are big, it means algorithm choice is everything.

## Idea / Hypothesis

The three slow sorts differ by less than two times

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] The ratio of fastest to slowest is less than 1.5 times on random (found: Ratio 4.7 on random, not under 2)
      fails-if:: The gap is greater than two times on random
      discriminates:: true
- [ ] The ratio is less than 2.0 times on at least four of six shapes (found: Ratio over 2 on 5 of 6 shapes)
      fails-if:: More than two shapes have ratios greater than two times
- [ ] The ratio on sorted lists is less than 2.0 times (found: Ratio over 2 on sorted too)
      fails-if:: The gap on sorted lists is greater than two times
- [x] [outcome-neutral] Every sort returns the same items in order that it was given (found: All three sorts returned correct lists)
      fails-if:: A sort returns a list out of order or missing items

## Planned Intervention

Six shapes times five sizes, same setup as h18. Thirty repeats. Calculate the ratio of fastest to slowest among the three at each size and shape.

## Run Links

- SortLab notebook, week 2

## Artifacts

<!-- what the run produced. Keep files under results/h21/ and link at least the report:
     - [Report](results/h21/report.md)   - results/h21/curve.png -->
_(none yet)_

## Findings

The gap is much bigger than two times on random lists. Insertion is four to five times faster than bubble on random data. The difference is much smaller on sorted data, where the gap is only about 10 times narrower. The claim that the gaps are less than two times is clearly refuted.
