# aliasing — inventory of the original

Port of Reaktor User Library #5241 "aliasing Synth" (Dietrich Pank, 2008). This file records
what the original **is**: settings, module types, structure, panel controls, tables. What it
*does* is in `signal-flow.md`; what we decide to do about it is in `port-decisions.md`.

Evidence markers as in `CLAUDE.md`, plus:

- **[observed: parser]**: read from the original `.ens` by the local record-stream parser
  (`tools/local/reaktor_dump.py`, gitignored, never published). Field meanings are inferences
  from this file; where they could be cross-checked, the check is named.
- **[observed: <time>]**: seen in a screenshot `reference/reaktor/screenshots/Bildschirmfoto
  2026-11-24 um <time>.png` (local only). Breadcrumb paths in the screenshots give the location.

Where parser and screenshot disagree, the screenshot (and later the Properties page) wins and
the parser mapping is fixed (`reaktor-port` skill).

**Not in this file on purpose:** snapshot values, the stored table contents and the panel's
saved values. They are the author's work and stay local (`tools/local/out/`, see
"Local outputs" below).

## Sources

| Input | Notes |
|---|---|
| `reference/reaktor/Aliasing Synth 515 (original 2008).ens` | 144 346 bytes, SHA-256 `62ec413e…` (full hash in `reference/reaktor/README.md`). Pre-R6 format: flat stream of `[`-framed records `KEnsemble`, `KSModul` (326), `KInPort` (396), `KOutPort` (371) [observed: parser] |
| 25 screenshots (Reaktor 6.5.2, 2026-11-24) | panel + every structure level with breadcrumb; index in `docs/research/notes/aliasing-synth-sources-2026-11-24.md` §3 |
| Research note | `docs/research/notes/aliasing-synth-sources-2026-11-24.md` (provenance, community port, first structure analysis) |

### Parser status (spike, 2026-11-24)

What the parser reads reliably [observed: parser]:

- **Record framing:** `5b` + u32 class-name length + class name + u32 version, body, `5d`. All
  records are siblings; a module record is followed by its port records.
- **Tree:** containers carry a child count (macro types 4/7: u32 at body+12; instrument/ensemble
  type 9: u32 at record offset 170). Walking the stream in pre-order with these counts consumes
  **exactly 326 of 326 modules**: the hierarchy is decoded, not guessed.
- **Ports:** `KOutPort` = version, port kind, ?, flags, [name], [help], *n*, *n* × (target module
  index in the same structure level, target input index). `KInPort` = version, kind, ?, 8 bytes
  (`ff…`), flags, [name], [help]. Flag bit 1 = no name, bit 2 = no help. Port kind: 1 = audio,
  2 = event, 3 = event/audio (hybrid), 0 = ensemble-level/display. **Wiring is complete in the
  out-port lists**; it reproduces every wire checked against the screenshots (SaturatorFilter,
  write osc, Notch, voice0-1, from voice>LR).
- **Module type ID** (u32 after the `00 ab 21 00` marker), box rectangle in the structure view,
  label and info text.
- **Parameter block** of panel elements and constants: normalised current value, steps, min, max,
  parameter ID; for constants the "min" slot holds the value. Cross-check: OUT fader −36..0 dB,
  Transpose −12..12, `60`, `-60`, `0.5`, `2` constants as shown in the screenshots.
- **Snapshots:** 38 named snapshots in "Bank 1"; each panel element stores 38 values (normalised).
- **Audio Table data:** 5 × 1024 float32 stored in the first table (record @0x1a078; data at file
  offset 0x1a338), all values in 0..0.99976.

Not decoded (raw only): Audio Table header fields beyond size/range, module properties such as
Ramp Osc mode (the Ramp Osc record is a plain 89-byte module record with no property data, so
it presumably uses the default mode — [open]), internal-connection (IC) targets (see §7), panel
layout.

### Local outputs (gitignored, private)

| File | Content |
|---|---|
| `tools/local/out/aliasing-2008.txt` | full tree dump: every module with type, label, rect, parameter block, ports and resolved wiring |
| `tools/local/out/aliasing-2008.json` | the same as JSON |
| `tools/local/out/aliasing-2008-snapshots.{tsv,json}` | 38 snapshots × 37 panel elements, normalised and in units |
| `tools/local/out/aliasing-2008-table.json` | stored Audio Table contents (5 rows × 1024) |

Regenerate: `python3 -I tools/local/reaktor_dump.py "<ens>" --json tools/local/out/aliasing-2008.json > tools/local/out/aliasing-2008.txt`
and `python3 -I tools/local/export_private.py "<ens>" tools/local/out`.

