---
type: wiki
title: Insertion sort
summary: Insertion sort builds a sorted list one item at a time, like sorting playing cards in your hand.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Insertion sort

Insertion sort processes items one by one, inserting each into its correct position in the already-sorted portion of the list.

## Background

Insertion sort resembles how many people sort playing cards by hand. You start with an empty sorted pile. Then you pick up one card at a time and insert it into the right position in the pile. Insertion sort on a computer works the same way. It starts with the first item (which is trivially sorted). Then it takes the second item and puts it in the right position relative to the first. Then it takes the third item and inserts it in the right spot among the first two. It continues until all items are processed. This algorithm also makes roughly n squared comparisons in the worst case, so it scales poorly for large lists. But it has some practical advantages. It works well on small lists. It works well on data that is already nearly sorted—if most items are already in the right place, insertion sort notices and finishes quickly. It is also stable, meaning items that compare equal maintain their original order. Because insertion sort is relatively simple and works well on small datasets, it is often used as part of [[sorting-algorithms-overview]] hybrid approaches. Some fast algorithms switch to insertion sort when the data chunks become small enough.

## See also

Related:: [[sorting-algorithms-overview]], [[selection-sort]]
