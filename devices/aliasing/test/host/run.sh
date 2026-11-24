#!/usr/bin/env bash
# Host test of the aliasing gen~ export: compile render.cpp against build/aliasing/export/cpp,
# render the scenarios below to build/aliasing/host/*.wav, then check them with m4l-analyze and
# check_renders.py. Never plays audio.
#
#   devices/aliasing/test/host/run.sh
#
# Needs a current export: tools/gen-export.sh aliasing (standalone Max, see CLAUDE.md).
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HERE="$ROOT/devices/aliasing/test/host"
EXP="$ROOT/build/aliasing/export/cpp"
OUT="$ROOT/build/aliasing/host"
[ -f "$EXP/aliasing.cpp" ] || { echo "run.sh: no export in $EXP (tools/gen-export.sh aliasing)" >&2; exit 2; }
if [ "$ROOT/devices/aliasing/aliasing.gendsp" -nt "$EXP/aliasing.cpp" ]; then
  echo "run.sh: WARNING: aliasing.gendsp is newer than the export - re-run tools/gen-export.sh aliasing" >&2
fi
mkdir -p "$OUT"

echo "== build"
clang -O2 -w -c "$EXP/gen_dsp/json.c" -o "$OUT/json.o"
clang -O2 -w -c "$EXP/gen_dsp/json_builder.c" -o "$OUT/json_builder.o"
clang++ -std=c++17 -O2 -w -I"$EXP" -I"$EXP/gen_dsp" "$HERE/render.cpp" "$EXP/gen_dsp/genlib.cpp" \
  "$OUT/json.o" "$OUT/json_builder.o" -o "$OUT/render"
R="$OUT/render"

echo "== render"
# 1 off: defaults, never activated -> silent
$R "$OUT/off.wav" --seconds 2
# 2 on: Activate on with the defaults
$R "$OUT/on.wav" --seconds 4 --set activate=1 --heads "$OUT/on.heads.f32"
# 3 gate: MIDI gate 0.5 .. 2.5 s only
$R "$OUT/gate.wav" --seconds 3.5 --gate 0.5:2.5
# 4 stress: extremes, all shapes cycled, syncs, two sample rates
STRESS=(--set activate=1 --set wpitch=64 --set rpitch=-64 --set wsym=-1 --set rdir=1
        --set rspread=6 --set wlforate=12 --set wlfodepth=1 --set rlforate=12 --set rlfodepth=1
        --set width=2 --set output=0 --set smoothread=1
        --at 0.5 wshape=1 --at 1.0 wshape=2 --at 1.5 rshape=1 --at 2.0 size=0.001
        --at 2.5 wpitch=-64 --at 2.5 rpitch=64 --at 3.0 size=1 --at 3.0 smoothread=0
        --sync 0.75 --sync 2.25 --sync 3.5)
$R "$OUT/stress.wav" --seconds 4 "${STRESS[@]}" --table "$OUT/stress.table.f32" --heads "$OUT/stress.heads.f32"
$R "$OUT/stress2.wav" --seconds 4 "${STRESS[@]}"
$R "$OUT/stress44.wav" --sr 44100 --seconds 4 "${STRESS[@]}"
# 5 sync: equal pitches, no spread, synced -> the table stays within one cell value of identity
$R "$OUT/sync.wav" --seconds 2 --set activate=1 --set wfine=0 --set rspread=0 --sync 0.5 \
  --table "$OUT/sync.table.f32"
# 6 frozen: Write Active off -> the table stays exactly the identity ramp
$R "$OUT/frozen.wav" --seconds 1 --set activate=1 --set wactive=0 --set wpitch=7 \
  --table "$OUT/frozen.table.f32"

echo "== m4l-analyze"
cd "$ROOT/tools"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
uv run m4l-analyze "$OUT"/{off,on,gate,stress,stress44,sync,frozen}.wav
uv run m4l-analyze --null "$OUT/stress.wav" "$OUT/stress2.wav"

echo "== checks"
uv run python "$HERE/check_renders.py" "$OUT"
