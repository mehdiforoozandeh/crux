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
| `init` | start, new | bootstrap a vault here (`--from seed.md` materializes a whole tree — see **Setup**) |
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

## Setup — `init --from` a seed outline

Standing up a vault node-by-node is tedious. Instead the agent drafts one **seed
outline** (from your docs, your existing repo, or a conversation), you edit/approve it,
and the engine materializes the whole vault in one atomic step:

```bash
python crux.py init --from seed.md --dir crux
```

The seed is an **indented-bullet outline** — indent (2 spaces) = nesting, a type prefix
per line. It's parsed deterministically (stdlib) and fully validated *before* any file is
written, so a malformed seed leaves nothing behind.

```
- Project: CANDI — self-supervised epigenome imputation & denoising
  - Q: Can JEPA improve CANDI?
    - Q: Does a predictive latent help imputation?
      - H: JEPA pretraining beats supervised init      # open idea (not yet run)
        - v: imputation Spearman ≥ +0.01 vs baseline   # a verifiable
        - v: no calibration regression
      - H: [tested] contrastive aux loss lifts peak AUROC   # reconstruct finished work
        - v: [x] peak AUROC ≥ +0.02 (found: 0.71 → 0.74)   # tick = met; (…) = evidence
        - v: [ ] no train-time slowdown
        - finding: net win on peaks; ~15% slower per step.
```

Node kinds and where they may sit (mirrors the model — the parser enforces it):

| prefix | node | parent must be | notes |
|--------|------|----------------|-------|
| `Project:` | project root | — (exactly one, at top) | `TITLE — GOAL` (em-dash or `--` splits goal) |
| `Q:` | question | Project or another `Q` | nests arbitrarily deep |
| `H:` | hypothesis | a `Q` | prefix `[tested]` to reconstruct already-run work |
| `v:` | verifiable | an `H` | optional `[x]`/`[ ]`/`[-]` tick + trailing `(evidence)` |
| `finding:` | finding line | an `H` | one-line narrative for a `[tested]` hypothesis |
| `problem:` | problem statement | an `H` | optional; why it's worth testing |

For a **`[tested]`** hypothesis the engine ticks the verifiables as written, records the
finding, and **closes it** — deriving the verdict *mechanically* from the ticks (`[x]`
met · `[ ]` unmet · `[-]` n/a). It never invents a verdict; you supply the ticks. Fresh
(un-`[tested]`) hypotheses land as open `idea`s to run through the normal flow.

## Engine version stamp

`init` records `engine_version` in `.crux.yaml`. On every run against an existing vault,
the engine compares that stamp to its own version; on a mismatch it prints a loud drift
warning and re-stamps (so the change lands as a `git` diff — an auditable record that the
engine moved under a fixed vault). Verdicts depend on both your ticks *and* the engine, so
the version travels with the vault in version control.
