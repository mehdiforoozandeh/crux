---
name: crux-autopilot
description: >-
  Set up a crux flight plan with the PI, in five acts, and write it to
  `auto/<qid>/plan.md` — the anchor question and a falsifiable goal, the null (approved by
  the PI, proposed by `crux-null`), the pre-registered checks and their control (written by
  `crux-verifiables` against that approved null), the objective address read off the
  discriminating check, the direction and the bar, and the harness in one turn. Scores the
  baseline with `crux auto check` rather than asking for it, defaults every remaining slot
  from the template, spawns `crux-design` for a verdict, then stops and hands the PI the
  path and the exact `crux auto approve` line. Adds no crux verb; never approves, never
  runs. Use when a crux user wants to start an autopilot search. Triggers: "set up a
  flight plan", "I want to search this", "start the autopilot", "write me an auto plan",
  "configure crux auto", crux autopilot, crux auto setup, flight plan.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  requires: "the crux skill, installed as a sibling of this one (drives its engine at <crux skill>/scaffold/)"
  notice: "Playbook only — drives the bundled crux engine's existing `auto` verbs; no engine changes, no new verb, no third-party code."
---

# crux-autopilot — write the flight plan, then stop

A flight plan carries twenty slots plus a baseline, and `crux auto run` refuses a plan short
of any of them. This skill gets the PI from "I want to search this" to a plan that passes
`crux auto check`. It asks for three of those slots. Everything else is derived from an
answer already given, measured by a command, or taken from the template and stated back in
one line.

## The five acts — three asks, two approvals

| # | the skill's turn | why it cannot be skipped |
|---|---|---|
| 1 | **ask** — the anchor question, and the goal in one falsifiable sentence | the frame is the PI's; nothing can derive it |
| 2 | **approve** — the null, proposed by `crux-null` | a ruling, not a value; spec 05 requires the PI's yes |
| — | *derived* — the checks, their kinds, the combination rule, the control | `crux-verifiables`, against the approved null |
| — | *derived* — the objective address | **read off** the discriminating check just written |
| 3 | **ask** — which direction is better, and the bar | direction is the one thing that must never be guessed |
| 4 | **ask** — the harness, in one turn: scorer command, run command, frozen paths, writable paths, budget ceiling | only the PI knows their repo |
| — | *measured* — the baseline | `crux auto check` dry-runs the scorer and prints it |
| — | *defaulted* — the remaining fourteen slots | template defaults, stated back, not asked |
| 5 | **approve** — `crux-design`'s verdict, then the PI's own `crux auto approve` | the PI's signature |

## The ordering that is load-bearing

**The objective address is read off a check, never chosen: the bar-and-direction turn comes
after `crux-verifiables` has written the checks, so the address comes out of a check that
already exists and the engine's `discriminates` lint passes as a consequence rather than as
a hurdle.** A PI who picks the number first and writes a check around it afterwards produces
a plan that passes every lint and is exactly the failure the spec forbids: the search clears
a bar the hypothesis was always going to clear, thousands of times, at cost, and teaches
nothing.

**Direction is asked, never inferred.** A metric named `loss` is *usually* minimised and a
metric named `score` *usually* maximised — and "usually" is how 05.2's reverted hard-coded
`<=` got written. One short question costs a turn; a backwards bar costs the whole run. Once
the direction is given, the discriminating check's operator is derived from it, never typed
from habit.

## The five voice rules

1. **One question per turn.** Never a questionnaire, never a numbered list of choices.
2. **Never ask what a command can measure.** The baseline is scored, never asked for.
3. **Never ask what the template defaults.** State the default in passing; discuss it only
   if the PI raises it.
4. **Never ask the PI to choose between options that differ only in something the search
   itself would discover.** That is what the autopilot is for — a choice the bandit can make
   in ten attempts must not cost a turn of the PI's attention.
5. **"I don't know" takes the default.** Record which slot was defaulted that way and move
   on; never escalate, re-ask, or explain the option space.

The skill never opens a turn by summarising the previous one, and never closes one by
listing what remains. Those two habits are what make a five-slot conversation read as twenty.

## The fourteen defaulted slots, in one line

Defaulted from the template and stated back once, not asked: `mode`, `islands`, `island_cap`, `parallel_total`, `parallel_island`, `retries`, `retention`, `replicates`, `rule`, `steward`/`steward_every`, `stall_attempts`, `abort_invalid_runs`, `scorer_timeout`, and the agent block (`agent`, `agent_failover`, `agent_cooldown`, `agent_probe`, `agent_probe_timeout`).

## The baseline is scored, not asserted

`crux auto check` dry-runs the scorer. Record the number it printed as `baseline:` and state
it back to the PI. Never ask the PI for a baseline they would be quoting from memory.
Terminal hypotheses already under the anchor are adopted as further starting observations.

## Writing is not approving

1. Write `auto/<qid>/plan.md` from `templates/flight_plan.md`.
2. Run `crux auto check` and fix what it reports.
3. Spawn `crux-design`.
4. Stop. Hand the PI the path, plus the exact `crux auto approve` line to run.

The skill **never** runs `crux auto approve` itself — that verb is the PI's signature, and it
stops here. Writing the file costs the PI nothing: `flight_plan_hash` means the approval
stamp covers a hash of the document, so an unapproved plan is inert and `crux auto run`
refuses it. The skill also **never** runs `crux auto guide` on its own initiative —
`## Guidance` is the PI's own words, append-only.

This skill adds no new `crux` verb. It drives the verbs that already exist.

## When `crux-design` rejects

| cause | who owns it | what the skill does |
|---|---|---|
| a compound claim | act 1 | reopen act 1; the goal is re-split, and acts 2–4 are redone against the new frame |
| a check that does not follow from the claim | act 3 | reopen act 3; `crux-verifiables` runs again against the same approved null |
| the run cannot discriminate | `crux-design` itself | take its own fix, then re-run `crux auto check` |

The skill never proceeds past a rejection on its own, and it never edits `crux-design`'s
verdict. Only the PI may say "go anyway". If they do, the skill records their sentence
verbatim in `## Guidance` via `crux auto guide` — their words, on their yes — so the run's
transcript carries why.
