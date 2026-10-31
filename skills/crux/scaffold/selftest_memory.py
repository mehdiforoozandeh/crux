#!/usr/bin/env python3
"""Self-test for the engine 4.0 tree model (spec 19, chunk C1): Question / Hypothesis /
Finding, the derived state and confidence, the null cap, parking, `crux finding`, the removed
verbs, the new validate rules and the id-allocation lock.

    python3 selftest_memory.py        # standalone: prints PASSED a / b, exits 1 on any failure

`run_all(check)` takes selftest.py's `check(name, cond)`, so the counts aggregate there. Every
test runs in a temp dir. No network, no tokens."""
import os, sys, re, json, shutil, subprocess, tempfile, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

CLI = os.path.join(HERE, "crux.py")


# ------------------------------------------------------------------------------- helpers
def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _write(p, text):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def _edit_fm(root, nid, **fields):
    """Hand-edit one node's frontmatter (the way a PI or a stray agent would)."""
    n = E.Vault(root).get(nid)
    fm = dict(n["fm"])
    for k, v in fields.items():
        if v is None:
            fm.pop(k, None)
        else:
            fm[k] = v
    E.write_if_changed(n["path"], E.render_doc(fm, n["body"]))


def _dir_bytes(root):
    """Every file under root -> its sha256. A byte map, so 'wrote nothing' is checkable."""
    out = {}
    for dp, dns, fns in os.walk(root):
        for fn in fns:
            p = os.path.join(dp, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root)] = hashlib.sha256(f.read()).hexdigest()
    return out


def _cli(root, *argv):
    env = dict(os.environ, CRUX_NO_UPDATE_CHECK="1")
    return subprocess.run([sys.executable, CLI] + list(argv), cwd=root, env=env,
                          capture_output=True, text=True, encoding="utf-8")


def _vault(tmp, name="v"):
    root = os.path.join(tmp, name)
    E.cmd_init("Memory test", root)
    return root


def _state(root, nid):
    return E.derive_state(E.Vault(root), nid)


def _hyp(root, title, parent, **kw):
    kw.setdefault("expect", "the treated arm scores higher than the control arm")
    return E.cmd_hypothesize(root, title, parent, **kw)[0]


def _raises(fn):
    try:
        fn()
    except E.CruxError:
        return True
    return False


# ------------------------------------------------------------------------------- sections
def _model_tests(check):
    check("model: ENGINE_VERSION is 4.1", E.ENGINE_VERSION == "4.1")
    check("model: SCHEMA_GENERATION is 3", E.SCHEMA_GENERATION == 3)
    check("model: node types are project / question / idea / finding (synthesis removed)",
          set(E.TYPES) == {"project", "question", "idea", "finding"})
    check("model: directions are supports · against · mixed · no answer yet",
          tuple(E.DIRECTIONS) == ("supports", "against", "mixed", "no-answer-yet"))
    check("model: confidences ascend weak < moderate < strong",
          tuple(E.CONFIDENCES) == ("weak", "moderate", "strong"))
    check("model: states are open · leaning · settled · parked",
          tuple(E.STATES) == ("open", "leaning", "settled", "parked"))
    check("model: null outcomes are ruled-out · not-ruled-out · none",
          tuple(E.NULL_STATES) == ("ruled-out", "not-ruled-out", "none"))
    tdir = os.path.join(HERE, "templates")
    check("model: templates/synthesis.md is deleted",
          not os.path.exists(os.path.join(tdir, "synthesis.md")))
    check("model: templates/finding.md exists and declares type: finding",
          os.path.exists(os.path.join(tdir, "finding.md"))
          and "type: finding" in _read(os.path.join(tdir, "finding.md")))
    idea = _read(os.path.join(tdir, "idea.md"))
    check("model: the hypothesis template carries ## Expect and no stored verdict or status",
          "## Expect" in idea and "\nverdict:" not in idea and "\nstatus:" not in idea)
    q = _read(os.path.join(tdir, "question.md"))
    check("model: the question template stores no status and no stale flag",
          "\nstatus:" not in q and "\nstale:" not in q)


