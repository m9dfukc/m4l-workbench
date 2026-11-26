# aliasing — redesign decisions after test t1 (2026-11-24)

Answers to the architecture-level items of `feedback-t1.md` (F1, F4, F15, F16, F17, F19),
settled with the user in a grilling round on 2026-11-24. Research behind them:
`docs/research/notes/live-auto-filter-2026-11-24.md` (F17) and
`docs/research/notes/m4l-custom-ui-and-sync-2026-11-24.md` (F19, F4/F15). Evidence markers as in
`CLAUDE.md`; "decided (user)" means the user accepted it in that round. Nothing here is built yet.

## R1 Gate without Activate (F1) — decided (user)

- The **Activate button goes**. A stored, automatable parameter **Gate: Drone | MIDI**, small in
  the Out area, default **Drone**.
  - Drone: the voices always run while the device is on; Live's device on/off is the switch.
  - MIDI: sound while any note is held, with the 5 ms declick envelope (D1 in `v0.1-core.md`).
- Phase restart (port-decisions Q2) on: device load, the Sync button, note-on (MIDI mode only),
  transport start (when a pointer is synced, see R2).

## R2 Pointer clock sync (F4) — decided (user)

- Each pointer (write, read) gets a rate mode **Free | Sync**.
  - Free: Pitch (−64…64 semitones around note 60, i.e. about 6.5 Hz – 10.7 kHz; corrected
    from "0.2–330 Hz" stated in the round, `gen/aliasing.genexpr` `notew = 60 + pw …`) + Fine, as in v0.1.
  - Sync: note value 8 bars … 1/64, straight / dotted / triplet, times a **multiplier ×1…×64**
    so synced rates reach the audio range (1/64 at 120 BPM is only 32 Hz).
    Multiplier range stays **×1…×64** (user, 2026-11-24): synced rates top out around 2 kHz at
    120 BPM (×64 on 1/64); higher pointer rates use Free mode (up to ~10.7 kHz).
- **Fine in Sync mode = detune** of ±1 semitone against the grid, so write and read drift apart
  slowly instead of locking (alternative "phase offset" rejected: it keeps a static pattern).
- **Phase lock:** restart on transport start, plus a **Resync** parameter Off / 1 / 2 / 4 / 8 bars
  that re-locks the detuned pointers. Since 2026-11-26 (user) a Resync setting other than Off
  restarts Hz pointers as well, so a free-running drone can be tied to the bar; with Off, Hz
  pointers ignore the transport (`v0.2-build.md` A4).
- Mechanism [hypothesis, research note Part B]: the transport reaches gen~ as a signal
  (`plugphasor~` or `phasor~ … @lock 1`) through an inlet; tempo is derived from the ramp, with
  `plugsync~` as fallback while the transport is stopped so the drone keeps running. Open checks
  G-SY1, G-SY2 in the research note.

## R3 LFO sync (F15) — decided (user)

- LFOs use the same rate model: **Free (Hz) | Sync** (note value, dotted, triplet).
- **Retrigger** Off / Note / Bar, **Phase** 0–360°, per-voice **Spread** (the original's `u(V)`
  rate spread) stays.
- Shapes: Sine, Triangle, Saw, Square, S&H, Smooth Random.

## R4 Modulation routing (F16) — decided (user)

- **4 mod slots**, each **Source / Target / Depth (bipolar)** = 12 Live parameters, all
  automatable and mappable. No matrix.
- Sources: LFO 1, LFO 2, Drift (slow smooth random per voice), MIDI velocity, mod wheel.
- Targets: Write Pitch, Read Pitch, Size, Write Symmetry, Read Spread, Band Center, Band Width,
  Resonator Freq (tone targets per R16–R19), Width, Output.
- Defaults: slot 1 LFO 1 → Write Pitch, slot 2 LFO 2 → Read Pitch (depth 0, as the original);
  slots 3–4 empty.

## R5 UI approach (F19) — decided (user)

- **Every control stays a real `live.*` parameter object, drawn by a `jspainterfile` painter**
  (one shared painter per control type: dial, tab/segmented, toggle/pill, menu, slider).
  Automation, undo per gesture, MIDI/key map by click, right-click menu, Push banks, double-click
  default and typed entry stay native; a failing painter degrades to the stock look.
- **The `v8ui` display carries everything that links several elements:** voice lanes, Size zoom,
  mouse drawing, the tone curve with drag handles, modulation views.
