---
type: flight-plan
anchor: <<anchor>>
mode: climb
baseline: <<baseline>>
islands:
island_cap: 3
budget_attempts: 40
budget_hours: 8
budget_model_calls: 400
parallel_total: 1
parallel_island: 1
retries: 2
retention: failed
scorer: python score.py
scorer_timeout: 600
run: python train.py
frozen: score.py, data/
writable: work/, results/
repo:
agent: claude -p "{brief}"
agent_failover:
closer: false
agent_cooldown: 1800
agent_probe: --version
agent_probe_timeout: 20
steward: false
steward_every: 10
stall_attempts: 8
abort_invalid_runs: 3
replicates: 3 seeds
rule: all
rule_m:
created: <<now>>
updated: <<now>>
---

# Flight plan — <<anchor>>

## Goal

<<goal>>

## Objective

address:: <<address>>
direction:: <<direction>>
bar:: <<bar>>

## Null

<<null>>

## Verifiables

- [ ] <<verifiable>>
      fails-if:: <<fails_if>>
      discriminates:: true
- [ ] [outcome-neutral] <<control>>
      fails-if:: <<control_fails_if>>

## Guidance

_(the PI's standing instructions to workers — appended with `crux auto guide`, never edited)_
