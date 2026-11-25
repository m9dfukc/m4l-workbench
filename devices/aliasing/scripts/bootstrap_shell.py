#!/usr/bin/env python3
"""Bootstrap of the Aliasing shell (devices/aliasing/Aliasing.amxd), v0.3.

Starts from Live's own instrument template (Max Instrument.amxd), keeps its patcher settings and
plugout~, and builds the v0.3 face of the mock-up (docs/v0.3-design.md D1-D30; every rect from
docs/mockup-v0.3/layout.md, which the mock-up generates): four theme-following panels, the pointer
rows (write, read) with Hz|Sync and x N / D, the v8ui display with the Size slider below it, and the
paged area LFO · Env / Mod (matrix) / Tone / Global. Every control is a real live.* parameter drawn by
a jspainter script (aliasing_paint_*.js, R5); labels are live.comment.
Logic: MIDI (notes held, note-on impulse, velocity, mod wheel), transport (plugsync~, a locked bar
phasor~), the gen~ core with its two buffer~s and the follower outlet, the v8ui display, the v8 page
switcher (also greys out idle controls and colours the panels from live.colors), and a dict Blob
parameter that stores the drawn table with the Live Set (R10). Box JSON follows real Max-saved
boxes (tools: m4l-boxref).

The unfrozen Aliasing.amxd is the source of truth once the user edits it in Max. This script
therefore refuses to overwrite an existing file unless --force is given, and --force discards
every edit made in Max since. (v0.1 -> v0.2 -> v0.3 were regenerated with --force: the shells had
no edits made in Max.)

Usage: python3 devices/aliasing/scripts/bootstrap_shell.py [--template PATH] [--out PATH] [--force]
       python3 devices/aliasing/scripts/bootstrap_shell.py --list-params   (parameter table, Markdown)
"""

from __future__ import annotations

import argparse
import json
import struct
import sys
from dataclasses import dataclass, field
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICE = HERE.parent
TEMPLATE = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Instrument.amxd")

FONT = "Ableton Sans Medium"
FONT_BOLD = "Ableton Sans Bold"
WIDTH = 968.0
VERSION = "v0.3"

# Graphite accents of the mock-up (dark theme); used as the stock colours if a painter fails.
WRITE = [0.894118, 0.894118, 0.894118, 1.0]  # #e4e4e4
READ = [0.560784, 0.65098, 0.713725, 1.0]  # #8fa6b6
NEUTRAL = [0.788235, 0.788235, 0.788235, 1.0]  # #c9c9c9
# Panel fill saved with the patch; the pages script replaces it from live.colors (D22).
PANEL_FALLBACK = [0.0, 0.0, 0.0, 0.07]

# unit styles / modulation modes / visibility (Max refpage m4l-ref/parameters.maxref.xml)
U_INT, U_FLOAT, U_MS, U_HZ, U_DB, U_PCT, U_ST, U_CUSTOM = 0, 1, 2, 3, 4, 5, 7, 9
MOD_NONE, MOD_BIPOLAR, MOD_ABSOLUTE = 0, 2, 4
T_FLOAT, T_INT, T_ENUM, T_BLOB = 0, 1, 2, 3
STORED_ONLY = 1

NOTES = ["8 bars", "4 bars", "2 bars", "1 bar", "1/2", "1/2D", "1/2T", "1/4", "1/4D", "1/4T", "1/8", "1/8D",
         "1/8T", "1/16", "1/16D", "1/16T", "1/32", "1/32T", "1/64"]  # = Data divb in the GenExpr
LFO_SHAPES = ["Sine", "Tri", "Saw", "Square", "S&H", "Random"]
W_SHAPES = ["Ramp", "Tri", "Tri ±", "Sine", "Pulse", "Pulsar", "Spike", "Noise"]  # D4, = Param wshape
# Mod matrix (D10-D14): (key, long name, short) of the sources (rows) and targets (columns); the
# columns are grouped by area as in the mock-up (write | read | table | tone | out), group index g.
SRCS = [("l1", "LFO 1", "L1"), ("l2", "LFO 2", "L2"), ("en", "Env", "Env"), ("dr", "Drift", "Drft"),
        ("ve", "Velocity", "Vel"), ("mw", "Mod Wheel", "MW"), ("vo", "Voice", "Voic"), ("nb", "Neighbour", "Nbr"),
        ("ro", "Read Osc", "ROsc")]
TGTS = [("wp", "Write Pitch", "W Pit", 0), ("sy", "Write Sym", "Sym", 0), ("wa", "Write", "Write", 0),
        ("rp", "Read Pitch", "R Pit", 1), ("sp", "Read Spread", "Sprd", 1), ("sz", "Size", "Size", 2),
        ("dv", "Drive", "Drive", 3), ("bc", "Band Center", "Ctr", 3), ("bw", "Band Width", "Wid", 3),
        ("rf", "Res Freq", "R Frq", 3), ("rb", "Res Fdbk", "R Fb", 3), ("ou", "Output", "Out", 4)]

PAINTER = {"live.dial": "aliasing_paint_dial.js", "live.tab": "aliasing_paint_tab.js",
           "live.text": "aliasing_paint_toggle.js", "live.slider": "aliasing_paint_slider.js",
           "live.menu": "aliasing_paint_menu.js", "live.numbox": "aliasing_paint_number.js"}
CELL_PAINTER = "aliasing_paint_cell.js"


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
            invisible: int | None = None, steps: int | None = None) -> dict:
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
    if steps is not None:  # D2: Live's drag resolution; int parameters get one step per value
        v["parameter_steps"] = steps
    if info:
        v["parameter_info"] = info
    if invisible is not None:
        v["parameter_invisible"] = invisible
    return v


def int_param(long: str, short: str, lo: int, hi: int, init: int, **kw) -> dict:
    return valueof(long, short, T_INT, mmin=lo, mmax=hi, initial=init, steps=hi - lo + 1, **kw)


def enum(long: str, short: str, items: list[str], init: int, info: str) -> dict:
    return valueof(long, short, T_ENUM, enum=items, initial=init, modmode=MOD_ABSOLUTE, info=info)


