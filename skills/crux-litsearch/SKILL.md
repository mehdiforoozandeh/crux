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

You do the conversation and write one file. The engine does the crawl and the ranking. You
never run the crawl and you never put anything in `raw/` — [crux-wiki](../crux-wiki/SKILL.md)'s
rule that the PI alone curates sources is untouched here; the PI just gets a computed list to
curate from instead of their memory.

## The two asks and the one approval

**Ask 1 — what is this search for?** One paragraph in the PI's own words. Not a keyword
list: the paragraph is what the PI reads in a month to remember why these papers. Write down
what they say, not a tidied version of it.

**Ask 2 — which papers do you already trust?** This is the ask that matters, and it is where
the turns go. Target **3–8**. Fewer than three and the shared subgraph is whatever one paper
happened to cite; more than eight and the seeds stop agreeing on a subject.

Take DOIs where the PI has them. Where they name a paper instead, resolve it yourself and
read the title back for confirmation before it goes in the file — a wrong seed is invisible
in the output and poisons every rank.

**If the PI has no seeds at all**, propose five or six candidates by name from what you know
of the field, say plainly that these are your suggestions and not a search result, and let
the PI strike the ones that do not belong. Do not invent DOIs; resolve each accepted title
with `crux ingest raw/<file> --doi …` and let OpenAlex supply the identifier.

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

`## Out of scope` is for you to read later, going through the candidate list. The engine does
not filter on it.

## Writing is not approving

Writing the file is not permission to crawl. Hand the PI the line and let them run it:

```
crux lit crawl <slug>
```

A crawl with no scope file still works — it seeds from every `raw/` source carrying a work
id, which is right for a vault with one line of enquiry. The scope exists for the vault that
has more than one.

## Reading the list afterwards

`wiki/lit/<slug>/candidates.tsv` is complete and sorted, often some thousands of rows. Do not
truncate the file: it is the record of what the PI chose from, and re-crawling to recover it
costs the whole budget again. **Present the top 30** and offer to go deeper.

Read the columns, not just the rank. `seeds` is how many seeds reach the paper directly and
is the strongest signal; `hubs` is depth-two reach; `cites` is context, never the ranking. A
high-`cites` row low in the list is the ranking working — the field's furniture. Then hand the
PI the keepers, one `crux ingest raw/<file> --doi <doi>` line each.

## Guardrails

- **The PI curates `raw/`.** You propose; they dispose. Never ingest a candidate unasked.
- **Never invent a DOI or a work id.** Resolve it or ask. A fabricated identifier ingests
  cleanly and is wrong forever.
- **Never truncate `candidates.tsv`,** and never hand-edit it — it regenerates from the crawl.
- **The one-way flow rule still holds.** Everything here is literature. A scope file must
  never cite a `q*`/`h*` node, and a project finding never becomes a seed.
