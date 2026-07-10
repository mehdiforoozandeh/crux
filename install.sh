#!/usr/bin/env bash
#
# install.sh — install the crux skills onto this machine.
#
# Symlinks every skill under ./skills/ into your Claude Code skills dir so the
# agent picks them up: the `crux` tool skill, `evolve-crux`, and any future crux
# skills. Drop a new skill folder under skills/ and it's installed automatically.
#
# Usage:
#   ./install.sh                    # install all crux skills into ~/.claude/skills
#   SKILLS_DIR=/tmp/x ./install.sh  # install into a custom dir (used for testing)
#
# Safe by design: only ever creates/refreshes symlinks it manages; a real
# (non-symlink) folder of the same name is left untouched and reported.

set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILLS_DIR="${SKILLS_DIR:-$HOME/.claude/skills}"

mkdir -p "$SKILLS_DIR"
linked=0; skipped=0

for d in "$REPO_DIR"/skills/*/; do
  d="${d%/}"; name="$(basename "$d")"; dest="$SKILLS_DIR/$name"
  if [[ ! -f "$d/SKILL.md" ]]; then
    echo "  ! skip $name — no SKILL.md" >&2; skipped=$((skipped+1)); continue
  fi
  if [[ -e "$dest" && ! -L "$dest" ]]; then
    echo "  ! skip $name — a real folder exists at $dest (left untouched)" >&2; skipped=$((skipped+1)); continue
  fi
  ln -sfn "$d" "$dest"
  echo "  ✓ $name"; linked=$((linked+1))
done

echo "== crux: $linked linked, $skipped skipped → $SKILLS_DIR =="
echo "Restart / reload your agent to pick up new skills."
