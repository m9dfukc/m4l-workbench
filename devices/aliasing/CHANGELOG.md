# aliasing — changelog

SemVer per device; tags `aliasing-v<version>` (monorepo). Earlier internal builds (v0.1–v0.3b) were
never released; their decisions are in `docs/`.

## Unreleased

- **Info texts on the face** (Live's Info View, Max's clue window): every control shows its text under
  its long name as the title. The texts of 0.3.0-beta.1 had reached only `parameter_info` (and the
  README); the faces still showed older wordings, and four objects showed nothing.
- **Device description:** what the instrument does and which controls it has, as the info text of the
  title lines "Aliasing v0.3b / after D. Pank" on the Global page, and in the patcher's description; one
  text per face. (The device's title bar and empty areas keep Live's own "The Aliasing Instrument": a
  device cannot set that text.)
- Labels show the text of their control; section titles (Write, Read, LFO 1/2, Env Follower, Mod, Tune,
  Output), the mod matrix headers (what a source sends, what ±100 % does to a target), the meters and
  the table display (drawing, sample drop, Line / 2D, tone curve) have texts of their own.
- Live never shows the info text of a panel or a comment (measured, `test/probe-info/`), so each label's
  text sits on an invisible hover zone (`ubutton`) in front of it. 34 new boxes in A, 18 in B; no
  parameter, cord or rect changed.
- Checked in Live: the controls' texts. Not yet checked: the label zones, the meters and the display.

## 0.3.0-beta.1 — 2026-11-26

First public beta (GitHub pre-release, tag `aliasing-v0.3.0-beta.1`). Tested in Live 12.4.16 on macOS
with Live's bundled Max 9.1.5 and with Max 9.2.1; not yet verified: a Set saved with a dropped or
drawn table and reopened, a frozen copy loaded with this repository out of reach, Windows. Two faces of the same instrument, released side by side so testers can say which
one should stay for 1.0:

- **Aliasing A** (`Aliasing.amxd`, 918 px): hybrid face, the whole 8 × 9 mod matrix on its page.
- **Aliasing B** (`Aliasing B.amxd`, 800 px): larger table display with side pages, the modulation of
  one target at a time in a strip (targets in use are marked with a dot, Clear resets one target).

Both share the DSP (`aliasing.gendsp`) and the parameters:

- 5 voices, each writes the phase of its read pointer into a 1024-cell table at the write pointer and
  reads it back; write and read run at different speeds (Pitch −64 … +130 st, Fine in 0.001 st, or
  tempo sync with × N ÷ D and a global Sync Rate).
- Write shapes Ramp, Tri, Pulsar, Spike, Noise with a shape parameter; write state Freeze | Write | Clean;
  read shapes Ramp and Tri; Size, Read Spread, Transpose, Resync, Ramp anti-aliasing.
- Modulation: LFO 1, LFO 2, envelope follower, velocity, mod wheel, the voice itself, its neighbour and
  its read oscillator onto 9 targets.
- Tone: Drive, Band (center, width), Resonator; color limiter (gain, saturation, color, release,
  ceiling), 5 Hz DC blocker and a safety clip at the end.
- Table display (line or 2D view) that can be drawn into.
- **Sample drop:** an audio file dropped onto the table display becomes the table of all five voices,
  **FIT** (whole file, up to 10 min, band-limited resampling) or **1:1** (first 1024 samples); the
  drop switches the write state to Freeze.
- Freeze-ready: the device project lists every runtime file, so a frozen copy carries them all.
