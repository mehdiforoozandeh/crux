---
type: wiki
title: Bucket sort
summary: Bucket sort distributes items into buckets, sorts each bucket, then concatenates the results.
category: method
sources: raw/handout-ch07-sorting-basics.txt
---

# Bucket sort

Bucket sort divides the range of values into buckets, distributes items into them, sorts each bucket individually, then combines them.

## Background

Bucket sort takes a different approach to sorting than comparing adjacent items. It first divides the range of possible values into several buckets. For example, if sorting numbers between 0 and 1000, you might create ten buckets: 0-100, 100-200, and so on. It then scans through the input list and places each item into the appropriate bucket. Once all items are distributed, it sorts the contents of each bucket (using any method, often a simpler algorithm). Finally, it concatenates the buckets in order. If items are evenly distributed across buckets, and each bucket gets sorted quickly, bucket sort can be very fast: O(n + k) on average, where k is the number of buckets. If all items land in one bucket, performance degrades. Bucket sort requires knowing the range of values in advance and creating storage for buckets. It is stable if the sub-sort used for each bucket is stable. Bucket sort is useful when items are uniformly distributed across a known range, such as sorting test scores from 0 to 100. It is not a general-purpose sort and is rarely used without such specialized conditions.

## See also

Related:: [[sorting-algorithms-overview]], [[timsort]]
