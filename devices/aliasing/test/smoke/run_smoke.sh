#!/usr/bin/env bash
# Smoke test of one face of the device in standalone Max (CLAUDE.md exception: a test patch from this
# repo, NonRealTime driver, Max quits itself; never Live). Builds build/aliasing/smoke/<face>/, runs Max,
# restores the audio driver preference if Max left it changed, then reports Max.log errors and the
# recording.
#
#   devices/aliasing/test/smoke/run_smoke.sh [hybrid|b]
#
# Runs outside the sandbox (app launch). Refuses to run while Max is running.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
FACE="${1:-hybrid}"
OUT="$ROOT/build/aliasing/smoke/$FACE"
MAX_BIN="${MAX_APP:-/Applications/Max.app}/Contents/MacOS/Max"
SETTINGS="$HOME/Library/Application Support/Cycling '74/Max 9/Settings"
LOGS="$HOME/Library/Application Support/Cycling '74/Max 9/Logs"
if pgrep -x Max > /dev/null 2>&1; then echo "run_smoke: Max is running - quit it first" >&2; exit 3; fi
mkdir -p "$OUT"
# Max reopens its last session's patches at start: park its workspace notes for this run (user,
# 2026-11-25; tools/max-workspace.sh) and put them back however the script ends.
"$ROOT/tools/max-workspace.sh" park "$OUT/workspace"
trap '"$ROOT/tools/max-workspace.sh" restore "$OUT/workspace"' EXIT
cp "$SETTINGS/audioprefs.txt" "$OUT/audioprefs.before.txt"
DRIVER="$(sed -n 's/.*prefdrivername "\([^"]*\)".*/\1/p' "$OUT/audioprefs.before.txt")"
DRIVER="${DRIVER:-Core Audio}"
rm -f "$OUT/smoke.wav" "$OUT/atab_after_drop.wav"
python3 -B "$ROOT/devices/aliasing/test/smoke/make_smoke.py" "$OUT" "$DRIVER" "$FACE"
echo "run_smoke: starting Max (driver to restore: $DRIVER)"
"$MAX_BIN" "$OUT/smoke.maxpat" > "$OUT/max-stdout.log" 2>&1 &
PID=$!
for _ in $(seq 1 120); do kill -0 "$PID" 2> /dev/null || break; sleep 1; done
if kill -0 "$PID" 2> /dev/null; then echo "run_smoke: Max did not quit within 120 s (pid $PID) - check for a dialog" >&2; exit 4; fi
if ! cmp -s "$SETTINGS/audioprefs.txt" "$OUT/audioprefs.before.txt"; then
  echo "run_smoke: audio prefs changed by the run - restoring"; diff "$OUT/audioprefs.before.txt" "$SETTINGS/audioprefs.txt" || true
  cp "$OUT/audioprefs.before.txt" "$SETTINGS/audioprefs.txt"
fi
cp "$LOGS/Max.log" "$OUT/Max.log"
echo "== Max.log: errors and warnings"
grep -a " error\]\| warn\]\|warning" "$OUT/Max.log" | sed 's/^\[[^]]*\] \[[0-9]*\] //' | sort | uniq -c | sort -rn | head -40 || true
echo "== Max.log: device posts"
grep -a "aliasing_\|probe_dial_painter\|ProbeUI" "$OUT/Max.log" | sed 's/^\[[^]]*\] \[[0-9]*\] //' | head -20 || true
echo "== recording"
ls -la "$OUT/smoke.wav" 2> /dev/null || echo "no recording"
echo "== sample drop (D50-D54)"
UV_CACHE_DIR="$ROOT/.uv-cache" uv run --quiet --project "$ROOT/tools" python -B "$ROOT/devices/aliasing/test/smoke/check_drop.py" "$OUT" "$FACE" || echo "run_smoke: sample drop check FAILED"
