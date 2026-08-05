# Spec 09 — Specialized agents

**Label:** `agents` · **Status:** ☐ todo
**Depends on:** [06 node economy](06-node-economy.md) (for the `--json` CLI surface)
**Supersedes parts of:** [05 autoresearch](05-autoresearch.md)

## Goal

Decompose crux's agent work into narrow, single-job subagents with deterministic toolbelts —
so that the parts of the loop that can be checked by code *are*, and the parts that need
judgment are done by an agent that cannot inherit the bias of the conversation that produced
the thing it is judging.

## Rules of thumb (binding on every agent in this spec)

1. **As little AI as necessary, as much deterministic code as possible.** Identify each
   verifiable part of the work and do it deterministically — or use the deterministic check as
   the *goalpost* that guides the agent, possibly in a loop.
2. **One job per agent** — narrow, well specified, with only the relevant context.
3. **Every crux agent has vault access.**
4. **Assume zero context.** Each subagent starts fresh: no conversation history, no files
   already read. The agent body spells out the workflow — when invoked → steps 1–N → output
   format.
5. **When not to use one:** iterative back-and-forth, shared multi-phase context, quick edits,
   or latency-sensitive work. Subagents pay a cold-start cost. **A reusable prompt that needs
   main-conversation context is a Skill, not an agent.**

Loopability is a nice-to-have for big jobs (migration, vault repair), and is only safe where
"done" is a deterministic predicate.

## Rule 1, applied first — what stops being an agent

Applying rule 1 honestly dissolves roughly half the naive roster into engine code:

| proposed as an agent | actually |
|---|---|
| audit health checks — over-cap nodes, orphan tasks, unresolvable artifacts, gate backlog, unrun-idea pileup | deterministic predicates → new checks in `crux validate` |
| version bridging — old vault gains new-format fields | mechanical schema rewrite → a `crux migrate` verb |

What remains agent work is where the **input is unstructured and the output needs judgment**.

### The toolbelt lives in the CLI

An agent with many deterministic tools is the right shape — but those tools must be **crux CLI
verbs**, not scripts bundled with the agent definition. Then `selftest.py` can assert them,
the cockpit can consume the same output, and the PI can run any of them by hand when the agent
is not trusted.

This forces a change crux has not made: the CLI prints for humans. An agent toolbelt needs
`--json`, individually selectable checks, and meaningful exit codes. Settled shape:
**`--json` on the existing verbs plus a `--check=<list>` selector**, rather than one verb per
check — checks are not user-facing concepts and N new verbs bloats the surface.
*(Tracked in [06](06-node-economy.md).)*

## The roster

| agent | cold input | judgment it supplies |
|---|---|---|
| `crux-migrate` | a research repo path | read unorganized code/docs/results → draft a **seed file** |
| `crux-close` | hypothesis id + results directory | read run output → per-box ticks + findings draft |
| `crux-audit` | vault path | drive the deterministic checks in a loop; propose fixes |
| `crux-critic` | a drafted node | is this one question or three? is this falsifiable? is it over cap? |
| `crux-null` | engine-built brief | name the null and the boring explanations |
| `crux-verifiables` | `{claim, approved null}` | write checks that discriminate |
| `crux-tests` | a requirement / RD | write tests against the requirement, never the code |

`crux-rd` is deliberately **not** here — it is a skill. See [07](07-rd-layer.md).

### Why `crux-critic` exists

Every other agent runs *after* a node exists. The bloat happens *while* it is written. A
bounded reviewer that sees the drafted node **and nothing else** — no vault, no history —
attacks it at the moment of creation. Context isolation is the entire mechanism: it cannot
pour the vault into the node because it cannot see the vault.

## The anti-bias architecture

This is the substantial part of the spec.

### The problem

