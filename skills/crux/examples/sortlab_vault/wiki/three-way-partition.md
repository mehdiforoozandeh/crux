---
type: wiki
title: Three-way split
summary: Dividing a list into three groups: items less than the pivot, items equal to the pivot, and items greater than the pivot.
category: method
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Three-way split

Regular quick sort wastes time comparing equal items. Three-way partition handles duplicates efficiently.

## Background

A standard quick sort divides the list into less-than-pivot and greater-than-pivot. But if there are many items equal to the pivot, those items get split across both halves and end up being partitioned again and again. This is wasteful. Three-way partition is a variant that puts all items equal to the pivot into the middle group during the first division. Then quick sort only recursively sorts the less-than group and the greater-than group, skipping the equal items entirely. This saves a huge amount of time when the input has many duplicates. On a list of all identical items, standard quick sort might take quadratic time, but three-way quick sort finishes in linear time. The fix is simple: during partitioning, maintain three regions instead of two. This shows why understanding the shape of your data matters for [[measuring-program-speed]]. The same algorithm behaves very differently depending on how many duplicates are present.

## See also

Related:: [[sorting-algorithms-overview]]
