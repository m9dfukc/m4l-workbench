---
name: reaktor-port
description: Port a Native Instruments Reaktor ensemble (or one of its macros) to a Max for Live device in this workbench - settings snapshot, inventory from screenshots and Properties pages, signal-flow document, rate and precision decisions per path, reference renders from Reaktor, layer mapping to gen~/poly~/v8, module-by-module port with offline tests, A/B against the original, and a deviation log. Use whenever the work is about rebuilding a Reaktor patch in Max ("portier das Reaktor-Ensemble", "wie macht Reaktor das", "nachbauen wie im Original", "klingt anders als in Reaktor", "A/B gegen Reaktor") - also mid-port when a module, table, filter or voice behaviour has to be matched.
---

# Port a Reaktor ensemble

Background and sources: `docs/research/notes/reaktor-fundamentals-and-porting-2026-11-24.md`
(Reaktor semantics, method, open checks) and `docs/research/notes/max-port-targets-gen-rnbo-2026-11-24.md`
(Max side, mapping table, numerics). Read the relevant sections before deciding anything; do
not re-research what is there.

**Ground rules**

- Porting a graph literally does not work ("exact porting (graphically) is never the way to
  go"). Port the **behaviour**, measured against the original, module by module.
- Built-in Primary modules (oscillators, filters) are closed boxes: match them **by
  measurement**, not by guessing their implementation.
- Where the original's *errors* are the sound (precision, control-rate stepping, table
  collisions, interpolation), a "better" implementation is a wrong one. Every intentional
  deviation is logged.
- **File parsing is allowed** (user, 2026-11-24): a local, read-only parser may dump the record
  stream of `.ens`/`.ism` files (modules, type IDs, names, values, ports) —
  `docs/research/notes/reaktor-file-parsers-2026-11-24.md` has the framing and the plan. Parser
  output is `[observed: parser]` and is cross-checked against screenshots/Properties pages before
  it drives a decision; numeric type IDs are mapped via test instruments with one known module
  each. The format is undocumented and NI has enforced its EULA against a *public* parser (2024):
  the parser code therefore lives **only in `tools/local/`** (gitignored; user, 2026-11-24).
- The user operates Reaktor and Live (screenshots, Properties, renders); Claude plans exactly
  what to capture and documents it. Third-party files stay in `devices/<name>/reference/reaktor/`
  (local only, never edited).

All port documents live in `devices/<name>/docs/` (English, committed, evidence markers):

| File | Content |
|---|---|
| `inventory.md` | settings snapshot, every macro/module with type, mono/poly, Properties; every panel control with range/default/units; snapshot table |
| `signal-flow.md` | block diagram (Mermaid), event→audio crossings, "Z" feedback delays, table read/write pairs with rates, voice-combiner boundary |
| `port-decisions.md` | per path: rate (a/b/c), precision, interpolation, layer (gen~/poly~/v8/patch), with reasons |
| `renders.md` | list of reference renders: MIDI, snapshot, settings, file name, SHA-256, determinism check |
| `deviations.md` | every known difference from the original, marked and with the evidence |

## Steps

### 0. Settings snapshot (user, in Reaktor standalone, Full mode)

Ask for: Reaktor version; the sample-rate display (Host or Fixed — aliasing scales with SR);
*Settings → Control Rate* (default 400 Hz, saved per ensemble); BPM; per instrument Voices,
Unison Min/Max/Spread, Assign mode, Reassign. Record in `inventory.md`.

### 1. Inventory (user captures, Claude records)

Give the user a precise capture list: for every structure level a readable screenshot, the
same with *Debug Structure → Show Module Sorting* and *Show Event Init Order*, and the
Properties pages (Function + Connection) of every module that matters — tables (size, units,
Min/Max, interpolation, clip/wrap, stored contents), oscillators (Ramp mode Standard /
Anti-Aliased / Hi-Res), filters (type, FM inputs), Core cells if any. Panel controls: label,
Min/Max/step/default, value per snapshot. Cross-check against the parser dump of the original
file (and its `strings`: macro names, help texts, snapshot names) so nothing is missed; where
dump and screenshots disagree, the screenshot/Properties page wins and the parser mapping is
fixed. Name screenshot files in the
inventory so each fact can be traced.

### 2. Signal flow

Draw it in `signal-flow.md` from the inventory. Mark every event→audio crossing (implicit
hold), every automatic one-sample feedback delay ("Z"), every table read/write pair with the
rate and pointer source of each side, voice boundaries, mono/poly transitions, units (Reaktor
pitch inputs are in semitones, levels in dB).

### 3. Decisions per path → `port-decisions.md`

- **Rate:** (a) emulate control rate (sample-and-hold every SR/CR samples), (b) per-sample on
  purpose (deviation, logged), (c) update on change. Default (a) for anything feeding table
  pointers or pitches that shape the sound.
- **Precision:** float32 emulation where accumulation or storage errors are audible (phase/
  position accumulators, stored table values, feedback states): `Buffer` bound to `buffer~`
  (32-bit storage) or an explicit rounding helper — both [untested] until compared with renders.
- **Tables:** write index `floor()`, clip values to Min/Max, explicit read interpolation and
  wrap/clip, explicit same-sample write/read order (statement order in GenExpr).
- **Layers:** voice DSP in one GenExpr file per voice in `poly~ <voice> N @steal 1` (the
  pattern of Ableton's Poli); per-voice tables as gen~ `Data`; `live.*` parameters in the
  shell; presets/mapping in v8. Deviate only with a reason in the doc.
- **Voices:** same count, allocation and stealing policy as the original.

Open design questions go to the user with the `grilling` skill.

### 4. Reference renders (user)

Write the render plan into `renders.md`, then hand it over: Reaktor 6 plugin in Live at the
ensemble's SR (48 kHz unless Fixed says otherwise), one MIDI clip per test (single notes at
several pitches, a chord, 10–20 s holds, velocity ramp), one snapshot per take, **reload
ensemble/snapshot before every take** (tables keep history), 32-bit float WAV, no master
processing, every take **twice** to check determinism (null the pair). Module tests: copy one
macro into a test ensemble with Audio In and render impulses, sweeps, noise at several
settings. Renders go to `devices/<name>/reference/renders/` (local only); `renders.md` keeps
names and checksums.

### 5. Module-by-module port

Leaf modules first (pointer/phasor logic, table semantics, oscillators, each filter, saturator),
each with an offline test before it meets Max: a Python reference (`tools/`) or the gen~
`exportcode` C++ driven by a small host harness, compared against the module render (frequency
response within an agreed tolerance, level/DC, exact index arithmetic for tables). Then the
voice, then the instrument. Every step that runs in Max/Live goes through `live-test`.

### 6. A/B

Same MIDI, same snapshot/parameters, level-matched. Compare long-term spectrum, spectrogram
difference, positions of the aliasing products, RMS envelopes, crest factor (scripts in
`tools/`). Chaotic or feedback paths diverge sample-wise: judge statistically and by ear, never
by a sample null alone. Log each comparison via `live-test`.

### 7. Deviations and credit

Every intentional or measured difference goes to `deviations.md` with its evidence marker.
The device README credits the original author and links the original; the terms for
publishing a port are checked before any release (`m4l-release`).
