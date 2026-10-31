# Spec 19 — build plan

- **Spec:** [`.spec/19-background-memory.md`](../19-background-memory.md), branch `spec/19-background-memory`, commit 15a9c26.
- **Planner:** read-only pass on 2026-10-31. Nothing is implemented here.
- **Rule:** every chunk is tests-first. A chunk writes its red asserts, then makes them green.

## 1. Baseline

Each fact below was checked twice (grep, then a read of the code).

- **Selftest:** `./crux selftest` → `PASSED 1913 / 1913`, ALL GREEN. The count includes `selftest_auto.run_all` (`selftest.py:9614`).
- **SKILL.md:** `wc -c skills/crux/SKILL.md` → 36,401 bytes. The cap in `AGENTS.md:22` is 34,000. Spec 19 sets 8,192.
- **Engine:** `ENGINE_VERSION = "3.5"` (`engine.py:17`), `CRUX_VERSION = "0.9.0"` (`engine.py:89`).
- **Vaults for the proof** (read with a script, no write):

| Vault | Stamp | Q | H (done) | Verdicts | Synthesis | Experiment tasks |
|---|---|---|---|---|---|---|
| demo | 1.2 | 2 | 2 (2) | supported 1, partial 1 | 0 | 0 |
| scaling | 3.5 | 3 | 7 (5) | supported 2, refuted 2, partial 1 | 2 approved | 0 |
| segssl | 3.5 | 5 | 16 (14) | supported 4, refuted 5, partial 4, inconclusive 1 | 4 approved | 0 |
| sortlab | 3.5 | 35 | 108 (87) | supported 40, refuted 24, inconclusive 19, invalid-run 4 | 6 approved | 45 (38 accepted) |
| CANDII | 3.3 | 1 | 2 (0) | none | 0 | 0 (109 ordinary tasks) |

All demo, scaling and segssl hypotheses are schema 0 (pre-spec-15). All sortlab and CANDII hypotheses are schema 2.

### What the spec removes or changes, found in code

| Thing | Where | Spec 19 effect |
|---|---|---|
| Review gate (question → `review` when all children terminal) | `engine.py:1288-1298` (`refresh`), `cmd_review` `:4173`, `gate_warnings` `:4622`, `snapshot()["queue"]` `:4911`, `render.py:71-74`, `webui/app.js:847,1106` | Removed. |
| Verdict derivation | `derive_verdict_15` `:1041`, `derive_verdict` `:1136`, `cmd_close` `:4109` | Replaced by Findings plus a derived state. |
| Synthesis node type | `TYPES` `:197`, `cmd_synthesize` `:4315`, `cmd_approve` `:4250`, `approved_synthesis` `:4196`, `templates/synthesis.md`, `app.js:1314` | Removed; migrated to Findings. |
| `answer`, `pursue` | `cmd_answer` `:4269`, `cmd_pursue` `:4300`; CLI `crux.py:181,184` | Removed; print a pointer. |
| `approve`, `approve-null` | `crux.py:194,268`; `cmd_approve_null` `:4204` | Removed (`approve-null` is a spec gap, see Q7). |
| Run gates on `test` | `cmd_test` `:4084` refuses `running` on `neutral_gap/rule_gap/null_gap/scenario_gap` | Must go: null and verifiables are now optional. |
| Experiment-task accept gate | `cmd_task_review` `:3331`, `cmd_task_accept` `:3353`, CLI `crux.py:242,248` | Removed. |
| Autopilot close | `auto.py:435-461` `file_node`: hypothesize → approve-null → test → tick → close | Writes a Finding mechanically. |
| Agents | `agents/`: audit, close, critic, design, glossary, migrate, null, situate, tests, verifiables | Keep situate, migrate. Add capture, pre-run. Remove the rest. |
| Eval fixtures | `skills/crux/evals/fixtures/{audit,close,critic,design,glossary,null,verifiables,tests}-01` | Retire or re-target. |
| Hooks | `install.sh` registers only a `PostToolUse` voice hook (`engine.py:2266-2420`). No `SessionStart` hook exists anywhere (grep of `skills/`, `agents/`, `install.sh`). | Add a SessionStart hook. |
| Transcript reader | `transcript_turns` `engine.py:2298` reads Claude Code JSONL already. | Reuse for the sweep. |
| Id allocation | `_new_id` `engine.py:3925` has no file lock. | Risk with a background writer (R2). |

