# aliasing — port decisions

Decided with the user in a grilling session on 2026-11-24 (questions Q1–Q21). The basis is
`inventory.md` and `signal-flow.md`. Each decision names its question; "(proposal)" marks details
Claude filled in under a decided branch — open to review, not separately decided.

## 0. Direction

| # | Decision |
|---|---|
| Q1 | **"Inspired by", not an emulation.** Same mechanism (two pointers at different speeds, the read phase written into a table at the write position, the table read back), our own DSP choices otherwise. No float32 or control-rate emulation, no attempt to null against Reaktor. Reaktor renders are listening references, not targets. |
| Q2 | **Drone like the original:** 5 fixed, always-running voices that differ by spread, LFO rate and pan; no MIDI pitch. **activate** is an automatable parameter **and** an incoming MIDI note gates it (note-on → 1, last note-off → 0). Pitch tracking/envelopes are later extensions. |
| Q3 | **No author data in the device:** own presets, own initial table. The original's snapshots and stored table stay local (`tools/local/out/`) and are used at most as private listening points. |
| Q21 | Name **Aliasing** (`Aliasing.amxd`). Credit in README and device info: "inspired by *aliasing Synth* by Dietrich Pank (Reaktor User Library #5241, 2008)". Asking the author before a public release is nice to have, not a blocker. |

## 1. DSP

| # | Path | Decision |
|---|---|---|
| Q4 | Precision | gen~ native 64-bit everywhere, **except the table** (Q15: float32 `Buffer`). No rounding helpers. |
| Q5 | Rate | Everything **per sample**. Pitch parameters smoothed (~10–20 ms) against zipper noise under automation; LFOs are audio-rate sines. No 400 Hz stepping. |
| Q6 | Sample rate | Host SR, no oversampling, **1024 cells** fixed. The sound differs slightly between 44.1 and 48 kHz (cell rate 1024·f vs fs); accepted. |
| Q7 | Voice layer | **One gen~ with an internal loop over the voices** (`NVOICES = 5` constant), per-voice state in `Data`, pan and stereo sum inside gen~. One `.gendsp`, one C++ export for host tests. No `poly~`/`mc.gen~`. |
| Q8 | Core | Deliberately raw: **naive (non-band-limited) pointers**: ramp 0..1 and asymmetric triangle; write index `floor`, **wrap**, reading **without interpolation** by default, statement order **write then read**; the **read phase (0..1) is the written data**; output `2v − 1`. A **Smooth** parameter switches read interpolation to linear. |
| Q15 | Table | gen~ **`Buffer` bound to `buffer~ ---atab`** (5 channels × 1024, float32, unique per device instance) — the DSP table and the display source are the same object. Initial content: identity ramp `T(x) = x` per row (proposal: written once on load by gen~). |
| Q9 | Filter/saturation | Own implementations: **4-pole HP and 4-pole LP** each as two cascaded TPT SVFs (Zavalishin) with **linear FM in Hz** from the **unfiltered** core signal (cutoff clamped to 10 Hz … 0.45·fs); **tanh** saturator; **peak/notch** as TPT bell or RBJ peaking (−30 … +20 dB); **1-pole DC blocker**. Order as the original: Peak → HP4 → Drive → Sat → LP4 → DC → Drive → Sat. |
| — | Safety | Development builds end with `fixnan`/`fixdenorm` + `clip(−1, 1)` (`.claude/rules/gen.md`). |

Per-voice behaviour kept from the original because it shapes the character (proposal, under Q1):

- read spread `sprd · ((V − 0.5)/Vcs − 0.5)` semitones; pan `width · pos(V)` with
  `pos(V) = ((V − 0.5) − Vcs/2)/((Vcs − 1)/2)`;
