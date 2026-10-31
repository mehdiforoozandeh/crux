"""crux vault migration 3.x -> 4.0 (spec 19, chunk C2).

Engine 4.0 replaces verdicts, syntheses and accepted experiments with Findings. A vault
stamped older than 4.0 is migrated automatically, with a backup, on the first load that can
write (`engine.check_and_stamp_version`, which every write-capable CLI verb runs). Read-only
loads (`crux serve`) never migrate: they may call `plan`, which is pure.

THE TABLE (spec 19 "Migration (engine 4.0)" + PI rulings 2026-10-31). Applied exactly.

  old record                                   new record
  ------------------------------------------   ---------------------------------------------
  hypothesis verdict supported                 Finding, direction supports. Confidence by the
                                               claim checks: all pass -> strong; one missed ->
                                               moderate; two or more missed -> weak.
  hypothesis verdict refuted                   Finding, direction against. Every claim check
                                               failed -> strong; any passed -> moderate.
  partial / inconclusive                       Finding, mixed, weak.
  invalid-run                                  Finding, no-answer-yet (weak), the run's
                                               result files kept as evidence.
  a failed control check                       caps confidence at weak.
  a null not ruled out                         caps confidence at weak (direction supports).
  checks edited after the run started          caps confidence at moderate; `why` names the
  (lock drift, lock taken at `running`)        edit. A seeded `reconstructed` lock is no cap.
  never closed (no verdict)                    no Finding; the state stays open.
  approved synthesis                           one strong Question Finding per question it
                                               names, NO direction, its text kept as Answer.
  unapproved synthesis                         a pending /crux-wrap candidate.
  experiment task, accepted                    a moderate Finding on its hypothesis, direction
                                               mapped like a verdict, evidence = the task file
                                               and its outputs under results/ or tasks/.
  experiment task, not accepted                a pending /crux-wrap candidate.
  experiment task, dropped                     nothing.
  Verifiables, Null, verdict, status           kept on the hypothesis, byte-unchanged.

Read precisely:
  - "missed" = a claim-directed check not met: unmet `[ ]` or could-not-evaluate `[-]`.
  - refuted with no check passed but one not evaluated: not "every check failed" -> moderate.
  - A supported verdict with no claim check at all has nothing to agree with -> weak.
  - The null state is computed only for direction supports, because the null is the rival
    explanation of a POSITIVE result. Declared null + every `discriminates::` check met ->
    ruled-out; declared null otherwise (a discriminating check missed, or none aimed at it) ->
    not-ruled-out; no declared null -> none. Against, mixed and no-answer-yet Findings carry
    no null field: on a refuted claim the discriminating check failing is the refutation
    itself, and capping it would make "all fail -> strong" unreachable.
  - The direction comes from the RECORDED verdict; the ticks only set the confidence.
  - A migrated Finding is dated by its source (hypothesis `updated`, synthesis `approved`,
    task `accepted`), so "newest breaks ties" keeps the historical order. Each carries
    `migrated_from: <source>` (`h12`, `t119:h17`, or `s3_what_the_timer:q18` — a synthesis
    is named by its file name, because its bare id no longer exists), which is also what
    makes the migration idempotent. A question's `synthesis:` pointer to a removed synthesis
    is dropped for the same reason.
  - A Finding's title is its `why`, as `crux finding` titles one.

FILES (all under `<vault>/.crux/`, a folder that git-ignores itself via `.crux/.gitignore`):
  backup-<old version>-<timestamp>/  a byte copy of the whole vault (minus .crux/ and .git/),
                                     complete before the first byte of the vault changes.
  migrate-4.0-report.json            every Finding written, every pending candidate, every
                                     skip, and every experiment whose conclusion disagrees
                                     with its hypothesis' own verdict.
  migrate-4.0-journal.json           exists only while a migration runs. If a crash leaves
                                     it behind, the next load rolls the journalled paths back
                                     from the backup and migrates again.
  pending.jsonl                      THE PENDING STORE (read by /crux-wrap, chunk C3).

PENDING STORE FORMAT — `<vault>/.crux/pending.jsonl`, UTF-8 JSON lines, one candidate per
line, append-only for writers, unique by `id`:

  {"id":       "s2:q2" | "t2:h6"        stable key: <origin>:<parent>; a writer skips an id
                                        already present
   "kind":     "synthesis" | "experiment" | (C3 adds its own kinds)
   "status":   "pending"                a reader may rewrite the line to "accepted" or
                                        "rejected" once the PI answers
   "parent":   "q2"                     the question or hypothesis the Finding would hang on
   "origin":   "s2"                     the old node or task it came from
   "source":   "migrate-4.0"            who wrote the candidate
   "created":  "2026-07-19T09:00:00"    when the source was written (not the migration time)
   "reason":   "unapproved synthesis"   one line: why it waits for the PI
   "proposal": {"direction": str|null, "confidence": str|null, "why": str|null,
                "answer": str|null, "evidence": [str]}
                                        exactly the arguments of `engine.cmd_finding`, so
                                        accepting a candidate is one call
   "text":     str                      the source's full text, kept verbatim}

Stdlib only.
"""
import os, json, shutil, datetime
import engine as E

