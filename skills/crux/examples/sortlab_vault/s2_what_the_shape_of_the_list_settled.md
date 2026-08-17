---
id: s2
type: synthesis
title: What the shape of the list settled
approved: "2026-08-16T16:07:12"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:12"
---

# Synthesis — What the shape of the list settled

Related:: [[q11_what_happens_on_a_list_that_is_already_s]], [[q12_what_happens_on_a_list_that_is_sorted_ba]], [[q14_what_happens_when_the_list_is_mostly_the]]

## Headline conclusions

On a sorted list, insertion sort is not the fastest—the built-in sort is. Bubble with early exit becomes nearly free on a sorted list, running in 0.3 milliseconds on 1000 items. Selection sort ignores the list's order and takes the same time sorted or reversed. A backwards list is insertion's worst case, taking 8x longer than a sorted list.

## Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| Insertion sort is fastest of my sorts on an already sorted list | Quick sort was faster on sorted lists | refuted |
| Bubble sort with an early exit is nearly free on a sorted list | 0.3 ms on 1000 sorted items | supported |
| Selection sort takes the same time sorted or not | Ran 12.4 ms both ways | supported |
| A backwards list is the worst case for insertion sort | Backwards took 8x longer than sorted | supported |
| A backwards list is the worst case for bubble sort too | Bubble was slower, but less extreme | inconclusive |
| Merge sort does not care that the list is backwards | Merge was 2.1 ms both ways | supported |
| My quick sort slows down when most items are equal | Duplicates caused 3x slowdown | supported |
| Bubble sort is unaffected by duplicate values | Duplicates actually sped it up slightly | refuted |
| A three-way split fixes my quick sort on duplicate-heavy lists | 3-way partition brought it back to 1.8 ms | supported |

## Implications for next batch

I should test my sorts on realistic data shapes, not just random lists. The shape changes which sort wins. I'll design test lists with sorted runs, duplicates, and reversed sections to see how each algorithm handles them.
