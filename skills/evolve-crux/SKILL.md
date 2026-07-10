---
name: evolve-crux
description: >-
  Evolve crux itself — add a capability or fix a recurring flaw in the crux tool,
  end to end: ideate → build → validate → ship. Turns a feature idea or a "crux keeps
  doing X" annoyance into a signed-off PRD, a tests-first implementation, a hard
  validation gate (selftest green · stdlib-only · existing vaults still load ·
  version/migration), and a pull request. Works for anyone contributing to crux, not
  just the maintainer; the maintainer self-merges and cuts releases. Use when working
  ON crux — adding to the engine/CLI/skill, picking up a ROADMAP epic (UI, wiki,
  marketing), or fixing an engine bug. Triggers: "evolve crux", "add a feature to crux",
  "crux keeps <doing X>", "improve crux", "contribute to crux", "send a crux PR",
  crux roadmap, wiki/GUI/autoresearch for crux.
license: MIT
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  notice: "Playbook for evolving the crux tool; no third-party code."
---

# evolve-crux — ship a change to crux, rigorously

This skill is for working **on crux the tool** (the repo at `~/crux`), not on a research
project that *uses* crux. It carries one change — a new capability or a fix for something
crux keeps getting wrong — through a strictly gated arc:

```
ideate → build → validate → ship
```

Each stage has an **exit criterion**; you do not advance until it's met. The arc is the
same whether the change is a one-line bug fix or a ROADMAP epic — only the ceremony scales.

## Who's driving (contributor-always)

Assume **the person evolving crux is not the maintainer.** Because crux ships this skill
to its users, everyone runs the *same* path and **ends at a pull request** — no
auto-detection of who you are, no privileged branch. The maintainer is just the
contributor who can **self-merge** their own PR, plus a small, separate **release** step
(below). This keeps one code path and makes third-party PRs first-class.

Work in a dedicated session **inside `~/crux`** (a fresh chat, not the project you were
researching). For a large build you may dispatch a worktree sub-agent, but the default is
the main thread.

---

## 1 · Ideate → a signed-off PRD  ◆

Ideation ends when there is a **PRD** the human has approved — not before any code. Reach
it by a **pingpong / grill-me back-and-forth** (surface one decision at a time; don't dump
options): what exactly are we adding or fixing, why, the design choice, and — load-bearing
— the **acceptance criteria** (the concrete checks that later *become* the validation
gate). Pre-registering "how we'll know it worked" is what makes `validate` enforceable
instead of vibes.

**The PRD scales to the change:**
- **Bug** ("crux keeps mis-splitting inline parens") → a one-line PRD: the wrong behavior,
  the correct behavior, and the acceptance criterion = *a failing selftest that asserts the
  correct behavior*.
- **Feature / ROADMAP epic** (UI, wiki, autoresearch) → a full grilled PRD (skeleton below).

Feature ideas frequently come from `ROADMAP.md`; if the change advances an epic, say so and
flip that item's status when it lands.

**PRD skeleton** (Markdown; the exact text becomes the PR body):

```markdown
# PRD: <short title>
- **Kind:** feature | fix | refactor        - **Roadmap:** <epic, or —>
- **Problem / motivation:** what's missing or wrong, and why it matters.
- **Design decision:** the approach chosen (and the main one rejected + why).
- **Scope:** what this change does *not* do.
- **Acceptance criteria:**
  - [ ] <criterion → a selftest assert>          # automatable
  - [ ] <criterion → manual check>  (manual: …)   # un-automatable (GUI, Obsidian render)
- **Backward-compat / migration:** does this change vault format? (if yes → §3 gate 4)
```

**Exit criterion:** the human has read and approved the PRD as one block.

---

## 2 · Build — tests-first  ◆→○

The moment the PRD is signed off, translate its acceptance criteria into the harness crux
already has:

1. **Write the asserts first (red).** Add new cases to `skills/crux/scaffold/selftest.py` — one
   per automatable acceptance criterion — and run `python skills/crux/scaffold/selftest.py`; the
   new ones should **fail**. (For a bug, this failing test *is* the reproduction.)
2. **Implement to green.** Edit `skills/crux/scaffold/` (`engine.py` / `crux.py` / `render.py` /
   `templates/`) until selftest is fully green — new asserts included, none regressed.
