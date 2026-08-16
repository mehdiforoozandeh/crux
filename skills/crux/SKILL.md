---
name: crux
description: "An agentic research companion — a scientific-method lab notebook for navigating large research programs. Organize work as a tree of Questions (what we don't know) and falsifiable Hypotheses (testable leaves), each with pre-registered verifiables and findings; a deterministic engine rolls results up into per-question answers, trips a human review gate, and regenerates an Obsidian-graphable META + experiments registry. Use when the user wants to run a research program rigorously: open/track research questions, design experiments as problem-statement → hypothesis → verifiables → findings, synthesize results, and update the open questions. Triggers: crux, \"open a research question\", \"lab notebook\", \"hypothesis/experiment tracking\", \"design an experiment\", \"what should we try next\", \"research notebook\", scientific method, meta-questions, research vault."
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  notice: Bundled engine is original MIT work; no third-party code.
---

# crux — an agentic research companion

`crux` turns a research program into a **scientific-method lab notebook**: a tree of
**Questions** (what we don't know) and **Hypotheses** (falsifiable, testable leaves),
rooted at a **Project**. A deterministic engine (`scaffold/`, a Python CLI) does the
bookkeeping — IDs, the `Parent::` tree, validators, the evidence-ledger roll-up, the
review gate, and regenerating `META.md` + `EXPERIMENTS.md`. The vault is plain markdown,
openable in Obsidian (graph mode shows the question/hypothesis tree).

You (the Agent) operate the engine on the researcher's behalf. The engine never judges;
**you** supply the science and the researcher (the **PI**) makes the calls.

## When to use this

The user is running a research program and wants it tracked rigorously: opening research
questions, designing experiments as problem → hypothesis → verifiables → findings,
recording results, deciding when a question is answered, and updating what's still open.
Not for one-off tasks with no hypothesis, and not for launching the runs themselves
(crux *records* runs; your training/job harness launches them).

## The model

- **Project** — the root node, one per vault.
- **Question** (`q*`) — has **no verifiables of its own**; it is resolved by **aggregating
  its children's findings**. Questions nest (a question's parent can be another question).
- **Hypothesis** (`h*`) — a falsifiable leaf under a question, with `## Verifiables`
  (pre-registered checks), `## Findings`, and `## Artifacts` — what the run produced.
- **Synthesis** (`s*`) — the written verdict of a question. A question **cannot close
  without one, approved by the PI** (see Lifecycles).

A hypothesis's `## Findings` can spawn **new** child questions — that's the loop reopening.
The tree is the `Parent:: [[…]]` wikilink in each file; `META.md`/`EXPERIMENTS.md` are
generated views (never hand-edit).

**Every question and hypothesis opens with `## ELI5` (one sentence, no jargon) and `## TL;DR`
(one paragraph: what it asks or claims, and what would settle it).** Write both when you
create the node. They are what the PI reads first in the cockpit, and they are the node's
job description — if you can't write the TL;DR, the node isn't ready to exist yet.

**Literature wiki (optional).** A crux vault can carry a `raw/` + `wiki/` **literature layer**
— prior methods, SOTA, baselines, definitions the agent compiles and draws on. It's a separate
skill (**crux-wiki**) sharing this engine; when proposing questions/hypotheses, consult
`WIKI.md` if the vault has one. Knowledge flows one way: literature → wiki → tree; findings
never enter the wiki.

**Evidence artifacts.** Whatever a run produced — the report, figures, tables — belongs in
`results/<hid>/` inside the vault, linked from the hypothesis's `## Artifacts`:

```markdown
## Artifacts

- [Full report](results/h1/report.md)
- results/h1/miou-by-seed.svg ADE20K val mIoU by seed
```

Paths are vault-relative (symlink `results/<hid>/` at your real run directory if the files
live elsewhere). `crux validate` **errors** when `results/<hid>/` holds files but no `.md`
report is linked, when a linked path doesn't resolve, or when one escapes the vault;
`crux close` only warns, so a hypothesis with no files still closes. The cockpit renders a
linked report — markdown, tables, and figures — in its right-hand pane.

