# aliasing — which write and read shapes are worth having (2026-11-25)

> Measured on the **v0.3 DSP** (8 write shapes, Read 1-Way/2-Way, Drift; `aliasing.gendsp` of commit
> 9c23f87). v0.3b implemented the verdicts (D34: Ramp, Tri, Pulsar, Spike, Noise renumbered 0–4; D35:
> Read Tri always 2-Way), so the scripts in `test/shapes/` run only against an export of that older
> `.gendsp`; the shape indices below are v0.3's.

Question (user, 2026-11-25): v0.3 has **8 write shapes** (Ramp, Tri, Tri ±, Sine, Pulse, Pulsar,
Spike, Noise, `v0.3-design.md` §2.1), each with a Sym parameter, and **2 read shapes** (Ramp, Tri)
with Smooth and 1-Way/2-Way. Are 8 write shapes too many? Which give clearly different results,
which duplicate another shape (perhaps at some Sym value), and does read need more or fewer?

Evidence markers as in `CLAUDE.md`. Unless marked otherwise, every number is
[measured: `devices/aliasing/test/shapes/run.sh` → `build/aliasing/shapes/grid_report.md`,
`checks_report.md`, `read_report.md`, 2026-11-25]: offline renders of the gen~ C++ export, measured
spectrally. **Nothing here was listened to**; "musically useful" is [hypothesis] until the user
hears the audition files (§7).

## 0. Answer

| Write shape | Verdict | Main evidence (excess over the floor, ensemble LSD / band, dB; §1) |
|---|---|---|
| Ramp | **keep** | farthest from the triangle family: 2.7–7.4 / 4.6–7.5 to every other shape at Sym 0 |
| Tri | **keep** | init default (D1), the original's "lo" mode rescaled; its Sym +1 *is* Ramp and Spike +1 *is* Tri (bit-identical) |
| Tri ± | **drop → Spike Sym 0** (Sym +1 → Pulsar Sym 0) | Tri ± 0 vs Spike 0: 0.4 / 0.5 (a Read-Spread nudge is 0.9 / 0.5); every Tri ± variant has a kept neighbour within 1.4 |
| Sine | **drop → Ramp Sym −0.5** (Sym ±1), Tri/Spike otherwise | Sine +1 vs Ramp −0.5: 0.8 / 1.5; Sine 0 vs Tri 0: 1.7 / 2.4; all Sine variants within 1.7 of a kept one |
| Pulse | **drop** (it is Freeze + 2 cells) | writes 2 cells per row: 98–100 % of the span never written; on a filled table 0.8–3.4 dB from Freeze |
| Pulsar | **keep** | widest Sym range (Sym −1 vs +1: 5.5 LSD): Duty = how much of the cycle writes; +1 *is* Ramp |
| Spike | **keep** (or Tri ± instead, §5) | Width range 3.9; −1 ≈ Pulsar −1 (0.2); +1 *is* Tri |
| Noise | **keep** | the only shape no other shape covers: ≥ 2.3 / ≥ 3.6 from the nearest variant of any other shape (mean over its Sym values) |

Read: **keep Ramp and Tri, drop the 1-Way/2-Way switch** (Tri = 2-Way): Read Tri 1-Way is
bit-identical to Read Ramp whenever Ramp AA is off (the default). **Add no read shape**: a Sine read
lands next to Tri 2-Way (1.6), a stepped read is Size at a few cells (1.8), a Pulse read collapses the
table to two cells (§4).

With the five kept shapes every one of the 35 non-Pulse variants has a kept neighbour at mean excess
0.33 dB, max 1.66 dB — less than a Sym +0.1 nudge on Ramp (1.72) (§3.7).

## 1. Method

- **Renderer**: `test/host/render.cpp` built into `build/aliasing/shapes/bin/` against the Max 9.2.1
  export `build/aliasing/export/cpp` (17:47; `aliasing.gendsp` 16:57, so the export is current).
  A second renderer from a patched copy of the export (`shapes_study.py xpatch`, only `rd` changed)
  provides hypothetical read shapes; it never touches the device's DSP.
