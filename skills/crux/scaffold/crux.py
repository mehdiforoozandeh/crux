#!/usr/bin/env python3
"""crux — an agentic research companion.

A scientific-method lab notebook: a tree of Questions (what we don't know) and
Hypotheses (falsifiable, testable leaves), rooted at a project. The agent drives
this CLI by default; it is also meant to be run directly by a human researcher.

Quick tour:
    crux init "My project"                  # bootstrap a vault here
    crux ask "Can X improve Y?"             # open a question (alias: question, q, meta)
    crux hypothesize "A beats B" -p q1 \\
        -v "metric ≥ +0.01 vs baseline"       # a leaf hypothesis (alias: hypothesis, idea)
    crux test h1 --run "job 4012"           # idea→staged→running (alias: experiment, run, stage, launch)
    crux close h1 -m "imp +0.012"           # verdict from verifiables (alias: record, conclude, verdict, land)
    crux review                             # questions awaiting your decision (alias: gate, decide)
    crux answer q1 -t "..."                 # resolve a question (alias: resolve, settle)
    crux pursue q1 --idea "next try"        # keep digging (alias: branch, extend, reopen)
    crux status                             # the tree / a node's ledger (alias: map, tree, where, show)

`close` reads the `## Verifiables` checkboxes you (or the agent) ticked:
all `- [x]` -> supported · any `- [ ]` -> refuted/partial · `- [-]` -> inconclusive.
"""
import argparse, sys, os, json

if sys.version_info < (3, 8):
    sys.exit("crux: needs Python >= 3.8 (found %d.%d)" % sys.version_info[:2])

# crux speaks UTF-8: verdict glyphs (✓ ○ ◆), the cockpit banner's arrow, the drift warning's
# ⚠, and vault text itself. A Windows console defaults to cp1252, where printing any of those
# raises UnicodeEncodeError and takes the whole command down — `crux serve` died right after
# the drift warning, before it could print the URL. Say what encoding we write in, and never
# let an unmappable glyph be fatal.
for _s in (sys.stdout, sys.stderr):
    try:
        _s.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass    # <3.7, or a stream that isn't reconfigurable — output just stays as it was

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E


def _vault():
    root = E.find_vault()
    warn = E.check_and_stamp_version(root)
    if warn:
        print(f"crux: ⚠ {warn}", file=sys.stderr)
    return root


def _vault_ro(start=None):
    """Resolve the vault WITHOUT stamping — for read-only verbs (serve). Warns on drift but
    never writes, so the GUI honors its no-write invariant even on a pre-versioned/drifted vault."""
    root = E.find_vault(start)
    stamped = E.yaml_load(E.read(os.path.join(root, E.VAULT_MARKER))).get("engine_version")
    if stamped is not None and str(stamped) != E.ENGINE_VERSION:
        print(f"crux: ⚠ engine drift: vault v{stamped} vs engine v{E.ENGINE_VERSION} "
              f"— serve is read-only and will not re-stamp.", file=sys.stderr)
    return root


def _jsonable(s):
    """Register `--json` on a verb. Every verb an agent loop drives carries it, so a caller
    never has to parse `✓ q3  (q3_foo.md)` out of prose. On `--json` stdout is JSON and
    nothing else — hints, drift warnings and back-pressure all go to stderr, where a pipe
    won't swallow them and a parse won't choke on them."""
    s.add_argument("--json", action="store_true",
                   help="emit machine-readable JSON on stdout instead of text")
    return s


def _emit(obj):
    print(json.dumps(obj, ensure_ascii=False))
    return 0


def _update_notice():
    """Tell the user once a day that a newer crux exists. Reads the answer from a cache
    (so it never blocks) and refreshes that cache in a daemon thread. Any failure at all —
    no network, no home directory, a corrupt cache — is silence, never a broken command.
    Set CRUX_NO_UPDATE_CHECK=1 to switch it off."""
    try:
        import update as U
        msg = U.maybe_check(E.CRUX_VERSION)
        if msg:
            print(msg, file=sys.stderr)
    except Exception:
        pass