- Rejected: (c) one large `v8ui` face with hidden `live.*` twins — hidden twins cannot be mapped
  by click in Live's map modes, undo/automation recording from patch-set values is unclear, and
  all native behaviour would have to be rebuilt (about 2–3× the effort). (a) plain restyled
  `live.*` stays the fallback if painters fail; (d) `jweb` not used.
- Gate before building the face: a small **probe device** (painted `live.dial` and `live.tab`)
  tested in Live with Max 9.1.5 and 9.2 — research note check G-UI1 (paint, theme repaint,
  automation/modulation dots via `parentpaint`, JS engine ES5 vs ES2020).

## R6 Tone section (F17) — decided (user), structure superseded by R16–R19

Own DSP; ideas only from Live's Auto Filter (licence note in the research note §5).

- Base chain as port-decisions Q9: Peak/Notch → HP4 → Drive → LP4 → DC blocker, linear FM from
  the core signal.
- From Auto Filter: **curve display** with drag handles for HP, LP and Notch, per-voice
  modulation shown as faint curves; **Notch follows LP** option (notch frequency as a ratio of
  the LP cutoff); **Clip** (soft clip) and **Output** after Drive.
- **Comb** (peaks ↔ notches) as an additional colour — in scope (user), details in R7.
- Not taken: circuit choice, envelope follower, sidechain, Vowel, Dry/Wet, DJ macro.

## R7 Comb (F17) — decided (user), superseded by R18 (Resonator)

- In series **after LP4, before the DC blocker**; **Mix 0 = bypass** and the default.
- Parameters: **Freq**, **Morph** (peaks ↔ notches, i.e. the sign of the feedback), **Feedback**,
  **Mix**.
- Frequency source: **fixed Hz** (20 Hz – 5 kHz) or **Track** = a ratio of the read pointer's
  frequency, so the comb follows the drone's fundamental.
- **Comb Freq is a mod target** (R4).

## R16–R19 Tone redesign (user critique of the first mock-up's Tone page) — decided (user)

The first mock-up laid the original's chain out as a row of dials (HP, Res, LP, Res, Notch, Gain,
FM): unintuitive. Options put to the user: (A) one multimode filter with LP→BP→HP morph,
(B) a variable band, (C) two formant-style peaks.

