# aliasing — signal flow of the original

Derived from the parser's wiring dump and the structure screenshots (`inventory.md` has the
sources, module type table and control ranges). Evidence markers as in `inventory.md`; every
wire below is **[observed: parser]** unless marked otherwise.

Units: Reaktor pitch in semitones (MIDI note numbers, 69 = 440 Hz), `Exp` converts pitch → Hz;
levels in dB. "ev" = event (control rate, 400 Hz here), "au" = audio (48 kHz).

## 1. Overview

The whole instrument is **polyphonic with 5 voices**: every voice has its own pointers, its own
table row, Notch, SaturatorFilter and pan. Voices are summed only at the end, in
`from voice>LR` (two voice combiners). There is no MIDI pitch path; the instrument is a drone
started by the **activate** button.

```mermaid
flowchart LR
  ACT["activate (Button, ev)"] --> M["M (Merge)"]
  M -->|G| WOSC
  M -->|G| ROSC
  M --> VAL["Value: Trig"]
  C60["60"] --> VAL
  VAL -->|P = 60 on activate| WOSC
  VAL -->|P| NOTCH
  TR["Transpose ±12"] -->|P+−| WOSC & ROSC

  ROSC["read: read pointer φr, 0..1 (au)"] -->|rd| WOSC
  WOSC["write osc: write pointer φw (au)<br/>+ W = NOT(G)·active (ev)"]

  SIZE["size bar MX 0..1 (ev)"]
  ROSC --> XR1["X: φr · G · size"] -->|RX| AT
  M --> XR1
  SIZE --> XR1
  WOSC --> XW1["X: φw · size"] -->|WX| AT
  SIZE --> XW1
  ROSC -->|In (data = φr)| AT
  WOSC -->|W| AT
  SIZE -->|XR (display)| AT
  AT["AT view: Audio Table 1024×5<br/>row V−1, out = 2·v − 1"] --> NOTCH
  NOTCH["Notch: Peak EQ (P = Frq), bypass"] --> SAT
  SAT["SaturatorFilter: HP4+FM → Drv → Sat → LP4+FM → (1-pole HP) → Drv → Sat, bypass"] --> LR
  OUT["OUT −36..0 dB"] -->|Lvl| LR
  LR["from voice>LR: Stereo Mixer per voice, Σ voices"] --> SW["Switch2x2 I/O"] --> O["Out L/R"]
```

## 2. Per voice, formulas

`V` = voice index (1..5), `Vcs` = voice count (5) from Voice Info.
`pos(V) = ((V − 0.5) − Vcs/2) / ((Vcs − 1)/2)` → −1..1 across the voices (voice0-1 macro,
output "-1..1"); `u(V) = (pos + 1)/2` → 0..1 (output "0..1").

### Write pointer (`write osc`)

```
LFO_w  = 60 + Amt_w^5 · sin(2π ∫ F_w dt)        F_w = Freq_w · (Freq_w + u(V))   [ev, CR]
STEREO = P + sprd_w · pos(V)                    P = 60, one event on activate    [ev]
P_w    = Merge(STEREO, LFO_w) + In-Pitch + fine_w + Transpose                    [ev]
ramp_w = RampOsc(F = Exp(P_w), A = 1, Snc = G)       0..1                        [au]
tri_w  = TriParSymm(P = P_w, A = 1, W = lo Qu).Tri   −1..1 (not rescaled!)       [au]
φw     = Qulity_w ∈ { hi: ramp_w, lo: tri_w, =read: φr }
W      = NOT(G).Not · active                                                      [ev]
```

- The **Merge** passes whichever input fired last. The LFO fires every control tick, so after
  activation `P_w` follows the LFO branch and the stereo branch (with the hidden write `sprd`) is
  overwritten within one tick [inference; check in render R3]. Reproducing this exactly means:
  the write spread is effectively inactive.
- The Frq display shows `Exp(P_w)` of the **last** voice via From Voice (Vcs).

### Read pointer (`read`)

```
LFO_r  = Amt_r^5 · sin(2π ∫ F_r dt)             F_r = Freq_r · (Freq_r + u(V))   [ev, CR]
SPREAD = 60 + sprd_r · ((V − 0.5)/Vcs − 0.5)                                     [ev]
P_r    = Transpose + SPREAD + out Pitch + fine_r + LFO_r                         [ev]
ramp_r = RampOsc(F = Exp(P_r), A = 1, Snc = G)                0..1               [au]
tri_r  = 0.5 · TriParSymm(P = P_r, A = 1, W = dir).Tri + 0.5  0..1               [au]
φr     = Qulity_r ∈ { hi: ramp_r, lo: tri_r }
```

Note the two spread formulas differ: read uses `(V−0.5)/Vcs − 0.5` (±0.4 for 5 voices), the
(dead) write spread uses `pos(V)` (±1).

