# h2 report — the advantage survives at equal compute (it does not)

Synthetic demo report for the shipped `scaling_vault` example. Any number a slide quotes
comes from `results/h2/metrics.json` (addressable as `h2#<dotted.path>`), never from this
prose.

- Equal data: Δ +1.8 points (95% CI 0.5–3.1) — replicates h1's direction.
- Equal compute: Δ −4.6 points (95% CI −6.0 to −3.2) — the sign flips once budgets are
  matched; the baseline improves to 47.9 while the data arm falls to 43.3.
- One bar met, one unmet → verdict partial, derived from the ticks.
