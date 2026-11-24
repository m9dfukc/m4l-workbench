"""Table behaviour: Reaktor original (signal-flow.md formulas) vs. our v0.1 port.

Simulates the write/read pointers per sample for 5 voices and plots the table rows the way
Reaktor's line view shows them (x zoomed to the span, XR = size). Also prints simple sound
measures of the read-out signal y = 2*T[read] - 1.

usage: uv run --project tools python devices/aliasing/scripts/table_sim.py OUTDIR [CASES]

CASES: optional comma-separated case numbers (e.g. 7,8,9) to plot only those.

Model of the original from docs/signal-flow.md section 2 [code]; it does NOT yet reproduce
the Reaktor screen recording of 2026-11-24 (see docs/table-behaviour.md).
"""
import sys
import math
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = sys.argv[1]
NV, CELLS = 5, 1024


def hz(note):
    return 440.0 * 2 ** ((note - 69) / 12)


def tri_skew(p, w):
    """0..1..0 over phase p, peak at w (w in (0,1))."""
    w = min(max(w, 1e-6), 1 - 1e-6)
    return np.where(p < w, p / w, (1 - p) / (1 - w))


def simulate(cfg, fs=48000, secs=1.0):
    n = int(fs * secs)
    t = np.arange(n) / fs
    table = np.tile(np.arange(CELLS) / CELLS, (NV, 1)).astype(np.float32)
    span = cfg["size"]
    ys = np.zeros((NV, n))
    for v in range(NV):
        V = v + 1
        u = ((V - 0.5) - NV / 2) / ((NV - 1) / 2) * 0.5 + 0.5
        # read pitch (event rate in Reaktor: 400 Hz steps)
        fr_lfo = cfg["r_lfo_f"] * (cfg["r_lfo_f"] + u)
        lfo = cfg["r_lfo_amt"] ** 5 * np.sin(2 * np.pi * fr_lfo * t)
        if cfg.get("control_rate"):
            step = fs // 400
            lfo = np.repeat(lfo[::step], step)[:n]
        p_r = 60 + cfg["transpose"] + cfg["r_sprd"] * ((V - 0.5) / NV - 0.5) + cfg["r_pitch"] + cfg["r_fine"] + lfo
        p_w = np.full(n, 60 + cfg["w_pitch"] + cfg["w_fine"] + cfg["transpose"])
        ph_r = np.cumsum(hz(p_r) / fs) % 1.0
        ph_w = np.cumsum(hz(p_w) / fs) % 1.0
        phi_r = tri_skew(ph_r, 0.5) if cfg.get('r_tri') else ph_r   # read Qulity lo = tri 0..1
        if cfg["w_shape"] == "ramp":
            phi_w = ph_w
        else:
            tri01 = tri_skew(ph_w, cfg["w_sym"])
            phi_w = 2 * tri01 - 1 if cfg["w_unscaled"] else tri01   # Reaktor lo: -1..1, ours 0..1
        row = table[v]
        wx = phi_w * span * CELLS
        rx = phi_r * span * CELLS
        for i in range(n):
            x = wx[i]
            if cfg["xmode"] == "wrap":   # v0.1 DSP: wrap into the full row (negative -> row end)
                c = int(math.floor(x)) % CELLS
            elif cfg["xmode"] == "clip":
                c = min(max(int(math.floor(x)), 0), CELLS - 1)
            else:  # ours: wrap inside the span
                s = max(1, int(round(span * CELLS)))
                c = int(math.floor(x)) % s
            row[c] = phi_r[i]
            ys[v, i] = 2 * row[min(int(math.floor(rx[i])), CELLS - 1)] - 1
    return table, ys


