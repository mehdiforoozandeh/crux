# AGENTS.md — repo orientation for coding agents

crux is four agent skills under [`skills/`](skills) — `crux`, `crux-wiki`, `crux-cockpit`,
`evolve-crux` — plus a stdlib-only Python engine at `skills/crux/scaffold/` (`engine.py`,
`crux.py`, `render.py`, `serve.py`, `webui/`). The root [`./crux`](crux) wrapper forwards
to the engine: `./crux --help` for the verb tour, `./crux selftest` to validate a checkout.

Contributing? The full workflow (ideate → build → validate → ship) is the
[`skills/evolve-crux/SKILL.md`](skills/evolve-crux/SKILL.md) playbook; follow it.

Hard rules, gated before every PR:

- **`./crux selftest` fully green**, and a behavior change adds asserts first
  (tests-first — the failing assert is the reproduction).
- **Stdlib only.** The engine takes no third-party dependency; the webui is no-build
  vanilla JS.
- **Existing vaults still load.** A vault-format or verdict/roll-up/view-logic change
  needs an `ENGINE_VERSION` bump in `engine.py` plus migration proof.
- **The cockpit (`crux serve`) is read-only** — no route ever writes.
- **Never hand-edit generated files** (`META.md`, `EXPERIMENTS.md`, `WIKI.md`, ledger
  blocks) — regenerate via the engine.
- **`skills/crux/SKILL.md` stays under 34,000 bytes** (`wc -c skills/crux/SKILL.md`). It
  loads on every crux session, and it grew 42% in five commits before anyone was counting.
  New material earns its place inline by one
  test: **if the agent never reads it, does it do the wrong thing — or does it visibly
  fail?** Content the engine itself refuses or validates may live in `references/` or
  `scaffold/README.md` behind a pointer, because the refusal is what sends the agent to go
  read it. Content only the agent can enforce — the leash, the voice rules, the migration
  guardrail, "never write `glossary.md` directly" — must be inline, however rare the path,
  because a missed read there is silent. Two riders: a prohibition stays inline even when its
  procedure moves out, and rare content whose trigger the agent would not notice needs a
  one-line tripwire left behind pointing at the reference. Repetition of a prohibition at
  each point of temptation is load-bearing, not bloat — do not dedupe it.
