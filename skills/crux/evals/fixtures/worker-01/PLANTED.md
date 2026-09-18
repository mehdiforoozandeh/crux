---
fixture: worker-01
agent: crux-auto-worker
ground_truth: proxy
oracle: stated_key
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# worker-01 — one attempt, against a sibling that already failed for a written reason

A worker is handed one brief and writes one proposal. This fixture is that brief, plus the key
a correct proposal has to hit.

The island has **one refuted sibling whose failure scenario was written down before it ran**.
That single fact is what makes the fixture scoreable with no model and no vault: the sibling
failed because the learning rate was the thing that moved, so a new attempt that moves the
same parameter again is not a new attempt — it is the refuted one with a different seed. The
key is therefore about *which parameter the claim moves*, and about the shape of the proposal,
and about nothing else.

No vault is read. The oracle is `stated_key`, the brief is carried in this file, and the hard
half of the score is the engine validating the submitted proposal exactly as the driver would.

## Planted

| id | tier | class | what a correct proposal must carry |
|---|---|---|---|
| `moves-a-new-parameter` | requirement | filter | the claim moves a parameter the refuted sibling's written failure scenario does **not** name — the sibling died on the learning rate, so a claim about the learning rate is the refuted attempt again |
| `claim-names-the-reason` | requirement | filter | the claim says **why** the change would move the objective, not only that it did; a number with no mechanism beside it is unattributable in the next worker's brief |
| `claim-under-cap` | requirement | economy | the claim fits the 400-word prose cap; over-cap is refused and the attempt is retried, never truncated, so an over-cap claim costs the run a whole attempt |
| `control-is-a-comparison` | requirement | filter | at least one control, and each control is a metric comparison with its own `fails_if` scenario — a control that names no world in which it fails covers nothing |
| `no-claim-directed-check` | requirement | filter | no control asserts the claim itself; the claim-directed checks are frozen in the plan the PI signed, and a worker adding one is a worker setting its own bar |

## The brief

The brief the agent was given, in the shape the engine assembles it. It is reproduced here so
the fixture is self-contained: nothing outside this file is read.

```
# Attempt brief — h4  (auto/q1/plan.md)

## Goal
Raise held-out accuracy on the small-molecule panel without growing the model.

## Objective
address: obj.score · direction: max · bar: 0.84

## Island
q1.2 — Does the optimiser schedule explain the gap, or the readout?

## Closed under this island
- h2 — best obj.score 0.812 — supported
- h3 — best obj.score 0.771 — refuted

## Refuted siblings, with the scenario each was written against
- h3 — "raising the learning rate closes the gap"
  fails_if: the gap is unchanged when only the learning rate moves, which is what happened
  (obj.score 0.771 against the 0.812 baseline, three seeds, all three worse)

## Guidance
- [2026-09-14] PI: report the seed count with every score.

## Steward guidance
No steward guidance yet.

## Output
One commit, and one JSON object at CRUX_PROPOSAL with keys claim, controls.
```

## What this proxy does **not** measure

Whether the claim is any **good** — only that it moves the parameter the sibling's failure
scenario names, and that the proposal validates.

Every planted row is structural or is one bit read off the brief. A proposal that moves a new
parameter, explains a mechanism that is wrong, and carries a well-formed control scores 1.0
here. Whether the change it proposes would actually reach 0.84 is answerable only by running
it, which is the part this harness does not do and does not pretend to do.

## Reading the eval

Five rows, four of them shape and one of them the single fact in the brief that matters. The
hard half sits beside the band: `auto_proposal` validates the submitted object exactly as the
driver would, so a proposal that scores five green rows and still fails the schema fails the
fixture.

`band: unset`. The pass bar is the PI's.
