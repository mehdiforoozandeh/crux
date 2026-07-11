---
type: wiki_schema
title: Wiki schema
---

# Wiki schema — conventions for THIS vault's literature wiki

Co-evolved by you (the PI) and the agent. The global rules live in the `crux-wiki`
skill; this file records the choices specific to this project.

## What the wiki is
A literature background layer: prior methods, SOTA, baselines, datasets, definitions —
compiled once from the immutable sources in `raw/`, then kept current. It exists to
sharpen `ask` / `hypothesize` and to interpret findings. It is **not** a record of this
project's own results.

## Flow rule (hard)
Literature → wiki → informs the tree. **Never** the reverse. A wiki page may link other
wiki pages; it must never cite a q/h tree node. Findings never enter the wiki.

## Page conventions
- One concept / entity / comparison per page; concept-slug filenames (`film-conditioning.md`).
- Frontmatter: `title`, `summary` (one line — becomes the index entry), `category`
  (entity | concept | method | comparison | dataset | overview | …), `sources`
  (comma-separated `raw/…` paths every claim traces to).
- Write for the LLM reader: dense and explicit over pretty.

## Categories in use
_(list the categories this vault uses, so pages stay consistent)_
