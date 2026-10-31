---
name: crux-autopilot
description: >-
  Set up a crux autopilot plan with the PI and write it to `auto/<qid>/plan.md`: the anchor
  question, the program repo and the paths the worker may edit, the frozen scorer, the
  objective with its direction and threshold, and the PI's own guidance. Checks the scorer
  contract, runs `crux auto check` (which scores the baseline), then stops and hands the PI the
  exact `crux auto run` line. Never starts the run. Use when a crux user wants to start an
  autopilot search. Triggers: "set up an autopilot run", "I want to search this", "start the
  autopilot", "write me an auto plan", "configure crux auto", crux autopilot, crux auto setup.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "2.0"
  requires: "the crux skill, installed as a sibling of this one (drives its engine at <crux skill>/scaffold/)"
  notice: "Playbook only — drives the bundled crux engine's existing `auto` verbs; no engine changes, no new verb, no third-party code."
---

# crux-autopilot — write the plan, check it, then stop

The plan is one file, `auto/<qid>/plan.md`: a `---` frontmatter of `key: value` lines, then
free text that is the PI's guidance. The engine refuses any other field and lists every
problem at once. Worked examples: the benchmark directories under `examples/autopilot/`
(`circle-packing/`, `m4-weekly/`, `memesuite-lite/`, `nanogpt-shakespeare/`), each with its
own `plan.md` and `README.md`.

```
---
anchor: q3
repo: ../program
base: HEAD
editable: src/model.py, configs/
scorer: python3 score.py
objective: val_loss min 1.36
mode: climb
budget_hours: 8
attempt_minutes: 20
worker: opus high
---
The PI's guidance, in their words.
```

`anchor`, `repo` (absolute, or relative to the vault root), `base` (a commit or ref),
`editable` (comma-separated; a trailing `/` is a directory), `scorer` and `objective` are
required. `objective` is `<address> <min|max> <bar>`: the score's address, its direction, and
the threshold (the plan's `bar` field). The rest default to the values shown; `mode` is
`climb` or `explore`, and `worker` is `<model> <low|medium|high|xhigh|max>`. The optional
`min_gain` (a number >= 0, in the objective's units) sets how much an attempt must beat its
parent, and climb's best, to count as better. Leave it out unless the PI has a reason: `crux
auto check` measures the scorer's noise (below), and with a deterministic scorer the default
is near zero, so any real gain counts. Put no comment after a value: it becomes part of the
value.

## The steps

1. **The anchor.** Find the question this run serves. If it does not exist, open it
   (`crux ask`), silently, as the crux core does for any question the conversation asks.
2. **The harness, in one turn.** Ask for the repo, the base, the editable paths and the scorer
   command. Everything not in `editable` is frozen; a change outside it discards the attempt.
3. **The scorer contract.** Run the scorer once on the base yourself and read its output. It
   must print **one JSON object**, and the objective address must reach a `{"value": n}` leaf.
   A wrong candidate must make it **exit non-zero and print `"passed": false`** with a reason.
   Correctness tests, anti-cheat checks and repeats against noise belong **inside the
   scorer**: the driver checks none of them. The scorer runs in the candidate's worktree, with
   `CRUX_WORKSPACE` set to a scratch directory. If the scorer misses any of this, say what is
   missing and fix it with the PI before you go on.
4. **The objective: address, direction, threshold.** Read the address off the scorer's output.
   **Ask the direction; never infer it.** A metric named `loss` is usually minimised, and
   "usually" is how a backwards threshold gets written; one short question is cheaper than a
   wasted run. Then ask the threshold.
5. **The defaults, in one line.** State `mode`, `budget_hours`, `attempt_minutes` and
   `worker` with their values, and change one only if the PI asks. `explore` suits many
   different routes; `climb` suits one line of improvement. `attempt_minutes` covers the
   worker and the scorer, and the worker loses one and a half scorer runs of it, so measure
   the scorer's time in step 3.
6. **The guidance.** Ask one open question for the PI's priors: the analogy they see, the
   routes they rate and in what order, the dead ends they already know, the invariant to keep.
   Do not turn it into a questionnaire. "I don't know" leaves it empty, and the run proceeds.
7. **Write the plan, then run `crux auto check <plan>`.** It scores the base **3 times** (the
   baseline is the median, and the spread is recorded as the scorer's **noise**), scores again
   with the first editable file emptied (the score must change), and runs the worker once (one
   model call) to prove it can commit. Fix what it reports and run it again. `--static` reads
   the plan alone and starts nothing.
8. **Stop.** Give the PI the plan's path, the baseline and the noise the check printed, and
   the exact line:
   `crux auto run auto/<qid>/plan.md`. On Fir, a benchmark starts with
   `bash examples/autopilot/run-fir.sh <bench>`.

**Never start `crux auto run` yourself.** Starting it is the PI's: the run spends compute
unattended, against a threshold the PI fixed. Start it only when the PI tells you to, in so
many words. Merging an attempt into `main` is also the PI's.

## How a run reads back

Each attempt becomes one hypothesis under the anchor with one finding, computed from the
score with no model call. This is the one place crux computes a confidence instead of judging
it:
- **Direction.** A kept attempt that beats its parent by more than `min_gain`: supports.
  A kept attempt that does not: against. A rejected, failed or discarded attempt: no answer
  yet, weak, with the worker log as evidence.
- **Confidence, symmetric.** Strong when the score lands past the bar, in either direction,
  by more than the noise (or `min_gain` when the noise is 0); else moderate. A run recorded
  before noise was measured caps every finding at moderate.

Read a run with `crux auto status [<qid>] --json`: `anchor`, `mode`, `address`, `direction`,
`bar`, `baseline`, `noise`, `best`, and `attempts` (each with `n`, `id`, `parent`, `score`,
`status`, `finding`, `direction`, `confidence`), plus `elapsed_hours`, `budget_hours`, `live`
and `stop`. The findings settle or lean the anchor like any others; there is nothing to close.
Report a run to the PI in science: what improved, by how much against the noise, and how sure
that makes us.

## Whose words go in the guidance

The guidance is **the PI's**. Never write it for them on your own initiative. If they say
"write it yourself", you hold the pen, not the authorship: keep every claim they made and add
none of your own. Harness facts a worker needs (what the scorer measures, how long it takes)
you may add, marked as yours on their own line.

## The voice rules

1. **One question per turn.** Never a questionnaire, never a numbered list of choices.
2. **Never ask what a command can measure.** The baseline and the scorer's time are run, never
   asked for.
3. **Never ask what has a default.** State it in passing.
4. **A question back is not an answer.** If the PI asks what a field means, answer plainly in
   their words, then ask the same question again.
5. **Bring the ruling that cannot be undone.** Which data the scorer reads and which protocol is
   scored cannot move once a score is seen. Put those to the PI before the first attempt, with a
   recommendation.
