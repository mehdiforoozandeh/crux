---
name: crux-autopilot
description: >-
  Set up a crux flight plan with the PI, in six acts, and write it to
  `auto/<qid>/plan.md` — the anchor question and a falsifiable goal, the null (approved by
  the PI, proposed by `crux-null`), the pre-registered checks and their control (written by
  `crux-verifiables` against that approved null), the objective address read off the
  discriminating check, the direction and the bar, the harness in one turn, and the PI's own
  standing guidance — the expert priors, analogies and dead ends that no derivation can
  produce. Scores the baseline by running the scorer rather than asking for it, searches the
  literature for rivals so the bar is set against what has actually been achieved on this
  data, defaults every remaining slot, spawns `crux-design` for a verdict, then stops and
  hands the PI the path and the exact `crux auto approve` line. Adds no crux verb; never
  approves, never runs. Use when a crux user wants to start an autopilot search. Triggers: "set up a
  flight plan", "I want to search this", "start the autopilot", "write me an auto plan",
  "configure crux auto", crux autopilot, crux auto setup, flight plan.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.1"
  requires: "the crux skill, installed as a sibling of this one (drives its engine at <crux skill>/scaffold/)"
  notice: "Playbook only — drives the bundled crux engine's existing `auto` verbs; no engine changes, no new verb, no third-party code."
---

# crux-autopilot — write the flight plan, then stop

A flight plan carries twenty slots plus a baseline, and `crux auto run` refuses a plan short
of any of them. This skill gets the PI from "I want to search this" to a plan that passes
`crux auto check`. It asks for four of those slots. Everything else is derived from an
answer already given, measured by a command, or defaulted and stated back in one line.

## The six acts — four asks, two approvals

| # | the skill's turn | why it cannot be skipped |
|---|---|---|
| 1 | **ask** — the anchor question, and the goal in one falsifiable sentence | the frame is the PI's; nothing can derive it |
| 2 | **approve** — the null, proposed by `crux-null` | a ruling, not a value; spec 05 requires the PI's yes |
| — | *derived* — the checks, their kinds, the combination rule, the control | `crux-verifiables`, against the approved null |
| — | *derived* — the objective address | **read off** the discriminating check just written |
| 3 | **ask** — which direction is better, and the bar | direction is the one thing that must never be guessed |
| 4 | **ask** — the harness, in one turn: scorer command, run command, frozen paths, writable paths, budget ceiling | only the PI knows their repo |
| 5 | **ask** — the PI's standing guidance: their priors, the analogies they see, the routes they rate, the dead ends | the one input the search cannot find for itself |
| — | *measured* — the baseline, and the published rivals | the scorer is run; the literature is searched |
| — | *defaulted* — the remaining slots | stated back in one line, not asked |
| 6 | **approve** — `crux-design`'s verdict, then the PI's own `crux auto approve` | the PI's signature |

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

## Act 5 — ask for the PI's guidance, and mean it

The bar, the checks and the null are all derived or ruled on. **The PI's own priors are not
derivable from anything, and they are the highest-value thing in the whole conversation.**
A search that starts from a blank program wastes attempts rediscovering what the PI already
knows; a search that starts from their framing spends those attempts on the part nobody
knows. Ask for it in one open turn, and name the kinds of answer that help:

- **The analogy.** What adjacent field has this same shape? One PI recognised a held-out-cohort
  classifier as a batch-effect removal problem from single-cell work, and later recognised the
  confound itself as dropout — which turned "the model reads sequencing depth" into a concrete
  route, matrix factorisation over entries that are missing rather than zero. No derivation
  produces that.
- **The routes they rate**, in the order they would try them.
- **The model families, and the order.** Simple first is a prior worth recording, not an
  obvious default.
- **What they already believe is a dead end**, so the search does not pay to find out.
- **The invariant they want preserved** — the thing that should hold across every split, which
  is often the real scientific claim under the metric.

**Do not turn this into a questionnaire.** One open question, then take what comes. "I don't
know" takes an empty `## Guidance` and the run proceeds; it is a loss, not a blocker.

### Whose words go in

`## Guidance` is append-only, through `crux auto guide`, and it is **the PI's**. Three rules:

1. **Never write it for them on your own initiative.**
2. **They may delegate the phrasing.** A PI who says "write it yourself, improve my words"
   has given you the pen, not the authorship. Record it under their name, keep every claim
   they made, and add none of your own.
3. **Your own entries are stamped as yours.** The harness facts a worker needs — the per-call
   compute budget, what the frames look like, which control catches what — are yours to add
   under your own author name, never the PI's. When one of your earlier entries turns out to
   be wrong on a fact, append a correction rather than editing: the log is append-only, and a
   silently fixed error is the one a worker will still be acting on.

## Rivals — search the literature before the bar is set

Ask whether a published rival exists on **this** data under **this** protocol, and go and look.
This is a measurement, not a question for the PI, and it routinely moves the frame.

What makes a rival usable is strict, and you must report which conditions you verified: the
same target, a whole held-out group rather than cross-validation, the same feature type, and a
cohort set that overlaps. A headline number measured on a cleaner subset of cohorts is not a
rival; say so rather than quietly adopting it.

Worked example of why it matters. The published headline for one task was 0.79–0.84, measured
on six deeply sequenced cohorts. The only result confirmed on the PI's actual eleven cohorts,
under the same protocol and using abundance alone, was **0.76**. Setting the bar against the
headline would have declared a real result a failure.

