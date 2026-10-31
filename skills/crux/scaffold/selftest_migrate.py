#!/usr/bin/env python3
"""Self-test for the 3.x -> 4.0 migration (spec 19, chunk C2): one assert per row of the
migration table and of the PI rulings Q4-Q6, the backup, idempotence, crash recovery, the
pure `plan`, the pending store and the disagreement report.

    python3 selftest_migrate.py       # standalone: prints PASSED a / b, exits 1 on any failure

`run_all(check)` takes selftest.py's `check(name, cond)`, so the counts aggregate there. Every
test runs in a temp dir built from a hand-written 3.5 fixture (`build_legacy_vault`), because
a 4.0 engine can no longer write a verdict. No network, no tokens."""
import os, sys, json, shutil, subprocess, tempfile, hashlib, io, contextlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import engine as E

CLI = os.path.join(HERE, "crux.py")


# ------------------------------------------------------------------------------- helpers
def _read(p):
    with open(p, encoding="utf-8") as f:
        return f.read()


def _write(p, text):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(text)


def tree_hashes(root, skip=(".crux", ".git")):
    """relpath -> sha256 of every file under `root`, skipping the top-level `skip` dirs."""
    out = {}
    for dirpath, dirnames, filenames in os.walk(root):
        if os.path.abspath(dirpath) == os.path.abspath(root):
            dirnames[:] = [d for d in dirnames if d not in skip]
        for fn in filenames:
            p = os.path.join(dirpath, fn)
            with open(p, "rb") as f:
                out[os.path.relpath(p, root).replace(os.sep, "/")] = hashlib.sha256(f.read()).hexdigest()
    return out


def _hyp_text(hid, parent, parent_base, title, verdict=None, status="done", checks=(),
              schema=2, rule=None, null=None, extra_fm=None, artifacts=(), updated=None):
    """One 3.x hypothesis file. `checks` is [(tick, text, discriminates)] where tick is
    'x' (met), ' ' (unmet) or '-' (could not evaluate); a text may lead with
    `[outcome-neutral]`."""
    fm = {"id": hid, "type": "idea"}
    if schema:
        fm["schema"] = schema
    fm.update({"title": title, "parent": parent, "status": status})
    if rule:
        fm["rule"] = rule
    if verdict:
        fm["verdict"] = verdict
    fm["created"] = "2026-07-01T10:00:00"
    fm["updated"] = updated or "2026-07-02T10:00:00"
    fm.update(extra_fm or {})
    lines = [f"# {hid} — {title}", "", f"Parent:: [[{parent_base}]]", "",
             "## ELI5", "", f"An easy line about {title}.", "", "## TL;DR", "",
             f"A paragraph about {title}.", ""]
    if null is not None:
        lines += ["## Null", "", null, ""]
    lines += ["## Idea / Hypothesis", "", title, "", "## Verifiables", ""]
    for i, (tick, text, disc) in enumerate(checks):
        lines.append(f"- [{tick}] {text}")
        if schema >= 2:
            lines.append(f"      fails-if:: world {i + 1}")
            if disc:
                lines.append("      discriminates:: true")
    lines += ["", "## Run Links", "", "- the lab notebook, week 2", "", "## Artifacts", ""]
    lines += [f"- {a}" for a in artifacts] or ["_(none yet)_"]
    lines += ["", "## Findings", "", f"Narrative findings for {hid}.", ""]
    return E.render_doc(fm, "\n".join(lines))


