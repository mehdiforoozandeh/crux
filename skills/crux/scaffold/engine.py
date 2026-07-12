#!/usr/bin/env python3
"""crux engine — the deterministic (○) core.

A crux vault is a directory of markdown nodes plus two generated views.
Node types: project (root) · question (aggregator) · idea (testable leaf) ·
synthesis (optional, horizontal). The engine never judges and never reads run
logs: the agent supplies a hypothesis' verdict (via verifiable checkboxes) and a
headline metric string; the engine only does bookkeeping — IDs, the Parent::
tree, validators, the evidence-ledger roll-up, the review gate, status
transitions, and regenerating META.md / EXPERIMENTS.md.

Stdlib only. The CLI (crux.py) and selftest.py call the cmd_* functions here.
"""
import os, re, sys, datetime, tempfile, shutil, hashlib

# ----------------------------------------------------------------------------- constants
ENGINE_VERSION = "1.1"          # bumped when verdict/roll-up/view logic or vault format changes; stamped into every vault
VAULT_MARKER = ".crux.yaml"
LEDGER_START = "<!-- crux:ledger:start -->"
LEDGER_END   = "<!-- crux:ledger:end -->"

# wiki layer (Epic 3): a PI-curated literature wiki alongside the q/h tree.
WIKI_DIR     = "wiki"           # agent-owned compiled markdown pages + log.md + SCHEMA.md
RAW_DIR      = "raw"            # immutable, PI-curated sources; the engine hashes bytes, never reads content
WIKI_INDEX   = "WIKI.md"        # generated index of wiki pages (Karpathy's index.md), rendered at vault root
SOURCES_FILE = os.path.join(WIKI_DIR, ".sources.tsv")   # engine-owned source registry: sha256<TAB>date<TAB>path<TAB>title
WIKI_LOG     = os.path.join(WIKI_DIR, "log.md")          # append-only chronological log (Karpathy's log.md)
WIKI_SCHEMA  = os.path.join(WIKI_DIR, "SCHEMA.md")       # per-vault conventions the agent + PI co-evolve
GENERATED    = ("META.md", "EXPERIMENTS.md", WIKI_INDEX) # root .md views the node scan must never treat as nodes

TYPES            = ["project", "question", "idea", "synthesis"]
QUESTION_STATUS  = ["open", "review", "resolved"]
IDEA_STATUS      = ["idea", "staged", "running", "done"]
VERDICTS         = ["supported", "partial", "refuted", "inconclusive"]
TERMINAL_IDEA    = "done"
TERMINAL_QUESTION= "resolved"

class CruxError(Exception):
    """Raised on any rule violation; the CLI turns it into a clean message + exit 1."""

def now():
    return datetime.datetime.now().isoformat(timespec="seconds")

# ----------------------------------------------------------------------------- tiny flat YAML
# We control the schema: frontmatter and config are flat `key: value` maps of
# scalars (str/int/bool/None). That lets us avoid a YAML dependency while staying
# Obsidian-compatible.
def yaml_load(text):
    d = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or ":" not in line:
            continue
        key, _, val = line.partition(":")
        d[key.strip()] = _coerce(val.strip())
    return d

def _coerce(val):
    if val == "":
        return None
    if (val[0], val[-1]) in (('"', '"'), ("'", "'")):
        return val[1:-1]
    if val == "true":  return True
    if val == "false": return False
    if re.fullmatch(r"-?\d+", val): return int(val)
    return val

def yaml_dump(d):
    return "\n".join(f"{k}: {_fmt(v)}" for k, v in d.items())

def _fmt(v):
    if v is None:  return ""
    if v is True:  return "true"
    if v is False: return "false"
    if isinstance(v, int): return str(v)
    s = str(v)
    if s == "" or s != s.strip() or s[0] in "[]{}>|*&!%@`\"'#" or ":" in s or "#" in s:
        return '"' + s.replace('"', '\\"') + '"'
    return s

# ----------------------------------------------------------------------------- file io
def read(path):
    with open(path, encoding="utf-8") as f:
        return f.read()

def write_if_changed(path, content):
    """Write only if bytes differ. This is what makes refresh idempotent."""
    if os.path.exists(path) and read(path) == content:
        return False
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return True

def parse_doc(text):
    m = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.S)
    if m:
        return yaml_load(m.group(1)), m.group(2)
    return {}, text

def render_doc(fm, body):
    return "---\n" + yaml_dump(fm) + "\n---\n\n" + body.lstrip("\n").rstrip() + "\n"

def replace_block(body, start, end, new):
    block = f"{start}\n{new}\n{end}"
    if start in body and end in body:
        return re.sub(re.escape(start) + r".*?" + re.escape(end), lambda _: block, body, flags=re.S)
    return body.rstrip() + "\n\n" + block + "\n"

# ----------------------------------------------------------------------------- misc helpers
def slugify(title):
    s = re.sub(r"[^a-z0-9]+", "_", title.lower()).strip("_")
    return (s or "node")[:40]

def natkey(nid):
    m = re.match(r"([a-zA-Z]*)(\d*)", nid)
    return (m.group(1), int(m.group(2)) if m.group(2) else 0)

