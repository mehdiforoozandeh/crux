#!/usr/bin/env python3
"""Agent evals for crux — spec 10.

`selftest.py` asserts that the ENGINE is right. This asserts that the AGENTS are, and it does
so without ever running one.

    python evals.py --certify-all
    python evals.py --fixture audit-01 --submission runs.json [--json]

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
  - `certify()` proves the manifest true by running the engine's own `validation_report` and
    comparing the emitted id set to the planted id set, exactly.

A fixture that drifts from its manifest goes red in `selftest` immediately, and no eval ever
grades against a stale ground truth. That is spec 10's anti-tautology rule made mechanical
rather than promised.

The defect key is **the id the engine already emits** — a node id (`h2`), or a namespaced key
(`wiki:<slug>`, `task:<file>`). Nobody matches a message. A fixture plants at most one defect
per id; two defects means two nodes.
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


def vault_of(manifest):
    return os.path.join(manifest["dir"], "vault")


# ----------------------------------------------------------------------------- certification
def emitted_ids(manifest):
    """The id set the engine reports on this fixture's vault, under the manifest's OWN
    `checks` list. Never a default: `gate` and `decks` are opt-in checks, so a certifier
    running the defaults would score a correctly-found gate backlog as invented."""
    r = E.validation_report(vault_of(manifest), checks=manifest["checks"])
    return {e["id"] for tier in ("problems", "warnings") for e in r[tier]}


#: Ticks, as they appear in a submitted id: `h1:v2=x`. Spelled out rather than reusing the
#: markdown characters because ` ` (unmet) cannot live inside an id.
TICKS = {"x": "x", "u": " ", "n": "-"}


def _oracle_validation_report(m):
    """audit-01's shape: the planted set IS the engine's emitted set, exactly."""
    return emitted_ids(m), []


def _oracle_ticks(m):
    """close-01: the planted ids are `<hid>:v<n>=<tick>`, so a WRONG tick is simultaneously a
    false positive and a false negative — which is exactly what it is.

    The verdict is not scored as an id. It is `verdict_read` in the submission, checked
    separately, because an agent can get every tick right and still call an invalid run
    `refuted` — the confusion `crux-close`'s definition names as the failure the kinds exist
    to prevent."""
    hid = str(m["fm"]["node"])
    n = E.Vault(vault_of(m)).get(hid)
    lines = E._verifiable_lines(n["body"])
    avail = {f"{hid}:v{i}={t}" for i in range(1, len(lines) + 1) for t in TICKS}

    # one tick per check, and no phantom check
    per = {}
    for pid in m["planted_ids"]:
        key, _, tick = pid.partition("=")
        per.setdefault(key, []).append(tick)
    cross = [(f"every check has exactly one planted tick ({sorted(per)})",
              sorted(per) == sorted(f"{hid}:v{i}" for i in range(1, len(lines) + 1))
              and all(len(v) == 1 for v in per.values()))]

    # the fixture must NOT contain the answer: the agent proposes the ticks
    cross.append(("the fixture's boxes are all unticked — the agent proposes them",
                  n.status == "running" and all(t == " " for t, _x in lines)))

    # and the manifest's own vector, run through the engine, must give the recorded verdict
    by = {k: [] for k in E.VERIFIABLE_KINDS}
    for i, (_t, text) in enumerate(lines, 1):
        tick = per.get(f"{hid}:v{i}", [None])[0]
        by[E.verifiable_kind(text)[0]].append(TICKS.get(tick, " "))
    tallies = {k: E._tally(v) for k, v in by.items()}
    derived = E.derive_verdict_15(tallies[E.DEFAULT_KIND], tallies[E.NEUTRAL_KIND],
                                  str(n["fm"].get(E.RULE_FIELD) or "all"))
    cross.append((f"the planted tick vector derives '{m['fm']['verdict_read']}' "
                  f"(engine says '{derived}')", derived == str(m["fm"]["verdict_read"])))
    return avail, cross


def _oracle_null(m):
    """null-01: the planted id is the confound FAMILY, from the engine's closed vocabulary.

    A decoy family is declared too — a second, superficially available boring explanation the
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
        """Any hypothesis anywhere under `qid` that carries findings. A question with none is
        one where nothing is settled yet, and saying so is the agent's job — filling the hole
        with plausible narrative is the failure a fluent model is most likely to have."""
        for k in v.children.get(qid, ()):
            n = v.nodes[k]
            if n.type == "idea" and E._deck_text(n["body"], "Findings"):
                return True
            if n.type == "question" and settled(k):
                return True
        return False

    avail |= {f"gap:{q}" for q in b["untested"]["open_questions"] if not settled(q)}
    ref = _section(m["body"], "Reference answer")
    cross = [("the reference answer lints clean",
              ref.strip() != "" and E.situate_lint(ref, [anchor]) == [])]
    return avail, cross


