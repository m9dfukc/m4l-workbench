# reference/

Shared ground truth for building devices.

| File | What |
|---|---|
| `m4l-production-guidelines.md` | Ableton's M4L Production Guidelines (vendored, see `tools/vendor/VENDOR.md`) |
| `patch-code-standard.md` | Ableton's patch code standard (vendored) |
| `m4l.md` | Compact `live.*` / M4L port reference (vendored from ssdvtechno) |

## Box JSON ground truth: `m4l-boxref`

Real, Max-saved examples of any object box come from the patches Max and Ableton ship on this
machine (Max help patches and packages, Live's resources, the installed Factory Packs — about
7 300 patch files, including boxes saved by Max 9.2.0). Nothing is copied into the repo:

```bash
cd tools && UV_CACHE_DIR=../.uv-cache uv run m4l-boxref live.dial            # newest example
cd tools && UV_CACHE_DIR=../.uv-cache uv run m4l-boxref --keys -n 3 live.menu # key statistics + 3 examples
```

Copy the structure of a real box (keys, `saved_attribute_attributes.valueof`, `parameter_*`
fields) instead of inventing it. This replaces the hand-built `reference-live-objects.amxd` that
the original guide suggested (decided 2026-11-24). The first device the user saves in Max 9.2
is the second ground truth: how *this* Max writes *our* boxes.