# ---- the page / mode visibility rule (mirror of js/src/pages_model.ts, initial state) -------------

INITIAL = {"page": 0, "wmode": 0, "rmode": 0, "l1mode": 0, "l2mode": 1, "wshape": 1}


def sym_label_of(shape: int) -> str:
    """pages_model.ts symLabelOf (D6)."""
    k = round(shape)
    if k <= 0:
        return "curve"
    if k <= 3:
        return "skew"
    if k == 5:
        return "duty"
    if k == 7:
        return "smooth"
    return "width"


def visible_in(varname: str, st: dict) -> bool | None:
    parts = varname.split("_")
    if len(parts) < 2:
        return None
    area, cond = parts[0], parts[1]
    pages = ["lfo", "mod", "tone", "out"]
    if area in pages:
        ok = pages.index(area) == st["page"]
    elif area == "tbl":
        ok = st["page"] != 2
    elif area in ("w", "r"):
        ok = True
    else:
        return None
    if cond in ("free", "sync") and area in ("w", "r"):
        m = st["wmode" if area == "w" else "rmode"]
        c = (m < 0.5) if cond == "free" else (m > 0.5)
    elif cond in ("hz1", "sy1"):
        c = (st["l1mode"] < 0.5) == (cond == "hz1")
    elif cond in ("hz2", "sy2"):
        c = (st["l2mode"] < 0.5) == (cond == "hz2")
    elif cond == "symlbl" and area == "w":
        c = sym_label_of(st["wshape"]) == (parts[2] if len(parts) > 2 else "")
    else:
        c = True
    return ok and c


def visible_at_load(varname: str) -> bool | None:
    return visible_in(varname, INITIAL)


# ---- control specs ----------------------------------------------------------------------------------

@dataclass
class Ctl:
    cls: str                      # live.dial / live.tab / live.text / live.slider / live.menu / live.numbox
    var: str                      # scripting name (page / mode / role rules)
    rect: list[float]             # presentation rect (docs/mockup-v0.3/layout.md)
    vo: dict | None               # valueof (None = no parameter)
    gen: str | None = None        # gen~ Param name ("prepend <gen>")
    scale: float | None = None    # multiply before gen~ (percent -> 0..1)
    pv: str | None = None         # "pv <name>" to the display
    pages: str | None = None      # message name to the page switcher
    extra: dict = field(default_factory=dict)
    accent: list[float] | None = None
    painter: str | None = None    # jspainter file (default by class)


@dataclass
class Label:
    text: str
    rect: list[float]
    var: str
    size: float = 8.0
    bold: bool = False
    just: int = 0                 # 0 left, 1 centre
    vcenter: bool = False         # on the text line of a 13-14 px tab next to it (D23)


def r(x: float, y: float, w: float, h: float) -> list[float]:
    return [float(x), float(y), float(w), float(h)]


