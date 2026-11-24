#!/usr/bin/env bash
# Export a device's gen~ patcher as C++ with standalone Max, unattended.
#
#   tools/gen-export.sh DEVICE [STEM]
#
# Writes a throwaway test patch build/<device>/export/export.maxpat next to a copy of
# devices/<device>/<stem>.gendsp, starts standalone Max with it, the patch sends `exportcode`
# to its gen~ at load and quits Max after a few seconds (`max clean`, `max quit`). The C++ lands
# in build/<device>/export/cpp/. No audio is started; the audio driver is not touched.
#
# Conditions (CLAUDE.md, "Exception, standalone Max for unattended tests"): only test patches
# from this repo, never Live, and only after the user confirmed that no Max with unsaved work
# is open (Max reuses a running instance). The script refuses to run while Max is running.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: tools/gen-export.sh DEVICE [STEM]

DEVICE  folder name under devices/ (e.g. aliasing)
STEM    gendsp file stem (default: DEVICE)
Env:    MAX_APP (default /Applications/Max.app), EXPORT_TIMEOUT seconds (default 90)
EOF
}

[ $# -ge 1 ] || { usage >&2; exit 2; }
case "$1" in -h|--help) usage; exit 0 ;; esac
DEVICE="$1"
STEM="${2:-$1}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
GENDSP="$ROOT/devices/$DEVICE/$STEM.gendsp"
[ -f "$GENDSP" ] || { echo "gen-export: no $GENDSP (run tools/check.sh $DEVICE first)" >&2; exit 2; }
MAX_APP="${MAX_APP:-/Applications/Max.app}"
MAX_BIN="$MAX_APP/Contents/MacOS/Max"
[ -x "$MAX_BIN" ] || { echo "gen-export: no Max binary at $MAX_BIN" >&2; exit 2; }
TIMEOUT="${EXPORT_TIMEOUT:-90}"

if pgrep -x Max > /dev/null 2>&1; then
  echo "gen-export: Max is running - quit it first (it would reuse the running instance)" >&2
  exit 3
fi

OUT="$ROOT/build/$DEVICE/export"
CPP="$OUT/cpp"
rm -rf "$CPP"
mkdir -p "$CPP"
cp "$GENDSP" "$OUT/$STEM.gendsp"

GENEXPR="$ROOT/devices/$DEVICE/gen/$STEM.genexpr"
python3 - "$OUT/export.maxpat" "$STEM" "$CPP" "$GENEXPR" <<'PY'
import json, os, re, sys
path, stem, cpp, genexpr = sys.argv[1:5]

def box(i, text, x, y, nin, nout, cls="newobj", **extra):
    b = {"id": f"obj-{i}", "maxclass": cls, "numinlets": nin, "numoutlets": nout,
         "outlettype": [""] * nout, "patching_rect": [x, y, 200.0, 22.0], "text": text}
    b.update(extra)
    return {"box": b}

def line(a, ao, b, bi):
    return {"patchline": {"source": [f"obj-{a}", ao], "destination": [f"obj-{b}", bi]}}

boxes = [
    box(1, "loadbang", 30.0, 30.0, 1, 1, outlettype=["bang"]),
    box(2, "t b b", 30.0, 70.0, 1, 2, outlettype=["bang", "bang"]),
    box(3, "exportcode", 200.0, 110.0, 2, 1, cls="message"),
    box(4, f"gen~ @gen {stem} @exportfolder {cpp} @exportname {stem}", 200.0, 150.0, 2, 2,
        outlettype=["signal", "signal"]),
    box(5, "delay 5000", 30.0, 110.0, 2, 1, outlettype=["bang"]),
    box(6, "; max clean; max quit", 30.0, 190.0, 2, 1, cls="message"),
]
# A GenExpr `Buffer x("ref")` whose buffer~ does not exist at export time was exported without
# its State member (the C++ referenced an undeclared `x`; measured 2026-11-24, Max 9.2.1).
# So create one buffer~ per declared reference (8 channels is enough for any channel index).
if os.path.isfile(genexpr):
    src = open(genexpr).read()
    refs = re.findall(r'^\s*Buffer\s+\w+\s*\(\s*"([^"]+)"', src, re.M)
    refs += [n for n in re.findall(r'^\s*Buffer\s+(\w+)\s*;', src, re.M)]
    for k, ref in enumerate(refs):
        boxes.append(box(10 + k, f"buffer~ {ref} 100 8", 420.0, 30.0 + 30.0 * k, 1, 2,
                         outlettype=["float", "bang"]))
# gen~ inlet/outlet counts follow the gendsp; 2 in / 2 out for the cords used here is enough,
# only the message inlet 0 is wired.
lines = [line(1, 0, 2, 0), line(2, 1, 3, 0), line(3, 0, 4, 0), line(2, 0, 5, 0), line(5, 0, 6, 0)]
pat = {"patcher": {"fileversion": 1,
                   "appversion": {"major": 9, "minor": 2, "revision": 0, "architecture": "x64", "modernui": 1},
                   "classnamespace": "box", "rect": [100.0, 100.0, 640.0, 300.0],
                   "boxes": boxes, "lines": lines}}
json.dump(pat, open(path, "w"), indent=1)
PY

echo "gen-export: starting Max with $OUT/export.maxpat"
"$MAX_BIN" "$OUT/export.maxpat" > "$OUT/max-stdout.log" 2>&1 &
PID=$!
for _ in $(seq 1 "$TIMEOUT"); do
  kill -0 "$PID" 2> /dev/null || break
  sleep 1
done
if kill -0 "$PID" 2> /dev/null; then
  echo "gen-export: Max did not quit within ${TIMEOUT}s - left running (pid $PID); check for a dialog" >&2
  exit 4
fi
if ls "$CPP"/*.cpp > /dev/null 2>&1; then
  echo "gen-export: exported to $CPP"; ls -R "$CPP" | head -40
else
  echo "gen-export: no C++ in $CPP" >&2; tail -20 "$OUT/max-stdout.log" >&2; exit 5
fi
