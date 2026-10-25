#!/usr/bin/env bash
# Build the frozen work dir: memesuite-lite at the pinned pre-PR-#21 commit, plus an
# isolated venv. Nothing is installed globally. Idempotent; safe to re-run.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
WORK="$HERE/work"
PIN=dd413f654eb9fb9b095fe61edd69b37c53962367     # first parent of PR #21's merge 45549db
POST=45549db5b9bbce69bf6039a6fc0e3f35601138ee    # PR #21 merged (the known answer)
PY="${PYTHON:-python3.11}"

mkdir -p "$WORK"
if [ ! -d "$WORK/memesuite-lite/.git" ]; then
  git clone --quiet https://github.com/jmschrei/memesuite-lite.git "$WORK/memesuite-lite"
fi
git -C "$WORK/memesuite-lite" fetch --quiet origin
git -C "$WORK/memesuite-lite" checkout --quiet --detach "$PIN"
test "$(git -C "$WORK/memesuite-lite" rev-parse HEAD)" = "$PIN"

# The frozen copy the scorer reads tests and the non-tomtom package files from.
rm -rf "$WORK/frozen"
mkdir -p "$WORK/frozen"
git -C "$WORK/memesuite-lite" archive "$PIN" memelite tests | tar -x -C "$WORK/frozen"

# Two candidate checkouts for validation: the pinned baseline and the PR #21 answer.
for name in baseline:$PIN pr21:$POST; do
  dir="$WORK/cand-${name%%:*}"; sha="${name#*:}"
  rm -rf "$dir"; mkdir -p "$dir"
  git -C "$WORK/memesuite-lite" archive "$sha" memelite | tar -x -C "$dir"
done

if [ ! -x "$WORK/venv/bin/python" ]; then
  "$PY" -m venv "$WORK/venv"
fi
"$WORK/venv/bin/python" -m pip install --quiet --upgrade pip
"$WORK/venv/bin/python" -m pip install --quiet --only-binary=:all: -r "$HERE/requirements.lock"
{ "$WORK/venv/bin/python" --version; "$WORK/venv/bin/python" -m pip freeze; } > "$WORK/versions.txt"
echo "ready: $WORK  (versions in work/versions.txt)"
