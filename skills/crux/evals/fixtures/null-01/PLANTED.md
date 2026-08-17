---
fixture: null-01
agent: crux-null
ground_truth: yes
oracle: null_vocabulary
node: h1
decoy: normalization
reference_null: capacity — the adapter arm is simply the larger encoder, 121M against 84M
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# null-01 — the boring explanation, planted in plain sight

`crux-null`'s job is one line: **if this result came out exactly as the claim predicts, what is
the most boring reason that could happen?** Not the most interesting rival theory — the
cheapest one, named as a family from the engine's closed vocabulary.

The fixture states the answer as a **fact in the shared record**, never as a concern: the two
arms are 84M and 121M parameters. Nobody calls that a confound anywhere in the vault. An agent
reading the brief has everything it needs and no prompt telling it what to conclude.

The node's own `## Null` is **empty** — the fixture must not contain the answer it is grading.

## Planted

| id | tier | class | what makes it the answer |
|---|---|---|---|
| `capacity` | family | closed-vocabulary | the arms differ by 37M parameters and nothing else; more parameters alone would move a 1.0-point bar |

## The decoy

`normalization` is planted as a **temptation**, and an agent that names it scores recall 0 —
which is what should happen. The vault mentions input normalisation by name (per-channel
z-scoring fitted on the training split), so it is superficially available; it is also
explicitly **shared across both arms**, so it cannot explain a difference between them.

The other four families are ruled out on the page, and the ruling-out is what makes `capacity`
the *cheapest* rather than merely *a* explanation:

| family | why it is not the answer here |
|---|---|
| `chance` | 10 seeds, 95% interval ±0.2 points, against a 1.0-point bar |
| `leakage` | the split was drawn before either arm was trained |
| `selection` | one fixed split, shared |
| `instrumentation` | the same evaluator scores both arms |

## Scoring

The family is genuine ground truth: it is one string from a six-item closed list the engine
already enforces, so recall and precision are exact.

Two things are reported **beside** the band rather than inside it, and the manifest says so
rather than dressing them up:

- **well-formedness** — one line, ≤ 25 words, a family named. `null_problem` decides it, and
  the reference null above is proof the fixture's own answer passes.
- **naming the instance, not the family alone** — *"capacity"* is useless; *"capacity — the
  adapter arm is simply the larger encoder"* is a null someone can test against. This is
  checkable only as a heuristic, so it never enters the band.

`band: unset`. The pass bar is the PI's.
