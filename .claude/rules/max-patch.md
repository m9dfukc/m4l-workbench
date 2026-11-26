---
paths:
  - "**/*.amxd"
  - "**/*.maxpat"
  - "**/*.maxhelp"
  - "tools/**/build_*.py"
---

# Max patches and M4L devices (.amxd / .maxpat)

The patch is a **thin shell**: I/O, `gen~ @gen …`, `v8 …`, `live.*` parameters, layout. Logic
belongs in GenExpr or TypeScript, not in patch cords.

## Before touching a patch file

- Ask whether the file is open in Max with unsaved changes: Max reloads changed files and
  **discards unsaved editor work without asking**.
- Prefer a generator (py2max / m4l-builder roundtrip) over hand-editing JSON. After the first
  bootstrap the **unfrozen `.amxd` is the source of truth**, not the generator script —
  rerunning a bootstrap script would overwrite the user's layout work.
- Review every change as a `maxdiff` diff (`git diff` uses it via `.gitattributes`).

## Never guess objects, ports or attributes

- Check names, inlet/outlet counts and attribute types against, in this order:
  real Max-saved boxes via `m4l-boxref <class>` (`cd tools && UV_CACHE_DIR=../.uv-cache uv run
  m4l-boxref --keys -n 3 live.dial`: searches Max's help patches, packages, Live's resources
  and the Factory Packs), the device's own saved `.amxd`, the local refpages
  `/Applications/Max.app/Contents/Resources/C74/docs/refpages/**/*.maxref.xml`, then the vendored
  references in `reference/`.
- A box declared with the wrong number of ports **loses its cords when the patch opens**.
- Known hallucinations: there is no `numbox` (→ `flonum`/`number`), no `times~` (→ `*~`), no Pd
  objects (`osc~`, `in~`, `out~`), `poly~` needs a patcher name before the voice count.
- `route a b c` has **four** inlets in Max 9 (args + 1). `trigger` fires right to left. Subpatcher
  inlet/outlet order follows x-position: never move them without checking cords.
- Typed `pack`/`unpack` (`pack f f`): untyped ones truncate floats. Floats with a decimal point
  (`1000.`); JSON drops `.0`, so keep floats as floats on purpose.
- Attribute values have types: `align 1`, not `align center` (silently ignored).
- Codebox source goes into `"code"`, not `"text"` (else the default template loads).

## Max for Live specifics

- Audio I/O: `plugin~`/`plugout~` (2 channels for audio effects), never `adc~`/`dac~`/`ezdac~`.
  Instruments take MIDI via `midiin`/`notein` and output via `plugout~`.
- **Start every shell from Live's own template** (`Max Instrument.amxd` / `Max Audio Effect.amxd`
  under `…/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/`), copied and then
  edited — generated containers can load as the wrong device type.
- Init: `live.thisdevice` instead of `loadbang` (fires when the device is ready in Live); init
  chains with `trigger`, not `delay`/`deferlow` (Production Guidelines).
- Polyphony: `poly~ <voice> N @steal 1` with `gen~` + `thispoly~` inside is Ableton's own
  pattern (Poli). `poly~ @parallel` is disabled in Live; mute idle voices for CPU. MC
  alternatives (`mc.gen~` + `mc.noteallocator~`) work at runtime; editing MC needs standalone Max.
- Parameters only via `live.*` objects: `parameter_enable 1`, a unique, readable
  `parameter_longname` (never defaults like `live.dial[3]`), `parameter_initial_enable 1` with a
  sensible `parameter_initial`, correct type (0 float / 1 int / 2 enum), range, unit style;
  modulation mode per the Ableton M4L Production Guidelines (`reference/m4l-production-guidelines.md`:
  Bipolar for float, Absolute for int; int type is limited to 0–255).
- The **Long Name is the identity** Live uses to recall parameters: never rename it once a
  version is out. Parameters set from inside the patch must be **Hidden** (else they flood
  Live's undo history). Only parameter-mode objects are saved with the Set (`pattr` only with
  Parameter Mode on).
- Device-local names for `send`/`receive`/`buffer~`/`dict`/`coll`/`value` start with `---`
  (replaced per device instance). This works in object boxes only, **not** inside JS strings —
  pass such names to v8 by message.
- New devices: `openinpresentation 1`; controls with `presentation 1` + `presentation_rect`
  inside the 169 px device height. Final layout and the Parameter Inspector check are done by
  the user in the Max editor.
- Set **Defined Latency** in the patcher inspector if the DSP adds latency (FFT, lookahead).
- **Freeze embeds only what the device project lists.** List every runtime file (`.gendsp`, the
  `v8`/`v8ui` scripts and every `jspainterfile`) in `patcher.project.contents.code` as
  `{"kind": "gendsp" | "javascript", "local": 1}`. With an empty project, Freeze missed the
  painters (referenced by attribute only) and the frozen device ran without its scripts and DSP
  [measured: aliasing t7, 2026-11-25]. `devices/aliasing/scripts/check_shell.py` enforces it.

## Tests are real

Do not "test" through message boxes like `int 60` (that calls a function named `int`): send
real numbers through the real path. A patch change is only done after the user loaded it and
reported the Max console (`live-test` skill).