- **Base state**: Width 0 (L = R), Band, Drive and limiter switched off (exact bypasses, D17),
  resonator off, matrix all 0, Read Spread 2 (default), Ramp AA off, 48 kHz, voices from the identity
  table (fresh load).
- **Grid**: 8 shapes × Sym {−1, −0.5, 0, +0.5, +1} × 5 pitch situations × read {Ramp, Tri 2-Way} ×
  Size {1, 0.1} = 800 cells, plus Clean and Freeze per situation and 8 calibration moves (§3.1).

| Pitch | Write | Read | Regime |
|---|---|---|---|
| P1 unison | 0 st (261.6 Hz) | 0 st | the v0.3 init state (D1) |
| P2 alias | 71 + 0.217 st (16004 Hz ≈ fs/3 + 4 Hz) | −30 st (46 Hz) | the v0.2 init sound (R21) |
| P3 slow | −12 st (130.8 Hz) | 0 st | write an octave below read |
| P4 fast | +24 st (1047 Hz) | +7 st (392 Hz) | write above read |
| P5 scan | −36 st (32.7 Hz) | 0 st | the head scans the span at a sub-audio rate |

- **Measures**: mono, skip 0.5 s, analysis 0.5–2.5 s. Spectra = m4l-analyze's Welch PSD (nperseg 8192,
  f > 20 Hz) of the RMS-normalised signal, floored at peak − 90 dB; distance = log-spectral distance
  (LSD) and the same on 1/3-octave bands ("band"). Features: level, crest, centroid, flatness, energy
  > 4 kHz. Table dumps at 2.5 and 4.5 s: share of span cells never written, change between dumps.
- **Why ensembles.** One render is chaotic in its tuning: Read Fine +0.01 st changes a single render's
  LSD by 3.8 dB, a Sym +0.1 nudge by 1.4–5.2 dB, while shape-to-shape distances are 4–9 dB. So each
  cell is rendered 6 times with Transpose 0, 0.004 … 0.02 st (both pointers), split into even and odd
  members. **floor** = LSD between the two halves of the same setting (1.1–5.2 dB, mean 2.7);
  **distance** = LSD between halves of two settings; **excess** = distance − mean floor, per situation,
  then averaged. Identical settings give excess 0 (the bit-identical pairs of §3.2 do).

## 2. What the shapes write [code: `gen/aliasing.genexpr` lines 595–628]

The written value is always the read phase `rd`; the shape only sets *where* (0..1 of the span).

- **Ramp** p^(4^−s); **Tri** skewed 0..1..0 (s = +1: rising ramp = Ramp 0; s = −1: falling ramp).
- **Tri ±** = 2·Tri − 1 clipped: half of every cycle parks on cell 0, the other half is an up-and-back
  sweep lasting half a cycle, peaked by Skew — i.e. a Spike of width 0.5 that writes cell 0 instead of
  resting.
- **Sine**: the Tri path with cosine speed (slow at the span ends, π/2 × faster in the middle).
- **Pulse**: only two positions, cell 0 and the span's end; every other cell keeps its value.
- **Pulsar** / **Spike**: a ramp / up-and-back over Duty / Width, then no write; at +1 they are Ramp 0 /
  Tri 0.
- **Noise**: a new random target each write cycle; Sym −1 holds one cell per cycle, any higher Sym
  sweeps a random segment.

## 3. Results (write)

### 3.1 Scale: what a small knob move costs (excess LSD / band)

| Move | excess | | Move | excess |
|---|---|---|---|---|
| Ramp Sym 0 → +0.1 | 1.72 / 1.60 | | Spike Sym 0 → +0.1 | 1.33 / 1.63 |
| Tri Sym 0 → +0.1 | 1.08 / 1.70 | | Noise Sym 0 → +0.1 | 0.18 / 0.15 |
| Sine Sym 0 → +0.1 | 0.53 / 1.07 | | Read Fine +0.01 st | 0.51 / 1.06 |
| Pulsar Sym 0 → +0.1 | 1.07 / 1.12 | | Read Spread 2 → 2.5 | 0.88 / 0.51 |

Reading used below: **≤ 1 dB = near-duplicate** (like a Read Spread or Fine nudge), **≤ ~2 dB =
close** (like a Sym +0.1 nudge), **> 2.5 dB with band > 3 dB = distinct**.