def main(argv=None):
    p = argparse.ArgumentParser(prog="crux", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", metavar="<verb>")

    s = sub.add_parser("init", aliases=["start", "new"], help="bootstrap a project vault (default dir: ./cruxvault)")
    s.add_argument("title", nargs="?", default=None); s.add_argument("--dir", default="cruxvault"); s.add_argument("--goal", default="")
    s.add_argument("--from", dest="seed", default=None, help="materialize the whole vault from an approved seed outline (setup)")

    s = _jsonable(sub.add_parser("ask", aliases=["question", "q", "meta"], help="open a Question under the project or another question"))
    s.add_argument("title"); s.add_argument("-p", "--parent", default=None, help="parent id (default: project root)")
    s.add_argument("-b", "--body", default="", help="optional question detail")

    s = _jsonable(sub.add_parser("hypothesize", aliases=["hypothesis", "idea"], help="add a testable hypothesis under a question"))
    s.add_argument("title"); s.add_argument("-p", "--parent", required=True, help="parent question id")
    s.add_argument("--problem", default="")
    s.add_argument("-n", "--neutral", action="append", default=[],
                   help="an OUTCOME-NEUTRAL verifiable: a positive control / sanity check that must "
                        "pass whatever the hypothesis turns out to be. Its failure invalidates the "
                        "run, not the claim. At least one is required before `test --to running`.")
    s.add_argument("--rule", default=None, choices=None,
                   help="how the claim-directed verifiables ADD UP, declared before the run: "
                        "all | any | m-of-n. Required once there is more than one of them — "
                        "without it, 'two of four passed' is an argument rather than "
                        "arithmetic. Cost of `all`: two checks at 80%% power each give 64%% "
                        "joint power, and thresholds may not be loosened to compensate.")
    s.add_argument("--rule-m", dest="rule_m", type=int, default=None,
                   help="the m in m-of-n (how many of the claim-directed checks must pass)")
    s.add_argument("-v", "--verifiable", action="append", default=[],
                                                            help="a falsifiable check (repeatable)")

    s = _jsonable(sub.add_parser("test", aliases=["experiment", "run", "stage", "launch"], help="advance an idea: idea→staged→running"))
    s.add_argument("id"); s.add_argument("--to", choices=["staged", "running"], default=None)
    s.add_argument("--run", default=None, help="a run link/job id to record")

    s = _jsonable(sub.add_parser("close", aliases=["record", "conclude", "verdict", "land"], help="close a hypothesis: derive verdict from verifiables"))
    s.add_argument("id"); s.add_argument("-m", "--metric", default=None); s.add_argument("-f", "--findings", default=None)

    _jsonable(sub.add_parser("review", aliases=["gate", "decide"], help="list questions awaiting your close/reopen decision"))

    s = _jsonable(sub.add_parser("answer", aliases=["resolve", "settle"], help="resolve a question (PI decision)"))
    s.add_argument("id"); s.add_argument("-t", "--text", default=None, help="the standing answer")

    s = _jsonable(sub.add_parser("pursue", aliases=["branch", "extend", "reopen"], help="keep a question open; optionally spawn a fresh hypothesis"))
    s.add_argument("id"); s.add_argument("--idea", default=None, help="title of a new child hypothesis")

    s = _jsonable(sub.add_parser("status", aliases=["map", "tree", "where", "show"], help="print the tree, or one node's ledger"))
    s.add_argument("id", nargs="?", default=None)

    s = _jsonable(sub.add_parser("synthesize", aliases=["weave", "rollup"], help="draft the synthesis that closes a question (or weaves several)"))
    s.add_argument("title"); s.add_argument("-q", "--questions", "--for", required=True,
                                            help="comma-separated question ids (--for reads better for a single question)")

    s = _jsonable(sub.add_parser("approve", aliases=["sign-off", "signoff"], help="PI signs off a synthesis — required before `answer` can resolve its question"))
    s.add_argument("id")

    s = _jsonable(sub.add_parser("ingest", aliases=["source", "add-source"], help="register a PI-curated source (under raw/) into the literature wiki"))
    s.add_argument("path", help="path (under raw/, relative to the vault) to the source to register")
    s.add_argument("-t", "--title", default=None, help="human title for the source (default: filename)")

    s = _jsonable(sub.add_parser("rd", aliases=["design", "requirements"], help="write the Requirements Document for a node's design"))
    s.add_argument("node", help="the question or hypothesis this design belongs to")
    s.add_argument("title")
    s.add_argument("--supersedes", default=None, metavar="SLUG",
                   help="replace this node's active RD — an active RD is never amended in place")

    # `task` carries sub-verbs rather than five top-level ones: the taskhub is queried far
    # more than it is written, and one namespace keeps the top-level verb list about the
    # science. Every sub-verb takes --json, per spec 06's rule that the agent toolbelt lives
    # in the CLI so selftest can assert it and the cockpit can reuse it.
    tp = sub.add_parser("task", aliases=["todo", "work"], help="the taskhub: the work this project has to do")
    tsub = tp.add_subparsers(dest="tcmd", metavar="<sub-verb>")

    s = _jsonable(tsub.add_parser("add", help="append a task (never rewrites, never renumbers)"))
    s.add_argument("title")
    s.add_argument("-c", "--category", required=True,
                   help="from this vault's declared list (`crux task categories`)")
    s.add_argument("--ref", dest="refs", action="append", default=[], metavar="ID",
                   help="a tree node / wiki/<slug> / rd/<slug> this serves (repeatable)")
    s.add_argument("--blocked-by", dest="blocked_by", default=None, metavar="IDS",
                   help="comma-separated task ids, or None — REQUIRED, so a missing edge is "
                        "a visible omission rather than silence")
    s.add_argument("--parent", default=None, help="decomposition only: the task this is part of")
    s.add_argument("--why", default=None, help="one line: what this unblocks")

    s = _jsonable(tsub.add_parser("done", help="close a task — requires an output that resolves"))
    s.add_argument("id")
    s.add_argument("-o", "--output", dest="outputs", action="append", default=[], metavar="REF",
                   help="a vault path or [[wikilink]] this produced (repeatable)")

    s = _jsonable(tsub.add_parser("drop", help="abandon a task (no output required)"))
    s.add_argument("id")

    s = _jsonable(tsub.add_parser("show", help="one task's record"))
    s.add_argument("id")

    s = _jsonable(tsub.add_parser("categories", help="the declared category list, or grow it"))
    s.add_argument("--add", default=None, metavar="NAME", help="declare a new category")

    s = _jsonable(sub.add_parser("validate", aliases=["lint", "check"], help="run all integrity checks on the vault (tree + wiki + economy + rd + tasks)"))
    s.add_argument("--strict", action="store_true",
                   help="treat economy warnings as failures (exit 1) — off by default")
    s.add_argument("--check", default=None, metavar="LIST",
                   help="comma-separated subset of checks to run: " + ",".join(E.CHECKS)
                        + " (default: all) — plus opt-in: " + ",".join(E.OPT_CHECKS))

    s = _jsonable(sub.add_parser("deck", aliases=["prezit", "present", "slides"],
                                 help="assemble the presentation payload for an anchor's subtree (spec 11)"))
    s.add_argument("anchor", nargs="?", default=None,
                   help="anchor node id — a question, or a hypothesis for a shorter deck")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--verify", metavar="DECK", default=None,
                   help="prove every addressed number in DECK still matches the vault")
    g.add_argument("--refresh", metavar="DECK", default=None,
                   help="rewrite DECK's cached values from the vault (values only; prose untouched)")
    g.add_argument("--lint", metavar="DECK", default=None,
                   help="check DECK's slide contract: header comments + the 7-content-unit budget")
    s.add_argument("--strict", action="store_true",
                   help="with --verify: also fail on numerals carrying no address")

    s = sub.add_parser("selftest", help="run the engine's built-in test suite (no GPU/tokens; validates the install)")
    s.add_argument("--keep", default=None, help="build the demo vault at this path and keep it")

    s = sub.add_parser("serve", aliases=["gui", "ui", "cockpit"], help="open the read-only browser cockpit over this vault")
    s.add_argument("--dir", default=None, help="vault directory (default: resolve upward from the current directory)")
    s.add_argument("--port", type=int, default=None, help="pin a port (default: auto from 8787)")
    s.set_defaults(open=None)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--open", dest="open", action="store_true", help="force-open the system browser")
    g.add_argument("--no-open", dest="open", action="store_false", help="never open a browser")

    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help(); return 0

    _update_notice()

    try:
        return dispatch(args)
    except E.CruxError as e:
        print(f"crux: {e}", file=sys.stderr)
        return 1


