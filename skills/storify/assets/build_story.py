"""Rebuild story.tex from story_src.tex: every number becomes a LaTeX macro.

The storify build pattern. Every number in the paper is read here from a result file,
never typed into the prose. The build writes each number as a \\newcommand macro and each
chart table as a \\pgfplotstableread table into the `% __DATA__` slot, and it records the
sha256 of every file it read in the `% crux-sources:` manifest line, so that
`crux story --verify story.tex` can prove the paper is current. Formatting (sign,
decimals, thousands separator) is done here, never in the prose. The build does not
compile: run `latexmk -pdf story.tex` after it.

    python3 build_story.py [VAULT]   # default: the folder above this one that holds META.md

Stdlib only. UTF-8 and "\\n" everywhere, so the build is byte-stable.
"""
import hashlib, json, pathlib, re, sys

HERE = pathlib.Path(__file__).resolve().parent
SRC, OUT = HERE / "story_src.tex", HERE / "story.tex"


def find_vault():
    if len(sys.argv) > 1:
        return pathlib.Path(sys.argv[1]).resolve()
    for d in (HERE, *HERE.parents):
        if (d / "META.md").is_file():
            return d
    sys.exit("build_story: no vault found; pass its path as the first argument")


VAULT = find_vault()
read = []                                   # every file the build reads, in order


def load(rel):
    """Read a vault-relative file and record it in the manifest. JSON is parsed."""
    p = VAULT / rel
    read.append(p)
    text = p.read_bytes().decode("utf-8")
    return json.loads(text) if p.suffix == ".json" else text


def num(v, d=1, sign=False):
    """A number as LaTeX text: fixed decimals, a real minus sign, an optional plus sign,
    and a thin-space thousands separator. Use the result as a macro body."""
    v = round(float(v), d)
    s = f"{abs(v):,.{d}f}".replace(",", "{,}")
    if v < 0:
        return "\\ensuremath{-}" + s
    return ("\\ensuremath{+}" if sign and v > 0 else "") + s


def raw(v, d=1):
    """A number as a plain table entry for pgfplots (no LaTeX markup)."""
    return f"{round(float(v), d):.{d}f}"


macros = {}    # macro name (letters only) -> LaTeX text
tables = {}    # table name (letters only) -> (column names, rows)

# ==== REDUCE: fill this block ==========================================================
# Read every result file through load(), then put each number the prose or a caption
# needs into `macros`, and each chart's data into `tables`. Example:
#
#   m = load("results/h1/metrics.json")
#   d = m["task_a"]["delta"]
#   macros["diffA"] = num(d["value"], sign=True)        # used in prose as \diffA
#   macros["diffAlo"], macros["diffAhi"] = num(d["ci"][0]), num(d["ci"][1])
#   tables["tblDiffs"] = (["y", "label", "d", "ep", "em"],
#                         [[0, "{First task}", raw(d["value"]),
#                           raw(d["ci"][1] - d["value"]), raw(d["value"] - d["ci"][0])]])
# =======================================================================================

for name in (*macros, *tables):
    assert re.fullmatch(r"[A-Za-z]+", name), f"macro/table name {name!r}: letters only"


def in_vault(p):
    """p's vault-relative POSIX path, or None when p lies outside the vault."""
    try:
        return p.relative_to(VAULT).as_posix()
    except ValueError:
        return None


lines = [f"\\newcommand{{\\{k}}}{{{v}}}" for k, v in sorted(macros.items())]
for k, (cols, rows) in sorted(tables.items()):
    body = "\n".join(" ".join(str(c) for c in r) for r in rows)
    lines.append(f"\\pgfplotstableread{{\n{' '.join(cols)}\n{body}\n}}\\{k}")
data = "\n".join(lines) or "% (no numbers)"

# the manifest: every file read, plus this script and the source when they live in the
# vault (they do in <vault>/stories/<anchor-id>/; a shipped example lives outside it)
read += [p for p in (pathlib.Path(__file__).resolve(), SRC) if in_vault(p)]
sources = {in_vault(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in read}
assert all(sources), "every file the build reads must lie inside the vault"

src = SRC.read_bytes().decode("utf-8")
assert src.count("% crux-sources: __SOURCES__") == 1 and src.count("% __DATA__") == 1
out = src.replace("% crux-sources: __SOURCES__",
                  "% crux-sources: " + json.dumps(sources, sort_keys=True))
out = out.replace("% __DATA__", data)
OUT.write_bytes(out.encode("utf-8"))
print(f"wrote {OUT}: {len(macros)} macro(s), {len(tables)} table(s), "
      f"{len(sources)} source file(s)")