def _v_prose_cap(m):
    """Every id classed `over-cap` really is over the cap, per the engine's own counter."""
    v = E.Vault(vault_of(m))
    bad = [p["id"] for p in m["planted"] if "over-cap" in p["class"]
           and E.prose_words(v.get(p["id"].split(":")[-1])["body"],
                             v.get(p["id"].split(":")[-1]).type) <= E.PROSE_CAP]
    return f"every over-cap id is genuinely over the cap ({bad})", not bad


def _v_scenario_gap(m):
    """Every id classed `redundant` really is one the engine flags for a shared scenario."""
    v = E.Vault(vault_of(m))
    bad = [p["id"] for p in m["planted"] if "redundant" in p["class"]
           and "SAME failure scenario" not in (E.scenario_gap(v.get(p["id"].split(":")[-1])) or "")]
    return f"every redundant id is one the engine flags ({bad})", not bad


def _v_no_verifiables(m):
    """The fixture must not contain the answer: the agent writes the checks."""
    n = E.Vault(vault_of(m)).get(str(m["fm"]["node"]))
    return ("the target node carries no verifiables — the agent writes them",
            sum(E.count_verifiables(n["body"])) == 0)


def _v_null_approved(m):
    """`crux-verifiables` writes against an APPROVED null; the PI gate sits before it."""
    n = E.Vault(vault_of(m)).get(str(m["fm"]["node"]))
    return ("the null is approved, as the agent's cold input requires",
            bool(str(n["fm"].get(E.NULL_APPROVED) or "").strip()))


def _v_evidence_resolves(m):
    """Every path named in the key exists under the fixture. A tick nobody can point at is a
    guess, and a key pointing at a file that is not there cannot catch one."""
    bad = [t for p in m["planted"] for t in re.findall(r"`([\w./-]+\.(?:md|csv|py|txt))`", p["note"])
           if not os.path.isfile(os.path.join(m["dir"], "vault", t))]
    return f"every evidence pointer in the key resolves ({bad})", not bad


def _v_term_counts(m):
    """Each planted term survives the deterministic filter it is graded beside — a term
    appearing once is dropped before the agent ever sees it."""
    v = E.Vault(vault_of(m))
    bad = [p["id"] for p in m["planted"]
           if len(E.count_term(v, p["id"].split(":", 1)[-1])["documents"]) < 2]
    return f"every planted term clears the occurrence floor ({bad})", not bad


def _v_distinct_expected(m):
    """THE anti-tautology check at the value level, and the reason tests-01 is worth having at
    all without executing anything: no expected value in the key may equal what the
    deliberately-broken implementation actually returns. A key that could be satisfied by
    describing the code is a description of the code."""
    wrong = set(_csv(m["fm"].get("wrong_values")))
    clash = sorted(w for p in m["planted"] for w in wrong if w and w in p["note"])
    return f"no key row expects what the broken implementation returns ({clash})", not clash


def _v_one_disease_per_node(m):
    """A fixture with two diseases on one node cannot tell a correct diagnosis from a lucky
    one — and the whole taxonomy exists because a mixed result never announces which it has."""
    pairs = [p["id"].split(":") for p in m["planted"]]
    ok = (all(len(x) == 2 for x in pairs)
          and len({d for d, _n in pairs}) == len(pairs) == len({n for _d, n in pairs}))
    return f"one disease per node, each disease once ({[':'.join(x) for x in pairs]})", ok