**Lifecycles**
- Hypothesis: `idea → staged → running → done`. Verdict is **derived on close** — never
  written by you — from three things: the **kind** of each verifiable, the declared
  **combination rule**, and the pass/fail vector. Five verdicts exist:
  `supported` · `refuted` · `inconclusive` · `invalid-run` · `partial` *(retired — see below)*.
  - Every verifiable is either **`[hypothesis]`** (a consequence of the claim; feeds the
    verdict) or **`[outcome-neutral]`** (a positive control / sanity check that must pass
    *whatever* the claim turns out to be). A failed or unread control gives **`invalid-run`**:
    the experiment tells us nothing and must be re-run. It is never a refutation — without a
    passing control, "the claim is false" and "the apparatus is broken" are the same picture.
  - The hypothesis declares **how its claim-directed checks add up**, before the run:
    `rule: all | any | m-of-n` (`crux hypothesize --rule`). That is what turns "two of four
    passed" from an argument into arithmetic. Under `m-of-n`, exactly one short is
    `inconclusive`; two or more short is `refuted`.
  - **`inconclusive` is derived, never chosen.** There is no flag that sets it — you can only
    arrive there. That is what stops it becoming the drawer everything ambiguous gets swept
    into.
  - **The boundary is permanent.** These rules bind hypotheses created at or after engine
    v1.6 (they carry `schema: 1`). Anything older keeps the verdict it was recorded with,
    forever, and is never re-checked, re-verdicted or flagged — that is why `partial` still
    exists in the vocabulary. **Do not "fix" an old node to the new schema.** Re-declaring
    what would settle a claim is a scientific act, so it is the PI's call, one node at a time.
- Question: `open → review → resolved`. The engine trips `open → review` automatically
  once every direct child is terminal. **Closing it is always the PI's call**, and it now
  takes a **synthesis the PI has approved**:

  ```bash
  crux synthesize "what q3 settled" --for q3   # ◆ you draft it (headline conclusions,
                                               #   cross-run table, implications)
  crux approve s1                              # ◆ ONLY after the PI has read and OK'd it
  crux answer q3 -t "the standing answer"      # ◆ now permitted; stamps synthesis: s1
  ```

  `crux answer` **refuses** a question with no approved synthesis. Never run `approve`
  on your own judgment — it is the PI's signature, and it is what the engine checks.
  (Questions resolved by a pre-1.2 vault are grandfathered and stay valid.)

**Updating crux.** Any crux command may print `crux: vX.Y.Z is available …` on stderr (once a
day, from a cache — it never blocks and never installs anything). If the PI asks you to update:

1. **A clone install** (the notice names it — `git -C <root> pull --ff-only`): check the tree
   is clean and on the default branch first (`git -C <root> status --short --branch`). If it
   is dirty, on a feature branch, or the pull is not a fast-forward, **stop and say so** —
   do not stash, reset, force, or merge to make it apply.
2. **A skills install**: `npx skills update`.
3. Then tell the PI to re-run their command; the new engine takes effect on the next
   invocation, not the one in flight.

A newer engine may carry a newer vault format. The first command against an existing vault
will warn about **engine drift** and re-stamp it — surface that warning verbatim; if the PI
needs to reproduce recorded results exactly, the answer is to pin the old engine, not to
ignore the warning. `CRUX_NO_UPDATE_CHECK=1` switches the whole check off.

## The taskhub — where doing goes

**Science goes in the tree. Doing goes in the taskhub.** A task is an **action**. If it is a
claim about the world that could be true or false, it is a hypothesis and belongs in the
tree.

**What gets in — one question:** *would you be annoyed if this vanished next week?* If yes it
belongs in the taskhub, however small — "fetch the antibody lot from the ENCODE portal"
passes. If no it is session scratch — "re-read h59's verifiables" — and stays in your own
todo list, which may point *at* a taskhub item but never lands in the vault. Persisting your
scratch so the PI can see what you did is the transcript's job. Tasks can be fine-grained;
they cannot be ephemeral. Rule of thumb: **a task should fit in one context window.**

**When status changes.** `done` means it produced something *and that something is linked* —
the engine refuses a `done` with no resolving output. Write the real output, not the nearest
thing that resolves. External blockers are not a state: "waiting on cluster quota" is a
dependency on a task called **obtain cluster quota**. One rule instead of two.

### The line, and where it moved

> **Work never creates direction. Work produces outputs — and an output that is evidence
> about a hypothesis enters the gated tier.**

