# aliasing — changelog

SemVer per device; tags `aliasing-v<version>` (monorepo). Earlier internal builds (v0.1–v0.3b) were
never released; their decisions are in `docs/`.

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
