# Crux

**A scientific-method lab notebook your AI agent drives.** `crux` keeps a falsifiable
**question → hypothesis → evidence** tree for your project, so nothing gets silently
p-hacked or forgotten across dozens of experiments. The agent runs the loop;
**you make the calls.**

## What it is

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/crux-chat-dark.gif">
    <img src="assets/crux-chat-light.gif" width="860" alt="A split screen. On the left, a scientist and an agent talk about an experiment in ordinary language — the scientist states a question and a guess, the agent reports what the nearest prior work did and did not rule out, the scientist names the two outcomes that would settle it and says to run it. On the right, a cockpit fills itself in as they talk: a question, a hypothesis and two checks appear on a tree with their tick boxes still empty, a literature graph of papers and areas, then a task list working through a plan. When the run comes back the agent reports only what the data did — one check green, one red — and the hypothesis is marked refuted only after the scientist says it is dead. Nobody types on the cockpit side; a caption reads 'the agents maintain this notebook, the human only talks science'.">
  </picture>
</p>

<p align="center"><sub><em>You talk science; the notebook fills.</em> The conversation never mentions crux. On the right, agents keep the science tree, the literature wiki and the task list in step with the talk — checks written down <em>before</em> the run, so the verdict is derived from the bar you set, not argued from the number that came back. The agent supplies the evidence; the verdict is yours.</sub></p>

Months in, can you still say what you asked, what you tested, and whether each question is
settled? `crux` keeps that explicit:

- **Questions** — what you don't know. They carry no answer of their own; they resolve by aggregating the findings beneath them, and they nest.
- **Hypotheses** — falsifiable leaves under a question, each with **pre-registered verifiables** (pass/fail checks written down *before* running: *"ADE20K val mIoU ≥ supervised + 2.0, 3-seed mean"*), its findings, and the report and figures the run produced. Only hypotheses are tested.
- A plain-Python **engine** does the bookkeeping: IDs, tree consistency, evidence tallied upward, a human **review gate**, a regenerated `META.md` + `EXPERIMENTS.md`.
- An **LLM agent** drives it; **you (the PI)** make the calls — which questions matter, where the bar sits, when a question is answered.

Nothing counts until you sign off.

## Install

Needs Python ≥ 3.8 (the engine is stdlib-only) and `git`; the `npx` path also needs
Node.js. Install all four crux skills with any [skills.sh](https://www.skills.sh)-compatible
agent — Claude Code, Cursor, Codex, Windsurf, Copilot CLI, and others:

```bash
npx skills add mehdiforoozandeh/crux --all
```

Or clone and symlink them into your agent's skills dirs:

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./install.sh
```

Restart your agent and you're set — `./crux selftest` checks the install. Scopes,
per-agent notes, updating, and troubleshooting: **[installation guide](INSTALL.md)**.

## Try it in 60 seconds

No agent, no dependencies, nothing to configure — open the cockpit over the bundled
example vault from a fresh clone:

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./crux serve --dir skills/crux/examples/segssl_vault
```

That's [segssl_vault](skills/crux/examples/segssl_vault) (**5 questions, 16 hypotheses** —
the vault behind the screenshots below): pan the status-colored tree, open h1's evidence
ledger and its rendered **report with figures**, flip to the **Wiki** tab for the literature
graph. (Port taken? `--port 8890`.)

## The cockpit

Your vault opens in **Obsidian**, but crux has a purpose-built home for it. **`crux serve`**
is a dependency-free, **read-only** browser **cockpit**: pan / zoom / search the live tree,
focus one question, watch the review gate, read any node's evidence ledger, and open a
hypothesis's **report — rendered markdown, figures and all — beside the tree**. Edits still
go through your agent or the CLI.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/cockpit-tree-dark.webp">
    <img src="assets/screens/cockpit-tree-light.webp" width="900" alt="The crux serve cockpit (read-only) over the SegSSL example: the question/hypothesis tree colored by status — a couple of branches expanded, the rest collapsed — with hypothesis h1's evidence ledger on the right: its pre-registered verifiables (all met), headline metric (+3.3 mIoU on ADE20K), run link, and finding. Served locally over 127.0.0.1; edits go through your agent or the crux CLI.">
  </picture>
</p>

<p align="center"><sub>The <b>cockpit</b> over the <a href="skills/crux/examples/segssl_vault">segssl_vault</a> example — the status-colored tree (branches collapse/expand) and a hypothesis's <b>evidence ledger</b> (verifiables · metric · run link · finding). Read-only; every edit goes through your agent or the <code>crux</code> CLI. <em>(Real screenshot; it matches your GitHub light/dark theme.)</em></sub></p>

The **literature wiki** gets its own view too. The `crux-wiki` skill — inspired by
[Karpathy's LLM-wiki idea](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f) —
compiles PI-curated sources into a knowledge base, drawn here as a graph **colored by
category, sized by links, cross-linked into the question tree**, flowing one way:
literature → wiki → tree.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/wiki-graph-dark.webp">
    <img src="assets/screens/wiki-graph-light.webp" width="900" alt="The cockpit's Wiki tab: the SegSSL literature wiki drawn as a force-directed knowledge graph — nodes are wiki pages colored by category (concept, method, dataset, comparison, entity) and sized by number of links; a left explorer lists the pages and the 15 curated sources; the right pane renders the selected page. This is crux's own view, not Obsidian's graph.">
  </picture>
</p>

<p align="center"><sub>The <b>literature wiki</b> as crux's own knowledge graph — pages by category, sized by links, cross-linked with the question tree. Compiled by the <code>crux-wiki</code> skill from PI-curated sources.</sub></p>

## License

> *Crux* — the Southern Cross, the sky's most reliable signpost. It keeps you oriented to the **crux** of each question.

[MIT](LICENSE) © Mehdi Foroozandeh
