---
id: s1
type: synthesis
title: What the three slow sorts settled
approved: "2026-08-16T16:07:12"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:12"
---

# Synthesis — What the three slow sorts settled

Related:: [[q8_which_of_the_three_slow_sorts_is_least_s]]

## Headline conclusions

Insertion sort is fastest of the three slow ones. Bubble sort without the early-exit trick is not always slowest—it sometimes beats selection sort. The slowest sort changed based on list size, so there is no single winner among these three.

## Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| Insertion sort is the fastest of the three slow sorts | Insertion was fastest on random lists of 1000 items | supported |
| Bubble sort is the slowest of the three at every size | Bubble often beat selection sort | refuted |
| Selection sort sits between the other two on random lists | Selection was sometimes the slowest | refuted |
| Bubble sort with an early exit stops being the slowest | Early exit helped, results mixed | inconclusive |
| The three slow sorts differ by less than two times | Slowest was 8x slower than fastest | refuted |

## Implications for next batch

I'll use insertion sort in any hybrid approach where I need a simple method. Bubble is not as bad as I thought, at least with the early exit. But none of these three are fast enough—I need to focus on merge and quick sort for the real races.
