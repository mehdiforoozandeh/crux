# Changelog

All notable changes to crux. Format loosely follows [Keep a Changelog](https://keepachangelog.com/);
the engine version (`ENGINE_VERSION`, stamped into every vault) bumps when the vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

### Added

- **The agent roster, and a convention for what an agent definition is** (spec
  [`09`](.spec/09-specialized-agents.md), PRD 09.4). Eight definitions ship in
  `agents/<name>/AGENT.md`, mirroring the `skills/` layout so there is one mental model:
  `crux-null` · `crux-verifiables` · `crux-critic` · `crux-migrate` · `crux-close` ·
  `crux-audit` · `crux-tests` · `crux-glossary`.

  Three frontmatter fields carry 09's architecture and are **asserted**, not just written:
  **`cold_input`** (the only thing the agent receives), **`toolbelt`** — every entry must be a
  real `crux ` verb, because 09 is explicit that the belt is CLI verbs rather than
  agent-private scripts, so `selftest` can assert them and the PI can run any of them by hand
  — and **`excludes`**, which makes each isolation boundary reviewable. `crux-verifiables`
  declares that it never sees `## Problem Statement`, and the suite **cross-checks that the
  brief actually enforces it** rather than trusting the declaration.

  The leash is checked against the **toolbelt**, not prose: no agent may run `crux close`,
  `answer`, `approve`, `pursue` or `task accept`. `crux-critic` ships with an **empty**
  toolbelt and no vault access at all — isolation by construction, since it cannot pour the
  vault into a node it cannot see.

  This **unparks specs 13 and 14**: `crux-glossary`'s row matches the contract spec 14 parked
  in `PARKED-09.md` exactly (propose-only cold input, no write verb, conversation excluded),
  and `crux brief` from PRD 09.0 is the dependency spec 13 was waiting on. Doc-only: no
  engine change, no `ENGINE_VERSION` bump. Spec 09 flips to ☑ with its work items ticked.

- **`crux migrate` — schema bridging, with evidence fields structurally unmigratable** (spec
  [`09`](.spec/09-specialized-agents.md), PRD 09.3). Adds the structural sections a newer
  engine expects (`## ELI5`, `## TL;DR`, `## Null`, `## Artifacts`, `## Protocol`), empty.
  Dry run by default; idempotent; authored prose is never reflowed, only added to.

  **This resolves the standing collision between specs 09 and 15, and 15 wins.** Spec 09
  dissolved version bridging into a mechanical rewrite; spec 15 ruled *"no `crux migrate`
  path for this"*, because bringing an old hypothesis up to evidence semantics means
  re-declaring what would settle a claim — a scientific act, PI-gated, one node at a time.
  Both are right about different fields, and the split was **measured**: a node built at 2.6
  differs from the committed pre-15 fixture by four structural sections plus exactly two
  frontmatter fields, `schema` and `rule`.

  So `MIGRATE_FORBIDDEN` is enforced structurally, not by policy: the verb has no code path
  that writes `schema`, `rule`, `rule_m`, the lock triple, `neutral_optout`, or the null
  approval — and it creates `## Null` **empty**, never filled. `schema` is the sharp one:
  writing it would not "add a field", it would **flip a node across the version boundary**,
  binding work settled before those rules existed to every spec-15 rule at once. Scientific
  staleness is surfaced as `info`, never repaired.

  Also adds `validate --check=gate` (opt-in): a question parked in `review` with no synthesis
  drafted. That is the one item on spec 09's audit list that was not already a check —
  over-cap nodes, unresolvable artifacts and unrun-idea pileup all shipped with specs 06 and
  v0.5. `ENGINE_VERSION` 2.6 → 2.7.

- **A failure scenario on every verifiable, and the two-part discrimination filter** (spec
  [`09`](.spec/09-specialized-agents.md), PRD 09.2). Spec 09 replaces a numeric cap on
  verifiables with a logical one: **two verifiables are redundant if they fail for the same
  reason.** Applied greedily, the agent stops when it runs out of worlds. The engine cannot
  judge that — what it *can* do is force the residue to be written down, so redundancy is
  visible at a glance to the PI and to `crux-critic`.

  Each check now carries the world in which it fails, on an **indented continuation line**:

  ```
  - [ ] imp-Spearman ≥ +0.01
        fails-if:: the gain is capacity alone — the width-matched arm also clears it
        discriminates:: true
  ```

  `discriminates::` is **its own field**, marking the check aimed at the declared null. `validate` and
  the `running` gate enforce both halves: every check has a non-empty scenario, no two are
  byte-identical, and at least one claim-directed check discriminates. Byte-identity is all
  the engine can honestly check — it catches copy-paste, and the rest is why the scenarios
  are written down at all.

  The continuation line was chosen because it is the only syntax that leaves **every** spec-15
  reader byte-clean: tick, kind, text, `(found: …)` and both tallies are unchanged, asserted
  against values captured before the change. New `--fails-if` / `--discriminates`, which
  attach to the preceding `-v`/`-n` — **additive, never a second argument to `-v`**, which was
  measured to break every existing caller. `ENGINE_VERSION` 2.5 → 2.6.

### Changed

- **`SCHEMA_GENERATION` → 2**, and `lock_material` is now **generation-keyed**. From
  generation 2 the failure scenario is part of the pre-registered commitment — it is what
  would have falsified the check, and writing it after results are visible is exactly the
  move the lock exists to detect. A node stamped **generation 1 keeps the material it was
  locked with, forever**: without that split, changing the commitment's shape would re-hash
  every already-locked node and flag an edit nobody made, which is the engine falsifying its
  own record. Proven on a fixture locked under generation 1 — it does not drift, and its
  vault validates clean.

- **`## Null` — the boring explanation, on a closed vocabulary, PI-gated** (spec
  [`09`](.spec/09-specialized-agents.md), PRD 09.1). The brief removes the parent's authored
  prompt, but one leak cannot be engineered away: the hypothesis **title** is directional.
  *"masked-token beats masked-stem"* presumes a winner, and a fresh agent still knows which
  way the room leans. The answer is not to neutralise the title but to push against it —
  name the **cheapest way this result could be trivially true**, then make the checks
  discriminate against *that*.

  Three goalposts, all in code, because instructions will not hold this (the crux skill
  already said *"keep the science explicit"* and produced 5,725-word nodes): **one null, one
  line, ≤25 words**; it must **name a family from a closed list** — `capacity` · `chance` ·
  `leakage` · `selection` · `normalization` · `instrumentation` — so the agent picks a family
  and names the instance rather than composing something exotic; and **the PI approves it
  before checks are written against it** (`crux approve-null <id>`), which is the gate
  between naming the boring explanation and testing against it. The null *is* the bar
  restated, and the leash already makes the bar the PI's call.

  Editing an approved null **voids the approval** — a different null is a different claim
  about what would be boring, and checks written against the old one discriminate against
  nothing. New `crux hypothesize --null`; the null flows into `crux brief`, `snapshot` and
  the cockpit pane. `ENGINE_VERSION` 2.4 → 2.5. Pre-15 hypotheses are never asked for one.

- **`crux brief <hypothesis> --json`** (spec [`09`](.spec/09-specialized-agents.md), PRD 09.0).
  The deterministic cold input every isolated agent receives: one hypothesis' claim, its
  question, its ancestry, its pre-registered checks with kinds and combination rule, the
  findings of **closed siblings**, linked wiki pages, and the *addresses* of available
  metrics. Assembled from vault state; **the calling agent never authors a sentence of it.**

  crux pre-registers verifiables, which defends against changing the bar *after* seeing
  results — it says nothing about *who sets it*, and an agent that has spent an hour helping
  argue for a hypothesis will pick a bar that clears. Zero context does not fix that alone,
  because the parent writes the prompt: *"verify that JEPA improves imputation"* has already
  said which way to lean. Same node, same brief, every time — which is what makes the
  isolation testable rather than merely claimed.

  Three exclusions, each for its own reason: **`## Problem Statement`** (spec 09 names it as
  where the advocacy lives); **the hypothesis' own findings and its own `(found: …)` values**
  (an agent writing checks must not see that hypothesis' results, or "pre-registration" is
  being performed after the fact — sibling findings stay, those are the shared record); and
  **metric values** (the brief says what *can* be measured, never what *was*).
  `ENGINE_VERSION` 2.3 → 2.4. Read-only; works on pre-15 and pre-08 vaults unchanged.

- **The taskhub's skill rules, and three spec amendments** (spec
  [`08`](.spec/08-taskhub.md), PRD 08.5). `SKILL.md` gains the rules the engine cannot check:
  what gets in ("would you be annoyed if this vanished next week?"), when status changes, the
  hard line — *work never creates direction; an output that is evidence enters the gated
  tier* — and the escape hatch, that a task which would open a question converts to a tree
  node. Plus the distinction that matters most now that both share four tokens: a
  hypothesis's **verdict** is derived by the engine from its ticks; an experiment's
  **conclusion** is written about a run and PI-accepted, and never closes anything.
  `.spec/08` is amended for the conclusion vocabulary and the frontier criterion (both wrong
  as written), and both specs now record the deliberate split between written node-tree
  lineage and derived task links, so neither layer gets "fixed" toward the other. No
  `ENGINE_VERSION` bump.

