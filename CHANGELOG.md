# Changelog

All notable changes to crux are recorded here. Format follows
[Keep a Changelog](https://keepachangelog.com/); the engine version
(`ENGINE_VERSION` in `engine.py`) is bumped only when vault format or
verdict/roll-up/view logic changes.

## [Unreleased]

- **Engine JSON API (`engine.snapshot`).** New read-only `snapshot(vault) -> dict`
  — the single machine-readable view of a vault (`engine_version`, `project`,
  `nodes`, `tree`, `queue`), serialized as `/snapshot.json`. Pure-read, stdlib-only,
  additive (no vault-format change). Delivers ROADMAP Epic 1 #2 and is the data
  contract the GUI consumes. (`ledger_block` and `snapshot` now share one
  `ledger_counts` roll-up so their numbers cannot drift.)
