---
fixture: design-01
agent: crux-design
ground_truth: proxy
oracle: stated_key
verify: one_disease_per_node
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# design-01 — three runs, one disease each

`crux-design` asks one question before the compute is spent: **is there any plausible outcome
of this run from which we would conclude nothing?** A mixed result is a symptom with three
diseases and it never announces which one it has, so the agent checks all three and fixes
exactly one.

Each hypothesis here carries **exactly one** disease. That is deliberate and it is checked at
certification: a node with two diseases cannot tell a correct diagnosis from a lucky one.

## Planted

| id | tier | class | the disease, and who owns it |
|---|---|---|---|
| `compound:h1` | diagnosis | (a) | *"improves relevance **and** cuts serving cost"* — two claims; the two checks answer different ones. Hand off to `crux-critic`; do **not** redesign the run. |
| `non-entailed:h2` | diagnosis | (b) | the claim is about long-tail relevance; the second check reads mean training loss, which is adjacent and does not follow from the claim. Hand off to `crux-verifiables`. |
| `cannot-discriminate:h3` | diagnosis | (c) | a 0.005 effect claimed on a 40-query panel whose own run-to-run spread is 0.02. This one is the agent's to fix. |

The handoffs are half the eval. Absorbing (a) or (b) instead of naming them would violate 09's
one-job rule and rebuild the bias problem those two agents exist to solve — and `crux-critic`'s
cold input is the drafted node *and nothing else*, so a caller passing it context would hand it
the very thing its isolation excludes.

## What this proxy does **not** measure

**Whether the outcome enumeration is complete.** The central question is answerable only over
the outcomes the agent actually thought of, and nothing here can tell a full enumeration from a
lucky one that happened to include the bad outcome. The diagnosis is scoreable; the reasoning
that produced it is not.

Nor does it measure the quality of the proposed fix for (c) — that a larger panel is proposed
is checkable; that the proposed n is *right* is a judgment.