### Added

- **The taskhub in the cockpit** (spec [`08`](.spec/08-taskhub.md), PRD 08.4). `snapshot`
  gains a `tasks` block — items with their **computed** `state` and role, the frontier, the
  acceptance queue, and the declared vocabularies, so the cockpit never keeps its own copy of
  the rules. Node → tasks and hypothesis → experiments reach the node pane as computed
  backlinks that appear in no node file. A fourth tab renders four views over one list —
  Frontier (default), All, By category, and the experiment timeline — with **one colour per
  category** as the visual language, in both themes, and a `pre-15` marker on a conclusion
  about a hypothesis that predates evidence semantics. The tab hides itself on a vault with no
  `tasks/`, exactly as the Wiki and RD tabs do. Read-only throughout: accepting an experiment
  stays a CLI act. No `ENGINE_VERSION` bump — pure read paths.

### Added

- **The gating split: work never creates direction** (spec [`08`](.spec/08-taskhub.md),
  PRD 08.3). Completing an ordinary task is act-and-report; completing an **experiment** is
  PI-gated, because its output is evidence. `crux task review` lists experiments awaiting
  acceptance and `crux task accept` is the PI's signature — a **separate** queue from
  `crux review`, which keeps spec 15's `(id, title, drift)` three-tuple untouched. Accepting
  records the signature and sets the existing `stale` signal on the refed hypotheses' parent
  questions; it writes no verdict, no tick and no roll-up entry, and five asserts prove those
  negatives. Because only the parent of a decomposition carries `hypothesis_refs`, the gate
  fires **once per experiment**, not once per sub-task. Drift on a refed hypothesis is printed
  loudly at both `review` and `accept` and **blocks nothing** — spec 15's ruling D7, given its
  own guard at this new touchpoint. `ENGINE_VERSION` 2.2 → 2.3.

### Added

- **Experiments are tasks** (spec [`08`](.spec/08-taskhub.md), PRD 08.2). A task that declares
  what it concluded about a hypothesis (`hypothesis_refs: "h44:supported, h45:refuted"`) **is**
  an experiment; the `experiment` category is computed from that and never stored, so there is
  no way to have an experiment that forgot to be marked one. The conclusion vocabulary is spec
  15's, derived from `VERDICTS` so the two cannot be edited apart: `supported` / `refuted` /
  `inconclusive` / `invalid-run`, with the retired `partial` refused by name. One experiment
  can conclude opposite things about two hypotheses — the fact the tree structurally cannot
  hold. Node → tasks and hypothesis → experiments are **computed** backlinks, so adding an
  experiment still edits no node file; the experiment timeline is a filtered section of
  `TASKHUB.md`, leaving the per-hypothesis `EXPERIMENTS.md` registry untouched. An experiment
  may bear on a **pre-15** hypothesis, and every view records which schema each refed
  hypothesis carries — the record sits on the task's side, so nothing is retro-stamped.
  `crux task add --concluded h44:supported`. `ENGINE_VERSION` 2.1 → 2.2.

### Added

- **The dependency graph, the frontier query, and `TASKHUB.md`** (spec
  [`08`](.spec/08-taskhub.md), PRD 08.1). `blocked` is computed from the graph and never
  stored — a state you can compute cannot drift — and external blockers become tasks rather
  than a second kind of state. `crux task list` answers the three questions actually asked of
  the layer (`--frontier`, `--ref <node>`, `--blocks <task>`), and the generated `TASKHUB.md`
  leads with the frontier because that is the query it exists to serve. Dependency cycles are
  caught deterministically over both `blocked_by` and `parent`, with the cycle path in the
  message. A **dropped** blocker discharges its edge (the spec's literal "all `done`" would
  strand the dependent forever, invisibly, inside the layer's own primary query), and the
  promotion is reported as `info` so it is never silent. `ENGINE_VERSION` 2.0 → 2.1.

### Added

- **The task store — a record the engine allocates and never rewrites** (spec
  [`08`](.spec/08-taskhub.md), PRD 08.0). A third side-layer beside the tree and the wiki:
  `tasks/`, holding the work a research programme has to *do*. `crux task add / done / drop /
  show / categories`, one file per task, engine-allocated ids that are never renumbered, a
  per-vault declared category list, and a `--check=tasks` structural lint. `done` hard-requires
  an output that resolves — a vault path or a `[[wikilink]]` — because a bare ticked box
  discards the thing that makes the layer traversable. The load-bearing property is negative
  and is the direct lesson from spec-kit, whose `tasks.md` is regenerated from its spec and
  loses state: **nothing regenerates the taskhub**. `experiment` is a reserved category from
  day one, refused by the engine, so assigning it later (2.2) is not a format change.
  `ENGINE_VERSION` 1.9 → 2.0; a pre-2.0 vault has no `tasks/` and loads byte-unchanged.

### Added
- **The cockpit narrates evidence semantics** (spec
  [`15`](.spec/15-evidence-semantics.md), PRD 15.6). The engine had been publishing `drift`,
  `rule`/`rule_m`, `locked`/`lock_at` and per-verifiable `kind` in `snapshot()` since 1.9, and
  the cockpit rendered **none** of them — found by walking the manual check, and measured
  rather than eyeballed (the string "drift" appeared nowhere in the DOM, in either theme).

  That is spec 15 §5's own failure reproduced: PLATO's rule *"failed at narration time, not
  computation time"*. A drifted hypothesis read as a clean `supported` over three green
  ticks, one of them literally titled *"a completely different check nobody registered"*; and
  on an `invalid-run` node, the control whose failure **caused** the verdict was
  indistinguishable from the claim checks.

  Now: a drifted node carries a dashed amber edge and a ⚠ in the **tree** (a flag only
  visible after opening the node is a flag that does nothing for a reader skimming), and the
  detail pane carries `rule`, a `⚠ drift` badge, a `not pre-registered` badge when the
  commitment was hashed only at close, and a `CONTROL` chip on outcome-neutral rows. Drift
  takes the **stroke**, never the fill, so "what was concluded" and "was the commitment
  edited" stay separately readable. Webui only — no engine change, no `ENGINE_VERSION` bump.

### Changed

- **`demo_vault`'s generated views regenerated through the engine.** The committed fixture
  was last regenerated at engine 1.3, so its `META.md`, `EXPERIMENTS.md` and in-node ledger
  blocks predated spec 15's view changes (the `rule` column, `invalid-run` in the verdict
  counts). Regenerated with `refresh()` — never by hand, per the `evolve-crux` guardrail —
  so the fixture is honest at 15's tip. **Every recorded verdict, every status and every
  authored line is byte-unchanged**, and the vault deliberately keeps `engine_version: 1.2`
  with no `schema` stamp on any node: its whole job is to be the *pre-15* oracle the
  non-retroactivity proof compares against, and re-stamping it would destroy that.