def _hypothesize_tests(check, tmp):
    root = _vault(tmp, "hyp")
    q1, _ = E.cmd_ask(root, "Does the treatment help?")
    before = _dir_bytes(root)
    check("hypothesize: a new hypothesis without an expectation is refused",
          _raises(lambda: E.cmd_hypothesize(root, "treatment helps", q1)))
    check("hypothesize: a blank expectation is refused too",
          _raises(lambda: E.cmd_hypothesize(root, "treatment helps", q1, expect="   ")))
    check("hypothesize: a refused hypothesis writes nothing (counter included)",
          _dir_bytes(root) == before)
    h1 = _hyp(root, "treatment helps", q1, expect="accuracy rises by at least 2 points")
    n = E.Vault(root).get(h1)
    check("hypothesize: --expect lands in ## Expect",
          "accuracy rises by at least 2 points" in E._section(n["body"], "Expect"))
    check("hypothesize: no verifiables means no checkbox at all (verifiables are optional)",
          sum(E.count_verifiables(n["body"])) == 0)
    check("hypothesize: the new node is stamped schema 3", E.node_schema(n) == 3)
    check("hypothesize: no null, no verifiables, no rule — the vault still validates clean",
          E.cmd_validate(root) == [])
    h2 = _hyp(root, "with checks", q1, verifiables=["accuracy +2 vs control"],
              null="chance — seed variance alone explains the gain")
    n2 = E.Vault(root).get(h2)
    check("hypothesize: optional null and verifiables are still written when given",
          "seed variance" in E._section(n2["body"], "Null")
          and E.count_verifiables(n2["body"]) == (0, 1, 0))

    # test: records run links, takes the lock, never refuses on a missing null/rule/scenario
    ok = True
    try:
        E.cmd_test(root, h1, to="running", run="job 101")
    except E.CruxError:
        ok = False
    check("test: --to running no longer refuses a hypothesis with no null, rule or checks", ok)
    check("test: the run link is recorded", "job 101" in _read(E.Vault(root).get(h1)["path"]))
    E.cmd_test(root, h2, to="running", run="job 102")
    check("test: --to running still takes the lock on a hypothesis with checks",
          bool(E.Vault(root).get(h2)["fm"].get(E.LOCK_FIELD)))

    r = _cli(root, "hypothesize", "cli without expectation", "-p", q1)
    check("cli: `crux hypothesize` without --expect exits 1 and names --expect",
          r.returncode == 1 and "--expect" in r.stderr)
    r = _cli(root, "hypothesize", "cli with expectation", "-p", q1, "--expect",
             "the loss falls below 0.3", "--json")
    ok = r.returncode == 0
    hid = json.loads(r.stdout)["id"] if ok else None
    check("cli: `crux hypothesize --expect` writes ## Expect",
          ok and "the loss falls below 0.3" in
          E._section(E.Vault(root).get(hid)["body"], "Expect"))


def _state_tests(check, tmp):
    root = _vault(tmp, "state")
    q1, _ = E.cmd_ask(root, "Does the treatment help?")
    h1 = _hyp(root, "treatment helps", q1)
    s = _state(root, h1)
    check("state: no finding -> open, no confidence",
          s["state"] == "open" and s["confidence"] is None and s["finding"] is None)
    f1, _, _ = E.cmd_finding(root, h1, "weak", why="one seed only", direction="supports")
    s = _state(root, h1)
    check("state: a weak finding -> leaning, weak",
          (s["state"], s["confidence"], s["finding"]) == ("leaning", "weak", f1))
    f2, _, _ = E.cmd_finding(root, h1, "moderate", why="three seeds", direction="supports")
    s = _state(root, h1)
    check("state: a moderate finding -> leaning, moderate",
          (s["state"], s["confidence"]) == ("leaning", "moderate"))
    f3, _, _ = E.cmd_finding(root, h1, "strong", why="five seeds and a held-out set",
                             direction="against")
    s = _state(root, h1)
    check("state: a strong finding -> settled, strong",
          (s["state"], s["confidence"], s["finding"]) == ("settled", "strong", f3))

    # strongest wins, newest breaks ties
    f4, _, _ = E.cmd_finding(root, h1, "weak", why="a later, weaker look", direction="mixed")
    s = _state(root, h1)
    check("roll-up: the strongest finding wins over a newer weaker one (PI ruling Q3)",
          (s["state"], s["confidence"], s["finding"]) == ("settled", "strong", f3))

    h2 = _hyp(root, "tie break", q1)
    a, _, _ = E.cmd_finding(root, h2, "moderate", why="first look", direction="supports")
    b, _, _ = E.cmd_finding(root, h2, "moderate", why="second look", direction="against")
    _edit_fm(root, a, created="2026-01-02T00:00:00")
    _edit_fm(root, b, created="2026-01-01T00:00:00")
    check("roll-up: equal strength -> the newer `created` decides",
          _state(root, h2)["finding"] == a)
    _edit_fm(root, a, created="2026-01-01T00:00:00")
    check("roll-up: equal strength and equal `created` -> the higher id decides",
          _state(root, h2)["finding"] == max((a, b), key=E.natkey))
    check("roll-up: node_findings lists findings oldest first, by created then id",
          [f.id for f in E.node_findings(E.Vault(root), h2)]
          == sorted((a, b), key=lambda x: ("2026-01-01T00:00:00", E.natkey(x))))

    # no answer yet never sets the state
    h3 = _hyp(root, "unreadable run", q1)
    E.cmd_finding(root, h3, "strong", why="the job crashed", direction="no answer yet")
    s = _state(root, h3)
    check("roll-up: a `no answer yet` finding alone leaves the node open",
          s["state"] == "open" and s["confidence"] is None)
    w, _, _ = E.cmd_finding(root, h3, "weak", why="a partial rerun", direction="supports")
    E.cmd_finding(root, h3, "strong", why="crashed again", direction="no-answer-yet")
    s = _state(root, h3)
    check("roll-up: a strong `no answer yet` never overrides a weak real finding",
          (s["state"], s["confidence"], s["finding"]) == ("leaning", "weak", w))
    check("finding: the spaced form `no answer yet` is stored as the token `no-answer-yet`",
          all(f["fm"].get("direction") in E.DIRECTIONS
              for f in E.node_findings(E.Vault(root), h3)))

    # parking
    E.cmd_park(root, h1)
    s = _state(root, h1)
    check("park: a parked node is parked whatever its findings say",
          s["state"] == "parked" and s["confidence"] == "strong")
    E.cmd_park(root, h1, undo=True)
    check("park: unparking restores the derived state", _state(root, h1)["state"] == "settled")
    check("park: a finding cannot be parked", _raises(lambda: E.cmd_park(root, f1)))
    check("park: the project cannot be parked", _raises(lambda: E.cmd_park(root, "root")))
    E.cmd_park(root, q1)
    check("park: a question can be parked", _state(root, q1)["state"] == "parked")
    E.cmd_park(root, q1, undo=True)