crux pre-registers verifiables. Pre-registration defends against changing the bar *after*
seeing results — it says nothing about **who sets it**. An agent that has just spent an hour
helping the PI argue for a hypothesis will pick a bar that hypothesis clears. Same failure the
`tdd` skill names at the value level (*"expected values must come from an independent source of
truth"*), generalized from values to the whole test.

The same applies on the software side: an implementation agent writing its own tests tests
what the code *does*, not what was *required*.

### Isolation boundary — facts yes, advocacy no

The fresh agent reads the shared factual record a skeptical colleague would read: the
hypothesis statement, the question, linked wiki pages, prior findings. It must not see the
conversation that produced the hypothesis.

Two agents, not one, because **the exclusion differs**:

- `crux-verifiables` gets the claim and excludes the **reasoning** that produced it
- `crux-tests` gets the requirement and excludes the **implementation**

### The engine builds the brief, not the parent agent

Zero context is worthless if the parent writes the prompt. *"Verify that JEPA improves
imputation"* has already told the fresh agent which way to lean, and selective evidence in the
brief finishes the job. The parent's bias leaks straight through the one channel it controls.

**Fix, and it is rule 1 again: `crux brief <node> --json` emits a payload assembled
deterministically from vault state** — question title, hypothesis claim, linked wiki pages,
prior findings under that question, available data and metrics. The parent agent never authors
a sentence of it, so bias has no channel. And it is testable: same node, same brief, every
time.

One field-level consequence: **the brief carries the hypothesis claim but not its
`## Problem Statement`.** That section is precisely where the advocacy lives.

### The null

Residual leak that cannot be engineered away: the hypothesis title is itself directional —
*"masked-token beats masked-stem"* presumes a winner. The answer is not to neutralize it but to
push against it.

**`## Null`** — a new one-line section on the hypothesis. The null is the **boring
explanation**: the cheapest way this result could be trivially true.

The vault already invented this by hand. q21 states *"a certified zero is the point; an
uncertified zero is worthless"*, then builds a detection floor and a negative control to earn
one. That is a null and its discriminating tests, and it cost 5,725 words because the schema
had nowhere to put them.

**Asymmetric, not a symmetric dialectic.** Two agents arguing opposite sides produce two
advocacy lists and a merge problem. The adversary's job is not to write competing verifiables
— it is to name the null. Then the verifiables must discriminate between the claim and that
null. q21's negative control (a permuted covariate through the *same* input channel, so extra
capacity cannot be the winner) is exactly this move.

**PI-gated.** crux's leash already makes the verifiable bar the PI's call, and the null *is*
the bar restated. The gate sits between the two agents: the PI reads one line, approves or
sharpens it, and only then are checks written against the approved null.

### Preventing the new agents from over-engineering

The agents built to fix bloat can bloat. Instructions will not hold this — proof: the crux
skill already says "keep the science explicit" and produced 5,725-word nodes. So the goalposts
go in code.

**Null (`crux-null`):** exactly one, one sentence, ≤25 words, and it must name a family from a
**closed confound vocabulary** — capacity, chance, leakage, selection, normalization artifact.
The agent picks a family and names the instance rather than composing something baroque.
Deterministic to check, and structurally prevents an exotic null because nothing exotic is on
the menu.

**Verifiables (`crux-verifiables`): no numeric cap.** A cap is arbitrary and truncates rather
than sharpens. Instead, a **logical filter every verifiable must pass**:

> Two verifiables are redundant if they fail for the same reason. They are distinct if the
> agent can name a world where one fails and the other passes.

Applied **greedily, as each is written** — v4 is admitted only if the agent can name a world
where v4 fails and v1–v3 all pass. That is what replaces the cap: the agent stops when it runs
out of worlds. (h59 currently carries 11 verifiables and h60 carries 10; under this filter
both collapse to roughly four.)

Note the sharpening: the requirement is orthogonal **failure modes**, not orthogonal outcomes.
Verifiables under one hypothesis are *supposed* to correlate — they are consequences of the
same claim, so if it is true most pass together. Demanding statistical independence would mean
they are not testing the same thing.

**Two-part filter, total:**
1. at least one verifiable discriminates against the declared null, and
2. every verifiable has a failure mode no other one shares.

Orthogonality alone would admit three peripheral checks.

**Deterministic residue: each verifiable carries its failure scenario as a field.** The engine
cannot judge orthogonality, but with the scenarios written down redundancy is visible at a
glance to the PI and to `crux-critic`.

## Decisions

| decision | rationale |
|---|---|
| deterministic checks become engine verbs, not agent judgment | rule 1 |
| toolbelt = CLI verbs, not agent-private scripts | selftest can assert; cockpit reuses; PI can run by hand |
| `--json` + `--check=<list>`, not a verb per check | checks aren't user-facing concepts |
| engine builds the brief | the only way isolation is real rather than nominal |
| brief excludes `## Problem Statement` | that is the advocacy channel |
| null and verifiables are two agents | fusing them lets one agent pick a null it can write neat checks for — convenience bias; and it removes the PI's approval point |
| PI approves the null | the leash already makes the bar the PI's call |
| `## Null` one-liner, closed vocabulary, ≤25 words | anti-cleverness goalpost in code |
| greedy admission test, no numeric cap | self-limiting and non-arbitrary |
| failure-scenario field on **every** verifiable | every one had to pass the test to exist |