Two facts the spec does not mention: `find_vault` (`engine.py:552`) walks only UPWARD from the cwd, and `crux init` puts the vault at `./cruxvault`. CANDII's vault is at `CANDII/cruxvault`, so a hook at the repo root does not find it today.

## 2. Chunks

Integration branch: `build/19`, cut from `spec/19-background-memory`. Each chunk's worktree is cut from `build/19` at its merge point, never from `origin/main`.

**Shared-file rule.** `engine.py`, `crux.py` and `selftest.py` are shared. Ownership is by region and by order:
- `engine.py`: C1 owns all of it first. C6 owns the payload region (`brief`, `deck_payload`, `situate_brief`, `:5052-5550`) after C1 merges.
- `crux.py`: C1 (tree verbs) → C2 (load-time migration call) → C3 (sweep, wrap, hook verbs), in that order.
- `selftest.py`: new asserts go in NEW modules (`selftest_memory.py`, `selftest_migrate.py`, `selftest_capture.py`). C1 adds a loop in `main()` that runs every `selftest_*.py` module, so later chunks never edit `main()`. Each chunk owns the old `run_*` functions it breaks, listed per chunk, and retires or rewrites only those.

### C1 — Engine model 4.0

- **Goal:** Question / Hypothesis / Finding; derived state and confidence; null cap; parking; new and removed verbs; validate rules; `ENGINE_VERSION` 4.0; `SCHEMA_GENERATION` 3.
- **Owns:** `engine.py` (all, first pass), `crux.py` (tree verbs), `templates/{idea,question,finding}.md`, delete `templates/synthesis.md`, new `selftest_memory.py`. Old selftest functions it owns: `run_demo`, `run_close_gate`, `run_evidence_boundary`, `run_verifiable_kind`, `run_combination_rule`, `run_hash_lock`, `run_null`, `run_failure_scenarios`, `run_methodology`, `run_experiments`, `run_experiment_gate`, `run_taskhub`, `run_task_graph`, `run_integrity`, `run_version`, `run_snapshot`, `run_agent_cli`.
- **Red asserts first** (acceptance 1):
  - Derived states: no Finding → open; newest Finding weak or moderate → leaning; strong → settled; `parked: true` → parked whatever the Findings say.
  - Roll-up: a newer Finding overrides an older one; the order key is `created`, then id; a `no answer yet` Finding leaves the state open (Q3).
  - Question roll-up follows the rule chosen in Q2.
  - Null cap: a Finding written with `null: not-ruled-out` and confidence strong or moderate is stored as weak; `validate` flags a hand-edited violation.
  - `hypothesize` without `--expect` is refused for a new node; with `--expect` it writes `## Expect`; `## Null` and `## Verifiables` are optional.
  - `test --to running` no longer refuses on a missing null, rule or scenario.
  - `review`, `answer`, `pursue`, `approve`, `synthesize`, `task review`, `task accept` exit 0 and print exactly one pointer line; they write nothing (byte-compare the vault).
  - The engine never writes a direction or a confidence it was not given (no code path derives them) — except C4's autopilot function, which C4 tests.
  - `snapshot()` carries `state`, `confidence`, `findings[]` per Q/H, and no `queue`.
  - Concurrent `_new_id` calls from two processes never return the same id (R2).
- **Depends on:** spec gap answers Q1–Q8.
- **Done-check:** `python3 skills/crux/scaffold/selftest_memory.py` green; `./crux selftest` green except the functions C5–C8 own, listed in the PR.

### C2 — Migration 3.x → 4.0

- **Goal:** automatic migration with a backup, on the first write-capable load.
- **Owns:** new `scaffold/migrate4.py`, the call site in `check_and_stamp_version` (one line, after C1), `crux.py` `_vault()` message, `skills/crux/examples/*` (regenerated through the engine, never by hand), new `selftest_migrate.py`. Old selftest functions: `run_migrate`, `run_wiki_migration`, `run_economy_migration`, `run_rd_migration`, `run_methodology_migration`, `run_glossary_migration`, `run_sortlab_fixture`.
- **Red asserts first** (acceptance 1, 8):
  - One assert per row of the spec's migration table, plus the rows Q4–Q6 add (`partial`, refuted confidence, unaccepted experiments, open hypotheses).
  - A backup exists before the first byte changes, and it byte-equals the pre-migration tree.
  - Migration is idempotent: a second load changes nothing.
  - A crash mid-migration leaves the vault loadable from the backup (write to a temp tree, then swap).
  - `serve` on a 3.x vault writes nothing (Q9).
  - The migration is a pure function `plan(vault) → changes` plus `apply`, so the cockpit can use `plan` read-only.
