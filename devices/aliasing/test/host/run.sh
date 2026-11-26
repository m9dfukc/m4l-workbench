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
# 2 drone: the init state (Drone gate, write = read = 0 st, D1) -> audible from the start
$R "$OUT/drone.wav" --seconds 4 --heads "$OUT/drone.heads.f32" --table "$OUT/drone.table.f32"
# 2b alias: the v0.2 init sound (R21: write 71 + 0.217 st = fs/3 + 4 Hz, read -30 st)
$R "$OUT/alias.wav" --seconds 2 --set wpitch=71 --set wfine=0.217 --set rpitch=-30 \
  --heads "$OUT/alias.heads.f32" --table "$OUT/alias.table.f32"
# 3 gate: MIDI gate mode, note held 0.5 .. 2.5 s
$R "$OUT/gate.wav" --seconds 3.5 --set gatemode=1 --gate 0.5:2.5 --note 0.5
# 4 stress: extremes of every section, all 5 write shapes (D34) and 3 write states, the matrix with every
#   source incl. Voice / Neighbour / Read Osc / Env feedback (D36), limiter extremes, section switches,
#   the write pointer synced at Sync Rate x16 (D37)
STRESS=(--set wpitch=130 --set rpitch=-64 --set wsym=-1 --set rspread=6
        --set width=2 --set output=0 --set smoothread=1 --set aaramp=1 --set velocity=1 --set modwheel=1
        --set mx_l1_wp=100 --set mx_l2_sz=-100 --set mx_l2_bc=100 --set mx_l1_ou=100 --set mx_vo_wp=100
        --set mx_nb_rp=-100 --set mx_ro_sz=100 --set mx_en_bc=100 --set mx_vo_wa=-100 --set mx_ro_rf=100
        --set mx_ve_sp=100 --set mx_mw_bc=-100 --set mx_nb_sy=100 --set mx_en_rf=-100 --set mx_l2_sp=100
        --set syncrate=8 --at 1.0 wmode=1 --at 3.4 wmode=0
        --set l1rate=20 --set l1shape=3 --set l2mode=0 --set l2rate=13 --set l2shape=4
        --set drive=24 --set bcenter=3000 --set bwidth=0.2 --set bres=100 --set bfm=100 --set bspread=100
        --set reson=1 --set rsmix=100 --set rsfb=95 --set rstrack=0 --set rsfreq=5000
        --set limgain=24 --set limsat=100 --set limcolor=100 --set limrel=1 --set limceil=0
        --at 0.4 wshape=0 --at 0.8 wshape=3 --at 1.2 wshape=4 --at 1.6 wshape=2 --at 2.0 wshape=1
        --at 2.4 wshape=4 --at 2.8 wshape=2 --at 1.5 rshape=1 --at 2.0 size=0.001 --at 2.0 limcolor=-100
        --at 2.0 bmode=1 --at 2.0 bslope=0 --at 2.5 wpitch=-64 --at 2.5 rpitch=64 --at 2.5 rsfb=-95
        --at 2.5 drvon=0 --at 2.5 bandon=0 --at 3.0 size=1 --at 3.0 smoothread=0 --at 3.0 aaramp=0
        --at 3.0 rsfreq=20 --at 3.0 wsym=1 --at 3.2 wactive=2 --at 3.6 wactive=0 --at 3.6 limon=0
        --sync 0.75 --sync 2.25 --note 1.25 --note 3.5)
$R "$OUT/stress.wav" --seconds 4 "${STRESS[@]}" --table "$OUT/stress.table.f32" --heads "$OUT/stress.heads.f32"
$R "$OUT/stress2.wav" --seconds 4 "${STRESS[@]}"
$R "$OUT/stress44.wav" --sr 44100 --seconds 4 "${STRESS[@]}"
# 5 sync: equal pitches, no spread, ramp, synced -> the table stays within one cell value of identity
$R "$OUT/sync.wav" --seconds 2 --set wpitch=0 --set rpitch=0 --set wfine=0 --set rspread=0 --set wshape=0 \
  --set size=1 --sync 0.5 --table "$OUT/sync.table.f32"
# 6 frozen: write state Freeze -> the table stays exactly the identity ramp
$R "$OUT/frozen.wav" --seconds 1 --set wactive=0 --table "$OUT/frozen.table.f32"
# 6b clean: 1 s of aliasing (v0.2 init sound), then Clean for 1.5 s over the whole row -> identity again
$R "$OUT/clean.wav" --seconds 2.5 --set wpitch=71 --set wfine=0.217 --set rpitch=-30 --set size=1 \
  --at 1.0 wactive=2 --table "$OUT/clean.table.f32"