def find_vault(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.exists(os.path.join(d, VAULT_MARKER)):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            raise CruxError("not inside a crux vault (no .crux.yaml found). Run `crux init` first.")
        d = parent

def check_and_stamp_version(root):
    """Compare the engine version stamped in the vault against this engine.
    On mismatch: return a loud warning AND record the current version (a git diff on
    .crux.yaml becomes the durable, auditable record of drift). Returns None if in sync."""
    cfg_path = os.path.join(root, VAULT_MARKER)
    cfg = yaml_load(read(cfg_path))
    stamped = cfg.get("engine_version")
    stamped = None if stamped is None else str(stamped)
    if stamped == ENGINE_VERSION:
        return None
    cfg["engine_version"] = ENGINE_VERSION
    write_if_changed(cfg_path, yaml_dump(cfg) + "\n")
    if stamped is None:
        return None  # pre-versioned vault; silently adopt the stamp
    return (f"engine drift: this vault was written with crux engine v{stamped}, "
            f"but you are running v{ENGINE_VERSION}. Verdicts and generated views may "
            f"differ. Pin the matching engine (re-install the crux skill at v{stamped}) "
            f"if you need to reproduce the recorded results exactly.")

# ----------------------------------------------------------------------------- templates
_BUILTIN = {
"project": """---
id: <<id>>
type: project
title: <<title>>
status: active
created: <<now>>
updated: <<now>>
---

# <<title>>

Project root — the whole research program. Top-level questions point here via `Parent::`.

## Goal

<<goal>>

## Navigate

See [[META]] for the live question tree and dashboard, and [[EXPERIMENTS]] for the flat experiment registry.
""",
"question": """---
id: <<id>>
type: question
title: <<title>>
parent: <<parent_id>>
status: open
stale: false
created: <<now>>
updated: <<now>>
---

# <<id>> — <<title>>

Parent:: [[<<parent_basename>>]]

## Question

<<title>>

## Answer so far

_(interpretation — written by the PI/agent; auto-flagged stale when new evidence lands)_

<<ledger_start>>
_(no children yet)_
<<ledger_end>>
""",
"idea": """---
id: <<id>>
type: idea
title: <<title>>
parent: <<parent_id>>
status: idea
verdict:
metric:
created: <<now>>
updated: <<now>>
---

# <<id>> — <<title>>

Parent:: [[<<parent_basename>>]]

## Problem Statement

<<problem>>

## Idea / Hypothesis

<<title>>

## Verifiables

<!-- on close, tick each box met/unmet/could-not-evaluate; the verdict is derived from them. -->
- [ ] <<verifiable>>

## Planned Intervention

_(how this hypothesis will be tested)_

## Run Links

_(none yet)_

## Findings

_(written by the PI/agent when the case is closed)_
""",
"synthesis": """---
id: <<id>>
type: synthesis
title: <<title>>
created: <<now>>
updated: <<now>>
---

# Synthesis — <<title>>

Related:: <<related>>

## Headline conclusions

## Cross-run table

## Implications for next batch
""",
"wiki": """---
type: wiki
title: <<title>>
summary: <<summary>>
category: <<category>>
sources: <<sources>>
created: <<now>>
updated: <<now>>
---

# <<title>>

_(lead: one sentence that extends the summary — scope, context, or the sharpest claim; don't restate the summary)_

## Background

_(synthesize across the cited sources — every claim traces to a file under `raw/`; don't mirror a single source)_

## See also

Related:: <<related>>
""",
"wiki_schema": """---
type: wiki_schema
title: Wiki schema
---

# Wiki schema — conventions for THIS vault's literature wiki

Co-evolved by you (the PI) and the agent. The global rules live in the `crux-wiki`
skill; this file records the choices specific to this project.

## What the wiki is
A literature background layer: prior methods, SOTA, baselines, datasets, definitions —
compiled once from the immutable sources in `raw/`, then kept current. It exists to
sharpen `ask` / `hypothesize` and to interpret findings. It is **not** a record of this
project's own results.

## Flow rule (hard)
Literature → wiki → informs the tree. **Never** the reverse. A wiki page may link other
wiki pages; it must never cite a q/h tree node. Findings never enter the wiki.

## Page conventions
- One concept / entity / comparison per page; concept-slug filenames (`film-conditioning.md`).
- Frontmatter: `title`, `summary` (one line — becomes the index entry), `category`
  (entity | concept | method | comparison | dataset | overview | …), `sources`
  (comma-separated `raw/…` paths every claim traces to).
- Write for the LLM reader: dense and explicit over pretty.

## Categories in use
_(list the categories this vault uses, so pages stay consistent)_
""",
}

def load_template(kind):
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates", kind + ".md")
    text = read(path) if os.path.exists(path) else _BUILTIN[kind]
    return text.replace("<<ledger_start>>", LEDGER_START).replace("<<ledger_end>>", LEDGER_END)

def fill(text, **kw):
    kw.setdefault("now", now())
    for k, v in kw.items():
        text = text.replace(f"<<{k}>>", str(v))
    return text

# ----------------------------------------------------------------------------- vault model
class Node(dict):
    @property
    def id(self):     return self["fm"]["id"]
    @property
    def type(self):   return self["fm"]["type"]
    @property
    def title(self):  return self["fm"].get("title", "")
    @property
    def status(self): return self["fm"].get("status")
    @property
    def parent(self):  return self["fm"].get("parent")
    @property
    def basename(self): return self["fn"][:-3]

class Vault:
    def __init__(self, root):
        self.root = root
        self.cfg = yaml_load(read(os.path.join(root, VAULT_MARKER)))
        self.nodes = {}
        for fn in sorted(os.listdir(root)):
            if not fn.endswith(".md") or fn in GENERATED:
                continue
            fm, body = parse_doc(read(os.path.join(root, fn)))
            if "id" not in fm:
                continue
            self.nodes[fm["id"]] = Node(path=os.path.join(root, fn), fn=fn, fm=fm, body=body)
        self.children = {nid: [] for nid in self.nodes}
        for nid, n in self.nodes.items():
            p = n.parent
            if p and p in self.children:
                self.children[p].append(nid)
        for k in self.children:
            self.children[k].sort(key=natkey)

    def get(self, nid):
        if nid not in self.nodes:
            raise CruxError(f"no node with id '{nid}'")
        return self.nodes[nid]

    def root_node(self):
        return self.get(self.cfg["root_id"])

def is_terminal(node):
    if node.type == "idea":     return node.status == TERMINAL_IDEA
    if node.type == "question": return node.status == TERMINAL_QUESTION
    return True

# ----------------------------------------------------------------------------- verifiables / verdict
def count_verifiables(body):
    met = unmet = na = 0
    in_sec = False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line.strip().lower() == "## verifiables"
            continue
        if not in_sec:
            continue
        m = re.match(r"\s*- \[(.)\]", line)
        if not m:
            continue
        c = m.group(1).lower()
        if c == "x":   met += 1
        elif c == "-": na += 1
        else:          unmet += 1
    return met, unmet, na

def derive_verdict(met, unmet, na):
    total = met + unmet + na
    if total == 0:                 return None
    if met == total:               return "supported"
    if unmet == 0 and na > 0:      return "inconclusive"
    if met == 0 and unmet > 0:     return "refuted"
    return "partial"

# ----------------------------------------------------------------------------- ledger / gate / refresh
def ledger_counts(v, qid):
    """Pure roll-up of a question's direct children into JSON-able counts. Single source
    of truth shared by `ledger_block` (the markdown view) and `snapshot` (the GUI JSON)."""
    kids = v.children[qid]
    ideas = [v.nodes[k] for k in kids if v.nodes[k].type == "idea"]
    subqs = [v.nodes[k] for k in kids if v.nodes[k].type == "question"]
    vc = {x: sum(1 for n in ideas if n["fm"].get("verdict") == x) for x in VERDICTS}
    return {"children": len(kids),
            "ideas_total": len(ideas),
            "ideas_done": sum(1 for n in ideas if n.status == "done"),
            "supported": vc["supported"], "partial": vc["partial"],
            "refuted": vc["refuted"], "inconclusive": vc["inconclusive"],
            "subq_total": len(subqs),
            "subq_resolved": sum(1 for n in subqs if n.status == "resolved")}

def ledger_block(v, qid):
    kids = v.children[qid]
    if not kids:
        return "_(no children yet)_"
    ideas = [v.nodes[k] for k in kids if v.nodes[k].type == "idea"]
    subqs = [v.nodes[k] for k in kids if v.nodes[k].type == "question"]
    c = ledger_counts(v, qid)
    summary = (f"**{c['children']} children** · ideas {c['ideas_done']}/{c['ideas_total']} done "
               f"(supported {c['supported']}, partial {c['partial']}, "
               f"refuted {c['refuted']}, inconclusive {c['inconclusive']})")
    if subqs:
        summary += f" · sub-questions {c['subq_resolved']}/{c['subq_total']} resolved"
    rows = []
    for n in (ideas + subqs):
        if n.type == "idea":
            extra = []
            if n["fm"].get("verdict"): extra.append(f"verdict **{n['fm']['verdict']}**")
            if n["fm"].get("metric"):  extra.append(f"metric `{n['fm']['metric']}`")
            tail = (" — " + ", ".join(extra)) if extra else ""
            rows.append(f"- `{n.id}` [[{n.basename}|{n.title}]] — *{n.status}*{tail}")
        else:
            rows.append(f"- `{n.id}` _(Q)_ [[{n.basename}|{n.title}]] — *{n.status}*")
    return summary + "\n\n" + "\n".join(rows)

def refresh(root):
    """Recompute all derived content from the nodes. Idempotent. Returns True if anything changed on disk."""
    v = Vault(root)
    changed = False
    # review gate (two-directional): a non-resolved question is in `review` iff it has
    # >=1 child and all direct children are terminal; otherwise `open`. Recomputing both
    # directions each refresh corrects an intermediate trip — e.g. during a bulk seed
    # materialize, a question can momentarily have only a terminal child before its later
    # (non-terminal) children are added. `resolved` is human-set and never auto-changed.
    for qid, n in v.nodes.items():
        if n.type == "question" and n.status in ("open", "review"):
            kids = v.children[qid]
            terminal = bool(kids) and all(is_terminal(v.nodes[k]) for k in kids)
            n["fm"]["status"] = "review" if terminal else "open"
    # evidence ledger into each question file (engine-owned block only)
    for qid, n in v.nodes.items():
        if n.type == "question":
            n["body"] = replace_block(n["body"], LEDGER_START, LEDGER_END, ledger_block(v, qid))
    # persist questions (status + ledger) idempotently
    for qid, n in v.nodes.items():
        if n.type == "question":
            if write_if_changed(n["path"], render_doc(n["fm"], n["body"])):
                changed = True
    # regenerate views
    import render
    if write_if_changed(os.path.join(root, "META.md"), render.render_meta(v)):        changed = True
    if write_if_changed(os.path.join(root, "EXPERIMENTS.md"), render.render_experiments(v)): changed = True
    if wiki_active(root):
        if write_if_changed(os.path.join(root, WIKI_INDEX), render.render_wiki(v, root)): changed = True
    return changed

# ----------------------------------------------------------------------------- validation
def validate(v):
    problems = []
    req = {"project": ["id","type","title","status"],
           "question":["id","type","title","status","parent"],
           "idea":    ["id","type","title","status","parent"],
           "synthesis":["id","type","title"]}
    for nid, n in v.nodes.items():
        t = n.type
        if t not in TYPES:
            problems.append((nid, f"unknown type '{t}'")); continue
        for k in req[t]:
            if n["fm"].get(k) in (None, ""):
                problems.append((nid, f"missing required field '{k}'"))
        if t == "question" and n.status not in QUESTION_STATUS:
            problems.append((nid, f"bad question status '{n.status}'"))
        if t == "idea" and n.status not in IDEA_STATUS:
            problems.append((nid, f"bad idea status '{n.status}'"))
        if t == "idea" and n["fm"].get("verdict") not in (None, "", *VERDICTS):
            problems.append((nid, f"bad verdict '{n['fm'].get('verdict')}'"))
        # parent integrity
        if t in ("question", "idea"):
            p = n.parent
            if p not in v.nodes:
                problems.append((nid, f"parent '{p}' does not exist"))
            else:
                pt = v.nodes[p].type
                if t == "idea" and pt != "question":
                    problems.append((nid, f"idea parent must be a question, got '{pt}'"))
                if t == "question" and pt not in ("project", "question"):
                    problems.append((nid, f"question parent must be project/question, got '{pt}'"))
        # running/done ideas need verifiables
        if t == "idea" and n.status in ("running", "done"):
            if sum(count_verifiables(n["body"])) == 0:
                problems.append((nid, f"idea is '{n.status}' but has no verifiables"))
        # ledger markers present in questions
        if t == "question" and (LEDGER_START not in n["body"] or LEDGER_END not in n["body"]):
            problems.append((nid, "missing ledger markers"))
    # cycle / single-parent tree
    for nid, n in v.nodes.items():
        seen, cur = set(), nid
        while cur in v.nodes and v.nodes[cur].parent:
            cur = v.nodes[cur].parent
            if cur in seen:
                problems.append((nid, "parent cycle detected")); break
            seen.add(cur)
    return problems

# ----------------------------------------------------------------------------- wiki layer (Epic 3)
# A PI-curated literature wiki: immutable sources under raw/, agent-compiled pages under
# wiki/. The engine owns only the bookkeeping — source hashes, the generated index, and the
# structural lint. It never reads a source's content or judges a page. Everything that needs
# meaning (what to compile, contradictions, staleness) is the agent's job. Flow is one-way:
# literature → wiki → informs the tree; findings never enter the wiki.
WIKILINK_RE = re.compile(r"\[\[\s*([^\]|#]+?)\s*(?:[|#][^\]]*)?\]\]")

def wiki_dir(root):    return os.path.join(root, WIKI_DIR)
def raw_dir(root):     return os.path.join(root, RAW_DIR)
def wiki_active(root): return os.path.isdir(wiki_dir(root))

def _rel(root, path):
    return os.path.relpath(os.path.abspath(path), root).replace(os.sep, "/")

def link_targets(text):
    """Basenames referenced by [[wikilinks]] in text (alias/heading stripped, any dir
    prefix and .md dropped). Order-preserving-unique, deterministic."""
    out, seen = [], set()
    for m in WIKILINK_RE.findall(text):
        t = m.strip().split("/")[-1]
        if t.endswith(".md"):
            t = t[:-3]
        if t and t not in seen:
            seen.add(t); out.append(t)
    return out

def load_sources(root):
    """Read the engine-owned source registry → {relpath: {sha256, date, title}}."""
    path = os.path.join(root, SOURCES_FILE)
    reg = {}
    if os.path.exists(path):
        for line in read(path).splitlines():
            if not line.strip():
                continue
            parts = line.split("\t")
            if len(parts) >= 4:
                reg[parts[2]] = {"sha256": parts[0], "date": parts[1], "title": "\t".join(parts[3:])}
    return reg

def save_sources(root, reg):
    lines = [f"{r['sha256']}\t{r['date']}\t{rel}\t{r['title']}" for rel, r in sorted(reg.items())]
    write_if_changed(os.path.join(root, SOURCES_FILE), ("\n".join(lines) + "\n") if lines else "")

def _sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()

def scan_wiki_pages(root):
    """Every compiled wiki page (a *.md under wiki/ with `type: wiki`), sorted by slug.
    log.md / SCHEMA.md are excluded automatically (their type isn't `wiki`)."""
    pages, wd = [], wiki_dir(root)
    if not os.path.isdir(wd):
        return pages
    for dirpath, dirnames, filenames in os.walk(wd):
        dirnames[:] = sorted(d for d in dirnames if not d.startswith("."))
        for fn in sorted(filenames):
            if not fn.endswith(".md"):
                continue
            fm, body = parse_doc(read(os.path.join(dirpath, fn)))
            if fm.get("type") != "wiki":
                continue
            srcs = [s.strip() for s in str(fm.get("sources") or "").split(",") if s.strip()]
            pages.append({"slug": fn[:-3], "fn": fn, "path": os.path.join(dirpath, fn), "fm": fm,
                          "body": body, "title": fm.get("title"), "summary": fm.get("summary"),
                          "category": (fm.get("category") or "uncategorized"), "sources": srcs,
                          "links": link_targets(body)})
    pages.sort(key=lambda p: p["slug"])
    return pages

WIKI_SPECIALS = {"_index": WIKI_INDEX, "_log": WIKI_LOG, "_schema": WIKI_SCHEMA}

def _wiki_snapshot(root):
    """The `wiki` block of snapshot(): the index only — public per-page fields plus a
    content hash for change detection, never a body or a filesystem path."""
    if not wiki_active(root):
        return {"active": False, "pages": [], "sources": [],
                "specials": {"index": False, "log": False, "schema": False}}
    return {
        "active": True,
        "pages": [{"slug": p["slug"], "title": p["title"], "summary": p["summary"],
                   "category": p["category"], "links": p["links"], "sources": p["sources"],
                   "hash": _sha256_file(p["path"])[:16]}
                  for p in scan_wiki_pages(root)],
        "sources": [{"date": r["date"], "path": rel, "title": r["title"]}
                    for rel, r in sorted(load_sources(root).items())],
        "specials": {"index": os.path.isfile(os.path.join(root, WIKI_INDEX)),
                     "log": os.path.isfile(os.path.join(root, WIKI_LOG)),
                     "schema": os.path.isfile(os.path.join(root, WIKI_SCHEMA))},
    }

def _mention_snippet(body, slug, width=140):
    """The first line of `body` whose wikilinks mention `slug`, trimmed to ~width chars
    around the mention (the canonical link parser decides what counts as a mention)."""
    for line in body.splitlines():
        if slug not in link_targets(line):
            continue
        line = line.strip()
        if len(line) <= width:
            return line
        pos = line.find(slug)
        br = line.rfind("[[", 0, pos)
        anchor = br if br != -1 else max(pos, 0)
        start = max(0, anchor - width // 3)
        end = min(len(line), start + width)
        return ("…" if start else "") + line[start:end] + ("…" if end < len(line) else "")
    return ""

def wiki_page_payload(root, slug):
    """Payload for /wiki/<slug>.json: a scanned page (with backlinks) or a reserved
    special; None for unknown or traversal-shaped slugs. The slug is only ever matched
    against the scan + reserved names — never used as a filesystem path — and rejection
    happens before any file is read. Duplicate slugs resolve deterministically: reserved
    names always win, then the first page by sorted path."""
    if not wiki_active(root):
        return None
    if slug in WIKI_SPECIALS:
        path = os.path.join(root, WIKI_SPECIALS[slug])
        if not os.path.isfile(path):
            return None
        fm, body = parse_doc(read(path))
        return {"slug": slug, "title": fm.get("title") or None,
                "summary": fm.get("summary") or None, "category": fm.get("category") or None,
                "sources": [], "updated": fm.get("updated") or None,
                "body": body, "backlinks": []}
    if not slug or "/" in slug or "\\" in slug or ".." in slug or slug.startswith("."):
        return None
    pages = scan_wiki_pages(root)
    matches = [p for p in pages if p["slug"] == slug]
    if not matches:
        return None
    page = min(matches, key=lambda p: p["path"])
    backlinks = [{"slug": q["slug"], "title": q["title"],
                  "snippet": _mention_snippet(q["body"], slug)}
                 for q in pages if q["slug"] != slug and slug in q["links"]]
    return {"slug": page["slug"], "title": page["title"], "summary": page["summary"],
            "category": page["category"], "sources": page["sources"],
            "updated": page["fm"].get("updated") or None,
            "body": page["body"], "backlinks": backlinks}

def ensure_wiki(root):
    """Lazily stand up the wiki subsystem (idempotent, safe on a pre-wiki vault)."""
    os.makedirs(wiki_dir(root), exist_ok=True)
    os.makedirs(raw_dir(root), exist_ok=True)
    if not os.path.exists(os.path.join(root, WIKI_LOG)):
        write_if_changed(os.path.join(root, WIKI_LOG),
                         "# Wiki log\n\n_Append-only. `grep '^## \\[' log.md` for the timeline._\n")
    if not os.path.exists(os.path.join(root, WIKI_SCHEMA)):
        write_if_changed(os.path.join(root, WIKI_SCHEMA), load_template("wiki_schema"))

def cmd_ingest(root, path, title=None):
    """Register a PI-curated source under raw/: record its sha256, append a Karpathy-format
    log line, (re)render the index. The agent compiles pages afterward — the engine never
    reads the source's content. Idempotent on an unchanged, already-registered file."""
    abspath = os.path.abspath(path if os.path.isabs(path) else os.path.join(root, path))
    rawroot = os.path.abspath(raw_dir(root))
    if os.path.commonpath([abspath, rawroot]) != rawroot:
        raise CruxError(f"ingest: a source must live under {RAW_DIR}/ (got {path!r}); place the "
                        "file in raw/ first — the PI curates what enters raw/")
    if not os.path.isfile(abspath):
        raise CruxError(f"ingest: no such file: {path}")
    ensure_wiki(root)
    rel, sha = _rel(root, abspath), _sha256_file(abspath)
    title = " ".join((title or os.path.splitext(os.path.basename(abspath))[0]).split())  # single-line: registry + log are line-based
    reg = load_sources(root)
    if rel in reg and reg[rel]["sha256"] == sha:
        refresh(root)
        return "unchanged", rel
    state = "updated" if rel in reg else "ingested"
    reg[rel] = {"sha256": sha, "date": datetime.date.today().isoformat(), "title": title}
    save_sources(root, reg)
    with open(os.path.join(root, WIKI_LOG), "a", encoding="utf-8") as f:
        f.write(f"\n## [{datetime.date.today().isoformat()}] ingest | {title}\n")
    refresh(root)
    return state, rel

def validate_wiki(root):
    """Structural lint over the wiki layer — mechanical checks only (broken/flow links,
    orphans, missing frontmatter, source hash drift, uncompiled/missing sources). Semantic
    checks (contradictions, staleness, missing pages) are the agent's job, not the engine's."""
    problems = []
    if not wiki_active(root):
        return problems
    v = Vault(root)
    pages = scan_wiki_pages(root)
    page_slugs = {p["slug"] for p in pages}
    tree_targets = set(v.nodes) | {n.basename for n in v.nodes.values()}

    # per-page: required frontmatter + cited-source integrity + link resolution
    for p in pages:
        for field in ("title", "summary"):
            if not str(p["fm"].get(field) or "").strip():
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': missing required field '{field}'"))
        for s in p["sources"]:
            if not os.path.isfile(os.path.join(root, s)):
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': cites missing source '{s}' (not a file under the vault)"))
        for t in p["links"]:
            if t in page_slugs:
                continue
            if t in tree_targets:
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': flow violation — links "
                                 f"tree node [[{t}]] (the wiki must not cite the tree)"))
            else:
                problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': broken link [[{t}]]"))

    # orphans: no inbound from another wiki page or a tree node. The generated WIKI.md is NOT
    # scanned as a page, so its links can never rescue an orphan (guards the Emmimal miscount).
    inbound = {p["slug"]: 0 for p in pages}
    for p in pages:
        for t in p["links"]:
            if t in inbound and t != p["slug"]:
                inbound[t] += 1
    for n in v.nodes.values():
        for t in link_targets(n["body"]):
            if t in inbound:
                inbound[t] += 1
    for p in pages:
        if inbound[p["slug"]] == 0:
            problems.append((f"wiki:{p['slug']}", f"wiki page '{p['slug']}': orphan (no inbound links)"))

    # tree → wiki: an explicit [[wiki/…]] reference in a node body must resolve
    for n in v.nodes.values():
        for m in re.findall(r"\[\[\s*wiki/([^\]|#]+?)(?:\.md)?\s*(?:[|#][^\]]*)?\]\]", n["body"]):
            if m.strip().split("/")[-1] not in page_slugs:
                problems.append((f"node:{n.id}", f"node '{n.id}': broken wiki link [[wiki/{m.strip()}]]"))

    # source registry: hash drift, missing file, uncompiled (no page cites it)
    reg, compiled = load_sources(root), set()
    for p in pages:
        compiled.update(p["sources"])
    for rel, rec in sorted(reg.items()):
        ap = os.path.join(root, rel)
        if not os.path.isfile(ap):
            problems.append((f"src:{rel}", f"source '{rel}': missing (registered but file not found)")); continue
        if _sha256_file(ap) != rec["sha256"]:
            problems.append((f"src:{rel}", f"source '{rel}': hash drift since ingest (re-ingest to refresh)"))
        if rel not in compiled:
            problems.append((f"src:{rel}", f"uncompiled source '{rel}': registered but no wiki page cites it"))
    return problems

