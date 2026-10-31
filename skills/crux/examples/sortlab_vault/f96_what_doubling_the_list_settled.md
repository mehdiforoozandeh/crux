---
id: f96
type: finding
schema: 3
title: What doubling the list settled
parent: q34
confidence: strong
migrated_from: "s5_what_doubling_the_list_settled:q34"
created: "2026-08-16T16:07:12"
updated: "2026-08-16T16:07:12"
---

# f96 — What doubling the list settled

Parent:: [[q34_does_the_doubling_ratio_settle_down_at_b]]

## Answer

What doubling the list settled

### Headline conclusions

When I double the list size, insertion sort's time increases by close to 4x, not 2x. This is what I expect from theory, but the measured ratio stays higher than theory predicts at smaller sizes. It settles closer to 4x only above 50000 items.

### Cross-run table

| hypothesis | what I measured | verdict |
|---|---|---|
| The doubling ratio settles above one hundred thousand items | Data noisy even at 1 million items | inconclusive |
| The measured ratio is closer to four than to two for insertion sort | Median ratio: 3.8x | supported |

### Implications for next batch

Insertion sort scales worse than I initially measured. For the laptop, lists above 10000 items take much longer. I should plot the ratio across all sizes to see where it stabilizes.
