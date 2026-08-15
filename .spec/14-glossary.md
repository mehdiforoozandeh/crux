# Spec 14 — Project glossary

**Label:** `glossary` · **Status:** ☐ todo
**Relates to:** [03 LLM wiki](03-llm-wiki.md) (definitions from literature),
[09 specialized agents](09-specialized-agents.md) (adds one agent to the roster)

## Goal

One `glossary.md` per vault holding the project's specialist vocabulary, so that an agent
knows which words it may use bare and which it must gloss — and so the PI is never talked at
in terminology they have not agreed to.

## The reframe that decides everything else

The PI's definition: *terms the PI is fully aware of.*

That makes this **not a definition store — it is a model of the PI's vocabulary.** Presence
means the agent may use the word without explanation. Absence means gloss it, or ask. The
one-line definition each entry carries is for the PI to read back later; the *membership* is
what the agent consumes.

Read that way, `glossary.md` is the persistent, per-vault extension of the PI's standing
vocabulary rule (*"free: anything already said in this conversation, plus standard genomics,
ML, bio and stats terms; anything else you bring in, gloss it in the same breath"*). The
global rule covers a session. The glossary covers a project, across years.

## Why the wiki cannot do this

[03](03-llm-wiki.md) already lists *definitions* in scope and ships a `concept` category. But
`wiki_schema.md` states a **hard flow rule**: *literature → wiki, never the reverse; a wiki
page must never cite a q/h tree node; findings never enter the wiki.*

So the wiki structurally **cannot** hold vocabulary this project coined — *"detection floor"*,
*"capacity certificate"*, *"the separability condition"*. Those are exactly the terms most
likely to be used bare at a PI who has never had them defined, because the agent invented them
and therefore finds them obvious.

The boundary is **depth, not origin**:

| | glossary | wiki |
|---|---|---|
| holds | one line per term, any origin | a full page, literature-derived only |
| answers | *may I use this word bare?* | *what does the literature say about it?* |
| project-coined terms | yes | forbidden by the flow rule |
| relationship | may point at a wiki page for depth | never points at the glossary |

## Design

### 1. Storage

`glossary.md` at the vault root, one per vault, **starting empty**. A new project has no
shared vocabulary yet, and seeding one would put words in the PI's mouth.

Two sections:

```markdown
## Terms
- **detection floor** — the smallest effect this assay could distinguish from noise.
- **capacity certificate** — evidence that a probe had enough capacity to fit, so a null
  result reflects the signal rather than the probe. See [[wiki/probing]].

## Not jargon
_(checked, dismissed, never proposed again)_
- attenuation
- held-out
```

The decline list is not bookkeeping — without it the same term is re-proposed on every
audit, forever, and the PI learns to ignore the prompt.

### 2. Centrality — the rule, and which way it runs

A term qualifies only when it is **central**, which is computable:

> the term appears in **≥ 2 distinct** nodes or wiki pages, **or** appears in any node title
> or wiki page title.

Recurrence is the PI's own criterion (*"becoming central"*), and it means a term mentioned
once and never again never interrupts anyone. Ingesting a paper that introduces fifteen terms
produces candidates only for those that connect to something already in the vault.

**The engine does not generate the candidate list. It filters one.**

This inverts the obvious arrangement, and the inversion is the load-bearing design choice
here. Deterministic term *extraction* from prose does not work for the terms that matter:
*"detection floor"*, *"capacity certificate"* and *"the separability condition"* are bigrams
and trigrams, not tokens, and n-gram frequency over research prose is noisy in both
directions — it misses real multi-word jargon and floods the list with ordinary phrases that
happen to recur.

So:

> **The agent proposes candidate terms freely. The engine filters them by the centrality
> rule.**

The deterministic part stays the **goalpost** rather than the generator — which is what
[09](09-specialized-agents.md)'s rule 1 actually asks for (*"use the deterministic check as
the goalpost that guides the agent"*), not "do everything in code." An agent reading vault
prose recognizes a coined multi-word term effortlessly; counting where it occurs is exactly
what an agent is bad at and code is good at. Each side does the half it is suited to.

The filter is still the whole guarantee: a term the agent finds interesting but which appears
once is silently dropped, and never reaches the PI. So agent enthusiasm cannot become PI
interruptions.

### 3. The three-way split

| layer | job |
|---|---|
| **agent** — `crux-glossary` | reads node prose and wiki pages; proposes candidate terms, including multi-word ones; judges the thing code cannot — specialist jargon or public knowledge. Proposes only; never writes |
| **engine** — `crux validate --check=glossary`, `--json` | for each proposed term, count occurrences and title hits; drop anything failing the centrality rule; drop anything already in the glossary, the decline list, the wiki index, or the shipped common-English stoplist; emit survivors with where they appear and how often |
| **PI** | yes / no per surviving proposal |

The agent cannot see the conversation that coined the term. That is the same anti-bias
architecture as `crux-verifiables`, and it exists for a sharpened version of the same reason:
**the agent that coined the jargon is the worst possible judge of whether it is jargon** — it
knows what the word means, so the word reads as obvious.

Note the ordering consequence: the *counting* is deterministic and re-runnable, so a proposed
term that fails centrality today and recurs next month passes then, with no memory needed
beyond the vault itself.

### 4. When it runs, and how you are asked

Runs as a `validate` check, so it rides the existing lint pass and warns the way the 400-word
cap does. No new trigger, no per-write agent spawn.

Proposals are answered **inline, one at a time**, as a yes/no. A batch queue was considered
and dropped: the PI's stated preference is inline, and centrality already suppresses the bulk
case that made batching sound necessary.

### 5. Scope — both, and disk is where it is checked

The rule applies to conversation *and* to node prose. Enforcement lives on disk, because that
is where a term outlives the session and confuses future-you, and because disk is the only
side an engine can check. Conversation stays best-effort — but the agent that has the
glossary in context uses the project's words because it has them, not because it is forbidden
others.

## Decisions

| decision | rationale |
|---|---|
| the glossary is a model of the PI's vocabulary, not a dictionary | the PI's own definition; it decides membership semantics, the decline list, and what the agent consumes |
| separate from the wiki | the wiki's one-way flow rule forbids project-coined terms, which are the highest-risk ones |
| starts empty | a seeded glossary asserts the PI knows words they may not |
| centrality = ≥2 appearances or any title | computable, matches "becoming central", suppresses the bulk-ingest case |
| **the agent proposes terms; the engine filters by centrality** | multi-word jargon cannot be extracted deterministically, and that is exactly the jargon that matters. Rule 1 asks for the deterministic check as the *goalpost*, not as the generator. The filter still bounds what reaches the PI |
| a subagent judges, not the main conversation | the coiner cannot judge its own coinage; context isolation is the mechanism |
| the agent proposes, never writes | membership is a claim about the PI, so only the PI can make it |
| decline list lives in `glossary.md` | asked once, ever; and the file honestly records both halves of the vocabulary model |
| runs as a `validate` check | no new trigger; rides a pass that already exists |
| inline yes/no, one at a time | PI preference; centrality removes the reason to batch |

## Rejected alternatives

- **Instruction only** — a rule in the crux skill saying "never use undefined jargon."
  [06](06-node-economy.md) settled this class of fix: the skill already said "keep the science
  explicit" and produced 5,725-word nodes. *Instructions were never the binding constraint.*
- **A skill instead of an agent.** Fails [09](09-specialized-agents.md)'s rule 5 — this is a
  bounded job with a deterministic cold input, not a conversational one.
- **Glossary entries as wiki pages.** Breaks the wiki's flow rule for exactly the terms that
  matter most, and turns a one-line membership check into a page-authoring task.
- **First-appearance candidacy, no threshold.** Proposes terms that never recur; trains the PI
  to dismiss the prompt.
- **Agent-judged centrality with no numeric rule.** Unassertable, and drifts — the failure
  [06](06-node-economy.md) documented.
- **A batch review queue.** More machinery than the volume justifies once centrality filters.
- **Re-asking about declined terms.** Cheapest engine, worst experience; the PI answers the
  same question for months.

## Open questions

- The contents and provenance of the shipped common-English stoplist.
- How the engine counts occurrences of an agent-proposed **multi-word** term — exact string
  match is brittle across inflection and hyphenation (*"detection floor"* vs *"detection
  floors"* vs *"detection-floor"*). Normalizing case and trailing plurals is probably enough;
  anything more clever risks over-matching. This is the one remaining piece of the inverted
  design that is not settled.
- Whether an entry may be edited once accepted, and whether editing re-opens PI approval. A
  definition that silently drifts is worse than none.
- Whether the glossary should be loaded into context on every crux-skill trigger, or fetched
  on demand. Always-loaded is simpler and costs tokens on every turn.
- Whether `validate` should warn on undefined jargon in node prose, or only collect
  candidates. Warning makes it enforcement; collecting makes it a suggestion.

## Work items

- ☐ `glossary.md` template, `## Terms` + `## Not jargon`, created empty at `init`
- ☐ Centrality **filter** — takes agent-proposed terms, counts occurrences and title hits,
  subtracts glossary / decline list / wiki index / stoplist, emits survivors
- ☐ Multi-word occurrence counting (case + plural normalization); settle the open question
- ☐ Shipped common-English stoplist
- ☐ `crux validate --check=glossary` with `--json` candidate output
- ☐ `crux-glossary` agent definition — proposes terms from vault prose, judges jargon vs
  public knowledge, never writes
- ☐ Inline yes/no PI flow; accepted terms appended; declined terms recorded
- ☐ Skill rule: use glossary terms bare, gloss everything else, propose on centrality
- ☐ `ENGINE_VERSION` bump + proof an old vault without `glossary.md` still loads

## Acceptance criteria

- A fresh vault has an empty `glossary.md`, and `validate` is clean.
- A term **proposed by the agent** but appearing in exactly one node is dropped by the filter
  and never reaches the PI; the same term, once it appears in a second node, survives.
- A term in a node title survives on its first appearance.
- A proposed **multi-word** term is counted correctly across the vault — the case the whole
  inverted design exists to handle.
- `crux-glossary` sees vault prose, the glossary and the decline list, and **no** conversation
  text.
- A declined term never appears as a candidate again.
- Ingesting a wiki page with fifteen new terms produces candidates only for those meeting the
  centrality rule.
- An old vault with no `glossary.md` loads and validates.
- `selftest.py` passes with a grown assert count.
