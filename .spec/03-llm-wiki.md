# Spec 03 — LLM wiki

**Label:** `wiki` · **Status:** ◐ in progress

## Goal

A **literature** layer in the vault — a living, interlinked knowledge base of *prior*
knowledge (background, definitions, methods, SOTA, baselines, references) that the agent
compiles from PI-curated immutable sources and draws on, cross-linked with the crux tree so
questions and hypotheses can cite and build on what's known.

Knowledge flows **one way**: literature → wiki → tree. A project's own findings never enter
the wiki — this keeps provenance clean and prevents the self-ingestion failure mode.
Instantiates Karpathy's LLM-wiki pattern.

## Delivered

Shipped as the `crux-wiki` skill + engine `ingest` / `WIKI.md` / wiki-lint
(`ENGINE_VERSION` 1.1).

- ☑ **Define the wiki page** — `type: wiki` pages under `wiki/` (concept-slug filenames),
  parentless and outside the roll-up tree, linked via `[[wikilinks]]`; immutable sources
  under `raw/`.
- ☑ **Agent reads the wiki for context** — `WIKI.md` index + pages consulted when proposing
  questions/hypotheses; tree nodes may cite `[[wiki/page]]` (the crux-wiki skill).
- ☑ **Agent compiles the wiki from literature** — `crux ingest` registers a source; the
  agent compiles/updates pages that cite `raw/`. *(Amended: knowledge comes from curated
  literature, not from distilling the project's own findings — findings never enter the wiki.)*
- ☑ **Index & render** — engine-generated `WIKI.md` at the vault root (pages by category +
  source registry), byte-stable, without polluting the question/hypothesis tree; structural
  lint via `crux validate`.
- ☑ **Browse the wiki in the cockpit** — a `Wiki` tab in `crux serve`: explorer rail
  (virtual category folders + pinned index/log/schema/sources) + deterministic force-directed
  link graph (color = category, size = degree) + markdown reader with backlinks;
  `[[wiki/…]]` citations in the tree's detail pane jump straight into it.
  *(PRD: [`docs/prd/gui-wiki-tab.md`](../docs/prd/gui-wiki-tab.md); `wiki` snapshot key +
  `/wiki/<slug>.json`.)*

## Open: index resolution — raising what `WIKI.md` can route

Found by a multi-axis audit of the CANDI vault (2026-08-01, 144 sources / 40 pages). Both
items are engine-side changes to index generation; the vault-side fixes from the same audit
are done. The finding was that retrieval fails in one specific way: **the index resolves
pages**, so any query pitched at sub-page granularity falls back to grep. Both fixes are
cheap and neither requires the agent to write a new sentence.

- ☐ **Source → page reverse index** — `WIKI.md`'s source roster prints
  `raw/zhang-2008-macs.xml — … (5 page(s))` but never *which five*, and the count is computed
  from a list the renderer already holds and discards. Emit the citing-page slugs, and add
  them as a 5th column in `wiki/.sources.tsv`. Makes "I just read this paper — where did it
  land, and what else cites it?" a zero-hop lookup instead of a grep, and makes ingest fan-out
  visible at a glance. *(In the audited vault, fan-out was 1.48 pages/source against
  Karpathy's 10–15, and 24 of 25 frontier sources sat in single-page silos — invisible until
  someone scripted the sources-to-pages map.)*
- ☐ **Heading-level sub-entries in the generated index** — harvest each page's `##` headings
  at render time and emit them as indented sub-entries under its catalog line (or as a
  separate `## Claims` section listing `page › heading`). Raises the index's effective
  resolution from ~40 entries to ~250 for ~150 lines, next to the 130+ already spent on the
  source roster. *(In the audit's 12-question retrieval benchmark, both failures had this
  single cause: the answer was a named section inside a page whose one-line index entry
  contained no matching token.)*
- ☐ **Record ingest fan-out in `log.md`** — extend the ingest log line to name the pages an
  ingest touched (`## [date] ingest | <title> → film-conditioning, covariate-conditioning`),
  computed by diffing which pages gained the source in their `sources:` frontmatter on the
  next refresh. Today `log.md` is a source-registration ledger; Karpathy's is "a record of
  ingests, queries and lint passes". Cheapest structural guard against silo-ingest recurring.

## Why this epic matters to the later ones

The wiki layer is the **reference implementation** for two later specs. It established the
pattern: a class of documents that live in the vault, link into the tree, sit outside the
roll-up, get a generated index, and are structurally linted. Both
[07 RD layer](07-rd-layer.md) and [08 taskhub](08-taskhub.md) copy this shape rather than
inventing a new one.

The index-resolution finding above is also a **transferable warning**: an index whose
granularity doesn't match the queries made against it degrades to grep. Taskhub's navigation
design (`work the frontier`) exists specifically to avoid repeating it.

`wiki_schema.md`'s "categories in use" — a per-vault declared taxonomy, co-evolved by PI and
agent — is the precedent taskhub reuses for task categories.
