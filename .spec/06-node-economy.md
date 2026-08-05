# Spec 06 — Node economy

**Label:** `economy` · **Status:** ☐ todo
**Blocks:** [07 RD layer](07-rd-layer.md), [08 taskhub](08-taskhub.md), [09 specialized agents](09-specialized-agents.md)

## Goal

Make crux enforce **economy** the way it already enforces **falsifiability**. Today every
guardrail in the engine and the skill pushes toward more rigor and none pushes toward less
volume, so nodes grow without bound until the vault is unreadable by the PI it exists to
serve.

Target outcome: a PI can open any node in the cockpit, read it in under a minute, and know
what is being asked, what would settle it, and where the detail lives.

## Motivation — the evidence

Measured on the CANDI vault (2026-08-04): 22 questions, 70 hypotheses, 0 syntheses.
Question nodes total 14,237 words; hypothesis nodes 40,851.

Node size is bimodal, and the split is by **authoring path**, not by intrinsic complexity:

| how the node was created | when | words per node |
|---|---|---|
| q1–q14, materialized by `init --from seed.md` | 07-02 | **101–153** (one outlier, q4, at 376) |
| h49–h58, batch-proposed as a sub-tree | 07-24 | **286–477** |
| q15–q21, opened one at a time in conversation | 07-03 → 08-02 | 414 → **5,725** |
| h59–h70, negotiated one at a time | 08-02 | up to **3,591** |

The seed grammar is one line per node (`- Q: an open question`), so a long node is
structurally impossible. `crux ask` takes a free-text `--body`, and after creation the agent
simply opens the `.md` and writes into it. Same agent, same project, same fortnight — a 40×
difference driven entirely by which path was used.

**Nodes are born bloated, not grown.** `git log` shows q19 was already 3,228 words in its
first commit. Accretion happens too (q21 carries 18 `AMENDED` / `PI ruling` markers across
two days) but it is the second effect, not the first.

### Root cause

The engine has **no size or fan-out limit anywhere**. `validate()` checks types, required
frontmatter, parent integrity, verifiable presence on `running`/`done` ideas, artifact
resolution, ledger markers, and cycles. Nothing can observe that q21 has 11 children and
5,725 words, or that 24 hypotheses vault-wide have never been run.

The templates are innocent. `question.md` ships three sections — the title, `## Answer so
far`, and the ledger. Every one of q21's headings (`TL;DR`, `ELI5`, `Why it is worth
answering`, `How it closes`, `Cost`, `PI rulings`, `Details`) is agent-invented.

### Compounding: nothing closes

7 questions `open`, **12 in `review`**, 2 `resolved`. Zero syntheses have ever been written,
and `crux answer` refuses a question without an approved one. 24 hypotheses remain `idea`.
The gate fires and is ignored, so the tree is pure accumulation.

### Contributing, minor

- **Chat-format leakage.** q21 and h60 carry `### TL;DR` / `### ELI5` headings — the user's
  global response-format rule, which explicitly scopes itself to chat and not to files on
  disk, applied to files on disk. *(Superseded as a defect by this spec: see Decisions.)*
- **`investigate` / `spec` (vendored gstack) carry an explicit expansion doctrine** — *"AI
  makes completeness cheap, so the complete thing is the goal… boil the ocean one lake at a
  time"*, plus a `Completeness: X/10` score where 10 = all edge cases. A real thumb on the
  scale whenever either loads, but not needed to explain q15–q21.

## Design

### 1. Required summary sections

Both `question.md` and `idea.md` gain, immediately under the H1:

```markdown
## ELI5

_(one sentence, plain language, no jargon)_

## TL;DR

_(one paragraph: what this asks/claims, and what would settle it)_
```

