# Crux

**A scientific-method lab notebook your AI agent drives.** `crux` keeps a falsifiable
**question → hypothesis → evidence** tree for your research project — so nothing gets
silently p-hacked or forgotten across dozens of experiments. The agent runs the loop;
**you make the calls.**

**Why not just a doc, Notion, or W&B?** Those hold notes, a graph, and run logs. crux adds the part they don't:

| Your current setup | What crux adds on top |
|---|---|
| **Obsidian / Notion** — notes + a link graph | a **question → hypothesis** structure the engine keeps consistent, and rolls findings up automatically |
| **A spreadsheet / lab notebook** | **pass/fail bars you lock in _before_ the run**, and a **mechanical verdict** derived from them — no post-hoc goalpost-moving |
| **W&B / MLflow** — run logs & metrics | a human **review gate** and evidence roll-up across many parallel hypotheses; crux sits **beside** your tracker, not on top of it |

It's all plain markdown that only ever writes under `cruxvault/` — non-destructive,
Obsidian-compatible, and it can migrate a repo you already have.

## What it is

Months into a project, can you still say exactly what you asked, what you tested, and whether
each question is actually settled? `crux` makes that explicit and keeps it that way — organizing
a research program the way the scientific method actually works:

- **Questions** — what you don't know. They carry no answer of their own; they're resolved by aggregating the findings beneath them. Questions nest.
- **Hypotheses** — falsifiable, testable leaves under a question. Each carries **pre-registered verifiables** — the concrete pass/fail checks you write down *before* running (like *"test accuracy ≥ +2% vs baseline, held-out"*) — plus its **findings**. Hypotheses are the only things actually tested.
- A plain-Python **engine** does the bookkeeping so you don't: it assigns IDs, keeps the tree consistent, tallies the evidence upward, pauses at a human **review gate** for your sign-off before anything counts as final, and regenerates a navigable `META.md` map + `EXPERIMENTS.md` registry.
- An **LLM agent** drives it conversationally; **you (the PI)** make the judgment calls — which questions matter, the verifiable bar, and when a question is truly answered.

For example: you ask *"Does data augmentation improve test accuracy?"*; crux pins a hypothesis
with a bar you set in advance (*"+2% held-out"*); your agent runs it and reports back; **you**
sign off on the verdict. Nothing counts until you do.

<p align="center">
  <img src="assets/crux-schematic.svg" alt="Crux schematic — a vault tree of Questions and Hypotheses; the ask → hypothesize → test → close → review → answer loop; and the PI / Agent / Engine roles" width="820">
</p>

<p align="center"><sub><em>The model.</em> A Project holds Questions; Questions hold falsifiable Hypotheses, resolved through the ask → hypothesize → test → close → review → answer loop. Color here marks <b>role</b> (project · question · hypothesis); in the cockpit below it marks <b>status</b>.</sub></p>

## Install