def _csv_arg(val):
    """`--blocked-by t3,t4` -> ['t3','t4']; `None` (the literal the field requires) -> []."""
    return [x.strip() for x in (val or "").split(",") if x.strip() and x.strip() != E.NO_BLOCKERS]


def _dispatch_task(a):
    t = getattr(a, "tcmd", None)
    if not t:
        print("crux: task needs a sub-verb — add / done / drop / show / categories",
              file=sys.stderr)
        return 1
    if t == "categories":
        cats = E.cmd_task_categories(_vault(), a.add)
        if a.json:
            return _emit({"categories": list(cats), "reserved": E.TASK_RESERVED_CATEGORY})
        print("declared task categories: " + ", ".join(cats))
        print(f"  ({E.TASK_RESERVED_CATEGORY} is reserved — it is computed, never typed)")
        return 0
    root = _vault()
    if t == "add":
        if a.blocked_by is None:
            print("crux: --blocked-by is required (use `--blocked-by None` when nothing "
                  "blocks it) — a missing edge must be a visible omission, not silence",
                  file=sys.stderr)
            return 1
        tid, fn = E.cmd_task_add(root, a.title, a.category, refs=a.refs,
                                 blocked_by=_csv_arg(a.blocked_by), parent=a.parent, why=a.why)
        if a.json:
            return _emit({"id": tid, "file": f"{E.TASK_DIR}/{fn}", "category": a.category,
                          "refs": a.refs, "blocked_by": _csv_arg(a.blocked_by)})
        print(f"✓ {tid}  ({E.TASK_DIR}/{fn})")
    elif t == "done":
        st = E.cmd_task_done(root, a.id, a.outputs)
        if a.json:
            return _emit({"id": a.id, "status": st})
        print(f"✓ {a.id} → {st}")
    elif t == "drop":
        st = E.cmd_task_drop(root, a.id)
        if a.json:
            return _emit({"id": a.id, "status": st})
        print(f"✓ {a.id} → {st}")
    elif t == "show":
        rec = E.task_json(root, a.id)
        if a.json:
            return _emit(rec)
        print(f"{rec['id']} [{rec['category']}] {rec['title']}  —  status: {rec['status']}")
        print(f"  refs: {', '.join(rec['refs']) or '—'}   "
              f"blocked_by: {', '.join(rec['blocked_by']) or E.NO_BLOCKERS}")
        for o in rec["outputs"]:
            print(f"  output: {o['path']}")
    return 0