### 3.2 Exact duplicates [measured: `checks_report.md`]

Bit-identical through all five pitch situations, Size 1 and 0.1, read Ramp and Tri 2-Way:
**Tri Sym +1 = Ramp Sym 0**, **Pulsar Sym +1 = Ramp Sym 0**, **Spike Sym +1 = Tri Sym 0**.
With Ramp AA on, Ramp would differ from Tri +1 / Pulsar +1 (only Ramp uses the AA phase) [code].

### 3.3 Sym 0: excess, LSD above the diagonal, band below

| | Ramp | Tri | Tri ± | Sine | Pulse | Pulsar | Spike | Noise |
|---|---|---|---|---|---|---|---|---|
| Ramp | | 3.7 | 4.9 | 5.2 | 12.7 | 2.7 | 5.2 | 7.4 |
| Tri | 6.2 | | 2.0 | 1.7 | 13.5 | 1.7 | 2.3 | 5.4 |
| Tri ± | 7.2 | 3.5 | | 2.0 | 13.1 | 3.0 | **0.4** | 4.5 |
| Sine | 6.9 | 2.4 | 2.9 | | 14.7 | 3.2 | 2.2 | 4.9 |
| Pulse | 12.7 | 13.3 | 12.9 | 13.6 | | 14.2 | 13.6 | 13.0 |
| Pulsar | 4.6 | 3.1 | 4.2 | 3.9 | 13.1 | | 3.1 | 6.3 |
| Spike | 7.5 | 3.9 | **0.5** | 3.2 | 13.3 | 4.5 | | 5.0 |
| Noise | 7.0 | 6.4 | 5.8 | 5.9 | 12.2 | 6.3 | 6.1 | |

Spectral features at Sym 0 (situation mean): centroid / flatness — Ramp 4245 Hz / 0.14, Tri 3885 /
0.22, Tri ± 4610 / 0.28, Sine 4881 / 0.39, Pulsar 3824 / 0.17, Spike 4817 / 0.29, **Noise 6333 / 0.49**,
Pulse 3194 / 0.18 at −26.9 dB (others ≈ −20.5 dB); Clean / Freeze 511 Hz / 0.005.

### 3.4 Near-duplicates and their merge targets (excess LSD / band)

| Dropped variant | Nearest kept variant | Excess | Max over situations |
|---|---|---|---|
| Tri ± −1 / −0.5 / 0 / +0.5 / +1 | Pulsar 0 / Spike +0.5 / **Spike 0** / Spike −0.5 / **Pulsar 0** | 1.4, 1.2, **0.4**, 1.1, **0.8** (band 1.6, 2.1, 0.5, 2.4, 0.6) | 3.0–7.7 |
| Sine −1 / −0.5 / 0 / +0.5 / +1 | Ramp −0.5 / Tri −0.5 / Spike +0.5 / Tri +0.5 / **Ramp −0.5** | 1.4, 1.5, 1.4, 1.7, **0.8** (band 2.5, 1.8, 1.9, 2.0, 1.5) | 2.9–6.7 |

The excess of a merge pair exceeds 2 dB in 1–6 of the 20 situations, always at Size 0.1 with write
at or below read (P1, P3, P5), mostly with read Tri — the regime where shapes matter at all (§3.6);
there a merge may be audible [open: audition]. Elsewhere the merge targets sit at the floor.

Further pairs: **Pulsar −1 ≈ Spike −1** 0.2 / 0.3 (both write 2 % of the cycle); Tri −1 (falling
ramp) vs Ramp 0: 1.1 / 1.2 (direction matters little); Sine 0 vs Tri 0: 1.7 / 2.4; Noise 0 vs its
nearest other shape (Ramp +1): 2.5 / 4.3.

### 3.5 Pulse is Freeze with two stuck cells

- In every situation 98 % (Size 0.1) to 100 % (Size 1) of the span is never written; the table
  changes by ≤ 0.012 between 2.5 and 4.5 s (the other shapes: 0.21–0.42).