## 1. Settings snapshot

| Setting | Value | Evidence |
|---|---|---|
| Ensemble sample rate (saved) | 48 000 Hz | [observed: parser] header bytes 0x26 (`80 bb 00 00`) |
| Control rate (saved) | 400 Hz | [observed: parser] header bytes 0x2a (`90 01 00 00`) |
| Tempo | 120 BPM | [observed: parser] header float 120.0 |
| Instrument voices | **5** | [observed: parser] u32 `5` right after the snapshot list in the instrument record; field meaning inferred, matches "5 voices" in the description [sourced] |
| Ensemble voices | 1 | [observed: parser] same field in the ensemble record |
| Unison, assign mode, reassign, MIDI channel | — | [open] → capture C1 |
| Reaktor's sample-rate display at load (Host vs Fixed 48 kHz) | — | [open] → capture C1 |
| Snapshots | 38 in "Bank 1" (names e.g. "quak", "killer bass", "Berliner Ring 2050", "field (re-activate to sync)") | [observed: parser] |

The LFO macros carry the help text "Event output (500 events/second)" on their output (a library
leftover); the ensemble's control rate is 400 Hz, which is what an event LFO follows [sourced:
fundamentals note §3] — so the pointer pitch steps every 120 samples at 48 kHz [inference].

## 2. Module type IDs

Numeric IDs from the original R5 file mapped to Reaktor modules. "Evidence" names the screenshot
label or the port/formula behaviour that fixes the mapping. Unconfirmed rows are the capture C3
list (hover tooltip in Reaktor).

| ID | Module | Ins/outs as stored | Evidence |
|---|---|---|---|
| 4 | Macro | per macro | [observed: parser + all structure screenshots] |
| 5 / 6 | Macro In / Out terminal | 0/1, 1/0 | terminals carry the macro port names (P, G, rd, W, RX, WX, …) |
| 7 | Macro (variant; only "AT view") | 6/1 | [observed: parser]; why it differs from 4 [open] |
| 9 | Instrument (and ensemble root) | 0/2 | "aliasing Synth" |
| 20 | Knob / Fader | 0/1 | OUT (fader) and all knobs share the ID; style is a property [inference] |
| 22 | Button | 0/1 | active, activate, reset, view, `>>/< >` |
| 24 | Switch | 2–3/1 | on, −DC, Qulity [observed: 15.52.50] |
| 25 | XY | 4/3 | size bar, Button (2-mode) [observed: 15.53.47] |
| 30 | Numeric readout (display) | 1/0 | "F", "Frq", "Hz" displays |
| 52 | Gate (MIDI) | 0/1 | [observed: 15.54.32] "Gate" |
| 100 | Constant | 0/1 | value in the parameter block |
| 110 | Add (+) | 2–5/1 | [observed: 15.52.50] |
| 111 | Multiply (X) | 2–3/1 | [observed: 15.52.50, 15.54.50] |
| 114 | Divide (÷) | 2/1 | formula check: voice0-1 and pan decode to `((V−0.5) − Vcs/2) / ((Vcs−1)/2)` only with 114 = ÷, 115 = − |
| 115 | Subtract (−) | 2/1 | as above |
| 116 | Mult/Add `a·b+c` ("X+") | 3/1 | [observed: 15.54.13] |
| 117 | Exp (P→F) | 1/1 | [observed: 15.52.50, 15.54.50] |
| 119 | Log (lin → dB?) | 1/1 | `1/Vcs` → 119 → + Lvl; [open] exact function |
| 126 | Power (x^y) | 2/1 | LFO amplitude = Amt^5 [observed: 15.53.07] |
| 156 | Mixer (1 channel, Lvl in dB) | 2/1 | [observed: 15.54.50] |
| 157 | Stereo Mixer (Lvl, Pan, In) | 3/2 | [observed: 15.55.00] |
| 163 | Router (Ctl, In) | 2/1 | [observed: 15.52.50] |
| 178 | Tri/Par Symm (P, A, W → Tri, Par) | 3/2 | [observed: 15.52.50] |
| 207 | Ramp Osc (F, A, Snc, Ph) | 4/1 | [observed: 15.52.50] |
| 208 | Audio Table (RX, RY, WX, WY, In, W, XO, XR, YO, YR → Out, DX, DY) | 10/3 | [observed: 15.54.13] |
| 260 | LFO (5 in, 3 out; out 1 used) | 5/3 | [observed: 15.53.07] |
| 300 | 1-Pole Filter (P, In → HP, LP) | 2/2 | [observed: 15.54.50] |
| 308 | 4-Pole Filter (P, F, Res, In → HP2, BP2, LP2, BP4, BL4, **LP4**) | 4/6 | [observed: 15.54.50]; output 6 (LP4) used |
| 310 | 4-Pole HP (P, F, Res, In → HP2, BP2, LP2, **HP4**, BH4, BP4) | 4/6 | [observed: 15.54.50]; output 4 (HP4) used |
| 314 | Peak EQ (P, Res, B, In) | 4/1 | [observed: 15.54.32] |
| 360 | Saturator | 1/1 | [observed: 15.54.50] |
| 411 | NOT (output 2 = "Not") | 1/2 | [observed: 15.52.50] |
| 414 | Separator | 2/2 | [observed: 15.55.16] |
| 415 | Value (Trig, In) | 2/1 | [observed: 15.51.27] |
| 417 | Merge ("M", event merger) | 1–2/1 | tooltip [observed: 15.52.50] |
| 420 | Hold | 2/1 | [observed: 15.53.57] |
| 442 | Voice Combiner `}` | 1/1 | [observed: 15.55.00] |
| 443 | ? ("from last Gate", output unconnected) | 1/1 | [open] |
| 444 | Select Max (In, G) | 2/1 | [observed: 15.54.32] |
| 451 | From Voice ("Fr. V") | 2/1 | [observed: 15.52.50] |
| 452 | "S" in size bar (self-loop on the XY) | 1/1 | [open] |
| 453 | "S" in the Reso paths and KeyTrack | 1/1 | [open] — tooltip needed; matters for filter resonance |
| 456 | Voice Info (→ V, Vcs, Min, Max) | 0/4 | [observed: 15.52.50] |
| 461 | Snapshot | 12/12 | [observed: 15.53.57] |
| 500 / 501 | Ensemble Audio In / Out (16 ch) | 0/16, 16/0 | [observed: 15.51.10] |
| 531 | IC Send | 1/0 | `>read PIC`, `>write PIC`, `>write fineIC`, `sw>` [observed: 15.52.50] |