- **Depends on:** C1.
- **Done-check:** a script copies the four example vaults and CANDII (`cp -R` into a scratch dir; the CANDII source is never opened for write), runs `crux validate` on each copy, and prints per-vault counts of migrated Findings by direction and confidence. The reviewer compares the counts with the table in section 1.

### C3 — Capture plumbing and hooks

- **Goal:** SessionStart hook (core injection + catch-up sweep), sweep mark, pending list, `crux wrap --json`.
- **Owns:** new `scaffold/sweep.py`, `crux.py` (`hook session-start`, `sweep`, `pending`, `wrap` verbs; after C2), `install.sh`, new `selftest_capture.py`. Old selftest function: `run_voice_enforcement` (only where it reads the hook list).
- **Red asserts first** (acceptance 1, 3, 7):
  - Sweep mark: per-transcript offset is stored; a second sweep with no new bytes starts nothing; new bytes start exactly one run.
  - The hook output for a cwd with a vault (at cwd, an ancestor, or one level down such as `./cruxvault`) carries the core text as `additionalContext`; for a cwd without a vault it is empty and exits 0.
  - The hook never fires a sweep when `CRUX_SWEEP=1` is in the environment (no recursion, R3), and it skips transcripts that a capture run wrote.
  - The transcript text handed to the capture run is truncated to the hard cap.
  - `wrap --json` lists the records this session wrote, read from the session's own crux tool calls, plus the pending list.
  - `install.sh` is idempotent for the new hook, keeps unrelated settings keys, and removes dangling `~/.claude/agents/crux-*.md` links for removed agents.
  - The hook exits 0 and is silent on any internal error.
- **Depends on:** C1 (verbs the capture run calls), C2 (crux.py order). Can be built in parallel with C2 and merged after it.
- **Done-check:** `SKILLS_DIR=$tmp AGENTS_DIR=$tmp2 HOME=$tmp3 ./install.sh` twice, then `jq .hooks.SessionStart $tmp3/.claude/settings.json` shows one entry; `selftest_capture.py` green.

### C4 — Autopilot Findings

- **Goal:** each attempt gets one Finding: bar met → supports, else against; strong when the margin exceeds the noise (Q10), else moderate. No model call.
- **Owns:** `auto.py`, `selftest_auto.py`.
- **Red asserts first:** kept-and-better → supports; kept-and-not-better → against; rejected or failed → `no answer yet` with the log as evidence; margin above noise → strong, at or below → moderate; no `approve_null` or `cmd_close` call remains (`grep`).
- **Depends on:** C1.
- **Done-check:** `python3 skills/crux/scaffold/selftest_auto.py` (through `./crux selftest`) green; `./crux auto status` on the stub run shows Findings.

### C5 — Cockpit and generated views

- **Goal:** render state and confidence; list Findings; remove the review queue, synthesis detail and acceptance badges. Read-only stays.
- **Owns:** `render.py`, `serve.py`, `webui/*`. Old selftest functions: `run_serve`, `run_file_route`, `run_webui`, `run_cockpit_evidence`, `run_task_gui`, `run_wiki_gui`, `run_rd_gui`.
- **Red asserts first** (acceptance 9): `META.md` and `EXPERIMENTS.md` show state and confidence columns and no `review` section; `app.js` has a class per state and per confidence and no `review-btn`; every serve route answers GET only, and a full click-through writes no byte (existing byte-map test, re-pointed).
- **Depends on:** C1 (snapshot shape). Parallel with C2–C4.
- **Done-check:** `./crux serve --dir <migrated sortlab copy> --no-open`, then load the page in the browser pane; a settled, a leaning, an open and a parked node each render; selftest green for owned functions.

### C6 — Payload readers

- **Goal:** `brief`, `deck_payload`, `situate_brief` read Findings, state and confidence instead of verdict and synthesis. Rename only (spec: out of scope beyond renames).
- **Owns:** `engine.py` payload region (after C1 merges), `skills/prezit/`, `skills/storify/`. Old selftest functions: `run_brief`, `run_deck`, `run_deck_verify`, `run_prezit`, `run_prezit_paper`, `run_storify_engine`, `run_storify_skill`, `run_deck_rd`, `run_situate`, `run_situate_title_anchor`.
- **Red asserts first:** each payload carries `findings[]` with direction, confidence, why and evidence; no payload carries `verdict` or `synthesis`; `crux deck --verify` and `crux story --verify` still pass on the migrated scaling vault.
- **Depends on:** C1, C2 (migrated fixtures).
- **Done-check:** `./crux deck q1 --json` and `./crux brief q1 --mode=situate --json` on the migrated scaling copy; owned selftest green.

