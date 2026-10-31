---
fixture: capture-01
agent: crux-capture
ground_truth: yes
oracle: capture_yield
transcript: transcript.txt
evidence: results/light-trial/heights.csv
work_markers: timer, seed trays
checks: tree
band: unset
k: 5
---

# capture-01 — one short conversation, and what it must leave in the record

`crux-capture` reads a slice of conversation and records the science silently. This fixture
is that slice (`transcript.txt`), the record before it was captured (`vault/`), and the
record a correct capture leaves (`reference/`). The reference was written with the ordinary
crux verbs, so every derived field in it is the engine's own.

**Hand-authored.** Nothing here was produced by `crux-capture` or by anything sharing its
prompt lineage. The topic is seedlings under a grow lamp, so no field knowledge is needed to
check it.

## What the conversation holds

- **Ideation.** The PI asks whether light hours change seedling growth, and guesses that 16
  hours beats 12 by about 20%. A question and a hypothesis with that expectation.
- **A result with evidence.** The PI names `results/light-trial/heights.csv`: about 15%
  taller. Same direction, short of the expected size: a near miss.
- **A null that is not ruled out.** The 16-hour trays sat on the warmer shelf. Warmth alone
  could explain the gain, so the supports finding is capped at weak.
- **A dropped node.** The PI sets the watering hypothesis aside at the start. It is parked.
- **A duplicate trap.** The PI re-asks the watering question. It already exists, so a
  correct capture opens nothing for it.
- **A work trap.** Fixing the lamp timer and ordering seed trays are tasks. They are work,
  not knowledge, so no node is opened for them.

## Planted

The ids are yield keys from `evals.capture_keys(vault, after)`, a pure function of the
record before and after the run. Certification computes them over `reference/` and requires
the set below exactly.

| id | tier | class | what a correct capture does |
|---|---|---|---|
| `open:question` | node | ideation | opens the light-hours question |
| `open:hypothesis+expect` | node | ideation | opens "16 hours beats 12" with its expectation stated |
| `finding:evidence` | finding | evidence | records the result, linked to the heights file |
| `finding:weak` | finding | closure | judges it weak: a near miss, and the null not ruled out |
| `finding:null-open` | finding | closure | records that the warmer shelf was not ruled out |
| `parked:h1` | node | park | parks the watering hypothesis the PI dropped |

A careless capture shows up as an id outside this set: `duplicate:q1` (a second watering
question), `work-in-tree` (a node for the timer or the trays), `finding:moderate` or
`finding:strong` (the null cap ignored), `finding:no-evidence`, `open:hypothesis-bare`, or
`parked:<id>` for a node the conversation kept.

## Hard checks

Beside the band, one bit each: the run asked the PI nothing (`asked_pi` is empty), and the
prose it wrote carries no node id and no crux vocabulary (`prose`, scanned by
`engine.voice_lint`). Produce a run's entry with
`python evals.py --fixture capture-01 --yield <the record after the run>`.

`band: unset`. The pass bar is the PI's.
