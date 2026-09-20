---
name: crux-litsearch
description: >-
  Set up a literature search over a crux vault with the PI, in two asks and one approval, and
  write it to `wiki/lit/<slug>/scope.md` — what the search is for, and the 3–8 papers the PI
  already trusts, which are what the citation crawl walks outward from. Spends its turns
  getting the seeds right rather than polishing prose, because the seed set defines the
  subgraph and a beautiful scope over bad seeds gives a bad list. Lints the file with
  `crux lit lint`, then stops and hands the PI the exact `crux lit crawl` line. Never runs the
  crawl, never writes to `raw/`. Use when a crux user wants to find the papers their wiki is
  missing. Triggers: "what am I missing in the literature", "find papers for this", "set up a
  literature search", "search the literature", "who else has done this", crux lit, lit scope,
  literature crawl.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  requires: "the crux and crux-wiki skills, installed as siblings (shares the engine at <crux skill>/scaffold/)"
---

# crux-litsearch — write the scope, then stop

A crux wiki's PI curates `raw/` from memory. This skill replaces that with the citation
graph's own answer: start from papers the PI already trusts, walk outward, and rank what
comes back by how much of the seed set reaches it.

You do the conversation and write one file; the engine crawls and ranks. You never run the
crawl and never put anything in `raw/` unasked — [crux-wiki](../crux-wiki/SKILL.md)'s rule
that the PI alone curates sources holds; they just curate from a computed list, not memory.

## The two asks and the one approval

**Ask 1 — what is this search for?** One paragraph in the PI's own words, not a keyword
list: it is what they read in a month to remember why these papers. Write what they say, not
a tidied version.

**Ask 2 — which papers do you already trust?** The ask that matters, and where the turns go.
Target **3–8**: fewer and the shared subgraph is whatever one paper happened to cite, more and
the seeds stop agreeing on a subject. Take DOIs where the PI has them; where they name a paper
instead, resolve it and read the title back before it enters the file — a wrong seed is
invisible in the output and poisons every rank.

**If the PI has no seeds**, propose five or six papers by name from what you know of the
field, say plainly that these are suggestions and not a search result, and let the PI strike
what does not belong. Never invent a DOI — resolve each accepted title with
`crux ingest raw/<file> --doi …` and let OpenAlex supply the identifier.

**Approval — the file.** Write `wiki/lit/<slug>/scope.md`, run `crux lit lint <slug>`, fix
anything it reports, show the PI the file, and **stop**. The PI runs the crawl.

## What you write

```markdown
---
type: lit-scope
slug: <the directory name>
---

## Problem

<the PI's paragraph>

## Seeds

- 10.1038/nmeth.1906
- W4230875896

## Out of scope

- <what the PI said not to bother with>
```

`## Out of scope` is for you to read later, going through the list; the engine does not
filter on it.

## Writing is not approving

Writing the file is not permission to crawl. Hand the PI the line and let them run it:

```
crux lit crawl <slug>
```

A crawl with no scope file still works, seeding from every `raw/` source carrying a work id
— right for a vault with one line of enquiry. The scope is for the vault with more than one.

## Reading the list afterwards

`wiki/lit/<slug>/candidates.tsv` is complete and sorted, often some thousands of rows. Do not
truncate the file: it is the record of what the PI chose from, and re-crawling to recover it
costs the whole budget again. **Present the top 30** and offer to go deeper.

Read the columns, not just the rank. `seeds` is how many seeds reach the paper directly and
is the strongest signal; `hubs` is depth-two reach; `cites` is context, never the ranking. A
high-`cites` row low in the list is the ranking working — the field's furniture.

Then take the keepers. Read their work ids off the list and hand the PI one line:

```
crux lit fetch <slug> --pick W… --pick W…
```

It downloads each open-access PDF into `raw/` and registers it with the canonical title. A
paper with no open-access copy, and a publisher gating the file behind a browser check, are
both reported with the DOI and skipped — nothing partial lands in `raw/`, and the PI fetches
those by hand. Expect roughly half to need it.

## Guardrails

- **The PI curates `raw/`.** You propose; they dispose. Never `lit fetch` a candidate the PI
  has not named, however obviously right it looks.
- **Never invent a DOI or a work id.** Resolve it or ask. A fabricated identifier ingests
  cleanly and is wrong forever.
- **Never truncate `candidates.tsv`,** and never hand-edit it — it regenerates from the crawl.
- **The one-way flow rule still holds.** Everything here is literature. A scope file must
  never cite a `q*`/`h*` node, and a project finding never becomes a seed.
