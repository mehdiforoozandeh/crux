---
fixture: critic-01
agent: crux-critic
ground_truth: proxy
oracle: stated_key
verify: prose_cap, scenario_gap
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# critic-01 — four drafts, three of them broken

`crux-critic` sees **the draft alone**: no vault, no history, no conversation. Each planted
finding is therefore something readable from one node's text.

Three of the four drafts are broken in a different way, and the fourth is sound — because a
critic that flags everything is as useless as one that flags nothing, and only a clean draft
in the set can catch that.

## Planted

| id | tier | class | what is wrong with it |
|---|---|---|---|
| `over-cap:h1` | finding | over-cap | 996 words of prose against the 400-word cap; the meeting transcript was pasted in rather than compressed |
| `compound:h2` | finding | compound | *"lowers latency **and** reduces memory pressure"* — two claims, one node, and each check answers a different one |
| `redundant:h3` | finding | redundant | both checks declare the same failure scenario, *"the index builder is not actually faster"*; there is no world where one fails and the other passes |
| `sound:h4` | finding | clean | one claim, falsifiable, in budget, one check with its own scenario. Flagging this is a false positive. |

Two of the four are cross-checked against the engine at certification time — `prose_words`
really does put h1 over the cap, and `scenario_gap` really does flag h3 — so the key cannot
drift away from the fixture without going red.

## What this proxy does **not** measure

**Whether the critic's reasoning is right, only whether its conclusion matches.** `compound:h2`
is the clearest case: an agent that flags h2 for the wrong reason scores the same as one that
names the "and". *"Is this one question or three"* has no parser, and spec 10 permits a judge
here — but a judge is a model call, which this harness does not make.

`over-cap:h1` and `redundant:h3` are the strongest rows, because a deterministic check already
knows the answer. `sound:h4` is the weakest: a critic could stay silent on it for any reason,
including having nothing to say.
