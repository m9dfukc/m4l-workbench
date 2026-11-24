#!/usr/bin/env python3
"""Generate ProbeUI.amxd, the UI/storage probe for the aliasing face rebuild (checks G-UI1, G-UI5).

Starts from Live's blank audio effect template (Max Audio Effect.amxd), keeps its plugin~ -> plugout~
pass-through and adds:
  - live.dial "Probe Dial" drawn by probe_dial_painter.js (jspainterfile)
  - live.tab  "Probe Tab"  drawn by probe_tab_painter.js  (jspainterfile)
  - buffer~ ---probetab (5 x 1024), v8 probe_store.js, Scramble / Verify buttons, and two Blob
    parameters (Stored Only) that keep the table with the Live Set: variant A, pattr "Probe Table"
    holding a 5120-float list; variant B, dict ---probedict "Probe Table Dict" holding the table as
    JSON (the pattern of Ableton's Variations / Performer / Vector devices).

Box JSON follows real Max-saved boxes (tools: m4l-boxref live.dial / live.tab / pattr / dict / live.text).
Stdlib only; reuses read_amxd / write_amxd / Patch / valueof from devices/aliasing/scripts/bootstrap_shell.py.

Usage: python3 devices/aliasing/test/probe-ui/make_probe.py [--template PATH] [--out PATH] [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # no __pycache__ next to bootstrap_shell.py
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from bootstrap_shell import (  # noqa: E402
    MOD_ABSOLUTE, MOD_BIPOLAR, T_ENUM, T_FLOAT, U_FLOAT, Patch, read_amxd, valueof, write_amxd,
)

MAX_DEVICES = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices")
TEMPLATE = MAX_DEVICES / "Max Audio Effect.amxd"
FALLBACK_TEMPLATE = MAX_DEVICES / "Max Instrument.amxd"
FONT = "Ableton Sans Medium"
FONT_BOLD = "Ableton Sans Bold"
T_BLOB = 3  # parameter_type Blob (m4l-ref/parameters.maxref.xml; Ableton's Waveshaper "pattr wave")
STORED_ONLY = 1  # parameter_invisible


def build(template: dict) -> dict:
    pat = template["patcher"]
    p = Patch()
    # keep the template's plugin~ / plugout~ and their two cords (audio passes through untouched)
    io = [b for b in pat["boxes"] if b["box"].get("text") in ("plugin~", "plugout~")]
    plugout = next((b["box"]["id"] for b in io if b["box"]["text"] == "plugout~"), None)
    plugin = next((b["box"]["id"] for b in io if b["box"]["text"] == "plugin~"), None)
    if plugin is None:  # instrument template fallback: add a plugin~ like the audio effect template's
        plugin = "obj-plugin"
        io.append({"box": {"id": plugin, "maxclass": "newobj", "text": "plugin~", "numinlets": 2, "numoutlets": 2,
                           "outlettype": ["signal", "signal"], "patching_rect": [48.0, 34.0, 53.0, 20.0]}})
    p.boxes.extend(io)
    for ch in (0, 1):
        p.wire(plugin, ch, plugout, ch)

    def comment(text: str, prect: list[float], x: float, y: float, bold: bool = False, size: float = 9.0,
                varname: str | None = None) -> str:
        box = {"maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": [x, y, prect[2], prect[3]], "presentation": 1, "presentation_rect": prect,
               "fontname": FONT_BOLD if bold else FONT, "fontsize": size}
        if prect[3] > 16:
            box["linecount"] = max(1, round(prect[3] / 12))
        if varname:
            box["varname"] = varname
        return p.add(box)

    def button(text: str, varname: str, prect: list[float], x: float, y: float) -> str:
        # live.text in button mode (mode 0) without a parameter: bangs on click (transition 0->1)
        return p.add({"maxclass": "live.text", "numinlets": 1, "numoutlets": 2, "outlettype": ["", ""],
                      "parameter_enable": 0, "mode": 0, "text": text, "texton": text, "varname": varname,
                      "fontname": FONT, "fontsize": 9.0, "patching_rect": [x, y, prect[2], prect[3]],
                      "presentation": 1, "presentation_rect": prect})

    # --- face ---------------------------------------------------------------------------------
    comment("UI probe: painted live.* (G-UI1) + table storage (G-UI5)", [8.0, 3.0, 344.0, 14.0], 400.0, 20.0,
            bold=True)
    dial_info = "Painted live.dial. Automate, modulate or macro-map it: the aut/mod/mac row must light up."
    dial = p.add({
        "maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
        "parameter_enable": 1, "jspainterfile": "probe_dial_painter.js",
        "patching_rect": [400.0, 60.0, 96.0, 92.0], "presentation": 1, "presentation_rect": [8.0, 20.0, 96.0, 92.0],
        "varname": "probe_dial", "showname": 0, "shownumber": 0, "annotation": dial_info,
        "saved_attribute_attributes": {"valueof": valueof(
            "Probe Dial", "Probe Dial", T_FLOAT, mmin=0.0, mmax=1.0, initial=0.5, unitstyle=U_FLOAT,
            modmode=MOD_BIPOLAR, info=dial_info)},
    })
    tab_info = "Painted live.tab: pill segmented control with waveform icons."
    tab = p.add({
        "maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
        "parameter_enable": 1, "jspainterfile": "probe_tab_painter.js",
        "patching_rect": [520.0, 60.0, 136.0, 24.0], "presentation": 1, "presentation_rect": [116.0, 24.0, 136.0, 24.0],
        "varname": "probe_tab", "num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0,
        "fontname": FONT, "fontsize": 9.0, "annotation": tab_info,
        "saved_attribute_attributes": {"valueof": valueof(
            "Probe Tab", "Probe Tab", T_ENUM, enum=["Sine", "Tri", "Saw", "Square"], modmode=MOD_ABSOLUTE,
            info=tab_info)},
    })
    comment("Probe Tab (painted live.tab)", [116.0, 50.0, 136.0, 13.0], 520.0, 90.0)
    scramble = button("Scramble", "scramble", [116.0, 70.0, 64.0, 18.0], 520.0, 130.0)
    verify = button("Verify", "verify", [188.0, 70.0, 64.0, 18.0], 600.0, 130.0)
    status = comment("status: waiting for init", [116.0, 92.0, 236.0, 26.0], 400.0, 420.0, varname="status")
    comment("Open the Max console. Switch Live's theme (repaint?), automate/modulate the dial. "
            "Scramble, save the Set, close, reopen: STORE and RESTORE checksums must match (README.md).",
            [8.0, 122.0, 344.0, 40.0], 400.0, 470.0)

    # --- storage ------------------------------------------------------------------------------
    p.obj("buffer~ ---probetab @samps 1024 5", 40.0, 200.0, 1, ["float", "bang"])
    store = p.obj("v8 probe_store.js ---probetab ---probedict", 40.0, 330.0, 2, ["", "", ""], w=260.0,
                  saved_object_attributes={"embed": 0, "parameter_enable": 0},
                  textfile={"filename": "probe_store.js", "flags": 0, "embed": 0, "autowatch": 1})
    thisdev = p.obj("live.thisdevice", 40.0, 240.0, 1, ["bang", "int", "int"])
    init_t = p.obj("t b b", 40.0, 270.0, 1, ["bang", "bang"])
    init_msg = p.msg("init", 40.0, 300.0)
    name_msg = p.msg("bufname ---probetab, dictname ---probedict", 100.0, 300.0)
    p.wire(thisdev, 0, init_t, 0)
    p.wire(init_t, 1, name_msg, 0)  # right to left: names first (backup for the box args), then init
    p.wire(init_t, 0, init_msg, 0)
    p.wire(name_msg, 0, store, 0)
    p.wire(init_msg, 0, store, 0)
    scr_msg = p.msg("scramble", 520.0, 160.0)
    ver_msg = p.msg("verify", 600.0, 160.0)
    p.wire(scramble, 0, scr_msg, 0)
    p.wire(verify, 0, ver_msg, 0)
    p.wire(scr_msg, 0, store, 0)
    p.wire(ver_msg, 0, store, 0)

    def blob_valueof(longname: str) -> dict:
        # Blob parameter, Stored Only: saved with the Set and presets, not automatable
        # (user guide parameter_mode / m4l live_parameters "Parameter Data Types")
        return {"valueof": {"parameter_longname": longname, "parameter_shortname": longname,
                            "parameter_type": T_BLOB, "parameter_invisible": STORED_ONLY,
                            "parameter_initial_enable": 0, "parameter_modmode": 0}}

    # variant A: same box shape as Ableton's Waveshaper "pattr wave" / Step Arp "pattr"
    plist = p.add({"maxclass": "newobj", "text": "pattr probetable", "numinlets": 1, "numoutlets": 3,
                   "outlettype": ["", "", ""], "patching_rect": [40.0, 380.0, 110.0, 22.0], "varname": "probetable",
                   "saved_object_attributes": {"parameter_enable": 1, "parameter_mappable": 0},
                   "saved_attribute_attributes": blob_valueof("Probe Table")})
    # variant B: same box shape as Ableton's Variations "dict ---presets_params" (Max 9.0.7)
    pdict = p.add({"maxclass": "newobj", "text": "dict ---probedict", "numinlets": 2, "numoutlets": 5,
                   "outlettype": ["dictionary", "", "", "", ""], "patching_rect": [220.0, 380.0, 120.0, 22.0],
                   "varname": "probedict",
                   "saved_object_attributes": {"embed": 0, "legacy": 1, "parameter_enable": 1,
                                               "parameter_mappable": 0},
                   "saved_attribute_attributes": blob_valueof("Probe Table Dict")})
    p.wire(store, 0, plist, 0)
    p.wire(store, 1, pdict, 0)
    p.wire(plist, 0, store, 1)  # echo after a store, recall when Live restores the Set
    p.wire(pdict, 0, store, 1)
    p.wire(store, 2, status, 0)  # "set <text>"

    _ = (dial, tab)  # parameters only; nothing downstream
    new = dict(pat)
    new["boxes"] = p.boxes
    new["lines"] = p.lines
    new["openinpresentation"] = 1
    new["devicewidth"] = 360.0
    new["rect"] = [100.0, 100.0, 760.0, 560.0]
    new["title"] = "ProbeUI"
    new["description"] = "UI probe for the aliasing face: jspainter live.dial / live.tab and Blob table storage."
    new["default_fontname"] = FONT
    new["default_fontsize"] = 9.0
    new["dependency_cache"] = []
    return {"patcher": new}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=None,
                    help="Live's Max Audio Effect.amxd (default; Max Instrument.amxd if it is missing)")
    ap.add_argument("--out", type=Path, default=HERE / "ProbeUI.amxd", help="output .amxd")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    args = ap.parse_args(argv)
    if args.out.exists() and not args.force:
        print(f"make_probe: {args.out} exists; use --force to overwrite (ask first whether it is open in Max)",
              file=sys.stderr)
        return 3
    template = args.template
    if template is None:
        template = TEMPLATE if TEMPLATE.exists() else FALLBACK_TEMPLATE
        if template is FALLBACK_TEMPLATE:
            print(f"make_probe: {TEMPLATE} missing, using the instrument template", file=sys.stderr)
    head, patch = read_amxd(template)
    if not head.startswith(b"ampf") or not (b"aaaa" in head[:16] or b"iiii" in head[:16]):
        print(f"make_probe: {template} is not an audio effect / instrument .amxd", file=sys.stderr)
        return 2
    write_amxd(args.out, head, build(patch))
    print(f"wrote {args.out} (from {template.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
