# Ableton Live 12 Auto Filter: feature set and UI, as idea source for the aliasing "Tone" section

Date: 2026-11-24

**Question:** What exactly is Ableton Live 12's Auto Filter (Live 12.4 era, redesigned in 12.2)
as a feature set and UI, and which of its ideas fit the Tone section of `aliasing` (5-voice
drone, own GenExpr DSP)?

Evidence markers as in `CLAUDE.md`. "Local" sources are files of the installed Live 12 Suite
12.4.16 and Max 9.2.0, read only (Live and Max were not launched). Bracketed letters such as
[M] point to the Sources list at the end.

## Summary

- Auto Filter was **redesigned in Live 12.2** (released 2025-06-11): new UI with an output
  spectrum and separate L/R modulation curves, six new filter types, reworked circuits, new
  LFO shapes, Output/Clip/Dry-Wet [sourced: R, L, B].
- **Ten filter types:** Low-pass, High-pass, Band-pass, Notch, Morph, DJ, Comb, Resampling,
  Notch + LP, Vowel [sourced: M, X].
- **Four circuits** now: SVF, DFM, MS2, PRD; they only affect LP/HP/BP/Notch/Morph. The pre-12.2
  circuits Clean, OSR and SMP are gone from the new device [sourced: M, R, C, M11].
- The old device lives on as **Auto Filter Legacy** (presets in a Legacy folder) [sourced: R, local].
- **Modulation:** stereo LFO (8 shapes, Morph, Phase/Spin, Steps or S&H quantization), envelope
  follower (Attack, Hold, Release, S&H, bipolar amount), sidechain with its own EQ [sourced: M, L].
- **Face:** big central display (filter curve + L/R modulated curves + live output spectrum,
  one drag handle for Freq/Res), Freq/Res column left, Drive/circuit/Clip/Output/Dry-Wet
  column right, modulation row below the display [sourced: M, L, local screenshot].
- About **42 automatable device parameters** plus 3 sidechain parameters in the default preset
  [sourced: local preset].
- The **Resampling** type is a deliberate aliasing filter: a phasor at the cutoff frequency
  triggers sample-and-hold with linear interpolation [sourced: L].
- Best fits for `aliasing` [hypothesis]: drag handle on a curve display with per-voice modulation
  curves, a DJ-style single "Tone" macro over our HP and LP, per-voice LFO spread (Phase/Spin
  idea), Wander/S&H+Smooth shapes, Clip + Output after Drive, Notch tied to the LP cutoff.
- Poor fits [hypothesis]: hardware-modelled circuit choice, sidechain/envelope follower on a
  steady drone, Vowel, Morph slopes up to 48 dB.

## 1. Filter types, circuits, Drive, Resonance

### Filter types (Live 12.2+)

| Type | Behaviour | Slopes | Source |
|---|---|---|---|
| Low-pass, High-pass, Band-pass, Notch | classic responses | 12 or 24 dB | [sourced: M] |
| Morph | one Morph control sweeps LP (low) → BP (mid) → HP (high) | 6, 12, 24, 48 dB | [sourced: M, L] |
| DJ | one bipolar Control (−100 … +100 %) replaces Freq: positive removes lows, negative removes highs, like a DJ mixer; resonance grows towards the extremes | – | [sourced: M, L] |
| Comb | peaks or notches at multiples of the cutoff; Morph moves from peaks (low) to notches (high); flanging when modulated | – | [sourced: M, L] |
| Resampling | resamples continuously at a rate set by the cutoff; spectral images and aliasing; "linear interpolation, triggered by a phasor wrapping at the filter cutoff frequency"; Res greyed out | – | [sourced: M, L] |
| Notch + LP | an SVF notch plus a low-pass; Morph moves the notch towards the LP cutoff, reaching it at 100 % | 12 or 24 dB | [sourced: M, L] |
| Vowel | formant filter; Pitch (semitones) replaces Freq, Formant replaces Res, Morph normalises formant gains | – | [sourced: M, L] |

The Max object `abl.device.autofilter~` (Ableton DSP package 2.0.0, bundled with Max 9.2.0)
documents the same ten types, Vowel Formant as a morph through a/e/i/o/u, Vowel Pitch
−36 … +36 st, Frequency 20 … 20000 Hz, Resonance 0 … 1 [sourced: local refpage A]. Whether the
Live device uses the same ranges is [open].

### Circuits

