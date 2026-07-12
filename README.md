# Crux

**An agentic research companion** — a scientific-method lab notebook your LLM agent drives.

> *Crux* (the Southern Cross) is the sky's smallest constellation and its most reliable signpost — for centuries it's how navigators found their bearings. `crux` does the same for a research program: it keeps you oriented through a growing tree of open questions and the hypotheses that resolve them, and helps you get to the **crux** of each one.

## What it is

`crux` organizes a research program the way the scientific method actually works:

- **Questions** — what you don't know. They carry no answer of their own; they're resolved by aggregating the findings beneath them. Questions nest.
- **Hypotheses** — falsifiable, testable leaves under a question, each with **pre-registered verifiables** and **findings**. The only things actually tested.
- A deterministic **engine** does the bookkeeping — IDs, the parent tree, validators, the evidence-ledger roll-up, a human **review gate**, and regenerating a navigable `META.md` map + `EXPERIMENTS.md` registry.
- An **LLM agent** drives it conversationally; **you (the PI)** make the judgment calls — which questions matter, the verifiable bar, and when a question is truly answered.

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

The vault is just plain markdown, so you can open it in **Obsidian** if you like — the
question/hypothesis tree and `[[wikilinks]]` work out of the box. But crux has its **own**
home for it: run **`crux serve`** for a dependency-free, **read-only** browser **cockpit** —
pan / zoom / search the live, status-colored tree, watch the review gate, and read each
node's evidence ledger. It's what we recommend; Obsidian stays available for editing.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/cockpit-tree-dark.webp">
    <img src="assets/screens/cockpit-tree-light.webp" width="900" alt="The crux serve cockpit (read-only) over the SegSSL example: the question/hypothesis tree colored by status — a couple of branches expanded, the rest collapsed — with hypothesis h1's evidence ledger on the right: its pre-registered verifiables (all met), headline metric (+3.3 mIoU on ADE20K), run link, and finding. Served locally over 127.0.0.1; edits go through your agent or the crux CLI.">
  </picture>
</p>

<p align="center"><sub>The <b>cockpit</b> over the <a href="skills/crux/examples/segssl_vault">segssl_vault</a> example — the status-colored tree (branches collapse/expand) and a hypothesis's <b>evidence ledger</b> (verifiables · metric · run link · finding). Read-only; every edit goes through your agent or the <code>crux</code> CLI. <em>(Real screenshot; it matches your GitHub light/dark theme.)</em></sub></p>

It also gives the **literature wiki** its own home — a knowledge-graph view that's crux's, not
Obsidian's. The `crux-wiki` skill compiles PI-curated sources into interlinked pages; the
cockpit draws them as a graph colored by category and sized by links, cross-linked with the
tree (knowledge flows literature → wiki → tree, never back).

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

crux is **human-in-charge by default**: the agent drafts, runs, and reports, but *you* approve
before an experiment runs and before any verdict is recorded. Full seed-spec reference in
[`skills/crux/scaffold/README.md`](skills/crux/scaffold/README.md).

## A minute with crux

You drive crux by **talking to your agent**. You describe the science; it proposes the concrete
node and a falsifiable bar; you approve; it runs the engine. You never memorize verbs. Here a
researcher opens a question and designs the first hypothesis:

<p align="center">
  <img src="assets/minute-with-crux.svg" alt="A chat: the researcher types /crux to start a project, the agent opens the question 'Does data augmentation improve test accuracy?' (q1), then proposes and pre-registers a hypothesis with a falsifiable verifiable (test accuracy ≥ +2% vs the no-aug baseline, held-out) as h1 — each engine command run only after the researcher approves." width="820">
</p>

The verdict is **mechanical**: `crux close` reads the verifiable checkboxes (`[x]` met · `[ ]` unmet · `[-]` n/a) and derives `supported` / `partial` / `refuted` / `inconclusive`. The engine never reads your run logs — you supply the per-box judgment and a headline metric. That keeps it domain-agnostic. Running an experiment and recording a verdict are always **your** call — crux is human-in-charge by default.

## License

[MIT](LICENSE) © Mehdi Foroozandeh
