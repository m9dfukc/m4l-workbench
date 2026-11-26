#!/usr/bin/env python3
"""Bootstrap of the two Aliasing shells, v0.3b (D33, D40): the hybrid face as Aliasing.amxd and
option (b) as Aliasing B.amxd, both on the same gen~ core, display, page script and painters.

Starts from Live's own instrument template (Max Instrument.amxd), keeps its patcher settings and
plugout~, and builds one face (docs/face-review-2026-11-25.md, sections "Hybrid" h.1 and "Option (b)"
b.2; decisions D33-D44 in docs/v0.3-design.md; layout tables docs/mockup-v0.3b/layout-hybrid.md and
layout-b.md, kept in sync with this file):
- hybrid, 968 x 169: two pointer rows, the tall display with the Size slider, four pages (LFO · Env,
  Mod = the 72-cell matrix with destinations as rows, Tone, Global);
- b, 800 x 169: display 496 x 85 + seven side pages, a modulation strip (the 8 depths of one target,
  picked with a menu; the other 64 cells hidden at the same rects), a constant row of 48-px dials.
Every dial is a 48-px live.dial with its name and value inside (showname 1: Live gives the painter
48 px whatever the saved rect [measured: dial probe 2026-11-25]); single-line controls are 15 px, text
9.5 pt. Every control is a real live.* parameter drawn by a jspainter script (aliasing_paint_*.js, R5);
labels are live.comment. Logic: MIDI (notes held, note-on impulse, velocity, mod wheel), transport
(plugsync~, a locked bar phasor~), the gen~ core with its two buffer~s and the follower outlet, the
v8ui display, the v8 page switcher (pages, greying, theme colours), a dict Blob parameter that
stores the drawn table with the Live Set (R10), and the sample drop (D50-D54: an invisible live.drop behind
the display, sfinfo~ and a mono buffer~ the display reads a dropped file through). Box JSON follows real Max-saved boxes (m4l-boxref).

The unfrozen .amxd files are the source of truth once the user edits them in Max. This script
therefore refuses to overwrite an existing file unless --force is given, and --force discards every
edit made in Max since. (v0.1 -> v0.3b were regenerated with --force: the shells had no Max edits.)

Usage: python3 devices/aliasing/scripts/bootstrap_shell.py [--face hybrid|b] [--template PATH] [--out PATH] [--force]
       python3 devices/aliasing/scripts/bootstrap_shell.py --face b --list-params   (parameter table, Markdown)
       python3 devices/aliasing/scripts/bootstrap_shell.py --face b --list-layout   (layout table, Markdown)
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
FS = 9.5  # Ableton's label size (research note summary 2), D33
VERSION = "v0.3b"
FACES = ("hybrid", "b")
FACE_WIDTH = {"hybrid": 918.0, "b": 800.0}  # hybrid: 968 - 50 since the compact pointer rows (D47)
FACE_FILE = {"hybrid": "Aliasing.amxd", "b": "Aliasing B.amxd"}
FACE_TITLE = {"hybrid": "Aliasing", "b": "Aliasing B"}
WIDTH = FACE_WIDTH["hybrid"]  # the hybrid's width (older importers)
DIAL_H = 48.0  # live.dial with showname 1, shownumber 1 [measured: dial probe, build/aliasing/dialprobe]
LINE_H = 15.0  # single-line controls (Ableton's measure, research note summary 1)

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
HIDDEN = 2  # not stored, not automatable, not on Push (903 Max-saved live.text use it: m4l-boxref)

NOTES = ["8 bars", "4 bars", "2 bars", "1 bar", "1/2", "1/2D", "1/2T", "1/4", "1/4D", "1/4T", "1/8", "1/8D",
         "1/8T", "1/16", "1/16D", "1/16T", "1/32", "1/32T", "1/64"]  # = Data divb in the GenExpr
LFO_SHAPES = ["Sine", "Tri", "Saw", "Square", "S&H", "Random"]
W_SHAPES = ["Ramp", "Tri", "Pulsar", "Spike", "Noise"]  # D34, = Param wshape
# Mod matrix (D36): (key, long name, short, strip label) of the sources and (key, long name, short) of the
# targets in the order of the hybrid's rows and the Mod Target menu (= pages_model.ts TARGETS).
SRCS = [("l1", "LFO 1", "L1", "LFO 1"), ("l2", "LFO 2", "L2", "LFO 2"), ("en", "Env", "Env", "Env"),
        ("ve", "Velocity", "Vel", "Vel"), ("mw", "Mod Wheel", "MW", "Wheel"), ("vo", "Voice", "Voice", "Voice"),
        ("nb", "Neighbour", "Next", "Next"), ("ro", "Read Osc", "ROsc", "R Osc")]
TGTS = [("wp", "Write Pitch", "WPit"), ("sy", "Write Sym", "Sym"), ("wa", "Write Gate", "Gate"),
        ("rp", "Read Pitch", "RPit"), ("sp", "Read Spread", "Sprd"), ("sz", "Size", "Size"),
        ("bc", "Band Center", "Ctr"), ("rf", "Res Freq", "RFrq"), ("ou", "Output", "Out")]
TARGET_ROLE = {"wp": "write", "sy": "write", "wa": "write", "rp": "read", "sp": "read"}
SYM_GROUPS = ["curve", "skew", "duty", "width", "smooth"]  # = W_SHAPES (D6, D34)

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


# ---- the page / mode visibility rule (mirror of js/src/pages_model.ts) ------------------------------

FACE_PAGES = {"hybrid": ["lfo", "mod", "tone", "out"], "b": ["lfo1", "lfo2", "env", "band", "res", "lim", "out"]}
FACE_TONE_PAGES = {"hybrid": [2], "b": [3, 4]}
TARGET_KEYS = [t[0] for t in TGTS]


def initial_state(face: str) -> dict:
    return {"face": face, "page": 0, "target": 0, "wmode": 0, "rmode": 0, "l1mode": 0, "l2mode": 1, "wshape": 1}


def sym_label_of(shape: int) -> str:
    """pages_model.ts symLabelOf (D6, D34)."""
    return SYM_GROUPS[max(0, min(len(SYM_GROUPS) - 1, round(shape)))]


def visible_in(varname: str, st: dict) -> bool | None:
    """pages_model.ts visibilityFor: True / False, or None for objects without a rule."""
    parts = varname.split("_") if varname else []
    if len(parts) < 2:
        return None
    face = st.get("face", "hybrid")
    area, cond = parts[0], parts[1]
    pages = FACE_PAGES[face]
    if face == "b" and area == "mod":
        t = parts[2] if len(parts) > 2 else ""
        return None if t not in TARGET_KEYS else TARGET_KEYS.index(t) == st["target"]
    if area in pages:
        ok = pages.index(area) == st["page"]
    elif area == "tbl":
        ok = st["page"] not in FACE_TONE_PAGES[face]
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


# ---- control specs ----------------------------------------------------------------------------------

@dataclass
class Ctl:
    cls: str                      # live.dial / live.tab / live.text / live.slider / live.menu / live.numbox
    var: str                      # scripting name (page / mode / role rules)
    rect: list[float]             # presentation rect (docs/mockup-v0.3b/layout-<face>.md)
    vo: dict | None               # valueof (None = no parameter)
    gen: str | None = None        # gen~ Param name ("prepend <gen>")
    scale: float | None = None    # multiply before gen~ (percent -> 0..1)
    pv: str | None = None         # "pv <name>" to the display
    pages: str | None = None      # message name to the page switcher
    extra: dict = field(default_factory=dict)
    accent: list[float] | None = None
    painter: str | None = None    # jspainter file (default by class)
    key: str = ""                 # logical control (same in both faces)


@dataclass
class Label:
    text: str
    rect: list[float]
    var: str
    size: float = FS
    bold: bool = False
    just: int = 0                 # 0 left, 1 centre, 2 right
    overlay: bool = False         # name-row overlay on a dial (ignoreclick, drawn after it, h.2)


def r(x: float, y: float, w: float, h: float) -> list[float]:
    return [float(x), float(y), float(w), float(h)]


def onoff(long: str, short: str, init: int, info: str) -> dict:
    return enum(long, short, ["Off", "On"], init, info)


def specs(face: str) -> dict[str, Ctl]:
    """Every control of the device by logical key; varname and rect are filled in by the face layout."""
    c: dict[str, Ctl] = {}
    Z = r(0, 0, 0, 0)

    def add(key, cls, vo, gen=None, **kw):
        c[key] = Ctl(cls, key, list(Z), vo, gen, key=key, **kw)

    def dial(key, vo, gen, accent=NEUTRAL, **kw):
        add(key, "live.dial", vo, gen, accent=accent, **kw)

    def tab(key, vo, gen, **kw):
        add(key, "live.tab", vo, gen, **kw)

    def pill(key, vo, gen, text, texton=None, **kw):
        add(key, "live.text", vo, gen, extra={"mode": 1, "text": text, "texton": texton or text}, **kw)

    # ---- pointer rows ----
    for p, name, acc in (("w", "Write", WRITE), ("r", "Read", READ)):
        tab(f"{p}.mode", enum(f"{name} Mode", f"{name[0]} Mode", ["Hz", "Sync"], 0,
            f"{name} pointer rate: Hz = free pitch, Sync = note value x N / D x Sync Rate at Live's tempo."),
            f"{p}mode", pages=f"{p}mode")
        add(f"{p}.mult", "live.numbox", int_param(
            f"{name} Mult", "Mult", 1, 128, 1, unitstyle=U_CUSTOM, units="×%d", modmode=MOD_ABSOLUTE,
            info=f"Sync mode: the note value's rate times N (D3), so synced {name.lower()} rates reach the audio "
                 "range."), f"{p}mult")
        add(f"{p}.div", "live.numbox", int_param(
            f"{name} Div", "Div", 1, 32, 1, unitstyle=U_CUSTOM, units="÷%d", modmode=MOD_ABSOLUTE,
            info="Sync mode: divides the rate by D (D3): odd cycle lengths such as 5/16 that drift against the "
                 "bar."), f"{p}den")
        dial(f"{p}.pitch", int_param(
            f"{name} Pitch", "Pitch", -64, 130, 0, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
            info=f"{name} pointer pitch in semitones around note 60 (-64..130). Above about half the sample rate "
                 "the pattern depends on the sample rate (44.1 and 48 kHz differ)."), f"{p}pitch", accent=acc)
        dial(f"{p}.note", enum(
            f"{name} Rate", "Rate", NOTES, 13, f"Sync mode: {name.lower()} pointer note value (bars are 4/4)."),
            f"{p}note", accent=acc)
        dial(f"{p}.fine", valueof(
            f"{name} Fine", "Fine", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, unitstyle=U_CUSTOM,
            units="%0.3f st", modmode=MOD_BIPOLAR, steps=2001,
            info="Fine pitch in semitones; in Sync mode a detune against the tempo grid (Resync re-locks it)."),
            f"{p}fine", accent=acc)
    dial("w.sym", valueof(
        "Write Sym", "Sym", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR, steps=201,
        info="The write shape's parameter (D6): Curve (Ramp), Skew (Tri), Duty (Pulsar), Width (Spike), "
             "Smooth (Noise)."), "wsym", accent=WRITE)
    tab("w.shape", enum(
        "Write Shape", "W Shape", W_SHAPES, 1,
        "Path of the write head (the read phase is written along it): Ramp, Tri, Pulsar and Spike (bursts, "
        "then no writing), Noise (random cells)."), "wshape", pages="wshape")
    tab("w.active", enum(
        "Write State", "W State", ["Freeze", "Write", "Clean"], 1,
        "Freeze keeps the table, Write lets the write head change it, Clean writes where the read pointer "
        "reads (the original's \"=read\": the plain read waveform; heals the table)."), "wactive", pages="wactive")
    dial("r.spread", valueof(
        "Read Spread", "Spread", T_FLOAT, mmin=0.0, mmax=6.0, initial=2.0, unitstyle=U_CUSTOM,
        units="%0.2f st", modmode=MOD_BIPOLAR, steps=601, info="Read pitch spread across the 5 voices."),
        "rspread", accent=READ)
    tab("r.shape", enum(
        "Read Shape", "R Shape", ["Ramp", "Tri"], 0, "Read pointer: ramp, or triangle up and down (D35)."),
        "rshape")
    pill("r.smooth", onoff("Smooth", "Smooth", 0, "Read interpolation: off reads whole cells (raw), on is linear."),
         "smoothread", "Smooth")

    # ---- Size: a slider below the hybrid's display (D9), a dial in face b's row ----
    size_vo = valueof("Size", "Size", T_FLOAT, mmin=0.1, mmax=100.0, initial=10.0, unitstyle=U_PCT, exponent=2.0,
                      modmode=MOD_BIPOLAR, info="Pointer span: both pointers cover only this part of the table; "
                                                "the display zooms to it.")
    if face == "hybrid":
        add("size", "live.slider", size_vo, "size", scale=0.01, pv="size",
            extra={"orientation": 1, "relative": 1, "showname": 0, "shownumber": 0})
    else:
        dial("size", size_vo, "size", scale=0.01, pv="size")

    # ---- page selector (stored only) ----
    page_items = ["LFO · Env", "Mod", "Tone", "Global"] if face == "hybrid" else \
        ["LFO 1", "LFO 2", "Env", "Band", "Res", "Limit", "Global"]
    add("page", "live.tab", valueof("Page", "Page", T_ENUM, enum=page_items, invisible=STORED_ONLY,
                                    info="Shows one page of controls: " + ", ".join(page_items) + "."),
        pages="page", extra={"num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0})

    # ---- LFOs (R3) and the envelope follower (D16) ----
    for k in (1, 2):
        free_hz, sync_init, shape_init, retrig_init, phase_init, mode_init = (
            (0.15, 7, 0, 0, 0.0, 0) if k == 1 else (0.07, 3, 5, 2, 90.0, 1))
        tab(f"lfo{k}.mode", enum(f"LFO {k} Mode", f"L{k} Mode", ["Hz", "Sync"], mode_init,
                                 f"LFO {k} rate: Hz or a note value."), f"l{k}mode", pages=f"l{k}mode")
        tab(f"lfo{k}.shape", enum(f"LFO {k} Shape", f"L{k} Shape", LFO_SHAPES, shape_init, f"LFO {k} waveform."),
            f"l{k}shape")
        dial(f"lfo{k}.rate", valueof(
            f"LFO {k} Rate", "Rate", T_FLOAT, mmin=0.01, mmax=20.0, initial=free_hz, unitstyle=U_HZ, exponent=3.0,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate in Hz (each voice runs slightly faster or slower: Spread)."),
            f"l{k}rate")
        dial(f"lfo{k}.note", enum(f"LFO {k} Sync Rate", "Rate", NOTES, sync_init,
                                  f"LFO {k} note value at Live's tempo."), f"l{k}note")
        dial(f"lfo{k}.phase", valueof(
            f"LFO {k} Phase", "Phase", T_FLOAT, mmin=0.0, mmax=360.0, initial=phase_init, unitstyle=U_CUSTOM,
            units="%0.0f°", modmode=MOD_BIPOLAR, steps=361, info=f"LFO {k} start phase (used on retrigger)."),
            f"l{k}phase")
        dial(f"lfo{k}.spread", valueof(
            f"LFO {k} Spread", "Spread", T_FLOAT, mmin=0.0, mmax=100.0, initial=50.0, unitstyle=U_PCT,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate spread across the 5 voices (100 % = +-half an octave)."),
            f"l{k}spread")
        tab(f"lfo{k}.retrig", enum(
            f"LFO {k} Retrig", f"L{k} Retrig", ["Off", "Note", "Bar"], retrig_init,
            f"LFO {k} restart: never, on every MIDI note-on, or on every bar while Live's transport runs."),
            f"l{k}retrig")
    dial("env.att", valueof(
        "Env Attack", "Attack", T_FLOAT, mmin=0.1, mmax=100.0, initial=5.0, unitstyle=U_MS, exponent=3.0,
        modmode=MOD_BIPOLAR, info="Envelope follower attack (the follower reads the output before the limiter)."),
        "enatt")
    dial("env.rel", valueof(
        "Env Release", "Release", T_FLOAT, mmin=10.0, mmax=2000.0, initial=150.0, unitstyle=U_MS, exponent=3.0,
        modmode=MOD_BIPOLAR, info="Envelope follower release."), "enrel")
    dial("env.gain", valueof(
        "Env Gain", "Gain", T_FLOAT, mmin=-24.0, mmax=24.0, initial=12.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Envelope follower gain: the source is the follower level x this, clipped to 0..1."), "engain")

    # ---- mod matrix (D25, D26, D36) ----
    for s, sname, sshort, _ in SRCS:
        for t, tlong, tshort in TGTS:
            add(f"mx.{s}.{t}", "live.numbox", valueof(
                f"{sname} > {tlong}", f"{sshort}>{tshort}", T_FLOAT, mmin=-100.0, mmax=100.0, initial=0.0,
                unitstyle=U_PCT, modmode=MOD_BIPOLAR, steps=2001,
                info=f"Mod matrix: {sname} modulates {tlong} (depth in percent)."), f"mx_{s}_{t}",
                painter=CELL_PAINTER)
    if face == "b":
        add("mod_target", "live.menu", valueof(
            "Mod Target", "Mod Target", T_ENUM, enum=[t[1] for t in TGTS], invisible=STORED_ONLY,
            info="The target whose eight modulation depths the strip shows; a dot marks the modulated "
                 "targets (D48)."), pages="target")
        clear_vo = enum("Mod Clear", "Clear", ["Off", "On"], 0,
                        "Sets the eight modulation depths of the shown target to 0 (D49).")
        clear_vo["parameter_invisible"] = 2  # hidden: a momentary action, neither automated nor stored
        add("mod_clear", "live.text", clear_vo, extra={"mode": 0, "text": "Clear", "texton": "Clear"})

    # ---- tone (R16-R18, D17); section power switches = bold title + power symbol (D32, D43) ----
    def power(key, long, init, text, gen, pv=None, pages=None):
        add(key, "live.text", onoff(long, long, init, f"Switches the {text.lower()} section on or off (off = exact "
                                    "bypass)."), gen, pv=pv, pages=pages, extra={"mode": 1, "text": text, "texton": text})

    power("drive.on", "Drive On", 1, "Drive", "drvon", pages="drvon")
    dial("drive", valueof("Drive", "Amount", T_FLOAT, mmin=0.0, mmax=24.0, initial=0.0, unitstyle=U_DB,
                          modmode=MOD_BIPOLAR, info="Saturation before the band (tanh); 0 dB = clean."), "drive")
    power("band.on", "Band On", 1, "Band", "bandon", pv="bandon", pages="bandon")
    band = [("center", "Band Center", "Center", 20.0, 20000.0, 632.0, U_HZ, None, 4.0, "bcenter",
             "Band centre frequency (Spread fans it across the voices)."),
            ("width", "Band Width", "Width", 0.2, 10.0, 10.0, U_CUSTOM, "%0.1f oct", None, "bwidth",
             "Band width in octaves; 10 = open (practically bypass)."),
            ("res", "Band Res", "Res", 0.0, 100.0, 0.0, U_PCT, None, None, "bres", "Resonance at the band edges."),
            ("fm", "Band FM", "FM", 0.0, 100.0, 0.0, U_PCT, None, None, "bfm",
             "Audio-rate FM of the band centre from the unfiltered core signal (100 % = +-4 octaves)."),
            ("spread", "Band Spread", "Spread", 0.0, 100.0, 25.0, U_PCT, None, None, "bspread",
             "Band centres across the 5 voices (100 % = +-2 octaves).")]
    for key, long, short, lo, hi, init, us, units, expo, gen, info in band:
        dial(f"band.{key}", valueof(long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, units=units,
                                    exponent=expo, modmode=MOD_BIPOLAR, info=info), gen, accent=WRITE,
             pv={"center": "center", "width": "bwidth", "res": "bres"}.get(key))
    tab("band.mode", enum("Band Mode", "B Mode", ["Pass", "Reject"], 0,
                          "Pass keeps the band, Reject removes it (band-stop)."), "bmode", pv="bmode")
    tab("band.slope", enum("Band Slope", "B Slope", ["12", "24 dB"], 1, "Band edge slope: 12 or 24 dB per octave."),
        "bslope", pv="bslope")
    power("res.on", "Res On", 0, "Resonator", "reson", pv="reson", pages="reson")
    pill("res.track", onoff("Res Track", "Track", 1, "Resonator follows each voice's read pointer frequency."),
         "rstrack", "Track Read", pv="rstrack", pages="track")
    res = [("freq", "Res Freq", "Freq", 20.0, 5000.0, 140.0, U_HZ, 3.0, "rsfreq",
            "Resonator frequency (inactive while Track follows the read pointer)."),
           ("fb", "Res Feedback", "Fdbk", -95.0, 95.0, 50.0, U_PCT, None, "rsfb",
            "Resonator feedback: + = peaks (metallic), - = notches (hollow)."),
           ("mix", "Res Mix", "Mix", 0.0, 100.0, 50.0, U_PCT, None, "rsmix", "Resonator mix.")]
    for key, long, short, lo, hi, init, us, expo, gen, info in res:
        dial(f"res.{key}", valueof(long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, exponent=expo,
                                   modmode=MOD_BIPOLAR, info=info), gen, accent=READ, pv=gen)

    # ---- global ----
    tab("gate", enum("Gate", "Gate", ["Drone", "MIDI"], 0,
                     "Drone: the voices always run (Live's device switch turns them off). MIDI: sound while a note is "
                     "held; every note-on restarts the pointers."), "gatemode")
    tab("resync", enum("Resync", "Resync", ["Off", "1", "2", "4", "8"], 0,
                       "Re-locks synced pointers every 1, 2, 4 or 8 bars while Live's transport runs (counted from "
                       "the start)."), "resync")
    add("syncnow", "live.text", enum("Sync", "Sync", ["Off", "On"], 0, "Restarts both pointers now."),
        extra={"mode": 0, "text": "Sync now", "texton": "Sync now"})
    pill("aa", onoff("Ramp AA", "Ramp AA", 0, "Anti-aliased ramps (PolyBLEP) for both pointers, like the "
                     "original's oscillators; off = naive."), "aaramp", "Ramp AA")
    # short name "Transp" so the hybrid's "Tune" label starts left of it (user, 2026-11-25, D46)
    dial("transpose", int_param("Transpose", "Transp", -48, 48, 0, unitstyle=U_ST, modmode=MOD_ABSOLUTE,
                                info="Transposes both pointers in Hz mode (D21); greyed while both are synced."),
         "transpose")
    dial("syncrate", enum("Sync Rate", "Rate", ["÷16", "÷8", "÷4", "÷2", "×1", "×2", "×4", "×8", "×16"], 4,
                          "Multiplies every synced pointer rate by a power of two (D37): synced pointers stay on the "
                          "grid; greyed while no pointer is synced."), "syncrate")
    power("lim.on", "Limiter On", 1, "Limiter", "limon", pages="limon")
    lim = [("gain", "Limiter Gain", "Gain", 0.0, 24.0, 0.0, U_DB, None, "limgain", "Gain into the limiter."),
           ("sat", "Saturation", "Sat", 0.0, 100.0, 0.0, U_PCT, None, "limsat",
            "Saturation before the limiter (0 = clean)."),
           ("color", "Color", "Color", -100.0, 100.0, 0.0, U_PCT, None, "limcolor",
            "Tilts the saturation: - drives the lows harder (warm), + the highs (edgy)."),
           ("rel", "Limiter Release", "Release", 1.0, 1000.0, 100.0, U_MS, 3.0, "limrel", "Limiter release."),
           ("ceil", "Ceiling", "Ceiling", -12.0, 0.0, -0.3, U_DB, None, "limceil",
            "The output never goes above this (zero latency).")]
    for key, long, short, lo, hi, init, us, expo, gen, info in lim:
        dial(f"lim.{key}", valueof(long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, exponent=expo,
                                   modmode=MOD_BIPOLAR, info=info), gen)
    dial("width", valueof("Width", "Width", T_FLOAT, mmin=0.0, mmax=200.0, initial=100.0, unitstyle=U_PCT,
                          modmode=MOD_BIPOLAR, info="Stereo spread of the 5 voices: 0 mono, 100 even, 200 wide."),
         "width", scale=0.01)
    dial("output", valueof("Output", "Output", T_FLOAT, mmin=-36.0, mmax=0.0, initial=-6.0, unitstyle=U_DB,
                           modmode=MOD_BIPOLAR, info="Output level (the 5-voice sum is compensated by -14 dB)."),
         "output")
    return c


# ---- face layouts -------------------------------------------------------------------------------------

@dataclass
class Layout:
    face: str
    width: float
    controls: list[Ctl]
    labels: list[Label]
    lines: list[tuple[list[float], str]]          # live.line dividers (vertical, line centred in a 3-px box)
    panels: list[tuple[list[float], str]]         # theme surfaces (D22), drawn first
    markers: list[tuple[list[float], str]]        # matrix row markers (panel boxes, coloured by the pages script)
    meters: list[tuple[list[float], str, int]]    # live.meter~: rect, varname, gen~ outlet (2 = follower)
    display: list[float]                          # v8ui rect


def comment_at(text: str, x: float, base: float, w: float, var: str, *, bold: bool = False, just: int = 0,
               size: float = FS, h: float = 15.0) -> Label:
    """A live.comment whose text starts at x (left), is centred in w (centre) or ends at x (right), with its
    baseline at base: the text sits 4 px in from the box edge and its baseline 11 px below the box top
    [measured: face review §0 for 8-9 pt; hypothesis for 9.5 pt]."""
    if just == 2:
        bx = x + 4 - w
    elif just == 1:
        bx = x
    else:
        bx = x - 4
    return Label(text, r(bx, base - 11, w, h), var, size, bold, just)


def overlay(text: str, dial: list[float], var: str) -> Label:
    """Name row of a dial written by a comment (h.2): baseline at the painter's name baseline (dial y + 10)."""
    return Label(text, r(dial[0], dial[1] - 1, dial[2], 15), var, FS, False, 1, overlay=True)