TARGET        = "4.0"
CRUX_DIR      = ".crux"
PENDING_FILE  = os.path.join(CRUX_DIR, "pending.jsonl")
REPORT_FILE   = os.path.join(CRUX_DIR, "migrate-4.0-report.json")
JOURNAL_FILE  = os.path.join(CRUX_DIR, "migrate-4.0-journal.json")
BACKUP_PREFIX = "backup-"
MIGRATED_FROM = "migrated_from"
SOURCE        = "migrate-4.0"
PENDING_KEYS  = ("id", "kind", "status", "parent", "origin", "source", "created", "reason",
                 "proposal", "text")
_SKIP_TOP     = (CRUX_DIR, ".git")          # never copied into a backup, never rolled back

VERDICT_DIRECTION = {"supported": "supports", "refuted": "against", "partial": "mixed",
                     "inconclusive": "mixed", "invalid-run": E.NO_ANSWER}


# ------------------------------------------------------------------------------- versions
def _vkey(s):
    try:
        return tuple(int(x) for x in str(s).split("."))
    except ValueError:
        return None

def needs_migration(stamped):
    """True for a vault stamped older than 4.0, or never stamped at all."""
    if stamped is None:
        return True
    k = _vkey(stamped)
    return k is not None and k < _vkey(TARGET)


# ------------------------------------------------------------------------------- the rules
def _cap(conf, limit):
    return limit if E.confidence_rank(conf) > E.confidence_rank(limit) else conf

def _plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"

def verdict_finding(v, n):
    """The Finding fields for one closed 3.x hypothesis, or None when it was never closed.
    A pure function of the node: the recorded verdict, its ticks, its null, its lock."""
    verdict = n["fm"].get("verdict")
    if verdict not in VERDICT_DIRECTION:
        return None
    by = E.count_verifiables_by_kind(n["body"])
    hmet, hunmet, hna = by[E.DEFAULT_KIND]
    nmet, nunmet, nna = by[E.NEUTRAL_KIND]
    k, missed = hmet + hunmet + hna, hunmet + hna
    direction = VERDICT_DIRECTION[verdict]
    rule = E.node_rule(n)[0] or "none declared"
    tally = f"{hmet} of {k} claim checks passed"
    if verdict == "supported":
        conf = "weak" if k == 0 else ("strong" if missed == 0 else
                                      "moderate" if missed == 1 else "weak")
        clause = "no claim check was recorded" if k == 0 else tally
    elif verdict == "refuted":
        conf = "strong" if (k and hmet == 0 and hna == 0) else "moderate"
        clause = tally
    elif verdict == "invalid-run":
        conf = "weak"
        clause = (f"{_plural(nunmet + nna, 'control check')} failed or could not be read, "
                  f"so the run says nothing about the claim" if nunmet + nna else
                  "the run could not answer the claim")
    else:
        conf = "weak"
        clause = f"{tally}, so the answer is mixed"
    caps = []
    null = None
    if nunmet + nna and verdict != "invalid-run":
        conf = _cap(conf, "weak")
        caps.append("a control check failed, which caps confidence at weak")
    if direction == "supports":
        declared = E._null_text(n)
        disc = [i for i, s in enumerate(E.verifiable_scenarios(n["body"])) if s["discriminates"]]
        ticks = [t for t, _ in E._verifiable_lines(n["body"])]
        if not declared:
            null = "none"
        elif disc and all(i < len(ticks) and ticks[i] == "x" for i in disc):
            null = "ruled-out"
        else:
            null = E.NULL_NOT_RULED_OUT
            conf = _cap(conf, E.NULL_CAP)
            caps.append("the null was not ruled out by a check aimed at it, which caps "
                        "confidence at weak")
    if E.lock_drift(n) and str(n["fm"].get(E.LOCK_WHERE_FIELD) or "") != E.RECONSTRUCTED:
        conf = _cap(conf, "moderate")
        caps.append(f"the checks were edited after the run started (locked "
                    f"{n['fm'].get(E.LOCKED_AT_FIELD)}), which caps confidence at moderate")
    why = f"The recorded verdict was {verdict}: {clause}"
    if caps:
        why += "; " + "; ".join(caps)
    why += "."
    evidence = []
    for a in E.parse_artifacts(n["body"]):
        if not E._evidence_problem(v.root, a["path"]) and a["path"] not in evidence:
            evidence.append(a["path"])
    if verdict == "invalid-run" and not evidence and \
            not E._evidence_problem(v.root, f"{E.RESULTS_DIR}/{n.id}"):
        evidence.append(f"{E.RESULTS_DIR}/{n.id}")
    checks = f"claim {hmet}/{k} met; controls {nmet}/{nmet + nunmet + nna} met; rule {rule}"
    return {"parent": n.id, "direction": direction, "confidence": conf, "null": null,
            "why": why, "verifiables": checks, "evidence": evidence, "answer": None,
            "created": str(n["fm"].get("updated") or n["fm"].get("created") or ""),
            "title": why, MIGRATED_FROM: n.id, "row": verdict}

