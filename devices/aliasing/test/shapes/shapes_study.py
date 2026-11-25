"""Write/read shape study of the aliasing gen~ export (devices/aliasing/docs/shapes-study.md).

Renders a grid of write shapes x Sym x pitch situations x read shape x Size with the host
renderer (devices/aliasing/test/host/render.cpp, built by run.sh next to this file), measures
spectral features, table metrics and pairwise spectral distances, and prints the result tables
that the study doc quotes. Renders and intermediates stay in OUT (build/aliasing/shapes/);
WAVs of the grid are analysed and deleted at once. Never plays audio.

  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py grid     RENDER OUT
  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py checks   RENDER OUT
  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py report   OUT/grid.npz
  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py read     RENDER XRENDER OUT
  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py audition RENDER OUT [NAME:SHAPE:SYM ...]
  uv run --project tools python devices/aliasing/test/shapes/shapes_study.py xpatch   EXPORT_CPP OUT_CPP

grid      the write-shape grid -> OUT/grid.npz, OUT/grid_report.md; then `checks`
checks    exact-duplicate null tests, prefilled-table check -> OUT/checks_report.md
report    rewrite OUT/grid_report.md from OUT/grid.npz (no rendering)
read      read-side checks (Tri 1-Way vs Ramp null test; hypothetical read shapes from the patched
          renderer XRENDER, env ALIASING_XREAD; Smooth, Read Osc) -> OUT/read_report.md
audition  one file per write shape (5 pitch situations x 1.5 s) -> OUT/audition/*.wav, peak -18 dBFS
xpatch    copy of the export with experimental read shapes (built by run.sh; never the device's DSP)

Analysis: mono sum, skip 0.5 s, W1 = 0.5-2.5 s. Spectra = m4l-analyze's Welch PSD (nperseg 8192,
f > 20 Hz) of the RMS-normalised signal, floored at its peak - 90 dB; distance = RMS dB difference
(log-spectral distance, LSD) and the same on 1/3-octave bands. The device is chaotic in its tuning
(0.01 st of Fine changes a single render's spectrum as much as a shape change), so shapes are compared
as tuning ensembles: 6 renders per cell with Transpose 0, 0.004 ... 0.02 st (both pointers), split
into the even and odd members; distance(a, b) = mean of LSD(a_even, b_odd) and LSD(a_odd, b_even),
floor(a) = LSD(a_even, a_odd) (what two equivalent ensembles of the same setting differ by);
excess(a, b) = distance - (floor(a) + floor(b)) / 2, per situation, then averaged. Identical
settings give excess 0; the calibration moves (Sym +0.1, Read Fine +0.01 st, Read Spread +0.5)
give the scale of "a small knob nudge".
"""

from __future__ import annotations

import itertools
import os
import re
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np
import soundfile as sf

from m4l_tools.analyze import psd_db

SR = 48000
N, NV = 1024, 5
SHAPES = ["Ramp", "Tri", "Tri ±", "Sine", "Pulse", "Pulsar", "Spike", "Noise"]
SYMS = [-1.0, -0.5, 0.0, 0.5, 1.0]
NS = len(SHAPES) * len(SYMS)          # the shape x Sym variants come first in variants()
# Pitch situations: (label, write pitch, write fine, read pitch)
PITCH = [
    ("P1 unison", 0, 0.0, 0),        # init state (D1)
    ("P2 alias", 71, 0.217, -30),     # v0.2 init sound (R21): write fs/3 + 4 Hz, read 46 Hz
    ("P3 slow", -12, 0.0, 0),         # write an octave below read
    ("P4 fast", 24, 0.0, 7),          # write 1047 Hz, read 392 Hz
    ("P5 scan", -36, 0.0, 0),         # write 32.7 Hz: the head scans the span at a sub-audio rate
]
READS = [("ramp", ["rshape=0"]), ("tri2", ["rshape=1", "rdir=1"])]
SIZES = [1.0, 0.1]
# Analysis-friendly base: all voices centred (L = R), Band / Drive / limiter bypassed exactly (D17),
# resonator off (default), no modulation (matrix all 0, default). Read Spread stays at its default 2.
BASE = ["width=0", "bandon=0", "drvon=0", "limon=0"]
SKIP, W1, W2, TOTAL = 0.5, 2.5, 4.5, 4.5
FLOOR_DB = 90.0
NPERSEG = 8192
JITTER = [0.0, 0.004, 0.008, 0.012, 0.016, 0.02]   # st via Transpose; even / odd members = the two halves
# The set the study recommends (devices/aliasing/docs/shapes-study.md); the report maps the rest onto it
KEEP = ["Ramp", "Tri", "Pulsar", "Spike", "Noise"]
# Calibration variants: small knob moves from a Sym 0 variant (label, base label, sets)
CAL = [(f"cal {SHAPES[k]} +0.1", f"{SHAPES[k]} +0.0", [f"wshape={k}", "wsym=0.1", "wactive=1"]) for k in (0, 1, 3, 5, 6, 7)]
CAL += [("cal Tri +0.0 Read Fine +0.01", "Tri +0.0", ["wshape=1", "wsym=0", "wactive=1", "rfine=0.01"]),
        ("cal Tri +0.0 Read Spread 2.5", "Tri +0.0", ["wshape=1", "wsym=0", "wactive=1", "rspread=2.5"])]
# Pairs whose per-situation distances the report lists (variant labels as in variants())
PAIRS = [("Tri ± +0.0", "Spike +0.0"), ("Tri ± +1.0", "Pulsar +0.0"), ("Tri ± -1.0", "Tri +0.0"),
         ("Ramp -0.5", "Sine +1.0"), ("Sine +0.0", "Tri +0.0"), ("Sine +0.0", "Ramp -1.0"),
         ("Pulsar -1.0", "Spike -1.0"), ("Spike +0.0", "Pulsar +0.0"), ("Tri -1.0", "Ramp +0.0"),
         ("Tri -0.5", "Tri +0.5"), ("Sine -0.5", "Sine +0.5"), ("Tri ± -0.5", "Tri ± +0.5"),
         ("Ramp -1.0", "Ramp +1.0"), ("Noise +0.0", "Ramp +1.0"), ("Noise -1.0", "Noise -0.5"),
         ("Noise -0.5", "Noise +1.0"), ("Pulse +0.0", "Freeze"), ("Pulse -1.0", "Pulse +1.0")]