def _question_tests(check, tmp):
    root = _vault(tmp, "question")
    q1, _ = E.cmd_ask(root, "Does the treatment help?")
    check("question: no findings anywhere -> open", _state(root, q1)["state"] == "open")
    h1 = _hyp(root, "treatment helps", q1)
    E.cmd_finding(root, h1, "strong", why="five seeds", direction="supports")
    s = _state(root, q1)
    check("question: a strong child-hypothesis finding counts, capped at moderate (leaning)",
          (s["state"], s["confidence"]) == ("leaning", "moderate"))
    q2, _ = E.cmd_ask(root, "Is the effect weak?")
    h2 = _hyp(root, "weak effect", q2)
    E.cmd_finding(root, h2, "weak", why="one seed", direction="supports")
    s = _state(root, q2)
    check("question: a weak child finding stays weak under the cap",
          (s["state"], s["confidence"]) == ("leaning", "weak"))
    h3 = _hyp(root, "another arm", q1)
    E.cmd_finding(root, h3, "weak", why="noisy", direction="against")
    check("question: the strongest child finding is the one that counts",
          _state(root, q1)["confidence"] == "moderate")
    fq, _, _ = E.cmd_finding(root, q1, "weak", answer="Probably yes, on two datasets.")
    s = _state(root, q1)
    check("question: its own finding decides, even when weaker than a child's",
          (s["state"], s["confidence"], s["finding"]) == ("leaning", "weak", fq))
    fq2, _, _ = E.cmd_finding(root, q1, "strong",
                              answer="Yes: the gain holds on every dataset we tried.")
    s = _state(root, q1)
    check("question: a strong own finding settles it",
          (s["state"], s["confidence"], s["finding"]) == ("settled", "strong", fq2))
    q3, _ = E.cmd_ask(root, "Parent question")
    q4, _ = E.cmd_ask(root, "Sub question", parent=q3)
    E.cmd_finding(root, q4, "strong", answer="The sub-question is answered.")
    check("question: a settled sub-question does not count toward its parent",
          _state(root, q4)["state"] == "settled" and _state(root, q3)["state"] == "open")
    q5, _ = E.cmd_ask(root, "Only unreadable runs")
    h5 = _hyp(root, "crashed arm", q5)
    E.cmd_finding(root, h5, "strong", why="crashed", direction="no-answer-yet")
    check("question: a child's `no answer yet` finding does not count",
          _state(root, q5)["state"] == "open")

    # the shape of a question finding (PI ruling: no direction)
    before = _dir_bytes(root)
    check("finding: a question finding with a direction is refused",
          _raises(lambda: E.cmd_finding(root, q1, "weak", answer="x", direction="supports")))
    check("finding: a question finding without answer text is refused",
          _raises(lambda: E.cmd_finding(root, q1, "weak")))
    check("finding: a hypothesis finding without a direction is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x")))
    check("finding: a hypothesis finding without a why is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", direction="supports")))
    check("finding: an unknown confidence is refused",
          _raises(lambda: E.cmd_finding(root, h1, "certain", why="x", direction="supports")))
    check("finding: an unknown direction is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x", direction="maybe")))
    check("finding: an unknown null outcome is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x", direction="supports",
                                        null="probably")))
    check("finding: the project cannot hold a finding",
          _raises(lambda: E.cmd_finding(root, "root", "weak", answer="x")))
    fids = [f.id for f in E.node_findings(E.Vault(root), h1)]
    check("finding: a finding cannot hold a finding",
          _raises(lambda: E.cmd_finding(root, fids[0], "weak", answer="x")))
    check("finding: every refusal writes nothing", _dir_bytes(root) == before)

    n = E.Vault(root).get(fq2)
    check("finding: stored as its own file with type finding, an f-id and its parent",
          n.type == "finding" and re.fullmatch(r"f\d+", n.id) and n.parent == q1
          and os.path.basename(n["path"]).startswith(n.id + "_"))
    check("finding: a question finding keeps its answer text and carries no direction",
          "every dataset" in E._section(n["body"], "Answer") and not n["fm"].get("direction"))


def _null_cap_tests(check, tmp):
    root = _vault(tmp, "null")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    f1, _, note = E.cmd_finding(root, h1, "strong", why="clean win", direction="supports",
                                null="not-ruled-out")
    n = E.Vault(root).get(f1)
    check("null cap: strong with the null not ruled out is stored as weak",
          n["fm"]["confidence"] == "weak")
    check("null cap: the caller is told the confidence was capped", bool(note))
    h2 = _hyp(root, "it helps too", q1)
    f2, _, _ = E.cmd_finding(root, h2, "moderate", why="ok win", direction="supports",
                             null="not-ruled-out")
    check("null cap: moderate is capped to weak as well",
          E.Vault(root).get(f2)["fm"]["confidence"] == "weak")
    f3, _, note3 = E.cmd_finding(root, h2, "strong", why="null excluded", direction="supports",
                                 null="ruled-out")
    check("null cap: a null that was ruled out leaves strong alone",
          E.Vault(root).get(f3)["fm"]["confidence"] == "strong" and note3 is None)
    h3 = _hyp(root, "it hurts", q1)
    f4, _, note4 = E.cmd_finding(root, h3, "strong", why="clean loss", direction="against",
                                 null="not-ruled-out")
    check("null cap: supports only — an against finding with the null not ruled out keeps "
          "strong", E.Vault(root).get(f4)["fm"]["confidence"] == "strong" and note4 is None
          and _state(root, h3)["confidence"] == "strong")
    for d in ("mixed", "no-answer-yet"):
        h = _hyp(root, f"it is {d}", q1)
        fx, _, nx = E.cmd_finding(root, h, "moderate", why="x", direction=d,
                                  null="not-ruled-out")
        check(f"null cap: a {d} finding with the null not ruled out keeps moderate",
              E.Vault(root).get(fx)["fm"]["confidence"] == "moderate" and nx is None)
    check("null cap: the capped finding validates clean", E.cmd_validate(root) == [])
    helptext = " ".join(_cli(root, "finding", "--help").stdout.split())
    check("null cap: the --null help says the cap binds a supports finding only",
          "caps a supports finding at weak" in helptext
          and "a null not ruled out caps confidence at weak" not in helptext)
    _edit_fm(root, f1, confidence="strong")
    probs = E.cmd_validate(root)
    check("null cap: validate flags a hand-edited finding that breaks the cap",
          any(i == f1 and "null" in m for i, m in probs))
    s = _state(root, h1)
    check("null cap: derivation still reads the hand-edited finding as weak",
          (s["state"], s["confidence"]) == ("leaning", "weak"))