def _synthesis_answer(s):
    """The synthesis' own text, every authored line, as Answer text. Its `##` headings drop
    one level so they cannot end the finding's `## Answer` section."""
    lines = []
    for line in s["body"].splitlines():
        if line.startswith("# ") or line.strip().startswith("Related::"):
            continue
        lines.append("#" + line if line.startswith("## ") else line)
    body = "\n".join(lines).strip()
    return (s.title + ("\n\n" + body if body else "")).strip()

def _task_evidence(root, t):
    ev = [os.path.relpath(t["path"], root).replace(os.sep, "/")]
    for o in t["outputs"]:
        if not E._evidence_problem(root, o["path"]) and o["path"] not in ev:
            ev.append(o["path"])
    return ev


# ------------------------------------------------------------------------------- plan
def _existing_sources(v):
    return {str(f["fm"].get(MIGRATED_FROM)) for f in v.nodes.values()
            if f.type == "finding" and f["fm"].get(MIGRATED_FROM)}

def read_pending(root):
    """Every candidate in the pending store, in file order. [] when there is none."""
    p = os.path.join(root, PENDING_FILE)
    if not os.path.exists(p):
        return []
    out = []
    for line in E.read(p).splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except ValueError:
                continue
    return out

def _one_line(x):
    return " ".join(str(x or "").split())

def _finding_text(fid, rec, parent_basename):
    head = rec["title"]
    title = head if len(head) <= 80 else head[:77].rsplit(" ", 1)[0] + "…"
    fm = {"id": fid, "type": "finding", "schema": E.SCHEMA_GENERATION, "title": title,
          "parent": rec["parent"]}
    for k in E.FINDING_FIELDS:
        val = rec.get(k)
        if k == "evidence":
            val = ", ".join(val or []) or None
        if val not in (None, ""):
            fm[k] = _one_line(val) if k != "evidence" else val
    fm[MIGRATED_FROM] = rec[MIGRATED_FROM]
    fm["created"] = rec["created"] or "1970-01-01T00:00:00"
    fm["updated"] = fm["created"]
    body = f"# {fid} — {title}\n\nParent:: [[{parent_basename}]]\n"
    if rec.get("answer"):
        body += f"\n## Answer\n\n{rec['answer']}\n"
    return E.slugify(title), E.render_doc(fm, body)

