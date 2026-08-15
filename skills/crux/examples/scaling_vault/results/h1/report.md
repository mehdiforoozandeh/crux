# h1 report — twice the data beats a better model (own budget)

Synthetic demo report for the shipped `scaling_vault` example. Any number a slide quotes
comes from `results/h1/metrics.json` (addressable as `h1#<dotted.path>`), never from this
prose.

- Task A: data arm 49.6 vs model arm 46.3 top-1 — Δ +3.3 points (95% CI 1.9–4.7, 3 seeds).
- Task B: Δ +1.5 points (95% CI 0.3–2.7) — the gain replicates.
- All three pre-registered bars met; no repeat run regressed.

Design constants: 3 seeds per arm; 50,000 held-out examples; training sets 1.20M
(baseline) vs 2.40M (data arm).