def _evidence_tests(check, tmp):
    root = _vault(tmp, "evidence")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    _write(os.path.join(root, "results", h1, "report.md"), "# report\n")
    tid, tfn = E.cmd_task_add(root, "run the sweep", "implementation", refs=[h1],
                              blocked_by=[])
    f1, _, _ = E.cmd_finding(root, h1, "moderate", why="the sweep agrees",
                             direction="supports",
                             evidence=[f"results/{h1}/report.md", f"tasks/{tfn}"])
    check("evidence: links under results/ and tasks/ are stored in order",
          E.finding_evidence(E.Vault(root).get(f1)) == [f"results/{h1}/report.md",
                                                       f"tasks/{tfn}"])
    check("evidence: a link that does not resolve is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x", direction="supports",
                                        evidence=["results/h1/missing.md"])))
    _write(os.path.join(root, "notes.txt"), "loose\n")
    check("evidence: a link outside results/ and tasks/ is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x", direction="supports",
                                        evidence=["notes.txt"])))
    check("evidence: a link escaping the vault is refused",
          _raises(lambda: E.cmd_finding(root, h1, "weak", why="x", direction="supports",
                                        evidence=["../outside.md"])))
    check("evidence: the vault validates clean with resolving evidence",
          E.cmd_validate(root) == [])
    snap = E.snapshot(root)
    check("snapshot: a vault with tasks snapshots, and the taskhub carries no review queue",
          "queue" not in snap["tasks"] and snap["tasks"]["items"])
    os.remove(os.path.join(root, "results", h1, "report.md"))
    check("validate: evidence that stopped resolving is a problem",
          any(i == f1 and "evidence" in m for i, m in E.cmd_validate(root)))


def _validate_tests(check, tmp):
    root = _vault(tmp, "validate")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    f1, _, _ = E.cmd_finding(root, h1, "weak", why="x", direction="supports")
    check("validate: a fresh 4.0 vault with a finding is clean", E.cmd_validate(root) == [])
    rep = E.validation_report(root)
    check("validate: no `gate` check is offered any more",
          "gate" not in E.CHECKS + E.OPT_CHECKS
          and _raises(lambda: E.validation_report(root, ["gate"])))

    def probs_for(nid):
        return [m for i, m in E.cmd_validate(root) if i == nid]

    _edit_fm(root, f1, direction="sideways")
    check("validate: a bad direction is a problem", bool(probs_for(f1)))
    _edit_fm(root, f1, direction="supports", confidence="huge")
    check("validate: a bad confidence is a problem", bool(probs_for(f1)))
    _edit_fm(root, f1, confidence="weak", null="maybe")
    check("validate: a bad null outcome is a problem", bool(probs_for(f1)))
    _edit_fm(root, f1, null=None, parked=True)
    check("validate: `parked` on a finding is a problem", bool(probs_for(f1)))
    _edit_fm(root, f1, parked=None, parent="root")
    check("validate: a finding whose parent is not a question or hypothesis is a problem",
          bool(probs_for(f1)))
    _edit_fm(root, f1, parent=h1, direction=None)
    check("validate: a hypothesis finding without a direction is a problem",
          bool(probs_for(f1)))
    _edit_fm(root, f1, direction="supports")
    fq, _, _ = E.cmd_finding(root, q1, "weak", answer="maybe")
    _edit_fm(root, fq, direction="supports")
    check("validate: a question finding carrying a direction is a problem", bool(probs_for(fq)))
    _edit_fm(root, fq, direction=None)
    _edit_fm(root, "root", parked=True)
    check("validate: `parked` on the project is a problem", bool(probs_for("root")))
    _edit_fm(root, "root", parked=None)
    check("validate: back to clean", E.cmd_validate(root) == [])

    # ## Expect: required on a new hypothesis, information on a migrated one
    n = E.Vault(root).get(h1)
    body = re.sub(r"## Expect\n.*?(?=\n## )", "", n["body"], flags=re.S)
    E.write_if_changed(n["path"], E.render_doc(n["fm"], body))
    check("validate: a new hypothesis without ## Expect is a problem",
          any("Expect" in m for m in probs_for(h1)))
    _edit_fm(root, h1, schema=2)
    rep = E.validation_report(root)
    check("validate: a migrated (pre-4.0) hypothesis without ## Expect is info, not a problem",
          not any(p["id"] == h1 for p in rep["problems"])
          and any(i["id"].startswith("boundary:") and "Expect" in i["message"]
                  for i in rep["info"]))

    # retired gates: no null/rule/scenario/neutral demands on a running hypothesis
    h2 = _hyp(root, "two checks, no rule", q1, verifiables=["a", "b"])
    E.cmd_test(root, h2, to="running")
    check("validate: a running hypothesis with two checks, no rule, no null, no control and "
          "no scenarios is clean", probs_for(h2) == [])