def place(sp: dict[str, Ctl], out: list[Ctl], key: str, var: str, rect: list[float], **extra) -> list[float]:
    c = sp[key]
    c.var = var
    c.rect = rect
    if c.cls == "live.dial":
        c.extra = {**c.extra, "showname": 1, "shownumber": 1}
    c.extra = {**c.extra, **extra}
    out.append(c)
    return rect


# D47 (user, 2026-11-25): the pointer rows end 50 px earlier (Freeze / Write / Clean stacked next to the
# dials), and everything right of them moves left by this much: the hybrid is 918 px wide. The rects below
# keep face review h.1's numbers; shift_x() moves every rect at x >= 300.
HYBRID_SHIFT = -50.0


def shift_x(rect: list[float]) -> list[float]:
    return [rect[0] + HYBRID_SHIFT, rect[1], rect[2], rect[3]] if rect[0] >= 300 else rect


def layout_hybrid() -> Layout:
    """Face review "Hybrid" h.1: (a)'s structure with (b)'s measures; compact pointer rows (D47)."""
    sp = specs("hybrid")
    C: list[Ctl] = []
    L: list[Label] = []
    for p, title, y0 in (("w", "Write", 4.0), ("r", "Read", 86.0)):
        L.append(comment_at(title, 12, y0 + 13, 52, f"{p}_title", bold=True))
        place(sp, C, f"{p}.mode", f"{p}_mode", r(10, y0 + 18, 50, LINE_H))
        place(sp, C, f"{p}.mult", f"{p}_sync_mult", r(10, y0 + 36, 24, LINE_H))
        place(sp, C, f"{p}.div", f"{p}_sync_div", r(36, y0 + 36, 24, LINE_H))
        d0 = place(sp, C, f"{p}.pitch", f"{p}_free_pitch", r(64, y0 + 4, 42, DIAL_H))
        place(sp, C, f"{p}.note", f"{p}_sync_note", list(d0))
        d1 = place(sp, C, f"{p}.fine", f"{p}_fine", r(106, y0 + 4, 42, DIAL_H))
        L.append(overlay("Fine", d1, f"{p}_free_lblfine"))
        L.append(overlay("Detune", d1, f"{p}_sync_lbldetune"))
        L.append(comment_at("Shape", 12, y0 + 69, 52, f"{p}_shapelbl"))
        if p == "w":
            d2 = place(sp, C, "w.sym", "w_sym", r(148, y0 + 4, 42, DIAL_H))
            for g in SYM_GROUPS:
                L.append(overlay(g.capitalize(), d2, f"w_symlbl_{g}"))
            # D47: a drop-down next to the dials, its name in their name row (user, 2026-11-25: the 3-row
            # switch read as a hamburger menu)
            sp["w.active"].cls = "live.menu"
            L.append(comment_at("State", 198, y0 + 14, 56, "w_statelbl"))
            place(sp, C, "w.active", "w_active", r(194, y0 + 20, 56, LINE_H))
            place(sp, C, "w.shape", "w_shape", r(64, y0 + 58, 24 * len(W_SHAPES), LINE_H))
        else:
            place(sp, C, "r.spread", "r_spread", r(148, y0 + 4, 42, DIAL_H))
            place(sp, C, "r.smooth", "r_smooth", r(194, y0 + 20, 56, LINE_H))  # D47: same column and height
            place(sp, C, "r.shape", "r_shape", r(64, y0 + 58, 56, LINE_H))
    place(sp, C, "size", "tbl_size", r(308, 145, 328, 18))
    place(sp, C, "page", "page", r(646, 8, 314, LINE_H))

    # LFO · Env (dx = 0, 106)
    for k in (1, 2):
        dx = (k - 1) * 106.0
        L.append(comment_at(f"LFO {k}", 648 + dx, 41, 44, f"lfo_l{k}title", bold=True))
        place(sp, C, f"lfo{k}.mode", f"lfo_l{k}mode", r(698 + dx, 30, 50, LINE_H))
        place(sp, C, f"lfo{k}.shape", f"lfo_l{k}shape", r(646 + dx, 50, 102, LINE_H))
        place(sp, C, f"lfo{k}.rate", f"lfo_hz{k}_rate", r(646 + dx, 70, 34, DIAL_H))
        place(sp, C, f"lfo{k}.note", f"lfo_sy{k}_note", r(646 + dx, 70, 34, DIAL_H))
        place(sp, C, f"lfo{k}.phase", f"lfo_l{k}phase", r(680 + dx, 70, 34, DIAL_H))
        place(sp, C, f"lfo{k}.spread", f"lfo_l{k}spread", r(714 + dx, 70, 34, DIAL_H))
        L.append(comment_at("Retrig", 648 + dx, 139, 34, f"lfo_l{k}retriglbl"))
        place(sp, C, f"lfo{k}.retrig", f"lfo_l{k}retrig", r(678 + dx, 128, 70, LINE_H))
    L.append(comment_at("Env Follower", 862, 41, 98, "lfo_envtitle", bold=True))
    for i, key in enumerate(("env.att", "env.rel", "env.gain")):
        place(sp, C, key, f"lfo_env_{key[4:]}", r(858 + 34 * i, 70, 34, DIAL_H))
    L.append(comment_at("post Tone · pre Limiter", 862, 139, 98, "lfo_envnote"))

    # Mod: destinations as rows (face review §7 option A, D36)
    xs = [710, 740, 770, 804, 834, 868, 898, 928]
    for (s, _, _, slabel), x in zip(SRCS, xs):
        L.append(Label("MW" if s == "mw" else slabel, r(x - 1, 28, 30, 13), f"mod_cl_{s}", FS, False, 1))
    markers = []
    for row, (t, tlong, _) in enumerate(TGTS):
        y = 44.0 + 13.0 * row
        markers.append((r(646, y + 2, 2, 8), f"mod_mark_{t}"))
        L.append(Label(tlong, r(648, y - 1, 60, 13), f"mod_rl_{t}", FS))
        for (s, _, _, _), x in zip(SRCS, xs):
            place(sp, C, f"mx.{s}.{t}", f"mod_{s}_{t}", r(x, y, 28, 12))

    # Tone
    place(sp, C, "drive.on", "tone_drive_on", r(646, 27, 44, LINE_H))
    place(sp, C, "band.on", "tone_band_on", r(698, 27, 44, LINE_H))
    place(sp, C, "band.mode", "tone_band_mode", r(748, 27, 84, LINE_H))
    place(sp, C, "band.slope", "tone_band_slope", r(836, 27, 70, LINE_H))
    place(sp, C, "drive", "tone_drive", r(646, 44, 44, DIAL_H))
    for i, key in enumerate(("center", "width", "res", "fm", "spread")):
        place(sp, C, f"band.{key}", f"tone_band_{key}", r(698 + 44 * i, 44, 44, DIAL_H))
    place(sp, C, "res.on", "tone_res_on", r(646, 96, 66, LINE_H))
    place(sp, C, "res.track", "tone_res_track", r(716, 96, 66, LINE_H))
    for i, key in enumerate(("freq", "fb", "mix")):
        place(sp, C, f"res.{key}", f"tone_res_{key}", r(646 + 44 * i, 113, 44, DIAL_H))

    # Global: the version lines on top, Gate / Resync / buttons aligned to the bottom of the dial rows
    # (y 161) (user, 2026-11-25, D46)
    L.append(comment_at(f"Aliasing {VERSION}", 648, 38, 104, "out_info1", h=13))
    L.append(comment_at("after D. Pank", 648, 51, 104, "out_info2", h=13))
    L.append(comment_at("Gate", 648, 86, 100, "out_lgate"))
    place(sp, C, "gate", "out_gate", r(646, 90, 100, LINE_H))
    L.append(comment_at("Resync (bars)", 648, 119, 100, "out_lresync"))
    place(sp, C, "resync", "out_resync", r(646, 123, 100, LINE_H))
    place(sp, C, "syncnow", "out_syncnow", r(646, 146, 48, LINE_H))
    place(sp, C, "aa", "out_aa", r(698, 146, 48, LINE_H))
    place(sp, C, "lim.on", "out_lim_on", r(754, 27, 52, LINE_H))
    for i, key in enumerate(("gain", "sat", "color", "rel", "ceil")):
        place(sp, C, f"lim.{key}", f"out_lim_{key}", r(754 + 36 * i, 44, 36, DIAL_H))
    L.append(comment_at("Tune", 756, 107, 46, "out_ltune"))
    place(sp, C, "transpose", "out_transpose", r(752, 113, 46, DIAL_H))
    place(sp, C, "syncrate", "out_syncrate", r(800, 113, 36, DIAL_H))
    L.append(comment_at("Output", 864, 107, 70, "out_lout"))
    place(sp, C, "width", "out_width", r(862, 113, 36, DIAL_H))
    place(sp, C, "output", "out_output", r(898, 113, 36, DIAL_H))
    for c in C:
        c.rect = shift_x(c.rect)
    for lb in L:
        lb.rect = shift_x(lb.rect)
    return Layout(
        "hybrid", FACE_WIDTH["hybrid"], C, L,
        lines=[(shift_x(rc), v) for rc, v in [(r(749, 30, 3, 114), "lfo_div1"), (r(855, 30, 3, 114), "lfo_div2"),
                                              (r(748, 30, 3, 130), "out_div")]],
        panels=[(r(4, 4, 250, 79), "panel_w"), (r(4, 86, 250, 79), "panel_r"),  # D47: 300 -> 250
                (shift_x(r(306, 4, 332, 161)), "panel_disp"), (shift_x(r(642, 4, 322, 161)), "panel_page")],
        markers=[(shift_x(rc), v) for rc, v in markers],
        meters=[(shift_x(rc), v, o) for rc, v, o in [
            (r(942, 29, 8, 132), "out_meterl", 0), (r(952, 29, 8, 132), "out_meterr", 1),
            # from the "E" of "Env Follower" (text x 862) to the right edge of the Gain ring (943 + 12.5
            # + 1.25 = 957) (user, 2026-11-25, D46)
            (r(862, 54, 95, 7), "lfo_envmeter", 2)]],
        display=shift_x(r(308, 6, 328, 136)))