### C7 — Agents and evals

- **Goal:** add `crux-capture` and `crux-prerun`; keep `crux-situate`, `crux-migrate` (re-pointed to the new seed shape); remove close, critic, audit, glossary, design, null, verifiables; move `crux-tests` (Q12).
- **Owns:** `agents/*`, `evals.py`, `skills/crux/evals/*`, `_doctor_agents` roster expectations (a two-line edit in `engine.py`, sequenced after C6). Old selftest functions: `run_agent_roster`, `run_situate_agent`, `run_design_agent`, `run_agent_evals`, `run_eval_scorer`, `run_mutation_harness`, `run_ground_truth_fixtures`, `run_proxy_register`, `run_persona_eval`, `run_doctor`.
- **Red asserts first:** the roster is exactly {capture, prerun, situate, migrate}; each AGENT.md names its trigger; `crux-capture` may call only crux verbs and never asks the PI; `crux-prerun` drafts expectation, null and checks and states which outcome would change the confidence; a new `capture-01` fixture (a fixed transcript plus a manifest of the nodes it must yield) certifies against the engine.
- **Depends on:** C1, C3 (capture brief shape).
- **Done-check:** `python3 skills/crux/scaffold/evals.py --certify-all` green; `./crux doctor` on a fresh install reports no dangling agent.

### C8 — Skill text

- **Goal:** `skills/crux/SKILL.md` becomes the always-on core, ≤ 8,192 bytes, with the five parts the spec lists. Everything else moves to `references/` or a specialist skill behind a pointer. New `skills/crux-wrap/SKILL.md` (the `/crux-wrap` command).
- **Owns:** `skills/crux/SKILL.md`, `skills/crux/references/*`, `skills/crux-wrap/`, `skills/crux-autopilot/`, `skills/crux-cockpit/`, `skills/crux-wiki/`, `skills/crux-litsearch/`, `skills/crux-rd/`, `skills/evolve-crux/`, `AGENTS.md`. Old selftest functions: `run_rulebook`, `run_taskhub_skill`, `run_rd_skill`, `run_science_voice`, `run_correct_terms`, `run_cli_third_person`, `run_cli_help`.
- **Red asserts first** (acceptance 1, 2, 6): `len(SKILL.md bytes) <= 8192`; the core contains the voice section, the tree/taskhub boundary, the closure-judgment rule, and one router line per skill and agent named in the spec; every `references/*.md` pointer in the core resolves; no removed verb appears in any SKILL.md except as "removed"; `crux-wrap` SKILL.md says it shows records first and asks only about pending candidates.
- **Depends on:** C1–C7 (final verb and agent names).
- **Done-check:** `wc -c skills/crux/SKILL.md` ≤ 8192; `./crux selftest` fully green.

### C9 — Integration and release

- **Goal:** the live acceptance checks, the five-vault proof, the version bump, release notes.
- **Owns:** `CRUX_VERSION` → 1.0.0 (one line in `engine.py`), `README.md`, `INSTALL.md`, `.spec/README.md`, `skills/crux/examples/README.md`, the PR body.
- **Checks:** acceptance 3–7 run live, attended, in fresh Claude Code sessions in a scratch repo with a vault; each run's transcript and the resulting nodes are attached to the PR. Acceptance 8 re-runs C2's proof script on `build/19` HEAD.
- **Depends on:** C1–C8.
- **Done-check:** `./crux selftest` fully green; the count is reported next to 1913 with the list of retired asserts (Q13); proof script output attached.

## 3. Merge order and integration

1. C1 → `build/19`. Run full `./crux selftest`; record which old functions are red (only those C5–C8 own may be red).
2. C2, C4, C5 build in parallel. Merge order: C2, then C4, then C5. Full selftest after each.
3. C3 builds in parallel with C2; merges after C2.
4. C6 after C2. C7 after C3 and C6.
5. C8 last of the builds. After C8, `./crux selftest` must be fully green.
6. C9 on `build/19` HEAD; then one PR `build/19` → `main`.

Merge `build/19` into each open chunk branch after every merge (merge, not rebase). The integration tests run on `build/19` after each merge; the live checks run only in C9.

## 4. Spec gaps — questions with a recommendation

