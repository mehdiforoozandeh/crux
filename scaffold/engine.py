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
import os, re, sys, datetime, tempfile, shutil

# ----------------------------------------------------------------------------- constants
ENGINE_VERSION = "1.0"          # bumped when verdict/roll-up/view logic changes; stamped into every vault
VAULT_MARKER = ".crux.yaml"
LEDGER_START = "<!-- crux:ledger:start -->"
LEDGER_END   = "<!-- crux:ledger:end -->"

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
            if not fn.endswith(".md") or fn in ("META.md", "EXPERIMENTS.md"):
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
def ledger_block(v, qid):
    kids = v.children[qid]
    if not kids:
        return "_(no children yet)_"
    ideas = [v.nodes[k] for k in kids if v.nodes[k].type == "idea"]
    subqs = [v.nodes[k] for k in kids if v.nodes[k].type == "question"]
    n_done = sum(1 for n in ideas if n.status == "done")
    vc = {x: sum(1 for n in ideas if n["fm"].get("verdict") == x) for x in VERDICTS}
    q_res = sum(1 for n in subqs if n.status == "resolved")
    summary = (f"**{len(kids)} children** · ideas {n_done}/{len(ideas)} done "
               f"(supported {vc['supported']}, partial {vc['partial']}, "
               f"refuted {vc['refuted']}, inconclusive {vc['inconclusive']})")
    if subqs:
        summary += f" · sub-questions {q_res}/{len(subqs)} resolved"
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

# ----------------------------------------------------------------------------- commands (called by CLI + selftest)
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
    return validate(Vault(root))

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