# ----------------------------------------------------------------------------- commands (called by CLI + selftest)
def _write_obsidian_vault(root):
    """Make the vault a recognized Obsidian vault out of the box: the presence of
    `.obsidian/app.json` is what makes Obsidian open the folder as an *existing* vault
    (no 'create vault?' prompt), so the Q/H `[[Parent::]]` graph is one click away.
    Empty config = Obsidian fills in its own sane defaults on first open."""
    od = os.path.join(root, ".obsidian")
    os.makedirs(od, exist_ok=True)
    write_if_changed(os.path.join(od, "app.json"), "{}\n")

def cmd_init(title, dirpath=".", goal=""):
    root = os.path.abspath(dirpath)
    os.makedirs(root, exist_ok=True)
    if os.path.exists(os.path.join(root, VAULT_MARKER)):
        raise CruxError("a crux vault already exists here")
    slug = slugify(title)
    cfg = {"title": title, "slug": slug, "root_id": "root", "engine_version": ENGINE_VERSION,
           "counter_q": 0, "counter_h": 0, "counter_s": 0}
    write_if_changed(os.path.join(root, VAULT_MARKER), yaml_dump(cfg) + "\n")
    body = fill(load_template("project"), id="root", title=title, goal=goal or "_(state the program goal)_")
    write_if_changed(os.path.join(root, f"{slug}.md"), body)
    _write_obsidian_vault(root)
    refresh(root)
    return root, f"{slug}.md"

