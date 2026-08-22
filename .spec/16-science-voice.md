# Spec 16 — Science voice: the invisible notebook

**Label:** `voice` · **Status:** ☑ done — landed 2026-08-22 as engine 3.2, [PRD 16.1](../docs/prd/16.1-science-voice.md)
**Relates to:** [14 glossary](14-glossary.md) (the mirror-rule machinery this extends),
[13 situate & design](13-situate-and-design.md) (owns the anchoring lint this amends),
[09 specialized agents](09-specialized-agents.md) (crux-situate's contract changes),
[10 agent evals](10-agent-evals.md) (the harness the persona eval joins)

## Goal

The agent talks to the PI in the language of science. crux is the lab notebook the agent
keeps in the background — the PI should be able to work for weeks without noticing it is
running. Node IDs and crux vocabulary appear in chat only when the PI brings them there.

The frame that decides everything: **the PI is the advisor, the agent is the grad student,
crux is the grad student's notebook.** A grad student does not tell their advisor "q19 is
solved" — the advisor would ask what the hell q19 is. The student says the science: *"I
think we've answered whether masked-token pretraining beats masked-stem — the three checks
we agreed on all passed. Do you buy it?"* The advisor may leaf through the notebook (the
cockpit, the tree) whenever they want — when writing a paper, when auditing progress — and
then the notebook's vocabulary is theirs to use. But the default channel, daily
conversation, is science.

This is a control inversion. The current UX is crux-first: the engine is the protagonist
and the PI learns its vocabulary to operate it. The intended UX is PI-first: the PI does
science, and the notebook trails behind them, silently kept.

## Motivation

Today the agent-to-PI channel is ID-led, and it is **taught by example**, which binds
harder than any rule:

- `skills/crux/SKILL.md` — the modeled session dialogue surfaces raw commands and IDs to
  the PI: *"→ `crux ask \"...\"` (`q1`). First hypothesis under it?"*. The gate prose
  speaks in IDs ("recording `h44:refuted` … Closing h44 is still `crux close h44`").
- `README.md` — the marketing transcript: *"crux: That's your open question q1"*, *"h1 →
  supported"*.
- `skills/crux/evals/fixtures/situate-01/submissions/perfect.json` — the gold answer for
  the one human-facing agent opens *"Resolved: q1 — …"* and speaks in IDs throughout.

Two mechanisms **actively enforce** ID-led speech:

- `agents/crux-situate/AGENT.md` mandates "name the ids … in the first line of your
  answer".
- `engine.py`'s `situate:unanchored` lint **fails** an answer whose first line does not
  name the anchor ids; `evals.py`'s oracle scores findings as ID tokens (`untested:h2`).

And two existing rules already argue this spec's side — the change resolves an internal
contradiction rather than importing a new philosophy:

- The glossary guardrail (SKILL.md): *"the PI … should never be talked at in terminology
  they have not agreed to."* It currently governs domain jargon only. `q19` and "review
  gate" are terminology the PI has not agreed to.
- `crux-situate`'s own plain-language rule: *"No crux vocabulary the PI has not agreed
  to"* — in direct tension with its "name the ids first" rule, in the same file.

## Design

### 1. The mirror rule over the crux lexicon

All crux vocabulary is unagreed jargon under [14](14-glossary.md)'s model of the PI's
vocabulary. That covers **node IDs** (`q19`, `h72`, `t91`, `s1`) and **process terms** —
review gate, verifiables, null, synthesis, verdict, taskhub, vault, node, seed, RD, and
the rest of the lexicon this spec's build will enumerate. The agent never introduces any
of it in chat. The PI using a term licenses it back — the mirror rule (this spec's
coinage).

Plain science words are free: question, hypothesis, evidence, finding, experiment, check,
result. They are standard scientific language, not crux coinage — the grad student does
not owe a gloss for "hypothesis."

**Persistence is split.** Node IDs are licensed **per-conversation only** — they are
ephemeral handles, and "the PI knew what q19 was in March" will not be true in April.
Process terms can graduate **permanently** through the existing `crux-glossary`
PI-approval flow: a PI who says "gate" repeatedly gets it proposed as agreed vocabulary,
and once in `glossary.md` it is licensed for good. No new machinery; the glossary was
already "a model of the PI's vocabulary," and this extends its domain from project jargon
to crux's own.

### 2. Silent bookkeeping

