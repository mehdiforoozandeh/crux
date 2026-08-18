---
id: q9
type: question
schema: 2
title: Does merge sort beat the quick sort I wrote?
parent: q1
status: review
stale: true
created: "2026-08-16T16:06:20"
updated: "2026-08-16T16:06:20"
---

# q9 — Does merge sort beat the quick sort I wrote?

Parent:: [[q1_which_sort_that_i_wrote_myself_is_fastes]]

## ELI5

On random items, does merge beat my quick sort?

## TL;DR

I have timed insertion and selection. Now I need to know if merge or quick is faster. I wrote both of them and timed them on ten thousand random items. The one with the lower median wins.

Background:: [[wiki/merge-sort]], [[wiki/quick-sort]]

## Question

Merge and quick are supposed to be faster than the slow three. I want to know which of these two is better on a real laptop. The answer tells me which algorithm I like more.

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

On 10,000 random items, merge took 2.1 milliseconds and quick took 2.4 milliseconds. Merge seems faster. But on nearly sorted lists, quick might do better. I am still testing different shapes before I decide on a final ranking.

<!-- crux:ledger:start -->
**3 children** · ideas 3/3 done (supported 1, partial 0, refuted 1, inconclusive 1, invalid-run 0)

- `h22` [[h22_my_merge_sort_beats_my_quick_sort_on_ran|My merge sort beats my quick sort on random lists]] — *done* — verdict **refuted**, metric `Quick sort 11 ms, merge sort 18 ms at 100k random.`
- `h23` [[h23_my_quick_sort_uses_less_memory_than_my_m|My quick sort uses less memory than my merge sort]] — *done* — verdict **supported**, metric `At 100k: quick 1200 KB, merge 2800 KB. Quick uses 43 percent of merge's memory.`
- `h24` [[h24_my_merge_sort_is_steadier_from_run_to_ru|My merge sort is steadier from run to run than my quick sort]] — *done* — verdict **inconclusive**, metric `At 50k: merge 2.1 ms stdev (12 percent), quick 3.4 ms stdev (31 percent).`
<!-- crux:ledger:end -->
