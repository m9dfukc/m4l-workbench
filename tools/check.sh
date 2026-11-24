#!/usr/bin/env bash
# Offline check chain for one device. Never opens Max or Live, never plays audio.
#
#   1. gencheck every devices/<name>/gen/*.genexpr for Max 9.1.5 (bundled in Live) and
#      9.2.0 (standalone), --strict, with gen/lib/ as the require() path
#   2. regenerate devices/<name>/<stem>.gendsp from each top-level gen/*.genexpr
#      (files under gen/lib/ are require() libraries and get no .gendsp)
#   3. TypeScript layer, if the device has one (js/src/ + a "build:<name>" script)
#   4. every .amxd/.maxpat of the device must parse with maxdiff; prints a short summary
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: tools/check.sh [--no-write] DEVICE

DEVICE      folder name under devices/ (e.g. aliasing)
--no-write  check only, do not regenerate .gendsp files
Max versions checked: $GENCHECK_VERSIONS (default "9.1.5 9.2.0").
Exit status is non-zero if any step fails.
EOF
}

WRITE=1
DEVICE=""
while [ $# -gt 0 ]; do
  case "$1" in
    --no-write) WRITE=0; shift ;;
    -h|--help) usage; exit 0 ;;
    -*) echo "check.sh: unknown option $1" >&2; usage >&2; exit 2 ;;
    *) [ -z "$DEVICE" ] || { echo "check.sh: one DEVICE only" >&2; exit 2; }; DEVICE="$1"; shift ;;
  esac
done
[ -n "$DEVICE" ] || { usage >&2; exit 2; }

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DIR="$ROOT/devices/$DEVICE"
[ -d "$DIR" ] || { echo "check.sh: no device folder $DIR" >&2; exit 2; }
GENCHECK="$ROOT/tools/vendor/gencheck/gencheck.py"
MAXDIFF="$ROOT/tools/vendor/maxdevtools/maxdiff"
VERSIONS="${GENCHECK_VERSIONS:-9.1.5 9.2.0}"
FAIL=0

step() { printf '\n== %s\n' "$*"; }

# --- 1 + 2: GenExpr -----------------------------------------------------------
step "GenExpr ($VERSIONS)"
shopt -s nullglob
GEN_FILES=("$DIR"/gen/*.genexpr "$DIR"/gen/lib/*.genexpr)
GEN_PATH_ARGS=()
[ -d "$DIR/gen/lib" ] && GEN_PATH_ARGS=(--gen-path "$DIR/gen/lib")
if [ ${#GEN_FILES[@]} -eq 0 ]; then
  echo "no .genexpr files"
else
  for f in "${GEN_FILES[@]}"; do
    for v in $VERSIONS; do
      if ! python3 "$GENCHECK" --max-version "$v" --strict ${GEN_PATH_ARGS[@]+"${GEN_PATH_ARGS[@]}"} "$f"; then
        FAIL=1
      fi
    done
  done
  if [ "$WRITE" -eq 1 ] && [ "$FAIL" -eq 0 ]; then
    step "regenerate .gendsp"
    for f in "$DIR"/gen/*.genexpr; do
      stem="$(basename "$f" .genexpr)"
      out="$DIR/$stem.gendsp"
      tmp="$(mktemp "${TMPDIR:-/tmp}/gendsp.XXXXXX").gendsp"
      # gencheck keeps an existing .gendsp it did not write: write to a fresh path, then move.
      if python3 "$GENCHECK" --max-version 9.2.0 ${GEN_PATH_ARGS[@]+"${GEN_PATH_ARGS[@]}"} --write-gendsp "$tmp" "$f" > /dev/null; then
        if [ -f "$out" ] && cmp -s "$tmp" "$out"; then
          echo "$stem.gendsp unchanged"; rm -f "$tmp"
        else
          mv "$tmp" "$out"; echo "$stem.gendsp written"
        fi
      else
        rm -f "$tmp"; echo "$stem.gendsp NOT written"; FAIL=1
      fi
    done
  elif [ "$WRITE" -eq 1 ]; then
    echo "(.gendsp not regenerated: gencheck failed)"
  fi
fi

# --- 3: TypeScript -------------------------------------------------------------
step "TypeScript"
if [ -d "$DIR/js/src" ]; then
  if [ -f "$ROOT/package.json" ] && grep -q "\"build:$DEVICE\"" "$ROOT/package.json"; then
    (cd "$ROOT" && pnpm run --silent "build:$DEVICE") || FAIL=1
  else
    echo "js/src exists but package.json has no \"build:$DEVICE\" script"; FAIL=1
  fi
else
  echo "no TS layer"
fi

# --- 4: patches ------------------------------------------------------------------
step "patches (maxdiff)"
PATCHES=("$DIR"/*.amxd "$DIR"/*.maxpat "$DIR"/test/*.maxpat)
if [ ${#PATCHES[@]} -eq 0 ]; then
  echo "no .amxd/.maxpat files"
else
  for p in "${PATCHES[@]}"; do
    case "$p" in *.amxd) conv=amxd_textconv.py ;; *) conv=maxpat_textconv.py ;; esac
    if out="$(python3 "$MAXDIFF/$conv" "$p" 2>&1)"; then
      objs="$(printf '%s\n' "$out" | grep -c '^\[' || true)"
      if printf '%s\n' "$out" | grep -qi 'frozen'; then
        echo "$(basename "$p"): FROZEN device — never commit frozen devices"; FAIL=1
      else
        echo "$(basename "$p"): parses, $objs object lines"
      fi
    else
      echo "$(basename "$p"): maxdiff failed"; printf '%s\n' "$out" | tail -5; FAIL=1
    fi
  done
fi

echo
if [ "$FAIL" -eq 0 ]; then echo "check.sh: $DEVICE OK"; else echo "check.sh: $DEVICE FAILED"; fi
exit "$FAIL"
