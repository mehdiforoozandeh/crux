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
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == heading.lower()
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


def certify(name, root=None):
    """Prove the manifest true. Read-only; the fixture tree is never written.

    Three ways a hand-authored fixture goes wrong, and all three are caught here:
      missing — a planted id the engine does not emit (the defect was never planted, or was
                planted as something `validate` does not report at all: a task `blocked_by`
                cycle is a *status*, not a problem);
      extra   — an id the engine emits that nobody planted, which would score a CORRECT agent
                finding as invented;
      band    — `unset` is legal and reported, never silently treated as a pass."""
    m = load_manifest(name, root)
    got = emitted_ids(m)
    missing = sorted(m["planted_ids"] - got)
    extra = sorted(got - m["planted_ids"])
    return {"fixture": name, "agent": m["agent"], "ground_truth": m["ground_truth"],
            "ok": not missing and not extra, "missing": missing, "extra": extra,
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

    band = parse_band(m["band"])
    if band is None:
        out["verdict"] = UNGRADED           # the PI has not set the bar; claim nothing
    else:
        # the band is the WORST run, not the average: "across K runs" is what stops one lucky
        # run carrying four bad ones
        out["verdict"] = (PASS if out["recall"]["min"] >= band["recall"]
                          and out["precision"]["min"] >= band["precision"] else FAIL)
    return out


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
        return 0 if all(r["ok"] for r in rows) else 1

    r = certify(a.fixture)
    print(json.dumps(r, indent=1) if a.json else r)
    return 0 if r["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