def _removed_verb_tests(check, tmp):
    root = _vault(tmp, "removed")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    E.cmd_task_add(root, "a chore", "implementation", blocked_by=[])
    E.refresh(root)
    cases = [["review"], ["gate"], ["decide"], ["review", "--json"],
             ["answer", q1, "-t", "yes"], ["resolve", q1], ["settle", q1],
             ["pursue", q1, "--idea", "x"], ["branch", q1], ["reopen", q1],
             ["approve", "s1"], ["sign-off", "s1"],
             ["synthesize", "what it settled", "--for", q1], ["weave", "x", "--for", q1],
             ["close", h1, "-m", "+1"], ["verdict", h1],
             ["approve-null", h1], ["approve_null", h1],
             ["task", "review"], ["task", "accept", "t1"], ["task", "sign-off", "t1"],
             ["todo", "review"]]
    for argv in cases:
        before = _dir_bytes(root)
        r = _cli(root, *argv)
        lines = [l for l in r.stdout.splitlines() if l.strip()]
        check(f"removed: `crux {' '.join(argv)}` exits 0 with one pointer line and writes "
              f"nothing", r.returncode == 0 and len(lines) == 1 and not r.stderr.strip()
              and _dir_bytes(root) == before)
    for name in ("cmd_review", "cmd_answer", "cmd_pursue", "cmd_approve", "cmd_synthesize",
                 "cmd_close", "cmd_approve_null", "cmd_task_review", "cmd_task_accept",
                 "gate_warnings", "approved_synthesis"):
        check(f"removed: the engine no longer has {name}", not hasattr(E, name))
    check("removed: every removed verb has a pointer in REMOVED_VERBS",
          {"review", "answer", "pursue", "approve", "synthesize", "close", "approve-null",
           "task review", "task accept"} <= set(E.REMOVED_VERBS))


def _cli_tests(check, tmp):
    root = _vault(tmp, "cli")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    r = _cli(root, "finding", h1, "-d", "supports", "-c", "moderate", "-w",
             "three seeds agree", "--json")
    ok = r.returncode == 0
    out = json.loads(r.stdout) if ok else {}
    check("cli: `crux finding --json` records a finding and reports the parent's new state",
          ok and re.fullmatch(r"f\d+", out.get("id") or "") and out.get("parent") == h1
          and out.get("state") == "leaning" and out.get("confidence") == "moderate")
    for alias in ("record", "conclude", "land"):
        r = _cli(root, alias, h1, "-d", "against", "-c", "weak", "-w", "via " + alias)
        check(f"cli: `crux {alias}` is an alias of `crux finding`",
              r.returncode == 0 and any("via " + alias == f["fm"].get("why")
                                        for f in E.node_findings(E.Vault(root), h1)))
    r = _cli(root, "finding", q1, "-c", "strong", "-a", "Yes, robustly.", "--json")
    check("cli: a question finding takes --answer and settles the question",
          r.returncode == 0 and json.loads(r.stdout).get("state") == "settled")
    r = _cli(root, "finding", h1, "-d", "supports", "-c", "strong", "-w", "x",
             "--null", "not-ruled-out", "--json")
    check("cli: the null cap is reported on --json",
          r.returncode == 0 and json.loads(r.stdout).get("stored_confidence") == "weak"
          and json.loads(r.stdout).get("capped"))
    r = _cli(root, "finding", q1, "-d", "supports", "-c", "weak", "-a", "x")
    check("cli: a refused finding exits 1", r.returncode == 1)
    r = _cli(root, "park", h1, "--json")
    check("cli: `crux park` parks a node",
          r.returncode == 0 and _state(root, h1)["state"] == "parked")
    r = _cli(root, "park", h1, "--undo")
    check("cli: `crux park --undo` unparks it",
          r.returncode == 0 and _state(root, h1)["state"] != "parked")
    r = _cli(root, "status")
    check("cli: `crux status` prints derived states, not stored statuses",
          r.returncode == 0 and "settled" in r.stdout and "leaning" in r.stdout)


