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
# 1 off: MIDI gate mode, no note -> silent
$R "$OUT/off.wav" --seconds 2 --set gatemode=1
# 2 drone: the init state (Drone gate) -> audible from the start
$R "$OUT/drone.wav" --seconds 4 --heads "$OUT/drone.heads.f32" --table "$OUT/drone.table.f32"
# 3 gate: MIDI gate mode, note held 0.5 .. 2.5 s
$R "$OUT/gate.wav" --seconds 3.5 --set gatemode=1 --gate 0.5:2.5 --note 0.5
# 4 stress: extremes of every section, all shapes cycled, syncs and notes, two sample rates
STRESS=(--set wpitch=130 --set rpitch=-64 --set wsym=-1 --set rdir=1 --set rspread=6
        --set width=2 --set output=0 --set smoothread=1 --set aaramp=1 --set softclip=0
        --set m1src=1 --set m1tgt=1 --set m1depth=100 --set m2src=2 --set m2tgt=3 --set m2depth=-100
        --set m3src=3 --set m3tgt=6 --set m3depth=100 --set m4src=1 --set m4tgt=10 --set m4depth=100
        --set l1rate=20 --set l1shape=3 --set l2mode=0 --set l2rate=13 --set l2shape=4
        --set drive=24 --set bcenter=3000 --set bwidth=0.2 --set bres=100 --set bfm=100 --set bspread=100
        --set rsmix=100 --set rsfb=95 --set rstrack=0 --set rsfreq=5000
        --at 0.5 wshape=0 --at 1.0 wshape=2 --at 1.5 wshape=3 --at 1.5 rshape=1 --at 2.0 size=0.001
        --at 2.0 bmode=1 --at 2.0 bslope=0 --at 2.5 wpitch=-64 --at 2.5 rpitch=64 --at 2.5 rsfb=-95
        --at 3.0 size=1 --at 3.0 smoothread=0 --at 3.0 aaramp=0 --at 3.0 rsfreq=20
        --sync 0.75 --sync 2.25 --note 1.25 --note 3.5)
$R "$OUT/stress.wav" --seconds 4 "${STRESS[@]}" --table "$OUT/stress.table.f32" --heads "$OUT/stress.heads.f32"
$R "$OUT/stress2.wav" --seconds 4 "${STRESS[@]}"
$R "$OUT/stress44.wav" --sr 44100 --seconds 4 "${STRESS[@]}"
# 5 sync: equal pitches, no spread, ramp, synced -> the table stays within one cell value of identity
$R "$OUT/sync.wav" --seconds 2 --set wpitch=0 --set rpitch=0 --set wfine=0 --set rspread=0 --set wshape=0 \
  --set size=1 --sync 0.5 --table "$OUT/sync.table.f32"
# 6 frozen: Write Active off -> the table stays exactly the identity ramp
$R "$OUT/frozen.wav" --seconds 1 --set wactive=0 --table "$OUT/frozen.table.f32"
# 7 tempo: both pointers synced at 120 BPM: write x64 on 1/16 = 512 Hz, read x1 on 1/4 = 2 Hz
$R "$OUT/tempo.wav" --seconds 2 --transport 120 --set wmode=1 --set wnote=13 --set wmult=64 --set wfine=0 \
  --set rmode=1 --set rnote=7 --set rmult=1 --set rspread=0 --heads "$OUT/tempo.heads.f32"
# 8 band: open vs narrow Pass vs narrow Reject at 1 kHz (spectral energy around the centre)
BAND=(--set rpitch=12 --set rspread=0 --set bcenter=1000 --set bspread=0 --set bres=0)
$R "$OUT/band_open.wav" --seconds 3 "${BAND[@]}"
$R "$OUT/band_pass.wav" --seconds 3 "${BAND[@]}" --set bwidth=1
$R "$OUT/band_reject.wav" --seconds 3 "${BAND[@]}" --set bwidth=1 --set bmode=1
# 9 aa: anti-aliased ramps differ from naive ones and stay finite
$R "$OUT/aa.wav" --seconds 2 --set aaramp=1 --set wshape=0
$R "$OUT/naive.wav" --seconds 2 --set aaramp=0 --set wshape=0

echo "== m4l-analyze"
cd "$ROOT/tools"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
uv run m4l-analyze "$OUT"/{off,drone,gate,stress,stress44,sync,frozen,tempo,band_open,band_pass,band_reject,aa}.wav
uv run m4l-analyze --null "$OUT/stress.wav" "$OUT/stress2.wav"

echo "== checks"
uv run python "$HERE/check_renders.py" "$OUT"
