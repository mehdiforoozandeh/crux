"""Baseline candidate: a 5x5 grid of circles of radius 0.1, plus one small circle in the
gap at the centre of four grid circles. Sum of radii = 2.5 + 0.1*(sqrt(2) - 1) - margin.

Contract: print exactly one JSON object {"circles": [[x, y, r], ...]} with 26 triples on
stdout; nothing else on stdout. The scorer checks the printed numbers exactly, so radii
from floating-point arithmetic are shrunk by a small margin first.
"""
import json
import numpy as np

MARGIN = 1e-12

g = [0.1, 0.3, 0.5, 0.7, 0.9]       # literals: 0.1 + 0.2*k in floats overlaps by 4e-17
circles = [[x, y, 0.1] for x in g for y in g]
gap_r = 0.1 * (np.sqrt(2.0) - 1.0) - MARGIN      # tangent to the four circles around (0.2, 0.2)
circles.append([0.2, 0.2, float(gap_r)])
print(json.dumps({"circles": circles}))