def _agents_md_tests(check, tmp):
    """Decision 10 outside Claude Code: `crux init` leaves a one-line pointer to the always-on
    core in the project's AGENTS.md: create, append, never a duplicate, nowhere else."""
    home = os.path.join(tmp, "ahome")
    os.makedirs(home)
    # USERPROFILE: Windows expands `~` from it, never from HOME
    env = dict(os.environ, CRUX_NO_UPDATE_CHECK="1", HOME=home, USERPROFILE=home)

    def init(cwd, *argv):
        os.makedirs(cwd, exist_ok=True)
        return subprocess.run([sys.executable, CLI, "init"] + list(argv), cwd=cwd, env=env,
                              capture_output=True, text=True, encoding="utf-8")

    def ptrs(path):
        lines = _read(path).splitlines() if os.path.isfile(path) else []
        return [x for x in lines if "skills/crux/SKILL.md" in x]

    def resolves(line):
        m = re.search(r"(\S*skills/crux/SKILL\.md)", line)
        p = m.group(1).strip("`") if m else ""
        return bool(p) and os.path.isfile(os.path.expanduser(p.replace("~", home, 1))
                                          if p.startswith("~") else p)

    outer = os.path.join(tmp, "aouter")
    proj = os.path.join(outer, "proj")
    r = init(proj, "Pointer project")
    am = os.path.join(proj, "AGENTS.md")
    check("agents.md: `crux init` creates AGENTS.md with one pointer to the core",
          r.returncode == 0 and len(ptrs(am)) == 1 and len(_read(am).splitlines()) == 1)
    check("agents.md: ... and the pointer names a SKILL.md that exists",
          bool(ptrs(am)) and resolves(ptrs(am)[0]))
    check("agents.md: ... and nothing outside the project is touched",
          not os.path.exists(os.path.join(outer, "AGENTS.md"))
          and not os.path.exists(os.path.join(proj, "cruxvault", "AGENTS.md")))

    proj2 = os.path.join(tmp, "aproj2")
    own = "# Project rules\n\nRun the tests before a commit."     # no trailing newline
    _write(os.path.join(proj2, "AGENTS.md"), own)
    r = init(proj2, "Second project")
    am2 = os.path.join(proj2, "AGENTS.md")
    text = _read(am2)
    check("agents.md: an existing AGENTS.md keeps its text and gets the pointer appended",
          r.returncode == 0 and text.startswith(own + "\n") and len(ptrs(am2)) == 1
          and text.rstrip("\n").splitlines()[-1] == ptrs(am2)[0])

    r2 = init(proj2, "Again", "--dir", "second")
    r3 = init(proj2, "Again")                                     # refused: vault exists
    check("agents.md: a repeated init never writes a duplicate pointer",
          r2.returncode == 0 and r3.returncode != 0 and len(ptrs(am2)) == 1
          and _read(am2) == text)

    proj3 = os.path.join(tmp, "aproj3")
    _write(os.path.join(proj3, "AGENTS.md"), "keep me\n")
    _write(os.path.join(proj3, "cruxvault", E.VAULT_MARKER), "title: x\n")
    r = init(proj3, "Exists")
    check("agents.md: a refused init leaves AGENTS.md untouched",
          r.returncode != 0 and _read(os.path.join(proj3, "AGENTS.md")) == "keep me\n")

    proj4 = os.path.join(tmp, "aproj4")
    seed = os.path.join(proj4, "seed.md")
    _write(seed, "- Project: Seeded — a goal\n  - Q: does it work\n")
    r = init(proj4, "--from", seed)
    check("agents.md: `crux init --from` adds the pointer too",
          r.returncode == 0 and len(ptrs(os.path.join(proj4, "AGENTS.md"))) == 1)

    # install.sh links skills/crux into ~/.agents/skills for non-Claude agents: when that
    # link resolves to this core, the pointer names it portably, not by this machine's path.
    os.makedirs(os.path.join(home, ".agents", "skills"))
    try:
        os.symlink(os.path.dirname(HERE), os.path.join(home, ".agents", "skills", "crux"),
                   target_is_directory=True)
    except (OSError, NotImplementedError):
        print("  skip   agents.md: ~/.agents/skills/crux pointer (this platform disallows "
              "symlinks)")
        return
    proj5 = os.path.join(tmp, "aproj5")
    r = init(proj5, "Installed")
    p5 = ptrs(os.path.join(proj5, "AGENTS.md"))
    check("agents.md: an installed crux skill is named as ~/.agents/skills/crux/SKILL.md",
          r.returncode == 0 and len(p5) == 1 and "`~/.agents/skills/crux/SKILL.md`" in p5[0]
          and resolves(p5[0]))


def _derive_only_tests(check, tmp):
    """The engine never writes a direction or a confidence it was not given."""
    root = _vault(tmp, "derive")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1, verifiables=["metric +1"])
    E.cmd_test(root, h1, to="running")
    n = E.Vault(root).get(h1)
    E.write_if_changed(n["path"], E.render_doc(
        n["fm"], n["body"].replace("- [ ] metric +1", "- [x] metric +1")))
    E.refresh(root)
    v = E.Vault(root)
    check("derive: ticking every check and refreshing writes no finding",
          not [x for x in v.nodes.values() if x.type == "finding"])
    check("derive: and leaves the hypothesis open", _state(root, h1)["state"] == "open")
    f1, _, _ = E.cmd_finding(root, h1, "moderate", why="ticked", direction="mixed")
    fb = _read(E.Vault(root).get(f1)["path"])
    E.refresh(root); E.snapshot(root); E.cmd_validate(root); E.status_text(root)
    check("derive: refresh / snapshot / validate / status leave a finding byte-identical",
          _read(E.Vault(root).get(f1)["path"]) == fb)
    v = E.Vault(root)
    check("derive: the finding stores exactly the direction and confidence it was given",
          v.get(f1)["fm"]["direction"] == "mixed" and v.get(f1)["fm"]["confidence"] == "moderate")
    check("derive: no question or hypothesis file stores a direction, confidence or state",
          not any(k in x["fm"] for x in v.nodes.values() if x.type in ("question", "idea")
                  for k in ("direction", "confidence", "state", "verdict")))
    check("derive: refresh no longer trips a question to `review`",
          "review" not in _read(v.get(q1)["path"]).split("---")[1])
    check("derive: refresh is idempotent", E.refresh(root) is False)


