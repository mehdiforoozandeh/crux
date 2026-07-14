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
import argparse, sys, os

if sys.version_info < (3, 8):
    sys.exit("crux: needs Python >= 3.8 (found %d.%d)" % sys.version_info[:2])

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


def main(argv=None):
    p = argparse.ArgumentParser(prog="crux", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", metavar="<verb>")

    s = sub.add_parser("init", aliases=["start", "new"], help="bootstrap a project vault (default dir: ./cruxvault)")
    s.add_argument("title", nargs="?", default=None); s.add_argument("--dir", default="cruxvault"); s.add_argument("--goal", default="")
    s.add_argument("--from", dest="seed", default=None, help="materialize the whole vault from an approved seed outline (setup)")

    s = sub.add_parser("ask", aliases=["question", "q", "meta"], help="open a Question under the project or another question")
    s.add_argument("title"); s.add_argument("-p", "--parent", default=None, help="parent id (default: project root)")
    s.add_argument("-b", "--body", default="", help="optional question detail")

    s = sub.add_parser("hypothesize", aliases=["hypothesis", "idea"], help="add a testable hypothesis under a question")
    s.add_argument("title"); s.add_argument("-p", "--parent", required=True, help="parent question id")
    s.add_argument("--problem", default=""); s.add_argument("-v", "--verifiable", action="append", default=[],
                                                            help="a falsifiable check (repeatable)")

    s = sub.add_parser("test", aliases=["experiment", "run", "stage", "launch"], help="advance an idea: idea→staged→running")
    s.add_argument("id"); s.add_argument("--to", choices=["staged", "running"], default=None)
    s.add_argument("--run", default=None, help="a run link/job id to record")

    s = sub.add_parser("close", aliases=["record", "conclude", "verdict", "land"], help="close a hypothesis: derive verdict from verifiables")
    s.add_argument("id"); s.add_argument("-m", "--metric", default=None); s.add_argument("-f", "--findings", default=None)

    sub.add_parser("review", aliases=["gate", "decide"], help="list questions awaiting your close/reopen decision")

    s = sub.add_parser("answer", aliases=["resolve", "settle"], help="resolve a question (PI decision)")
    s.add_argument("id"); s.add_argument("-t", "--text", default=None, help="the standing answer")

    s = sub.add_parser("pursue", aliases=["branch", "extend", "reopen"], help="keep a question open; optionally spawn a fresh hypothesis")
    s.add_argument("id"); s.add_argument("--idea", default=None, help="title of a new child hypothesis")

    s = sub.add_parser("status", aliases=["map", "tree", "where", "show"], help="print the tree, or one node's ledger")
    s.add_argument("id", nargs="?", default=None)

    s = sub.add_parser("synthesize", aliases=["weave", "rollup"], help="create a horizontal synthesis across questions")
    s.add_argument("title"); s.add_argument("-q", "--questions", required=True, help="comma-separated question ids")

    s = sub.add_parser("ingest", aliases=["source", "add-source"], help="register a PI-curated source (under raw/) into the literature wiki")
    s.add_argument("path", help="path (under raw/, relative to the vault) to the source to register")
    s.add_argument("-t", "--title", default=None, help="human title for the source (default: filename)")

    sub.add_parser("validate", aliases=["lint", "check"], help="run all integrity checks on the vault (tree + wiki)")

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

    try:
        return dispatch(args)
    except E.CruxError as e:
        print(f"crux: {e}", file=sys.stderr)
        return 1


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
        print(f"✓ {nid}  ({fn})")
    elif c in ("hypothesize", "hypothesis", "idea"):
        nid, fn = E.cmd_hypothesize(_vault(), a.title, a.parent, a.problem, a.verifiable)
        print(f"✓ {nid}  ({fn})" + ("" if a.verifiable else "\n  ⚠ no verifiables yet — add them before `test --to running`"))
    elif c in ("test", "experiment", "run", "stage", "launch"):
        default_to = "staged" if c == "stage" else "running"   # `stage` queues; run/launch/experiment/test → running
        st = E.cmd_test(_vault(), a.id, a.to or default_to, a.run)
        print(f"✓ {a.id} → {st}")
    elif c in ("close", "record", "conclude", "verdict", "land"):
        verdict = E.cmd_close(_vault(), a.id, a.metric, a.findings)
        print(f"✓ {a.id} closed → verdict: {verdict}")
    elif c in ("review", "gate", "decide"):
        pend = E.cmd_review(_vault())
        if not pend:
            print("no questions awaiting a decision.")
        else:
            print("Awaiting your decision (close with `answer`, or `pursue` to keep digging):")
            for nid, title in pend:
                print(f"  ◐ {nid}  {title}")
    elif c in ("answer", "resolve", "settle"):
        E.cmd_answer(_vault(), a.id, a.text)
        print(f"✓ {a.id} resolved")
    elif c in ("pursue", "branch", "extend", "reopen"):
        new = E.cmd_pursue(_vault(), a.id, a.idea)
        print(f"✓ {a.id} reopened" + (f"; spawned {new[0]}" if new else ""))
    elif c in ("status", "map", "tree", "where", "show"):
        print(E.status_text(_vault(), a.id))
    elif c in ("synthesize", "weave", "rollup"):
        nid, fn = E.cmd_synthesize(_vault(), a.title, [x.strip() for x in a.questions.split(",")])
        print(f"✓ {nid}  ({fn})")
    elif c in ("ingest", "source", "add-source"):
        state, rel = E.cmd_ingest(_vault(), a.path, a.title)
        print(f"✓ {state}: {rel}\n  next: compile/update the wiki page(s) that cite it, then `crux validate`")
    elif c in ("validate", "lint", "check"):
        probs = E.cmd_validate(_vault())
        if not probs:
            print("✓ vault is valid")
            return 0
        for nid, msg in probs:
            print(f"✗ {nid}: {msg}")
        return 1
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
