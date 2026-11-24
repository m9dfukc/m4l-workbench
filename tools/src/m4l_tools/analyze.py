"""Quick health check and spectral comparison of audio renders.

Aliasing-heavy and chaotic signals are compared by their spectra (Welch PSD), not by
subtracting waveforms. Sample-exact nulls only make sense between gen~ in Max and its own
C++ export, use --null for that.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import soundfile as sf
from scipy import signal


def load(path: str) -> tuple[np.ndarray, int]:
    data, sr = sf.read(path, dtype="float64", always_2d=True)
    return data, sr


def health(name: str, x: np.ndarray, sr: int) -> bool:
    finite = np.isfinite(x).all()
    peak = float(np.max(np.abs(x[np.isfinite(x)]))) if x.size else 0.0
    rms = float(np.sqrt(np.mean(np.square(np.nan_to_num(x))))) if x.size else 0.0
    dc = np.mean(np.nan_to_num(x), axis=0)

    def db(v: float) -> float:
        return 20 * np.log10(max(v, 1e-12))

    print(f"{name}: {x.shape[0] / sr:.2f} s, {sr} Hz, {x.shape[1]} ch, "
          f"peak {db(peak):.1f} dBFS, rms {db(rms):.1f} dBFS, "
          f"dc {', '.join(f'{d:+.4f}' for d in dc)}, finite={finite}")
    ok = finite and peak <= 1.0
    if not ok:
        print(f"  FAIL: {'non-finite samples' if not finite else 'peak above 0 dBFS'}")
    return ok


def psd_db(x: np.ndarray, sr: int, nperseg: int) -> tuple[np.ndarray, np.ndarray]:
    mono = x.mean(axis=1)
    f, p = signal.welch(mono, fs=sr, window="hann", nperseg=nperseg, noverlap=nperseg // 2)
    return f, 10 * np.log10(np.maximum(p, 1e-20))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("files", nargs="+", help="WAV/AIFF files; with two files, compare the second against the first")
    ap.add_argument("--nperseg", type=int, default=8192, help="Welch segment length (default 8192)")
    ap.add_argument("--null", action="store_true", help="also report the sample-exact difference of two files")
    args = ap.parse_args(argv)

    loaded = [(p, *load(p)) for p in args.files]
    ok = all(health(p, x, sr) for p, x, sr in loaded)

    if len(loaded) == 2:
        (pa, a, sra), (pb, b, srb) = loaded
        if sra != srb:
            print(f"sample rates differ ({sra} vs {srb}): no comparison")
            return 1
        fa, da = psd_db(a, sra, args.nperseg)
        _, db_ = psd_db(b, srb, args.nperseg)
        band = fa > 20
        lsd = float(np.sqrt(np.mean(np.square(db_[band] - da[band]))))
        print(f"log-spectral distance (Welch PSD, >20 Hz): {lsd:.2f} dB")
        if args.null:
            n = min(len(a), len(b))
            ch = min(a.shape[1], b.shape[1])
            diff = b[:n, :ch] - a[:n, :ch]
            peak = float(np.max(np.abs(diff))) if n else 0.0
            print(f"null: peak difference {20 * np.log10(max(peak, 1e-20)):.1f} dBFS over {n} samples"
                  + (" (bit-identical)" if peak == 0.0 else ""))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