# The fixture's rows: hid -> (verdict, status, checks, rule, schema, null, expected)
# expected = (direction, confidence) or None for "no finding".
NULL_TXT = "chance — one lucky run would show this on its own"
ROWS = {
    # supported: all claim checks pass -> strong (the discriminating check passed: null ruled out)
    "h1": ("supported", "done", [("x", "A beats B", True), ("x", "B never crashes", False),
                                 ("x", "[outcome-neutral] the baseline reproduces", False)],
           "all", 2, NULL_TXT, ("supports", "strong")),
    # supported, one claim check missed -> moderate
    "h2": ("supported", "done", [("x", "A beats B", True), (" ", "A beats C", False)],
           "any", 2, NULL_TXT, ("supports", "moderate")),
    # supported, two claim checks missed -> weak
    "h3": ("supported", "done", [("x", "A beats B", True), (" ", "A beats C", False),
                                 ("-", "A beats D", False)],
           "any", 2, NULL_TXT, ("supports", "weak")),
    # supported, but the check aimed at the null failed -> the null is not ruled out -> weak
    "h4": ("supported", "done", [("x", "A beats B", False), (" ", "A beats B at equal size", True)],
           "any", 2, NULL_TXT, ("supports", "weak")),
    # supported, but a control check failed -> capped at weak
    "h5": ("supported", "done", [("x", "A beats B", False), ("x", "A beats C", False),
                                 (" ", "[outcome-neutral] the baseline reproduces", False)],
           None, 0, None, ("supports", "weak")),
    # refuted, every claim check failed -> strong against
    "h6": ("refuted", "done", [(" ", "A beats B", True), (" ", "A beats C", False)],
           "all", 2, NULL_TXT, ("against", "strong")),
    # refuted, one claim check passed -> moderate against
    "h7": ("refuted", "done", [("x", "A beats B", True), (" ", "A beats C", False)],
           "all", 2, NULL_TXT, ("against", "moderate")),
    # partial -> mixed, weak
    "h8": ("partial", "done", [("x", "A beats B", False), (" ", "A beats C", False)],
           None, 0, None, ("mixed", "weak")),
    # inconclusive -> mixed, weak
    "h9": ("inconclusive", "done", [("x", "A beats B", True), ("-", "A beats C", False)],
           "all", 2, NULL_TXT, ("mixed", "weak")),
    # invalid-run -> no answer yet, the run kept as evidence
    "h10": ("invalid-run", "done", [("x", "A beats B", True),
                                    (" ", "[outcome-neutral] the baseline reproduces", False)],
            "all", 2, NULL_TXT, ("no-answer-yet", "weak")),
    # never closed -> no Finding
    "h11": (None, "running", [(" ", "A beats B", True)], "all", 2, NULL_TXT, None),
    # every claim check passed, but the checks were edited after the run started -> moderate
    "h12": ("supported", "done", [("x", "A beats B", True), ("x", "A beats C", False)],
            "all", 2, NULL_TXT, ("supports", "moderate")),
    # a seeded, reconstructed lock is history, not a pre-registration: no cap
    "h13": ("supported", "done", [("x", "A beats B", True)], "all", 2, NULL_TXT,
            ("supports", "strong")),
    # never closed, and no experiment refs it -> no Finding at all, the state stays open
    "h14": (None, "idea", [], None, 2, None, None),
}