def plan(root):
    """What migrating `root` to 4.0 would change. PURE: it reads the vault and writes
    nothing, so the read-only cockpit can render it (ruling Q9).

    Returns {from, to, findings, writes, removes, pending, disagreements, skipped,
    counter_f}: `writes` maps a vault-relative path to its full new text, `removes` lists
    vault-relative paths to delete, `pending` the candidates not yet in the store. An empty
    `writes`, `removes` and `pending` means there is nothing to migrate."""
    v = E.Vault(root)
    done = _existing_sources(v)
    have_pending = {p.get("id") for p in read_pending(root)}
    tasks = E.scan_tasks(root)
    recs, pending, removes, disagreements, skipped = [], [], [], [], []

    ideas = sorted((n for n in v.nodes.values() if n.type == "idea"), key=lambda n: E.natkey(n.id))
    for n in ideas:
        rec = verdict_finding(v, n)
        if rec is None:
            skipped.append({"id": n.id, "reason": "never closed: no Finding, the state is open"})
        elif n.id not in done:
            recs.append(rec)

    syns = sorted((n for n in v.nodes.values() if n.type == "synthesis"),
                  key=lambda n: E.natkey(n.id))
    for s in syns:
        removes.append(s["fn"])
        qids = [q for q in E._related_ids(v, s["body"]) if v.nodes[q].type == "question"]
        answer = _synthesis_answer(s)
        text = E.read(s["path"])
        approved = s["fm"].get("approved")
        if approved and qids:
            for q in qids:
                if f"{s.basename}:{q}" in done:
                    continue
                recs.append({"parent": q, "direction": None, "confidence": "strong",
                             "null": None, "why": None, "verifiables": None, "evidence": [],
                             "answer": answer, "created": str(approved), "title": s.title,
                             MIGRATED_FROM: f"{s.basename}:{q}", "row": "approved synthesis"})
            continue
        reason = ("unapproved synthesis" if not approved
                  else "approved synthesis that names no question")
        for q in (qids or [None]):
            pending.append({"id": f"{s.id}:{q}", "kind": "synthesis", "status": "pending",
                            "parent": q, "origin": s.id, "source": SOURCE,
                            "created": str(s["fm"].get("created") or ""), "reason": reason,
                            "proposal": {"direction": None, "confidence": None, "why": None,
                                         "answer": answer, "evidence": []},
                            "text": text})

    for t in tasks:
        if not E.task_is_experiment(t):
            continue
        for hid, concl in t["hypothesis_refs"]:
            h = v.nodes.get(hid)
            verdict = h["fm"].get("verdict") if h is not None and h.type == "idea" else None
            accepted = t["fm"].get(E.TASK_ACCEPTED)
            if verdict and concl and concl != verdict:
                disagreements.append({"task": t["id"], "hypothesis": hid, "conclusion": concl,
                                      "verdict": verdict, "task_status": t["status"],
                                      "accepted": bool(accepted)})
            key = f"{t['id']}:{hid}"
            if t["status"] == "dropped":
                skipped.append({"id": key, "reason": "dropped experiment: nothing"})
                continue
            if h is None or h.type != "idea" or concl not in VERDICT_DIRECTION:
                skipped.append({"id": key, "reason": f"experiment refs '{hid}' with "
                                                     f"conclusion '{concl}': not mappable"})
                continue
            direction = VERDICT_DIRECTION[concl]
            why = (f"Experiment {t['id']} concluded {concl}"
                   + (f", and the PI accepted it on {accepted}." if accepted else "."))
            ev = _task_evidence(root, t)
            if accepted:
                if key not in done:
                    recs.append({"parent": hid, "direction": direction, "confidence": "moderate",
                                 "null": None, "why": why, "verifiables": None, "evidence": ev,
                                 "answer": None, "created": str(accepted),
                                 "title": why, MIGRATED_FROM: key,
                                 "row": "accepted experiment"})
            else:
                pending.append({"id": key, "kind": "experiment", "status": "pending",
                                "parent": hid, "origin": t["id"], "source": SOURCE,
                                "created": str(t["fm"].get("created") or ""),
                                "reason": "experiment conclusion the PI never accepted",
                                "proposal": {"direction": direction, "confidence": "moderate",
                                             "why": why, "answer": None, "evidence": ev},
                                "text": E.read(t["path"])})

    # a question's `synthesis:` pointer names a node this migration removes: drop it, so no
    # record points at an id that no longer exists (the Finding's `migrated_from` keeps it)
    gone = {s.id for s in syns}
    unlinked = {}
    for q in sorted((n for n in v.nodes.values() if n.type == "question"),
                    key=lambda n: E.natkey(n.id)):
        if str(q["fm"].get("synthesis") or "") in gone:
            fm = {k: val for k, val in q["fm"].items() if k != "synthesis"}
            unlinked[q["fn"]] = E.render_doc(fm, q["body"])
    pending = [p for p in pending if p["id"] not in have_pending]
    counter = int(v.cfg.get("counter_f") or 0)
    findings, writes = [], {}
    for rec in recs:
        counter += 1
        fid = f"f{counter}"
        slug, text = _finding_text(fid, rec, v.nodes[rec["parent"]].basename)
        fn = f"{fid}_{slug}.md"
        writes[fn] = text
        findings.append({"id": fid, "file": fn, "parent": rec["parent"],
                         "direction": rec["direction"], "confidence": rec["confidence"],
                         "null": rec["null"], "row": rec["row"],
                         MIGRATED_FROM: rec[MIGRATED_FROM]})
    writes.update(unlinked)
    return {"from": None if v.cfg.get("engine_version") is None else str(v.cfg.get("engine_version")),
            "to": E.ENGINE_VERSION, "findings": findings, "writes": writes, "removes": removes,
            "pending": pending, "disagreements": disagreements, "skipped": skipped,
            "counter_f": counter}