def layout_b() -> Layout:
    """Face review "Option (b)" b.2: display + side page / modulation strip / constant dial row, 800 x 169."""
    sp = specs("b")
    C: list[Ctl] = []
    L: list[Label] = []
    # band 3: the constant dial row
    for p, title, x0, dx in (("w", "Write", 4.0, 0.0), ("r", "Read", 334.0, 330.0)):
        L.append(comment_at(title, x0 + 6, 130, 50, f"{p}_title", bold=True))
        place(sp, C, f"{p}.mode", f"{p}_mode", r(8 + dx, 135, 56, LINE_H))
        place(sp, C, f"{p}.mult", f"{p}_sync_mult", r(8 + dx, 152, 27, LINE_H))
        place(sp, C, f"{p}.div", f"{p}_sync_div", r(37 + dx, 152, 27, LINE_H))
    for p, xs in (("w", (68, 116, 164)), ("r", (398, 446, 494))):
        d0 = place(sp, C, f"{p}.pitch", f"{p}_free_pitch", r(xs[0], 119, 48, DIAL_H))
        place(sp, C, f"{p}.note", f"{p}_sync_note", list(d0))
        d1 = place(sp, C, f"{p}.fine", f"{p}_fine", r(xs[1], 119, 48, DIAL_H))
        L.append(overlay("Fine", d1, f"{p}_free_lblfine"))
        L.append(overlay("Detune", d1, f"{p}_sync_lbldetune"))
        if p == "w":
            d2 = place(sp, C, "w.sym", "w_sym", r(xs[2], 119, 48, DIAL_H))
            for g in SYM_GROUPS:
                L.append(overlay(g.capitalize(), d2, f"w_symlbl_{g}"))
        else:
            place(sp, C, "r.spread", "r_spread", r(xs[2], 119, 48, DIAL_H))
    place(sp, C, "w.shape", "w_shape", r(216, 126, 22 * len(W_SHAPES), LINE_H))
    place(sp, C, "w.active", "w_active", r(216, 146, 110, LINE_H))
    place(sp, C, "r.shape", "r_shape", r(546, 126, 60, LINE_H))
    place(sp, C, "r.smooth", "r_smooth", r(546, 146, 60, LINE_H))
    place(sp, C, "size", "row_size", r(618, 119, 48, DIAL_H))
    place(sp, C, "width", "row_width", r(666, 119, 48, DIAL_H))
    place(sp, C, "output", "row_output", r(714, 119, 48, DIAL_H))

    # band 2: the modulation strip (D36); the menu marks modulated targets with a dot (D48) and a Clear
    # button resets the shown target's eight depths (D49), so the sources step by 80 px instead of 83
    L.append(comment_at("Mod", 10, 109, 28, "strip_title"))
    place(sp, C, "mod_target", "mod_target", r(34, 98, 80, LINE_H))
    place(sp, C, "mod_clear", "strip_clear", r(117, 98, 30, LINE_H))
    for i, (s, _, _, slabel) in enumerate(SRCS):
        L.append(comment_at(slabel, 182 + 80 * i, 109, 36, f"strip_lbl_{s}", just=2))
        for t, _, _ in TGTS:
            place(sp, C, f"mx.{s}.{t}", f"mod_{s}_{t}", r(188 + 80 * i, 98, 39, LINE_H))

    # band 1: side pages
    place(sp, C, "page", "page", r(512, 6, 280, LINE_H))
    x0, ly, dy = 514.0, 25.0, 43.0
    for k in (1, 2):
        a = f"lfo{k}"
        place(sp, C, f"lfo{k}.mode", f"{a}_l{k}mode", r(x0, ly, 48, LINE_H))
        place(sp, C, f"lfo{k}.shape", f"{a}_l{k}shape", r(566, ly, 108, LINE_H))
        L.append(comment_at("Retrig", 708, ly + 11, 38, f"{a}_retriglbl", just=2))
        place(sp, C, f"lfo{k}.retrig", f"{a}_l{k}retrig", r(712, ly, 78, LINE_H))
        place(sp, C, f"lfo{k}.rate", f"{a}_hz{k}_rate", r(x0, dy, 48, DIAL_H))
        place(sp, C, f"lfo{k}.note", f"{a}_sy{k}_note", r(x0, dy, 48, DIAL_H))
        place(sp, C, f"lfo{k}.phase", f"{a}_l{k}phase", r(x0 + 48, dy, 48, DIAL_H))
        place(sp, C, f"lfo{k}.spread", f"{a}_l{k}spread", r(x0 + 96, dy, 48, DIAL_H))
    L.append(comment_at("Level", 516, ly + 11, 34, "env_lbllevel"))
    L.append(comment_at("post Tone · pre Limiter", 790, ly + 11, 122, "env_note", just=2))
    for i, key in enumerate(("env.att", "env.rel", "env.gain")):
        place(sp, C, key, f"env_env_{key[4:]}", r(x0 + 48 * i, dy, 48, DIAL_H))
    place(sp, C, "band.on", "band_band_on", r(x0, ly, 44, LINE_H))
    place(sp, C, "band.mode", "band_band_mode", r(562, ly, 84, LINE_H))
    place(sp, C, "band.slope", "band_band_slope", r(650, ly, 70, LINE_H))
    place(sp, C, "drive.on", "band_drive_on", r(744, ly, 46, LINE_H))
    for i, key in enumerate(("center", "width", "res", "fm", "spread")):
        place(sp, C, f"band.{key}", f"band_band_{key}", r(x0 + 46 * i, dy, 46, DIAL_H))
    place(sp, C, "drive", "band_drive", r(744, dy, 46, DIAL_H))
    place(sp, C, "res.on", "res_res_on", r(x0, ly, 66, LINE_H))
    place(sp, C, "res.track", "res_res_track", r(584, ly, 66, LINE_H))
    for i, key in enumerate(("freq", "fb", "mix")):
        place(sp, C, f"res.{key}", f"res_res_{key}", r(x0 + 48 * i, dy, 48, DIAL_H))
    place(sp, C, "lim.on", "lim_lim_on", r(x0, ly, 52, LINE_H))
    for i, key in enumerate(("gain", "sat", "color", "rel", "ceil")):
        place(sp, C, f"lim.{key}", f"lim_lim_{key}", r(x0 + 48 * i, dy, 48, DIAL_H))
    place(sp, C, "gate", "out_gate", r(x0, ly, 84, LINE_H))
    L.append(comment_at("Resync (bars)", 676, ly + 11, 80, "out_lresync", just=2))
    place(sp, C, "resync", "out_resync", r(680, ly, 110, LINE_H))
    place(sp, C, "transpose", "out_transpose", r(x0, dy, 48, DIAL_H))
    place(sp, C, "syncrate", "out_syncrate", r(x0 + 48, dy, 48, DIAL_H))
    place(sp, C, "syncnow", "out_syncnow", r(626, dy + 6, 64, LINE_H))
    place(sp, C, "aa", "out_aa", r(626, dy + 26, 64, LINE_H))
    L.append(comment_at(f"Aliasing {VERSION}", 790, dy + 17, 100, "out_info1", just=2))
    L.append(comment_at("after D. Pank", 790, dy + 37, 100, "out_info2", just=2))
    return Layout(
        "b", FACE_WIDTH["b"], C, L, lines=[],
        panels=[(r(4, 4, 500, 89), "panel_disp"), (r(508, 4, 288, 89), "panel_page"), (r(4, 95, 792, 21), "panel_mod"),
                (r(4, 118, 326, 50), "panel_w"), (r(334, 118, 276, 50), "panel_r"), (r(614, 118, 182, 50), "panel_out")],
        markers=[],
        meters=[(r(772, 122, 8, 42), "row_meterl", 0), (r(782, 122, 8, 42), "row_meterr", 1),
                (r(548, 29, 120, 7), "env_meter", 2)],
        display=r(6, 6, 496, 85))