- Its large distance to everything (12–15 dB) is an artefact of the fresh identity table: at Size 0.1
  Freeze plays a quiet saw (−41 dB) and Pulse adds two full-range cells (clicks at −31…−34 dB).
- On a table filled first (1 s of Tri in P2, then the variant) Pulse rewrites 0–2 % of the span and
  stays 0.8–3.4 dB (single render) from Freeze, against 6.0–12.6 for Noise −1 and 9.1–13.2 for Tri
  [measured: `checks_report.md`, prefilled table].

### 3.6 When the shape matters at all

Mean excess between the 7 non-Pulse shapes at Sym 0 (LSD / band): **P1 5.1 / 6.1, P3 4.8 / 6.9,
P5 5.0 / 6.5**, but **P2 2.3 / 2.8 and P4 1.2 / 2.0**. With a fast write pointer each write cycle is
a few samples, so the shape is sampled at a few points and most pairs fall to excess ≈ 0 (P2: only
Noise stands out, 6.8–12.9). Small spans separate shapes more (P1, read Ramp / Tri: Size 0.1 4.9 /
11.9 vs Size 1 1.5 / 1.9). So the shape choice matters where the write pointer runs **at or below the
read rate over a small span** — which includes the v0.3 init state (P1, Size 0.1) — and hardly at all
in the v0.2 "alias" regime.

### 3.7 Sym ranges (within-shape excess, LSD)

- **Pulsar** −1 vs +1: 5.5; **Spike** 3.9: the widest ranges (Duty / Width = writing density).
- **Ramp**: any curve vs 0: 3.2–5.5; −1 vs +1: 2.2.
- **Skew is mirror-symmetric in sound**: Tri −0.5 vs +0.5 0.4, Sine 0.5, Tri ± 0.8; at ±1: Tri 1.1,
  Sine 0.9, Tri ± 0.8. Half of each Skew range repeats the other half.
- **Noise Smooth** acts mostly at its low end: −1 vs −0.5 2.4, −0.5 vs +1 2.0, 0 vs +0.5 0.6
  (a +0.1 nudge: 0.18). Only Sym −1 (one cell per write cycle) leaves parts of the table untouched for
  seconds: at Size 1, 32 % (P1), 57 % (P3), 87 % (P5) of the span unwritten after 4.5 s; on a filled
  table it rewrites 12–51 % in 2.5 s where Noise +1 and Tri rewrite 97–100 % — a slow "crumbling".
- **Pulse** Width: 0.5–2.8, moot.

### 3.8 Subsets (excess from every non-Pulse variant to the nearest variant of the subset)

| Set | LSD mean / max | Band mean / max |
|---|---|---|
| all 7 non-Pulse | 0 / 0 | 0 / 0 |
| Ramp, Tri, Sine, Pulsar, Spike, Noise | 0.14 / 1.42 | 0.20 / 2.17 |
| **Ramp, Tri, Pulsar, Spike, Noise** (recommended) | **0.33 / 1.66** | **0.48 / 2.49** |
| Ramp, Tri, Tri ±, Pulsar, Noise (port variant, §5) | 0.27 / 1.57 | 0.44 / 2.49 |
| Ramp, Sine, Pulsar, Spike, Noise (best 5 by number) | 0.26 / 1.63 | 0.34 / 2.17 |
| Ramp, Tri, Spike, Noise | 0.51 / 2.11 | 0.77 / 2.84 |
| Ramp, Tri, Pulsar, Noise | 0.55 / 2.18 | 0.84 / 3.33 |
| Ramp, Spike, Noise (best 3) | 0.65 / 2.11 | 0.98 / 2.84 |

Below five shapes the worst variant moves past "close" (max > 2 dB LSD, > 2.8 dB band); above five
the gain is small. Noise is in every good set.

## 4. Read side [measured: `read_report.md`]

- **Tri 1-Way = Ramp**: bit-identical in all five situations with all 8 write shapes when Ramp AA is
  off (`skewtri(p, 1) = p` for p < 1, [code: genexpr lines 38–42]). With Ramp AA on they differ (peak difference
  −11.5…−16.9 dBFS), but only because Tri stays naive — the Ramp AA switch already offers that.