## 3. Structure tree

Child counts and order as stored [observed: parser]. Index = position in its structure level
(the target index used by the wiring).

```
Ensemble (3)
├─ Audio In (500), Audio Out (501)
└─ aliasing Synth  — instrument, 5 voices (22)
   ├─ SaturatorFilter (26)        "Split filter with Saturator between the two 2-pole filter units."
   ├─ Notch (14)                  "EQ filter"
   │  └─ KeyTrack (10)            output unconnected (dead branch, see §6)
   ├─ write osc (28)
   │  ├─ LFO (14) └─ voice0-1 (17)
   │  └─ stereo (17)              hidden spread knob
   ├─ read (26)
   │  ├─ LFO (12) └─ voice0-1 (17)
   │  └─ Osc (13) └─ from last Gate (9)
   ├─ from voice>LR (24)          pan, level, voice combiners
   ├─ Button (2-mode) (7)         OUT "reset" to −6 dB via IC
   ├─ Switch2x2 I/O (8)           leftover L2/R2 "Beat Loop" inputs
   ├─ AT view (14)                type 7
   │  ├─ line view (13)           Audio Table #1 (stores data)
   │  └─ 2D view (13)             Audio Table #2 (no stored data)
   ├─ (unnamed view macro) (13)   Snapshot → Hold 22 → Separator → toggle
   └─ size bar (5)
   + top level: OUT fader, Transpose knob, activate button, view button, M (Merge),
     Value(60), two X (Multiply), IC send sw>, two Out terminals
```

## 4. Panel controls

All panel elements with their stored range [observed: parser]. "Steps" is Reaktor's
"Num Steps" (mouse resolution). Param ID is Reaktor's internal ID (used by the IC links in §7).
Unit and behaviour come from the signal flow (`signal-flow.md`).

