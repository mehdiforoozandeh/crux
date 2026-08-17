---
id: h24
type: idea
schema: 2
title: My merge sort is steadier from run to run than my quick sort
parent: q9
status: done
rule: all
measurement: Standard deviation in milliseconds and as a percentage of median.
replicates: 30 repeats at each of 8 sizes
verdict: inconclusive
metric: "At 50k: merge 2.1 ms stdev (12 percent), quick 3.4 ms stdev (31 percent)."
created: "2026-08-16T16:06:24"
updated: "2026-08-16T16:07:04"
null_approved: "2026-08-16T16:06:32"
null_hash: 1b53c973f9a296aa
lock: 0e7df6d19e0022a7
locked: "2026-08-16T16:06:46"
lock_at: running
---

# h24 — My merge sort is steadier from run to run than my quick sort

Parent:: [[q9_does_merge_sort_beat_the_quick_sort_i_wr]]

## ELI5

My merge sort is steadier from run to run than my quick sort.

## TL;DR

Merge sort always does the same amount of work regardless of the input, while quick sort's time depends on whether the random pivot choices are lucky. I claimed merge sort is steadier and measured the variance in times across thirty runs for both sorts on the same sizes. The results show merge sort has less spread.

Background:: [[wiki/merge-sort]]

## Null
chance - one lucky run out of thirty would show this difference on its own

## Problem Statement

I was curious whether the unpredictability of quick sort shows up in my measurements. If quick sort is more of a gamble, it might not be the best choice for timing-critical work.

## Idea / Hypothesis

My merge sort is steadier from run to run than my quick sort

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [x] Merge sort has lower standard deviation than quick at all sizes (found: Merge 12%, quick 31% stdev)
      fails-if:: Quick sort is steadier than merge at any size
      discriminates:: true
- [-] Merge sort's spread stays narrower than quick sort's at one million items (found: Could not run at one million items)
      fails-if:: Quick sort's spread is narrower at one million items
- [x] [outcome-neutral] Both sorts are timed on the same list with the same repeat count (found: Same list and thirty repeats each)
      fails-if:: The two sorts get different lists or different repeat counts

## Planned Intervention

Both sorts on random lists from one thousand to one hundred thousand. Thirty repeats per size. Calculate standard deviation as a percentage of the median time.

## Run Links

- SortLab notebook, week 4

## Artifacts

<!-- what the run produced. Keep files under results/h24/ and link at least the report:
     - [Report](results/h24/report.md)   - results/h24/curve.png -->
_(none yet)_

## Findings

Merge sort's times clustered more tightly around the median. At 50k items, merge had a 12 percent standard deviation while quick was at 31 percent. This means quick sort is faster on average but less predictable.