def measures(ys, fs=48000):
    y = ys.sum(axis=0) / NV
    y = y[len(y) // 2:]
    spec = np.abs(np.fft.rfft(y * np.hanning(len(y)))) ** 2
    f = np.fft.rfftfreq(len(y), 1 / fs)
    cen = float((f * spec).sum() / spec.sum())
    hf = float(spec[f > 4000].sum() / spec.sum())
    steps = float(np.mean(np.abs(np.diff(ys, axis=1)) > 0.05))
    return cen, hf, steps


base = dict(transpose=0.0945, r_sprd=2.173, r_pitch=-29.5, r_fine=0.0, r_lfo_amt=1.0, r_lfo_f=0.378,
            w_fine=0.255, w_sym=0.047, size=0.262)
A = dict(base, w_pitch=73, w_shape="tri", w_unscaled=True, xmode="clip", control_rate=True)
D = dict(base, w_pitch=73, w_shape="tri", w_unscaled=False, xmode="span")
# Captured 2026-11-24 (C4/C6): Audio Table X [0..1], Clip, no interpolation; Reaktor at 48 kHz;
# the write Frq display reads 18003.1 Hz = note 133.255 = 60 + 73 + 0.255 (Transpose not in it).
R = dict(base, transpose=0.0, w_pitch=73, w_shape="tri", w_unscaled=True, xmode="clip", control_rate=True, fs=48000)
cases = [
    ("1 original model, 026 as captured (18003 Hz write, 48 kHz, clip), size 0.08, 4 s", dict(R, size=0.08, secs=4.0)),
    ("2 same, size 0.29, 4 s", dict(R, size=0.29, secs=4.0)),
    ("3 as 1 but Tri/Par Symm W read as -1..1 with 0 = symmetric (W 0.047 -> near-symmetric triangle), 4 s", dict(R, size=0.08, secs=4.0, w_sym=0.5236)),
    ("3b as 3, size 0.29", dict(R, size=0.29, secs=4.0, w_sym=0.5236)),
    ("4 same but write 18101 Hz (+0.1 st Transpose): drift 101 Hz instead of 3 Hz", dict(R, size=0.08, transpose=0.0945)),
    ("5 our v0.1 DSP: write triangle 0..1, pitch clamped to +64, size 0.08", dict(R, size=0.08, w_pitch=64, w_unscaled=False, xmode="span")),
    ("6 our v0.1 DSP with range opened (73) but triangle 0..1, size 0.08", dict(R, size=0.08, w_unscaled=False, xmode="span")),
]

# Init state candidates (redesign R21, 2026-11-25): write 71 + 0.217 st = 16004 Hz = fs/3 + 4 Hz at
# 48 kHz, read -30 st, spread 2.0, size 0.1, LFOs off, no transpose.
I = dict(transpose=0.0, r_sprd=2.0, r_pitch=-30.0, r_fine=0.0, r_lfo_amt=0.0, r_lfo_f=0.0,
         w_pitch=71, w_fine=0.217, w_sym=0.5, size=0.1, control_rate=False, secs=4.0)
cases += [
    ("7 init state, v0.1 Tri (-1..1 wrapped into the row)", dict(I, w_shape="tri", w_unscaled=True, xmode="wrap")),
    ("8 init state, v0.2 Tri (0..1, clip)", dict(I, w_shape="tri", w_unscaled=False, xmode="clip")),
    ("9 init state, v0.2 Tri +- (-1..1, clip = original)", dict(I, w_shape="tri", w_unscaled=True, xmode="clip")),
    ("10 init state, write Ramp (clip)", dict(I, w_shape="ramp", w_unscaled=False, xmode="clip")),
    ("11 init state at 44.1 kHz, v0.2 Tri (0..1, clip)", dict(I, w_shape="tri", w_unscaled=False, xmode="clip", fs=44100)),
]
if len(sys.argv) > 2:  # optional: only cases whose name starts with one of these numbers
    keep = set(sys.argv[2].split(","))
    cases = [c for c in cases if c[0].split(" ")[0] in keep]

fig, axes = plt.subplots(len(cases), 1, figsize=(7.5, 2.2 * len(cases)), facecolor="#b8b0c4")
for ax, (name, cfg) in zip(axes, cases):
    table, ys = simulate(cfg, fs=cfg.get('fs', 48000), secs=cfg.get('secs', 1.0))
    span = max(1, int(round(cfg["size"] * CELLS)))
    ax.set_facecolor("black")
    for v in range(NV):
        ax.plot(np.arange(span), table[v, :span] * 0.85 + (NV - 1 - v), color="white", lw=0.8)
    ax.set_xlim(0, span)
    ax.set_xticks([])
    ax.set_yticks([])
    cen, hf, steps = measures(ys, cfg.get('fs', 48000))
    ax.set_title(f"{name}\ncentroid {cen:.0f} Hz, energy >4 kHz {hf*100:.1f} %", fontsize=8, loc="left")
    print(f"{name}: centroid {cen:.0f} Hz, >4k {hf*100:.1f} %, jumps {steps*100:.1f} % of samples")
fig.tight_layout()
fig.savefig(f"{OUT}/table_sim.png", dpi=110)
print("wrote", f"{OUT}/table_sim.png")