Routine notebook-keeping — opening questions, recording hypotheses, opening and closing
tasks, updating findings — is **fully silent**. No "registering this as h1?", no command
echo, no permission-asking. The grad student does not ask the advisor's leave to write in
their own notebook. The engine calls are visible in the tool-call transcript for a PI who
looks, and the cockpit shows the result; the conversation itself stays 100% science.

### 3. Signature moments

crux's gates survive untouched **semantically** and become invisible **mechanically**.
Where the PI's sign-off is required — approving a synthesis, closing a hypothesis on its
ticks, approving a null, accepting a task's conclusion — the agent asks the natural
science question and shows the actual content being signed:

> "Do you think the question of X is sufficiently answered, given A, B, and C? Here is
> how I'd summarize what we learned: …"

The draft summary is shown because it is what gets recorded as the standing answer — the
PI must not sign prose they have not read. The checks are presented as plain statements of
what each showed, not as `☑ v1`. A conversational "yes, that's settled" **is** the
signature; the agent then runs `synthesize` / `approve` / `answer` / `close` silently.

### 4. The relevance gate on agent-initiated questions

The agent may raise a pending signature question **only when the node is relevant to the
current conversation**: in the same lineage (ancestor or descendant) or an **immediate
sibling** of what is being discussed. It never interrogates the PI about an unrelated
subtree, and never opens a session with a backlog quiz.

The inverse holds: when the **PI** asks — "where are we", "what's pending", "what needs
me" — everything is fair game. The restriction binds agent initiative, not PI requests.

### 5. Referring to nodes: title-anchored paraphrase

With IDs gone, the agent names a node by its scientific content, keeping the **node
title's key terms** in the sentence — "whether masked-token pretraining beats
masked-stem" — so the PI can find it in the cockpit and two similar hypotheses stay
distinguishable in speech. The agent never invents a shorthand nickname for a node; a
nickname is an ID with more letters.

### 6. Notebook mode

An explicit PI request to see the notebook — the tree, the progression of questions, a
paper outline from the vault — **opens notebook vocabulary for that exchange**: IDs,
statuses, and structure are all fair game, and the agent **also offers to open the
cockpit**. When the exchange ends, conversation reverts to science voice.

### 7. Engine changes

- **Situate lint** (`situate:unanchored`): the first line must name the scope by the
  anchor node's **title (verbatim, case-insensitive) or its ID**. Agents are instructed to
  use the title: *"Here's where things stand on 'how do we cut the label budget' and
  everything under it."* Misresolution stays deterministically visible; IDs never have to
  surface. The eval oracle moves with it.
- **CLI text output is declared agent-facing.** It stays ID-led and terse — it is the
  agent's working channel, `--json` with eyes. One edit: second-person phrasing ("Awaiting
  your decision") becomes third person ("Awaiting the PI's decision"), so the text stops
  presenting itself as words to relay verbatim.
- **Cockpit unchanged.** ID badges stay — the cockpit is the notebook, and the notebook is
  where IDs live.

### 8. Rewriting the teaching artifacts

Examples train harder than rules, so every artifact that models ID-led speech is
re-authored in the new voice:

- `skills/crux/SKILL.md` — the session dialogue, the gate prose, the "conversational
  front-end" section; plus a new top-level voice section carrying rules 1–6 above.
- `README.md` — the marketing transcript, which doubles as the public statement of the
  invisible-notebook story.
- `skills/crux/evals/fixtures/situate-01/submissions/*.json` — the gold, verbose, and
  invented answers.
- `agents/crux-situate/AGENT.md` — "name the ids first" becomes "name the scope by title
  first," resolving its self-contradiction. The other nine agents' reports go to the
  orchestrating agent, not the PI, and keep IDs; the skill's voice rules bind at the relay
  point.

### 9. Verification: the persona eval

A **permanent** eval class, not a one-off acceptance run. A Sonnet "PI persona" converses
with a crux-driving agent over one of the shipped example problems for N turns. Grading is
layered, cheapest first:

1. **Deterministic chat scan** — agent messages are scanned for node-ID patterns
   (`\b[qhts]\d+\b` and kin) and the crux lexicon, honoring the mirror rule: a term or ID
   the persona used first in that conversation is licensed. Any unlicensed hit fails.
2. **Vault-state assertions** — the notebook was actually kept despite the silence: nodes
   exist, tasks opened and closed, gates tripped, the synthesis recorded after the
   persona's "yes."
