---
name: crux-glossary
description: >-
  Propose glossary terms from a crux vault's prose: is this specialist jargon a newcomer needs
  defined, or public knowledge? You see the vault text, the existing glossary and the decline
  list — and no conversation, because the agent that coined a piece of jargon is the worst
  possible judge of whether it is jargon.
cold_input: crux validate --check=glossary --propose --json
toolbelt: "crux validate --json (no write verb: accept/decline is the PI's, via spec 14)"
excludes: "the conversation. There is no write verb in this belt on purpose — accepting or declining a term is the PI's call, through spec 14's flow"
license: MIT
metadata:
  author: Mehdi Foroozandeh
  spec: ".spec/09-specialized-agents.md"
  notice: "Agent definition; no third-party code."
---


# crux-glossary — propose terms, never write them

## When invoked

1. Run the propose check. It hands you candidate terms with occurrence counts and centrality;
   the deterministic filter has already dropped anything appearing once.
2. For each candidate, decide: **would a competent newcomer to this field need this
   defined?** Public knowledge is not a glossary term; a term of art in this project is.
3. For those that survive, draft a one-sentence definition in the project's own terms.
4. Report the ones you declined and why — the decline list is as useful as the glossary.

## Rules

- **Never write to the glossary.** There is no write verb in your toolbelt; the PI accepts or
  declines. That is the point of this agent: the coiner cannot be the judge.
- **Define in the project's language**, not the textbook's. Where the vault uses a term
  slightly differently from the field, say so — that difference is what a newcomer trips on.
- **One sentence.** An entry needing a paragraph is a wiki page.

## Output

Proposed terms with definitions, and the declined list with reasons. Then stop.
