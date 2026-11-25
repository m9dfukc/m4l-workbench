#!/usr/bin/env python3
"""Smoke-test patch for standalone Max: the v0.2 device's own boxes (from scripts/bootstrap_shell.py)
with plugout~ replaced by sfrecord~, plus a runner that switches to the NonRealTime driver,
records a few seconds while it pages through the face and flips modes, restores the audio driver
and quits Max. Written to OUTDIR/smoke.maxpat next to copies of the runtime files.

Never Live, never the user's patches, no sound (NonRealTime driver). See run_smoke.sh.

Usage: python3 devices/aliasing/test/smoke/make_smoke.py OUTDIR DRIVER
       DRIVER = the audio driver to restore afterwards (e.g. "Core Audio")
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICE = HERE.parent.parent
sys.path.insert(0, str(DEVICE / "scripts"))
import bootstrap_shell as bs  # noqa: E402


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        print(__doc__)
        return 2
    out = Path(argv[0]).resolve()
    driver = argv[1]
    out.mkdir(parents=True, exist_ok=True)
    for f in list(DEVICE.glob("aliasing*.js")) + [DEVICE / "aliasing.gendsp",
                                                    DEVICE / "test" / "probe-ui" / "probe_dial_painter.js"]:
        shutil.copy2(f, out / f.name)

    _, tmpl = bs.read_amxd(bs.TEMPLATE)
    dev = bs.build(tmpl)["patcher"]
    boxes = [b for b in dev["boxes"] if b["box"]["id"] != "obj-plugout"]
    ids = {b["box"]["id"] for b in boxes}
    lines = [l for l in dev["lines"] if l["patchline"]["destination"][0] in ids]
    by_var = {b["box"].get("varname"): b["box"]["id"] for b in boxes if b["box"].get("varname")}
    gen_id = next(b["box"]["id"] for b in boxes if str(b["box"].get("text", "")).startswith("gen~ "))

    n = [900]

    def add(box: dict) -> str:
        n[0] += 1
        box = {"id": f"obj-{n[0]}", **box}
        boxes.append({"box": box})
        return box["id"]

    def obj(text: str, x: float, y: float, nin: int, outs: list[str]) -> str:
        return add({"maxclass": "newobj", "text": text, "numinlets": nin, "numoutlets": len(outs),
                    "outlettype": outs, "patching_rect": [x, y, max(60.0, 7.0 * len(text)), 22.0]})

    def msg(text: str, x: float, y: float) -> str:
        return add({"maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1, "outlettype": [""],
                    "patching_rect": [x, y, max(60.0, 7.0 * len(text)), 22.0]})

    def wire(s: str, o: int, d: str, i: int) -> None:
        lines.append({"patchline": {"source": [s, o], "destination": [d, i]}})

    x0, y0 = 1500.0, 40.0
    rec = obj("sfrecord~ 2", x0, y0 + 400, 2, ["signal"])
    wire(gen_id, 0, rec, 0)
    wire(gen_id, 1, rec, 1)
    # a probe painter on one extra dial: posts which JS engine runs jspainter scripts (G-UI1)
    add({"maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
         "parameter_enable": 1, "jspainterfile": "probe_dial_painter.js", "varname": "smoke_probe",
         "patching_rect": [x0 + 300, y0, 96.0, 92.0], "presentation": 1, "presentation_rect": [8.0, 175.0, 96.0, 92.0],
         "saved_attribute_attributes": {"valueof": bs.valueof("Smoke Probe", "Probe", bs.T_FLOAT, mmin=0.0, mmax=1.0,
                                                              initial=0.5)}})
    lb = obj("loadbang", x0, y0, 1, ["bang"])
    seq = obj("t b b b", x0, y0 + 30, 1, ["bang", "bang", "bang"])
    start = msg("; dsp setdriver NonRealTime; dsp start", x0, y0 + 60)
    open_ = msg(f"open {out / 'smoke.wav'}, 1", x0 + 300, y0 + 60)
    init_bufs = msg("buffers ---atab ---aheads", x0 + 600, y0 + 60)
    wire(lb, 0, seq, 0)
    wire(seq, 2, init_bufs, 0)
    wire(init_bufs, 0, by_var["display"], 0)
    wire(seq, 1, start, 0)
    wire(seq, 0, open_, 0)
    wire(open_, 0, rec, 0)
    # timeline (scheduler time): page / mode flips while recording, then stop, restore, quit
    steps = [
        (800, "page", "2"), (1200, "w_mode", "1"), (1500, "r_mode", "1"), (1800, "page", "3"),
        (2100, "lfo_l1mode", "1"), (2300, "page", "0"), (2600, "w_mode", "0"), (2800, "r_mode", "0"),
        (3000, "out_gate", "1"), (3300, "out_gate", "0"), (3500, "page", "1"), (3700, "tone_res_track", "0"),
    ]
    for k, (t, var, val) in enumerate(steps):
        d = obj(f"delay {t}", x0, y0 + 120 + 30 * k, 2, ["bang"])
        m = msg(val, x0 + 120, y0 + 120 + 30 * k)
        wire(lb, 0, d, 0)
        wire(d, 0, m, 0)
        wire(m, 0, by_var[var], 0)
    stop = obj("delay 4500", x0 + 300, y0 + 120, 2, ["bang"])
    stop_t = obj("t b b", x0 + 300, y0 + 150, 1, ["bang", "bang"])
    stop_rec = msg("0", x0 + 400, y0 + 180)
    stop_dsp = msg(f'; dsp stop; dsp setdriver "{driver}"', x0 + 300, y0 + 210)
    quit_d = obj("delay 1500", x0 + 300, y0 + 240, 2, ["bang"])
    quit_m = msg("; max clean; max quit", x0 + 300, y0 + 270)
    wire(lb, 0, stop, 0)
    wire(stop, 0, stop_t, 0)
    wire(stop_t, 1, stop_rec, 0)
    wire(stop_rec, 0, rec, 0)
    wire(stop_t, 0, stop_dsp, 0)
    wire(stop_t, 0, quit_d, 0)
    wire(quit_d, 0, quit_m, 0)

    pat = {"patcher": {**{k: v for k, v in dev.items() if k not in ("boxes", "lines")},
                       "boxes": boxes, "lines": lines, "rect": [40.0, 60.0, 1000.0, 320.0],
                       "openinpresentation": 1}}
    (out / "smoke.maxpat").write_text(json.dumps(pat, indent=1, ensure_ascii=False))
    print(f"wrote {out / 'smoke.maxpat'}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
