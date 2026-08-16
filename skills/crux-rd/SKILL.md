---
name: crux-rd
description: >-
  Write the Requirements Document for a crux node — the design detail that does not fit, and
  should not fit, inside a 400-word question or hypothesis. An RD is one immutable design
  document per node, living in `rd/` beside the tree, linked from the node, outside the
  roll-up: the estimand and its bound, the probe ladder, the negative control, the known
  distortion that must travel with every result. You do not interview and you do not
  re-derive — you write up the design that has just been settled in conversation with the PI,
  and you apply the write-vs-skip filter that stops every node from growing one. A design
  change is never an amendment: it is a new RD that supersedes the old, and the chain is the
  reasoning history. Invoke explicitly — the PI decides when a design has settled.
license: MIT
disable-model-invocation: true
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  spec: ".spec/07-rd-layer.md"
  requires: "the crux skill, installed as a sibling of this one (shares its engine at <crux skill>/scaffold/)"
  notice: "Borrows ADR mechanics (immutability, supersession, an explicit write filter); no third-party code."
---

# crux-rd — the design document a node cannot hold

crux caps a node's prose at **400 words**. That cap exists because nodes measured in the
thousands of words stopped being readable by the PI they exist to serve. But a cap with no
outlet just makes prose denser. **This is the outlet.**

An RD is where design detail goes **to be readable, not to hide.** The node's TL;DR must
still stand alone: a reader who never opens the RD still knows what is being asked and what
would settle it. If moving text into an RD makes the node unintelligible, the move was wrong.

## When you are invoked

**Only when asked.** This skill ships `disable-model-invocation: true` and means it. The
design being written up **lives in the conversation that just happened with the PI** — that
is the whole reason this is a skill and not an agent. From a cold start you would either
restate the node or re-derive the design badly.

So: no interview, no research phase, no "shall I write this up?" offered unprompted. When the
PI says the design has settled, you synthesize what was already discussed.

## The write-vs-skip filter — apply this *before* writing anything

Without an explicit filter, every node grows an RD, and the vault has simply moved its
bloat one directory over. **An RD is warranted when at least one of these holds:**

1. **The design would exceed the 400-word prose cap on its own.** Not the node — the design.
   If the whole thing fits in `## Idea / Hypothesis` inside budget, it belongs there.
2. **The design makes a choice a reader would otherwise re-litigate.** There is a rejected
   alternative worth recording. Research reasoning lives in the branch that was *not* taken,
   and it is the half that gets lost.
3. **The design carries a known distortion that must travel with every result.** A pooling
   scheme that biases small strata, an attenuation you accept, a proxy that is not the thing.
   If a reader of the findings needs to know it, it has to be written somewhere durable.

**Explicitly not warranted: a hypothesis whose design *is* its verifiables.** That is the
common case. Pre-registered checks with a metric, a baseline and a threshold are already a
complete design, already structured, and already exempt from the cap. Writing an RD for one
adds a file and no information.

When the filter says skip, **say so and stop.** "That design is its verifiables — it does not
need an RD" is a correct, complete answer.

## Writing one

```bash
crux rd <node-id> "<title>"          # a question or a hypothesis; the project root and syntheses do not carry RDs
```

That creates `rd/<slug>.md` and writes the `RD::` backlink into the node, beside `Parent::`.
Then you fill the template's sections:

| section | what goes in it |
|---|---|
| **Context** | what forced this design — the constraint, the finding, the question |
| **Out of scope** | an explicit fence. What this design deliberately does not cover, binding on the node and its children |
| **Design** | the substance |
| **Considered options** | the alternatives, and why each lost |
| **Consequences and known distortions** | what this gets wrong on purpose, and what must travel with every result |
| **Supersedes** | the chain (forward only — see below) |

Two habits worth keeping. **Write for a reader who was not in the conversation** — that is
the person the RD exists for, and it is you in six weeks. And **after writing, re-read the
node**: if its TL;DR no longer stands alone, move a sentence back.

## An active RD is **never amended in place**

This is the rule the whole layer is built around. When a design changes:

```bash
crux rd <node-id> "<new title>" --supersedes <old-slug>
```

That writes a new RD, flips the old one to `superseded`, and re-points the node. The chain
is the reasoning history — what was believed, and what replaced it. Editing the live document
instead destroys exactly the record that makes a design reviewable, which is the failure this
layer was built to fix: a node body treated as the only durable record accumulates
`AMENDED` markers until nobody can tell what the design currently is.

**The engine does not police this.** `crux validate` checks that the link resolves, that the
two ownership records agree, that only one design is live, and that the chain is acyclic — it
does **not** detect an edit to a superseded RD, by design. **`git log -p rd/<slug>.md` is the
audit trail**, the same call crux already makes for a node's decision history. So the
discipline is yours: if you find yourself editing a superseded file, stop and supersede
instead.

The same rule you already follow for nodes applies here: **on a PI ruling, edit the node; the
diff is the history.** For an RD, the ruling writes a *new* document.

## What an RD is not

- **Not evidence.** It never enters the roll-up, never moves `ledger_counts`, never trips the
  review gate. Verdicts come from verifiables; an RD is a document.
- **Not a work list.** Open work items are a taskhub concern, not a design document. An RD
  that accumulates TODOs is turning into the node it was meant to relieve.
- **Not a changelog.** Decision history goes to git.
- **Not literature.** Background, prior methods and baselines are the wiki's job
  (`crux-wiki`), and the flow is one-way: the wiki may never cite an RD or a tree node. An RD
  may cite the wiki freely — grounding a design in prior work is the flow rule working.

## Checking your work

```bash
crux validate --check=rd     # link resolves · ownership agrees · one live design · chain acyclic
crux validate                # the whole vault, RD lint included
```

If a node is still over the 400-word cap after you have moved its design out, the remainder
is either work items or history — and neither belongs in the node either.