# 6c write gate (D15): Freeze + Velocity -> Write at +100 %: velocity 1 opens writing, 0.4 does not
$R "$OUT/wgate_open.wav" --seconds 1 --set wactive=0 --set mx_ve_wa=100 --set velocity=1 --table "$OUT/wgate_open.table.f32"
$R "$OUT/wgate_shut.wav" --seconds 1 --set wactive=0 --set mx_ve_wa=100 --set velocity=0.4 --table "$OUT/wgate_shut.table.f32"
# 7 tempo: both pointers synced at 120 BPM: write x64 / 4 on 1/16 = 128 Hz, read x1 on 1/4 = 2 Hz (D3)
$R "$OUT/tempo.wav" --seconds 2 --transport 120 --set wmode=1 --set wnote=13 --set wmult=64 --set wden=4 \
  --set wfine=0 --set rmode=1 --set rnote=7 --set rmult=1 --set rspread=0 --heads "$OUT/tempo.heads.f32"
# 7b Sync Rate (D37): the same at x2 -> 256 Hz / 4 Hz; Transpose +12 st must not move synced pointers
$R "$OUT/tempo_rate.wav" --seconds 2 --transport 120 --set wmode=1 --set wnote=13 --set wmult=64 --set wden=4 \
  --set wfine=0 --set rmode=1 --set rnote=7 --set rmult=1 --set rspread=0 --set syncrate=5 --set transpose=12 \
  --heads "$OUT/tempo_rate.heads.f32"
# 7c Sync Rate /16 on the write pointer, Transpose +12 st on a Hz read pointer: 8 Hz, read note 72
$R "$OUT/tempo_slow.wav" --seconds 2 --transport 120 --set wmode=1 --set wnote=13 --set wmult=64 --set wden=4 \
  --set wfine=0 --set rspread=0 --set syncrate=0 --set transpose=12 --heads "$OUT/tempo_slow.heads.f32"
# 7d Resync with Hz pointers (frozen table, 120 BPM = 2 s bars): Resync 1 restarts them every bar, so
#    consecutive bars are the same signal; with Resync Off they ignore the transport and the bars differ
$R "$OUT/resync_hz.wav" --seconds 6 --transport 120 --set wactive=0 --set resync=1
$R "$OUT/resync_off.wav" --seconds 6 --transport 120 --set wactive=0
# 8 band: open vs narrow Pass vs narrow Reject at 1 kHz (spectral energy around the centre)
BAND=(--set rpitch=12 --set rspread=0 --set bcenter=1000 --set bspread=0 --set bres=0)
$R "$OUT/band_open.wav" --seconds 3 "${BAND[@]}"
$R "$OUT/band_pass.wav" --seconds 3 "${BAND[@]}" --set bwidth=1
$R "$OUT/band_reject.wav" --seconds 3 "${BAND[@]}" --set bwidth=1 --set bmode=1
# 9 aa: anti-aliased ramps differ from naive ones and stay finite
$R "$OUT/aa.wav" --seconds 2 --set aaramp=1 --set wshape=0
$R "$OUT/naive.wav" --seconds 2 --set aaramp=0 --set wshape=0
# 10 exact bypasses (D17, D19): limiter not limiting with Saturation 0, Color alone, Drive section off
ALIAS=(--set wpitch=71 --set wfine=0.217 --set rpitch=-30)
$R "$OUT/lim_off.wav" --seconds 2 "${ALIAS[@]}" --set limon=0
$R "$OUT/lim_idle.wav" --seconds 2 "${ALIAS[@]}" --set limon=1 --set limceil=0
$R "$OUT/lim_color.wav" --seconds 2 "${ALIAS[@]}" --set limon=1 --set limceil=0 --set limcolor=100
$R "$OUT/drv_zero.wav" --seconds 2 "${ALIAS[@]}" --set drive=0
$R "$OUT/drv_off.wav" --seconds 2 "${ALIAS[@]}" --set drive=24 --set drvon=0
# 11 limiter ceiling: +24 dB into a -6 dB ceiling with full saturation
$R "$OUT/lim_ceil.wav" --seconds 2 "${ALIAS[@]}" --set output=0 --set limgain=24 --set limsat=100 --set limceil=-6
# 12 envelope follower (D16): Env -> Output at -100 % pulls the level down against the same patch without it
$R "$OUT/env_ref.wav" --seconds 2 "${ALIAS[@]}"
$R "$OUT/env_duck.wav" --seconds 2 "${ALIAS[@]}" --set mx_en_ou=-100 --set engain=24
# 13 resonator section switch: off (default) vs on at Mix 100 % differ
$R "$OUT/res_on.wav" --seconds 2 "${ALIAS[@]}" --set reson=1 --set rsmix=100

echo "== m4l-analyze"
cd "$ROOT/tools"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
uv run m4l-analyze "$OUT"/{off,drone,alias,gate,stress,stress44,sync,frozen,clean,tempo,tempo_rate,band_open,band_pass,band_reject,aa,lim_ceil,env_duck,res_on}.wav
uv run m4l-analyze --null "$OUT/stress.wav" "$OUT/stress2.wav"

echo "== checks"
uv run python "$HERE/check_renders.py" "$OUT"