- **Guard parity for the cockpit.** The legend guard derived from `E.VERDICTS` is what forced
  `invalid-run` into the UI during the 15 build; there was no equivalent for per-node fields,
  which is exactly why three shipped unrendered. A new guard derives the expectation from
  `snapshot()`'s **actual** published surface — every idea and verifiable field must be
  consumed by `app.js`, minus a deliberately small, justified allowlist — so a field added to
  the engine tomorrow joins the expectation without anyone remembering to update a list.
- **The hash-lock is pinned newline-invariant.** The wiki source registry hashes raw bytes
  (`_sha256_file`), which is what broke `demo_vault` on Windows CI under an autocrlf
  checkout. The lock never inherited that: it hashes `lock_material()`, a string built from a
  body `read()` already normalized in text mode. Three asserts pin it — including a real CRLF
  file round-tripped from disk — so a future move to byte-hashing fails here rather than on
  someone else's runner.

- **The separability rulebook, and the skill's account of a verdict** (spec
  [`15`](.spec/15-evidence-semantics.md), PRD 15.5). The `crux` skill gains the PI's rule for
  when one experiment may settle several hypotheses, verbatim — *"each hypothesis turned by
  its own independently varied knob … and no single shared ingredient could flip all the
  answers together without a pre-declared outcome-neutral check catching it and voiding the
  whole run; anything less means you ran one experiment with many labels, not many answers"* —
  plus the three checks it decomposes into (different lever / different failure / different
  verdict). A selftest assert compares the skill's copy against the spec's word for word, so
  the two cannot drift.

  The skill's verdict section is rewritten: it was still teaching *"any unmet →
  refuted/partial"*, which is the retired rule. It now describes the two verifiable kinds,
  the combination rule, all five verdicts, `inconclusive` as derived-never-chosen, and — the
  part an agent most needs — that **the boundary is permanent and an old node must not be
  "fixed"** to the new schema. Doc-only; no `ENGINE_VERSION` change, no migration.

  Spec 09 records the `crux-verifiables` amendment where it will be built (assign kinds,
  choose and justify the rule, state the 64%-joint-power cost of `all`), since that agent
  does not exist yet. Spec 15's shipped work items are ticked and its status is `◐`.

- **The hash-lock: enforced pre-registration, and a permanent drift flag** (spec
  [`15`](.spec/15-evidence-semantics.md), PRD 15.3). When a hypothesis goes `running`, the
  engine content-hashes its **commitment** — the combination rule plus every verifiable, in
  document order, as (kind, text) — into `lock:` with a `locked:` timestamp. Any later edit
  to a check, a kind, the rule, or the *order* is detected and raised as a `validate`
  problem. Two things deliberately do **not** count: ticking a box (that is what closing
  *is*) and appending a `(found: …)` note (that is the evidence, recorded after). Whitespace
  is collapsed, so reflowing a long check is not drift.

  The negative result this answers is blunt: bare preregistration shows no measurable drop in
  positive results and 46% of preregistered hypotheses simply vanish from the paper, while
  Registered Reports run 44% positive against 96%. The active ingredient is *enforced
  commitment*, not the document — and a vault is a git repo, so crux can enforce what a
  journal cannot.

  **Edits are flagged, never refused.** Research legitimately discovers a check was wrong,
  and refusing the edit only launders it into a duplicate hypothesis. The flag is permanent
  and no verb clears it. It **blocks nothing**: `crux review` shows it beside the question at
  the moment the PI is deciding, `crux answer` prints it and proceeds. The engine flags; the
  PI decides. `ENGINE_VERSION` 1.8 → 1.9.

  `close` also locks, marking `lock_at: close` and raising a *warning* — `cmd_close` has no
  status precondition and is reachable straight from `idea`, so a lock taken only at
  `running` is bypassable by the shortest path the CLI offers. The warning says what is true:
  the checks and the results became visible at the same moment.

### Changed

- **`crux review` reports drift, and its return shape grew a third field**
  `(id, title, drift)`; `--json` gains `"drift"`.
- **A seed-reconstructed hypothesis is marked `reconstructed: true`** and reported in its own
  words — *"reconstructed from a seed and never pre-registered"* — instead of being counted
  as predating evidence semantics. A vault created today can hold these, so calling them old
  would be baffling.

- **The combination rule, and a verdict with no `partial` in it** (spec
  [`15`](.spec/15-evidence-semantics.md), PRD 15.2). A hypothesis now declares **how its
  claim-directed checks add up**, before the run: `rule: all | any | m-of-n` (with
  `rule_m:`), settable at creation via `crux hypothesize --rule/--rule-m`. That turns "two of
  four passed" from an argument into arithmetic. ICH E9 §2.2.5 states the design space as
  exactly this quantifier — any / some minimum number / all — and those three ship.
  `ordered` (fixed-sequence gatekeeping) is a **reserved** token: recognized and refused with
  a pointer to spec 15, so no vault can contain one and adding it later is not a format
  change. It is the structure PLATO's authors narrated past, and shipping it needs a render
  contract that is not built.

  The verdict becomes a total function of **(kinds, rule, pass/fail vector)** with a
  four-value image: `supported` · `refuted` · `inconclusive` · **`invalid-run`** (new). Run
  validity is read *first and separately* — a failed or unread outcome-neutral control yields
  `invalid-run`, never `refuted`, because a broken apparatus is not a refutation. Under
  `m-of-n`, exactly *m−1* passes is `inconclusive` (the "consider" tier) and two or more short
  is `refuted`, so `inconclusive` stays narrow rather than becoming the drawer. It is
  **derived, never chosen**: no verb, flag or field sets it. `ENGINE_VERSION` 1.7 → 1.8.

  `partial` is **retired, not removed**. It can never again be derived for a node that binds
  evidence semantics, but it stays in the vocabulary permanently: `snapshot` clamps any
  verdict outside `VERDICTS` to `None` and the cockpit renders a `done` node with a `None`
  verdict as *inconclusive*, so deleting the token would silently re-label every pre-15
  partial result. A pre-15 node is still closed by the **unchanged** pre-15 function —
  asserted against its full truth table, captured before the change and pasted into the suite
  as a literal.

### Changed

- **The verdict roll-up is generated from `VERDICTS` instead of four hard-coded names.**
  `ledger_counts` hand-picked the four as literal dict keys and `render_meta`'s dashboard
  listed them in a format string, so adding a fifth verdict raised `KeyError` in
  `_ledger_summary` and rendered *nowhere* in `META.md`. Both are now derived from the
  constant, matching what the cockpit legend already did. `EXPERIMENTS.md` gains a `rule`
  column beside `verdict` — spec 15's render-time requirement that the verdict and the rule
  that produced it travel together wherever a hypothesis is read.

