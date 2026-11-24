"""Pass/fail checks on the host renders of the aliasing gen~ export, v0.2 (see run.sh).

Usage: uv run python check_renders.py BUILD_HOST_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

N, NV, NCH = 1024, 5, 10


def db(v: float) -> float:
    return 20 * np.log10(max(v, 1e-12))


def main(argv: list[str]) -> int:
    if len(argv) != 1:
        print(__doc__)
        return 2
    d = Path(argv[0])
    fails: list[str] = []

    def check(ok: bool, msg: str) -> None:
        print(("ok   " if ok else "FAIL ") + msg)
        if not ok:
            fails.append(msg)

    def wav(name: str) -> tuple[np.ndarray, int]:
        x, sr = sf.read(d / f"{name}.wav", dtype="float64", always_2d=True)
        return x, sr

    def seg(x: np.ndarray, sr: int, t0: float, t1: float) -> np.ndarray:
        return x[int(t0 * sr):int(t1 * sr)]

    def peak(x: np.ndarray) -> float:
        return float(np.max(np.abs(x))) if x.size else 0.0

    def rms(x: np.ndarray) -> float:
        return float(np.sqrt(np.mean(np.square(x)))) if x.size else 0.0

    def table(name: str) -> np.ndarray:
        return np.fromfile(d / f"{name}.table.f32", dtype=np.float32).reshape(NV, N)

    def heads(name: str) -> np.ndarray:
        return np.fromfile(d / f"{name}.heads.f32", dtype=np.float32).reshape(NCH, NV)

    def band_energy(x: np.ndarray, sr: int, lo: float, hi: float) -> float:
        m = x.mean(axis=1)
        spec = np.abs(np.fft.rfft(m * np.hanning(len(m)))) ** 2
        f = np.fft.rfftfreq(len(m), 1 / sr)
        return float(spec[(f >= lo) & (f < hi)].sum() / max(spec.sum(), 1e-30))

    names = ("off", "drone", "gate", "stress", "stress44", "sync", "frozen", "tempo",
             "band_open", "band_pass", "band_reject", "aa", "naive")
    for name in names:
        x, _ = wav(name)
        check(bool(np.isfinite(x).all()) and peak(x) <= 1.0, f"{name}: finite, peak <= 0 dBFS ({db(peak(x)):.1f})")

    x, sr = wav("off")
    check(peak(x) < 1e-6, f"off: silent in MIDI gate mode without a note (peak {db(peak(x)):.1f} dBFS)")

    x, sr = wav("drone")
    r = rms(seg(x, sr, 0.5, 4))
    check(r > 10 ** (-40 / 20), f"drone: audible from the start in Drone mode (rms {db(r):.1f} dBFS)")
    dc = float(np.abs(seg(x, sr, 1, 4).mean(axis=0)).max())
    check(dc < 0.01, f"drone: |dc| < 0.01 after the DC blocker ({dc:.4f})")
    h = heads("drone")
    check(bool(((h[0:2] >= 0) & (h[0:2] <= 1)).all()), "drone: head positions within 0..1")
    check(bool((h[2] == 1).all()), "drone: write enable 1 for all voices")
    check(bool(np.allclose(h[3], 0.1, atol=1e-6)), f"drone: effective Size 0.1 per voice ({h[3].round(4).tolist()})")
    fw = float(h[4, 0])
    check(abs(fw - 16004.3) < 2.0, f"drone: write frequency = 16004 Hz (fs/3 + 4 Hz) ({fw:.1f})")
    check(abs(float(h[9, 0]) - sr) < 0.5, f"drone: samplerate in the display data ({h[9, 0]:.0f})")
    t = table("drone")
    check(bool((t >= 0).all() and (t <= 1).all()), "drone: table values within 0..1")
    ident = np.tile(np.arange(N, dtype=np.float64) / N, (NV, 1))
    changed = int((np.abs(t[:, :103] - ident[:, :103]) > 1e-6).sum())
    check(changed > 50, f"drone: the write pointer rewrites the active span ({changed} cells changed)")

    x, sr = wav("gate")
    check(peak(seg(x, sr, 0, 0.45)) < 1e-6, "gate: silent before the MIDI gate")
    r = rms(seg(x, sr, 0.6, 2.4))
    check(r > 10 ** (-40 / 20), f"gate: audible while gated (rms {db(r):.1f})")
    check(peak(seg(x, sr, 2.8, 3.5)) < 1e-3, f"gate: decays after gate off (peak {db(peak(seg(x, sr, 2.8, 3.5))):.1f})")

    t = table("stress")
    check(bool(np.isfinite(t).all() and (t >= 0).all() and (t <= 1).all()), "stress: table values within 0..1")
    h = heads("stress")
    check(bool(np.isfinite(h).all()), "stress: display data finite")
    check(bool(((h[0:2] >= 0) & (h[0:2] <= 1)).all()), "stress: head positions within 0..1")
    x, sr = wav("stress")
    r = rms(x)
    check(r > 10 ** (-60 / 20), f"stress: not silent (rms {db(r):.1f})")

    t = table("frozen").astype(np.float64)
    check(float(np.abs(t - ident).max()) == 0.0, "frozen: Write Active off keeps the identity table")
    t = table("sync").astype(np.float64)
    dev = float(np.abs(t - ident).max())
    check(dev <= 1.0 / N + 1e-7, f"sync: equal pitches keep the table within one cell value of identity "
                                 f"(max dev {dev * N:.3f} cells)")

    h = heads("tempo")
    check(abs(float(h[4, 0]) - 512.0) < 0.5, f"tempo: synced write = 64 x 1/16 at 120 BPM = 512 Hz ({h[4, 0]:.2f})")
    check(abs(float(h[5, 0]) - 2.0) < 0.01, f"tempo: synced read = 1/4 at 120 BPM = 2 Hz ({h[5, 0]:.3f})")
    check(abs(float(h[9, 3]) - 120.0) < 0.01, f"tempo: BPM in the display data ({h[9, 3]:.2f})")

    xo, sr = wav("band_open")
    xp, _ = wav("band_pass")
    xr, _ = wav("band_reject")
    eo = band_energy(seg(xo, sr, 0.5, 3), sr, 700, 1400)
    ep = band_energy(seg(xp, sr, 0.5, 3), sr, 700, 1400)
    er = band_energy(seg(xr, sr, 0.5, 3), sr, 700, 1400)
    check(ep > 1.5 * eo, f"band: Pass 1 oct at 1 kHz concentrates energy at 0.7-1.4 kHz ({eo:.3f} -> {ep:.3f})")
    check(er < 0.5 * eo, f"band: Reject 1 oct at 1 kHz removes energy at 0.7-1.4 kHz ({eo:.3f} -> {er:.3f})")

    xa, _ = wav("aa")
    xn, _ = wav("naive")
    diff = float(np.abs(xa - xn).max())
    check(diff > 1e-3, f"aa: anti-aliased ramps change the output (max diff {diff:.3f})")

    print(f"\n{len(fails)} failed" if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
