#!/usr/bin/env python3
"""crux engine — the deterministic (○) core.

A crux vault is a directory of markdown nodes plus two generated views.
Node types: project (root) · question (aggregator) · idea (testable leaf) ·
synthesis (optional, horizontal). The engine never judges and never reads run
logs: the agent supplies a hypothesis' verdict (via verifiable checkboxes) and a
headline metric string; the engine only does bookkeeping — IDs, the Parent::
tree, validators, the evidence-ledger roll-up, the review gate, status
transitions, and regenerating META.md / EXPERIMENTS.md.

Stdlib only. The CLI (crux.py) and selftest.py call the cmd_* functions here.
"""
import os, re, sys, json, html, datetime, tempfile, shutil, hashlib, shlex, math

# ----------------------------------------------------------------------------- constants
ENGINE_VERSION = "3.5"          # bumped when verdict/roll-up/view logic or vault format changes; stamped into every vault
                                # 1.4: prezit (spec 11) — the engine now reads two new optional
                                # vault conventions: results/<hid>/metrics.json (addressable
                                # numbers) and an optional `## Protocol` section on questions.
                                # Additive + read-only: a pre-1.4 vault loads unchanged.
                                # 1.6: evidence semantics (spec 15) — nodes created from here
                                # on carry `schema: 1`. The stamp is the version boundary:
                                # spec-15 rules bind stamped nodes only, and ABSENCE of the
                                # stamp means the node predates them, permanently.
                                # 1.7: every verifiable carries a `kind` — `hypothesis` (a
                                # consequence of the claim) or `outcome-neutral` (a control
                                # that must pass whatever the claim turns out to be).
                                # 1.8: a hypothesis declares a combination RULE before the
                                # run, the verdict becomes a function of (kinds, rule,
                                # vector), and `invalid-run` joins the vocabulary.
                                # 1.9: the commitment (checks + kinds + rule) is content-
                                # hashed when the run starts; any later edit is flagged as
                                # drift, loudly and permanently — never refused.
                                # 1.5: the RD layer (spec 07) — the engine now scans a new
                                # directory (rd/), interprets a new `type: rd`, and writes a
                                # new generated view (RD.md). Additive: a pre-1.5 vault has no
                                # rd/ at all and loads byte-unchanged.
                                # 2.0: the taskhub (spec 08) — a third side-layer, tasks/,
                                # holding the work a research programme has to DO. A source
                                # artifact: nothing regenerates it, ever. Additive — a pre-2.0
                                # vault has no tasks/ and loads byte-unchanged. The major bump
                                # is deliberate: 1.x ended at 1.9, a new artifact class in a
                                # new directory is the largest format change since the wiki
                                # layer, and a two-digit minor ("1.10") sorts below "1.9"
                                # under plain string comparison.
                                # 2.9: `crux brief --mode=situate` (spec 13) — a second,
                                # WIDER payload on the same verb: subtree, ancestry, linked
                                # wiki, what is untested, inbound citations and the taskhub.
                                # Read-only; no vault format change. The mode is a safety
                                # boundary, not a convenience — `isolated` stays the default
                                # so a forgotten flag degrades to over-isolation rather than
                                # to leaked advocacy, and an unknown mode is REFUSED.
                                # 3.0: the situate output bound (spec 13) — `situate_lint`
                                # plus `crux brief --lint-situate`, the deterministic goalpost
                                # a situate ANSWER must clear. The major digit rolls because
                                # 2.x ended at 2.9 and a two-digit minor sorts below a
                                # one-digit one under plain string comparison — the same
                                # reason 1.x ended at 1.9. It is a counter, not a
                                # compatibility era: read-only, no vault format change.
                                # 3.1: the methodology slots (spec 13) — two OPTIONAL
                                # frontmatter keys on a hypothesis, `measurement:` and
                                # `replicates:`, declared before the run. Absence is
                                # permanently legal and is reported at the `info` tier only.
                                # Deliberately NOT part of the hash-locked commitment: they
                                # describe how a run is carried out, not what would settle
                                # the claim, so adding them cannot drift a locked node.
                                # 3.2: science voice (spec 16) — `situate:unanchored` now
                                # accepts the anchor's TITLE as well as its id, so orienting
                                # the PI no longer forces a node id into chat. A shipped
                                # deterministic bound changed behaviour, and the stamp is how
                                # a vault records which engine wrote it, so the counter
                                # rolls. NOT a compatibility era: no vault format change, no
                                # verdict/roll-up change, nothing to migrate. Also additive
                                # and read-only: `voice_lint` + `CRUX_LEXICON` (the mirror
                                # rule as code, consumed by the evals) and `gate_relation`
                                # (the relevance gate, annotated onto `review --near`).
                                # 3.3: autopilot 05.0 (spec 05) — the vault format gains ONE
                                # optional frontmatter key on a hypothesis, `builds_on:`, the
                                # lineage of an attempt branched from another attempt. It is
                                # a field and not a tree edge on purpose: tree depth tracks
                                # QUESTIONS, and a 140-attempt run would otherwise bury the
                                # one question being asked under 140 levels of nothing.
                                # Absence is permanently legal, so a pre-3.3 vault loads
                                # byte-unchanged and there is nothing to migrate. Everything
                                # else the slice adds is read-only or append-only and touches
                                # no node: the flight plan document at auto/<qid>/plan.md,
                                # flat PUCT selection, and the engine-assembled worker brief.
CRUX_VERSION = "0.8.0"          # the RELEASE version (what ships / what the update check compares); independent of the vault format
VAULT_MARKER = ".crux.yaml"
LEDGER_START = "<!-- crux:ledger:start -->"
LEDGER_END   = "<!-- crux:ledger:end -->"

# wiki layer (Epic 3): a PI-curated literature wiki alongside the q/h tree.
WIKI_DIR     = "wiki"           # agent-owned compiled markdown pages + log.md + SCHEMA.md
RAW_DIR      = "raw"            # immutable, PI-curated sources; the engine hashes bytes, never reads content
WIKI_INDEX   = "WIKI.md"        # generated index of wiki pages (Karpathy's index.md), rendered at vault root
SOURCES_FILE = os.path.join(WIKI_DIR, ".sources.tsv")   # engine-owned source registry: sha256<TAB>date<TAB>path<TAB>openalex-id<TAB>title
OPENALEX_DIR = os.path.join(WIKI_DIR, ".openalex")      # cached OpenAlex responses, one JSON per url
OPENALEX_API = "https://api.openalex.org"
WIKI_LOG     = os.path.join(WIKI_DIR, "log.md")          # append-only chronological log (Karpathy's log.md)
WIKI_SCHEMA  = os.path.join(WIKI_DIR, "SCHEMA.md")       # per-vault conventions the agent + PI co-evolve

# RD layer (Epic 7): Requirements Documents — where the design detail displaced by the
# 400-word prose cap goes. Deliberately the wiki layer's shape, not a second pattern: a
# parentless side-layer of markdown pages, linked from the node, with a generated index and
# a structural lint. An RD is a DOCUMENT, not evidence — it never enters the roll-up, never
# moves a verdict and never trips the review gate.
RD_DIR       = "rd"             # agent/PI-written design documents, one active per node
RD_INDEX     = "RD.md"          # generated index of RD pages, rendered at the vault root
RD_STATUS    = ("draft", "active", "superseded")
RD_LINK      = "RD::"           # the node's backlink, written beside `Parent::`

# taskhub layer (Epic 8): the project's work layer — data prep, infrastructure, code,
# manuscript figures, and (from 2.2) the experiments themselves. Deliberately the wiki/RD
# shape again: a parentless side-layer of markdown files, scanned separately, with a
# generated index and a structural lint.
#
# The load-bearing property is NEGATIVE and it is the direct lesson from spec-kit, whose
# `tasks.md` is generated from the spec and whose documented workflow REGENERATES it,
# destroying checkbox state. So: the tree can trigger a task; it can never own one. Nothing
# regenerates the taskhub. `refresh` writes the index and never a task.
#
# A task is not a node. `Vault` scans the vault root only, so a file under tasks/ is
# structurally outside v.nodes — it can never be a child, never enter ledger_counts, never
# move a verdict and never trip the review gate. That is not incidental; it is the mechanism.
TASK_DIR     = "tasks"          # one file per task; ids are engine-allocated and never renumbered
TASK_INDEX   = "TASKHUB.md"     # generated index, shaped by the frontier query it serves
TASK_STATUS  = ("open", "done", "dropped")
TASK_BLOCKED = "blocked"        # COMPUTED (2.1), never stored — a state you can compute cannot drift
TASK_LINK    = "Refs::"         # the task's own outbound links, written; node -> task stays DERIVED
NO_BLOCKERS  = "None"           # the literal, so a missing edge is a visible omission (`to-tickets`)

# Category is a tag from a per-vault declared list, not a parent: categories are not actions,
# so they are not tasks. The cockpit renders one colour per category as `t-<category>`, which
# is why a token may not contain whitespace — spec 15 learned that the hard way when
# `invalid run` produced the broken CSS class `h-invalid run`.
TASK_CATEGORIES_KEY = "task_categories"
DEFAULT_TASK_CATEGORIES = ("data-acquisition", "hpc-setup", "implementation",
                           "visualization", "manuscript", "admin")
# `experiment` is RESERVED: it cannot be typed by hand, and from 2.2 the engine assigns it to
# any task carrying `hypothesis_refs`. Reserved from 2.0 rather than introduced later, for
# exactly the reason spec 15 reserves `ordered`: refusing rather than ignoring is what makes
# the later addition NOT a format change, because no vault written in between can be
# ambiguous about what the word meant.
TASK_RESERVED_CATEGORY = "experiment"

# An EXPERIMENT is a task whose output is evidence. That is the entire difference: strip both
# records down and exactly one row differs — what the output is. Two record types differing in
# one field are one record type, which is why the proposed separate experiment layer was
# designed in full and then merged here.
#
# The role is COMPUTED, never stored: a task that declares what it concluded about a
# hypothesis IS an experiment. There is no way to have an experiment that forgot to be marked
# one, and no way to mislabel a chore as one.
#
# The conclusion vocabulary is spec 15's, DERIVED from VERDICTS rather than restated, so it
# can never drift from the engine's own list. `partial` is excluded: 15 retired it from the
# image of the derivation (it *is* the partial answer that spec abolishes), and a new record
# must never reintroduce it. The rest — including `invalid-run` — carry over exactly, so the
# legend, the theme colours and the CSS class suffixes 15 already built cover both.
#
# Note the two PROVENANCES that share these tokens, because they are not the same thing:
# a hypothesis's `verdict` is DERIVED BY THE ENGINE from the tick vector under a declared
# rule; an experiment's conclusion is WRITTEN about a run and PI-accepted (2.3). Sharing the
# vocabulary is deliberate; sharing the mechanism would be a leash violation.
HYPOTHESIS_REFS = "hypothesis_refs"
RETIRED_CONCLUSION = "partial"

GENERATED    = ("META.md", "EXPERIMENTS.md", WIKI_INDEX, RD_INDEX, TASK_INDEX) # root .md views the node scan must never treat as nodes

# project glossary (spec 14): the PI's vocabulary model, one file per vault.
GLOSSARY_FILE = "glossary.md"
# Root .md files the node scan must skip BY NAME. `glossary.md` is PI-owned, not generated,
# so it does not belong in GENERATED — but it must be excluded just as firmly. Without the
# name check it is invisible only because it happens to carry no `id:` frontmatter, and the
# day someone adds one the glossary silently becomes a node with an unknown type.
NON_NODE_FILES = GENERATED + (GLOSSARY_FILE,)

# evidence artifacts (v0.5): a hypothesis points at what its run actually produced.
# Convention home is results/<hid>/ inside the vault, listed under the node's `## Artifacts`.
# The engine only does bookkeeping here too — it classifies by extension and checks the
# paths resolve; it never opens an artifact, and never judges one.
RESULTS_DIR      = "results"
METRICS_FILE     = "metrics.json"   # optional, PI/harness-written: results/<hid>/metrics.json
                                    # holds the addressable numbers a deck may quote (spec 11 §5a).
                                    # The engine reads and resolves it; it NEVER writes or computes one.
ARTIFACT_KINDS   = {"report": (".md",),
                    "image":  (".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"),
                    "data":   (".csv", ".tsv", ".json", ".txt")}
# What the cockpit's read-only file route is willing to hand back. Declared HERE, and keyed
# to content types in serve.py, so the UI can tell in advance which artifacts it may offer as
# links — an artifact outside this set is shown, but inert, instead of linking to a 404.
SERVABLE_EXT     = frozenset({".md", ".txt", ".csv", ".tsv", ".json", ".pdf",
                              ".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp"})

TYPES            = ["project", "question", "idea", "synthesis"]
QUESTION_STATUS  = ["open", "review", "resolved"]
IDEA_STATUS      = ["idea", "staged", "running", "done"]
# `partial` is RETIRED, not removed. It can never be derived for a node that binds evidence
# semantics — it *is* the partial answer spec 15 abolishes — but it must stay in the
# vocabulary forever: `snapshot` clamps any verdict outside this list to None, and the
# cockpit renders a `done` node with a None verdict as inconclusive, so deleting the token
# would silently re-label every pre-15 partial result. That is the render path overturning
# recorded science, which is the one thing the leash forbids.
#
# `invalid-run` is hyphenated because the cockpit builds its CSS class as "h-" + verdict; a
# space would produce the broken class `h-invalid run`. A render fact, not a preference.
VERDICTS         = ["supported", "partial", "refuted", "inconclusive", "invalid-run"]
# spec 08's experiment conclusions: VERDICTS minus the retired `partial`. Derived here,
# immediately after the list it depends on, so a verdict added to the engine is automatically
# available as a conclusion and the two can never be edited apart.
CONCLUSIONS      = tuple(x for x in VERDICTS if x != RETIRED_CONCLUSION)
TERMINAL_IDEA    = "done"
TERMINAL_QUESTION= "resolved"

# evidence semantics (v1.6 / spec 15): the version boundary.
#
# Spec 15 rewrites what a verifiable is and what a verdict means. Its rules bind hypotheses
# created at or after this engine version and NEVER anything older — a retroactive rule would
# re-verdict settled nodes, i.e. the engine overturning recorded science, which is precisely
# what the leash exists to prevent.
#
# The mechanism has to be per-NODE. The vault-level `engine_version` in .crux.yaml cannot
# carry it: `check_and_stamp_version` overwrites that stamp on drift *before* it returns the
# warning, so one command after an upgrade erases the evidence that the vault is old.
#
# So: every question/idea created from 1.6 on carries `schema: 1`, and absence reads as 0.
# The boundary is permanent and visible, not a transition to be completed — there is
# deliberately no `crux migrate` for it. Bringing an old hypothesis up to the new schema
# means re-declaring what would settle a claim, which is a scientific act, PI-gated, one
# node at a time.
# The NULL (spec 09). The brief removes the parent's authored prompt, but one leak cannot be
# engineered away: the hypothesis TITLE is directional — "masked-token beats masked-stem"
# presumes a winner, and a fresh agent still knows which way the room leans. The answer is
# not to neutralise the title but to push against it. The null is the BORING EXPLANATION:
# the cheapest way this result could be trivially true. The checks must then discriminate
# between the claim and that null.
#
# Three goalposts, all in code. Instructions will not hold this and the proof is on the
# record — the crux skill already said "keep the science explicit" and produced 5,725-word
# nodes. The vault also invented the null by hand once, at a cost of 5,725 words, because
# the schema had nowhere to put it.
#
#   one null, one line, <= 25 words     — deterministic
#   it names a family from a CLOSED list — the agent picks a family and names the instance,
#                                          so nothing exotic is even on the menu
#   the PI approves it before checks are written — the gate between crux-null and
#                                          crux-verifiables; the null IS the bar restated,
#                                          and the leash already makes the bar the PI's call
CONFOUND_FAMILIES = ("capacity", "chance", "leakage", "selection", "normalization",
                     "instrumentation")
NULL_MAX_WORDS    = 25
NULL_APPROVED     = "null_approved"

# Generation 2 (spec 09): a verifiable's FAILURE SCENARIO joins the pre-registered
# commitment. The generation is what `lock_material` keys off, so a node stamped 1 keeps
# the material it was locked with — forever. Without that split, bumping the commitment's
# shape would re-hash every already-locked node and flag an edit nobody made, which is the
# engine falsifying its own record.

SCHEMA_GENERATION = 2

# `validation_report`'s third tier. `info` is neither a problem nor a warning: it never
# affects `ok`, so a legacy vault is never put into red by a boundary it could not have
# known about. Ids are `<namespace>:<slug>` — consumers filter on the namespace and must
# never string-match a message, because messages get reworded and ids do not.
INFO_NAMESPACES = ("boundary", "task", "agents", "glossary", "design")  # <namespace>:<slug>

# Verifiables come in two classes and crux used to flatten them, which is what let a broken
# apparatus and a false claim produce the same-looking partial pass.
#
#   hypothesis       a consequence of the claim. Feeds the verdict.
#   outcome-neutral  a positive control / manipulation check / floor-ceiling check. It must
#                    pass REGARDLESS of what the claim turns out to be. Its failure
#                    invalidates the RUN, and nothing about the claim is learned.
#
# Regulators call the property this protects assay sensitivity (ICH E10): without a passing
# positive control, "the hypothesis is false" and "the apparatus is broken" are
# indistinguishable. The separability research adds the other half — an outcome-neutral check
# is the DUAL of a common-mode failure, a detector for the one shared ingredient (a batch, a
# seed, a preprocessing path, a control arm) that would otherwise sink every bundled
# hypothesis at once, silently.
#
# Syntax is a LEADING bracket tag on the checkbox line:
#
#   - [x] [outcome-neutral] the known-good encoder reproduces 0.46 (found: 0.461)
#         ^^^^^^^^^^^^^^^^^                                       ^^^^^^^^^^^^^^^
#         the kind (this)                                         the evidence (spec 11)
#
# Leading, not trailing, and that is forced rather than chosen: the seed parser strips a
# trailing `(...)` as the evidence note, so `(outcome-neutral)` would be silently recorded as
# a finding. Anchoring the kind to the FRONT means it can never compete for that slot.
# A verifiable's FAILURE SCENARIO — the world in which this check fails (spec 09). It rides
# on an INDENTED CONTINUATION LINE under the checkbox, not as a suffix on it:
#
#   - [ ] imp-Spearman >= +0.01
#         fails-if:: the gain is capacity alone — the width-matched arm also clears it
#         discriminates:: true
#         ^^^^^^^^^^^^^^^ its OWN field (D8), not a marker packed onto the line above. A `!`
#                         suffix was considered and declined: terser, but easy to miss in
#                         review, and review is the entire point of writing these down.
#
# The continuation line was measured against every reader spec 15 shipped and is invisible to
# all of them: tick, kind, text, `(found: …)` and both tallies are byte-unchanged. The three
# alternatives were not — a trailing `(fails-if: …)` is swallowed by the seed parser's
# evidence regex (the same failure that ruled out `(outcome-neutral)`), and a suffix or an
# inline field pollutes the check's own sentence in the cockpit and on every deck slide.
#
# Why it exists: spec 09 replaces a numeric cap on verifiables with a logical one — two
# verifiables are redundant if they fail for the SAME REASON. The engine cannot judge that.
# What it can do is force the residue to be written down, so redundancy is visible at a
# glance to the PI and to `crux-critic`. Every verifiable had to pass the admission test to
# exist, so every one has a scenario.
FAILS_IF_RE      = re.compile(r"^\s+fails-if::\s*(.+?)\s*$")
DISCRIMINATES_RE = re.compile(r"^\s+discriminates::\s*(.*?)\s*$")
# what counts as "yes" on a `discriminates::` line; a bare marker means yes
_TRUEISH         = ("", "true", "yes", "y", "1")

DEFAULT_KIND     = "hypothesis"
NEUTRAL_KIND     = "outcome-neutral"
VERIFIABLE_KINDS = (DEFAULT_KIND, NEUTRAL_KIND)
_KIND_ALIASES    = {"hypothesis": DEFAULT_KIND, "hyp": DEFAULT_KIND, "h": DEFAULT_KIND,
                    "claim": DEFAULT_KIND,
                    "outcome-neutral": NEUTRAL_KIND, "outcome_neutral": NEUTRAL_KIND,
                    "neutral": NEUTRAL_KIND, "control": NEUTRAL_KIND, "on": NEUTRAL_KIND,
                    "positive-control": NEUTRAL_KIND}
_KIND_TAG_RE     = re.compile(r"^\s*\[([A-Za-z][A-Za-z_-]*)\]\s+")
# The written opt-out for "this claim genuinely has no meaningful positive control". A
# non-empty string satisfies the requirement; the reason itself IS the audit trail, which is
# the point — "there is no control here" has to be SAID, not silently assumed.
NEUTRAL_OPTOUT   = "neutral_optout"

# How a hypothesis' claim-directed checks add up, declared BEFORE the run. This is what turns
# "two of four passed" from an argument into arithmetic. ICH E9 2.2.5 states the design space
# as a quantifier — whether an impact on ANY of the variables, SOME MINIMUM NUMBER of them,
# or ALL of them is required — and those three are what ship.
#
# `ordered` (the fixed-sequence / gatekeeping rule: test in order, stop at the first failure)
# is RESERVED and refused, by PI ruling. It is the exact structure PLATO's authors narrated
# past — a pre-specified 10-step hierarchy that stopped at endpoint 6 and whose endpoints
# 7-10 were published anyway — and it is the hardest of the four to render unambiguously.
# Reserving rather than ignoring the token is the point: no vault can contain one, so adding
# it later is not a format change.
COMBINATION_RULES = ("all", "any", "m-of-n")
RESERVED_RULES    = ("ordered",)
RULE_FIELD        = "rule"
RULE_M_FIELD      = "rule_m"

# The lock. Bare pre-registration largely does not work — preregistered studies show no drop
# in positive results, and 46% of preregistered hypotheses are simply missing from the paper.
# Registered Reports DO work (44% positive results against 96%), and the active ingredient is
# ENFORCED COMMITMENT, not the document. crux can enforce what a journal cannot, because a
# verifiable is content-addressable and a vault is a git repo.
#
# Edits are FLAGGED, not refused. Research legitimately discovers that a check was wrong, and
# refusing the edit only produces a laundered duplicate hypothesis. A loud, permanent flag is
# both more honest and harder to ignore. Nothing in the engine consults the flag to change a
# verdict, a status or a roll-up: it warns at `review` and at `answer` and blocks neither —
# the engine flags, the PI decides.
LOCK_FIELD        = "lock"        # sha256[:16] of the canonical commitment
LOCKED_AT_FIELD   = "locked"      # when — the timestamp crux can prove and a journal cannot
LOCK_WHERE_FIELD  = "lock_at"     # "running" (pre-registered) | "close" (never was)
RECONSTRUCTED     = "reconstructed"   # seeded [tested]: history, not a pre-registration

# `crux migrate` bridges SCHEMA, never SCIENCE (spec 09 + spec 15's ruling).
#
# Spec 09 dissolves version bridging into a mechanical rewrite. Spec 15 ruled the opposite
# for its own fields: bringing an old hypothesis up to evidence semantics means re-declaring
# what would settle a claim, which is a scientific act, PI-gated, one node at a time. Both
# are right about different fields, and the split was measured rather than guessed.
#
# `schema` is the sharp one and deserves naming: writing it does not "add a field", it FLIPS
# A NODE ACROSS THE VERSION BOUNDARY, and every spec-15 rule — control required, rule
# required, null approved, scenarios, lock, drift — instantly binds work that was settled
# before those rules existed. One automated write is the whole grandfathering ruling undone.
#
# So the verb does not know how to write these. Not a warning, not a --force.
MIGRATE_FORBIDDEN = frozenset({"schema", RULE_FIELD, RULE_M_FIELD, LOCK_FIELD,
                               LOCKED_AT_FIELD, LOCK_WHERE_FIELD, NEUTRAL_OPTOUT,
                               NULL_APPROVED, "null_hash"})
# Sections it may CREATE (empty) but never FILL. An empty `## Null` is inert — the null gate
# is stamp-gated, so a pre-15 node is never asked for one — but a *filled* null would be the
# engine inventing the boring explanation on the PI's behalf.
MIGRATE_SECTIONS = {"idea":     ("ELI5", "TL;DR", "Null", "Artifacts"),
                    "question": ("ELI5", "TL;DR", "Protocol")}

# node economy (v1.3): the engine has always enforced falsifiability and never economy, so
# nodes grew without bound until the vault stopped being readable by the PI it exists to
# serve. Two numbers push back — a prose budget per node, and a fan-out budget per question.
#
# Both are WARNINGS, never problems. A hard error would put every already-bloated vault into
# permanent red on nodes whose only remedy (RD pages, a taskhub) is not built yet; that
# bundles a migration project onto a feature. `crux validate --strict` is the opt-in.
PROSE_CAP  = 400        # words of prose per node
FANOUT_MAX = 5          # unrun hypotheses under one question

# What the cap counts. Deliberately NOT `## Verifiables`, `## Run Links`, `## Artifacts` or
# the generated ledger: those are structured lists, they are not what made nodes unreadable,
# and capping them would punish thoroughness in the one place crux wants it. ELI5 and TL;DR
# count *inside* the budget rather than on top of it — otherwise the schema raises the
# ceiling instead of capping it.
PROSE_SECTIONS = {
    "question": ("ELI5", "TL;DR", "Question", "Answer so far"),
    "idea":     ("ELI5", "TL;DR", "Problem Statement", "Idea / Hypothesis",
                 "Planned Intervention", "Findings"),
}

# `crux validate --check=<list>`. Named so an agent can drive one check deterministically
# without parsing prose, and so the PI can silence a tier without silencing the whole lint.
# OPT_CHECKS run ONLY when named: `decks` walks presentations/, which plain `validate`
# must ignore entirely (spec 11 §9) — a vault lint must not slow down or warn on derived
# documents nobody asked about.
CHECKS     = ("tree", "wiki", "economy", "fanout", "rd", "tasks", "glossary")
OPT_CHECKS = ("decks", "gate")
PRESENTATIONS_DIR = "presentations"     # derived decks live here; never evidence, never
                                        # linked from `## Artifacts`

# `crux brief --mode=…` (spec 13). Two payloads on one verb, and the pair is a SAFETY
# boundary: `isolated` is spec 09's bias-proof cold input, which excludes the problem
# statement precisely because that is where the advocacy lives; `situate` is the opposite —
# subtree, ancestry, findings — for orienting the PI after time away.
#
# `isolated` is the default so that a forgotten flag degrades to over-isolation rather than
# to leaked advocacy, and an unrecognised value is REFUSED rather than coerced. That refusal
# is the load-bearing part: any "unknown means the default" rule is one edit away from
# "unknown means the wider payload".
BRIEF_MODES        = ("isolated", "situate")
BRIEF_DEFAULT_MODE = "isolated"

# What a situate ANSWER owes the PI. Spec 13 is unusually firm here — "brevity is situate's
# acceptance criterion, not a preference", and "a verbose /situate has failed at its only
# job" — so it is a bound in code rather than a sentence in an agent body. The spec's own
# evidence for why: SKILL.md has said "keep the science explicit" since v0.5 and the vault it
# governs held a 5,725-word node. Instructions did not hold.
#
# `total_words` IS `PROSE_CAP` on purpose. A node's budget and an orientation's budget are the
# same 400 words, counted by the same tokenizer, so the PI carries one number rather than two
# and no future change can make them drift apart.
SITUATE_BUDGET = {"eli5_words": 60, "tldr_paragraphs": 3, "total_words": PROSE_CAP}

# The methodology slots (spec 13). Spec 15 made three design facts machine-checkable — a
# control is declared, at least one check is outcome-neutral, a combination rule is named.
# Two more were specified and never built: WHAT is measured, and with how many replicates.
#
# `metric:` is NOT either of them, and the difference is the whole point: `metric` is the
# headline RESULT written at `close`, so reusing it would let the result be written into the
# slot that is supposed to constrain the result.
#
# Three properties, each deliberate:
#   frontmatter, not prose   same shape as `rule` / `metric` / `neutral_optout`, so there is
#                            no fifth line format to parse, and declaring a design cannot eat
#                            the 400-word prose budget.
#   NOT in `lock_material`   they describe how a run is carried out, not what would settle the
#                            claim. Spec 09's D1 measured the alternative: anything added to
#                            the commitment re-hashes every locked node and flags a drift
#                            nobody caused, which is the engine falsifying its own record.
#   reported as `info`       `ok` is `not problems and not warnings`, so a warning would put
#                            every existing vault into red over a field it never had. A
#                            missing declaration means the design was not written down; it
#                            does not make the record incoherent.
MEASUREMENT_FIELD = "measurement"
REPLICATES_FIELD  = "replicates"
# The window where a design is both decided and still changeable. A raw `idea` has no design
# yet and nagging it is noise; a `done` hypothesis' design is history, and flagging it would
# be the retro-checking spec 15 forbids.
DESIGN_STATUSES   = ("staged", "running")

class CruxError(Exception):
    """Raised on any rule violation; the CLI turns it into a clean message + exit 1."""

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ----------------------------------------------------------------------------- tiny flat YAML
# We control the schema: frontmatter and config are flat `key: value` maps of
# scalars (str/int/bool/None). That lets us avoid a YAML dependency while staying
# Obsidian-compatible.
def yaml_load(text):
    d = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        d[key.strip()] = _coerce(val.strip())
    return d

def _coerce(val):
    if val == "":
        return None
    if (val[0], val[-1]) in (('"', '"'), ("'", "'")):
        return val[1:-1]
    if val == "true":  return True
    if val == "false": return False
    if re.fullmatch(r"-?\d+", val): return int(val)
    return val

def yaml_dump(d):
    return "\n".join(f"{k}: {_fmt(v)}" for k, v in d.items())

def _fmt(v):
    if v is None:  return ""
    if v is True:  return "true"
    if v is False: return "false"
    if isinstance(v, int): return str(v)
    s = str(v)
    if s == "" or s != s.strip() or s[0] in "[]{}>|*&!%@`\"'#" or ":" in s or "#" in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s

# ----------------------------------------------------------------------------- file io
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write_if_changed(path, content):
    """Write only if bytes differ. This is what makes refresh idempotent."""
    if os.path.exists(path) and read(path) == content:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def parse_doc(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        return yaml_load(m.group(1)), m.group(2)
    return {}, text

def render_doc(fm, body):
    return "---\n" + yaml_dump(fm) + "\n---\n\n" + body.lstrip("\n").rstrip() + "\n"

def replace_block(body, start, end, new):
    block = f"{start}\n{new}\n{end}"
    if start in body and end in body:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, body, flags=re.S)
    return body.rstrip() + "\n\n" + block + "\n"

# ----------------------------------------------------------------------------- misc helpers
def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return (s or "node")[:40]

def natkey(nid):
    m = re.match(r"([a-zA-Z]*)(\d*)", nid)
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)

def find_vault(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, VAULT_MARKER)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise CruxError("not inside a crux vault (no .crux.yaml found). Run `crux init` first.")
        d = parent

def check_and_stamp_version(root):
    """Compare the engine version stamped in the vault against this engine.
    On mismatch: return a loud warning AND record the current version (a git diff on
    .crux.yaml becomes the durable, auditable record of drift). Returns None if in sync."""
    cfg_path = os.path.join(root, VAULT_MARKER)
    cfg = yaml_load(read(cfg_path))
    stamped = cfg.get("engine_version")
    stamped = None if stamped is None else str(stamped)
    if stamped == ENGINE_VERSION:
        return None
    cfg["engine_version"] = ENGINE_VERSION
    write_if_changed(cfg_path, yaml_dump(cfg) + "\n")
    if stamped is None:
        return None  # pre-versioned vault; silently adopt the stamp
    # Third person, like every other line the CLI prints (spec 16): this is written ABOUT
    # the PI, not to them. The second-person original invited the agent to quote it at the
    # PI verbatim, which put "vault", "engine" and "verdicts" into a conversation the mirror
    # rule keeps free of them.
    return (f"engine drift: this vault was written with crux engine v{stamped}, "
            f"but the engine now running is v{ENGINE_VERSION}. Verdicts and generated views "
            f"may differ. Pin the matching engine (re-install the crux skill at v{stamped}) "
            f"to reproduce the recorded results exactly.")

# ----------------------------------------------------------------------------- templates
_BUILTIN = {
"project": """---
id: <<id>>
type: project
title: <<title>>
status: active
created: <<now>>
updated: <<now>>
---

# <<title>>

Project root — the whole research program. Top-level questions point here via `Parent::`.

## Goal

<<goal>>

## Navigate

See [[META]] for the live question tree and dashboard, and [[EXPERIMENTS]] for the flat experiment registry.
""",
"question": """---
id: <<id>>
type: question
schema: <<schema>>
title: <<title>>
parent: <<parent_id>>
status: open
stale: false
created: <<now>>
updated: <<now>>
---

# <<id>> — <<title>>

Parent:: [[<<parent_basename>>]]

## Question

<<title>>

## Protocol

<!-- optional (engine 1.4 / spec 11): the rules locked BEFORE any run — endpoints, arms,
     thresholds, scope. `crux deck` surfaces this as the "rules locked up front" note. -->
_(optional: the pre-registered rules — endpoints, thresholds, scope — locked before any run)_

## Answer so far

_(interpretation — written by the PI/agent; auto-flagged stale when new evidence lands)_

<<ledger_start>>
_(no children yet)_
<<ledger_end>>
""",
"idea": """---
id: <<id>>
type: idea
schema: <<schema>>
title: <<title>>
parent: <<parent_id>>
status: idea
rule:
measurement:
replicates:
verdict:
metric:
created: <<now>>
updated: <<now>>
---

# <<id>> — <<title>>

Parent:: [[<<parent_basename>>]]

## Null

_(one line: the cheapest way this result could be trivially true — name a family from capacity, chance, leakage, selection, normalization, instrumentation)_

## Problem Statement

<<problem>>

## Idea / Hypothesis

<<title>>

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] <<verifiable>>

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Artifacts

<!-- what the run produced. Keep files under results/<<id>>/ and link at least the report:
     - [Report](results/<<id>>/report.md)   - results/<<id>>/curve.png -->
_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
""",
"synthesis": """---
id: <<id>>
type: synthesis
title: <<title>>
approved:
created: <<now>>
updated: <<now>>
---

# Synthesis — <<title>>

Related:: <<related>>

## Headline conclusions

## Cross-run table

## Implications for next batch
""",
"wiki": """---
type: wiki
title: <<title>>
summary: <<summary>>
category: <<category>>
sources: <<sources>>
created: <<now>>
updated: <<now>>
---

# <<title>>

_(lead: one sentence that extends the summary — scope, context, or the sharpest claim; don't restate the summary)_

## Background

_(synthesize across the cited sources — every claim traces to a file under `raw/`; don't mirror a single source)_

## See also

Related:: <<related>>
""",
"rd": """---
type: rd
node: <<node>>
title: <<title>>
status: draft
supersedes: <<supersedes>>
created: <<now>>
updated: <<now>>
---

# <<title>>

RD for [[<<node_basename>>]] — `<<node>>`

## Context

_(what forced this design — the constraint, the finding, or the question that made it necessary)_

## Out of scope

_(an explicit fence: what this design deliberately does NOT cover, binding on the node and its children)_

## Design

_(the substance)_

## Considered options

_(the alternatives, and why each lost — research reasoning lives in the rejected branch)_

## Consequences and known distortions

_(what this design gets wrong on purpose, and what must travel with every result because of it)_

## Supersedes

_(forward-only. An active RD is never amended in place: a design change writes a NEW RD with
  `crux rd <node> "<title>" --supersedes <slug>`, and the chain is the reasoning history.
  The reverse link is generated into RD.md — never write `superseded by` into an old RD.)_
""",
"wiki_schema": """---
type: wiki_schema
title: Wiki schema
---

# Wiki schema — conventions for THIS vault's literature wiki

Co-evolved by you (the PI) and the agent. The global rules live in the `crux-wiki`
skill; this file records the choices specific to this project.

## What the wiki is
A literature background layer: prior methods, SOTA, baselines, datasets, definitions —
compiled once from the immutable sources in `raw/`, then kept current. It exists to
sharpen `ask` / `hypothesize` and to interpret findings. It is **not** a record of this
project's own results.

## Flow rule (hard)
Literature → wiki → informs the tree. **Never** the reverse. A wiki page may link other
wiki pages; it must never cite a q/h tree node. Findings never enter the wiki.

## Page conventions
- One concept / entity / comparison per page; concept-slug filenames (`film-conditioning.md`).
- Frontmatter: `title`, `summary` (one line — becomes the index entry), `category`
  (entity | concept | method | comparison | dataset | overview | …), `sources`
  (comma-separated `raw/…` paths every claim traces to).
- Write for the LLM reader: dense and explicit over pretty.

## Categories in use
_(list the categories this vault uses, so pages stay consistent)_
""",
}

def load_template(kind):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", kind + ".md")
    text = read(path) if os.path.exists(path) else _BUILTIN[kind]
    return (text.replace("<<ledger_start>>", LEDGER_START)
                .replace("<<ledger_end>>", LEDGER_END)
                .replace("<<TASK_LINK>>", TASK_LINK))

def fill(text, **kw):
    kw.setdefault("now", now())
    kw.setdefault("schema", SCHEMA_GENERATION)   # every node is stamped at creation
    for k, v in kw.items():
        text = text.replace(f"<<{k}>>", str(v))
    return text

# ----------------------------------------------------------------------------- vault model
class Node(dict):
    @property
    def id(self):     return self["fm"]["id"]
    @property
    def type(self):   return self["fm"]["type"]
    @property
    def title(self):  return self["fm"].get("title", "")
    @property
    def status(self): return self["fm"].get("status")
    @property
    def parent(self):  return self["fm"].get("parent")
    @property
    def basename(self): return self["fn"][:-3]

class Vault:
    def __init__(self, root):
        self.root = root
        self.cfg = yaml_load(read(os.path.join(root, VAULT_MARKER)))
        self.nodes = {}
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".md") or fn in NON_NODE_FILES:
                continue
            fm, body = parse_doc(read(os.path.join(root, fn)))
            if "id" not in fm:
                continue
            self.nodes[fm["id"]] = Node(path=os.path.join(root, fn), fn=fn, fm=fm, body=body)
        self.children = {nid: [] for nid in self.nodes}
        for nid, n in self.nodes.items():
            p = n.parent
            if p and p in self.children:
                self.children[p].append(nid)
        for k in self.children:
            self.children[k].sort(key=natkey)

    def get(self, nid):
        if nid not in self.nodes:
            raise CruxError(f"no node with id '{nid}'")
        return self.nodes[nid]

    def root_node(self):
        return self.get(self.cfg["root_id"])

def is_terminal(node):
    if node.type == "idea":     return node.status == TERMINAL_IDEA
    if node.type == "question": return node.status == TERMINAL_QUESTION
    return True

def node_schema(node):
    """The node's schema generation; 0 means it predates evidence semantics. Total — a
    missing, empty or malformed value degrades to 0 rather than raising, because this is
    called on every node of every vault including ones written by hand."""
    try:
        return int(node["fm"].get("schema") or 0)
    except (TypeError, ValueError):
        return 0

def binds_evidence_semantics(node):
    """True iff spec 15's rules apply to this node. The ONLY place the boundary is asked
    about, so there is one answer and no drift between callers."""
    return node_schema(node) >= 1

# ----------------------------------------------------------------------------- verifiables / verdict
def verifiable_kind(text):
    """Split a leading `[kind]` tag off a verifiable's text -> (kind, text_without_tag).

    Total and lossless: an UNKNOWN tag returns (`hypothesis`, text-with-the-tag-still-on-it)
    rather than swallowing it. A tag crux does not understand must stay visible on the line
    — `validate` raises it as a problem, and silently deleting it would hide the mistake in
    the one place a reader would look for it. An untagged line is `hypothesis`, which is what
    makes every pre-15 verifiable read exactly as it always did."""
    m = _KIND_TAG_RE.match(text)
    if not m:
        return DEFAULT_KIND, text
    kind = _KIND_ALIASES.get(m.group(1).lower())
    if kind is None:
        return DEFAULT_KIND, text
    return kind, text[m.end():]

def unknown_kind_tag(text):
    """The raw tag if this line carries a bracket tag crux does not recognize, else None."""
    m = _KIND_TAG_RE.match(text)
    if m and m.group(1).lower() not in _KIND_ALIASES:
        return m.group(1)
    return None

def _verifiable_lines(body):
    """[(tick_char, text)] for every checkbox under `## Verifiables`, in document order.
    One scanner, so the tally, the cockpit reader and the deck reader cannot drift."""
    out, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "verifiables"
            continue
        if not in_sec:
            continue
        m = re.match(r"\s*- \[(.)\]\s*(.*)$", line)
        if m:
            out.append((m.group(1).lower(), m.group(2).strip()))
    return out

def verifiable_scenarios(body):
    """[{fails_if, discriminates}] per verifiable, in document order — the continuation lines
    attached to each checkbox. Positionally aligned with `_verifiable_lines`, so index i is
    always check i, with `fails_if=None` where none was written.

    Two independent fields, per D8: `fails-if::` names the world where this check fails, and
    `discriminates::` marks the one aimed at the declared null. Separate lines rather than a
    `!` packed onto the first, because the whole reason these are written down is that a
    human reads them — and a one-character marker is exactly what a reader skims past."""
    out, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "verifiables"
            continue
        if not in_sec:
            continue
        if re.match(r"\s*- \[(.)\]", line):
            out.append({"fails_if": None, "discriminates": False})
            continue
        if not out:
            continue
        m = FAILS_IF_RE.match(line)
        if m:
            out[-1]["fails_if"] = m.group(1).strip()
            continue
        d = DISCRIMINATES_RE.match(line)
        if d:
            out[-1]["discriminates"] = d.group(1).strip().lower() in _TRUEISH
    return out

def _tally(states):
    met = sum(1 for c in states if c == "x")
    na  = sum(1 for c in states if c == "-")
    return met, len(states) - met - na, na

def count_verifiables_by_kind(body):
    """{kind: (met, unmet, na)} over `## Verifiables`. The input to spec 15's verdict.

    Deliberately additive: `count_verifiables` below keeps its exact pre-15 meaning and
    return type, so every existing caller, view and assert is byte-unchanged. 15.1 parses
    and requires the split; consuming it is 15.2's job."""
    by = {k: [] for k in VERIFIABLE_KINDS}
    for tick, text in _verifiable_lines(body):
        by[verifiable_kind(text)[0]].append(tick)
    return {k: _tally(v) for k, v in by.items()}

def count_verifiables(body):
    met = unmet = na = 0
    in_sec = False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line.strip().lower() == "## verifiables"
            continue
        if not in_sec:
            continue
        m = re.match(r"\s*- \[(.)\]", line)
        if not m:
            continue
        c = m.group(1).lower()
        if c == "x":   met += 1
        elif c == "-": na += 1
        else:          unmet += 1
    return met, unmet, na

def lock_material(n):
    """The canonical string a hypothesis commits to: its combination rule, then every
    verifiable in DOCUMENT ORDER as (kind, normalized text).

    Two exclusions are load-bearing, and both are the difference between a useful flag and
    one that fires on every hypothesis:

    - the TICK is not part of the commitment. Ticking a box is exactly what closing does.
    - the `(found: …)` note is not part of it either. That is the evidence, recorded after
      the run, and spec 11 already treats it as separable from the check text.

    Whitespace is collapsed, so reflowing a long check is not drift. ORDER is part of the
    commitment: reordering is a real change, and under a future `ordered` rule it would be
    the entire content of one."""
    rule, m = node_rule(n)
    parts = [f"rule={rule or ''}", f"m={'' if m is None else m}"]
    # GENERATION-KEYED. From generation 2 the failure scenario is part of the commitment —
    # it is what would have falsified the check, and writing it after results are visible is
    # the move the lock exists to detect. A node stamped generation 1 keeps the material it
    # was locked with, because re-hashing it would flag an edit that never happened.
    gen = node_schema(n)
    scen = verifiable_scenarios(n["body"]) if gen >= 2 else []
    for i, (_tick, text) in enumerate(_verifiable_lines(n["body"])):
        kind, text = verifiable_kind(text)
        text = " ".join(_FOUND_RE.sub("", text).split())
        piece = f"{kind}\x1f{text}"
        if gen >= 2:
            s = scen[i] if i < len(scen) else {"fails_if": None, "discriminates": False}
            piece += "\x1f" + " ".join((s["fails_if"] or "").split())
            piece += "\x1f" + ("!" if s["discriminates"] else "")
        parts.append(piece)
    return "\x1e".join(parts)

def lock_hash(n):
    return hashlib.sha256(lock_material(n).encode("utf-8")).hexdigest()[:16]

def lock_drift(n):
    """True iff the commitment changed after it was locked. A node with no lock — every
    pre-15 node, and every reconstructed one — can never drift."""
    stored = n["fm"].get(LOCK_FIELD)
    return bool(stored) and str(stored) != lock_hash(n)

def take_lock(n, where):
    """Stamp the commitment, once. Idempotent: the first lock is the record, so a second
    `--to running` never rewrites it."""
    if n["fm"].get(LOCK_FIELD) or not binds_evidence_semantics(n):
        return False
    n["fm"][LOCK_FIELD] = lock_hash(n)
    n["fm"][LOCKED_AT_FIELD] = now()
    n["fm"][LOCK_WHERE_FIELD] = where
    return True

def derive_verdict_15(hyp, neutral, rule, m=None):
    """The verdict for a node that binds evidence semantics: a total function of
    (kinds, rule, pass/fail vector). `hyp` and `neutral` are (met, unmet, na) triples from
    `count_verifiables_by_kind`.

    Run validity is read FIRST and separately from the claim. That order is the whole point
    of the two kinds: a failed positive control means the experiment tells us nothing, not
    that the world said no. Reversing these two branches recreates the defect.

    `partial` is not in the image. Every outcome is supported / refuted / inconclusive /
    invalid-run, and `inconclusive` is DERIVED, never chosen — there is no verb, flag or
    field that sets it, which is what stops it becoming the drawer."""
    if rule in RESERVED_RULES:
        raise CruxError(f"combination rule '{rule}' is reserved, not implemented — see spec 15 "
                        f"(open question: whether `ordered` should ship at all). Use one of "
                        f"{', '.join(COMBINATION_RULES)}.")
    if rule not in COMBINATION_RULES:
        raise CruxError(f"unknown combination rule '{rule}' — use one of "
                        f"{', '.join(COMBINATION_RULES)}")
    hmet, hunmet, hna = hyp
    nmet, nunmet, nna = neutral
    n = hmet + hunmet + hna
    if rule == "m-of-n":
        if not isinstance(m, int) or not (1 <= m <= max(n, 1)):
            raise CruxError(f"rule 'm-of-n' needs `{RULE_M_FIELD}` set to an integer in "
                            f"1..{n} (got {m!r})")

    # 1-2. run validity. A control that failed, or that could not be read at all, leaves
    # "the claim is false" and "the apparatus is broken" indistinguishable — which is
    # exactly what `invalid-run` names. Fails safe.
    if nunmet:
        return "invalid-run"
    if nna:
        return "invalid-run"
    # 3. nothing was claimed: controls only.
    if n == 0:
        return "invalid-run"

    # 4-6. now, and only now, read the claim under its declared rule.
    if rule == "all":
        if hunmet:
            return "refuted"            # one veto decides the conjunction
        return "inconclusive" if hna else "supported"
    if rule == "any":
        if hmet:
            return "supported"
        return "inconclusive" if hna else "refuted"
    # m-of-n. The boundary is exact: m-1 is the "consider" tier (a near miss with a defined
    # next action), and two or more short is a failure of the declared rule. Making every
    # sub-threshold outcome inconclusive would mean m-of-n could never refute anything,
    # which is the drawer the spec warns about.
    if hmet >= m:
        return "supported"
    if hmet + hna >= m:
        return "inconclusive"           # the threshold is still reachable
    if hmet == m - 1:
        return "inconclusive"
    return "refuted"

def node_rule(n):
    """(rule, m) as declared in frontmatter, or (None, None) when several checks have no
    declaration. A hypothesis with exactly one claim-directed check defaults to `all`: for
    k=1 that is the same as `any` and the same as 1-of-1, so there is nothing to declare and
    demanding a declaration would be ceremony."""
    rule = str(n["fm"].get(RULE_FIELD) or "").strip() or None
    m = n["fm"].get(RULE_M_FIELD)
    if rule is None:
        return ("all", None) if sum(count_verifiables_by_kind(n["body"])[DEFAULT_KIND]) <= 1 \
               else (None, None)
    return rule, (m if isinstance(m, int) else None)

def rule_gap(n):
    """The message for a stamped hypothesis whose checks do not add up to anything — several
    claim-directed checks and no declared rule, or a rule crux will not honor — else None.
    Gated on the stamp, exactly like `neutral_gap`: a pre-15 hypothesis never declared one
    and is not asked to."""
    if n.type != "idea" or not binds_evidence_semantics(n):
        return None
    rule, m = node_rule(n)
    if rule is None:
        k = sum(count_verifiables_by_kind(n["body"])[DEFAULT_KIND])
        return (f"hypothesis '{n.id}': {k} claim-directed verifiables and no combination "
                f"rule. Declare how they add up BEFORE the run — `{RULE_FIELD}: "
                f"{' | '.join(COMBINATION_RULES)}` in frontmatter (with `{RULE_M_FIELD}: <m>` "
                f"for m-of-n) — or 'two of four passed' stays an argument instead of "
                f"arithmetic. Note the cost when choosing `all`: two checks at 80% power "
                f"each give 64% joint power, and thresholds may not be loosened to "
                f"compensate.")
    try:
        derive_verdict_15(count_verifiables_by_kind(n["body"])[DEFAULT_KIND],
                          count_verifiables_by_kind(n["body"])[NEUTRAL_KIND], rule, m)
    except CruxError as e:
        return f"hypothesis '{n.id}': {e}"
    return None

def derive_verdict(met, unmet, na):
    total = met + unmet + na
    if total == 0:                 return None
    if met == total:               return "supported"
    if unmet == 0 and na > 0:      return "inconclusive"
    if met == 0 and unmet > 0:     return "refuted"
    return "partial"

# ----------------------------------------------------------------------------- artifacts
def artifact_kind(path):
    ext = os.path.splitext(path)[1].lower()
    for kind, exts in ARTIFACT_KINDS.items():
        if ext in exts:
            return kind
    return "other"

def parse_artifacts(body, heading="artifacts"):
    """Bullets under `## Artifacts` as [{label, path, kind}], in document order. Two forms:

        - [Full report](results/h1/report.md)
        - results/h1/curve.png the ADE20K curve

    Either form may carry a trailing note, so the label comes from the link text when there
    is one and from the trailing text otherwise.

    The `_(placeholder)_` line and any prose are ignored. Pure — no filesystem access, so
    a node body can be parsed without a vault (and a pre-1.2 node with no such section
    simply yields []).

    `heading` is parameterised so the taskhub's `## Output` reuses this grammar verbatim
    rather than growing a second, subtly different one. The default keeps every existing
    caller byte-identical."""
    out, in_sec, in_comment = [], False, False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == heading
            continue
        if not in_sec:
            continue
        # HTML comments are guidance, not artifacts — the template's own example links
        # live in one, and a user may comment a line out. Track the block, skip it whole.
        if in_comment:
            in_comment = "-->" not in line
            continue
        if "<!--" in line:
            in_comment = "-->" not in line
            line = re.sub(r"<!--.*?-->", "", line)
        m = re.match(r"\s*-\s+(?!_\()(.+)$", line)
        if not m:
            continue
        text = m.group(1).strip()
        # Deliberately unanchored: a note after the closing paren is prose, not part of the
        # path. Anchoring here sent `- [Report](p.md) — a note` down the bare-path branch,
        # which split it on whitespace into the path '[Report'.
        link = re.match(r"\[([^\]]*)\]\(\s*([^)\s]+)\s*\)", text)
        if link:
            label, path = link.group(1).strip(), link.group(2).strip()
        else:
            parts = text.split(None, 1)
            path, label = parts[0], (parts[1].strip() if len(parts) > 1 else "")
        if not path:
            continue
        out.append({"label": label or os.path.basename(path), "path": path,
                    "kind": artifact_kind(path)})
    return out

def artifact_escapes(path):
    """True if a recorded path could reach outside the vault (absolute, drive-letter, or
    containing a `..` segment). Checked lexically, before anything touches the disk."""
    if not path or path.startswith(("/", "\\", "~")) or re.match(r"^[A-Za-z]:", path):
        return True
    return ".." in path.replace("\\", "/").split("/")

def results_files(root, hid):
    """Every non-hidden file under results/<hid>/ (recursive). The signal for 'this
    hypothesis has produced something on disk'."""
    d = os.path.join(root, RESULTS_DIR, hid)
    out = []
    if not os.path.isdir(d):
        return out
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = [x for x in dirnames if not x.startswith(".")]
        out += [os.path.join(dirpath, fn) for fn in sorted(filenames) if not fn.startswith(".")]
    return out

def artifact_problems(root, n):
    """Lint for one idea node: paths must stay in the vault and resolve, and a hypothesis
    that has produced files must link a report among them."""
    problems, arts = [], parse_artifacts(n["body"])
    for a in arts:
        if artifact_escapes(a["path"]):
            problems.append((n.id, f"hypothesis '{n.id}': artifact path must be inside the "
                                   f"vault: '{a['path']}'"))
        elif not os.path.isfile(os.path.join(root, a["path"])):
            problems.append((n.id, f"hypothesis '{n.id}': links missing artifact '{a['path']}'"))
    files = results_files(root, n.id)
    if files and not any(a["kind"] == "report" and not artifact_escapes(a["path"]) for a in arts):
        problems.append((n.id, f"hypothesis '{n.id}': {RESULTS_DIR}/{n.id}/ holds {len(files)} "
                               f"file(s) but no report is linked under '## Artifacts'"))
    return problems

def artifact_warnings(root, nid):
    """The same 'files on disk, no report linked' signal as a WARNING, for `crux close`.
    Closing must stay possible for a hypothesis that genuinely produced no files."""
    n = Vault(root).get(nid)
    if n.type != "idea":
        return []
    return [m for _, m in artifact_problems(root, n) if "no report is linked" in m]

# ----------------------------------------------------------------------------- ledger / gate / refresh
def ledger_counts(v, qid):
    """Pure roll-up of a question's direct children into JSON-able counts. Single source
    of truth shared by `ledger_block` (the markdown view) and `snapshot` (the GUI JSON)."""
    kids = v.children[qid]
    ideas = [v.nodes[k] for k in kids if v.nodes[k].type == "idea"]
    subqs = [v.nodes[k] for k in kids if v.nodes[k].type == "question"]
    # Generated from VERDICTS, never a hand-picked list of names: hard-coding the four
    # meant adding a fifth raised KeyError here and rendered nowhere in META.md.
    vc = {x: sum(1 for n in ideas if n["fm"].get("verdict") == x) for x in VERDICTS}
    return dict({"children": len(kids),
                 "ideas_total": len(ideas),
                 "ideas_done": sum(1 for n in ideas if n.status == "done"),
                 "subq_total": len(subqs),
                 "subq_resolved": sum(1 for n in subqs if n.status == "resolved")}, **vc)

def ledger_block(v, qid):
    kids = v.children[qid]
    if not kids:
        return "_(no children yet)_"
    ideas = [v.nodes[k] for k in kids if v.nodes[k].type == "idea"]
    subqs = [v.nodes[k] for k in kids if v.nodes[k].type == "question"]
    c = ledger_counts(v, qid)
    summary = (f"**{c['children']} children** · ideas {c['ideas_done']}/{c['ideas_total']} done "
               f"({', '.join(f'{x} {c[x]}' for x in VERDICTS)})")
    if subqs:
        summary += f" · sub-questions {c['subq_resolved']}/{c['subq_total']} resolved"
    rows = []
    for n in (ideas + subqs):
        if n.type == "idea":
            extra = []
            if n["fm"].get("verdict"): extra.append(f"verdict **{n['fm']['verdict']}**")
            if n["fm"].get("metric"):  extra.append(f"metric `{n['fm']['metric']}`")
            tail = (" — " + ", ".join(extra)) if extra else ""
            rows.append(f"- `{n.id}` [[{n.basename}|{n.title}]] — *{n.status}*{tail}")
        else:
            rows.append(f"- `{n.id}` _(Q)_ [[{n.basename}|{n.title}]] — *{n.status}*")
    return summary + "\n\n" + "\n".join(rows)

def refresh(root):
    """Recompute all derived content from the nodes. Idempotent. Returns True if anything changed on disk."""
    v = Vault(root)
    changed = False
    # review gate (two-directional): a non-resolved question is in `review` iff it has
    # >=1 child and all direct children are terminal; otherwise `open`. Recomputing both
    # directions each refresh corrects an intermediate trip — e.g. during a bulk seed
    # materialize, a question can momentarily have only a terminal child before its later
    # (non-terminal) children are added. `resolved` is human-set and never auto-changed.
    for qid, n in v.nodes.items():
        if n.type == "question" and n.status in ("open", "review"):
            kids = v.children[qid]
            terminal = bool(kids) and all(is_terminal(v.nodes[k]) for k in kids)
            n["fm"]["status"] = "review" if terminal else "open"
    # evidence ledger into each question file (engine-owned block only)
    for qid, n in v.nodes.items():
        if n.type == "question":
            n["body"] = replace_block(n["body"], LEDGER_START, LEDGER_END, ledger_block(v, qid))
    # persist questions (status + ledger) idempotently
    for qid, n in v.nodes.items():
        if n.type == "question":
            if write_if_changed(n["path"], render_doc(n["fm"], n["body"])):
                changed = True
    # regenerate views
    import render
    if write_if_changed(os.path.join(root, "META.md"), render.render_meta(v)):        changed = True
    if write_if_changed(os.path.join(root, "EXPERIMENTS.md"), render.render_experiments(v)): changed = True
    if wiki_active(root):
        if write_if_changed(os.path.join(root, WIKI_INDEX), render.render_wiki(v, root)): changed = True
    if rd_active(root):
        if write_if_changed(os.path.join(root, RD_INDEX), render.render_rd(v, root)):     changed = True
    # The taskhub's INDEX is generated; a task never is. `refresh` writes TASKHUB.md and
    # nothing under tasks/ — that asymmetry is the whole spec-kit lesson, and selftest
    # byte-compares tasks/ across this call to keep it true.
    if task_active(root):
        if write_if_changed(os.path.join(root, TASK_INDEX), render.render_taskhub(v, root)): changed = True
    return changed

# ----------------------------------------------------------------------------- validation
# ----------------------------------------------------------------------------- node economy (v1.3)
_PLACEHOLDER = re.compile(r"^\s*_\(.*\)_\s*$")

def _prose_tokens(text):
    """Whitespace-separated words in a prose section, minus the two things that are guidance
    rather than content: HTML comments, and a line that is nothing but a `_(placeholder)_`.
    Dropping placeholders matters — otherwise a node spends part of its budget on the
    template's own prompts before anyone has written a word."""
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.S)
    return " ".join(l for l in text.splitlines() if not _PLACEHOLDER.match(l)).split()

def prose_words(body, node_type):
    """Words of prose in a node body, counting only PROSE_SECTIONS. Pure — no vault, no
    filesystem — so it can be called on a string, and a pre-1.3 node with no `## ELI5`
    simply contributes zero for that section instead of raising.

    The ledger is split off first: it is generated, it can run to hundreds of words on a
    busy question, and it lives *under* `## Answer so far`, so `_section` would otherwise
    swallow it and make every question with children look over-cap."""
    pre = body.split(LEDGER_START)[0]
    return sum(len(_prose_tokens(_section(pre, h))) for h in PROSE_SECTIONS.get(node_type, ()))

def unrun_children(v, qid):
    """Hypotheses under `qid` that have never been staged, run or closed — the ones that are
    pure intent. A question stockpiling these is the fan-out failure mode."""
    return [c for c in v.children.get(qid, [])
            if v.nodes[c].type == "idea" and v.nodes[c].status == "idea"]

def economy_warnings(v):
    """Nodes whose counted prose exceeds PROSE_CAP."""
    out = []
    for nid, n in v.nodes.items():
        if n.type not in PROSE_SECTIONS:
            continue
        w = prose_words(n["body"], n.type)
        if w > PROSE_CAP:
            out.append((nid, f"{n.type} '{nid}': {w} words of prose, over the {PROSE_CAP}-word cap "
                             f"(verifiables, artifacts and the ledger are not counted). Compress it, "
                             f"or move the detail somewhere it belongs."))
    return out

def lock_warnings(v):
    """A hypothesis whose commitment was only hashed at `close` was never pre-registered —
    the checks and the results were visible at the same moment. A warning, not a problem:
    the work is recorded honestly, it just carries no commitment."""
    out = []
    for nid, n in v.nodes.items():
        if n.type == "idea" and n["fm"].get(LOCK_WHERE_FIELD) == "close":
            out.append((nid, f"hypothesis '{nid}': closed without ever going `running`, so its "
                             f"verifiables were never pre-registered — they were locked at "
                             f"close, with the results already visible."))
    return out

def fanout_warnings(v):
    """Questions holding more unrun hypotheses than FANOUT_MAX."""
    out = []
    for nid, n in v.nodes.items():
        if n.type != "question":
            continue
        k = len(unrun_children(v, nid))
        if k > FANOUT_MAX:
            out.append((nid, f"question '{nid}': {k} hypotheses proposed and none of them run "
                             f"(cap {FANOUT_MAX}). Run or close some before adding more."))
    return out

def fanout_pressure(v, qid):
    """The back-pressure message for the hypothesis about to be created under `qid`, or None
    when there is room. Fires at exactly FANOUT_MAX because the node being added is the one
    that breaches — warning after the fact is a warning too late."""
    k = len(unrun_children(v, qid))
    if k >= FANOUT_MAX:
        return (f"question '{qid}' already holds {k} unrun hypotheses (cap {FANOUT_MAX}) — "
                f"this one puts it over. Run or close some before proposing more.")
    return None

def null_problem(text, schema=1):
    """The message for a null that fails a goalpost, or None. `schema` is the node's
    generation: a pre-15 node is never asked for one, so 0 always passes.

    Pure — takes a string, so the goalposts are testable without a vault."""
    if schema < 1:
        return None
    lines = [l for l in (text or "").splitlines() if l.strip()]
    if not lines:
        return (f"no null declared. Name the BORING explanation — the cheapest way this "
                f"result could be trivially true — as one line naming a family from: "
                f"{', '.join(CONFOUND_FAMILIES)}.")
    if len(lines) > 1:
        return (f"{len(lines)} nulls declared; there is exactly one. The null is the single "
                f"cheapest boring explanation, not a list of everything that could go wrong.")
    one = lines[0].strip()
    words = len(one.split())
    if words > NULL_MAX_WORDS:
        return (f"the null runs to {words} words, over the {NULL_MAX_WORDS}-word cap. It is "
                f"one line: a family and its instance, not an argument.")
    fam = one.lower().split()
    if not any(f in fam or any(w.startswith(f) for w in fam) for f in CONFOUND_FAMILIES):
        return (f"the null names no confound family. Pick one of "
                f"{', '.join(CONFOUND_FAMILIES)} and name the instance — the closed list is "
                f"what stops an exotic null nobody can test against.")
    return None

def scenario_gap(n):
    """The `validate`/gate message for a hypothesis' failure scenarios, or None.

    Two checks, and they are total per spec 09:
      1. at least one verifiable discriminates against the declared null, and
      2. every verifiable has a non-empty failure scenario, no two byte-identical.

    Byte-identity is all the engine can honestly check — it cannot tell whether two
    differently-worded scenarios describe the same world. It catches copy-paste; the rest is
    `crux-critic`'s job, which is precisely why the scenarios are written down at all."""
    if n.type != "idea" or node_schema(n) < 2:
        return None
    lines = _verifiable_lines(n["body"])
    scen = verifiable_scenarios(n["body"])
    if not lines:
        return None
    missing = [i + 1 for i, s in enumerate(scen) if not (s["fails_if"] or "").strip()]
    if missing:
        return (f"hypothesis '{n.id}': verifiable(s) {', '.join(map(str, missing))} have no "
                f"failure scenario. Every check had to name a world where IT fails and the "
                f"others pass to earn its place — write that world on an indented "
                f"`fails-if:: …` line under the check (`--fails-if` at creation).")
    seen = {}
    for i, s in enumerate(scen):
        key = " ".join(s["fails_if"].lower().split())
        if key in seen:
            return (f"hypothesis '{n.id}': verifiables {seen[key] + 1} and {i + 1} declare the "
                    f"SAME failure scenario, so they fail for the same reason and one of them "
                    f"is redundant. Two checks are distinct only if you can name a world where "
                    f"one fails and the other passes.")
        seen[key] = i
    hyp_idx = [i for i, (_t, txt) in enumerate(lines) if verifiable_kind(txt)[0] == DEFAULT_KIND]
    if hyp_idx and not any(scen[i]["discriminates"] for i in hyp_idx):
        return (f"hypothesis '{n.id}': no verifiable discriminates against the declared null. "
                f"Mark the one that does with a `discriminates:: true` line under it "
                f"(`--discriminates` at creation) — "
                f"without it the checks can all pass while the boring explanation is the true "
                f"one, which is the whole failure the null exists to catch.")
    return None

def null_gap(n):
    """The `validate`/gate message for a hypothesis' null, or None. Gated on the stamp, so a
    pre-15 hypothesis is never asked for one."""
    if n.type != "idea" or not binds_evidence_semantics(n):
        return None
    p = null_problem(_null_text(n) or "", node_schema(n))
    if p:
        return f"hypothesis '{n.id}': {p}"
    if n["fm"].get(NULL_APPROVED) and n["fm"].get("null_hash") != _null_hash(n):
        return (f"hypothesis '{n.id}': the null was EDITED after approval, so the approval no "
                f"longer stands. A different null is a different claim about what would be "
                f"boring, and checks written against the old one discriminate against "
                f"nothing. Re-approve with `crux approve-null {n.id}`.")
    if not str(n["fm"].get(NULL_APPROVED) or "").strip():
        return (f"hypothesis '{n.id}': the null is declared but not approved. The null IS the "
                f"bar restated, and the bar is the PI's call — `crux approve-null {n.id}` "
                f"once they have read it. Checks are written against an APPROVED null.")
    return None

def _fm_text(n, field):
    txt = str(n["fm"].get(field) or "").strip()
    return txt or None

def node_measurement(n):
    """What this hypothesis measures, declared before the run — or None. Never `metric`,
    which is the result written at close."""
    return _fm_text(n, MEASUREMENT_FIELD)

def node_replicates(n):
    """The declared n / replication plan, or None. Free text on purpose: "5 seeds x 3 folds"
    and "n = 12 per arm" are both honest, and neither parses into a number the engine could
    use without inventing a statistical model."""
    return _fm_text(n, REPLICATES_FIELD)

def neutral_gap(n):
    """The message for a stamped hypothesis that has no outcome-neutral verifiable and no
    written opt-out, or None when it is satisfied. Spec 15 §1.

    Gated on the node's stamp, never on its status: a pre-15 hypothesis is *correct* without
    a control — the bar did not exist when the work was done — and retro-flagging it would
    put a working vault into permanent red against a rule it could not have known."""
    if n.type != "idea" or not binds_evidence_semantics(n):
        return None
    if count_verifiables_by_kind(n["body"])[NEUTRAL_KIND] != (0, 0, 0):
        return None
    if str(n["fm"].get(NEUTRAL_OPTOUT) or "").strip():
        return None
    return (f"hypothesis '{n.id}': no outcome-neutral verifiable. Without a passing control, "
            f"'the claim is false' and 'the apparatus is broken' are indistinguishable "
            f"(assay sensitivity). Add one with `-n \"<check>\"`, or record an explicit "
            f"opt-out in frontmatter: `{NEUTRAL_OPTOUT}: <why this claim has no meaningful "
            f"positive control>`.")

def validate(v):
    problems = []
    req = {"project": ["id","type","title","status"],
           "question":["id","type","title","status","parent"],
           "idea":    ["id","type","title","status","parent"],
           "synthesis":["id","type","title"]}
    for nid, n in v.nodes.items():
        t = n.type
        if t == "task":
            # `Vault` keys on the presence of `id`, not on `type`, so a task written to the
            # vault root lands in v.nodes and would otherwise be reported as `unknown type
            # 'task'` — a true message pointing at entirely the wrong thing.
            problems.append((nid, f"task '{nid}': a task must live under {TASK_DIR}/ "
                                  f"(found at the vault root); move the file, or create it "
                                  f"with `crux task add`")); continue
        if t not in TYPES:
            problems.append((nid, f"unknown type '{t}'")); continue
        for k in req[t]:
            if n["fm"].get(k) in (None, ""):
                problems.append((nid, f"missing required field '{k}'"))
        if t == "question" and n.status not in QUESTION_STATUS:
            problems.append((nid, f"bad question status '{n.status}'"))
        if t == "idea" and n.status not in IDEA_STATUS:
            problems.append((nid, f"bad idea status '{n.status}'"))
        if t == "idea" and n["fm"].get("verdict") not in (None, "", *VERDICTS):
            problems.append((nid, f"bad verdict '{n['fm'].get('verdict')}'"))
        # parent integrity
        if t in ("question", "idea"):
            p = n.parent
            if p not in v.nodes:
                problems.append((nid, f"parent '{p}' does not exist"))
            else:
                pt = v.nodes[p].type
                if t == "idea" and pt != "question":
                    problems.append((nid, f"idea parent must be a question, got '{pt}'"))
                if t == "question" and pt not in ("project", "question"):
                    problems.append((nid, f"question parent must be project/question, got '{pt}'"))
        # running/done ideas need verifiables
        if t == "idea" and n.status in ("running", "done"):
            if sum(count_verifiables(n["body"])) == 0:
                problems.append((nid, f"idea is '{n.status}' but has no verifiables"))
        if t == "idea" and node_schema(n) >= 2 and n.status not in ("running", "done"):
            g = scenario_gap(n)
            if g and "SAME failure scenario" in g:
                problems.append((nid, g))     # redundancy is wrong on sight, not at run time
        # a malformed null is wrong the moment it is written, not when the run starts —
        # otherwise a draft accumulates nulls nobody can act on
        if t == "idea" and binds_evidence_semantics(n):
            written = _null_text(n)
            if written:
                p = null_problem(written, node_schema(n))
                if p:
                    problems.append((nid, f"hypothesis '{nid}': {p}"))
        # a declared rule crux will not honor is wrong the moment it is written, not the
        # moment the run starts — `ordered` in particular is reserved, and a vault must never
        # be able to carry one
        if t == "idea" and binds_evidence_semantics(n):
            declared = str(n["fm"].get(RULE_FIELD) or "").strip()
            if declared and declared not in COMBINATION_RULES:
                why = ("is reserved, not implemented — see spec 15"
                       if declared in RESERVED_RULES else "is not a combination rule")
                problems.append((nid, f"hypothesis '{nid}': rule '{declared}' {why}. Use one "
                                      f"of {', '.join(COMBINATION_RULES)}."))
        # evidence semantics: a kind tag crux does not recognize is a typo, not a kind. It
        # is left on the line rather than swallowed, and raised here.
        if t == "idea" and binds_evidence_semantics(n):
            for _, text in _verifiable_lines(n["body"]):
                bad = unknown_kind_tag(text)
                if bad:
                    problems.append((nid, f"hypothesis '{nid}': unknown verifiable kind "
                                          f"'[{bad}]' — use "
                                          f"{' or '.join('[%s]' % k for k in VERIFIABLE_KINDS)}"))
        # ...and once a run has actually started, the control requirement bites
        if t == "idea" and n.status in ("running", "done"):
            for gap in (neutral_gap(n), rule_gap(n), null_gap(n), scenario_gap(n)):
                if gap:
                    problems.append((nid, gap))
        # lineage (spec 05). Exactly one problem per node, and only when the field is
        # written: its ABSENCE is the norm and must read as it always did.
        if t == "idea" and node_builds_on(n):
            g = builds_on_problem(v, n)
            if g:
                problems.append((nid, g))
        if t == "idea" and lock_drift(n):
            problems.append((nid, f"hypothesis '{nid}': DRIFT — the verifiables, their kinds "
                                  f"or the combination rule changed after the commitment was "
                                  f"locked at {n['fm'].get(LOCKED_AT_FIELD)}. The edit stands "
                                  f"(research does discover a check was wrong); the flag is "
                                  f"permanent. `git log -p {n['fn']}` is the diff."))
        # evidence artifacts: paths resolve, stay in the vault, and a hypothesis that
        # produced files links a report among them
        if t == "idea":
            problems += artifact_problems(v.root, n)
        # ledger markers present in questions
        if t == "question" and (LEDGER_START not in n["body"] or LEDGER_END not in n["body"]):
            problems.append((nid, "missing ledger markers"))
    # cycle / single-parent tree
    for nid, n in v.nodes.items():
        seen, cur = set(), nid
        while cur in v.nodes and v.nodes[cur].parent:
            cur = v.nodes[cur].parent
            if cur in seen:
                problems.append((nid, "parent cycle detected")); break
            seen.add(cur)
    return problems

# ----------------------------------------------------------------------------- glossary (spec 14)
# `glossary.md` is NOT a definition store — it is a model of the PI's vocabulary. Presence
# means the agent may use the word bare; absence means gloss it, or ask. The one-line
# definition each entry carries is for the PI to read back later; the MEMBERSHIP is what the
# agent consumes.
#
# It is separate from the wiki because the wiki's flow rule (literature → wiki, never the
# reverse) structurally forbids project-COINED terms — "detection floor", "capacity
# certificate" — and those are exactly the terms most likely to be used bare at a PI who has
# never had them defined, because the agent invented them and therefore finds them obvious.
#
# The file is the PI's. The engine reads it, and writes it only where the PI said so
# (`crux glossary accept|decline`). Everything here is total: a missing file, a missing
# section, a hand-edited line and free prose between entries all read as data, never as an
# error.
_GLOSS_TERM = re.compile(r"^\s*[-*]\s+\*\*(?P<term>[^*]+?)\*\*\s*(?:[—:-]\s*(?P<def>.*))?$")
_GLOSS_PLAIN = re.compile(r"^\s*[-*]\s+(?P<term>.+?)\s*$")
_GLOSS_HINT = re.compile(r"^\s*_\(.*\)_\s*$")

def _deplural(tok):
    """Strip ONE trailing plural from a token. Deliberately not a stemmer: `-es` only after
    a sibilant, `-s` never after `ss`, and never on a token short enough that the `s` is
    probably part of the word."""
    if len(tok) > 3 and tok.endswith("es") and tok[-3] in "sxzho":
        return tok[:-2]
    if len(tok) > 3 and tok.endswith("s") and not tok.endswith("ss"):
        return tok[:-1]
    return tok

def glossary_key(term):
    """The canonical key for a term: casefold, collapse every run of spaces/tabs/hyphens/
    underscores to one space, depluralize the FINAL token only.

    One normalizer serves both matching (spec 14's counting rule) and identity (is this the
    term the PI already declined?). That is deliberate: if the two could differ, a declined
    term would come back under a different hyphenation and the PI would answer the same
    question forever — which is the exact failure the decline list exists to prevent."""
    toks = [t for t in re.split(r"[-_\s]+", str(term or "").strip().lower()) if t]
    if not toks:
        return ""
    return " ".join(toks[:-1] + [_deplural(toks[-1])])

def parse_glossary(text):
    """`glossary.md` → {"terms": [{term, definition, key}], "declined": [term, …]}.

    Pure: takes a string, not a path, so it is unit-testable with no vault — the shape
    `prose_words` and `count_verifiables` already use."""
    terms, declined, section = [], [], None
    for line in str(text or "").splitlines():
        s = line.strip()
        if s.startswith("## "):
            h = s[3:].strip().lower()
            section = "terms" if h == "terms" else ("declined" if h == "not jargon" else None)
            continue
        if not s or section is None or _GLOSS_HINT.match(line):
            continue
        if section == "terms":
            m = _GLOSS_TERM.match(line)
            if m:
                t = " ".join(m.group("term").split())
                terms.append({"term": t, "definition": (m.group("def") or "").strip(),
                              "key": glossary_key(t)})
            continue
        m = _GLOSS_PLAIN.match(line)
        if m:
            declined.append(" ".join(m.group("term").split()))
    return {"terms": terms, "declined": declined}

def glossary_path(root):
    return os.path.join(root, GLOSSARY_FILE)

def load_glossary(root):
    """The vault's vocabulary model. An absent file is an EMPTY model, never an error:
    a pre-14 vault is correct, not broken, and nothing here may create the file."""
    p = glossary_path(root)
    return parse_glossary(read(p) if os.path.isfile(p) else "")

# --- counting a proposed term (spec 14, PRD 14.1) ------------------------------------
# THE RULE, and it is one sentence on purpose:
#
#   A term matches when its words appear consecutively INSIDE ONE MARKDOWN BLOCK,
#   case-insensitively, separated by any run of spaces, tabs, hyphens or underscores, with
#   the last word optionally carrying a trailing `s` or `es`.
#
# Settled empirically rather than by argument. Spec 14 guessed that "normalizing case and
# trailing plurals is probably enough"; measured against the three shipped example vaults,
# it is not. That rule fixes every plural case and ZERO hyphenation cases, and hyphenation is
# where the variance actually lives — "dense contrastive pretraining" is written 9 times
# unhyphenated and 7 times hyphenated by the same author in the same vault. Under the guess,
# "mask transformer head" scores 0 documents despite 12 occurrences across 3 documents, two
# of them node titles, and the centrality filter would silently drop the most obviously
# coined term in the vault.
#
# Block scoping is equally forced: allowing a newline inside the separator run produced 27
# measured false positives where a heading's last word glued to the body's first
# ("## Run Links" + "- job 40012" matching 'links job' in 8 documents). Every crux node is
# built from headings and bullets, so that fires constantly.
#
# Depluralizing EVERY token was tested and rejected: identical on all 17 probe terms, with a
# 114-candidate over-match tail of verbs and function words ("transfers to", "orders of").
#
# Derivational morphology is deliberately out: "label efficiency" does not match
# "label-efficient". Those are different words, and a PI who agreed to one has not agreed to
# the other.
_BLOCK_START = re.compile(r"^\s*(?:[-*+>]|\d+[.)]|\|)")
_TERM_SEP = r"[-_‐‑ \t]+"
MAX_TERM_WORDS = 5

def glossary_blocks(body, title=""):
    """Markdown → a list of flattened, lowercased blocks.

    Blocks break on blank lines and at the start of a heading, list item, blockquote or table
    row, so a term can never be assembled across markdown structure. Within a block, lines
    are joined — an intra-paragraph line wrap still counts as one phrase.

    Dropped first, for the same reasons `_prose_tokens` drops them: the generated ledger
    (it repeats child titles, which would let a term reach a second document without a second
    real use), HTML comments, and `_(placeholder)_` lines (template prompts, not content)."""
    text = str(body or "")
    pre = text.split(LEDGER_START)[0]
    if LEDGER_END in text:
        pre += "\n\n" + text.split(LEDGER_END)[-1]
    pre = re.sub(r"<!--.*?-->", " ", pre, flags=re.S)
    out, cur = ([str(title).strip().lower()] if str(title or "").strip() else []), []
    for line in pre.splitlines():
        s = line.strip()
        if not s or _PLACEHOLDER.match(line):
            if cur: out.append(" ".join(cur)); cur = []
            continue
        if s.startswith("#") or _BLOCK_START.match(line):
            if cur: out.append(" ".join(cur)); cur = []
            out.append(s.lstrip("#").strip().lower())
            continue
        cur.append(s)
    if cur:
        out.append(" ".join(cur))
    return [b for b in out if b]

def term_pattern(term):
    """A compiled regex implementing the rule above. Every token is escaped, so a term
    containing regex metacharacters (`c++ kernel`) is matched literally rather than
    exploding."""
    toks = [t for t in re.split(r"[-_\s]+", str(term or "").strip().lower()) if t]
    if not toks:
        return re.compile(r"(?!x)x")        # matches nothing
    parts = [re.escape(t) for t in toks[:-1]] + [re.escape(_deplural(toks[-1])) + r"(?:e?s)?"]
    return re.compile(r"(?<![\w-])" + _TERM_SEP.join(parts) + r"(?![\w-])", re.I)

def glossary_corpus(v):
    """The documents a term is counted over: (id, title, body) per node and per compiled wiki
    page. Excluded by construction — generated views (META/EXPERIMENTS/WIKI/RD/TASKS: counting
    them would double-count every node), `raw/` sources (the wiki layer's standing invariant
    is that the engine never reads a source's CONTENT, only its bytes), `results/` artifacts,
    `wiki/log.md` and `wiki/SCHEMA.md` (not `type: wiki`), and `glossary.md` itself (a term is
    trivially central in the file that defines it)."""
    docs = [(nid, n.title or "", n["body"]) for nid, n in v.nodes.items()]
    for p in scan_wiki_pages(v.root):
        docs.append(("wiki:" + p["slug"], p["title"] or "",
                     (p["summary"] or "") + "\n\n" + p["body"]))
    return docs

def count_term(v, term):
    """Where a term appears and how often: {"documents": [id…], "occurrences": N,
    "titles": [id…], "per_document": {id: n}}.

    Pure read — builds nothing, writes nothing, and is deterministic on an unchanged vault,
    which is what makes a term that fails centrality today pass next month with no memory
    beyond the vault itself."""
    rx = term_pattern(term)
    docs, per, titles, total = [], {}, [], 0
    for nid, title, body in sorted(glossary_corpus(v)):
        k = sum(len(rx.findall(b)) for b in glossary_blocks(body, title))
        if k:
            docs.append(nid); per[nid] = k; total += k
        if rx.search(str(title or "").lower()):
            titles.append(nid)
    return {"documents": docs, "occurrences": total, "titles": titles, "per_document": per}

# --- the centrality filter (spec 14, PRD 14.2) ----------------------------------------
# THE INVERSION, and it is the load-bearing design choice in spec 14:
#
#   The agent proposes candidate terms freely. The engine FILTERS them by centrality.
#   The engine does not generate the list.
#
# Deterministic extraction from prose does not work for the terms that matter. "detection
# floor", "capacity certificate" and "the separability condition" are bigrams and trigrams,
# and n-gram frequency over research prose is noisy in both directions — it misses real
# multi-word jargon and floods the list with ordinary phrases that recur. Measured on the
# shipped example vaults, the top bigrams are "of the", "rather than", "it is".
#
# An agent reading vault prose recognizes a coined multi-word term effortlessly; counting
# where it occurs is exactly what an agent is bad at and code is good at. Each side does the
# half it is suited to, and the deterministic part stays the GOALPOST rather than the
# generator — which is what spec 09's rule 1 actually asks for.
#
# The filter is still the whole guarantee: a term the agent finds interesting but which
# appears once is silently dropped and never reaches the PI. Agent enthusiasm cannot become
# PI interruptions.
#
# Hand-written, ~250 entries, deliberately not sourced from NLTK or scikit-learn: crux takes
# no third-party dependency, and a pasted word list is a third-party artifact with a licence
# even when it is only data. Function words only — it exists to stop a proposal of "the data",
# not to do extraction, which is the agent's job.
GLOSSARY_STOPLIST = frozenset("""
a about above after again against all almost along already also although always am among an
and another any anybody anyone anything are around as at away back be became because become
becomes been before began begin behind being below beside besides best better between beyond
both but by came can cannot come could did different do does doing done down due during each
early either else enough especially even ever every everybody everyone everything except far
few fewer first five for found four from full further gave get give given go goes going gone
got great had half has have having he hence her here hers herself him himself his how however
i if in indeed inside instead into is it its itself just keep kept know known large last late
later least left less let like likely little long look made main make makes making many may
maybe me mean means might mine more moreover most mostly much must my myself near nearly need
neither never new next no nobody none nor not nothing now number of off often on once one only
onto or other others otherwise ought our ours ourselves out outside over own part particular
per perhaps possible put quite rather really result results right said same saw say says second
see seem seems seen several shall she should show shown side similar since six small so some
somebody someone something sometimes soon still such sure take taken than that the their theirs
them themselves then thence there therefore these they thing things think third this those
though three through throughout thus time to together too took toward towards two under unless
until up upon us use used uses using usually very via want was way we well went were what when
whence where whereas whether which while who whom whose why will with within without would yes
yet you your yours yourself
""".split())

def _proposal_key(term):
    """Validate and canonicalize one proposed term. Raises rather than silently dropping —
    a malformed proposal is a bug in the caller, and swallowing it would look identical to
    the term failing centrality, which is the one thing the filter must be unambiguous about."""
    t = " ".join(str(term or "").split())
    if not t:
        raise CruxError("glossary: an empty term was proposed")
    n = len([x for x in re.split(r"[-_\s]+", t) if x])
    if n > MAX_TERM_WORDS:
        raise CruxError(f"glossary: {t!r} is {n} words; a term is 1–{MAX_TERM_WORDS} "
                        f"(a longer phrase is a sentence, and its count means nothing)")
    return glossary_key(t)

def glossary_candidates(root, propose, v=None):
    """Filter agent-proposed terms by centrality; return the survivors.

    CENTRALITY, exactly as spec 14 settles it: a term survives when it appears in >= 2
    distinct nodes or wiki pages, OR appears in any node title or wiki page title.

    Documents gate; occurrences ride along in the payload. The spec states the rule in
    documents and one work item in occurrences — they differ on precisely the case the filter
    exists to suppress (a term said twice in ONE node), so the document reading wins.

    Then four subtractions, all through `glossary_key`, so a difference of case, hyphen or
    plural can never resurrect a settled term: already accepted, already declined, already a
    wiki page (title or slug), or a stoplisted single word.

    Dropped terms are NOT returned. The filter's guarantee is that a dropped term never
    reaches the PI; emitting it as "dropped" would put it back on the PI's screen through the
    side door."""
    if not propose:
        return []
    v = v or Vault(root)
    g = load_glossary(root)
    settled = {t["key"] for t in g["terms"]} | {glossary_key(d) for d in g["declined"]}
    for p in scan_wiki_pages(root):
        settled.add(glossary_key(p["slug"]))
        if p["title"]:
            settled.add(glossary_key(p["title"]))
    out, seen = [], set()
    for term in propose:
        key = _proposal_key(term)
        if key in seen or key in settled:
            continue
        seen.add(key)
        if " " not in key and key in GLOSSARY_STOPLIST:
            continue
        c = count_term(v, term)
        # SPEC 16'S ONE EXCEPTION, and it is narrow. crux's own process vocabulary — "review
        # gate", "verifiable", "synthesis" — is jargon the PI has not agreed to exactly like
        # a coined project term, and spec 16 routes its permanent graduation through this
        # flow. But it appears nowhere in the corpus centrality counts: the terms live in the
        # SKILL and the conversation, not in the vault's prose. Without the waiver the
        # graduation path is dead on arrival, and a PI who has said "gate" fifty times can
        # never be offered the word.
        #
        # The waiver does not weaken the guarantee it sits inside. The filter exists so that
        # agent enthusiasm cannot become PI interruptions, and CRUX_LEXICON is a closed,
        # measured list of 38 terms — not something an agent can grow at proposal time.
        crux_own = key in CRUX_LEXICON
        if not crux_own and len(c["documents"]) < 2 and not c["titles"]:
            continue
        n, t = len(c["documents"]), len(c["titles"])
        out.append({"term": " ".join(str(term).split()), "key": key,
                    "documents": c["documents"], "occurrences": c["occurrences"],
                    "titles": c["titles"], "per_document": c["per_document"],
                    "crux_vocabulary": crux_own,
                    "reason": ("crux's own vocabulary, which the PI has been using"
                               if crux_own and not c["documents"] and not c["titles"] else
                               f"{n} document{'' if n == 1 else 's'}"
                               + (f", {t} title{'' if t == 1 else 's'}" if t else ""))})
    return out

def glossary_info(cands):
    """The `glossary:` info line. One line for the batch, not one per term — the PI answers
    them inline, one at a time, and the lint's job is only to say they are waiting."""
    if not cands:
        return []
    n = len(cands)
    return [("glossary:candidates",
             f"{n} vocabulary candidate{'' if n == 1 else 's'} passed centrality: "
             f"{', '.join(repr(c['term']) for c in cands)}. Ask the PI yes/no, one at a "
             f"time, then record it with `crux glossary accept|decline`.", n)]

def ensure_glossary(root):
    """Create `glossary.md` from the template if it is absent. Called at `init`, and by the
    PI's own accept/decline — never by a read path, so an existing vault gains the file only
    when the PI has actually said something."""
    p = glossary_path(root)
    if not os.path.isfile(p):
        write_if_changed(p, load_template("glossary"))
    return p

# --- the write path (spec 14, PRD 14.3) -----------------------------------------------
# THE ONLY PLACE THE ENGINE WRITES glossary.md. Membership is a claim about the PI — "these
# are words I know" — so only the PI can make it. The agent proposes and never writes; this
# is what makes that mechanical rather than aspirational, because there is exactly one verb
# that touches the file and it is in no agent's toolbelt.
#
# Entries are rewritten as whole SECTIONS, sorted by key, and everything else in the file
# (the header prose, a note the PI added by hand, a blank line they liked) is passed through
# untouched. The file is theirs; the engine only maintains the two lists inside it.
def _render_glossary(text, terms, declined):
    """Put `terms` and `declined` back into `text`, replacing ONLY the two section bodies.

    Entry lines are regenerated; every other line — the header prose, the italic hint, a note
    the PI added by hand, their blank lines — passes through untouched. The file is theirs;
    the engine maintains the two lists inside it and nothing else.

    Each section is rebuilt as: heading, then any prose the PI kept there (the italic hint),
    then the entries — with exactly one blank line between groups. Rebuilding rather than
    patching is what makes it a FIXED POINT: rendering an already-rendered file returns the
    same bytes, so a no-op accept really is a no-op on disk."""
    groups, order = {}, []          # section name -> [prose lines]; None = outside both
    cur = None
    for line in text.splitlines():
        if line.startswith("## "):
            h = line[3:].strip().lower()
            cur = "terms" if h == "terms" else ("declined" if h == "not jargon" else None)
            if cur is None:
                groups.setdefault("_tail", []).append(line); order.append("_tail")
            continue
        if cur is None:
            groups.setdefault("_head" if not order else "_tail", []).append(line)
            continue
        if _GLOSS_TERM.match(line) or (cur == "declined" and _GLOSS_PLAIN.match(line)
                                       and not _GLOSS_HINT.match(line)):
            continue                # an entry: regenerated, never preserved
        groups.setdefault(cur, []).append(line)

    def block(name, heading, rows):
        prose = [l for l in groups.get(name, []) if l.strip()]
        out = [heading]
        if prose:
            out += [""] + prose
        if rows:
            out += [""] + rows
        return out

    head = [l for l in groups.get("_head", []) if l.strip() or True]
    while head and not head[-1].strip():
        head.pop()
    lines = head + [""] if head else []
    lines += block("terms", "## Terms",
                   [f"- **{t['term']}** — {t['definition']}" for t in terms])
    lines += [""] + block("declined", "## Not jargon", [f"- {d}" for d in declined])
    tail = [l for l in groups.get("_tail", []) if l.strip()]
    if tail:
        lines += [""] + tail
    return "\n".join(lines).rstrip() + "\n"

def _glossary_write(root, term, definition, declining):
    """Shared body of accept/decline: idempotent, and EXCLUSIVE — a term is in exactly one of
    the two lists, so accepting a declined term moves it and vice versa. The move is reported
    rather than done silently: a PI who loses track of their own decline list has lost the
    thing that stops the same question being asked forever."""
    t = " ".join(str(term or "").split())
    if not t:
        raise CruxError("glossary: a term is required")
    key = _proposal_key(t)
    if not declining and not str(definition or "").strip():
        raise CruxError(f"glossary: accepting {t!r} needs a one-line definition (-d) — "
                        "membership without a read-back line defeats half the file's purpose")
    p = ensure_glossary(root)
    g = parse_glossary(read(p))
    terms = [x for x in g["terms"] if x["key"] != key]
    declined = [d for d in g["declined"] if glossary_key(d) != key]
    moved = (len(terms) != len(g["terms"])) if declining else (len(declined) != len(g["declined"]))
    if declining:
        declined.append(t)
    else:
        terms.append({"term": t, "definition": " ".join(str(definition).split()), "key": key})
    terms.sort(key=lambda x: x["key"])
    declined.sort(key=glossary_key)
    write_if_changed(p, _render_glossary(read(p), terms, declined))
    return {"term": t, "key": key, "state": "declined" if declining else "accepted",
            "moved": moved}

def cmd_glossary_accept(root, term, definition):
    """Record that the PI knows this word. It may now be used bare."""
    return _glossary_write(root, term, definition, declining=False)

def cmd_glossary_decline(root, term):
    """Record that the PI does not want this word in the glossary — asked once, ever."""
    return _glossary_write(root, term, None, declining=True)

def cmd_glossary_list(root):
    """The vocabulary model, read-only. Creates nothing: a pre-14 vault stays pre-14 until
    the PI actually says something."""
    return load_glossary(root)

# ----------------------------------------------------------------------------- science voice (spec 16)
# THE FRAME, and it decides everything below: the PI is the advisor, the agent is the grad
# student, and crux is the grad student's notebook. A grad student does not tell their
# advisor "q19 is solved" — the advisor would ask what the hell q19 is. They say the science.
#
# So crux's own vocabulary — node ids AND process terms — is unagreed jargon under spec 14's
# model of the PI's vocabulary, and the agent never introduces it in chat. The PI using a
# word licenses it back: THE MIRROR RULE. Persistence is split, because the two halves decay
# differently. Ids are ephemeral handles licensed for one conversation only ("the PI knew
# what q19 was in March" will not be true in April); process terms graduate permanently
# through the glossary flow spec 14 already built.
#
# This is a lint, not a filter. It reads a conversation and reports; nothing here rewrites a
# sentence, and nothing here runs at chat time. Its consumers are the persona eval and
# selftest, which is the point: spec 06 settled that instructions were never the binding
# constraint on agent behaviour — the modeled dialogues are — so the dialogues are scanned.

#: A node id as it appears in prose. CASE-SENSITIVE, and that is the measured half of spec
#: 16's open question about false positives.
#:
#: Measured over the four shipped example vaults: 3,016 matches of the lowercase form, every
#: one of them a real node or task id — zero false positives. Admitting uppercase produces
#: exactly the collision spec 16 predicted by name: `T5`, the language model, in
#: `scaling_vault/wiki/transformer-language-models.md`, plus `H1`/`H2`/`H3`/`Q2` at sentence
#: starts. `selftest.run_science_voice` re-runs that measurement rather than quoting it, so a
#: future vault that breaks it goes red instead of being remembered as fine.
#:
#: Uppercase is where science lives — T5, H1, Q2, H2O, S1 — and lowercase is where crux
#: lives, because the engine allocates ids in lowercase and has since v0.1.
NODE_ID_RE = re.compile(r"\b[qhts]\d+\b")

#: crux's process vocabulary, normalised through `glossary_key` so hyphenation, case and a
#: trailing plural cannot smuggle a term past the list. Spec 16's default home, and 14's
#: precedent: a frozenset in the engine, one list rather than one per consumer.
#:
#: Membership was decided by MEASUREMENT, not by taste. Each candidate was counted in the
#: example vaults' `wiki/` prose — pure science voice, guaranteed by the wiki layer's one-way
#: flow rule — and any candidate with real hits there was dropped as a false-positive risk:
#: `seed` (19 hits, random seeds), `partial` (5), `anchor` (4), `idea` (4), `parent` (2).
#: `brief` and `pursue` are out as plain English on their face.
#:
#: What is deliberately ABSENT is the other half of the rule: plain science words — question,
#: hypothesis, evidence, finding, experiment, check, result, supported, refuted,
#: inconclusive, baseline — are standard scientific language, not crux coinage. The grad
#: student does not owe their advisor a gloss for "hypothesis".
CRUX_LEXICON = frozenset(glossary_key(t) for t in (
    # the notebook and its parts
    "crux", "cruxvault", "vault", "notebook", "node", "node id", "subtree", "tree",
    "cockpit", "wiki", "wikilink", "glossary", "ledger", "evidence ledger",
    "META.md", "EXPERIMENTS.md", "TASKHUB.md", "WIKI.md", "RD.md",
    # the process
    "verifiable", "verdict", "synthesis", "synthesize", "null", "review gate", "gate",
    "taskhub", "situate", "roll-up", "seed file", "seed outline", "prose cap",
    "outcome-neutral", "combination rule", "invalid-run", "commitment drift",
    "rd", "requirements document",
))

#: The notebook surface. A PI who asks to see one of these is leafing through the notebook,
#: which is the advisor's right — and for that exchange the notebook's own vocabulary,
#: including ids, is theirs to hear. Reverts at their next turn.
NOTEBOOK_TERMS = frozenset(glossary_key(t) for t in
                           ("notebook", "tree", "cockpit", "vault", "cruxvault"))

VOICE_SPEAKERS = ("pi", "agent")

#: compiled once: a lint over a long transcript would otherwise rebuild ~40 patterns a turn
_LEXICON_PATTERNS = tuple((k, term_pattern(k)) for k in sorted(CRUX_LEXICON))


def is_crux_term(term):
    """True when `term` is crux's own vocabulary rather than plain science."""
    return glossary_key(term) in CRUX_LEXICON


#: longest first, so a licensed phrase swallows the shorter term inside it. Without this,
#: a PI who agreed to "review gate" would still be flagged for hearing "gate" — the words
#: overlap in the text, and the shorter one is not a second leak, it is the same one counted
#: twice. Same reason "evidence ledger" must not also report "ledger".
_LEXICON_BY_LENGTH = tuple(sorted(_LEXICON_PATTERNS, key=lambda kv: -len(kv[0])))


def _terms_used(text):
    """The lexicon terms `text` uses, with each matched span consumed so a contained term
    cannot fire a second time."""
    rest, out = str(text or ""), set()
    for k, rx in _LEXICON_BY_LENGTH:
        masked, n = rx.subn(lambda m: " " * (m.end() - m.start()), rest)
        if n:
            out.add(k)
            rest = masked
    return out


def voice_lint(turns, agreed=(), report_from=1):
    """Findings on one CONVERSATION, as `(id, message)` pairs — empty when clean.

    `turns` is ordered `(speaker, text)` with speaker in `VOICE_SPEAKERS`; `agreed` is the
    PI's glossary terms, licensed from turn zero. Pure: no vault, no filesystem, no network.

    `report_from` scopes the REPORT without touching the licensing: turns before it still
    license what the PI said, they just stop producing findings. The chat-time consumer
    (PRD 16.2) needs exactly that — the mirror rule is cumulative over a conversation, but
    re-reporting turn 3's slip on every later tool call turns the signal into wallpaper.

    Two findings, one per kind of leak:

      voice:node-id    the agent said `q19` and the PI never had
      voice:crux-term  the agent said "review gate", "verifiable", "synthesis" — the same
                       what-the-hell-is-q19 problem in different clothes

    Order matters and that is the whole mechanism: a term is licensed from the turn the PI
    uses it, not for the turns before. Scanning a conversation rather than a message is what
    makes the mirror rule checkable at all."""
    licensed_terms = {glossary_key(t) for t in (agreed or ()) if str(t).strip()}
    licensed_ids, notebook, out = set(), False, []
    for i, turn in enumerate(turns, 1):
        speaker, text = turn
        speaker = str(speaker or "").strip().lower()
        if speaker not in VOICE_SPEAKERS:
            raise CruxError(f"voice: turn {i} is spoken by '{speaker}' — a conversation has "
                            f"exactly two sides, {' and '.join(VOICE_SPEAKERS)}")
        ids, terms = set(NODE_ID_RE.findall(str(text or ""))), _terms_used(text)
        if speaker == "pi":
            # the mirror rule: whatever the PI brings into the room is theirs to hear back
            licensed_ids |= ids
            licensed_terms |= terms
            notebook = bool(terms & NOTEBOOK_TERMS)
            continue
        if notebook:
            continue                      # leafing through the notebook — its words are open
        if i < report_from:
            continue                      # licensed above, reported by a narrower consumer
        for nid in sorted(ids - licensed_ids, key=natkey):
            out.append(("voice:node-id",
                        f"turn {i}: the agent said {nid!r}, which the PI has not used in "
                        f"this conversation. Name the node by its title instead — a "
                        f"paraphrase keeping the title's key terms, never a nickname."))
        for t in sorted(terms - licensed_terms):
            out.append(("voice:crux-term",
                        f"turn {i}: the agent said {t!r}, which is crux vocabulary rather "
                        f"than science. Say the science, or wait for the PI to say the word "
                        f"first."))
    return out


def chat_handle(nid, title):
    """The one line every id-minting verb prints beside the id it just allocated.

    Spec 16 gave the agent a prohibition — never introduce an id in chat — and put it two
    hundred lines from the receipt that hands it one. PRD 16.2's reading of why that lost:
    the agent reaches for `t81` partly because it needs SOME handle for the thing it just
    filed, and the id is the nearest handle in context. A prohibition removes the wrong
    answer; it does not supply the right one. So the receipt supplies it, in the same breath
    as the id it replaces — rule 5's title-anchored paraphrase, at the moment of temptation
    rather than in a section read once.

    Agent-facing and third person like every line the CLI prints (spec 16), so nothing here
    is phrased as words to relay."""
    return f'  in chat: "{title}" — the id {nid} is notebook-side'


# --- the lint at CHAT time (PRD 16.2) -------------------------------------------------
# Spec 16 shipped `voice_lint` with its consumers named as "the persona eval and selftest",
# and said so in the comment above: *nothing here runs at chat time.* The PI then reported
# the leak twice from live sessions. That is the gap, and this closes it: the same pure lint,
# a new consumer, reading the session transcript a Claude Code hook hands over.
#
# What this CANNOT do, stated once so nobody expects otherwise: a PostToolUse hook fires
# AFTER the message it judges. There is no interception point between the agent composing
# PI-facing text and the PI reading it, so this catches the REPETITION, not the first leak.
# `chat_handle` above is the preventive half; this is the measurement half.

#: The tool calls worth judging. `crux` as a whole word or as `crux.py`, so `cd cruxvault`
#: does not trigger and `python …/scaffold/crux.py status` does.
VOICE_HOOK_TRIGGER = re.compile(r"(?:^|[^\w./-])(?:\./)?crux(?:\.py)?(?:[^\w-]|$)")

#: Injected context is not the PI talking. A `<system-reminder>` block rides inside a user
#: turn and carries whatever the harness felt like adding — treating it as the PI's own words
#: would license any id it happens to mention, which is the one way this lint could be talked
#: into approving exactly what it exists to catch.
_INJECTED_RE = re.compile(r"<system-reminder>.*?</system-reminder>", re.S | re.I)

VOICE_HOOK_EVENT = "PostToolUse"
VOICE_HOOK_MATCHER = "Bash"
DOCTOR_SETTINGS_PATHS = ("~/.claude/settings.json", "~/.claude/settings.local.json")


def _turn_text(content):
    """The chat text of one message, and ONLY that.

    Tool-use and tool-result blocks are dropped, and the drop is the whole point: a tool
    result is where ids legitimately live — `✓ t81  (tasks/t81_x.md)` is a receipt, not the
    PI saying `t81` — so counting one as a spoken turn would license every id in the vault
    and the lint would pass every conversation forever."""
    if isinstance(content, str):
        return content
    out = []
    for b in (content or ()):
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(str(b.get("text") or ""))
    return "\n".join(out)


def transcript_turns(path):
    """A Claude Code JSONL transcript → `voice_lint`'s `(speaker, text)` turns.

    Tolerant by policy: an unparseable line is skipped, never raised on. This runs inside a
    hook, and a hook that breaks a session is strictly worse than the leak it was added to
    catch. Sidechain records are dropped too — a subagent's conversation is not the PI's, and
    the other `crux-*` agents keep their ids by ruling."""
    turns = []
    with open(path, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except Exception:
                continue
            if not isinstance(rec, dict) or rec.get("isSidechain") or rec.get("isMeta"):
                continue
            kind = rec.get("type")
            if kind not in ("user", "assistant"):
                continue
            msg = rec.get("message")
            text = _turn_text(msg.get("content") if isinstance(msg, dict) else None)
            if kind == "user":
                text = _INJECTED_RE.sub(" ", text)
            if not text.strip():
                continue
            turns.append(("pi" if kind == "user" else "agent", text))
    return turns


def voice_hook_command():
    """The literal command the hook runs — this engine's own `crux.py`, absolutely pathed.

    Absolute on purpose: a hook has no working directory it can rely on, and the whole point
    of `crux doctor`'s check is to notice when the clone this points into has moved."""
    here = os.path.dirname(os.path.abspath(__file__))
    return "%s %s voice --hook" % (shlex.quote(sys.executable),
                                   shlex.quote(os.path.join(here, "crux.py")))


def hook_report(payload):
    """The hook's whole decision: a context string to hand back, or None to stay silent.

    Silent is the default and covers every uninteresting case — the tool call was not a crux
    command, the transcript is unreadable, the newest turn is the PI's, the agent's newest
    turn is clean. Reporting is scoped to the NEWEST agent turn while licensing stays
    cumulative over the conversation: without the scoping, one slip in turn 3 re-fires on
    every tool call for the rest of the session, and a warning that never stops is a warning
    nobody reads."""
    if not isinstance(payload, dict):
        return None
    cmd = payload.get("tool_input")
    cmd = cmd.get("command") if isinstance(cmd, dict) else None
    if not VOICE_HOOK_TRIGGER.search(str(cmd or "")):
        return None
    path = payload.get("transcript_path")
    path = os.path.expanduser(str(path)) if path else None
    if not path or not os.path.isfile(path):
        return None
    turns = transcript_turns(path)
    agent_turns = [i for i, (s, _t) in enumerate(turns, 1) if s == "agent"]
    if not agent_turns:
        return None
    agreed = ()
    try:
        agreed = [t["term"] for t in load_glossary(find_vault(payload.get("cwd") or None))["terms"]]
    except Exception:
        pass                      # no vault, or an unreadable one: lint with an empty model
    found = voice_lint(turns, agreed, report_from=agent_turns[-1])
    if not found:
        return None
    lines = ["crux voice — the newest PI-facing message broke the mirror rule "
             "(SKILL.md, \"Voice — the invisible notebook\"):"]
    lines += ["  · %s  %s" % (i, m) for i, m in found]
    lines.append("Say it again in science before going on: name the node by its title, and "
                 "give the PI what the bookkeeping MEANS rather than the fact that it "
                 "happened. No apology and no meta-commentary about this notice — just the "
                 "science, from here on.")
    return "\n".join(lines)


def install_voice_hook(settings_path, command=None):
    """Register the chat-time lint in a Claude Code settings file. Returns what it did.

    Idempotent by SEARCH, not by equality: an existing `voice --hook` entry is rewritten to
    the current path rather than duplicated, so re-running `./install.sh` after moving the
    clone repairs the hook instead of stacking a second dead one. Every unrelated key and
    every unrelated hook in the file is preserved — this is the user's settings file, and a
    tool that eats it has done more damage than the leak it was fixing."""
    path = os.path.expanduser(settings_path)
    cfg = {}
    if os.path.isfile(path):
        try:
            cfg = json.loads(read(path) or "{}")
        except Exception as e:
            raise CruxError(f"{path} is not valid JSON ({e}) — fix or move it, then re-run")
    if not isinstance(cfg, dict):
        raise CruxError(f"{path} does not hold a JSON object — fix or move it, then re-run")
    cmd = command or voice_hook_command()
    hooks = cfg.setdefault("hooks", {})
    if not isinstance(hooks, dict):
        raise CruxError(f"{path}: 'hooks' does not hold a JSON object — fix it, then re-run")
    groups = hooks.setdefault(VOICE_HOOK_EVENT, [])
    if not isinstance(groups, list):
        raise CruxError(f"{path}: 'hooks.{VOICE_HOOK_EVENT}' does not hold a list — fix it, "
                        f"then re-run")
    for g in groups:
        for h in (g.get("hooks") or []) if isinstance(g, dict) else ():
            if isinstance(h, dict) and "voice --hook" in str(h.get("command") or ""):
                if h["command"] == cmd:
                    return "present"
                h["command"] = cmd
                _write_settings(path, cfg)
                return "repaired"
    groups.append({"matcher": VOICE_HOOK_MATCHER,
                   "hooks": [{"type": "command", "command": cmd}]})
    _write_settings(path, cfg)
    return "installed"


def _write_settings(path, cfg):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    write_if_changed(path, json.dumps(cfg, indent=2, ensure_ascii=False) + "\n")


def voice_hook_state(settings_paths=None):
    """(registered-paths, searched-paths) for the chat-time hook."""
    searched = [os.path.expanduser(p) for p in (settings_paths or DOCTOR_SETTINGS_PATHS)]
    found = []
    for p in searched:
        if not os.path.isfile(p):
            continue
        try:
            cfg = json.loads(read(p) or "{}")
        except Exception:
            continue
        groups = (cfg.get("hooks") or {}).get(VOICE_HOOK_EVENT) or [] if isinstance(cfg, dict) else []
        for g in groups if isinstance(groups, list) else ():
            for h in (g.get("hooks") or []) if isinstance(g, dict) else ():
                if isinstance(h, dict) and "voice --hook" in str(h.get("command") or ""):
                    found.append(p)
    return sorted(set(found)), searched


GATE_RELATIONS = ("self", "ancestor", "descendant", "sibling", "unrelated")


def _ancestors(v, nid):
    """`nid`'s ancestors, nearest first. Cycle-safe: a malformed vault must not hang a lint."""
    out, cur, seen = [], v.nodes.get(nid), {nid}
    while cur is not None and cur.parent and cur.parent in v.nodes and cur.parent not in seen:
        seen.add(cur.parent)
        out.append(cur.parent)
        cur = v.nodes[cur.parent]
    return out


def gate_relation(v, near, other):
    """How `other` stands to `near`: one of `GATE_RELATIONS`.

    Spec 16's relevance gate: the agent may raise a pending signature question on its own
    initiative only when the node is in the current conversation's LINEAGE (ancestor or
    descendant) or is an IMMEDIATE sibling. Computed here rather than judged, per spec 09's
    rule 1 — the deterministic check is the goalpost.

    It binds agent initiative only. A PI who asks what is pending gets everything, which is
    why nothing in the engine filters on this: it annotates."""
    if near == other:
        return "self"
    if near not in v.nodes or other not in v.nodes:
        return "unrelated"
    if other in _ancestors(v, near):
        return "ancestor"
    if near in _ancestors(v, other):
        return "descendant"
    p = v.nodes[near].parent
    if p and p == v.nodes[other].parent:
        return "sibling"
    return "unrelated"


# ----------------------------------------------------------------------------- wiki layer (Epic 3)
# A PI-curated literature wiki: immutable sources under raw/, agent-compiled pages under
# wiki/. The engine owns only the bookkeeping — source hashes, the generated index, and the
# structural lint. It never reads a source's content or judges a page. Everything that needs
# meaning (what to compile, contradictions, staleness) is the agent's job. Flow is one-way:
# literature → wiki → informs the tree; findings never enter the wiki.
WIKILINK_RE = re.compile(r"\[\[\s*([^\]|#]+?)\s*(?:[|#][^\]]*)?\]\]")

def wiki_dir(root):    return os.path.join(root, WIKI_DIR)
def raw_dir(root):     return os.path.join(root, RAW_DIR)
def wiki_active(root): return os.path.isdir(wiki_dir(root))

def _rel(root, path):
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")

def link_targets(text):
    """Basenames referenced by [[wikilinks]] in text (alias/heading stripped, any dir
    prefix and .md dropped). Order-preserving-unique, deterministic."""
    out, seen = [], set()
    for m in WIKILINK_RE.findall(text):
        t = m.strip().split("/")[-1]
        if t.endswith(".md"):
            t = t[:-3]
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

def load_sources(root):
    """Read the engine-owned source registry → {relpath: {sha256, date, title}}."""
    path = os.path.join(root, SOURCES_FILE)
    reg = {}
    if os.path.exists(path):
        for line in read(path).splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            # 4 columns is the pre-3.4 format (no work id). Titles are whitespace-collapsed
            # on write, so they never contain a tab — the column count is unambiguous.
            if len(parts) == 4:
                reg[parts[2]] = {"sha256": parts[0], "date": parts[1], "workid": "", "title": parts[3]}
            elif len(parts) >= 5:
                reg[parts[2]] = {"sha256": parts[0], "date": parts[1], "workid": parts[3],
                                 "title": "\t".join(parts[4:])}
    return reg

def save_sources(root, reg):
    lines = [f"{r['sha256']}\t{r['date']}\t{rel}\t{r.get('workid', '')}\t{r['title']}"
             for rel, r in sorted(reg.items())]
    write_if_changed(os.path.join(root, SOURCES_FILE), ("\n".join(lines) + "\n") if lines else "")

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_wiki_pages(root):
    """Every compiled wiki page (a *.md under wiki/ with `type: wiki`), sorted by slug.
    log.md / SCHEMA.md are excluded automatically (their type isn't `wiki`)."""
    pages, wd = [], wiki_dir(root)
    if not os.path.isdir(wd):
        return pages
    for dirpath, dirnames, filenames in os.walk(wd):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            fm, body = parse_doc(read(os.path.join(dirpath, fn)))
            if fm.get("type") != "wiki":
                continue
            srcs = [s.strip() for s in str(fm.get("sources") or "").split(",") if s.strip()]
            pages.append({"slug": fn[:-3], "fn": fn, "path": os.path.join(dirpath, fn), "fm": fm,
                          "body": body, "title": fm.get("title"), "summary": fm.get("summary"),
                          "category": (fm.get("category") or "uncategorized"), "sources": srcs,
                          "links": link_targets(body)})
    pages.sort(key=lambda p: p["slug"])
    return pages

WIKI_SPECIALS = {"_index": WIKI_INDEX, "_log": WIKI_LOG, "_schema": WIKI_SCHEMA}

def _wiki_snapshot(root):
    """The `wiki` block of snapshot(): the index only — public per-page fields plus a
    content hash for change detection, never a body or a filesystem path."""
    if not wiki_active(root):
        return {"active": False, "pages": [], "sources": [],
                "specials": {"index": False, "log": False, "schema": False}}
    return {
        "active": True,
        "pages": [{"slug": p["slug"], "title": p["title"], "summary": p["summary"],
                   "category": p["category"], "links": p["links"], "sources": p["sources"],
                   "hash": _sha256_file(p["path"])[:16]}
                  for p in scan_wiki_pages(root)],
        "sources": [{"date": r["date"], "path": rel, "title": r["title"]}
                    for rel, r in sorted(load_sources(root).items())],
        "specials": {"index": os.path.isfile(os.path.join(root, WIKI_INDEX)),
                     "log": os.path.isfile(os.path.join(root, WIKI_LOG)),
                     "schema": os.path.isfile(os.path.join(root, WIKI_SCHEMA))},
    }

def _rd_snapshot(root):
    """The `rd` block of snapshot(): the index only — public per-page fields plus a content
    hash for change detection, never a body. The cockpit polls this about once a second, so
    unbounded design prose must stay behind /rd/<slug>.json."""
    if not rd_active(root):
        return {"active": False, "pages": []}
    return {"active": True,
            "pages": [{"slug": p["slug"], "title": p["title"], "node": p["node"],
                       "status": p["status"], "supersedes": p["supersedes"],
                       "hash": _sha256_file(p["path"])[:16]}
                      for p in scan_rd_pages(root)]}

def _mention_snippet(body, slug, width=140):
    """The first line of `body` whose wikilinks mention `slug`, trimmed to ~width chars
    around the mention (the canonical link parser decides what counts as a mention)."""
    for line in body.splitlines():
        if slug not in link_targets(line):
            continue
        line = line.strip()
        if len(line) <= width:
            return line
        pos = line.find(slug)
        br = line.rfind("[[", 0, pos)
        anchor = br if br != -1 else max(pos, 0)
        start = max(0, anchor - width // 3)
        end = min(len(line), start + width)
        return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")
    return ""

def _page_payload(root, slug, pages, extra=None):
    """The shared reader payload for ANY layer of markdown pages with backlinks: body +
    backlinks, or None for an unknown or traversal-shaped slug. Extracted from the wiki
    reader so the RD layer reuses it instead of growing a second one — the slug is only ever
    matched against the scan, never used as a filesystem path, and rejection happens before
    any file is read. Duplicate slugs resolve deterministically: the first page by sorted path."""
    if not slug or "/" in slug or "\\" in slug or ".." in slug or slug.startswith("."):
        return None
    matches = [p for p in pages if p["slug"] == slug]
    if not matches:
        return None
    page = min(matches, key=lambda p: p["path"])
    backlinks = [{"slug": q["slug"], "title": q["title"],
                  "snippet": _mention_snippet(q["body"], slug)}
                 for q in pages if q["slug"] != slug and slug in q["links"]]
    d = {"slug": page["slug"], "title": page["title"],
         "summary": page["fm"].get("summary") or None,
         "category": page["fm"].get("category") or None,
         "sources": page.get("sources") or [],
         "updated": page["fm"].get("updated") or None,
         "body": page["body"], "backlinks": backlinks}
    if extra:
        d.update({k: page.get(k) if k in page else page["fm"].get(k) for k in extra})
    return d

def rd_page_payload(root, slug):
    """Payload for /rd/<slug>.json — the same reader the wiki tab uses, pointed at the RD
    layer. None on a pre-07 vault, so the route 404s rather than 500s."""
    if not rd_active(root):
        return None
    return _page_payload(root, slug, scan_rd_pages(root), extra=("node", "status", "supersedes"))

def wiki_page_payload(root, slug):
    """Payload for /wiki/<slug>.json: a scanned page (with backlinks) or a reserved
    special; None for unknown or traversal-shaped slugs. The slug is only ever matched
    against the scan + reserved names — never used as a filesystem path — and rejection
    happens before any file is read. Duplicate slugs resolve deterministically: reserved
    names always win, then the first page by sorted path."""
    if not wiki_active(root):
        return None
    if slug in WIKI_SPECIALS:
        path = os.path.join(root, WIKI_SPECIALS[slug])
        if not os.path.isfile(path):
            return None
        fm, body = parse_doc(read(path))
        return {"slug": slug, "title": fm.get("title") or None,
                "summary": fm.get("summary") or None, "category": fm.get("category") or None,
                "sources": [], "updated": fm.get("updated") or None,
                "body": body, "backlinks": []}
    return _page_payload(root, slug, scan_wiki_pages(root))

def ensure_wiki(root):
    """Lazily stand up the wiki subsystem (idempotent, safe on a pre-wiki vault)."""
    os.makedirs(wiki_dir(root), exist_ok=True)
    os.makedirs(raw_dir(root), exist_ok=True)
    if not os.path.exists(os.path.join(root, WIKI_LOG)):
        write_if_changed(os.path.join(root, WIKI_LOG),
                         "# Wiki log\n\n_Append-only. `grep '^## \\[' log.md` for the timeline._\n")
    if not os.path.exists(os.path.join(root, WIKI_SCHEMA)):
        write_if_changed(os.path.join(root, WIKI_SCHEMA), load_template("wiki_schema"))

def cmd_ingest(root, path, title=None, workid=None):
    """Register a PI-curated source under raw/: record its sha256, append a Karpathy-format
    log line, (re)render the index. The agent compiles pages afterward — the engine never
    reads the source's content. Idempotent on an unchanged, already-registered file."""
    abspath = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    rawroot = os.path.abspath(raw_dir(root))
    if os.path.commonpath([abspath, rawroot]) != rawroot:
        raise CruxError(f"ingest: a source must live under {RAW_DIR}/ (got {path!r}); place the "
                        "file in raw/ first — the PI curates what enters raw/")
    if not os.path.isfile(abspath):
        raise CruxError(f"ingest: no such file: {path}")
    ensure_wiki(root)
    rel, sha = _rel(root, abspath), _sha256_file(abspath)
    reg = load_sources(root)
    workid = workid or reg.get(rel, {}).get("workid", "")   # a known id survives a re-ingest
    title = " ".join((title or os.path.splitext(os.path.basename(abspath))[0]).split())  # single-line: registry + log are line-based
    if rel in reg and reg[rel]["sha256"] == sha:
        # The bytes are unchanged, so this is not a re-ingest and gets no log line. But a
        # work id supplied now for a source registered earlier is new information, and
        # dropping it would make `ingest --doi` a silent no-op on the common path: register
        # with --title today, attach the DOI later.
        if workid and reg[rel].get("workid", "") != workid:
            reg[rel]["workid"] = workid
            save_sources(root, reg)
        refresh(root)
        return "unchanged", rel
    state = "updated" if rel in reg else "ingested"
    reg[rel] = {"sha256": sha, "date": datetime.date.today().isoformat(),
                "workid": workid, "title": title}
    save_sources(root, reg)
    with open(os.path.join(root, WIKI_LOG), "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.date.today().isoformat()}] ingest | {title}\n")
    refresh(root)
    return state, rel

# ---------------------------------------------------------------------------------------
# The literature scope (spec 17.3) — what a search is about, written down before it runs.
#
# `crux lit crawl` seeds itself from every raw/ source that carries a work id, which is
# wrong for any vault holding more than one line of enquiry: a raw/ with chromatin papers
# AND optimiser papers produces a subgraph about neither. The seed set is the load-bearing
# input, so it gets a file the PI approves rather than an accident of what was ingested.
#
# The skill writes this file; the engine checks it. Same split as the flight plan.
# ---------------------------------------------------------------------------------------

LIT_DIR   = os.path.join(WIKI_DIR, "lit")
SCOPE_MIN_SEEDS, SCOPE_MAX_SEEDS = 3, 8


def scope_path(root, slug):
    return os.path.join(root, LIT_DIR, slug, "scope.md")


def parse_scope(text):
    """-> {fm, problem, seeds, out_of_scope}. Pure: takes text, never a path."""
    fm, body = {}, text
    if text.startswith("---\n"):
        end = text.find("\n---", 4)
        if end != -1:
            for line in text[4:end].splitlines():
                if ":" in line:
                    k, v = line.split(":", 1)
                    fm[k.strip()] = v.strip()
            body = text[end + 4:]
    seeds = [l.strip().lstrip("-*").strip() for l in _section(body, "Seeds").splitlines()]
    return {"fm": fm, "problem": _section(body, "Problem"),
            "seeds": [x for x in seeds if x],
            "out_of_scope": _section(body, "Out of scope")}


def _looks_like_seed(root, seed):
    """A bare OpenAlex work id, or a DOI — nothing else is resolvable without guessing."""
    if re.fullmatch(r"W\d+", seed):
        return True
    return bool(re.fullmatch(r"(https?://doi\.org/)?10\.\d{4,9}/\S+", seed))


def scope_problems(root, scope, slug):
    """[{check, message}] — EVERY way this scope is wrong, in one pass.

    All of them, not the first: the PI reads this once and fixes it once."""
    out = []
    def add(c, m):
        out.append({"check": c, "message": m})

    declared = (scope.get("fm") or {}).get("slug", "")
    if declared and slug and declared != slug:
        add("scope-slug", f"scope declares slug {declared!r} but lives in {slug!r}/ — the "
                          "directory is the name; make the frontmatter agree with it")

    seeds = scope.get("seeds") or []
    seen, dups = set(), []
    for x in seeds:
        (dups.append(x) if x in seen else seen.add(x))
    if dups:
        add("scope-seed-duplicate", f"seed listed more than once: {', '.join(sorted(set(dups)))}"
                                    " — a seed counts once however many times it appears, so a "
                                    "repeat silently buys nothing")
    unknown = [x for x in seeds if not _looks_like_seed(root, x)]
    if unknown:
        add("scope-seed-unknown", f"not a work id or a DOI: {', '.join(unknown)} — a seed must "
                                  "be resolvable without guessing. Use the OpenAlex id (W…) or "
                                  "the DOI, not the paper's name")
    elif not (SCOPE_MIN_SEEDS <= len(set(seeds)) <= SCOPE_MAX_SEEDS):
        add("scope-seed-count",
            f"{len(set(seeds))} distinct seeds; wanted {SCOPE_MIN_SEEDS}-{SCOPE_MAX_SEEDS}. "
            "Fewer than three and the shared subgraph is whatever one paper happened to cite; "
            "more than eight and the seeds stop agreeing on a subject")

    problem = (scope.get("problem") or "").strip()
    if not problem:
        add("scope-problem-empty", "## Problem is empty — the search has nothing to be about, "
                                   "and the PI reading the candidate list in a month will have "
                                   "no way to tell what it was for")
    elif len(_prose_tokens(problem)) > PROSE_CAP:
        add("scope-problem-long", f"## Problem runs {len(_prose_tokens(problem))} words, over "
                                  f"the {PROSE_CAP}-word cap — a scope that needs an essay is "
                                  "two searches")
    return out


def load_scope(root, slug):
    """The parsed scope for `slug`, or None when the search has no scope file."""
    path = scope_path(root, slug)
    return parse_scope(read(path)) if os.path.exists(path) else None

def validate_wiki(root):
    """Structural lint over the wiki layer — mechanical checks only (broken/flow links,
    orphans, missing frontmatter, source hash drift, uncompiled/missing sources). Semantic
    checks (contradictions, staleness, missing pages) are the agent's job, not the engine's."""
    problems = []
    if not wiki_active(root):
        return problems
    v = Vault(root)
    pages = scan_wiki_pages(root)
    page_slugs = {p["slug"] for p in pages}
    tree_targets = set(v.nodes) | {n.basename for n in v.nodes.values()}

    # explicit `[[rd/…]]` references, kept prefixed: `link_targets` strips the directory,
    # so without this the flow violation below would read as a bare "broken link" and send
    # the reader hunting for a wiki page that was never meant to exist.
    def _rd_refs(text):
        return {m.strip().split("/")[-1] for m in
                re.findall(r"\[\[\s*" + RD_DIR + r"/([^\]|#]+?)(?:\.md)?\s*(?:[|#][^\]]*)?\]\]", text)}

    # per-page: required frontmatter + cited-source integrity + link resolution
    for p in pages:
        rd_refs = _rd_refs(p["body"])
        for field in ("title", "summary"):
            if not str(p["fm"].get(field) or "").strip():
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': missing required field '{field}'"))
        for s in p["sources"]:
            if not os.path.isfile(os.path.join(root, s)):
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': cites missing source '{s}' (not a file under the vault)"))
        for t in p["links"]:
            if t in rd_refs:
                # the one-way rule, extended: the literature layer must not cite the
                # project's own design reasoning any more than it may cite the tree
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': flow violation — links "
                                 f"RD page [[{RD_DIR}/{t}]] (the wiki must not cite the project's own design)"))
                continue
            if t in page_slugs:
                continue
            if t in tree_targets:
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': flow violation — links "
                                 f"tree node [[{t}]] (the wiki must not cite the tree)"))
            else:
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': broken link [[{t}]]"))

    # orphans: no inbound from another wiki page or a tree node. The generated WIKI.md is NOT
    # scanned as a page, so its links can never rescue an orphan (guards the Emmimal miscount).
    inbound = {p["slug"]: 0 for p in pages}
    for p in pages:
        for t in p["links"]:
            if t in inbound and t != p["slug"]:
                inbound[t] += 1
    for n in v.nodes.values():
        for t in link_targets(n["body"]):
            if t in inbound:
                inbound[t] += 1
    # an RD citing a wiki page is intended usage — grounding a design in the literature is
    # the flow rule working, so it must not leave that page reported as an orphan
    for r in scan_rd_pages(root):
        for t in r["links"]:
            if t in inbound:
                inbound[t] += 1
    for p in pages:
        if inbound[p["slug"]] == 0:
            problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': orphan (no inbound links)"))

    # tree → wiki: an explicit [[wiki/…]] reference in a node body must resolve
    for n in v.nodes.values():
        for m in re.findall(r"\[\[\s*wiki/([^\]|#]+?)(?:\.md)?\s*(?:[|#][^\]]*)?\]\]", n["body"]):
            if m.strip().split("/")[-1] not in page_slugs:
                problems.append((f"node:{n.id}", f"node '{n.id}': broken wiki link [[wiki/{m.strip()}]]"))

    # source registry: hash drift, missing file, uncompiled (no page cites it)
    reg, compiled = load_sources(root), set()
    for p in pages:
        compiled.update(p["sources"])
    for rel, rec in sorted(reg.items()):
        ap = os.path.join(root, rel)
        if not os.path.isfile(ap):
            problems.append((f"src:{rel}", f"source '{rel}': missing (registered but file not found)")); continue
        if _sha256_file(ap) != rec["sha256"]:
            problems.append((f"src:{rel}", f"source '{rel}': hash drift since ingest (re-ingest to refresh)"))
        if rel not in compiled:
            problems.append((f"src:{rel}", f"uncompiled source '{rel}': registered but no wiki page cites it"))
    return problems

# ----------------------------------------------------------------------------- RD layer (Epic 7)
# Requirements Documents. The engine owns only the bookkeeping — the page, the backlink, the
# generated index and (in 07.2) the structural lint. What belongs in an RD, and whether a node
# earns one at all, is judgment and lives in the `crux-rd` skill.
#
# Two records, cross-checked: the RD declares `node:`, the node carries an `RD::` wikilink.
# The backlink sits in the body PREAMBLE beside `Parent::` — text before the first `## `
# heading is invisible to `_section`, so linking a design document costs nothing from the
# 400-word budget the RD exists to free.

def rd_dir(root):    return os.path.join(root, RD_DIR)
def rd_active(root): return os.path.isdir(rd_dir(root))

def ensure_rd(root):
    """Lazily stand up the RD layer (idempotent, safe on a pre-07 vault)."""
    os.makedirs(rd_dir(root), exist_ok=True)

def scan_rd_pages(root):
    """Every RD page (a *.md under rd/ with `type: rd`), sorted by slug. Pure read."""
    pages, d = [], rd_dir(root)
    if not os.path.isdir(d):
        return pages
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = sorted(x for x in dirnames if not x.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            fm, body = parse_doc(read(os.path.join(dirpath, fn)))
            if fm.get("type") != "rd":
                continue
            pages.append({"slug": fn[:-3], "fn": fn, "path": os.path.join(dirpath, fn),
                          "fm": fm, "body": body, "title": fm.get("title") or fn[:-3],
                          "node": fm.get("node"), "status": fm.get("status") or "draft",
                          "supersedes": fm.get("supersedes") or None,
                          "links": link_targets(body)})
    pages.sort(key=lambda p: p["slug"])
    return pages

def active_rd(root, nid):
    """The one active RD owned by `nid`, or None. Deterministic on the (lint-caught) case of
    two: the first by slug."""
    for p in scan_rd_pages(root):
        if p["node"] == nid and p["status"] == "active":
            return p
    return None

def _rd_link_line(slug, title):
    return f"{RD_LINK} [[{RD_DIR}/{slug}]] — {title}"

def set_rd_link(body, slug, title):
    """Put the `RD::` backlink in the body preamble, directly under `Parent::` — replacing an
    existing one rather than accumulating. Returns the new body."""
    line = _rd_link_line(slug, title)
    lines = body.splitlines()
    for i, l in enumerate(lines):
        if l.strip().startswith(RD_LINK):
            lines[i] = line
            return "\n".join(lines)
    for i, l in enumerate(lines):
        if l.strip().startswith("Parent::"):
            lines.insert(i + 1, line)
            return "\n".join(lines)
    return line + "\n\n" + body

def _rd_slug(root, title, taken):
    base = slugify(title)
    slug, n = base, 1
    while slug in taken or os.path.exists(os.path.join(rd_dir(root), slug + ".md")):
        n += 1
        slug = f"{base}_{n}"
    return slug

def cmd_rd(root, nid, title, supersedes=None):
    """Write the Requirements Document for one node: create `rd/<slug>.md` and the node's
    `RD::` backlink. Returns (slug, filename).

    One ACTIVE RD per node. A design change never edits the active RD in place — it writes a
    new one with `--supersedes`, and the chain is the reasoning history. That is the direct
    fix for a node body treated as the only durable record.

    The engine does not detect an edit to a superseded RD (PI ruling, spec 07 D7): `git log -p
    rd/<slug>.md` is the audit trail, exactly as it is for a node's decision history."""
    v = Vault(root)
    n = v.get(nid)
    if n.type not in ("question", "idea"):
        raise CruxError(f"an RD belongs to a question or a hypothesis (got a '{n.type}' for "
                        f"'{nid}'); the project root and syntheses do not carry one")
    ensure_rd(root)
    pages = {p["slug"]: p for p in scan_rd_pages(root)}
    old = None
    if supersedes:
        old = pages.get(supersedes)
        if old is None:
            raise CruxError(f"cannot supersede '{supersedes}': no such RD under {RD_DIR}/")
        if old["node"] != nid:
            raise CruxError(f"cannot supersede '{supersedes}': it belongs to '{old['node']}', "
                            f"not '{nid}' — an RD belongs to exactly one node")
    live = active_rd(root, nid)
    if live and (old is None or live["slug"] != old["slug"]):
        raise CruxError(f"'{nid}' already has an active RD ('{live['slug']}'). An active RD is "
                        f"never amended in place — to replace it:\n"
                        f"    crux rd {nid} \"{title}\" --supersedes {live['slug']}")
    slug = _rd_slug(root, title, set(pages))
    fn = slug + ".md"
    text = fill(load_template("rd"), node=nid, title=title, node_basename=n.basename,
                supersedes=supersedes or "")
    text = text.replace("status: draft", "status: active")
    write_if_changed(os.path.join(rd_dir(root), fn), text)
    if old is not None:
        # frontmatter only — the superseded document's BODY is what the chain records, and the
        # engine must never be the thing that changes it
        old["fm"]["status"] = "superseded"
        old["fm"]["updated"] = now()
        write_if_changed(old["path"], render_doc(old["fm"], old["body"]))
    n["body"] = set_rd_link(n["body"], slug, title)
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    refresh(root)
    return slug, fn

def validate_rd(root):
    """Structural lint over the RD layer — mechanical checks only: the node's backlink
    resolves, the two ownership records agree, exactly one design is live per node, and the
    supersession chain resolves and is acyclic. Whether an RD is warranted, current or good
    is judgment; that lives in the `crux-rd` skill, exactly as the wiki's semantics live in
    `crux-wiki`.

    Deliberately NOT checked: whether a superseded RD was edited (spec 07 D7). The engine has
    no memory of a file's previous bytes, and `git log -p rd/<slug>.md` already is the record
    — the same call spec 06 made when it sent decision history to git."""
    problems = []
    if not rd_active(root):
        return problems
    v = Vault(root)
    pages = scan_rd_pages(root)
    by_slug = {p["slug"]: p for p in pages}

    # the node half of the ownership pair: which RD each node's `RD::` line points at
    node_link = {}
    for n in v.nodes.values():
        for m in re.findall(r"\[\[\s*" + RD_DIR + r"/([^\]|#]+?)(?:\.md)?\s*(?:[|#][^\]]*)?\]\]", n["body"]):
            node_link[n.id] = m.strip().split("/")[-1]
    for nid in sorted(node_link, key=natkey):
        if node_link[nid] not in by_slug:
            problems.append((f"node:{nid}", f"node '{nid}': broken RD link "
                                            f"[[{RD_DIR}/{node_link[nid]}]]"))

    active = {}
    for p in pages:
        sid = f"rd:{p['slug']}"
        if p["status"] not in RD_STATUS:
            problems.append((sid, f"rd page '{p['slug']}': bad status '{p['status']}' "
                                  f"(expected one of {', '.join(RD_STATUS)})"))
        node = p["node"]
        if not node or node not in v.nodes:
            problems.append((sid, f"rd page '{p['slug']}': owning node '{node}' does not exist"))
        else:
            if p["status"] == "active":
                active.setdefault(node, []).append(p["slug"])
                linked = node_link.get(node)
                if linked and linked in by_slug and linked != p["slug"]:
                    problems.append((sid, f"rd page '{p['slug']}': claims node '{node}', but "
                                          f"'{node}' links [[{RD_DIR}/{linked}]]"))
        if p["supersedes"] and p["supersedes"] not in by_slug:
            problems.append((sid, f"rd page '{p['slug']}': supersedes missing page "
                                  f"'{p['supersedes']}'"))
    for node in sorted(active, key=natkey):
        slugs = sorted(active[node])
        if len(slugs) > 1:
            problems.append((f"node:{node}", f"node '{node}': {len(slugs)} active RDs "
                                             f"({', '.join(slugs)}) — an RD is superseded, "
                                             f"never duplicated"))

    # the chain must terminate. Walked per page with a seen-set rather than trusting the
    # data, so a hand-edited cycle reports instead of spinning.
    for p in pages:
        seen, cur = {p["slug"]}, p["supersedes"]
        while cur in by_slug:
            if cur in seen:
                problems.append((f"rd:{p['slug']}", f"rd page '{p['slug']}': supersession cycle"))
                break
            seen.add(cur)
            cur = by_slug[cur]["supersedes"]
    return problems

# ----------------------------------------------------------------------------- taskhub layer (Epic 8)
# Science goes in the tree. Doing goes in the taskhub. A task is an ACTION: if it is a claim
# about the world that could be true or false, it is a hypothesis and belongs in the tree.
#
# What gets in: "would you be annoyed if this vanished next week?" If yes it belongs here,
# however small. If no it is session scratch and stays in the agent's own todo list. Tasks
# can be fine-grained; they cannot be ephemeral.
def task_dir(root):    return os.path.join(root, TASK_DIR)
def task_active(root): return os.path.isdir(task_dir(root))

def ensure_tasks(root):
    """Lazily stand up the taskhub (idempotent, safe on a pre-2.0 vault)."""
    os.makedirs(task_dir(root), exist_ok=True)

def task_categories(root):
    """The vault's declared category list. Falls back to the defaults when the key is absent,
    so a vault created before 2.0 can add its first task without being told to configure
    something first."""
    cfg = yaml_load(read(os.path.join(root, VAULT_MARKER)))
    raw = [c.strip() for c in str(cfg.get(TASK_CATEGORIES_KEY) or "").split(",") if c.strip()]
    return tuple(raw) if raw else DEFAULT_TASK_CATEGORIES

def _csv_field(val):
    """A comma-separated frontmatter scalar -> [str]. The engine's YAML is a flat map of
    scalars by design (no list type), so every multi-valued field is one string — the wiki
    layer's `sources:` idiom."""
    return [x.strip() for x in str(val or "").split(",") if x.strip()]

def task_blockers(t):
    """The blocker ids on a task. The literal `None` means "no edge, and I said so" — which
    is the whole point of the field being mandatory (`to-tickets`): a missing edge must be a
    visible omission rather than silence."""
    raw = _csv_field(t["fm"].get("blocked_by"))
    return [x for x in raw if x != NO_BLOCKERS]

def task_hypothesis_refs(t):
    """[(hypothesis id, conclusion)] for a task, in declared order. Empty for an ordinary task.

    One experiment can say DIFFERENT things about different hypotheses — a pilot may support
    h44 and refute h45 — so the conclusion rides on the ref itself, one pair per hypothesis.
    This is the only structured place that fact exists; without it the timeline cannot be
    rendered and no check can be written against it."""
    out = []
    for item in _csv_field(t["fm"].get(HYPOTHESIS_REFS)):
        hid, _, concl = item.partition(":")
        out.append((hid.strip(), concl.strip()))
    return out

def task_is_experiment(t):
    """A task that declares what it concluded about a hypothesis IS an experiment. Nothing is
    stored to say so — the same move this layer makes for `blocked`, and for the same reason,
    with higher stakes: this is the one category that changes whether the PI gets asked."""
    return bool(task_hypothesis_refs(t))

def task_category(t):
    """The task's category as every view must show it: `experiment` when the role is present,
    otherwise the declared tag. Computed, so the one category with gating consequences is
    the one category that cannot drift."""
    return TASK_RESERVED_CATEGORY if task_is_experiment(t) else t["category"]

def task_ref_link(ref, basenames):
    """One `refs` entry as a wikilink Obsidian can actually follow.

    A ref is STORED as an id (`q21`), because an id is stable and a filename is not — but a
    node's file is `q21_<slug>.md`, so `[[q21]]` resolves to nothing in Obsidian. The stored
    form stays the id and the rendered form carries the basename with the id as its alias:
    `[[q21_can_jepa…|q21]]`. Full traversability is the point of the layer; a link that only
    resolves inside crux is half a link."""
    if "/" in ref:                       # wiki/<slug> or rd/<slug> — already a real path
        return f"[[{ref}]]"
    base = basenames.get(ref)
    return f"[[{base}\\|{ref}]]" if base else f"[[{ref}]]"

def task_basenames(v):
    return {n.id: n.basename for n in v.nodes.values()}

def scan_tasks(root):
    """Every task (a *.md under tasks/ with `type: task`), in id order. Pure read.

    A second scanner rather than widening `Vault`, and that is deliberate: widening `Vault`
    to walk subdirectories would put tasks into the roll-up in one line."""
    out, d = [], task_dir(root)
    if not os.path.isdir(d):
        return out
    for dirpath, dirnames, filenames in os.walk(d):
        dirnames[:] = sorted(x for x in dirnames if not x.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            fm, body = parse_doc(read(os.path.join(dirpath, fn)))
            if fm.get("type") != "task":
                continue
            out.append({"id": fm.get("id"), "fn": fn, "path": os.path.join(dirpath, fn),
                        "fm": fm, "body": body, "title": fm.get("title") or fn[:-3],
                        "category": fm.get("category"), "status": fm.get("status") or "open",
                        "parent": fm.get("parent") or None,
                        "blocked_by": task_blockers({"fm": fm}),
                        "refs": _csv_field(fm.get("refs")),
                        "hypothesis_refs": task_hypothesis_refs({"fm": fm}),
                        "outputs": parse_artifacts(body, "output")})
    out.sort(key=lambda t: natkey(str(t["id"] or "")))
    return out

def _link_universe(root, v=None):
    """Everything a task's `refs` (or a wikilink output) may legally point at: tree node ids
    and basenames, plus `wiki/<slug>` and `rd/<slug>`."""
    v = v or Vault(root)
    out = set(v.nodes) | {n.basename for n in v.nodes.values()}
    out |= {f"{WIKI_DIR}/{p['slug']}" for p in scan_wiki_pages(root)}
    out |= {f"{RD_DIR}/{p['slug']}" for p in scan_rd_pages(root)}
    return out

def _task_slug(root, title, taken):
    base = slugify(title)
    slug, n = base, 1
    while slug in taken:
        n += 1
        slug = f"{base}_{n}"
    return slug

def _check_category(root, category):
    """Refuse an undeclared category, and refuse the reserved one BY NAME.

    The refusal lives here rather than in argparse `choices=`: argparse exits 2 instead of 1,
    prints nothing useful under `--json`, and — decisively — never fires on a hand-edited
    file, which is where a category actually drifts."""
    if not category:
        raise CruxError(f"a task needs a category — one of {', '.join(task_categories(root))}")
    if category == TASK_RESERVED_CATEGORY:
        raise CruxError(
            f"'{TASK_RESERVED_CATEGORY}' is a reserved category and cannot be typed by hand. "
            f"It is computed: a task is an experiment when it declares what it concluded "
            f"about a hypothesis (see spec 08). Use one of "
            f"{', '.join(task_categories(root))}.")
    if category not in task_categories(root):
        raise CruxError(f"unknown task category '{category}' — this vault declares "
                        f"{', '.join(task_categories(root))}. Add one with "
                        f"`crux task categories --add {category}`.")

def _check_conclusion(concl):
    """One conclusion token, checked against spec 15's vocabulary.

    `partial` gets its own message: it is not an unknown word, it is a RETIRED one, and a
    reader who typed it deserves to be told which spec retired it and why rather than being
    handed a list."""
    if concl == RETIRED_CONCLUSION:
        raise CruxError(
            f"'{RETIRED_CONCLUSION}' is retired as a conclusion (spec 15): it is the partial "
            f"answer evidence semantics exists to abolish. Say what the run actually showed — "
            f"{', '.join(CONCLUSIONS)}.")
    if concl not in CONCLUSIONS:
        raise CruxError(f"unknown conclusion '{concl}' — an experiment concludes one of "
                        f"{', '.join(CONCLUSIONS)} about each hypothesis it refs")

def cmd_task_add(root, title, category, refs=None, blocked_by=None, parent=None, why=None,
                 hypothesis_refs=None):
    """Append one task. Returns (id, filename).

    Append-only, always: nothing here rewrites, renumbers, reorders or deletes an existing
    task, and no other command in the engine writes under tasks/ at all."""
    v = Vault(root)
    _check_category(root, category)
    for hid, concl in (hypothesis_refs or []):
        n = v.nodes.get(hid)
        if n is None or n.type != "idea":
            raise CruxError(f"hypothesis_refs must name a hypothesis (an `idea` node); '{hid}' "
                            + (f"is a '{n.type}'" if n else "is not in this vault")
                            + ". A task bearing on a question rather than a hypothesis wants "
                              "plain `--ref`.")
        _check_conclusion(concl)
    universe = _link_universe(root, v)
    for r in (refs or []):
        if r not in universe:
            raise CruxError(f"task ref '{r}' resolves to nothing — refs point at a tree node, "
                            f"a `{WIKI_DIR}/<slug>` page or an `{RD_DIR}/<slug>` document")
    known = {t["id"] for t in scan_tasks(root)}
    for b in (blocked_by or []):
        if b not in known:
            raise CruxError(f"cannot block on '{b}': no such task")
    if parent is not None and parent not in known:
        raise CruxError(f"cannot parent under '{parent}': no such task")
    ensure_tasks(root)
    tid = _new_id(v, "task")
    fn = _task_slug(root, f"{tid}_{title}", {t["fn"][:-3] for t in scan_tasks(root)}) + ".md"
    bn = task_basenames(v)
    links = ", ".join(task_ref_link(r, bn) for r in (refs or [])) or "_(none)_"
    hyp = ", ".join(f"{hid}:{c}" for hid, c in (hypothesis_refs or []))
    text = fill(load_template("task"), id=tid, title=title, category=category,
                hypothesis_refs=hyp,
                parent=parent or "", refs=", ".join(refs or []),
                blocked_by=", ".join(blocked_by or []) or NO_BLOCKERS,
                ref_links=links, why=why or "_(what this unblocks)_")
    write_if_changed(os.path.join(task_dir(root), fn), text)
    refresh(root)
    return tid, fn

def _get_task(root, tid):
    for t in scan_tasks(root):
        if t["id"] == tid:
            return t
    raise CruxError(f"no task with id '{tid}'")

def _write_task(t):
    t["fm"]["updated"] = now()
    write_if_changed(t["path"], render_doc(t["fm"], t["body"]))

def cmd_task_done(root, tid, outputs=None):
    """Close a task. An output ref is HARD-REQUIRED and must resolve.

    An action that completed almost always produced something — code at a path, a dataset, a
    figure, a registered page — and a bare ticked box discards exactly the thing that makes
    this layer traversable."""
    t = _get_task(root, tid)
    for o in (outputs or []):
        t["body"] = append_bullet(t["body"], "Output", o)
    if not parse_artifacts(t["body"], "output"):
        raise CruxError(f"cannot close {tid}: record what it produced first — "
                        f"`crux task done {tid} --output <path|[[node]]>`. A task that "
                        f"genuinely produced nothing was probably `drop`ped, not done.")
    t["fm"]["status"] = "done"
    _write_task(t)
    refresh(root)
    return "done"

def cmd_task_drop(root, tid):
    """Drop a task. No output required: a drop is a decision not to do the work, and the
    reason belongs in the body and in `git log`, not in a field nobody reads (spec 06)."""
    t = _get_task(root, tid)
    t["fm"]["status"] = "dropped"
    _write_task(t)
    refresh(root)
    return "dropped"

# --- the gating split (2.3) ---------------------------------------------------------------
# The original rule was "a task may never create direction". It was doing double duty and it
# breaks the first time someone observes that a RUN is a task. Replaced by:
#
#     Work never creates direction. Work produces outputs — and an output that is evidence
#     about a hypothesis enters the gated tier.
#
# The line moves from WHICH LAYER to WHICH OUTPUT, and it becomes computable:
#   - a task with no hypothesis_refs is act-and-report. Ticking "fetched the antibody lot"
#     sets no direction, spends no compute, records no scientific result.
#   - a task WITH them concluded something about a claim, so the PI accepts it — exactly as
#     `answer` and `approve` are accepted today.
#
# What accepting does, and what it deliberately does NOT do: it records the PI's signature on
# the task and marks the parent question of each refed hypothesis `stale` — the existing
# "new evidence landed, your interpretation may be out of date" signal that `cmd_close`
# already sets and `cmd_answer` already clears. It writes no verdict, no status, no tick, and
# touches no roll-up. Feeding the derivation was considered and DECLINED: spec 15 rules that
# only `cmd_close` writes a verdict, and a task feeding it would let an agent set a verdict
# the PI never ticked. Work informs; it does not decide.
TASK_ACCEPTED = "accepted"

def task_pending_gate(t):
    """Is this task waiting for the PI? An experiment that has completed and not been
    accepted. A chore is never here, however large; an experiment always is, however small."""
    return (task_is_experiment(t) and t["status"] == "done"
            and not t["fm"].get(TASK_ACCEPTED))

def cmd_task_review(root):
    """(id, title, hypothesis_refs, drifted) for every experiment awaiting the PI's
    acceptance.

    A SEPARATE queue from `cmd_review`, deliberately. That function returns 15's
    `(id, title, drift)` three-tuple and is rendered in three places including
    `snapshot()["queue"]`; reshaping it would be a contract change on a surface the cockpit
    already draws. And the two decisions are not the same decision: "is this question
    settled" is not "do you accept what this run concluded".

    `drifted` lists the refed hypotheses whose commitment was edited after the run. Surfaced
    HERE because this is the exact moment the PI is deciding — and it BLOCKS NOTHING."""
    v = Vault(root)
    out = []
    for t in scan_tasks(root):
        if not task_pending_gate(t):
            continue
        drifted = [hid for hid, _ in t["hypothesis_refs"]
                   if hid in v.nodes and lock_drift(v.nodes[hid])]
        out.append((t["id"], t["title"], t["hypothesis_refs"], drifted))
    return out

def cmd_task_accept(root, tid):
    """The PI's signature on what an experiment concluded. Returns the timestamp.

    Idempotent: the first acceptance's timestamp is the record, so re-accepting never
    rewrites history — the same contract `cmd_approve` has for a synthesis."""
    t = _get_task(root, tid)
    if not task_is_experiment(t):
        raise CruxError(f"'{tid}' is not an experiment — it concluded nothing about a "
                        f"hypothesis, so there is nothing to accept. Ordinary tasks are "
                        f"act-and-report: `crux task done {tid}` is the whole of it.")
    existing = t["fm"].get(TASK_ACCEPTED)
    if existing:
        return str(existing)
    stamp = now()
    t["fm"][TASK_ACCEPTED] = stamp
    _write_task(t)
    # New evidence has landed against these hypotheses, so their questions' standing
    # interpretations may be out of date. This is the ONLY thing acceptance writes outside
    # the task, it is a pre-existing flag with pre-existing meaning, and it moves no verdict.
    v = Vault(root)
    for hid, _ in t["hypothesis_refs"]:
        n = v.nodes.get(hid)
        parent = v.nodes.get(n.parent) if n else None
        if parent and parent.type == "question" and not parent["fm"].get("stale"):
            parent["fm"]["stale"] = True
            write_if_changed(parent["path"], render_doc(parent["fm"], parent["body"]))
    refresh(root)
    return stamp

def task_gate_info(root, tasks=None):
    """`info` lines for the gate. Both are information, never problems: an unaccepted dropped
    experiment is a real record, and a nested experiment is legitimate."""
    out = []
    tasks = tasks if tasks is not None else scan_tasks(root)
    by = {t["id"]: t for t in tasks}
    unacc = [t for t in tasks if task_is_experiment(t) and t["status"] == "dropped"
             and not t["fm"].get(TASK_ACCEPTED)]
    if unacc:
        out.append(("task:unaccepted",
                    f"{len(unacc)} dropped experiment{'' if len(unacc) == 1 else 's'} "
                    f"({', '.join(t['id'] for t in unacc)}) recorded a conclusion that was "
                    f"never accepted — it is history, not evidence.", len(unacc)))
    nested = [t for t in tasks if task_is_experiment(t) and t["parent"] in by
              and task_is_experiment(by[t["parent"]])]
    if nested:
        out.append(("task:nested-experiment",
                    f"{len(nested)} experiment{'' if len(nested) == 1 else 's'} sit under "
                    f"another experiment ({', '.join(t['id'] for t in nested)}) — each fires "
                    f"its own review gate.", len(nested)))
    return out

def cmd_task_categories(root, add=None):
    """Read, or grow, the declared category list. Growth is an explicit act with a diff —
    the moment of friction that stops taxonomy drift."""
    cats = task_categories(root)
    if add is None:
        return cats
    add = add.strip()
    if not add or re.search(r"\s", add):
        raise CruxError(f"a category is a single token with no whitespace (got {add!r}) — the "
                        f"cockpit renders it as the CSS class `t-{add}`")
    if add == TASK_RESERVED_CATEGORY:
        raise CruxError(f"'{TASK_RESERVED_CATEGORY}' is reserved and computed; it cannot be declared")
    if add in cats:
        return cats
    v = Vault(root)
    cats = cats + (add,)
    v.cfg[TASK_CATEGORIES_KEY] = ", ".join(cats)
    _save_cfg(v)
    return cats

# --- the dependency graph (2.1) -----------------------------------------------------------
# `blocked` is COMPUTED and never stored, for the same reason the role of an experiment is:
# a state you can compute is a state that cannot drift. External blockers are not a state
# either — "waiting on cluster quota" is a dependency on a task called *obtain cluster
# quota*, which keeps one rule instead of two and fits "tasks are actions".
def task_by_id(root):
    return {t["id"]: t for t in scan_tasks(root)}

def task_cleared(t):
    """Is this blocker discharged? `done` OR `dropped`.

    The spec's own acceptance criterion says "blockers are all `done`", and read literally
    that strands a task forever whenever its blocker is dropped — invisibly, inside the one
    query the agent is told to work from, which is the "nothing gets forgotten" failure
    produced by the layer's primary query. A drop is a decision not to do the work, so it
    discharges the edge; `validate` then reports the promotion as info so it is never silent.
    """
    return t["status"] in ("done", "dropped")

def task_cycle(t, by_id, field):
    """The cycle through `field` (`blocked_by` or `parent`) reachable from `t`, as the list of
    ids that close it, or None.

    A full coloured DFS, not a single-path walk: `blocked_by` is a LIST, so a task can have a
    clean first branch and a cycle on its second. Following only the first candidate finds the
    common case and silently misses that one — which is precisely the class of bug a
    deterministic check exists to make impossible. Grey = on the current path (closing onto it
    is the cycle), black = fully explored and proven acyclic, so each task is expanded once."""
    grey, black, path = set(), set(), []

    def walk(x):
        xid = x["id"]
        grey.add(xid); path.append(xid)
        nxt = [x["parent"]] if field == "parent" else x["blocked_by"]
        for cand in [c for c in nxt if c]:
            if cand in grey:
                return path[path.index(cand):] + [cand]
            if cand in by_id and cand not in black:
                found = walk(by_id[cand])
                if found:
                    return found
        grey.discard(xid); black.add(xid); path.pop()
        return None

    return walk(t)

def task_state(t, by_id):
    """The task's state as a reader sees it: its stored status, or the computed `blocked`.

    A task in a dependency cycle is reported `blocked` — it genuinely cannot be worked, and
    `validate` is what says why."""
    if t["status"] != "open":
        return t["status"]
    if task_cycle(t, by_id, "blocked_by"):
        return TASK_BLOCKED
    return TASK_BLOCKED if any(b not in by_id or not task_cleared(by_id[b])
                               for b in t["blocked_by"]) else "open"

def task_frontier(root, tasks=None):
    """Work the frontier: the open tasks whose blockers are all discharged, in id order.
    The one question an agent asks at the start of a session and a PI asks on opening the
    tab — and, since 2.2, it spans chores and experiments in one result."""
    tasks = tasks if tasks is not None else scan_tasks(root)
    by = {t["id"]: t for t in tasks}
    return [t for t in tasks if task_state(t, by) == "open"]

def task_drop_cleared(root, tasks=None):
    """Tasks that reached the frontier because a blocker was DROPPED rather than done."""
    tasks = tasks if tasks is not None else scan_tasks(root)
    by = {t["id"]: t for t in tasks}
    return [t for t in task_frontier(root, tasks)
            if any(b in by and by[b]["status"] == "dropped" for b in t["blocked_by"])]

def cmd_task_list(root, frontier=False, status=None, category=None, ref=None, blocks=None):
    """One list verb with filters rather than four verbs. `--ref q21` answers "what is open
    under q21" and `--blocks t9` answers "what blocks anything currently running" — the
    spec's other two named queries — without either needing its own command.

    `blocked` is a legal filter value even though it is never a legal stored value. That
    asymmetry is the point."""
    tasks = scan_tasks(root)
    by = {t["id"]: t for t in tasks}
    out = task_frontier(root, tasks) if frontier else list(tasks)
    if status:
        out = [t for t in out if task_state(t, by) == status]
    if category:
        out = [t for t in out if t["category"] == category]
    if ref:
        out = [t for t in out if ref in t["refs"]]
    if blocks:
        out = [t for t in out if blocks in by and t["id"] in by[blocks]["blocked_by"]]
    return out

def tasks_by_node(root, tasks=None):
    """{node id: [task ids]} — the COMPUTED backlink, node -> tasks.

    Computed rather than written, exactly as the wiki tab's backlinks are: a task ref is
    many-to-many and churns weekly, so writing it would mean every `crux task add` edits N
    node files. (07's `RD::` is written instead, and that is not an inconsistency — an RD is
    one-per-node, permanent, and belongs in the Obsidian graph. Node-tree lineage is written;
    the task graph is derived.)"""
    out = {}
    for t in (tasks if tasks is not None else scan_tasks(root)):
        for r in t["refs"]:
            out.setdefault(r, []).append(t["id"])
    return out

def experiments_by_hypothesis(root, tasks=None):
    """{hypothesis id: [{task, conclusion, status}]} — the computed hypothesis -> experiments
    backlink. Nothing here is written into the node, and nothing here moves its verdict."""
    out = {}
    for t in (tasks if tasks is not None else scan_tasks(root)):
        for hid, concl in t["hypothesis_refs"]:
            out.setdefault(hid, []).append({"task": t["id"], "conclusion": concl,
                                            "status": t["status"]})
    return out

def _task_snapshot(root, v=None):
    """The `tasks` block of snapshot(): the whole work layer as the cockpit reads it.

    Inert-but-present on a vault with no tasks/ (`active: False`), which is the shape
    `_wiki_snapshot` already uses — copied verbatim so a consumer never has to test for the
    key. `blocked` and `is_experiment` are published as COMPUTED values: that is not a
    contradiction of "never stored", it is what stops the cockpit keeping its own copy of the
    rule, exactly as `limits` publishes the economy budgets."""
    if not task_active(root):
        return {"active": False, "categories": list(DEFAULT_TASK_CATEGORIES),
                "reserved_category": TASK_RESERVED_CATEGORY, "conclusions": list(CONCLUSIONS),
                "items": [], "frontier": [], "queue": []}
    v = v or Vault(root)
    tasks = scan_tasks(root)
    by = {t["id"]: t for t in tasks}
    items = []
    for t in tasks:
        d = task_json(root, t["id"], v)
        d["state"] = task_state(t, by)
        d["blocks"] = [x["id"] for x in tasks if t["id"] in x["blocked_by"]]
        d["children"] = [x["id"] for x in tasks if x["parent"] == t["id"]]
        items.append(d)
    return {"active": True,
            "categories": list(task_categories(root)),
            "reserved_category": TASK_RESERVED_CATEGORY,
            "conclusions": list(CONCLUSIONS),
            "items": items,
            "frontier": [t["id"] for t in task_frontier(root, tasks)],
            "queue": [{"id": i, "title": ti,
                       "hypothesis_refs": [{"id": h, "conclusion": c} for h, c in hr],
                       "drifted": d}
                      for i, ti, hr, d in cmd_task_review(root)]}

def task_json(root, tid, v=None):
    """One task's read-only JSON — the shape `snapshot` will publish under `tasks.items`
    (2.4). Public so `crux task show --json` reuses the serializer instead of growing a
    second one that can drift from it."""
    t = _get_task(root, tid)
    v = v or Vault(root)
    return {"id": t["id"], "title": t["title"], "category": task_category(t),
            "declared_category": t["category"],
            "is_experiment": task_is_experiment(t),
            "status": t["status"], "parent": t["parent"], "blocked_by": t["blocked_by"],
            "refs": t["refs"], "outputs": t["outputs"],
            # each refed hypothesis carries WHICH SIDE of spec 15's boundary it sits on. The
            # stamp is read from the node, never copied onto the task: a pre-15 hypothesis
            # stays pre-15 forever, and an experiment about it is a record on the task's
            # side, not a retro-stamp on the node's.
            "accepted": t["fm"].get(TASK_ACCEPTED) or None,
            "pending_gate": task_pending_gate(t),
            "hypothesis_refs": [{"id": hid, "conclusion": c,
                                 "schema": node_schema(v.nodes[hid]) if hid in v.nodes else None}
                                for hid, c in t["hypothesis_refs"]],
            "created": t["fm"].get("created"), "updated": t["fm"].get("updated")}

def task_info(root, v=None):
    """The taskhub's `info` lines — namespace `task:`. Information, never a problem: a
    dropped task is a decision, not a defect, and `ok` must never turn on one."""
    out = []
    if not task_active(root):
        return out
    tasks = scan_tasks(root)
    cleared = task_drop_cleared(root, tasks)
    if cleared:
        out.append(("task:drop-cleared",
                    f"{len(cleared)} task{'' if len(cleared) == 1 else 's'} reached the "
                    f"frontier because a blocker was dropped, not done "
                    f"({', '.join(t['id'] for t in cleared)}) — check the work is still "
                    f"wanted.", len(cleared)))
    n = sum(1 for t in tasks if t["status"] == "dropped")
    if n:
        out.append(("task:dropped",
                    f"{n} task{'' if n == 1 else 's'} {'is' if n == 1 else 'are'} dropped — "
                    f"work deliberately not done. `git log` carries why.", n))
    # hierarchy is operative (PI ruling 2026-08-21: warn, never refuse): a parent may
    # legitimately close ahead of its parts, so this informs and `ok` never turns on it.
    # A dropped subtask discharges, exactly as a dropped blocker clears its edge.
    over = [t for t in tasks if t["status"] == "done"
            and any(c["parent"] == t["id"] and not task_cleared(c) for c in tasks)]
    if over:
        out.append(("task:open-subtasks",
                    f"{len(over)} done task{'' if len(over) == 1 else 's'} "
                    f"({', '.join(t['id'] for t in over)}) "
                    f"{'has' if len(over) == 1 else 'have'} open or blocked subtasks — "
                    f"a parent closed over unfinished parts.", len(over)))
    return out

def validate_tasks(root):
    """Structural lint over the taskhub — mechanical checks only. Whether a task is worth
    recording, and whether `done` is honest, is judgment: that lives in the skill."""
    problems = []
    if not task_active(root):
        return problems
    v = Vault(root)
    tasks = scan_tasks(root)
    ids = {t["id"] for t in tasks}
    cats = task_categories(root)
    universe = _link_universe(root, v)
    for t in tasks:
        tid = t["id"]
        if not tid:
            problems.append((f"task:{t['fn']}", f"task file '{t['fn']}': missing required field 'id'"))
            continue
        for k in ("title", "category", "status"):
            if t["fm"].get(k) in (None, ""):
                problems.append((tid, f"task '{tid}': missing required field '{k}'"))
        # `blocked_by` is mandatory so that a missing edge is a visible omission rather than
        # silence. `None` is the literal for "no edge, deliberately".
        if t["fm"].get("blocked_by") in (None, ""):
            problems.append((tid, f"task '{tid}': missing required field 'blocked_by' "
                                  f"(use `{NO_BLOCKERS}` when nothing blocks it)"))
        if t["status"] == TASK_BLOCKED:
            problems.append((tid, f"task '{tid}': '{TASK_BLOCKED}' is computed from the "
                                  f"dependency graph and is never stored — set "
                                  f"{'/'.join(TASK_STATUS)} instead"))
        elif t["status"] not in TASK_STATUS:
            problems.append((tid, f"task '{tid}': bad status '{t['status']}'"))
        c = t["category"]
        if c == TASK_RESERVED_CATEGORY:
            problems.append((tid, f"task '{tid}': category '{TASK_RESERVED_CATEGORY}' is "
                                  f"reserved and computed, never written by hand"))
        elif c and c not in cats:
            problems.append((tid, f"task '{tid}': undeclared category '{c}' (this vault "
                                  f"declares {', '.join(cats)})"))
        for r in t["refs"]:
            if r not in universe:
                problems.append((tid, f"task '{tid}': ref '{r}' resolves to nothing"))
        # the experiment half: each ref names a hypothesis, and says what this run concluded
        # about it. A pre-15 (unstamped) hypothesis is refable without restriction — the
        # conclusion lives on the TASK's record, so nothing about the old node is
        # retro-checked, re-verdicted or flagged, which is exactly what 15.0 guarantees.
        for hid, concl in t["hypothesis_refs"]:
            n = v.nodes.get(hid)
            if n is None:
                problems.append((tid, f"task '{tid}': hypothesis_refs names '{hid}', which is "
                                      f"not in this vault"))
            elif n.type != "idea":
                problems.append((tid, f"task '{tid}': hypothesis_refs names '{hid}', a "
                                      f"'{n.type}' — an experiment bears on a hypothesis"))
            if concl == RETIRED_CONCLUSION:
                problems.append((tid, f"task '{tid}': conclusion '{RETIRED_CONCLUSION}' for "
                                      f"'{hid}' is retired (spec 15); use one of "
                                      f"{', '.join(CONCLUSIONS)}"))
            elif concl not in CONCLUSIONS:
                problems.append((tid, f"task '{tid}': unknown conclusion '{concl}' for "
                                      f"'{hid}' (use {', '.join(CONCLUSIONS)})"))
        for b in t["blocked_by"]:
            if b not in ids:
                problems.append((tid, f"task '{tid}': blocked_by '{b}' is not a task"))
        if t["parent"] and t["parent"] not in ids:
            problems.append((tid, f"task '{tid}': parent '{t['parent']}' is not a task"))
        for field in ("blocked_by", "parent"):
            cyc = task_cycle(t, {x["id"]: x for x in tasks}, field)
            if cyc:
                problems.append((tid, f"task '{tid}': {field} cycle "
                                      f"{' → '.join(cyc)}"))
        if t["status"] == "done":
            if not t["outputs"]:
                problems.append((tid, f"task '{tid}': done with no output recorded under "
                                      f"'## Output'"))
            for o in t["outputs"]:
                problems += _task_output_problem(root, tid, o, universe)
    return problems

def _task_output_problem(root, tid, o, universe):
    """One output ref, checked. Two forms, both reusing machinery that already exists: a
    vault-relative path (the `## Artifacts` rules — inside the vault, and it resolves), or a
    `[[wikilink]]` to a node, a wiki page or an RD, for the many research outputs that are
    real but are not files."""
    path = o["path"]
    link = link_targets(path) or link_targets(o["label"])
    if link:
        return [] if any(x in universe or x.split("/")[-1] in
                         {y.split("/")[-1] for y in universe} for x in link) else \
               [(tid, f"task '{tid}': output [[{link[0]}]] resolves to nothing")]
    if artifact_escapes(path):
        return [(tid, f"task '{tid}': output path must be inside the vault: '{path}'")]
    if not os.path.isfile(os.path.join(root, path)):
        return [(tid, f"task '{tid}': output '{path}' does not exist")]
    return []

# ----------------------------------------------------------------------------- commands (called by CLI + selftest)
def _write_obsidian_vault(root):
    """Make the vault a recognized Obsidian vault out of the box: the presence of
    `.obsidian/app.json` is what makes Obsidian open the folder as an *existing* vault
    (no 'create vault?' prompt), so the Q/H `[[Parent::]]` graph is one click away.
    Empty config = Obsidian fills in its own sane defaults on first open."""
    od = os.path.join(root, ".obsidian")
    os.makedirs(od, exist_ok=True)
    write_if_changed(os.path.join(od, "app.json"), "{}\n")

def cmd_init(title, dirpath=".", goal=""):
    root = os.path.abspath(dirpath)
    os.makedirs(root, exist_ok=True)
    if os.path.exists(os.path.join(root, VAULT_MARKER)):
        raise CruxError("a crux vault already exists here")
    slug = slugify(title)
    cfg = {"title": title, "slug": slug, "root_id": "root", "engine_version": ENGINE_VERSION,
           "counter_q": 0, "counter_h": 0, "counter_s": 0, "counter_t": 0,
           # the declared task-category list: seeded here so a vault is usable from minute
           # one, and grown only by `crux task categories --add` — an explicit act with a
           # diff, which is what makes "declared" mean anything. Without a declared list you
           # get `data-prep`, `datasets` and `data-related` as siblings after six months.
           TASK_CATEGORIES_KEY: ", ".join(DEFAULT_TASK_CATEGORIES)}
    write_if_changed(os.path.join(root, VAULT_MARKER), yaml_dump(cfg) + "\n")
    body = fill(load_template("project"), id="root", title=title, goal=goal or "_(state the program goal)_")
    write_if_changed(os.path.join(root, f"{slug}.md"), body)
    ensure_glossary(root)       # empty: a new project has no shared vocabulary yet
    _write_obsidian_vault(root)
    refresh(root)
    return root, f"{slug}.md"

# ----------------------------------------------------------------------------- seed-spec (setup: read source -> propose tree -> approve -> write)
# The agent drafts one human-editable seed file; the human approves it; the engine
# materializes the whole vault atomically. Format = indented-bullet outline, indent
# (2 spaces) = nesting, type prefix = node kind:
#
#   - Project: TITLE — GOAL
#     - Q: a question
#       - Q: a nested question
#         - H: a hypothesis                         (open; not yet run)
#           - v: metric ≥ threshold vs baseline     (a verifiable)
#           - vn: known-good baseline reproduces    (an outcome-neutral control)
#       - H: [tested] an already-run hypothesis     (migration: reconstruct done work)
#         - v: [x] first check (found: 0.46 → 0.48) (tick = met; parenthetical = evidence)
#         - v: [ ] second check
#         - finding: one-line narrative of the result
#
# Rules mirror the model: Project→Q ; Q→Q|H ; H→v|vn|finding|problem. `vn:` is a `v:`
# that is outcome-neutral (a control). Verdicts on
# [tested] hypotheses are still derived mechanically from the ticks — the engine
# never invents them.
def _seed_val(line):
    """Return (indent, key, value) for a `  - Key: value` bullet, else None."""
    m = re.match(r"^(\s*)-\s+([A-Za-z]+):\s?(.*)$", line.rstrip())
    if not m:
        return None
    return len(m.group(1)), m.group(2).lower(), m.group(3).strip()

def _parse_verifiable(val):
    """A seed `- v:` / `- vn:` value -> {tick, kind, text, evidence}.

    Extraction order is fixed and load-bearing: tick, then the LEADING kind tag, then the
    TRAILING evidence parenthetical. Reversing the last two is how `(outcome-neutral)` ends
    up recorded as a finding — the reason the kind tag is anchored to the front."""
    m = re.match(r"\[([ xX-])\]\s*(.*)$", val)
    tick, text = (m.group(1).lower(), m.group(2).strip()) if m else (" ", val)
    kind, text = verifiable_kind(text)
    evidence = None
    if m:  # only tested verifiables carry a trailing (evidence) note
        em = re.search(r"\s*\((.*)\)\s*$", text)
        if em:
            evidence, text = em.group(1).strip(), text[:em.start()].strip()
    return {"tick": tick, "kind": kind, "text": text.strip(), "evidence": evidence}

def parse_seed(text):
    """Parse the seed outline into a project dict with nested children. Raises CruxError
    on malformed structure. Pure (no I/O) so the whole seed is validated before any write."""
    project, stack = None, []   # stack: list of (indent, node)
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parsed = _seed_val(raw)
        if not parsed:
            raise CruxError(f"seed: cannot parse line: {raw.strip()!r} "
                            "(expected `- Project:/Q:/H:/v:/finding: …`)")
        indent, key, val = parsed
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else None
        if key == "project":
            if parent is not None or project is not None:
                raise CruxError("seed: exactly one top-level `- Project:` is required")
            title, _, goal = val.partition(" — ")
            if not goal:
                title, _, goal = val.partition(" -- ")
            node = {"type": "project", "title": title.strip(),
                    "goal": goal.strip(), "children": []}
            project = node
        elif key == "q":
            if parent is None or parent["type"] not in ("project", "question"):
                raise CruxError(f"seed: a Q must sit under Project or another Q (got {val!r})")
            node = {"type": "question", "title": val, "children": []}
            parent["children"].append(node)
        elif key == "h":
            if parent is None or parent["type"] != "question":
                raise CruxError(f"seed: an H must sit under a Q (got {val!r})")
            tested = False
            m = re.match(r"\[tested\]\s*(.*)$", val, re.I)
            if m:
                tested, val = True, m.group(1).strip()
            node = {"type": "hypothesis", "title": val, "tested": tested,
                    "problem": "", "finding": "", "verifiables": []}
            parent["children"].append(node)
        elif key in ("v", "vn"):
            if parent is None or parent["type"] != "hypothesis":
                raise CruxError(f"seed: a verifiable ({key}) must sit under an H (got {val!r})")
            vf = _parse_verifiable(val)
            if key == "vn":                     # `vn:` is sugar for an outcome-neutral `v:`
                vf["kind"] = NEUTRAL_KIND
            parent["verifiables"].append(vf)
            node = None
        elif key in ("finding", "problem"):
            if parent is None or parent["type"] != "hypothesis":
                raise CruxError(f"seed: `{key}` must sit under an H (got {val!r})")
            parent[key] = val
            node = None
        else:
            raise CruxError(f"seed: unknown node type '{key}:' (use Project/Q/H/v/vn/finding/problem)")
        if node is not None:
            stack.append((indent, node))
    if project is None:
        raise CruxError("seed: no `- Project:` line found")
    return project

def _render_verifiables(body, verifiables):
    """Replace the template's `## Verifiables` list with the seed's ticks + evidence."""
    lines = []
    for vf in verifiables:
        ev = f"   ({vf['evidence']})" if vf["evidence"] else ""
        tag = f"[{vf['kind']}] " if vf.get("kind") == NEUTRAL_KIND else ""
        lines.append(f"- [{vf['tick']}] {tag}{vf['text']}{ev}")
    block = "\n".join(lines)
    return re.sub(r"(## Verifiables\n\n)(?:<!--.*?-->\n)?(?:- \[.\].*\n?)+",
                  lambda m: m.group(1) + block + "\n", body, count=1)

def _materialize(root, project):
    cmd_init(project["title"], root, goal=project["goal"] or "")
    def walk_question(node, parent_id):
        for child in node["children"]:
            if child["type"] == "question":
                qid, _ = cmd_ask(root, child["title"], parent=parent_id)
                walk_question(child, qid)
            else:
                _add_hypothesis(root, child, parent_id)
    def _add_hypothesis(root, h, qid):
        if h["tested"] and not h["verifiables"]:
            raise CruxError(f"seed: [tested] hypothesis {h['title']!r} needs at least one verifiable")
        hid, _, _ = cmd_hypothesize(
            root, h["title"], parent=qid, problem=h["problem"],
            verifiables=[vf["text"] for vf in h["verifiables"] if vf["kind"] != NEUTRAL_KIND],
            neutral=[vf["text"] for vf in h["verifiables"] if vf["kind"] == NEUTRAL_KIND])
        if not h["tested"]:
            return
        n = Vault(root).get(hid)
        # Reconstructed past work: drop the schema stamp so evidence semantics do not bind
        # it. `[tested]` means "this ran before crux was watching" — it cannot retroactively
        # acquire an outcome-neutral control or a pre-registered combination rule, and
        # demanding one would be the engine asking the PI to re-declare, after the fact,
        # what would have settled an already-settled claim. Untested seeded hypotheses are
        # genuinely new work and keep their stamp.
        n["fm"].pop("schema", None)
        n["fm"][RECONSTRUCTED] = True
        n["body"] = _render_verifiables(n["body"], h["verifiables"])
        write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
        cmd_close(root, hid, findings=h["finding"] or None)
    for child in project["children"]:
        if child["type"] != "question":
            raise CruxError("seed: the Project's direct children must be questions (Q)")
        qid, _ = cmd_ask(root, child["title"], parent=None)
        walk_question(child, qid)

def cmd_init_from(seed_path, dirpath="."):
    """Atomically materialize a whole vault from an approved seed outline."""
    root = os.path.abspath(dirpath)
    if os.path.exists(os.path.join(root, VAULT_MARKER)):
        raise CruxError("a crux vault already exists here")
    project = parse_seed(read(seed_path))          # fully validate before any write
    build = tempfile.mkdtemp(prefix="crux_build_")
    try:
        _materialize(build, project)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise
    os.makedirs(root, exist_ok=True)
    for fn in os.listdir(build):
        shutil.move(os.path.join(build, fn), os.path.join(root, fn))
    shutil.rmtree(build, ignore_errors=True)
    slug = slugify(project["title"])
    return root, f"{slug}.md"

def _save_cfg(v):
    write_if_changed(os.path.join(v.root, VAULT_MARKER), yaml_dump(v.cfg) + "\n")

def _new_id(v, kind):
    """Allocate the next id of `kind`. The counter is read with a DEFAULT rather than indexed:
    every vault written before a counter existed simply lacks the key, and `v.cfg[key] += 1`
    would raise KeyError on the first allocation after an upgrade — which is the most likely
    first action a user takes. (`counter_t` on any pre-2.0 vault is exactly this case.)"""
    key = {"question": "counter_q", "idea": "counter_h", "synthesis": "counter_s",
           "task": "counter_t"}[kind]
    v.cfg[key] = int(v.cfg.get(key) or 0) + 1
    prefix = {"question": "q", "idea": "h", "synthesis": "s", "task": "t"}[kind]
    _save_cfg(v)
    return f"{prefix}{v.cfg[key]}"

def cmd_ask(root, title, parent=None, body_text=""):
    v = Vault(root)
    parent = parent or v.cfg["root_id"]
    p = v.get(parent)
    if p.type not in ("project", "question"):
        raise CruxError("a question's parent must be the project or another question")
    nid = _new_id(v, "question")
    fn = f"{nid}_{slugify(title)}.md"
    text = fill(load_template("question"), id=nid, title=title,
                parent_id=parent, parent_basename=p.basename)
    if body_text:
        text = text.replace(f"## Question\n\n{title}", f"## Question\n\n{body_text}")
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn

def cmd_hypothesize(root, title, parent, problem="", verifiables=None, neutral=None,
                    rule=None, rule_m=None, null=None, fails_if=None, discriminates=None,
                    measurement=None, replicates=None, builds_on=None, nid=None, claim=None):
    """Returns (id, filename, warning). The third element is fan-out back-pressure — None
    when the parent question has room, a message when this hypothesis puts it over
    FANOUT_MAX. Never a refusal: proposing is cheap and sometimes right, so crux says the
    number out loud and lets the PI decide.

    `nid` (05.2) files at an id that was ALREADY allocated — the one autopilot reserved under
    the lock before any node existed — instead of allocating a second. The counter does not
    move, because it already moved when the id was handed out. `claim` puts the whole claim in
    `## Idea / Hypothesis` while the title stays the short form. Both absent is 05.1's
    behaviour, byte for byte."""
    v = Vault(root)
    p = v.get(parent)
    if p.type != "question":
        raise CruxError("a hypothesis must hang under a question (use `ask` first)")
    # lineage (spec 05): checked BEFORE anything is written, so a bad target leaves no node
    # behind to clean up. The rule is the whole reason the field is not a tree edge — an
    # attempt branched from another attempt is a SIBLING of it, under the same question.
    if builds_on:
        b = v.nodes.get(builds_on)
        if b is None:
            raise CruxError(f"builds_on '{builds_on}' does not exist")
        if b.type != "idea":
            raise CruxError(f"builds_on '{builds_on}' is a '{b.type}', not a hypothesis")
        if b.parent != parent:
            raise CruxError(f"builds_on '{builds_on}' sits under '{b.parent}', not under "
                            f"'{parent}'")
    # the reserved id (05.2), checked BEFORE anything is written — an id refused after the
    # counter moved would burn a hypothesis number for a node that never existed
    if nid is not None:
        if not re.fullmatch(r"h\d+", str(nid)):
            raise CruxError(f"hypothesis id '{nid}' is not a hypothesis id (h<number>)")
        if nid in v.nodes:
            raise CruxError(f"hypothesis id '{nid}' is already in use")
        allocated = int(v.cfg.get("counter_h") or 0)
        if natkey(nid)[1] > allocated:
            raise CruxError(f"hypothesis id '{nid}' was never allocated "
                            f"(counter_h is {allocated})")
    warning = fanout_pressure(v, parent)
    if nid is None:
        nid = _new_id(v, "idea")
    fn = f"{nid}_{slugify(title)}.md"
    text = fill(load_template("idea"), id=nid, title=title, parent_id=parent,
                parent_basename=p.basename, problem=problem or "_(why this is worth testing)_",
                verifiable=(verifiables[0] if verifiables else "_(state a falsifiable, pre-registered check)_"))
    # claim-directed checks first, then the outcome-neutral controls — the controls gate the
    # run, and a reader should meet the claim before the apparatus check for it
    # scenarios are positional over (claim checks..., controls...) — the same order the
    # lines are written in, which is the order the lock hashes them in
    fi = list(fails_if or []); dz = list(discriminates or [])
    def _scen(i):
        s = fi[i] if i < len(fi) else None
        if not s:
            return ""
        line = f"\n      fails-if:: {s}"
        if i < len(dz) and dz[i]:
            line += "\n      discriminates:: true"
        return line
    rest = [f"- [ ] {x}{_scen(i + 1)}" for i, x in enumerate((verifiables or [])[1:])]
    noff = len(verifiables or [])
    rest += [f"- [ ] [{NEUTRAL_KIND}] {x}{_scen(noff + i)}" for i, x in enumerate(neutral or [])]
    if rest or fi:
        lead = verifiables[0] if verifiables else "_(state a falsifiable, pre-registered check)_"
        text = text.replace(f"- [ ] {lead}",
                            f"- [ ] {lead}{_scen(0)}" + ("\n" + "\n".join(rest) if rest else ""))
    if claim is not None:
        text = text.replace(f"## Idea / Hypothesis\n\n{title}\n",
                            f"## Idea / Hypothesis\n\n{claim.strip()}\n", 1)
    if null is not None:
        p = null_problem(null, SCHEMA_GENERATION)
        if p:
            raise CruxError(f"null: {p}")
        fm_t, body_t = parse_doc(text)
        text = render_doc(fm_t, set_null(body_t, null))
    if rule is not None:
        if rule in RESERVED_RULES:
            raise CruxError(f"combination rule '{rule}' is reserved, not implemented — see "
                            f"spec 15. Use one of {', '.join(COMBINATION_RULES)}.")
        if rule not in COMBINATION_RULES:
            raise CruxError(f"unknown combination rule '{rule}' — use one of "
                            f"{', '.join(COMBINATION_RULES)}")
        fm, body = parse_doc(text)
        fm[RULE_FIELD] = rule
        if rule_m is not None:
            fm[RULE_M_FIELD] = int(rule_m)
        text = render_doc(fm, body)
    # the methodology slots (spec 13). Declared here or later by hand — either way they are
    # ordinary frontmatter, never part of the commitment the run locks.
    if measurement is not None or replicates is not None:
        fm, body = parse_doc(text)
        if measurement is not None:
            fm[MEASUREMENT_FIELD] = measurement
        if replicates is not None:
            fm[REPLICATES_FIELD] = replicates
        text = render_doc(fm, body)
    if builds_on:
        fm, body = parse_doc(text)
        fm[BUILDS_ON_FIELD] = builds_on
        text = render_doc(fm, body)
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn, warning

def _bump(node):
    node["fm"]["updated"] = now()

def append_bullet(body, heading, text):
    """Append `- text` to the `## heading` section, dropping that section's `_(placeholder)_`
    line if it still has one. Everything here is scoped to the section on purpose: a
    body-wide placeholder test silently dropped every run link after the first once a second
    section (`## Artifacts`) shipped with a placeholder of its own. Non-bullet lines in the
    section (an HTML comment, say) are preserved in place."""
    lines = body.splitlines()
    start = None
    for i, l in enumerate(lines):
        if l.startswith("## ") and l[3:].strip().lower() == heading.lower():
            start = i
            break
    if start is None:
        return body
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")), len(lines))
    seg = [l for l in lines[start + 1:end] if not re.match(r"\s*_\(.*\)_\s*$", l)]
    while seg and not seg[-1].strip():
        seg.pop()
    if not seg or seg[0].strip():
        seg.insert(0, "")
    seg.append(f"- {text}")
    return "\n".join(lines[:start + 1] + seg + [""] + lines[end:])

def cmd_test(root, nid, to=None, run=None):
    v = Vault(root)
    n = v.get(nid)
    if n.type != "idea":
        raise CruxError("test applies to ideas/hypotheses only")
    order = IDEA_STATUS
    target = to or order[min(order.index(n.status) + 1, len(order) - 1)]
    if target not in ("staged", "running"):
        raise CruxError("test moves an idea to 'staged' or 'running'")
    if target == "running" and sum(count_verifiables(n["body"])) == 0:
        raise CruxError(f"refusing to run {nid}: register at least one verifiable first")
    if target == "running":
        for gap in (neutral_gap(n), rule_gap(n), null_gap(n), scenario_gap(n)):
            if gap:
                raise CruxError(f"refusing to run {nid}: " + gap.split(": ", 1)[1])
    n["fm"]["status"] = target
    if target == "running":
        take_lock(n, "running")
    if run:
        n["body"] = append_bullet(n["body"], "Run Links", run)
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    refresh(root)
    return target

def cmd_close(root, nid, metric=None, findings=None, no_claim=False):
    """Close one hypothesis on its pre-registered checks. The verdict is DERIVED here and is
    never an argument — that is most of what makes a crux verdict worth reading.

    `no_claim` is the autopilot's no-claim path, and it is deliberately a FACT rather than a
    verdict: the caller reports that this node carries no hypothesis, and the engine decides
    what that means. A driver still cannot name a verdict, and no value of this argument
    produces `supported`.

    It exists because an autopilot attempt is now measured even when its REPORT was faulty — a
    reporting mistake must not destroy a measurement — so a node whose claim is the
    AUTO_NO_CLAIM placeholder can arrive here carrying a real, fully graded tick vector. That
    vector would derive `supported`, and the verdict would be a judgment about a hypothesis
    nobody ever stated. So the measurement is kept, the metric is kept, and the judgment is
    withheld: `invalid-run` already means "the apparatus ran and the claim cannot be read",
    which is the honest reading of an attempt that claimed nothing."""
    v = Vault(root)
    n = v.get(nid)
    if n.type != "idea":
        raise CruxError("close applies to ideas/hypotheses (use `answer` to close a question)")
    met, unmet, na = count_verifiables(n["body"])
    if met + unmet + na == 0:
        raise CruxError("cannot close: no verifiables to evaluate")
    # THE BOUNDARY. Dispatch on the node's stamp, never on "is it already done" —
    # `cmd_close` has no status precondition and is re-runnable on a done node, so an old
    # node re-closed after an upgrade must still get the old function. This is the line
    # that stops the engine overturning recorded science.
    if binds_evidence_semantics(n):
        gap = rule_gap(n)
        if gap:
            raise CruxError(f"cannot close {nid}: " + gap.split(": ", 1)[1])
        by = count_verifiables_by_kind(n["body"])
        rule, m = node_rule(n)
        verdict = derive_verdict_15(by[DEFAULT_KIND], by[NEUTRAL_KIND], rule, m)
    else:
        verdict = derive_verdict(met, unmet, na)
    # AFTER the derivation, never instead of it: the gap that is checked, the rule that is
    # read and the refusal on an unclosable node all still happen, so a no-claim attempt is
    # held to every structural rule its siblings are. Only the reading of the vector is
    # withheld, because there is no claim for it to be a reading OF.
    if no_claim:
        verdict = "invalid-run"
    # `cmd_close` has no status precondition and is reachable straight from `idea`, so a
    # lock taken only at `running` is bypassable by the shortest path the CLI offers. Lock
    # here too, and record that it was never a pre-registration — refusing the close instead
    # would just push the user through `test --to running` first, laundering the same thing.
    take_lock(n, "close")
    n["fm"]["status"] = "done"
    n["fm"]["verdict"] = verdict
    if metric is not None:
        n["fm"]["metric"] = metric
    if findings:
        n["body"] = re.sub(r"## Findings\n\n_\(written by the PI/agent when the case is closed\)_",
                           f"## Findings\n\n{findings}", n["body"])
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    # new evidence -> parent question interpretation goes stale
    parent = v.nodes.get(n.parent)
    if parent and parent.type == "question":
        parent["fm"]["stale"] = True
        write_if_changed(parent["path"], render_doc(parent["fm"], parent["body"]))
    refresh(root)
    return verdict

def cmd_review(root):
    """(id, title, drift) for every question awaiting a decision. `drift` is True when any
    hypothesis under it has an edited commitment — surfaced HERE because this is the exact
    moment the PI is deciding, and a flag they never see is a flag that did nothing."""
    v = Vault(root)
    def drifted(qid):
        return any(lock_drift(v.nodes[c]) for c in v.children.get(qid, ())
                   if v.nodes[c].type == "idea")
    return [(n.id, n.title, drifted(n.id)) for n in v.nodes.values()
            if n.type == "question" and n.status == "review"]

def gate_scope(v, near, ids):
    """`{id: (relation, in_scope)}` for a batch of pending gates against `near`.

    One helper so the two queues — questions at `review`, experiments at `task review` —
    annotate identically. They are different decisions, but "is this any of the PI's business
    right now" is the same question for both."""
    out = {}
    for i in ids:
        rel = gate_relation(v, near, i)
        out[i] = (rel, rel != "unrelated")
    return out

def approved_synthesis(v, qid):
    """The approved synthesis that closes `qid`, or None. Deterministic when several
    relate to the same question: the lowest id wins."""
    cands = [n for n in v.nodes.values()
             if n.type == "synthesis" and n["fm"].get("approved")
             and qid in _related_ids(v, n["body"])]
    return min(cands, key=lambda n: natkey(n.id)).id if cands else None

def cmd_approve_null(root, hid):
    """The PI's sign-off on the null — the gate between `crux-null` and `crux-verifiables`.
    Idempotent: the first approval's timestamp is the record.

    The approval stores a hash of what was approved, so EDITING the null silently clears it.
    That is not bookkeeping: a different null is a different claim about what would be boring,
    and checks written against the old one no longer discriminate against anything."""
    v = Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise CruxError(f"approve-null applies to a hypothesis (got a '{n.type}' for '{hid}')")
    p = null_problem(_null_text(n) or "", node_schema(n))
    if p:
        raise CruxError(f"cannot approve {hid}'s null: {p}")
    if n["fm"].get(NULL_APPROVED) and n["fm"].get("null_hash") == _null_hash(n):
        return str(n["fm"][NULL_APPROVED])
    stamp = now()
    n["fm"][NULL_APPROVED] = stamp
    n["fm"]["null_hash"] = _null_hash(n)
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    refresh(root)
    return stamp

def set_null(body, text):
    """Write `text` as the whole content of `## Null`, replacing the template's guidance
    comment and placeholder. One helper, because two callers were each carrying their own
    regex and both broke the moment the template gained a comment."""
    lines, out, in_sec, done = body.splitlines(), [], False, False
    for line in lines:
        if line.startswith("## "):
            if in_sec and not done:
                out.append(text); out.append(""); done = True
            in_sec = line[3:].strip().lower() == "null"
            out.append(line)
            continue
        if in_sec and not done:
            continue                      # drop the comment + placeholder wholesale
        out.append(line)
    if in_sec and not done:
        out.append(""); out.append(text)
    return "\n".join(out)

def _null_hash(n):
    return hashlib.sha256(" ".join((_null_text(n) or "").split()).encode("utf-8")).hexdigest()[:16]

def cmd_approve(root, sid):
    """The PI's sign-off on a synthesis — the second human touchpoint of the close
    sequence, and the thing `answer` checks for. Idempotent: the first approval's
    timestamp is the record, so re-approving never rewrites history."""
    v = Vault(root)
    n = v.get(sid)
    if n.type != "synthesis":
        raise CruxError(f"approve applies to a synthesis (got a '{n.type}' for '{sid}'); "
                        f"draft one with `crux synthesize \"…\" --for <question-id>`")
    existing = n["fm"].get("approved")
    if existing:
        return str(existing)
    stamp = now()
    n["fm"]["approved"] = stamp
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    refresh(root)
    return stamp

def cmd_answer(root, qid, text=None):
    v = Vault(root)
    n = v.get(qid)
    if n.type != "question":
        raise CruxError("answer applies to questions")
    # v0.5 close-gate: a question is closed by an APPROVED synthesis, never by a bare
    # status flip. Questions already resolved by a pre-1.2 engine are grandfathered —
    # this gate applies to new closes only (see docs/prd/v0.5-cockpit-evidence.md §I).
    sid = approved_synthesis(v, qid)
    if not sid:
        raise CruxError(
            f"cannot resolve {qid}: a question closes only on an approved synthesis.\n"
            f"    1. crux synthesize \"what {qid} settled\" --for {qid}\n"
            f"    2. the PI reads it, then: crux approve <sid>\n"
            f"    3. crux answer {qid}")
    n["fm"]["status"] = "resolved"
    n["fm"]["synthesis"] = sid
    n["fm"]["stale"] = False
    if text:
        n["body"] = re.sub(r"## Answer so far\n\n.*?\n\n(?=<!-- crux:ledger:start)",
                           f"## Answer so far\n\n{text}\n\n", n["body"], flags=re.S)
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    # resolving a sub-question is new evidence for its parent question
    parent = v.nodes.get(n.parent)
    if parent and parent.type == "question":
        parent["fm"]["stale"] = True
        write_if_changed(parent["path"], render_doc(parent["fm"], parent["body"]))
    refresh(root)
    return qid

def cmd_pursue(root, qid, idea_title=None):
    v = Vault(root)
    n = v.get(qid)
    if n.type != "question":
        raise CruxError("pursue applies to questions")
    n["fm"]["status"] = "open"
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    new = None
    if idea_title:
        new = cmd_hypothesize(root, idea_title, qid)  # adds a non-terminal child, then refreshes → Q stays open
    else:
        refresh(root)
    return new

def cmd_synthesize(root, title, questions):
    v = Vault(root)
    for q in questions:
        v.get(q)  # validate existence
    nid = _new_id(v, "synthesis")
    fn = f"{nid}_{slugify(title)}.md"
    related = ", ".join(f"[[{v.get(q).basename}]]" for q in questions)
    text = fill(load_template("synthesis"), id=nid, title=title, related=related)
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn

def design_info(v):
    """The methodology slots, reported as INFORMATION — namespace `design:`.

    Never a problem and never a warning. A missing declaration does not make the record
    incoherent, and `ok` turns on warnings, so warning here would put every vault written
    before 3.1 into red over a field it never had.

    One line per condition with a count, not one per node, and silence when there is nothing
    to say — the shape `boundary_info` and `task_info` already use."""
    out = []
    for field, label, why in (
            (MEASUREMENT_FIELD, "name a measurement",
             "what is measured, and with what instrument"),
            (REPLICATES_FIELD, "state replicates",
             "how many runs the claim rests on")):
        gap = [x for x in v.nodes.values()
               if x.type == "idea" and x.status in DESIGN_STATUSES
               and not _fm_text(x, field)]
        if gap:
            out.append((f"design:{field}",
                        f"{len(gap)} hypothes{'is does' if len(gap) == 1 else 'es do'} not "
                        f"{label} before the run ({', '.join(sorted(x.id for x in gap))}) — "
                        f"declare {why} in frontmatter, or run `crux-design`.", len(gap)))
    return out

def boundary_info(v):
    """The evidence-semantics boundary, reported as INFORMATION. Never a problem, never a
    warning: a pre-15 vault is correct, not broken, and spec 15 is explicit that the boundary
    is reported "as information, never as a problem". One line per condition, not one per
    node, and silence when there is nothing to say."""
    out = []
    olds = [x for x in v.nodes.values()
            if x.type == "idea" and not binds_evidence_semantics(x)]
    recon = [x for x in olds if x["fm"].get(RECONSTRUCTED)]
    n = len(olds) - len(recon)
    if n:
        out.append(("boundary:evidence-semantics",
                    f"{n} hypothes{'is' if n == 1 else 'es'} predate evidence semantics "
                    f"(no schema stamp); spec-15 rules do not apply to them.", n))
    if recon:
        # A vault created today can hold these, so calling them "old" would be baffling.
        # They are reconstructed history: the science happened before crux was watching.
        out.append(("boundary:reconstructed",
                    f"{len(recon)} hypothes{'is was' if len(recon) == 1 else 'es were'} "
                    f"reconstructed from a seed and never pre-registered — the results "
                    f"existed before the checks were written down.", len(recon)))
    return out

def _section_placeholder(name):
    return {"ELI5":     "_(one sentence, plain language, no jargon)_",
            "TL;DR":    "_(one paragraph: what this claims, and what would settle it)_",
            "Null":     "_(one line: the cheapest way this result could be trivially true — "
                        "name a family from " + ", ".join(CONFOUND_FAMILIES) + ")_",
            "Artifacts": "_(none yet)_",
            "Protocol": "_(optional: the pre-registered rules — endpoints, thresholds, "
                        "scope — locked before any run)_"}.get(name, "_(not written)_")

def _migrate_plan(v):
    """[{id, adds}] — which structural sections each node is missing. Read-only."""
    out = []
    for nid, n in sorted(v.nodes.items(), key=lambda kv: natkey(kv[0])):
        want = MIGRATE_SECTIONS.get(n.type)
        if not want:
            continue
        have = {l[3:].strip() for l in n["body"].splitlines() if l.startswith("## ")}
        adds = [s for s in want if s not in have]
        if adds:
            out.append({"id": nid, "adds": adds})
    return out

def cmd_migrate(root, apply=False):
    """Bridge a vault's SCHEMA to the current engine: add the structural sections newer
    versions expect, empty. Dry run by default.

    What it will not do — structurally, rather than by policy: write any field in
    MIGRATE_FORBIDDEN, fill a `## Null`, touch `## Verifiables`, or move a verdict. A
    migration able to do those could overturn recorded science, which is the one thing the
    leash forbids, so this verb has no code path that writes them."""
    v = Vault(root)
    plan = _migrate_plan(v)
    if not apply:
        return {"applied": False, "changes": plan}
    for entry in plan:
        n = v.get(entry["id"])
        # append before the generated ledger (questions) or at the end, so authored content
        # is never reflowed — only added to
        pre, sep, post = n["body"].partition(LEDGER_START)
        add = "".join(f"\n## {s}\n\n{_section_placeholder(s)}\n" for s in entry["adds"])
        body = pre.rstrip() + "\n" + add + ("\n" + sep + post if sep else "")
        fm = dict(n["fm"])
        for f in MIGRATE_FORBIDDEN:
            fm.pop(f, None)          # belt and braces: a migration cannot introduce one
        write_if_changed(n["path"], render_doc(fm, body))
    refresh(root)
    return {"applied": True, "changes": plan}

# ------------------------------------------------------------------------------- doctor
# The install's own health check. Everything INSTALL.md documents under "Troubleshooting" is
# a state a machine can read, and the worst of them is silent: install.sh symlinks the skills
# and the agent roster INTO a clone, so moving that clone leaves dangling links and the skills
# simply stop existing — no error, anywhere, ever.
#
# Deterministic on purpose. Every check below is an os.path call, a version tuple compare, or
# a string compare on the vault stamp. There is no judgment in it, which is what lets it run
# from a bare clone with no agent present and lets selftest gate it.
#
# THREE levels, because two is a loophole. A drifted vault and an available release are both
# real things to say and neither is a broken install; folding them into `fail` would make the
# exit code useless in a script, and dropping them would make the verb blind to the second
# most common way crux confuses someone.
DOCTOR_SKILL_DIRS = ("~/.claude/skills", "~/.agents/skills")   # Claude Code · the shared dir
DOCTOR_AGENT_DIR  = "~/.claude/agents"                          # flat <name>.md, per install.sh
SCAFFOLD_MODULES  = ("engine", "render", "serve", "update", "evals", "crux")
SCAFFOLD_DIRS     = ("templates", "webui")


def _install_shape():
    """('clone' | 'skills' | 'unknown', path) — the layout this engine runs from. Local
    import, matching every other update.py call site here; a missing module means the
    layout is simply unknown, never a crashed health check."""
    try:
        import update as _u
        return _u.detect_install(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        return "unknown", os.path.dirname(os.path.abspath(__file__))


def _doc(name, level, detail, fix=""):
    """One line of the report. `fix` is the literal command to run, and is REQUIRED on
    anything that is not ok — a diagnostic that leaves you to search the docs for the remedy
    has moved the problem rather than solved it."""
    return {"name": name, "level": level, "detail": detail, "fix": fix}


def _link_state(path):
    """('missing' | 'dangling' | 'link' | 'real', resolved-target-or-None).

    `os.path.exists` follows symlinks, so a dangling link is exists()==False and
    islink()==True at once — which is exactly the state that makes this failure invisible."""
    if os.path.islink(path):
        target = os.path.realpath(path)
        return ("link", target) if os.path.exists(target) else ("dangling", target)
    if os.path.exists(path):
        return "real", path
    return "missing", None


def _doctor_python():
    v = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info < (3, 8):
        return _doc("python", "fail", f"{v} at {sys.executable} — crux needs >= 3.8",
                    "install Python 3.8+ and put it on PATH")
    return _doc("python", "ok", f"{v} at {sys.executable}")


def _doctor_engine():
    here = os.path.dirname(os.path.abspath(__file__))
    missing = [m + ".py" for m in SCAFFOLD_MODULES if not os.path.exists(os.path.join(here, m + ".py"))]
    missing += [d + "/" for d in SCAFFOLD_DIRS if not os.path.isdir(os.path.join(here, d))]
    if missing:
        return _doc("engine", "fail", f"{here} is missing {', '.join(missing)}",
                    "re-clone crux, or `npx skills update`")
    return _doc("engine", "ok",
                f"{len(SCAFFOLD_MODULES)} modules + {'/, '.join(SCAFFOLD_DIRS)}/ present in {here}")


def _doctor_skills(skills_dirs=None):
    dirs = [os.path.expanduser(d) for d in (skills_dirs or DOCTOR_SKILL_DIRS)]
    live, dead, notes = [], [], []
    for d in dirs:
        state, target = _link_state(os.path.join(d, "crux"))
        if state == "dangling":
            dead.append(d); notes.append(f"{d}/crux → {target} (gone)")
        elif state in ("link", "real"):
            live.append(d); notes.append(f"{d}/crux → {target}" if state == "link" else f"{d}/crux (copy)")
    if dead:
        return _doc("skills", "fail", "; ".join(notes),
                    "the clone the symlink points into moved or was deleted — re-clone crux "
                    "and re-run ./install.sh")
    if live:
        return _doc("skills", "ok", "; ".join(notes))
    # Not an error: `./crux --help` and `crux serve --dir …` work from a bare clone with no
    # agent anywhere. Say the install is absent, do not call it broken.
    return _doc("skills", "warn", "crux is in none of " + ", ".join(dirs),
                "./install.sh   (or: npx skills add mehdiforoozandeh/crux --all)")


def _doctor_agents(agents_dir=None):
    d = os.path.expanduser(agents_dir or DOCTOR_AGENT_DIR)
    kind, repo = _install_shape()
    roster = []
    if kind == "clone" and os.path.isdir(os.path.join(repo, "agents")):
        roster = sorted(n for n in os.listdir(os.path.join(repo, "agents"))
                        if os.path.isfile(os.path.join(repo, "agents", n, "AGENT.md")))
    if not os.path.isdir(d):
        return _doc("agents", "warn", f"no agent directory at {d}", "./install.sh")
    installed, dead = [], []
    for f in sorted(os.listdir(d)):
        if not f.startswith("crux-") or not f.endswith(".md"):
            continue
        state, _t = _link_state(os.path.join(d, f))
        (dead if state == "dangling" else installed).append(f[:-3])
    if dead:
        return _doc("agents", "fail", f"{len(dead)} dangling in {d}: {', '.join(dead)}",
                    "re-clone crux and re-run ./install.sh")
    if roster and set(roster) - set(installed):
        miss = sorted(set(roster) - set(installed))
        return _doc("agents", "warn",
                    f"{len(installed)} of {len(roster)} installed in {d} — missing {', '.join(miss)}",
                    "./install.sh")
    return _doc("agents", "ok", f"{len(installed)} crux-*.md in {d}")


def _doctor_version():
    kind, path = _install_shape()
    where = {"clone": f"clone at {path}", "skills": f"skills install at {path}"}.get(kind, f"unknown layout at {path}")
    base = f"crux v{CRUX_VERSION} · engine v{ENGINE_VERSION} · {where}"
    try:
        import update as _u
        cache = _u.read_cache()
        latest = cache.get("latest")
        # Cache only — never a socket. doctor is the verb you run when something is already
        # wrong, which is exactly when a network round-trip is the last thing you want.
        if latest and _u.is_newer(latest, CRUX_VERSION):
            return _doc("version", "warn", f"{base} — v{latest} is available",
                        _u.update_command(kind, path))
    except Exception:
        pass
    return _doc("version", "ok", base)


def _doctor_vault(root):
    cfg = yaml_load(read(os.path.join(root, VAULT_MARKER)))
    stamped = cfg.get("engine_version")
    stamped = None if stamped is None else str(stamped)
    if stamped is None:
        return _doc("vault", "ok", f"{root} — unstamped; the next write adopts v{ENGINE_VERSION}")
    if stamped != ENGINE_VERSION:
        return _doc("vault", "warn",
                    f"{root} — engine drift: stamped v{stamped}, running v{ENGINE_VERSION}",
                    f"pin the matching engine to reproduce recorded results, or run any "
                    f"write verb to re-stamp to v{ENGINE_VERSION}")
    return _doc("vault", "ok", f"{root} — stamped v{stamped}")


def _doctor_migrate(root):
    plan = _migrate_plan(Vault(root))
    if plan:
        return _doc("migrate", "warn",
                    f"{len(plan)} node(s) missing structural sections: "
                    + ", ".join(e["id"] for e in plan[:6]) + ("…" if len(plan) > 6 else ""),
                    "crux migrate            (dry run)   ·   crux migrate --apply")
    return _doc("migrate", "ok", "every node has the sections this engine expects")


def _doctor_voice_hook(settings_paths=None):
    """Is the chat-time voice lint actually wired in? (PRD 16.2)

    A WARN when absent, never a fail, for `_doctor_skills`' reason: crux runs perfectly well
    from a bare clone with no agent anywhere, and an install that is merely incomplete must
    not be reported as broken. The hook only means something where an agent is driving."""
    found, searched = voice_hook_state(settings_paths)
    if found:
        return _doc("voice-hook", "ok",
                    f"the chat-time voice lint is registered in {', '.join(found)}")
    return _doc("voice-hook", "warn",
                "the chat-time voice lint is in none of " + ", ".join(searched)
                + " — crux's own ids and vocabulary can reach the PI unnoticed",
                "./install.sh   (or: crux voice --install-hook)")


def cmd_doctor(root=None, skills_dirs=None, agents_dir=None, settings_paths=None):
    """Is this install healthy? Reports; never repairs.

    `root=None` resolves a vault upward from the current directory and simply omits the two
    vault checks when there is none — the state a broken install is usually in.

    Read-only, and strictly: this is the ONE verb that must not call
    `check_and_stamp_version`, because re-stamping would silently repair the very drift it
    exists to report. `skills_dirs` / `agents_dir` / `settings_paths` default to the real install targets
    are parameters so the suite can point them at a scratch dir."""
    checks = [_doctor_python(), _doctor_engine(),
              _doctor_skills(skills_dirs), _doctor_agents(agents_dir),
              _doctor_voice_hook(settings_paths), _doctor_version()]
    if root is None:
        try:
            root = find_vault()
        except CruxError:
            root = None
    if root:
        checks += [_doctor_vault(root), _doctor_migrate(root)]
    return {"ok": not any(c["level"] == "fail" for c in checks),
            "checks": checks, "crux_version": CRUX_VERSION, "engine_version": ENGINE_VERSION}


def gate_warnings(v):
    """The gate backlog: a question parked in `review` with no synthesis drafted for it. The
    one item on spec 09's audit list that was not already a check — over-cap nodes,
    unresolvable artifacts and unrun-idea pileup all shipped with specs 06 and v0.5."""
    out = []
    for nid, n in v.nodes.items():
        if n.type != "question" or n.status != "review":
            continue
        drafted = any(s.type == "synthesis" and nid in _related_ids(v, s["body"])
                      for s in v.nodes.values())
        if not drafted:
            out.append((nid, f"question '{nid}' has been awaiting a decision with no synthesis "
                             f"drafted for it. `crux synthesize \"what {nid} settled\" --for "
                             f"{nid}` is the first step; the PI approves it, then `crux answer`."))
    return out

def validation_report(root, checks=None, propose=None):
    """The full lint in two tiers. `problems` break the vault's integrity; `warnings` are the
    economy checks, which are advisory by design (see PROSE_CAP). `checks` selects a subset of
    CHECKS; None runs them all.

    This is the machine-readable form behind `crux validate --json` and the cockpit — one
    serializer, so the CLI, the GUI and an agent can never drift apart on what 'valid' means."""
    names = tuple(checks) if checks else CHECKS   # opt-in checks (decks) run only when named
    unknown = [c for c in names if c not in CHECKS + OPT_CHECKS]
    if unknown:
        raise CruxError(f"unknown check(s): {', '.join(unknown)} — known checks are "
                        f"{', '.join(CHECKS + OPT_CHECKS)} ({', '.join(OPT_CHECKS)} opt-in)")
    v = Vault(root)
    problems, warnings, info = [], [], []
    if "tree"    in names: problems += validate(v); info += boundary_info(v) + design_info(v)
    if "wiki"    in names: problems += validate_wiki(root)
    if "economy" in names: warnings += economy_warnings(v)
    if "fanout"  in names: warnings += fanout_warnings(v)
    if "tree"    in names: warnings += lock_warnings(v)
    if "rd"      in names: problems += validate_rd(root)
    if "tasks"   in names:
        problems += validate_tasks(root)
        info += task_info(root) + task_gate_info(root)
    if "decks"   in names: warnings += deck_warnings(root)
    if "gate"    in names: warnings += gate_warnings(v)
    # The glossary check is a FILTER, not a scan: with nothing proposed it has nothing to
    # filter and says nothing at all. That is what lets it sit in the default CHECKS without
    # changing one byte of output for every vault that exists today.
    cands = glossary_candidates(root, propose, v) if "glossary" in names else []
    info += glossary_info(cands)
    return {"ok": not problems and not warnings,     # `info` is deliberately NOT in `ok`
            "checks": list(names),
            "problems": [{"id": i, "message": m} for i, m in problems],
            "warnings": [{"id": i, "message": m} for i, m in warnings],
            "info": [dict({"id": i, "message": m}, **({"count": c} if c is not None else {}))
                     for i, m, c in info],
            "candidates": cands}

def cmd_validate(root, checks=None):
    """The hard problems only, as (id, message) pairs. Kept at this return type on purpose:
    it is what every caller and every selftest assert already expects. Warnings live in
    `validation_report`."""
    return [(p["id"], p["message"]) for p in validation_report(root, checks)["problems"]]

# ----------------------------------------------------------------------------- text status view
def status_text(root, node=None):
    v = Vault(root)
    if node:
        n = v.get(node)
        out = [f"{n.id} [{n.type}] {n.title}  —  status: {n.status}"]
        if n.type == "idea" and n["fm"].get("verdict"):
            out.append(f"  verdict: {n['fm']['verdict']}   metric: {n['fm'].get('metric') or '—'}")
        if n.type == "question":
            out.append("  ledger:")
            out.append("    " + ledger_block(v, n.id).replace("\n", "\n    "))
        return "\n".join(out)
    lines = []
    def walk(nid, depth):
        n = v.nodes[nid]
        tag = {"project": "▣", "question": "?", "idea": "•"}.get(n.type, "·")
        extra = ""
        if n.type == "idea" and n["fm"].get("verdict"):
            extra = f"  ({n['fm']['verdict']})"
        lines.append("  " * depth + f"{tag} {n.id} [{n.status}] {n.title}{extra}")
        for c in v.children.get(nid, []):
            walk(c, depth + 1)
    walk(v.cfg["root_id"], 0)
    return "\n".join(lines)

# ----------------------------------------------------------------------------- snapshot (read-only JSON contract for the GUI)
# `snapshot` is the single machine-readable view of a vault: the GUI (crux serve)
# consumes it as /snapshot.json and never re-parses markdown. Pure read — it builds a
# Vault and reads bodies, but writes nothing. Stdlib only; returns plain JSON types.
def _section(body, heading):
    """Return the text under a `## <heading>` up to the next `## ` (stripped, '' if absent)."""
    out, grab = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            grab = line[3:].strip().lower() == heading.lower()
            continue
        if grab:
            out.append(line)
    return "\n".join(out).strip()

def _summary(body, heading):
    """An `## ELI5` / `## TL;DR` section for the cockpit. Returns '' both when the section is
    absent (a pre-1.3 node) and when it still holds nothing but the template placeholder — a
    summary nobody has written should read as empty, not lead the detail pane with
    `_(one sentence, plain language, no jargon)_`."""
    text = _section(body, heading)
    return "" if not _prose_tokens(text) else text

def _verifiables(body):
    """The `## Verifiables` list as read-only tri-state:
    [{text, state, kind}] with state in met/unmet/na and kind in VERIFIABLE_KINDS.
    The `[kind]` tag is lifted into its own field and stripped from `text` — a reader should
    get a sentence, not markup."""
    items = []
    for c, text in _verifiable_lines(body):
        kind, text = verifiable_kind(text)
        state = "met" if c == "x" else "na" if c == "-" else "unmet"
        items.append({"text": text.strip(), "state": state, "kind": kind})
    return items

def _run_links(body):
    """Non-placeholder bullets under `## Run Links`."""
    links, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "run links"
            continue
        if in_sec and re.match(r"\s*- (?!_\(none)", line):
            links.append(line.strip()[2:].strip())
    return links

def _related_ids(v, body):
    """Question ids a synthesis links to, read in order from its `Related::` wikilinks."""
    by_basename = {n.basename: n.id for n in v.nodes.values()}
    ids = []
    for line in body.splitlines():
        if line.strip().startswith("Related::"):
            for m in re.finditer(r"\[\[([^\]|]+)", line):
                nid = by_basename.get(m.group(1).strip())
                if nid:
                    ids.append(nid)
    return ids

def _ledger_summary(c):
    """A compact one-line ledger summary for a review-queue row."""
    parts = [f"{c['children']} children", f"{c['ideas_done']}/{c['ideas_total']} ideas done"]
    verd = [f"{c[k]} {k}" for k in VERDICTS if c[k]]
    if verd:
        parts.append(", ".join(verd))
    if c["subq_total"]:
        parts.append(f"{c['subq_resolved']}/{c['subq_total']} sub-questions resolved")
    return " · ".join(parts)

def _rd_by_node(root):
    """{node id: active RD slug} in one scan. Passed into `_node_json` rather than looked up
    per node: the detail pane needs the pointer, and re-scanning rd/ once per node would make
    the snapshot quadratic in a vault that uses the layer heavily."""
    return {p["node"]: p["slug"] for p in reversed(scan_rd_pages(root))
            if p["status"] == "active" and p["node"]}

def _node_json(v, n, rd_map=None, task_map=None):
    d = {"id": n.id, "type": n.type, "title": n.title, "status": n.status}
    if n.type in ("question", "idea"):
        # the slug of this node's active RD, or None — so the pane can offer "open the
        # design" without walking the index
        d["rd"] = (_rd_by_node(v.root) if rd_map is None else rd_map).get(n.id)
        # the taskhub backlinks, COMPUTED here and stored nowhere. `tasks` is everything
        # serving this node; `experiments` is what was actually run against a hypothesis and
        # what it concluded — the one question the tree structurally cannot answer.
        tt = scan_tasks(v.root) if task_map is None else task_map
        d["tasks"] = tasks_by_node(v.root, tt).get(n.id, [])
        if n.type == "idea":
            d["experiments"] = experiments_by_hypothesis(v.root, tt).get(n.id, [])
        # which side of the evidence-semantics boundary this node sits on (0 = predates it),
        # published so the cockpit and an agent never re-read frontmatter to find out
        d["schema"] = node_schema(n)
    if n.type == "question":
        pre = n["body"].split(LEDGER_START)[0]
        d["parent"] = n.parent
        d["stale"] = bool(n["fm"].get("stale"))
        # the summary pair leads the cockpit's detail pane; `detail` is the long form behind
        # it. Before 1.3 `detail` WAS the lead, which is how a 5,000-word question arrived in
        # the pane as a wall of text.
        d["eli5"] = _summary(pre, "ELI5")
        d["tldr"] = _summary(pre, "TL;DR")
        d["words"] = prose_words(n["body"], "question")
        d["detail"] = _section(pre, "Question")
        d["answer"] = _section(pre, "Answer so far")
        d["synthesis"] = n["fm"].get("synthesis") or None   # the approved synthesis that closed it
        d["ledger"] = ledger_counts(v, n.id)
        d["children"] = list(v.children[n.id])
    elif n.type == "idea":
        verdict = n["fm"].get("verdict")
        d["parent"] = n.parent
        d["verdict"] = verdict if verdict in VERDICTS else None   # only ever a valid enum or None
        d["metric"] = n["fm"].get("metric") or None
        d["eli5"] = _summary(n["body"], "ELI5")
        d["tldr"] = _summary(n["body"], "TL;DR")
        d["words"] = prose_words(n["body"], "idea")
        d["problem"] = _section(n["body"], "Problem Statement")
        d["hypothesis"] = _section(n["body"], "Idea / Hypothesis")
        # the design, published (spec 13). `## Planned Intervention` has been written by the
        # template since v0.5 and read by NOTHING — not this serializer, not the cockpit — so
        # "the design lands in Planned Intervention" put it somewhere only `cat` could see.
        d["planned"] = _section(n["body"], "Planned Intervention")
        d["measurement"] = node_measurement(n)
        d["replicates"] = node_replicates(n)
        vfs = _verifiables(n["body"])
        for item, s in zip(vfs, verifiable_scenarios(n["body"])):
            item.update(s)
        d["verifiables"] = vfs
        # how the checks add up, published beside them — spec 15's render-time rule: the
        # verdict and the rule that produced it travel together wherever the node is read
        rule, m = node_rule(n) if binds_evidence_semantics(n) else (None, None)
        d["rule"], d["rule_m"] = rule, m
        d["tally"] = {k: list(x) for k, x in count_verifiables_by_kind(n["body"]).items()}
        d["null"] = _null_text(n)
        d["null_approved"] = str(n["fm"].get(NULL_APPROVED)) if n["fm"].get(NULL_APPROVED) else None
        d["locked"] = bool(n["fm"].get(LOCK_FIELD))
        d["lock_at"] = n["fm"].get(LOCK_WHERE_FIELD) or None
        d["drift"] = lock_drift(n)
        d["run_links"] = _run_links(n["body"])
        d["artifacts"] = [dict(a,
                               exists=(not artifact_escapes(a["path"])
                                       and os.path.isfile(os.path.join(v.root, a["path"]))),
                               servable=os.path.splitext(a["path"])[1].lower() in SERVABLE_EXT)
                          for a in parse_artifacts(n["body"])]
        d["findings"] = _section(n["body"], "Findings")
    elif n.type == "synthesis":
        d["related"] = _related_ids(v, n["body"])
        d["approved"] = n["fm"].get("approved") or None
        # the written verdict itself — a synthesis is what closes a question, so the cockpit
        # has to be able to show it. The `Related::` line is dropped: it's already `related`.
        d["body"] = "\n".join(l for l in n["body"].splitlines()
                              if not l.strip().startswith("Related::")).strip()
    return d

def node_json(vault, nid):
    """One node's read-only JSON — the same shape `snapshot()` puts under `nodes`. Public so
    `crux status <id> --json` reuses the serializer instead of growing a second one."""
    v = vault if isinstance(vault, Vault) else Vault(vault)
    return _node_json(v, v.get(nid))

def _subtree(v, nid):
    return {"id": nid, "children": [_subtree(v, c) for c in v.children[nid]]}

def _update_snapshot():
    """The `update` block: read from the update cache ONLY. `serve` must never touch the
    network, so the cockpit reports whatever the last CLI invocation happened to learn — and
    it stays silent when the user has opted out, so switching the check off silences the GUI
    chip too, not just the CLI line."""
    try:
        import update as _u
        if os.environ.get(_u.OPT_OUT):
            return {"latest": None, "available": False}
        latest = _u.read_cache().get("latest")
        return {"latest": latest, "available": bool(latest and _u.is_newer(latest, CRUX_VERSION))}
    except Exception:
        return {"latest": None, "available": False}

def snapshot(vault):
    """Read-only JSON snapshot of a vault. `vault` is a Vault or a root path.
    Keys: engine_version + crux_version, update (from the cache; never a live fetch),
    project, nodes (flat map by id), tree (parent-link hierarchy from the root; synthesis
    nodes are excluded — they attach via `related`), queue, wiki (index of the literature
    layer — page bodies stay behind /wiki/<slug>.json)."""
    v = vault if isinstance(vault, Vault) else Vault(vault)
    root_id = v.cfg["root_id"]
    root = v.get(root_id)
    rd_map = _rd_by_node(v.root)
    # scanned ONCE and threaded through, like rd_map: re-scanning tasks/ per node would make
    # the snapshot quadratic in a vault that uses the layer heavily
    task_map = scan_tasks(v.root)
    return {
        "engine_version": ENGINE_VERSION,
        "crux_version": CRUX_VERSION,
        "update": _update_snapshot(),
        # the economy budgets, published so the cockpit reads the engine's numbers instead of
        # keeping its own copy of them
        "limits": {"prose_cap": PROSE_CAP, "fanout_max": FANOUT_MAX},
        "project": {"id": root_id, "title": v.cfg.get("title"), "slug": v.cfg.get("slug"),
                    "status": root.status, "goal": _section(root["body"], "Goal")},
        "nodes": {nid: _node_json(v, n, rd_map, task_map) for nid, n in v.nodes.items()},
        "tree": _subtree(v, root_id),
        "queue": [{"id": n.id, "title": n.title, "summary": _ledger_summary(ledger_counts(v, n.id))}
                  for n in v.nodes.values() if n.type == "question" and n.status == "review"],
        "wiki": _wiki_snapshot(v.root),
        "rd": _rd_snapshot(v.root),
        "tasks": _task_snapshot(v.root, v),
    }

# ----------------------------------------------------------------------------- deck payload (spec 11 / prezit)
# `crux deck <anchor> --json` assembles the entire story material for one anchor's subtree,
# deterministically, from vault state only. The engine authors no prose and computes no
# number — selection and phrasing are the calling agent's whole job. Pure read.
#
# The traceability contract rides on `results/<hid>/metrics.json` (optional, written by the
# PI or the run harness, never by crux): nested JSON whose every leaf is an object carrying
# a required `value` (number, or a string for formatted displays like "1.20M") and optional
# `ci`/`se`/`n`/`unit`; unknown leaf keys are carried through untouched. An address is
# `<hid>#<dotted.key.path>` — vault-relative by construction.

class AddressError(CruxError):
    """A metrics address that cannot be resolved. `kind` distinguishes the failure so
    `--verify` can bucket it: bad-address | missing-file | missing-key | missing-value."""
    def __init__(self, kind, msg):
        super().__init__(msg)
        self.kind = kind

def load_metrics(root, hid):
    """Parsed results/<hid>/metrics.json, or None when the file does not exist."""
    path = os.path.join(root, RESULTS_DIR, hid, METRICS_FILE)
    if not os.path.isfile(path):
        return None
    try:
        return json.loads(read(path))
    except ValueError as e:
        raise CruxError(f"malformed {RESULTS_DIR}/{hid}/{METRICS_FILE}: {e}")

def resolve_address(root, addr):
    """Resolve `<hid>#<dotted.key.path>` to its metrics leaf. Raises AddressError with a
    distinct `kind` for each failure mode; never touches anything outside results/."""
    hid, sep, keypath = str(addr).partition("#")
    hid, keypath = hid.strip(), keypath.strip()
    if not sep or not hid or not keypath or "/" in hid or "\\" in hid or "." in hid:
        raise AddressError("bad-address",
                           f"bad metrics address '{addr}' (expected <hid>#<dotted.key.path>)")
    tree = load_metrics(root, hid)
    if tree is None:
        raise AddressError("missing-file", f"{addr}: no {RESULTS_DIR}/{hid}/{METRICS_FILE}")
    node = tree
    for part in keypath.split("."):
        if not isinstance(node, dict) or part not in node:
            raise AddressError("missing-key", f"{addr}: key path '{keypath}' does not resolve")
        node = node[part]
    if not isinstance(node, dict) or "value" not in node:
        raise AddressError("missing-value",
                           f"{addr}: not a metrics leaf (an object carrying 'value')")
    return node

def _metric_leaves(tree, prefix=""):
    """Depth-first [(dotted.path, leaf)] for every leaf (a dict carrying `value`), keys
    sorted lexicographically at every level — the defined, deterministic order."""
    out = []
    if isinstance(tree, dict):
        if "value" in tree:
            return [(prefix, tree)]
        for k in sorted(tree):
            out += _metric_leaves(tree[k], f"{prefix}.{k}" if prefix else k)
    return out

_FOUND_RE = re.compile(r"\s*\(found:\s*(.*?)\)\s*$")

def _deck_verifiables(body):
    """`## Verifiables` for the payload:
    [{text, state, kind, found, fails_if, discriminates}].

    `found` is the trailing `(found: …)` evidence parenthetical the seed materializer writes.

    `kind` (spec 15) matters to a deck: a failed OUTCOME-NEUTRAL check means the run was
    invalid, not that the claim was refuted, and a slide must not narrate the second when
    the vault recorded the first.

    `fails_if` / `discriminates` (spec 09) matter for the same reason one rung up. A slide
    saying "the check passed" is worth what the check was aimed at — and the check aimed at
    the declared null is the one that carries the claim. Without these the deck can present
    four decorative checks and the discriminating one identically."""
    out = []
    for item, s in zip(_verifiables(body), verifiable_scenarios(body)):
        m = _FOUND_RE.search(item["text"])
        out.append({"text": _FOUND_RE.sub("", item["text"]).strip(), "state": item["state"],
                    "kind": item["kind"], "found": m.group(1).strip() if m else None,
                    "fails_if": s["fails_if"], "discriminates": s["discriminates"]})
    return out

def _deck_text(body, heading):
    """A prose section for the payload: placeholder-empty like `_summary`, with HTML
    comments stripped — template guidance is not vault-authored content."""
    return re.sub(r"<!--.*?-->", "", _summary(body, heading), flags=re.S).strip()

def _deck_question_fields(n):
    pre = n["body"].split(LEDGER_START)[0]
    return {"question": _deck_text(pre, "Question"),
            "protocol": _deck_text(pre, "Protocol"),
            "answer_so_far": _deck_text(pre, "Answer so far")}

def _deck_idea_fields(n):
    verdict = n["fm"].get("verdict")
    rule, m = node_rule(n) if binds_evidence_semantics(n) else (None, None)
    return {"verdict": verdict if verdict in VERDICTS else None,
            "rule": rule, "rule_m": m, "drift": lock_drift(n),
            # the null is the bar restated: what the checks had to rule out. A deck that
            # reports a verdict without it is reporting a number with no scale.
            "null": _null_text(n),
            # a BOOLEAN, not the timestamp. The deck payload is byte-stable by contract and
            # carries no dates; what a slide needs is "was this bar signed off", not when.
            "null_approved": bool(n["fm"].get(NULL_APPROVED)),
            "metric": n["fm"].get("metric") or None,
            "verifiables": _deck_verifiables(n["body"]),
            "findings": _deck_text(n["body"], "Findings"),
            "artifacts": parse_artifacts(n["body"])}

def _deck_child(v, cid):
    n = v.nodes[cid]
    d = {"id": n.id, "type": n.type, "title": n.title, "status": n.status}
    if n.type == "question":
        d.update(_deck_question_fields(n))
    else:
        d.update(_deck_idea_fields(n))
    d["children"] = [_deck_child(v, c) for c in v.children.get(cid, ())]
    return d

def _subtree_ids(v, nid):
    """Every node id at or under `nid`, in tree order (the anchor first). The RD walk's
    traversal — deliberately NOT the wiki walk's anchor+ancestors, because RDs fill the
    methods slot for the anchor's own story and a parent's design is not it."""
    out = [nid]
    for c in v.children.get(nid, ()):
        out += _subtree_ids(v, c)
    return out

def _subtree_hids(v, nid):
    """Every idea id at or under `nid`, in tree order (the anchor itself included when it
    is an idea)."""
    n = v.nodes[nid]
    out = [nid] if n.type == "idea" else []
    for c in v.children.get(nid, ()):
        out += _subtree_hids(v, c)
    return out

def deck_payload(root, anchor):
    """The deterministic story payload behind `crux deck <anchor> --json`. Same vault
    state -> byte-identical json.dumps output: no timestamps, no absolute paths, every
    list order defined. Anchors with no children still emit (the proposal-deck case);
    a hypothesis anchor is legal and yields a shorter payload."""
    v = Vault(root)
    n = v.get(anchor)
    if n.type not in ("question", "idea"):
        raise CruxError(f"deck anchors on a question or hypothesis (got '{n.type}' for '{anchor}')")

    lineage = ancestor_chain(v, n)          # root -> parent, cycle-guarded (shared, D3)

    def _line(m):
        pre = m["body"].split(LEDGER_START)[0]
        txt = _deck_text(pre, "Goal") if m.type == "project" else _deck_text(pre, "Answer so far")
        return {"id": m.id, "type": m.type, "title": m.title, "status": m.status,
                "answer_so_far": txt}

    anchor_d = {"id": n.id, "type": n.type, "title": n.title, "status": n.status,
                "question": None, "protocol": None, "answer_so_far": None,
                "verdict": None, "rule": None, "rule_m": None, "drift": False,
                "null": None, "null_approved": False,
                "metric": None, "verifiables": [], "findings": None,
                "artifacts": []}
    anchor_d.update(_deck_question_fields(n) if n.type == "question" else _deck_idea_fields(n))

    siblings = [v.nodes[c] for c in v.children.get(n.parent, ()) if c != n.id] \
               if n.parent in v.nodes else []

    hids = _subtree_hids(v, n.id)
    ideas = [v.nodes[h] for h in hids]
    by_state = {s: sum(1 for i in ideas if i.status == s) for s in IDEA_STATUS}

    # wiki pages linked from the anchor, then its ancestors (root -> parent), first-mention
    # order, de-duplicated; entries point at the page, bodies stay in the vault
    wiki = wiki_refs(root, [n["body"]] + [m["body"] for m in lineage])

    # RD pages owned by the anchor or anything under it (spec 07). Active only: a superseded
    # design is history, and putting it on a methods slide is exactly what the supersession
    # lifecycle exists to prevent. Order is defined — tree order of the owning node, then
    # slug — because the payload's contract is byte-identical output for identical state.
    rd_by_node = {}
    for r in scan_rd_pages(root):
        if r["status"] == "active" and r["node"]:
            rd_by_node.setdefault(r["node"], []).append(r)
    rds = [{"slug": r["slug"], "title": r["title"], "path": _rel(root, r["path"])}
           for mid in _subtree_ids(v, n.id)
           for r in sorted(rd_by_node.get(mid, ()), key=lambda x: x["slug"])]

    sid = approved_synthesis(v, n.id) if n.type == "question" else None
    synthesis = None
    if sid:
        s = v.nodes[sid]
        synthesis = {"id": sid, "approved": str(s["fm"].get("approved")),
                     "text": "\n".join(l for l in s["body"].splitlines()
                                       if not l.strip().startswith("Related::")).strip()}

    figures = []
    hids = sorted(hids, key=natkey)     # defined order: hid natkey, then file/key order
    for hid in hids:
        labels = {a["path"]: a["label"] for a in parse_artifacts(v.nodes[hid]["body"])}
        for f in results_files(root, hid):
            rel = _rel(root, f)
            figures.append({"hid": hid, "path": rel,
                            "ext": os.path.splitext(f)[1].lower(),
                            "bytes": os.path.getsize(f), "caption": labels.get(rel, "")})

    metrics = []
    for hid in hids:
        tree = load_metrics(root, hid)
        if tree:
            for path, leaf in _metric_leaves(tree):
                metrics.append(dict({"addr": f"{hid}#{path}"}, **leaf))

    return {
        "engine_version": ENGINE_VERSION,
        "anchor": anchor_d,
        "lineage": [_line(m) for m in lineage],
        "siblings": [{"id": s.id, "type": s.type, "title": s.title, "status": s.status}
                     for s in siblings],
        "children": [_deck_child(v, c) for c in v.children.get(n.id, ())],
        "wiki": wiki,
        "rd": rds,  # spec 07: the anchor's subtree's design documents — the methods source
        "synthesis": synthesis,
        "scope": {"executed": by_state["running"] + by_state["done"],
                  "parked": by_state["idea"] + by_state["staged"],
                  "by_state": by_state},
        "figures": figures,
        "metrics": metrics,
    }

# ----------------------------------------------------------------------------- brief (spec 09)
# `crux brief <hid> --json` is the cold input every isolated agent receives.
#
# crux pre-registers verifiables. Pre-registration defends against changing the bar AFTER
# seeing results — it says nothing about WHO sets it, and an agent that has just spent an
# hour helping the PI argue for a hypothesis will pick a bar that hypothesis clears.
#
# Zero context does not fix that on its own, because the PARENT writes the prompt. "Verify
# that JEPA improves imputation" has already told the fresh agent which way to lean, and a
# selectively-quoted brief finishes the job. So the payload is assembled HERE, from vault
# state, and the calling agent never authors a sentence of it. Same node, same brief, every
# time — which is also what makes the isolation testable rather than merely claimed.
#
# Three exclusions, each for its own reason:
#
#   `## Problem Statement`  — spec 09 names it: that section is precisely where the
#                             advocacy lives.
#   the node's OWN findings and its own `(found: …)` values — an agent writing checks for a
#                             hypothesis must not see that hypothesis' results, or
#                             "pre-registration" is being performed after the fact. Sibling
#                             findings stay: those are the shared record a skeptical
#                             colleague would read.
#   metric VALUES             — the brief advertises what can be measured (key paths), never
#                             what was measured.
def ancestor_chain(v, n):
    """[Node] from the root down to `n`'s parent, cycle-guarded. Shared by `deck_payload`
    and `brief` (D3): both need the same walk, and two copies of a cycle guard is two places
    for it to be wrong."""
    out, cur, seen = [], n, {n.id}
    while cur.parent and cur.parent in v.nodes and cur.parent not in seen:
        cur = v.nodes[cur.parent]
        seen.add(cur.id)
        out.append(cur)
    out.reverse()
    return out

def wiki_refs(root, bodies):
    """[{slug, title, path}] for every wiki page linked from `bodies`, first-mention order,
    de-duplicated. Shared by `deck_payload` and `brief` (D3).

    Note what is NOT shared: the two payloads pick DIFFERENT bodies to scan and shape their
    own fields. The exclusions that make the brief safe live in `brief` itself, where they
    are sentinel-tested — sharing the walks must not quietly widen them."""
    pages = {p["slug"]: p for p in scan_wiki_pages(root)}
    out, seen = [], set()
    for body in bodies:
        for tgt in link_targets(body):
            if tgt in pages and tgt not in seen:
                seen.add(tgt)
                out.append({"slug": tgt, "title": pages[tgt]["title"],
                            "path": _rel(root, pages[tgt]["path"])})
    return out

def brief(root, hid, mode=BRIEF_DEFAULT_MODE):
    """The deterministic cold input for an agent. Pure read; byte-stable.

    Two modes, and the split is a SAFETY boundary rather than a convenience. `isolated` is
    09's bias-proof payload and stays the default, so a forgotten flag degrades to
    over-isolation rather than to leaked advocacy. `situate` (spec 13) is the opposite
    payload — subtree, ancestry, findings, the problem statement — for orienting the PI, who
    wrote the advocacy and cannot be biased by reading it back.

    An unrecognised mode is REFUSED. Any fallback rule ("unknown means the default") is one
    edit away from "unknown means the wider payload", and this is the flag where that edit
    would matter."""
    if mode not in BRIEF_MODES:
        raise CruxError(f"unknown brief mode '{mode}' — use one of {', '.join(BRIEF_MODES)}. "
                        f"'{BRIEF_DEFAULT_MODE}' is the default and the bias-proof one.")
    if mode == "situate":
        return situate_brief(root, hid)
    v = Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise CruxError(f"brief is per-hypothesis (got a '{n.type}' for '{hid}'); an agent's "
                        f"cold input is one claim, not a subtree")
    parent = v.nodes.get(n.parent)

    # ancestry: ids and titles ONLY, root -> parent. Enough to orient, too little to argue —
    # the shared walk hands back nodes; the narrowing to three fields is the brief's own.
    chain = ancestor_chain(v, n)
    anc = [{"id": m.id, "type": m.type, "title": m.title} for m in chain]

    # the shared factual record: what CLOSED siblings under the same question found.
    prior = []
    for cid in (v.children.get(n.parent, ()) if parent else ()):
        c = v.nodes[cid]
        if cid == hid or c.type != "idea" or c.status != TERMINAL_IDEA:
            continue
        prior.append({"id": c.id, "title": c.title, "verdict": c["fm"].get("verdict"),
                      "findings": _section(c["body"], "Findings")})

    # the pre-registered checks, stripped of their results
    vfs = []
    for item, s in zip(_verifiables(n["body"]), verifiable_scenarios(n["body"])):
        vfs.append({"text": _FOUND_RE.sub("", item["text"]).strip(),
                    "kind": item["kind"], "state": item["state"],
                    "fails_if": s["fails_if"], "discriminates": s["discriminates"]})

    wiki = wiki_refs(root, [n["body"]] + [m["body"] for m in chain])

    tree = load_metrics(root, hid)
    rule, m = node_rule(n) if binds_evidence_semantics(n) else (None, None)
    return {
        "engine_version": ENGINE_VERSION,
        "mode": mode,           # a payload names its own contract; inferring it from which
                                # fields are absent is right until someone adds a field
        "id": n.id,
        "claim": _section(n["body"], "Idea / Hypothesis"),
        "question": _section(parent["body"].split(LEDGER_START)[0], "Question") if parent else None,
        "ancestry": anc,
        "null": _null_text(n),
        "verifiables": vfs,
        "rule": rule, "rule_m": m,
        "schema": node_schema(n),
        "prior_findings": prior,
        "wiki": wiki,
        # addresses only. What CAN be measured, never what WAS.
        "metrics_available": [path for path, _leaf in _metric_leaves(tree or {})],
    }

def _null_text(n):
    """The declared null, or None. Defined here so `brief` can carry it from the moment the
    section exists (PRD 09.1) without the brief needing a second edit."""
    txt = _summary(n["body"], "Null")
    return re.sub(r"<!--.*?-->", "", txt, flags=re.S).strip() or None

# ----------------------------------------------------------------------------- situate (spec 13)
# `crux brief <node> --mode=situate --json` is the OTHER payload: what the PI needs after
# months away, when the tree shows what exists but not where we are.
#
# Five questions, and four of them are computable — which is why this is a mode on a verb
# rather than an agent's reading of the vault:
#
#   what q20 is            the node's own ELI5 / TL;DR
#   where we are           child statuses, the ledger, the ancestors' answers-so-far
#   what is known          `## Findings` on CLOSED children — never on an open one
#   what is yet to be tested  unrun ideas + unticked checks + open sub-questions  <- ENGINE
#   the paths forward      judgment. The agent's, not the engine's. Nothing here computes it.
#
# The engine authors no sentence of it: every string is vault text or a count. That is what
# keeps the payload assertable, and it is the same discipline `deck_payload` already keeps.
def situate_lint(text, anchors=()):
    """Findings on a composed situate ANSWER, as `(id, message)` pairs — empty when clean.

    Pure: no vault, no filesystem, no network. The agent drafts, lints, tightens, then speaks;
    spec 10's evals get the same oracle instead of inventing a second one.

    Five rules, each for a named failure:

      situate:empty        nothing to check — a silent pass would be the worst outcome
      situate:eli5-shape   an ELI5 that has quietly become a second TL;DR
      situate:tldr-shape   "three paragraphs" becoming seven
      situate:too-long     the failure spec 13 names by name
      situate:unanchored   the anchor is not named in the answer. Resolving to the WRONG
                           subtree is situate's worst failure, and the damage is carried by
                           *confident*, not by *wrong*: a misresolution the PI can see in the
                           first line costs one correction, one buried under four fluent
                           paragraphs is believed. The lint cannot check that the resolution
                           was right; it can check that it was disclosed.

    An anchor is either an id (`"q20"`) or an `(id, title)` pair, and a PAIR is satisfied by
    EITHER form (title matched verbatim, case-insensitively). That is spec 16's amendment,
    and it costs the check nothing: what the rule buys is disclosure of which subtree was
    read, and "here's where things stand on 'how do we cut the label budget'" discloses it
    exactly as well as "q20" does — to a PI who can act on it, rather than to one who has to
    go look up what q20 was."""
    out = []
    paras = [p for p in re.split(r"\n\s*\n", (text or "").strip()) if _prose_tokens(p)]
    if not paras:
        return [("situate:empty", "nothing to lint — a situate answer is one ELI5 paragraph "
                                  "then three TL;DR paragraphs.")]
    n_eli5 = len(_prose_tokens(paras[0]))
    if n_eli5 > SITUATE_BUDGET["eli5_words"]:
        out.append(("situate:eli5-shape",
                    f"the ELI5 paragraph runs {n_eli5} words (max "
                    f"{SITUATE_BUDGET['eli5_words']}). It is the one sentence someone outside "
                    f"the field could repeat back, not a second TL;DR."))
    if len(paras) - 1 != SITUATE_BUDGET["tldr_paragraphs"]:
        out.append(("situate:tldr-shape",
                    f"{len(paras) - 1} TL;DR paragraph(s) after the ELI5; the shape is "
                    f"exactly {SITUATE_BUDGET['tldr_paragraphs']} — what this is, where we "
                    f"are, what remains."))
    total = len(_prose_tokens(text))
    if total > SITUATE_BUDGET["total_words"]:
        out.append(("situate:too-long",
                    f"{total} words (max {SITUATE_BUDGET['total_words']}). Situating the PI "
                    f"is the whole job; a verbose orientation has failed at it."))
    missing = [_anchor_label(a) for a in (anchors or ()) if a and not _anchor_named(text, a)]
    if missing:
        out.append(("situate:unanchored",
                    f"the answer never names what it oriented over ({'; '.join(missing)}). "
                    f"Name the scope in the first line — the node's title is enough, and is "
                    f"what the PI can act on — because a wrong subtree must be visible, not "
                    f"buried under four fluent paragraphs."))
    return out


def _anchor_forms(anchor):
    """One anchor -> the strings that would satisfy it. A bare string is an id and nothing
    else; a pair is `(id, title)` and either form counts."""
    if isinstance(anchor, (list, tuple)):
        return [str(x) for x in anchor if str(x or "").strip()]
    return [str(anchor)]


#: trailing sentence punctuation on a title, dropped before matching. Spec 16's own worked
#: example is *"where things stand on 'how do we cut the label budget'"* and the node is
#: titled "How do we cut the label budget?" — an anchor rule that fails on a dropped question
#: mark is a rule about typography, not about disclosure. Leading and internal text is NOT
#: normalised: the point of the check is that the PI can recognise the subtree.
_TITLE_TAIL = " ?.!:;,"


def _anchor_named(text, anchor):
    forms = _anchor_forms(anchor)
    low = str(text or "").lower()
    # the id is matched case-sensitively (it is a token the engine allocated); the title
    # case-insensitively, because a first line legitimately capitalises the start of a
    # sentence and nobody should have to lower-case a question to satisfy a lint
    return any((f in str(text or "")) if i == 0
               else (f.strip().rstrip(_TITLE_TAIL).lower() in low)
               for i, f in enumerate(forms))


def _anchor_label(anchor):
    forms = _anchor_forms(anchor)
    return forms[0] if len(forms) < 2 else f"{forms[0]} — {forms[1]!r}"

def _situate_child(v, cid):
    """One descendant, summary-shaped and recursive. Deliberately NOT the whole node: an
    orientation that inlines 40,000 words of prose has failed at its only job. Findings ride
    only with a CLOSED hypothesis — an open node's half-written findings are not knowledge."""
    n = v.nodes[cid]
    verdict = n["fm"].get("verdict")
    return {
        "id": n.id, "type": n.type, "title": n.title, "status": n.status,
        "schema": node_schema(n),
        "eli5": _summary(n["body"], "ELI5") or None,
        "verdict": (verdict if verdict in VERDICTS else None) if n.type == "idea" else None,
        "tally": ({k: list(x) for k, x in count_verifiables_by_kind(n["body"]).items()}
                  if n.type == "idea" else None),
        "findings": (_deck_text(n["body"], "Findings") or None
                     if n.type == "idea" and n.status == TERMINAL_IDEA else None),
        "answer_so_far": (_deck_text(n["body"].split(LEDGER_START)[0], "Answer so far") or None
                          if n.type == "question" else None),
        "children": [_situate_child(v, c) for c in v.children.get(cid, ())],
    }

def _situate_untested(v, ids):
    """The row spec 13 marks *engine*: what is yet to be tested. Three kinds of "not yet",
    kept apart because they have different remedies — a hypothesis nobody ran, a check nobody
    ticked, and a question nobody answered."""
    unrun, checks, openq = [], [], []
    for nid in ids:
        n = v.nodes[nid]
        if n.type == "idea":
            if n.status in ("idea", "staged"):
                unrun.append({"id": n.id, "title": n.title, "status": n.status})
            for item in _verifiables(n["body"]):
                if item["state"] == "unmet":
                    checks.append({"hid": n.id, "text": item["text"], "kind": item["kind"]})
        elif n.type == "question" and n.status != TERMINAL_QUESTION:
            openq.append(n.id)
    return {"unrun_ideas": unrun, "open_checks": checks, "open_questions": openq}

def _situate_inbound(v, ids):
    """Nodes OUTSIDE the subtree whose prose links into it — *"h44 under q13 waits on this
    answer"*, which is exactly the fact that makes a returning PI stop and re-read.

    Ids and titles only. The size objection to inbound citations is entirely a property of
    the shape: a snippet is unbounded, `{id, type, title}` is forty bytes.

    The generated ledger is stripped before scanning. Every parent links every child there,
    so counting it would report a node's own parent as a citation — a true link that says
    nothing, drowning the ones that do."""
    inside = set(ids)
    names = {v.nodes[nid].basename: nid for nid in ids}
    names.update({nid: nid for nid in ids})
    out = []
    for nid in sorted(v.nodes, key=natkey):
        if nid in inside:
            continue
        n = v.nodes[nid]
        pre = n["body"].split(LEDGER_START)[0]
        if any(t in names for t in link_targets(pre)):
            out.append({"id": n.id, "type": n.type, "title": n.title})
    return out

def _situate_work(root, v, ids):
    """The taskhub, scoped to the subtree. Spec 13 predates spec 08, and its answer to *what
    is yet to be tested* — unrun ideas plus unticked checks — now under-reports: post-08 a
    hypothesis can have a run QUEUED or IN FLIGHT, and telling a PI who has been away that
    nothing has been tried while three runs are executing is the worst thing this payload
    could do.

    Present-and-inert without a taskhub, the shape `_wiki_snapshot` already uses, so no
    consumer has to test for the key."""
    if not task_active(root):
        return {"active": False, "open": [], "experiments": []}
    inside = set(ids)
    tasks = scan_tasks(root)
    opens, exps = [], []
    for t in tasks:
        hrefs = [h for h, _c in t["hypothesis_refs"]]
        touches = inside.intersection(set(t["refs"]) | set(hrefs))
        if not touches:
            continue
        if t["status"] == "open":
            opens.append({"id": t["id"], "title": t["title"], "category": task_category(t),
                          "state": task_state(t, {x["id"]: x for x in tasks})})
        if [h for h in hrefs if h in inside]:
            exps.append({"id": t["id"], "title": t["title"], "status": t["status"],
                         "hypothesis_refs": [{"id": h, "conclusion": c}
                                             for h, c in t["hypothesis_refs"] if h in inside]})
    return {"active": True, "open": opens, "experiments": exps}

def situate_brief(root, anchor=None):
    """`--mode=situate`: the orientation payload. Pure read; byte-stable.

    No anchor means the project root — the come-back-after-months case *is* the whole-vault
    case, and the root is an ordinary node, so this is the same walk one level higher rather
    than a second concept."""
    v = Vault(root)
    n = v.get(anchor) if anchor else v.get(v.cfg["root_id"])
    if n.type not in ("project", "question", "idea"):
        raise CruxError(f"situate orients over the project, a question or a hypothesis "
                        f"(got a '{n.type}' for '{n.id}')")

    # the SHARED walk (D3), like `brief` and `deck_payload`: one cycle guard, not three.
    # What is not shared is the field selection — situate needs each ancestor's answer-so-far,
    # which is exactly what the isolated brief withholds.
    chain = ancestor_chain(v, n)
    lineage = []
    for cur in chain:
        pre = cur["body"].split(LEDGER_START)[0]
        lineage.append({"id": cur.id, "type": cur.type, "title": cur.title,
                        "status": cur.status,
                        # a project's answer-so-far IS its goal; the field is one thing —
                        # "what this level is currently telling us" — not two
                        "answer_so_far": (_deck_text(pre, "Goal") if cur.type == "project"
                                          else _deck_text(pre, "Answer so far")) or None})

    pre = n["body"].split(LEDGER_START)[0]
    anchor_d = {
        "id": n.id, "type": n.type, "title": n.title, "status": n.status,
        "schema": node_schema(n),
        "eli5": _summary(n["body"], "ELI5") or None,
        "tldr": _summary(n["body"], "TL;DR") or None,
        # the problem statement IS carried here, and that is the whole point of the mode
        # split: 09 excludes it from an agent about to write the bar, because that is where
        # the advocacy lives. The PI wrote the advocacy. Reading it back cannot bias them.
        "problem": _deck_text(n["body"], "Problem Statement") or None,
        "question": _deck_text(pre, "Question") or None,
        "answer_so_far": (_deck_text(pre, "Goal") if n.type == "project"
                          else _deck_text(pre, "Answer so far")) or None,
        "verdict": None, "rule": None, "rule_m": None,
        "verifiables": [], "findings": None,
    }
    if n.type == "idea":
        verdict = n["fm"].get("verdict")
        rule, m = node_rule(n) if binds_evidence_semantics(n) else (None, None)
        anchor_d.update({"verdict": verdict if verdict in VERDICTS else None,
                         "rule": rule, "rule_m": m,
                         "verifiables": _verifiables(n["body"]),
                         "findings": _deck_text(n["body"], "Findings") or None})

    ids = _subtree_ids(v, n.id)
    # the shared wiki walk (D3), over the anchor's body then its ancestors' — the same bodies
    # the isolated brief scans, because "what has been read about this" does not change with
    # who is asking
    wiki = wiki_refs(root, [n["body"]] + [m["body"] for m in chain])

    sid = approved_synthesis(v, n.id) if n.type == "question" else None
    synthesis = None
    if sid:
        s = v.nodes[sid]
        synthesis = {"id": sid, "approved": str(s["fm"].get("approved")),
                     "text": "\n".join(l for l in s["body"].splitlines()
                                       if not l.strip().startswith("Related::")).strip()}

    return {
        "engine_version": ENGINE_VERSION,
        "mode": "situate",
        "anchor": anchor_d,
        "ancestry": lineage,
        "subtree": [_situate_child(v, c) for c in v.children.get(n.id, ())],
        "wiki": wiki,
        "synthesis": synthesis,
        "untested": _situate_untested(v, ids),
        "inbound": _situate_inbound(v, ids),
        "work": _situate_work(root, v, ids),
    }

# ----------------------------------------------------------------------------- deck verify / refresh (spec 11 §5d/5e)
# `--verify` walks the deck SOURCE (never a rendered DOM): chart tick/value/axis text is
# generated from data arrays already covered by their `src:` entries, so scanning rendered
# text would report every chart numeral as unsourced. Four buckets:
#   mismatch      address resolves, cached value differs            -> fail
#   unresolvable  no such hypothesis / file / key path / leaf       -> fail
#   derived       data-derived="a,b": inputs resolved, result NOT recomputed -> pass, listed
#   unsourced     a slide-prose numeral with no address             -> pass; fails --strict
# `data-src="literal"` is the strict-mode escape for definitional constants ("the 95%
# interval"). All findings are reported before any exit decision — a repair session needs
# the whole list, not the first line of it.

_SRC_OBJ_RE  = re.compile(r"\{[^{}]*?\bsrc\s*:\s*(['\"])([^'\"]+)\1[^{}]*\}")
_NUM_KEY_RE  = {k: re.compile(r"\b%s\s*:\s*(-?[0-9][0-9_.eE+-]*)" % k) for k in ("v", "lo", "hi")}
_DATA_TAG_RE = re.compile(r"<(\w+)([^>]*\bdata-(src|derived)\s*=\s*\"([^\"]*)\"[^>]*)>(.*?)</\1>", re.S)
_SLIDE_SEC_RE = re.compile(r'<section\s+class="slide[^"]*"[^>]*>(.*?)</section>', re.S)

def _slide_sections(text):
    """The real slides: _SLIDE_SEC_RE matches that do not START inside an HTML comment.
    A literal '<section class="slide">' quoted in a header comment (the reference deck's
    editing notes do exactly that) must never become a phantom slide."""
    spans = [(m.start(), m.end()) for m in re.finditer(r"<!--.*?-->", text, flags=re.S)]
    return [m for m in _SLIDE_SEC_RE.finditer(text)
            if not any(s <= m.start() < e for s, e in spans)]

def _slide_of(starts, pos):
    """1-based ordinal of the slide the position sits in, given the real slide start
    offsets (script blocks after the last section attribute to the last slide)."""
    return max(1, sum(1 for s in starts if s <= pos))

def _norm_display(s):
    """Normalize a displayed value for comparison (PI ruling #7): entities unescaped,
    unicode minus/en-dash -> '-', thousands separators and an explicit '+' dropped, a
    trailing '%' dropped."""
    s = html.unescape(str(s)).strip()
    s = s.replace("−", "-").replace("–", "-")
    s = s.replace(",", "")
    if s.endswith("%"):
        s = s[:-1].strip()
    if s.startswith("+"):
        s = s[1:]
    return s

def _values_match(display, value):
    d, w = _norm_display(display), _norm_display(value)
    if d == w:
        return True
    try:
        return float(d) == float(w)
    except (TypeError, ValueError):
        return False

def _numeral_token(tok):
    """The token stripped of edge punctuation if it is an unsourced-numeral CANDIDATE,
    else None. Excluded by design: node-id-shaped tokens (q1/h12/s3, possessives
    included) and letter-hyphen-digit compounds ('top-1'); geometry and chart data never
    reach here (script/style and addressed spans are removed before tokenizing)."""
    t = tok.strip(".,;:!?()[]{}\"'“”‘’—–·")
    t = re.sub(r"['’]s$", "", t)        # h3's -> h3
    if not t or not any(ch.isdigit() for ch in t):
        return None
    if re.fullmatch(r"[qhs]\d+", t):
        return None
    if re.fullmatch(r"[A-Za-z][A-Za-z0-9]*-\d+[A-Za-z0-9]*", t):
        return None
    return t

def _unsourced_numerals(text):
    """Digit-bearing tokens in slide TEXT nodes only — inside <section class="slide">,
    after dropping comments, script/style, and every tag carrying data-src/data-derived
    (their content is already covered by the address)."""
    out = []
    secs = _slide_sections(text)
    starts = [m.start() for m in secs]
    for sm in secs:
        slide = _slide_of(starts, sm.start())
        seg = re.sub(r"<!--.*?-->", " ", sm.group(1), flags=re.S)
        seg = re.sub(r"<(script|style)\b.*?</\1>", " ", seg, flags=re.S | re.I)
        seg = _DATA_TAG_RE.sub(" ", seg)
        seg = re.sub(r"<[^>]+>", " ", seg)
        for tok in html.unescape(seg).split():
            t = _numeral_token(tok)
            if t:
                out.append({"numeral": t, "slide": slide})
    return out

def _deck_addresses(text):
    """Every addressed datum in the deck source, in document order:
    kind 'chart' (a src: object literal with cached v/lo/hi), 'span' (data-src with cached
    inner text), or 'derived' (data-derived input list). Positions are into `text`."""
    out = []
    for m in _SRC_OBJ_RE.finditer(text):
        nums = {}
        for k, kre in _NUM_KEY_RE.items():
            km = kre.search(m.group(0))
            if km:
                nums[k] = (m.start() + km.start(1), m.start() + km.end(1), km.group(1))
        out.append({"kind": "chart", "addr": m.group(2), "pos": m.start(), "nums": nums})
    for m in _DATA_TAG_RE.finditer(text):
        inner = m.group(5)
        entry = {"kind": "span" if m.group(3) == "src" else "derived",
                 "addr": m.group(4), "pos": m.start(),
                 "inner": (m.end() - len("</" + m.group(1) + ">") - len(inner),
                           m.end() - len("</" + m.group(1) + ">"), inner)}
        out.append(entry)
    return out

def deck_verify(root, path):
    """Walk every src / data-src / data-derived in the deck file and compare its cached
    value against the vault. Returns the full findings dict; the CLI decides exit codes
    (mismatch/unresolvable always fail; unsourced fails only under --strict)."""
    text = read(path)
    rep = {"mismatch": [], "unresolvable": [], "derived": [], "literal": [], "unsourced": []}
    starts = [m.start() for m in _slide_sections(text)]

    def _resolve(addr, slide):
        try:
            return resolve_address(root, addr)
        except AddressError as e:
            rep["unresolvable"].append({"addr": addr, "slide": slide, "kind": e.kind,
                                        "msg": str(e)})
            return None

    for d in _deck_addresses(text):
        slide = _slide_of(starts, d["pos"])
        if d["addr"] == "literal":
            rep["literal"].append({"slide": slide})
            continue
        if d["kind"] == "derived":
            inputs = [a.strip() for a in d["addr"].split(",") if a.strip()]
            if all(_resolve(a, slide) is not None for a in inputs):
                rep["derived"].append({"inputs": inputs, "slide": slide})
            continue
        leaf = _resolve(d["addr"], slide)
        if leaf is None:
            continue
        if d["kind"] == "span":
            shown = re.sub(r"<[^>]+>", "", d["inner"][2]).strip()
            if not _values_match(shown, leaf.get("value")):
                rep["mismatch"].append({"addr": d["addr"], "slide": slide, "field": "text",
                                        "msg": f"{d['addr']} (slide {slide}): deck shows "
                                               f"'{shown}', vault has {leaf.get('value')!r}"})
            continue
        # chart object: v against value, lo/hi against ci
        ci = leaf.get("ci")
        wants = {"v": leaf.get("value")}
        if isinstance(ci, (list, tuple)) and len(ci) == 2:
            wants["lo"], wants["hi"] = ci[0], ci[1]
        for k, (s0, s1, got) in d["nums"].items():
            if k not in wants:
                rep["mismatch"].append({"addr": d["addr"], "slide": slide, "field": k,
                                        "msg": f"{d['addr']} (slide {slide}): deck caches "
                                               f"{k}={got} but the vault records no ci"})
            elif not _values_match(got, wants[k]):
                rep["mismatch"].append({"addr": d["addr"], "slide": slide, "field": k,
                                        "msg": f"{d['addr']} (slide {slide}): deck has "
                                               f"{k}={got}, vault has {wants[k]!r}"})
    rep["unsourced"] = _unsourced_numerals(text)
    return rep

def _format_like(old, val):
    """Render `val` in the formatting conventions of the display text it replaces:
    explicit '+', &minus; entity / unicode minus, thousands separators, trailing '%', and
    the old decimal count when it can carry the new value exactly. String-typed metrics
    values are written verbatim — their formatting IS the value."""
    if isinstance(val, str):
        return val
    raw = html.unescape(old).strip()
    neg, mag = val < 0, abs(val)
    m = re.search(r"\d[\d,]*(?:\.(\d+))?", raw)
    dec = len(m.group(1)) if m and m.group(1) else 0
    s = f"{mag:,.{dec}f}" if ("," in raw) else f"{mag:.{dec}f}"
    if float(s.replace(",", "")) != mag:        # old decimal count can't carry it exactly
        s = repr(float(mag)) if not float(mag).is_integer() else str(int(mag))
    if neg:
        s = ("&minus;" if "&minus;" in old else "−" if "−" in old else "-") + s
    elif raw.startswith("+"):
        s = "+" + s
    if raw.endswith("%"):
        s += "%"
    return s

def deck_refresh(root, path):
    """Rewrite the cached values (chart v/lo/hi numerals and data-src span text) from
    current vault state. Touches NOTHING else — prose, structure, and data-derived spans
    (whose results the engine must not compute) are left alone. Returns the change list;
    the CLI turns it into the loud per-slide warning, because a correct value refresh can
    silently falsify the sentence around a number — refresh fixes values, only a human can
    fix the prose."""
    text = read(path)
    ops, changes, unresolvable = [], [], []
    starts = [m.start() for m in _slide_sections(text)]
    for d in _deck_addresses(text):
        slide = _slide_of(starts, d["pos"])
        if d["addr"] == "literal" or d["kind"] == "derived":
            continue
        try:
            leaf = resolve_address(root, d["addr"])
        except AddressError as e:
            unresolvable.append({"addr": d["addr"], "slide": slide, "msg": str(e)})
            continue
        if d["kind"] == "chart":
            ci = leaf.get("ci")
            wants = {"v": leaf.get("value")}
            if isinstance(ci, (list, tuple)) and len(ci) == 2:
                wants["lo"], wants["hi"] = ci[0], ci[1]
            for k, (s0, s1, got) in d["nums"].items():
                if k in wants and not _values_match(got, wants[k]):
                    new = json.dumps(wants[k])
                    ops.append((s0, s1, new))
                    changes.append({"addr": d["addr"], "slide": slide, "field": k,
                                    "old": got, "new": new})
        else:
            s0, s1, inner = d["inner"]
            shown = re.sub(r"<[^>]+>", "", inner).strip()
            if "<" in inner or _values_match(shown, leaf.get("value")):
                continue        # nested markup is prose territory — verify will say if stale
            new = _format_like(shown, leaf.get("value"))
            ops.append((s0, s1, new))
            changes.append({"addr": d["addr"], "slide": slide, "field": "text",
                            "old": shown, "new": new})
    for s0, s1, new in sorted(ops, key=lambda o: -o[0]):
        text = text[:s0] + new + text[s1:]
    if changes:
        write_if_changed(path, text)
    return {"changes": changes, "slides": sorted({c["slide"] for c in changes}),
            "unresolvable": unresolvable}

# --- contract lint (spec 11 work item; PI ruling #8) -------------------------------
# Every <section class="slide"> must carry a contract-header comment (job / source /
# numbers / cut — the override surface a user's "make mine different" pushes against),
# and no slide may exceed DECK_UNITS_MAX content units, counted mechanically over the
# declared class list below. Countable, therefore lintable — the spec's own D3 rationale.
# Footer overlap and 16:9 projector fit cannot be checked without rendering: manual.
DECK_CONTRACT_KEYS = ("job", "source", "numbers", "cut")
DECK_UNITS_MAX     = 7
_DECK_UNIT_PATTERNS = (
    ("chain node", r'class="node\b'),
    ("bullet",     r"<li\b"),
    ("table",      r"<table\b"),
    ("callout",    r'class="target\b'),
    ("chart",      r'class="chartbox\b'),
    ("chip list",  r'class="chips\b'),
    ("legend",     r'class="legend\b'),
    ("note",       r'class="note\b'),
    ("prose lead", r'class="lead\b'),
    ("pipeline",   r'class="pipe\b'),
)

def deck_lint(path):
    """[(slide_no, message)] for every contract violation in the deck file. Empty = clean."""
    text = read(path)
    problems = []
    secs = _slide_sections(text)
    if not secs:
        return [(0, 'no <section class="slide"> found')]
    for i, sm in enumerate(secs, 1):
        # the header is the last comment in the gap between the previous section's end and
        # this one's start — comments inside a section's own markup never masquerade as one
        gap = text[(secs[i - 2].end() if i > 1 else 0):sm.start()]
        cm = re.findall(r"<!--(.*?)-->", gap, flags=re.S)
        if not cm:
            problems.append((i, f"slide {i}: no contract header comment before the section"))
        else:
            missing = [k for k in DECK_CONTRACT_KEYS
                       if not re.search(r"\b%s\b" % k, cm[-1].lower())]
            if missing:
                problems.append((i, f"slide {i}: contract header missing {', '.join(missing)}"))
        seg = re.sub(r"<!--.*?-->", " ", sm.group(1), flags=re.S)
        units = sum(len(re.findall(p, seg)) for _, p in _DECK_UNIT_PATTERNS)
        if units > DECK_UNITS_MAX:
            problems.append((i, f"slide {i}: {units} content units, over the "
                                f"{DECK_UNITS_MAX}-unit cap"))
    return problems

def deck_warnings(root):
    """`validate --check=decks`: verify every *.html under presentations/ and surface
    mismatch/unresolvable findings as WARNINGS — a stale derived document must never brick
    the vault lint (and under --strict, warnings already fail, which is the asked-for
    behavior)."""
    out = []
    pd = os.path.join(root, PRESENTATIONS_DIR)
    if not os.path.isdir(pd):
        return out
    for dirpath, dirnames, filenames in os.walk(pd):
        dirnames[:] = sorted(x for x in dirnames if not x.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".html"):
                continue
            rel = _rel(root, os.path.join(dirpath, fn))
            rep = deck_verify(root, os.path.join(dirpath, fn))
            for bucket in ("mismatch", "unresolvable"):
                for f in rep[bucket]:
                    out.append((f"deck:{rel}", f"deck '{rel}': {bucket} — {f['msg']}"))
    return out


# ============================================================================= autopilot (spec 05)
# PRD 05.0 — the flight plan and the brief. The PURE half of autopilot: everything here reads
# the vault (and appends the PI's own words to one file), and nothing here starts a process,
# touches git, or writes results/<hid>/metrics.json, state.json or ledger.jsonl. Those paths
# are named as constants so 05.2 cannot invent a second spelling; this slice never writes
# them.
#
# The design rule the whole section rests on: a plan is a crux DOCUMENT, so every parser it
# needs already exists. `## Verifiables` is byte-for-byte the node format and goes through
# `_verifiables` / `verifiable_scenarios` / `count_verifiables_by_kind` unchanged; the null
# goes through `null_problem`; a metric address goes through `resolve_address`, the same
# contract `deck --verify` proves against. Nothing below is a second parser.

AUTO_DIR          = "auto"                       # auto/<qid>/…
PLAN_FILE         = "plan.md"
AUTO_STATE_FILE   = "state.json"                 # written by 05.2; the path is fixed HERE so
AUTO_LEDGER_FILE  = "ledger.jsonl"               # the two slices cannot drift. Never written here.

AUTO_REQUIRED_FIELDS = ("anchor", "mode", "baseline", "island_cap", "budget_attempts",
                        "budget_hours", "budget_model_calls", "parallel_total",
                        "parallel_island", "retries", "retention", "scorer", "run",
                        "frozen", "writable", "agent", "model", "effort", "steward",
                        "steward_every",
                        "stall_attempts", "abort_invalid_runs", "replicates", "rule")
AUTO_INT_FIELDS      = ("island_cap", "budget_attempts", "budget_model_calls", "parallel_total",
                        "parallel_island", "retries", "steward_every", "stall_attempts",
                        "abort_invalid_runs")            # non-negative int
AUTO_LIST_FIELDS     = ("islands", "frozen", "writable", "agent_failover")   # comma-separated
AUTO_MODES           = ("climb", "explore")
# The worker's model and effort are the PI's to choose in the setup conversation, and the
# plan is the one place they are written: a run once spent a night on the CLI's defaults
# because nothing carried the pair the PI had asked for. The effort levels are Claude Code's.
AUTO_EFFORTS         = ("low", "medium", "high", "xhigh", "max")
AUTO_AGENT_CLAUDE    = "claude"                  # the argv[0] basename the two fields bind
# D2: Climb IS c_puct = 0. There is no separate greedy code path to drift away from the
# explore one — the two modes are one formula at two settings of one constant.
AUTO_C_PUCT          = {"climb": 0.0, "explore": 1.0}
OBJECTIVE_DIRECTIONS = ("min", "max")
AUTO_SECTIONS        = ("Goal", "Objective", "Null", "Verifiables", "Guidance")

# 05.1. What a workspace is worth keeping once the attempt is over, and how long the PI's
# scorer may run before the driver gives up on it. Both are READ by the driver, never acted on
# here: the engine only says which values are legal, which is a question about the document.
AUTO_RETENTIONS             = ("all", "failed", "none")
AUTO_SCORER_TIMEOUT_DEFAULT = 600.0
# Optional, and optional forever — a plan written before 05.1 is still a valid plan. `repo` is
# deliberately NOT checked below: whether a path is a working tree is a question only a
# process can answer, so the driver reports that one under its own slug.
AUTO_OPTIONAL_FIELDS        = ("repo", "scorer_timeout")

# 05.2. The vocabulary the driver writes, and the arithmetic it is allowed to do — all of it
# HERE, so the impure half cannot invent a second spelling of a phase, an event or a stop.
# The engine still never writes state.json or ledger.jsonl; it only says what may go in them.
AUTO_PHASES            = ("reserved", "drafted", "committed", "scored", "closed")
AUTO_LEDGER_EVENTS     = ("run-opened", "attempt-reserved", "worker-started", "worker-done",
                          "worker-failed", "node-filed", "scored", "violation", "retry",
                          "closed", "confirm", "island-best", "stall", "escalated",
                          "abandoned", "resumed", "stop",
                          "failover", "cooldown", "closer", "steward")
AUTO_STOP_REASONS      = ("success", "budget", "abort", "stall")
AUTO_BUDGET_AXES       = ("attempts", "hours", "model_calls")
# The whole grammar by which a machine may grade a check. `≤ ≥ ≠` are spellings, not extra
# operators: the PI's prose and the 05.0 fixtures already use them, and a plan that reads
# well to a human must not be refused for the shape of one glyph.
AUTO_COMPARISON_OPS    = ("<=", "<", ">=", ">", "==", "!=")
AUTO_OP_ALIASES        = {"≤": "<=", "≥": ">=", "≠": "!="}


def auto_direction_op(direction):
    """The comparison operator a plan's objective `direction` implies: max -> `>=`, min -> `<=`.

    It exists because the rule was previously spelled twice and got out of step: 05.2 reverted
    a hard-coded `<=`, and `auto_crosses` already says `value >= bar if direction == "max" else
    value <= bar` for the VALUE. This is the same rule for the CHECK TEXT, so a plan whose
    discriminating check points the other way from its own objective can be refused before the
    compute is spent. Pure and total; anything but min/max is a CruxError."""
    if direction == "max":
        return ">="
    if direction == "min":
        return "<="
    raise CruxError(f"objective direction must be one of {', '.join(OBJECTIVE_DIRECTIONS)} "
                    f"(got '{direction}')")


# What the approval hash does NOT cover: the stamp itself, and the `updated:` clock. The
# `## Guidance` region is excluded inside `flight_plan_hash` for the same reason — the PI is
# meant to keep talking to the workers mid-run, and having that clear the signature would
# make the feature useless.
AUTO_APPROVAL_UNHASHED = ("approved", "approved_hash", "updated")
AUTO_PROPOSAL_KEYS     = ("claim", "controls")
AUTO_CONTROL_KEYS      = ("fails_if", "text")
AUTO_WORKER_RETRY_REASONS = ("worker-start", "worker-exit", "no-commit", "proposal-missing",
                             "proposal-unparseable", "claim-missing", "claim-over-cap")
AUTO_SCORER_RETRY_CHECKS  = ("scorer-exit", "scorer-timeout", "scorer-output")
AUTO_VIOLATION_KINDS   = ("frozen", "manifest")
AUTO_TASK_CATEGORY     = "autopilot"
AUTO_TITLE_WORDS       = 15
AUTO_NO_CLAIM          = "Autopilot attempt {hid} left no usable claim ({reason})."
AUTO_STATE_KEYS        = ("run", "anchor", "plan", "plan_hash", "opened", "updated", "driver",
                          "mode", "c_puct", "escalated", "steward_requested", "base",
                          "islands", "best", "budget", "in_flight", "closed",
                          "consecutive_invalid", "stalls", "confirmed", "stop", "tasks",
                          "events", "next_island",
                          "agents", "steward")

# 05.3. The agents. One ordered COMMAND LIST that a try walks once, a cooldown for a command
# that hit a provider limit, a probe that costs nothing, the closer's proposal schema and the
# steward's. All of it here, so the impure half cannot invent a second spelling.
# ---- the command list, the walk, the probe
AUTO_AGENTS                = ("crux-auto-worker", "crux-close", "crux-auto-steward")
AUTO_COOLDOWN_DEFAULT      = 1800.0        # seconds; plan field `agent_cooldown:`
AUTO_PROBE_DEFAULT         = "--version"   # plan field `agent_probe:`
AUTO_PROBE_TIMEOUT_DEFAULT = 20.0          # seconds; plan field `agent_probe_timeout:`
# Ported from the era skill's scaffold/generate.py LIMIT_PATTERNS (MIT — that file carries no
# licence header and is part of the PI's own MIT-licensed `era` skill; Apache-2.0 and FROZEN
# belong to futs.py alone, which is a different file). Read case-insensitively.
#
# A LIMIT AND AN OUTAGE ARE ONE FAMILY for every purpose the driver has: both are the provider
# failing rather than the worker acting, both are waited out rather than retried harder, and
# neither may be read as a bad attempt. The second row was added after a run died on
# `abort_invalid_runs` with 25 attempts of budget left — five workers killed by a session limit
# and a run of 529s, every one of them counted as a worker behaving badly.
AUTO_RATE_LIMIT_PATTERNS   = (r"5-?hour limit", r"usage limit", r"rate limit",
                              r"limit reached", r"too many requests", r"reset[s]? at",
                              r"please try again later",
                              r"overloaded", r"service unavailable",
                              r"internal server error", r"\b529\b", r"api_error",
                              # The CLI's OWN session limit — the commonest provider failure
                              # on a workstation, and the one shape no row above caught:
                              # "You've hit your session limit · resets 9:10pm". It killed the
                              # first run of a search and then the fourth, and because this
                              # same predicate also drives the cooldown there was no wait
                              # either: four attempts burned in thirteen seconds, retrying
                              # into a wall with hours left on it. Matched as a FAMILY, since
                              # the wording moves with the surface and the plan — but never on
                              # the bare word "limit", because a program is entitled to print
                              # that about its own iteration cap.
                              r"hit your [^\n]{0,40}limit", r"session limit",
                              r"reset[s]? (?:at\s+)?\d{1,2}(?::\d{2})?\s*[ap]\.?m\.?",
                              r"reset[s]? (?:at\s+)?\d{1,2}:\d{2}")
# ---- the closer
AUTO_CLOSE_KEYS            = ("ticks", "findings", "report")
AUTO_TICK_ALPHABET         = ("x", " ", "-")
AUTO_REPORT_FILE           = "report.md"           # results/<hid>/report.md
AUTO_REPORT_BYTES          = 20000                 # a report is a file, not a node section
# The closer's findings paragraph goes into the NODE, and `prose_words` sums every one of a
# node's prose sections against ONE whole-node budget of PROSE_CAP — while `auto_proposal`
# separately allows a claim of up to PROSE_CAP on its own. A findings cap of PROSE_CAP would
# therefore let a legal 400-word claim plus a legal 400-word findings put 800 words in a
# 400-word node, so every closed attempt of the run would carry an over-cap advisory: the
# self-manufactured backlog the report link exists to close. 80 is the number
# AUTO_BRIEF_BUDGET already uses for findings, so no new number is invented.
AUTO_CLOSE_FINDINGS_WORDS  = 80
# ---- the steward
AUTO_STEWARD_KEYS          = ("guidance", "island")
AUTO_ISLAND_KEYS           = ("title", "problem")
AUTO_STEWARD_SLOTS         = ("goal", "objective.address", "objective.direction",
                              "objective.bar", "anchor.id", "anchor.title", "islands",
                              "budget", "island_cap")
AUTO_NO_STEWARD            = "No steward guidance yet."

# 05.4. The cockpit's own read of a run. Everything a reader needs, derived from the run's own
# directory and nothing else — the tree snapshot is not consulted, because a run rewrites
# state.json after every event and a reader that touched the tree would rebuild it per poll.
AUTO_LIVE_SECONDS   = 120.0      # no driver write within this window => `stale`, never `running`
AUTO_EVENTS_TAIL    = 200        # ledger events carried by default, newest-first
AUTO_EVENTS_MAX     = 2000       # the ceiling `?events=` may ask for
AUTO_LIVENESS       = ("running", "stale", "stopped")
AUTO_PORTFOLIO_K    = 5
AUTO_PORTFOLIO_RULE = ("Ranked by the objective, then taken greedily — a candidate in the same "
                       "lineage as one already taken is skipped.")
AUTO_COCKPIT_RUN_KEYS = ("anchor", "run", "plan", "mode", "opened", "updated", "liveness",
                         "objective", "stop", "budget", "islands", "best", "in_flight",
                         "agents", "steward", "attempts", "portfolio", "events", "event_count")
AUTO_COCKPIT_ATTEMPT_KEYS = ("id", "attempt_no", "island", "parent", "builds_on", "title",
                             "score", "seed", "verdict", "phase", "at")

OBJECTIVE_LINE_RE = re.compile(r"^\s*(address|direction|bar)::\s*(.+?)\s*$")
GUIDANCE_RE       = re.compile(r"^- \[(?P<at>[^\]]+)\] (?P<author>[^:]+): (?P<text>.+)$")

BUILDS_ON_FIELD = "builds_on"


def flight_plan_path(root, qid):
    """auto/<qid>/plan.md, absolute. One spelling of the convention, so a verb, a test and
    05.2's loop cannot disagree about where a plan lives."""
    return os.path.join(root, AUTO_DIR, qid, PLAN_FILE)


def auto_qid_arg(value):
    """The anchor out of whatever the PI typed: a qid, or the plan path the other verbs take.

    `status` and `refs` are keyed by anchor while `check`, `approve`, `run` and `guide` are
    keyed by `auto/<qid>/plan.md`, and nothing on the command line says which is which. A PI
    who has just typed the plan path five times types it a sixth, and `auto status
    auto/q1/plan.md` then went looking for a run on an anchor literally named
    `auto/q1/plan.md` — reported as a mangled path, with nothing to say the ARGUMENT was the
    fault. One verb set, one argument: a path ending in the plan file yields the directory it
    sits in, and anything else is already a qid and is returned untouched."""
    if value is None:
        return None
    s = str(value).replace(os.sep, "/").rstrip("/")
    head, _, tail = s.rpartition("/")
    if tail == PLAN_FILE and head:
        return head.rpartition("/")[2] or value
    return value


def _auto_text(text):
    """A plan section as content: HTML comments stripped, whitespace trimmed."""
    return re.sub(r"<!--.*?-->", "", text or "", flags=re.S).strip()


def node_builds_on(n):
    """The attempt this one was branched from, or None."""
    return _fm_text(n, BUILDS_ON_FIELD)


def builds_on_problem(v, n):
    """The `validate` message for a hypothesis' `builds_on:`, or None. Exactly one problem
    per node: the four ways the field can lie are checked in order and the first wins, because
    a node whose target does not exist has nothing left to say about cycles."""
    target = node_builds_on(n)
    if not target:
        return None
    b = v.nodes.get(target)
    if b is None:
        return f"hypothesis '{n.id}': {BUILDS_ON_FIELD} '{target}' does not exist"
    if b.type != "idea":
        return (f"hypothesis '{n.id}': {BUILDS_ON_FIELD} '{target}' is a '{b.type}', not a "
                f"hypothesis")
    if b.parent != n.parent:
        return (f"hypothesis '{n.id}': {BUILDS_ON_FIELD} '{target}' sits under '{b.parent}', "
                f"not under '{n.parent}'")
    # the walk, until an id repeats. Reported only on the nodes that are ON the cycle: a node
    # that merely POINTS INTO one is not itself lying about its own lineage.
    path, seen, cur = [n.id], {n.id}, target
    while True:
        path.append(cur)
        if cur in seen:
            return (f"hypothesis '{n.id}': {BUILDS_ON_FIELD} cycle: " + " -> ".join(path)) \
                   if cur == n.id else None
        seen.add(cur)
        nxt = v.nodes.get(cur)
        if nxt is None or nxt.type != "idea":
            return None
        cur = node_builds_on(nxt)
        if not cur:
            return None


# ----------------------------------------------------------------------------- the flight plan
def parse_flight_plan(text):
    """The plan document as data. TOTAL — garbage in, a dict out, never an exception: this is
    what `auto check` calls on a file a human just hand-edited, and a traceback there tells
    nobody which line was wrong."""
    try:
        fm, body = parse_doc(text or "")
    except Exception:
        fm, body = {}, (text or "")
    heads = [l.rstrip() for l in body.splitlines() if l.startswith("## ")]
    names = {h[3:].strip().lower() for h in heads}

    objective = None
    if "objective" in names:
        objective = {"address": None, "direction": None, "bar": None}
        for line in _section(body, "Objective").splitlines():
            m = OBJECTIVE_LINE_RE.match(line)
            if m:
                objective[m.group(1)] = m.group(2).strip()

    guidance, guidance_bad = [], []
    if "guidance" in names:
        ordinal = 0
        for line in re.sub(r"<!--.*?-->", "", _section(body, "Guidance"), flags=re.S).splitlines():
            if not line.strip() or _PLACEHOLDER.match(line):
                continue
            ordinal += 1
            m = GUIDANCE_RE.match(line.rstrip())
            if m:
                guidance.append({"at": m.group("at"), "author": m.group("author").strip(),
                                 "text": m.group("text").strip()})
            else:
                guidance_bad.append(ordinal)

    return {"fm": fm, "body": body, "sections": heads,
            "goal": _auto_text(_section(body, "Goal")),
            "objective": objective,
            "null": _auto_text(_section(body, "Null")) or None,
            "verifiables": _verifiables(body),
            "scenarios": verifiable_scenarios(body),
            "guidance": guidance, "guidance_bad": guidance_bad}


def _auto_subtree(v, qid):
    """Every node id at or under `qid`, cycle-guarded, deterministic order."""
    out, stack, seen = [], [qid], set()
    while stack:
        cur = stack.pop(0)
        if cur in seen or cur not in v.nodes:
            continue
        seen.add(cur)
        out.append(cur)
        stack += list(v.children.get(cur, ()))
    return out


def _auto_norm_path(p):
    """A frozen/writable entry as one comparable path: normalised, trailing slash gone."""
    s = os.path.normpath(str(p).strip().replace("\\", "/")).replace(os.sep, "/")
    return s.rstrip("/") or s


def auto_check_comparison(text):
    """`{key, op, number, rest}` when a verifiable BEGINS with a metric comparison, else None.

    Pure and total, and deliberately the smallest rule that can turn a number into a tick: the
    check's own text carries the address, the operator and the threshold, so `_verifiables`,
    `verifiable_scenarios` and the hash lock are all unchanged and no node written before this
    release reads differently. Everything after the number is free prose.

    None is not a failure here — it is "this line is not a comparison", which the plan lint
    refuses before a run and the tick vector reads as `[-]`."""
    _kind, t = verifiable_kind(str(text or ""))
    t = _FOUND_RE.sub("", t).strip()
    parts = t.split(None, 3)
    if len(parts) < 3:
        return None
    key, op, num = parts[0], parts[1], parts[2]
    rest = parts[3] if len(parts) == 4 else ""
    op = AUTO_OP_ALIASES.get(op, op)
    if op not in AUTO_COMPARISON_OPS:
        return None
    # 05.0's objective-address grammar, plus the operator glyphs: a key that could be read as
    # `obj.value<=1` is refused rather than guessed at.
    if re.search(r"[#/\\\s<>=!≤≥≠]", key) or any(c == "" for c in key.split(".")):
        return None
    try:
        value = float(num)
    except ValueError:
        return None
    if not math.isfinite(value):
        return None
    return {"key": key, "op": op, "number": value, "rest": rest}


def flight_plan_problems(root, plan, path=None):
    """[{check, message}] — EVERY way this plan is wrong, in one pass, in a fixed order.

    All of them, not the first: a plan is the document a PI signs before a run of 140
    attempts, and handing back one problem at a time turns one review into six. Checks that
    depend on an earlier value are SKIPPED when that value is missing or already reported, so
    one mistake is reported once rather than cascading into four."""
    out = []
    def add(slug, msg):
        out.append({"check": slug, "message": msg})

    fm = plan.get("fm") or {}
    body = plan.get("body") or ""
    def present(name):
        val = fm.get(name)
        return not (val is None or val == "")

    # 1. the required fields, in the declared order
    for name in AUTO_REQUIRED_FIELDS:
        if not present(name):
            add("field", f"flight plan missing required field: {name}")

    # 2. field types
    ints_ok = {}
    for name in AUTO_INT_FIELDS:
        if not present(name):
            continue
        raw = fm.get(name)
        if isinstance(raw, bool) or not isinstance(raw, int) or raw < 0:
            add("field-type", f"flight plan field '{name}' must be a non-negative integer "
                              f"(got '{raw}')")
        else:
            ints_ok[name] = raw
    if present("budget_hours"):
        raw = fm.get("budget_hours")
        try:
            if float(raw) < 0:
                raise ValueError
        except (TypeError, ValueError):
            add("field-type", f"flight plan field 'budget_hours' must be a non-negative "
                              f"number (got '{raw}')")
    if present("steward") and not isinstance(fm.get("steward"), bool):
        add("field-type", f"flight plan field 'steward' must be true or false "
                          f"(got '{fm.get('steward')}')")
    # 2d (05.1). Optional — absent or empty means the default. Zero is refused with the rest:
    # a scorer that must finish in no time is a run that fails at the first attempt.
    if present("scorer_timeout"):
        raw = fm.get("scorer_timeout")
        try:
            if float(raw) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            add("field-type", f"flight plan field 'scorer_timeout' must be a positive number "
                              f"(got '{raw}')")
    # 2e (05.2). `replicates:` is prose everywhere else in crux ("3 seeds x 2 folds"), and the
    # confirmation run needs an actual count of seeds out of it. The first integer in the
    # string is that count, and a plan that carries none cannot declare success at all — so it
    # is refused where the plan is signed rather than at the end of a night.
    if present("replicates"):
        raw = fm.get("replicates")
        m = re.search(r"-?\d+", str(raw))
        if m is None or int(m.group(0)) < 1:
            add("field-type", f"flight plan field 'replicates' must name a whole number of "
                              f"seeds, 1 or more (got '{raw}')")
    # 2f (05.2). Zero passes the non-negative test above and then means "start no attempt and
    # never start one" — a run that cannot begin, discovered only when the driver trips its own
    # guard. One attempt at a time is the floor for both.
    for name in ("parallel_total", "parallel_island"):
        if name in ints_ok and ints_ok[name] < 1:
            add("field-type", f"flight plan field '{name}' must be a whole number of attempts, "
                              f"1 or more (got '{fm.get(name)}')")
    # 2g (05.3). The three new optional fields. `agent_probe` needs no check of its own: any
    # string is a legal probe argument list, and one that does not parse is caught by 2h's
    # sibling logic where the probe argv is built.
    if present("closer") and not isinstance(fm.get("closer"), bool):
        add("field-type", f"flight plan field 'closer' must be true or false "
                          f"(got '{fm.get('closer')}')")
    if present("agent_cooldown"):
        raw = fm.get("agent_cooldown")
        try:
            if float(raw) < 0:
                raise ValueError
        except (TypeError, ValueError):
            add("field-type", f"flight plan field 'agent_cooldown' must be a non-negative "
                              f"number of seconds (got '{raw}')")
    if present("agent_probe_timeout"):
        raw = fm.get("agent_probe_timeout")
        try:
            if float(raw) <= 0:
                raise ValueError
        except (TypeError, ValueError):
            add("field-type", f"flight plan field 'agent_probe_timeout' must be a positive "
                              f"number of seconds (got '{raw}')")
    # 2h (05.3). Every command of the list has to be argv a process can be started from. A
    # misspelling here is a whole night lost, and it costs nothing to refuse it where the plan
    # is signed — `auto check --static` starts nothing and still catches it.
    for n, c in enumerate([fm.get("agent")] + _csv_field(fm.get("agent_failover")), 1):
        # A blank `agent:` reads as None out of the frontmatter, and "the plan names no agent
        # command" is exactly what 2h is for — so it is reported here as well as by check 1,
        # because the two say different things: one that the field is absent, one that the
        # list has no first command.
        try:
            argv = shlex.split(str(c or ""))
        except ValueError as e:
            add("agent-command", f"flight plan agent command {n} does not parse under "
                                 f"shlex: {c} ({e})")
            continue
        if not argv:
            add("agent-command", f"flight plan agent command {n} is empty")
            continue
        # 2i. A claude command takes its model and effort from the plan's two fields and from
        # nowhere else, so a pair written into the command itself is refused: it would win
        # over the fields silently, or be passed twice.
        if os.path.basename(argv[0]) == AUTO_AGENT_CLAUDE:
            for flag, ph in (("--model", "{model}"), ("--effort", "{effort}")):
                for i, x in enumerate(argv):
                    val = (x[len(flag) + 1:] if x.startswith(flag + "=")
                           else argv[i + 1] if x == flag and i + 1 < len(argv) else None)
                    if val is not None and val != ph:
                        add("agent-command", f"flight plan agent command {n} sets {flag} "
                                             f"itself ('{val}'): set the plan's "
                                             f"'{flag[2:]}' field instead, and write "
                                             f"{flag} {ph} or nothing at all")
                        break

    # 2j. the worker's model and effort
    if present("effort") and fm.get("effort") not in AUTO_EFFORTS:
        add("field-type", f"flight plan field 'effort' must be one of "
                          f"{', '.join(AUTO_EFFORTS)} (got '{fm.get('effort')}')")
    if present("model") and (not isinstance(fm.get("model"), str)
                             or len(str(fm.get("model")).split()) != 1):
        add("field-type", f"flight plan field 'model' must be one model name with no spaces "
                          f"(got '{fm.get('model')}')")

    # 3. the mode
    mode = fm.get("mode")
    if present("mode") and mode not in AUTO_MODES:
        add("mode", f"flight plan mode must be one of {', '.join(AUTO_MODES)} (got '{mode}')")

    # 3b (05.1). Retention decides what happens to a workspace that may hold sixty gigabytes
    # of checkpoints, so a misspelling has to be refused where the plan is signed.
    retention = fm.get("retention")
    if present("retention") and retention not in AUTO_RETENTIONS:
        add("retention", f"flight plan retention must be one of {', '.join(AUTO_RETENTIONS)} "
                         f"(got '{retention}')")

    # 4. the combination rule — the same closed list spec 15 already honors
    rule = fm.get("rule")
    rule_ok = False
    if present("rule"):
        if rule in RESERVED_RULES:
            add("rule", f"flight plan rule '{rule}' is reserved, not implemented — see "
                        f"spec 15. Use one of {', '.join(COMBINATION_RULES)}.")
        elif rule not in COMBINATION_RULES:
            add("rule", f"flight plan rule '{rule}' is not a combination rule. Use one of "
                        f"{', '.join(COMBINATION_RULES)}.")
        else:
            rule_ok = True
    if rule_ok and rule == "m-of-n":
        n_claims = sum(count_verifiables_by_kind(body)[DEFAULT_KIND])
        m = fm.get(RULE_M_FIELD)
        # No `max(n_claims, 1)` floor: with zero claim-directed checks the range 1..0 is empty
        # and NOTHING is a valid rule_m — which is the honest answer, and the message already
        # says 1..0. The floor made the message and the test disagree.
        if not isinstance(m, int) or isinstance(m, bool) or not (1 <= m <= n_claims):
            add("rule", f"flight plan rule 'm-of-n' needs rule_m set to an integer in "
                        f"1..{n_claims} (got {m!r})")

    v = None
    try:
        v = Vault(root)
    except Exception:
        v = None

    # 5. the anchor
    anchor = fm.get("anchor") if present("anchor") else None
    anchor_ok = False
    subtree = set()
    if anchor is not None and v is not None:
        a = v.nodes.get(anchor)
        if a is None:
            add("anchor", f"flight plan anchor '{anchor}' does not exist")
        elif a.type != "question":
            add("anchor", f"flight plan anchor '{anchor}' is a '{a.type}', not a question")
        else:
            anchor_ok = True
            subtree = set(_auto_subtree(v, anchor))
    if anchor_ok and path:
        rel = path if not os.path.isabs(path) else _rel(root, path)
        rel = str(rel).replace(os.sep, "/")
        m = re.fullmatch(re.escape(AUTO_DIR) + r"/([^/]+)/" + re.escape(PLAN_FILE), rel)
        if m and m.group(1) != anchor:
            add("anchor", f"flight plan at {rel} declares anchor '{anchor}'; the directory "
                          f"and the anchor must agree")

    # 6. the islands — sub-questions of the anchor the run may work in parallel
    islands = _csv_field(fm.get("islands"))
    if anchor_ok:
        for q in islands:
            nd = v.nodes.get(q)
            if nd is None:
                add("islands", f"flight plan island '{q}' does not exist")
            elif nd.type != "question":
                add("islands", f"flight plan island '{q}' is a '{nd.type}', not a question")
            elif q not in subtree:
                add("islands", f"flight plan island '{q}' is not under the anchor '{anchor}'")
    if "island_cap" in ints_ok and len(islands) > ints_ok["island_cap"]:
        add("islands", f"flight plan names {len(islands)} islands, over island_cap "
                       f"{ints_ok['island_cap']}")

    # 7. the baseline — the attempt every later score is read against
    baseline = fm.get("baseline") if present("baseline") else None
    baseline_ok = False
    if baseline is not None and v is not None:
        nd = v.nodes.get(baseline)
        if nd is None:
            add("baseline", f"flight plan baseline '{baseline}' does not exist")
        elif nd.type != "idea":
            add("baseline", f"flight plan baseline '{baseline}' is a '{nd.type}', not a "
                            f"hypothesis")
        elif anchor_ok and baseline not in subtree:
            add("baseline", f"flight plan baseline '{baseline}' is not under the anchor "
                            f"'{anchor}'")
        elif load_metrics(root, baseline) is None:
            add("baseline", f"flight plan baseline '{baseline}' has no "
                            f"{RESULTS_DIR}/{baseline}/{METRICS_FILE}")
        else:
            baseline_ok = True

    # 8. the sections
    present_secs = {h[3:].strip().lower() for h in plan.get("sections", [])}
    sec_ok = {}
    for name in ("Goal", "Objective", "Null", "Verifiables"):
        filled = name.lower() in present_secs and bool(_prose_tokens(_section(body, name)))
        sec_ok[name] = filled
        if not filled:
            add("section", f"flight plan section '{name}' is missing or empty")
    sec_ok["Guidance"] = "guidance" in present_secs
    if not sec_ok["Guidance"]:
        add("section", "flight plan section 'Guidance' is missing")

    # 9. the null, through the gate spec 09 already owns
    if sec_ok["Null"]:
        g = null_problem(plan.get("null"), SCHEMA_GENERATION)
        if g:
            add("null", f"flight plan null: {g}")

    # 10. the objective
    objective = plan.get("objective") or {}
    address = direction = None
    bar_ok = False
    if sec_ok["Objective"]:
        for key in ("address", "direction", "bar"):
            if not str(objective.get(key) or "").strip():
                add("objective", f"flight plan objective is missing '{key}::'")
        direction = objective.get("direction")
        if direction is not None and direction not in OBJECTIVE_DIRECTIONS:
            add("objective", f"flight plan objective direction must be min or max "
                             f"(got '{direction}')")
            direction = None
        bar = objective.get("bar")
        if bar is not None:
            try:
                float(bar)
                bar_ok = True
            except (TypeError, ValueError):
                add("objective", f"flight plan objective bar must be a number (got '{bar}')")
        raw_addr = objective.get("address")
        if raw_addr is not None:
            if (not raw_addr.strip() or "#" in raw_addr or "/" in raw_addr
                    or re.search(r"\s", raw_addr)):
                add("objective", f"flight plan objective address must be a dotted key path "
                                 f"into {METRICS_FILE} (got '{raw_addr}')")
            else:
                address = raw_addr.strip()

    # 11. and that address has to RESOLVE — the `deck --verify` contract, reused
    if address and baseline_ok:
        try:
            # Resolving is not enough: the objective is compared and ranked, so a string at
            # that key passes `auto check` and then kills selection at the first attempt.
            leaf = resolve_address(root, f"{baseline}#{address}")
            try:
                float(leaf["value"])
            except (TypeError, ValueError):
                raise CruxError(f"value '{leaf['value']}' is not a number")
        except CruxError as e:
            add("objective-address", f"flight plan objective '{address}' does not resolve in "
                                     f"{RESULTS_DIR}/{baseline}/{METRICS_FILE}: {e}")

    # 12-14. the checks. The controls gate the run; the discriminating one carries the claim.
    if sec_ok["Verifiables"]:
        if count_verifiables_by_kind(body)[NEUTRAL_KIND] == (0, 0, 0):
            add("control", "flight plan verifiables carry no outcome-neutral control")
        gaps = [str(i + 1) for i, s in enumerate(plan.get("scenarios") or [])
                if not (s.get("fails_if") or "").strip()]
        if gaps:
            add("scenario", f"flight plan verifiable(s) {', '.join(gaps)} have no failure "
                            f"scenario")
        # 13b (05.2, amended 05.3). Without a closer the driver has no model, so every check
        # it inherits has to be one it can evaluate from a metrics document — a prose check
        # would make `supported` unreachable for the whole run, a fact worth learning before
        # the compute is spent. With `closer: true` the prose checks are `crux-close`'s to
        # propose, so the grammar no longer has to hold.
        if not bool(fm.get("closer")):
            for i, item in enumerate(plan.get("verifiables") or [], 1):
                if auto_check_comparison(item.get("text")) is None:
                    add("check-grammar",
                        f"flight plan verifiable {i} is not a metric comparison: it must begin "
                        f"'<key.path> <op> <number>' with <op> one of "
                        f"{', '.join(AUTO_COMPARISON_OPS)} (got '{item.get('text')}')")
        if address:
            tok = re.compile(r"(?<![\w.])" + re.escape(address) + r"(?![\w.])")
            named = any(item["kind"] == DEFAULT_KIND and s.get("discriminates")
                        and tok.search(item["text"] or "")
                        for item, s in zip(plan.get("verifiables") or [],
                                           plan.get("scenarios") or []))
            if not named:
                add("discriminates", f"flight plan objective '{address}' does not correspond "
                                     f"to a discriminating check: no verifiable marked "
                                     f"discriminates:: true names it")
            # 14b (05.5). The discriminating check must point the same way as the objective:
            # `direction: max` with a check reading `<=` searches against its own bar, which
            # is what 05.2 reverted a hard-coded operator for. It is the SAME selection as
            # above — only the discriminating check that names the address is constrained. A
            # control may point either way on purpose: the tier-zero plan's own control reads
            # `obj.score <= 0` under `direction: max` and is correct. Skipped when the
            # direction is missing or already reported, and when the text is not a comparison
            # at all — that line already has `check-grammar`, and one mistake is reported once.
            if direction is not None:
                want = auto_direction_op(direction)
                for item, s in zip(plan.get("verifiables") or [],
                                   plan.get("scenarios") or []):
                    if not (item["kind"] == DEFAULT_KIND and s.get("discriminates")
                            and tok.search(item["text"] or "")):
                        continue
                    cmp_ = auto_check_comparison(item["text"])
                    if cmp_ is None or cmp_["op"] == want:
                        continue
                    add("objective-op",
                        f"flight plan objective direction '{direction}' wants '{want}' on the "
                        f"discriminating check, got '{cmp_['op']}' ('{item['text']}')")

    # 15. frozen vs writable. A frozen path a worker may also write is not frozen.
    if present("frozen") and present("writable"):
        for f in _csv_field(fm.get("frozen")):
            nf = _auto_norm_path(f)
            for w in _csv_field(fm.get("writable")):
                nw = _auto_norm_path(w)
                if nf == nw or nf.startswith(nw + "/") or nw.startswith(nf + "/"):
                    add("paths", f"flight plan frozen path '{nf}' overlaps writable root "
                                 f"'{nw}'")

    # 16. guidance is a log, and an unstamped line is not an entry
    for ordinal in plan.get("guidance_bad") or []:
        add("guidance", f"flight plan guidance entry {ordinal} is not stamped (expected "
                        f"'- [<timestamp>] <author>: <text>')")
    return out


def auto_check(root, path):
    """`{ok, plan, anchor, mode, problems}` for one flight plan. PURE READ: it does not
    re-stamp .crux.yaml, does not refresh, and starts no process."""
    p = path if os.path.isabs(path) else os.path.join(root, path)
    rel = _rel(root, p)
    if not os.path.isfile(p):
        raise CruxError(f"no flight plan at {rel}")
    plan = parse_flight_plan(read(p))
    problems = flight_plan_problems(root, plan, rel)
    fm = plan.get("fm") or {}
    return {"ok": not problems, "plan": rel,
            "anchor": fm.get("anchor") or None,
            "mode": fm.get("mode") or None,
            "problems": problems}


def load_flight_plan(root, path):
    """The plan, parsed and REFUSED on the first problem — for every caller that is about to
    act on it rather than report on it. `auto_check` is the one that reports."""
    p = path if os.path.isabs(path) else os.path.join(root, path)
    rel = _rel(root, p)
    if not os.path.isfile(p):
        raise CruxError(f"no flight plan at {rel}")
    plan = parse_flight_plan(read(p))
    problems = flight_plan_problems(root, plan, rel)
    if problems:
        raise CruxError(problems[0]["message"])
    fm = plan.get("fm") or {}
    obj = plan.get("objective") or {}
    islands = _csv_field(fm.get("islands")) or [fm.get("anchor")]
    plan = dict(plan)
    raw_repo = fm.get("repo")
    raw_timeout = fm.get("scorer_timeout")
    plan.update({"path": rel, "anchor": fm.get("anchor"), "mode": fm.get("mode"),
                 "c_puct": AUTO_C_PUCT[fm.get("mode")], "baseline": fm.get("baseline"),
                 "islands": islands, "direction": obj.get("direction"),
                 "address": obj.get("address"), "bar": float(obj.get("bar")),
                 "rule": fm.get("rule"),
                 "rule_m": fm.get(RULE_M_FIELD) if isinstance(fm.get(RULE_M_FIELD), int)
                           and not isinstance(fm.get(RULE_M_FIELD), bool) else None,
                 # 05.1, for the driver. Normalised HERE so the driver, the manifest and the
                 # frozen diff cannot each spell `work/` a different way.
                 "repo": str(raw_repo) if raw_repo not in (None, "") else None,
                 "scorer_timeout": (float(raw_timeout) if raw_timeout not in (None, "")
                                    else AUTO_SCORER_TIMEOUT_DEFAULT),
                 "scorer": fm.get("scorer"),
                 "retention": fm.get("retention"),
                 "frozen": [_auto_norm_path(x) for x in _csv_field(fm.get("frozen"))],
                 "writable": [_auto_norm_path(x) for x in _csv_field(fm.get("writable"))]})
    # 05.2, for the driver. Every one of these passed `flight_plan_problems` above, so the
    # coercions below cannot fail: the ints are non-negative ints, `steward` is a bool,
    # `replicates` holds an integer of 1 or more, and every check is a comparison.
    plan.update({"replicates": int(re.search(r"-?\d+", str(fm.get("replicates"))).group(0)),
                 "steward": bool(fm.get("steward")),
                 "agent": fm.get("agent"), "run": fm.get("run"),
                 "model": str(fm.get("model")), "effort": str(fm.get("effort")),
                 "budget_attempts": int(fm.get("budget_attempts")),
                 "budget_hours": float(fm.get("budget_hours")),
                 "budget_model_calls": int(fm.get("budget_model_calls")),
                 "parallel_total": int(fm.get("parallel_total")),
                 "parallel_island": int(fm.get("parallel_island")),
                 "retries": int(fm.get("retries")),
                 "stall_attempts": int(fm.get("stall_attempts")),
                 "abort_invalid_runs": int(fm.get("abort_invalid_runs"))})
    # 05.3, for the driver. `agent_failover` splits with the same `_csv_field` that splits
    # `islands`/`frozen`/`writable`; the three new optional fields fall back to their
    # defaults. `steward_every` and `island_cap` are already required and int-checked, but
    # being in AUTO_REQUIRED_FIELDS is not the same as reaching the driver — the steward needs
    # both, so they are coerced here like every other field the loop reads.
    plan.update({"agent_failover": [str(x) for x in _csv_field(fm.get("agent_failover"))],
                 "closer": bool(fm.get("closer")),
                 "agent_cooldown": (float(fm["agent_cooldown"])
                                    if fm.get("agent_cooldown") not in (None, "")
                                    else AUTO_COOLDOWN_DEFAULT),
                 "agent_probe": (str(fm["agent_probe"])
                                 if fm.get("agent_probe") not in (None, "")
                                 else AUTO_PROBE_DEFAULT),
                 "agent_probe_timeout": (float(fm["agent_probe_timeout"])
                                         if fm.get("agent_probe_timeout") not in (None, "")
                                         else AUTO_PROBE_TIMEOUT_DEFAULT),
                 "steward_every": int(fm.get("steward_every")),
                 "island_cap": int(fm.get("island_cap"))})
    checks = []
    for i, (item, s) in enumerate(zip(plan.get("verifiables") or [],
                                      plan.get("scenarios") or []), 1):
        c = auto_check_comparison(item["text"]) or {}
        checks.append({"index": i, "kind": item["kind"], "text": item["text"],
                       "fails_if": s.get("fails_if"),
                       "discriminates": bool(s.get("discriminates")),
                       "key": c.get("key"), "op": c.get("op"), "number": c.get("number")})
    plan["checks"] = checks
    return plan


# 05.3. The command list, the argv it becomes, the probe argv it is reduced to, and the one
# question a log tail is asked. All four are pure string work, which is why they live here
# rather than beside the driver that calls them: a test may pin them without a process.

def auto_command_list(plan):
    """The ordered command list one try walks once: `agent:` first, then `agent_failover:`.

    Nothing is dropped and nothing is validated — an entry that does not parse is still a row
    in `auto check`'s agents block, because "the second command is misspelled" is the finding,
    not a silence. Index 0 is the preference order's head, and every try starts there, so the
    preferred command comes back by itself the moment its cooldown lapses.

    Every command carries the plan's `model` and `effort`: `{model}` and `{effort}` are
    substituted wherever they appear, and a `claude` command that names neither gets the flag
    appended — `flight_plan_problems` has already refused one that sets its own. Substituted
    HERE, before `{brief}`, so the brief — untrusted text a model wrote — is never re-scanned.
    A plan with no pair (a fixture, a hand-built dict) passes its commands through unchanged."""
    model, effort = plan.get("model"), plan.get("effort")
    out = []
    for c in [plan["agent"]] + list(plan.get("agent_failover") or []):
        c = str(c)
        try:
            prog = os.path.basename((shlex.split(c) or [""])[0])
        except ValueError:
            out.append(c)                       # reported by 2h; passed through untouched
            continue
        for ph, flag, val in (("{model}", "--model", model), ("{effort}", "--effort", effort)):
            if not val:
                continue
            if ph in c:
                c = c.replace(ph, shlex.quote(str(val)))
            elif prog == AUTO_AGENT_CLAUDE:
                c = f"{c} {flag} {shlex.quote(str(val))}"
        out.append(c)
    return out


def auto_agent_argv(command, agent, brief):
    """One command string -> argv, with `{agent}` and `{brief}` substituted in ANY element.

    `{agent}` substitutes BEFORE `{brief}`: the brief is untrusted text a model wrote, and a
    brief that happens to contain the four characters `{agent}` must not be re-scanned. The
    brief goes in as TEXT, not as a path — the path reaches the child through CRUX_BRIEF.

    A `ValueError` from `shlex.split` propagates: the caller decides whether an unparseable
    command is a plan problem, a probe row or a failover."""
    argv = shlex.split(str(command or ""))
    a, b = str(agent or ""), str(brief or "")
    return [x.replace("{agent}", a).replace("{brief}", b) for x in argv]


def auto_probe_argv(command, probe):
    """The same command reduced to something that can be run with no prompt, plus `probe`.

    Two clauses. (1) Every element carrying a placeholder is dropped — the probe sends no
    brief, so an element that would have held one has nothing to hold. (2) A LONG option left
    dangling by (1) is dropped too, back to front, because `--agent` with nothing after it is
    a parse error in most CLIs.

    Clause 2 reads a long option (`--name`) and not every `-`, because by the GNU convention a
    long option's value is a separate element and a short flag may be a bare toggle: PRD §D's
    three worked examples turn on exactly that difference — `claude -p --agent {agent}
    "{brief}"` and the shipped template's `claude -p "{brief}"` both probe as
    `claude -p --version`, so `--agent` goes and `-p` stays.

    Clause 2 also always tests against clause 1's FIXED removal set, never against what clause
    2 itself removed: walking on would eat `-p` from
    `claude -p --agent {agent} --file {brief}` as well.

    A `ValueError` from `shlex.split` propagates, as in `auto_agent_argv`."""
    argv = shlex.split(str(command or ""))
    keep = [i for i, x in enumerate(argv) if "{brief}" not in x and "{agent}" not in x]
    dropped = set(range(len(argv))) - set(keep)
    while keep and argv[keep[-1]].startswith("--") and (keep[-1] + 1) in dropped:
        keep.pop()
    return [argv[i] for i in keep] + shlex.split(str(probe or ""))


def auto_rate_limited(text):
    """True when a log tail reads as a provider limit rather than as a bug in the attempt.

    A closed list of patterns, read case-insensitively, ported from the era skill's own
    LIMIT_PATTERNS. Total and never raises — it is asked about child output, which may be
    anything at all. Only a FAILED try's tail is ever passed here: an agent that merely
    mentions a rate limit in a transcript it then commits over must not be able to move the
    driver."""
    return bool(re.search("|".join(AUTO_RATE_LIMIT_PATTERNS), str(text or ""), re.I))


def metrics_value(tree, keypath, where):
    """One dotted key path through a parsed metrics document, as a float.

    The same walk `resolve_address` does, minus the vault: the driver has the document in
    hand — it just read it off the scorer's stdout — and there is no file to address. `where`
    is what the caller wants the refusal to name, so one helper serves both the dry run
    ("scorer output") and the recorded attempt."""
    node = tree
    for part in str(keypath).split("."):
        if not isinstance(node, dict) or part not in node:
            raise AddressError("missing-key", f"{where}: key path '{keypath}' does not resolve")
        node = node[part]
    if not isinstance(node, dict) or "value" not in node:
        raise AddressError("missing-value",
                           f"{where}: not a metrics leaf (an object carrying 'value')")
    raw = node["value"]
    if isinstance(raw, bool):
        raise AddressError("missing-value", f"{where}: value '{raw}' is not a number")
    try:
        return float(raw)
    except (TypeError, ValueError):
        raise AddressError("missing-value", f"{where}: value '{raw}' is not a number")


def manifest_diff(before, after):
    """`{added, removed, changed}` between two walks of the same roots.

    Pure set arithmetic over `{path, size, mtime_ns}` entries, so the whole comparison can be
    read and trusted without a filesystem. `changed` is size-or-mtime rather than a hash: the
    question is whether an attempt touched a shared root at all, and hashing sixty gigabytes
    to answer it would cost more than the run."""
    b = {e["path"]: e for e in (before or [])}
    a = {e["path"]: e for e in (after or [])}
    changed = [p for p in b if p in a
               and (b[p].get("size") != a[p].get("size")
                    or b[p].get("mtime_ns") != a[p].get("mtime_ns"))]
    return {"added": sorted(set(a) - set(b)), "removed": sorted(set(b) - set(a)),
            "changed": sorted(changed)}


# ------------------------------------------------------------------- 05.2: ticks and findings
# The one place a number becomes a tick. Total on purpose: true is `[x]`, false is `[ ]`, and
# "the key does not resolve, or there is no metrics document at all" is `[-]` — which is the
# whole crash path, because a `[-]` on an outcome-neutral check is already `invalid-run` under
# `derive_verdict_15`. The driver asserts nothing; it supplies this vector and `cmd_close`
# derives the verdict from it exactly as it does for a hand-closed node.
def auto_tick(metrics, text, where):
    """`(tick, found)` for one check against one metrics document. `tick` in "x", " ", "-"."""
    c = auto_check_comparison(text)
    if c is None:
        return ("-", "n/a — not a metric comparison")
    if metrics is None:
        return ("-", f"n/a — no {where}")
    try:
        v = metrics_value(metrics, c["key"], where)
    except AddressError as e:
        return ("-", f"n/a — {e}")
    n = c["number"]
    ok = {"<=": v <= n, "<": v < n, ">=": v >= n, ">": v > n,
          "==": v == n, "!=": v != n}[c["op"]]
    return ("x" if ok else " ", repr(v))


def auto_tick_body(body, ticks):
    """`body` with the i-th checkbox under `## Verifiables` ticked and noted `(found: …)`.

    Every other byte survives, continuation lines included: a `fails-if::` line is the
    commitment, and the driver has no business reflowing it. An existing note is REPLACED
    rather than appended to, so re-ticking is idempotent and `lock_material` — which already
    strips `(found: …)` — sees no change either way."""
    lines = body.split("\n")
    pat = re.compile(r"^(\s*- \[)(.)(\]\s*)(.*)$")
    hits, in_sec = [], False
    for i, line in enumerate(lines):
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "verifiables"
            continue
        if in_sec and pat.match(line):
            hits.append(i)
    if len(ticks) != len(hits):
        raise CruxError(f"auto ticks: {len(ticks)} ticks for {len(hits)} verifiables")
    for (tick, found), i in zip(ticks, hits):
        m = pat.match(lines[i])
        lines[i] = (m.group(1) + tick + m.group(3)
                    + _FOUND_RE.sub("", m.group(4)).rstrip() + f" (found: {found})")
    return "\n".join(lines)


def cmd_auto_ticks(root, hid, metrics, ticks=None):
    """Write the tick vector into one hypothesis' `## Verifiables`. Returns the vector.

    No `refresh` and no `updated:` bump: this is the evidence being recorded against a
    pre-registered check, not an edit to the commitment, and spec 11 already treats the
    `(found: …)` note as separable. `cmd_close` does the refreshing a moment later.

    `ticks` (05.3) is a vector the caller ALREADY has — the closer's merged onto the
    scorer's — written through as given, with no recomputation. It exists because the driver
    may not call `render_doc`/`write_if_changed` itself, so a merged vector has to be able to
    reach the node through the engine. `ticks=None` is 05.2's behaviour and bytes exactly."""
    v = Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise CruxError(f"auto ticks apply to a hypothesis (got a '{n.type}' for '{hid}')")
    where = f"{RESULTS_DIR}/{hid}/{METRICS_FILE}"
    if ticks is None:
        ticks = [auto_tick(metrics, text, where) for _c, text in _verifiable_lines(n["body"])]
    write_if_changed(n["path"], render_doc(n["fm"], auto_tick_body(n["body"], ticks)))
    return ticks


def auto_findings(address, value, ticks, failure=None):
    """The findings paragraph an autopilot close writes. A fixed template, so two runs of the
    same attempt read the same; `crux-close`'s prose arrives in 05.3.

    Backslashes become forward slashes because `cmd_close` substitutes findings with
    `re.sub`, where `\\g` in the replacement is a group reference and a Windows path is a
    traceback."""
    parts = [f"Autopilot close. Objective {address} = "
             f"{repr(value) if value is not None else 'n/a'}."]
    for i, (tick, found) in enumerate(ticks, 1):
        parts.append(f"Check {i}: {({'x': 'met', ' ': 'unmet', '-': 'n/a'})[tick]}, "
                     f"found {found}.")
    if failure:
        parts.append(f"Failure: {' '.join(str(failure).split())[:200]}.")
    return " ".join(parts).replace("\\", "/")


AUTO_CONFIRM_MISSED = "Confirmation missed:"


def cmd_auto_note_confirm_missed(root, hid, address, bar, direction, seeds, values):
    """Append the missed confirmation to a closed attempt's findings, once.

    The verdict is read at seed 0 off the pre-registered checks and does not move — a missed
    seed is a failed confirmation, never a changed verdict. But without this line the tree
    reads `supported` for a crossing that did not hold at the seeds the run re-scored it at,
    and the only record of that was the run's own ledger. Idempotent, so a resumed driver that
    re-runs the confirmation writes the line once."""
    v = Vault(root)
    n = v.get(hid)
    if n is None or n.type != "idea":
        raise CruxError(f"auto confirm note applies to a hypothesis (got '{hid}')")
    if AUTO_CONFIRM_MISSED in _section(n["body"], "Findings"):
        return False
    op = ">=" if direction == "max" else "<="
    shown = ", ".join("n/a" if x is None else f"{x:g}" for x in values)
    note = (f"{AUTO_CONFIRM_MISSED} re-scored at seeds {', '.join(str(s) for s in seeds)}, "
            f"{address} = {shown}, where every seed had to reach {op} {bar:g}. The checks "
            f"above are read at seed 0 and stand; the run did not stop on this attempt.")
    body = re.sub(r"(## Findings\n\n)(.*?)(\n*)(?=\n## |\Z)",
                  lambda m: f"{m.group(1)}{m.group(2)}\n\n{note}{m.group(3)}",
                  n["body"], count=1, flags=re.S)
    if body == n["body"]:
        raise CruxError(f"auto confirm note: '{hid}' has no ## Findings section to append to")
    write_if_changed(n["path"], render_doc(n["fm"], body))
    return True


def auto_crosses(value, bar, direction):
    """Did this value cross the plan's bar, inclusive, by the plan's direction?"""
    return value is not None and (value >= bar if direction == "max" else value <= bar)


def auto_improves(value, best, direction):
    """Is this value STRICTLY better than `best` (None meaning nothing to beat)? Strict, so an
    attempt that only matches the incumbent never takes the pointer from it."""
    return value is not None and (best is None
                                  or (value > best if direction == "max" else value < best))


# ------------------------------------------------------------------ 05.2: the plan's approval
def flight_plan_hash(text):
    """16 hex over what the PI actually signed: the frontmatter minus the approval stamp and
    the `updated:` clock, plus the body with the CONTENT of `## Guidance` removed.

    The Guidance exclusion is the whole design of the signature: `crux auto guide` is how the
    PI keeps talking to workers while a run is going, and an approval that a guidance line
    cleared would be an approval nobody could use."""
    fm, body = parse_doc(text)
    keep = {k: v for k, v in fm.items() if k not in AUTO_APPROVAL_UNHASHED}
    lines = body.split("\n")
    i = next((k for k, l in enumerate(lines)
              if l.startswith("## ") and l[3:].strip().lower() == "guidance"), None)
    if i is not None:
        j = next((k for k in range(i + 1, len(lines)) if lines[k].startswith("## ")),
                 len(lines))
        lines = lines[:i + 1] + lines[j:]
    material = json.dumps(keep, sort_keys=True, ensure_ascii=False) + "\x1e" + "\n".join(lines)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def auto_approval(text):
    """`{state, approved, approved_hash, hash}` for a plan's signature. `state` is
    `unapproved` (never signed), `approved` (signed, and the content still matches) or
    `edited` (signed, then changed outside `## Guidance`)."""
    fm = parse_doc(text)[0]
    a = str(fm.get("approved") or "").strip() or None
    h = str(fm.get("approved_hash") or "").strip() or None
    cur = flight_plan_hash(text)
    state = "unapproved" if (a is None or h is None) else \
            ("approved" if h == cur else "edited")
    return {"state": state, "approved": a, "approved_hash": h, "hash": cur}


def cmd_auto_approve(root, path):
    """The PI's signature on a flight plan: `approved:` and `approved_hash:`, written once.

    Idempotent, the way `approve-null` is — the FIRST approval's timestamp is the record. The
    hash is written quoted, because this engine's flat YAML turns an all-digit scalar into an
    int and a hash of sixteen digits would lose its leading zeros on the way back in.

    Deliberately NOT a `flight_plan_problems` check: every plan written before this release is
    unapproved, and making that a problem would change every pinned problem list for a fact
    that is not a defect of the document."""
    p = path if os.path.isabs(path) else os.path.join(root, path)
    rel = _rel(root, p)
    if not os.path.isfile(p):
        raise CruxError(f"no flight plan at {rel}")
    text = read(p)
    problems = flight_plan_problems(root, parse_flight_plan(text), rel)
    if problems:
        raise CruxError(f"cannot approve {rel}: {problems[0]['message']}")
    ap = auto_approval(text)
    if ap["state"] == "approved":
        return {"plan": rel, "approved": ap["approved"],
                "approved_hash": ap["approved_hash"], "already": True}
    stamp, h = now(), ap["hash"]
    m = re.match(r"^---\n(.*?)\n---\n?", text, re.S)
    if m is None:
        raise CruxError(f"cannot approve {rel}: the plan has no frontmatter to stamp")
    rows = [l for l in m.group(1).split("\n")
            if l.partition(":")[0].strip() not in ("approved", "approved_hash")]
    rows += [f"approved: {stamp}", f'approved_hash: "{h}"']
    write_if_changed(p, "---\n" + "\n".join(rows) + "\n---\n" + text[m.end():])
    return {"plan": rel, "approved": stamp, "approved_hash": h, "already": False}


# --------------------------------------------------------- 05.2: the proposal a worker leaves
def auto_proposal(raw, plan):
    """A worker's `proposal.json`, validated against a CLOSED schema: `claim`, and optional
    `controls` of `{text, fails_if}`.

    `retry` is the whole judgment here. A missing, unparseable or over-cap proposal is the
    machine's failure and is retried. Everything else about the FORM of the document is
    repaired rather than refused: a key outside the schema is ignored, and a control that is
    malformed, self-tagged, ungrammatical or duplicated is DROPPED, each with a line in
    `warnings`. A proposal is a report, not evidence — the commit and the scorer's document
    are the evidence — so a reporting mistake must not be able to throw away a measurement
    that was never taken. The integrity checks that DO void an attempt live in the driver:
    the frozen-path diff and the shared-root manifest.

    There is no field in which a worker can express a claim-directed check, so D17 holds by
    construction rather than by instruction: a control is tagged by the driver, and one that
    arrives carrying its own tag is dropped rather than honoured."""
    def out(retry, reason, detail, claim=None):
        return {"ok": False, "retry": retry, "reason": reason, "detail": detail,
                "claim": claim, "controls": [], "warnings": []}

    if raw is None:
        return out(True, "proposal-missing",
                   "the worker left no proposal.json in its workspace")
    try:
        obj = json.loads(raw)
    except ValueError as e:
        return out(True, "proposal-unparseable", f"proposal.json is not one JSON object ({e})")
    if not isinstance(obj, dict):
        return out(True, "proposal-unparseable",
                   f"proposal.json is not one JSON object (got {type(obj).__name__})")

    raw_claim = obj.get("claim")
    claim = (raw_claim.strip()
             if isinstance(raw_claim, str) and raw_claim.strip()
             and len(_prose_tokens(raw_claim)) <= PROSE_CAP else None)

    warnings = []
    extra = set(obj) - set(AUTO_PROPOSAL_KEYS)
    if extra:
        warnings.append(f"ignored key(s) outside {', '.join(AUTO_PROPOSAL_KEYS)}: "
                        f"{', '.join(sorted(extra))}")
    controls = obj.get("controls", [])
    if not isinstance(controls, list):
        warnings.append(f"dropped controls: not a list (got "
                        f"{type(controls).__name__})")
        controls = []
    seen = {" ".join(str(c.get("fails_if") or "").lower().split())
            for c in (plan.get("checks") or [])}
    seen.discard("")
    clean = []
    for i, c in enumerate(controls, 1):
        if (not isinstance(c, dict) or set(c) != set(AUTO_CONTROL_KEYS)
                or not all(isinstance(c.get(k), str) and c.get(k).strip()
                           for k in AUTO_CONTROL_KEYS)):
            warnings.append(f"dropped control {i}: it must be an object with exactly text "
                            f"and fails_if, both non-empty strings")
            continue
        tag = _KIND_TAG_RE.match(c["text"])
        if tag:
            warnings.append(f"dropped control {i}: it carries its own [{tag.group(1)}] tag, "
                            f"and the driver tags every control {NEUTRAL_KIND}")
            continue
        if auto_check_comparison(c["text"]) is None:
            warnings.append(f"dropped control {i}: not a metric comparison "
                            f"'<key.path> <op> <number>' with <op> one of "
                            f"{', '.join(AUTO_COMPARISON_OPS)} (got "
                            f"'{c['text'].strip()}')")
            continue
        norm = " ".join(c["fails_if"].lower().split())
        if norm in seen:
            warnings.append(f"dropped control {i}: it repeats an existing failure scenario "
                            f"'{c['fails_if'].strip()}'")
            continue
        seen.add(norm)
        clean.append({"text": c["text"].strip(), "fails_if": c["fails_if"].strip()})

    if not isinstance(raw_claim, str) or not raw_claim.strip():
        return out(True, "claim-missing", "proposal.json carries no claim", claim)
    n = len(_prose_tokens(raw_claim))
    if n > PROSE_CAP:
        return out(True, "claim-over-cap",
                   f"the claim runs to {n} words, over the {PROSE_CAP}-word cap", claim)
    return {"ok": True, "retry": False, "reason": None, "detail": None,
            "claim": raw_claim.strip(), "controls": clean, "warnings": warnings}


def auto_is_no_claim(root, hid):
    """Does this attempt's node carry the AUTO_NO_CLAIM placeholder instead of a hypothesis?

    The DURABLE answer to "did this attempt report a claim", and the reason it is read from
    the node rather than from the driver's side-table: that table is rebuilt from disk on
    resume and holds no proposal for an attempt whose worker ran under a driver that has since
    died. Asking it there made every RESUMED attempt look claimless, which forced
    `invalid-run` onto attempts that had stated a perfectly good hypothesis — a resumed
    attempt and a fresh one grading differently, which is the one thing the finish path
    exists to prevent.

    `_step_file` always runs before the close and writes either the worker's claim or the
    placeholder, so by the time anyone asks, the node already knows."""
    n = Vault(root).nodes.get(hid)
    if n is None:
        return True
    marker = AUTO_NO_CLAIM.split("{")[0].strip()
    return bool(marker) and marker in _section(n["body"], "Idea / Hypothesis")


def auto_claim_title(claim):
    """A node title from a claim: its first sentence, capped at AUTO_TITLE_WORDS words."""
    s = " ".join(str(claim).split())
    m = re.search(r"[.!?](\s|$)", s)
    first = s[:m.start() + 1] if m else s
    return " ".join(first.split()[:AUTO_TITLE_WORDS]) or "untitled attempt"


def auto_node_spec(plan, claim, controls):
    """Everything `cmd_hypothesize` needs to file one attempt: the plan's checks verbatim, in
    plan order, then the worker's own controls tagged outcome-neutral by the DRIVER.

    `fails_if` and `discriminates` are positional over (claims…, plan controls…, proposal
    controls…) — the same order the lines are written in, which is the order the lock hashes
    them in. A proposal control never discriminates: it is an apparatus check, and the claim
    is the plan's."""
    checks = list(plan.get("checks") or [])
    claims = [c for c in checks if c["kind"] == DEFAULT_KIND]
    plan_controls = [c for c in checks if c["kind"] == NEUTRAL_KIND]
    extra = list(controls or [])
    return {"title": auto_claim_title(claim), "claim": claim,
            "verifiables": [c["text"] for c in claims],
            "neutral": [c["text"] for c in plan_controls] + [c["text"] for c in extra],
            "fails_if": [c["fails_if"] or "" for c in claims + plan_controls]
                        + [c["fails_if"] for c in extra],
            "discriminates": [bool(c["discriminates"]) for c in claims + plan_controls]
                             + [False for _c in extra],
            "rule": plan.get("rule"), "rule_m": plan.get("rule_m"), "null": plan.get("null")}


# ----------------------------------------------------- 05.2: the run's state, stops and ledger
def auto_new_state(plan, run_id, at, pid, host, baseline_score, max_attempts=None):
    """The `state.json` a run opens with. Exactly `AUTO_STATE_KEYS`, always — the file is
    rewritten whole after every event, and a reader (the cockpit, 05.4) must never meet a
    shape that depends on how far the run got."""
    anchor = plan["anchor"]
    total = plan["budget_attempts"] if max_attempts is None \
        else min(plan["budget_attempts"], int(max_attempts))
    return {
        "run": run_id, "anchor": anchor, "plan": plan["path"], "plan_hash": None,
        "opened": at, "updated": at, "driver": {"pid": pid, "host": host},
        "mode": plan["mode"], "c_puct": plan["c_puct"], "escalated": False,
        "steward_requested": False, "base": None,
        "islands": {i: {"branch": f"crux/auto/{anchor}/island/{i}", "pointer": None,
                        "best": plan["baseline"], "best_score": baseline_score,
                        "seen_score": baseline_score, "stall": 0}
                    for i in plan["islands"]},
        "best": {"id": None, "score": None},
        "budget": {"attempts": {"used": 0, "total": total},
                   "hours": {"used": 0.0, "total": plan["budget_hours"]},
                   "model_calls": {"used": 0, "total": plan["budget_model_calls"]}},
        "in_flight": {}, "closed": [], "consecutive_invalid": 0, "stalls": 0,
        "confirmed": None, "stop": None, "tasks": {"run": None, "exceptions": []},
        "events": 0, "next_island": 0,
        # 05.3. `agents` is keyed by the COMMAND STRING — the plan is hash-locked for the
        # run's life, so the string is stable — and holds an absolute wall-clock stamp, so a
        # resume does not forget a cooldown. `steward.last_closed` is the `len(closed)` at
        # which the steward last ran: the guard against two invocations in one window.
        "agents": {},
        "steward": {"guidance": [], "invocations": 0, "islands": [], "last_closed": 0},
    }


def auto_stop(state, plan):
    """The stop that applies right now, or None. Four reasons, in this order, and no fifth:
    spec 11 rejects a `converged` stop, and the loop is not entitled to the opinion."""
    b = state["budget"]
    if state["confirmed"]:
        h = state["confirmed"]
        return {"reason": "success", "axis": None, "attempt": h,
                "detail": f"{h} closed supported, crossed the bar and passed confirmation at "
                          f"{plan['replicates']} seeds"}
    k = plan["abort_invalid_runs"]
    if k > 0 and state["consecutive_invalid"] >= k:
        return {"reason": "abort", "axis": None, "attempt": None,
                "detail": f"{state['consecutive_invalid']} invalid runs in a row "
                          f"(abort_invalid_runs {k})"}
    if state["stalls"] >= 2:
        return {"reason": "stall", "axis": None, "attempt": None,
                "detail": f"no improvement in {plan['stall_attempts']} closed attempts, twice"}
    if len(state["closed"]) >= b["attempts"]["total"]:
        return {"reason": "budget", "axis": "attempts", "attempt": None,
                "detail": f"{b['attempts']['used']} of {b['attempts']['total']} attempts "
                          f"closed"}
    if b["hours"]["used"] >= b["hours"]["total"]:
        return {"reason": "budget", "axis": "hours", "attempt": None,
                "detail": f"{b['hours']['used']:.4f} of {b['hours']['total']:g} driver hours "
                          f"used"}
    if b["model_calls"]["used"] >= b["model_calls"]["total"]:
        return {"reason": "budget", "axis": "model_calls", "attempt": None,
                "detail": f"{b['model_calls']['used']} of {b['model_calls']['total']} "
                          f"model calls used"}
    return None


def auto_ledger_line(event, fields, at=None):
    """One `ledger.jsonl` line, without its newline. The event vocabulary is closed HERE, so
    a driver that invented a name refuses to write it rather than writing a log nobody can
    fold."""
    if event not in AUTO_LEDGER_EVENTS:
        raise CruxError(f"'{event}' is not an autopilot ledger event")
    obj = dict(fields or {})
    obj["at"] = at or now()
    obj["event"] = event
    return json.dumps(obj, sort_keys=True, ensure_ascii=False)


def auto_manifest_violations(diff, workspace_roots, ids):
    """The shared-root paths an attempt touched that belong to NO attempt of this run.

    Every path under `<writable>/<some reserved id>/` is somebody's workspace and is therefore
    fine; anything else is a write into ground two attempts share, which is the one thing a
    parallel run cannot allow.

    `workspace_roots` is EVERY writable root, not just the first. It used to be the first
    alone, which made the plan grammar lie about its own list: a PI reading `writable: work/,
    results/` is told two roots are writable, and a worker that put a checkpoint in the second
    lost its attempt to a violation it could not have predicted, unretried and unrepairable.
    One string is still accepted, because that is what every 05.2 caller passes."""
    roots = [workspace_roots] if isinstance(workspace_roots, str) else list(workspace_roots or [])
    roots = [_auto_norm_path(r) for r in roots] or [""]
    owned = tuple(ids or ())
    out = set()
    for p in (list((diff or {}).get("added") or []) + list((diff or {}).get("removed") or [])
              + list((diff or {}).get("changed") or [])):
        if any(p == f"{r}/{h}" or p.startswith(f"{r}/{h}/") for r in roots for h in owned):
            continue
        out.add(p)
    return sorted(out)


def auto_status(root, qid=None):
    """`{anchor, state, events, last_event}` for one run. A PURE READ: no lock, no process,
    and it creates nothing — not even `auto/` — so a vault that never met autopilot reads
    exactly as it did."""
    qid = auto_qid_arg(qid)
    d = os.path.join(root, AUTO_DIR)
    if qid is None:
        ids = []
        if os.path.isdir(d):
            ids = sorted([x for x in os.listdir(d)
                          if os.path.isfile(os.path.join(d, x, AUTO_STATE_FILE))], key=natkey)
        if not ids:
            raise CruxError(f"auto status: no autopilot run in this vault "
                            f"({AUTO_DIR}/<qid>/{AUTO_STATE_FILE})")
        if len(ids) > 1:
            raise CruxError(f"auto status: several runs ({', '.join(ids)}); name the anchor")
        qid = ids[0]
    p = os.path.join(d, qid, AUTO_STATE_FILE)
    if not os.path.isfile(p):
        raise CruxError(f"auto status: no autopilot run on {qid} "
                        f"({AUTO_DIR}/{qid}/{AUTO_STATE_FILE} does not exist)")
    try:
        state = json.loads(read(p))
    except ValueError as e:
        raise CruxError(f"{AUTO_DIR}/{qid}/{AUTO_STATE_FILE} is damaged: {e}")
    events, last = 0, None
    lp = os.path.join(d, qid, AUTO_LEDGER_FILE)
    if os.path.isfile(lp):
        for line in read(lp).splitlines():
            # a torn tail is its own unparseable line; a reader skips it rather than
            # refusing to report the run it belongs to
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if isinstance(o, dict):
                events += 1
                last = o
    return {"anchor": qid, "state": state, "events": events, "last_event": last}


def auto_portfolio(rows, direction, k=AUTO_PORTFOLIO_K):
    """The diverse portfolio: rank by score in the objective's direction, then take greedily,
    skipping any candidate that is an ancestor or a descendant of one already taken.

    ERA returns top-k DIVERSE deliberately — one score is one evaluation, and five variations of
    one idea is not five ideas. Lineage is the diversity axis because it is the only one crux has
    for free: `builds_on` is already written on every attempt, and MAP-Elites' behaviour
    descriptors are rejected in spec §3 for exactly the reason that nobody writes them.

    TOTAL: a malformed row is dropped, never raised on. Returns the selected rows themselves,
    in rank order, so a caller that wants ids takes them and a caller that wants the row has it."""
    try:
        k = int(k)
    except (TypeError, ValueError):
        return []
    if k <= 0:
        return []

    # Lineage is built from EVERY row, candidate or not: a chain that passes through an
    # excluded attempt still links its two ends, or a dropped middle would let one idea in twice.
    parent = {}
    for r in rows or ():
        if isinstance(r, dict) and r.get("id") is not None:
            parent[r["id"]] = r.get("builds_on")

    def ancestors(x):
        out, cur = set(), parent.get(x)
        while cur is not None and cur not in out:
            out.add(cur)
            cur = parent.get(cur)
        return out

    def related(a, b):
        return a in ancestors(b) or b in ancestors(a)

    cands = []
    for r in rows or ():
        if not isinstance(r, dict):
            continue
        rid = r.get("id")
        # an invalid run measured nothing, and a None score is not a candidate — so neither
        # can ever outrank a real measurement
        if rid is None or r.get("verdict") == "invalid-run" or r.get("score") is None:
            continue
        try:
            value = float(r.get("score"))
        except (TypeError, ValueError):
            continue
        cands.append((r, rid, value))

    # two stable passes: ties break on natkey(id) ascending in BOTH directions, so the
    # answer is the same on every machine and every run
    cands.sort(key=lambda t: natkey(str(t[1])))
    cands.sort(key=lambda t: t[2], reverse=(direction != "min"))

    out, taken = [], []
    for r, rid, _value in cands:
        if any(related(rid, other) for other in taken):
            continue
        out.append(r)
        taken.append(rid)
        if len(out) >= k:
            break
    return out


def auto_cockpit(root, events=AUTO_EVENTS_TAIL, at=None):
    """Everything the Autopilot tab shows, for every run in this vault. A PURE READ of the run's
    OWN directory — `auto/<qid>/{state.json,ledger.jsonl,plan.md}` — and nothing else.

    It constructs no `Vault`, parses no node, calls no `resolve_address` and calls no
    `auto_island_attempts`: that one builds a whole `Vault(root)`, which is exactly the cost this
    endpoint exists to avoid. It creates nothing — not even `auto/` — so a vault that never met
    autopilot reads exactly as it did, the same rule `auto_status` already keeps.

    `plan.md` is the third file because the objective's `direction` lives in neither the state
    nor the ledger, and `auto_portfolio` cannot rank without it; `parse_flight_plan` is total
    text->dict, so reading it costs no tree. `at` stands in for "now" so liveness is testable
    without moving a clock; the server never passes it."""
    try:
        tail = max(0, min(int(events), AUTO_EVENTS_MAX))
    except (TypeError, ValueError):
        tail = AUTO_EVENTS_TAIL
    ref = at or now()

    d = os.path.join(root, AUTO_DIR)
    if not os.path.isdir(d):
        return {"active": False, "runs": []}
    ids = sorted([x for x in os.listdir(d)
                  if os.path.isfile(os.path.join(d, x, AUTO_STATE_FILE))], key=natkey)
    if not ids:
        return {"active": False, "runs": []}

    runs = []
    for qid in ids:
        runs.append(_auto_cockpit_run(d, qid, tail, ref))
    return {"active": bool(runs), "runs": runs}


def _auto_cockpit_run(d, qid, tail, ref):
    """One run's payload — exactly `AUTO_COCKPIT_RUN_KEYS`, in that order, whatever stage the
    run reached. The frozen shape is 05.3's own rule: a reader must never meet a shape that
    depends on how far the run got."""
    try:
        state = json.loads(read(os.path.join(d, qid, AUTO_STATE_FILE)))
    except ValueError as e:
        raise CruxError(f"{AUTO_DIR}/{qid}/{AUTO_STATE_FILE} is damaged: {e}")
    if not isinstance(state, dict):
        state = {}

    # ---------------------------------------------------------------------- the ledger, once
    parsed = []
    lp = os.path.join(d, qid, AUTO_LEDGER_FILE)
    if os.path.isfile(lp):
        for line in read(lp).splitlines():
            # a torn tail is its own unparseable line; a reader skips it rather than
            # refusing to report the run it belongs to
            try:
                o = json.loads(line)
            except ValueError:
                continue
            if isinstance(o, dict):
                parsed.append(o)

    # ------------------------------------------------------------------------- the objective
    obj = {"address": None, "direction": None, "bar": None}
    try:
        parsed_plan = (parse_flight_plan(read(os.path.join(d, qid, PLAN_FILE))) or {})
        spec = parsed_plan.get("objective") or {}
        bar = spec.get("bar")
        obj = {"address": spec.get("address"), "direction": spec.get("direction"),
               "bar": (float(bar) if bar not in (None, "") else None)}
    except Exception:
        obj = {"address": None, "direction": None, "bar": None}

    # --------------------------------------------------------------- in flight, by the state
    flight = state.get("in_flight")
    if not isinstance(flight, dict):
        flight = {}
    in_flight = [dict(v, id=key) for key, v in
                 sorted(flight.items(), key=lambda kv: natkey(str(kv[0])))
                 if isinstance(v, dict)]

    attempts = _auto_cockpit_attempts(parsed, flight, state.get("closed"))
    portfolio = [r["id"] for r in auto_portfolio(attempts, obj["direction"], AUTO_PORTFOLIO_K)]

    return {"anchor": qid,
            "run": state.get("run"),
            "plan": state.get("plan"),
            "mode": state.get("mode"),
            "opened": state.get("opened"),
            "updated": state.get("updated"),
            "liveness": _auto_liveness(state, ref),
            "objective": obj,
            "stop": state.get("stop"),
            "budget": state.get("budget"),
            "islands": state.get("islands"),
            "best": state.get("best"),
            "in_flight": in_flight,
            "agents": state.get("agents"),
            "steward": state.get("steward"),
            "attempts": attempts,
            "portfolio": portfolio,
            "events": list(reversed(parsed[-tail:])) if tail else [],
            "event_count": len(parsed)}


def _auto_liveness(state, ref):
    """§I-0's three states. There is no heartbeat field: `driver` is written at open and on
    resume and never again, and the lock is held only momentarily inside each event. So a set
    `stop` wins outright, and everything else is the age of `updated` against
    `AUTO_LIVE_SECONDS`. `stale` says only *no driver write since `updated`* — the tab never
    claims the driver died, and an `updated` that will not parse is stale, never running."""
    if state.get("stop"):
        return "stopped"
    try:
        written = datetime.datetime.fromisoformat(str(state.get("updated")))
        asof = datetime.datetime.fromisoformat(str(ref))
    except (TypeError, ValueError):
        return "stale"
    return "running" if (asof - written).total_seconds() <= AUTO_LIVE_SECONDS else "stale"


def _auto_cockpit_attempts(parsed, flight, closed):
    """The ledger folded into one row per attempt id, every row carrying exactly
    `AUTO_COCKPIT_ATTEMPT_KEYS` in that order. Later events overwrite earlier fields, `at` is
    the last event seen for that id, and the live `in_flight` phase wins over the folded one
    because the driver knows `committed`, a phase no ledger event spells."""
    rows, order = {}, []

    def row(aid):
        r = rows.get(aid)
        if r is None:
            r = dict((k, None) for k in AUTO_COCKPIT_ATTEMPT_KEYS)
            r["id"] = aid
            rows[aid] = r
            order.append(aid)
        return r

    for o in parsed:
        name, aid = o.get("event"), o.get("attempt")
        if aid is None or name not in ("attempt-reserved", "node-filed", "scored", "closed"):
            continue
        try:
            r = row(aid)
        except TypeError:                      # an unhashable attempt id is not an attempt id
            continue
        if name == "attempt-reserved":
            r["island"], r["parent"], r["phase"] = o.get("island"), o.get("parent"), "reserved"
        elif name == "node-filed":
            r["island"], r["parent"] = o.get("island"), o.get("parent")
            r["builds_on"], r["title"], r["phase"] = o.get("builds_on"), o.get("title"), "drafted"
        elif name == "scored":
            r["score"], r["seed"], r["phase"] = o.get("value"), o.get("seed"), "scored"
        else:
            r["verdict"], r["island"], r["phase"] = o.get("verdict"), o.get("island"), "closed"
            if o.get("value") is not None:     # a closed invalid run carries none, and none is
                r["score"] = o.get("value")    # invented for it
        r["at"] = o.get("at")

    for aid, r in rows.items():
        entry = flight.get(aid)
        if isinstance(entry, dict) and entry.get("phase") is not None:
            r["phase"] = entry["phase"]

    ordinal = {}
    for i, cid in enumerate(closed or ()):
        try:
            if cid not in ordinal:
                ordinal[cid] = i + 1
        except TypeError:
            continue
    for aid, r in rows.items():
        r["attempt_no"] = ordinal.get(aid)

    def rank(r):
        n = r.get("attempt_no")
        # the ones with an ordinal first, ascending by it; then the rest, by natkey(id)
        return (0, n, ("", 0)) if n is not None else (1, 0, natkey(str(r.get("id"))))

    return sorted((rows[a] for a in order), key=rank)


def append_guidance(root, path, text, author):
    """Append one stamped entry to `## Guidance`. APPEND-ONLY by construction, not by promise:
    every byte from the file start through the `## Guidance` heading line is untouched, and
    every entry already there survives verbatim. Returns the entry line."""
    t = " ".join(str(text or "").split())
    a = " ".join(str(author or "").split())
    if not t:
        raise CruxError("guidance text is empty")
    if not a:
        raise CruxError("guidance author is empty")
    p = path if os.path.isabs(path) else os.path.join(root, path)
    rel = _rel(root, p)
    if not os.path.isfile(p):
        raise CruxError(f"no flight plan at {rel}")
    lines = read(p).split("\n")
    start = next((i for i, l in enumerate(lines)
                  if l.startswith("## ") and l[3:].strip().lower() == "guidance"), None)
    if start is None:
        raise CruxError("flight plan has no ## Guidance section to append to")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
               len(lines))
    seg = lines[start + 1:end]
    content = [l for l in seg if l.strip()]
    if content and all(_PLACEHOLDER.match(l) for l in content):
        seg = [l for l in seg if not _PLACEHOLDER.match(l)]   # the template's own prompt
    while seg and not seg[-1].strip():
        seg.pop()
    if not seg or seg[0].strip():
        seg.insert(0, "")
    entry = f"- [{now()}] {a}: {t}"
    seg.append(entry)
    write_if_changed(p, "\n".join(lines[:start + 1] + seg + [""] + lines[end:]))
    return entry


# ----------------------------------------------------------------------------- selection (PUCT)
# Ported from google-research/era implementation/futs.py (Apache-2.0, commit eb56676…); the
# arithmetic below is theirs verbatim — rank score + c_puct * (1/N) * sqrt(total visits) /
# (1 + visits) — never imported, never vendored.
#
# The `1/N` prior is load-bearing and is why the port is written out rather than
# approximated: with a constant prior the exploration term grows without bound as the
# population does, and the search never settles on anything.
def puct_rank(attempts, c_puct, direction="max", virtual=()):
    """[{id, score, visits, rank_score, puct}] sorted by puct desc, ties by natural id.

    Pure arithmetic over a list of dicts: no vault, no filesystem, no model — which is the
    whole argument for selection living in the engine rather than in the loop that uses it.
    The caller's list is never mutated; virtual visits are applied to a copy."""
    rows = list(attempts or [])
    if not rows:
        raise CruxError("puct: no scored attempts to rank")
    if direction not in OBJECTIVE_DIRECTIONS:
        raise CruxError(f"puct: direction must be min or max (got '{direction}')")
    visits = {r["id"]: int(r.get("visits") or 0) for r in rows}
    parent = {r["id"]: r.get("builds_on") for r in rows}
    # `backpropagate_visit`: an in-flight attempt is a visit to its parent and to every
    # ancestor of it, so a lineage already being worked stops looking cheap.
    for vid in (virtual or ()):
        cur, walked = vid, set()
        while cur in visits and cur not in walked:
            walked.add(cur)
            visits[cur] += 1
            cur = parent.get(cur)
    eff = {r["id"]: (float(r["score"]) if direction == "max" else -float(r["score"]))
           for r in rows}
    n = len(rows)
    # Ties in effective score break so the LOWER natural id ranks HIGHER. The rank list runs
    # worst-first, so equal scores sort by natkey DESCENDING: a newcomer that only MATCHES the
    # incumbent never takes the selection from it, and "ties go to the lowest id" holds here
    # and in the brief's `best` alike.
    order = sorted(rows, key=lambda r: natkey(r["id"]), reverse=True)
    order.sort(key=lambda r: eff[r["id"]])
    rank = {r["id"]: (i / (n - 1) if n > 1 else 0.5) for i, r in enumerate(order)}
    total = sum(visits.values())
    prior = 1.0 / n
    out = [{"id": r["id"], "score": float(r["score"]), "visits": visits[r["id"]],
            "rank_score": rank[r["id"]],
            "puct": rank[r["id"]] + c_puct * prior * math.sqrt(total) / (1 + visits[r["id"]])}
           for r in rows]
    out.sort(key=lambda d: (-d["puct"], natkey(d["id"])))
    return out


def puct_select(attempts, c_puct, direction="max", virtual=()):
    """The id to build the next attempt on. `c_puct = 0` IS Climb — the highest-scoring
    attempt, on every call, with no separate greedy branch to drift away from this one."""
    return puct_rank(attempts, c_puct, direction=direction, virtual=virtual)[0]["id"]


def auto_island_attempts(root, plan, island):
    """The island's scored candidates: the baseline (always, wherever it sits) plus every
    CLOSED attempt under the island. `[{id, score, builds_on, visits, verdict}]` by id.

    `score` is None when the address does not resolve or the run was invalid — an invalid run
    measured nothing, and ranking it would let a broken apparatus win."""
    v = Vault(root)
    address = plan.get("address")
    base = plan.get("baseline")
    ids = []
    if base in v.nodes:
        ids.append(base)
    for cid in v.children.get(island, ()):
        c = v.nodes[cid]
        if c.type == "idea" and c.status == TERMINAL_IDEA and cid not in ids:
            ids.append(cid)
    ids.sort(key=natkey)

    lineage = {nid: node_builds_on(nd) for nid, nd in v.nodes.items() if nd.type == "idea"}
    def chain(nid):
        out, cur, seen = [], lineage.get(nid), set()
        while cur and cur not in seen:
            seen.add(cur)
            out.append(cur)
            cur = lineage.get(cur)
        return out

    rows = []
    for nid in ids:
        nd = v.nodes[nid]
        verdict = nd["fm"].get("verdict") or None
        score = None
        if address and verdict != "invalid-run":
            try:
                score = float(resolve_address(root, f"{nid}#{address}")["value"])
            except (CruxError, TypeError, ValueError):
                score = None
        bo = node_builds_on(nd)
        # a report is a visit, whatever it concluded: the cost was paid either way
        visits = (1 if bo else 0) + sum(1 for other in ids if other != nid
                                        and nid in chain(other))
        rows.append({"id": nid, "score": score, "builds_on": bo, "visits": visits,
                     "verdict": verdict})
    return rows


def auto_select(root, path, island=None, virtual=()):
    """The attempt a new one should build on, for one island of one flight plan."""
    plan = load_flight_plan(root, path)
    isl = island or plan["anchor"]
    if isl != plan["anchor"] and isl not in plan["islands"]:
        raise CruxError(f"auto select: '{isl}' is neither the anchor nor an island of the "
                        f"flight plan")
    rows = [r for r in auto_island_attempts(root, plan, isl) if r.get("score") is not None]
    return puct_select(rows, plan["c_puct"], direction=plan["direction"], virtual=virtual)


# ----------------------------------------------------------------------------- the worker brief
# What a fresh worker is handed, and nothing else. The three ways a brief tells an agent which
# answer to come back with are the anchor's own advocacy, another island's dead ends, and a
# number that was true an hour ago — so the exclusions and the address re-resolution are part
# of ASSEMBLY, not a linter run afterwards. A brief that fails a check is never produced.
AUTO_BRIEF_SLOTS  = ("goal", "objective.address", "objective.direction", "objective.bar",
                     "island.id", "island.title", "parent.id", "parent.claim", "parent.score",
                     "best.id", "best.score", "null", "verifiables", "rule")
AUTO_BRIEF_BUDGET = {"inspirations": 3, "refuted": 5, "guidance": 10, "findings_words": 80,
                     "steward": 10, "ledger": 40}
AUTO_BRIEF_CHECKS = ("schema", "budget", "stable", "leakage", "addresses")
AUTO_CUT_PREFIX   = "Cut to budget:"
# What a claim is FOR, in words. The cap itself is PROSE_CAP and is the engine's; this is the
# range a worker should aim at, well under it, so a claim is never close enough to the cap for
# one more sentence to cost the attempt. An attempt wrote 1126 words into its claim and then
# 737 on its retry, and lost both — the brief had never said a cap existed.
AUTO_CLAIM_TARGET     = (150, 250)
AUTO_NO_REFUTED       = "No refuted attempts on this island yet."
AUTO_NO_INSPIRATIONS  = "No other supported attempts on this island yet."
AUTO_NO_OTHER_ISLANDS = "No other islands."
AUTO_NO_GUIDANCE      = "No guidance yet."


def auto_plan_for(root, v, hid):
    """(qid, plan path) of the nearest ancestor question of `hid` that carries a flight plan,
    or (None, None). Nearest first: a sub-question's own plan governs its own island."""
    n = v.nodes.get(hid)
    if n is None:
        return None, None
    for m in reversed(ancestor_chain(v, n)):
        if m.type == "question" and os.path.isfile(flight_plan_path(root, m.id)):
            return m.id, flight_plan_path(root, m.id)
    return None, None


def auto_brief(root, hid, island=None, islands=None, steward=None, budget=None):
    """The brief for the next attempt built on `hid`. Byte-stable: no timestamps, every list
    order defined, every number carried as the address it came from.

    `island` (05.2) names the island the NEW attempt will sit under, which is not always the
    parent's question: the first attempt on an Explore island builds on the baseline, and the
    baseline sits under the anchor. Absent, the island is the parent's own question exactly as
    in 05.0, and the payload is unchanged.

    `islands` (05.3) is the EFFECTIVE island set, which from this slice on is the run's
    `state.json` table rather than the plan's frontmatter: a steward-opened island is not in
    `islands:` — that field IS hashed, and writing it would clear the PI's approval mid-run —
    so without this the membership check below would refuse the very island the run just
    opened. Absent, the plan's own list, byte-identical to 05.2.

    `steward` (05.3) is the steward's standing guidance, rendered in its OWN labelled section
    so a worker can see who said what. Absent or empty, the section says so.

    `budget` is the RUN's own `{used, total}` for attempts, straight out of `state.json`.
    Absent — `crux auto brief` typed by hand — the attempt count falls back to the vault walk
    it always used. See the comment at the count itself for what that walk gets wrong."""
    v = Vault(root)
    n = v.get(hid)
    # The type check comes FIRST. Plan discovery walks ancestors and excludes the node itself,
    # so a question that carries its own plan would otherwise be told no plan covers it —
    # which is true of the walk and false of the vault, and says nothing about the real fault.
    if n.type != "idea":
        raise CruxError(f"auto brief is per-attempt (got a '{n.type}' for '{hid}')")
    qid, ppath = auto_plan_for(root, v, hid)
    if qid is None:
        raise CruxError(f"no flight plan covers {hid}: none of its ancestor questions has "
                        f"{AUTO_DIR}/<qid>/{PLAN_FILE}")
    plan = load_flight_plan(root, ppath)
    eff_islands = list(plan["islands"] if islands is None else islands)
    if island is None:
        island = n.parent
        if island != plan["anchor"] and island not in eff_islands:
            raise CruxError(f"auto brief: '{hid}' sits under '{island}', which is neither the "
                            f"anchor nor an island of the flight plan")
    else:
        if island != plan["anchor"] and island not in eff_islands:
            raise CruxError(f"auto brief: '{island}' is neither the anchor nor an island of "
                            f"the flight plan")
        if hid != plan["baseline"] and n.parent != island:
            raise CruxError(f"auto brief: '{hid}' is neither the baseline nor an attempt "
                            f"under '{island}'")

    address, direction, base = plan["address"], plan["direction"], plan["baseline"]
    anchor = plan["anchor"]
    cut = []

    def claim_of(nid):
        return _section(v.nodes[nid]["body"], "Idea / Hypothesis")

    def findings_of(nid):
        return _deck_text(v.nodes[nid]["body"], "Findings")

    def addr_of(nid):
        return {"value": float(resolve_address(root, f"{nid}#{address}")["value"]),
                "addr": f"{nid}#{address}"}

    def trimmed(nid):
        text = findings_of(nid)
        toks = text.split()
        cap = AUTO_BRIEF_BUDGET["findings_words"]
        if len(toks) <= cap:
            return text
        cut.append(f"findings {nid}: kept {cap} of {len(toks)} words (leading words)")
        return " ".join(toks[:cap]) + " …"

    def extreme(rows):
        """The best of `rows` by the plan's direction; ties to the lowest natural id."""
        pool = [r for r in rows if r.get("score") is not None]
        if not pool:
            return None
        return sorted(pool, key=lambda r: (r["score"] if direction == "min" else -r["score"],
                                           natkey(r["id"])))[0]

    cands = auto_island_attempts(root, plan, island)
    best_row = extreme([c for c in cands if c["verdict"] == "supported" or c["id"] == base])
    best_id = best_row["id"] if best_row else None

    insp_rows = sorted([c for c in cands if c["verdict"] == "supported"
                        and c["score"] is not None and c["id"] not in (hid, best_id)],
                       key=lambda r: (r["score"] if direction == "min" else -r["score"],
                                      natkey(r["id"])))
    if len(insp_rows) > AUTO_BRIEF_BUDGET["inspirations"]:
        cut.append(f"inspirations: kept {AUTO_BRIEF_BUDGET['inspirations']} of "
                   f"{len(insp_rows)} (top by score)")
        insp_rows = insp_rows[:AUTO_BRIEF_BUDGET["inspirations"]]

    ref_ids = sorted([c for c in v.children.get(island, ())
                      if v.nodes[c].type == "idea"
                      and v.nodes[c]["fm"].get("verdict") == "refuted"],
                     key=natkey, reverse=True)
    if len(ref_ids) > AUTO_BRIEF_BUDGET["refuted"]:
        cut.append(f"refuted: kept {AUTO_BRIEF_BUDGET['refuted']} of {len(ref_ids)} "
                   f"(newest by id)")
        ref_ids = ref_ids[:AUTO_BRIEF_BUDGET["refuted"]]

    guidance = list(plan.get("guidance") or [])
    if len(guidance) > AUTO_BRIEF_BUDGET["guidance"]:
        cut.append(f"guidance: kept {AUTO_BRIEF_BUDGET['guidance']} of {len(guidance)} "
                   f"(newest)")
        guidance = guidance[-AUTO_BRIEF_BUDGET["guidance"]:]

    steward_lines = list(steward or [])
    if len(steward_lines) > AUTO_BRIEF_BUDGET["steward"]:
        cut.append(f"steward: kept {AUTO_BRIEF_BUDGET['steward']} of {len(steward_lines)} "
                   f"(newest)")
        steward_lines = steward_lines[-AUTO_BRIEF_BUDGET["steward"]:]

    def failed_checks(nid):
        nd = v.nodes[nid]
        out = []
        for item, s in zip(_verifiables(nd["body"]), verifiable_scenarios(nd["body"])):
            if item["kind"] == DEFAULT_KIND and item["state"] == "unmet":
                out.append({"text": item["text"], "fails_if": s.get("fails_if")})
        return out

    def score_or_none(nid):
        try:
            return addr_of(nid)
        except (CruxError, TypeError, ValueError):
            return None

    # every OTHER island contributes its BEST and nothing else. A worker that could read a
    # sibling island's dead ends is being told which way to lean.
    migration = []
    for oi in eff_islands:
        if oi == island or oi not in v.nodes:
            continue
        ocands = auto_island_attempts(root, plan, oi)
        # An island nobody has worked yet has exactly one candidate — the shared baseline,
        # which sits somewhere else. Reporting that as "its best" tells a worker the island
        # has produced something when it has produced nothing.
        if base not in v.children.get(oi, ()) and all(c["id"] == base for c in ocands):
            continue
        ob = extreme([c for c in ocands
                      if c["verdict"] == "supported" or c["id"] == base])
        if ob is None:
            continue
        migration.append({"island": {"id": oi, "title": v.nodes[oi].title},
                          "best": {"id": ob["id"], "claim": claim_of(ob["id"]),
                                   "score": score_or_none(ob["id"])}})

    # THE RUN's counter, not the vault's. Counting every `idea` under the anchor counts the
    # baseline and every attempt every EARLIER run left behind, so a fresh run told its first
    # worker "16 of 30 used, 14 remaining" while its own `state.json` read `0 of 30` — wrong
    # from the first attempt and further wrong after every restart. The driver holds the only
    # honest answer, which is the same number `auto_stop` reads, so a worker and the stop
    # condition can no longer disagree about how much run is left.
    #
    # The vault count survives as the fallback for `crux auto brief` run BY HAND, where there
    # is no driver to ask. That path reports on a run rather than steering one.
    if budget:
        used = int(budget.get("used") or 0)
        total = budget.get("total")
    else:
        used = sum(1 for nd in v.nodes.values()
                   if nd.type == "idea" and any(m.id == anchor for m in ancestor_chain(v, nd)))
        total = plan["fm"].get("budget_attempts")

    payload = {
        "engine_version": ENGINE_VERSION, "mode": "auto", "plan": plan["path"],
        "anchor": {"id": anchor, "title": v.nodes[anchor].title},
        "goal": plan.get("goal") or "",
        "objective": {"address": address, "direction": direction, "bar": plan["bar"]},
        "island": {"id": island, "title": v.nodes[island].title},
        "parent": {"id": hid, "claim": claim_of(hid), "verdict": n["fm"].get("verdict") or None,
                   "score": score_or_none(hid), "findings": trimmed(hid)},
        "best": ({"id": best_id, "claim": claim_of(best_id), "score": score_or_none(best_id)}
                 if best_id else None),
        "inspirations": [{"id": r["id"], "claim": claim_of(r["id"]),
                          "score": score_or_none(r["id"]), "findings": trimmed(r["id"])}
                         for r in insp_rows],
        "refuted": [{"id": r, "claim": claim_of(r), "score": score_or_none(r),
                     "findings": trimmed(r), "failed_checks": failed_checks(r)}
                    for r in ref_ids],
        "migration": migration,
        "null": plan.get("null") or "",
        "verifiables": [{"text": item["text"], "kind": item["kind"],
                         "fails_if": s.get("fails_if"), "discriminates": s.get("discriminates")}
                        for item, s in zip(plan.get("verifiables") or [],
                                           plan.get("scenarios") or [])],
        "rule": plan.get("rule"), "rule_m": plan.get("rule_m"),
        "guidance": guidance,
        "steward": steward_lines,
        "budget": {"attempts": {"total": total, "used": used,
                                "remaining": max((total or 0) - used, 0)}},
        # The three facts a worker needs in order to SUCCEED, as opposed to the facts it needs
        # in order to choose. They reached the worker only when a human remembered to append
        # them with `crux auto guide`, and on 2026-09-21 a run aborted after five invalid
        # attempts for want of them: three workers tried an interpreter the plan never named,
        # could not run anything, and concluded execution was forbidden; two wrote a
        # twenty-key `proposal.json` where `auto_proposal` reads exactly two keys. Two of the
        # five had in fact measured a program that passed every check. Guidance is a prompt
        # and a prompt is not a guarantee, so what the engine already KNOWS it now states —
        # every run, whether or not anybody remembered.
        "harness": {"scorer": plan["scorer"], "address": address,
                    "op": auto_direction_op(direction),
                    "shared": ", ".join(f"`{w}`" for w in plan["writable"]) or "no shared root",
                    "frozen": ", ".join(f"`{f}`" for f in plan["frozen"]) or "nothing"},
        "schema": {"keys": list(AUTO_PROPOSAL_KEYS),
                   "control_keys": list(AUTO_CONTROL_KEYS),
                   "ops": list(AUTO_COMPARISON_OPS),
                   "claim_words": PROSE_CAP,
                   "claim_target": list(AUTO_CLAIM_TARGET)},
        "cut": cut,
    }

    # check 1: the schema. A brief is never returned half-assembled — a missing slot means a
    # worker would be told less than the contract says it gets, which is worse than a refusal.
    for slot in AUTO_BRIEF_SLOTS:
        val = payload
        for part in slot.split("."):
            val = val.get(part) if isinstance(val, dict) else None
        if val is None or val == "" or val == [] or val == {}:
            raise CruxError(f"auto brief: required slot '{slot}' is absent or empty")
    return payload


def auto_brief_verify(root, payload):
    """Every {value, addr} pair in a brief, re-resolved against the vault. [] means the brief
    still tells the truth. This is the `deck --verify` contract at brief scale: a stale
    'current best' is the one lie in a brief no reader could ever catch."""
    out = []
    def walk(o):
        if isinstance(o, dict):
            if set(o) == {"value", "addr"}:
                addr = o.get("addr")
                try:
                    live = float(resolve_address(root, addr)["value"])
                except (CruxError, TypeError, ValueError) as e:
                    out.append({"addr": addr, "value": o.get("value"), "live": None,
                                "message": str(e)})
                    return
                if float(o.get("value")) != live:
                    out.append({"addr": addr, "value": o.get("value"), "live": live,
                                "message": f"{addr}: brief carries {o.get('value')}, "
                                           f"vault has {live}"})
                return
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(payload)
    return out


def auto_brief_leaks(root, payload):
    """The strings that must NOT be in this brief but are. Computed from the vault, never from
    a list of sentinels: the anchor's advocacy, every attempt's private problem statement, and
    everything a sibling island holds except the one line its best contributes."""
    v = Vault(root)
    blob = json.dumps(payload, ensure_ascii=False)
    anchor = (payload.get("anchor") or {}).get("id")
    island = (payload.get("island") or {}).get("id")
    bests = {m["island"]["id"]: m["best"]["id"] for m in (payload.get("migration") or [])}
    excluded = []

    an = v.nodes.get(anchor)
    if an is not None:
        pre = an["body"].split(LEDGER_START)[0]
        for h in ("Problem Statement", "Answer so far", "Protocol", "TL;DR", "ELI5"):
            excluded.append((f"{anchor} ## {h}", _auto_text(_section(pre, h))))
    for nid in _auto_subtree(v, anchor) if an is not None else ():
        nd = v.nodes[nid]
        if nd.type == "idea":
            excluded.append((f"{nid} ## Problem Statement",
                             _auto_text(_section(nd["body"], "Problem Statement"))))

    try:
        _p = load_flight_plan(root, payload.get("plan"))
        # 05.3: a steward-opened island is not in the plan's `islands:` frontmatter, so the
        # plan's list alone would silently stop excluding that island's prose from another
        # island's brief — the one lie in a brief no reader could catch. The payload's own
        # `migration` names every island the brief carried, so the union is the real set.
        islands, base = sorted(set(_p["islands"]) | set(bests)), _p["baseline"]
    except CruxError:
        islands, base = list(bests), None
    for oi in islands:
        if oi == island or oi not in v.nodes:
            continue
        ob = bests.get(oi)
        for nid in _auto_subtree(v, oi):
            if nid == oi or nid == base:
                # The baseline is a candidate of EVERY island (§5) — the PI's own starting
                # point, not one island's private product. When it happens to sit under
                # another island, banning its prose would make a valid plan fail its own lint.
                continue                      # the island's own id and title are the header
            nd = v.nodes[nid]
            heads = PROSE_SECTIONS.get(nd.type, ())
            if nid == ob:
                heads = ("Findings", "Problem Statement", "TL;DR", "ELI5",
                         "Planned Intervention")
            else:
                excluded.append((f"{nid} title", nd.title))
            pre = nd["body"].split(LEDGER_START)[0]
            for h in heads:
                excluded.append((f"{nid} ## {h}", _auto_text(_section(pre, h))))

    out = []
    for label, text in excluded:
        t = (text or "").strip()
        if not t or not _prose_tokens(t):
            continue
        if t in blob:
            out.append(f"{label} reached the brief")
    return out


def auto_brief_lint(root, hid):
    """Every brief check, in the declared order, as a report. The verb behind
    `crux auto brief --lint`: the brief itself, then whether it can be trusted."""
    names = list(AUTO_BRIEF_CHECKS)
    try:
        payload = auto_brief(root, hid)
    except CruxError as e:
        return {"ok": False, "id": hid, "brief": None, "text": "",
                "checks": [{"name": names[0], "ok": False, "detail": str(e)}]
                          + [{"name": nm, "ok": False, "detail": "not run"}
                             for nm in names[1:]]}
    text = auto_brief_text(payload)
    checks = [{"name": "schema", "ok": True,
               "detail": f"{len(AUTO_BRIEF_SLOTS)} slots filled"}]
    cut = payload.get("cut") or []
    checks.append({"name": "budget", "ok": True,
                   "detail": "nothing cut" if not cut else "; ".join(cut)})

    first = json.dumps(payload, sort_keys=True)
    again = json.dumps(auto_brief(root, hid), sort_keys=True)
    copied, copy_err = None, None
    tmp = tempfile.mkdtemp(prefix="crux_auto_stable_")
    try:
        # Only what a brief reads: the vault marker and the root-level documents, plus the
        # flight plans and the metrics its addresses resolve into. Copying the whole vault
        # would drag raw/ and wiki/ through every lint for nothing.
        for nm in sorted(os.listdir(root)):
            src = os.path.join(root, nm)
            if os.path.isfile(src):
                shutil.copy2(src, os.path.join(tmp, nm))
            elif nm in (AUTO_DIR, RESULTS_DIR) and os.path.isdir(src):
                shutil.copytree(src, os.path.join(tmp, nm))
        copied = json.dumps(auto_brief(tmp, hid), sort_keys=True)
    except Exception as e:
        copy_err = f"{e.__class__.__name__}: {e}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    # A copy that could not be made or could not be briefed FAILS the check. Treating it as a
    # pass is the one outcome that makes a stability check worthless: it goes green exactly
    # when it learned nothing.
    stable = (again == first) and copied == first
    if stable:
        detail = "identical across two assemblies and a copy of the vault"
    elif copy_err is not None:
        detail = f"the vault copy could not be briefed ({copy_err})"
    else:
        detail = "the payload is not byte-stable"
    checks.append({"name": "stable", "ok": stable, "detail": detail})

    leaks = auto_brief_leaks(root, payload)
    checks.append({"name": "leakage", "ok": not leaks,
                   "detail": "nothing private reached the brief" if not leaks
                             else "; ".join(leaks)})

    reports = auto_brief_verify(root, payload)
    n_addr = len(_auto_addr_pairs(payload))
    checks.append({"name": "addresses", "ok": not reports,
                   "detail": f"{n_addr} numbers re-resolved" if not reports
                             else "; ".join(r["message"] for r in reports)})
    return {"ok": all(c["ok"] for c in checks), "id": hid, "brief": payload, "text": text,
            "checks": checks}


def _auto_addr_pairs(payload):
    """Every {value, addr} pair in a brief, in walk order."""
    out = []
    def walk(o):
        if isinstance(o, dict):
            if set(o) == {"value", "addr"}:
                out.append(o)
                return
            for x in o.values():
                walk(x)
        elif isinstance(o, list):
            for x in o:
                walk(x)
    walk(payload)
    return out


def auto_brief_text(payload):
    """The brief as a worker reads it. Deterministic: same payload, same bytes, and every
    empty case says so out loud rather than rendering a blank — 'no refuted attempts' is a
    fact about the island, and a missing section reads as an omission."""
    p = payload or {}
    isl = p.get("island") or {}
    obj = p.get("objective") or {}
    best = p.get("best") or {}
    bscore = best.get("score") or {}
    par = p.get("parent") or {}
    pscore = par.get("score") or {}
    out = [f"# Autopilot brief — next attempt on {isl.get('id')}  ({p.get('plan')})", ""]

    out += ["## Goal", "", p.get("goal") or "—", ""]
    out += ["## Objective", "",
            f"{obj.get('address')} · {obj.get('direction')} · bar {obj.get('bar')}",
            f"current best: {best.get('id')} = {bscore.get('value')}  "
            f"[{bscore.get('addr')}]", ""]
    out += ["## Island", "", f"{isl.get('id')} — {isl.get('title')}", ""]
    out += ["## Parent attempt", "",
            f"{par.get('id')} — {par.get('claim')}",
            f"score: {pscore.get('value')}  [{pscore.get('addr')}]",
            f"verdict: {par.get('verdict') or '—'}",
            f"findings: {par.get('findings') or '—'}", ""]

    out += ["## Inspirations", ""]
    insp = p.get("inspirations") or []
    if not insp:
        out.append(AUTO_NO_INSPIRATIONS)
    for i in insp:
        s = i.get("score") or {}
        out.append(f"- {i.get('id')} — {i.get('claim')} · {s.get('value')}  [{s.get('addr')}]")
        if i.get("findings"):
            out.append(f"  {i['findings']}")
    out.append("")

    out += ["## Refuted attempts", ""]
    ref = p.get("refuted") or []
    if not ref:
        out.append(AUTO_NO_REFUTED)
    for r in ref:
        s = r.get("score") or {}
        val = s.get("value") if s else None
        out.append(f"- {r.get('id')} — {r.get('claim')} · "
                   f"{val if val is not None else '—'}")
        for c in r.get("failed_checks") or []:
            out.append(f"  failed: {c.get('text')} — fails-if: {c.get('fails_if') or '—'}")
    out.append("")

    out += ["## Other islands", ""]
    mig = p.get("migration") or []
    if not mig:
        out.append(AUTO_NO_OTHER_ISLANDS)
    for m in mig:
        b = m.get("best") or {}
        s = b.get("score") or {}
        out.append(f"- {(m.get('island') or {}).get('id')} best: {b.get('id')} — "
                   f"{b.get('claim')} · {s.get('value')}  [{s.get('addr')}]")
    out.append("")

    out += ["## Inherited bar", "", f"null: {p.get('null') or '—'}"]
    rule_line = f"rule: {p.get('rule')}"
    if p.get("rule_m") is not None:
        rule_line += f" (m={p.get('rule_m')})"
    out.append(rule_line)
    for vf in p.get("verifiables") or []:
        out.append(f"- [{vf.get('kind')}] {vf.get('text')}")
        if vf.get("fails_if"):
            out.append(f"      fails-if:: {vf['fails_if']}")
        if vf.get("discriminates"):
            out.append("      discriminates:: true")
    out.append("")

    out += ["## Guidance", ""]
    guid = p.get("guidance") or []
    if not guid:
        out.append(AUTO_NO_GUIDANCE)
    for g in guid:
        out.append(f"- [{g.get('at')}] {g.get('author')}: {g.get('text')}")
    out.append("")

    out += ["## Steward guidance", ""]
    stew = p.get("steward") or []
    if not stew:
        out.append(AUTO_NO_STEWARD)
    for g in stew:
        out.append(f"- [{g.get('at')}] {g.get('author')}: {g.get('text')}")
    out.append("")

    # ## Harness and ## Output are the engine SPEAKING rather than reporting. Everything above
    # is what the run has learned; these two are what the worker has to do, and they are here
    # because a run died when they were only in someone's memory of `crux auto guide`.
    h = p.get("harness") or {}
    out += ["## Harness", "",
            f"You are in a throwaway git checkout of the repository, and it is yours. Edit it,",
            f"run it, and COMMIT your work there — the commit is the attempt, and an attempt",
            f"with no commit is discarded. Committing here is authorized even where a standing",
            f"rule tells you not to commit: this checkout is not the PI's branch and is thrown",
            f"away after the driver has read it.", "",
            f"Your own directory for anything bigger than a commit is `$CRUX_WORKSPACE`.",
            f"`$CRUX_WORKTREE` is the checkout; `$CRUX_PROPOSAL` is the file named below.",
            f"Other attempts are running beside you and share {h.get('shared')}. Your own",
            f"workspace under any of those is yours; another attempt's files there are not,",
            f"and touching them voids your attempt.", "",
            f"The driver — not you — scores your commit by running, in the checkout:", "",
            f"    {h.get('scorer')}", "",
            f"Run that yourself to see where you stand. It is also the interpreter and the",
            f"entry point this project is known to work under, so prefer it to any other one",
            f"you might reach for; an interpreter the plan does not name may not be installed.",
            f"Do NOT write `{RESULTS_DIR}/` — the driver writes the score, from that command's",
            f"own output, and a number you write there is not evidence. Do not touch",
            f"{h.get('frozen')}: a commit that does voids the attempt outright.", ""]

    sch = p.get("schema") or {}
    tgt = list(sch.get("claim_target") or AUTO_CLAIM_TARGET)
    out += ["## Output", "",
            f"Write ONE JSON object to `$CRUX_PROPOSAL` with exactly these keys:", "",
            f"- `claim`: what you changed and why you expected it to help. HARD LIMIT "
            f"{sch.get('claim_words')} words —",
            f"  a claim over it costs the whole attempt, after all the work is done, and no",
            f"  retry gets that work back. Aim at {tgt[0]}–{tgt[1]} words and you will never",
            f"  be near it. Put NO tables, NO per-case or per-country numbers, NO ablation",
            f"  sweeps and NO code in there: the driver reads every number from the scorer and",
            f"  not one from this file, so detail here buys nothing and can cost everything.",
            f"  What changed, and why you thought it would help. That is all it is for.",
            f"- `controls`: a list — possibly empty — of "
            f"{{{', '.join(f'`{k}`' for k in sch.get('control_keys') or [])}}} objects.", "",
            f"Every `text` must BEGIN with a metric comparison — `<key.path> <op> <number>`,",
            f"with `<op>` one of {', '.join(sch.get('ops') or [])} — and may carry prose after",
            f"it. A control points whichever way you mean it to — the example below borrows",
            f"the objective's own operator only so it reads as something rather than nothing:",
            "",
            f"    {{\"text\": \"{h.get('address')} {h.get('op')} {obj.get('bar')} — "
            f"measured on three seeds\",",
            f"     \"fails_if\": \"the value moves with the seed rather than with the change\"}}",
            "",
            f"A control that is prose alone is DROPPED, not refused, and so is a key outside",
            f"the two above — the attempt is still scored and still gets a verdict. Your",
            f"commit is measured either way; what a missing or over-cap `claim` costs is the",
            f"VERDICT, because a verdict is a judgment about a hypothesis and an attempt that",
            f"stated none has nothing to judge. The work survives; the answer does not.",
            f"Do not name a verdict and do not tag a control with a kind; both are the",
            f"driver's.", ""]

    b = (p.get("budget") or {}).get("attempts") or {}
    out += ["## Budget", "",
            f"attempts: {b.get('used')} of {b.get('total')} used, "
            f"{b.get('remaining')} remaining"]
    cut = p.get("cut") or []
    if cut:
        out += ["", f"{AUTO_CUT_PREFIX} " + "; ".join(cut)]
    return "\n".join(out).rstrip() + "\n"


# ------------------------------------------------- 05.3: the closer, the report, the steward
# `crux-close` is reused BYTE-UNCHANGED. Everything that makes it usable headlessly is here,
# in the brief: the schema it must answer in, where its workspace is, and which ticks the
# scorer has already settled. The agent definition is not edited, because an agent the PI
# reads and an agent the driver runs have to be the same agent.

def auto_close_brief(root, hid, plan, ticks):
    """The payload `crux-close` is handed for one finished attempt. A pure read of the vault.

    The anchor's advocacy is excluded by CONSTRUCTION, not by a filter run afterwards: the
    payload reads the attempt, the plan and the scorer's own vector, and never touches the
    anchor at all. `results` is the VAULT-RELATIVE path, so the brief is byte-stable across a
    copy; the absolute path reaches the agent through CRUX_RESULTS."""
    v = Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise CruxError(f"auto close brief is per-attempt (got a '{n.type}' for '{hid}')")
    if len(ticks) != len(plan["checks"]):
        raise CruxError(f"auto close brief: {len(ticks)} ticks for "
                        f"{len(plan['checks'])} checks")
    return {
        "engine_version": ENGINE_VERSION, "mode": "close", "plan": plan["path"],
        "attempt": {"id": hid, "claim": _section(n["body"], "Idea / Hypothesis")},
        "objective": {"address": plan["address"], "direction": plan["direction"],
                      "bar": plan["bar"]},
        "results": f"{RESULTS_DIR}/{hid}/",
        "checks": [{"index": c["index"], "kind": c["kind"], "text": c["text"],
                    "fails_if": c["fails_if"], "discriminates": bool(c["discriminates"]),
                    "graded": ticks[i][0] != "-", "tick": ticks[i][0], "found": ticks[i][1]}
                   for i, c in enumerate(plan["checks"])],
        "rule": plan["rule"], "rule_m": plan["rule_m"], "null": plan["null"],
        "schema": {"keys": list(AUTO_CLOSE_KEYS), "ticks": list(AUTO_TICK_ALPHABET),
                   "findings_words": AUTO_CLOSE_FINDINGS_WORDS,
                   "report_bytes": AUTO_REPORT_BYTES}}


def auto_close_brief_text(payload):
    """The close brief as markdown. Deterministic, and every empty case spoken.

    `## Output` asks for the proposal the agent would print ANYWAY, plus the same proposal as
    one JSON object at `$CRUX_PROPOSAL`. It suppresses nothing: `crux-close` is unchanged, so
    a PI reading the transcript still sees the table it always saw, and the JSON is an
    addition for a driver that has no eyes."""
    p = payload or {}
    att, obj = p.get("attempt") or {}, p.get("objective") or {}
    sch = p.get("schema") or {}
    out = [f"# Close brief — {att.get('id')}  ({p.get('plan')})", ""]
    out += ["## Attempt", "", f"{att.get('id')} — {att.get('claim')}", ""]
    out += ["## Objective", "",
            f"{obj.get('address')} · {obj.get('direction')} · bar {obj.get('bar')}", ""]
    out += ["## Results", "",
            f"{p.get('results')}   (the absolute path is in CRUX_RESULTS)", ""]
    out += ["## Checks", ""]
    rule_line = f"rule: {p.get('rule')}"
    if p.get("rule_m") is not None:
        rule_line += f" (m={p.get('rule_m')})"
    out.append(rule_line)
    out.append(f"null: {p.get('null') or '—'}")
    for c in p.get("checks") or []:
        out.append(f"- {c.get('index')} [{c.get('kind')}] {c.get('text')}")
        if c.get("fails_if"):
            out.append(f"      fails-if:: {c['fails_if']}")
        if c.get("discriminates"):
            out.append("      discriminates:: true")
        if c.get("graded"):
            out.append(f"      graded by the scorer: [{c.get('tick')}]  "
                       f"(found: {c.get('found')})")
        else:
            out.append("      not graded — this one is the reader's")
    out.append("")
    out += ["## Output", "",
            "Write the same proposal you would print — the table of (verifiable, proposed "
            "tick, the",
            "evidence), the outcome-neutral result, and the findings draft —",
            # This clause stays on ONE line: it is the whole contract with a REUSED agent —
            # the brief adds an output and replaces nothing — and a reader who greps for it
            # must find it whole.
            "**and also write that same proposal as one JSON object to `$CRUX_PROPOSAL`**, "
            "with", "exactly these keys:", "",
            "- `ticks`: an object keyed by check index (1-based, the order above), each value "
            "one of", "  `\"x\"` (met), `\" \"` (unmet) or `\"-\"` (not evaluable). A check "
            "already graded by the scorer", "  above is the scorer's; proposing a different "
            "tick for one refuses the whole proposal.",
            f"- `findings`: the findings paragraph, at most {sch.get('findings_words')} "
            f"words.",
            f"- `report`: the markdown of the run report, at most {sch.get('report_bytes')} "
            f"bytes.", "",
            "Any other key refuses the proposal. There is no verdict field: the verdict is "
            "derived."]
    return "\n".join(out).rstrip() + "\n"


def auto_close_proposal(raw, plan, ticks):
    """`{ok, reason, detail, ticks, findings, report}` for one `close.json`.

    NOTHING here is retried. A closer that ran and answered badly has made its own act, and
    the same agent handed the same brief would repeat it — so the attempt closes on the
    engine's own vector instead, which is the honest reading of the evidence on disk.

    First match wins, so one fault is reported once rather than cascading into four."""
    def bad(reason, detail):
        return {"ok": False, "reason": reason, "detail": detail,
                "ticks": {}, "findings": None, "report": None}

    if raw is None:
        return bad("closer-missing", "the closer left no close.json in its workspace")
    try:
        obj = json.loads(raw)
    except ValueError as e:
        return bad("closer-unparseable", f"close.json is not one JSON object ({e})")
    if not isinstance(obj, dict):
        return bad("closer-unparseable",
                   f"close.json is not one JSON object (got {type(obj).__name__})")
    extra = set(obj) - set(AUTO_CLOSE_KEYS)
    if extra:
        return bad("closer-schema", f"close.json carries keys outside "
                                    f"{', '.join(AUTO_CLOSE_KEYS)}: "
                                    f"{', '.join(sorted(extra))}")
    if not isinstance(obj.get("ticks"), dict):
        return bad("closer-schema", "close.json ticks is not an object keyed by check index")
    for k in sorted(obj["ticks"], key=lambda x: str(x)):
        if re.fullmatch(r"[1-9]\d*", str(k)) is None or int(k) > len(plan["checks"]):
            return bad("closer-schema", f"close.json ticks name no check: {k}")
        if obj["ticks"][k] not in AUTO_TICK_ALPHABET:
            return bad("closer-schema", f"close.json tick for check {int(k)} is not one of "
                                        f"'x', ' ', '-' (got {obj['ticks'][k]!r})")
    # The contradiction. A number the scorer read out of a metrics document is not a matter of
    # opinion, and a reporter that overrules it is refused whole rather than partly believed.
    for i in range(1, len(ticks) + 1):
        if ticks[i - 1][0] == "-":
            continue
        for k in obj["ticks"]:
            if int(k) == i and obj["ticks"][k] != ticks[i - 1][0]:
                return bad("closer-contradiction",
                           f"close.json ticks check {i} '{obj['ticks'][k]}' where the "
                           f"scorer's number grades it '{ticks[i - 1][0]}' "
                           f"(found: {ticks[i - 1][1]})")
    if not isinstance(obj.get("findings"), str) or not obj["findings"].strip():
        return bad("closer-schema", "close.json carries no findings")
    n = len(_prose_tokens(obj["findings"]))
    if n > AUTO_CLOSE_FINDINGS_WORDS:
        return bad("closer-findings",
                   f"the findings run to {n} words, over the "
                   f"{AUTO_CLOSE_FINDINGS_WORDS}-word cap")
    if not isinstance(obj.get("report"), str) or not obj["report"].strip():
        return bad("closer-schema", "close.json carries no report")
    return {"ok": True, "reason": None, "detail": None,
            "ticks": {int(k): v for k, v in obj["ticks"].items()},
            "findings": obj["findings"].strip(),
            "report": obj["report"].strip()[:AUTO_REPORT_BYTES]}


def auto_merge_ticks(ticks, proposed):
    """The engine's vector with the closer's proposal filled into the gaps it left. Total.

    A check the scorer graded keeps the SCORER's pair verbatim — an agreeing proposal is
    ignored rather than applied, so nothing a model wrote can reach a tick a number already
    settled. Only a `[-]` is the reader's to fill."""
    out = []
    for i, pair in enumerate(ticks, 1):
        if pair[0] != "-":
            out.append(pair)
        elif i in (proposed or {}):
            out.append((proposed[i], "graded by crux-close"))
        else:
            out.append(pair)
    return out


def auto_report_text(plan, hid, value, ticks, failure=None):
    """The run report when no closer wrote one. A fixed template, so two runs of the same
    attempt read the same. It lives under `results/`, so it does not count against
    `PROSE_CAP` — the findings paragraph is the part that sits in the node body."""
    lines = [f"# Attempt {hid}", "",
             f"Objective {plan['address']} = {repr(value) if value is not None else 'n/a'} "
             f"(direction {plan['direction']}, bar {plan['bar']:g}).", "",
             "## Checks", ""]
    for i, (tick, found) in enumerate(ticks, 1):
        word = {"x": "met", " ": "unmet", "-": "n/a"}[tick]
        lines.append(f"- [{tick}] check {i}: {word}, found {found}.")
    if failure:
        lines += ["", "## Failure", "", " ".join(str(failure).split())[:2000] + "."]
    return "\n".join(lines).rstrip() + "\n"


def auto_link_report(root, hid, rel):
    """Link `rel` under one hypothesis' `## Artifacts`. Returns the bullet line.

    `append_guidance`'s idiom, applied to a node: every byte through the heading line is
    untouched, the template's own `_(placeholder)_` goes only when it is all the section
    holds, and an HTML-comment block survives. Idempotent — a section that already links
    this path is not rewritten at all, which is what makes a resumed close a no-op.

    No `refresh`, no `updated:` bump and no `lock_hash` change: a link to a file the run
    produced is not an edit to the commitment the PI signed."""
    v = Vault(root)
    n = v.get(hid)
    if n.type != "idea":
        raise CruxError(f"auto link report applies to a hypothesis "
                        f"(got a '{n.type}' for '{hid}')")
    rel = str(rel).replace(os.sep, "/")
    for a in parse_artifacts(n["body"]):
        if a["path"] == rel:
            return f"- [Report]({rel})"
    lines = n["body"].split("\n")
    start = next((i for i, l in enumerate(lines)
                  if l.startswith("## ") and l[3:].strip().lower() == "artifacts"), None)
    if start is None:
        raise CruxError(f"{hid} has no ## Artifacts section to link into")
    end = next((j for j in range(start + 1, len(lines)) if lines[j].startswith("## ")),
               len(lines))
    seg = lines[start + 1:end]
    content = [l for l in seg if l.strip() and not l.lstrip().startswith("<!--")
               and "-->" not in l]
    if content and all(_PLACEHOLDER.match(l) for l in content):
        seg = [l for l in seg if not _PLACEHOLDER.match(l)]
    while seg and not seg[-1].strip():
        seg.pop()
    if not seg or seg[0].strip():
        seg.insert(0, "")
    entry = f"- [Report]({rel})"
    seg.append(entry)
    write_if_changed(n["path"],
                     render_doc(n["fm"], "\n".join(lines[:start + 1] + seg + [""]
                                                   + lines[end:])))
    return entry


# The steward. It reads the RUN's own record — the ledger, the island table, the budget — and
# nothing from any node body except a title and a score. That is the whole leakage rule: an
# agent that could read an island's findings would be proposing the angle the findings argue
# for, which is the one thing a fresh angle must not be.

def auto_steward_brief(root, plan, state, events):
    """The payload `crux-auto-steward` is handed once per invocation. Byte-stable over
    unchanged run state: no timestamp of its own, every list order defined.

    `events` is the ledger objects the DRIVER already read, oldest first — the engine never
    reads `ledger.jsonl`, because the engine never reads a file the driver owns."""
    v = Vault(root)
    cut = []

    def score_of(nid):
        if not nid:
            return None
        try:
            return {"value": float(resolve_address(root, f"{nid}#{plan['address']}")["value"]),
                    "addr": f"{nid}#{plan['address']}"}
        except (CruxError, TypeError, ValueError):
            return None

    closed = list(state.get("closed") or [])
    islands = []
    for i, rec in (state.get("islands") or {}).items():
        nd = v.nodes.get(i)
        attempts = sum(1 for h in closed
                       if h in v.nodes and v.nodes[h].parent == i)
        islands.append({"id": i, "title": nd.title if nd is not None else i,
                        "best": {"id": rec.get("best"), "score": score_of(rec.get("best"))},
                        "stall": rec.get("stall"), "attempts": attempts})

    evs = list(events or [])
    keep = AUTO_BRIEF_BUDGET["ledger"]
    if len(evs) > keep:
        cut.append(f"ledger: kept {keep} of {len(evs)} events (newest)")
        evs = evs[-keep:]

    budget = {}
    for axis in AUTO_BUDGET_AXES:
        rec = ((state.get("budget") or {}).get(axis) or {})
        u, t = rec.get("used") or 0, rec.get("total") or 0
        budget[axis] = {"used": u, "total": t, "remaining": max(t - u, 0)}

    anchor = plan["anchor"]
    an = v.nodes.get(anchor)
    payload = {
        "engine_version": ENGINE_VERSION, "mode": "steward", "plan": plan["path"],
        "anchor": {"id": anchor, "title": an.title if an is not None else anchor},
        "goal": plan.get("goal") or "",
        "objective": {"address": plan["address"], "direction": plan["direction"],
                      "bar": plan["bar"]},
        "islands": islands,
        "island_cap": plan["island_cap"],
        "islands_open": len(state.get("islands") or {}),
        "ledger": evs,
        "guidance": list(plan.get("guidance") or []),
        "steward_guidance": list((state.get("steward") or {}).get("guidance") or []),
        "budget": budget,
        "schema": {"keys": list(AUTO_STEWARD_KEYS), "island": list(AUTO_ISLAND_KEYS),
                   "title_words": AUTO_TITLE_WORDS, "problem_words": PROSE_CAP},
        "cut": cut,
    }
    # The same schema check the worker brief runs, over the steward's own slot list: a brief
    # is never returned half-assembled, because an agent told less than the contract says it
    # gets would be proposing in the dark.
    for slot in AUTO_STEWARD_SLOTS:
        val = payload
        for part in slot.split("."):
            val = val.get(part) if isinstance(val, dict) else None
        if val is None or val == "" or val == [] or val == {}:
            raise CruxError(f"auto steward brief: required slot '{slot}' is absent or empty")
    return payload


def auto_steward_brief_text(payload):
    """The steward brief as markdown. Every section present even when empty, so an absence
    reads as an absence rather than as a section the assembler forgot."""
    p = payload or {}
    obj = p.get("objective") or {}
    anc = p.get("anchor") or {}
    sch = p.get("schema") or {}
    out = [f"# Steward brief — {anc.get('id')}  ({p.get('plan')})", ""]
    out += ["## Goal", "", p.get("goal") or "—", ""]
    out += ["## Objective", "",
            f"{obj.get('address')} · {obj.get('direction')} · bar {obj.get('bar')}", ""]
    out += ["## Islands", ""]
    out.append(f"{p.get('islands_open')} open, island_cap {p.get('island_cap')}")
    for i in p.get("islands") or []:
        b = i.get("best") or {}
        s = b.get("score") or {}
        out.append(f"- {i.get('id')} — {i.get('title')} · best {b.get('id')} = "
                   f"{s.get('value')} · stall {i.get('stall')} · "
                   f"{i.get('attempts')} attempt(s)")
    out.append("")
    out += ["## Budget", ""]
    for axis in AUTO_BUDGET_AXES:
        b = (p.get("budget") or {}).get(axis) or {}
        out.append(f"{axis}: {b.get('used')} of {b.get('total')} used, "
                   f"{b.get('remaining')} remaining")
    out.append("")
    out += ["## The PI's guidance", ""]
    guid = p.get("guidance") or []
    if not guid:
        out.append(AUTO_NO_GUIDANCE)
    for g in guid:
        out.append(f"- [{g.get('at')}] {g.get('author')}: {g.get('text')}")
    out.append("")
    out += ["## Earlier steward guidance", ""]
    sg = p.get("steward_guidance") or []
    if not sg:
        out.append(AUTO_NO_STEWARD)
    for g in sg:
        out.append(f"- [{g.get('at')}] {g.get('author')}: {g.get('text')}")
    out.append("")
    out += ["## Ledger", ""]
    for e in p.get("ledger") or []:
        rest = {k: val for k, val in (e or {}).items() if k not in ("at", "event")}
        out.append(f"- {(e or {}).get('at')} {(e or {}).get('event')} "
                   f"{json.dumps(rest, sort_keys=True, ensure_ascii=False)}")
    cut = p.get("cut") or []
    if cut:
        out += ["", f"{AUTO_CUT_PREFIX} " + "; ".join(cut)]
    out.append("")
    out += ["## Output", "",
            "Write one JSON object to `$CRUX_PROPOSAL`, with at most these keys and at least "
            "one of", "them:", "",
            f"- `guidance`: one standing instruction for every later attempt, at most "
            f"{sch.get('problem_words')} words.",
            f"- `island`: a NEW sub-question under the anchor, as an object with exactly "
            f"`title` (at most", f"  {sch.get('title_words')} words) and `problem` (at most "
            f"{sch.get('problem_words')} words). Refused at `island_cap` "
            f"{p.get('island_cap')},",
            f"  and {p.get('islands_open')} are open already.", "",
            "Any other key refuses the proposal. The objective, the bar and the checks are "
            "frozen and", "are not the steward's to touch; a verdict is derived and is not "
            "anybody's to propose."]
    return "\n".join(out).rstrip() + "\n"


def auto_steward_proposal(raw, plan, state):
    """`{ok, reason, detail, guidance, island}` for one steward `proposal.json`.

    A steward NEVER stops a run: every branch below is advice the driver logs and carries on
    past. A run that dies for want of advice is worse than a run without it."""
    def bad(reason, detail):
        return {"ok": False, "reason": reason, "detail": detail,
                "guidance": None, "island": None}

    if raw is None:
        return bad("steward-missing", "the steward left no proposal.json in its workspace")
    try:
        obj = json.loads(raw)
    except ValueError as e:
        return bad("steward-unparseable", f"proposal.json is not one JSON object ({e})")
    if not isinstance(obj, dict):
        return bad("steward-unparseable",
                   f"proposal.json is not one JSON object (got {type(obj).__name__})")
    extra = set(obj) - set(AUTO_STEWARD_KEYS)
    if extra:
        return bad("steward-schema", f"proposal.json carries keys outside "
                                     f"{', '.join(AUTO_STEWARD_KEYS)}: "
                                     f"{', '.join(sorted(extra))}")
    g, isl = obj.get("guidance"), obj.get("island")
    if g is None and isl is None:
        return bad("steward-empty", "proposal.json proposes neither guidance nor an island")
    if g is not None:
        if not isinstance(g, str) or not g.strip():
            return bad("steward-schema", "proposal.json guidance is not a non-empty string")
        n = len(_prose_tokens(g))
        if n > PROSE_CAP:
            return bad("steward-schema",
                       f"the guidance runs to {n} words, over the {PROSE_CAP}-word cap")
    if isl is not None:
        if (not isinstance(isl, dict) or set(isl) != set(AUTO_ISLAND_KEYS)
                or not all(isinstance(isl.get(k), str) and isl.get(k).strip()
                           for k in AUTO_ISLAND_KEYS)):
            return bad("steward-schema", "proposal.json island must be an object with "
                                         "exactly title and problem, both non-empty strings")
        n = len(_prose_tokens(isl["title"]))
        if n > AUTO_TITLE_WORDS:
            return bad("steward-schema", f"the island title runs to {n} words, over the "
                                         f"{AUTO_TITLE_WORDS}-word cap")
        n = len(_prose_tokens(isl["problem"]))
        if n > PROSE_CAP:
            return bad("steward-schema", f"the island problem statement runs to {n} words, "
                                         f"over the {PROSE_CAP}-word cap")
        if len(state.get("islands") or {}) >= plan["island_cap"]:
            return bad("steward-cap", f"the run already holds "
                                      f"{len(state.get('islands') or {})} islands, at "
                                      f"island_cap {plan['island_cap']}")
    return {"ok": True, "reason": None, "detail": None,
            "guidance": " ".join(g.split()) if g is not None else None,
            "island": ({"title": " ".join(isl["title"].split()),
                        "problem": " ".join(isl["problem"].split())}
                       if isl is not None else None)}