# ----------------------------------------------------------------------------- seed-spec (setup: read source -> propose tree -> approve -> write)
# The agent drafts one human-editable seed file; the human approves it; the engine
# materializes the whole vault atomically. Format = indented-bullet outline, indent
# (2 spaces) = nesting, type prefix = node kind:
#
#   - Project: TITLE — GOAL
#     - Q: a question
#       - Q: a nested question
#         - H: a hypothesis                         (open; not yet run)
#           - v: metric ≥ threshold vs baseline     (a verifiable)
#       - H: [tested] an already-run hypothesis     (migration: reconstruct done work)
#         - v: [x] first check (found: 0.46 → 0.48) (tick = met; parenthetical = evidence)
#         - v: [ ] second check
#         - finding: one-line narrative of the result
#
# Rules mirror the model: Project→Q ; Q→Q|H ; H→v|finding|problem. Verdicts on
# [tested] hypotheses are still derived mechanically from the ticks — the engine
# never invents them.
def _seed_val(line):
    """Return (indent, key, value) for a `  - Key: value` bullet, else None."""
    m = re.match(r"^(\s*)-\s+([A-Za-z]+):\s?(.*)$", line.rstrip())
    if not m:
        return None
    return len(m.group(1)), m.group(2).lower(), m.group(3).strip()