| Section / path | Label | Type | Min | Max | Steps | ID | Unit / role |
|---|---|---|---|---|---|---|---|
| top | **activate** | Button | 0 | 1 | — | 61 | all-voice gate ("all-voice-Gate on") |
| top | **Transpose** | Knob | −12 | 12 | 127 | 91 | semitones, both pointers |
| top | **OUT** | Fader | −36 | 0 | 127 | 1 | dB, output level (+ voice-count compensation) |
| top | **view** | Button | 1 | 0 | — | 104 | table display style (UI only) |
| write osc | **In-Pitch** | Knob | −64 | 130 | 388 | 27 | semitones, added to 60 |
| write osc | **fine** | Knob | 0 | 0.5 | 500 | 29 | semitones |
| write osc | **lo Qu** | Knob | **1** | **0** | 127 | 28 | Tri/Par Symm W (symmetry); range runs 1 → 0 |
| write osc | **Qulity** | Switch, **3 positions** | — | — | — | 36 | hi = Ramp Osc, lo = Tri/Par Symm, **=read** = write position follows the read signal |
| write osc | **active** | Button | 0 | 1 | — | 37 | write enable |
| write osc | **reset** | Button | 0 | 1 | — | 58 | copy write pitch to read (Router → IC `>read PIC`) |
| write osc / LFO | **Amt** | Knob | 0 | 1 | 100 | 31 | amplitude = Amt^5 semitones; display ×100 |
| write osc / LFO | **Freq** | Knob | 0 | 12 | 240 | 33 | LFO base frequency (Hz) |
| write osc / stereo | **sprd** (hidden) | Knob | 0 | 6 | 127 | 83 | write pitch spread over voices; on the structure only, not on the panel [observed: parser rect + 15.50.59] |
| read | **out Pitch** | Knob | −64 | 64 | 256 | 38 | semitones |
| read | **fine** | Knob | 0 | 0.5 | 500 | 42 | semitones |
| read | **sprd** | Knob | 0 | 6 | 127 | 82 | read pitch spread over voices |
| read | **Qulity** | Switch, 2 positions | — | — | — | 39 | hi = Ramp Osc, lo = Tri/Par Symm (scaled to 0..1) |
| read | **>>/< >** | Button | **1** | **0** | — | 40 | Tri/Par Symm W of the read pointer (one direction / bidirectional) |
| read | **reset** | Button | 0 | 1 | — | 87 | copy read pitch + fine to write (IC `>write PIC`, `>write fineIC`) |
| read / LFO | **Amt** | Knob | 0 | 1 | 200 | 43 | as write LFO |
| read / LFO | **Freq** | Knob | 0 | 12 | 127 | 45 | as write LFO |
| Notch | **Frq** | Knob | 20 | 130 | 127 | 19 | semitones (pitch of the Peak EQ) |
| Notch | **Reso** | Knob | 0 | 0.98 | 127 | 16 | Peak EQ Res, via "S" |
| Notch | **Boost** | Knob | −30 | 20 | 127 | 18 | dB (negative = notch) |
| Notch | **on** | Switch | — | — | — | 21 | bypass |
| Notch / KeyTrack | **K folw** | Knob | 0 | 1 | 127 | 20 | dead: KeyTrack output unconnected |
| SaturatorFilter | **/HP** | Knob | −10 | 130 | 140 | 6 | semitones, HP4 cutoff pitch |
| SaturatorFilter | **Reso** (HP) | Knob | 0 | 0.98 | 127 | 5 | via "S" |
| SaturatorFilter | **FAmt** (HP) | Knob | 0 | 3000 | 127 | 9 | Hz per unit input (linear FM) |
| SaturatorFilter | **LP\\** | Knob | 0 | 130 | 240 | 2 | semitones, LP4 cutoff pitch |
| SaturatorFilter | **Reso** (LP) | Knob | 0 | 0.98 | 127 | 12 | via "S" |
| SaturatorFilter | **FAmt** (LP) | Knob | 0 | 3000 | 127 | 13 | Hz per unit input (linear FM) |
| SaturatorFilter | **Drv** | Knob | 0 | 30 | 100 | 4 | dB into both saturators |
| SaturatorFilter | **on** | Switch | — | — | — | 10 | bypass (dry vs processed) |
| SaturatorFilter | **−DC** | Switch | — | — | — | 90 | 1-pole HP (DC block) vs raw LP4 |
| from voice>LR | **stereo** | Knob | 0 | 2 | 127 | 75 | pan spread ("0 mono, 1 equal from L to R, 2 more extreme L/R") |
| size bar | **size bar** | XY | 0 | 1 | 7 | 107 | pointer span multiplier (MX); X range 0..1 [observed: parser], Properties [open] |
| Button (2-mode) | **reset** (OUT) | XY | 0 | 1 | 11 | 77 | sets OUT to −6 dB via IC |
| Switch2x2 I/O | on ×2 | Switch | — | — | — | 92, 93 | leftover input selection (L/R vs unconnected L2/R2) |
| AT view | (switch) | Switch | — | — | — | 103 | picks line-view vs 2D-view table output |