| # | Decision |
|---|---|
| R16 | **(B) Variable band.** Controls **Center**, **Width** (octaves, 0.2 … 10; fully open = practically bypass), **Res** (resonance at the band edges), **Slope** 12/24 dB, **FM** (audio-rate FM of Center from the unfiltered core signal, the original's grit). Internally still a coupled HP + LP (two TPT SVFs each side for 24 dB). **Pass / Reject** switch turns the same band into a band-stop, which replaces the separate notch and "Notch follows LP". (A) and (C) rejected; (C) may return later as a colour. |
| R17 | **Per voice:** each of the 5 voices has its own band; **Spread** fans Center across the voices (the faint per-voice curves in the display show it). |
| R18 | **Stages in order Drive → Band → Resonator → Clip**, shown left to right on the Tone page. Drive before the band (resonance shapes the distortion). **Resonator** replaces "Comb": **Freq** (fixed 20 Hz – 5 kHz, or **Track** = follows the read pointer frequency), **Feedback bipolar** (+ = peaks/metallic, − = notches/hollow; replaces Morph + Feedback), **Mix** (0 = bypass, default). **Clip** (soft clip) is a toggle at the end. |
| R19 | **Display on the Tone page:** drag inside the band = Center (x) and Res (y); drag a band edge = Width; double-click the band = Pass/Reject; the resonator's own handle: x = Freq, y = Feedback (up = peaks, down = notches). |

Mock-up updated accordingly (version 3 of the canvas; source copy `docs/mockup-v0.2/Main.dc.html`).

## R20–R23 Table behaviour (after the Reaktor screen recording) — `table-behaviour.md`

| # | Decision |
|---|---|
| R20 | **Write Pitch range −64 … 130** like the original (decided, user). The sample-rate dependence above roughly half the sample rate is named in the docs and the parameter info text; Fine gets finer resolution there and the display may show the rate as a multiple of fs [hypothesis: UI detail]. |
| R21 | **Init state:** a calm, recognisable start plus own presets for the aliasing regimes (v0.3); **until presets exist the init state sits in the aliasing regime** (write high, read low, small Size) (decided, user). |
| R22 | **"Tri ±" write shape** (the original's unscaled −1 … 1 triangle) as a fourth Shape entry next to Ramp / Tri / =Read — **only after capture C4** (clip or wrap) (decided, user). |
| R24 | **Anti-aliased ramp as an option** (decided, user, 2026-11-24): the original's Ramp Osc runs in "Anti-Aliased Sync" (capture C6, `table-behaviour.md` §6); the port offers an anti-aliased ramp next to the naive one for the Ramp shape of both pointers (Tri stays naive like Tri/Par Symm). Our own band-limited ramp (e.g. polyBLEP) [hypothesis: Reaktor's exact algorithm unknown]; outputs beyond 0 … 1 are clipped like the original's table. Where the switch sits and its default are [open] for the build round. |
| R23 | **Close the model gap first** (table-behaviour.md C5): the user captures C4 (Audio Table properties), C6 (oscillator properties), the sample rate and a simple-settings recording — the recording on 2026-11-25 (user). |

## R8–R15 Face details (F2, F3, F6–F14, F18) — decided (user), round 3

| # | Item | Decision |
|---|---|---|
| R8 | Pages, width (F13) | Left: Write and Read rows, always visible. Centre: the display. Right: pages **LFO · Mod · Tone · Out**, switched by a painted segmented `live.tab` (pill look). Device width about **900–1000 px** (was 834); height stays Live's 169 px. |
| R9 | Size (F6, F7) | Size stays a real `live.slider` (hidden parameters cannot be mapped by click), painted as a **thin bar along the bottom edge of the display**, overlaid so it reads as part of it. The display **zooms the x axis to the active span** (`Size·1024` cells) with a tiny overview of the whole row. |
| R10 | Mouse drawing (F9) | Drag in a lane writes that voice's row; **Shift** = all 5 voices; **Alt** = straight line; **double-click** a lane = reset to the identity ramp. The drawn table is **saved with the set** via a stored-only blob parameter [hypothesis: probe device]. While Write runs, the write pointer overwrites the drawing again — intended. |
| R11 | Lanes, views (F11, F12) | Line view = **5 stacked lanes** (~24 px each), no overlay. Line/2D via a **small icon in the display's top-right corner** (no tab). On the Tone page the display shows the **filter curve with drag handles** (R6, R19) instead of the table; the **Size bar and its overview are hidden there** (Size belongs to the table, not the filter; the paged-hide mechanism covers it) and the curve uses the full display height. |
| R12 | Write/Read rows (F2, F3) | Shape = painted segmented control with **waveform icons**; Active / Smooth / Direction = small **pill toggles**; **Free/Sync** = mini toggle that shows either the Pitch dial or the note-value dial (like Live's LFO Hz/Sync); more space between labels and dials. |
| R13 | Out page (F18) | Gate (Drone/MIDI), Resync, Transpose, Width, Output, a slim output meter. |
| R14 | Colours, display look (F8, F10) | Chosen **in the mock-up**: 2–3 switchable muted, near-monochrome palettes (one hue in two lightnesses for write/read; warm grey/sand; cool), line weights, optional slight glow. |
| R15 | Order | Interactive mock-up for approval **and**, in parallel, a small **probe device** (painted `live.dial` + `live.tab`, blob storage test) the user loads in Live with Max 9.2 and once with Live's bundled 9.1.5. The face rebuild starts only after mock-up approval **and** a passed probe. |

## Mock-up — approved (user, 2026-11-24)

- Interactive 1:1 mock-up of the v0.2 face (968 × 169 px), approved by the user:
  https://claude.ai/artifact/Q7WjdTv3XSUBiQkBwCKwt3 (private Design canvas). Source copy:
  `docs/mockup-v0.2/Main.dc.html` (reference for the rebuild, not runtime code).
- Approved as shown with the defaults: palette **Graphite** (write `#e4e4e4`, read `#8fa6b6` on
  dark; `#242424` / `#41627a` on light), glow on, line weight 1. Sand and Ice stay alternatives.
- It is a sketch of looks and interactions only; the motion in the display is a slowed-down
  simulation, not the DSP. Exact ranges are not set by it (Sync multiplier: R2, ×1…×64).
- Tone page reworked after the approval (R16–R19), Size hidden on the Tone page, pointer-row layout
  fixed (pills next to Shape, Mult field under Hz | Sync, Fine → "Detune" in Sync, single-line
  frequency hint): **approved (user, 2026-11-24)**, canvas version 16.
- Next: probe device test (R15, `test/probe-ui/`), then the face rebuild with jspainter painters.
