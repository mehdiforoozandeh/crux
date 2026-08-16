---
type: wiki
title: Stability
summary: A stable sort preserves the original order of items that compare equal.
category: concept
sources: raw/handout-ch10-stability-and-space.txt
---

# Stability

When sorting a list containing equal items, a stable sort leaves equal items in their original order. An unstable sort might rearrange them.

## Background

Suppose you have a list of students with scores: Alice 90, Bob 85, Carol 90, Diana 85. If you sort by score, the score-90 students end up at the top. A stable sort would put Alice before Carol (their original order). An unstable sort might put Carol before Alice. Why does this matter? If students have multiple attributes, sorting by one attribute while preserving order from a previous sort can encode multi-level sorting. For example, sort by name first (Alice, Bob, Carol, Diana), then sort by score using a stable sort. Stable sort preserves the within-score name order from the first sort. Bubble sort and merge sort are stable. Quick sort and heap sort are not. Insertion sort is stable if implemented carefully. Stability can matter when sorting complex data where equal items should maintain some other ordering. It is a minor concern compared to speed, but it is easy to forget about. Some programming languages' built-in sort functions are stable by design, others are not. Understanding stability helps avoid subtle bugs where equal items are rearranged unexpectedly.

## See also

Related:: [[algorithm-analysis-overview]], [[adaptive-sorting]]
