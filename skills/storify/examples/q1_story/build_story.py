"""Rebuild story.tex from story_src.tex: every number becomes a LaTeX macro.

Worked example: scaling_vault, the question "Does more data beat a better model?".
Inputs (vault-relative):
  results/h1/metrics.json   first and second task, each arm at its own cost; design constants
  results/h2/metrics.json   replication at own cost; first task at equal training compute
  results/h3/metrics.json   harder task, at own cost and at equal training compute

The storify build pattern. Every number in the paper is read here from a result file,
never typed into the prose. The build writes each number as a \\newcommand macro and each
chart table as a \\pgfplotstableread table into the `% __DATA__` slot, and it records the
sha256 of every file it read in the `% crux-sources:` manifest line, so that
`crux story --verify story.tex` can prove the paper is current. Formatting (sign,
decimals, thousands separator) is done here, never in the prose. The build does not
compile: run `latexmk -pdf story.tex` after it.

    python3 build_story.py [VAULT]   # default: the shipped scaling_vault

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
    # this shipped example lives outside any vault: default to the shipped scaling_vault
    return (HERE / ".." / ".." / ".." / "crux" / "examples" / "scaling_vault").resolve()


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

# ==== REDUCE ==========================================================================
h1, h2, h3 = (load(f"results/{h}/metrics.json") for h in ("h1", "h2", "h3"))


def millions(v):
    """'1.20M' -> '1.2~million'."""
    m = re.fullmatch(r"([0-9.]+)M", str(v))
    return num(m.group(1), 1) + "~million"


des = h1["design"]
macros.update(nSeeds=num(des["seeds"]["value"], 0),
              nHeldout=num(des["heldout_n"]["value"], 0),
              nTrainBase=millions(des["train_n_baseline"]["value"]),
              nTrainData=millions(des["train_n_data_arm"]["value"]))

# each comparison: the difference (data arm minus model arm) with its 95% CI, and the
# two arms' accuracies where the result file holds them
rows = {"FirstOwn": h1["task_a"], "SecondOwn": h1["task_b"], "RepOwn": h2["equal_data"],
        "HardOwn": h3["equal_data"], "FirstEqc": h2["equal_compute"],
        "HardEqc": h3["equal_compute"]}
for key, leaf in rows.items():
    d = leaf["delta"]
    macros["d" + key] = num(d["value"], sign=True)
    macros["lo" + key], macros["hi" + key] = num(d["ci"][0]), num(d["ci"][1])
    if "data_arm" in leaf:
        macros["accData" + key] = num(leaf["data_arm"]["value"])
        macros["accModel" + key] = num(leaf["model_arm"]["value"])

# the swing on the first task when compute is matched (own cost minus equal compute)
macros["swingFirst"] = num(h1["task_a"]["delta"]["value"] - h2["equal_compute"]["delta"]["value"])
# how many of the six differences are statistically significant (CI excludes zero)
sig = sum(1 for leaf in rows.values() if leaf["delta"]["ci"][0] > 0 or leaf["delta"]["ci"][1] < 0)
macros["nSig"] = num(sig, 0)
macros["nCompared"] = num(len(rows), 0)


def diff_row(y, leaf):
    d = leaf["delta"]
    return [y, raw(d["value"]), raw(d["ci"][1] - d["value"]), raw(d["value"] - d["ci"][0])]


# panel (a): differences with 95% CI; y positions top to bottom
tables["tblOwn"] = (["y", "d", "ep", "em"],
                    [diff_row(7, rows["FirstOwn"]), diff_row(6, rows["RepOwn"]),
                     diff_row(5, rows["SecondOwn"]), diff_row(4, rows["HardOwn"])])
tables["tblEqc"] = (["y", "d", "ep", "em"],
                    [diff_row(2, rows["FirstEqc"]), diff_row(1, rows["HardEqc"])])
# panel (b): the two arms' accuracies where both are on file
tables["tblAcc"] = (["x", "data", "model"],
                    [[i, raw(rows[k]["data_arm"]["value"]), raw(rows[k]["model_arm"]["value"])]
                     for i, k in enumerate(("FirstOwn", "FirstEqc", "HardOwn"))])
# ======================================================================================

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