### Table (`AT view` → `line view` / `2D view`)

```
RX = φr · G · size        WX = φw · size        RY = WY = V − 1      YR = Vcs
In = φr (the read pointer itself is the written data)
W  = NOT(G) · active       XO = 0, XR = size (display zoom only)
y  = 2 · Table.Out − 1
```

With `G = 0` (not activated) the read position is 0. With `size` < 1 both pointers cover only
the first part of the row. Whether RX/WX are in [0…1] units (so 1.0 = whole row) or in cell
indices is the key open table property [open → capture C4]; the size bar's 0..1 range makes
[0…1] units very likely [inference].

### Notch

```
Peak EQ: P = Frq (semitones), Res = S(Reso), B = Boost (dB), In = y
out = on ? PeakEQ : y          (KeyTrack/K folw: computed, output unused)
```

### SaturatorFilter

```
hp   = 4PoleHP.HP4(P = /HP, F = FAmt_hp · y, Res = S(Reso_hp), In = y)
s1   = Saturator(Mixer(hp, Lvl = Drv dB))
lp   = 4PoleFilter.LP4(P = LP\, F = FAmt_lp · y, Res = S(Reso_lp), In = s1)
dc   = −DC ? OnePole(P unconnected).HP(lp) : lp
s2   = Saturator(Mixer(dc, Lvl = Drv dB))
out  = on ? s2 : y
```

Both FM inputs take the **unfiltered table output y**, scaled by FAmt (Hz per unit) [observed:
parser + 15.54.50]. The same Drv feeds both mixers.

### Output (`from voice>LR`, `Switch2x2 I/O`)

```
Lvl  = OUT + Log(1/Vcs)        (≈ −14 dB at 5 voices if Log is 20·log10 [open])
Pan  = stereo · pos(V)
(L, R) = StereoMixer(Lvl, Pan, In = out);  Σ over voices (voice combiners)
Switch2x2: passes L/R (the L2/R2 "Beat Loop" inputs are unconnected)
```

## 3. Rate crossings (event → audio)

Every event value that enters an audio input is held until the next event (zero-order hold at
the control rate, 400 Hz = every 120 samples at 48 kHz) [sourced: fundamentals note §3].

| Crossing | Effect |
|---|---|
| `Exp(P_w)`, `Exp(P_r)` → Ramp Osc **F** | pointer frequency steps at 400 Hz while the LFO moves; the pointer phase itself is per sample |
| `P_w`, `P_r` → Tri/Par Symm **P** | same |
| `lo Qu`, `dir` → Tri/Par Symm **W** | stepped symmetry |
| `G` → Ramp **Snc**, `G` → RX multiply | sync on activate; RX gated |
| `size` → RX/WX multiply | stepped span |
| `W` → table write enable | write gate |
| knobs → filter P, Res (via S), mixer Lvl (Drv), stereo mixer Lvl/Pan | parameter steps; FM inputs F are audio |

## 4. Table read/write pair

| Side | Position | Rate | Source |
|---|---|---|---|
| Write | WX = φw · size | audio | write pointer (Ramp / Tri −1..1 / φr) |
| Write data | In = φr | audio | read pointer |
| Write enable | W = NOT(G)·active | event | gate + button |
| Read | RX = φr · G · size | audio | read pointer |
| Row | RY = WY = V − 1 | event (constant per voice) | Voice Info |

Open semantics [open → capture C4, renders R1/R4]: X units, clip vs wrap (matters for the
write Tri's negative half, −1..0), read interpolation, write rounding (manual: floor), value
clipping to 0..1 (manual), and whether a read in the same sample sees the value written in that
sample.

Two tables are written identically; only table #1 stores initial data (#2 starts empty), and
the AT view switch picks which one is heard. If the switch's saved position selects #2, the
first write sweep starts from an empty row [inference].

## 5. Feedback and processing order

- **No audio feedback loops** in the wiring: the table is the only memory between the pointers
  and the output; nothing feeds back into the pointers [observed: parser]. So no automatic "Z"
  one-sample delays are expected on the audio path [inference]. The only loop is an event loop in
  `size bar` (XY MX → S → + → XY X2), a UI behaviour.
- Order inside the Audio Table module (write then read, or read then write) is not visible in the
  structure [open → C6 "Show Module Sorting" does not answer it; render R1 does].

## 6. Port-relevant summary

- Pointer pitch = event at 400 Hz, pointer phase = audio at 48 kHz.
- The table stores pointer phase, not audio; the sound is `2·T[φr] − 1` with `T` built from
  earlier `φr` values written at `φw`.
- Everything after the table is per voice (5 × Notch, 5 × SaturatorFilter), then pan and sum.