Questions marked **(science)** change what the record says. The PI must answer them; the plan does not decide them.

- **Q1. Where does a Finding live?** Recommend: its own file, `type: finding`, id `f<n>`, `parent:` a Question or Hypothesis, frontmatter `direction`, `confidence`, `why`, `evidence` (list), and for a Hypothesis `vs_expect`, `null` (`ruled-out | not-ruled-out | none`), `verifiables`. The cockpit lists Findings in the node pane, not as tree nodes. Keep `type: idea` on disk and say "hypothesis" in all text, to avoid a rename of every file.
- **Q2. (science) Question roll-up.** The spec says "a node's state and confidence come from its Findings", but a Question can also have child Hypotheses. Recommend: the newest direct Finding on the Question decides. With no direct Finding, the Question takes the newest Finding among its child Hypotheses, capped at moderate (leaning), because a settled hypothesis does not by itself answer the question. Sub-questions do not roll up.
- **Q3. (science) "Newest counts most" vs "later overrides".** Recommend: newest-wins, by `created` then id. No weighting. A `no answer yet` Finding is recorded but does not change the state from the previous Finding (or from open).
- **Q4. (science) Migration confidence for `refuted`.** The table defines confidence only for supported. Recommend the mirror: every claim-directed check failed → strong; any passed → moderate. For supported with two or more missed (possible under `any` or `m-of-n`): weak.
- **Q5. (science) Rows the table omits.** `partial` (10 nodes in demo, scaling, segssl): recommend mixed, weak. A hypothesis not closed (idea, staged, running): no Finding, state open. A drifted lock (`lock_drift`): recommend confidence capped at moderate, with the drift named in `why`. A seeded `reconstructed` lock: no cap.
- **Q6. (science) Synthesis and task conclusions.** A synthesis has no direction. Recommend: an approved synthesis becomes a Finding on its Question with confidence strong (the PI signed it, so the question stays settled), direction `mixed`, `why` = its first headline sentence, and a pending item asking the agent to set the direction at the next `/crux-wrap`. An unapproved synthesis becomes a pending item only. For experiment tasks (sortlab: 45, 38 accepted): accepted → a Finding with the conclusion mapped like a verdict and confidence moderate; unaccepted → pending; dropped → nothing. When a task Finding is newer than the node's verdict Finding and disagrees, the migration report lists it.
- **Q7. Fate of the remaining spec-15 verbs.** Recommend: `close` prints a pointer to the new `crux finding` verb, which takes the aliases `record`, `conclude`, `land`; `approve-null` prints a pointer (the null is no longer PI-approved); `test` records run links and takes the lock, with no refusal; the lock and drift stay as a flag that the closure judgment reads. `glossary` and `voice` engine verbs stay (the voice lint reads the glossary); only the glossary agent goes.
- **Q8. What does `validate` check now?** Recommend: drop the rule, neutral, null and scenario gaps and `gate_warnings`; drop `--check=gate`. Add: a new hypothesis without `## Expect` is a problem (a migrated one is `info`); Finding enums are valid; a Finding's parent is a Q or H; evidence links resolve under `results/` or `tasks/`; no Finding breaks the null cap; `parked` only on Q or H.
- **Q9. Cockpit on an old vault.** The cockpit cannot write, so it cannot migrate. Recommend: `serve` renders the migration plan in memory (C2's pure `plan`) with a banner "not migrated yet"; any write verb migrates.
- **Q10. (science) Autopilot noise.** The spec says "strong when the margin exceeds the scorer's noise", but no noise number exists: `auto.py` has only `min_gain` and one baseline score (`setup_check`, `:497`). Recommend: a new optional plan field `noise`; when absent, use `min_gain`; when both are absent, every supporting attempt is moderate.
- **Q11. Sweep storage and the capture run.** Recommend: sweep marks and the pending list live in `<vault>/.crux/` (a new, git-ignored folder: transcript paths are machine-local). The hook spawns one detached `claude -p` with a small model, `--allowedTools` limited to crux verbs, a turn cap, and `CRUX_SWEEP=1`; the engine enforces the token cap by truncating the input. Sweep runs on `source: startup` and `clear`, not on `resume` or `compact`.
- **Q12. Where does `crux-tests` go?** Recommend: `skills/evolve-crux/agents/crux-tests.md`, installed by `install.sh` from that path, and removed from the crux router and doctor roster.
- **Q13. Selftest count.** The evolve-crux gate says the count must grow (`evolve-crux/SKILL.md:116`). Removing four gates will retire asserts. Recommend: allow a lower total for this release, with a list of the retired asserts in the PR.
- **Q14. Hypothesis stored status.** `idea/staged/running/done` duplicates the derived state and the taskhub. Recommend: stop reading `status` for Q and H; migration keeps the field as history; "is it running" comes from an open taskhub task that links the node.
- **Q15. How does `/crux-wrap` know "this session's records"?** Recommend: from the session transcript's own crux tool calls (deterministic, no new frontmatter), not from a session id on each node.

## 5. Risks

- **R1. Migration changes recorded science.** It turns verdicts into confidence by rule. Mitigation: a backup first, a per-vault report of every Finding written, and the PI answers Q4–Q6 before C2 starts.
- **R2. Concurrent writers.** The capture run, autopilot and the main agent can write at once; `_new_id` has no lock. Mitigation: a stdlib lock file (`os.open(..., O_CREAT|O_EXCL)`) around id allocation and node writes, in C1.
- **R3. Hook recursion and self-capture.** A `claude -p` run started by the hook fires its own SessionStart, and its transcript lands in the same projects folder. Mitigation: the `CRUX_SWEEP=1` guard and a list of capture-run transcripts in the sweep mark.
- **R4. Vault discovery.** `find_vault` only walks upward; most vaults sit at `./cruxvault`. Mitigation: the hook also checks one level down.
- **R5. Cost and permissions of the background run.** It uses the PI's own plan and needs Bash permission for crux verbs. A missing `claude` binary or auth must be silent, never a broken session.
- **R6. Context budget.** Claude Code caps hook context output; 8,192 bytes is under the cap as far as known, but C3 must test the real limit in C9's live run.
- **R7. Silent ideation fills the tree.** The spec accepts this (open question 1). Parking is the only control.
- **R8. Large shared files.** `engine.py` (6,217 lines) and `selftest.py` (9,633 lines) are edited by several chunks. The region rules in section 2 and merge-not-rebase keep conflicts small.
- **R9. Live acceptance (3–7) is not in selftest.** It needs a model. It is checked once, by hand, in C9; a regression after release is not caught automatically.

**ELI5:** This plan splits a big rewrite of the research notebook into nine small jobs, says which files each job may touch, and lists the questions the owner must answer first.

**TL;DR:** The build is nine chunks: the engine model (C1) first, then migration (C2), capture hooks (C3), autopilot (C4), cockpit (C5), payloads (C6), agents (C7), skill text (C8) and release (C9). Baseline is 1,913 green asserts and a 36,401-byte SKILL.md. The spec leaves the roll-up rule, several migration rows, synthesis direction and autopilot noise undefined; Q2–Q6 and Q10 change what the record says, so the PI must answer them before C1 and C2 start.

## PI rulings (2026-10-31)

- **Mechanical questions Q1, Q7–Q9, Q11–Q15:** the planner's recommendations above are accepted as written.
- **Q3 — which Finding counts:** the strongest Finding sets a node's state and confidence; the newest breaks ties. "No answer yet" Findings are recorded but never set the state.
- **Q2 — Question roll-up:** the question's own Findings decide (strongest wins). With none, the strongest Finding among its child hypotheses counts, capped at moderate (leaning). Sub-questions do not count.
- **Question Findings (new):** a Finding on a Question carries the answer text, a confidence and evidence links, and **no direction**. Direction (supports · against · mixed · no answer yet) applies to Hypothesis Findings only.
- **Q4 — migrated confidence:** agreement count. Supported: all claim checks pass → strong; one missed → moderate; two or more → weak. Refuted mirrors it: all fail → strong against; any pass → moderate. A failed control, or a null not ruled out, caps at weak.
- **Q5 — missing rows:** `partial` → mixed, weak. A never-closed hypothesis → no Finding, state open. Checks edited after the run started → confidence capped at moderate, the edit named in the reason.
- **Q6 — syntheses:** an approved synthesis → a strong Question Finding with its text kept; an unapproved one → a pending `/crux-wrap` candidate.
- **Q6 — experiment tasks:** accepted conclusion → a moderate Finding on its hypothesis, linked to the task output; unaccepted → pending candidate; dropped → nothing. The migration report lists every disagreement with the hypothesis's own verdict.
- **Q10 — autopilot noise:** `crux auto check` scores the baseline 3 times and records the spread as `noise`. Strong when the gain beats the bar by more than `noise`, else moderate. When the spread is zero (a deterministic scorer), `min_gain` is used instead, and its default for a deterministic scorer is near zero (any marginal gain counts).

## Log

- 2026-10-31 W1: C1 spawned [opus] in /Users/mforooz/.orchestrate-wt/crux/C1 (chunk/C1 from build/19@647ae37). Brief applies PI rulings over plan text (strongest-wins, question Findings without direction).
- C1 slip 1: partial, 03e8d0d, selftest 1350/1397, memory 157/157. Unowned red fns (run_seed, run_wiki, run_artifacts, run_economy, run_rd, run_rd_lint, run_glossary_*; helpers _task_vault, pre15_vault, declare_null) assigned to C1. Retry 1 (resumed same agent). Diff 3.2k lines -> reviewer needed before merge.
- C1 slip 2: done, 8d74786, selftest 1570/1604 (all red owned by C2-C8). Reviewer [opus]: send back, deleted kept asserts (null/scenarios reach brief+deck, evmig pre-15, nested-experiment info). Retry 2 + remove dead null_gap. Diffs read via reviewer: 3.2k lines.
- C1 slip 3: done, 7f7529c, selftest 1578/1611 (red = C2-C8 owned). Retry diff 52 lines, read in full. ACCEPT, merged into build/19 (fast-forward). C1 retries: 2.
- W2: C2, C3, C4, C5 spawned [opus], worktrees from build/19@7f7529c. C3 merges after C2 (crux.py order).
- C3 slip: done, bd31c88, capture 55/55, selftest 1633/1666 (same 33 red). Pending format: JSONL <vault>/.crux/pending {kind,parent,text,source}; hook = crux.py hook session-start; capture brief agents/crux-capture/AGENT.md (C7). Waits for C2 merge.
- C3 review [opus]: send back. (1) claude -p only --allowedTools, not --tools: PI allow-rules leak into sweep. (2) vacuous allowlist assert. Added: first-sight mark = EOF (no history sweep), pending lock. Retry 1.
- C4 slip: done, 6069373, auto 87/87, selftest 1638/1670 no new red. Open (science, to PI): clearly-worse attempt -> strong against? Built moderate. Mechanical: text `auto status` should print finding/confidence (crux.py) -> assign after C3 merges.
- PI ruling: autopilot confidence symmetric (worse beyond noise = strong against). C4 review [opus]: send back, float tie at margin==noise. C4 retry 1 sent (+ symmetric, + pre-C4 ledger = unknown noise -> cap moderate).
- C3 retry slip: done f8b39e8, capture 61/61. Accept pending small-diff read; merge after C2.
- C5 slip: done 5ea96c9, selftest 1697/1726, owned green. Reviewer [opus] spawned.
- C2 slip: done 67f115a, migrate 104/104, 5-vault proof ok. PI ruling: null cap applies to supports only (engine changed to match, assigned to C2). C2 retry 1 sent (+ re-point run_evidence_boundary/run_doctor/run_glossary_oracle, pending file name + lock per C3).
- C5 review [opus]: ACCEPT. Merged into build/19. Follow-ups: C5b after C2 merge = serve renders migrate4.plan() in memory under banner (Q9); stale "pre-15" chip text app.js:2815,2995 -> fold into C5b.
- C2 retry slip: done dfa71ed, migrate 106/106, selftest 1736/1762 no new red, proof unchanged. Reviewer [opus] spawned (rules spot-check on sortlab).
- C4 retry slip: done c650c2e, auto 92/92 (4640 decimal ties, 0 wrong), no new red. ACCEPT, merged. C4 retries: 1.
- C2 review [opus]: ACCEPT (rules spot-checked h2/h10/h9). Merged C2 then C3 (no conflicts). build/19 selftest 1979/2002; red: C6 (deck*, brief, situate*), C7 (agent_*, ground_truth, proxy_register), C8 (science_voice, correct_terms), run_voice_enforcement (C3-owned, still red -> C2b).
- Follow-ups: C5b (serve in-memory migrate plan Q9 + stale pre-15 chip text) wave 3; C2b wave 4 (crux.py --null help supports-only, text auto status finding/confidence, id_lock stale-break vs long migration, run_voice_enforcement). Failed-control cap stays all-direction (literal ruling; only null cap narrowed).
- W3: C6, C7 (no engine.py edits; report doctor-roster lines on slip), C5b.
- C5b slip: done cfc581d, run_serve green, 1993/2016 no new red. Diff 146 lines read (serve.py preview: pure, thread+5s timeout, no writes). ACCEPT, merged.
- C6 slip: partial d1f1a18, 2141/2158; one red in run_brief needs crux.py:915 one-line (pf verdict -> state/confidence). Approved, retry 1.
- C6 retry slip: done 63848af, 2142/2158, owned green. Reviewer [opus] spawned. Note: "evmig" + sortlab red at baseline -> C2b to own.
- C6 review [opus]: send back (crux.py:915 why from newest not deciding Finding; answer-slide rule inconsistent -> settled; deck.html direction prompt on question answer). Retry 2.
- C6 retry 2 slip: done 8244b1e, 2143/2159, review defects fixed. ACCEPT, merged. C6 retries: 2.
- W3b: C2b spawned [opus] from build/19@d9c0ce6 (2157/2173): --null help, text auto status, id_lock live-holder, orphan red asserts (evmig, sortlab x2, voice_enforcement, task-verb help).
- C7 slip: partial f6b668e (base e63a1e3), certify 5/6 (situate-01: NameError fixed by C6 on build/19). Retry 1: merge build/19, prerun-01 facts -> shared record (isolation is from the argument, not the setup). install.sh evolve-crux agents link -> C2b. persona-01 rows + SKILL.md pin -> C8.
- C7 retry slip: done 10e300a (merged build/19), certify 6/6, 2213/2220, owned 205/205. Reviewer [opus] spawned, focus crux-capture AGENT.md fidelity.
- C7 review [opus]: send back (prerun toolbelt leaks status; expect missing from isolated brief -> add to engine.brief, granted to C7; migrate null-cap wording; capture strong with no null; pending --source wrap). Retry 2.
- C2b slip: done e3b23bd, 2191/2202 stable, no new red; all 5 targets green; example views regenerated via E.refresh; foreign-host lock stale after 3600 s (accepted). Lock code read by foreman; reviewer [opus] spawned (diff 760 lines).
- C7 retry 2 slip: done 11d678a, certify 6/6, owned 207/207, review defects fixed. ACCEPT, merged. C7 retries: 2. For C8: /crux-wrap must tell capture to pass --source wrap; persona-01 rows + pin.
- W4: C8 spawned [opus] from build/19@11d678a (core <=8192 B, crux-wrap skill, other skills, AGENTS.md cap, persona-01 re-pin). C2b in review.
- C2b review [opus]: send back (lock break race A-removes-B, pre-existing; OverflowError in _pid_alive). Retry 1. Note: PI machine ~/.claude/agents has 8 dangling crux-* links -> reinstall cleans (tell PI at release). selftest.py:5400 accept-in-verb-table -> C8.
- Foreman: main checkout /Users/mforooz/crux switched back to main (the PI's live skills/agents symlink into it; build/19 had removed 7 agents from their env). Integration now in /Users/mforooz/.orchestrate-wt/crux/integ (build/19). Plan file authority: integ copy.
- C2b retry slip: done 09c021d, memory 169/169, no new red; race fixed via atomic rename + link-back. ACCEPT (os.link-unsupported edge left, residual documented). Merged. C2b retries: 1.
- C8 slip: done ecd0353, SKILL.md 7,265 B, certify 6/6, 2262/2267. Retry 1: merge build/19 (C2b), own run_voice_enforcement section A (3.x legend -> 4.0 voice asserts).
- C8 retry slip: done 7d4f67a, SKILL.md 7,265 B, certify 6/6, selftest 2302/2302 ALL GREEN. Foreman read core + crux-wrap in full: faithful to rulings. ACCEPT, merged. C8 retries: 1.
- W5: C9 spawned [opus] from build/19@7d4f67a: 1.0.0 bump, docs, CHANGELOG, PR body, proof re-run, live checks 3-7 via claude -p haiku with --settings (no real config touched).
- C9 slip: partial 7ad6de4, 2302/2302, proof 5/5 ok, live model checks blocked (CLI OAuth expired). Found: (i) sweep launches capture at repo root -> crux verbs fail for ./cruxvault, background capture writes nothing; (ii) register_session outside lock; (iii) decision 10 AGENTS.md pointer via crux init not built. Merged C9 (docs/version). Verify round 1: C10 fixes (i)-(iii).
- C10 slip: done 5ec0526, selftest 2314/2314 ALL GREEN. CRUX_VAULT env fallback in find_vault; update_marks under id_lock for all 4 marks writers; crux init writes AGENTS.md pointer (idempotent). Diff 254 lines, engine part read. ACCEPT, merged. Remaining: live model checks 3-5 blocked on PI auth.