- **Verifiables carry a `kind`** (spec [`15`](.spec/15-evidence-semantics.md), PRD 15.1).
  Two classes, written as a leading bracket tag on the checkbox line:
  `[hypothesis]` (a consequence of the claim — the default, so every existing verifiable
  reads exactly as it always did) and `[outcome-neutral]` (a positive control or sanity
  check that must pass *whatever* the claim turns out to be). Regulators call the property
  this protects **assay sensitivity**: without a passing control, "the claim is false" and
  "the apparatus is broken" are indistinguishable, which is what let one flat list
  manufacture partial answers. A hypothesis created at 1.7 or later **cannot go `running`**
  without at least one outcome-neutral check or a written `neutral_optout:` reason — the
  reason itself is the audit trail, because "there is no control here" should be *said*.
  New `crux hypothesize -n/--neutral`, and a `vn:` line in the seed grammar. The tag is
  *leading* rather than trailing, and that is forced: the seed parser strips a trailing
  `(...)` as its evidence note, so `(outcome-neutral)` would be silently recorded as a
  finding. `ENGINE_VERSION` 1.6 → 1.7.

  This PRD deliberately changes **no verdict**: the kind is parsed, required and displayed,
  but the tally the verdict runs off is byte-unchanged. Consuming the split is PRD 15.2.

- **The evidence-semantics version boundary** (spec [`15`](.spec/15-evidence-semantics.md),
  PRD 15.0). Questions and hypotheses created from `ENGINE_VERSION` 1.6 on carry a
  `schema: 1` frontmatter stamp; **absence of the stamp means the node predates evidence
  semantics**, permanently. Spec 15's rules — verifiable kinds, the combination rule, the
  hash-lock — will bind stamped nodes only, so the engine can never re-verdict work that was
  settled under the old ones. The mechanism has to be per-node: the vault-level
  `engine_version` cannot carry it, because `check_and_stamp_version` overwrites that stamp
  on drift *before* returning the warning, so one command after an upgrade erases the
  evidence that the vault is old. `crux validate` gains a third tier, **`info`** — reported
  with a neutral glyph, never counted toward the exit code, and never escalated by
  `--strict`, because a vault that predates a rule is correct rather than broken. This PRD
  adds **no rule at all**: a stamped and an unstamped node behave identically in every
  command. `ENGINE_VERSION` 1.5 → 1.6; a pre-1.6 vault loads byte-unchanged, keeps every
  recorded verdict, and validates clean.

### Changed

- **A seeded `[tested]` hypothesis is no longer stamped with the evidence-semantics schema.**
  `[tested]` means "this ran before crux was watching" — reconstructed history, not new
  work. Requiring it to declare a control would be the engine asking the PI to invent, after
  the fact, what would have settled an already-settled claim. Untested seeded hypotheses are
  genuinely new work and keep their stamp.

- **Version asserts in `selftest.py` no longer pin a literal.** Five checks asserted
  `E.ENGINE_VERSION == "1.5"`, which made every future engine bump drag earlier specs' tests
  red. The ones asserting a *historical* bump now use `at_least_version()` ("that bump
  happened and was never reverted", which stays true), and the ones asserting *current*
  behaviour compare against `E.ENGINE_VERSION` itself — the idiom `rdmig` was already using
  one line above one of them.

- **The RD layer: `crux rd <node> "<title>"`** (spec [`07`](.spec/07-rd-layer.md), PRD 07.1).
  Requirements Documents — a home for the design detail the 400-word node cap displaces.
  One active RD per node, living in `rd/<slug>.md` as `type: rd`, linked from the node by an
  `RD::` line beside `Parent::`, indexed by a generated `RD.md`. An RD is a **document, not
  evidence**: it is outside the roll-up, never moves `ledger_counts`, and never trips the
  review gate. An active RD is never amended in place — `--supersedes` writes a new one and
  flips the old, and the chain is the reasoning history (the direct fix for a node body
  treated as the only durable record). The backlink sits in the body preamble on purpose:
  text before the first heading is invisible to the prose counter, so linking a design
  document costs nothing from the budget it exists to free. `ENGINE_VERSION` 1.4 → 1.5;
  a pre-1.5 vault has no `rd/` and loads byte-unchanged.

- **`crux validate --check=rd`: the RD structural lint** (spec
  [`07`](.spec/07-rd-layer.md), PRD 07.2). Four mechanical checks plus the status enum: the
  node's `RD::` backlink resolves; the two ownership records (the RD's `node:`, the node's
  link) agree; exactly one design is live per node; the supersession chain resolves and is
  acyclic. Findings are **problems**, matching the wiki lint — an integrity break, not an
  economy warning — and the check is always-on but returns immediately on a vault with no
  `rd/`. Two wiki-lint corrections ride along: a wiki page citing `[[rd/…]]` is now a **flow
  violation** (the one-way rule extended — the literature layer must not cite the project's
  own design) instead of an unhelpful "broken link", and a wiki page cited only by an RD is
  no longer reported as an orphan. Deliberately **not** checked: whether a superseded RD was
  edited — `git log -p rd/<slug>.md` is the audit trail, the same call made for a node's
  decision history.

- **The `crux-rd` skill** (spec [`07`](.spec/07-rd-layer.md), PRD 07.4). Carries the two
  things the engine must not hold: the **write-vs-skip filter** (an RD is warranted when the
  design would blow the cap on its own, or makes a choice a reader would re-litigate, or
  carries a distortion that must travel with every result — and is explicitly *not* warranted
  for a hypothesis whose design is its verifiables), and the **invocation rule** — the PI
  decides when a design has settled, so the skill ships `disable-model-invocation: true` and
  never offers unprompted. It also now carries the immutability rule outright: since the
  engine deliberately does not detect an edited superseded RD, the skill names
  `git log -p rd/<slug>.md` as the audit trail. Spec 07 is marked done and amended on two
  points: "one RD per node" is now "one *active* RD per node", and the written-vs-computed
  backlink split with spec 08 is recorded on both sides.

- **Decks pick up RD pages** (specs [`07`](.spec/07-rd-layer.md) +
  [`11`](.spec/11-prezit.md), PRD 07.5). `crux deck <anchor> --json` now fills the `rd` slot
  spec 11 cut and shipped empty: the **active** RDs owned by the anchor and everything under
  it, as `{slug, title, path}`, in tree order then slug. The traversal is anchor +
  *descendants*, not the neighbouring `wiki` block's anchor + *ancestors* — RDs are the
  methods source for the anchor's own story, so a parent's design must not land on a child's
  method slide. A vault with no `rd/` still gets `[]` and the command still cannot fail.

- **The cockpit reads RDs** (spec [`07`](.spec/07-rd-layer.md), PRD 07.3). A third tab, which
  appears only when the vault has an `rd/`: a rail grouped by owning node (superseded entries
  dimmed under their successor) and a reader. The reader is the **wiki tab's, extracted and
  shared** rather than copied — the pre-registered "app.js is pure-read (three GETs)" assert
  is what keeps it honest, since a second reader would need a fourth fetch. `snapshot` gains
  an `rd` index block (slug, title, node, status, supersedes, content hash — never a body,
  because the cockpit polls it about once a second) and every question and hypothesis gains
  `rd`: the slug of its active RD, or `null`. Nodes that have one now show a **Design** row
  that opens it; nodes that do not show nothing. New route `/rd/<slug>.json`, with the wiki
  route's traversal guard: the slug is matched against the scan and never used as a path.

### Fixed

- **Cockpit: the snapshot poll diffs and patches instead of rebuilding** (spec
  [`12`](.spec/12-cockpit-craft.md)). While an agent writes files — the normal crux
  workflow — every vault change used to rerun the whole pipeline (21.4 ms up to 1 Hz)
  and rebuild the detail pane, resetting the reader's scroll and replaying its entrance
  animations. Now a structural signature (tied by a selftest to the draw path's actual
  field reads) gates `layout()`/`renderTree()`; status/verdict/verifiable flips patch
  just the changed node groups in place; and the pane re-renders only when what it shows
  changed. Verified live: prose-only edits → 0 rebuilds (~2.5 ms per poll); a checkbox
  flip → one single-node patch; a new node → exactly one full render, as before.