- Adding, completing and dropping an **ordinary task** is **act-and-report** (`○`). It sets
  no direction, spends no compute and records no scientific result, so the PI needn't be
  concerned with it.
- Completing an **experiment** — a task that declares what it concluded about a hypothesis —
  is **propose → PI accepts → then do** (`◆`). `crux task accept` is their signature, exactly
  like `crux approve`. Never run it on your own judgment.
- **The moment a task would open a question, it stops being a task.** Convert it to a tree
  node and go through the normal gate. This is the one rule the engine cannot check — it
  cannot tell that a task's title is really a question — so it is the one that most needs
  saying.

### Two provenances, one vocabulary

An experiment's conclusion and a hypothesis's verdict use the **same four tokens**
(`supported` · `refuted` · `inconclusive` · `invalid-run`) and are produced by **different
mechanisms**:

| | who produces it | from what |
|---|---|---|
| a hypothesis's `verdict` | the **engine** | its tick vector under the declared combination rule |
| an experiment's conclusion | **you**, PI-accepted | what this run showed about that hypothesis |

So recording `h44:refuted` on an experiment does **not** close h44 — it tells the PI to go
look. Closing h44 is still `crux close h44` after they have ticked the boxes. You never tick
a box the evidence does not support, and you never record a verdict the PI has not accepted.

An experiment may bear on a hypothesis written before evidence semantics existed; the
conclusion is a record on the **task's** side and never re-verdicts the old node.

## Three roles — and the leash

- **Engine (○ deterministic).** Bookkeeping only — never judges, never reads run logs.
- **Agent (◆ judgment, drafts).** You: phrase questions, write hypotheses + verifiables,
  turn run results into a per-box verdict + headline metric, draft interpretations.
- **PI (◆ judgment, decides).** The human: which questions matter, which hypotheses are
  worth a run, the verifiable bar, and the close/reopen call.

**Leash rule** — crux is **human-in-charge by default** (this is fixed, not configurable):
- **Read-only / bookkeeping** (`status`, `review`, `validate`, `test --to staged`): act, then report.
- **Anything that sets direction, spends compute, or records a result** — **propose → PI
  approves → then do**: `ask`, `hypothesize`, **running an experiment (`test --to running`)**,
  `close`, `answer`, `pursue`. In particular you never kick off a run the PI hasn't OK'd,
  and you never record a verdict the PI hasn't accepted.
- **Taskhub**: ordinary tasks are act-and-report; **completing an experiment is PI-gated**
  (`crux task accept`) because its output is evidence. See *The taskhub* above.
- **`review` gate + `synthesize` → `approve` → `answer`**: always the PI's. Surface the
  gate, draft the synthesis, then stop — `approve` is their signature, not yours.

## Setting up a vault (first run)

When the user wants to start using crux in a project, **you** stand up the vault — they
should only think about the science. Never hand them a schema to fill in; run it as a
conversation and do the assembly yourself.

**One adaptive entry.** Open with a single question that covers every case:

> "Point me at anything that describes or contains this project — a proposal, notes, a
> draft paper, or your existing code/results — and I'll draft your crux setup from it.
> If there's nothing to read yet, we'll define it together."

The user never picks a "mode"; you adapt to how much material exists:
- **Descriptive docs** (proposal / grant / notes / draft) → read them.
- **An existing repo** (code, results, figures, READMEs) → read it. *(This is migration.)*
- **Nothing written yet** → a short pingpong/grill-me to pull the project out of their
  head: what are you trying to figure out or build? the big open questions? for the
  sharpest one, a specific testable hunch — and how you'd know if it's true?

**Then: draft one seed outline → they approve → the engine writes it.** Whatever the
source, converge on a single human-editable **seed file** (this *is* the proposal), show
it, let them edit/approve it as one block, then materialize the whole vault atomically:

```bash
python <skill>/scaffold/crux.py init --from seed.md --dir cruxvault
```

Don't create nodes one verb at a time during setup — approval happens on the seed.

**Seed format** (full table in `scaffold/README.md`) — indented bullets, 2-space indent =
nesting, a type prefix per line:

```
- Project: TITLE — GOAL
  - Q: an open question
    - Q: a nested question
      - H: a hypothesis to run
        - v: metric ≥ threshold vs baseline
      - H: [tested] work already done          # migration only
        - v: [x] a met check (found: 0.46 → 0.48)
        - v: [ ] an unmet check
        - finding: one-line result
```