def _snapshot_tests(check, tmp):
    root = _vault(tmp, "snap")
    q1, _ = E.cmd_ask(root, "Does it help?")
    h1 = _hyp(root, "it helps", q1)
    _write(os.path.join(root, "results", h1, "report.md"), "# r\n")
    f1, _, _ = E.cmd_finding(root, h1, "strong", why="clean", direction="supports",
                             evidence=[f"results/{h1}/report.md"], null="ruled-out",
                             vs_expect="as expected", verifiables="both checks passed")
    snap = E.snapshot(root)
    check("snapshot: no `queue` key", "queue" not in snap)
    hn, qn = snap["nodes"][h1], snap["nodes"][q1]
    check("snapshot: a hypothesis carries state and confidence",
          hn.get("state") == "settled" and hn.get("confidence") == "strong")
    check("snapshot: a question carries state and confidence",
          qn.get("state") == "leaning" and qn.get("confidence") == "moderate")
    fl = hn.get("findings")
    check("snapshot: a hypothesis lists its findings with direction, confidence, why and "
          "evidence", isinstance(fl, list) and len(fl) == 1 and fl[0]["id"] == f1
          and fl[0]["direction"] == "supports" and fl[0]["confidence"] == "strong"
          and fl[0]["why"] == "clean" and fl[0]["evidence"] == [f"results/{h1}/report.md"]
          and fl[0]["null"] == "ruled-out" and fl[0]["vs_expect"] == "as expected")
    check("snapshot: a question lists its own findings (none here)", qn.get("findings") == [])
    check("snapshot: findings are not tree nodes",
          f1 not in snap["nodes"] and f1 not in json.dumps(snap["tree"]))
    check("snapshot: the vocabulary is published",
          snap.get("vocab", {}).get("states") == list(E.STATES)
          and snap["vocab"].get("confidences") == list(E.CONFIDENCES)
          and snap["vocab"].get("directions") == list(E.DIRECTIONS))
    check("snapshot: node_json for one hypothesis carries the same state",
          E.node_json(root, h1)["state"] == "settled")


_ALLOC = r"""
import sys
sys.path.insert(0, sys.argv[1])
import engine as E
root, n = sys.argv[2], int(sys.argv[3])
ids = [E._new_id(E.Vault(root), "question") for _ in range(n)]
print(" ".join(ids))
"""