def build_legacy_vault(root, stamp="3.5"):
    """A 3.5-shaped vault covering every migration row. Written by hand: a 4.0 engine cannot
    write a verdict, a synthesis or an accepted experiment any more."""
    if os.path.exists(root):
        shutil.rmtree(root)
    E.cmd_init("Legacy Lab", root)
    q1, _ = E.cmd_ask(root, "Does A beat B?")
    q2, _ = E.cmd_ask(root, "Why does A beat B?")
    v = E.Vault(root)
    qb = {q: v.get(q).basename for q in (q1, q2)}
    for hid, (verdict, status, checks, rule, schema, null, _exp) in ROWS.items():
        parent = q1 if int(hid[1:]) <= 7 else q2
        title = f"hypothesis {hid} holds"
        arts = []
        if hid == "h10":
            _write(os.path.join(root, "results", "h10", "report.md"), "# h10 run\n\ncontrol failed\n")
            arts = ["[Report](results/h10/report.md)"]
        _write(os.path.join(root, f"{hid}_hypothesis_{hid}_holds.md"),
               _hyp_text(hid, parent, qb[parent], title, verdict, status, checks, schema,
                         rule, null, artifacts=arts,
                         updated=f"2026-07-{int(hid[1:]) + 2:02d}T10:00:00"))
    # locks: h12 locked at running, then a check edited; h13 sealed as reconstructed
    for hid, where in (("h12", "running"), ("h13", E.RECONSTRUCTED)):
        n = E.Vault(root).get(hid)
        n["fm"][E.LOCK_FIELD] = E.lock_hash(n)
        n["fm"][E.LOCKED_AT_FIELD] = "2026-07-01T11:00:00"
        n["fm"][E.LOCK_WHERE_FIELD] = where
        _write(n["path"], E.render_doc(n["fm"], n["body"]))
    p12 = E.Vault(root).get("h12")["path"]
    _write(p12, _read(p12).replace("- [x] A beats C", "- [x] A beats C on two datasets"))
    # syntheses: s1 approved (closes q1), s2 never approved
    for sid, qid, approved, title in (("s1", q1, "2026-07-20T09:00:00", "A wins on paper"),
                                      ("s2", q2, None, "Why A wins is still open")):
        fm = {"id": sid, "type": "synthesis", "title": title, "approved": approved,
              "created": "2026-07-19T09:00:00", "updated": "2026-07-19T09:00:00"}
        body = (f"# Synthesis — {title}\n\nRelated:: [[{qb[qid]}]]\n\n## Headline conclusions\n\n"
                f"- {title}: the headline of {sid}.\n\n## Cross-run table\n\n"
                f"| run | score |\n|---|---|\n| a | 1 |\n\n## Implications for next batch\n\n"
                f"Next: more of {sid}.\n")
        _write(os.path.join(root, f"{sid}_{E.slugify(title)}.md"), E.render_doc(fm, body))
    # a 3.x question closed by an approved synthesis points at it
    q = E.Vault(root).get(q1)
    q["fm"]["synthesis"] = "s1"
    _write(q["path"], E.render_doc(q["fm"], q["body"]))
    # experiment tasks
    E.ensure_tasks(root)
    _write(os.path.join(root, "results", "runs", "t1.csv"), "run,score\na,1\n")
    tasks = [
        # accepted, disagrees with h1's own verdict (supported)
        ("t1", "Rerun A against B", "h1:refuted", "done", "2026-07-25T09:00:00",
         "results/runs/t1.csv"),
        # unaccepted, agrees with h6 (refuted)
        ("t2", "Rerun A against C", "h6:refuted", "done", None, "results/runs/t1.csv"),
        # dropped, disagrees with h7 (refuted)
        ("t3", "Try A on D", "h7:supported", "dropped", None, None),
        # accepted on a hypothesis that was never closed
        ("t4", "Pilot of h11", "h11:supported", "done", "2026-07-26T09:00:00",
         "results/runs/t1.csv"),
    ]
    for tid, title, refs, status, accepted, out in tasks:
        fm = {"id": tid, "type": "task", "title": title, "category": "implementation",
              "parent": None, "blocked_by": "None", "refs": q1, "hypothesis_refs": refs,
              "status": status, "created": "2026-07-21T09:00:00",
              "updated": "2026-07-21T09:00:00"}
        if accepted:
            fm["accepted"] = accepted
        body = (f"# {tid} — {title}\n\n## Why\n\nBecause.\n\n## Output\n\n"
                + (f"- {out}\n" if out else "_(none)_\n")
                + f"\n## Evidence\n\nWhat {tid} showed.\n")
        _write(os.path.join(root, "tasks", f"{tid}_{E.slugify(title)}.md"), E.render_doc(fm, body))
    cfg = E.yaml_load(_read(os.path.join(root, E.VAULT_MARKER)))
    cfg.update({"engine_version": stamp, "counter_h": len(ROWS), "counter_s": 2,
                "counter_t": len(tasks)})
    cfg.pop("counter_f", None)
    _write(os.path.join(root, E.VAULT_MARKER), E.yaml_dump(cfg) + "\n")
    return {"q1": q1, "q2": q2}