The engine enforces the model: exactly one `Project`; `Q` under Project/`Q`; `H` under a
`Q`; `v`/`finding` under an `H`. It validates the whole seed before writing anything, so a
malformed seed leaves nothing behind.

**Reconstructing finished work (migration).** For work already done, mark the hypothesis
`[tested]`, tick its verifiables from the evidence you found (`[x]` met · `[ ]` unmet ·
`[-]` n/a, with a `(found: …)` note) and add a `finding:`. The engine derives the verdict
**mechanically** from your ticks — you propose the ticks, never the verdict. **Show your
evidence for each tick** and let the human approve the whole reconstructed seed before it's
recorded. Fresh (un-`[tested]`) hypotheses land as open ideas to run through the normal loop.

**Migration guardrail — absolute.** When reading an existing repo you may read anything,
but you may **only ever create, edit, move, or delete files under `cruxvault/`**. Never touch
the user's code, data, results, or docs. The vault is the only thing you write.

## The verbs

Run them via the engine CLI (see `scaffold/README.md`). `◆` = you draft + PI confirms; `○` = act-and-report.

| verb | aliases | role | what it does |
|------|---------|------|--------------|
| `init` | start, new | ○ | bootstrap a vault (`--from seed.md` = materialize a whole tree; see **Setup**) |
| `ask` | question, q, meta | ◆ | open a Question under the project or another question |
| `hypothesize` | hypothesis, idea | ◆ | add a hypothesis under a question — **register `-v` verifiables** |
| `test` | experiment, run, stage, launch | ◆ | `idea → staged → running`, attach a run link — **running needs PI's OK** |
| `close` | record, conclude, verdict, land | ◆ | derive verdict from verifiables + write findings → roll up |
| `review` | gate, decide | ○ | list questions awaiting the PI's decision |
| `answer` | resolve, settle | ◆ | PI resolves a question — **requires an approved synthesis** |
| `pursue` | branch, extend, reopen | ◆ | keep a question open; optionally spawn a fresh hypothesis |
| `status` | map, tree, where, show | ○ | print the tree / a node's ledger |
| `synthesize` | weave, rollup | ◆ | draft the synthesis that closes a question (`--for q3`), or weave several |
| `approve` | sign-off, signoff | ◆ | **the PI's signature on a synthesis** — never run this on your own judgment |
| `rd` | design, requirements | ◆ | write the Requirements Document for a node's design — the detail the 400-word cap displaces; one active RD per node, `--supersedes` to replace one (see the **crux-rd** skill) |
| `ingest` | source, add-source | ○→◆ | register a PI-curated `raw/` source into the literature wiki (then compile pages — see the **crux-wiki** skill) |
| `serve` | gui, ui, cockpit | ○ | open the read-only browser cockpit (localhost; view-only — tree, review gate, rendered reports + figures; launch playbook: the **crux-cockpit** skill) |
| `task add` \| `done` \| `drop` \| `list` \| `show` \| `categories` | todo, work | ○ | the work layer: append a task, close it with an output, query the frontier |
| `task accept` | sign-off | ◆ | **the PI accepts what an experiment concluded** — never run this on your own judgment |
| `task review` | — | ○ | experiments awaiting the PI's acceptance |
| `validate` | lint, check | ○ | integrity checks (tree + wiki + rd + tasks lint, plus the economy warnings). `--strict` fails on warnings; `--check=tree,economy` runs a subset |

Every verb above except `init`/`serve`/`selftest` takes **`--json`** — use it when you need to
read a result back rather than show it. `crux status --json` is the whole vault; `crux status
q3 --json` is one node; `crux validate --json` is `{ok, checks, problems, warnings}`.

## How you run a session

You are a conversational front-end to the engine. Translate the PI's natural language into
the right verb, **propose** the concrete node, get a yes, **then** run the command. Keep the
science explicit and falsifiable.