def _lock_tests(check, tmp):
    root = _vault(tmp, "lock")
    script = os.path.join(tmp, "alloc.py")
    _write(script, _ALLOC)
    procs = [subprocess.Popen([sys.executable, script, HERE, root, "30"],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
             for _ in range(4)]
    outs = [p.communicate(timeout=120) for p in procs]
    ids = [i for o, _e in outs for i in o.split()]
    check("lock: four processes allocating 30 ids each all succeed",
          all(p.returncode == 0 for p in procs) and len(ids) == 120)
    check("lock: concurrent _new_id calls never return the same id",
          len(set(ids)) == len(ids))
    cfg = E.yaml_load(_read(os.path.join(root, E.VAULT_MARKER)))
    check("lock: the counter equals the number of ids handed out", cfg.get("counter_q") == 120)
    check("lock: the lock file is released afterwards",
          not os.path.exists(os.path.join(root, E.LOCK_FILE)))
    # a stale lock (a crashed writer) does not wedge the vault forever
    _write(os.path.join(root, E.LOCK_FILE), "dead\n")
    old = os.path.getmtime(os.path.join(root, E.LOCK_FILE)) - 3600
    os.utime(os.path.join(root, E.LOCK_FILE), (old, old))
    ok = True
    try:
        E._new_id(E.Vault(root), "question")
    except Exception:
        ok = False
    check("lock: a stale lock older than the timeout is broken, not waited on forever", ok)
    check("lock: finding ids come from their own counter",
          E._new_id(E.Vault(root), "finding") == "f1")

    # A long holder is not a dead one: the 4.0 migration holds the lock while it copies a
    # backup (one real vault is 590 MB), and breaking its lock lets a second process roll
    # back a migration still in progress. Age alone never breaks a lock whose holder lives.
    import socket
    lp = os.path.join(root, E.LOCK_FILE)
    def aged(text, secs=3600):
        _write(lp, text)
        t = os.path.getmtime(lp) - secs
        os.utime(lp, (t, t))
    def takes(timeout=0.3):
        try:
            with E.id_lock(root, timeout=timeout):
                return True
        except E.CruxError:
            return False
    aged(f"{os.getpid()} {socket.gethostname()}\n", secs=2 * E.LOCK_TIMEOUT)
    check("lock: a lock held by a live process for longer than 30 s is not broken",
          not takes() and os.path.exists(lp)
          and _read(lp).split()[0] == str(os.getpid()))
    dead = subprocess.Popen([sys.executable, "-c", "pass"])
    dead.wait()
    aged(f"{dead.pid} {socket.gethostname()}\n")
    check("lock: an old lock whose holder on this host is dead is broken", takes())
    aged(f"{os.getpid()} some-other-host.invalid\n", secs=2 * E.LOCK_TIMEOUT)
    check("lock: a lock from another host is not broken on the 30 s age alone",
          not takes() and os.path.exists(lp))
    check("lock: an oversized pid is an unknown holder, never a crash",
          E._pid_alive(99999999999) is None)
    aged(f"99999999999 {socket.gethostname()}\n", secs=2 * E.LOCK_TIMEOUT)
    check("lock: ... so its lock waits for the foreign bound instead of breaking",
          not takes() and os.path.exists(lp))

    # The break race: A reads a dead holder, then B breaks that lock and takes a fresh one
    # before A acts. A must not remove B's live lock.
    dead2 = subprocess.Popen([sys.executable, "-c", "pass"])
    dead2.wait()
    aged(f"{dead2.pid} {socket.gethostname()}\n")
    b_stamp = f"{os.getpid()} {socket.gethostname()}\n"
    real = E.id_lock._stale_after
    fired = []
    def racing(self):
        res = real(self)
        if not fired:
            fired.append(1)
            os.remove(lp)               # B breaks the dead lock ...
            _write(lp, b_stamp)         # ... and takes its own, live and fresh
        return res
    E.id_lock._stale_after = racing
    try:
        a_took = takes()
    finally:
        E.id_lock._stale_after = real
    check("lock: a waiter that loses the break race never removes the new holder's lock",
          fired and not a_took and os.path.exists(lp) and _read(lp) == b_stamp
          and not [f for f in os.listdir(root) if f.endswith(".stale")])

    os.remove(lp)
    with E.id_lock(root):
        held = _read(lp).split()
    check("lock: the lock file names its holder's pid and host",
          held == [str(os.getpid()), socket.gethostname()])


def _auto_status_tests(check, tmp):
    """The text `crux auto status` carries each attempt's Finding (direction and confidence),
    which its --json form already did."""
    root = _vault(tmp, "autostatus")
    run = os.path.join(root, "auto", "q1")
    os.makedirs(run)
    _write(os.path.join(run, "plan.md"), "---\nobjective: m.json:acc max 0.5\n---\n")
    rows = [{"event": "setup", "baseline": 0.5, "noise": 0.01, "at": "2026-10-31T10:00:00Z"},
            {"event": "attempt", "n": 1, "id": "h7", "parent": "base", "score": 0.7,
             "status": "kept", "seconds": 3, "at": "2026-10-31T10:05:00Z", "finding": "f11",
             "direction": "supports", "confidence": "strong"},
            {"event": "attempt", "n": 2, "id": "h8", "parent": "h7", "score": 0.3,
             "status": "rejected", "seconds": 3, "at": "2026-10-31T10:10:00Z",
             "finding": "f12", "direction": "against", "confidence": "moderate"}]
    _write(os.path.join(run, "ledger.jsonl"), "".join(json.dumps(r) + "\n" for r in rows))
    out = _cli(root, "auto", "status", "q1").stdout
    lines = {l.split()[0]: l for l in out.splitlines() if l.startswith("  ") and l.split()}
    check("auto status: the text attempt line names its finding, direction and confidence",
          "f11" in lines.get("1", "") and "supports" in lines.get("1", "")
          and "strong" in lines.get("1", "")
          and "f12" in lines.get("2", "") and "against" in lines.get("2", "")
          and "moderate" in lines.get("2", ""))


SEED4 = """\
- Project: Seeded four — the 4.0 seed shape
  - Q: Does A help?
    - H: [tested] A helps
      - expect: A beats the baseline by 1 point
      - v: [x] metric >= +0.01 (found: +0.02)
      - finding: [supports, moderate] A cleared the bar on one dataset.
    - H: [tested] B helps
      - v: [x] metric >= +0.01
      - finding: B cleared it, in the old shape.
    - H: C helps
      - expect: C beats the baseline
"""


def _seed_tests(check, tmp):
    seed = os.path.join(tmp, "seed4.md")
    _write(seed, SEED4)
    root = os.path.join(tmp, "seeded")
    E.cmd_init_from(seed, root)
    v = E.Vault(root)
    fs = E.node_findings(v, "h1")
    check("seed: `- finding: [direction, confidence] …` becomes a finding with exactly those "
          "values", len(fs) == 1 and fs[0]["fm"].get("direction") == "supports"
          and fs[0]["fm"].get("confidence") == "moderate"
          and "one dataset" in fs[0]["fm"].get("why", ""))
    check("seed: `- expect:` lands in ## Expect", "1 point" in E.expect_text(v.get("h1"))
          and "beats the baseline" in E.expect_text(v.get("h3")))
    check("seed: an old-shape finding line writes NO finding (the engine invents no direction)",
          E.node_findings(v, "h2") == [] and E.derive_state(v, "h2")["state"] == "open")
    check("seed: the seeded question reads its child's finding, capped",
          E.derive_state(v, "q1")["state"] == "leaning")


def run_all(check):
    tmp = tempfile.mkdtemp(prefix="crux_memory_")
    try:
        for section in (_model_tests, _hypothesize_tests, _state_tests, _question_tests,
                        _null_cap_tests, _evidence_tests, _validate_tests,
                        _removed_verb_tests, _cli_tests, _agents_md_tests, _derive_only_tests,
                        _snapshot_tests, _seed_tests, _lock_tests, _auto_status_tests):
            try:
                if section is _model_tests:
                    section(check)
                else:
                    section(check, tmp)
            except Exception as e:      # an unexpected result is a FAIL line, never a traceback
                check(f"memory: {section.__name__} crashed: {type(e).__name__}: {e}", False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    passed, failed = [], []

    def check(name, cond):
        (passed if cond else failed).append(name)
        print(("  ok   " if cond else "  FAIL ") + name)
    run_all(check)
    print(f"\n  PASSED {len(passed)} / {len(passed) + len(failed)}")
    if failed:
        print("  FAILED:\n" + "\n".join("    " + f for f in failed))
        sys.exit(1)
    print("  ALL GREEN")


if __name__ == "__main__":
    main()