- **Cockpit: the hover spotlight no longer repaints the whole tree, and the blur
  overlays are gone** (spec [`12`](.spec/12-cockpit-craft.md); paint-gate ruling, final).
  The spotlight used to write ~199 classes per `pointerover`, fire ~12× per node crossed
  (no same-node guard), and start a 180 ms opacity animation on every dimmed group under
  up to nine `backdrop-filter` blurs — measured 54.8 fps with a 216.5 ms worst frame on a
  hover sweep. Now: a same-node guard, one `spot` class on the canvas, `.hov`/`.nbr`
  marks found through the node's own edges, no per-node fade (dim snaps), and the
  overlays carry one shared near-opaque background instead of blur. What lights up is
  unchanged. Measured (273 drawn nodes): class writes per crossing 284 → 4, redundant
  refire cost 0.73 → 0.02 ms, live animations after one hover 279 → 8; the gate's
  ablation showed each half alone restores ~60 fps / ~17 ms worst.

- **Cockpit: cosmetic changes never rebuild the tree** (spec
  [`12`](.spec/12-cockpit-craft.md)). Selecting a node, showing the review queue, search
  dimming and the legend filter used to tear down and re-parse the whole SVG
  (`renderTree()`, 10.9 ms) to move a CSS class (0.19 ms — 55×). They now share one
  in-place pass (`applyCosmeticState`) that toggles `dim`/`hit`/`.selected` and keeps the
  ARIA selection (`aria-selected`, `aria-activedescendant`) truthful; `renderTree()` is
  structural-only and still bakes the same classes, so the paths cannot drift. Search is
  debounced (~120 ms trailing, Enter/Escape flush): a 10-character query now costs one
  cosmetic pass, not ten rebuilds. Measured (273 drawn nodes): selection 142.9 → 62.5 ms
  end-to-end with rebuilds 1 → 0 per click; the tree-side swap itself p50 2.4 ms.