> **PI:** I think JEPA pretraining could help.
> **You:** That's a *Question* (no single verifiable). Open it under the project as
> *"Can JEPA pretraining improve CANDI?"* — yes?
> **PI:** yes
> **You:** → `crux ask "Can JEPA pretraining improve CANDI?"` (`q1`). First hypothesis under it?
> **PI:** masked-token beats masked-stem.
> **You:** Verifiable bar — I'd set *imp-Spearman ≥ +0.01 vs the stem baseline on held-out*. Good, or tighter?
> **PI:** good
> **You:** → `crux hypothesize "masked-token beats masked-stem" -p q1 -v "imp-Spearman ≥ +0.01 vs stem"`

**Granularity:** per-node confirm by default; when the PI says "draft me the next N," batch-propose a
sub-tree (a question + several hypotheses + verifiables) and let them approve/edit it as one block.

**Closing a case:** read the run results, tick each verifiable in the idea's `## Verifiables`
(`- [x]`/`- [ ]`/`- [-]`), write a one-paragraph `## Findings`, link the run's report and figures
under `## Artifacts`, then `crux close h1 -m "<metric>"`. The engine derives the verdict and rolls
it up.

**At a `review` gate:** present the question's ledger and your read of the evidence, then let the PI
choose `answer` (resolve) or `pursue` (keep digging). Never decide for them. If they resolve it,
draft the synthesis (`crux synthesize "…" --for q3`), show it, and wait — `crux approve` is theirs,
and `crux answer` will refuse until it's signed.

## Guardrails

- **Vocabulary — read `glossary.md` when you first touch a vault.** It is not a dictionary,
  it is a model of what the PI already knows. A term under `## Terms` may be used **bare**.
  Anything else you bring in — gloss it in the same breath, or ask. This holds for node prose
  *and* for what you say to the PI, who should never be talked at in terminology they have
  not agreed to. When `crux validate --check=glossary --propose "<term>"` surfaces a
  candidate, ask about it **inline, one at a time**, and record the answer with
  `crux glossary accept "<term>" -d "<one line>"` or `crux glossary decline "<term>"`.
  **Never write to `glossary.md` directly** — membership is a claim about the PI, so only the
  PI makes it. A term already declined is settled; do not raise it again.
- **Pre-register verifiables.** A hypothesis isn't testable until its `## Verifiables` state a metric +
  baseline + threshold. The engine refuses to mark an idea `running` with none, with no
  `[outcome-neutral]` control (or a written `neutral_optout:` reason), or — once there is
  more than one claim-directed check — with no combination rule. When you choose `all`, say
  the cost out loud: **two checks at 80% power each give 64% joint power, and thresholds may
  not be loosened to compensate.**
- **The commitment is locked when the run starts.** Going `running` content-hashes the
  checks, their kinds and the rule. A later edit is *allowed* — research does discover a
  check was wrong — but it raises a permanent **drift** flag on the node, in `validate`, and
  beside the question in `crux review`. It blocks nothing. Say what changed and why in the
  node; `git log -p <node>.md` is the diff.

### A mixed result is a symptom, not an outcome

Some checks passed, some did not — that is not a finding, it is a report that something
upstream went wrong. Verifiables under one hypothesis are *supposed* to correlate: they are
consequences of the same claim, so if it is true most pass together. Three diseases produce
the same symptom, and it never announces which one it has:

| cause | what actually went wrong | who fixes it |
|---|---|---|
| **compound claim** | the "hypothesis" was two or three claims; each check answered a different one | `crux-critic` — split the node |
| **non-entailed check** | the check does not follow from the claim; it tests something adjacent | `crux-verifiables` — rewrite the check |
| **the run could not discriminate** | underpowered, confounded, wrong instrument, no control | `crux-design` — fix the design |

The question that makes this operational, and it belongs **before** the compute is spent, not
after:

> **Is there any plausible outcome of this run from which we would conclude nothing?**
> If yes, the design is wrong — fix it before spending the compute.

Answer it by enumerating the outcomes: take the pass/fail vector under the declared rule, plus
the case where a control fails, and write the sentence you would be able to say for each. If
one of those sentences is *"we learned nothing"*, that is the design defect, and it is
cheapest to fix now.

The engine owns the presence of a declaration, never its quality. Before a run, a hypothesis
should carry a control, a combination rule, and — in frontmatter, beside `rule:` —
`measurement:` (what is measured, and with what instrument) and `replicates:` (the n the claim
will rest on). `crux validate` reports the gaps as information; whether the control is the
*right* control is judgment. Note that `measurement:` is **not** `metric:` — the second is the
headline result, written at `close`.