3. **LLM judge, soft behaviors only** — gates phrased as science questions with evidence
   named; the relevance gate honored; signatures showed the draft; notebook mode offered
   the cockpit.

Personas include at least one scripted to *use* an ID mid-conversation (mirror-rule
positive case) and one that asks to see the notebook (notebook-mode case).

## Decisions

| decision | rationale |
|---|---|
| mirror rule covers **all** crux vocabulary, not just IDs | "a synthesis awaits approval" is the what-the-hell-is-q19 problem in different clothes; the grad student doesn't say "verifiable" either |
| IDs per-conversation, terms via glossary | IDs are ephemeral handles — persisting them makes the agent say q19 in June because the PI did in March; process terms reuse 14's existing PI-approval flow |
| routine bookkeeping fully silent | the notebook is the grad student's own; permission-asking per entry is notebook chatter, and "the human must not even notice crux is running" is the stated goal |
| signature = science question + shown draft; plain "yes" signs | the gate survives semantically (PI reads what gets recorded) and disappears mechanically (no `crux approve s1` in chat) |
| agent-initiated gate questions are relevance-gated (lineage or immediate sibling) | the PI's rule, verbatim: never ask about a node unrelated to the current conversation; PI-initiated status requests open everything |
| title-anchored paraphrase for node references | free paraphrase makes similar nodes indistinguishable and breaks cockpit cross-reference; verbatim-only titles read like a records clerk |
| explicit notebook request opens IDs, and the agent offers the cockpit | leafing through the notebook is the advisor's right; the cockpit is the better reading surface for it |
| situate lint accepts title **or** ID | keeps the deterministic misresolution check ([13](13-situate-and-design.md)'s guarantee) without forcing IDs into chat |
| CLI text declared agent-facing, third-person, still ID-led | the humans who bypass the agent and run crux by hand are exactly the ones who want IDs; second person was nudging agents to paste it into chat |
| cockpit keeps ID badges | the PI said so: looking at the cockpit and using its numbers is fine — that is the notebook |
| all three teaching artifacts rewritten | leaving any one ID-led actively trains agents against the spec; examples bind harder than rules |
| verification is a permanent persona eval with a deterministic scan first | a one-off run lets the next prompt edit silently reintroduce q19-speak; the lexicon/ID scan is regexable and needs no judge |

## Rejected alternatives

- **Never-ever IDs, even mirrored.** Forces awkward paraphrase when the PI just typed
  "what's up with q19?" — the agent refusing to say a word the PI is using is its own
  UX failure.
- **IDs as quiet parentheticals** ("the question of X (q3)"). Keeps a cockpit handle but
  crux is never invisible; the citation habit metastasizes back into ID-led speech.
- **IDs-only scope (process vocabulary keeps).** "A synthesis awaits your approval" fails
  the advisor test exactly like "q21 awaits review."
- **One-line acknowledgment per bookkeeping act.** Constant low-level notebook chatter;
  the goal is that the PI does not notice the notebook.
- **Signature without showing the draft.** The PI signs prose they haven't read — guts
  the point of the gate.
- **Session-start gate digest / ask-all-immediately.** Sessions open with a quiz instead
  of the PI's agenda; superseded by the relevance gate.
- **Humanizing CLI text output.** Degrades the channel the agent parses, for an audience
  (terminal-first humans) that wants IDs.
- **Two-layer situate (IDs in raw report, orchestrator translates).** The translation step
  is exactly where an invisible misresolution can be introduced — defeats the lint.
- **Dropping the situate anchor entirely.** Gives up [13](13-situate-and-design.md)'s
  deterministic misresolution check for nothing; title-or-ID keeps it.
- **Everything persists once used.** Stale IDs become traps — the agent says q19 in June
  because the PI did in March, and now the PI is the one asking what the hell q19 is.
- **One-off acceptance run instead of a permanent eval.** The next prompt edit silently
  regresses and nothing catches it.
- **Instruction-only change, no artifact rewrites and no eval.** [06](06-node-economy.md)
  settled this class of fix: instructions were never the binding constraint; the modeled
  dialogues are.

## Open questions — all settled at build time

| question | answer | how it was settled |
|---|---|---|
| the exact crux lexicon, and where it lives | `CRUX_LEXICON`, a 38-term frozenset in `engine.py` beside 14's stoplist, normalised through `glossary_key` | measured. Each candidate was counted in the example vaults' `wiki/` prose — pure science voice by the wiki's one-way flow rule — and every candidate with real hits was dropped: `seed` (19, random seeds), `partial` (5), `anchor` (4), `idea` (4), `parent` (2). `brief` and `pursue` are out as plain English on their face. |
| the ID regex, and the "t5" risk | `\b[qhts]\d+\b`, **case-sensitive** | measured over all four shipped example vaults the way 14 measured its matcher: 3,016 matches of the lowercase form, every one a real node or task id, **zero** false positives. Admitting uppercase produces exactly the collision this spec predicted — `T5`, the model, in `scaling_vault/wiki/transformer-language-models.md`. Uppercase is where science lives; lowercase is where crux lives. `selftest` re-runs the measurement rather than quoting it. |
| which vault the persona eval runs on, N, and the bands | `scaling_vault`, **referenced not copied** (`example_vault:` in the manifest); five canned submissions, `k: 3`; `band: unset` | 13 nodes, deliberately jargon-free so the persona needs no field knowledge, and `q3` already carries one in-flight run and one untested idea — the states a signature-gate conversation needs. Bands stay the PI's, per [10](10-agent-evals.md). |
| relevance gate: engine-computed or agent-judged | **engine-computed**, the spec's own default | `engine.gate_relation` + `crux review --json --near` / `crux task review --json --near`, carrying `relation` and `in_scope`. It annotates and never filters, because the rule binds agent initiative and a PI who asks gets everything. |
| does `crux task review` acceptance ride the same phrasing | **yes** | it is the same gate in taskhub clothes: same `--near` annotation, same signature rule in SKILL.md rule 3, and `Awaiting the PI's acceptance` lost its second person along with the rest. |

## Work items

- ☑ SKILL.md: new top-level **voice** section (rules 1–6); re-author the session
  dialogue, gate prose, and lifecycle snippets in the new voice
- ☑ `agents/crux-situate/AGENT.md`: title-first anchoring; drop the ids-first-line
  mandate; keep the plain-language rule it already has
- ☑ `engine.py`: `situate:unanchored` accepts anchor title (verbatim, case-insensitive)
  or ID; `evals.py` oracle updated to match
- ☑ `crux.py`: second-person → third-person in text output ("Awaiting the PI's
  decision"); no other CLI text changes
- ☑ Relevance-gate support: engine surfaces lineage/sibling relation of pending gates to
  a given node in `--json` (or explicitly decide agent-judged; see open question)
- ☑ Glossary: crux process terms become proposable vocabulary via the existing
  `crux-glossary` flow when the PI uses them
- ☑ README transcript re-authored in the new voice
- ☑ Situate eval fixtures (`perfect.json`, `verbose.json`, `invented.json`) re-authored
- ☑ Persona eval: PI-persona harness, deterministic lexicon/ID scan with mirror-rule
  licensing, vault-state assertions, judge rubric for soft behaviors; fixtures include a
  mirror-rule positive case and a notebook-mode case
- ☑ `ENGINE_VERSION` bump + proof old vaults still load; `selftest.py` grown

## Acceptance criteria

- In a persona-eval conversation where the persona never uses crux vocabulary, the
  agent's messages contain **zero** node IDs and **zero** crux lexicon terms
  (deterministic scan), while the vault-state assertions show the notebook was kept.
- When the persona types an ID, the agent may use that ID for that node in that
  conversation — and the scan does not flag it.
- A gate reaching the PI is phrased as a science question naming the evidence, shows the
  draft being signed, and a plain conversational "yes" results in the recorded
  synthesis/answer/close — verified by vault state after the turn.
- The agent never raises a pending gate for a node outside the current conversation's
  lineage or immediate siblings (judge-checked against a fixture that plants an
  irrelevant pending gate).
- A "show me where things stand" persona request gets everything pending, regardless of
  relevance.
- A "show me the tree" request gets structure with IDs **and** an offer to open the
  cockpit.
- A situate answer whose first line names the anchor's title passes the lint; one naming
  neither title nor ID fails it; the ID form still passes.
- `crux` CLI text output contains no second-person address.
- README and SKILL.md contain no ID-led agent-to-PI dialogue.
- `selftest.py` passes with a grown assert count; the three shipped example vaults load
  and validate unchanged.