| Circuit | Description (Ableton's) | Source |
|---|---|---|
| SVF | clean state-variable filter, distorts when Drive > 0 | [sourced: M, L] |
| DFM | new; feeds back more of its own distortion; gentle sweeps to warm drive | [sourced: M, L, R] |
| MS2 | Sallen-Key with soft clipping that limits resonance; modelled on a Japanese semi-modular monosynth | [sourced: M, R] |
| PRD | ladder without explicit resonance limiting; modelled on a US dual-oscillator monosynth | [sourced: M, R] |

- Circuits apply only to Low-pass, High-pass, Band-pass, Notch and Morph [sourced: M].
- **Removed in 12.2:** SMP (a custom MS2/PRD hybrid) [sourced: C, M11]; Clean and OSR (OSR was a
  state-variable filter with a hard-clipping diode, modelled on a British monosynth) are no
  longer in the new circuit list [sourced: M, M11].
- The Max object only offers **SVF and DFM** [sourced: local refpage A].

### Drive, Resonance, output stage

- **Drive** adds input gain before the filter; 0 % is unaltered, distortion rises with the
  value [sourced: M]. In Live 11, Drive existed only for non-Clean circuits, and resonance
  above 100 % made non-Clean circuits self-oscillate [sourced: M11].
- **Output** compensates loudness after Drive; **Clip** soft-clips the output so it stays at or
  below 0 dB, with a flashing LED; **Dry/Wet** [sourced: M, L]. CDM notes the new gain staging
  makes deliberate overdrive easy [sourced: C].
- The Max object adds an **Oversample** on/off ("hi-quality mode") [sourced: local refpage A];
  whether the Live device exposes it is [open] (not in the default preset's parameter list).

## 2. Modulation

### LFO

- Independent L/R LFOs; **Stereo Mode** Phase (offset in degrees, 180° = opposite) or Spin
  (rate detune in %) [sourced: M].
- **Phase Offset** shifts the start point of both LFOs, only in tempo-synced modes [sourced: M].
- **Rate** in Hz, time (s), beat divisions or sixteenths via a Mode chooser [sourced: M].
  CDM: triplet and dotted values, divisions down to 1/64 [sourced: C]. Max object: 0.1 … 60 Hz,
  Spin 0 … 0.5 [sourced: local refpage A].
- **Waves:** Sine, Triangle, Saw, Square, Ramp Up, Ramp Down, Wander, S&H; Spin does nothing
  on Wander and S&H [sourced: M]. **LFO Morph** reshapes/tilts the wave; for S&H it becomes
  **Smooth** [sourced: M, L]. 12.4.3 fixed Morph affecting Wander [sourced: R].
- **Quantization:** Steps (N equal steps per cycle) or S&H (update at a beat-time value)
  [sourced: M, L].
- **LFO Amt** sets depth; usable together with or instead of the envelope [sourced: M].
- Retrigger: not described in the manual [open].

### Envelope follower

- Attack (inertia on rising level), **Hold** (finish the attack before release, even for short
  transients), Release, **Envelope S&H** with rate, and a bipolar **Envelope** amount
  [sourced: M, L]. Max object ranges: amount −1 … 1, attack 0 … 0.1, release 0 … 3 (unit not
  stated) [sourced: local refpage A].

### Sidechain

- Toggle on the left side of the device: External on/off, source + tap point (Pre FX, Post FX,
  Post Mixer), Mix, SC Gain, Listen, and an **SC EQ** (low shelf, peak, high shelf, LP, BP, HP;
  frequency, Q, gain). Mono sidechain on by default (context menu) [sourced: M, L, local
  refpage A].

### How modulation is shown

- The display draws the static filter curve, the **modulated left and right curves**
  separately and the **real-time output spectrum**; one handle sets Freq + Res (Pitch +
  Formant for Vowel) [sourced: M, L].
- Selecting the LFO or Envelope amount shows that source's detail parameters in a strip
  directly under the display [sourced: L, local screenshot].

## 3. Layout and UI

From the What's New screenshot shipped with Live
(`…/Builtin Lessons/0-What's New Category/1-What's New Lessons/Large/AutoFilter.png`, viewed
locally, not copied) [sourced: local screenshot], consistent with [M, L]:

- **Left column:** large **Freq** knob, filter-type chooser (icon), 12/24 slope buttons,
  **Res** knob; vertical **Sidechain** tab at the far left edge.
- **Centre:** wide display with grey output spectrum, two coloured curves (L/R), a round handle
  at cutoff/resonance; below it a context strip (e.g. "LFO | Phase | 0.0° | 0.0° | Steps 2").
- **Bottom row:** LFO Amt and Rate knobs, Wave chooser, Morph, Mode (Rate/sync), then a large
  **Envelope** amount knob.
- **Right column:** **Drive** knob, circuit chooser, Clip toggle with LED, Output (dB),
  **Dry/Wet** knob.
- No expanded view is described for Auto Filter; the manual mentions one only for EQ Eight
  [sourced: M]. The sidechain panel unfolds from its toggle [sourced: M, L].
- **Parameter count:** the default preset (`Core Library/Defaults/Audio Effects/Auto
  Filter.adv`) holds 42 device parameters (Filter_* 11, Lfo_* 16, Envelope_* 6, Output,
  SoftClipOn, DryWet, SideChainEq_* 5, plus On) and 3 sidechain parameters; defaults include
  Freq ≈ 10 kHz, Slope 24 dB, Circuit SVF, Envelope Attack 1 ms, Hold on, LFO Steps 8
  [sourced: local preset, read with gzip, not modified].

## 4. Ideas for the aliasing Tone section [hypothesis]

Context: the port already plans HP4 + LP4 (TPT SVF) with audio-rate FM, a peak/notch, drive and
tanh, DC blocker (`devices/aliasing/docs/port-decisions.md`, Q9).

### Ideas that fit

- **Curve display with a drag handle** (v8/jsui): drag LP cutoff/reso directly; a second
  handle for HP. Cheap in UI, high value; no DSP change.
- **Per-voice modulated curves** instead of L/R: five faint curves show where each voice's
  filter currently sits (FM, LFO); makes the 5-voice spread visible.
- **Output spectrum behind the curve**: shows the aliasing images the device is about; costs a
  little CPU (FFT on the summed output, low-priority drawing).
- **DJ-style single "Tone" macro**: one bipolar knob that closes the LP below 0 and opens the HP
  above 0; a performance control over our existing HP/LP pair, no new filter.
- **Notch tied to the LP cutoff** (Notch + LP idea): an option to set the notch as a ratio of
  the LP cutoff so the notch follows LP sweeps.
- **Stereo LFO Phase/Spin generalised to 5 voices**: phase spread (0 … 360° across voices) and
  rate spread (Spin) for slow, non-unison filter motion in a drone.
- **Wander and S&H + Smooth shapes**: slow random drift suits drones better than synced shapes.
- **Clip toggle + Output after Drive**: matches our safety stage (`.claude/rules/gen.md`) and
  keeps loudness constant while drive changes.
- **Comb (peaks ↔ notches at multiples of a frequency)**: a pitched resonance colour for drones;
  candidate for a later version, not the faithful port.

### Ideas that do not fit

- **Circuit chooser (SVF/DFM/MS2/PRD)**: we write our own filters; hardware-modelled variants add
  scope without serving the port, and their names are Ableton's labels.
- **Resampling filter**: thematically close, but the device already aliases by design; a second
  aliasing stage is redundant in the faithful port (maybe a later "extra").
- **Envelope follower**: a steady drone gives little level movement to follow.
- **Sidechain + SC EQ**: an M4L instrument has no audio input in the normal case; out of scope.
- **Vowel filter**: a separate formant design, outside the original's HP/LP/notch chain.
- **Morph slopes 6 … 48 dB**: our chain is fixed 4-pole HP + 4-pole LP as in the original.
- **Tempo-synced Steps/S&H quantisation**: low priority for a free-running drone; cheap to add
  later if wanted.
- **Dry/Wet**: inside an instrument, "Filter On" plus Output already covers the use.

## 5. Licence and IP note

- We take **feature and layout ideas only**. No Ableton code, DSP, presets, graphics,
  screenshots or text go into this repo; the screenshot above was only viewed in place.
- We do **not** claim any circuit emulation; our filters are generic textbook structures (TPT
  SVF, RBJ biquads), described by their own names, not as "DFM", "MS2", "PRD" or as models of
  any hardware.
- Generic terms (low-pass, notch, comb, S&H, LFO phase/spread, soft clip, dry/wet) are common
  vocabulary and free to use [hypothesis].
- `abl.device.autofilter~` ships with Max 9 (also in Live's bundled Max) [sourced: local]. It
  could be used in a device without copying anything, but the workbench rule is own GenExpr DSP,
  so it is at most a quick reference for A/B listening [hypothesis].

## Sources

- [M] Ableton Live 12 Reference Manual, Live Audio Effect Reference, 29.2 Auto Filter
  (29.2.1–29.2.7.1): https://www.ableton.com/en/manual/live-audio-effect-reference/
- [R] Ableton Live 12 release notes (12.2 Auto Filter redesign, 12.2 Core Library "Auto Filter
  Legacy" presets, 12.2.5 and 12.4.3 fixes): https://www.ableton.com/en/release-notes/live-12/
- [B] Ableton blog, "Live 12.2 is out now": https://www.ableton.com/en/blog/live-12-2-is-out-now/
- [C] CDM, "Live 12.2 hands-on guide": https://cdm.link/live-12-2-hands-on-guide/
- [M11] Ableton Live 11 Reference Manual, 24.2 Auto Filter (old circuits Clean, OSR, MS2, SMP,
  PRD): https://www.ableton.com/en/live-manual/11/live-audio-effect-reference/
- [L] Local, Live's What's New lesson, page "Auto Filter Update":
  `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Builtin Lessons/0-What's New Category/1-What's New Lessons/LessonsEN.txt`
- Local screenshot: same folder, `Large/AutoFilter.png` (viewed only).
- Local preset: `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Core Library/Defaults/Audio Effects/Auto Filter.adv`;
  legacy preset folder `…/Core Library/Devices/Audio Effects/Legacy/Auto Filter Legacy/`.
- [A] Local refpage `abl.device.autofilter~`, Ableton DSP package 2.0.0:
  `/Applications/Max.app/Contents/Resources/C74/packages/ableton-dsp/docs/abl.device.autofilter~.maxref.xml`
