# Changelog

All notable changes to crux. Format loosely follows Keep a Changelog; the engine
version (`ENGINE_VERSION`, stamped into every vault) bumps when the vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

- **Literature wiki (Epic 3).** A PI-curated literature layer alongside the question/
  hypothesis tree, instantiating Karpathy's LLM-wiki pattern on crux. Immutable sources
  under `raw/`, agent-compiled pages under `wiki/`, a new `crux ingest` verb (records
  source sha256, appends a greppable `wiki/log.md` line), an engine-generated `WIKI.md`
  index, and structural wiki lint folded into `crux validate` (broken/flow links, orphans,
  missing frontmatter, uncompiled/missing sources, source hash drift). Knowledge flows one
  way — literature → wiki → tree; findings never enter the wiki. New sibling skill
  **crux-wiki** carries the agent-side conventions (compile / query / semantic lint).
  Engine bumped to 1.1; pre-wiki vaults load unchanged and stand up the wiki lazily on
  first ingest.
