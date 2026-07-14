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
