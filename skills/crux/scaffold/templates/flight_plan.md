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
model:
effort:
agent_failover:
closer: true
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

- [ ] <<address>> <<bar-op>> <<bar>> — <<what reaching this number would mean>>
      fails-if:: <<the world in which this number is reached and the goal is still false>>
      discriminates:: true
- [ ] [outcome-neutral] <<control-key>> <<control-op>> <<control-number>> — <<what this rules out>>
      fails-if:: <<the world in which this control passes and the run is still invalid>>

Legend — how to fill the two checks above:

* `<<bar-op>>` is derived from `direction::`, never written as a literal: it is `>=` when
  `direction: max`, and `<=` when `direction: min`. Derive it every time; a hard-coded
  operator is the 05.2 defect, and it searches against its own bar.
* `<<address>>` must be repeated verbatim from `address::` in `## Objective`. The engine's
  `discriminates` rule matches token-wise, so a paraphrase is a different address and the
  plan is refused.
* `<<bar>>` is the same number as `bar::` in `## Objective` — one number, written twice,
  never two.
* `<<control-op>>` is not derived from `direction::`. A control is outcome-neutral, so it may
  point either way; `obj.score <= 0` under `direction: max` is correct, not a mistake.
* `fails-if::` names the world in which the check passes and the claim is still false. It is
  never a restatement of the check with the words turned around.

## Guidance

_(the PI's standing instructions to workers — appended with `crux auto guide`, never edited)_
