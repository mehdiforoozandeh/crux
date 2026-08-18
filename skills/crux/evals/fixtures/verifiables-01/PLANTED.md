---
fixture: verifiables-01
agent: crux-verifiables
ground_truth: proxy
oracle: stated_key
node: h1
verify: no_verifiables, null_approved
reference_n: 4
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# verifiables-01 — write the checks, against an approved null

A hypothesis with an approved null and **no checks at all**. `crux-verifiables` writes them:
kinds, a failure scenario on each, one marked as discriminating, a combination rule, and a
justification for the rule.

**Hand-authored, not lifted.** Spec 10 prescribes *"h59's real 11-verifiable node"*. `h59` is
not in this repo — it is a node in the PI's own research vault, and `evolve-crux`'s scope rule
is that this work never touches one. So the fixture states its own `reference_n: 4` and the
count band is measured against that, not against a number nobody outside one laptop can see.
No real research data enters this repo.

## Planted

| id | tier | class | what a correct set must carry |
|---|---|---|---|
| `discriminates` | requirement | filter | exactly one claim-directed check marked as discriminating against the approved leakage null — a set where every check also passes under the boring explanation is decorative |
| `outcome-neutral` | requirement | filter | at least one control that must pass whatever the claim turns out to be, or a written `neutral_optout` reason |
| `distinct-scenarios` | requirement | filter | no two checks share a failure scenario; the greedy admission test is "name a world where this one fails and every earlier one passes" |
| `rule-declared` | requirement | filter | `all` / `any` / `m-of-n`, justified in one line, with the joint-power cost stated out loud if `all` |
| `count-band` | requirement | economy | the set is at most 6 checks against `reference_n: 4`; the filter is the cap, and there is no numeric cap in the spec |

## What this proxy does **not** measure

Whether the checks are any **good**. All five rows above are structural: they say the set has
the right shape, not that it aims at the right thing. A set of four well-formed, mutually
distinct checks that all miss the point of the claim scores 1.0 here.

`count-band` in particular is a proxy inside a proxy: a count is not a judgment of quality, and
spec 10 says so in its own table. It is here because unbounded growth is the failure mode 06
measured, not because 6 is a meaningful number.
