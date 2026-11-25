#!/usr/bin/env python3
"""Smoke-test patch for standalone Max: one face's own boxes (v0.3b: hybrid = Aliasing.amxd, b =
Aliasing B.amxd, from scripts/bootstrap_shell.py) with plugout~ replaced by sfrecord~, plus a runner that
switches to the NonRealTime driver, records a few seconds while it pages through the face, flips modes,
write shapes and states, section switches, the strip target (face b) and a few matrix cells (Voice /
Read Osc / Env feedback), restores the audio driver and quits Max. Written to OUTDIR/smoke.maxpat next to
copies of the runtime files.

Never Live, never the user's patches, no sound (NonRealTime driver). See run_smoke.sh.

Usage: python3 devices/aliasing/test/smoke/make_smoke.py OUTDIR DRIVER [hybrid|b]
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
    if len(argv) not in (2, 3):
        print(__doc__)
        return 2
    out = Path(argv[0]).resolve()
    driver = argv[1]
    face = argv[2] if len(argv) == 3 else "hybrid"
    out.mkdir(parents=True, exist_ok=True)
    for f in list(DEVICE.glob("aliasing*.js")) + [DEVICE / "aliasing.gendsp",
                                                    DEVICE / "test" / "probe-ui" / "probe_dial_painter.js"]:
        shutil.copy2(f, out / f.name)

    _, tmpl = bs.read_amxd(bs.TEMPLATE)
    dev = bs.build(tmpl, face)["patcher"]
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
    init_bufs = msg("buffers ---atab ---aheads ---atable", x0 + 600, y0 + 60)
    wire(lb, 0, seq, 0)
    wire(seq, 2, init_bufs, 0)
    wire(init_bufs, 0, by_var["display"], 0)
    wire(seq, 1, start, 0)
    wire(seq, 0, open_, 0)
    wire(open_, 0, rec, 0)
    # timeline (scheduler time): page / mode flips while recording, then stop, restore, quit
    common = [
        (1200, "w_mode", "1"), (1500, "r_mode", "1"), (2600, "w_mode", "0"), (2800, "r_mode", "0"),
        (3000, "out_gate", "1"), (3300, "out_gate", "0"),
        # write shapes (D34) and states, feedback sources in the matrix (D36)
        (900, "w_shape", "2"), (1300, "w_shape", "4"), (1600, "w_active", "2"), (2000, "w_active", "1"),
        (1100, "mod_vo_wp", "50"), (1400, "mod_ro_sz", "60"), (1900, "mod_en_ou", "-50"), (2200, "mod_l1_wa", "-80"),
    ]
    if face == "hybrid":
        steps = common + [
            (800, "page", "2"), (1800, "page", "3"), (2100, "lfo_l1mode", "1"), (2300, "page", "0"),
            (3500, "page", "1"), (3700, "tone_res_track", "0"), (1000, "tone_res_on", "1"), (1700, "out_lim_on", "0"),
            (2400, "out_lim_on", "1"), (2500, "tone_band_on", "0"), (2700, "out_syncrate", "6"),
        ]
    else:
        steps = common + [
            (800, "page", "3"), (1000, "page", "4"), (1800, "page", "6"), (2100, "lfo1_l1mode", "1"),
            (2300, "page", "0"), (3500, "page", "5"), (3700, "res_res_track", "0"), (1050, "res_res_on", "1"),
            (1700, "lim_lim_on", "0"), (2400, "lim_lim_on", "1"), (2500, "band_band_on", "0"),
            (1150, "mod_target", "5"), (2250, "mod_target", "8"), (2700, "out_syncrate", "6"), (3100, "page", "2"),
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
