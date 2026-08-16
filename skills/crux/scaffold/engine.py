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
import os, re, sys, json, html, datetime, tempfile, shutil, hashlib

# ----------------------------------------------------------------------------- constants
ENGINE_VERSION = "2.8"          # bumped when verdict/roll-up/view logic or vault format changes; stamped into every vault
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
CRUX_VERSION = "0.5.1"          # the RELEASE version (what ships / what the update check compares); independent of the vault format
VAULT_MARKER = ".crux.yaml"
LEDGER_START = "<!-- crux:ledger:start -->"
LEDGER_END   = "<!-- crux:ledger:end -->"

# wiki layer (Epic 3): a PI-curated literature wiki alongside the q/h tree.
WIKI_DIR     = "wiki"           # agent-owned compiled markdown pages + log.md + SCHEMA.md
RAW_DIR      = "raw"            # immutable, PI-curated sources; the engine hashes bytes, never reads content
WIKI_INDEX   = "WIKI.md"        # generated index of wiki pages (Karpathy's index.md), rendered at vault root
SOURCES_FILE = os.path.join(WIKI_DIR, ".sources.tsv")   # engine-owned source registry: sha256<TAB>date<TAB>path<TAB>title
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
INFO_NAMESPACES = ("boundary", "task", "agents")  # <namespace>:<slug>; spec 14 claims its own next

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
CHECKS     = ("tree", "wiki", "economy", "fanout", "rd", "tasks")
OPT_CHECKS = ("decks", "gate")
PRESENTATIONS_DIR = "presentations"     # derived decks live here; never evidence, never
                                        # linked from `## Artifacts`

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
    return (f"engine drift: this vault was written with crux engine v{stamped}, "
            f"but you are running v{ENGINE_VERSION}. Verdicts and generated views may "
            f"differ. Pin the matching engine (re-install the crux skill at v{stamped}) "
            f"if you need to reproduce the recorded results exactly.")

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

def ensure_glossary(root):
    """Create `glossary.md` from the template if it is absent. Called at `init`, and by the
    PI's own accept/decline — never by a read path, so an existing vault gains the file only
    when the PI has actually said something."""
    p = glossary_path(root)
    if not os.path.isfile(p):
        write_if_changed(p, load_template("glossary"))
    return p

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
            if len(parts) >= 4:
                reg[parts[2]] = {"sha256": parts[0], "date": parts[1], "title": "\t".join(parts[3:])}
    return reg

def save_sources(root, reg):
    lines = [f"{r['sha256']}\t{r['date']}\t{rel}\t{r['title']}" for rel, r in sorted(reg.items())]
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

def cmd_ingest(root, path, title=None):
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
    title = " ".join((title or os.path.splitext(os.path.basename(abspath))[0]).split())  # single-line: registry + log are line-based
    reg = load_sources(root)
    if rel in reg and reg[rel]["sha256"] == sha:
        refresh(root)
        return "unchanged", rel
    state = "updated" if rel in reg else "ingested"
    reg[rel] = {"sha256": sha, "date": datetime.date.today().isoformat(), "title": title}
    save_sources(root, reg)
    with open(os.path.join(root, WIKI_LOG), "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.date.today().isoformat()}] ingest | {title}\n")
    refresh(root)
    return state, rel

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
                    rule=None, rule_m=None, null=None, fails_if=None, discriminates=None):
    """Returns (id, filename, warning). The third element is fan-out back-pressure — None
    when the parent question has room, a message when this hypothesis puts it over
    FANOUT_MAX. Never a refusal: proposing is cheap and sometimes right, so crux says the
    number out loud and lets the PI decide."""
    v = Vault(root)
    p = v.get(parent)
    if p.type != "question":
        raise CruxError("a hypothesis must hang under a question (use `ask` first)")
    warning = fanout_pressure(v, parent)
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

def cmd_close(root, nid, metric=None, findings=None):
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

def validation_report(root, checks=None):
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
    if "tree"    in names: problems += validate(v); info += boundary_info(v)
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
    return {"ok": not problems and not warnings,     # `info` is deliberately NOT in `ok`
            "checks": list(names),
            "problems": [{"id": i, "message": m} for i, m in problems],
            "warnings": [{"id": i, "message": m} for i, m in warnings],
            "info": [dict({"id": i, "message": m}, **({"count": c} if c is not None else {}))
                     for i, m, c in info]}

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

def brief(root, hid):
    """The deterministic cold input for an isolated agent. Pure read; byte-stable."""
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
