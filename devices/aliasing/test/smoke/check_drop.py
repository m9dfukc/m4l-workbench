#!/usr/bin/env python3
"""Check the sample drop in a smoke run (D50-D54): the table that standalone Max wrote after the drop
(OUTDIR/atab_after_drop.wav, buffer~ ---atab, 5 channels x 1024) against what the test file should give.

- hybrid: drop_fit.wav (4096 frames, stereo, 4 cycles) in FIT -> every row = 4 cycles, peak-normalised,
  sampled at the cell centres (frame 4 i + 1.5); tolerance 0.01 inside, 0.05 in the 8 cells at each end
- b: drop_one.wav (1000 frames, mono) in 1:1 -> cells 0..499 = 0.75, 500..999 = 0, 1000..1023 = 0.5
- all five rows equal; the rows inside the default Size span (cells 0..101) prove that Freeze held

Usage: uv run --project tools python devices/aliasing/test/smoke/check_drop.py OUTDIR hybrid|b
Exit 0 when the table matches, 1 otherwise.
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import soundfile as sf


def expected(face: str) -> np.ndarray:
    i = np.arange(1024)
    if face == "hybrid":
        x = np.sin(2 * np.pi * 4 * (4 * i + 1.5) / 4096)
        return 0.5 + 0.5 * x / np.abs(x).max()
    return np.where(i < 500, 0.75, np.where(i < 1000, 0.0, 0.5))


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[1] not in ("hybrid", "b"):
        print(__doc__)
        return 2
    out, face = Path(argv[0]), argv[1]
    f = out / "atab_after_drop.wav"
    if not f.is_file():
        print(f"check_drop: FAIL no {f} (the drop or the writewave step did not run)")
        return 1
    tab, _ = sf.read(str(f), always_2d=True)
    if tab.shape != (1024, 5):
        print(f"check_drop: FAIL table shape {tab.shape}, want (1024, 5)")
        return 1
    want = expected(face)
    errs = []
    for v in range(5):
        d = np.abs(tab[:, v] - want)
        inner = d[8:-8].max() if face == "hybrid" else d.max()
        edge = d.max()
        ok = inner < (0.01 if face == "hybrid" else 1e-3) and edge < 0.05
        errs.append(ok)
        print(f"check_drop: voice {v + 1}: max error {inner:.5f} inside, {edge:.5f} overall, "
              f"span 0..101 {d[:102].max():.5f} -> {'ok' if ok else 'FAIL'}")
    ok = all(errs)
    print(f"check_drop: {face} {'OK' if ok else 'FAIL'} ({'FIT, drop_fit.wav' if face == 'hybrid' else '1:1, drop_one.wav'})")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