def captured_demo(dst, stamp="1.2"):
    """The shipped demo_vault as it was before the 4.0 migration (7f7529c), rebuilt from the
    committed 4.0 copy. Exact for every node file: the migration left demo's hypothesis and
    question files byte-unchanged (outside the generated ledger) and only ADDED Findings that
    carry `migrated_from`, so removing those and restoring the stamp gives the 1.2 vault."""
    if os.path.exists(dst):
        shutil.rmtree(dst)
    shutil.copytree(os.path.join(HERE, "..", "examples", "demo_vault"), dst)
    for n in list(E.Vault(dst).nodes.values()):
        if n.type == "finding" and n["fm"].get("migrated_from"):
            os.remove(n["path"])
    cfgp = os.path.join(dst, E.VAULT_MARKER)
    cfg = E.yaml_load(_read(cfgp))
    cfg.pop("counter_f", None)
    cfg["engine_version"] = stamp
    _write(cfgp, E.yaml_dump(cfg) + "\n")
    return dst


def _findings(root):
    v = E.Vault(root)
    return {f.id: f for f in v.nodes.values() if f.type == "finding"}


def _by_source(root):
    """migrated_from -> finding node."""
    return {str(f["fm"].get("migrated_from")): f for f in _findings(root).values()}


def _cli(root, *argv):
    return subprocess.run([sys.executable, CLI] + list(argv), capture_output=True, cwd=root,
                          encoding="utf-8", errors="replace",
                          env=dict(os.environ, CRUX_NO_UPDATE_CHECK="1"))


# ------------------------------------------------------------------------------- tests
def _import_tests(check, tmp):
    import migrate4 as M
    check("mig4: migrate4 imports and exposes plan / apply / rollback",
          all(callable(getattr(M, x, None)) for x in ("plan", "apply", "rollback",
                                                      "migrate_on_load", "needs_migration")))
    check("mig4: needs_migration — 3.5, 1.2 and an unversioned vault migrate; 4.0 and later do not",
          M.needs_migration("3.5") and M.needs_migration("1.2") and M.needs_migration(None)
          and not M.needs_migration("4.0") and not M.needs_migration("4.1")
          and not M.needs_migration("10.0"))


def _plan_tests(check, tmp):
    import migrate4 as M
    root = os.path.join(tmp, "plan")
    build_legacy_vault(root)
    before = tree_hashes(root, skip=())
    p = M.plan(root)
    check("mig4: plan is pure — it writes no byte, and creates no .crux/",
          tree_hashes(root, skip=()) == before and not os.path.exists(os.path.join(root, ".crux")))
    check("mig4: plan is deterministic", json.dumps(M.plan(root), sort_keys=True)
          == json.dumps(p, sort_keys=True))
    check("mig4: plan names its changes (writes, removes, pending, disagreements)",
          all(k in p for k in ("findings", "writes", "removes", "pending", "disagreements",
                               "skipped", "from", "to")))
    check("mig4: plan targets the running engine", p["to"] == E.ENGINE_VERSION and p["from"] == "3.5")
    check("mig4: plan removes both legacy syntheses",
          sorted(os.path.basename(x)[:2] for x in p["removes"]) == ["s1", "s2"])


