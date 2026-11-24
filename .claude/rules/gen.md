---
paths:
  - "devices/**/*.genexpr"
  - "devices/**/*.gendsp"
  - "devices/**/gen/**"
---

# GenExpr / gen~ work

DSP lives in `devices/<name>/gen/*.genexpr` (`gen/lib/*.genexpr` = `require` libraries). The
`.gendsp` next to the `.amxd` is **generated** from each top-level file by `tools/check.sh`
(`gencheck --write-gendsp`) — never edit a `.gendsp` by hand, and regenerate it in the same
change as its `.genexpr`. An open `gen~ @gen <file>` picks up the rewritten file — measured on
Max 9.2.0 only [sourced: max-gen-helper]; on 9.1.5 it is [open]. Fallback: send `reload` to the
gen~ (hidden button in the test patch).

**Two Max versions:** stock Live runs 9.1.5, development uses 9.2.0. GenExpr must pass gencheck
for **both** (`check.sh` does that). So: no nested `require` (9.2+ only), no assignments to
constants like `phi` (9.2 refuses them). 9.2 changed dead-code elimination and constant
folding — "code that compiles on both versions may still sound different" — so A/B on 9.1.5
before a release. Always pass `--max-version` to gencheck: without it, it judges by whichever
Max started last (Live's 9.1.5 writes to the same log folder).

The `max-gen-helper` plugin's `gen-pitfalls` skill (measured rules, probe IDs) is the detailed
reference; use it when a gen~ goes silent or errors.

## Syntax and order (gencheck catches most of these)

- File order: `require` → function definitions → declarations (`Param`, `History`, `Data`,
  `Buffer`, `Delay`) → statements. "declarations must come before any expressions".
- Keywords capitalised (`Param`, `History`, `Data`, `Buffer`, `Delay`). Semicolons required.
- No `++` (use `+= 1`), no `a[i]` (use `peek`/`poke` on `Data`/`Buffer`), no `};` after a
  function body. Delay read: `dl.read(n)`, not `dl(n)`.
- Functions do **not** see `Param`/`History`/`Data`/`in1` by name: pass them as arguments.
- Never name your own function like a built-in (`scale`, `mix`, `wrap`, `clip`, `fold`, …):
  it is silently ignored and the built-in runs.
- Nested `require` needs Max 9.2+; Max 9.2 rejects assignments to `phi` and other constants.
- Floats with a decimal point in constants that must stay floats (`1.`, `0.5`).

## Semantics that matter for ports

- gen~ runs **per sample in 64-bit double**. Reaktor computes mostly in 32-bit float; where a
  port's sound depends on errors (aliasing, table collisions, truncation), emulate the
  original's precision and interpolation explicitly and say so in a comment — never assume
  "more precise is better" for these devices.
- Storage width: `Data` and `History` are 64-bit; a `Buffer` bound to a `buffer~` stores
  32-bit floats [sourced]. Choose deliberately when a port must reproduce float32 errors.
- `peek`/`sample`/`wave`/`lookup` differ in defaults (`peek`: no interpolation, 0 out of range;
  `sample`: linear; `wave`: wraps) [sourced: local refpages]. State the modes explicitly
  (`interp=`, `boundmode=`, `index=`) and round/floor indices explicitly (`floor()` for
  Reaktor-style table writes). What `poke` does with a fractional index is [open].
- Same-sample write and read of one table: the **statement order** in GenExpr is the order
  (a visual gen patcher cannot set it) [sourced: forum, G. Wakefield] — comment it.
- `History` gives exactly one sample of delay; feedback paths without it do not compile.
- Parameters change at message rate; smooth them (`slide`, `mix` toward target) where the
  original smooths, and do **not** smooth where the original jumps (zipper/aliasing may be part
  of the sound — check the original before "fixing" it).
- Sample rate comes from Live and can change: derive everything from `samplerate`, re-init
  sample-rate-dependent state on change.
- Polyphony is not gen~'s job: one gen~ = one voice; voices come from `poly~` or `mc` in the
  shell (decision per device, documented in its `docs/`).

## Safety stage

Development builds end every output with `fixnan` → `fixdenorm` → `clip(-1, 1)` (or a soft
clipper) so a blown-up filter cannot send NaN/inf or full-scale noise to Live. Remove or keep
it deliberately for a release, and document the decision in the device docs.

## Checks

1. `tools/check.sh <device>` (gencheck 9.1.5 + 9.2.0 on every `.genexpr`, regenerates `.gendsp`).
2. Offline test where one exists: the gen~ C++ export (`exportcode`, `@exportfolder build/…`)
   compiled into a host harness and driven by stimulus WAVs (pitch/gate as signals), checked
   with `m4l-analyze` (no NaN/inf, peak/DC, determinism, spectra). Exported C++ stays in
   `build/` (gitignored) until the export licence is checked. For host tests, design voices
   as one gen patcher with state in `Data` and controls as signal inputs where possible.
3. **"gencheck green" does not mean "compiles in Max"**: many gen~ errors only show once
   audio is running. Ask the user for the Max console output (`live-test` skill).
