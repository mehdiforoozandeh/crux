# Setting up a vault, and writing nodes

*Reference for [`SKILL.md`](../SKILL.md). Read it when the PI wants to start crux in a
project, when an existing repo is to be reconstructed into a vault, or before you write a
node's prose by hand.*

## Setting up a vault (first run)

You stand up the vault; the PI only thinks about the science. Never hand them a schema to
fill in. Open with one question that covers every case:

> "Point me at anything that describes or contains this project — a proposal, notes, a
> draft paper, or your existing code and results — and I'll set the whole thing up from it.
> If there's nothing written down yet, we'll work it out together."

Adapt to what exists:
- **Descriptive documents** (proposal, grant, notes, draft): read them.
- **An existing repo** (code, results, figures, READMEs): this is migration. Hand it to the
  **crux-migrate** agent with the repo path; it drafts a seed and never writes a vault.
- **Nothing written yet**: a short back-and-forth to pull the project out of their head. What
  are you trying to find out? The big open questions? For the sharpest one, a testable hunch,
  and what result you would expect if it is true?

**Then: one seed outline → the PI approves it → the engine writes it.** Show the seed, let the
PI edit and approve it as one block, then materialize the whole vault at once:

```bash
crux init --from seed.md --dir cruxvault
```

Do not create nodes one verb at a time during setup; approval happens on the seed. The seed
grammar (indented bullets, `Project:` / `Q:` / `H:` / `expect:` / `v:` / `finding:` prefixes)
is in `scaffold/README.md` under *Setup*, and the 4.0 shape with a finding's direction and
confidence is in the crux-migrate agent's definition. The engine validates the whole seed
before writing anything, so a malformed seed leaves nothing behind.
Either form of `crux init` also adds one line to the project's `AGENTS.md` (created if absent, never
duplicated) that points agents other than Claude Code at the always-on core.

**Reconstructing finished work.** A hypothesis that already ran is marked `[tested]`, carries
its expectation, ticks its checks from the evidence (`[x]` met, `[ ]` unmet, `[-]` n/a, each
with a `(found: …)` note), and gets a `finding:` with direction and confidence judged as in
the core's *Closure judgment*. Show the evidence for each tick, and let the PI approve the
whole seed before it is recorded.

**Migration guardrail — absolute.** When reading an existing repo you may read anything, but
you may **only ever create, edit, move, or delete files under `cruxvault/`**. Never touch the
user's code, data, results, or docs.

A vault from an older engine migrates itself on the first write-capable command, with a
backup first. Nothing for you to run.

## Running the engine

```bash
cd <vault>                       # or anywhere under it; the engine finds .crux.yaml upward
python <skill>/scaffold/crux.py <verb> [...]   # or the `crux` wrapper; --help on every verb
```

A vault holds the project node, question and hypothesis files, findings, `results/<hid>/`
evidence, `tasks/`, the generated `META.md` and `EXPERIMENTS.md`, `glossary.md`, and
`.crux.yaml`. The vault is the only thing you write into the user's repo.
`python scaffold/selftest.py` validates an install with no GPU, tokens or cluster.

## Writing a node

- **Every question and hypothesis opens with `## ELI5`** (one sentence a science
  undergraduate follows) **and `## TL;DR`** (what it asks or claims, and what would settle
  it). If you cannot write the TL;DR, the node is not ready to exist.
- **Evidence lives in `results/<hid>/`** inside the vault (symlink it to the real run
  directory if the files live elsewhere), and a finding links it with `-e`. `crux validate`
  errors when a linked path does not resolve or escapes the vault.
- **Keep a node under 400 words of prose.** The cap covers ELI5, TL;DR and framing prose, not
  the checks or the evidence links. A node that wants more room is usually several nodes.
- **One parent per node.** Extra `[[links]]` are "see also" and do not affect the roll-up.
- **When the PI rules, edit the text; the diff is the history.** Never append an "amended"
  block; `git log -p <node>.md` is the changelog.
- **Five untested hypotheses under one question is the cap.** Past that `crux hypothesize`
  warns and `validate` flags the question.
- **Node files are files, not chat.** No improvised headings beyond the schema.
- **Never hand-edit generated content** (`META.md`, `EXPERIMENTS.md`, the
  `<!-- crux:ledger -->` block); run a verb and let the engine regenerate.
