# Contributing

crux ships its own contribution workflow as an agent skill:
[`skills/evolve-crux/SKILL.md`](skills/evolve-crux/SKILL.md) — **ideate** (a signed-off
PRD) → **build** (tests-first in `skills/crux/scaffold/selftest.py`) → **validate**
(selftest green · stdlib-only · existing vaults still load · version/migration) →
**ship** (a PR whose body is the PRD). Point your agent at it, or walk it by hand;
[`AGENTS.md`](AGENTS.md) has the repo layout and the hard rules.

Quick check before any PR: `./crux selftest` — fully green, your new asserts included.
