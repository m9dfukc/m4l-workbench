#!/usr/bin/env bash
# Write/read shape study of the aliasing gen~ export (devices/aliasing/docs/shapes-study.md).
# Builds the host renderer (devices/aliasing/test/host/render.cpp) into OUT/bin, a second one from a
# patched copy of the export with experimental read shapes (OUT/xread, never the device's DSP), then
# renders and analyses the grid, the read-side checks and the audition files with shapes_study.py.
# Renders and intermediates stay in OUT; never plays audio.
#
#   devices/aliasing/test/shapes/run.sh [OUT] [EXPORT]
#     OUT     default build/aliasing/shapes
#     EXPORT  default build/aliasing/export/cpp (tools/gen-export.sh aliasing)
#   STEPS="grid read audition" to choose steps (default all three)
#
# Measures the v0.3 DSP (8 write shapes, rdir, Drift; aliasing.gendsp of commit 9c23f87). v0.3b (D34-D36)
# renumbered the shapes and removed rdir, so EXPORT must be a gen~ export of that older .gendsp
# (git show 9c23f87:devices/aliasing/aliasing.gendsp); the scenarios here do not run on v0.3b.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../.." && pwd)"
HERE="$ROOT/devices/aliasing/test/shapes"
OUT="${1:-$ROOT/build/aliasing/shapes}"
EXP="${2:-$ROOT/build/aliasing/export/cpp}"
STEPS="${STEPS:-grid read audition}"
[ -f "$EXP/aliasing.cpp" ] || { echo "run.sh: no export in $EXP (tools/gen-export.sh aliasing)" >&2; exit 2; }
if [ "$ROOT/devices/aliasing/aliasing.gendsp" -nt "$EXP/aliasing.cpp" ]; then
  echo "run.sh: WARNING: aliasing.gendsp is newer than the export - results describe the export" >&2
fi
mkdir -p "$OUT/bin" "$OUT/xread"
export UV_CACHE_DIR="${UV_CACHE_DIR:-$ROOT/.uv-cache}"
PY=(uv run --project "$ROOT/tools" python "$HERE/shapes_study.py")

echo "== build"
clang -O2 -w -c "$EXP/gen_dsp/json.c" -o "$OUT/bin/json.o"
clang -O2 -w -c "$EXP/gen_dsp/json_builder.c" -o "$OUT/bin/json_builder.o"
clang++ -std=c++17 -O2 -w -I"$EXP" -I"$EXP/gen_dsp" "$ROOT/devices/aliasing/test/host/render.cpp" \
  "$EXP/gen_dsp/genlib.cpp" "$OUT/bin/json.o" "$OUT/bin/json_builder.o" -o "$OUT/bin/render"
"${PY[@]}" xpatch "$EXP/aliasing.cpp" "$OUT/xread/aliasing.cpp"
clang++ -std=c++17 -O2 -w -I"$OUT/xread" -I"$EXP" -I"$EXP/gen_dsp" "$ROOT/devices/aliasing/test/host/render.cpp" \
  "$EXP/gen_dsp/genlib.cpp" "$OUT/bin/json.o" "$OUT/bin/json_builder.o" -o "$OUT/bin/render_xread"

for s in $STEPS; do
  echo "== $s"
  case "$s" in
    grid) "${PY[@]}" grid "$OUT/bin/render" "$OUT" ;;
    read) "${PY[@]}" read "$OUT/bin/render" "$OUT/bin/render_xread" "$OUT" ;;
    audition) "${PY[@]}" audition "$OUT/bin/render" "$OUT" ${AUDITION_EXTRA:-} ;;
    *) echo "run.sh: unknown step $s" >&2; exit 2 ;;
  esac
done