def _table_tests(check, tmp):
    import migrate4 as M
    root = os.path.join(tmp, "table")
    qs = build_legacy_vault(root)
    hyp_before = {fn: _read(os.path.join(root, fn)) for fn in os.listdir(root)
                  if fn.startswith("h") and fn.endswith(".md")}
    warn = E.check_and_stamp_version(root)
    check("mig4: the first write-capable load migrates and says so, naming the old version",
          warn is not None and "migrated" in warn and "3.5" in warn)
    check("mig4: the vault is stamped 4.0 after migration",
          str(E.Vault(root).cfg.get("engine_version")) == E.ENGINE_VERSION)
    by = _by_source(root)
    for hid, row in ROWS.items():
        exp = row[-1]
        f = by.get(hid)
        if exp is None:
            v = E.Vault(root)
            want = ["t4:h11"] if hid == "h11" else []
            check(f"mig4: {hid} (never closed) gets no verdict Finding (findings: {want})",
                  f is None and [str(x["fm"].get("migrated_from"))
                                 for x in E.node_findings(v, hid)] == want)
            if not want:
                check(f"mig4: {hid} (never closed, no experiment) stays open",
                      E.derive_state(v, hid)["state"] == "open")
            continue
        got = (f["fm"].get("direction"), f["fm"].get("confidence")) if f else None
        check(f"mig4: {hid} ({row[0]}) -> {exp[0]}, {exp[1]} (got {got})", got == exp)
        check(f"mig4: {hid}'s Finding hangs under {hid}", f is not None and f.parent == hid)
        check(f"mig4: {hid}'s Finding says why in one sentence",
              f is not None and str(f["fm"].get("why") or "").strip() != ""
              and "\n" not in str(f["fm"].get("why")))
    f4 = by.get("h4")
    check("mig4: a null not ruled out is recorded as such on the Finding",
          f4 is not None and f4["fm"].get("null") == E.NULL_NOT_RULED_OUT)
    check("mig4: a null ruled out by its discriminating check is recorded as ruled out",
          by.get("h1") is not None and by["h1"]["fm"].get("null") == "ruled-out")
    check("mig4: a hypothesis with no declared null records none",
          by.get("h5") is not None and by["h5"]["fm"].get("null") == "none")
    check("mig4: the control cap names the failed control",
          by.get("h5") is not None and "control" in by["h5"]["fm"].get("why", ""))
    w12 = str(by["h12"]["fm"].get("why") or "") if by.get("h12") else ""
    check("mig4: checks edited after the run started cap at moderate, and the reason names "
          "the edit", "edited" in w12 and "2026-07-01T11:00:00" in w12)
    check("mig4: a reconstructed lock is no cap", by.get("h13") is not None
          and by["h13"]["fm"].get("confidence") == "strong")
    ev10 = E.finding_evidence(by["h10"]) if by.get("h10") else []
    check("mig4: invalid-run keeps the run as evidence", "results/h10/report.md" in ev10)
    check("mig4: an invalid run never sets the state (no answer yet)",
          E.derive_state(E.Vault(root), "h10")["state"] == "open")
    check("mig4: a migrated Finding is dated by the closure, not by the migration",
          by.get("h1") is not None and str(by["h1"]["fm"].get("created")) == "2026-07-03T10:00:00")
    check("mig4: derived states follow — h1 settled, h2 leaning",
          E.derive_state(E.Vault(root), "h1")["state"] == "settled"
          and E.derive_state(E.Vault(root), "h2")["state"] == "leaning")

    # syntheses
    v = E.Vault(root)
    qf = [f for f in node_findings_all(v) if f.parent == qs["q1"]]
    check("mig4: an approved synthesis becomes ONE strong Question Finding on its question",
          len(qf) == 1 and qf[0]["fm"].get("confidence") == "strong")
    check("mig4: the Question Finding carries no direction",
          len(qf) == 1 and qf[0]["fm"].get("direction") in (None, ""))
    ans = E._section(qf[0]["body"], "Answer") if qf else ""
    check("mig4: the synthesis text is kept in the Answer, every authored line",
          "A wins on paper" in ans and "the headline of s1" in ans and "| a | 1 |" in ans
          and "Next: more of s1." in ans)
    check("mig4: the approved synthesis settles its question",
          E.derive_state(v, qs["q1"])["state"] == "settled")
    check("mig4: the question's pointer to the removed synthesis is dropped",
          "synthesis" not in v.get(qs["q1"])["fm"])
    check("mig4: the Question Finding names its synthesis by file name, never by a dead id",
          len(qf) == 1 and str(qf[0]["fm"].get("migrated_from")).startswith("s1_")
          and not E.NODE_ID_RE.search(str(qf[0]["fm"].get("migrated_from")).split(":")[0]))
    check("mig4: no synthesis node is left in the tree",
          not any(n.type == "synthesis" for n in v.nodes.values()))
    check("mig4: an unapproved synthesis writes no Finding",
          not any(f.parent == qs["q2"] for f in node_findings_all(v)))

    # experiment tasks
    t1 = by.get("t1:h1")
    check("mig4: an accepted experiment becomes a moderate Finding on its hypothesis",
          t1 is not None and t1.parent == "h1" and t1["fm"].get("confidence") == "moderate"
          and t1["fm"].get("direction") == "against")
    check("mig4: the experiment Finding links the task and its output",
          t1 is not None and any(e.startswith("tasks/t1_") for e in E.finding_evidence(t1))
          and "results/runs/t1.csv" in E.finding_evidence(t1))
    check("mig4: an accepted experiment on a never-closed hypothesis still lands",
          by.get("t4:h11") is not None and by["t4:h11"]["fm"].get("direction") == "supports")
    check("mig4: an unaccepted experiment writes no Finding", "t2:h6" not in by)
    check("mig4: a dropped experiment writes nothing", "t3:h7" not in by)

    # pending store
    pend = M.read_pending(root)
    kinds = sorted((p["kind"], p["origin"], p["parent"]) for p in pend)
    check(f"mig4: pending holds the unapproved synthesis and the unaccepted experiment only "
          f"(got {kinds})", kinds == [("experiment", "t2", "h6"), ("synthesis", "s2", qs["q2"])])
    check("mig4: every pending line is one JSON object with the documented keys",
          all(set(M.PENDING_KEYS) <= set(p) for p in pend)
          and all(p["status"] == "pending" for p in pend))
    raw = _read(os.path.join(root, M.PENDING_FILE)).splitlines()
    check("mig4: the pending store is JSON lines", len(raw) == len(pend)
          and all(json.loads(l) for l in raw))
    s2 = [p for p in pend if p["kind"] == "synthesis"]
    check("mig4: the pending synthesis keeps its text",
          s2 and "the headline of s2" in s2[0]["proposal"]["answer"])
    check("mig4: .crux/ ignores itself in git",
          _read(os.path.join(root, M.CRUX_DIR, ".gitignore")).strip() == "*")

    # report
    rep = json.loads(_read(os.path.join(root, M.REPORT_FILE)))
    dis = sorted((d["task"], d["hypothesis"], d["conclusion"], d["verdict"])
                 for d in rep["disagreements"])
    check(f"mig4: the report lists every experiment that disagrees with its hypothesis' "
          f"verdict (got {dis})",
          dis == [("t1", "h1", "refuted", "supported"), ("t3", "h7", "supported", "refuted")])
    check("mig4: the report lists every Finding written",
          sorted(r["id"] for r in rep["findings"]) == sorted(_findings(root)))
    check("mig4: the report lists the never-closed hypothesis as skipped",
          {"h11", "h14"} <= {s["id"] for s in rep["skipped"]})

    # what is kept
    after = {fn: _read(os.path.join(root, fn)) for fn in hyp_before}
    check("mig4: hypothesis files are byte-unchanged (verdict, Verifiables and Null kept as "
          "history and optional sections)", after == hyp_before)
    v = E.Vault(root)
    check("mig4: the finding counter is advanced past every migrated Finding",
          int(v.cfg.get("counter_f") or 0) == len(_findings(root)))
    probs = E.cmd_validate(root)
    check(f"mig4: the migrated vault validates, the drift flag on h12 its only problem "
          f"(got {probs})", [p[0] for p in probs] == ["h12"] and "DRIFT" in probs[0][1])
    f, fn, _ = E.cmd_finding(root, "h2", "strong", why="a new run", direction="supports")
    check("mig4: a new Finding after migration gets a fresh id",
          f == f"f{len(_findings(root))}" and E.Vault(root).get(f).parent == "h2")