def _parse_verifiable(val):
    m = re.match(r"\[([ xX-])\]\s*(.*)$", val)
    tick, text = (m.group(1).lower(), m.group(2).strip()) if m else (" ", val)
    evidence = None
    if m:  # only tested verifiables carry a trailing (evidence) note
        em = re.search(r"\s*\((.*)\)\s*$", text)
        if em:
            evidence, text = em.group(1).strip(), text[:em.start()].strip()
    return {"tick": tick, "text": text, "evidence": evidence}

def parse_seed(text):
    """Parse the seed outline into a project dict with nested children. Raises CruxError
    on malformed structure. Pure (no I/O) so the whole seed is validated before any write."""
    project, stack = None, []   # stack: list of (indent, node)
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        parsed = _seed_val(raw)
        if not parsed:
            raise CruxError(f"seed: cannot parse line: {raw.strip()!r} "
                            "(expected `- Project:/Q:/H:/v:/finding: …`)")
        indent, key, val = parsed
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1] if stack else None
        if key == "project":
            if parent is not None or project is not None:
                raise CruxError("seed: exactly one top-level `- Project:` is required")
            title, _, goal = val.partition(" — ")
            if not goal:
                title, _, goal = val.partition(" -- ")
            node = {"type": "project", "title": title.strip(),
                    "goal": goal.strip(), "children": []}
            project = node
        elif key == "q":
            if parent is None or parent["type"] not in ("project", "question"):
                raise CruxError(f"seed: a Q must sit under Project or another Q (got {val!r})")
            node = {"type": "question", "title": val, "children": []}
            parent["children"].append(node)
        elif key == "h":
            if parent is None or parent["type"] != "question":
                raise CruxError(f"seed: an H must sit under a Q (got {val!r})")
            tested = False
            m = re.match(r"\[tested\]\s*(.*)$", val, re.I)
            if m:
                tested, val = True, m.group(1).strip()
            node = {"type": "hypothesis", "title": val, "tested": tested,
                    "problem": "", "finding": "", "verifiables": []}
            parent["children"].append(node)
        elif key == "v":
            if parent is None or parent["type"] != "hypothesis":
                raise CruxError(f"seed: a verifiable (v) must sit under an H (got {val!r})")
            parent["verifiables"].append(_parse_verifiable(val))
            node = None
        elif key in ("finding", "problem"):
            if parent is None or parent["type"] != "hypothesis":
                raise CruxError(f"seed: `{key}` must sit under an H (got {val!r})")
            parent[key] = val
            node = None
        else:
            raise CruxError(f"seed: unknown node type '{key}:' (use Project/Q/H/v/finding/problem)")
        if node is not None:
            stack.append((indent, node))
    if project is None:
        raise CruxError("seed: no `- Project:` line found")
    return project

