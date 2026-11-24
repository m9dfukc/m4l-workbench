# aliasing — why the Reaktor table looks different from ours (2026-11-24)

Trigger: the user's screen recording of the original in Reaktor (local only:
`reference/reaktor/screenrecordings/Bildschirmaufnahme 2026-11-24 um 23.14.11.mov`, 28 s,
504 × 346 px, gitignored) — "the table behaves very differently in Reaktor and looks much less
linear than ours; it looks cooler". Frames were extracted locally (AVFoundation; Homebrew
ffmpeg is broken on this machine: it links `libx265.216`, `217` is installed). Simulation:
`scripts/table_sim.py` (our code, formulas from `signal-flow.md` §2). Evidence markers as in
`CLAUDE.md`.

## 1. What the recording shows [measured: screen recording, frames at 0, 3.1, 6.3, 9.4, 12.6, 15.7 s]

- Snapshot **026 "Zeppelin Kanzel"** (edited, `*`): write osc **In-Pitch 73 → 18003 Hz**, fine
  0.255, **Qulity lo** (Tri/Par Symm), lo Qu ≈ 0.05, write LFO Amt 0; read **out Pitch −29.5 →
  47.8 Hz**, LFO Amt 100 (= 1 semitone), sprd ≈ 2.2; Transpose ≈ 0.1; the user moves **Size**
  during the recording.
- The display is **zoomed to the span** (Size bar ≈ 8 %: the whole width shows the active cells).
- Size ≈ 8 %: every lane is a **zigzag of sloped segments over almost the full lane height with
  step discontinuities** (≈ 6 periods across the span), lanes differ per voice.
- Size ≈ 30 %: similar zigzag at a larger scale; Size ≈ 78 %: a **dense noisy fill** with a
  triangular envelope; Size → 0: flat lines (one cell); 2D view at Size ≈ 3 %: large blocks
  (single cells).

## 2. What v0.1 shows

At its defaults (write and read pitch 0, write fine 0.07, Size 1, ramp) the table stays close to
the identity ramp with a slowly moving discontinuity — "linear" (simulation case 5).

## 3. Causes

| # | Cause | Evidence |
|---|---|---|
| C1 | **Range and defaults.** The original's write **In-Pitch runs −64 … 130** (note 60 + 130 = 190, far above Nyquist) and its presets put the write pointer far above the read pointer (026: 18 kHz vs 48 Hz). v0.1 clamps both pitches to **±64** (write ≤ ~10.7 kHz) and starts with write ≈ read, where the table is barely changed. | [sourced: `tools/local/out` snapshot ranges, inventory §4] [code: `gen/aliasing.genexpr`] |
| C2 | **Display.** The original zooms the line view to the span (`XR = size`); v0.1 draws all 1024 cells and darkens the inactive part, so a small span is a few pixels wide. Already decided: R9 (zoom). | [sourced: signal-flow §2 table] [code] |
| C3 | **Write "lo" is not rescaled in the original:** Tri/Par Symm outputs **−1 … 1**, so half of each write cycle lands on negative positions, which the Audio Table **clips** to the first cell (capture C4, §6). v0.1 rescales the triangle to 0 … 1 — a deviation missing from D1–D6 in `v0.1-core.md`. | [sourced: signal-flow §2 write pointer] [code] |
| C4 | **Sample-rate sensitivity.** With write rates near the sample rate the written pattern depends on how close `f_w / fs` is to a simple ratio (the per-sample write positions form a drifting lattice). 44.1 and 48 kHz give clearly different tables for the same settings (cases 1 vs 2). Port decision Q6 ("differs slightly") understates this for high write rates. | [code: simulation]; Reaktor ran at **48 kHz** (capture, §6) |
| C5 | **Model gap — resolved (§6): the simulation had the wrong write frequency.** The simulation of the original's formulas does **not** reproduce the recording: it gives cell-to-cell zigzags (1–3 cells per period), Reaktor shows smooth runs over many cells. Something in the original slows the effective write motion or smooths it: candidates are the Audio Table properties (X units, clip/wrap, interpolation, write behaviour), the oscillators above Nyquist, or how the line view draws. | [open → captures] |

## 4. Effect on the sound

The table **is** the waveform: the read pointer plays it back (`y = 2·T − 1`). A stepped or
zigzag table means steps and folds in the output, i.e. more high partials and a grainy, moving
timbre; a near-linear table is close to a plain sawtooth. Simulation, summed voices
[code: `scripts/table_sim.py`, 2026-11-24]:

