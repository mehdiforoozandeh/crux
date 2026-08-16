---
fixture: migrate-01
agent: crux-migrate
ground_truth: proxy
oracle: stated_key
verify: evidence_resolves
node_band: 4, 8
checks: tree, wiki, economy, fanout, rd, tasks
band: unset
k: 5
---

# migrate-01 — reconstruct finished work as a seed

There is no vault here. `vault/repo/` is an **unorganized research repo** — a README, three
notes and two result files — and the deliverable is a seed file a human approves before
anything is written.

Two pieces of work were actually run and one was only written down. The distinction is the
eval: a proposed hypothesis is a plain hypothesis, not a tested one with empty boxes.

## Planted

| id | tier | class | the evidence it must rest on |
|---|---|---|---|
| `q:vocabulary` | node | question | `repo/notes/vocab.md` asks whether 64k beats 32k for the 120M model |
| `h:vocab-64k[tested]` | node | tested | ran, and cleared its stated bar: 18.9 → 18.2, a 0.7 improvement against a pre-agreed 0.4, in `repo/results/vocab.csv` |
| `h:latency[tested]` | node | tested | ran, and **missed** its bar: median decode latency rose 11% against a 5% ceiling, in `repo/results/latency.csv`. The unticked box is the finding. |
| `h:morphology` | node | untested | `repo/notes/morphology.md` says it in as many words: no runs, no numbers, nobody started. A plain hypothesis, never `[tested]` with empty boxes. |

`node_band: 4, 8` — the reconstruction is scored on landing inside a band, not on an exact
count, because how finely a repo decomposes into questions is a judgment call.

## What this proxy does **not** measure

**Fidelity.** Whether the reconstruction says what the original researcher meant is
unmeasurable without that researcher, and this repo is synthetic, so there is no one to ask.
What is checkable is what the spec's own table claims: the seed parses, the node count lands in
a band, and every `[x]` tick carries an evidence pointer that resolves.

Certification checks the pointers resolve. It cannot check that a tick is *warranted* by what
the file says — that reading is the judgment being graded.
