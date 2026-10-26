---
name: crux-autopilot
description: >-
  Set up a crux autopilot plan with the PI and write it to `auto/<qid>/plan.md`: the anchor
  question, the program repo and the paths the worker may edit, the frozen scorer, the
  objective with its direction and bar, and the PI's own guidance. Checks the scorer contract,
  runs `crux auto check` (which scores the baseline), then stops and hands the PI the exact
  `crux auto run` line. Never starts the run. Use when a crux user wants to start an
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
`editable` (comma-separated; a trailing `/` is a directory), `scorer` and `objective`
(`<address> <min|max> <bar>`) are required. The rest default to the values shown; `mode` is
`climb` or `explore`, and `worker` is `<model> <low|medium|high|xhigh|max>`. Put no comment
after a value: it becomes part of the value.

## The steps

1. **The anchor.** Find the question this run serves. If it does not exist, propose it; `ask`
   needs the PI's yes, as everywhere in crux.
2. **The harness, in one turn.** Ask for the repo, the base, the editable paths and the scorer
   command. Everything not in `editable` is frozen; a change outside it discards the attempt.
3. **The scorer contract.** Run the scorer once on the base yourself and read its output. It
   must print **one JSON object**, and the objective address must reach a `{"value": n}` leaf.
   A wrong candidate must make it **exit non-zero and print `"passed": false`** with a reason.
   Correctness tests, anti-cheat checks and repeats against noise belong **inside the
   scorer**: the driver checks none of them. The scorer runs in the candidate's worktree, with
   `CRUX_WORKSPACE` set to a scratch directory. If the scorer misses any of this, say what is
   missing and fix it with the PI before you go on.
4. **The objective: address, direction, bar.** Read the address off the scorer's output.
   **Ask the direction; never infer it.** A metric named `loss` is usually minimised, and
   "usually" is how a backwards bar gets written; one short question is cheaper than a wasted
   run. Then ask the bar.
5. **The defaults, in one line.** State `mode`, `budget_hours`, `attempt_minutes` and
   `worker` with their values, and change one only if the PI asks. `explore` suits many
   different routes; `climb` suits one line of improvement. `attempt_minutes` covers the
   worker and the scorer, and the worker loses one and a half scorer runs of it, so measure
   the scorer's time in step 3.
6. **The guidance.** Ask one open question for the PI's priors: the analogy they see, the
   routes they rate and in what order, the dead ends they already know, the invariant to keep.
   Do not turn it into a questionnaire. "I don't know" leaves it empty, and the run proceeds.
7. **Write the plan, then run `crux auto check <plan>`.** It scores the base, scores again with
   the first editable file emptied (the score must change), and runs the worker once (one model
   call) to prove it can commit. Fix what it reports and run it again. `--static` reads the
   plan alone and starts nothing.
8. **Stop.** Give the PI the plan's path, the baseline the check printed, and the exact line:
   `crux auto run auto/<qid>/plan.md`. On Fir, a benchmark starts with
   `bash examples/autopilot/run-fir.sh <bench>`.

**Never start `crux auto run` yourself.** The PI's start is the signature on the bar, and the
run spends compute unattended. Start it only when the PI tells you to, in so many words. Read a
run in progress with `crux auto status`.

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
