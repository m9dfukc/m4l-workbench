#!/usr/bin/env bash
# Keep standalone Max's restored workspace out of the unattended test runs (user, 2026-11-25).
#
# Max reopens every patch of its last session at start (Crash Recovery/maxworkspace-*.txt), so an
# unattended run of a test patch would also open the user's own patches (dial probe 2026-11-25: it
# opened a user's device next to the probe). Before a run, `park` moves the workspace files into
# DIR; after the run, `restore` moves the files Max wrote during the run into DIR/after-run/, puts
# the parked ones back and then runs `clean` on them.
#
# `clean` drops every entry that names a test patch under this repo's build/ from Max's workspace
# files. Those patches quit Max on their own (`; max quit`): left in the workspace, they reopened at
# every Max start and closed it again, also when the user opened a device's editor from Live (t7,
# 2026-11-25; smoke/export patches from runs before this helper existed had stayed in the user's
# workspace and were parked and restored with it).
#
#   tools/max-workspace.sh park DIR
#   tools/max-workspace.sh restore DIR
#   tools/max-workspace.sh clean            remove build/ test patches from the workspace files
#   tools/max-workspace.sh check            exit 3 if a workspace file names a file outside this repo
#
# Sourced by the run scripts (gen-export.sh, run_smoke.sh, run_dialprobe.sh); never touches the user's
# patches themselves, only Max's own workspace notes.
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CR_DEFAULT="$HOME/Library/Application Support/Cycling '74/Max 9/Crash Recovery"
CR="${MAX_CRASH_RECOVERY:-$CR_DEFAULT}"

cmd="${1:-}"
case "$cmd" in
  park)
    dir="${2:?park needs DIR}"
    mkdir -p "$dir/parked"
    n=0
    for f in "$CR"/maxworkspace-*.txt; do
      [ -e "$f" ] || continue
      mv "$f" "$dir/parked/"
      n=$((n + 1))
    done
    echo "max-workspace: parked $n workspace file(s) in $dir/parked"
    ;;
  restore)
    dir="${2:?restore needs DIR}"
    mkdir -p "$dir/after-run"
    for f in "$CR"/maxworkspace-*.txt; do
      [ -e "$f" ] || continue
      mv "$f" "$dir/after-run/"
    done
    n=0
    for f in "$dir"/parked/maxworkspace-*.txt; do
      [ -e "$f" ] || continue
      mv "$f" "$CR/"
      n=$((n + 1))
    done
    echo "max-workspace: restored $n workspace file(s); the run's own in $dir/after-run"
    "$0" clean
    ;;
  clean)
    for f in "$CR"/maxworkspace-*.txt; do
      [ -e "$f" ] || continue
      python3 - "$f" "Macintosh:$ROOT/build/" <<'PY'
import json, sys
path, prefix = sys.argv[1], sys.argv[2]
with open(path) as fh:
    data = json.load(fh)
gone = [k for k, v in data.items() if isinstance(v, dict) and str(v.get("filepath", "")).startswith(prefix)]
for k in gone:
    print(f"max-workspace: clean: {data[k]['filepath']}")
    del data[k]
if gone:
    with open(path, "w") as fh:
        json.dump(data, fh, indent=4)
PY
    done
    ;;
  check)
    bad=0
    for f in "$CR"/maxworkspace-*.txt; do
      [ -e "$f" ] || continue
      while IFS= read -r p; do
        case "$p" in
          "Macintosh:$ROOT/"*) ;;
          *) echo "max-workspace: $f opens $p"; bad=1 ;;
        esac
      done < <(sed -n 's/.*"filepath" *: *"\([^"]*\)".*/\1/p' "$f")
    done
    exit $((bad * 3))
    ;;
  *)
    echo "usage: tools/max-workspace.sh park DIR | restore DIR | clean | check" >&2
    exit 2
    ;;
esac
