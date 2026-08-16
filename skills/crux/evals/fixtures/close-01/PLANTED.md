---
fixture: close-01
agent: crux-close
ground_truth: yes
oracle: verifiable_ticks
node: h1
verdict_read: invalid-run
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# close-01 — a run whose correct reading is known by construction

A `running` hypothesis with three pre-registered checks and a canned `results/h1/` directory
in which **every check's outcome is unambiguous in the data**: one number, in one file, bearing
on one check. The boxes are all unticked. `crux-close` reads the results and *proposes* the
ticks; it never writes them, because since spec 15 a tick decides `invalid-run` versus
`refuted`, so writing one would set both the verdict and its reason.

The ground truth is not an opinion about what the run showed. It is `derive_verdict_15` —
a pure function already in the engine — applied to the tick vector the data forces.

## Planted

| id | tier | class | what the data says |
|---|---|---|---|
| `h1:v1=x` | tick | claim-directed | `metrics.txt`: the gap is 0.0276 mIoU on average, over the 0.02 bar. Met. |
| `h1:v2=x` | tick | claim-directed | `metrics.txt`: the gap clears 0.02 on 5 of 5 seeds, over the "at least 4 of 5" bar. Met. |
| `h1:v3=u` | tick | outcome-neutral | `shuffled_labels.txt`: both arms score far above chance on **shuffled** labels. The control failed. |

Tick alphabet: `x` met · `u` unmet · `n` could not evaluate. A **wrong** tick is both a false
positive and a false negative, which is exactly what it is.

## The discrimination this fixture exists for

The claim-directed checks both passed and the control did not. Under the declared rule (`all`)
the engine reads run validity **first**, so the verdict is **`invalid-run`** — the run tells us
nothing — and it is **not** `refuted`, and it is **not** `supported` on the strength of two
green ticks.

Confusing those two sentences is the failure `crux-close`'s own definition names: *"'the run is
invalid and the claim learned nothing' is a different sentence from 'the claim was refuted', and
confusing the two is the failure the kinds exist to prevent."*

So the submission carries a `verdict_read` beside its ticks, and it is scored as a hard
pass/fail beside the band. **An agent that gets every tick right and calls this run `refuted`
fails this fixture.** That is the point of it.

## Reading the eval

Three ticks to recall, three to be precise about, and one word that decides whether the agent
understood any of it.

`band: unset`. The pass bar is the PI's.
