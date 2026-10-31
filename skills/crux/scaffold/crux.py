#!/usr/bin/env python3
"""crux — an agentic research companion.

A scientific-method lab notebook: a tree of Questions (what we don't know) and
Hypotheses (falsifiable, testable leaves), rooted at a project. The agent drives
this CLI by default; it is also meant to be run directly by a human researcher.

Text output here is AGENT-FACING: terse, id-led, `--json` with eyes. It is written about
the PI, never to them, so no line of it is meant to be relayed to the PI verbatim.

Quick tour:
    crux init "My project"                  # bootstrap a vault here
    crux ask "Can X improve Y?"             # open a question (alias: question, q, meta)
    crux hypothesize "A beats B" -p q1 \\
        --expect "A scores 2 points higher"   # a hypothesis states its expectation first
    crux test h1 --run "job 4012"           # record a run link (alias: experiment, run, stage, launch)
    crux finding h1 -d supports -c moderate \\
        -w "three seeds agree"                # what was learned (alias: record, conclude, land)
    crux finding q1 -c strong -a "Yes: …"   # a question's answer (no direction)
    crux park h1                            # park a node the conversation dropped (--undo)
    crux status                             # the tree with derived states (alias: map, tree, where, show)

A node's state is DERIVED from its findings (spec 19): open (none) · leaning (strongest is
weak or moderate) · settled (strongest is strong) · parked. A null not ruled out caps a
finding's confidence at weak.
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
NEUTRAL_KIND_LABEL = E.NEUTRAL_KIND


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


def _pair_discriminates(argv):
    """Which `--fails-if` values carried a `--discriminates` after them. argparse's append
    actions record the two flags in separate lists and lose the interleaving, so the pairing
    is recovered from argv — the one place the order survives."""
    out, idx = [], -1
    for tok in argv:
        if tok == "--fails-if":
            idx += 1; out.append(False)
        elif tok == "--discriminates" and idx >= 0:
            out[idx] = True
    return out

def _removed_verb(raw):
    """The REMOVED_VERBS key a command line reaches, or None."""
    if not raw:
        return None
    if raw[0] in ("task", "todo", "work") and len(raw) > 1:
        return E.REMOVED_TASK_ALIASES.get(raw[1])
    return E.REMOVED_ALIASES.get(raw[0])


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
    s.add_argument("-e", "--expect", default=None,
                   help="REQUIRED: the expected result, stated before any evidence (spec 19)")
    # the methodology slots (spec 13): declared BEFORE the run, and deliberately not `--metric`
    # — that one is the result, written at close
    s.add_argument("--measurement", default=None,
                   help="what this hypothesis measures, and with what instrument — declared "
                        "before the run. Not the result: that is a finding.")
    s.add_argument("--replicates", default=None,
                   help="the declared n / replication plan (\"5 seeds x 3 folds\", "
                        "\"n = 12 per arm\")")
    # lineage (spec 05): an attempt branched from another attempt is its SIBLING, under the
    # same question. The field records the branch; the tree keeps tracking questions.
    s.add_argument("--builds-on", dest="builds_on", default=None, metavar="HID",
                   help="the attempt this one is branched from — a hypothesis under the same "
                        "question. Recorded as a field, never as a tree edge.")
    s.add_argument("-n", "--neutral", action="append", default=[],
                   help="an OUTCOME-NEUTRAL verifiable: a positive control / sanity check that must "
                        "pass whatever the hypothesis turns out to be. Optional.")
    # Additive, NOT a second argument to -v: `nargs=2` was measured to make `-v "a check"`
    # exit with "expected 2 arguments", breaking the skill's documented usage, the agent CLI
    # surface and every existing fixture. These attach to the most recent -v/-n instead, so a
    # bare -v keeps working and a missing scenario is caught by `validate` before the run.
    s.add_argument("--fails-if", dest="fails_if", action="append", default=[],
                   help="the world in which the PRECEDING -v/-n check fails. Two checks are "
                        "redundant if they fail for the same reason; this is what makes that "
                        "visible. Optional.")
    s.add_argument("--discriminates", dest="discriminates", action="append_const", const=True,
                   default=[], help="mark the preceding --fails-if as the one that "
                                    "discriminates against the declared null")
    s.add_argument("--null", default=None,
                   help="optional: the null hypothesis, the most parsimonious alternative "
                        "explanation of a positive result. One line, <=25 words, naming a confound "
                        "family (capacity, chance, leakage, selection, normalization, "
                        "instrumentation). A finding records whether it was ruled out.")
    s.add_argument("--rule", default=None, choices=None,
                   help="optional: how the claim-directed verifiables add up, declared before "
                        "the run: all | any | m-of-n.")
    s.add_argument("--rule-m", dest="rule_m", type=int, default=None,
                   help="the m in m-of-n (how many of the claim-directed checks must pass)")
    s.add_argument("-v", "--verifiable", action="append", default=[],
                                                            help="a falsifiable check (repeatable)")

    s = _jsonable(sub.add_parser("test", aliases=["experiment", "run", "stage", "launch"], help="record a run of a hypothesis: append a run link, lock its checks"))
    s.add_argument("id"); s.add_argument("--to", choices=["staged", "running"], default=None)
    s.add_argument("--run", default=None, help="a run link/job id to record")

    s = _jsonable(sub.add_parser("finding", aliases=["record", "conclude", "land"],
                                 help="record what was learned under a question or hypothesis "
                                      "(spec 19) — its state is derived from its findings"))
    s.add_argument("parent", help="the question or hypothesis this finding is about")
    s.add_argument("-c", "--confidence", required=True, help="strong | moderate | weak")
    s.add_argument("-d", "--direction", default=None,
                   help="hypothesis findings only: supports | against | mixed | no answer yet")
    s.add_argument("-w", "--why", default=None,
                   help="one sentence: why this direction and this confidence")
    s.add_argument("-a", "--answer", default=None,
                   help="question findings only: the answer text")
    s.add_argument("-e", "--evidence", action="append", default=[], metavar="PATH",
                   help="a link under results/ or tasks/ (repeatable)")
    s.add_argument("--null", default=None,
                   help="was the null ruled out? ruled-out | not-ruled-out | none — a null not "
                        "ruled out caps confidence at weak")
    s.add_argument("--vs-expect", dest="vs_expect", default=None,
                   help="how the result compared with the expectation")
    s.add_argument("--verifiables", default=None,
                   help="how the result compared with the verifiables")

    s = _jsonable(sub.add_parser("park", aliases=["shelve"],
                                 help="park a question or hypothesis the conversation dropped "
                                      "(--undo to unpark)"))
    s.add_argument("id")
    s.add_argument("--undo", action="store_true", help="unpark it")

    s = _jsonable(sub.add_parser("status", aliases=["map", "tree", "where", "show"], help="print the tree, or one node's ledger"))
    s.add_argument("id", nargs="?", default=None)

    s = _jsonable(sub.add_parser("ingest", aliases=["source", "add-source"], help="register a PI-curated source (under raw/) into the literature wiki"))
    s.add_argument("path", help="path (under raw/, relative to the vault) to the source to register")
    s.add_argument("-t", "--title", default=None, help="human title for the source (default: filename)")
    s.add_argument("--doi", default=None, help="look the source up on OpenAlex and use its canonical title, author list and year (needs the network; set OPENALEX_API_KEY)")

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
    # An experiment is a task whose output is evidence. Declaring what it concluded is what
    # MAKES it one — the category is computed from this, never typed.
    s.add_argument("--concluded", dest="concluded", action="append", default=[],
                   metavar="HID:CONCLUSION",
                   help="what this run concluded about a hypothesis, e.g. h44:supported "
                        "(repeatable; one of " + ", ".join(E.CONCLUSIONS) + "). "
                        "Declaring any makes this task an experiment.")

    s = _jsonable(tsub.add_parser("done", help="close a task — requires an output that resolves"))
    s.add_argument("id")
    s.add_argument("-o", "--output", dest="outputs", action="append", default=[], metavar="REF",
                   help="a vault path or [[wikilink]] this produced (repeatable)")

    s = _jsonable(tsub.add_parser("drop", help="abandon a task (no output required)"))
    s.add_argument("id")

    s = _jsonable(tsub.add_parser("list", aliases=["ls"], help="query the taskhub — work the frontier"))
    s.add_argument("--frontier", action="store_true",
                   help="only tasks whose blockers are all discharged — the default question")
    s.add_argument("--status", default=None, choices=list(E.TASK_STATUS) + [E.TASK_BLOCKED],
                   help="`blocked` is a legal filter though it is never a stored value")
    s.add_argument("--category", default=None)
    s.add_argument("--ref", default=None, metavar="ID", help="tasks serving this node/page")
    s.add_argument("--blocks", default=None, metavar="ID", help="tasks blocking this task")

    s = _jsonable(tsub.add_parser("show", help="one task's record"))
    s.add_argument("id")

    s = _jsonable(tsub.add_parser("categories", help="the declared category list, or grow it"))
    s.add_argument("--add", default=None, metavar="NAME", help="declare a new category")

    s = _jsonable(sub.add_parser("migrate", help="add the structural sections a newer engine "
                                 "expects, empty. Never writes an evidence field, never fills a "
                                 "null, never moves a verdict — bringing old science up to new "
                                 "rules is the PI's call, one node at a time"))
    s.add_argument("--apply", action="store_true", help="write the changes (default: dry run)")

    s = _jsonable(sub.add_parser("brief", help="the deterministic cold input for an isolated agent: "
                                          "one hypothesis' claim, question, pre-registered checks "
                                          "and the shared factual record — assembled from vault "
                                          "state, never authored by a calling agent"))
    s.add_argument("id", nargs="?", default=None,
                   help="a hypothesis (isolated) or any node (situate); omitted in situate "
                        "mode means the whole programme")
    s.add_argument("--mode", default=E.BRIEF_DEFAULT_MODE, metavar="MODE",
                   help="isolated (default — the bias-proof cold input for an agent) | "
                        "situate (subtree + ancestry + wiki + what is untested, for "
                        "orienting the PI)")
    s.add_argument("--lint-situate", action="store_true",
                   help="read a composed situate answer on stdin and check it against the "
                        "brevity bound (one ELI5 paragraph, three TL;DR paragraphs, "
                        f"{E.SITUATE_BUDGET['total_words']} words, the anchor named). "
                        "Exit 1 on any finding. Reads no vault and writes nothing.")
    s.add_argument("--anchor-title", dest="anchor_title", default=None, metavar="TEXT",
                   help="the anchor node's title, so the answer may name the scope by title "
                        "instead of by id (spec 16). Either form satisfies the anchor rule.")

    s = _jsonable(sub.add_parser("validate", aliases=["lint", "check"], help="run all integrity checks on the vault (tree + wiki + economy + rd + tasks)"))
    s.add_argument("--strict", action="store_true",
                   help="treat economy warnings as failures (exit 1) — off by default")
    s.add_argument("--propose", action="append", default=[], metavar="TERM",
                   help="a candidate glossary term to filter by centrality (repeatable). "
                        "The agent proposes; the engine only filters — see --check=glossary")
    s.add_argument("--propose-file", dest="propose_file", default=None, metavar="PATH",
                   help="read proposed terms from a file, one per line (blank lines and "
                        "'#' comments ignored)")
    s.add_argument("--check", default=None, metavar="LIST",
                   help="comma-separated subset of checks to run: " + ",".join(E.CHECKS)
                        + " (default: all) — plus opt-in: " + ",".join(E.OPT_CHECKS))

    s = _jsonable(sub.add_parser("deck", aliases=["prezit", "present", "slides", "story", "storify"],
                                 help="assemble the presentation payload for an anchor's subtree (spec 11); "
                                      "--verify/--lint on a .tex take the story path (storify)"))
    s.add_argument("anchor", nargs="?", default=None,
                   help="anchor node id — a question, or a hypothesis for a shorter deck")
    g = s.add_mutually_exclusive_group()
    g.add_argument("--verify", metavar="DECK", default=None,
                   help="prove every addressed number in DECK still matches the vault, and "
                        "that a built deck's source files are unchanged since its build")
    g.add_argument("--refresh", metavar="DECK", default=None,
                   help="rewrite DECK's cached values from the vault (values only; prose untouched)")
    g.add_argument("--lint", metavar="DECK", default=None,
                   help="check DECK's slide contract: header comments + the 7-content-unit budget")
    s.add_argument("--strict", action="store_true",
                   help="with --verify: also fail on numerals carrying no address")

    s = sub.add_parser("glossary", aliases=["vocab", "terms"],
                       help="the project's vocabulary: accept / decline a term, or list them")
    gs = s.add_subparsers(dest="gcmd", metavar="<accept|decline|list>")
    g1 = _jsonable(gs.add_parser("accept", help="record that the PI knows this term (it may now be used bare)"))
    g1.add_argument("term"); g1.add_argument("-d", "--definition", default="",
                                             help="the one-line definition, for the PI to read back later")
    g2 = _jsonable(gs.add_parser("decline", help="record that this term is not jargon — asked once, ever"))
    g2.add_argument("term")
    _jsonable(gs.add_parser("list", help="print the vocabulary model (terms + the decline list)"))

    s = _jsonable(sub.add_parser("voice", help="lint a conversation for crux's own vocabulary, or a stand-in for a science term, reaching the PI"))
    g = s.add_mutually_exclusive_group(required=True)
    g.add_argument("--hook", action="store_true",
                   help="read a Claude Code hook payload on stdin; report on the newest agent turn only")
    g.add_argument("--turns", metavar="PATH",
                   help='lint a JSON conversation: [["pi", "..."], ["agent", "..."]]')
    g.add_argument("--install-hook", dest="install_hook", action="store_true",
                   help="register the chat-time lint in a Claude Code settings file (idempotent)")
    s.add_argument("--settings", default=None,
                   help="the settings file --install-hook writes (default: ~/.claude/settings.json)")

    lp = sub.add_parser("lit", aliases=["literature"],
                        help="literature search (spec 17): walk the citation graph out from "
                             "trusted seeds and rank what is missing from raw/")
    lsub = lp.add_subparsers(dest="lcmd", metavar="<sub-verb>")
    s = _jsonable(lsub.add_parser("crawl", help="build the citation subgraph around the seed "
                                               "set and write a ranked candidate list"))
    s.add_argument("slug", help="a name for this search; output lands in wiki/lit/<slug>/")
    s.add_argument("--seed", action="append", default=[], metavar="W…",
                   help="an OpenAlex work id to seed with, beyond the raw/ sources that carry "
                        "one; repeatable")
    s.add_argument("--forward-cap", type=int, default=None,
                   help="top citers to take per work (default 200; the tail is noise)")
    s = _jsonable(lsub.add_parser("fetch", help="download the open-access PDF for each picked "
                                               "candidate into raw/ and register it"))
    s.add_argument("slug", help="the search whose candidate list the picks were read from")
    s.add_argument("--pick", action="append", default=[], metavar="W…", required=True,
                   help="an OpenAlex work id from candidates.tsv to take; repeatable")

    s = _jsonable(lsub.add_parser("lint", help="check a search's scope file and report every "
                                               "problem it carries, not just the first"))
    s.add_argument("slug", help="the search whose wiki/lit/<slug>/scope.md to check")

    # autopilot (spec 18). `check` runs the setup check (`--static`: parse the plan only),
    # `run` is the driver loop, `status` reads the ledger and writes nothing.
    ap = sub.add_parser("auto", aliases=["autopilot"],
                        help="autopilot (spec 18): check a plan, run it, read a run's ledger")
    asub = ap.add_subparsers(dest="acmd", metavar="<sub-verb>")

    s = _jsonable(asub.add_parser("check", help="check a plan: score the base, prove the scorer "
                                                "discriminates, prove the worker can commit"))
    s.add_argument("plan", help="the plan: auto/<qid>/plan.md, vault-relative or absolute")
    s.add_argument("--static", action="store_true",
                   help="parse the plan only — no process started")

    s = _jsonable(asub.add_parser("run", help="run a plan unattended until its budget is "
                                              "spent; continues a run already on disk"))
    s.add_argument("plan", help="the plan: auto/<qid>/plan.md, vault-relative or absolute")
    s.add_argument("--max-attempts", dest="max_attempts", type=int, default=None,
                   help="stop after this many attempts in this invocation")

    s = _jsonable(asub.add_parser("status", help="read a run's ledger — starts nothing, "
                                                 "writes nothing"))
    s.add_argument("qid", nargs="?", default=None,
                   help="the anchor question (default: the most recent run)")

    s = _jsonable(sub.add_parser("doctor", help="check this install: skill/agent links, engine version, vault drift"))

    s = sub.add_parser("selftest", help="run the engine's built-in test suite (no GPU/tokens; validates the install)")
    s.add_argument("--keep", default=None, help="build the demo vault at this path and keep it")

    s = sub.add_parser("serve", aliases=["gui", "ui", "cockpit"], help="open the read-only browser cockpit over this vault")
    s.add_argument("--dir", default=None, help="vault directory (default: resolve upward from the current directory)")
    s.add_argument("--port", type=int, default=None, help="pin a port (default: auto from 8787)")
    s.set_defaults(open=None)
    g = s.add_mutually_exclusive_group()
    g.add_argument("--open", dest="open", action="store_true", help="force-open the system browser")
    g.add_argument("--no-open", dest="open", action="store_false", help="never open a browser")

    # ---- capture plumbing (spec 19, C3): the SessionStart hook, the sweep, pending, wrap.
    hp = sub.add_parser("hook", help="Claude Code hook entry points (read a hook payload on stdin)")
    hsub = hp.add_subparsers(dest="hook_cmd", metavar="<event>", required=True)
    s = hsub.add_parser("session-start", help="inject the always-on core when a vault is near; "
                                              "start the catch-up sweep on startup or clear")
    s.add_argument("--install-hook", dest="install_hook", action="store_true",
                   help="register this hook in a Claude Code settings file (idempotent)")
    s.add_argument("--settings", default=None,
                   help="the settings file --install-hook writes (default: ~/.claude/settings.json)")

    _jsonable(sub.add_parser("sweep", help="run the catch-up sweep now: new transcript text since "
                                           "the mark → one background capture run"))

    pp = _jsonable(sub.add_parser("pending", help="the pending capture candidates /crux-wrap asks about"))
    psub = pp.add_subparsers(dest="pending_cmd", metavar="<action>")
    _jsonable(psub.add_parser("list", aliases=["ls"], help="list pending candidates (default)"))
    s = _jsonable(psub.add_parser("add", help="append a candidate the capture was unsure of"))
    s.add_argument("--kind", required=True, help="question | hypothesis | finding | ...")
    s.add_argument("--parent", default=None, help="the node it would hang under")
    s.add_argument("--text", required=True, help="the candidate, in plain words")
    s.add_argument("--source", default="sweep", help="where it came from (default: sweep)")
    s = _jsonable(psub.add_parser("clear", aliases=["rm", "resolve"],
                                  help="remove candidates once accepted or rejected"))
    s.add_argument("ids", nargs="+")

    s = _jsonable(sub.add_parser("wrap", help="/crux-wrap's data: this session's records, the "
                                              "pending list, and the session's new text"))
    s.add_argument("--transcript", default=None,
                   help="the session transcript (default: the newest in this cwd's projects folder)")

    raw = list(sys.argv[1:] if argv is None else argv)
    gone = _removed_verb(raw)
    if gone:
        # Before argparse and before any vault is resolved: a removed verb prints one pointer
        # line, exits 0 and writes nothing — not even the engine-version stamp.
        print(f"crux: {E.REMOVED_VERBS[gone]}")
        return 0
    args = p.parse_args(argv)
    if not args.cmd:
        p.print_help(); return 0

    if args.cmd not in ("voice", "hook"):
        _update_notice()

    try:
        return dispatch(args)
    except E.CruxError as e:
        print(f"crux: {e}", file=sys.stderr)
        return 1


def _voice_turns(raw):
    """A JSON conversation → `voice_lint`'s pairs. Both shapes a caller reaches for first:
    `[["pi", "..."], ...]` and `[{"speaker": "pi", "text": "..."}, ...]`."""
    if not isinstance(raw, list):
        raise E.CruxError("a conversation is a JSON list of turns, newest last")
    out = []
    for i, turn in enumerate(raw, 1):
        if isinstance(turn, dict):
            out.append((turn.get("speaker"), turn.get("text")))
        elif isinstance(turn, (list, tuple)) and len(turn) == 2:
            out.append((turn[0], turn[1]))
        else:
            raise E.CruxError(f"turn {i} is neither a [speaker, text] pair nor an object "
                              f"carrying 'speaker' and 'text'")
    return out


def _voice_agreed():
    """The PI's agreed vocabulary, licensed from turn zero — empty when there is no vault.

    Read-only and never stamping: linting a conversation must not touch the vault, and the
    absence of one is not an error here."""
    try:
        return [x["term"] for x in E.cmd_glossary_list(E.find_vault())["terms"]]
    except Exception:
        return []


def _voice_hook():
    """The `PostToolUse` entry point. Exits 0 and silent on ANY failure, with no exception:
    a hook that breaks a session is strictly worse than the leak it was added to catch, and
    this one runs after every Bash call the agent makes."""
    try:
        ctx = E.hook_report(json.loads(sys.stdin.read() or "{}"))
    except Exception:
        return 0
    if ctx:
        _emit({"hookSpecificOutput": {"hookEventName": E.VOICE_HOOK_EVENT,
                                      "additionalContext": ctx}})
    return 0


def _csv_arg(val):
    """`--blocked-by t3,t4` -> ['t3','t4']; `None` (the literal the field requires) -> []."""
    return [x.strip() for x in (val or "").split(",") if x.strip() and x.strip() != E.NO_BLOCKERS]


DASH = "—"        # the em dash for an empty slot, named because an f-string expression
                       # may not carry a backslash on the Pythons crux supports


def _dispatch_auto(a):
    """`crux auto check|run|status` (spec 18). `auto` is imported HERE and never at module
    scope, so a verb that starts no process does not load the module that can."""
    t = getattr(a, "acmd", None)
    if not t:
        print("crux: auto needs a sub-verb \u2014 check / run / status", file=sys.stderr)
        return 1
    import auto
    if t == "status":
        res = auto.status(_vault_ro(None), a.qid)
        if a.json:
            return _emit(res)
        best = res.get("best") or {}
        print(f"auto/{res['anchor']}  mode {res['mode']} \u00b7 objective {res['address']} "
              f"{res['direction']} {res['bar']} \u00b7 baseline {res['baseline']}")
        print(f"attempts: {len(res['attempts'])} \u00b7 best {best.get('id') or DASH} = "
              f"{DASH if best.get('score') is None else best.get('score')}")
        print(f"hours: {res['elapsed_hours']:.3f} elapsed of {res['budget_hours']:g} "
              f"\u00b7 {res['attempts_per_hour']} attempts/hour")
        for r in res["attempts"][-5:]:
            print(f"  {r['n']}  {r['id'] or DASH}  {r['status']}  {r['score']}")
        stop = res.get("stop")
        print(f"stop: {stop.get('reason')} \u2014 {stop.get('detail') or ''}" if stop
              else ("live" if res["live"] else "stop: none, and no line for a while"))
        return 0
    root = _vault() if t == "run" else _vault_ro(None)
    plan = a.plan if os.path.isabs(a.plan) or os.path.exists(a.plan) \
        else os.path.join(root, a.plan)
    if t == "run":
        st = auto.run(root, plan, max_attempts=a.max_attempts)
        if a.json:
            return _emit(st)
        print(f"\u2713 auto run stopped: {st.get('reason')} \u2014 {st.get('detail') or ''}")
        return 0
    res = auto.check(root, plan, static=getattr(a, "static", False))
    if a.json:
        _emit(res)
        return 0 if res["ok"] else 1
    for p in res["problems"]:
        print(f"\u2717 {p}")
    if not res["ok"]:
        return 1
    print(f"\u2713 plan ok: {a.plan}" + ("" if res.get("baseline") is None else
          f"  (baseline {res['baseline']}, scorer {res['scorer_seconds']:.1f}s)"))
    return 0


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
        hyp = []
        for spec in a.concluded:
            hid, sep, concl = spec.partition(":")
            if not sep:
                print(f"crux: --concluded takes <hypothesis>:<conclusion> (got {spec!r}) — "
                      f"one of {', '.join(E.CONCLUSIONS)}", file=sys.stderr)
                return 1
            hyp.append((hid.strip(), concl.strip()))
        tid, fn = E.cmd_task_add(root, a.title, a.category, refs=a.refs,
                                 blocked_by=_csv_arg(a.blocked_by), parent=a.parent, why=a.why,
                                 hypothesis_refs=hyp)
        rec = E.task_json(root, tid)
        if a.json:
            return _emit({"id": tid, "file": f"{E.TASK_DIR}/{fn}", "category": rec["category"],
                          "is_experiment": rec["is_experiment"], "refs": a.refs,
                          "hypothesis_refs": rec["hypothesis_refs"],
                          "blocked_by": _csv_arg(a.blocked_by)})
        print(f"✓ {tid}  ({E.TASK_DIR}/{fn})\n" + E.chat_handle(tid, a.title))
        if rec["is_experiment"]:
            print(f"  this task is an experiment (category `{E.TASK_RESERVED_CATEGORY}`, "
                  f"computed from --concluded)")
    elif t == "done":
        st = E.cmd_task_done(root, a.id, a.outputs)
        rec = E.task_json(root, a.id)
        if a.json:
            return _emit({"id": a.id, "status": st, "pending_gate": rec["pending_gate"]})
        print(f"✓ {a.id} → {st}")
    elif t == "drop":
        st = E.cmd_task_drop(root, a.id)
        if a.json:
            return _emit({"id": a.id, "status": st})
        print(f"✓ {a.id} → {st}")
    elif t in ("list", "ls"):
        rows = E.cmd_task_list(root, frontier=a.frontier, status=a.status,
                               category=a.category, ref=a.ref, blocks=a.blocks)
        by = E.task_by_id(root)
        recs = [dict(E.task_json(root, x["id"]), state=E.task_state(x, by)) for x in rows]
        if a.json:
            return _emit(recs)
        if not recs:
            print("no tasks match.")
        for x in recs:
            blk = (" ← " + ", ".join(x["blocked_by"])) if x["blocked_by"] else ""
            print(f"  {x['state']:>7}  {x['id']:>4} [{x['category']}] {x['title']}{blk}")
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


def _capture_vault():
    import sweep as SW
    root = SW.find_vault_near(os.getcwd())
    if not root:
        raise E.CruxError("no crux vault here, above, or one level down. Run `crux init` first.")
    return root


def _dispatch_capture(a):
    """`crux hook session-start | sweep | pending | wrap` (spec 19, C3). The hook exits 0 and
    is silent on ANY failure: a hook that breaks a session is worse than a missed sweep."""
    import sweep as SW
    c = a.cmd
    if c == "hook":
        if a.install_hook:
            path = a.settings or E.DOCTOR_SETTINGS_PATHS[0]
            print(f"✓ session-start hook {SW.install_session_hook(path)}  "
                  f"({os.path.expanduser(path)})")
            return 0
        try:
            try:
                payload = json.loads(sys.stdin.read() or "{}")
            except Exception:
                payload = {}
            ctx = SW.session_start(payload)
            if ctx:
                _emit({"hookSpecificOutput": {"hookEventName": SW.HOOK_EVENT,
                                              "additionalContext": ctx}})
        except Exception:
            pass
        return 0
    root = _capture_vault()
    if c == "sweep":
        cwd = os.getcwd()
        r = SW.run_sweep(root, SW.project_dir(cwd), cwd=cwd)
        if a.json:
            return _emit(r)
        print(f"✓ sweep launched ({r['chars']} chars from {len(r['transcripts'])} transcripts)"
              if r["launched"] else f"sweep: nothing launched — {r['reason']}")
        return 0
    if c == "pending":
        pc = a.pending_cmd or "list"
        if pc == "add":
            rec = SW.pending_add(root, a.kind, a.parent, a.text, a.source)
            if a.json:
                return _emit(rec)
            print(f"✓ pending {rec['id']}")
            return 0
        if pc in ("clear", "rm", "resolve"):
            gone = SW.pending_clear(root, a.ids)
            if a.json:
                return _emit({"cleared": gone})
            print(f"✓ cleared {len(gone)}")
            return 0
        items = SW.pending_list(root)
        if a.json:
            return _emit({"pending": items})
        for i in items:
            print(f"{i['id']}  {i['kind']:<10} {i.get('parent') or DASH:<6} {i['text']}")
        return 0
    if c == "wrap":
        tr = a.transcript or SW.newest_transcript(SW.project_dir(os.getcwd()), root)
        r = SW.wrap(root, os.path.abspath(tr) if tr else None)
        if a.json:
            return _emit(r)
        print(f"recorded this session: {len(r['records'])}")
        for x in r["records"]:
            print(f"  {x['id'] or DASH}  {x['verb']}  {x['result']}")
        print(f"pending: {len(r['pending'])}")
        for i in r["pending"]:
            print(f"  {i['id']}  {i['kind']}  {i['text']}")
        return 0
    return 0


def dispatch(a):
    c = a.cmd
    if c in ("init", "start", "new"):
        if a.seed:
            root, fn = E.cmd_init_from(a.seed, a.dir)
            cd = "" if os.path.relpath(root) == "." else f"cd {os.path.relpath(root)} && "
            print(f"✓ materialized vault at {root} from {a.seed}\n  root node: {fn}\n"
                  f"  next: {cd}crux status   — review the tree and its derived states")
        elif a.title:
            root, fn = E.cmd_init(a.title, a.dir, a.goal)
            cd = "" if os.path.relpath(root) == "." else f"cd {os.path.relpath(root)} && "
            print(f"✓ initialized vault at {root}\n  root node: {fn}\n  next: {cd}crux ask \"the first question\"")
        else:
            print("crux: init needs a project title, or --from <seed.md>", file=sys.stderr); return 1
    elif c in ("ask", "question", "q", "meta"):
        nid, fn = E.cmd_ask(_vault(), a.title, a.parent, a.body)
        if a.json:
            return _emit({"id": nid, "file": fn})
        print(f"✓ {nid}  ({fn})\n" + E.chat_handle(nid, a.title))
    elif c in ("hypothesize", "hypothesis", "idea"):
        nid, fn, warn = E.cmd_hypothesize(_vault(), a.title, a.parent, a.problem,
                                          a.verifiable, a.neutral, a.rule, a.rule_m, a.null,
                                          a.fails_if, _pair_discriminates(sys.argv),
                                          measurement=a.measurement, replicates=a.replicates,
                                          builds_on=a.builds_on, expect=a.expect)
        if a.json:
            return _emit({"id": nid, "file": fn, "parent": a.parent, "warning": warn})
        print(f"✓ {nid}  ({fn})\n" + E.chat_handle(nid, a.title))
        if warn:
            print(f"  ⚠ {warn}", file=sys.stderr)
    elif c in ("test", "experiment", "run", "stage", "launch"):
        default_to = "staged" if c == "stage" else "running"   # `stage` queues; run/launch/experiment/test → running
        st = E.cmd_test(_vault(), a.id, a.to or default_to, a.run)
        if a.json:
            return _emit({"id": a.id, "status": st})
        print(f"✓ {a.id} → {st}")
    elif c in ("finding", "record", "conclude", "land"):
        root = _vault()
        fid, fn, note = E.cmd_finding(root, a.parent, a.confidence, why=a.why,
                                      direction=a.direction, evidence=a.evidence, null=a.null,
                                      vs_expect=a.vs_expect, verifiables=a.verifiables,
                                      answer=a.answer)
        v = E.Vault(root)
        st = E.derive_state(v, a.parent)
        stored = v.get(fid)["fm"].get("confidence")
        if a.json:
            return _emit({"id": fid, "file": fn, "parent": a.parent,
                          "direction": v.get(fid)["fm"].get("direction") or None,
                          "stored_confidence": stored, "capped": bool(note), "note": note,
                          "state": st["state"], "confidence": st["confidence"]})
        print(f"✓ {fid} on {a.parent}  ({fn}) → {a.parent} {st['state']}"
              + (f" · {st['confidence']}" if st["confidence"] else ""))
        if note:
            print(f"  ⚠ {note}", file=sys.stderr)
    elif c in ("park", "shelve"):
        root = _vault()
        parked = E.cmd_park(root, a.id, undo=a.undo)
        st = E.derive_state(E.Vault(root), a.id)
        if a.json:
            return _emit({"id": a.id, "parked": parked, "state": st["state"],
                          "confidence": st["confidence"]})
        print(f"✓ {a.id} → {st['state']}")
    elif c in ("status", "map", "tree", "where", "show"):
        if a.json:
            root = _vault()
            return _emit(E.node_json(root, a.id) if a.id else E.snapshot(root))
        print(E.status_text(_vault(), a.id))
    elif c in ("ingest", "source", "add-source"):
        _root, _wid, _title = _vault(), None, a.title
        if a.doi:                       # lazy: a plain ingest never loads the network module
            import openalex
            _work = openalex.work_by_doi(_root, a.doi)
            _wid, _title = openalex.work_id(_work), _title or openalex.title_line(_work)
        state, rel = E.cmd_ingest(_root, a.path, _title, workid=_wid)
        if a.json:
            return _emit({"state": state, "path": rel})
        print(f"✓ {state}: {rel}\n  next: compile/update the wiki page(s) that cite it, then `crux validate`")
    elif c in ("task", "todo", "work"):
        return _dispatch_task(a)
    elif c in ("auto", "autopilot"):
        return _dispatch_auto(a)
    elif c in ("lit", "literature"):
        lcmd = getattr(a, "lcmd", None)
        root = _vault()
        if lcmd == "lint":                # pure: the scope lint never loads the network module
            scope = E.load_scope(root, a.slug)
            if scope is None:
                raise E.CruxError(f"lit lint: no scope file at {E.scope_path(root, a.slug)} — "
                                  "a search may run without one, but there is nothing to check")
            probs = E.scope_problems(root, scope, a.slug)
            if a.json:
                return _emit({"slug": a.slug, "problems": probs})
            if not probs:
                print(f"✓ scope for {a.slug} is clean ({len(scope['seeds'])} seeds)")
                return 0
            print(f"⚠ {len(probs)} problem(s) in the scope for {a.slug}:")
            for p in probs:
                print(f"  · {p['message']}")
            return 1
        if lcmd == "fetch":
            import openalex            # lazy: no other verb loads the network module
            rows = openalex.fetch_picks(root, a.slug, a.pick)
            if a.json:
                return _emit({"slug": a.slug, "picks": rows})
            for r in rows:
                if r["state"] == "ingested":
                    print(f"✓ {r['path']}\n    {r['title']}")
                elif r["state"] == "skipped":
                    print(f"· already in raw/: {r['path']}")
                elif r["state"] == "failed":
                    print(f"⚠ could not fetch {r['workid']}: {r['reason']}\n"
                          f"    nothing was written to raw/; get it from "
                          f"https://doi.org/{r['doi']} yourself\n    {r['title']}")
                elif r["state"] == "no-oa":
                    print(f"⚠ no open-access PDF for {r['workid']} — fetch it yourself from "
                          f"https://doi.org/{r['doi']}\n    {r['title']}")
                else:
                    print(f"⚠ OpenAlex does not know {r['workid']}")
            n = sum(1 for r in rows if r["state"] == "ingested")
            if n:
                print(f"  next: compile the wiki page(s) for the {n} new source(s), "
                      "then `crux validate`")
            return 1 if any(r["state"] in ("failed", "unknown") for r in rows) else 0
        if lcmd != "crawl":
            raise E.CruxError("lit: expected a sub-verb — `crux lit crawl <slug>`, "
                              "`crux lit lint <slug>` or `crux lit fetch <slug> --pick W…`")
        import openalex                # lazy: no other verb loads the network module
        if a.seed:
            seeds = [r["workid"] for r in E.load_sources(root).values() if r.get("workid")]
            seeds += list(a.seed)
            rows = openalex.crawl(root, seeds,
                                  **({"forward_cap": a.forward_cap} if a.forward_cap else {}))
        else:
            rows = openalex.crawl_scope(root, a.slug,
                                        **({"forward_cap": a.forward_cap} if a.forward_cap else {}))
        seeds = seeds if a.seed else (E.load_scope(root, a.slug) or {}).get("seeds") or [
            r["workid"] for r in E.load_sources(root).values() if r.get("workid")]
        path = openalex.write_candidates(root, a.slug, rows)
        rel = os.path.relpath(path, root)
        if a.json:
            return _emit({"slug": a.slug, "seeds": len(seeds), "candidates": len(rows),
                          "file": rel})
        print(f"✓ {len(rows)} candidates from {len(seeds)} seeds → {rel}")
        for r in rows[:10]:
            print(f"  {r['rank']:>3}. {r['score']:.3f}  {r['seeds']} seeds  {r['title'][:88]}")
        print("  next: read the list, and ingest the keepers with `crux ingest <file> --doi …`")
    elif c in ("rd", "design", "requirements"):
        root = _vault()
        slug, fn = E.cmd_rd(root, a.node, a.title, a.supersedes)
        if a.json:
            return _emit({"slug": slug, "file": f"{E.RD_DIR}/{fn}", "node": a.node,
                          "status": "active", "supersedes": a.supersedes})
        print(f"✓ {E.RD_DIR}/{fn}  (RD for {a.node})\n" + E.chat_handle(slug, a.title)
              + (f"\n  superseded {a.supersedes}" if a.supersedes else "")
              + "\n  next: write the design into it — the node's TL;DR must still stand alone")
    elif c == "migrate":
        res = E.cmd_migrate(_vault(), apply=a.apply)
        if a.json:
            return _emit(res)
        if not res["changes"]:
            print("✓ nothing to migrate — every node has the sections this engine expects.")
        else:
            for ch in res["changes"]:
                print(f"  {ch['id']}: + " + ", ".join(ch["adds"]))
            print(("✓ applied to " if res["applied"] else "dry run — would touch ")
                  + f"{len(res['changes'])} node(s)."
                  + ("" if res["applied"] else "  Re-run with --apply."))
            print("  (never written: the schema stamp, the combination rule, the lock, or the "
                  "content of a null — those are the PI's call, one node at a time.)")
    elif c == "brief":
        if a.lint_situate:
            # deliberately vault-free: the lint is pure text, so an agent can run it from
            # anywhere and "writes nothing" is true by construction rather than by promise
            anchor = (a.id, a.anchor_title) if a.anchor_title else a.id
            found = E.situate_lint(sys.stdin.read(), [anchor] if a.id else [])
            if a.json:
                _emit({"ok": not found,
                       "findings": [{"id": i, "message": m} for i, m in found]})
            else:
                for i, m in found:
                    print(f"  {i}: {m}")
                print("situate: clean" if not found
                      else f"situate: {len(found)} finding(s) — tighten and re-lint.")
            return 1 if found else 0
        b = E.brief(_vault_ro(None), a.id, mode=a.mode)
        if a.json:
            return _emit(b)
        if b["mode"] == "situate":
            an = b["anchor"]
            print(f"{an['id']}  {an['title']}  —  status: {an['status']}")
            for m in b["ancestry"]:
                print(f"  under {m['id']}: {(m['answer_so_far'] or '—')[:70]}")
            ut = b["untested"]
            print(f"  subtree:  {len(b['subtree'])} direct child(ren)")
            print(f"  untested: {len(ut['unrun_ideas'])} unrun · "
                  f"{len(ut['open_checks'])} open check(s) · "
                  f"{len(ut['open_questions'])} open question(s)")
            if b["work"]["active"]:
                print(f"  work:     {len(b['work']['open'])} open task(s) · "
                      f"{len(b['work']['experiments'])} experiment(s)")
            print("  (the paths forward are judgment — this verb never writes a sentence.)")
            return 0
        print(f"{b['id']}  {b['claim']}")
        if b["question"]:
            print(f"  question: {b['question']}")
        if b["null"]:
            print(f"  null:     {b['null']}")
        print(f"  rule:     {b['rule'] or '—'}" + (f" (m={b['rule_m']})" if b["rule_m"] else ""))
        for x in b["verifiables"]:
            tag = " [control]" if x["kind"] == NEUTRAL_KIND_LABEL else ""
            print(f"    - {x['text']}{tag}")
        for pf in b["prior_findings"]:
            print(f"  prior:    {pf['id']} ({pf['verdict']}) {pf['findings'][:70]}")
    elif c in ("validate", "lint", "check"):
        checks = [x.strip() for x in a.check.split(",") if x.strip()] if a.check else None
        propose = list(a.propose)
        if a.propose_file:
            root_ = E.find_vault()
            p = a.propose_file if os.path.isabs(a.propose_file) else os.path.join(root_, a.propose_file)
            if not os.path.isfile(p):
                print(f"crux: no such proposal file: {a.propose_file}", file=sys.stderr); return 1
            propose += [ln.strip() for ln in E.read(p).splitlines()
                        if ln.strip() and not ln.strip().startswith("#")]
        rep = E.validation_report(_vault(), checks, propose=propose)
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
        # vocabulary candidates: a question for the PI, never a finding about the vault.
        # Printed under the info glyph, never counted toward the exit code, never silenced
        # by --strict — a vault whose prose has repeated a term is not broken.
        for cd in rep.get("candidates", []):
            print(f"· candidate term: {cd['term']}  ({cd['reason']}; "
                  f"{cd['occurrences']} occurrence(s) in {', '.join(cd['documents'])})")
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
    elif c in ("deck", "prezit", "present", "slides", "story", "storify"):
        # a read verb: resolve without stamping, like serve — payload assembly and verify
        # never mutate a vault (refresh rewrites the DECK file, still not the vault)
        root = _vault_ro()
        if a.verify and a.verify.lower().endswith(".tex"):
            rep = E.story_verify(root, a.verify)
            failed = bool(rep["mismatch"] or rep["unresolvable"]
                          or (a.strict and rep["unsourced"]))
            if a.json:
                _emit(rep)
                return 1 if failed else 0
            for f in rep["mismatch"]:
                print(f"✗ mismatch     {f['msg']}")
            for f in rep["unresolvable"]:
                print(f"✗ unresolvable {f['msg']}")
            for u in rep["unsourced"]:
                mark = "✗" if a.strict else "⚠"
                print(f"{mark} unsourced    line {u['line']}: numeral '{u['numeral']}' is typed "
                      f"into the body — use a build macro, or \\lit{{}} for a design constant")
            if failed:
                return 1
            print(f"✓ story sources: {len(rep['sources'])} file(s) unchanged since the story "
                  f"was built"
                  + (f" ({len(rep['unsourced'])} unsourced numeral(s) above — --strict to fail on them)"
                     if rep["unsourced"] else ""))
            return 0
        if a.lint and a.lint.lower().endswith(".tex"):
            res = E.story_lint(a.lint)
            if a.json:
                _emit(dict(res, problems=[{"line": i, "message": m} for i, m in res["problems"]]))
                return 1 if res["problems"] else 0
            if res["allowed"]:
                print(f"allowed: {', '.join(res['allowed'])}")
            for _, m in res["problems"]:
                print(f"✗ {m}")
            if res["problems"]:
                return 1
            pages = f"{res['pages']} page(s)" if res["pages"] is not None else "no log, pages unchecked"
            print(f"✓ story lint clean: four sections in order, {res['words']:,} of "
                  f"{E.STORY_WORDS_MAX:,} words, {pages}, voice clean")
            return 0
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
            if "sources" in rep:
                print(f"✓ deck sources: {len(rep['sources'])} file(s) unchanged since the "
                      f"deck was built")
            print(f"✓ deck verified: every addressed number matches the vault"
                  + (f" ({len(rep['unsourced'])} unsourced numeral(s) above — --strict to fail on them)"
                     if rep["unsourced"] else ""))
            return 0
        if a.refresh:
            res = E.deck_refresh(root, a.refresh)
            if a.json:
                return _emit(res)
            if res.get("rebuild"):
                print("  ⚠ a built deck: its DATA comes from build_deck.py — rerun the build "
                      "script; refresh rewrites addressed values only", file=sys.stderr)
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
    elif c in ("glossary", "vocab", "terms"):
        root = _vault()
        if a.gcmd == "list" or not a.gcmd:
            g = E.cmd_glossary_list(root)
            if getattr(a, "json", False):
                return _emit(g)
            if not g["terms"] and not g["declined"]:
                print("glossary is empty — no shared vocabulary agreed yet.")
            for t in g["terms"]:
                print(f"  {t['term']} — {t['definition']}")
            for d in g["declined"]:
                print(f"  (not jargon) {d}")
            return 0
        if a.gcmd == "accept":
            r = E.cmd_glossary_accept(root, a.term, a.definition)
        else:
            r = E.cmd_glossary_decline(root, a.term)
        if a.json:
            return _emit(r)
        print(f"✓ {r['term']} → {r['state']}"
              + ("  (moved from the other list)" if r["moved"] else ""))
    elif c in ("serve", "gui", "ui", "cockpit"):
        import serve as SV
        SV.serve(_vault_ro(a.dir), port=a.port, force_open=a.open)
    elif c == "voice":
        if a.hook:
            return _voice_hook()
        if a.install_hook:
            path = a.settings or E.DOCTOR_SETTINGS_PATHS[0]
            state = E.install_voice_hook(path)
            if a.json:
                return _emit({"settings": os.path.expanduser(path), "state": state,
                              "command": E.voice_hook_command()})
            print(f"✓ voice hook {state}  ({os.path.expanduser(path)})")
            return 0
        found = E.voice_lint(_voice_turns(json.loads(E.read(a.turns))), _voice_agreed())
        if a.json:
            return _emit({"ok": not found,
                          "findings": [{"id": i, "message": m} for i, m in found]})
        for i, m in found:
            print(f"{i}  {m}")
        return 1 if found else 0
    elif c == "doctor":
        r = E.cmd_doctor()
        if a.json:
            _emit(r)
            return 0 if r["ok"] else 1
        print(f"crux doctor — v{r['crux_version']} (engine v{r['engine_version']})\n")
        mark = {"ok": "ok  ", "warn": "warn", "fail": "FAIL"}
        for ck in r["checks"]:
            print(f"  {mark[ck['level']]}  {ck['name']:<10} {ck['detail']}")
            if ck["fix"]:
                print(f"          fix: {ck['fix']}")
        bad = [ck["level"] for ck in r["checks"] if ck["level"] != "ok"]
        print("\n" + (f"{bad.count('fail')} fail · {bad.count('warn')} warn" if bad else "all clear"))
        return 0 if r["ok"] else 1
    elif c in ("hook", "sweep", "pending", "wrap"):
        return _dispatch_capture(a)
    elif c == "selftest":
        import subprocess
        st = os.path.join(os.path.dirname(os.path.abspath(__file__)), "selftest.py")
        return subprocess.call([sys.executable, st] + (["--keep", a.keep] if a.keep else []))
    return 0


if __name__ == "__main__":
    sys.exit(main())