def node_findings_all(v):
    return [n for n in v.nodes.values() if n.type == "finding"]


def _backup_tests(check, tmp):
    import migrate4 as M
    root = os.path.join(tmp, "backup")
    build_legacy_vault(root)
    pre = tree_hashes(root)
    seen = {}
    real = M._write_atomic

    def spy(path, text):
        if "first" not in seen:
            bks = M.backups(root)
            seen["first"] = bks and tree_hashes(bks[-1], skip=()) == pre
        if os.path.abspath(path) == os.path.abspath(os.path.join(root, M.PENDING_FILE)):
            seen["pending_locked"] = os.path.exists(os.path.join(root, M.CRUX_DIR, E.LOCK_FILE))
        return real(path, text)
    M._write_atomic = spy
    try:
        E.check_and_stamp_version(root)
    finally:
        M._write_atomic = real
    check("mig4: a backup exists, complete, before the first byte changes", seen.get("first") is True)
    check("mig4: the pending store is C3's file, .crux/pending",
          M.PENDING_FILE.replace(os.sep, "/") == ".crux/pending")
    check("mig4: the pending store is written under the .crux/ lock (C3's interface)",
          seen.get("pending_locked") is True)
    bks = M.backups(root)
    check("mig4: exactly one backup, under .crux/", len(bks) == 1
          and os.path.dirname(bks[0]) == os.path.join(root, M.CRUX_DIR))
    check("mig4: the backup byte-equals the pre-migration tree", tree_hashes(bks[0], skip=()) == pre)
    check("mig4: the backup holds the old stamp",
          str(E.yaml_load(_read(os.path.join(bks[0], E.VAULT_MARKER))).get("engine_version")) == "3.5")

    # idempotent
    mid = tree_hashes(root, skip=())
    check("mig4: a second load returns nothing", E.check_and_stamp_version(root) is None)
    check("mig4: a second load changes no byte", tree_hashes(root, skip=()) == mid)
    p = M.plan(root)
    check("mig4: plan on a migrated vault is empty",
          not p["writes"] and not p["removes"] and not p["pending"])
    check("mig4: apply on a migrated vault changes nothing",
          M.apply(root) is None and tree_hashes(root, skip=()) == mid)


