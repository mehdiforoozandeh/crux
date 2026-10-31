#!/usr/bin/env python3
"""Agent evals for crux — spec 10.

`selftest.py` asserts that the ENGINE is right. This asserts that the AGENTS are, and it does
so without ever running one.

    python evals.py --certify-all
    python evals.py --fixture capture-01 --submission runs.json [--json]
    python evals.py --fixture capture-01 --yield <vault after a capture run>

## The shape, and why it is this shape

Spec 10 asks for a harness that invokes a model K times and bands the distribution. That is,
item for item, spec 05's three unbuilt work items — a Runner, a Budget & stop, and an autonomy
envelope — pointed at a fixture instead of at a hypothesis. `.spec/README.md` says **"Do not
implement 05."** The loop is the risk, not the target.

So the harness **never invokes an agent**. It scores a *submitted* findings file: whoever ran
the agent — the PI, attended, in a chat session — writes the ids it reported to a JSON file, and
this module does set arithmetic against a hand-authored manifest. Everything spec 10 measures is
still measured. The model-invoking runner is PARKED, not flagged off: there is no `--spawn`, and
this module has no network import and no subprocess that is not `crux.py`, which
`selftest.run_agent_evals` asserts by reading this file's own source.

## Ground truth, and how it is kept true

A fixture is only ground truth if something other than the agent says what is in it. So:

  - the manifest (`PLANTED.md`) is hand-authored and reviewed;
  - `certify()` proves the manifest true by asking the engine. For capture-01 that is
    `capture_keys` over the vault before and after a reference capture, compared to the
    planted id set exactly; the other oracles read the engine's own vocabulary or payload.

A fixture that drifts from its manifest goes red in `selftest` immediately, and no eval ever
grades against a stale ground truth. That is spec 10's anti-tautology rule made mechanical
rather than promised.

The key is **a structural fact the engine reads** — a yield key (`open:question`,
`parked:h1`), a confound family, a payload id. Nobody matches a message. A fixture plants at
most one row per id.
"""
import os, re, sys, json, hashlib, argparse

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

FIXTURES = os.path.join(os.path.dirname(HERE), "evals", "fixtures")

#: every manifest declares these. `oracle` names the engine function that certifies it;
#: `band` is the PI's pre-registered bar and ships `unset` until they have seen a distribution.
MANIFEST_FIELDS = ("fixture", "agent", "ground_truth", "oracle", "checks", "band", "k")

GROUND_TRUTH_VALUES = ("yes", "proxy")
BAND_UNSET = "unset"


# ----------------------------------------------------------------------------- manifests
def fixture_names(root=None):
    """Every fixture directory, sorted. A directory without a PLANTED.md is not a fixture."""
    root = root or FIXTURES
    if not os.path.isdir(root):
        return []
    return sorted(n for n in os.listdir(root)
                  if os.path.isfile(os.path.join(root, n, "PLANTED.md")))


def _csv(val):
    """`a, b, c` -> ['a','b','c']. The house idiom for a list in a flat-scalar frontmatter —
    the same one `sources:` and `refs:` already use, so no second YAML dialect appears."""
    return [x.strip() for x in str(val or "").split(",") if x.strip()]


