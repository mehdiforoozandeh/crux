---
type: wiki
title: Algorithm analysis overview
summary: Algorithm analysis uses mathematical notation to predict how speed changes as data size grows.
category: overview
sources: raw/handout-ch09-growth-rates.txt
---

# Algorithm analysis overview

Instead of timing every program, mathematicians predict how algorithms slow down when given larger inputs. This prediction uses a shorthand called Big-O notation.

## Background

When you double the amount of data to sort, does the program take twice as long, or four times as long, or something else? This depends on the algorithm. Some algorithms get slower roughly as fast as the data grows. Others get much slower—doubling the data might quadruple the time. Algorithm analysis is a mathematical way to predict this slowdown without having to measure it by hand. A simple algorithm might check every item against every other item, which means the time grows as the square of the data size. A better algorithm might use [[big-o-notation]] to describe this: O(n^2) for the slow one, meaning time grows with the square of the input size n. Different algorithms have different patterns. Understanding these patterns helps programmers choose which algorithm to use before they even write code. Some patterns are O(n), growing roughly as the data does. Others are O(n log n), a middle ground. Still others are O(n^2) or worse. This analysis is theoretical—it assumes an idealized computer that has no background tasks and a perfect timer. Real computers are messier. But the analysis gives a useful guide to which approaches to try first.

## See also

Related:: [[big-o-notation]], [[benchmarking-practice-overview]]
