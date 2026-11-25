"""Pass/fail checks on the host renders of the aliasing gen~ export, v0.3 (see run.sh).

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

    names = ("off", "drone", "alias", "gate", "stress", "stress44", "sync", "frozen", "clean",
             "wgate_open", "wgate_shut", "tempo", "band_open", "band_pass", "band_reject", "aa", "naive",
             "lim_off", "lim_idle", "lim_color", "drv_zero", "drv_off", "lim_ceil", "env_ref", "env_duck",
             "res_on")
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
    check(abs(fw - 261.63) < 0.05, f"drone: init write frequency = note 60 = 261.63 Hz (D1) ({fw:.2f})")
    fr = float(h[5, 2])
    check(abs(fr - 261.63) < 0.05, f"drone: init read frequency (middle voice) = 261.63 Hz (D1) ({fr:.2f})")
    check(abs(float(h[9, 0]) - sr) < 0.5, f"drone: samplerate in the display data ({h[9, 0]:.0f})")
    t = table("drone")
    check(bool((t >= 0).all() and (t <= 1).all()), "drone: table values within 0..1")
    ident = np.tile(np.arange(N, dtype=np.float64) / N, (NV, 1))
    changed = int((np.abs(t[:, :103] - ident[:, :103]) > 1e-6).sum())
    check(changed > 50, f"drone: the write pointer rewrites the active span ({changed} cells changed)")
    h = heads("alias")
    fw = float(h[4, 0])
    check(abs(fw - 16004.3) < 2.0, f"alias: v0.2 init write frequency = 16004 Hz (fs/3 + 4 Hz) ({fw:.1f})")
    t = table("alias")
    changed = int((np.abs(t[:, :103] - ident[:, :103]) > 1e-6).sum())
    check(changed > 50, f"alias: the write pointer rewrites the active span ({changed} cells changed)")

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
    check(float(np.abs(t - ident).max()) == 0.0, "frozen: write state Freeze keeps the identity table")
    t = table("clean").astype(np.float64)
    near = float((np.abs(t - ident) <= 1.0 / N + 1e-7).mean())
    check(near > 0.99, f"clean: Clean heals an aliased table back to identity ({near * 100:.2f} % of cells "
                       "within one cell value)")
    t = table("wgate_open").astype(np.float64)
    check(int((np.abs(t - ident) > 1e-6).sum()) > 50, "write gate: Freeze + Velocity 1 at +100 % writes")
    t = table("wgate_shut").astype(np.float64)
    check(float(np.abs(t - ident).max()) == 0.0, "write gate: Freeze + Velocity 0.4 at +100 % stays frozen")
    t = table("sync").astype(np.float64)
    dev = float(np.abs(t - ident).max())
    check(dev <= 1.0 / N + 1e-7, f"sync: equal pitches keep the table within one cell value of identity "
                                 f"(max dev {dev * N:.3f} cells)")

    h = heads("tempo")
    check(abs(float(h[4, 0]) - 128.0) < 0.2, f"tempo: synced write = 1/16 x 64 / 4 at 120 BPM = 128 Hz ({h[4, 0]:.2f})")
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

    # exact bypasses (D17, D19); the section switches fade in 5 ms and snap, so compare after 0.2 s
    def same(a: str, b: str, t0: float = 0.0) -> float:
        xa, sra = wav(a)
        xb, _ = wav(b)
        return float(np.abs(seg(xa, sra, t0, 2) - seg(xb, sra, t0, 2)).max())
    dmax = same("lim_off", "lim_idle")
    check(dmax == 0.0, f"limiter: on but not limiting, Saturation 0 = exact bypass (max diff {dmax:.2e})")
    dmax = same("lim_idle", "lim_color")
    check(dmax == 0.0, f"limiter: Color alone changes nothing (max diff {dmax:.2e})")
    dmax = same("drv_zero", "drv_off")
    check(dmax == 0.0, f"drive: section off = exact bypass, from the first sample (max diff {dmax:.2e})")
    x, sr = wav("lim_ceil")
    p6 = peak(seg(x, sr, 0.05, 2))
    check(p6 <= 10 ** (-6 / 20) + 1e-6, f"limiter: +24 dB into a -6 dB ceiling stays below it ({db(p6):.2f} dBFS)")
    check(rms(x) > 10 ** (-30 / 20), f"limiter: still audible at the ceiling (rms {db(rms(x)):.1f})")
    xr_, sr = wav("env_ref")
    xd, _ = wav("env_duck")
    rr, rd_ = rms(seg(xr_, sr, 0.5, 2)), rms(seg(xd, sr, 0.5, 2))
    check(rd_ < rr * 10 ** (-3 / 20), f"env follower: Env -> Output -100 % lowers the level ({db(rr):.1f} -> {db(rd_):.1f})")
    xo, _ = wav("res_on")
    dmax = same("env_ref", "res_on", 0.2)
    check(dmax > 1e-3, f"resonator: section on changes the output, off is the default (max diff {dmax:.3f})")

    print(f"\n{len(fails)} failed" if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
