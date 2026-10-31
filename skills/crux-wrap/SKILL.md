---
name: crux-wrap
description: >-
  /crux-wrap — end-of-session capture for a crux vault. Runs the capture agent over this
  session, shows the PI in plain words what the session already recorded, then asks one
  accept-or-reject question per pending candidate.
license: MIT
disable-model-invocation: true
metadata:
  author: Mehdi Foroozandeh
  version: "1.0"
  spec: ".spec/19-background-memory.md (Capture: /crux-wrap)"
  requires: "the crux skill and the crux-capture agent, installed beside this one"
  notice: "Playbook only; drives the crux engine's `wrap` and `pending` verbs. No third-party code."
---

# crux-wrap — capture this session, show it, ask about the rest

The PI typed `/crux-wrap`. Do these four steps in order, and say nothing beyond what steps 3
and 4 tell you to say.

1. **Read the session.** Run `crux wrap --json`. It returns `records` (what this session
   already wrote, read from its own crux calls), `pending` (the candidates waiting on the PI),
   and `text` (the session's transcript not yet swept, capped; `truncated` says if the cap
   cut it). It also moves the sweep mark, so the next session start does not sweep this text
   again. No vault? Say in one sentence that there is no notebook in this project yet, and
   stop.

2. **Run the capture agent.** If `text` is not empty, write it to a scratch file and hand the
   **crux-capture** agent that file's path. Tell it, in the brief: *"Started by /crux-wrap:
   pass `--source wrap` on every pending item."* It records what it is sure of and adds what
   it is not sure of to the pending list. Its report lists one line per record; keep those
   lines for step 3. If the agent is not installed, do its job yourself under its rules
   (`agents/crux-capture/AGENT.md`): never ask the PI anything during this step.

3. **Show what the session already recorded.** One short list, in plain words: the
   `records` from step 1 plus the records the capture agent just wrote. Each line is the
   science: the question asked, the hypothesis with what it expects, the finding with its
   direction and how confident it is. No node id, no command, no crux vocabulary (the voice
   rules in the core apply). Nothing recorded? Say so in one sentence.

4. **Ask about each pending candidate, and only those.** Run `crux pending list --json`. For
   each candidate, ask one `AskUserQuestion`: the candidate in plain words, with two options,
   **accept** (record it) and **reject** (drop it). One question per candidate, never a batch,
   and never a question about anything already recorded. Then act on the answer:
   - **accept**: write it with the verb its `kind` names: `crux ask` (question),
     `crux hypothesize --expect` (hypothesis), `crux finding` (finding), `crux park`
     (park), `crux task add` (task), or the change it names (correction, which always wins
     over the record). Then `crux pending clear <id>`.
   - **reject**: `crux pending clear <id>`.
   - The PI rewords it in their answer: record their wording, not the candidate's.

When the last candidate is answered, stop. Nothing after it: no summary, no "all done".
