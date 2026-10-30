#!/usr/bin/env bash
# Build the frozen work dir: nanoGPT at a pinned commit, the tinyshakespeare data encoded as
# nanoGPT's prepare.py does, and an isolated venv. Nothing is installed globally.
# Idempotent; safe to re-run. On an Alliance cluster (Fir), first run:
#   module load StdEnv/2023 python/3.12.4
# and the venv is built from the cluster's own wheelhouse (pip --no-index).
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
PIN=3adf61e154c3fe3fca428ad6bc3818b27a3b8291      # karpathy/nanoGPT master, 2025-11-12
PY="${PYTHON:-python3}"
DATA_URL=https://raw.githubusercontent.com/karpathy/char-rnn/master/data/tinyshakespeare/input.txt
DATA_SHA=86c4e6aa9db7c042ec79f339dcb96d42b0075e16b8fc2e86bf0ca57e2dc565ed

mkdir -p "$WORK"
if [ ! -d "$WORK/nanoGPT/.git" ]; then
  git clone --quiet https://github.com/karpathy/nanoGPT.git "$WORK/nanoGPT"
fi
git -C "$WORK/nanoGPT" fetch --quiet origin
git -C "$WORK/nanoGPT" checkout --quiet --detach "$PIN"
test "$(git -C "$WORK/nanoGPT" rev-parse HEAD)" = "$PIN"

# The data: the file nanoGPT's prepare.py downloads, pinned by sha256.
mkdir -p "$WORK/frozen/data"
IN="$WORK/frozen/data/input.txt"
if [ ! -f "$IN" ]; then
  curl -sSfL -o "$IN.part" "$DATA_URL" && mv "$IN.part" "$IN"
fi
got="$(shasum -a 256 "$IN" 2>/dev/null || sha256sum "$IN")"; got="${got%% *}"
if [ "$got" != "$DATA_SHA" ]; then
  echo "input.txt sha256 mismatch: got $got, want $DATA_SHA" >&2; exit 1
fi

# The frozen model the scorer trains. Only model.py is used; the loop is in score.py.
git -C "$WORK/nanoGPT" show "$PIN:model.py" > "$WORK/frozen/model.py"

# The candidate for the baseline: the whole pinned checkout. Its
# config/train_shakespeare_char.py is the upstream baseline config, unchanged.
rm -rf "$WORK/cand-baseline"; mkdir -p "$WORK/cand-baseline"
git -C "$WORK/nanoGPT" archive "$PIN" | tar -x -C "$WORK/cand-baseline"

if [ ! -x "$WORK/venv/bin/python" ]; then
  "$PY" -m venv "$WORK/venv"
fi
PIP=("$WORK/venv/bin/python" -m pip install --quiet)
if [ -d /cvmfs/soft.computecanada.ca ]; then
  PIP+=(--no-index)                     # Alliance: the cluster's own wheelhouse only
else
  "$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
  PIP+=(--only-binary=:all:)
fi
"${PIP[@]}" -r "$HERE/requirements.lock"
{ "$WORK/venv/bin/python" --version; "$WORK/venv/bin/python" -m pip freeze; } > "$WORK/versions.txt"

# train.bin / val.bin: nanoGPT's data/shakespeare_char/prepare.py, minus its download
# (which needs `requests`): sorted characters -> ids, first 90% train, last 10% val, uint16.
"$WORK/venv/bin/python" - "$WORK/frozen/data" <<'PYEOF'
import os, sys, numpy as np
d = sys.argv[1]
data = open(os.path.join(d, "input.txt")).read()
stoi = {ch: i for i, ch in enumerate(sorted(set(data)))}
n = len(data)
for name, part in (("train", data[:int(n * 0.9)]), ("val", data[int(n * 0.9):])):
    np.array([stoi[c] for c in part], dtype=np.uint16).tofile(os.path.join(d, name + ".bin"))
PYEOF
echo "ready: $WORK  (versions in work/versions.txt)"