def dispatch(a):
    c = a.cmd
    if c in ("init", "start", "new"):
        if a.seed:
            root, fn = E.cmd_init_from(a.seed, a.dir)
            cd = "" if os.path.relpath(root) == "." else f"cd {os.path.relpath(root)} && "
            print(f"✓ materialized vault at {root} from {a.seed}\n  root node: {fn}\n"
                  f"  next: {cd}crux status   — review the tree, then crux review for questions awaiting you")
        elif a.title:
            root, fn = E.cmd_init(a.title, a.dir, a.goal)
            cd = "" if os.path.relpath(root) == "." else f"cd {os.path.relpath(root)} && "
            print(f"✓ initialized vault at {root}\n  root node: {fn}\n  next: {cd}crux ask \"your first question\"")
        else:
            print("crux: init needs a project title, or --from <seed.md>", file=sys.stderr); return 1
    elif c in ("ask", "question", "q", "meta"):
        nid, fn = E.cmd_ask(_vault(), a.title, a.parent, a.body)
        if a.json:
            return _emit({"id": nid, "file": fn})
        print(f"✓ {nid}  ({fn})")
    elif c in ("hypothesize", "hypothesis", "idea"):
        nid, fn, warn = E.cmd_hypothesize(_vault(), a.title, a.parent, a.problem,
                                          a.verifiable, a.neutral, a.rule, a.rule_m)
        if a.json:
            return _emit({"id": nid, "file": fn, "parent": a.parent, "warning": warn})
        print(f"✓ {nid}  ({fn})" + ("" if a.verifiable else "\n  ⚠ no verifiables yet — add them before `test --to running`"))
        if warn:
            print(f"  ⚠ {warn}", file=sys.stderr)
    elif c in ("test", "experiment", "run", "stage", "launch"):
        default_to = "staged" if c == "stage" else "running"   # `stage` queues; run/launch/experiment/test → running
        st = E.cmd_test(_vault(), a.id, a.to or default_to, a.run)
        if a.json:
            return _emit({"id": a.id, "status": st})
        print(f"✓ {a.id} → {st}")
    elif c in ("close", "record", "conclude", "verdict", "land"):
        root = _vault()
        verdict = E.cmd_close(root, a.id, a.metric, a.findings)
        # closing is never blocked by missing paperwork — but unlinked results get said out loud
        warns = E.artifact_warnings(root, a.id)
        if a.json:
            return _emit({"id": a.id, "status": "done", "verdict": verdict, "warnings": warns})
        print(f"✓ {a.id} closed → verdict: {verdict}")
        for w in warns:
            print(f"  ⚠ {w}", file=sys.stderr)
    elif c in ("review", "gate", "decide"):
        pend = E.cmd_review(_vault())
        if a.json:
            return _emit([{"id": nid, "title": title, "drift": drift}
                          for nid, title, drift in pend])
        if not pend:
            print("no questions awaiting a decision.")
        else:
            print("Awaiting your decision (close with `answer`, or `pursue` to keep digging):")
            for nid, title, drift in pend:
                # the drift flag belongs HERE, at the moment the PI is deciding. It never
                # blocks: the engine flags, the PI decides.
                print(f"  ◐ {nid}  {title}" + ("   ⚠ a child hypothesis has DRIFT — its "
                                               "verifiables changed after the run started"
                                               if drift else ""))
    elif c in ("answer", "resolve", "settle"):
        root = _vault()
        E.cmd_answer(root, a.id, a.text)
        sid = E.Vault(root).get(a.id)["fm"].get("synthesis")
        if a.json:
            return _emit({"id": a.id, "status": "resolved", "synthesis": sid})
        print(f"✓ {a.id} resolved (synthesis {sid})")
    elif c in ("approve", "sign-off", "signoff"):
        stamp = E.cmd_approve(_vault(), a.id)
        if a.json:
            return _emit({"id": a.id, "approved": stamp})
        print(f"✓ {a.id} approved at {stamp}\n  next: crux answer <question-id>")
    elif c in ("pursue", "branch", "extend", "reopen"):
        new = E.cmd_pursue(_vault(), a.id, a.idea)
        if a.json:
            return _emit({"id": a.id, "status": "open", "spawned": new[0] if new else None,
                          "warning": new[2] if new else None})
        print(f"✓ {a.id} reopened" + (f"; spawned {new[0]}" if new else ""))
        if new and new[2]:
            print(f"  ⚠ {new[2]}", file=sys.stderr)
    elif c in ("status", "map", "tree", "where", "show"):
        if a.json:
            root = _vault()
            return _emit(E.node_json(root, a.id) if a.id else E.snapshot(root))
        print(E.status_text(_vault(), a.id))
    elif c in ("synthesize", "weave", "rollup"):
        nid, fn = E.cmd_synthesize(_vault(), a.title, [x.strip() for x in a.questions.split(",")])
        if a.json:
            return _emit({"id": nid, "file": fn})
        print(f"✓ {nid}  ({fn})")
    elif c in ("ingest", "source", "add-source"):
        state, rel = E.cmd_ingest(_vault(), a.path, a.title)
        if a.json:
            return _emit({"state": state, "path": rel})
        print(f"✓ {state}: {rel}\n  next: compile/update the wiki page(s) that cite it, then `crux validate`")
    elif c in ("task", "todo", "work"):
        return _dispatch_task(a)
    elif c in ("rd", "design", "requirements"):
        root = _vault()
        slug, fn = E.cmd_rd(root, a.node, a.title, a.supersedes)
        if a.json:
            return _emit({"slug": slug, "file": f"{E.RD_DIR}/{fn}", "node": a.node,
                          "status": "active", "supersedes": a.supersedes})
        print(f"✓ {E.RD_DIR}/{fn}  (RD for {a.node})"
              + (f"\n  superseded {a.supersedes}" if a.supersedes else "")
              + "\n  next: write the design into it — the node's TL;DR must still stand alone")
    elif c in ("validate", "lint", "check"):
        checks = [x.strip() for x in a.check.split(",") if x.strip()] if a.check else None
        rep = E.validation_report(_vault(), checks)
        failed = bool(rep["problems"]) or (a.strict and bool(rep["warnings"]))
        if a.json:
            _emit(rep)
            return 1 if failed else 0
        for p in rep["problems"]:
            print(f"✗ {p['id']}: {p['message']}")
        for w in rep["warnings"]:
            print(f"⚠ {w['id']}: {w['message']}")
        # information, not a finding: printed with a neutral glyph, never counted toward
        # the exit code, and never silenced by --strict. A vault that predates a rule is
        # correct, not broken.
        for i in rep["info"]:
            print(f"· {i['message']}")
        if rep["problems"]:
            return 1
        if rep["warnings"]:
            # economy is advisory by default: the overflow channels an over-cap node needs
            # don't all exist yet, so red here would be red with nowhere to go.
            n = len(rep["warnings"])
            if a.strict:
                print(f"✗ {n} warning(s), and --strict was asked for")
                return 1
            print(f"✓ vault is valid — {n} economy warning(s) above (`--strict` to fail on them)")
            return 0
        print("✓ vault is valid")
        return 0
    elif c in ("deck", "prezit", "present", "slides"):
        # a read verb: resolve without stamping, like serve — payload assembly and verify
        # never mutate a vault (refresh rewrites the DECK file, still not the vault)
        root = _vault_ro()
        if a.verify:
            rep = E.deck_verify(root, a.verify)
            failed = bool(rep["mismatch"] or rep["unresolvable"]
                          or (a.strict and rep["unsourced"]))
            if a.json:
                _emit(rep)
                return 1 if failed else 0
            for f in rep["mismatch"]:
                print(f"✗ mismatch     {f['msg']}")
            for f in rep["unresolvable"]:
                print(f"✗ unresolvable {f['msg']}")
            for d in rep["derived"]:
                print(f"· derived      slide {d['slide']}: inputs current, result not "
                      f"recomputed ({', '.join(d['inputs'])})")
            for u in rep["unsourced"]:
                mark = "✗" if a.strict else "⚠"
                print(f"{mark} unsourced    slide {u['slide']}: numeral '{u['numeral']}' "
                      f"carries no address")
            if failed:
                return 1
            print(f"✓ deck verified: every addressed number matches the vault"
                  + (f" ({len(rep['unsourced'])} unsourced numeral(s) above — --strict to fail on them)"
                     if rep["unsourced"] else ""))
            return 0
        if a.refresh:
            res = E.deck_refresh(root, a.refresh)
            if a.json:
                return _emit(res)
            if not res["changes"] and not res["unresolvable"]:
                print("✓ deck already current — nothing rewritten")
                return 0
            for ch in res["changes"]:
                print(f"  slide {ch['slide']}: {ch['addr']} {ch['field']} "
                      f"{ch['old']} -> {ch['new']}")
            for u in res["unresolvable"]:
                print(f"  ⚠ left alone (unresolvable): {u['msg']}", file=sys.stderr)
            if res["changes"]:
                print(f"✓ {len(res['changes'])} value(s) rewritten\n"
                      f"  ⚠ numbers moved on slide(s) {', '.join(map(str, res['slides']))} — "
                      f"re-read the prose around them: a correct refresh can silently "
                      f"falsify the sentence that interprets a number.", file=sys.stderr)
            return 0
        if a.lint:
            probs = E.deck_lint(a.lint)
            if a.json:
                _emit([{"slide": i, "message": m} for i, m in probs])
                return 1 if probs else 0
            for _, m in probs:
                print(f"✗ {m}")
            if probs:
                return 1
            print("✓ deck lint clean: contract headers present, every slide within the unit budget")
            return 0
        if not a.anchor:
            print("crux: deck needs an anchor id (e.g. `crux deck q1 --json`), or "
                  "--verify/--refresh/--lint <deck.html>", file=sys.stderr)
            return 1
        payload = E.deck_payload(root, a.anchor)
        if a.json:
            return _emit(payload)
        print(f"deck {a.anchor}: {len(payload['lineage'])} ancestor(s) · "
              f"{len(payload['children'])} direct child(ren) · "
              f"{len(payload['figures'])} figure file(s) · "
              f"{len(payload['metrics'])} addressed metric(s)\n"
              f"  full payload: crux deck {a.anchor} --json")
    elif c in ("serve", "gui", "ui", "cockpit"):
        import serve as SV
        SV.serve(_vault_ro(a.dir), port=a.port, force_open=a.open)
    elif c == "selftest":
        import subprocess
        st = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selftest.py")
        return subprocess.call([sys.executable, st] + (["--keep", a.keep] if a.keep else []))
    return 0


if __name__ == "__main__":
    sys.exit(main())
