#!/usr/bin/env bash
# Dial probe in standalone Max (CLAUDE.md exception: a test patch from this repo, no DSP, Max quits
# itself; never Live). Builds build/aliasing/dialprobe/, runs Max, restores the audio prefs if Max
# changed them, then prints the "dialprobe" lines from Max.log (face-review h.4, D42).
#
#   devices/aliasing/test/dial-probe/run_dialprobe.sh
#
# Runs outside the sandbox (app launch). Refuses to run while Max is running.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
OUT="$ROOT/build/aliasing/dialprobe"
MAX_BIN="${MAX_APP:-/Applications/Max.app}/Contents/MacOS/Max"
SETTINGS="$HOME/Library/Application Support/Cycling '74/Max 9/Settings"
LOGS="$HOME/Library/Application Support/Cycling '74/Max 9/Logs"
if pgrep -x Max > /dev/null 2>&1; then echo "run_dialprobe: Max is running - quit it first" >&2; exit 3; fi
mkdir -p "$OUT"
# Max reopens its last session's patches at start: park its workspace notes for this run (user,
# 2026-11-25; tools/max-workspace.sh) and put them back however the script ends.
"$ROOT/tools/max-workspace.sh" park "$OUT/workspace"
trap '"$ROOT/tools/max-workspace.sh" restore "$OUT/workspace"' EXIT
cp "$SETTINGS/audioprefs.txt" "$OUT/audioprefs.before.txt"
python3 -B "$ROOT/devices/aliasing/test/dial-probe/make_dialprobe.py" "$OUT"
echo "run_dialprobe: starting Max"
"$MAX_BIN" "$OUT/dialprobe.maxpat" > "$OUT/max-stdout.log" 2>&1 &
PID=$!
for _ in $(seq 1 90); do kill -0 "$PID" 2> /dev/null || break; sleep 1; done
if kill -0 "$PID" 2> /dev/null; then echo "run_dialprobe: Max did not quit within 90 s (pid $PID) - check for a dialog" >&2; exit 4; fi
if ! cmp -s "$SETTINGS/audioprefs.txt" "$OUT/audioprefs.before.txt"; then
  echo "run_dialprobe: audio prefs changed by the run - restoring"
  cp "$OUT/audioprefs.before.txt" "$SETTINGS/audioprefs.txt"
fi
cp "$LOGS/Max.log" "$OUT/Max.log"
echo "== Max.log: errors"
grep -a " error\]" "$OUT/Max.log" | sed 's/^\[[^]]*\] \[[0-9]*\] //' | sort | uniq -c | head -20 || true
echo "== dialprobe lines"
grep -a "dialprobe" "$OUT/Max.log" | sed 's/^\[[^]]*\] \[[0-9]*\] //' || echo "none"