## The voice rules

1. **One question per turn.** Never a questionnaire, never a numbered list of choices.
2. **Never ask what a command can measure.** The baseline is scored, never asked for.
3. **Never ask what the template defaults.** State the default in passing; discuss it only
   if the PI raises it.
4. **Never ask the PI to choose between options that differ only in something the search
   itself would discover.** That is what the autopilot is for — a choice the bandit can make
   in ten attempts must not cost a turn of the PI's attention.
5. **"I don't know" takes the default.** Record which slot was defaulted that way and move
   on; never escalate, re-ask, or explain the option space.
6. **A question back is not an answer.** The PI may stop mid-act and ask what a slot means —
   "what is the null?", "what is richness?". Answer it plainly, in their vocabulary, then put
   the same question again. Never read the question as the ruling, and never read their
   restating your proposal in their own words as a rejection of it: when they say the thing
   back correctly, that is the approval.
7. **Bring the number that cannot be un-decided.** Some rulings cannot be revisited once a
   score is seen — which samples are scored, which protocol is the scored one, where a
   confound threshold sits. Put those to the PI **before** the first attempt, with the trade
   stated in full and a recommendation, and say plainly that moving it afterwards is what the
   whole design exists to prevent.

The skill never opens a turn by summarising the previous one, and never closes one by
listing what remains. Those two habits are what make a five-slot conversation read as twenty.

## The defaulted slots, in one line

Defaulted and stated back once, not asked: `mode`, `islands`, `island_cap`, `parallel_total`, `parallel_island`, `retries`, `retention`, `replicates`, `rule`, `steward`/`steward_every`, `stall_attempts`, `abort_invalid_runs`, `scorer_timeout`, and the agent block (`agent`, `agent_failover`, `agent_cooldown`, `agent_probe`, `agent_probe_timeout`).

## The baseline is scored, not asserted

`baseline:` names a hypothesis node under the anchor that carries `results/<hid>/metrics.json`,
and the objective address must resolve inside that file — so the baseline is a node you create
and score, not a number the PI recites. Write the starting program, run the frozen scorer on
it, save its JSON as that node's metrics, and link it under `## Artifacts`. `crux auto check`
then re-runs the scorer and prints the objective back. Never ask the PI for a baseline they
would be quoting from memory. Terminal hypotheses already under the anchor are adopted as
further starting observations.

**Score the baseline at several seeds, not one.** Every threshold in every check is a claim
about what is outside the noise, and one run cannot tell you where the noise is. Four runs is
usually enough. Put the measured range in the check's own line, in brackets, so a reader can
see what the floor was set against — and so a later reviewer can catch a floor set inside the
spread. One control in a real plan was set from a published band and would have voided three
of four baseline runs; four measured seeds is what caught it.

**Then score one obvious strong program too.** Not to register it — to find out what the
search is really for. If an off-the-shelf model already clears the bar, the interesting
question is not the gap to the literature but which check that model fails, and the guidance
should say so before attempt 1 rather than after attempt 6.

## Writing is not approving

1. Write `auto/<qid>/plan.md`.
2. Run `crux auto check` and fix what it reports.
3. Spawn `crux-design`.
4. Stop. Hand the PI the path, plus the exact `crux auto approve` line to run.

Two things `crux auto check` will refuse that are easy to write by accident: `## Null` must be
**one** non-blank line within the word cap, so the evidence for the null goes under `## Goal`,
not under `## Null`; and unless `closer: true`, every check must **begin** with a metric
comparison — `<dotted.key> <op> <number>` — so a prose check has to become a number the scorer
emits.

The skill **never** runs `crux auto approve` itself — that verb is the PI's signature, and it
stops here. A PI saying "approved" in conversation is not the signature: check the file for
`approved:` and `approved_hash:` before telling anyone the plan is signed. Writing the file costs the PI nothing: `flight_plan_hash` means the approval
stamp covers a hash of the document, so an unapproved plan is inert and `crux auto run`
refuses it. On `crux auto guide`, see "Whose words go in" above: the PI's entries are theirs and are never
written on your own initiative, while harness facts and corrections are yours and are stamped
under your own author name.

This skill adds no new `crux` verb. It drives the verbs that already exist.

## When `crux-design` rejects

| cause | who owns it | what the skill does |
|---|---|---|
| a compound claim | act 1 | reopen act 1; the goal is re-split, and acts 2–4 are redone against the new frame |
| a check that does not follow from the claim | act 3 | reopen act 3; `crux-verifiables` runs again against the same approved null |
| the run cannot discriminate | `crux-design` itself | take its own fix, then re-run `crux auto check` |

**Expect more than one rejection, and budget for it.** A rejection for "the run cannot
discriminate" is the skill's own to fix, and the fix often changes the scorer — which means
re-scoring the baseline at every seed and going back for another verdict. Two rounds is
ordinary. Verify the reviewer's central claims yourself before acting on them, and say so when
one does not hold: in one run the reviewer read a wall-clock figure measured under four-way
CPU contention and drew a budget conclusion from it that the solo timings did not support.

The skill never proceeds past a rejection on its own, and it never edits `crux-design`'s
verdict. Only the PI may say "go anyway". If they do, the skill records their sentence
verbatim in `## Guidance` via `crux auto guide` — their words, on their yes — so the run's
transcript carries why.