VERIFICATIONS = {"prose_cap": _v_prose_cap, "scenario_gap": _v_scenario_gap,
                 "no_verifiables": _v_no_verifiables, "null_approved": _v_null_approved,
                 "evidence_resolves": _v_evidence_resolves, "term_counts": _v_term_counts,
                 "distinct_expected": _v_distinct_expected,
                 "one_disease_per_node": _v_one_disease_per_node}


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


ORACLES = {"validation_report": _oracle_validation_report,
           "verifiable_ticks": _oracle_ticks,
           "null_vocabulary": _oracle_null,
           "situate_payload": _oracle_situate,
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
      missing — a planted id the oracle does not offer (the defect was never planted, or was
                planted as something `validate` does not report at all: a task `blocked_by`
                cycle is a *status*, not a problem);
      extra   — an id the oracle offers that nobody planted. For `validation_report` this is
                fatal: it would score a CORRECT agent finding as invented. For the fixtures
                whose oracle offers a *menu* (every family in the closed vocabulary, every
                tick a check could carry), extra is expected and is not a failure — what
                matters there is that no planted id is outside the menu.
      band    — `unset` is legal and reported, never silently treated as a pass."""
    m = load_manifest(name, root)
    if m["oracle"] not in ORACLES:
        raise E.CruxError(f"fixture '{name}': unknown oracle '{m['oracle']}' — known oracles "
                          f"are {', '.join(sorted(ORACLES))}")
    avail, cross = ORACLES[m["oracle"]](m)
    exact = m["oracle"] == "validation_report"
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
    return [certify(n, root) for n in fixture_names(root)]


# ----------------------------------------------------------------------------- scoring
#: verdicts. UNGRADED is the one that matters: a band nobody has set must never read as a
#: pass, because a bar invented with no measurement behind it is a guess with a decimal point.
PASS, FAIL, UNGRADED, REFUSED = "PASS", "FAIL", "UNGRADED", "REFUSED"


def agent_sha(agent, repo=None):
    """sha256 of an agent's definition — what pins a submission to the prompt that produced
    it. Without it a score is a number with no provenance, and re-scoring after an edit
    silently compares one agent to a different one."""
    repo = repo or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    p = os.path.join(repo, "agents", agent, "AGENT.md")
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

    Some things a distribution cannot express. `crux-close` can propose a perfect tick vector
    and still call the run `refuted` rather than `invalid-run` — a different sentence, and
    confusing the two is the failure spec 15's kinds exist to prevent. `crux-situate` can be
    accurate and four times too long, and brevity is that agent's stated acceptance criterion.
    Both are one bit, so both are graded as one bit."""
    out = []
    want = m["fm"].get("verdict_read")
    if want:
        got = str(submission.get("verdict_read") or "")
        out.append((f"verdict_read {got or '(none)'!r}", got == str(want),
                    f"the run reads as '{want}'"))
    if m["oracle"] == "situate_payload":
        answer = str(submission.get("answer") or "")
        findings = situate_findings(answer, str(m["fm"]["node"]))
        out.append((f"the answer lints clean ({[i for i, _x in findings]})", not findings,
                    "brevity is situate's acceptance criterion, not a preference"))
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
#: Verbs no agent's toolbelt may carry. The TOOLBELT is the authority — what an agent may
#: actually run — so that is what is checked; prose is not. 09's D9: since spec 15 a tick
#: decides `invalid-run` versus `refuted`, so an agent writing one sets both the verdict and
#: its reason.
LEASH_VERBS = ("crux close", "crux answer", "crux approve", "crux task accept",
               "crux pursue", "crux migrate --apply")
#: The wider write surface, for the agents whose whole contract is "propose, never write".
WRITE_VERBS = ("crux ask", "crux hypothesize", "crux close", "crux answer", "crux approve",
               "crux task add", "crux glossary accept", "crux rd", "crux ingest")


def load_definitions(names, repo=None):
    """{name: (frontmatter, body)} for the agent definitions that exist."""
    repo = repo or os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
    out = {}
    for n in names:
        p = os.path.join(repo, "agents", n, "AGENT.md")
        if os.path.isfile(p):
            out[n] = E.parse_doc(E.read(p))
    return out


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

    # every toolbelt entry is a real crux verb — 09 is explicit that the belt is CLI verbs,
    # not agent-private scripts, so selftest can assert them and the PI can run any by hand
    bad = []
    for name, (fm, _b) in sorted(defs.items()):
        for line in str(fm.get("toolbelt") or "").split(";"):
            line = line.strip()
            if not line:
                continue
            if not line.startswith("crux "):
                bad.append(f"{name}: {line!r} is not a crux verb")
            elif line.split()[1] not in verbs:
                bad.append(f"{name}: no such verb {line.split()[1]!r}")
    P["belt-verbs"] = (f"agents: every toolbelt entry is a real crux verb (bad: {bad[:3]})", not bad)

    crit = fm_of("crux-critic")
    P["critic-isolated"] = ("agents: the critic is isolated by construction — no vault, empty toolbelt",
                            not str(crit.get("toolbelt") or "").strip()
                            and "vault" in str(crit.get("excludes") or "").lower())
    P["verifiables-exclusion"] = ("agents: crux-verifiables declares the exclusion the brief actually enforces",
                                  "Problem Statement" in str(fm_of("crux-verifiables").get("excludes") or ""))

    leash = [f"{n}: {b}" for n, (fm, _) in sorted(defs.items())
             for b in LEASH_VERBS if b in str(fm.get("toolbelt") or "")]
    P["leash"] = (f"agents: no agent's toolbelt can set a verdict or a direction (found: {leash})",
                  not leash)
    P["close-says-so"] = ("agents: and crux-close says so in words, since it is the one that could",
                          "you never run `crux close`" in body_of("crux-close").lower())

    gl = fm_of("crux-glossary")
    P["glossary-contract"] = ("agents: the glossary agent matches spec 14's parked contract",
                              "propose" in str(gl.get("cold_input") or "")
                              and "no write verb" in str(gl.get("toolbelt") or "").lower()
                              and "conversation" in str(gl.get("excludes") or "").lower())

    versioned = sorted(n for n, (fm, b) in defs.items()
                       if re.search(r"engine[ _-]?version", (str(fm) + b), re.I))
    P["no-version-pin"] = (f"agents: no agent definition pins an engine version (found: {versioned})",
                           not versioned)

    # ---- spec 13's two, same convention, same table
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

    des, des_body = fm_of("crux-design"), body_of("crux-design")
    P["design-isolated"] = ("agents: crux-design reads the ISOLATED brief — the designer must not see advocacy",
                            "crux brief" in str(des.get("cold_input"))
                            and "--mode=situate" not in str(des.get("cold_input")))
    P["design-excludes"] = ("agents: crux-design's excludes name the advocacy channel",
                            "Problem Statement" in str(des.get("excludes")))
    P["design-readonly"] = ("agents: crux-design cannot write — it proposes, the PI applies",
                            not any(w in str(des.get("toolbelt")) for w in
                                    ("crux close", "crux answer", "crux approve", "crux pursue",
                                     "crux task accept", "crux hypothesize")))
    P["design-taskhub"] = ("agents: crux-design's belt reaches the taskhub for what was already tried",
                           "crux task list" in str(des.get("toolbelt")))
    P["design-question"] = ("agents: crux-design states the central question verbatim",
                            "Is there any plausible outcome of this run from which we would "
                            "conclude nothing?" in des_body)
    P["design-taxonomy"] = ("agents: crux-design names all three causes and both handoff targets",
                            all(x in des_body for x in ("compound claim", "crux-critic",
                                                        "crux-verifiables"))
                            and "does not follow from the claim" in des_body)
    P["design-handoff"] = ("agents: crux-design hands off by NAMING, never by invoking",
                           "never invoke" in des_body.lower() or "does not invoke" in des_body.lower())
    P["design-proposal"] = ("agents: crux-design's output is a proposal, never a vault write",
                            "proposal" in des_body.lower() and "## Output" in des_body)
    return P


# ----------------------------------------------------------------------------- mutation
#: Each row: slug -> (agent or None for "any", the property it MUST break, how to degrade it).
#: Hand-written, and each names its target BEFORE being run — the anti-tautology rule applied
#: one level up: the thing that writes the test is not the thing that writes the answer.
MUTATIONS = {
    "belt-adds-close":            ("crux-audit", "leash"),
    "belt-adds-answer":           ("crux-migrate", "leash"),
    "belt-adds-approve":          ("crux-null", "leash"),
    "belt-fake-verb":             ("crux-tests", "belt-verbs"),
    "critic-gains-belt":          ("crux-critic", "critic-isolated"),
    "verifiables-drops-exclusion": ("crux-verifiables", "verifiables-exclusion"),
    "situate-reads-isolated":     ("crux-situate", "situate-mode"),
    "situate-gains-write":        ("crux-situate", "situate-readonly"),
    "design-reads-situate":       ("crux-design", "design-isolated"),
    "design-drops-never-invoke":  ("crux-design", "design-handoff"),
    "close-drops-never-run":      ("crux-close", "close-says-so"),
    "glossary-gains-write":       ("crux-glossary", "glossary-contract"),
    "drop-output-section":        ("crux-verifiables", "workflow:crux-verifiables"),
    "drop-cold-input":            ("crux-critic", "fields:crux-critic"),
    "name-mismatch":              ("crux-audit", "dirname:crux-audit"),
    "pin-engine-version":         ("crux-design", "no-version-pin"),
}


def mutate(fm, body, mutation):
    """Degrade one definition, in memory. Returns (fm, body); writes nothing, ever — so no
    mutated definition can survive a crash into the repo."""
    fm, body = dict(fm), body
    belt = str(fm.get("toolbelt") or "")
    if mutation == "belt-adds-close":       fm["toolbelt"] = belt + "; crux close <hid>"
    elif mutation == "belt-adds-answer":    fm["toolbelt"] = belt + "; crux answer <qid>"
    elif mutation == "belt-adds-approve":   fm["toolbelt"] = belt + "; crux approve <sid>"
    elif mutation == "belt-fake-verb":      fm["toolbelt"] = belt + "; crux autoresearch --loop"
    elif mutation == "critic-gains-belt":   fm["toolbelt"] = "crux status --json"
    elif mutation == "situate-gains-write": fm["toolbelt"] = belt + "; crux ask <title>"
    elif mutation == "glossary-gains-write":
        fm["toolbelt"] = "crux glossary accept <term>"
    elif mutation == "verifiables-drops-exclusion":
        fm["excludes"] = str(fm.get("excludes")).replace("## Problem Statement", "the draft")
    elif mutation == "situate-reads-isolated":
        fm["cold_input"] = str(fm.get("cold_input")).replace("--mode=situate", "")
    elif mutation == "design-reads-situate":
        fm["cold_input"] = str(fm.get("cold_input")) + " --mode=situate"
    elif mutation == "design-drops-never-invoke":
        body = re.sub(r"[Nn]ever invoke|[Dd]oes not invoke", "should avoid calling", body)
    elif mutation == "close-drops-never-run":
        body = body.replace("You never run `crux close`.", "Leave `crux close` to the PI.")
    elif mutation == "drop-output-section":
        body = body.split("## Output")[0]
    elif mutation == "drop-cold-input":     fm.pop("cold_input", None)
    elif mutation == "name-mismatch":       fm["name"] = str(fm.get("name")) + "-v2"
    elif mutation == "pin-engine-version":
        body += "\n\nRequires engine version 3.1 or later.\n"
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
    a = ap.parse_args(argv)

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