def _crash_tests(check, tmp):
    import migrate4 as M
    clean = os.path.join(tmp, "clean")
    build_legacy_vault(clean)
    E.check_and_stamp_version(clean)
    root = os.path.join(tmp, "crash")
    build_legacy_vault(root)
    pre = tree_hashes(root)
    real, n = M._write_atomic, {"k": 0}

    def boom(path, text):
        n["k"] += 1
        if n["k"] == 3:
            raise OSError("disk full (simulated)")
        return real(path, text)
    M._write_atomic = boom
    crashed = False
    try:
        E.check_and_stamp_version(root)
    except OSError:
        crashed = True
    finally:
        M._write_atomic = real
    check("mig4: the simulated crash happened mid-migration",
          crashed and os.path.exists(os.path.join(root, M.JOURNAL_FILE)))
    check("mig4: the crashed vault is still stamped with the old version",
          str(E.yaml_load(_read(os.path.join(root, E.VAULT_MARKER))).get("engine_version")) == "3.5")
    check("mig4: the backup taken before the crash byte-equals the pre-migration tree",
          M.backups(root) and tree_hashes(M.backups(root)[0], skip=()) == pre)
    M.rollback(root)
    check("mig4: rollback restores the pre-migration tree byte for byte",
          tree_hashes(root) == pre and not os.path.exists(os.path.join(root, M.JOURNAL_FILE)))
    # a crashed migration is finished by the next load: rollback, then migrate again
    M._write_atomic = boom
    n["k"] = 0
    try:
        E.check_and_stamp_version(root)
    except OSError:
        pass
    finally:
        M._write_atomic = real
    warn = E.check_and_stamp_version(root)
    check("mig4: the next load after a crash completes the migration", warn and "migrated" in warn)
    norm = lambda r: sorted((str(f["fm"].get("migrated_from")), f["fm"].get("direction"),
                             f["fm"].get("confidence"), f.parent, f["fn"])
                            for f in _findings(r).values())
    check("mig4: and the result equals a clean migration", norm(root) == norm(clean))
    check("mig4: pending is not duplicated by the retry",
          len(M.read_pending(root)) == len(M.read_pending(clean)))