def _render_verifiables(body, verifiables):
    """Replace the template's `## Verifiables` list with the seed's ticks + evidence."""
    lines = []
    for vf in verifiables:
        ev = f"   ({vf['evidence']})" if vf["evidence"] else ""
        lines.append(f"- [{vf['tick']}] {vf['text']}{ev}")
    block = "\n".join(lines)
    return re.sub(r"(## Verifiables\n\n)(?:<!--.*?-->\n)?(?:- \[.\].*\n?)+",
                  lambda m: m.group(1) + block + "\n", body, count=1)

def _materialize(root, project):
    cmd_init(project["title"], root, goal=project["goal"] or "")
    def walk_question(node, parent_id):
        for child in node["children"]:
            if child["type"] == "question":
                qid, _ = cmd_ask(root, child["title"], parent=parent_id)
                walk_question(child, qid)
            else:
                _add_hypothesis(root, child, parent_id)
    def _add_hypothesis(root, h, qid):
        if h["tested"] and not h["verifiables"]:
            raise CruxError(f"seed: [tested] hypothesis {h['title']!r} needs at least one verifiable")
        hid, _ = cmd_hypothesize(root, h["title"], parent=qid, problem=h["problem"],
                                 verifiables=[vf["text"] for vf in h["verifiables"]])
        if not h["tested"]:
            return
        n = Vault(root).get(hid)
        n["body"] = _render_verifiables(n["body"], h["verifiables"])
        write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
        cmd_close(root, hid, findings=h["finding"] or None)
    for child in project["children"]:
        if child["type"] != "question":
            raise CruxError("seed: the Project's direct children must be questions (Q)")
        qid, _ = cmd_ask(root, child["title"], parent=None)
        walk_question(child, qid)