def layout_of(face: str) -> Layout:
    if face not in FACES:
        raise ValueError(f"unknown face {face!r} (hybrid | b)")
    lay = layout_hybrid() if face == "hybrid" else layout_b()
    placed = {c.key for c in lay.controls}
    missing = sorted(set(specs(face)) - placed)
    assert not missing, f"face {face}: controls without a place: {missing}"
    return lay


def controls(face: str = "hybrid") -> list[Ctl]:
    return layout_of(face).controls


def build(template: dict, face: str = "hybrid") -> dict:
    pat = template["patcher"]
    plugout = next(b["box"] for b in pat["boxes"] if b["box"].get("text") == "plugout~")
    lay = layout_of(face)
    st0 = initial_state(face)
    p = Patch()

    def hide_rule(box: dict) -> dict:
        vis = visible_in(str(box.get("varname", "")), st0)
        if vis is False:
            box["hidden"] = 1
        return box

    def prect(rect: list[float]) -> list[float]:
        return [rect[0], rect[1] + 1200.0, rect[2], rect[3]]

    # ---- panels and row markers first (back of the z-order) -------------------------------------------
    for rect, var in lay.panels:
        p.add({"maxclass": "panel", "varname": var, "numinlets": 1, "numoutlets": 0, "background": 1,
               "mode": 0, "border": 0, "rounded": 4, "bgcolor": PANEL_FALLBACK, "bgfillcolor": PANEL_FALLBACK,
               "patching_rect": prect(rect), "presentation": 1, "presentation_rect": rect})
    for rect, var in lay.markers:
        role = TARGET_ROLE.get(var.split("_")[-1], "neutral")
        col = READ if role == "read" else [0.5, 0.5, 0.5, 1.0] if role == "neutral" else [0.15, 0.15, 0.15, 1.0]
        p.add(hide_rule({"maxclass": "panel", "varname": var, "numinlets": 1, "numoutlets": 0, "background": 1,
                         "mode": 0, "border": 0, "rounded": 0, "bgcolor": col, "bgfillcolor": col,
                         "patching_rect": prect(rect), "presentation": 1, "presentation_rect": rect}))
    p.boxes.append({"box": {**plugout, "id": "obj-plugout", "patching_rect": [40.0, 980.0, 120.0, 22.0]}})

    # ---- core --------------------------------------------------------------------------------------
    gen = p.obj("gen~ @gen aliasing @atab ---atab @aheads ---aheads", 40.0, 920.0, 4,
                ["signal", "signal", "signal"], w=330.0)
    p.obj("buffer~ ---atab @samps 1024 5", 420.0, 920.0, 1, ["float", "bang"])
    p.obj("buffer~ ---aheads @samps 5 10", 420.0, 950.0, 1, ["float", "bang"])
    # sample drop (D50-D54): a mono buffer, so `read <file> 0 <ms>` sums the file's channels and reads at
    # most its size [sourced: msp-ref/buffer~.maxref.xml "read"]; the display sizes it per drop
    adrop = p.obj("buffer~ ---adrop @samps 1 1", 1440.0, 760.0, 1, ["float", "bang"], w=170.0)
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
    dr = lay.display
    # sample drop zone (D50): an invisible live.drop at the display's rect, directly behind it, clicks
    # passing through (ignoreclick) - Ableton's pattern in Granulator III, Emit and Vector Grain. Hidden
    # parameter: a Set never re-imports a file at load, the table itself is stored (dict "Table")
    clear = [0.3, 0.3, 0.3, 0.0]
    sdrop = p.add({"maxclass": "live.drop", "varname": "sample_drop", "numinlets": 1, "numoutlets": 2,
                   "outlettype": ["", ""], "parameter_enable": 1, "ignoreclick": 1, "decodemode": 1, "legend": "",
                   "bordercolor": clear, "focusbordercolor": clear, "textcolor": clear,
                   "patching_rect": [1440.0, 600.0, 120.0, 40.0], "presentation": 1, "presentation_rect": list(dr),
                   "saved_attribute_attributes": {
                       "bordercolor": {"expression": ""}, "focusbordercolor": {"expression": ""},
                       "textcolor": {"expression": ""},
                       "valueof": {"parameter_longname": "Sample Drop", "parameter_shortname": "Drop",
                                   "parameter_type": 4, "parameter_invisible": HIDDEN, "parameter_modmode": 0}}})
    disp = p.add({"maxclass": "v8ui", "filename": "aliasing_display.js", "embed": 0, "numinlets": 1,
                  "numoutlets": 2, "outlettype": ["", ""], "parameter_enable": 0,
                  "patching_rect": list(dr), "presentation": 1, "presentation_rect": list(dr), "varname": "display",
                  "textfile": {"filename": "aliasing_display.js", "flags": 0, "embed": 0, "autowatch": 1}})
    pages = p.obj(f"v8 aliasing_pages.js {face}", 840.0, 560.0, 1, [], w=160.0,
                  saved_object_attributes={"embed": 0, "parameter_enable": 0},
                  textfile={"filename": "aliasing_pages.js", "flags": 0, "embed": 0, "autowatch": 1})
    thisdev = p.obj("live.thisdevice", 840.0, 480.0, 1, ["bang", "int", "int"], w=105.0)
    init = p.obj("t b b b", 840.0, 520.0, 1, ["bang", "bang", "bang"])
    bufmsg = p.msg("buffers ---atab ---aheads ---atable ---adrop", 960.0, 520.0)
    tpmsg = p.msg("tonepages " + " ".join(str(k) for k in FACE_TONE_PAGES[face]), 1260.0, 480.0)
    facemsg = p.msg(f"face {face}", 1000.0, 480.0)
    p.wire(thisdev, 0, init, 0)
    p.wire(init, 2, bufmsg, 0)
    p.wire(init, 2, tpmsg, 0)
    p.wire(bufmsg, 0, disp, 0)
    p.wire(tpmsg, 0, disp, 0)
    p.wire(init, 1, facemsg, 0)  # after load: apply the face, the stored page and modes
    p.wire(facemsg, 0, pages, 0)
    # panel, marker and meter colours from Live's theme (D22, D39): at load and whenever the theme changes
    lcol = p.obj("live.colors", 1260.0, 560.0, 1, ["", "bang"], w=80.0)
    lqry = p.msg("live_surface_bg", 1260.0, 520.0)
    lpre = p.obj("prepend surface", 1260.0, 600.0, 1, [""])
    p.wire(init, 0, lqry, 0)
    p.wire(lcol, 1, lqry, 0)
    p.wire(lqry, 0, lcol, 0)
    p.wire(lcol, 0, lpre, 0)
    p.wire(lpre, 0, pages, 0)

    # the display's gestures -> parameters; the stored Display Mode tab (not on the face)
    route_names = ["mode", "center", "bwidth", "bres", "bmode", "rsfreq", "rsfb", "rsmix", "rstrack", "reson",
                   "fit", "wactive", "sfopen", "bufsize", "bufread"]
    route = p.obj("route " + " ".join(route_names), 960.0, 600.0, len(route_names) + 1,
                  [""] * (len(route_names) + 1), w=640.0)
    p.wire(disp, 0, route, 0)
    dmode = p.add({"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
                   "parameter_enable": 1, "patching_rect": [960.0, 640.0, 60.0, 15.0], "varname": "display_mode",
                   "num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0, "fontname": FONT,
                   "fontsize": FS, "saved_attribute_attributes": {"valueof": valueof(
                       "Display Mode", "Disp Mode", T_ENUM, enum=["Line", "2D"], invisible=STORED_ONLY,
                       info="Table display: Line or 2D (the icons in the display).")}})
    p.wire(route, 0, dmode, 0)
    mpre = p.obj("prepend mode", 960.0, 670.0, 1, [""])
    p.wire(dmode, 0, mpre, 0)
    p.wire(mpre, 0, disp, 0)

    # sample drop (D50-D54, v0.3-design 4c): live.drop -> display -> sfinfo~ (length, rate, channels) ->
    # display -> buffer~ ---adrop (size, read) -> "dropready" -> display (fits, Freeze, writes, stores)
    dfit = p.add({"maxclass": "live.tab", "numinlets": 1, "numoutlets": 3, "outlettype": ["", "", "float"],
                  "parameter_enable": 1, "patching_rect": [1440.0, 520.0, 60.0, 15.0], "varname": "drop_fit",
                  "num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0, "fontname": FONT,
                  "fontsize": FS, "saved_attribute_attributes": {"valueof": valueof(
                      "Drop Fit", "Drop Fit", T_ENUM, enum=["Fit", "1:1"], invisible=STORED_ONLY,
                      info="Sample drop: Fit = the whole file resampled to the table row, 1:1 = its first 1024 "
                           "samples (the FIT / 1:1 pills in the display).")}})
    p.wire(route, route_names.index("fit"), dfit, 0)
    fpre = p.obj("prepend fit", 1440.0, 550.0, 1, [""])
    p.wire(dfit, 0, fpre, 0)
    p.wire(fpre, 0, disp, 0)
    dpre = p.obj("prepend droppath", 1580.0, 600.0, 1, [""], w=110.0)
    p.wire(sdrop, 0, dpre, 0)
    p.wire(dpre, 0, disp, 0)
    sfopen = p.obj("prepend open", 1440.0, 660.0, 1, [""])
    sfinfo = p.obj("sfinfo~", 1440.0, 690.0, 1, ["int", "int", "float", "float", "", ""], w=170.0)
    p.wire(route, route_names.index("sfopen"), sfopen, 0)
    p.wire(sfopen, 0, sfinfo, 0)
    for k, name in ((3, "sfms"), (2, "sfsr"), (0, "sfch")):  # sfinfo~ outputs right to left: channels last
        pre = p.obj(f"prepend {name}", 1440.0 + 60.0 * k, 720.0, 1, [""])
        p.wire(sfinfo, k, pre, 0)
        p.wire(pre, 0, disp, 0)
    bsize = p.obj("prepend sizeinsamps", 1620.0, 700.0, 1, [""], w=120.0)
    bread = p.obj("prepend read", 1620.0, 730.0, 1, [""])
    p.wire(route, route_names.index("bufsize"), bsize, 0)
    p.wire(route, route_names.index("bufread"), bread, 0)
    p.wire(bsize, 0, adrop, 0)
    p.wire(bread, 0, adrop, 0)
    dready = p.msg("dropready", 1440.0, 800.0)
    p.wire(adrop, 1, dready, 0)  # right outlet: read done
    p.wire(dready, 0, disp, 0)

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

    # ---- controls; each dial's name-row overlays right after it (drawn on top, h.2) ---------------------
    by_var: dict[str, str] = {}
    by_key: dict[str, str] = {}
    col = {"n": 0}
    overlays: dict[str, list[Label]] = {}
    for lb in lay.labels:
        if lb.overlay:
            overlays.setdefault(f"{lb.rect[0]}:{lb.rect[1] + 1}", []).append(lb)

    def logic_xy() -> tuple[float, float]:
        k = col["n"]
        col["n"] += 1
        return 40.0 + (k % 9) * 150.0, 1450.0 + (k // 9) * 30.0

    def add_label(lb: Label) -> None:
        box = {"maxclass": "live.comment", "text": lb.text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": prect(lb.rect), "presentation": 1, "presentation_rect": list(lb.rect),
               "fontname": FONT_BOLD if lb.bold else FONT, "fontsize": lb.size, "textjustification": lb.just,
               "varname": lb.var}
        if lb.overlay:
            box["ignoreclick"] = 1
        p.add(hide_rule(box))

    for ctl_ in lay.controls:
        rect = ctl_.rect
        box: dict = {"maxclass": ctl_.cls, "varname": ctl_.var, "patching_rect": prect(rect),
                     "presentation": 1, "presentation_rect": rect,
                     "jspainterfile": ctl_.painter or PAINTER[ctl_.cls], "fontname": FONT, "fontsize": FS}
        outs = {"live.dial": ["", "float"], "live.tab": ["", "", "float"], "live.text": ["", ""],
                "live.slider": ["", "float"], "live.menu": ["", "", "float"], "live.numbox": ["", "float"]}[ctl_.cls]
        box.update({"numinlets": 1, "numoutlets": len(outs), "outlettype": outs})
        if ctl_.cls == "live.tab":
            box.update({"num_lines_patching": 1, "num_lines_presentation": 1, "multiline": 0})
        if ctl_.cls == "live.text" and ctl_.extra.get("mode") == 1:
            box["outputmode"] = 1  # D38: toggles switch on mouse up (Ableton checklist)
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
            # live.text: Live shows its two values with the box attributes automation /
            # automationon ("val1"/"val2" when absent, whatever parameter_enum says) [sourced:
            # live.text.maxref.xml "Automation Off/On Label"; measured: testlog t4-auto, 2026-11-25]
            if ctl_.cls == "live.text" and len(ctl_.vo.get("parameter_enum", [])) == 2:
                box["automation"], box["automationon"] = ctl_.vo["parameter_enum"]
        box["saved_attribute_attributes"] = saa
        oid = p.add(hide_rule(box))
        by_var[ctl_.var] = oid
        by_key[ctl_.key] = oid
        for lb in overlays.pop(f"{rect[0]}:{rect[1]}", []) if ctl_.cls == "live.dial" else []:
            add_label(lb)
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
            if face == "b" and ctl_.gen.startswith("mx_"):
                p.wire(pre, 0, pages, 0)  # the pages script marks modulated targets in the menu (D48)
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
                p.wire(pre, 0, disp, 0)  # the display shows the tone curve on the tone pages
    assert not overlays, f"overlays without a dial: {list(overlays)}"

    # display gestures -> the controls (user gestures: undo entries are intended here)
    targets = {"center": "band.center", "bwidth": "band.width", "bres": "band.res", "bmode": "band.mode",
               "rsfreq": "res.freq", "rsfb": "res.fb", "rsmix": "res.mix", "rstrack": "res.track", "reson": "res.on",
               "wactive": "w.active"}  # a sample drop sets Write State to Freeze (D53)
    for k, name in enumerate(route_names):
        if name in targets:
            p.wire(route, k, by_key[targets[name]], 0)

    # face b: Clear -> the pages script resets the shown target's eight depths (D49). Any output of the button
    # clears (twice is harmless): what a button-mode live.text sends on a click is not measured, and it sends
    # nothing on bang / int / float messages [measured: build/aliasing/btnprobe/Max.log, Max 9.2.1]
    if "mod_clear" in by_key:
        csel = p.obj("t b", 1260.0, 640.0, 1, ["bang"])
        cmsg = p.msg("clearmod", 1260.0, 670.0)
        p.wire(by_key["mod_clear"], 0, csel, 0)
        p.wire(csel, 0, cmsg, 0)
        p.wire(cmsg, 0, pages, 0)

    # Sync button -> click~ -> gen~ in2
    ssel = p.obj("sel 1", 1100.0, 600.0, 2, ["bang", ""])
    sclick = p.obj("click~", 1100.0, 640.0, 1, ["signal"])
    p.wire(by_key["syncnow"], 0, ssel, 0)
    p.wire(ssel, 0, sclick, 0)
    p.wire(sclick, 0, gen, 1)

    # output meter (L, R) and the follower level (gen~ out3); graphite colours from the pages script (D39)
    for k, (rect, var, outlet) in enumerate(lay.meters):
        box = {"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2, "outlettype": ["float", "int"],
               "patching_rect": [700.0 + 120.0 * k, 960.0, rect[2], rect[3]], "presentation": 1,
               "presentation_rect": rect, "varname": var}
        if rect[2] > rect[3]:
            box.update({"orientation": 1, "display_range": [-36.0, 0.0]})
        m = p.add(hide_rule(box))
        p.wire(gen, outlet, m, 0)

    # ---- labels and dividers ---------------------------------------------------------------------------
    for lb in lay.labels:
        if not lb.overlay:
            add_label(lb)
    for rect, var in lay.lines:
        p.add(hide_rule({"maxclass": "live.line", "numinlets": 1, "numoutlets": 0, "varname": var,
                         "patching_rect": prect(rect), "presentation": 1, "presentation_rect": rect}))

    new = dict(pat)
    new["boxes"] = p.boxes
    new["lines"] = p.lines
    new["openinpresentation"] = 1
    new["devicewidth"] = lay.width
    new["rect"] = [60.0, 80.0, 1440.0, 900.0]
    new["title"] = FACE_TITLE[face]
    new["description"] = (f"Aliasing {VERSION} ({'hybrid face' if face == 'hybrid' else 'face B'}): a 5-voice drone "
                          "where a table is written and read at different speeds, with tempo sync, LFOs, an envelope "
                          "follower, a mod matrix, a tone section and a color limiter. An original design inspired by "
                          "'aliasing Synth' by D. Pank (Reaktor User Library #5241, 2008).")
    new["default_fontname"] = FONT
    new["default_fontsize"] = FS
    new["dependency_cache"] = []
    new["project"] = with_runtime_files(new.get("project") or {}, p.boxes)
    return {"patcher": new}


def runtime_files(boxes: list[dict]) -> list[str]:
    """Every file the shell loads from its folder at run time: gen~ @gen <name>.gendsp, the v8 / v8ui scripts
    and the jspainter painters (referenced only by an attribute, no box of their own)."""
    files: set[str] = set()
    for b in boxes:
        x = b["box"]
        t = str(x.get("text", ""))
        if t.startswith("gen~ ") and "@gen " in t:
            files.add(t.split("@gen ", 1)[1].split()[0] + ".gendsp")
        if t.startswith("v8 "):
            files.add(t.split()[1])
        if x.get("maxclass") == "v8ui" and x.get("filename"):
            files.add(x["filename"])
        if x.get("jspainterfile"):
            files.add(x["jspainterfile"])
    return sorted(files)


def with_runtime_files(project: dict, boxes: list[dict]) -> dict:
    """The device project lists the runtime files, so that Freeze embeds them: "freezing includes all files in
    the Project window" [sourced: Max user guide, projects]. Without the entry, Freeze missed the painters (t7,
    2026-11-25: "jsscriptnobox: can't find file aliasing_paint_dial.js" while freezing). Format as Max saves it,
    e.g. Ableton's Vector Map.amxd: contents.code = {"x.gendsp": {"kind": "gendsp", "local": 1}, "y.js":
    {"kind": "javascript", "local": 1}}."""
    proj = dict(project)
    contents = dict(proj.get("contents") or {})
    contents.setdefault("patchers", {})
    contents["code"] = {f: {"kind": "gendsp" if f.endswith(".gendsp") else "javascript", "local": 1}
                        for f in runtime_files(boxes)}
    proj["contents"] = contents
    return proj


def read_amxd(path: Path) -> tuple[bytes, dict]:
    data = path.read_bytes()
    i = data.index(b"ptch")
    n = struct.unpack("<I", data[i + 4:i + 8])[0]
    return data[:i], json.loads(data[i + 8:i + 8 + n].rstrip(b"\x00").decode("utf-8"))


def write_amxd(path: Path, head: bytes, patch: dict) -> None:
    body = json.dumps(patch, indent="\t", ensure_ascii=False).encode("utf-8") + b"\n\x00"
    path.write_bytes(head + b"ptch" + struct.pack("<I", len(body)) + body)


def param_table(face: str) -> str:
    rows = ["| Long name | Control | Range / items | Initial | gen~ Param | Scripting name |", "|---|---|---|---|---|---|"]
    for c in controls(face):
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


def layout_table(face: str) -> str:
    """Markdown table of every presentation rect of a face, in box order (docs/mockup-v0.3b/layout-<face>.md)."""
    lay = layout_of(face)
    st0 = initial_state(face)

    def row(kind: str, var: str, rect: list[float], note: str = "") -> str:
        vis = visible_in(var, st0)
        rule = "always" if vis is None else ("shown at load" if vis else "hidden at load")
        return f"| `{var}` | {kind} | {' '.join(f'{v:g}' for v in rect)} | {rule} | {note} |"
    out = [f"| Scripting name | Object | Rect x y w h | Visible | Note |", "|---|---|---|---|---|"]
    for rect, var in lay.panels:
        out.append(row("panel", var, rect, "theme surface (D22)"))
    for rect, var in lay.markers:
        out.append(row("panel (marker)", var, rect, f"row role {TARGET_ROLE.get(var.split('_')[-1], 'neutral')}"))
    out.append(row("v8ui", "display", lay.display, "Tone page: 308 6 328 157 (D31)" if face == "hybrid" else
                   "tone curve on Band and Res"))
    seen_cells = 0
    for c in lay.controls:
        vo = c.vo or {}
        if face == "b" and c.var.startswith("mod_") and c.var != "mod_target":
            if c.var.endswith("_wp"):
                out.append(row(c.cls, c.var.replace("_wp", "_<t>"), c.rect, "9 cells at this rect, one per target; "
                               "visible while Mod Target = t"))
            seen_cells += 1
            continue
        if face == "hybrid" and c.var.startswith("mod_"):
            if c.var.startswith("mod_l1_"):
                out.append(row(c.cls, c.var.replace("mod_l1_", "mod_<s>_"), c.rect,
                               "row; sources at x 710 740 770 804 834 868 898 928"))
            seen_cells += 1
            continue
        h = " (Live draws 48)" if c.cls == "live.dial" else ""
        out.append(row(c.cls, c.var, c.rect, f"{vo.get('parameter_longname', '')}{h}"))
    for lb in lay.labels:
        if face == "hybrid" and lb.var.startswith("mod_cl_") and not lb.var.endswith("_l1"):
            continue
        kind = "live.comment" + (" overlay" if lb.overlay else "") + (" bold" if lb.bold else "")
        note = f"\"{lb.text}\"" + (", centred" if lb.just == 1 else ", right" if lb.just == 2 else "")
        if face == "hybrid" and lb.var == "mod_cl_l1":
            note += "; headers for all 8 sources at cell x - 1"
        out.append(row(kind, lb.var, lb.rect, note))
    for rect, var, outlet in lay.meters:
        out.append(row("live.meter~", var, rect, "follower (gen~ out3)" if outlet == 2 else f"output {'LR'[outlet]}"))
    for rect, var in lay.lines:
        out.append(row("live.line", var, rect, "divider"))
    out.append(f"\n{len(lay.controls)} controls ({seen_cells} matrix cells), {len(lay.labels)} comments, "
               f"{len(lay.panels)} panels, {len(lay.markers)} markers, {len(lay.meters)} meters, {len(lay.lines)} dividers.")
    return "\n".join(out)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--face", choices=FACES, default="hybrid", help="hybrid (Aliasing.amxd) or b (Aliasing B.amxd)")
    ap.add_argument("--template", type=Path, default=TEMPLATE, help="Live's Max Instrument.amxd")
    ap.add_argument("--out", type=Path, default=None, help="output .amxd (default: the face's file in the device folder)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output (discards Max edits)")
    ap.add_argument("--list-params", action="store_true", help="print the parameter table (Markdown) and exit")
    ap.add_argument("--list-layout", action="store_true", help="print the layout table (Markdown) and exit")
    args = ap.parse_args(argv)
    if args.list_params:
        print(param_table(args.face))
        return 0
    if args.list_layout:
        print(layout_table(args.face))
        return 0
    out = args.out or DEVICE / FACE_FILE[args.face]
    if out.exists() and not args.force:
        print(f"bootstrap_shell: {out} exists - it is the source of truth now; use --force to overwrite",
              file=sys.stderr)
        return 3
    head, template = read_amxd(args.template)
    if not head.startswith(b"ampf") or b"iiii" not in head:
        print("bootstrap_shell: template is not an instrument .amxd", file=sys.stderr)
        return 2
    write_amxd(out, head, build(template, args.face))
    print(f"wrote {out} (face {args.face})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