def controls() -> list[Ctl]:
    c: list[Ctl] = []

    def dial(var, rect, vo, gen, accent=NEUTRAL, **kw):
        c.append(Ctl("live.dial", var, rect, vo, gen, accent=accent, **kw))

    def tab(var, rect, vo, gen, rows=1, **kw):
        c.append(Ctl("live.tab", var, rect, vo, gen,
                     extra={"num_lines_patching": rows, "num_lines_presentation": rows, "multiline": 0}, **kw))

    def pill(var, rect, vo, gen, text, texton=None, **kw):
        c.append(Ctl("live.text", var, rect, vo, gen, extra={"mode": 1, "text": text, "texton": texton or text}, **kw))

    def onoff(long, short, init, info):
        return enum(long, short, ["Off", "On"], init, info)

    # ---- pointer rows (always visible); the read row sits 82 px below the write row ----
    for p, name, dy, acc in (("w", "Write", 0.0, WRITE), ("r", "Read", 82.0, READ)):
        gp = p
        tab(f"{p}_mode", r(10, 28 + dy, 52, 14), enum(f"{name} Mode", f"{name[0]} Mode", ["Hz", "Sync"], 0,
            f"{name} pointer rate: Hz = free pitch, Sync = note value x N / D at Live's tempo."),
            f"{gp}mode", pages=f"{gp}mode")
        c.append(Ctl("live.numbox", f"{p}_sync_mult", r(10, 46 + dy, 25, 14), int_param(
            f"{name} Mult", "Mult", 1, 128, 1, unitstyle=U_CUSTOM, units="×%d", modmode=MOD_ABSOLUTE,
            info=f"Sync mode: the note value's rate times N (D3), so synced {name.lower()} rates reach the audio "
                 "range."), f"{gp}mult"))
        c.append(Ctl("live.numbox", f"{p}_sync_div", r(37, 46 + dy, 25, 14), int_param(
            f"{name} Div", "Div", 1, 32, 1, unitstyle=U_CUSTOM, units="÷%d", modmode=MOD_ABSOLUTE,
            info="Sync mode: divides the rate by D (D3): odd cycle lengths such as 5/16 that drift against the "
                 "bar."), f"{gp}den"))
        info_p = (f"{name} pointer pitch in semitones around note 60 (-64..130). Above about half the sample "
                  "rate the pattern depends on the sample rate (44.1 and 48 kHz differ).")
        dial(f"{p}_free_pitch", r(66, 22 + dy, 40, 45), int_param(
            f"{name} Pitch", "Pitch", -64, 130, 0, unitstyle=U_ST, modmode=MOD_ABSOLUTE, info=info_p),
            f"{gp}pitch", accent=acc)
        dial(f"{p}_sync_note", r(66, 22 + dy, 40, 45), enum(
            f"{name} Rate", "Rate", NOTES, 13, f"Sync mode: {name.lower()} pointer note value (bars are 4/4)."),
            f"{gp}note", accent=acc)
        dial(f"{p}_fine", r(106, 22 + dy, 40, 45), valueof(
            f"{name} Fine", "Fine", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, unitstyle=U_CUSTOM,
            units="%0.3f st", modmode=MOD_BIPOLAR, steps=2001,
            info="Fine pitch in semitones; in Sync mode a detune against the tempo grid (Resync re-locks it)."),
            f"{gp}fine", accent=acc)
        if p == "w":
            dial("w_sym", r(146, 22, 40, 45), valueof(
                "Write Sym", "Sym", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR, steps=201,
                info="The write shape's parameter (D6): Curve (Ramp), Skew (Tri, Tri ±, Sine), Width (Pulse, "
                     "Spike), Duty (Pulsar), Smooth (Noise)."), "wsym", accent=acc)
            tab("w_shape", r(190, 23, 108, 32), enum(
                "Write Shape", "W Shape", W_SHAPES, 1,
                "Path of the write head (the read phase is written along it): Ramp, Tri, the original's Tri ±, "
                "Sine, Pulse (two cells), Pulsar and Spike (bursts, then no writing), Noise (random cells)."),
                "wshape", rows=2, pages="wshape")
            tab("w_active", r(190, 59, 108, 14), enum(
                "Write State", "W State", ["Freeze", "Write", "Clean"], 1,
                "Freeze keeps the table, Write lets the write head change it, Clean writes where the read pointer "
                "reads (the original's \"=read\": the plain read waveform; heals the table)."),
                "wactive", pages="wactive")
        else:
            dial("r_spread", r(146, 104, 40, 45), valueof(
                "Read Spread", "Spread", T_FLOAT, mmin=0.0, mmax=6.0, initial=2.0, unitstyle=U_CUSTOM,
                units="%0.2f st", modmode=MOD_BIPOLAR, steps=601, info="Read pitch spread across the 5 voices."),
                "rspread", accent=acc)
            tab("r_shape", r(190, 105, 108, 18), enum(
                "Read Shape", "R Shape", ["Ramp", "Tri"], 0, "Read pointer: ramp or triangle (Direction)."),
                "rshape")
            pill("r_smooth", r(190, 127, 52, 14), onoff(
                "Smooth", "Smooth", 0, "Read interpolation: off reads whole cells (raw), on is linear."),
                "smoothread", "Smooth")
            pill("r_dir", r(246, 127, 52, 14), enum(
                "Read Direction", "Direction", ["1-Way", "2-Way"], 0,
                "Read triangle: one way (rising ramp) or both ways."), "rdir", "1-Way", "2-Way")

    # ---- Size slider below the display (D9) ----
    c.append(Ctl("live.slider", "tbl_size", r(308, 145, 328, 18), valueof(
        "Size", "Size", T_FLOAT, mmin=0.1, mmax=100.0, initial=10.0, unitstyle=U_PCT, exponent=2.0,
        modmode=MOD_BIPOLAR, info="Pointer span: both pointers cover only this part of the table; the display "
                                  "zooms to it."), "size", scale=0.01, pv="size",
        extra={"orientation": 1, "relative": 1, "showname": 0, "shownumber": 0}))

    # ---- page selector (stored only) ----
    c.append(Ctl("live.tab", "page", r(646, 8, 314, 16), valueof(
        "Page", "Page", T_ENUM, enum=["LFO · Env", "Mod", "Tone", "Global"], invisible=STORED_ONLY,
        info="Shows the LFO · Env, Mod, Tone or Global controls."), None, pages="page",
        extra={"num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0}))

    # ---- LFO · Env page (R3, D16) ----
    for k in (1, 2):
        lx = 646.0 + (k - 1) * 106.0
        free_hz, sync_init, shape_init, retrig_init, phase_init, mode_init = (
            (0.15, 7, 0, 0, 0.0, 0) if k == 1 else (0.07, 3, 5, 2, 90.0, 1))
        tab(f"lfo_l{k}mode", r(lx + 50, 30, 52, 13), enum(
            f"LFO {k} Mode", f"L{k} Mode", ["Hz", "Sync"], mode_init, f"LFO {k} rate: Hz or a note value."),
            f"l{k}mode", pages=f"l{k}mode")
        tab(f"lfo_l{k}shape", r(lx, 49, 102, 16), enum(
            f"LFO {k} Shape", f"L{k} Shape", LFO_SHAPES, shape_init, f"LFO {k} waveform."), f"l{k}shape")
        dial(f"lfo_hz{k}_rate", r(lx, 83, 34, 40), valueof(
            f"LFO {k} Rate", "Rate", T_FLOAT, mmin=0.01, mmax=20.0, initial=free_hz, unitstyle=U_HZ, exponent=3.0,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate in Hz (each voice runs slightly faster or slower: Spread)."),
            f"l{k}rate")
        dial(f"lfo_sy{k}_note", r(lx, 83, 34, 40), enum(
            f"LFO {k} Sync Rate", "Rate", NOTES, sync_init, f"LFO {k} note value at Live's tempo."), f"l{k}note")
        dial(f"lfo_l{k}phase", r(lx + 34, 83, 34, 40), valueof(
            f"LFO {k} Phase", "Phase", T_FLOAT, mmin=0.0, mmax=360.0, initial=phase_init, unitstyle=U_CUSTOM,
            units="%0.0f°", modmode=MOD_BIPOLAR, steps=361, info=f"LFO {k} start phase (used on retrigger)."),
            f"l{k}phase")
        dial(f"lfo_l{k}spread", r(lx + 68, 83, 34, 40), valueof(
            f"LFO {k} Spread", "Spread", T_FLOAT, mmin=0.0, mmax=100.0, initial=50.0, unitstyle=U_PCT,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate spread across the 5 voices (100 % = +-half an octave)."),
            f"l{k}spread")
        tab(f"lfo_l{k}retrig", r(lx + 32, 137, 70, 13), enum(
            f"LFO {k} Retrig", f"L{k} Retrig", ["Off", "Note", "Bar"], retrig_init,
            f"LFO {k} restart: never, on every MIDI note-on, or on every bar while Live's transport runs."),
            f"l{k}retrig")
    dial("lfo_env_att", r(858, 83, 34, 40), valueof(
        "Env Attack", "Attack", T_FLOAT, mmin=0.1, mmax=100.0, initial=5.0, unitstyle=U_MS, exponent=3.0,
        modmode=MOD_BIPOLAR, info="Envelope follower attack (the follower reads the output before the limiter)."),
        "enatt")
    dial("lfo_env_rel", r(892, 83, 34, 40), valueof(
        "Env Release", "Release", T_FLOAT, mmin=10.0, mmax=2000.0, initial=150.0, unitstyle=U_MS, exponent=3.0,
        modmode=MOD_BIPOLAR, info="Envelope follower release."), "enrel")
    dial("lfo_env_gain", r(926, 83, 34, 40), valueof(
        "Env Gain", "Gain", T_FLOAT, mmin=-24.0, mmax=24.0, initial=12.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Envelope follower gain: the source is the follower level x this, clipped to 0..1."), "engain")

    # ---- Mod page: matrix (D10-D15, D25, D26) ----
    for row, (s, sname, sshort) in enumerate(SRCS):
        y = 42.0 + 13.0 * row
        for i, (t, tlong, tshort, g) in enumerate(TGTS):
            x = 694.0 + 21.0 * i + 3.0 * g
            c.append(Ctl("live.numbox", f"mod_{s}_{t}", r(x, y, 20, 12), valueof(
                f"{sname} > {tlong}", f"{sshort}>{tshort.replace(' ', '')}", T_FLOAT, mmin=-100.0, mmax=100.0,
                initial=0.0, unitstyle=U_PCT, modmode=MOD_BIPOLAR, steps=2001,
                info=f"Mod matrix: {sname} modulates {tlong} (depth in percent)."), f"mx_{s}_{t}",
                painter=CELL_PAINTER))

    # ---- Tone page (R16-R18, D17) ----
    # section power switches (D32, mock-up variant E): the painter draws the bold title and a power
    # symbol right after it; the whole box toggles. Widths leave room for the symbol after the title.
    def power(var, rect, long, init, text, gen, pv=None, pages=None):
        c.append(Ctl("live.text", var, rect, onoff(long, long, init, f"Switches the {text.lower()} section on "
                     "or off (off = exact bypass)."), gen, pv=pv, pages=pages,
                     extra={"mode": 1, "text": text, "texton": text}))

    power("tone_drive_on", r(646, 29, 48, 13), "Drive On", 1, "DRIVE", "drvon", pages="drvon")
    dial("tone_drive", r(648, 56, 36, 36), valueof(
        "Drive", "Drive", T_FLOAT, mmin=0.0, mmax=24.0, initial=0.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Saturation before the band (tanh); 0 dB = clean."), "drive")
    power("tone_band_on", r(698, 29, 48, 13), "Band On", 1, "BAND", "bandon", pv="bandon", pages="bandon")
    band = [("center", "Band Center", "Center", 20.0, 20000.0, 632.0, U_HZ, None, 4.0, "bcenter",
             "Band centre frequency (Spread fans it across the voices)."),
            ("width", "Band Width", "Width", 0.2, 10.0, 10.0, U_CUSTOM, "%0.1f oct", None, "bwidth",
             "Band width in octaves; 10 = open (practically bypass)."),
            ("res", "Band Res", "Res", 0.0, 100.0, 0.0, U_PCT, None, None, "bres", "Resonance at the band edges."),
            ("fm", "Band FM", "FM", 0.0, 100.0, 0.0, U_PCT, None, None, "bfm",
             "Audio-rate FM of the band centre from the unfiltered core signal (100 % = +-4 octaves)."),
            ("spread", "Band Spread", "Spread", 0.0, 100.0, 25.0, U_PCT, None, None, "bspread",
             "Band centres across the 5 voices (100 % = +-2 octaves).")]
    for k, (key, long, short, lo, hi, init, us, units, expo, gen, info) in enumerate(band):
        dial(f"tone_band_{key}", r(698 + 36 * k, 56, 36, 36), valueof(
            long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, units=units, exponent=expo,
            modmode=MOD_BIPOLAR, info=info), gen, accent=WRITE,
            pv={"center": "center", "width": "bwidth", "res": "bres"}.get(key))
    tab("tone_band_mode", r(884, 58, 76, 13), enum(
        "Band Mode", "B Mode", ["Pass", "Reject"], 0, "Pass keeps the band, Reject removes it (band-stop)."),
        "bmode", pv="bmode")
    tab("tone_band_slope", r(884, 75, 76, 13), enum(
        "Band Slope", "B Slope", ["12", "24 dB"], 1, "Band edge slope: 12 or 24 dB per octave."),
        "bslope", pv="bslope")
    power("tone_res_on", r(646, 98, 80, 13), "Res On", 0, "RESONATOR", "reson", pv="reson", pages="reson")
    pill("tone_res_track", r(730, 98, 64, 13), onoff(
        "Res Track", "Track", 1, "Resonator follows each voice's read pointer frequency."),
        "rstrack", "Track Read", pv="rstrack", pages="track")
    res = [("freq", "Res Freq", "Freq", 20.0, 5000.0, 140.0, U_HZ, 3.0, "rsfreq",
            "Resonator frequency (inactive while Track follows the read pointer)."),
           ("fb", "Res Feedback", "Fdbk", -95.0, 95.0, 50.0, U_PCT, None, "rsfb",
            "Resonator feedback: + = peaks (metallic), - = notches (hollow)."),
           ("mix", "Res Mix", "Mix", 0.0, 100.0, 50.0, U_PCT, None, "rsmix", "Resonator mix.")]
    for k, (key, long, short, lo, hi, init, us, expo, gen, info) in enumerate(res):
        dial(f"tone_res_{key}", r(646 + 36 * k, 125, 36, 36), valueof(
            long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, exponent=expo,
            modmode=MOD_BIPOLAR, info=info), gen, accent=READ, pv=gen)

    # ---- Global page (was Out; scripting prefix out_, D20) ----
    # Global left column: labels above the tabs, so Resync's five segments get 20 px each ("Off" fits;
    # the mock-up's 14 px showed "O.", deviation from layout.md recorded there)
    tab("out_gate", r(646, 55, 100, 14), enum(
        "Gate", "Gate", ["Drone", "MIDI"], 0,
        "Drone: the voices always run (Live's device switch turns them off). MIDI: sound while a note is held; "
        "every note-on restarts the pointers."), "gatemode")
    tab("out_resync", r(646, 83, 100, 14), enum(
        "Resync", "Resync", ["Off", "1", "2", "4", "8"], 0,
        "Re-locks synced pointers every 1, 2, 4 or 8 bars while Live's transport runs (counted from the start)."),
        "resync")
    c.append(Ctl("live.text", "out_syncnow", r(646, 101, 48, 14), enum(
        "Sync", "Sync", ["Off", "On"], 0, "Restarts both pointers now."), None,
        extra={"mode": 0, "text": "Sync now", "texton": "Sync now"}))
    pill("out_aa", r(698, 101, 48, 14), onoff(
        "Ramp AA", "Ramp AA", 0, "Anti-aliased ramps (PolyBLEP) for both pointers, like the original's oscillators; "
                                 "off = naive."), "aaramp", "Ramp AA")
    dial("out_transpose", r(650, 129, 36, 36), int_param(
        "Transpose", "Transp", -48, 48, 0, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
        info="Transposes both pointers in Hz mode (D21); synced pointers stay on the tempo grid."), "transpose")
    power("out_lim_on", r(752, 29, 64, 13), "Limiter On", 1, "LIMITER", "limon", pages="limon")
    lim = [("gain", "Limiter Gain", "Gain", 0.0, 24.0, 0.0, U_DB, None, None, "limgain", "Gain into the limiter."),
           ("sat", "Saturation", "Sat", 0.0, 100.0, 0.0, U_PCT, None, None, "limsat",
            "Saturation before the limiter (0 = clean)."),
           ("color", "Color", "Color", -100.0, 100.0, 0.0, U_PCT, None, None, "limcolor",
            "Tilts the saturation: - drives the lows harder (warm), + the highs (edgy)."),
           ("rel", "Limiter Release", "Release", 1.0, 1000.0, 100.0, U_MS, None, 3.0, "limrel", "Limiter release."),
           ("ceil", "Ceiling", "Ceiling", -12.0, 0.0, -0.3, U_DB, None, None, "limceil",
            "The output never goes above this (zero latency).")]
    for k, (key, long, short, lo, hi, init, us, units, expo, gen, info) in enumerate(lim):
        dial(f"out_lim_{key}", r(752 + 36 * k, 56, 36, 36), valueof(
            long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, units=units, exponent=expo,
            modmode=MOD_BIPOLAR, info=info), gen)
    dial("out_width", r(752, 125, 36, 36), valueof(
        "Width", "Width", T_FLOAT, mmin=0.0, mmax=200.0, initial=100.0, unitstyle=U_PCT, modmode=MOD_BIPOLAR,
        info="Stereo spread of the 5 voices: 0 mono, 100 even, 200 wide."), "width", scale=0.01)
    dial("out_output", r(788, 125, 36, 36), valueof(
        "Output", "Output", T_FLOAT, mmin=-36.0, mmax=0.0, initial=-6.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Output level (the 5-voice sum is compensated by -14 dB)."), "output")
    return c


def labels() -> list[Label]:
    out: list[Label] = []
    L = out.append
    for p, name, dy in (("w", "WRITE", 0.0), ("r", "READ", 82.0)):
        L(Label(name, r(10, 11 + dy, 52, 13), f"{p}_title", 9.0, True))
        L(Label("Pitch", r(66, 11 + dy, 40, 11), f"{p}_free_lbl1", just=1))
        L(Label("Rate", r(66, 11 + dy, 40, 11), f"{p}_sync_lbl1", just=1))
        L(Label("Fine", r(106, 11 + dy, 40, 11), f"{p}_free_lbl2", just=1))
        L(Label("Detune", r(106, 11 + dy, 40, 11), f"{p}_sync_lbl2", just=1))
        L(Label("Shape", r(190, 11 + dy, 60, 11), f"{p}_shapelbl"))
    for text in ("Curve", "Skew", "Width", "Duty", "Smooth"):
        L(Label(text, r(146, 11, 40, 11), f"w_symlbl_{text.lower()}", just=1))
    L(Label("Spread", r(146, 93, 40, 11), "r_lbl3", just=1))
    for k in (1, 2):
        lx = 646.0 + (k - 1) * 106.0
        L(Label(f"LFO {k}", r(lx, 30, 44, 13), f"lfo_l{k}title", 9.0, True))
        for j, t in enumerate(("Rate", "Phase", "Spread")):
            L(Label(t, r(lx + 34 * j, 72, 34, 11), f"lfo_l{k}lbl{j}", just=1))
        L(Label("Retrig", r(lx, 137, 30, 13), f"lfo_l{k}retriglbl", vcenter=True))
    L(Label("ENV FOLLOWER", r(858, 30, 102, 13), "lfo_envtitle", 9.0, True))
    for j, t in enumerate(("Attack", "Release", "Gain")):
        L(Label(t, r(858 + 34 * j, 72, 34, 11), f"lfo_envlbl{j}", just=1))
    L(Label("post Tone · pre Limiter", r(858, 137, 102, 13), "lfo_envnote", vcenter=True))
    for i, (t, tlong, tshort, g) in enumerate(TGTS):
        L(Label(tshort, r(694 + 21 * i + 3 * g, 29, 20, 11), f"mod_cl_{t}", 7.5, just=1))
    for row, (s, sname, sshort) in enumerate(SRCS):
        L(Label(sname, r(646, 42 + 13 * row, 46, 12), f"mod_rl_{s}", vcenter=True))
    L(Label("Amount", r(646, 45, 40, 11), "tone_ldrive", just=1))
    L(Label("›", r(688, 66, 10, 12), "tone_arrow1", 9.0, just=1))
    for k, t in enumerate(("Center", "Width", "Res", "FM", "Spread")):
        L(Label(t, r(698 + 36 * k, 45, 36, 11), f"tone_lband{k}", just=1))
    for k, t in enumerate(("Freq", "Fdbk", "Mix")):
        L(Label(t, r(646 + 36 * k, 114, 36, 11), f"tone_lres{k}", just=1))
    L(Label("PLAY", r(646, 29, 50, 13), "out_tplay", 9.0, True))
    L(Label("Gate", r(646, 44, 100, 11), "out_lgate"))
    L(Label("Resync (bars)", r(646, 72, 100, 11), "out_lresync"))
    L(Label("Transpose", r(646, 118, 44, 11), "out_ltransp", just=1))
    for k, t in enumerate(("Gain", "Sat", "Color", "Release", "Ceiling")):
        L(Label(t, r(752 + 36 * k, 45, 36, 11), f"out_llim{k}", just=1))
    L(Label("OUTPUT", r(752, 98, 60, 13), "out_tout", 9.0, True))
    L(Label("Width", r(752, 114, 36, 11), "out_lwidth", just=1))
    L(Label("Output", r(788, 114, 36, 11), "out_loutput", just=1))
    L(Label(f"Aliasing {VERSION} · after D. Pank", r(830, 150, 108, 11), "out_info", 7.5))
    return out


# divider lines (live.line, vertical: a line centred in a 3-px box): (rect, varname)
LINES = [(r(749, 32, 3, 118), "lfo_div1"), (r(855, 32, 3, 118), "lfo_div2"), (r(748, 32, 3, 128), "out_div")]
# theme-following section surfaces (D22), drawn first = behind everything
PANELS = [(r(4, 4, 300, 79), "panel_w"), (r(4, 86, 300, 79), "panel_r"), (r(306, 4, 332, 161), "panel_disp"),
          (r(642, 4, 322, 161), "panel_page")]


def build(template: dict) -> dict:
    pat = template["patcher"]
    plugout = next(b["box"] for b in pat["boxes"] if b["box"].get("text") == "plugout~")
    p = Patch()

    def hide_rule(box: dict) -> dict:
        vis = visible_at_load(str(box.get("varname", "")))
        if vis is False:
            box["hidden"] = 1
        return box

    # ---- panels first (back of the z-order) -------------------------------------------------------
    for rect, var in PANELS:
        p.add({"maxclass": "panel", "varname": var, "numinlets": 1, "numoutlets": 0, "background": 1,
               "mode": 0, "border": 0, "rounded": 4, "bgcolor": PANEL_FALLBACK, "bgfillcolor": PANEL_FALLBACK,
               "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]], "presentation": 1,
               "presentation_rect": rect})
    p.boxes.append({"box": {**plugout, "id": "obj-plugout", "patching_rect": [40.0, 980.0, 120.0, 22.0]}})

    # ---- core --------------------------------------------------------------------------------------
    gen = p.obj("gen~ @gen aliasing @atab ---atab @aheads ---aheads", 40.0, 920.0, 4,
                ["signal", "signal", "signal"], w=330.0)
    p.obj("buffer~ ---atab @samps 1024 5", 420.0, 920.0, 1, ["float", "bang"])
    p.obj("buffer~ ---aheads @samps 5 10", 420.0, 950.0, 1, ["float", "bang"])
    p.wire(gen, 0, "obj-plugout", 0)
    p.wire(gen, 1, "obj-plugout", 1)

    # ---- MIDI: notes held (gate), note-on impulse + velocity, mod wheel -----------------------------
    notein = p.obj("notein", 40.0, 560.0, 1, ["int", "int", "int"])
    borax = p.obj("borax", 40.0, 600.0, 3, ["int"] * 9, w=110.0)
    held = p.obj("> 0", 40.0, 640.0, 2, ["int"])
    gate_sig = p.obj("sig~", 40.0, 680.0, 1, ["signal"])
    p.wire(notein, 0, borax, 0)
    p.wire(notein, 1, borax, 1)
    p.wire(borax, 2, held, 0)
    p.wire(held, 0, gate_sig, 0)
    p.wire(gate_sig, 0, gen, 0)  # in1 = notes held
    vsel = p.obj("sel 0", 170.0, 600.0, 2, ["bang", ""])
    vtrig = p.obj("t b i", 170.0, 640.0, 1, ["bang", "int"])
    vscale = p.obj("/ 127.", 230.0, 680.0, 2, ["float"])
    vpre = p.obj("prepend velocity", 230.0, 720.0, 1, [""])
    note_click = p.obj("click~", 170.0, 720.0, 1, ["signal"])
    p.wire(notein, 1, vsel, 0)
    p.wire(vsel, 1, vtrig, 0)  # non-zero velocity = note-on
    p.wire(vtrig, 1, vscale, 0)  # right to left: velocity first, then the impulse
    p.wire(vscale, 0, vpre, 0)
    p.wire(vpre, 0, gen, 0)
    p.wire(vtrig, 0, note_click, 0)
    p.wire(note_click, 0, gen, 2)  # in3 = note-on impulse
    ctl = p.obj("ctlin 1", 320.0, 560.0, 1, ["int", "int"])
    mwscale = p.obj("/ 127.", 320.0, 600.0, 2, ["float"])
    mwpre = p.obj("prepend modwheel", 320.0, 640.0, 1, [""])
    p.wire(ctl, 0, mwscale, 0)
    p.wire(mwscale, 0, mwpre, 0)
    p.wire(mwpre, 0, gen, 0)

    # ---- transport: state and tempo (plugsync~), bar ramp (locked phasor~) ---------------------------
    psync = p.obj("plugsync~", 480.0, 560.0, 1, ["int", "int", "int", "float", "list", "float", "float", "int", "int"],
                  w=120.0)
    pchg = p.obj("change", 480.0, 600.0, 1, ["", "int", "int"])
    ppre = p.obj("prepend playing", 480.0, 640.0, 1, [""])
    schg = p.obj("change", 560.0, 600.0, 1, ["", "int", "int"])
    spre = p.obj("prepend spb", 560.0, 640.0, 1, [""])
    p.wire(psync, 0, pchg, 0)
    p.wire(pchg, 0, ppre, 0)
    p.wire(ppre, 0, gen, 0)
    p.wire(psync, 5, schg, 0)
    p.wire(schg, 0, spre, 0)
    p.wire(spre, 0, gen, 0)
    bar = p.obj("phasor~ 1.0.0 @lock 1", 640.0, 560.0, 2, ["signal"], w=150.0)
    p.wire(bar, 0, gen, 3)  # in4 = bar ramp

    # ---- display, pages, storage, theme -----------------------------------------------------------------
    disp = p.add({"maxclass": "v8ui", "filename": "aliasing_display.js", "embed": 0, "numinlets": 1,
                  "numoutlets": 2, "outlettype": ["", ""], "parameter_enable": 0,
                  "patching_rect": [308.0, 6.0, 328.0, 136.0], "presentation": 1,
                  "presentation_rect": [308.0, 6.0, 328.0, 136.0], "varname": "display",
                  "textfile": {"filename": "aliasing_display.js", "flags": 0, "embed": 0, "autowatch": 1}})
    pages = p.obj("v8 aliasing_pages.js", 840.0, 560.0, 1, [], w=140.0,
                  saved_object_attributes={"embed": 0, "parameter_enable": 0},
                  textfile={"filename": "aliasing_pages.js", "flags": 0, "embed": 0, "autowatch": 1})
    thisdev = p.obj("live.thisdevice", 840.0, 480.0, 1, ["bang", "int", "int"], w=105.0)
    init = p.obj("t b b b", 840.0, 520.0, 1, ["bang", "bang", "bang"])
    bufmsg = p.msg("buffers ---atab ---aheads ---atable", 960.0, 520.0)
    p.wire(thisdev, 0, init, 0)
    p.wire(init, 2, bufmsg, 0)
    p.wire(bufmsg, 0, disp, 0)
    p.wire(init, 1, pages, 0)  # after load: apply the stored page and modes
    # panel colours from Live's theme (D22): at load and whenever the theme changes
    lcol = p.obj("live.colors", 1260.0, 560.0, 1, ["", "bang"], w=80.0)
    lqry = p.msg("live_surface_bg", 1260.0, 520.0)
    lpre = p.obj("prepend surface", 1260.0, 600.0, 1, [""])
    p.wire(init, 0, lqry, 0)
    p.wire(lcol, 1, lqry, 0)
    p.wire(lqry, 0, lcol, 0)
    p.wire(lcol, 0, lpre, 0)
    p.wire(lpre, 0, pages, 0)

    # the display's gestures -> parameters; the stored Display Mode tab (not on the face)
    route_names = ["mode", "center", "bwidth", "bres", "bmode", "rsfreq", "rsfb", "rsmix", "rstrack", "reson"]
    route = p.obj("route " + " ".join(route_names), 960.0, 600.0, len(route_names) + 1,
                  [""] * (len(route_names) + 1), w=460.0)
    p.wire(disp, 0, route, 0)
    dmode = p.add({"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
                   "parameter_enable": 1, "patching_rect": [960.0, 640.0, 60.0, 15.0], "varname": "display_mode",
                   "num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0, "fontname": FONT,
                   "fontsize": 9.0, "saved_attribute_attributes": {"valueof": valueof(
                       "Display Mode", "Disp Mode", T_ENUM, enum=["Line", "2D"], invisible=STORED_ONLY,
                       info="Table display: Line or 2D (the icons in the display).")}})
    p.wire(route, 0, dmode, 0)
    mpre = p.obj("prepend mode", 960.0, 670.0, 1, [""])
    p.wire(dmode, 0, mpre, 0)
    p.wire(mpre, 0, disp, 0)

    # dict Blob parameter: the drawn table, saved with the Set (R10; probe variant B, Ableton's pattern)
    tdict = p.add({"maxclass": "newobj", "text": "dict ---atable", "numinlets": 2, "numoutlets": 5,
                   "outlettype": ["dictionary", "", "", "", ""], "patching_rect": [1100.0, 520.0, 110.0, 22.0],
                   "varname": "atable",
                   "saved_object_attributes": {"embed": 0, "legacy": 1, "parameter_enable": 1,
                                               "parameter_mappable": 0},
                   "saved_attribute_attributes": {"valueof": {
                       "parameter_longname": "Table", "parameter_shortname": "Table", "parameter_type": T_BLOB,
                       "parameter_invisible": STORED_ONLY, "parameter_initial_enable": 0, "parameter_modmode": 0}}})
    p.wire(disp, 1, tdict, 0)
    p.wire(tdict, 0, disp, 0)

    # ---- controls -------------------------------------------------------------------------------------
    by_var: dict[str, str] = {}
    col = {"n": 0}

    def logic_xy() -> tuple[float, float]:
        k = col["n"]
        col["n"] += 1
        return 40.0 + (k % 9) * 150.0, 1450.0 + (k // 9) * 30.0

    for ctl_ in controls():
        rect = ctl_.rect
        box: dict = {"maxclass": ctl_.cls, "varname": ctl_.var, "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]],
                     "presentation": 1, "presentation_rect": rect,
                     "jspainterfile": ctl_.painter or PAINTER[ctl_.cls], "fontname": FONT, "fontsize": 9.0}
        outs = {"live.dial": ["", "float"], "live.tab": ["", "", "float"], "live.text": ["", ""],
                "live.slider": ["", "float"], "live.menu": ["", "", "float"], "live.numbox": ["", "float"]}[ctl_.cls]
        box.update({"numinlets": 1, "numoutlets": len(outs), "outlettype": outs})
        if ctl_.cls == "live.dial":
            box.update({"showname": 0, "shownumber": 1})
        if ctl_.cls == "live.tab":
            box.update({"num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0})
        box.update(ctl_.extra)
        saa: dict = {}
        if ctl_.accent and ctl_.cls == "live.dial":
            box["activedialcolor"] = ctl_.accent
            saa["activedialcolor"] = {"expression": ""}
        if ctl_.vo is not None:
            box["parameter_enable"] = 1
            saa["valueof"] = ctl_.vo
            if ctl_.vo.get("parameter_info"):
                box["annotation"] = ctl_.vo["parameter_info"]
        box["saved_attribute_attributes"] = saa
        oid = p.add(hide_rule(box))
        by_var[ctl_.var] = oid
        src = oid
        if ctl_.gen:
            x, y = logic_xy()
            if ctl_.scale:
                sc = p.obj(f"* {ctl_.scale}", x, y, 2, ["float"])
                p.wire(oid, 0, sc, 0)
                src = sc
            pre = p.obj(f"prepend {ctl_.gen}", x + (50.0 if ctl_.scale else 0.0), y, 1, [""])
            p.wire(src, 0, pre, 0)
            p.wire(pre, 0, gen, 0)
        if ctl_.pv:
            x, y = logic_xy()
            pre = p.obj(f"prepend pv {ctl_.pv}", x, y, 1, [""])
            p.wire(oid, 0, pre, 0)
            p.wire(pre, 0, disp, 0)
        if ctl_.pages:
            x, y = logic_xy()
            pre = p.obj(f"prepend {ctl_.pages}", x, y, 1, [""])
            p.wire(oid, 0, pre, 0)
            p.wire(pre, 0, pages, 0)
            if ctl_.var == "page":
                p.wire(pre, 0, disp, 0)  # the display shows the tone curve on page Tone

    # display gestures -> the controls (user gestures: undo entries are intended here)
    targets = {"center": "tone_band_center", "bwidth": "tone_band_width", "bres": "tone_band_res",
               "bmode": "tone_band_mode", "rsfreq": "tone_res_freq", "rsfb": "tone_res_fb", "rsmix": "tone_res_mix",
               "rstrack": "tone_res_track", "reson": "tone_res_on"}
    for k, name in enumerate(route_names):
        if name in targets:
            p.wire(route, k, by_var[targets[name]], 0)

    # Sync button -> click~ -> gen~ in2
    ssel = p.obj("sel 1", 1100.0, 600.0, 2, ["bang", ""])
    sclick = p.obj("click~", 1100.0, 640.0, 1, ["signal"])
    p.wire(by_var["out_syncnow"], 0, ssel, 0)
    p.wire(ssel, 0, sclick, 0)
    p.wire(sclick, 0, gen, 1)

    # output meter (Global) and the follower level (LFO · Env, gen~ out3)
    for k in (0, 1):
        m = p.add(hide_rule({"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2,
                             "outlettype": ["float", "int"], "patching_rect": [700.0 + 20.0 * k, 960.0, 8.0, 132.0],
                             "presentation": 1, "presentation_rect": [942.0 + 10.0 * k, 29.0, 8.0, 132.0],
                             "varname": f"out_meter{'lr'[k]}"}))
        p.wire(gen, k, m, 0)
    em = p.add(hide_rule({"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2, "outlettype": ["float", "int"],
                          "orientation": 1, "display_range": [-36.0, 0.0],
                          "patching_rect": [760.0, 960.0, 102.0, 10.0], "presentation": 1,
                          "presentation_rect": [858.0, 52.0, 102.0, 10.0], "varname": "lfo_envmeter"}))
    p.wire(gen, 2, em, 0)

    # ---- labels and dividers ---------------------------------------------------------------------------
    for lb in labels():
        rect = list(lb.rect)
        if lb.vcenter:
            # onto the text line of the painted tab / cell next to it (D23): in t3 the "Retrig" baseline sat
            # 1 px above the tab text's (screenshot rows 151 vs 152) [measured: t3 screenshot]
            rect[1] += 1.0
            rect[3] -= 1.0
        box = {"maxclass": "live.comment", "text": lb.text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]], "presentation": 1,
               "presentation_rect": rect, "fontname": FONT_BOLD if lb.bold else FONT, "fontsize": lb.size,
               "textjustification": lb.just, "varname": lb.var}
        p.add(hide_rule(box))
    for rect, var in LINES:
        p.add(hide_rule({"maxclass": "live.line", "numinlets": 1, "numoutlets": 0, "varname": var,
                         "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]], "presentation": 1,
                         "presentation_rect": rect}))

    new = dict(pat)
    new["boxes"] = p.boxes
    new["lines"] = p.lines
    new["openinpresentation"] = 1
    new["devicewidth"] = WIDTH
    new["rect"] = [60.0, 80.0, 1440.0, 900.0]
    new["title"] = "Aliasing"
    new["description"] = (f"Aliasing {VERSION}: a 5-voice drone where a table is written and read at different "
                          "speeds, with tempo sync, LFOs, an envelope follower, a mod matrix, a tone section and a "
                          "color limiter. Inspired by 'aliasing Synth' by Dietrich Pank (Reaktor User Library "
                          "#5241, 2008).")
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


def param_table() -> str:
    rows = ["| Long name | Control | Range / items | Initial | gen~ Param | Scripting name |", "|---|---|---|---|---|---|"]
    for c in controls():
        if c.vo is None:
            continue
        vo = c.vo
        if "parameter_enum" in vo:
            rng = " / ".join(vo["parameter_enum"]) if len(vo["parameter_enum"]) <= 8 else (
                f"{vo['parameter_enum'][0]} ... {vo['parameter_enum'][-1]} ({len(vo['parameter_enum'])})")
            init = vo["parameter_enum"][int(vo["parameter_initial"][0])]
        else:
            rng = f"{vo.get('parameter_mmin', 0)} ... {vo.get('parameter_mmax')}"
            if "parameter_steps" in vo:
                rng += f" ({vo['parameter_steps']} steps)"
            init = vo["parameter_initial"][0]
        gen = c.gen or "-"
        if c.scale:
            gen += f" (x {c.scale})"
        rows.append(f"| {vo['parameter_longname']} | {c.cls} | {rng} | {init} | {gen} | `{c.var}` |")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=TEMPLATE, help="Live's Max Instrument.amxd")
    ap.add_argument("--out", type=Path, default=DEVICE / "Aliasing.amxd", help="output .amxd")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output (discards Max edits)")
    ap.add_argument("--list-params", action="store_true", help="print the parameter table (Markdown) and exit")
    args = ap.parse_args(argv)
    if args.list_params:
        print(param_table())
        return 0
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