- Ramp vs Tri 2-Way: excess 2.7 — a real choice, keep both.
- Hypothetical shapes (patched renderer, 10 situations × write Ramp, Tri, Sine, Noise):
  **Sine 2-Way** read vs Tri 2-Way 1.6 (vs Ramp 3.0): close to Tri; **Step 8** (quantised read) vs Ramp
  at a span of 8 cells (Size 0.0078) 1.8: reachable with Size; **Pulse** read ≥ 6.0 from everything
  (centroid 539 Hz, flatness 0.015): it reads two cells, so the output is a square wave whose polarity
  flips as the write head crosses them — none of the table errors that are the device's sound
  [hypothesis on its musical value].
- Already reachable: Smooth (Ramp 2.4, Tri 1.3 from the plain read); Read Osc → Size +33 % curves the
  read path (2.4 from Ramp) and pulls Ramp and Tri together (1.3 between them); Read Osc → Read Pitch
  +50 % 1.8 from Ramp.

## 5. Recommendation details

1. **Write shapes: Ramp, Tri, Pulsar, Spike, Noise** (§0). For the 2 × 4 icon grid this is one row of
   5, or 2 × 3 with one empty cell.
2. **Spike or Tri ±** is a free choice — at Sym 0 they are the same sound (0.4 / 0.5), and the sets
   with either score alike (0.33 vs 0.27). Spike pairs with Pulsar (Width = density, rests like D29);
   Tri ± is the original's unscaled "lo" mode (R22) and helps an A/B against Reaktor. Claude's lean:
   Spike, and use Spike 0 as the Tri ± stand-in for A/B [hypothesis until the user listens].
3. **Skew** could become unipolar (0 = symmetric … 1 = full ramp) without losing sound (§3.7)
   [hypothesis; the display would lose the mirror image]. Not required.
4. **Noise Smooth**: most of its effect sits between −1 and −0.5; a response curve that spreads that
   region, or a different parameter, would make the knob more useful [hypothesis].
5. **Read**: Ramp | Tri (2-Way), no 1-Way/2-Way switch, no new read shapes; Smooth stays.
6. Presets (v0.4) that show the shapes off should use slow write, small Size (§3.6).

## 6. Not checked / open

- **Listening** — all of this is spectral; whether e.g. Sine's softer, noisier triangle is worth a slot
  is a musical call [open: user, audition files §7].
- Sym under modulation (matrix → Write Sym), Sync-mode pointers, write rates below 32.7 Hz (where
  shapes become rhythmic scans; P5 is the slowest case), Ramp AA on, 44.1 kHz, Tone sections on,
  other Read Spread values.
- Excess subtracts the mean of two floors; where floors differ a lot (Noise 1.2 vs Spike −1 4.7) it can
  understate a difference — the band excess is the cross-check.
- How the display draws the dropped shapes (visual value) and the Reaktor A/B for Tri ± vs Spike 0.

## 7. Files

- Scripts: `test/shapes/run.sh` (build both renderers, run the steps), `test/shapes/shapes_study.py`
  (grid, checks, report, read, audition, xpatch); all steps 3 min 42 s on this machine (exit 0).
- Results (gitignored): `build/aliasing/shapes/grid.npz`, `grid_report.md`, `checks_report.md`,
  `read_report.md`.
- Audition files (`build/aliasing/shapes/audition/`, 7.5 s each: P1…P5 × 1.5 s, Size 0.1, read Ramp,
  default tone, peak −18 dBFS; listen with the limiter rule in `CLAUDE.md`): `w0_ramp_sym0`,
  `w1_tri_sym0`, `w2_tripm_sym0`, `w3_sine_sym0`, `w4_pulse_sym0`, `w5_pulsar_sym0`, `w6_spike_sym0`,
  `w7_noise_sym0`, `w7_noise_symm1`; merge pairs `w2_tripm_symp1` vs `w5_pulsar_sym0`,
  `w3_sine_symp1` vs `w0_ramp_symm05`, `w2_tripm_sym0` vs `w6_spike_sym0`; Pulse on a filled table
  `w4_pulse_after_tri` vs `freeze_after_tri` (6 s, should match after 1.5 s).