- LFO frequency per voice `F = rate · (rate + u(V))`, `u = (pos + 1)/2`; LFO depth curve
  `depth^5` semitones (the original's fine-motion curve);
- write position for Shape = Tri uses the unscaled −1..1 triangle (wraps), Shape = =Read uses the
  read pointer; read Tri is rescaled to 0..1;
- read position is 0 while not activated; writing only while activated **and** Write Active is on;
- output level `Output + 20·log10(1/NVOICES)` dB.

Dropped from the original (dead or UI-only): KeyTrack/K folw, the hidden write spread (overwritten
by the LFO in the original), Switch2x2 I/O, the view macro, the OUT reset button, the two IC
"reset" buttons (replaced by **Sync**, Q20).

## 2. Controls (Q10, Q20)

34 automatable parameters. Ranges follow the original and may change during tuning (proposal).

| Section | Parameter | Range / values | Notes |
|---|---|---|---|
| Global | **Activate** | off/on | rising edge (or first MIDI note) restarts both pointer phases |
| Global | **Sync** | button | write Pitch/Fine := read Pitch/Fine, both phases → 0 (the "saw" start state) |
| Global | Transpose | −12 … +12 st | both pointers |
| Global | **Size** | 0.001 … 1 | pointer span multiplier (the original's size bar); also draggable in the display |
| Global | Width | 0 … 2 | pan spread (0 mono, 1 even, 2 extreme) |
| Global | Output | −36 … 0 dB | plus the fixed voice-count compensation |
| Global | Smooth | off / linear | read interpolation (Q8) |
| Write | **Pitch** | −64 … +64 st around note 60 | coarse |
| Write | **Fine** | −1 … +1 st | high-resolution fine control (Live parameter resolution, open check 8) |
| Write | **Shape** | Ramp / Tri / =Read | |
| Write | Symmetry | −1 … +1 | triangle skew (+1 rising saw, 0 triangle, −1 falling saw) |
| Write | Active | off / on | off = read only, table frozen |
| Write | LFO Rate | 0 … 12 | see per-voice formula |
| Write | LFO Depth | 0 … 1 | depth^5 semitones |
| Read | **Pitch** | −64 … +64 st around note 60 | |
| Read | **Fine** | −1 … +1 st | |
| Read | **Shape** | Ramp / Tri | |
| Read | Direction | one-way / both | triangle symmetry 1 vs 0 for the read pointer |
| Read | Spread | 0 … 6 st | per-voice detune |
| Read | LFO Rate, LFO Depth | as write | |
| Tone | Notch Freq | 20 Hz … 10 kHz (log) | displayed in Hz |
| Tone | Notch Q, Gain, On | 0 … 0.98 (→ Q), −30 … +20 dB, off/on | |
| Tone | HP, LP | 20 Hz … 20 kHz (log) | |
| Tone | HP Reso, LP Reso | 0 … 0.98 | |
| Tone | HP FM, LP FM | 0 … 3000 Hz | per unit of core signal |
| Tone | Drive | 0 … 30 dB | both stages |
| Tone | DC, Filter On | off/on | |

Non-automatable, saved with the set: **Display** on/off, display mode (Line/2D), preset menu.

## 3. Display and GUI (Q13, Q16–Q18)

- The **table display is integral to the instrument**, not an add-on: it comes with v0.1.
- `v8ui` (mgraphics) reads `---atab` at up to **30 fps** plus the write/read head positions from
  gen~ (`snapshot~`); **Display on/off** stops redrawing (last frame stays, dimmed) — no UI load
  when off, DSP unaffected.
- Modes: **Line** (5 voice rows overlaid, one colour per voice, write head and read head as
  markers in the two accent colours) and **2D** (heatmap: rows = voices, brightness = value,
  heads as lines). Click toggles. **Size** is integrated into the display (draggable bar).
- Layout at Live's fixed **169 px** device height, target **≈ 800–850 px** wide:
  left always visible (Activate, Sync, write Pitch/Fine/Shape, read Pitch/Fine/Shape), centre the
  display (≈ 300 × 130 px), right a `live.tab`-paged area: **Mod** (LFOs, Symmetry, Direction,
  Spread), **Tone** (Notch + filter), **Out** (Width, Output, Transpose, Smooth).
- Colours follow Live's theme (light/dark), with two fixed accent colours for **Write** and
  **Read**, used everywhere (dial rings, display markers).
- **Next step before building the shell:** a true-to-scale HTML mock-up for review.

## 4. Presets and logic (Q12, Q19)

- Presets: **JSON text files in the repo** (`devices/aliasing/presets/*.json`) are the source; a
  `live.menu` selects; a v8 script (from TS) applies them. Live `.adv` presets are saved from them
  by the user before a release (for the browser/Push).
- Toolchain (first v8 use in the workbench): **esbuild** bundles one flat `.js` per v8 object
  (`aliasing_display.js`, `aliasing_presets.js`), `tsc --noEmit` type-checks; both run in
  `tools/check.sh`. Pure logic (preset validation, colour/scale maths) in Max-free modules with
  Node tests.

## 5. Milestones (Q14)

Each step goes through `live-test` (load, listen with limiter, console/log).

| Version | Content |
|---|---|
| v0.1 core | Activate/MIDI gate, Sync, write/read pointers (all shapes), table as `buffer~`, Size, Smooth, Width/pan, Output + safety stage; **table display** (Line/2D, on/off); first load and listening test in Live |
| v0.2 tone | Notch and SaturatorFilter |
| v0.3 presets | JSON presets + menu, 8–12 own presets |
| v0.4 polish | presentation layout final, CPU check, `.adv` export |

No Python prototype: straight to GenExpr, checked with gencheck and an exported-C++ host test.

## 6. Reaktor material still needed (Q11)

- **Captures:** C4 (Audio Table properties: X units, clip/wrap, interpolation) and C6 (Ramp Osc
  mode) — they define the mechanism the port takes over. C1 optional; C2, C3, C5, C7, C8 dropped
  (kept in `captures.md` as optional).
- **Renders:** R1a, R1d (core sanity) and R7a–e (five snapshots as listening references). R0,
  R2–R6 and the module renders M1–M6 are optional.

## 7. Differences from the original (by design)

Every difference above is intentional under Q1. The main ones, for `deviations.md` once
listening tests start: per-sample control instead of 400 Hz events; 64-bit state (float32
table); own filters and saturator; host sample rate; identity-ramp initial table; Sync button
instead of two resets; MIDI gate added; dead/UI-only parts dropped; new GUI and display.