3. **Un-automatable criteria** (a GUI looking right, Obsidian rendering) stay as a **manual
   checklist** carried in the PRD; you'll walk them by hand in `validate`.

**Hard constraint — stdlib-only.** The engine takes **no third-party dependency.** If a
criterion seems to need one, that's a design problem to raise, not a dep to add.

**Exit criterion:** selftest green with the new asserts, and code matches the PRD's design
decision (not a different one you drifted into).

---

## 3 · Validate — the gate  ○

A fixed gate; **all four must pass before ship.** Nothing here is judgment — it's a checklist.

1. **Selftest green.** `python skills/crux/scaffold/selftest.py` → all pass, and the count has *grown*
   by your new asserts (a feature that added no assert didn't really register its criteria).
2. **Stdlib-only.** Grep the diff for imports; fail on any module outside the Python stdlib.
   `git diff -U0 -- skills/crux/scaffold | grep -E '^\+\s*(import|from) ' | grep -vE '<stdlib names>'`
3. **Existing vaults still load.** Run the engine's read paths — `status`, `review`,
   `validate`, and a render — against a vault **copy** and confirm nothing breaks:
   - if a **real vault is discoverable** (e.g. a `cruxvault/` in a nearby project), copy it
     to a scratch dir and validate against the copy — never mutate the original;
   - **otherwise** fall back to the committed synthetic fixture **`skills/crux/examples/demo_vault/`**
     (copy it out first). This synthetic vault is the *default* gate — it ships in the repo,
     so every contributor can run it; the real-vault check is an optional local upgrade.
4. **Version / migration.** *Only if the change alters vault format or verdict/roll-up/view
   logic:* bump `ENGINE_VERSION` in `engine.py`, **and** prove an **old-format** vault
   migrates or still reads cleanly (the drift warning from `check_and_stamp_version` is
   expected; a crash or wrong verdict is a fail). If format is unchanged, leave
   `ENGINE_VERSION` alone and note "no migration."

Then walk any **manual** acceptance criteria from the PRD and tick them.

**Exit criterion:** all four gates pass + every PRD acceptance criterion is ticked. If any
fails, go back — do **not** proceed to ship.

---

## 4 · Ship — open a PR  ◆

Ship happens **only after §3 fully passes.** For everyone, ship ends at a **green pull
request** whose body **is the PRD**:

1. Add an **Unreleased** entry to `CHANGELOG.md` (create it if absent): one line under
   `## [Unreleased]` describing the change. Contributors do **not** bump the version or tag.
2. Branch, commit, push to a fork, open the PR:
   ```bash
   gh repo fork mehdiforoozandeh/crux --remote      # first time only; skip if you have push
   git switch -c evolve/<slug>
   git add -A && git commit -m "<kind>: <short title>"
   git push -u origin evolve/<slug>
   gh pr create --title "<kind>: <short title>" --body-file <the PRD>.md
   ```
3. The PR self-documents: reviewer checks the diff against the PRD's pre-registered
   acceptance criteria and the green selftest — not reverse-engineered intent.

**Exit criterion:** a PR is open, selftest green in it, PRD as the body.

### Maintainer-only: self-merge + cut a release

The maintainer runs the **identical** arc, then:
- **Self-merge** their own PR once the gate is green (they may push/merge to `main`).
- **Cut a release** as a *separate, occasional* action — decoupled from any single feature,
  not once per PR: roll the accumulated `## [Unreleased]` CHANGELOG entries into a version
  section, `git tag vX.Y.Z`, push tags. Because `/crux` is installed as a **symlink** to
  `~/crux`, merging already updates the live skill — no reinstall.

---

## Guardrails

- **The gate is non-negotiable.** No shipping on an un-green selftest, a new dependency, a
  broken existing vault, or a format change without a version bump + migration proof.
- **Tests before code.** Acceptance criteria become asserts *first*; if a criterion can't be
  expressed as a check (assert or manual), the PRD isn't done.
- **Don't hand-edit generated views** in the fixtures (`META.md`, `EXPERIMENTS.md`, ledger
  blocks) — regenerate them via the engine so the fixture stays honest.
- **One change per PR.** A feature and an unrelated fix are two arcs, two PRDs, two PRs.
- **Scope is crux the tool.** This skill edits `~/crux`. It never touches a user's research
  vault or project code — those are what crux (and this change) serve.
