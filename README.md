# Crux

[![downloads](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fraw.githubusercontent.com%2Fmehdiforoozandeh%2Fcrux%2Ftraffic%2Fclones.json&query=%24.total&label=downloads&color=blue)](.github/workflows/clone-count.yml)
[![blog post](https://img.shields.io/badge/blog%20post-Agents%20on%20leash-FF6719?logo=substack&logoColor=white)](https://mforoozz.substack.com/p/agents-on-leash)

`crux` is an open-source toolbox for computational research with AI agents.

<p align="center">
  <img src="assets/crux-triptych.gif" width="860" alt="Three diagrams side by side, each building itself up and then holding. Left, 'knowledge base': three seed papers grow a citation crawl, an LLM compiles it into a wiki graph, and an agent reads WIKI.md and returns an answer. Middle, 'research tree': a project branches into questions; one question branches into two hypotheses, and each hypothesis has two verifiables — the green hypothesis has two ticks, the red one has two crosses. Right, 'automated research loop': an autopilot loop runs agent proposes, edits code, runs, evaluates; below it, a plot of metric against attempt climbs in steps as green points are kept, while a grey point is not.">
</p>

<p align="center"><sub>Three of crux's modules. <b>Knowledge base:</b> literature compiled into a wiki that agents read. <b>Research tree:</b> questions, hypotheses and findings, recorded from the conversation, each finding with its evidence and a confidence. <b>Automated research loop:</b> autopilot iterates on code against a metric.</sub></p>

## Motivation

AI coding agents can write code, run experiments and summarize results faster than a
researcher can follow. Over weeks and months, it becomes hard to track which questions a
project asked, what was tested, what the evidence showed, and which decisions the researcher
made. `crux` gives agents a shared structure for this work, keeps it as the project's
long-term memory, and gives the researcher a way to review it.

## What crux provides

`crux` consists of specialized agents and skills, a deterministic engine, and a read-only
browser interface (the **cockpit**). All state is stored as plain markdown in a vault inside
the project repository. It is organized into the modules below.

### Knowledge base

A literature wiki that agents consult for background, baselines and metrics. Following
[Karpathy's LLM-wiki pattern](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f),
sources are compiled into cross-linked markdown pages. A citation crawl over
[OpenAlex](https://openalex.org) starts from seed papers chosen by the researcher and ranks
related work that is not yet in the wiki. The wiki contains published work only; project
results are kept in the research tree. Skills: `crux-wiki`, `crux-litsearch`.

### Research tree

The project's long-term memory, organized by the scientific method: the questions asked, the
hypotheses made, what was found, the evidence for it, and how confident we are.

- **Questions** can nest, and can hold findings directly (exploratory work) or through
  hypotheses.
- **Hypotheses** state an **expectation** before any evidence, e.g. *"ADE20K val mIoU ≥
  supervised + 2.0, 3-seed mean"*. A **null** and **pre-registered checks (verifiables)** are
  added when they can be defined.
- **Findings** record what a result showed: a direction (supports, against, mixed, no answer
  yet), a confidence (strong, moderate, weak), one sentence of why, and links to the evidence.
  The agent judges the evidence against the expectation, the null and the checks; a null that
  is not ruled out caps a supporting finding at weak.

A node's state is derived from its findings: **open** (none yet), **leaning** (weak or
moderate), **settled** (strong), or **parked** (dropped by the conversation). There is no
close step, and the researcher corrects the record in plain words.

**The tree fills itself.** The agent records nodes silently as the conversation produces
them, guided by an always-on core that a Claude Code `SessionStart` hook injects in any repo
with a vault. Two triggers catch what it missed: at session start, a catch-up sweep hands
the transcript text not yet swept to one background capture run on a small model; and
**`/crux-wrap`** shows what this session recorded, then asks the researcher to accept or
reject each remaining candidate. Four agents support this: `crux-capture`, `crux-prerun`
(designs a run before compute), `crux-situate` (where things stand) and `crux-migrate`
(reconstructs an existing repo).

### Taskhub

A task list for work that is not a claim, such as downloading data, writing a scorer or
launching a run. Each task declares the tasks that block it, and a task can only be marked
done with a link to its output. The tree holds knowledge and the taskhub holds work: a task's
output enters the tree only as evidence on a finding.

### Autopilot

An optimization loop for questions with a single metric, such as a loss or a runtime. It
extends [autoresearch](https://github.com/karpathy/autoresearch). The researcher and the
agent first write a short plan: the editable files, a frozen scorer, the objective and its
threshold, a time budget, and guidance. In each attempt, an agent changes the code, the program
is scored, and the attempt is recorded in the research tree as a hypothesis with a finding
whose direction and confidence come from the score, with no model call.
Climb mode always builds on the best attempt; explore mode picks the parent with the
tree-search rule from Google's [ERA](https://www.nature.com/articles/s41586-026-10658-6),
which balances refining the best attempt against exploring less-visited ones. Skill:
`crux-autopilot`; command: `crux auto`.

### Engine

A stdlib-only Python engine handles IDs, tree consistency, the derived states and the roll-up
of confidence. Agents drive the engine through its CLI; the engine never judges evidence. The
researcher (the PI) keeps the decisions that cost something: starting an autopilot run,
starting compute they did not ask for, and merging into `main`. Their correction in plain
words always wins over the agent's record.

## Install

Needs Python ≥ 3.8 (the engine is stdlib-only) and `git`; the `npx` path also needs
Node.js. Install the crux skills with any [skills.sh](https://www.skills.sh)-compatible
agent — Claude Code, Cursor, Codex, Windsurf, Copilot CLI, and others:

```bash
npx skills add mehdiforoozandeh/crux --all
```

Or clone and symlink them into your agent's skills dirs:

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./install.sh
```

`./install.sh` also registers the session-start hook in `~/.claude/settings.json` and removes
links to agents that crux no longer ships, so re-run it after you update. Restart your agent
and you're set — `./crux selftest` checks the install. A vault from an earlier crux migrates
on its first write, after a backup. Scopes,
per-agent notes, updating, and troubleshooting: **[installation guide](INSTALL.md)**.

## Try it

No agent, no dependencies, nothing to configure — open the cockpit over the bundled
example vault from a fresh clone:

```bash
git clone https://github.com/mehdiforoozandeh/crux
cd crux && ./crux serve --dir skills/crux/examples/sortlab_vault
```

That's [sortlab_vault](skills/crux/examples/sortlab_vault):
one person asking which of the sorts they wrote is fastest, and whether they can beat the one
the language ships. Pan the state-colored tree and open any hypothesis's findings,
flip to the **Wiki** tab for the literature graph, and to **Taskhub** for the plans and runs
behind the results. (Port taken? `--port 8890`.) The screenshots below are
[segssl_vault](skills/crux/examples/segssl_vault), a lived-in research vault.

## The cockpit

Your vault opens in **Obsidian**, but crux has a purpose-built home for it. **`crux serve`**
is a dependency-free, **read-only** browser **cockpit** with one tab per module — **Tree**,
**Wiki**, **Taskhub** and **Autopilot**. On the Tree tab you pan / zoom / search the live
tree colored by state and confidence, focus one question, read any node's findings and
evidence, and open a
hypothesis's **report — rendered markdown, figures and all — beside the tree**. Edits still
go through your agent or the CLI.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/cockpit-tree-dark.webp">
    <img src="assets/screens/cockpit-tree-light.webp" width="900" alt="The crux serve cockpit (read-only) over the SegSSL example: the question/hypothesis tree colored by status — a couple of branches expanded, the rest collapsed — with hypothesis h1's evidence ledger on the right: its pre-registered verifiables (all met), headline metric (+3.3 mIoU on ADE20K), run link, and finding. Served locally over 127.0.0.1; edits go through your agent or the crux CLI.">
  </picture>
</p>

<p align="center"><sub>The <b>cockpit</b> over the <a href="skills/crux/examples/segssl_vault">segssl_vault</a> example — the status-colored tree (branches collapse/expand) and a hypothesis's <b>evidence ledger</b> (verifiables · metric · run link · finding). Read-only; every edit goes through your agent or the <code>crux</code> CLI. <em>(Real screenshot; it matches your GitHub light/dark theme.)</em></sub></p>

The Wiki tab draws the **knowledge base** as a graph **colored by category, sized by links,
cross-linked into the question tree**, flowing one way: literature → wiki → tree.

<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="assets/screens/wiki-graph-dark.webp">
    <img src="assets/screens/wiki-graph-light.webp" width="900" alt="The cockpit's Wiki tab: the SegSSL literature wiki drawn as a force-directed knowledge graph — nodes are wiki pages colored by category (concept, method, dataset, comparison, entity) and sized by number of links; a left explorer lists the pages and the 15 curated sources; the right pane renders the selected page. This is crux's own view, not Obsidian's graph.">
  </picture>
</p>

<p align="center"><sub>The <b>literature wiki</b> as crux's own knowledge graph — pages by category, sized by links, cross-linked with the question tree. Compiled by the <code>crux-wiki</code> skill from PI-curated sources.</sub></p>

## Contributing

Contributions are welcome; see [CONTRIBUTING.md](CONTRIBUTING.md).

## License

> *Crux* — the Southern Cross, the sky's most reliable signpost. It keeps you oriented to the **crux** of each question.

[MIT](LICENSE) © Mehdi Foroozandeh