### One experiment, several hypotheses — when that is allowed

> **One experiment settles several hypotheses separately only when** each hypothesis is
> turned by its own independently varied knob — a comparison the design can attribute to it
> alone, at a resolution high enough for the kind of effect it claims — and no single shared
> ingredient (one batch, one seed, one preprocessing path, one control) could flip all the
> answers together without a pre-declared outcome-neutral check catching it and voiding the
> whole run; **anything less means you ran one experiment with many labels, not many
> answers.**

Three checks, in the order they fail:
- **Different lever.** Each hypothesis is turned by its own independently varied knob — its
  own comparison, not shared with another and not a by-product of two others.
- **Different failure.** No single shared ingredient may flip every answer at once
  undetected. Block it, replicate it, cover it with an `[outcome-neutral]` check, or log it
  as a risk on every hypothesis in the bundle. This is what outcome-neutral checks are *for*:
  they are the dual of a shared failure, so **sharing one across a bundle is the fix, not the
  flaw**.
- **Different verdict.** Each hypothesis carries its own checks, its own rule, and can be
  stated without reference to the others. If flipping one answer would change another, they
  were never separable — that is one compound claim wearing several labels.
- **Never hand-edit generated content** — `META.md`, `EXPERIMENTS.md`, or the `<!-- crux:ledger -->`
  block inside a question. Run a verb and let the engine regenerate. You *do* write the question's
  `## Answer so far` prose (above the ledger) and the idea's `## Findings`.
- **The engine is domain-agnostic.** It never parses logs/metrics — you supply the per-box verdict and
  a headline metric string. This is what keeps crux reusable across projects.
- **One parent per node** (it's a tree). Use extra `[[links]]` for "see also" — they show in the graph
  but don't affect roll-up.
- **Keep a node under 400 words of prose.** The budget covers `ELI5` + `TL;DR` + the framing
  sections + `Answer so far` / `Findings`. It does **not** cover `## Verifiables`,
  `## Run Links` or `## Artifacts` — be as thorough there as the science needs; the cap is
  aimed at prose, not at rigor. `crux validate` says which nodes are over.

  A node that wants more room is usually one node doing several jobs. Split the question,
  or move the design detail into the report you link under `## Artifacts`.
- **When the PI rules, edit the text — the diff is the history.** Never append an
  `AMENDED 2026-08-04 (PI ruling)` block to a node. Vault files are git-tracked, so
  `git log -p <node>.md` already *is* the changelog, and appending rulings is how a
  600-word node quietly becomes a 5,000-word one. Rewrite the affected sentence in place.
- **Don't stockpile hypotheses.** Five proposed-but-unrun hypotheses under one question is
  the cap; past that `crux hypothesize` warns and `validate` flags the question. Run or close
  some before proposing more — an unrun hypothesis costs nothing to write and buys nothing
  until it's tested.
- **Node files are files, not chat.** Your response-formatting habits don't apply here: no
  `### TL;DR`-style improvised headings beyond the schema above, no restating the section
  you just wrote. The node's schema is the format.

## Running the engine

```bash
cd <vault>                       # or anywhere under it; the engine finds .crux.yaml upward
python <skill>/scaffold/crux.py <verb> [...]   # --help on every verb
```
A vault is created by `init` (or `init --from seed.md` at setup) and contains: the project
node, `q*`/`h*` node files, `s*` synthesis files, `results/<hid>/` evidence artifacts, the
generated `META.md` + `EXPERIMENTS.md`, and `.crux.yaml` (config + ID counters + the
`engine_version` stamp). The vault is the only
thing you write into the user's repo — the engine itself stays in the skill install. On a
version mismatch the engine warns about drift and re-stamps; surface that warning to the PI.

**Validate the install:** `python scaffold/selftest.py` builds a dummy vault and asserts every
invariant (roll-up, gate, idempotency, integrity, CLI help) — no GPU/tokens/SLURM. Add `--keep ./demo`
to keep the vault and open it in Obsidian.

## `scaffold/`
`crux.py` (CLI) · `engine.py` (model, validators, ledger, gate, transitions) · `render.py`
(generated views) · `templates/` (node skeletons — editable) · `selftest.py` · `README.md` (CLI reference).