`crux` is a small collection of skills under [`skills/`](skills). Install them all with any
[skills.sh](https://www.skills.sh)-compatible agent (Claude Code and others):

```bash
npx skills add mehdiforoozandeh/crux
```

Or clone and run the installer — it symlinks every crux skill into your Claude Code skills
dir (the `crux` tool skill, `evolve-crux`, and any future crux skills):

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./install.sh
```

The engine is Python 3, stdlib only — no dependencies. From a clone, run it with the
root-level wrapper: `./crux --help` (it forwards to `skills/crux/scaffold/crux.py`).

## The cockpit

Your vault is plain markdown you can open in **Obsidian** — but crux has its own purpose-built
home for it. Run **`crux serve`** for a dependency-free, **read-only** browser **cockpit**:
pan / zoom / search the live, status-colored tree, watch the review gate, and read each node's
evidence ledger. It's a viewer, so every edit still goes through your agent or the `crux` CLI —
Obsidian stays available for hands-on editing.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/cockpit-tree-dark.webp">
    <img src="assets/screens/cockpit-tree-light.webp" width="900" alt="The crux serve cockpit (read-only) over the SegSSL example: the question/hypothesis tree colored by status — a couple of branches expanded, the rest collapsed — with hypothesis h1's evidence ledger on the right: its pre-registered verifiables (all met), headline metric (+3.3 mIoU on ADE20K), run link, and finding. Served locally over 127.0.0.1; edits go through your agent or the crux CLI.">
  </picture>
</p>

<p align="center"><sub>The <b>cockpit</b> over the <a href="skills/crux/examples/segssl_vault">segssl_vault</a> example — the status-colored tree (branches collapse/expand) and a hypothesis's <b>evidence ledger</b> (verifiables · metric · run link · finding). Read-only; every edit goes through your agent or the <code>crux</code> CLI. <em>(Real screenshot; it matches your GitHub light/dark theme.)</em></sub></p>

It also gives the **literature wiki** its own view — one Obsidian can't. The `crux-wiki` skill —
inspired by [Karpathy's LLM-wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
(immutable curated sources an agent compiles into interlinked pages) — compiles PI-curated sources
into a knowledge base; the cockpit draws it as a graph **colored by literature category, sized by
links, and cross-linked into the live question tree**, with a one-way literature → wiki → tree flow.
That's structure Obsidian's undifferentiated graph doesn't capture.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/wiki-graph-dark.webp">
    <img src="assets/screens/wiki-graph-light.webp" width="900" alt="The cockpit's Wiki tab: the SegSSL literature wiki drawn as a force-directed knowledge graph — nodes are wiki pages colored by category (concept, method, dataset, comparison, entity) and sized by number of links; a left explorer lists the pages and the 15 curated sources; the right pane renders the selected page. This is crux's own view, not Obsidian's graph.">
  </picture>
</p>

<p align="center"><sub>The <b>literature wiki</b> as crux's own knowledge graph — pages by category, sized by links, cross-linked with the question tree. Compiled by the <code>crux-wiki</code> skill from PI-curated sources.</sub></p>

## Setting up in your project

Once the skill is installed, just tell your agent to **set up crux in your repo**. It runs
a short interview — *you only think about the science* — and stands up the vault for you:

- **Have a proposal, notes, or a draft paper?** Point the agent at it; it drafts your setup from it.
- **Already have a working repo** (code, results, months of work)? It reads it and *migrates*
  it into an organized crux-tree — reconstructing what was asked, tested, and found. It only
  ever writes under `cruxvault/` and never touches your existing files.
- **Nothing written down yet?** It figures the project out with you, one question at a time.

Either way it drafts one **seed outline**, you approve it, and the engine materializes the
whole notebook atomically. The seed shows both a fresh hypothesis and a migrated (already-run) one:

```
- Project: CANDI — self-supervised epigenome imputation
  - Q: Can JEPA improve CANDI?
    - H: JEPA pretraining beats supervised init            # fresh — an idea to run
      - v: imputation Spearman ≥ +0.01 vs baseline
    - H: [tested] contrastive aux loss lifts peak AUROC    # migrated — already-run work
      - v: [x] peak AUROC ≥ +0.02 (found: 0.71 → 0.74)
      - finding: net win on peaks.
```
```bash
crux init --from seed.md --dir cruxvault
```

crux is **human-in-charge by default**: you sign off exactly twice per hypothesis — before it
runs, and before its verdict is recorded — and never more. Full seed-spec reference in
[`skills/crux/scaffold/README.md`](skills/crux/scaffold/README.md).

## A minute with crux

You drive crux by **talking to your agent**. You describe the science; it proposes the concrete
node and a falsifiable bar; you approve; it runs the engine. You never memorize verbs. Here a
researcher opens a question and designs the first hypothesis:

<p align="center">
  <img src="assets/minute-with-crux.svg" alt="A chat: the researcher types /crux to start a project, the agent opens the question 'Does data augmentation improve test accuracy?' (q1), then proposes and pre-registers a hypothesis with a falsifiable verifiable (test accuracy ≥ +2% vs the no-aug baseline, held-out) as h1 — each engine command run only after the researcher approves." width="820">
</p>

Under the hood, that whole conversation is just a handful of engine commands — you never type
them, but here they are end to end:

```bash
crux ask "Does data augmentation improve test accuracy?"                       # opens q1
crux hypothesize "aug beats no-aug" -p q1 -v "test acc ≥ +2% vs baseline, held-out"  # h1, bar locked
crux test h1 --run "wandb.ai/…/runs/abc"                                        # idea → running
crux close h1 -m "acc +2.4%"                                                    # verdict from the ticked checkboxes
crux serve                                                                      # open the read-only cockpit
```

The verdict is **mechanical**: `crux close` reads the verifiable checkboxes (`[x]` met · `[ ]` unmet · `[-]` n/a) and derives `supported` / `partial` / `refuted` / `inconclusive`. The engine never reads your run logs — you supply the per-box judgment and a headline metric. That keeps it domain-agnostic and keeps you honest: the bar was set before the run.

## License

> *Crux* — the Southern Cross, the sky's most reliable signpost. It keeps you oriented to the **crux** of each question.

[MIT](LICENSE) © Mehdi Foroozandeh