# Exact duplicates suspected from the formulas (sample-exact null test through all situations)
NULLS = [("Ramp Sym 0", ["wshape=0", "wsym=0"], "Tri Sym +1", ["wshape=1", "wsym=1"]),
         ("Ramp Sym 0", ["wshape=0", "wsym=0"], "Pulsar Sym +1", ["wshape=5", "wsym=1"]),
         ("Tri Sym 0", ["wshape=1", "wsym=0"], "Spike Sym +1", ["wshape=6", "wsym=1"])]


# ---------------------------------------------------------------- rendering

def render(binary: str, out: str, sets: list[str], seconds: float, table: str | None = None,
           ats: list[tuple[float, str]] | None = None, env: dict | None = None) -> None:
    cmd = [binary, out, "--seconds", str(seconds), "--sr", str(SR)]
    for s in sets:
        cmd += ["--set", s]
    for t, s in ats or []:
        cmd += ["--at", str(t), s]
    if table:
        cmd += ["--table", table]
    subprocess.run(cmd, check=True, env={**os.environ, **(env or {})})


def situations():
    for (pl, wp, wf, rp), (rl, rsets), sz in itertools.product(PITCH, READS, SIZES):
        label = f"{pl.split()[0]}-{rl}-s{sz:g}"
        sets = [f"wpitch={wp}", f"wfine={wf}", f"rpitch={rp}", f"size={sz}", *rsets]
        yield label, sz, sets


def variants():
    """(label, sets): 40 shape x Sym variants, the two write-state references, the calibration moves."""
    out = []
    for k, name in enumerate(SHAPES):
        for s in SYMS:
            out.append((f"{name} {s:+.1f}", [f"wshape={k}", f"wsym={s}", "wactive=1"]))
    out.append(("Clean", ["wactive=2"]))
    out.append(("Freeze", ["wactive=0"]))
    out += [(lab, sets) for lab, _, sets in CAL]
    return out


# ---------------------------------------------------------------- analysis

THIRD = 1000.0 * 2.0 ** (np.arange(-14, 14) / 3.0)   # 1/3-octave centres 40 Hz .. 20 kHz
TLO, THI = THIRD * 2 ** (-1 / 6), THIRD * 2 ** (1 / 6)