def _has_changes(p):
    return bool(p["writes"] or p["removes"] or p["pending"])


# ------------------------------------------------------------------------------- disk
def _write_atomic(path, text):
    """Write `text` to `path` through a temp file and a rename, so a crash never leaves a
    half-written file. Every vault write of the migration goes through here."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".mig4.tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(text)
    os.replace(tmp, path)

def _ensure_crux_dir(root):
    d = os.path.join(root, CRUX_DIR)
    os.makedirs(d, exist_ok=True)
    gi = os.path.join(d, ".gitignore")
    if not os.path.exists(gi):
        with open(gi, "w", encoding="utf-8") as f:
            f.write("*\n")
    return d

def backups(root):
    """Every migration backup of this vault, oldest first."""
    d = os.path.join(root, CRUX_DIR)
    if not os.path.isdir(d):
        return []
    return [os.path.join(d, x) for x in sorted(os.listdir(d))
            if x.startswith(BACKUP_PREFIX) and not x.endswith(".tmp")
            and os.path.isdir(os.path.join(d, x))]

def _copy_tree(src, dst):
    """Byte copy of `src` into `dst`, minus the top-level .crux/, .git/ and the vault lock
    file. File modes are
    copied when the OS allows it; the bytes are what the backup promises."""
    for dirpath, dirnames, filenames in os.walk(src):
        top = os.path.abspath(dirpath) == os.path.abspath(src)
        if top:
            dirnames[:] = [d for d in dirnames if d not in _SKIP_TOP]
            # the vault lock is held by this very migration; it is not vault content
            filenames = [f for f in filenames if f != E.LOCK_FILE]
        rel = os.path.relpath(dirpath, src)
        os.makedirs(os.path.join(dst, rel), exist_ok=True)
        for fn in filenames:
            s, d = os.path.join(dirpath, fn), os.path.join(dst, rel, fn)
            shutil.copyfile(s, d)
            try:
                shutil.copymode(s, d)
            except OSError:
                pass

def _make_backup(root, stamped):
    d = _ensure_crux_dir(root)
    for x in os.listdir(d):                     # a backup a crash left half-copied
        if x.startswith(BACKUP_PREFIX) and x.endswith(".tmp"):
            shutil.rmtree(os.path.join(d, x), ignore_errors=True)
    stamp = datetime.datetime.now().strftime("%Y%m%dT%H%M%S")
    name = f"{BACKUP_PREFIX}{stamped or 'unversioned'}-{stamp}"
    final, i = os.path.join(d, name), 1
    while os.path.exists(final):
        i += 1
        final = os.path.join(d, f"{name}-{i}")
    tmp = final + ".tmp"
    if os.path.exists(tmp):
        shutil.rmtree(tmp)
    _copy_tree(root, tmp)
    os.rename(tmp, final)                       # the backup appears whole, or not at all
    return final

def _journal_paths(root, p):
    """Every vault path the migration may touch: what it writes and removes, the config, and
    every root-level .md (refresh rewrites the generated views and the question ledgers)."""
    paths = set(p["writes"]) | set(p["removes"]) | {E.VAULT_MARKER}
    paths |= {fn for fn in os.listdir(root) if fn.endswith(".md")}
    return sorted(paths)

def rollback(root):
    """Undo a migration a crash left half-done: every journalled path is restored from the
    backup (or deleted when the backup never had it), then the journal is removed. Returns
    True when there was something to roll back."""
    jp = os.path.join(root, JOURNAL_FILE)
    if not os.path.exists(jp):
        return False
    j = json.loads(E.read(jp))
    bk = j["backup"]
    for rel in j["paths"]:
        dst, src = os.path.join(root, rel), os.path.join(bk, rel)
        if os.path.exists(src):
            shutil.copyfile(src, dst)
        elif os.path.exists(dst):
            os.remove(dst)
        if os.path.exists(dst + ".mig4.tmp"):
            os.remove(dst + ".mig4.tmp")
    os.remove(jp)
    return True

def apply(root, stamped=None):
    """Migrate `root` to 4.0. Returns the report dict, or None when there was nothing to
    convert. Order is the guarantee: backup (whole) -> journal -> writes -> refresh -> counter
    -> report -> journal removed -> stamp. A crash before the journal is removed leaves the
    old stamp and the journal, and the next load rolls back and starts again."""
    with E.id_lock(root):
        rollback(root)
        if stamped is None:
            stamped = E.yaml_load(E.read(os.path.join(root, E.VAULT_MARKER))).get("engine_version")
            stamped = None if stamped is None else str(stamped)
        p = plan(root)
        if not _has_changes(p):
            return None
        bk = _make_backup(root, stamped)
        _write_atomic(os.path.join(root, JOURNAL_FILE),
                      json.dumps({"backup": bk, "paths": _journal_paths(root, p)}, indent=1))
        for rel, text in p["writes"].items():
            _write_atomic(os.path.join(root, rel), text)
        for rel in p["removes"]:
            if os.path.exists(os.path.join(root, rel)):
                os.remove(os.path.join(root, rel))
        if p["pending"]:
            pp = os.path.join(root, PENDING_FILE)
            old = E.read(pp) if os.path.exists(pp) else ""
            if old and not old.endswith("\n"):
                old += "\n"
            _write_atomic(pp, old + "".join(json.dumps(x, ensure_ascii=False) + "\n"
                                            for x in p["pending"]))
        E.refresh(root)
        cfgp = os.path.join(root, E.VAULT_MARKER)
        cfg = E.yaml_load(E.read(cfgp))
        cfg["counter_f"] = p["counter_f"]
        _write_atomic(cfgp, E.yaml_dump(cfg) + "\n")
        report = {"from": stamped, "to": E.ENGINE_VERSION, "migrated": E.now(),
                  "backup": os.path.relpath(bk, root).replace(os.sep, "/"),
                  "findings": p["findings"], "removed": p["removes"],
                  "pending": [{k: x[k] for k in ("id", "kind", "parent", "origin", "reason")}
                              for x in p["pending"]],
                  "disagreements": p["disagreements"], "skipped": p["skipped"]}
        _write_atomic(os.path.join(root, REPORT_FILE), json.dumps(report, indent=1,
                                                                  ensure_ascii=False) + "\n")
        # the journal goes BEFORE the stamp: past this line every Finding, the counter and
        # the report are on disk, so a crash here leaves a vault whose next load finds
        # nothing left to convert and only re-stamps
        os.remove(os.path.join(root, JOURNAL_FILE))
        cfg["engine_version"] = E.ENGINE_VERSION
        _write_atomic(cfgp, E.yaml_dump(cfg) + "\n")
        return report

def migrate_on_load(root, stamped):
    """The hook `check_and_stamp_version` calls. Returns the one line the CLI prints when a
    migration ran, else None. Third person, like every CLI line (spec 16)."""
    if not needs_migration(stamped) and not os.path.exists(os.path.join(root, JOURNAL_FILE)):
        return None
    rep = apply(root, stamped)
    if rep is None:
        return None
    return (f"migrated this vault from engine v{stamped or 'unversioned'} to "
            f"v{E.ENGINE_VERSION}: {_plural(len(rep['findings']), 'finding')} written, "
            f"{_plural(len(rep['pending']), 'candidate')} pending for /crux-wrap, "
            f"{_plural(len(rep['disagreements']), 'experiment disagreement')} listed. "
            f"backup: {rep['backup']}; report: {REPORT_FILE.replace(os.sep, '/')}.")
