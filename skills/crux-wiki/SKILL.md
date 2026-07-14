---
name: crux-wiki
description: >-
  A literature wiki for a crux research vault — Andrej Karpathy's LLM-wiki pattern applied to
  a crux project. The PI curates immutable sources under `raw/`; you (the agent) compile them
  into a persistent, interlinked `wiki/` of background, prior methods, SOTA, baselines,
  datasets, and definitions, and draw on it to ask sharper questions and design better
  hypotheses. The crux engine owns the bookkeeping (source hashes, the generated `WIKI.md`
  index, structural lint via `crux validate`); you supply the reading and synthesis. One-way
  by design: literature → wiki → informs the tree; a project's own findings never enter the
  wiki. Use when a crux user wants a project-relevant literature base. Triggers: "ingest this
  paper", "add to the wiki", "what does the literature say", "compile a wiki", "lint the wiki",
  literature review, prior work / SOTA / baselines for a crux project, crux wiki, LLM wiki.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  requires: "the crux skill, installed as a sibling of this one (shares its engine at <crux skill>/scaffold/)"
  notice: "Instantiates Karpathy's LLM-wiki pattern on crux; bundled engine is original MIT work; no third-party code."
---

# crux-wiki — a literature wiki for a crux vault

This skill adds a **literature layer** to a crux research vault: a living, interlinked
knowledge base of *prior* knowledge — background, methods, SOTA, baselines, datasets,
definitions — that you maintain and draw on. It is [Andrej Karpathy's LLM-wiki pattern]
(compile curated sources once into a persistent wiki; keep it current; don't re-derive on
every query) instantiated on crux, so crux's deterministic engine does the bookkeeping the
pattern needs.

It rides on the **crux** skill and its engine (`<crux skill>/scaffold/` — the crux skill
is this skill's sibling directory in your skills dir; in a repo clone, `skills/crux`).
If the engine is missing, install the crux skill first
(`npx skills add mehdiforoozandeh/crux --all`, or the repo's `./install.sh`). crux
tracks the *new* knowledge you're producing (the Question→Hypothesis tree); crux-wiki
tracks the *existing* knowledge you're building on. They are cross-linked but separate.

## The one-way flow rule (hard, load-bearing)

```
literature (raw/) → wiki/ → informs  ask · hypothesize · interpreting findings
```

**Never the reverse.** The wiki is a literature source-of-truth. A crux project's own
results — verdicts, findings, closed hypotheses — **never** flow into the wiki. Wiki pages
may link *out* to nothing but other wiki pages and their `raw/` sources; they must never
cite a `q*`/`h*` tree node. This keeps provenance clean (every wiki claim traces to a
curated source, never to your own unpublished result) and structurally prevents the
self-ingestion / model-collapse failure mode that degrades agent-maintained wikis.

The reverse direction *is* allowed and encouraged: a tree node (a question or hypothesis)
may cite `[[wiki/page]]` to ground itself in the literature.

## The three layers

- **`raw/`** — the PI's curated sources: papers, articles, notes, data files. **Immutable.**
  You read them; you never modify them. This is the source of truth. **Only the PI decides
  what enters `raw/`** — that curation is the human's job in this pattern.
- **`wiki/`** — the compiled pages, **owned by you**. Concept-slug markdown files
  (`film-conditioning.md`), plus the append-only `wiki/log.md` and the co-evolved
  `wiki/SCHEMA.md`. You create pages, update them as sources arrive, and maintain the links.
- **`wiki/SCHEMA.md`** — this vault's conventions (which categories it uses, page style,
  domain quirks). Seeded on first ingest; you and the PI co-evolve it. Read it at the start
  of a wiki session so you stay a disciplined maintainer, not a generic chatbot.

The engine generates one more file — **`WIKI.md`** at the vault root: the index (Karpathy's
`index.md`), a catalog of every page by category with its one-line summary, plus the source
registry with compiled status. **Never hand-edit `WIKI.md`** — it regenerates on every crux
command. It is your entry point for a query.

## The three operations

### Ingest — `crux ingest raw/<file> --title "<title>"`  ○→◆

The PI drops a source into `raw/`. You run `crux ingest` — the engine (○) records its
sha256 in the registry, appends a `## [YYYY-MM-DD] ingest | <title>` line to `wiki/log.md`,
and re-renders `WIKI.md`.

**Title convention:** the `--title` carries the paper title **plus the full author list
and year** — e.g. `"Masked Autoencoders Are Scalable Vision Learners — Kaiming He,
Xinlei Chen, Saining Xie, Yanghao Li, Piotr Dollár, Ross Girshick (2021)"`. The registry
title is the only author-bearing field in the vault, so this is what makes sources
findable by author (in the cockpit's wiki search, in `WIKI.md`, and by grep); a bare
"He et al" hides every co-author. Keep it on one line (the registry and log are
line-based).

Then **you** (◆) do the reading and synthesis the engine can't:

1. Read the source in `raw/`.
2. Compile it into the wiki — **update existing pages** where the source touches known
   concepts (entity/method/dataset pages), and **create new pages** for genuinely new
   concepts. A single rich source often touches many pages. Every page cites its `raw/`
   sources in frontmatter (`sources:`), and every claim traces to one of them.
3. Note where the new source **contradicts** an existing page — flag it explicitly on the
   page (see the semantic-lint checklist), don't silently overwrite.
4. Run `crux validate` and fix any structural finding it reports.

Because the PI already curated what entered `raw/`, compilation is **act-and-report**: do
it, then summarize what you filed. You do not need per-page approval.

### Query — read `WIKI.md` → drill in → answer with citations  ◆

Pure agent behavior; no engine verb. To answer a question against the wiki: read `WIKI.md`
first to find relevant pages, open them, follow `[[links]]`, and synthesize an answer that
**cites the pages and their `raw/` sources**. Prefer compiled wiki content over your own
training knowledge.

**File good answers back** (Karpathy's key insight): a comparison table, a SOTA summary, a
connection you discovered — if it's durable and worth keeping, save it as a new wiki page so
explorations compound instead of vanishing into chat. Filed-back pages still obey the flow
rule: they synthesize *literature*, cited to `raw/` — never a project finding.

### Lint — `crux validate` (structural) + your semantic pass  ○ + ◆

Two tiers, split exactly along crux's engine/agent line:

- **Structural (engine, deterministic).** `crux validate` reports, as hard findings:
  broken `[[wiki links]]` (both directions), flow-rule violations (a wiki page citing the
  tree), missing `title`/`summary`, orphan pages (no inbound link), pages citing a missing
  source, registered-but-uncompiled sources, and **source hash drift** (a `raw/` file's
  bytes changed since ingest — re-ingest it). These can't drift because the index and checks
  are regenerated, not hand-kept.
- **Semantic (you, judgment).** The engine never judges meaning; you run the health check
  Karpathy describes and the community's production reports converge on. **Do it at the
  start of a wiki session** — on-demand-only maintenance never happens ("vaults rot in
  silence"). Checklist:
  - **Contradictions** between pages → make it a first-class flagged state on the page
    (a `> [!contradiction]` note or a `contested: true` line), recording *both* positions
    with their sources and dates. Do not silently pick a winner.
  - **Stale claims** a newer source superseded → update the entity page **in place** (the
    page states current knowledge; the log stays the append-only history). Don't leave the
    old claim frozen while new facts pile up elsewhere.
  - **Missing pages** — an important concept cited across several sources but with no page
    of its own → create it.
  - **Missing cross-references / thin pages** — pages that should link but don't; pages too
    sparse to be useful.
  - **Data gaps** — a question the wiki can't answer yet → suggest a source for the PI to add.

## Page conventions

- **One thing per page** — an entity, a concept, a method, a comparison, an overview.
  Concept-slug filenames (`average-reference-baseline.md`), renamed/merged freely as
  understanding evolves (slugs, not numbered ids — the wiki is not the tree).
- **Frontmatter:** `type: wiki` (required — this is what makes it a page), `title`,
  `summary` (one line — this becomes the index entry), `category`
  (`entity | concept | method | comparison | dataset | overview | …`), `sources`
  (comma-separated `raw/…` paths; every claim on the page traces to one).
- **Write for the LLM reader.** You are the primary reader of this wiki, not a human. Favor
  dense, explicit, structured prose over pretty formatting.
- **Lead line extends the summary.** The `summary` frontmatter *is* the index entry — don't
  repeat it verbatim as the page's first body line. Open with a sentence that *extends* it:
  scope, context, or the sharpest claim.
- **Synthesize, don't mirror (anti-bloat).** Create a page when a concept appears across ≥2
  sources or is central to one — not for passing mentions. A **single-source page earns its
  place only if it adds cross-source value** — a shared metric axis, a contradiction link, a
  comparison caveat — beyond paraphrasing that source; if it would just restate one small
  source, fold the concept into a comparison or concept page instead. When your sources are
  short (a paragraph each), prefer 2–3 synthesis pages over one page per named method. The win
  is compressing facts scattered across many sources; a page that mirrors one source 1:1 adds
  negative value.
- **Start the template** from `<crux skill>/scaffold/templates/wiki.md`.

## Setup

The wiki stands up lazily on the **first `crux ingest`** — it creates `wiki/`, `wiki/log.md`,
`wiki/SCHEMA.md`, and the first `WIKI.md`. There's nothing to initialize by hand. On an
existing crux vault, the first ingest bumps the engine to a wiki-aware version cleanly (old
vaults keep working; the tree is untouched).

To start: point the PI at `raw/` ("drop the papers/notes you want me to build on into
`raw/`"), ingest them one at a time (Karpathy's supervised default — read the summary, guide
emphasis) or in a batch, then open `WIKI.md` in Obsidian to see the graph.

## Guardrails

- **The flow rule is absolute.** Literature → wiki → tree. Never file a project finding into
  the wiki; never let a wiki page cite a `q*`/`h*` node. `crux validate` enforces the second
  half mechanically.
- **The PI curates `raw/`.** You never decide what counts as a source. You never modify a
  `raw/` file.
- **Cite everything.** Every wiki claim traces to a `raw/` source. This is the guard against
  hallucinating into the wiki — an uncited claim is a lint smell.
- **Let the engine do bookkeeping.** Don't hand-maintain the index or hunt links by eye —
  `WIKI.md` is generated and `crux validate` finds the broken/orphan/drift cases. Your job is
  the reading, the synthesis, and the semantic judgments the engine can't make.
- **Don't hand-edit generated content** — `WIKI.md`, or the crux tree's `META.md`/
  `EXPERIMENTS.md`. Run a crux command to regenerate.
- **Optional at scale.** At small scale the `WIKI.md` index is enough (no embedding-RAG
  needed). If a vault grows to many hundreds of pages, a local markdown search tool
  ([qmd](https://github.com/tobi/qmd), BM25 + vector, CLI or MCP) is the natural add — but
  it's optional and outside this skill.

## The engine (shared with crux)

crux-wiki drives the same engine the `crux` skill ships (`<crux skill>/scaffold/`):
`crux ingest` (register a source), `crux validate` (tree + wiki structural lint), and
`crux status`. Pages are plain markdown you write per the template; the engine scans them,
never generates their content. Validate the install with
`python <crux skill>/scaffold/crux.py selftest` — its `# wiki layer` section asserts every
wiki invariant (ingest, index render, idempotency, structural lint, backward-compat) with
no GPU/tokens.
