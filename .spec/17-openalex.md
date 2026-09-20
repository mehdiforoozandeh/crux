# Spec 17 — OpenAlex: the literature the wiki has not read yet

**Label:** `wiki` · **Status:** ◐ in progress
**Relates to:** [03 LLM wiki](03-llm-wiki.md) (the layer this feeds), [05 autopilot](05-autopilot.md)
(the setup-conversation shape reused by 17.3)

## Goal

Let a crux vault find the papers that should be in `raw/` and are not — by walking the
citation graph outward from sources the PI already trusts, and handing back a ranked
candidate list the PI ticks.

## Why the wiki needs this

[03](03-llm-wiki.md) makes the PI the sole curator of `raw/`, and that is correct: it is what
stops the wiki compiling whatever a keyword query dragged in. But it leaves the PI curating
from memory. The skill's own semantic-lint checklist admits the gap — *"a question the wiki
can't answer yet → suggest a source for the PI to add"* — and hands it to the agent, which is
the worst tool for it. An agent asked which paper is missing answers from training data.

The fix is not to relax the curation rule. It is to give the PI a **computed** list to curate
from. The citation graph is the right instrument because it is the literature's own record of
what matters, rather than a model's recollection of it.

## What OpenAlex is

An open index of ~250M works run by the non-profit OurResearch, successor to Microsoft
Academic Graph. Per work it carries: canonical title, full author list, year, venue,
open-access status and PDF url, assigned topics, `referenced_works` (what it cites) and
`cited_by_count`. The bulk snapshot is CC0.

Since 2026-02-13 the REST API needs a registered key and bills by credits. Measured against
the live API on 2026-09-19:

| | budget | what it buys |
|---|---|---|
| no key | $0.10/day | ~100 list requests — DOI lookups yes, a crawl no |
| free key | $1.00/day | ~10,000 credits; 50 works per list request |

A crawl that cannot finish inside the remaining budget **refuses before spending anything**
and prints the estimate. Half a candidate list looks complete and is not.

## The reframe that decides everything else

**Rank by seed-reach, not by citation count.** Ranking a candidate by `cited_by_count`
surfaces Adam, BWA and Nextflow — works cited universally, which is exactly why they carry no
information about *this* problem. The signal that means on-topic is **how many distinct seeds
reach the candidate**; dividing by its global citation count suppresses the universal classics,
because everything reaches them.

Everything else follows from that. The crawl exists to produce the reach counts. The seed set
is therefore the load-bearing input, which is why 17.3's conversation spends its turns
extracting 3–8 trusted papers rather than polishing a prose scope.

## What "the crawl" means here

Call it **the crawl**: building the citation subgraph around the seed set, then ranking it.
It is not web crawling — nothing is scraped, and no page is followed. It is repeated
structured queries against the OpenAlex API for two fields, `referenced_works` and `cites:`,
walked outward from the seeds and cached to disk.

This is the centre of the epic, not a side feature. 17.1 exists to make it possible; 17.3 and
17.4 exist to feed it and to consume its output. Every other slice is in service of producing
one ranked candidate list from one seed set.

## Direction is not symmetric

Backward (`referenced_works`) can only reach works **older** than the seeds. It builds
background, definitions and prior methods, and it structurally cannot find SOTA. Forward
(`cites:`) is the half that finds current baselines and what superseded a seed. Both run; each
candidate records which direction found it, because the two feed different wiki categories.

Depth 2 is the ceiling. At ~40 references per work, 5 seeds reach ~200 at depth 1, ~8,000 at
depth 2 and ~320,000 at depth 3. Cost is not what binds — 8,000 works is ~160 list requests,
comfortably inside a free key. What binds is that depth 3 dilutes the reach signal past the
point where the ranking means anything.

## Known blind spot

Snowballing finds what the trusted literature points at. A relevant paper in an adjacent field
that shares no citations with the seeds is unreachable by construction. Keyword or vector
search alongside is the mitigation; a deeper crawl is not.

## The flow rule holds

OpenAlex is literature metadata, so it sits on the legal side of [03](03-llm-wiki.md)'s
one-way rule. Two constraints keep it there:

- **OpenAlex never enters `raw/` as a source.** It is metadata *about* sources, including
  sources the vault does not have.
- **Citation counts are popularity, not evidence.** They may rank a candidate list. They may
  never become a claim on a wiki page; a page's claim still traces to a `raw/` file the PI
  curated and the agent read.

And the curation rule is untouched: OpenAlex proposes, the PI disposes.

## Hard constraints (PI-confirmed, 2026-09-19)

1. **Stdlib only.** `urllib.request`. No package, ever.
2. **Opt-in.** Every network call sits behind an explicit flag or verb. No existing command
   acquires a network dependency.
3. **Cached.** Every response is written to disk and re-read. A re-run is free and reproducible.
4. **Never blocking.** `crux validate` and `selftest` stay fully offline and green from a
   fresh clone with no key. "No OpenAlex at all" stays a first-class choice, not a degraded one.
5. **The key lives in `OPENALEX_API_KEY`**, never in the vault — a vault is a git repo.

## Slices

Build order differs from use order on purpose: 17.3's conversation is designed against a
scorer that already exists, rather than a guessed one.

| # | Slice | Ships |
|---|-------|-------|
| 17.1 | Client + DOI enrichment | `crux ingest --doi`, the cache, budget refusal, the offline fixture harness |
| 17.2 | Crawl + ranking | seeds → `candidates.tsv`, scored by seed-reach ÷ citation count |
| 17.3 | Scoping skill | the conversation that writes an approved scope file |
| 17.4 | Fetch + ingest | OA PDFs for ticked candidates into `raw/`, auto-ingested |

## Open questions

- Does `candidates.tsv` belong in the vault's git history, or under an ignored cache path?
- 17.4 fetches only open-access PDFs. What does the list do with a paywalled candidate the PI
  ticks — record the DOI and wait for the PI's own copy, or drop it?
