# Crux

**An agentic research companion** — a scientific-method lab notebook your LLM agent drives.

> *Crux* (the Southern Cross) is the sky's smallest constellation and its most reliable signpost — for centuries it's how navigators found their bearings. `crux` does the same for a research program: it keeps you oriented through a growing tree of open questions and the hypotheses that resolve them, and helps you get to the **crux** of each one.

## What it is

`crux` organizes a research program the way the scientific method actually works:

- **Questions** — what you don't know. They carry no answer of their own; they're resolved by aggregating the findings beneath them. Questions nest.
- **Hypotheses** — falsifiable, testable leaves under a question, each with **pre-registered verifiables** and **findings**. The only things actually tested.
- A deterministic **engine** does the bookkeeping — IDs, the parent tree, validators, the evidence-ledger roll-up, a human **review gate**, and regenerating a navigable `META.md` map + `EXPERIMENTS.md` registry.
- An **LLM agent** drives it conversationally; **you (the PI)** make the judgment calls — which questions matter, the verifiable bar, and when a question is truly answered.

Everything is plain markdown in an **Obsidian-graphable vault**: open it and the question/hypothesis tree *is* the graph.

## Install

As an agent skill (Claude Code and other [skills.sh](https://www.skills.sh)-compatible agents):

```bash
npx skills add mehdiforoozandeh/crux
```

Or clone and use the engine directly (Python 3, stdlib only — no dependencies):

```bash
git clone https://github.com/mehdiforoozandeh/crux
python crux/scaffold/crux.py --help
```

## A minute with crux

```bash
crux init "My project"
crux ask "Can X improve Y?"                          # open a question (alias: question, q, meta)
crux hypothesize "A beats B" -p q1 \
     -v "metric ≥ +0.01 vs baseline"                 # a falsifiable leaf (alias: idea)
crux launch h1 --run "job 4012"                      # idea → running (alias: run, test, stage)
# …tick the verifiables in h1_*.md, then:
crux close h1 -m "metric +0.012"                     # verdict derived; rolled up the tree
crux review                                          # questions awaiting your decision
crux answer q1 -t "A is the load-bearing change."    # resolve it
crux status                                          # the live tree
```

The verdict is **mechanical**: `crux close` reads the verifiable checkboxes (`[x]` met · `[ ]` unmet · `[-]` n/a) and derives `supported` / `partial` / `refuted` / `inconclusive`. The engine never reads your run logs — you supply the per-box judgement and a headline metric. That keeps it domain-agnostic.

## How it's built

- `SKILL.md` — the PI ⇄ Agent ⇄ Engine playbook the LLM follows.
- `scaffold/` — the engine: `crux.py` (CLI), `engine.py`, `render.py`, `templates/`, `selftest.py`. See [`scaffold/README.md`](scaffold/README.md) for the full CLI reference.

Validate the install end-to-end (no GPU/tokens/SLURM):

```bash
python scaffold/selftest.py            # builds a dummy vault, asserts every invariant
python scaffold/selftest.py --keep ./v # …and keep it to open in Obsidian
```

## Roadmap

`crux` is the home for a small constellation of agentic-research tools. Planned siblings under the same roof: **era** (whole-program search toward a score) and **autoresearch** (autonomous experiment loops), with a GUI later.

## License

[MIT](LICENSE) © Mehdi Foroozandeh
