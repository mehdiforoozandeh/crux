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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import engine as E


def _vault():
    root = E.find_vault()
    warn = E.check_and_stamp_version(root)
    if warn:
        print(f"crux: ⚠ {warn}", file=sys.stderr)
    return root


def main(argv=None):
    p = argparse.ArgumentParser(prog="crux", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", metavar="<verb>")

    s = sub.add_parser("init", aliases=["start", "new"], help="bootstrap a project vault in the current directory")
    s.add_argument("title", nargs="?", default=None); s.add_argument("--dir", default="."); s.add_argument("--goal", default="")
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

    sub.add_parser("validate", aliases=["lint", "check"], help="run all integrity checks on the vault")

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
            print(f"✓ materialized vault at {root} from {a.seed}\n  root node: {fn}\n"
                  f"  next: crux status   — review the tree, then crux review for questions awaiting you")
        elif a.title:
            root, fn = E.cmd_init(a.title, a.dir, a.goal)
            print(f"✓ initialized vault at {root}\n  root node: {fn}\n  next: crux ask \"your first question\"")
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
    elif c in ("validate", "lint", "check"):
        probs = E.cmd_validate(_vault())
        if not probs:
            print("✓ vault is valid")
            return 0
        for nid, msg in probs:
            print(f"✗ {nid}: {msg}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
