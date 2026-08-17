---
type: wiki
title: Median of three
summary: A technique to find a pivot for quick sort by comparing three items and using the one that is neither smallest nor largest.
category: method
sources: raw/handout-ch08-divide-and-conquer.txt
---

# Median of three

Picking a random pivot can backfire on certain data patterns. Using median-of-three avoids many worst cases.

## Background

Quick sort needs a good pivot, but finding the true middle value is expensive if you have to look at all items. Median-of-three is a cheap way to get a good pivot: examine three items, usually the first, middle, and last, and pick the one that falls between the other two. If the first is 10, the middle is 50, and the last is 30, the median is 30. Using 30 as the pivot gives a better split than picking the first item, which would give 10. This simple trick costs just two comparisons but protects quick sort from worst-case behavior on sorted or reverse-sorted input. It is simple enough that many implementations use it by default. The only case it does not help is when all three items are in order already, but then the list is already sorted and quick sort finishes fast anyway. This technique is an example of how a small algorithmic choice can dramatically change performance. It costs almost nothing but provides protection [[measuring-program-speed]] reveals.

## See also

Related:: [[sorting-algorithms-overview]], [[three-way-partition]]
