# aliasing — reference renders from Reaktor

Plan for reference renders from the original. The user renders; Claude checks them and fills
in the table at the end. Renders and test inputs are local only:
`devices/aliasing/reference/renders/` (gitignored).

**Needed (port-decisions Q11): R1a, R1d and R7a–e only** — listening references for an
"inspired by" port (Q1), not numeric targets. Everything else below (R0, R2–R6, M1–M6) is
optional and stays as a menu in case a behaviour has to be checked later.

## Setup (once)

- Live 12, project sample rate **48 kHz** (the ensemble's saved rate). Reaktor 6.5.2 **plugin**
  on a MIDI track, ensemble = the original 2008 `.ens`.
- **Safety:** limiter on the **Master** (for listening), monitor down. Renders are exported as
  **individual tracks** (pre-master), so the limiter does not touch them.
- Make **activate** automatable: in Reaktor, assign it (and the knobs a test changes) to host
  automation; then draw an automation step `activate` 0 → 1 at 1.1.1.
- Export: *File → Export Audio/Video*, rendered track = the Reaktor track only, 32-bit float WAV,
  48 kHz, no normalise, no dither, length as listed.
- **Before every take:** reload the ensemble (the table keeps history; reloading restores the
  stored table) and then set the parameters, or load the named snapshot.
- Every take **twice** (`_t1`, `_t2`) for the determinism check.

Naming: `R<nr><letter>_<short-name>_48k_t<take>.wav`, e.g. `R1a_core-synced_48k_t1.wav`.
For every take write down the parameter values you changed, in a text file next to the WAV
(`R1a.txt`).

## Base state "core" (used by R1–R5)

Starting from the freshly loaded ensemble: Notch **on = off**, SaturatorFilter **on = off**,
**stereo 0**, read **sprd 0**, both LFO **Amt 0**, **Transpose 0**, size bar at **max**, OUT
−6 dB, write **active** on, write and read **Qulity = hi**. Then activate at 1.1.1.

## Renders

| Nr | Name | Change from "core" | Length | Answers |
|---|---|---|---|---|
| R0 | determinism | snapshot "quak", unchanged | 10 s | do two identical takes null? (if not: Reaktor randomness or timing; all later comparisons become statistical) |
| R1a | core-synced | In-Pitch −24, out Pitch −24, fines 0 (both pointers at 60−24) | 10 s | expect a plain saw: base mapping, table units, `2v−1` |
| R1b | core-detune-fine | as R1a, read fine 0.05 | 10 s | seam rate, sensitivity |
| R1c | core-detune-1st | as R1a, out Pitch −23 | 10 s | k ≈ 1.06 |
| R1d | core-ratio-2 | as R1a, out Pitch −12 | 10 s | k = 2 |
| R1e | core-ratio-big | In-Pitch −48, out Pitch 0 | 10 s | k ≈ 16, heavy skipping |
| R2a | write-fast | In-Pitch −20 (≈ 62 Hz > 46.9 Hz cell rate), out Pitch −24 | 10 s | write-cell skipping |
| R2b | write-slow | In-Pitch −40 (≈ 15 Hz), out Pitch −24 | 10 s | multiple writes per cell |
| R2c/d | size | as R1d with size bar at 50 % and 10 % | 10 s each | span mapping |
| R3a | lfo-write | as R1a, write LFO Amt 0.5, Freq 1 | 20 s | control-rate steps (400 Hz) on the write pointer |
| R3b | write-sprd | as R3a, write osc › stereo › hidden sprd at 6 (structure knob) | 20 s | is the write spread really overwritten by the LFO (R3a = R3b)? |
| R3c | lfo-read | as R1a, read LFO Amt 0.5, Freq 1 | 20 s | read-side steps, per-voice LFO rates |
| R4a | write-lo | as R1d, write Qulity lo, lo Qu 1 / 0.5 / 0 (three takes) | 10 s each | triangle pointer, negative positions (clip vs wrap) |
| R4b | read-lo | as R1d, read Qulity lo, `>>/< >` off and on | 10 s each | bidirectional read |
| R4c | write-eq-read | as R1d, write Qulity =read | 10 s | third switch position |
| R5 | voices | as R1d, stereo 1, read sprd 2 | 10 s | per-voice spread and pan law |
| R6 | 44k1 | R1a and R1d again with Live at 44.1 kHz | 10 s each | sample-rate dependence |
| R7a–e | full chain | snapshots "quak", "killer bass", "Berliner Ring 2050", "field (re-activate to sync)", "Zug hält" | 20 s each | A/B of the complete sound |

### Module renders (test ensemble)

The filters and saturators sit behind the table and cannot be fed directly. For these, build a
small **test ensemble** in Reaktor: an instrument with Audio In → a **copy of the SaturatorFilter
macro** (and one with a copy of the **Notch** macro) → Audio Out, with the same knob ranges. Load
it as an **effect** plugin in Live on an audio track and play the test inputs through it.

Claude generates the test inputs (48 kHz, 32-bit float) into
`reference/renders/inputs/` when this step starts: unit impulse, log sine sweep 20 Hz–20 kHz,
white noise, slow linear ramp −4..+4 (saturator curve), sine 100 Hz at −24/−12/0/+6 dBFS.

| Nr | Module | Settings | Answers |
|---|---|---|---|
| M1 | 4-Pole HP alone (Drv 0, LP\ 130, −DC off) | /HP 40/70/100, Reso 0/0.5/0.98 | HP4 response, resonance law |
| M2 | 4-Pole Filter LP alone (/HP −10) | LP\ 40/70/100, Reso 0/0.5/0.98 | LP4 response |
| M3 | FM | FAmt 0/500/3000 with sine 100 Hz | FM scaling (Hz per unit) |
| M4 | Saturator | Drv 0/10/30, ramp input | saturator curve and drive staging |
| M5 | Peak EQ | Frq 60/90, Boost −30/0/+20, Reso 0/0.5/0.98 | EQ shape, Q law |
| M6 | 1-Pole HP (−DC on) | — | DC-block corner (P unconnected) |

## Results

Filled in after each render session (via `live-test`): file, SHA-256, null result of t1/t2.

| File | SHA-256 | Determinism (t1 − t2 peak) | Notes |
|---|---|---|---|
| | | | |