Switch position encoding: the stored normalised value is 0.5, 0.667 or 1 for 2- and 3-input
switches; which input that selects is [open] (capture C2), so the private snapshot table keeps
the raw values.

Constants [observed: parser]: 60 (base pitch at the top level, in each LFO path and in read), 1
(Ramp/Tri amplitude A, voice arithmetic), 0.5, 2, −1 (table output `2v−1`, voice position
maths), 5 (LFO Amt exponent), 100 (display scaling), 0.1 (unconnected, write stereo), 3 (From
Voice index in "from last Gate"), 22 (Hold in the view macro), −60 (KeyTrack), −6 (OUT reset),
0 (table XO).

## 5. Audio Tables

| | line view (#1) | 2D view (#2) |
|---|---|---|
| Record | @0x1a078, 21 197 bytes | @0x204cb, 593 bytes |
| Size X × Y | 1024 × 5 | same header [observed: parser] |
| Value range | 0..1 | same |
| Stored data | yes: 5 × 1024 float32 (0.0..0.99976), rows look like ramp segments with wrap jumps | **none** |
| Header difference | one u32 = 3 | = 4 (display style: line vs 2D) [inference] |
| Inputs wired | RX, RY = WY (`V−1`), WX, In (read signal), W, XO = 0, XR = size bar, YR = Vcs | identical |
| Output | `Out·2 − 1` (Mult/Add 116) → AT view switch | identical |

Both tables are written with identical inputs and the AT view switch passes one of them on
(`signal-flow.md` §4). Header floats 48.0, 120.0, 268.0, 5.0 and u32 24, 4 are not decoded. X
units, clip/wrap, read interpolation and "save table data" are **[open]** (capture C4) — they
define the pointer → cell mapping.

## 6. Corrections to the research note

The parser changes these points of `docs/research/notes/aliasing-synth-sources-2026-11-24.md`
(screenshots re-checked):

1. **Notch: KeyTrack is dead.** The Frq knob feeds the Peak EQ's P directly (and the KeyTrack Cut
   input and the Exp display); KeyTrack's C output has no connection. So the notch pitch is
   `Frq` (semitones), K folw does nothing [observed: parser; consistent with 15.54.32].
2. **write osc "Qulity" has three positions:** hi (Ramp), lo (Tri/Par Symm), **=read** (the
   macro's `rd` input, i.e. the read pointer's 0..1 signal, becomes the write position)
   [observed: parser + 15.52.50].
3. **Filter outputs:** HP uses output 4 "HP4" of the *4-Pole HP*; LP uses output 6 "LP4" of the
   *4-Pole Filter* [observed: parser + 15.54.50].
4. **−DC switch:** input 1 = 1-Pole Filter HP output (P unconnected), input 2 = LP4 directly; so
   "−DC" switches a DC-blocking 1-pole HP in or out [observed: parser + 15.54.50].
5. **LFO frequency per voice:** `F = Freq · (Freq + u)`, with `u` = voice position 0..1 from
   voice0-1 (Add then Multiply). The research note left it ambiguous [observed: parser].
6. **Read LFO has no base pitch**; the write LFO adds the constant 60 (its macro input) to
   `Amt^5 · sin`. Read gets 60 from its own constant in the spread sum [observed: parser].
7. **Ranges** now known for all controls (§4), e.g. `lo Qu` and `>>/< >` run 1 → 0, LFO Freq
   0..12, OUT −36..0 dB.

## 7. Internal connections (IC)

IC sends inside the instrument: `>read PIC` (write osc reset → read out Pitch), `>write PIC` and
`>write fineIC` (read reset → write In-Pitch and fine), `sw>` (view macro → AT view switch), and
the OUT reset button (→ OUT fader, −6 dB) [observed: 15.52.50, 15.55.16 + parser]. The
instrument record ends with 6 ID pairs (`0x27ee→0x27f1`, `0x27e5→0x27f2`, `0x27e6→0x27f3`,
`0x27e4→0x27f4`, `0x27ee→0x27f5`, `0x273c→0x27f6`) that look like the IC link table; resolving
the IDs to modules is not reliable yet [observed: parser, partial]. The receiving sides are
[open] (capture C5). These links are UI conveniences ("sync" gestures), not DSP.

Also unresolved: the write osc `reset` button and the Router's Ctl input show no stored wire
[observed: parser]; the screenshot suggests one [observed: 15.52.50] → capture C5.
