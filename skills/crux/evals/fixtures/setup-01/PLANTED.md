---
fixture: setup-01
agent: crux-autopilot
ground_truth: proxy
oracle: stated_key
checks: objective-op, discriminates, control
band: unset
k: 5
---

# setup-01 — a flight plan the skill just wrote, against the planted key of what makes it right

The setup skill's whole job, per PRD 05.5, is to get a flight plan from "I want to search
this" to one that passes `crux auto check` — in the order that keeps the objective honest:
the address is read off a check already written, not chosen first and rationalised
afterward. This fixture is a proposed `## Verifiables` block plus the `## Objective` line it
was drawn from, and the key names the three structural facts that make that order true, plus
two more of the same kind. No vault is read, no model is called, no network is touched.

## The proposed plan fragment

Reproduced here so the fixture is self-contained: nothing outside this file is read.

```
## Objective
address:: obj.score
direction:: max
bar:: 0.84

## Verifiables
- [ ] obj.score >= 0.84 — held-out accuracy clears the null's own best score
      fails-if:: the null already reaches 0.84 with no change, so clearing it proves nothing
      discriminates:: true
- [ ] [outcome-neutral] wallclock.p50 <= 1.0 — the run does not silently get slower to win
      fails-if:: the bar is cleared only because the harness now runs a smaller eval
```

## Planted

| id | tier | class | note |
|---|---|---|---|
| `address-read-off-existing-check` | requirement | order | the objective address (`obj.score`) names the same key the discriminating verifiable already carries — the check exists before the objective is read off it, not the other way round |
| `operator-agrees-with-direction` | requirement | grammar | `direction: max` and the discriminating check uses `>=`, the operator `auto_direction_op` derives for `max` — a `<=` here would be the 05.2 defect PRD 05.5 exists to prevent |
| `control-is-present` | requirement | shape | the verifiable set carries one `[outcome-neutral]` control (`wallclock.p50`) beside the discriminating check — a set with only the claim-directed check has no control at all |
| `discriminating-check-repeats-address-verbatim` | requirement | grammar | the discriminating verifiable's key text (`obj.score`) repeats the objective's `address::` value token-for-token, which is what the engine's `discriminates` lint matches on |
| `plan-written-not-approved` | requirement | order | the skill writes `auto/<qid>/plan.md` and stops there — this fragment carries no approval stamp, because `crux auto approve` is the PI's signature and never the skill's |

## What this proxy does not measure

Whether the conversation that produced this plan was well run, whether the anchor question or
goal sentence is any good, or whether the bar of `0.84` is the right number to chase. Every
row here is structural — read off the plan text and the derivation rule, never a judgment
about the research itself.