**Body sections, not frontmatter.** The engine's YAML is deliberately a flat map of scalars
(`engine.py` — *"We control the schema… That lets us avoid a YAML dependency while staying
Obsidian-compatible"*). A paragraph-length `tldr:` would be one enormous quoted line,
unreadable in Obsidian and hostile to hand-editing. Body sections also cost almost nothing to
consume: `_section(body, heading)` already extracts by heading, exactly as it does for
`Problem Statement` and `Findings`.

### 2. The prose cap

**400 words**, counting **prose sections only**:

| node | counted |
|---|---|
| question | `## ELI5` + `## TL;DR` + `## Question` + `## Answer so far` |
| hypothesis | `## ELI5` + `## TL;DR` + `## Problem Statement` + `## Idea / Hypothesis` + `## Planned Intervention` + `## Findings` |

**Not counted:** `## Verifiables`, `## Run Links`, `## Artifacts`, and the generated
`<!-- crux:ledger -->` block. These are structured lists, they are not the bloat, and capping
them would punish thoroughness in the one place it is wanted.

ELI5 and TL;DR count *inside* the 400 rather than on top of it — otherwise the change just
raises the ceiling.

### 3. Three overflow channels

A cap without an outlet makes prose denser, not shorter. q21 is one file doing three jobs:

| what's in q21 | where it belongs |
|---|---|
| design detail — probe ladder, capacity certificates, the estimand | **RD** ([07](07-rd-layer.md)) |
| open work items — "re-bake MERGED with replicate cells", "dedupe the 133 reused accessions" | **taskhub** ([08](08-taskhub.md)) |
| decision history — 18 × `AMENDED 2026-08-04 (PI ruling 4b)` | **git log** |

The third is free and unused. 79 of the CANDI vault's 92 node files are already git-tracked;
`git log -p q21.md` *is* the changelog. The rule — **when the PI rules, edit the text; the
diff is the history** — removes roughly 1,500 words from q21 by itself and costs nothing to
implement beyond writing it down.

### 4. Cockpit

`_node_json` currently sets a question's `detail` to the entire `## Question` section. For
q21 that dumps 5,000 words into the detail pane, and it is the single line most responsible
for the cockpit being unskimmable. Add `eli5` and `tldr` snapshot keys; the pane leads with
them and collapses the rest behind a disclosure.

### 5. Fan-out back-pressure

`crux hypothesize` warns (or refuses under `--strict`) when the parent question already has
N unrun `idea` children. q21 had 10 when the 11th was added.

### 6. CLI surface for agents

`--json` on the existing verbs, plus a `--check=<list>` selector on `validate`. Needed by
[09](09-specialized-agents.md), where agents drive deterministic checks; putting the toolbelt
in the CLI rather than in agent-private scripts means `selftest.py` can assert it, the cockpit
can consume the same output, and the PI can run any of it by hand.

## Decisions

| decision | rationale |
|---|---|
| ELI5/TL;DR as body sections, not frontmatter | flat-scalar YAML by design; `_section()` already extracts by heading |
| cap prose sections only | verifiables and artifacts are structured, not bloat |
| ELI5/TL;DR count inside the 400 | otherwise it is a ceiling raise, not a cap |
| decision history goes to git, not into the body | already tracked; `AMENDED` blocks duplicate `git log -p` |
| required ELI5/TL;DR is **not** the format leak we diagnosed | the leak was *unbounded* chat formatting on disk; a fixed, bounded schema slot is the opposite — it forces compression. An earlier proposal to lint for `### TL;DR` in nodes is **withdrawn**. |
| agent toolbelt lives in the CLI | selftest can assert it; cockpit reuses it; PI can run it |

## Rejected alternatives

- **Fixing this in `CLAUDE.md`.** The global instruction already says the response-format
  rules apply to chat and not to files on disk, and it was ignored anyway. Restating an
  instruction that already failed is not a fix; a check is.
- **Fixing this only in the crux skill.** Same reasoning. The skill already says "keep the
  science explicit and falsifiable" and produced 5,725-word nodes. Instructions were never
  the binding constraint.
- **Blaming the harness.** The chat-format leak and the gstack completeness doctrine are both
  real and both documented above, but q15–q21 do not need either to be explained. Recorded so
  nobody re-runs the investigation.
- **A hard word cap on verifiables or artifacts.** See above — wrong target.

## Open questions

- **Enforcement level.** Three candidates, undecided:
  1. warn by default, `validate --strict` exits non-zero *(recommended)*
  2. hard error immediately
  3. warn on existing vaults, hard from birth for vaults created at the new `ENGINE_VERSION`

  The stakes are concrete: a hard error puts the CANDI vault into permanent red on q19, q21,
  h48, h59 and h60 until those five are refactored into RDs — bundling a migration project
  onto a feature. The codebase already distinguishes tiers (`artifact_problems` vs
  `artifact_warnings`), so a warn tier is not a new concept.
- The exact fan-out threshold N.

## Work items

- ☐ Add `## ELI5` / `## TL;DR` to `templates/question.md` and `templates/idea.md`
- ☐ Prose-word counter + cap check in `validate()`, prose sections only
- ☐ Fan-out check: unrun `idea` children per question
- ☐ `eli5` / `tldr` keys in `_node_json`; cockpit leads with them, collapses `detail`
- ☐ `--json` on existing verbs; `--check=<list>` selector on `validate`
- ☐ Back-pressure in `cmd_hypothesize`
- ☐ Skill rule: on a PI ruling, **edit** the node; never append an `AMENDED` block
- ☐ `ENGINE_VERSION` → 1.3 + proof an old-format vault still loads

## Acceptance criteria

- A vault created at 1.3 has ELI5 and TL;DR on every question and hypothesis.
- `validate` reports every node whose counted prose exceeds 400 words, and reports nothing
  for a node under it.
- Verifiable-heavy and artifact-heavy nodes do **not** trip the cap.
- An old-format (pre-1.3) vault loads, validates, and reports drift rather than erroring.
- `snapshot` exposes `eli5` and `tldr`; the cockpit detail pane opens with them.
- `selftest.py` passes with a grown assert count.