def cmd_init_from(seed_path, dirpath="."):
    """Atomically materialize a whole vault from an approved seed outline."""
    root = os.path.abspath(dirpath)
    if os.path.exists(os.path.join(root, VAULT_MARKER)):
        raise CruxError("a crux vault already exists here")
    project = parse_seed(read(seed_path))          # fully validate before any write
    build = tempfile.mkdtemp(prefix="crux_build_")
    try:
        _materialize(build, project)
    except BaseException:
        shutil.rmtree(build, ignore_errors=True)
        raise
    os.makedirs(root, exist_ok=True)
    for fn in os.listdir(build):
        shutil.move(os.path.join(build, fn), os.path.join(root, fn))
    shutil.rmtree(build, ignore_errors=True)
    slug = slugify(project["title"])
    return root, f"{slug}.md"

def _save_cfg(v):
    write_if_changed(os.path.join(v.root, VAULT_MARKER), yaml_dump(v.cfg) + "\n")

def _new_id(v, kind):
    key = {"question": "counter_q", "idea": "counter_h", "synthesis": "counter_s"}[kind]
    v.cfg[key] += 1
    prefix = {"question": "q", "idea": "h", "synthesis": "s"}[kind]
    _save_cfg(v)
    return f"{prefix}{v.cfg[key]}"

def cmd_ask(root, title, parent=None, body_text=""):
    v = Vault(root)
    parent = parent or v.cfg["root_id"]
    p = v.get(parent)
    if p.type not in ("project", "question"):
        raise CruxError("a question's parent must be the project or another question")
    nid = _new_id(v, "question")
    fn = f"{nid}_{slugify(title)}.md"
    text = fill(load_template("question"), id=nid, title=title,
                parent_id=parent, parent_basename=p.basename)
    if body_text:
        text = text.replace(f"## Question\n\n{title}", f"## Question\n\n{body_text}")
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn

def cmd_hypothesize(root, title, parent, problem="", verifiables=None):
    v = Vault(root)
    p = v.get(parent)
    if p.type != "question":
        raise CruxError("a hypothesis must hang under a question (use `ask` first)")
    nid = _new_id(v, "idea")
    fn = f"{nid}_{slugify(title)}.md"
    text = fill(load_template("idea"), id=nid, title=title, parent_id=parent,
                parent_basename=p.basename, problem=problem or "_(why this is worth testing)_",
                verifiable=(verifiables[0] if verifiables else "_(state a falsifiable, pre-registered check)_"))
    if verifiables and len(verifiables) > 1:
        extra = "\n".join(f"- [ ] {x}" for x in verifiables[1:])
        text = text.replace(f"- [ ] {verifiables[0]}", f"- [ ] {verifiables[0]}\n{extra}")
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn

def _bump(node):
    node["fm"]["updated"] = now()

def cmd_test(root, nid, to=None, run=None):
    v = Vault(root)
    n = v.get(nid)
    if n.type != "idea":
        raise CruxError("test applies to ideas/hypotheses only")
    order = IDEA_STATUS
    target = to or order[min(order.index(n.status) + 1, len(order) - 1)]
    if target not in ("staged", "running"):
        raise CruxError("test moves an idea to 'staged' or 'running'")
    if target == "running" and sum(count_verifiables(n["body"])) == 0:
        raise CruxError(f"refusing to run {nid}: register at least one verifiable first")
    n["fm"]["status"] = target
    if run:
        n["body"] = re.sub(r"## Run Links\n\n_\(none yet\)_",
                           f"## Run Links\n\n- {run}",
                           n["body"]) if "_(none yet)_" in n["body"] else \
                    re.sub(r"(## Run Links\n\n)", rf"\1- {run}\n", n["body"])
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    refresh(root)
    return target

def cmd_close(root, nid, metric=None, findings=None):
    v = Vault(root)
    n = v.get(nid)
    if n.type != "idea":
        raise CruxError("close applies to ideas/hypotheses (use `answer` to close a question)")
    met, unmet, na = count_verifiables(n["body"])
    if met + unmet + na == 0:
        raise CruxError("cannot close: no verifiables to evaluate")
    verdict = derive_verdict(met, unmet, na)
    n["fm"]["status"] = "done"
    n["fm"]["verdict"] = verdict
    if metric is not None:
        n["fm"]["metric"] = metric
    if findings:
        n["body"] = re.sub(r"## Findings\n\n_\(written by the PI/agent when the case is closed\)_",
                           f"## Findings\n\n{findings}", n["body"])
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    # new evidence -> parent question interpretation goes stale
    parent = v.nodes.get(n.parent)
    if parent and parent.type == "question":
        parent["fm"]["stale"] = True
        write_if_changed(parent["path"], render_doc(parent["fm"], parent["body"]))
    refresh(root)
    return verdict

def cmd_review(root):
    v = Vault(root)
    return [(n.id, n.title) for n in v.nodes.values()
            if n.type == "question" and n.status == "review"]

def cmd_answer(root, qid, text=None):
    v = Vault(root)
    n = v.get(qid)
    if n.type != "question":
        raise CruxError("answer applies to questions")
    n["fm"]["status"] = "resolved"
    n["fm"]["stale"] = False
    if text:
        n["body"] = re.sub(r"## Answer so far\n\n.*?\n\n(?=<!-- crux:ledger:start)",
                           f"## Answer so far\n\n{text}\n\n", n["body"], flags=re.S)
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    # resolving a sub-question is new evidence for its parent question
    parent = v.nodes.get(n.parent)
    if parent and parent.type == "question":
        parent["fm"]["stale"] = True
        write_if_changed(parent["path"], render_doc(parent["fm"], parent["body"]))
    refresh(root)
    return qid

def cmd_pursue(root, qid, idea_title=None):
    v = Vault(root)
    n = v.get(qid)
    if n.type != "question":
        raise CruxError("pursue applies to questions")
    n["fm"]["status"] = "open"
    _bump(n)
    write_if_changed(n["path"], render_doc(n["fm"], n["body"]))
    new = None
    if idea_title:
        new = cmd_hypothesize(root, idea_title, qid)  # adds a non-terminal child, then refreshes → Q stays open
    else:
        refresh(root)
    return new

