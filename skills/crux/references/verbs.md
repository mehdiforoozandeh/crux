# The verbs, and whose call each one is

*Reference for [`SKILL.md`](../SKILL.md). Flags and aliases: `crux <verb> --help`, the
source of truth. This page carries only what `--help` does not: whose call a verb is.*

"Yours" means you run it without asking, and silently: the PI hears the science, never the
call. Every verb except `init`, `serve` and `selftest` takes `--json`; use it to read a
result back.

| verb | whose call | note |
|---|---|---|
| `status` · `validate` · `brief` | yours | read-only |
| `ask` · `hypothesize` | yours | opened silently as the conversation produces them; each needs `--bears` (how its answer moves its parent's answer), a hypothesis also `--expect` |
| `finding` | yours | the closure judgment in the core; `-a` on a question, `-d` on a hypothesis |
| `park` | yours | a node the conversation dropped; `--undo` when the PI picks it up again |
| `test` | yours to record | `--run` records a run link; `--to running` locks the checks. Starting compute the PI did not ask for is theirs |
| `task add` · `done` · `drop` · `list` · `show` · `categories` | yours | see `references/taskhub.md` |
| `pending list` · `add` · `clear` | yours | the capture candidates `/crux-wrap` asks about |
| `wrap` · `sweep` · `hook` | the capture plumbing | run by `/crux-wrap` and the session-start hook |
| `init` | yours, after the PI approves the seed | see `references/vault.md` |
| `serve` | yours | the read-only cockpit (the **crux-cockpit** skill) |
| `glossary accept` · `decline` | the PI's answer, recorded by you | never write `glossary.md` directly |
| `ingest` · `lit` | the PI curates `raw/` | the **crux-wiki** and **crux-litsearch** skills |
| `rd` | yours, when the PI says a design has settled | the **crux-rd** skill |
| `deck` | yours | the **prezit** and **storify** skills |
| `auto check` · `auto status` | yours | the **crux-autopilot** skill |
| `auto run` | **the PI's** | it spends compute unattended; start it only on the PI's explicit yes |
| `migrate` · `doctor` · `voice` | yours | maintenance and checks |

`hypothesize` also takes `--builds-on <hid>`: the earlier attempt this one branched from.
Lineage only.

## Removed in engine 4.0

Each prints one line naming its replacement and writes nothing.

| removed verb | use instead |
|---|---|
| `review` (removed) | `crux status`: a node's state is derived from its findings |
| `answer`, `synthesize` (removed) | `crux finding <qid> -a "<answer>" -c <confidence>` |
| `close` (removed) | `crux finding <hid> -d <direction> -c <confidence> -w "<why>"` |
| `approve`, `approve-null` (removed) | nothing waits for sign-off; a finding records whether the null was ruled out |
| `pursue` (removed) | `crux hypothesize`, or `crux park <id> --undo` |
| `task accept`, `task review` (removed) | `crux finding <hid> -e tasks/<file>` |
