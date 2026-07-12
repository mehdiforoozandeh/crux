# Recapturing the cockpit screenshots

The `.webp` files in this folder are real screenshots of the `crux serve` cockpit,
embedded in the top-level [`README.md`](../../README.md). Regenerate them whenever the
GUI changes. They are shot at **2× DPI** and displayed at `width="900"`, as
light/dark pairs via `<picture>` so each matches the reader's GitHub theme.

| file | tab | state |
|------|-----|-------|
| `cockpit-tree-{light,dark}` | Tree | `q3`/`q4`/`q5` collapsed, `h1` selected → evidence ledger |
| `wiki-graph-{light,dark}`   | Wiki | knowledge graph + `_index` page |

The tree shots collapse the deeper branches (and hide the color-key legend + help
hint) so the remaining boxes render **large and legible** at README width.

## Recipe

Demo material: the [`segssl_vault`](../../skills/crux/examples/segssl_vault) example
(a full, resolved research program — makes the richest tree and wiki graph).

```bash
# 1. serve the vault (pin the port so recapture.js can find it)
cd skills/crux/examples/segssl_vault
../../scaffold/crux.py serve --no-open --port 8896     # leave running

# 2. drive the installed Chrome to shoot each state at 2x → /tmp/crux-shots/*.png
npm i puppeteer-core                                    # uses your Chrome, no download
CRUX_URL=http://localhost:8896 node assets/screens/recapture.js

# 3. downscale to 1800px wide and encode WebP q90 → assets/screens/*.webp
python3 - <<'PY'
from PIL import Image; import os, glob
SRC, DST = "/tmp/crux-shots", "assets/screens"
for p in glob.glob(f"{SRC}/*.png"):
    im = Image.open(p).convert("RGB"); w, h = im.size
    im = im.resize((1800, round(h*1800/w)), Image.LANCZOS)
    im.save(os.path.join(DST, os.path.splitext(os.path.basename(p))[0] + ".webp"),
            "WEBP", quality=90, method=6)
PY
```

Node ids (`h1`, and the collapsed `q3`/`q4`/`q5`) come from the vault's `META.md`;
change them in `recapture.js` if you shoot a different vault. Keep captures
**read-only** and the `View-only` pill in frame — the cockpit never writes.