def cmd_synthesize(root, title, questions):
    v = Vault(root)
    for q in questions:
        v.get(q)  # validate existence
    nid = _new_id(v, "synthesis")
    fn = f"{nid}_{slugify(title)}.md"
    related = ", ".join(f"[[{v.get(q).basename}]]" for q in questions)
    text = fill(load_template("synthesis"), id=nid, title=title, related=related)
    write_if_changed(os.path.join(root, fn), text)
    refresh(root)
    return nid, fn

def cmd_validate(root):
    return validate(Vault(root)) + validate_wiki(root)

# ----------------------------------------------------------------------------- text status view
def status_text(root, node=None):
    v = Vault(root)
    if node:
        n = v.get(node)
        out = [f"{n.id} [{n.type}] {n.title}  —  status: {n.status}"]
        if n.type == "idea" and n["fm"].get("verdict"):
            out.append(f"  verdict: {n['fm']['verdict']}   metric: {n['fm'].get('metric') or '—'}")
        if n.type == "question":
            out.append("  ledger:")
            out.append("    " + ledger_block(v, n.id).replace("\n", "\n    "))
        return "\n".join(out)
    lines = []
    def walk(nid, depth):
        n = v.nodes[nid]
        tag = {"project": "▣", "question": "?", "idea": "•"}.get(n.type, "·")
        extra = ""
        if n.type == "idea" and n["fm"].get("verdict"):
            extra = f"  ({n['fm']['verdict']})"
        lines.append("  " * depth + f"{tag} {n.id} [{n.status}] {n.title}{extra}")
        for c in v.children.get(nid, []):
            walk(c, depth + 1)
    walk(v.cfg["root_id"], 0)
    return "\n".join(lines)

# ----------------------------------------------------------------------------- snapshot (read-only JSON contract for the GUI)
# `snapshot` is the single machine-readable view of a vault: the GUI (crux serve)
# consumes it as /snapshot.json and never re-parses markdown. Pure read — it builds a
# Vault and reads bodies, but writes nothing. Stdlib only; returns plain JSON types.
def _section(body, heading):
    """Return the text under a `## <heading>` up to the next `## ` (stripped, '' if absent)."""
    out, grab = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            grab = line[3:].strip().lower() == heading.lower()
            continue
        if grab:
            out.append(line)
    return "\n".join(out).strip()

def _verifiables(body):
    """The `## Verifiables` list as read-only tri-state: [{text, state}] with state in met/unmet/na."""
    items, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "verifiables"
            continue
        if not in_sec:
            continue
        m = re.match(r"\s*- \[(.)\]\s*(.*)$", line)
        if not m:
            continue
        c = m.group(1).lower()
        state = "met" if c == "x" else "na" if c == "-" else "unmet"
        items.append({"text": m.group(2).strip(), "state": state})
    return items

def _run_links(body):
    """Non-placeholder bullets under `## Run Links`."""
    links, in_sec = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            in_sec = line[3:].strip().lower() == "run links"
            continue
        if in_sec and re.match(r"\s*- (?!_\(none)", line):
            links.append(line.strip()[2:].strip())
    return links

def _related_ids(v, body):
    """Question ids a synthesis links to, read in order from its `Related::` wikilinks."""
    by_basename = {n.basename: n.id for n in v.nodes.values()}
    ids = []
    for line in body.splitlines():
        if line.strip().startswith("Related::"):
            for m in re.finditer(r"\[\[([^\]|]+)", line):
                nid = by_basename.get(m.group(1).strip())
                if nid:
                    ids.append(nid)
    return ids

def _ledger_summary(c):
    """A compact one-line ledger summary for a review-queue row."""
    parts = [f"{c['children']} children", f"{c['ideas_done']}/{c['ideas_total']} ideas done"]
    verd = [f"{c[k]} {k}" for k in VERDICTS if c[k]]
    if verd:
        parts.append(", ".join(verd))
    if c["subq_total"]:
        parts.append(f"{c['subq_resolved']}/{c['subq_total']} sub-questions resolved")
    return " · ".join(parts)

def _node_json(v, n):
    d = {"id": n.id, "type": n.type, "title": n.title, "status": n.status}
    if n.type == "question":
        pre = n["body"].split(LEDGER_START)[0]
        d["parent"] = n.parent
        d["stale"] = bool(n["fm"].get("stale"))
        d["detail"] = _section(pre, "Question")
        d["answer"] = _section(pre, "Answer so far")
        d["ledger"] = ledger_counts(v, n.id)
        d["children"] = list(v.children[n.id])
    elif n.type == "idea":
        verdict = n["fm"].get("verdict")
        d["parent"] = n.parent
        d["verdict"] = verdict if verdict in VERDICTS else None   # only ever a valid enum or None
        d["metric"] = n["fm"].get("metric") or None
        d["problem"] = _section(n["body"], "Problem Statement")
        d["hypothesis"] = _section(n["body"], "Idea / Hypothesis")
        d["verifiables"] = _verifiables(n["body"])
        d["run_links"] = _run_links(n["body"])
        d["findings"] = _section(n["body"], "Findings")
    elif n.type == "synthesis":
        d["related"] = _related_ids(v, n["body"])
    return d

def _subtree(v, nid):
    return {"id": nid, "children": [_subtree(v, c) for c in v.children[nid]]}

def snapshot(vault):
    """Read-only JSON snapshot of a vault. `vault` is a Vault or a root path.
    Keys: engine_version, project, nodes (flat map by id), tree (parent-link hierarchy
    from the root; synthesis nodes are excluded — they attach via `related`), queue,
    wiki (index of the literature layer — page bodies stay behind /wiki/<slug>.json)."""
    v = vault if isinstance(vault, Vault) else Vault(vault)
    root_id = v.cfg["root_id"]
    root = v.get(root_id)
    return {
        "engine_version": ENGINE_VERSION,
        "project": {"id": root_id, "title": v.cfg.get("title"), "slug": v.cfg.get("slug"),
                    "status": root.status, "goal": _section(root["body"], "Goal")},
        "nodes": {nid: _node_json(v, n) for nid, n in v.nodes.items()},
        "tree": _subtree(v, root_id),
        "queue": [{"id": n.id, "title": n.title, "summary": _ledger_summary(ledger_counts(v, n.id))}
                  for n in v.nodes.values() if n.type == "question" and n.status == "review"],
        "wiki": _wiki_snapshot(v.root),
    }