| Case | Spectral centroid | Energy > 4 kHz |
|---|---|---|
| original model, 026, 44.1 kHz, Size 0.08 | 911 Hz | 4.4 % |
| original model, 026, 48 kHz, Size 0.08 | 1004 Hz | 4.8 % |
| original model, 026, 44.1 kHz, Size 0.29 | 5521 Hz | 51 % |
| v0.1 DSP, same settings, write pitch clamped to +64, Size 0.29 | 4247 Hz | 42 % |
| v0.1 defaults | 802 Hz | 3.1 % |

So yes, it is audible [hypothesis until a listening test]: the "cool" look and the original's
sound come from the same regime — very fast write, slow read, small span — which v0.1 cannot
reach (range) and does not start in (defaults). The exact pattern of the original is not
modelled yet (C5).

## 5. Proposals (for the user) — decided as R20–R23 in `redesign-t1.md`

- P1 Open the write pitch range like the original (−64 … 130), keep read at ±64.
- P2 Start (init state / first preset) in the interesting regime: write high, read low, small Size.
- P3 Optional **Raw** write mode: the unscaled −1 … 1 triangle of the original (C3); needs C4
  (clip or wrap) first.
- P4 Close the model gap (C5) before tuning further: user captures C4 (Audio Table properties),
  the Reaktor sample rate, and a short recording with simple settings (write ramp, In-Pitch 73,
  read −29.5, Size 0.08, LFOs off), plus render R-cases from `renders.md` if needed; then compare
  with `scripts/table_sim.py`.

## 6. Captures (user, 2026-11-24) and model update

Screenshots of the Reaktor structure and Properties (pasted into the conversation, not stored in
the repo) [measured: user captures C4, C6]:

| Item | Value |
|---|---|
| Audio Table `line view` and `2D view` (identical) | X **[0 … 1]** units, Y Index; size 1024 × 5; value range 0 … 1; **Interpolation None**; **Clip** (X/Y); Init Mode "Backup With Structure"; Samples/Sec 48 |
| Reaktor sample rate | **48 kHz** (toolbar `48000`, table Samples/Sec 48) |
| Ramp Osc (write osc, read › Osc) | Quality **Anti-Aliased Sync** (not Standard, not Hi-Res) |
| Tri/Par Symm (write osc, read › Osc) | no quality options |
| Structure | matches `signal-flow.md` §2 (Exp → F of Ramp Osc, P of Tri/Par Symm, G → Snc, `Qulity` switch hi / lo / =rea) |

**Model gap resolved [code: `scripts/table_sim.py`, cases 1–4]:** the first simulations added
Transpose (0.09) to the write pitch, i.e. 18101 Hz. The panel shows **18003.1 Hz** (= note
60 + 73 + 0.255). At 48 kHz that is 0.375065 · fs, a hair above 3/8: the per-sample write
positions form an 8-point lattice that drifts at only **≈ 3 Hz**. Each lattice point then sweeps
the span slowly while the read phase (≈ 48 Hz) is written, which gives **long sloped runs with
steps** — the look of the recording. At 18101 Hz the drift is ≈ 101 Hz and the table turns into
cell-to-cell zigzag. **A tenth of a semitone decides the pattern.**

Still [open]:

- Tri/Par Symm `W` semantics: read as "0 = symmetric" (so `lo Qu` 0.047 is a nearly symmetric
  triangle) the simulation shows the zigzag of the recording better than "peak position"
  [hypothesis: case 3].
- **Anti-Aliased Sync ramps** in the original (write "hi", read "hi") vs. our naive ramps: an
  anti-aliased ramp has ripple and overshoot near the wrap, so read positions and written values
  differ from a naive ramp, increasingly at high pitches; values beyond 0 … 1 are clipped by the
  table. Not modelled yet. Decided: offered as an option (redesign R24).
- The simple-settings recording (R23) remains useful to check `W` and the anti-aliased ramp.

Consequences for the port [hypothesis]: the interesting regimes sit at write rates **just off
simple fractions of the sample rate** (fs/2, fs/3, 3fs/8 …); the Write Pitch control needs very
fine resolution there, and the display could show the drift ("beat") against the nearest
fraction. Because the pattern is fs-relative, 44.1 vs 48 kHz Live sets will sound different
unless the device tunes relative to fs.