- **Serve: the snapshot is cached on a vault stat key** (spec
  [`12`](.spec/12-cockpit-craft.md)). The server used to regenerate the whole snapshot on
  every 1 Hz poll purely to compute the ETag, then answer 304 — measured 29 ms of Python
  and 181 files re-read per second (~2.4% of a core, forever). Now a stat walk
  (dir-inclusive max mtime + entry count — dir mtimes catch deletions) keys a cache of
  the serialized bytes + content-hash ETag; regeneration happens only when the vault
  actually changed. Measured on a 286-file vault: 37.2 ms → 1.1 ms per poll (33×). The
  client contract (ETag/304, `poll()`'s text-diff guard) is byte-identical.

### Added

- **The `prezit` skill — presentations from a subtree, end to end**
  (spec [`11`](.spec/11-prezit.md) closed, PRD 11c). `skills/prezit/` ships the workflow
  (harvest → read the reports → agree the arc with the PI → draft → verify → refine, with
  `--refresh` + re-read-the-prose for re-presentation), the deck **template**
  (`assets/deck.html`: chrome, palette tokens, fade-only + reduced-motion, keyboard nav,
  DOM-derived slide count, print stylesheet, contract-headed stubs, both chart scaffolds)
  and the worked **example** (`examples/q1_scaling_deck.html`, built on
  `examples/scaling_vault` q1 — `--verify --strict` green, lint clean, chart annotations
  computed from cached values rather than hand-typed). New `crux deck --lint` checks every
  slide's contract header (job/source/numbers/cut) and the 7-content-unit budget.
- **`crux deck --verify` / `--refresh` — the deck traceability contract, enforced**
  (spec [`11`](.spec/11-prezit.md) §5, PRD 11b). `--verify <deck.html>` walks every
  `src:` / `data-src` / `data-derived` in the deck **source** (never a rendered DOM) and
  buckets each: *mismatch* and *unresolvable* fail with distinct reporting; *derived* passes
  with inputs checked, result not recomputed; *unsourced* passes and is listed —
  `--strict` fails it, with `data-src="literal"` as the escape for definitional constants.
  All findings are reported before the exit decision. `--refresh <deck.html>` rewrites the
  cached values only — sign convention, `&minus;` entities, thousands separators and
  decimal count preserved; string-typed values verbatim — and warns per slide, loudly:
  refresh fixes values, only a human can fix the sentence around them. `validate` gains an
  **opt-in** `--check=decks` (stale decks surface as warnings; plain `validate` ignores
  `presentations/` entirely; `--strict` fails on them like any warning). No vault-format
  change — no migration.
- **`crux deck <anchor> --json` — the deterministic presentation payload** (engine **1.4**,
  spec [`11`](.spec/11-prezit.md), PRD 11a). One anchor's whole story material — lineage,
  siblings, recursive children with verifiables/findings/artifacts, linked wiki pages, the
  approved synthesis, scope counts, figures and every addressed metric — assembled from vault
  state only, byte-identical across runs, no prose authored by the engine. Aliases `prezit`,
  `present`, `slides`. New optional conventions the engine now reads (and never writes):
  `results/<hid>/metrics.json` (nested leaves carrying `value` (+`ci`/`se`/`n`/`unit`),
  addressed as `<hid>#<dotted.key.path>`) and a `## Protocol` section on questions (the
  "rules locked up front" note). Pre-1.4 vaults load unchanged — the bump is additive; the
  drift warning is the only visible effect. `examples/scaling_vault` gains committed
  `results/h1..h3/` fixtures (metrics + linked reports) so the reference deck's addresses
  resolve.
- **Cockpit benchmark harness** (`tools/bench/`, spec [`12`](.spec/12-cockpit-craft.md)).
  The console-paste paint/interaction probe, a seeded synthetic-vault grower (drives the
  real CLI, so every node is format-valid), a 1 Hz agent-writes simulator, and committed
  baseline JSONs — so every cockpit perf claim is re-measurable, env recorded per run.
  Dev tooling only: nothing ships in the skill or is served by the cockpit.

- **Cockpit: keyboard-first tree canvas** (spec [`12`](.spec/12-cockpit-craft.md)). The tree
  `<svg>` is a real focusable ARIA tree (`tabindex`, `role="tree"`, per-node `treeitem` +
  `aria-activedescendant`, a `:focus-visible` ring that isn't clipped). Orientation-relative
  arrows move the selection (child points where the children visibly are — in radial, ↓ is
  outward), siblings stop at the ends, `Space` folds, `Enter` hands the detail pane the
  focus, and the camera follows every move via the existing `tweenView()` (instant under
  reduced motion). Keyboard costs the mouse nothing: every pointer gesture is unchanged, and
  a guard keeps keyboard-driven camera glides from lighting the hover spotlight.

- **Cockpit: search that cycles** (spec [`12`](.spec/12-cockpit-craft.md)). `Enter` advances
  to the next match and wraps; `Shift+Enter` goes back; a counter in the field shows the set
  size before you cycle ("11") and your position once you do ("3 / 11"). One match set feeds
  both, in deterministic order — the tree's own walk order, the wiki's index order — over
  visible nodes only, in both tabs. (Before: Enter re-jumped to the first match forever.)

- **Node economy — crux now enforces economy the way it already enforced falsifiability**
  (engine **1.3**, spec [`06`](.spec/06-node-economy.md)). Every guardrail used to push toward
  more rigor and none toward less volume, so nodes grew until the vault stopped being readable
  by the PI it exists to serve — measured on one real vault, questions ran from 101 to 5,725
  words with the split falling on *how the node was authored*, not on how hard the question was.
  - Questions and hypotheses now open with **`## ELI5`** (one sentence) and **`## TL;DR`**
    (one paragraph: what it asks or claims, and what would settle it).
  - **A 400-word prose budget per node.** Counts the framing and interpretation sections only —
    `## Verifiables`, `## Run Links`, `## Artifacts` and the generated ledger are free, because
    they were never the bloat and capping them would punish thoroughness where crux wants it.
  - **A fan-out budget of 5 unrun hypotheses per question.** `crux hypothesize` warns on the
    call that would breach it.
  - Both are **warnings**: `crux validate` prints them and still exits 0. **`--strict`** makes
    them fail, and **`--check=tree,wiki,economy,fanout`** runs a subset.
  - The **cockpit detail pane now opens with ELI5 + TL;DR** and folds the long prose behind a
    disclosure. Before this, a question's whole `## Question` section was the first thing in the
    pane — the single line most responsible for the cockpit being unskimmable.
- **`--json` on every verb an agent loop drives** — `ask`, `hypothesize`, `test`, `close`,
  `review`, `answer`, `pursue`, `status`, `synthesize`, `approve`, `ingest`, `validate`. On
  `--json`, stdout is JSON and nothing else; hints and warnings go to stderr. `crux status
  --json` is the whole snapshot, `crux status q3 --json` one node, `crux validate --json` the
  `{ok, checks, problems, warnings}` report. In the CLI rather than in agent-private scripts, so
  `selftest.py` can assert it, the cockpit reuses it, and you can run any of it by hand.
- **A third example vault, `scaling_vault/`** — *More data, or a better model?* 13 nodes,
  24 wiki pages, 22 arXiv sources (every id checked against the arXiv API before the page
  citing it was written). Deliberately small and jargon-free: the shape of a crux vault
  should be legible before you know the field it sits in, which `segssl_vault` cannot do.
  `q1` carries the point — a hypothesis comes back *supported* and the answer still
  contradicts it, because the winning arm had twice the compute.
- **An animated README hero** (`assets/crux-hero-{light,dark}.gif`), replacing the static
  schematic, and following your GitHub theme like the screenshots do.
  It walks the same model the schematic diagrammed — verifiable → hypothesis → question →
  programme — and ends on the mark. Drawn from `scaling_vault`, so what it shows is in
  the repo. It opens on the frame it closes on, held a second at each end, so the loop
  is seamless and the still shown before it plays carries the name and the URL.

### Changed

- The README's opening figure is now that animation rather than
  `assets/crux-schematic-{light,dark}.svg`. The SVGs are kept; nothing references them.

### Fixed

- **Cockpit: a type scale that reads** (spec [`12`](.spec/12-cockpit-craft.md)). The detail
  pane's three text steps were 12.5 / 14 / 16.5 px — ratios under 1.2, which does not read
  as a step. Now 12 / 16 / 21 (a perfect fourth): small is a genuine overview, large a
  genuine reading mode, and the whole pane scales in `em` off the step as before. The
  chrome went the opposite way: ~12 distinct sizes between 8.5 and 15.5 px collapsed to
  three named variables (10 / 11.5 / 12.5), with hierarchy carried by ink tier and weight —
  SVG canvas labels are exempt because their sizes feed the node-geometry `measureText`.
- **Cockpit: the theme now actually follows the OS** (spec
  [`12`](.spec/12-cockpit-craft.md)). The stylesheet header promised "saved preference,
  else system"; the code defaulted to dark and never consulted the OS. Now: with no saved
  preference the cockpit resolves from `prefers-color-scheme` and follows OS flips live;
  the first ☀/☾ press writes an explicit choice that sticks. A blocking `<head>` stamp sets
  the theme before first paint, so neither theme ever flashes the other on load.
- **An artifact bullet may now carry a note after a markdown link.** `parse_artifacts()`
  anchored its link regex to end-of-line, so `- [Report](results/h1/report.md) — a note`
  fell through to the bare-path branch and split into the path `'[Report'` — surfacing as
  two `crux validate` errors that named neither the bullet nor the cause. The bare-path
  form always allowed a trailing description; now both do. The rule: the label comes from
  the link text when there is one, and from the trailing text otherwise.

## [0.5.1] - 2026-07-25

### Fixed

- **`crux selftest` failed on every machine that isn't the author's.** A v0.5.0 assert
  probed a hardcoded `/Users/<author>/crux` path to check that `detect_install` recognises a
  git checkout — so it tested the *runner's* filesystem, not the function. Green on one Mac,
  `PASSED 321/322` and exit 1 on any Linux or Windows box, which made v0.5.0's own
  advertised post-install check fail for new users. The test now builds a throwaway checkout
  in a temp dir (a `.git` directory is all `detect_install` needs — no git binary, no
  subprocess) and normalises through `realpath`, since macOS hands out temp dirs under
  `/var`, itself a symlink to `/private/var`. **The shipped `update.py` was never wrong** —
  only its test. Reported against v0.5.0 on RHEL 9 / Python 3.11.
- **`crux serve` could stall for seconds before printing its URL.** The stdlib's
  `HTTPServer.server_bind()` does a reverse-DNS lookup (`socket.getfqdn`) purely to fill in a
  `server_name` crux never reads — and it sits between the bind and the banner. Instant on a
  normal machine, >30s on a host with slow or absent DNS (a locked-down cluster node, an
  offline laptop, GitHub's macOS runners). The cockpit now binds without it.
- **crux crashed on a Windows console the moment it printed a glyph.** crux writes UTF-8
  (verdict glyphs, the banner's arrow, the drift warning's ⚠, vault text); a cp1252 console
  raises `UnicodeEncodeError` on the first one and takes the command with it — `crux serve`
  died right after the drift warning, before it could print the URL, and `crux --help` failed
  outright. The CLI now states the encoding it writes in.
- **The selftest harness assumed one platform's text conventions**: every text open now pins
  UTF-8 (Windows read UTF-8 vault files as cp1252 and died before the first check), fixtures
  are written with `newline=""` so they are byte-identical everywhere (Windows turned `\n`
  into `\r\n` and changed a file's sha256 under the source-registry test), and the
  `XDG_CACHE_HOME` assert builds its expected path with `os.path.join` instead of hardcoding
  POSIX separators.
- Added coverage for the symlink resolution `install.sh` depends on (skills symlinked into a
  clone must resolve to the clone, not the link) and for a copied/npx install — neither had a
  test.

### Added

- **CI.** `.github/workflows/selftest.yml` runs `./crux selftest` on ubuntu + macOS across
  Python 3.9/3.11/3.13, plus 3.8 on ubuntu-22.04 (the floor the README advertises), with a
  non-blocking informational Windows job. The repo had no CI, which is why the above shipped.

## [0.5.0] - 2026-07-25

### Added

- **Evidence artifacts.** A hypothesis now points at what its run actually produced: files
  live under `results/<hid>/` in the vault and are linked from a new `## Artifacts` section
  (`[label](path)` or a bare path). `crux validate` errors when a results directory holds
  files but no `.md` report is linked, when a linked path doesn't resolve, or when a path
  escapes the vault; `crux close` only warns, so a hypothesis with no files still closes.
  A hypothesis that has a report shows an **Open report** button under its badges, and the
  cockpit renders it **in the detail pane** — headings, tables, code, and **figures inline**
  (click one to open it full size) — served by a new read-only `GET /file/<path>` route
  (extension allowlist, no traversal, no dot-segments). Symlinking `results/<hid>/` at the
  run directory in your experiment repo is the supported way to keep files where they land.
- **A question closes on an approved synthesis.** `crux answer` now refuses a question that
  has no synthesis node approved by the PI: `crux synthesize "…" --for q3` drafts it,
  `crux approve s1` is the human signature (timestamped, idempotent), and `answer` then
  resolves the question and records `synthesis: s1` on it. Questions resolved by an earlier
  engine are grandfathered — the gate applies to new closes only. **ENGINE_VERSION 1.1 → 1.2.**
- **Markdown is rendered everywhere in the cockpit.** Problem statements, findings, answers
  and goals used to print their markdown source verbatim in the detail pane; they now go
  through the renderer (which gained images and relative-link resolution) — the same one the
  wiki reader uses.
- **Full-screen panels.** Either side of the cockpit can take the whole window, in the Tree
  tab and the Wiki tab: a `⛶` control on each panel, `[` / `]` to maximize, `Esc` to restore.
  Persisted.
- **Focus one question.** Double-click a node (or press `f`, or use the toolbar button on a
  selection) and every branch off its ancestor path folds away — the spine from the root
  stays for orientation, the question's own subtree stays open. A breadcrumb over the tree
  shows the path, with clickable ancestors to widen focus and `✕` / `Esc` to clear.
- **Update check — it tells you, it never installs.** `crux` reports once a day when a newer
  release exists and hands over the exact command for *your* install (`git -C <root> pull
  --ff-only` for a clone, resolved through `install.sh`'s symlinks; `npx skills update` for a
  copied one), plus "ask your agent to update crux" — the `crux` skill now documents the
  preflight an agent must run first. crux deliberately does **not** update itself: a vault
  records the engine version its verdicts were produced under, and that should change because
  someone decided so, not because a background thread did. At most one request per 24h, in a
  background thread with a 1.5s timeout, printed **from a cache** on stderr so no command's
  output waits on the network and stdout stays clean for agents parsing it.
  `CRUX_NO_UPDATE_CHECK=1` disables the whole thing, chip included. The cockpit shows the same
  state as a topbar chip, read from that cache — `serve` never makes a network request. A new
  `CRUX_VERSION` constant carries the release version, separate from the vault-format
  `ENGINE_VERSION`.
- **The living tree.** Every node is spring-anchored to its deterministic layout position,
  so you can drag one (or watch a refresh reshape the tree) and it always glides home —
  entrants fly out of their parent, and the tree comes to rest perfectly still.
  Plus a new **radial view** (toolbar toggle, persisted): the project at the centre,
  questions and hypotheses on depth rings; the orientation toggle applies to the tidy
  view only. Reduced-motion renders the exact static tree as before. Hardened for
  Safari/WebKit (which re-rasterizes SVG text on every repaint): radial spokes are
  trimmed to the pill rims, per-frame writes touch only elements that visibly moved
  (measured 14→60fps on a radial drag), and mass relayouts — a view switch on a big
  vault — glide label-less, the text returning at settle (20→58fps at ~90 nodes).
  (PRD: [`docs/prd/gui-living-tree.md`](docs/prd/gui-living-tree.md).)
- **`crux serve --dir <vault>`.** Point the cockpit at any vault without `cd`-ing into
  it (resolves upward from the given directory, same as the cwd default). Powers the
  README's new zero-setup **Try it in 60 seconds** path over the bundled
  `segssl_vault` example.
- **`crux selftest`.** The engine's test suite is now a first-class verb (it forwards
  to `scaffold/selftest.py`, `--keep` included) — the post-install check is
  `./crux selftest` instead of knowing the script path.
- **Python floor.** The engine states and enforces its requirement: Python ≥ 3.8, with
  a clear message instead of a raw `SyntaxError` on older interpreters.
- **Conditional cockpit polling.** `/snapshot.json` now carries an `ETag`; the webui
  echoes it back and an unchanged vault answers `304` with no body — the ~1/s poll stops
  re-sending the full snapshot when nothing changed (matters for big vaults and battery).
- **`AGENTS.md` + `CONTRIBUTING.md`.** Repo-root orientation for coding agents (layout,
  `./crux` wrapper, the selftest/stdlib-only/read-only gates) — Codex, Cursor, and
  Copilot read `AGENTS.md` natively — plus a thin CONTRIBUTING pointing at the
  `evolve-crux` workflow.

### Changed

- **The colour key is the engine's whole vocabulary.** `inconclusive`, `idea` and `staged`
  were painted on nodes but missing from the legend — `inconclusive` verdicts had no colour
  to look up at all. All ten states are now listed, and a selftest derives the expected set
  from the engine's own constants so the two can't drift apart again.
- **The browser tab names the project** — `crux cockpit: <project>` instead of `crux cockpit`,
  so several open cockpits stay tellable apart.
- **A roomier search box** — 290px, up from a fixed 230px, with a shorter placeholder
  (`Search nodes · ↵ jump`) that fits inside it. It is bounded, not greedy: it never grows
  to swallow the toolbar. Below 1400px the view controls drop to icons (tooltips kept) so
  the box keeps its width on a laptop screen.
- **The tree rests completely still.** The idle "breathing" motion is gone, and the physics
  loop now *stops* once everything is on its anchor instead of animating forever — an idle
  cockpit costs zero animation frames. Drag, fly-home, and relayout glides are unchanged.
- **The bundled `segssl_vault` example** demonstrates the v0.5 model: h1 carries a real
  report (with an SVG chart, a PNG figure, and a CSV) under `results/h1/`, and each resolved
  question carries the approved synthesis that closed it.

### Fixed

- **`crux test --run` kept only the first run link.** The insert point was decided by a
  whole-body `_(none yet)_` probe, so the moment a second section shipped with a placeholder
  of its own (`## Artifacts`), every later run link was silently discarded — no error, and
  the CLI still printed success. Appending is now scoped to the named section, so links
  accumulate in the order they were recorded. (Caught by the v0.5 review pass; regression
  test added.)
- **Artifacts are served under a restrictive CSP.** An SVG is the one allowlisted type that
  is also a *document*: navigate straight to one and its `<script>` would run in the
  cockpit's own origin, where `/snapshot.json` — the whole vault — is same-origin readable.
  `/file/` responses now carry `default-src 'none'; … sandbox` plus `nosniff`, which
  neuters that without affecting `<img>` rendering. Files are also streamed rather than read
  into memory whole.
- **The update check re-hit the network on every command.** Its 24h window was only stamped
  by a *successful* fetch, on a daemon thread that a short-lived command killed on exit — so
  the stamp was never written, the notice never appeared, and every invocation fired another
  abandoned request. The window is now claimed before the request goes out, the worker is no
  longer a daemon, and cache writes are atomic (`os.replace`) so two concurrent crux
  processes can't leave a torn file behind.
- **Artifacts the cockpit can't serve are shown, not linked.** A recorded `.bin`/`.ckpt`
  used to render as a download link that could only ever 404; the servable extension set now
  lives in one place (`engine.SERVABLE_EXT`, keyed to `serve.FILE_TYPES`) and the UI marks
  anything outside it as inert.
- **`CRUX_NO_UPDATE_CHECK=1` now silences the cockpit chip too**, not just the CLI line.
- **The Review button did nothing while a report was open**, and a manual branch-expand while
  focused was undone by the next poll (focus now folds only nodes that *arrive* while it is
  active). The focus button's contextual label also refreshes when the selection is dropped.
- **Post-`init` hint.** `crux init` now prints `next: cd cruxvault && crux ask …` — the
  vault is created *below* the cwd, so the old hint failed with "not inside a crux
  vault" when run verbatim from where the user just ran `init`.
- **`install.sh` cross-agent + portability.** The installer now links skills into both
  `~/.claude/skills` (Claude Code) and `~/.agents/skills` (the shared dir Cursor, Codex,
  Windsurf, and Copilot CLI read); `SKILLS_DIR` still overrides to a single custom dir.
  It fails fast with a clear message under non-bash `sh` (dash), and its final output
  warns that the skills are symlinks into the clone.
- **SKILL.md paths that broke after installation.** `crux-wiki` and `crux-cockpit`
  referenced the engine via repo-root-relative paths (`skills/crux/scaffold/…`) that
  don't exist once skills are installed as siblings; both now use the
  `<crux skill>/scaffold/…` placeholder and tell the agent to install the `crux` skill
  first if the engine is missing. `evolve-crux` no longer hardcodes the maintainer's
  `~/crux` checkout.

### Docs

- **Install docs split.** README's Install section is now a two-command quick install;
  the detail (what gets installed, per-agent notes, scopes, lifecycle, troubleshooting)
  moved to a dedicated [`INSTALL.md`](INSTALL.md).
- **Install section rewritten for accuracy.** Requirements stated (Python ≥ 3.8, git,
  Node.js for the npx path); the npx command gains `--all` (without it the interactive
  picker starts with zero skills selected); all four skills are named; project-vs-global
  scope, updating (`git pull` vs `npx skills update`), uninstalling, the keep-the-clone
  warning, and the restart-your-agent step are documented.
- **Per-agent invocation notes.** README says how skills surface per agent (`/crux` in
  Cursor, `@crux` in Windsurf, `/skills` in Codex, automatic in Claude Code) and warns
  that project-scope `npx` installs drop agent dirs into the repo (`.gitignore` or
  commit deliberately).

## [0.4.0] - 2026-07-12

### Added

- **Wiki tab in the cockpit (Epic 1 × Epic 3).** `crux serve` grows a `Tree | Wiki`
  switcher (shown only on wiki-bearing vaults): an explorer rail with virtual category
  folders + pinned index / log / schema / sources (rail resizable via its own draggable
  divider), a **living force-directed wikilink graph** — Obsidian-like physics: it
  settles with visible ease, nodes are grab-draggable (the neighborhood tugs along and
  springs back), vault changes morph the constellation organically, and the simulation
  sleeps when idle (color = category, size = link degree, hover-highlighted
  neighborhoods, minimizable category key; the tree keeps its deterministic layout) —
  and a markdown **reader** with a backlinks-with-snippets section; `[[wiki/slug]]`
  citations in the tree's detail pane are now live and jump straight into the Wiki tab.
  Tree nodes also light up on hover with the same responsiveness as wiki nodes. Backed
  by an additive `wiki` key in `engine.snapshot()` (index only — no page bodies in the
  1s poll) and a lazy, read-only, traversal-safe `/wiki/<slug>.json` route (body +
  server-computed backlinks; reserved slugs `_index`/`_log`/`_schema` serve the
  specials). Categories get maximally-distinct colors (sorted-order assignment over a
  warm/cool-alternating palette), and a ⚛ button spreads the constellation to a
  pure-repulsion "ion" equilibrium. Wiki search also filters the rail's sources, and the crux-wiki ingest
  convention now carries the full author list in source titles — papers are findable by
  any co-author's name. One vendored static asset — `webui/vendor/motion.js` (motion.dev
  browser build, MIT) — as progressive-enhancement animation only: the UI is fully
  functional without it, the engine stays stdlib-only, and the GUI stays write-free.
  No vault-format change (`ENGINE_VERSION` stays 1.1). PRD: `docs/prd/gui-wiki-tab.md`
  (incl. post-signoff amendments).

- **`./crux`** — a root-level executable wrapper that forwards every argument to the
  engine (`skills/crux/scaffold/crux.py`), so a clone runs `./crux <verb>` directly and
  the repo front page leads with the product's name. Pure delegation; skills installers
  never see it.

- **`crux-cockpit` skill** — the GUI launcher: an agent playbook that runs `crux serve`
  beginning to finish. Locates the vault (or offers vault-setup / a disposable demo vault
  when none exists), kills any stale server for that vault (fresh-start, scoped per vault),
  launches backgrounded with `--no-open`, verifies `/` **and** `/snapshot.json` answer
  before reporting, and hands the user one clickable localhost URL — plus status / stop /
  restart. Covers local **and** remote work: on VS Code Remote-SSH the agent creates the
  port forward itself via the remote CLI (`code --openExternal` — reliable on shared/HPC
  hosts where VS Code's auto-forwarding silently degrades), with click-to-forward and the
  Ports panel as fallbacks; on a plain SSH terminal it hands the user the exact `ssh -L`
  tunnel command (incl. multi-hop `-J` for compute nodes behind a login node); and in any
  remote context it pins the port persistently (`~/.cache/crux-cockpit/`) so an
  always-fresh relaunch can't silently break an open tunnel. Playbook only: no engine
  changes (ENGINE_VERSION stays 1.1).

- **Cockpit GUI polish (Epic 1).** Every question and hypothesis now shows its short code
  (**Q10 / H13**) on the left of the node — and the **compact** node view becomes a clean
  codes-only map. An always-visible **view-only reminder** (a header "View-only" pill plus a
  pinned detail-pane footer) makes explicit that the cockpit never writes: edits go through
  the agent or the crux CLI. The server now sends `Cache-Control: no-store` on every response,
  so a plain browser reload always reflects the latest webui and vault state (no stale-cache
  surprises while iterating). Webui + `serve.py` only; ENGINE_VERSION stays 1.1.

### Fixed

- **Cockpit: detail-pane links were dead when a text size was active.** The review-queue rows
  and the Children / Related links did nothing, because the text-size control writes a
  `data-font` attribute onto the content container and the click handler's
  `closest("[data-font]")` matched that container and returned before reaching its navigation
  branch. The font check is now scoped to its own buttons, so clicking a review row or child
  link opens that node as expected.

## [0.3.0] - 2026-07-11

Two headline additions — a **browser GUI** (Epic 1) and a **literature wiki** (Epic 3).

### Added

- **`crux serve` — a read-only browser cockpit (Epic 1, GUI v1).** A new `serve` verb boots a
  stdlib HTTP server on `127.0.0.1` (auto-selected free port; `--port` / `--open` / `--no-open`),
  prints one clickable `http://localhost:<port>` URL, and opens context-aware across a plain
  terminal / VS Code / Remote-SSH. It serves a no-build vanilla-JS frontend (`webui/`): a
  deterministic, status-colored crux-tree you can pan, zoom (mouse **and** trackpad), collapse /
  expand, search-to-jump, and re-orient (left-right ↔ top-down), in a full-text (default) or
  compact node view, with a **focus-open** mode that collapses every settled question in one
  click; plus a contextual right pane — the review queue by default, a read-only node detail on
  click — with an adjustable text size. Dark (default) and light Obsidian-like themes, each
  concept a unique status color. It live-refreshes from `/snapshot.json` (~1s poll) with stable
  node positions and performs **no writes** — every mutation still goes through the agent/CLI.
  Delivers Epic 1 #2 and #3, and the read halves of #4 and #5.
- **Engine JSON API — `engine.snapshot(vault) -> dict`**, served at `/snapshot.json`: the single
  machine-readable view of a vault (`engine_version`, `project`, `nodes`, `tree`, `queue`).
  Pure-read, stdlib-only, additive. `ledger_block` and `snapshot` share one `ledger_counts`
  roll-up so their numbers cannot drift. (Epic 1 #2.)
- **Literature wiki (Epic 3).** A PI-curated literature layer beside the question / hypothesis
  tree, instantiating Karpathy's LLM-wiki pattern: immutable sources under `raw/`, agent-compiled
  pages under `wiki/`, a new `crux ingest` verb (records source sha256, appends a greppable
  `wiki/log.md` line), an engine-generated `WIKI.md` index, and structural wiki lint folded into
  `crux validate` (broken / flow links, orphans, missing frontmatter, uncompiled or missing
  sources, source-hash drift). Knowledge flows one way — literature → wiki → tree; a project's own
  findings never enter the wiki. New sibling skill **crux-wiki** carries the agent-side
  conventions (compile / query / semantic lint).

### Changed

- `ENGINE_VERSION` → **1.1** — additive only (the wiki's `WIKI.md` / `raw/` layout and the
  read-only snapshot API). Pre-wiki vaults load unchanged and stand up the wiki lazily on first
  ingest; no migration required. `crux validate` now also runs the wiki structural lint.

[0.5.1]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.5.1
[0.5.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.5.0
[0.4.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.4.0
[0.3.0]: https://github.com/mehdiforoozandeh/crux/releases/tag/v0.3.0
