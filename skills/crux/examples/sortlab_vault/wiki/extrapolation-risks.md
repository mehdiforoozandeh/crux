---
type: wiki
title: Predicting past your data
summary: Guessing performance at sizes you never tested is risky because patterns change outside the tested range.
category: concept
sources: raw/teacher-note-reading-a-graph.txt
---

# Predicting past your data

A curve that fits your data perfectly can give wildly wrong predictions beyond your data.

## Background

You measure sort times for lists up to 10,000 items and fit a curve. The curve fits perfectly. You then predict the time for 100,000 items by extending the curve far beyond your data. But at 100,000 items, a new behavior might appear. Thermal throttling might kick in, or garbage collection might hit harder, or a hardware cache might saturate. The algorithm might even switch to a different strategy for large inputs. All of these would violate the curve you fitted to smaller sizes. This is why professional benchmarkers are cautious about extrapolation. They measure at sizes as close to their target as they can afford. When extrapolation is unavoidable, they mark it clearly as a guess. The further you extrapolate, the worse your prediction. Predicting one size larger than your data is often reasonable. Predicting ten times larger is risky. Predicting a hundred times larger is almost certainly wrong. This is why [[curve-fitting-basics]] is useful for understanding patterns in your measured data but dangerous for prediction far outside it.

## See also

Related:: [[algorithm-analysis-overview]]
