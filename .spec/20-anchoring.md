# Spec 20 — Anchoring: every item serves the question above it

- **Kind:** feature (capture rules, one node section, one finding flag, one closure cap, one wrap step)
- **Spec:** extends [19](19-background-memory.md); answers its open question 1 (pruning).
- **Status:** draft, 2026-10-31. Decisions (i)–(viii) below are PI rulings.
- **Research:** [research/research-drift.md](research/research-drift.md).
- **Release:** `ENGINE_VERSION` 4.0 → 4.1 (decision vi changes the roll-up).

## Problem

Over a long project, sub-questions and hypotheses pile up. Each finding opens new questions,
and the work drifts away from the top question. Crux already makes each hypothesis falsifiable
(an expectation before evidence, a locked set of checks). Nothing makes an item say how its
answer helps the question above it, and nothing asks again whether a line of work still serves
the top question.

## Goal

Every question and hypothesis states how its answer would move its parent's answer. The agent
keeps the top question in view, parks tangents, treats exploration as a source of leads, and
asks whether stalled lines still serve the top question. **Crux stays lean**: no new node type,
no new verb, no new agent, no timer.

## Decisions

| # | Decision | Ruling |
|---|---|---|
| i | Scope | All five rules from the research, in one spec. |
| ii | Bears-on form | Its own section, `## Bears on`, on questions and hypotheses. |
| iii | Hypotheses | `## Bears on` sits beside `## Problem Statement`; neither replaces the other. |
| iv | Enforcement | `crux ask` and `crux hypothesize` refuse without `--bears`. The Python API keeps it optional, so the seed path, autopilot and existing tests are unchanged. Old items without it get one info line from `validate`, never an error. |
| v | No bears-on line | The agent cannot write one → the item goes to the pending list, and `/crux-wrap` asks the PI. |
| vi | Exploration cap | `crux finding <qid> --exploratory` marks a finding on a question that came from looking at data with no stated prediction. That finding counts at most moderate. A descriptive measurement without the flag can still be strong. |
| vii | Progress review | At `/crux-wrap` only. No count threshold, no timer. |
| viii | Leanness | An acceptance criterion, measured in bytes and in schema items (below). |

## Design

### Rule 1 — Bears on (agent-enforced, engine-required at the CLI)

`## Bears on` is one or two sentences: which answer of the parent this item could change, and
in which direction. For a question under the project, the parent is the project's `## Goal`.

> Bears on: if pretraining matches today's accuracy at half the labels, the parent question
> (can we cut the label budget?) leans yes; if not, the budget question needs another route.

A side question that only unblocks another item says its exit in the same section: "done when
the encoder runs on the March split." No extra field.

The core skill gets one inline line: *a question or hypothesis is recorded only with how its
answer moves its parent's answer; when that cannot be said, it goes to the pending list.*

### Rule 2 — Read the path to the top question

`crux brief` (every mode) and `crux wrap --json` carry `path`: the titles and `## Bears on`
lines from the top question down to the item. `crux status --json` is unchanged, because the
agent reads it often and its size matters. The core skill tells the agent to read the path
before it opens an item or proposes a next step. The **crux-prerun** agent also states which
run outcome would move the parent, not only the hypothesis.

### Rule 3 — Park tangents

A question that a finding raises but that does not bear on its parent is not opened. It goes to
the pending list with `--text` that names it as a side question. Inline in the core skill
(one line) and in the **crux-capture** agent rules.

### Rule 4 — Exploration yields leads

A finding with `exploratory: true` in its frontmatter counts at most moderate in
`effective_confidence`, the same way the null cap counts at most weak. The cap is enforced on
write and applied again on read, so a hand edit cannot raise a node's state. Its only proper
yield is a sharper hypothesis or a ruled-out direction; the closure-judgment block in the core
gets one bullet.

### Rule 5 — Progress review at `/crux-wrap`

`crux wrap --json` adds `review`: each question that gained an item this session and has no
strong finding, with its `path`. The `crux-wrap` skill gets one step: for each such question
that the agent judges stalled (it now only explains old results and predicts nothing new),
ask the PI one `AskUserQuestion` with three options: **keep going**, **park this line**, or
**rewrite the parent** (a finding showed the parent asks the wrong question). The agent asks
only about lines it judges stalled. No line judged stalled → no question.

## Leanness budget

| Item | Budget |
|---|---|
| New node types, verbs, agents | 0 |
| New node sections | 1 (`## Bears on`) |
| New flags | 2 (`--bears` on ask/hypothesize, `--exploratory` on finding) |
| New finding frontmatter fields | 1 (`exploratory`) |
| Core `SKILL.md` growth | ≤ 600 bytes, and total ≤ 8,192 |
| `crux-wrap` skill growth | 1 step |
| `crux status --json` | unchanged |

## Acceptance

1. `./crux selftest` fully green, with new asserts written first for:
   1. `crux ask` and `crux hypothesize` refuse without `--bears`, and write `## Bears on` with it.
   2. The Python API without `bears` still writes an item (seed, autopilot, old tests).
   3. `validate` reports a missing `## Bears on` as info, never as an error.
   4. An exploratory strong finding counts as moderate; a strong finding without the flag
      still settles a question; the cap is enforced on write and on read.
   5. `crux brief` and `crux wrap --json` carry `path` from the top question down.
   6. `crux wrap --json` lists in `review` exactly the questions that gained an item this
      session and have no strong finding.
   7. `crux status --json` gains no key over 4.0 on the demo vault.
2. `wc -c skills/crux/SKILL.md` ≤ 8,192, and growth ≤ 600 bytes over `origin/main`.
3. Migration proof: the four example vaults and a copy of the CANDII vault load at 4.1 with
   no node's state or confidence moved (no old finding carries `exploratory`).
4. Stdlib only. The cockpit stays read-only.
5. Manual: in a scripted ideation conversation, a new hypothesis carries a `## Bears on` line
   that names the parent's answer; a tangent lands in the pending list, not the tree.

## Out of scope

A count threshold for review (decision vii). Rendering `## Bears on` specially in the cockpit.
Back-filling `## Bears on` into old items. MECE checks, hypothesis tournaments, registered
reports (rejected in the research).
