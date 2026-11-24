#!/usr/bin/env python3
"""One-time bootstrap of the Aliasing shell (devices/aliasing/Aliasing.amxd), v0.1.

Starts from Live's own instrument template (Max Instrument.amxd), keeps its patcher settings and
plugout~, and adds the v0.1 objects: MIDI gate (notein -> borax), Sync (copies the read pitch/fine
to the write dials, then a click~ restarts the phases), the gen~ core with its two buffer~s, the
v8ui table display, the v8 page switcher and the live.* parameters with the presentation layout
from docs/gui.md. Box JSON follows real Max-saved boxes (tools: m4l-boxref).

After the first bootstrap the unfrozen Aliasing.amxd is the source of truth (the user edits it
in Max). This script therefore refuses to overwrite an existing file unless --force is given,
and --force would discard every edit made in Max since.

v0.1 scope: no Tone page controls (v0.2: only a placeholder text), no preset menu (v0.3).

Usage: python3 devices/aliasing/scripts/bootstrap_shell.py [--template PATH] [--out PATH] [--force]
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICE = HERE.parent
TEMPLATE = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Instrument.amxd")

WRITE = [1.0, 0.360784313725490, 0.541176470588235, 1.0]  # #ff5c8a
READ = [0.235294117647059, 0.776470588235294, 0.941176470588235, 1.0]  # #3cc6f0
FONT = "Ableton Sans Medium"
FONT_BOLD = "Ableton Sans Bold"

# unit styles / modulation modes / visibility (Max refpage m4l-ref/parameters.maxref.xml)
U_INT, U_FLOAT, U_HZ, U_DB, U_PCT, U_ST, U_CUSTOM = 0, 1, 3, 4, 5, 7, 9
MOD_NONE, MOD_BIPOLAR, MOD_ABSOLUTE = 0, 2, 4
T_FLOAT, T_INT, T_ENUM = 0, 1, 2
STORED_ONLY = 1


class Patch:
    def __init__(self) -> None:
        self.boxes: list[dict] = []
        self.lines: list[dict] = []
        self.n = 100

    def add(self, box: dict) -> str:
        self.n += 1
        box = {"id": f"obj-{self.n}", **box}
        self.boxes.append({"box": box})
        return box["id"]

    def obj(self, text: str, x: float, y: float, nin: int, outs: list[str], w: float = 0, **extra) -> str:
        return self.add({"maxclass": "newobj", "text": text, "numinlets": nin, "numoutlets": len(outs),
                         "outlettype": outs, "patching_rect": [x, y, w or max(40.0, 7.0 * len(text)), 22.0],
                         **extra})

    def msg(self, text: str, x: float, y: float) -> str:
        return self.add({"maxclass": "message", "text": text, "numinlets": 2, "numoutlets": 1,
                         "outlettype": [""], "patching_rect": [x, y, max(40.0, 7.0 * len(text)), 22.0]})

    def wire(self, src: str, outlet: int, dst: str, inlet: int) -> None:
        self.lines.append({"patchline": {"source": [src, outlet], "destination": [dst, inlet]}})


def valueof(longname: str, shortname: str, ptype: int, *, mmin: float | None = None, mmax: float | None = None,
            initial: float = 0, unitstyle: int = U_FLOAT, modmode: int = MOD_NONE, enum: list[str] | None = None,
            units: str | None = None, exponent: float | None = None, info: str = "",
            invisible: int | None = None) -> dict:
    v: dict = {"parameter_longname": longname, "parameter_shortname": shortname, "parameter_type": ptype,
               "parameter_initial_enable": 1, "parameter_initial": [initial], "parameter_unitstyle": unitstyle,
               "parameter_modmode": modmode, "parameter_linknames": 0}
    if mmin is not None:
        v["parameter_mmin"] = mmin
    if mmax is not None:
        v["parameter_mmax"] = mmax
    if enum is not None:
        v["parameter_enum"] = enum
        v["parameter_mmax"] = len(enum) - 1
    if units is not None:
        v["parameter_units"] = units
    if exponent is not None:
        v["parameter_exponent"] = exponent
    if info:
        v["parameter_info"] = info
    if invisible is not None:
        v["parameter_invisible"] = invisible
    return v


def colors(**fixed: list[float]) -> tuple[dict, dict]:
    """Fixed (non-theme) colours plus their saved_attribute_attributes entries."""
    return fixed, {k: {"expression": ""} for k in fixed}


def build(template: dict) -> dict:
    pat = template["patcher"]
    plugout = next(b["box"] for b in pat["boxes"] if b["box"].get("text") == "plugout~")
    p = Patch()
    p.boxes.append({"box": {**plugout, "id": "obj-plugout", "patching_rect": [40.0, 620.0, 120.0, 22.0]}})

    def ui(maxclass: str, varname: str, rect: list[float], prect: list[float], vo: dict | None, nin: int,
           outs: list[str], cols: tuple[dict, dict] = ({}, {}), **extra) -> str:
        box = {"maxclass": maxclass, "numinlets": nin, "numoutlets": len(outs), "outlettype": outs,
               "patching_rect": rect, "presentation": 1, "presentation_rect": prect, "varname": varname, **extra}
        fixed, saa = cols
        box.update(fixed)
        if vo is not None:
            box["parameter_enable"] = 1
            box["saved_attribute_attributes"] = {**saa, "valueof": vo}
            if vo.get("parameter_info"):
                box["annotation"] = vo["parameter_info"]
        elif saa:
            box["saved_attribute_attributes"] = saa
        return p.add(box)

    def dial(varname: str, prect: list[float], vo: dict, x: float, y: float, accent: list[float] | None = None) -> str:
        cols = colors(activedialcolor=accent) if accent else ({}, {})
        return ui("live.dial", varname, [x, y, 44.0, 47.0], prect, vo, 1, ["", "float"], cols,
                  fontname=FONT, fontsize=9.0, showname=1, shownumber=1)

    def toggle(varname: str, prect: list[float], vo: dict, x: float, y: float, text: str, mode: int = 1,
               accent: list[float] | None = None) -> str:
        cols = colors(activebgoncolor=accent) if accent else ({}, {})
        return ui("live.text", varname, [x, y, prect[2], prect[3]], prect, vo, 1, ["", ""], cols,
                  fontname=FONT, fontsize=9.0, mode=mode, text=text, texton=text)

    def tab(varname: str, prect: list[float], vo: dict, x: float, y: float, rows: int,
            accent: list[float] | None = None) -> str:
        cols = colors(activebgoncolor=accent) if accent else ({}, {})
        return ui("live.tab", varname, [x, y, prect[2], prect[3]], prect, vo, 1, ["", "", "float"], cols,
                  fontname=FONT, fontsize=9.0, num_lines_patching=rows, num_lines_presentation=rows, multiline=0)

    def label(text: str, prect: list[float], x: float, y: float, color: list[float] | None = None,
              bold: bool = True, varname: str | None = None) -> str:
        box = {"maxclass": "comment", "text": text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": [x, y, prect[2] + 20, 18.0], "presentation": 1, "presentation_rect": prect,
               "fontname": FONT_BOLD if bold else FONT, "fontsize": 9.0}
        if color:
            box["textcolor"] = color
        if varname:
            box["varname"] = varname
        return p.add(box)

    def line(prect: list[float], x: float, y: float) -> str:
        return p.add({"maxclass": "live.line", "numinlets": 1, "numoutlets": 0,
                      "patching_rect": [x, y, prect[2], prect[3]], "presentation": 1, "presentation_rect": prect})

    # --- core: gen~, buffers, output -----------------------------------------------------------
    gen = p.obj("gen~ @gen aliasing @atab ---atab @aheads ---aheads", 40.0, 560.0, 2, ["signal", "signal"], w=330.0)
    p.obj("buffer~ ---atab @samps 1024 5", 420.0, 560.0, 1, ["float", "bang"])
    p.obj("buffer~ ---aheads @samps 5 3", 420.0, 590.0, 1, ["float", "bang"])
    p.wire(gen, 0, "obj-plugout", 0)
    p.wire(gen, 1, "obj-plugout", 1)

    def param_to_gen(src: str, name: str, x: float, y: float) -> str:
        pre = p.obj(f"prepend {name}", x, y, 1, [""])
        p.wire(src, 0, pre, 0)
        p.wire(pre, 0, gen, 0)
        return pre

    # --- MIDI gate: any held note gates Activate (OR inside gen~) ------------------------------
    notein = p.obj("notein", 40.0, 20.0, 1, ["int", "int", "int"])
    borax = p.obj("borax", 40.0, 60.0, 3, ["int"] * 9, w=110.0)
    held = p.obj("> 0", 40.0, 100.0, 2, ["int"])
    sig = p.obj("sig~", 40.0, 140.0, 1, ["signal"])
    p.wire(notein, 0, borax, 0)
    p.wire(notein, 1, borax, 1)
    p.wire(borax, 2, held, 0)
    p.wire(held, 0, sig, 0)
    p.wire(sig, 0, gen, 0)  # in1 = MIDI gate signal

    # --- global column ---------------------------------------------------------------------------
    act = toggle("activate", [8.0, 10.0, 60.0, 26.0], valueof(
        "Activate", "Activate", T_ENUM, enum=["Off", "On"], modmode=MOD_ABSOLUTE,
        info="Starts the drone: both pointers restart on activation. A held MIDI note also activates."),
        200.0, 20.0, "Activate")
    param_to_gen(act, "activate", 200.0, 60.0)

    sync = toggle("sync", [8.0, 40.0, 60.0, 15.0], valueof(
        "Sync", "Sync", T_ENUM, enum=["Off", "On"], modmode=MOD_ABSOLUTE,
        info="Copies the read Pitch and Fine to the write pointer and restarts both phases."),
        320.0, 20.0, "Sync", mode=0)
    trig = p.obj("t b b b", 320.0, 60.0, 1, ["bang", "bang", "bang"])
    click = p.obj("click~", 320.0, 100.0, 1, ["signal"])
    keep_rpitch = p.obj("f", 380.0, 100.0, 2, ["float"])
    keep_rfine = p.obj("f", 430.0, 100.0, 2, ["float"])
    p.wire(sync, 0, trig, 0)
    p.wire(trig, 2, keep_rpitch, 0)  # right to left: copy pitch, copy fine, then restart
    p.wire(trig, 1, keep_rfine, 0)
    p.wire(trig, 0, click, 0)
    p.wire(click, 0, gen, 1)  # in2 = sync impulse

    # --- write row -------------------------------------------------------------------------------
    label("WRITE", [84.0, 8.0, 80.0, 12.0], 520.0, 0.0, WRITE)
    wpitch = dial("wpitch", [84.0, 20.0, 44.0, 47.0], valueof(
        "Write Pitch", "Pitch", T_INT, mmin=-64, mmax=130, initial=71, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
        info="Write pointer pitch in semitones around note 60 (-64..130 like the original). Above about half the sample rate the written pattern depends on the sample rate (44.1 and 48 kHz sound different)."), 520.0, 20.0, WRITE)
    wfine = dial("wfine", [130.0, 20.0, 44.0, 47.0], valueof(
        "Write Fine", "Fine", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.217, unitstyle=U_CUSTOM, units="%0.3f st",
        modmode=MOD_BIPOLAR, info="Write pointer fine pitch. Small differences to the read pointer make the slow changes."),
        570.0, 20.0, WRITE)
    wshape = tab("wshape", [178.0, 22.0, 44.0, 45.0], valueof(
        "Write Shape", "W Shape", T_ENUM, enum=["Ramp", "Tri", "=Read"], initial=1, modmode=MOD_ABSOLUTE,
        info="Write pointer shape: ramp, triangle (Symmetry, wraps), or the read pointer itself."),
        620.0, 20.0, 3, WRITE)
    wactive = toggle("wactive", [226.0, 22.0, 44.0, 15.0], valueof(
        "Write Active", "W Active", T_ENUM, enum=["Off", "On"], initial=1, modmode=MOD_ABSOLUTE,
        info="Off freezes the table: only the read pointer runs."), 670.0, 20.0, "Active", accent=WRITE)
    param_to_gen(wpitch, "wpitch", 520.0, 80.0)
    param_to_gen(wfine, "wfine", 570.0, 110.0)
    param_to_gen(wshape, "wshape", 620.0, 80.0)
    param_to_gen(wactive, "wactive", 670.0, 110.0)
    p.wire(keep_rpitch, 0, wpitch, 0)
    p.wire(keep_rfine, 0, wfine, 0)

    line([84.0, 78.0, 186.0, 5.0], 520.0, 140.0)

    # --- read row --------------------------------------------------------------------------------
    label("READ", [84.0, 86.0, 80.0, 12.0], 520.0, 170.0, READ)
    rpitch = dial("rpitch", [84.0, 98.0, 44.0, 47.0], valueof(
        "Read Pitch", "Pitch", T_INT, mmin=-64, mmax=64, initial=-30, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
        info="Read pointer pitch in semitones around note 60 (coarse)."), 520.0, 190.0, READ)
    rfine = dial("rfine", [130.0, 98.0, 44.0, 47.0], valueof(
        "Read Fine", "Fine", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, unitstyle=U_CUSTOM, units="%0.3f st",
        modmode=MOD_BIPOLAR, info="Read pointer fine pitch."), 570.0, 190.0, READ)
    rshape = tab("rshape", [178.0, 100.0, 44.0, 30.0], valueof(
        "Read Shape", "R Shape", T_ENUM, enum=["Ramp", "Tri"], modmode=MOD_ABSOLUTE,
        info="Read pointer shape: ramp or triangle (Direction)."), 620.0, 190.0, 2, READ)
    smooth = toggle("smoothread", [226.0, 100.0, 44.0, 15.0], valueof(
        "Smooth", "Smooth", T_ENUM, enum=["Off", "Linear"], modmode=MOD_ABSOLUTE,
        info="Read interpolation: off reads whole cells (raw), Linear interpolates."),
        670.0, 190.0, "Smooth", accent=READ)
    param_to_gen(rpitch, "rpitch", 520.0, 250.0)
    param_to_gen(rfine, "rfine", 570.0, 280.0)
    param_to_gen(rshape, "rshape", 620.0, 250.0)
    param_to_gen(smooth, "smoothread", 670.0, 280.0)
    p.wire(rpitch, 0, keep_rpitch, 1)
    p.wire(rfine, 0, keep_rfine, 1)

    for x in (76.0, 278.0, 594.0):
        line([x - 2.0, 10.0, 5.0, 141.0], 760.0 + x / 4, 20.0)

    # --- display ---------------------------------------------------------------------------------
    disp = p.add({"maxclass": "v8ui", "filename": "aliasing_display.js", "embed": 0, "numinlets": 1,
                  "numoutlets": 2, "outlettype": ["", ""], "parameter_enable": 0,
                  "patching_rect": [40.0, 320.0, 300.0, 134.0], "presentation": 1,
                  "presentation_rect": [286.0, 8.0, 300.0, 134.0], "varname": "display",
                  "textfile": {"filename": "aliasing_display.js", "flags": 0, "embed": 0, "autowatch": 1}})
    label("Size", [286.0, 147.0, 26.0, 13.0], 360.0, 320.0, bold=False)
    size = ui("live.slider", "size", [360.0, 340.0, 180.0, 15.0], [312.0, 146.0, 180.0, 15.0], valueof(
        "Size", "Size", T_FLOAT, mmin=0.001, mmax=1.0, initial=0.1, unitstyle=U_FLOAT, exponent=2.0,
        modmode=MOD_BIPOLAR, info="Pointer span: both pointers cover only this part of the table. Also draggable in the display."),
        1, ["", "float"], orientation=1, showname=0, shownumber=1, relative=1, fontname=FONT, fontsize=9.0)
    dmode = tab("display_mode", [496.0, 146.0, 56.0, 15.0], valueof(
        "Display Mode", "Disp Mode", T_ENUM, enum=["Line", "2D"], invisible=STORED_ONLY,
        info="Table display: Line or 2D. A click in the display toggles it."), 360.0, 370.0, 1)
    dshow = toggle("display_on", [556.0, 146.0, 30.0, 15.0], valueof(
        "Display", "Display", T_ENUM, enum=["Off", "On"], initial=1, invisible=STORED_ONLY,
        info="Display on/off. Off stops drawing (no UI load), the sound is not affected."),
        420.0, 370.0, "View")
    param_to_gen(size, "size", 360.0, 400.0)
    # the display gets Size as "span": v8ui swallows "size" (box size message, bug B1)
    span_pre = p.obj("prepend span", 360.0, 430.0, 1, [""])
    p.wire(size, 0, span_pre, 0)
    p.wire(span_pre, 0, disp, 0)
    mode_pre = p.obj("prepend mode", 470.0, 400.0, 1, [""])
    show_pre = p.obj("prepend display", 560.0, 400.0, 1, [""])
    p.wire(dmode, 0, mode_pre, 0)
    p.wire(mode_pre, 0, disp, 0)
    p.wire(dshow, 0, show_pre, 0)
    p.wire(show_pre, 0, disp, 0)
    p.wire(disp, 0, size, 0)  # Size dragged in the display -> the parameter (undoable gesture)
    p.wire(disp, 1, dmode, 0)  # click toggled the mode -> the stored-only tab

    # init: buffer names to the display (--- is replaced per device instance in boxes, not in JS)
    thisdev = p.obj("live.thisdevice", 40.0, 240.0, 1, ["bang", "int", "int"])
    init = p.obj("t b b", 40.0, 270.0, 1, ["bang", "bang"])
    bufmsg = p.msg("buffers ---atab ---aheads", 120.0, 290.0)
    p.wire(thisdev, 0, init, 0)
    p.wire(init, 1, bufmsg, 0)
    p.wire(bufmsg, 0, disp, 0)

    # --- paged area --------------------------------------------------------------------------------
    page = tab("page", [602.0, 8.0, 228.0, 15.0], valueof(
        "Page", "Page", T_ENUM, enum=["Mod", "Tone", "Out"], invisible=STORED_ONLY,
        info="Shows the Mod, Tone or Out controls."), 820.0, 320.0, 1)
    pages = p.obj("v8 aliasing_pages.js", 820.0, 360.0, 1, [], w=140.0,
                  saved_object_attributes={"embed": 0, "parameter_enable": 0},
                  textfile={"filename": "aliasing_pages.js", "flags": 0, "embed": 0, "autowatch": 1})
    p.wire(page, 0, pages, 0)
    p.wire(init, 0, pages, 0)  # after load: apply the stored page

    # Mod page
    label("WRITE", [602.0, 50.0, 40.0, 12.0], 820.0, 420.0, WRITE, varname="mod_wlabel")
    wsym = dial("mod_wsym", [644.0, 32.0, 44.0, 47.0], valueof(
        "Write Symmetry", "Symmetry", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR,
        info="Write triangle skew: +1 rising saw, 0 triangle, -1 falling saw."), 870.0, 420.0, WRITE)
    wlrate = dial("mod_wlforate", [736.0, 32.0, 44.0, 47.0], valueof(
        "Write LFO Rate", "LFO Rate", T_FLOAT, mmin=0.0, mmax=12.0, initial=0.0, exponent=2.0, modmode=MOD_BIPOLAR,
        info="Write pitch LFO rate; per voice F = rate * (rate + u), u = 0..1 across the voices."), 920.0, 420.0, WRITE)
    wldepth = dial("mod_wlfodepth", [782.0, 32.0, 44.0, 47.0], valueof(
        "Write LFO Depth", "LFO Depth", T_FLOAT, mmin=0.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR,
        info="Write pitch LFO depth: depth^5 semitones."), 970.0, 420.0, WRITE)
    line([602.0, 86.0, 228.0, 5.0], 820.0, 480.0)
    p.boxes[-1]["box"]["varname"] = "mod_divider"
    label("READ", [602.0, 116.0, 40.0, 12.0], 820.0, 510.0, READ, varname="mod_rlabel")
    rdir = tab("mod_rdir", [644.0, 106.0, 44.0, 30.0], valueof(
        "Read Direction", "Direction", T_ENUM, enum=["1-way", "Both"], modmode=MOD_ABSOLUTE,
        info="Read triangle: one-way (rising) or both directions."), 870.0, 510.0, 2, READ)
    rspread = dial("mod_rspread", [690.0, 98.0, 44.0, 47.0], valueof(
        "Read Spread", "Spread", T_FLOAT, mmin=0.0, mmax=6.0, initial=2.0, unitstyle=U_CUSTOM, units="%0.2f st",
        modmode=MOD_BIPOLAR, info="Read pitch spread across the 5 voices."), 920.0, 510.0, READ)
    rlrate = dial("mod_rlforate", [736.0, 98.0, 44.0, 47.0], valueof(
        "Read LFO Rate", "LFO Rate", T_FLOAT, mmin=0.0, mmax=12.0, initial=0.0, exponent=2.0, modmode=MOD_BIPOLAR,
        info="Read pitch LFO rate; per voice F = rate * (rate + u)."), 970.0, 510.0, READ)
    rldepth = dial("mod_rlfodepth", [782.0, 98.0, 44.0, 47.0], valueof(
        "Read LFO Depth", "LFO Depth", T_FLOAT, mmin=0.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR,
        info="Read pitch LFO depth: depth^5 semitones."), 1020.0, 510.0, READ)
    for src, name, x in ((wsym, "wsym", 870.0), (wlrate, "wlforate", 920.0), (wldepth, "wlfodepth", 970.0)):
        param_to_gen(src, name, x, 470.0)
    for src, name, x in ((rdir, "rdir", 870.0), (rspread, "rspread", 920.0), (rlrate, "rlforate", 970.0),
                         (rldepth, "rlfodepth", 1020.0)):
        param_to_gen(src, name, x, 560.0)

    # Tone page (v0.2)
    label("Tone section (notch, filters, drive): v0.2", [607.0, 70.0, 220.0, 13.0], 1080.0, 420.0, bold=False,
          varname="tone_note")

    # Out page
    transpose = dial("out_transpose", [607.0, 50.0, 44.0, 47.0], valueof(
        "Transpose", "Transpose", T_INT, mmin=-12, mmax=12, initial=0, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
        info="Transposes both pointers."), 1080.0, 470.0)
    width = dial("out_width", [665.0, 50.0, 44.0, 47.0], valueof(
        "Width", "Width", T_FLOAT, mmin=0.0, mmax=2.0, initial=1.0, modmode=MOD_BIPOLAR,
        info="Stereo spread of the 5 voices: 0 mono, 1 even, 2 extreme."), 1130.0, 470.0)
    output = dial("out_output", [723.0, 50.0, 44.0, 47.0], valueof(
        "Output", "Output", T_FLOAT, mmin=-36.0, mmax=0.0, initial=-6.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Output level (the 5-voice sum is already compensated by -14 dB)."), 1180.0, 470.0)
    for src, name, x in ((transpose, "transpose", 1080.0), (width, "width", 1130.0), (output, "output", 1180.0)):
        param_to_gen(src, name, x, 530.0)
    for k, outlet in enumerate((0, 1)):
        m = p.add({"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2, "outlettype": ["float", "int"],
                   "patching_rect": [1240.0 + 24 * k, 470.0, 17.0, 116.0], "presentation": 1,
                   "presentation_rect": [790.0 + 19 * k, 32.0, 17.0, 116.0], "varname": f"out_meter{'LR'[k]}"})
        p.wire(gen, outlet, m, 0)
    label("5 voices · drone · MIDI note gates Activate", [607.0, 118.0, 170.0, 11.0], 1080.0, 600.0,
          bold=False, varname="out_info")

    # Start on page Mod: Tone/Out objects hidden until aliasing_pages.js applies the stored Page.
    for entry in p.boxes:
        if str(entry["box"].get("varname", "")).startswith(("tone_", "out_")):
            entry["box"]["hidden"] = 1

    new = dict(pat)
    new["boxes"] = p.boxes
    new["lines"] = p.lines
    new["openinpresentation"] = 1
    new["devicewidth"] = 834.0
    new["rect"] = [100.0, 100.0, 1320.0, 700.0]
    new["title"] = "Aliasing"
    new["description"] = ("Aliasing v0.1: a 5-voice drone where a table is written and read at different speeds. "
                          "Inspired by 'aliasing Synth' by Dietrich Pank (Reaktor User Library #5241, 2008).")
    new["default_fontname"] = FONT
    new["default_fontsize"] = 9.0
    new["dependency_cache"] = []
    return {"patcher": new}


def read_amxd(path: Path) -> tuple[bytes, dict]:
    data = path.read_bytes()
    i = data.index(b"ptch")
    n = struct.unpack("<I", data[i + 4:i + 8])[0]
    return data[:i], json.loads(data[i + 8:i + 8 + n].rstrip(b"\x00").decode("utf-8"))


def write_amxd(path: Path, head: bytes, patch: dict) -> None:
    body = json.dumps(patch, indent="\t", ensure_ascii=False).encode("utf-8") + b"\n\x00"
    path.write_bytes(head + b"ptch" + struct.pack("<I", len(body)) + body)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=TEMPLATE, help="Live's Max Instrument.amxd")
    ap.add_argument("--out", type=Path, default=DEVICE / "Aliasing.amxd", help="output .amxd")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output (discards Max edits)")
    args = ap.parse_args(argv)
    if args.out.exists() and not args.force:
        print(f"bootstrap_shell: {args.out} exists - it is the source of truth now; use --force to overwrite",
              file=sys.stderr)
        return 3
    head, template = read_amxd(args.template)
    if not head.startswith(b"ampf") or b"iiii" not in head:
        print("bootstrap_shell: template is not an instrument .amxd", file=sys.stderr)
        return 2
    write_amxd(args.out, head, build(template))
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