def _table(body, heading):
    """Rows of the first markdown table under `## <heading>`, as lists of stripped cells.

    The header row and the `|---|` rule are dropped. Pure — no filesystem access."""
    rows, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("#"):
            # any heading level: a register may legitimately sit under a `###`
            in_sec = line.lstrip("#").strip().lower() == heading.lower()
            continue
        if not in_sec:
            continue
        s = line.strip()
        if not s.startswith("|"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            rows = []                      # the rule line: everything before it was the header
            continue
        rows.append(cells)
    return rows


def load_manifest(name, root=None):
    """Parse one fixture's PLANTED.md. Raises CruxError on anything malformed, because a
    manifest the harness cannot read is a ground truth nobody can check."""
    root = root or FIXTURES
    path = os.path.join(root, name, "PLANTED.md")
    if not os.path.isfile(path):
        raise E.CruxError(f"fixture '{name}': no PLANTED.md at {path}")
    fm, body = E.parse_doc(E.read(path))
    missing = [k for k in MANIFEST_FIELDS if fm.get(k) in (None, "")]
    if missing:
        raise E.CruxError(f"fixture '{name}': manifest is missing {', '.join(missing)}")
    if str(fm["ground_truth"]) not in GROUND_TRUTH_VALUES:
        raise E.CruxError(f"fixture '{name}': ground_truth must be one of "
                          f"{'/'.join(GROUND_TRUTH_VALUES)}, got '{fm['ground_truth']}'")
    planted = []
    for r in _table(body, "Planted"):
        if len(r) < 3:
            raise E.CruxError(f"fixture '{name}': planted row needs id | tier | class: {r}")
        planted.append({"id": r[0].strip("`"), "tier": r[1], "class": r[2],
                        "note": r[3] if len(r) > 3 else ""})
    if not planted:
        raise E.CruxError(f"fixture '{name}': no planted defects in the manifest")
    ids = [p["id"] for p in planted]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        # the constraint that buys exact scoring with no engine change: the id IS the key
        raise E.CruxError(f"fixture '{name}': two defects planted on one id ({', '.join(dup)}) "
                          f"— plant them in two nodes instead")
    return {"name": name, "dir": os.path.join(root, name), "fm": fm, "body": body,
            "agent": str(fm["agent"]), "ground_truth": str(fm["ground_truth"]),
            "oracle": str(fm["oracle"]), "checks": tuple(_csv(fm["checks"])),
            "band": str(fm["band"]), "k": int(fm["k"]), "planted": planted,
            "planted_ids": set(ids)}


def repo_root():
    return os.path.dirname(os.path.dirname(os.path.dirname(HERE)))


def vault_of(manifest):
    """The vault a fixture is graded over.

    Normally the fixture's own `vault/`. A manifest may instead declare
    `example_vault: <name>` and be graded over a SHIPPED example vault — spec 16's persona
    eval does, because "the agent converses over one of the shipped example problems" is the
    fixture's premise, and a copy would drift away from the thing it claims to be. Read-only
    either way: nothing in this module writes to a vault."""
    ex = str(manifest["fm"].get("example_vault") or "").strip()
    if ex:
        return os.path.join(repo_root(), "skills", "crux", "examples", ex)
    return os.path.join(manifest["dir"], "vault")


# ----------------------------------------------------------------------------- certification
#: Words too common to tell two research questions apart. The duplicate test compares what is
#: left, so "Does X change Y?" and "Does X affect Y?" collide and two different questions don't.
_DUP_STOP = frozenset("does that this with from than what when which have more less into "
                      "over under about there their they them were been being will would "
                      "should could after before same".split())
#: Two titles whose content words overlap at least this much (Jaccard) ask the same thing.
DUP_OVERLAP = 0.5


def _content_words(text):
    return {w for w in re.findall(r"[a-z]+", str(text or "").lower())
            if len(w) >= 4 and w not in _DUP_STOP}


def _same_question(a, b):
    wa, wb = _content_words(a), _content_words(b)
    return bool(wa and wb) and len(wa & wb) / len(wa | wb) >= DUP_OVERLAP


def capture_keys(start, after, work_markers=()):
    """What a capture run did to a vault, as yield keys: a pure function of the vault BEFORE
    the run and the vault AFTER it, read through the engine. Nothing is matched on prose a
    model wrote; every key is a structural fact.

      open:question            it opened a question
      open:hypothesis+expect   it opened a hypothesis that states an expectation
      open:hypothesis-bare     ... or one that does not (the 4.0 model requires it)
      finding:evidence         it recorded a finding whose evidence resolves
      finding:no-evidence      ... or one with none
      finding:<confidence>     the confidence each new finding counts with (null cap applied)
      finding:null-open        a hypothesis finding that records its null as not ruled out
      parked:<id>              it parked a node that existed before the run
      duplicate:<id>           it opened a second node for a question or hypothesis that
                               already existed (`new` when two new nodes duplicate each other)
      work-in-tree             it opened a node for work: a manifest-declared work marker
                               appears in a new node's title or prose
      removed:<id>             a node that existed before the run is gone

    The first five kinds are what a correct capture yields; the rest are what a careless one
    does, so a fixture scores both missed records and invented ones."""
    s, a = E.Vault(start), E.Vault(after)
    keys = set()
    keys |= {f"removed:{i}" for i in s.nodes if i not in a.nodes}
    olds = [n for n in s.nodes.values() if n.type in ("question", "idea")]
    new = [n for i, n in sorted(a.nodes.items()) if i not in s.nodes]
    nodes = [n for n in new if n.type in ("question", "idea")]
    for n in nodes:
        if n.type == "question":
            keys.add("open:question")
        else:
            keys.add("open:hypothesis+expect" if E.expect_text(n) else "open:hypothesis-bare")
        keys |= {f"duplicate:{o.id}" for o in olds
                 if o.type == n.type and _same_question(o.title, n.title)}
        text = (n.title + "\n" + n["body"]).lower()
        if any(w.lower() in text for w in work_markers):
            keys.add("work-in-tree")
    for i, n in enumerate(nodes):
        if any(o.type == n.type and _same_question(o.title, n.title) for o in nodes[i + 1:]):
            keys.add("duplicate:new")
    for f in (n for n in new if n.type == "finding"):
        ev = E.finding_evidence(f)
        ok = bool(ev) and all(E._evidence_problem(after, x) is None for x in ev)
        keys.add("finding:evidence" if ok else "finding:no-evidence")
        keys.add(f"finding:{E.effective_confidence(f)}")
        if f["fm"].get("null") == E.NULL_NOT_RULED_OUT:
            keys.add("finding:null-open")
    for n in olds:
        if n.id in a.nodes and a.nodes[n.id]["fm"].get(E.PARKED_FIELD) is True \
                and n["fm"].get(E.PARKED_FIELD) is not True:
            keys.add(f"parked:{n.id}")
    return keys


def capture_prose(start, after):
    """Every sentence a capture run wrote into the record: new titles, expectations, nulls,
    and each finding's why, answer and comparison. This is what the invisible-notebook rule
    is scanned over."""
    s, a = E.Vault(start), E.Vault(after)
    out = []
    for i, n in sorted(a.nodes.items()):
        if i in s.nodes:
            continue
        out.append(n.title)
        if n.type == "idea":
            out += [E.expect_text(n), E._section(n["body"], "Null")]
        if n.type == "finding":
            out += [str(n["fm"].get(k) or "") for k in ("why", "vs_expect")]
            out.append(E._section(n["body"], "Answer"))
    return [t for t in out if str(t).strip()]


def _oracle_capture(m):
    """capture-01: a fixed transcript, the vault before it was captured (`vault/`), and the
    vault a correct capture leaves (`reference/`, written with the ordinary crux verbs). The
    available set is `capture_keys(vault, reference)`, so the ENGINE says what the reference
    yields and the manifest must agree with it exactly, as audit-01 did with validate."""
    start, ref = vault_of(m), os.path.join(m["dir"], "reference")
    markers = _csv(m["fm"].get("work_markers"))
    avail = capture_keys(start, ref, markers)
    tpath = os.path.join(m["dir"], str(m["fm"].get("transcript") or "transcript.txt"))
    transcript = E.read(tpath) if os.path.isfile(tpath) else ""
    sv, rv = E.Vault(start), E.Vault(ref)
    ev = _csv(m["fm"].get("evidence"))
    cross = [
        ("the transcript is a conversation: the PI and the agent both speak",
         "\nPI: " in transcript and "\nAGENT: " in transcript),
        ("the starting vault yields nothing — the fixture does not contain the answer",
         capture_keys(start, start, markers) == set()),
        ("the reference only adds or parks: every earlier node keeps its id and title",
         all(i in rv.nodes and rv.nodes[i].title == n.title for i, n in sv.nodes.items())),
        ("the reference vault validates clean",
         E.validation_report(ref, checks=m["checks"])["problems"] == []),
        (f"every evidence file the transcript names exists before the run ({ev})",
         bool(ev) and all(p in transcript and os.path.exists(os.path.join(start, p))
                          for p in ev)),
        ("every work marker is in the transcript, so the trap is really set",
         bool(markers) and all(w.lower() in transcript.lower() for w in markers)),
        ("the reference capture speaks science — no node id, no crux vocabulary",
         E.voice_lint([("agent", t) for t in capture_prose(start, ref)]) == []),
    ]
    return avail, cross


def _oracle_null(m):
    """null-01: the planted id is the confound FAMILY, from the engine's closed vocabulary.

    A decoy family is declared too — a second, superficially available alternative explanation the
    fixture explicitly rules out. An agent that names it scores recall 0, which is what should
    happen."""
    avail = set(E.CONFOUND_FAMILIES)
    hid = str(m["fm"]["node"])
    n = E.Vault(vault_of(m)).get(hid)
    decoy = str(m["fm"].get("decoy") or "")
    cross = [("exactly one family is planted", len(m["planted_ids"]) == 1),
             (f"the decoy '{decoy}' is a real family and is not the answer",
              decoy in E.CONFOUND_FAMILIES and decoy not in m["planted_ids"]),
             ("the reference null passes the engine's own null check",
              E.null_problem(str(m["fm"]["reference_null"]), E.node_schema(n)) is None),
             ("the fixture's own `## Null` is empty — the agent writes it",
              not (E._null_text(n) or "").strip())]
    return avail, cross


def _oracle_situate(m):
    """situate-01: the payload's own facts, as ids.

    `untested:` and `inflight:` are different facts and the agent's definition says to keep
    them apart — a claim nobody has run and a claim whose run is executing need different next
    moves. `gap:` is a question with no findings on any child, and it is the invention trap:
    the submission must say nothing is settled there rather than narrate around it."""
    anchor = str(m["fm"]["node"])
    root = vault_of(m)
    v = E.Vault(root)
    b = E.brief(root, anchor, mode="situate")
    def descend(qid):
        for k in v.children.get(qid, ()):
            yield v.nodes[k]
            if v.nodes[k].type == "question":
                yield from descend(k)

    avail = {f"untested:{u['id']}" for u in b["untested"]["unrun_ideas"]}
    avail |= {f"inflight:{n.id}" for n in descend(anchor)
              if n.type == "idea" and n.status == "running"}

    def settled(qid):
        """Any hypothesis anywhere under `qid` that carries a finding (the 4.0 record: a
        finding file under it, spec 19). A question with none is
        one where nothing is settled yet, and saying so is the agent's job — filling the hole
        with plausible narrative is the failure a fluent model is most likely to have."""
        for k in v.children.get(qid, ()):
            n = v.nodes[k]
            if n.type == "idea" and E.node_findings(v, k):
                return True
            if n.type == "question" and settled(k):
                return True
        return False

    avail |= {f"gap:{q}" for q in b["untested"]["open_questions"] if not settled(q)}
    ref = _section(m["body"], "Reference answer")
    cross = [("the reference answer lints clean",
              ref.strip() != "" and E.situate_lint(ref, [situate_anchor(m)]) == []),
             # spec 16: the gold answer is what trains hardest, so it is scanned rather than
             # read. An ID-led reference would teach the voice the lint above no longer forces.
             ("the reference answer speaks science — no node id, no crux vocabulary",
              ref.strip() != "" and E.voice_lint([("agent", ref)]) == [])]
    return avail, cross


def situate_anchor(m):
    """`(id, title)` for a situate fixture's anchor, read from the fixture's own vault.

    Spec 16 lets a situate answer name its scope by TITLE or by id, so the oracle has to know
    both. The title comes from vault state rather than from the manifest for the reason every
    other fact here does: a hand-copied title is a second source of truth that can drift."""
    aid = str(m["fm"]["node"])
    return (aid, E.Vault(vault_of(m)).get(aid).title or "")


def _v_evidence_resolves(m):
    """Every path named in the key exists under the fixture. A tick nobody can point at is a
    guess, and a key pointing at a file that is not there cannot catch one."""
    bad = [t for p in m["planted"] for t in re.findall(r"`([\w./-]+\.(?:md|csv|py|txt))`", p["note"])
           if not os.path.isfile(os.path.join(m["dir"], "vault", t))]
    return f"every evidence pointer in the key resolves ({bad})", not bad


def _v_distinct_expected(m):
    """THE anti-tautology check at the value level, and the reason tests-01 is worth having at
    all without executing anything: no expected value in the key may equal what the
    deliberately-broken implementation actually returns. A key that could be satisfied by
    describing the code is a description of the code."""
    wrong = set(_csv(m["fm"].get("wrong_values")))
    clash = sorted(w for p in m["planted"] for w in wrong if w and w in p["note"])
    return f"no key row expects what the broken implementation returns ({clash})", not clash


VERIFICATIONS = {"evidence_resolves": _v_evidence_resolves,
                 "distinct_expected": _v_distinct_expected}


def _oracle_stated_key(m):
    """The PROXY oracle, and its proxy-ness is the whole point.

    Here the engine holds no answer, so the key is **stated** by a human rather than derived:
    available == planted, which means certification cannot catch a wrong key. Spec 10 asks for
    exactly this to be admitted rather than dressed up — *"an eval that overstates its own
    rigour is the same failure mode this whole backlog exists to fix"* — so every fixture using
    this oracle must declare `ground_truth: proxy` and say in its manifest what it fails to
    measure.

    What certification CAN still do is check the fixture's own construction, via the
    `verify:` list. Those are real engine calls: the node the key calls over-cap really is
    over-cap, the term really clears the occurrence floor, no expected value matches the broken
    implementation. They keep the fixture honest without pretending the key is derived."""
    cross = []
    for name in _csv(m["fm"].get("verify")):
        if name not in VERIFICATIONS:
            raise E.CruxError(f"fixture '{m['name']}': unknown verification '{name}' — known "
                              f"are {', '.join(sorted(VERIFICATIONS))}")
        cross.append(VERIFICATIONS[name](m))
    cross.append(("a stated key must be declared a proxy — the engine does not derive it",
                  m["ground_truth"] == "proxy"))
    cross.append(("every planted row says what it is, in the note column",
                  all(p["note"].strip() for p in m["planted"])))
    return set(m["planted_ids"]), cross



# ----------------------------------------------------------------------------- persona (spec 16)
# The one fixture class whose deliverable is a CONVERSATION. Spec 16 asks for grading in
# three layers, cheapest first, and the ordering is the point: the voice rule is regexable,
# so a model must never be the thing that checks it. A property graded by a judge is a
# property that silently stops being checked.
#
#   1. deterministic  `engine.voice_lint` over the agent's turns, honouring the mirror rule
#   2. vault state    the notebook was actually kept, despite the silence
#   3. the judge      soft behaviours only — was the gate phrased as a science question, was
#                     the draft shown, was an out-of-scope gate left alone, was the cockpit
#                     offered. Those are the PLANTED ids, and they are a stated key, so the
#                     fixture declares `ground_truth: proxy` like every other stated key here.
#
# The harness still never invokes an agent. Whoever ran the persona, attended, writes the
# transcript and the captured end state into the submission — the same contract spec 10 set,
# for the same reason: a runner that decides when to stop and caps what it spends is spec
# 05's parked work under another name.

#: the closed predicate vocabulary a manifest's `## Vault state` table may use. Closed on
#: purpose: an open-ended expression language here would be a second engine, and a fixture
#: that can assert anything can assert something wrong without anyone noticing.
STATE_PREDICATES = ("state", "confidence", "direction", "answered", "parked", "task",
                    "pending")


def vault_state(status):
    """The slice of `crux status --json` the state predicates read, and nothing else.

    A projection rather than the whole payload: a submission carrying 30KB of vault JSON per
    run is unreviewable, and every field kept here is one a predicate can name. The 4.0 model
    (spec 19): a node's state and confidence are derived from its findings, `direction` is the
    direction of the finding that sets the state, and a question is answered when a finding on
    it carries answer text."""
    nodes = {}
    for i, n in (status.get("nodes") or {}).items():
        fs = {f.get("id"): f for f in (n.get("findings") or ())}
        lead = fs.get(n.get("state_finding")) or {}
        nodes[i] = {"type": n.get("type"), "state": n.get("state"),
                    "confidence": n.get("confidence"),
                    "direction": lead.get("direction"),
                    "parked": bool(n.get("parked")),
                    "answered": any(str(f.get("answer") or "").strip() for f in fs.values())}
    tasks = {t["id"]: {"status": t.get("status"), "pending_gate": bool(t.get("pending_gate"))}
             for t in ((status.get("tasks") or {}).get("items") or [])}
    return {"nodes": nodes, "tasks": tasks}


def state_rows(m):
    """`[(key, expectation, note)]` from the manifest's `## Vault state` table."""
    out = []
    for r in _table(m["body"], "Vault state"):
        if len(r) < 2:
            raise E.CruxError(f"fixture '{m['name']}': a vault-state row needs key | proves: {r}")
        out.append((r[0].strip("`"), r[1], r[2] if len(r) > 2 else ""))
    return out


def check_state(m, after):
    """Every declared predicate against a captured end state, as `[(key, ok, why)]`."""
    nodes, tasks = (after or {}).get("nodes") or {}, (after or {}).get("tasks") or {}
    out = []
    for key, proves, _n in state_rows(m):
        pred, _, rest = key.partition(":")
        target, _, want = rest.partition("=")
        if pred not in STATE_PREDICATES:
            raise E.CruxError(f"fixture '{m['name']}': unknown state predicate '{pred}' — known "
                              f"are {', '.join(STATE_PREDICATES)}")
        n, t = nodes.get(target) or {}, tasks.get(target) or {}
        got = {"state": n.get("state"), "confidence": n.get("confidence"),
               "direction": n.get("direction"), "answered": n.get("answered"),
               "parked": n.get("parked"), "task": t.get("status"),
               "pending": t.get("pending_gate")}[pred]
        ok = (str(got) == want) if want else bool(got)
        out.append((f"{key} (got {got!r})", ok, proves))
    return out


def transcript_turns(submission):
    """The submitted conversation as `voice_lint` turns. A submission with no transcript is
    not scored clean — it is scored as having said nothing, which is a failure."""
    return [(t.get("speaker"), t.get("text")) for t in (submission.get("transcript") or [])]


def _oracle_persona(m):
    """persona-01: the judge rubric is the key, and the fixture's own construction is checked.

    The planted ids are `judge:*` and nothing else. Everything mechanical about this fixture
    — the voice scan and the state assertions — sits in `hard_checks`, beside the band rather
    than inside it, for the same reason situate's lint does: they are one bit each, and no
    distribution over K runs makes an id leak acceptable."""
    root = vault_of(m)
    v = E.Vault(root)
    cross = [("a judged key must be declared a proxy — no engine derives 'was that phrased "
              "as a science question'", m["ground_truth"] == "proxy"),
             ("every planted row is a judged behaviour, named as one",
              all(p["id"].startswith("judge:") and p["note"].strip() for p in m["planted"])),
             ("the fixture runs over a shipped example vault, not a copy of one",
              bool(str(m["fm"].get("example_vault") or "").strip()) and os.path.isdir(root))]

    # the relevance fixture has to actually plant something irrelevant, and the engine says
    # so rather than the author. Without this the judge is asked whether the agent avoided a
    # trap that was never set.
    anchor = str(m["fm"].get("anchor") or "")
    out_of = _csv(m["fm"].get("out_of_scope"))
    cross.append((f"the conversation's anchor '{anchor}' is a real node", anchor in v.nodes))
    cross.append((f"every id declared out of scope really is, per the engine ({out_of})",
                  bool(out_of) and all(E.gate_relation(v, anchor, i) == "unrelated"
                                       for i in out_of)))
    cross.append(("the state table declares what the notebook must show",
                  len(state_rows(m)) >= 3))
    return set(m["planted_ids"]), cross


ORACLES = {"capture_yield": _oracle_capture,
           "null_vocabulary": _oracle_null,
           "situate_payload": _oracle_situate,
           "persona_voice": _oracle_persona,
           "stated_key": _oracle_stated_key}


def _section(body, heading):
    """The text under `## <heading>`. When the section contains a fenced block, ONLY the fence
    is returned — a committed reference answer is the fence, and the sentences introducing it
    are commentary. Without that rule the commentary counts as a paragraph and the shape check
    fails on the manifest's own prose rather than on the answer."""
    lines, on = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            on = line[3:].strip().lower() == heading.lower()
            continue
        if on:
            lines.append(line)
    fenced, out, inside = [], [], False
    for line in lines:
        if line.strip().startswith("```"):
            inside = not inside
            continue
        (fenced if inside else out).append(line)
    return "\n".join(fenced if fenced else out).strip("\n")


def certify(name, root=None):
    """Prove the manifest true. Read-only; the fixture tree is never written.

    Three ways a hand-authored fixture goes wrong, and all three are caught here:
      missing — a planted id the oracle does not offer (the record was never planted, or
                the engine does not read it the way the manifest claims);
      extra   — an id the oracle offers that nobody planted. For `capture_yield` this is
                fatal: it would score a CORRECT capture as invented. For the fixtures whose
                oracle offers a *menu* (every family in the closed vocabulary), extra is
                expected and is not a failure — what matters there is that no planted id is
                outside the menu.
      band    — `unset` is legal and reported, never silently treated as a pass."""
    m = load_manifest(name, root)
    if m["oracle"] not in ORACLES:
        raise E.CruxError(f"fixture '{name}': unknown oracle '{m['oracle']}' — known oracles "
                          f"are {', '.join(sorted(ORACLES))}")
    avail, cross = ORACLES[m["oracle"]](m)
    exact = m["oracle"] == "capture_yield"
    missing = sorted(m["planted_ids"] - avail)
    extra = sorted(avail - m["planted_ids"]) if exact else []
    failed = [c for c, ok in cross if not ok]
    return {"fixture": name, "agent": m["agent"], "ground_truth": m["ground_truth"],
            "oracle": m["oracle"],
            "ok": not missing and not extra and not failed,
            "missing": missing, "extra": extra, "cross_failed": failed,
            "planted": len(m["planted_ids"]), "band": m["band"],
            "band_set": m["band"] != BAND_UNSET}


def certify_all(root=None):
    """Every fixture's certificate. One whose oracle raises is a failed certificate, named,
    never a traceback that hides the fixtures after it."""
    out = []
    for n in fixture_names(root):
        try:
            out.append(certify(n, root))
        except Exception as e:
            out.append({"fixture": n, "agent": "?", "ground_truth": "?", "oracle": "?",
                        "ok": False, "missing": [], "extra": [],
                        "cross_failed": [f"the oracle raised {type(e).__name__}: {e}"],
                        "planted": 0, "band": BAND_UNSET, "band_set": False})
    return out


# ----------------------------------------------------------------------------- scoring
#: verdicts. UNGRADED is the one that matters: a band nobody has set must never read as a
#: pass, because a bar invented with no measurement behind it is a guess with a decimal point.
PASS, FAIL, UNGRADED, REFUSED = "PASS", "FAIL", "UNGRADED", "REFUSED"


def definition_path(agent, repo=None):
    """Where an agent's definition lives. The research roster is `agents/<name>/AGENT.md`;
    `crux-tests` builds crux rather than research, so it lives with evolve-crux (spec 19,
    Q12); and a fixture may grade the ORCHESTRATING skill rather than an agent — spec 16's
    persona eval measures the voice rules, which live in the skill. None when nothing exists."""
    repo = repo or repo_root()
    for p in (os.path.join(repo, "agents", agent, "AGENT.md"),
              os.path.join(repo, "skills", "evolve-crux", "agents", agent + ".md"),
              os.path.join(repo, "skills", agent, "SKILL.md")):
        if os.path.isfile(p):
            return p
    return None


def agent_sha(agent, repo=None):
    """sha256 of an agent's definition — what pins a submission to the prompt that produced
    it. Without it a score is a number with no provenance, and re-scoring after an edit
    silently compares one agent to a different one."""
    p = definition_path(agent, repo)
    if p is None:
        raise E.CruxError(f"no definition for '{agent}'")
    with open(p, "rb") as f:
        return hashlib.sha256(f.read()).hexdigest()


def parse_band(band):
    """`recall>=0.8, precision>=0.9` -> {'recall': 0.8, 'precision': 0.9}; `unset` -> None."""
    if str(band).strip() == BAND_UNSET:
        return None
    out = {}
    for part in _csv(band):
        m = re.fullmatch(r"(recall|precision)\s*>=\s*([01](?:\.\d+)?)", part.strip())
        if not m:
            raise E.CruxError(f"bad band term '{part}' (use `recall>=0.8, precision>=0.9`, "
                              f"or `{BAND_UNSET}`)")
        out[m.group(1)] = float(m.group(2))
    if set(out) != {"recall", "precision"}:
        raise E.CruxError("a band states BOTH recall and precision — recall-only scoring "
                          "teaches an agent to report everything")
    return out


def score_run(planted, reported):
    """One run's precision and recall over id sets, with the tp/fp/fn listed by id so a
    failure is readable rather than a decimal.

    Reporting NOTHING scores precision 0.0, not 1.0 and not an error. An empty report is
    total failure, and the vacuous-truth reading of precision is the one way a scorer can
    hand a perfect mark to an agent that did nothing."""
    planted, reported = set(planted), set(reported)
    tp, fp, fn = planted & reported, reported - planted, planted - reported
    return {"recall": (len(tp) / len(planted)) if planted else 1.0,
            "precision": (len(tp) / len(reported)) if reported else (0.0 if planted else 1.0),
            "tp": sorted(tp), "fp": sorted(fp), "fn": sorted(fn)}


def load_submission(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def score(manifest, submission, repo=None):
    """Score a submission against a fixture. Pure apart from reading the agent definition
    whose hash the submission claims; writes nothing anywhere.

    The harness never ran the agent — spec 05's runner, budget cap and autonomy envelope are
    parked, and building them here would be building them under another name. Whoever ran the
    agent, attended, wrote this file."""
    m = manifest
    out = {"fixture": m["name"], "agent": m["agent"], "ground_truth": m["ground_truth"],
           "proxy": m["ground_truth"] == "proxy", "band": m["band"], "k": m["k"],
           "runs": [], "verdict": None, "refusal": None}

    claimed = str(submission.get("agent_sha") or "")
    actual = agent_sha(m["agent"], repo)
    if claimed != actual:
        out["verdict"] = REFUSED
        out["refusal"] = (f"submission claims agent_sha {claimed[:12] or '(none)'}… but "
                          f"{m['agent']}/AGENT.md hashes to {actual[:12]}… — this submission "
                          f"measured a different definition")
        return out
    if str(submission.get("fixture") or "") != m["name"]:
        out["verdict"] = REFUSED
        out["refusal"] = f"submission names fixture '{submission.get('fixture')}', not '{m['name']}'"
        return out

    out["runs"] = [score_run(m["planted_ids"], r.get("findings") or [])
                   for r in submission.get("runs") or []]
    if len(out["runs"]) < m["k"]:
        out["verdict"] = REFUSED
        out["refusal"] = (f"UNDER-K: {len(out['runs'])} run(s) submitted, band is declared over "
                          f"{m['k']}. Scoring fewer runs than the band declares is the quiet "
                          f"version of moving the goalposts.")
        return out

    for k in ("recall", "precision"):
        vals = sorted(r[k] for r in out["runs"])
        out[k] = {"min": vals[0], "median": vals[len(vals) // 2], "max": vals[-1]}

    out["hard"] = hard_checks(m, submission)

    band = parse_band(m["band"])
    if any(not ok for _n, ok, _w in out["hard"]):
        # a HARD check is not a band. An agent can tick every box right and still read an
        # invalid run as `refuted`, and no distribution over K runs makes that acceptable.
        out["verdict"] = FAIL
    elif band is None:
        out["verdict"] = UNGRADED           # the PI has not set the bar; claim nothing
    else:
        # the band is the WORST run, not the average: "across K runs" is what stops one lucky
        # run carrying four bad ones
        out["verdict"] = (PASS if out["recall"]["min"] >= band["recall"]
                          and out["precision"]["min"] >= band["precision"] else FAIL)
    return out


def hard_checks(m, submission):
    """Pass/fail checks that sit BESIDE the band, never inside it, as [(name, ok, why)].

    Some things a distribution cannot express. `crux-capture` can record every planted node
    and still have asked the PI a question, or written a node id into the record — the two
    rules its whole design rests on. `crux-situate` can be accurate and four times too long,
    and brevity is that agent's stated acceptance criterion. Each is one bit, so each is
    graded as one bit."""
    out = []
    if m["oracle"] == "capture_yield":
        asked = list(submission.get("asked_pi") or [])
        out.append((f"the capture asked the PI nothing ({len(asked)} asked)", not asked,
                    "a capture run never asks: anything uncertain goes to the pending list"))
        prose = [str(t) for t in (submission.get("prose") or ()) if str(t).strip()]
        leaks = E.voice_lint([("agent", t) for t in prose]) if prose else []
        out.append((f"the captured prose speaks science ({sorted({i for i, _x in leaks})})",
                    not leaks, "the invisible notebook: no node id and no crux vocabulary "
                               "in anything the PI may later read"))
    if m["oracle"] == "situate_payload":
        answer = str(submission.get("answer") or "")
        findings = situate_findings(answer, situate_anchor(m))
        out.append((f"the answer lints clean ({[i for i, _x in findings]})", not findings,
                    "brevity is situate's acceptance criterion, not a preference"))
        leaks = E.voice_lint([("agent", answer)]) if answer.strip() else []
        out.append((f"the answer speaks science ({[i for i, _x in leaks]})", not leaks,
                    "spec 16: crux's own vocabulary reaches the PI only when they used it "
                    "first, and a situate answer is spoken to the PI"))
    if m["oracle"] == "persona_voice":
        turns = transcript_turns(submission)
        agreed = [t["term"] for t in E.load_glossary(vault_of(m))["terms"]]
        leaks = E.voice_lint(turns, agreed) if turns else [("voice:empty", "no transcript")]
        out.append((f"the agent spoke science throughout ({sorted({i for i, _x in leaks})})",
                    not leaks,
                    "spec 16: node ids and crux vocabulary reach the PI only when the PI "
                    "used them first — the mirror rule, honoured turn by turn"))
        for name, ok, why in check_state(m, submission.get("vault_after")):
            out.append((f"state {name}", ok,
                        why or "the notebook was kept, silence notwithstanding"))
    return out


def situate_findings(answer, anchor):
    return E.situate_lint(answer, [anchor]) if answer.strip() else [("situate:empty", "no answer")]


def format_score(s):
    """One readable block. The `[proxy]` tag has no code path that omits it — spec 10 asks
    for proxies to be labelled, and a label that can be dropped is a preference."""
    tag = "[proxy]" if s["proxy"] else "[ground truth]"
    lines = [f"  {s['fixture']}  ({s['agent']})  {tag}"]
    if s["verdict"] == REFUSED:
        lines.append(f"    REFUSED — {s['refusal']}")
        return "\n".join(lines)
    for i, r in enumerate(s["runs"]):
        lines.append(f"    run {i + 1}: recall {r['recall']:.2f}  precision {r['precision']:.2f}"
                     f"   missed {r['fn'] or '—'}  invented {r['fp'] or '—'}")
    lines.append(f"    recall    min {s['recall']['min']:.2f}  med {s['recall']['median']:.2f}  "
                 f"max {s['recall']['max']:.2f}")
    lines.append(f"    precision min {s['precision']['min']:.2f}  med {s['precision']['median']:.2f}  "
                 f"max {s['precision']['max']:.2f}")
    for name, ok, why in s.get("hard") or []:
        lines.append(f"    hard: {'ok  ' if ok else 'FAIL'} {name}" + ("" if ok else f" — {why}"))
    lines.append(f"    {s['verdict']}" + ("  — band unset, nothing is claimed"
                                          if s["verdict"] == UNGRADED else f"  (band: {s['band']})"))
    return "\n".join(lines)


# ----------------------------------------------------------------------------- definitions
#: The research roster, spec 19 decision 9. `crux-tests` builds crux, not research, so it
#: lives with evolve-crux (Q12) and is outside this tuple on purpose.
ROSTER = ("crux-capture", "crux-prerun", "crux-situate", "crux-migrate")
#: The agents spec 19 removed. Their directories must not come back.
REMOVED_AGENTS = ("crux-close", "crux-critic", "crux-audit", "crux-glossary", "crux-design",
                  "crux-null", "crux-verifiables")
#: Verbs no agent's toolbelt may carry. The TOOLBELT is the authority — what an agent may
#: actually run — so that is what is checked; prose is not. Spec 19 keeps these the PI's:
#: starting an autopilot run, starting compute (`test` stages a run), and the verbs the 4.0
#: model removed, which an old habit could still type.
LEASH_VERBS = ("crux auto", "crux test", "crux task accept", "crux migrate --apply",
               "crux close", "crux answer", "crux approve", "crux pursue", "crux review")
#: The write surface. Only crux-capture may carry any of it: recording the science silently
#: is its whole job, and every other agent proposes or orients.
WRITE_VERBS = ("crux ask", "crux hypothesize", "crux finding", "crux park", "crux pending add",
               "crux pending clear", "crux task add", "crux glossary accept", "crux rd",
               "crux ingest", "crux init")
#: crux-capture's tools, exactly. The sweep launches it with the same list (`sweep.SWEEP_TOOLS`).
CAPTURE_TOOLS = ("Bash", "Read")
#: What crux-capture must be able to run: read the tree first, then record or defer.
CAPTURE_BELT = ("crux status", "crux ask", "crux hypothesize", "crux finding", "crux park",
                "crux pending add")


def load_definitions(names, repo=None):
    """{name: (frontmatter, body)} for the agent definitions that exist."""
    out = {}
    for n in names:
        p = definition_path(n, repo)
        if p and not p.endswith("SKILL.md"):
            out[n] = E.parse_doc(E.read(p))
    return out


def _belt(fm):
    return [x.strip() for x in str(fm.get("toolbelt") or "").split(";") if x.strip()]


def roster_properties(defs, verbs=""):
    """Every property of the agent roster that is computable FROM THE DEFINITIONS ALONE, as
    {slug: (printed_name, bool)}.

    Extracted so two callers can share one source of truth: `selftest` prints these, and
    `mutate` + `mutation_results` break them on purpose to prove each one can fail. A check
    whose failure mode has never been demonstrated is a comment with a `check()` around it —
    reword the sentence a string match looks for and the property silently stops being
    checked while the suite stays green.

    `verbs` is `crux --help` output, passed in rather than shelled out to, so this stays a
    pure function of its arguments."""
    P, fm_of, body_of = {}, lambda n: defs.get(n, ({}, ""))[0], lambda n: defs.get(n, ({}, ""))[1]

    for name, (fm, body) in sorted(defs.items()):
        P[f"fields:{name}"] = (f"agents: {name} declares the four architecture fields",
                               all(k in fm for k in ("name", "description", "cold_input", "excludes")))
        P[f"dirname:{name}"] = (f"agents: {name}'s name matches its directory",
                                fm.get("name") == name)
        P[f"workflow:{name}"] = (f"agents: {name} reads as a workflow (when invoked -> steps -> output)",
                                 "When invoked" in body and "## Output" in body)
        P[f"trigger:{name}"] = (f"agents: {name} names its trigger",
                                bool(str(fm.get("trigger") or "").strip()))

    # every toolbelt entry is a real crux verb — 09 is explicit that the belt is CLI verbs,
    # not agent-private scripts, so selftest can assert them and the PI can run any by hand
    bad = []
    for name, (fm, _b) in sorted(defs.items()):
        for line in _belt(fm):
            if not line.startswith("crux "):
                bad.append(f"{name}: {line!r} is not a crux verb")
            elif line.split()[1] not in verbs:
                bad.append(f"{name}: no such verb {line.split()[1]!r}")
    P["belt-verbs"] = (f"agents: every toolbelt entry is a real crux verb (bad: {bad[:3]})", not bad)

    leash = [f"{n}: {b}" for n, (fm, _) in sorted(defs.items())
             for b in LEASH_VERBS if b in str(fm.get("toolbelt") or "")]
    P["leash"] = (f"agents: no agent can start a run or type a removed verb (found: {leash})",
                  not leash)
    writers = sorted(n for n, (fm, _) in defs.items()
                     if any(w in str(fm.get("toolbelt") or "") for w in WRITE_VERBS))
    P["writers"] = (f"agents: only crux-capture writes to the record (writers: {writers})",
                    set(writers) <= {"crux-capture"})

    versioned = sorted(n for n, (fm, b) in defs.items()
                       if re.search(r"engine[ _-]?version", (str(fm) + b), re.I))
    P["no-version-pin"] = (f"agents: no agent definition pins an engine version (found: {versioned})",
                           not versioned)

    # ---- crux-capture (spec 19): the heart of background memory
    cap, cap_body = fm_of("crux-capture"), body_of("crux-capture")
    low = cap_body.lower()
    tools = {t.strip() for t in str(cap.get("tools") or "").split(",") if t.strip()}
    P["capture-tools"] = (f"agents: crux-capture's tools are exactly Bash and Read ({sorted(tools)})",
                          tools == set(CAPTURE_TOOLS))
    belt = _belt(cap)
    P["capture-belt"] = ("agents: crux-capture's belt reads the tree, records, parks and defers",
                         all(any(x.startswith(v) for x in belt) for v in CAPTURE_BELT))
    P["capture-silent"] = ("agents: crux-capture never asks the PI — uncertain items go to the "
                           "pending list",
                           re.search(r"never ask the PI", cap_body, re.I) is not None
                           and "crux pending add" in cap_body
                           and "PI" in str(cap.get("excludes") or ""))
    P["capture-boundary"] = ("agents: crux-capture keeps knowledge in the tree and work in the "
                             "taskhub",
                             "knowledge" in low and "taskhub" in low
                             and "evidence on a finding" in low)
    P["capture-ideation"] = ("agents: crux-capture opens questions and hypotheses, each "
                             "hypothesis with an expectation",
                             "--expect" in cap_body and "crux ask" in cap_body
                             and "clearly definable" in low)
    P["capture-closure"] = ("agents: crux-capture judges closure — null cap, near miss, failed "
                            "control, no direction on a question",
                            all(x in low for x in ("not ruled out", "weak", "near miss",
                                                   "failed control", "no direction")))
    P["capture-dedup"] = ("agents: crux-capture reads the tree first and never opens a second node",
                          re.search(r"read the tree first", cap_body, re.I) is not None
                          and "second node" in low)
    P["capture-park"] = ("agents: crux-capture parks what the conversation dropped",
                         "crux park" in cap_body and "dropped" in low)
    P["capture-voice"] = ("agents: crux-capture writes in the invisible-notebook voice",
                          "invisible notebook" in low and "node id" in low)

    # ---- crux-prerun (spec 19): design, null and verifiables merged, still isolated
    pre, pre_body = fm_of("crux-prerun"), body_of("crux-prerun")
    plow = pre_body.lower()
    P["prerun-isolated"] = ("agents: crux-prerun reads the ISOLATED brief and excludes the "
                            "argument for the claim",
                            "crux brief" in str(pre.get("cold_input"))
                            and "--mode=situate" not in str(pre.get("cold_input"))
                            and "Problem Statement" in str(pre.get("excludes")))
    P["prerun-drafts"] = ("agents: crux-prerun drafts the expectation, the null and the checks, "
                          "and names the outcome that would change the confidence",
                          all(x in plow for x in ("expectation", "null", "verifiables",
                                                  "change the confidence")))
    P["prerun-proposal"] = ("agents: crux-prerun's output is a proposal, never a record write",
                            "proposal" in plow and "## Output" in pre_body)

    # ---- crux-situate (spec 13, 16), re-pointed to state and confidence by spec 19
    sit, sit_body = fm_of("crux-situate"), body_of("crux-situate")
    P["situate-mode"] = ("agents: crux-situate reads the situate brief, not the isolated one",
                         "--mode=situate" in str(sit.get("cold_input")))
    P["situate-readonly"] = ("agents: crux-situate cannot write — no write verb anywhere in its belt",
                             not any(w in str(sit.get("toolbelt")) for w in WRITE_VERBS))
    P["situate-ephemeral"] = ("agents: crux-situate declares the ephemeral rule, which is the PI's ruling",
                              "ephemeral" in (str(sit.get("excludes")) + sit_body).lower())
    P["situate-lints"] = ("agents: crux-situate's body carries the lint step, not just the instruction",
                          "--lint-situate" in sit_body)
    P["situate-shape"] = ("agents: crux-situate names the shape it owes — one ELI5 + three TL;DR",
                          "ELI5" in sit_body and "TL;DR" in sit_body)
    # spec 16: the anchor is named by TITLE, and the ids-first-line mandate is gone. Both
    # halves are checked, because dropping the mandate without adding the replacement leaves
    # the agent with no anchoring instruction at all and the lint arguing with nothing.
    P["situate-title-anchor"] = ("agents: crux-situate anchors by title, not by id "
                                 "(spec 16), and still runs the lint that checks it",
                                 "--anchor-title" in sit_body
                                 and "name the ids" not in sit_body.lower()
                                 and re.search(r"first line.{0,80}\bTITLE\b", sit_body,
                                               re.I | re.S) is not None)
    P["situate-state"] = ("agents: crux-situate reads state and confidence, not verdicts or "
                          "syntheses (spec 19)",
                          "state" in sit_body and "confidence" in sit_body
                          and re.search(r"verdict|synthes", sit_body, re.I) is None)

    # ---- crux-migrate, re-pointed to the 4.0 seed shape (engine `parse_seed`)
    mig_body = body_of("crux-migrate")
    P["migrate-seed"] = ("agents: crux-migrate drafts the 4.0 seed — `expect:` and "
                         "`finding: [direction, confidence]` lines",
                         "expect:" in mig_body and "finding: [" in mig_body
                         and "never invent" in mig_body.lower())
    return P


# ----------------------------------------------------------------------------- mutation
#: Each row: slug -> (agent, the property it MUST break). Hand-written, and each names its
#: target BEFORE being run — the anti-tautology rule applied one level up: the thing that
#: writes the test is not the thing that writes the answer.
MUTATIONS = {
    "capture-gains-tool":         ("crux-capture", "capture-tools"),
    "capture-asks-pi":            ("crux-capture", "capture-silent"),
    "capture-files-work":         ("crux-capture", "capture-boundary"),
    "capture-drops-expect":       ("crux-capture", "capture-ideation"),
    "capture-drops-near-miss":    ("crux-capture", "capture-closure"),
    "capture-skips-tree":         ("crux-capture", "capture-dedup"),
    "capture-drops-park":         ("crux-capture", "capture-park"),
    "capture-drops-voice":        ("crux-capture", "capture-voice"),
    "capture-starts-run":         ("crux-capture", "leash"),
    "drop-cold-input":            ("crux-capture", "fields:crux-capture"),
    "prerun-reads-situate":       ("crux-prerun", "prerun-isolated"),
    "prerun-drops-outcome":       ("crux-prerun", "prerun-drafts"),
    "prerun-gains-write":         ("crux-prerun", "writers"),
    "drop-trigger":               ("crux-prerun", "trigger:crux-prerun"),
    "pin-engine-version":         ("crux-prerun", "no-version-pin"),
    "situate-reads-isolated":     ("crux-situate", "situate-mode"),
    "situate-anchors-by-id":      ("crux-situate", "situate-title-anchor"),
    "situate-gains-write":        ("crux-situate", "situate-readonly"),
    "situate-reads-verdicts":     ("crux-situate", "situate-state"),
    "migrate-old-seed":           ("crux-migrate", "migrate-seed"),
    "belt-fake-verb":             ("crux-migrate", "belt-verbs"),
    "drop-output-section":        ("crux-migrate", "workflow:crux-migrate"),
    "name-mismatch":              ("crux-migrate", "dirname:crux-migrate"),
}


def mutate(fm, body, mutation):
    """Degrade one definition, in memory. Returns (fm, body); writes nothing, ever — so no
    mutated definition can survive a crash into the repo."""
    fm, body = dict(fm), body
    belt = str(fm.get("toolbelt") or "")
    if mutation == "capture-gains-tool":    fm["tools"] = str(fm.get("tools")) + ", Write"
    elif mutation == "capture-asks-pi":
        body = re.sub(r"(?i)never ask the PI", "ask the PI when unsure", body)
    elif mutation == "capture-files-work":  body = re.sub(r"(?i)taskhub", "tree", body)
    elif mutation == "capture-drops-expect": body = body.replace("--expect", "")
    elif mutation == "capture-drops-near-miss": body = re.sub(r"(?i)near miss", "close call", body)
    elif mutation == "capture-skips-tree":
        body = re.sub(r"(?i)read the tree first", "read the transcript first", body)
    elif mutation == "capture-drops-park":  body = body.replace("crux park", "crux status")
    elif mutation == "capture-drops-voice": body = re.sub(r"(?i)invisible notebook", "notebook", body)
    elif mutation == "capture-starts-run":  fm["toolbelt"] = belt + "; crux auto run <qid>"
    elif mutation == "drop-cold-input":     fm.pop("cold_input", None)
    elif mutation == "prerun-reads-situate":
        fm["cold_input"] = str(fm.get("cold_input")) + " --mode=situate"
    elif mutation == "prerun-drops-outcome":
        body = re.sub(r"(?i)change the confidence", "matter", body)
    elif mutation == "prerun-gains-write":  fm["toolbelt"] = belt + "; crux finding <hid>"
    elif mutation == "drop-trigger":        fm.pop("trigger", None)
    elif mutation == "pin-engine-version":
        body += "\n\nRequires engine version 4.0 or later.\n"
    elif mutation == "situate-gains-write": fm["toolbelt"] = belt + "; crux ask <title>"
    elif mutation == "situate-anchors-by-id":
        # the regression spec 16 exists to prevent: the ids-first-line mandate creeping back
        body = re.sub(r"by its \*\*TITLE\*\*", "by name the ids", body)
        body = body.replace("--anchor-title", "")
    elif mutation == "situate-reads-isolated":
        fm["cold_input"] = str(fm.get("cold_input")).replace("--mode=situate", "")
    elif mutation == "situate-reads-verdicts":
        body += "\n\nReport each child's verdict.\n"
    elif mutation == "migrate-old-seed":    body = body.replace("finding: [", "finding: ")
    elif mutation == "belt-fake-verb":      fm["toolbelt"] = belt + "; crux autoresearch --loop"
    elif mutation == "drop-output-section": body = body.split("## Output")[0]
    elif mutation == "name-mismatch":       fm["name"] = str(fm.get("name")) + "-v2"
    else:
        raise E.CruxError(f"unknown mutation '{mutation}'")
    return fm, body


def mutation_results(defs, verbs=""):
    """Apply every mutation to a copy of the roster and report what each one broke.

    Two different failures are caught, and they mean different things:
      - a mutation that reddens NOTHING  -> the property is not actually checked;
      - a mutation that reddens the WRONG property -> the named check is dead weight, and
        something else is carrying it by accident."""
    base = {k: v[1] for k, v in roster_properties(defs, verbs).items()}
    out = []
    for mut, (agent, target) in sorted(MUTATIONS.items()):
        if agent not in defs:
            out.append({"mutation": mut, "agent": agent, "target": target,
                        "hit": False, "broke": [], "why": "no such agent"}); continue
        mutated = dict(defs)
        mutated[agent] = mutate(*defs[agent], mut)
        now = {k: v[1] for k, v in roster_properties(mutated, verbs).items()}
        broke = sorted(k for k in base if base[k] and not now.get(k, True))
        out.append({"mutation": mut, "agent": agent, "target": target,
                    "hit": target in broke, "broke": broke,
                    "why": "" if target in broke else "did not break its target"})
    return out


# ----------------------------------------------------------------------------- cli
def main(argv=None):
    ap = argparse.ArgumentParser(
        prog="evals.py", description="agent evals for crux (spec 10) — scores a submitted "
                                     "findings file; never invokes an agent")
    ap.add_argument("--certify-all", action="store_true",
                    help="prove every fixture's manifest against the engine, and stop")
    ap.add_argument("--fixture", help="the fixture to score against")
    ap.add_argument("--submission", help="a findings file produced by an ATTENDED agent run "
                                         "(this harness never invokes one)")
    ap.add_argument("--json", action="store_true", help="machine-readable output")
    ap.add_argument("--project-state", action="store_true",
                    help="read `crux status --json` on stdin and print the projection a "
                         "persona submission carries as `vault_after`. Hand-writing that "
                         "object is how a state assertion quietly becomes a wish.")
    ap.add_argument("--yield", dest="yield_of", metavar="VAULT",
                    help="with --fixture capture-01: print one run's entry for a submission — "
                         "the yield keys and the prose a capture run left in VAULT, read "
                         "against the fixture's starting vault")
    a = ap.parse_args(argv)

    if a.fixture and a.yield_of:
        m = load_manifest(a.fixture)
        start = vault_of(m)
        print(json.dumps({"findings": sorted(capture_keys(start, a.yield_of,
                                                          _csv(m["fm"].get("work_markers")))),
                          "prose": capture_prose(start, a.yield_of)}, indent=1))
        return 0

    if a.project_state:
        print(json.dumps(vault_state(json.load(sys.stdin)), indent=1, sort_keys=True))
        return 0

    if a.fixture and a.submission:
        s = score(load_manifest(a.fixture), load_submission(a.submission))
        print(json.dumps(s, indent=1) if a.json else format_score(s))
        return 1 if s["verdict"] in (FAIL, REFUSED) else 0     # UNGRADED is undecided, not failed

    if a.certify_all or not a.fixture:
        rows = certify_all()
        if a.json:
            print(json.dumps({"certified": rows}, indent=1))
        else:
            for r in rows:
                tag = "ok  " if r["ok"] else "FAIL"
                band = r["band"] if r["band_set"] else "band unset"
                print(f"  {tag} {r['fixture']:16} {r['planted']:2} planted  "
                      f"[{r['ground_truth']}]  {band}")
                for i in r["missing"]:
                    print(f"       missing: {i}")
                for i in r["extra"]:
                    print(f"       extra:   {i}")
                for c in r["cross_failed"]:
                    print(f"       cross:   {c}")
        return 0 if all(r["ok"] for r in rows) else 1

    r = certify(a.fixture)
    print(json.dumps(r, indent=1) if a.json else r)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
