#!/usr/bin/env bash
# Configure the maxdiff textconv drivers for this clone (git config is not versioned).
# Safe to run more than once. Needs python3 >= 3.10 on PATH.
set -euo pipefail

case "${1:-}" in
  -h|--help)
    echo "Usage: tools/setup-git.sh"
    echo "Sets diff.maxpat / diff.amxd / diff.als textconv in this repo's .git/config"
    echo "to the vendored maxdiff (tools/vendor/maxdevtools/maxdiff)."
    exit 0 ;;
esac

ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
MAXDIFF="tools/vendor/maxdevtools/maxdiff"
[ -f "$MAXDIFF/amxd_textconv.py" ] || { echo "setup-git.sh: $MAXDIFF missing" >&2; exit 1; }

# Paths are absolute so textconv also works from subdirectories.
git config diff.maxpat.textconv "python3 \"$ROOT/$MAXDIFF/maxpat_textconv.py\""
git config diff.amxd.textconv   "python3 \"$ROOT/$MAXDIFF/amxd_textconv.py\""
git config diff.amxd.binary     true
git config diff.als.textconv    "python3 \"$ROOT/$MAXDIFF/als_textconv.py\""
git config diff.als.binary      true

echo "maxdiff textconv configured:"
git config --get-regexp '^diff\.(maxpat|amxd|als)\.'