## Rejected alternatives

- **Splitting the crux skill by verb** (`crux-ask`, `crux-hypothesize`, `crux-ideate`, …).
  Three reasons: it does not address the cause (instructions were never the binding
  constraint); six near-synonymous skill descriptions degrade trigger routing rather than
  sharpening it; and the leash is cross-cutting, so every split is another fragment that can
  forget it. **One `crux` skill stays the conversational front-end** — model, verbs, leash,
  economy rules — and agents handle the bounded jobs where context isolation is the mechanism.
- **A `discriminating` flag on verifiables that the verdict rule respects.** Honest
  consequence of the null design — passing four decorative checks while the discriminating one
  fails should not read as `supported` — but rejected as over-engineering. `## Null` as a
  one-liner, no flag, no change to verdict derivation; the rule lives in the skill and is
  enforced by the brief, since `crux-verifiables` can see nothing else.
- **A symmetric dialectic pair** (supporter + refuter). Produces two advocacy lists and a merge
  problem. Asymmetric instead.
- **A numeric cap on verifiables.** Arbitrary; truncates instead of sharpening.
- **Strict outcome-orthogonality between verifiables.** Too strong — see above.
- **`crux-rd` as an agent.** Fails rules 4 and 5. See [07](07-rd-layer.md).

## Open questions

- **`crux-close` internals.** Undefined. It reads results and proposes ticks + findings, but
  the tick proposal is a verdict input and the leash says verdicts are PI-accepted — so the
  output contract needs pinning.
- **`crux-audit` internals.** Undefined beyond "drives the deterministic checks in a loop."
  Loop-until-clean is safe only where clean is a deterministic predicate: schema migration and
  health audit qualify, **scientific staleness does not.**
- Whether `crux-critic` and `crux-verifiables` stay separate. Critic judges form, verifier
  authors substance — rule 2 says separate, but they are adjacent.
- The exact contents of the closed confound vocabulary.

## The staleness warning

The PI's request for an agent that "rescans old vaults and updates them" fuses three jobs.
They must stay separate:

1. **Schema migration** — old vault lacks new-format fields. Mechanical, deterministic,
   ungated, loop until `validate --strict` exits 0.
2. **Health audit** — over-cap nodes, orphan tasks, gate backlog, unresolvable artifacts.
   Deterministic, loopable.
3. **Scientific staleness** — "our older questions and hypotheses are outdated." **This is not
   an audit.** It is a claim that recorded answers no longer reflect what we now know: a
   research judgment on the same footing as `answer` and `pursue`, PI-gated, one node at a
   time.

An agent that silently rewrites scientific content under cover of version bridging is exactly
what the leash exists to prevent. The agent may *surface* staleness candidates — "q4's answer
predates six findings that cite it" is computable — and stops there.

## Work items

- ☐ Move audit health checks into `validate` as selectable checks
- ☐ `crux migrate` verb for schema bridging
- ☐ `crux brief <node> --json` — deterministic brief assembly
- ☐ `## Null` section in `templates/idea.md`; closed confound vocabulary; ≤25-word check
- ☐ Failure-scenario field per verifiable — schema, CLI (`-v` gains a second argument),
  snapshot, cockpit
- ☐ `validate` check: ≥1 verifiable discriminates against the null; every verifiable has a
  non-empty distinct failure scenario
- ☐ Agent definitions: `crux-migrate`, `crux-close`, `crux-audit`, `crux-critic`, `crux-null`,
  `crux-verifiables`, `crux-tests`
- ☐ PI gate between `crux-null` and `crux-verifiables`
- ☐ `ENGINE_VERSION` bump + migration proof

## Acceptance criteria

- `crux brief h59 --json` is byte-identical across runs and contains no text authored by a
  calling agent.
- The brief contains the hypothesis claim and excludes `## Problem Statement`.
- `validate` rejects a hypothesis whose null exceeds 25 words or names no confound family.
- `validate` rejects a hypothesis where no verifiable discriminates against the null.
- Every verifiable has a non-empty failure scenario.
- Re-running `crux-verifiables` on h59's fixture yields materially fewer than 11 verifiables.
- `selftest.py` passes with a grown assert count.
