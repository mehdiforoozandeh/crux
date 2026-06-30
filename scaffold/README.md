# crux engine — CLI reference

A self-contained Python 3 (stdlib-only) CLI that maintains a **crux vault**: a
scientific-method lab notebook of markdown nodes you can open as an Obsidian vault.
The agent drives it by default; it's equally usable by hand.

```bash
python crux.py --help          # full tour
python crux.py <verb> --help   # per-verb help
python selftest.py               # build a dummy vault and assert every invariant (no deps)
python selftest.py --keep ./demo # …and keep it so you can open ./demo in Obsidian
```

## The model

- **Project** — the root node (one per vault).
- **Question** (`q*`) — what you don't know. No verifiables of its own; **resolved by aggregating its children**. Nestable.
- **Hypothesis** (`h*`) — a falsifiable, testable leaf under a question. Has `## Verifiables` + `## Findings` + a verdict.

The tree lives in each node's `Parent:: [[…]]` wikilink (so the Obsidian graph draws it). `META.md` and `EXPERIMENTS.md` are **generated** — never hand-edit them.

## Verbs (canonical · aliases)

| verb | aliases | what it does |
|------|---------|--------------|
| `init` | start, new | bootstrap a vault here |
| `ask` | question, q, meta | open a Question under the project or another question |
| `hypothesize` | hypothesis, idea | add a testable hypothesis under a question (register `-v` verifiables) |
| `test` | experiment, run, stage, launch | advance an idea: `idea → staged → running` (`stage`→staged, others→running) |
| `close` | record, conclude, verdict, land | derive the verdict from ticked verifiables; roll up the ledger |
| `review` | gate, decide | list questions the engine has tripped to `review` |
| `answer` | resolve, settle | resolve a question with a standing answer |
| `pursue` | branch, extend, reopen | keep a question open; optionally spawn a fresh hypothesis |
| `status` | map, tree, where, show | print the tree, or one node's ledger |
| `synthesize` | weave, rollup | optional horizontal synthesis across questions |
| `validate` | lint, check | run all integrity checks |

## Lifecycles

- **Hypothesis:** `idea → staged → running → done`. Can't go `running` without ≥1 verifiable.
- **Question:** `open → review → resolved`. The engine trips `open → review` automatically once every direct child is terminal (idea `done` / sub-question `resolved`). **Closing the question is always a human decision** (`answer` or `pursue`).

## Verdict (mechanical)

On `close`, the engine reads the `## Verifiables` checkboxes:
`- [x]` met · `- [ ]` unmet · `- [-]` could-not-evaluate.
**All met → `supported`** · all-or-some unmet → `refuted`/`partial` · only n/a remaining → `inconclusive`.
The engine never reads run logs — you supply the per-box judgement and a headline `--metric` string.

## A full session

```bash
python crux.py init "My project" --goal "..."
python crux.py ask "Can X improve Y?"
python crux.py hypothesize "A beats B" -p q1 -v "metric ≥ +0.01 vs baseline" -v "no regression on Z"
python crux.py launch h1 --run "job 4012"
# …tick the boxes in h1_*.md (the agent or you), then:
python crux.py close h1 -m "metric +0.012" -f "A wins decisively."
python crux.py review            # → q1 awaits a decision
python crux.py answer q1 -t "A is the load-bearing change."
```