def norm_pow(x: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Welch power spectrum (linear) of the RMS-normalised mono signal (m4l-analyze's psd_db)."""
    m = x.mean(axis=1, keepdims=True)
    m = m / max(float(np.sqrt(np.mean(m ** 2))), 1e-12)
    f, pdb = psd_db(m, SR, NPERSEG)
    return f, 10 ** (pdb / 10)


def floor_db(f: np.ndarray, p: np.ndarray) -> np.ndarray:
    pdb = 10 * np.log10(np.maximum(p, 1e-30))
    return np.maximum(pdb, pdb[f > 20].max() - FLOOR_DB)


def bands_db(f: np.ndarray, pdb: np.ndarray) -> np.ndarray:
    p = 10 ** (pdb / 10)
    e = np.array([p[(f >= a) & (f < b)].sum() for a, b in zip(TLO, THI)])
    return 10 * np.log10(np.maximum(e / max(e.sum(), 1e-30), 1e-9))


def lsd(a: np.ndarray, b: np.ndarray, f: np.ndarray | None = None) -> float:
    d = a - b if f is None else (a - b)[f > 20]
    return float(np.sqrt(np.mean(d ** 2)))


def features(x: np.ndarray, f: np.ndarray, pdb: np.ndarray) -> dict:
    m = x.mean(axis=1)
    rms = float(np.sqrt(np.mean(m ** 2)))
    peak = float(np.max(np.abs(m)))
    sel = (f > 20) & (f < 20000)
    p = 10 ** (pdb[sel] / 10)
    fs_ = f[sel]
    # movement: mean 1/3-octave flux (dB) between 4096-sample frames, hop 2048
    fr, win, fl, prev = 4096, np.hanning(4096), [], None
    ff = np.fft.rfftfreq(fr, 1 / SR)
    for s in range(0, len(m) - fr, fr // 2):
        spec = np.abs(np.fft.rfft(m[s:s + fr] * win)) ** 2
        e = np.array([spec[(ff >= a) & (ff < b)].sum() for a, b in zip(TLO, THI)])
        edb = 10 * np.log10(np.maximum(e, e.max() * 1e-8 + 1e-30))
        if prev is not None:
            fl.append(np.sqrt(np.mean((edb - prev) ** 2)))
        prev = edb
    return dict(level=20 * np.log10(max(rms, 1e-12)), crest=20 * np.log10(max(peak, 1e-12) / max(rms, 1e-12)),
                centroid=float((p * fs_).sum() / p.sum()), flatness=float(np.exp(np.mean(np.log(p))) / np.mean(p)),
                hf=float(p[fs_ > 4000].sum() / p.sum()), flux=float(np.mean(fl)) if fl else 0.0)


def table_metrics(t25: np.ndarray, t45: np.ndarray, sz: float) -> dict:
    n = min(N, int(np.floor(sz * N)) + 1)
    i = np.arange(n)
    span = t45[:, :n]
    return dict(err=float(np.mean(np.abs(span - np.minimum(i / (sz * N), 1.0)))),
                jumps=float(np.mean(np.sum(np.abs(np.diff(span, axis=1)) > 0.1, axis=1))),
                untouched=float(np.mean(span == (i / N).astype(np.float32))),
                change=float(np.mean(np.abs(span - t25[:, :n]))))


def ensemble(binary: str, sets: list[str], tmp: Path, tag: str, first: np.ndarray | None = None,
             env: dict | None = None) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """f, member 0 (dB), even half, odd half (dB, power-averaged) of the Transpose jitter ensemble."""
    pows, f = [], None
    for k, j in enumerate(JITTER):
        if k == 0 and first is not None:
            pows.append(first)
            continue
        wav = tmp / f"{tag}.j{k}.wav"
        render(binary, str(wav), sets + [f"transpose={j}"], W1, env=env)
        x, _ = sf.read(wav, dtype="float64", always_2d=True)
        wav.unlink()
        f, p = norm_pow(x[int(SKIP * SR):])
        pows.append(p)
    if f is None:
        f = np.fft.rfftfreq(NPERSEG, 1 / SR)
    return f, floor_db(f, pows[0]), floor_db(f, np.mean(pows[0::2], axis=0)), floor_db(f, np.mean(pows[1::2], axis=0))


def analyse_cell(binary: str, sets: list[str], sz: float, tmp: Path, tag: str) -> dict:
    wav, ta, tb = tmp / f"{tag}.wav", tmp / f"{tag}.a.f32", tmp / f"{tag}.b.f32"
    render(binary, "/dev/null", sets, W1, table=str(ta))
    render(binary, str(wav), sets, TOTAL, table=str(tb))
    x, sr = sf.read(wav, dtype="float64", always_2d=True)
    assert sr == SR and np.isfinite(x).all()
    t25 = np.fromfile(ta, dtype=np.float32).reshape(NV, N)
    t45 = np.fromfile(tb, dtype=np.float32).reshape(NV, N)
    for p in (wav, ta, tb):
        p.unlink()
    f, p1 = norm_pow(x[int(SKIP * SR):int(W1 * SR)])
    _, p2 = norm_pow(x[int(W1 * SR):int(W2 * SR)])
    f, d0, h1, h2 = ensemble(binary, sets, tmp, tag, first=p1)
    return dict(f=f, p0=d0.astype(np.float32), h1=h1.astype(np.float32), h2=h2.astype(np.float32),
                self_lsd=lsd(d0, floor_db(f, p2), f), **features(x[int(SKIP * SR):], f, d0),
                **table_metrics(t25, t45, sz))


def cross(H1: np.ndarray, H2: np.ndarray, f: np.ndarray | None = None) -> tuple[np.ndarray, np.ndarray]:
    """Ensemble distances [S, V, V] (diagonal = floor) from halves [S, V, bins]."""
    S, V = H1.shape[:2]
    E = np.zeros((S, V, V))
    for s in range(S):
        for a in range(V):
            for b in range(a, V):
                d = 0.5 * (lsd(H1[s, a], H2[s, b], f) + lsd(H2[s, a], H1[s, b], f)) if a != b else lsd(H1[s, a], H2[s, a], f)
                E[s, a, b] = E[s, b, a] = d
    return E, np.einsum("svv->sv", E).copy()


# ---------------------------------------------------------------- grid

def cmd_grid(binary: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    sits = list(situations())
    vars_ = variants()
    jobs = [(si, vi) for si in range(len(sits)) for vi in range(len(vars_))]
    with tempfile.TemporaryDirectory(dir=out) as td:
        tmp = Path(td)

        def job(j):
            si, vi = j
            return analyse_cell(binary, BASE + sits[si][2] + vars_[vi][1], sits[si][1], tmp, f"g{si}_{vi}")

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            res = list(ex.map(job, jobs))
    S, V = len(sits), len(vars_)
    keys = ["level", "crest", "centroid", "flatness", "hf", "flux", "err", "jumps", "untouched", "change", "self_lsd"]
    feat = {k: np.array([r[k] for r in res]).reshape(S, V) for k in keys}
    f = res[0]["f"]
    P0, H1, H2 = (np.stack([r[k] for r in res]).reshape(S, V, -1) for k in ("p0", "h1", "h2"))
    D = np.zeros((S, V, V))
    for s in range(S):
        for a in range(V):
            for b in range(a + 1, V):
                D[s, a, b] = D[s, b, a] = lsd(P0[s, a], P0[s, b], f)
    E, EF = cross(H1, H2, f)
    BH1 = np.apply_along_axis(lambda p: bands_db(f, p), 2, H1)
    BH2 = np.apply_along_axis(lambda p: bands_db(f, p), 2, H2)
    EB, EBF = cross(BH1, BH2)
    np.savez_compressed(out / "grid.npz", D=D, E=E, EF=EF, EB=EB, EBF=EBF, f=f, H1=H1, H2=H2,
                        sits=np.array([s[0] for s in sits]), vars=np.array([v[0] for v in vars_]),
                        **{f"feat_{k}": v for k, v in feat.items()})
    report = grid_report(out / "grid.npz")
    (out / "grid_report.md").write_text(report)
    print(report)
    cmd_checks(binary, out)


def cmd_checks(binary: str, out: Path) -> None:
    rep = null_pairs(binary, out) + prefill_check(binary, out)
    (out / "checks_report.md").write_text(rep)
    print(rep)


def null_pairs(binary: str, out: Path) -> str:
    """Sample-exact comparison of suspected duplicates through all pitch situations, Size 1 and 0.1."""
    L = ["## Exact duplicates: sample-exact difference, 5 pitch situations x 0.5 s in a row, read Ramp and Tri\n",
         "| A | B | Size | read | peak difference |", "|---|---|---|---|---|"]
    with tempfile.TemporaryDirectory(dir=out) as td:
        tmp = Path(td)
        for (na, sa, nb, sb), sz, (rl, rsets) in itertools.product(NULLS, SIZES, READS):
            ats = []
            for n, (_, wp, wf, rp) in enumerate(PITCH):
                ats += [(0.5 * n, f"wpitch={wp}"), (0.5 * n, f"wfine={wf}"), (0.5 * n, f"rpitch={rp}")]
            xs = []
            for k, s in enumerate((sa, sb)):
                fn = tmp / f"n{k}.wav"
                render(binary, str(fn), BASE + rsets + [f"size={sz}", *s], 0.5 * len(PITCH), ats=ats)
                xs.append(sf.read(fn, always_2d=True)[0])
            d = float(np.max(np.abs(xs[0] - xs[1])))
            L.append(f"| {na} | {nb} | {sz:g} | {rl} | {'bit-identical' if d == 0 else f'{20 * np.log10(d):.1f} dBFS'} |")
    return "\n".join(L) + "\n\n"


def prefill_check(binary: str, out: Path) -> str:
    """Shapes that write few cells (Pulse, stepped Noise) on a table that is not the identity: 1 s of
    Tri in P2 scrambles the table, then at 1 s the target pitches and the variant start; analysed
    1.5-3.5 s against Freeze from the same start; 'rewritten' = share of span cells changed 1.0 -> 3.5 s.
    Single renders (no ensemble)."""
    tests = [("Pulse +0.0", ["wshape=4", "wsym=0"]), ("Noise -1.0", ["wshape=7", "wsym=-1"]),
             ("Noise +1.0", ["wshape=7", "wsym=1"]), ("Tri +0.0", ["wshape=1", "wsym=0"]),
             ("Freeze", ["wactive=0"])]
    _, wp2, wf2, rp2 = PITCH[1]
    jobs = []
    for (pl, wp, wf, rp), sz in itertools.product([p for p in PITCH if not p[0].startswith("P2")], SIZES):
        for tn, tsets in tests:
            pre = BASE + [f"wpitch={wp2}", f"wfine={wf2}", f"rpitch={rp2}", f"size={sz}", "rshape=0",
                          "wshape=1", "wsym=0", "wactive=1"]
            ats = [(1.0, s) for s in [f"wpitch={wp}", f"wfine={wf}", f"rpitch={rp}", *tsets]]
            jobs.append((f"{pl.split()[0]}-ramp-s{sz:g}", sz, tn, pre, ats))
    with tempfile.TemporaryDirectory(dir=out) as td:
        tmp = Path(td)

        def job(k):
            _, sz, _, pre, ats = jobs[k]
            wav, ta, tb = tmp / f"p{k}.wav", tmp / f"p{k}.a.f32", tmp / f"p{k}.b.f32"
            render(binary, "/dev/null", pre, 1.0, table=str(ta), ats=ats)
            render(binary, str(wav), pre, 3.5, table=str(tb), ats=ats)
            x, _ = sf.read(wav, dtype="float64", always_2d=True)
            n = min(N, int(np.floor(sz * N)) + 1)
            t1 = np.fromfile(ta, dtype=np.float32).reshape(NV, N)[:, :n]
            t2 = np.fromfile(tb, dtype=np.float32).reshape(NV, N)[:, :n]
            for p in (wav, ta, tb):
                p.unlink()
            y = x[int(1.5 * SR):]
            f, p = norm_pow(y)
            return f, floor_db(f, p), float(np.mean(t1 != t2)), 20 * np.log10(np.sqrt(np.mean(y.mean(axis=1) ** 2)))

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            res = list(ex.map(job, range(len(jobs))))
    nt = len(tests)
    L = ["## Prefilled table (1 s of Tri in P2, then the variant): single-render LSD to Freeze / rewritten share / level dB\n",
         "| Situation | " + " | ".join(t[0] for t in tests) + " |", "|---" * (nt + 1) + "|"]
    for g in range(len(jobs) // nt):
        row = res[g * nt:(g + 1) * nt]
        L.append(f"| {jobs[g * nt][0]} | " + " | ".join(f"{lsd(r[1], row[-1][1], r[0]):.1f} / {r[2]:.2f} / {r[3]:.0f}"
                                                    for r in row) + " |")
    return "\n".join(L) + "\n"


def grid_report(npz: Path) -> str:
    z = np.load(npz)
    D, E, EF, EB, EBF = z["D"], z["E"], z["EF"], z["EB"], z["EBF"]
    sits, vars_ = list(z["sits"]), list(z["vars"])
    feat = {k[5:]: z[k] for k in z.files if k.startswith("feat_")}
    S, V = D.shape[0], D.shape[1]
    nsh = len(SHAPES)
    sym0 = [vars_.index(f"{n} +0.0") for n in SHAPES]
    iclean, ifreeze = vars_.index("Clean"), vars_.index("Freeze")
    Dm, Em, EBm = D.mean(0), E.mean(0), EB.mean(0)
    X = E - 0.5 * (EF[:, :, None] + EF[:, None, :])        # excess over the floors, per situation
    XB = EB - 0.5 * (EBF[:, :, None] + EBF[:, None, :])
    Xm, XBm = X.mean(0), XB.mean(0)
    L = []
    w = L.append
    w(f"# Shape study grid ({S} situations x {V} variants, ensembles of {len(JITTER)})\n")
    w("Situations: " + ", ".join(sits) + "\n")
    w(f"Floors (mean over cells): ensemble LSD {EF.mean():.2f} dB (shape variants {EF[:, :NS].mean():.2f}), "
      f"ensemble band {EBF.mean():.2f} dB; time self-distance of one render (W1 vs 2.5-4.5 s) "
      f"{feat['self_lsd'].mean():.2f} dB\n")

    w("## Calibration: small knob moves (situation mean; single-render LSD / ensemble LSD / ensemble band)\n")
    w("| Move | single | ensemble | band | floor (ens / band) | excess (ens / band) |")
    w("|---|---|---|---|---|---|")
    for lab, base, _ in CAL:
        a, b = vars_.index(lab), vars_.index(base)
        w(f"| {lab[4:]} vs {base} | {Dm[a, b]:.1f} | {Em[a, b]:.1f} | {EBm[a, b]:.1f} | "
          f"{0.5 * (EF[:, a] + EF[:, b]).mean():.1f} / {0.5 * (EBF[:, a] + EBF[:, b]).mean():.1f} | "
          f"{Xm[a, b]:.2f} / {XBm[a, b]:.2f} |")
    w("")

    w(f"## Features at Sym 0, mean over the {S} situations (single render; d = ensemble LSD)\n")
    w("| Shape | level dB | crest dB | centroid Hz | flatness | >4 kHz | flux dB | table err | jumps | untouched | change | d(Clean) | d(Freeze) |")
    w("|---" * 13 + "|")
    for k in sym0 + [iclean, ifreeze]:
        fm = {n: feat[n][:, k].mean() for n in feat}
        w(f"| {vars_[k]} | {fm['level']:.1f} | {fm['crest']:.1f} | {fm['centroid']:.0f} | {fm['flatness']:.3f} | "
          f"{fm['hf']:.2f} | {fm['flux']:.2f} | {fm['err']:.3f} | {fm['jumps']:.0f} | {fm['untouched']:.2f} | "
          f"{fm['change']:.3f} | {Em[k, iclean]:.1f} | {Em[k, ifreeze]:.1f} |")
    w("")

    w("## Features per situation at Sym 0 (centroid Hz / flatness / level dB)\n")
    w("| Situation | " + " | ".join(SHAPES) + " | Clean | Freeze |")
    w("|---" * (nsh + 3) + "|")
    for s in range(S):
        w(f"| {sits[s]} | " + " | ".join(f"{feat['centroid'][s, k]:.0f}/{feat['flatness'][s, k]:.2f}/{feat['level'][s, k]:.0f}"
                                     for k in sym0 + [iclean, ifreeze]) + " |")
    w("")

    def matrix(M, title, idx, names):
        w(f"## {title}\n")
        w("| | " + " | ".join(names) + " |")
        w("|---" * (len(names) + 1) + "|")
        for a, na in zip(idx, names):
            w(f"| {na} | " + " | ".join(f"({M[a, b]:.1f})" if a == b else f"{M[a, b]:.1f}" for b in idx) + " |")
        w("")

    names0 = SHAPES + ["Clean", "Freeze"]
    matrix(Em, "Ensemble LSD at Sym 0, mean over situations (dB; diagonal = floor)", sym0 + [iclean, ifreeze], names0)
    matrix(EBm, "Ensemble 1/3-octave band distance at Sym 0 (dB; diagonal = floor)", sym0 + [iclean, ifreeze], names0)
    matrix(Xm, "Excess over the floors at Sym 0, ensemble LSD (dB)", sym0 + [iclean, ifreeze], names0)
    matrix(XBm, "Excess over the floors at Sym 0, ensemble band distance (dB)", sym0 + [iclean, ifreeze], names0)
    matrix(Dm, "Single-render LSD at Sym 0 (dB), for comparison", sym0 + [iclean, ifreeze], names0)

    for M, nm in ((Xm, "ensemble LSD"), (XBm, "ensemble band")):
        w(f"## Coverage: mean over A's 5 Sym values of the excess to the nearest variant of B ({nm})\n")
        w("| A \\ B | " + " | ".join(SHAPES) + " |")
        w("|---" * (nsh + 1) + "|")
        for a in range(nsh):
            ia = list(range(a * 5, a * 5 + 5))
            cells = ["" if a == b else f"{np.mean([M[i, b * 5:b * 5 + 5].min() for i in ia]):.1f}" for b in range(nsh)]
            w(f"| {SHAPES[a]} | " + " | ".join(cells) + " |")
        w("")

    w("## Nearest other-shape variant per variant (by excess; ensemble LSD mean [max over situations])\n")
    w("| Variant | nearest | LSD | [max] | floor a/b | excess | band excess | 2nd shape | excess |")
    w("|---|---|---|---|---|---|---|---|---|")
    pool = list(range(NS)) + [iclean, ifreeze]
    for i in range(NS):
        order = [j for j in sorted(pool, key=lambda j: Xm[i, j]) if j != i and (j >= NS or j // 5 != i // 5)]
        j = order[0]
        j2 = next(k for k in order[1:] if (k >= NS) or (j >= NS) or k // 5 != j // 5)
        w(f"| {vars_[i]} | {vars_[j]} | {Em[i, j]:.1f} | [{E[:, i, j].max():.1f}] | {EF[:, i].mean():.1f}/{EF[:, j].mean():.1f} | "
          f"{Xm[i, j]:.1f} | {XBm[i, j]:.1f} | {vars_[j2]} | {Xm[i, j2]:.1f} |")
    w("")

    w("## Within-shape Sym matrices (excess, ensemble LSD; rows/columns Sym -1, -0.5, 0, +0.5, +1)\n")
    for a in range(nsh):
        ia = list(range(a * 5, a * 5 + 5))
        w(f"- {SHAPES[a]}: " + "; ".join(" ".join(f"{v:.1f}" for v in row) for row in Xm[np.ix_(ia, ia)]))
    w("")

    cand = [s for s in range(nsh) if SHAPES[s] != "Pulse"]
    tgt = [i for i in range(NS) if i // 5 in cand]

    def cover(sub):
        cols = [i for i in range(NS) if i // 5 in sub]
        d, db = [], []
        for i in tgt:
            d.append(0.0 if i // 5 in sub else float(Xm[i, cols].min()))
            db.append(0.0 if i // 5 in sub else float(XBm[i, cols].min()))
        return float(np.mean(d)), float(np.max(d)), float(np.mean(db)), float(np.max(db))

    w("## Shape subsets: excess from every non-Pulse variant to the nearest variant of the subset\n")
    w("(situation mean; own-shape variants count 0; best two per size by mean LSD excess, then named sets)\n")
    w("| k | subset | LSD excess mean | max | band excess mean | max |")
    w("|---|---|---|---|---|---|")
    rows = []
    for k in range(3, len(cand)):
        rows += [(k, sub, c) for c, sub in sorted((cover(sub), sub) for sub in itertools.combinations(cand, k))[:2]]
    for n in [KEEP, ["Ramp", "Tri", "Tri ±", "Pulsar", "Noise"], ["Ramp", "Tri", "Sine", "Pulsar", "Spike", "Noise"],
              ["Ramp", "Tri", "Tri ±", "Pulsar", "Spike", "Noise"],
              ["Ramp", "Tri", "Spike", "Noise"], ["Ramp", "Tri", "Pulsar", "Noise"], ["Ramp", "Spike", "Noise"]]:
        sub = tuple(SHAPES.index(s) for s in n)
        rows.append((len(sub), sub, cover(sub)))
    for k, sub, (m, mx, mb, mxb) in rows:
        w(f"| {k} | {', '.join(SHAPES[s] for s in sub)} | {m:.2f} | {mx:.2f} | {mb:.2f} | {mxb:.2f} |")
    w("")

    keep = [SHAPES.index(s) for s in KEEP]
    cols = [i for i in range(NS) if i // 5 in keep]
    w(f"## Dropped variants -> nearest variant (by excess) of the kept set {', '.join(KEEP)}\n")
    w("| Dropped | nearest kept | LSD mean | min | max | floor a/b | excess | max excess | band excess |")
    w("|---|---|---|---|---|---|---|---|---|")
    for i in range(NS):
        if i // 5 in keep:
            continue
        j = cols[int(np.argmin(Xm[i, cols]))]
        w(f"| {vars_[i]} | {vars_[j]} | {Em[i, j]:.1f} | {E[:, i, j].min():.1f} | {E[:, i, j].max():.1f} | "
          f"{EF[:, i].mean():.1f}/{EF[:, j].mean():.1f} | {Xm[i, j]:.1f} | {X[:, i, j].max():.1f} | {XBm[i, j]:.1f} |")
    w("")

    groups = sorted({s.split("-")[0] for s in sits})
    w("## Selected pairs: ensemble LSD, floor, excess; excess per pitch situation (mean over read x Size), dB\n")
    w("| Pair | mean | floor | excess | band excess | " + " | ".join(f"{g} excess" for g in groups) + " |")
    w("|---" * (len(groups) + 5) + "|")
    for a, b in PAIRS:
        ia, ib = vars_.index(a), vars_.index(b)
        x = X[:, ia, ib]
        per = [np.mean([x[s] for s in range(S) if sits[s].startswith(g + "-")]) for g in groups]
        w(f"| {a} / {b} | {Em[ia, ib]:.1f} | {0.5 * (EF[:, ia] + EF[:, ib]).mean():.1f} | {Xm[ia, ib]:.1f} | "
          f"{XBm[ia, ib]:.1f} | " + " | ".join(f"{p:.1f}" for p in per) + " |")
    w("")

    w("## Per situation: mean excess between the 7 non-Pulse shapes at Sym 0 (LSD / band) and the extremes\n")
    w("| Situation | mean excess | band | closest pair | excess | farthest pair | excess | floor |")
    w("|---|---|---|---|---|---|---|---|")
    np0 = [k for k, n in zip(sym0, SHAPES) if n != "Pulse"]
    nn0 = [n for n in SHAPES if n != "Pulse"]
    iu = np.triu_indices(len(np0), 1)
    for s in range(S):
        sub, subb = X[s][np.ix_(np0, np0)][iu], XB[s][np.ix_(np0, np0)][iu]
        k, kk = int(np.argmin(sub)), int(np.argmax(sub))
        w(f"| {sits[s]} | {sub.mean():.1f} | {subb.mean():.1f} | {nn0[iu[0][k]]} / {nn0[iu[1][k]]} | {sub[k]:.1f} | "
          f"{nn0[iu[0][kk]]} / {nn0[iu[1][kk]]} | {sub[kk]:.1f} | {EF[s, np0].mean():.1f} |")
    for g in sorted({x.split("-")[0] for x in sits}):
        ss = [s for s in range(S) if sits[s].startswith(g + "-")]
        w(f"| {g} (mean) | {np.mean([X[s][np.ix_(np0, np0)][iu].mean() for s in ss]):.1f} | "
          f"{np.mean([XB[s][np.ix_(np0, np0)][iu].mean() for s in ss]):.1f} | | | | | |")
    w("")

    w("## Table: share of span cells never written (untouched) / mean |T(4.5 s) - T(2.5 s)| per situation\n")
    tv = ["Ramp +0.0", "Pulsar -1.0", "Spike -1.0", "Pulse +0.0", "Noise -1.0", "Noise +1.0"]
    w("| Situation | " + " | ".join(tv) + " |")
    w("|---" * (len(tv) + 1) + "|")
    for s in range(S):
        w(f"| {sits[s]} | " + " | ".join(f"{feat['untouched'][s, vars_.index(t)]:.2f} / {feat['change'][s, vars_.index(t)]:.3f}"
                                     for t in tv) + " |")
    w("")

    from scipy.cluster.hierarchy import fcluster, linkage
    from scipy.spatial.distance import squareform
    sub = np.maximum(Xm[:NS, :NS], 0)
    np.fill_diagonal(sub, 0)
    Z = linkage(squareform(sub, checks=False), method="average")
    for thr in (1.0, 1.5, 2.0):
        lab = fcluster(Z, thr, criterion="distance")
        grp = {}
        for i, l in enumerate(lab):
            grp.setdefault(l, []).append(vars_[i])
        multi = [g for g in grp.values() if len({v.rsplit(' ', 1)[0] for v in g}) > 1]
        w(f"Clusters (average linkage on LSD excess at {thr:g} dB) spanning more than one shape: "
          + ("; ".join("{" + ", ".join(g) + "}" for g in multi) if multi else "none") + "\n")
    return "\n".join(L) + "\n"


# ---------------------------------------------------------------- read side

def cmd_read(binary: str, xbinary: str, out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    L = ["# Read-side checks\n"]
    w = L.append
    with tempfile.TemporaryDirectory(dir=out) as td:
        tmp = Path(td)
        w("## Read Tri 1-Way vs Read Ramp (sample-exact difference, 2 s, the 8 write shapes in turn)\n")
        w("| Ramp AA | situation | peak difference |")
        w("|---|---|---|")
        seq = [(0.25 * k, f"wshape={k}") for k in range(8)]
        for aa in (0, 1):
            for pl, wp, wf, rp in PITCH:
                common = BASE + [f"wpitch={wp}", f"wfine={wf}", f"rpitch={rp}", f"aaramp={aa}"]
                xs = []
                for k, s in enumerate((["rshape=0"], ["rshape=1", "rdir=0"])):
                    fn = tmp / f"t{k}.wav"
                    render(binary, str(fn), common + s, 2.0, ats=seq)
                    xs.append(sf.read(fn, always_2d=True)[0])
                d = float(np.max(np.abs(xs[0] - xs[1])))
                w(f"| {'on' if aa else 'off'} | {pl} | {'bit-identical' if d == 0 else f'{20 * np.log10(d):.1f} dBFS'} |")
        w("")

        # hypothetical read shapes (patched renderer, mode > 0) against what the device already offers
        alts = [
            ("Ramp", 0, ["rshape=0"]),
            ("Tri 2-Way", 0, ["rshape=1", "rdir=1"]),
            ("Ramp + Smooth", 0, ["rshape=0", "smoothread=1"]),
            ("Tri 2-Way + Smooth", 0, ["rshape=1", "rdir=1", "smoothread=1"]),
            ("Ramp, Read Osc->Size +33", 0, ["rshape=0", "mx_ro_sz=33"]),
            ("Tri 2-Way, Read Osc->Size +33", 0, ["rshape=1", "rdir=1", "mx_ro_sz=33"]),
            ("Ramp, Read Osc->Read Pitch +50", 0, ["rshape=0", "mx_ro_rp=50"]),
            ("Ramp, Size = 8 cells", 0, ["rshape=0", "SIZE8"]),
            ("x Sine 2-Way", 1, []),
            ("x Pulse", 2, []),
            ("x Step 8", 3, []),
        ]
        wsh = [(0, "Ramp"), (1, "Tri"), (3, "Sine"), (7, "Noise")]
        sits = [(f"{pl.split()[0]}-s{sz:g}", sz, [f"wpitch={wp}", f"wfine={wf}", f"rpitch={rp}"])
                for (pl, wp, wf, rp), sz in itertools.product(PITCH, SIZES)]
        jobs = []
        for si, (_, sz, ssets) in enumerate(sits):
            for ki, (k, _) in enumerate(wsh):
                for ai, (_, mode, asets) in enumerate(alts):
                    szz = 8 / N if "SIZE8" in asets else sz
                    sets = BASE + ssets + [a for a in asets if a != "SIZE8"] + [f"size={szz}", f"wshape={k}", "wsym=0"]
                    jobs.append((si, ki, ai, mode, sets))

        def job(j):
            si, ki, ai, mode, sets = j
            env = {"ALIASING_XREAD": str(mode)}
            b = xbinary if mode else binary
            wav = tmp / f"r{si}_{ki}_{ai}.wav"
            render(b, str(wav), sets, W1, env=env)
            x, _ = sf.read(wav, dtype="float64", always_2d=True)
            wav.unlink()
            x = x[int(SKIP * SR):]
            f, p = norm_pow(x)
            _, d0, h1, h2 = ensemble(b, sets, tmp, f"r{si}_{ki}_{ai}", first=p, env=env)
            return f, h1, h2, features(x, f, d0)

        with ThreadPoolExecutor(max_workers=os.cpu_count() or 4) as ex:
            res = list(ex.map(job, jobs))
    f = res[0][0]
    A, SW = len(alts), len(sits) * len(wsh)
    H1 = np.array([r[1] for r in res]).reshape(SW, A, -1)
    H2 = np.array([r[2] for r in res]).reshape(SW, A, -1)
    E, EF = cross(H1, H2, f)
    Em = E.mean(0)
    names = [a[0] for a in alts]
    w(f"## Read variants: ensemble LSD (dB), mean over {len(sits)} situations x write shapes "
      + ", ".join(n for _, n in wsh) + " at Sym 0 (diagonal = floor)\n")
    w("| | " + " | ".join(f"{i}" for i in range(A)) + " |")
    w("|---" * (A + 1) + "|")
    for a in range(A):
        w(f"| {a} {names[a]} | " + " | ".join(f"({Em[a, b]:.1f})" if a == b else f"{Em[a, b]:.1f}" for b in range(A)) + " |")
    w("")
    Xm = (E - 0.5 * (EF[:, :, None] + EF[:, None, :])).mean(0)
    w("| Read variant | centroid Hz | flatness | level dB | nearest (by excess) | LSD | [max] | floor a/b | excess | excess to Ramp | to Tri 2-Way |")
    w("|---|---|---|---|---|---|---|---|---|---|---|")
    for a in range(A):
        sel = [r[3] for r, j in zip(res, jobs) if j[2] == a]
        j = min((b for b in range(A) if b != a), key=lambda b: Xm[a, b])
        w(f"| {names[a]} | {np.mean([s['centroid'] for s in sel]):.0f} | {np.mean([s['flatness'] for s in sel]):.3f} | "
          f"{np.mean([s['level'] for s in sel]):.1f} | {names[j]} | {Em[a, j]:.1f} | {E[:, a, j].max():.1f} | "
          f"{EF[:, a].mean():.1f}/{EF[:, j].mean():.1f} | {Xm[a, j]:.1f} | {Xm[a, 0]:.1f} | {Xm[a, 1]:.1f} |")
    w("")
    rep = "\n".join(L) + "\n"
    (out / "read_report.md").write_text(rep)
    print(rep)


# ---------------------------------------------------------------- audition

AUDITION = [
    ("w0_ramp_sym0", 0, 0.0), ("w1_tri_sym0", 1, 0.0), ("w2_tripm_sym0", 2, 0.0), ("w3_sine_sym0", 3, 0.0),
    ("w4_pulse_sym0", 4, 0.0), ("w5_pulsar_sym0", 5, 0.0), ("w6_spike_sym0", 6, 0.0), ("w7_noise_sym0", 7, 0.0),
    ("w7_noise_symm1", 7, -1.0),
    # merge targets of the dropped shapes: Sine +-1 -> Ramp -0.5; Tri +-0 -> Spike 0 (above); Tri +-1 -> Pulsar 0
    ("w0_ramp_symm05", 0, -0.5), ("w2_tripm_symp1", 2, 1.0), ("w3_sine_symp1", 3, 1.0),
]


def cmd_audition(binary: str, out: Path, items: list[tuple[str, int, float]]) -> None:
    """Each file: the 5 pitch situations x 1.5 s in a row at Size 0.1, read Ramp, the device's default
    tone (Band open, Drive 0 dB, Width 1, limiter on); peak-normalised to -18 dBFS with 10 ms fades."""
    d = out / "audition"
    d.mkdir(parents=True, exist_ok=True)
    seg = 1.5
    for name, k, sym in items:
        ats = []
        for n, (_, wp, wf, rp) in enumerate(PITCH):
            ats += [(n * seg, f"wpitch={wp}"), (n * seg, f"wfine={wf}"), (n * seg, f"rpitch={rp}")]
        render(binary, str(d / f"{name}.wav"), [f"wshape={k}", f"wsym={sym}", "size=0.1"], seg * len(PITCH), ats=ats)
        normalise(d / f"{name}.wav")
    # Pulse on a table that is not the identity: 1.5 s of Tri in P2 fills it, then P3 pitches and Pulse
    # (or Freeze) for 4.5 s; the two files should sound alike after 1.5 s
    _, wp2, wf2, rp2 = PITCH[1]
    _, wp3, wf3, rp3 = PITCH[2]
    for name, sets in (("w4_pulse_after_tri", ["wshape=4", "wsym=0"]), ("freeze_after_tri", ["wactive=0"])):
        render(binary, str(d / f"{name}.wav"), ["wshape=1", "size=0.1", f"wpitch={wp2}", f"wfine={wf2}", f"rpitch={rp2}"],
               6.0, ats=[(1.5, s) for s in [f"wpitch={wp3}", f"wfine={wf3}", f"rpitch={rp3}", *sets]])
        normalise(d / f"{name}.wav")


def normalise(fn: Path) -> None:
    x, sr = sf.read(fn, dtype="float64", always_2d=True)
    x *= 10 ** (-18 / 20) / max(np.max(np.abs(x)), 1e-12)
    fade = np.linspace(0, 1, int(0.01 * sr))[:, None]
    x[:len(fade)] *= fade
    x[-len(fade):] *= fade[::-1]
    sf.write(fn, x.astype(np.float32), sr, subtype="FLOAT")
    print(fn)


# ---------------------------------------------------------------- patched export (read experiment)

XPATCH_HEAD = """// PATCHED COPY for devices/aliasing/test/shapes (read-shape experiment), not the device's DSP.
// ALIASING_XREAD: 0 as built, 1 Sine 2-way, 2 Pulse, 3 Step 8 (value written = position read).
#include <cmath>
#include <cstdlib>
static int aliasing_xread_mode() {
\tstatic int m = std::getenv("ALIASING_XREAD") ? std::atoi(std::getenv("ALIASING_XREAD")) : 0;
\treturn m;
}
static double aliasing_xread(double rd, double phr) {
\tswitch (aliasing_xread_mode()) {
\tcase 1: return 0.5 - 0.5 * std::cos(6.283185307179586 * phr);
\tcase 2: return phr >= 0.5 ? 1.0 : 0.0;
\tcase 3: return std::floor(8.0 * phr) / 8.0;
\tdefault: return rd;
\t}
}
"""


def cmd_xpatch(src: Path, dst: Path) -> None:
    """Copy the export's aliasing.cpp with the read shape `rd` routed through aliasing_xread()."""
    text = src.read_text()
    pat = re.compile(r"t_sample rd = \((cond_\d+) \? trir : rampr\);")
    if len(pat.findall(text)) != 1:
        raise SystemExit("xpatch: the read-shape line was not found exactly once (export changed?)")
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(XPATCH_HEAD + pat.sub(r"t_sample rd = aliasing_xread((\1 ? trir : rampr), phr);", text))


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] not in ("grid", "checks", "report", "read", "audition", "xpatch"):
        print(__doc__)
        return 2
    if argv[0] == "grid":
        cmd_grid(argv[1], Path(argv[2]))
    elif argv[0] == "checks":
        cmd_checks(argv[1], Path(argv[2]))
    elif argv[0] == "report":
        rep = grid_report(Path(argv[1]))
        (Path(argv[1]).parent / "grid_report.md").write_text(rep)
        print(rep)
    elif argv[0] == "xpatch":
        cmd_xpatch(Path(argv[1]), Path(argv[2]))
    elif argv[0] == "read":
        cmd_read(argv[1], argv[2], Path(argv[3]))
    else:
        extra = [(n, int(k), float(s)) for n, k, s in (spec.split(":") for spec in argv[3:])]
        cmd_audition(argv[1], Path(argv[2]), AUDITION + extra)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
