---
fixture: glossary-01
agent: crux-glossary
ground_truth: proxy
oracle: stated_key
verify: term_counts
checks: tree, wiki, economy, fanout, rd, tasks, glossary
band: unset
k: 5
---

# glossary-01 — jargon, or public knowledge?

The vault's prose mixes two kinds of phrase: terms of art this project coined or bent, and
words any competent newcomer to the field already owns. `crux-glossary` decides which is which.
It never writes: accepting or declining is the PI's, through spec 14's flow.

The deterministic filter has already run before the agent sees anything — a phrase appearing in
one document is dropped by the engine, never by judgment. So the eval is only about the calls
the filter cannot make.

## Planted

| id | tier | class | why it is a term of art here |
|---|---|---|---|
| `term:collapse point` | accept | project-jargon | this project's own name for where the merge table stops separating rare forms; a newcomer cannot guess it |
| `term:merge table` | accept | project-jargon | used throughout as the thing being tuned, with a project-specific meaning |

## Declined, and the decline list is the other half of the eval

| term | why it must be declined |
|---|---|
| `gradient descent` | public knowledge in this field |
| `cross-entropy loss` | public knowledge in this field |
| `transformer` | public knowledge in this field |

Proposing any of these three is a false positive and costs precision. An agent that accepts
every repeated phrase has not made a judgment; it has made a word count.

## What this proxy does **not** measure

**Where the line is.** *"Would a competent newcomer need this defined"* has no oracle — the key
above is one reviewer's answer, and a defensible reviewer could move `transformer` across the
line for a cross-disciplinary audience. That is the sense in which this is a proxy, and no
amount of K makes it ground truth.

Certification checks only what the engine can: every planted term clears the occurrence floor
the deterministic filter applies, so the fixture cannot grade an agent on a term the filter
would have dropped before it ever arrived.
