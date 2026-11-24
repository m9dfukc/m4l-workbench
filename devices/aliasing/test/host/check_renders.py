"""Pass/fail checks on the host renders of the aliasing gen~ export (see run.sh).

Usage: uv run python check_renders.py BUILD_HOST_DIR
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf

N, NV = 1024, 5


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
        return np.fromfile(d / f"{name}.heads.f32", dtype=np.float32).reshape(3, NV)

    for name in ("off", "on", "gate", "stress", "stress44", "sync", "frozen"):
        x, _ = wav(name)
        check(bool(np.isfinite(x).all()) and peak(x) <= 1.0, f"{name}: finite, peak <= 0 dBFS ({db(peak(x)):.1f})")

    x, sr = wav("off")
    check(peak(x) < 1e-6, f"off: silent when never activated (peak {db(peak(x)):.1f} dBFS)")

    x, sr = wav("on")
    check(rms(seg(x, sr, 0.5, 4)) > 10 ** (-40 / 20), f"on: audible when active (rms {db(rms(seg(x, sr, 0.5, 4))):.1f} dBFS)")
    dc = float(np.abs(seg(x, sr, 0.5, 4).mean(axis=0)).max())
    check(dc < 0.05, f"on: |dc| < 0.05 ({dc:.4f})")
    h = heads("on")
    check(bool(((h >= 0) & (h <= 1)).all()), "on: head positions within 0..1")
    check(bool((h[2] == 1).all()), "on: write enable 1 for all voices")

    x, sr = wav("gate")
    check(peak(seg(x, sr, 0, 0.45)) < 1e-6, "gate: silent before the MIDI gate")
    check(rms(seg(x, sr, 0.6, 2.4)) > 10 ** (-40 / 20), f"gate: audible while gated (rms {db(rms(seg(x, sr, 0.6, 2.4))):.1f})")
    check(peak(seg(x, sr, 2.7, 3.5)) < 1e-3, f"gate: decays after gate off (peak {db(peak(seg(x, sr, 2.7, 3.5))):.1f})")

    t = table("stress")
    check(bool(np.isfinite(t).all() and (t >= 0).all() and (t <= 1).all()), "stress: table values within 0..1")
    h = heads("stress")
    check(bool(((h >= 0) & (h <= 1)).all()), "stress: head positions within 0..1")

    ident = np.tile(np.arange(N, dtype=np.float64) / N, (NV, 1))
    t = table("frozen").astype(np.float64)
    check(float(np.abs(t - ident).max()) == 0.0, "frozen: Write Active off keeps the identity table")
    t = table("sync").astype(np.float64)
    dev = float(np.abs(t - ident).max())
    changed = int((t != ident).sum())
    check(dev <= 1.0 / N, f"sync: equal pitches keep the table within one cell value of identity "
                          f"(max dev {dev * N:.3f} cells, {changed} cells rewritten)")

    print(f"\n{len(fails)} failed" if fails else "\nall checks passed")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