def _readonly_tests(check, tmp):
    import migrate4 as M
    root = os.path.join(tmp, "ro")
    build_legacy_vault(root)
    before = tree_hashes(root, skip=())
    import crux as C
    with contextlib.redirect_stderr(io.StringIO()):
        C._vault_ro(root)
    E.snapshot(root)
    M.plan(root)
    check("mig4: serve's read-only load, snapshot and plan write nothing on a 3.x vault (Q9)",
          tree_hashes(root, skip=()) == before)
    r = _cli(root, "validate")
    check("mig4: a write-capable CLI verb migrates and says so on stderr",
          "migrated" in r.stderr and "backup" in r.stderr and _findings(root))
    check("mig4: the CLI line is not a drift warning", "Pin the matching engine" not in r.stderr)
    r2 = _cli(root, "status")
    check("mig4: the next CLI call is silent about migration", "migrated" not in r2.stderr)


def _nothing_to_migrate_tests(check, tmp):
    import migrate4 as M
    root = os.path.join(tmp, "empty")
    if os.path.exists(root):
        shutil.rmtree(root)
    E.cmd_init("Nothing yet", root)
    q1, _ = E.cmd_ask(root, "an open question")
    cfgp = os.path.join(root, E.VAULT_MARKER)
    _write(cfgp, _read(cfgp).replace(f"engine_version: {E.ENGINE_VERSION}", "engine_version: 3.3"))
    before = tree_hashes(root, skip=())
    warn = E.check_and_stamp_version(root)
    moved = sorted(k for k in set(before) | set(tree_hashes(root, skip=()))
                   if before.get(k) != tree_hashes(root, skip=()).get(k))
    check("mig4: a 3.x vault with nothing to convert only re-stamps (no backup, no .crux/)",
          moved == [E.VAULT_MARKER] and not os.path.exists(os.path.join(root, M.CRUX_DIR)))
    check("mig4: and still reports the drift it crossed", warn is not None and "3.3" in warn)


def run_all(check):
    tmp = tempfile.mkdtemp(prefix="crux_migrate4_")
    try:
        for section in (_import_tests, _plan_tests, _table_tests, _backup_tests, _crash_tests,
                        _readonly_tests, _nothing_to_migrate_tests):
            try:
                section(check, tmp)
            except Exception as e:      # an unexpected result is a FAIL line, never a traceback
                check(f"mig4: {section.__name__} crashed: {type(e).__name__}: {e}", False)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    os.environ["CRUX_NO_UPDATE_CHECK"] = "1"
    passed, failed = [], []

    def _check(name, cond):
        (passed if cond else failed).append(name)
        print(("  ok   " if cond else "  FAIL ") + name)
    run_all(_check)
    print(f"\n  PASSED {len(passed)} / {len(passed) + len(failed)}")
    for f in failed:
        print("   - " + f)
    sys.exit(1 if failed else 0)
