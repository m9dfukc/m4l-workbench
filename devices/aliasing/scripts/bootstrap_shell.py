#!/usr/bin/env python3
"""Bootstrap of the Aliasing shell (devices/aliasing/Aliasing.amxd), v0.2.

Starts from Live's own instrument template (Max Instrument.amxd), keeps its patcher settings and
plugout~, and builds the v0.2 face of the approved mock-up (docs/redesign-t1.md, mock-up section;
layout and decisions in docs/v0.2-build.md): pointer rows (write, read) with Hz|Sync, the v8ui
display with the Size bar overlaid, the paged area LFO / Mod / Tone / Out. Every control is a real
live.* parameter drawn by a jspainter script (aliasing_paint_*.js, R5); labels are live.comment.
Logic: MIDI (notes held, note-on impulse, velocity, mod wheel), transport (plugsync~, a locked bar
phasor~), the gen~ core with its two buffer~s, the v8ui display, the v8 page switcher and a dict
Blob parameter that stores the drawn table with the Live Set (R10). Box JSON follows real
Max-saved boxes (tools: m4l-boxref).

The unfrozen Aliasing.amxd is the source of truth once the user edits it in Max. This script
therefore refuses to overwrite an existing file unless --force is given, and --force discards
every edit made in Max since. (v0.1 -> v0.2 was regenerated with --force on 2026-11-25: the
v0.1 shell had no edits made in Max.)

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

# Graphite accents of the mock-up (dark theme); used as the stock colours if a painter fails.
WRITE = [0.894118, 0.894118, 0.894118, 1.0]  # #e4e4e4
READ = [0.560784, 0.65098, 0.713725, 1.0]  # #8fa6b6
NEUTRAL = [0.788235, 0.788235, 0.788235, 1.0]  # #c9c9c9

# unit styles / modulation modes / visibility (Max refpage m4l-ref/parameters.maxref.xml)
U_INT, U_FLOAT, U_HZ, U_DB, U_PCT, U_ST, U_CUSTOM = 0, 1, 3, 4, 5, 7, 9
MOD_NONE, MOD_BIPOLAR, MOD_ABSOLUTE = 0, 2, 4
T_FLOAT, T_INT, T_ENUM, T_BLOB = 0, 1, 2, 3
STORED_ONLY = 1

NOTES = ["8 bars", "4 bars", "2 bars", "1 bar", "1/2", "1/2D", "1/2T", "1/4", "1/4D", "1/4T", "1/8", "1/8D",
         "1/8T", "1/16", "1/16D", "1/16T", "1/32", "1/32T", "1/64"]  # = Data divb in the GenExpr
LFO_SHAPES = ["Sine", "Tri", "Saw", "Square", "S&H", "Random"]
MOD_SOURCES = ["None", "LFO 1", "LFO 2", "Drift", "Velocity", "Mod Wheel"]
MOD_TARGETS = ["None", "Write Pitch", "Read Pitch", "Size", "Write Sym", "Read Spread", "Band Center",
               "Band Width", "Res Freq", "Width", "Output"]

PAINTER = {"live.dial": "aliasing_paint_dial.js", "live.tab": "aliasing_paint_tab.js",
           "live.text": "aliasing_paint_toggle.js", "live.slider": "aliasing_paint_slider.js",
           "live.menu": "aliasing_paint_menu.js", "live.numbox": "aliasing_paint_number.js"}


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


# ---- the page / mode visibility rule (mirror of js/src/pages_model.ts, initial state) -------------

INITIAL = {"page": 0, "wmode": 0, "rmode": 0, "l1mode": 0, "l2mode": 1}


def visible_at_load(varname: str) -> bool | None:
    parts = varname.split("_")
    if len(parts) < 2:
        return None
    area, cond = parts[0], parts[1]
    pages = ["lfo", "mod", "tone", "out"]
    if area in pages:
        ok = pages.index(area) == INITIAL["page"]
    elif area == "tbl":
        ok = INITIAL["page"] != 2
    elif area in ("w", "r"):
        ok = True
    else:
        return None
    sync = {"w": INITIAL["wmode"], "r": INITIAL["rmode"]}
    conds = {"hz1": INITIAL["l1mode"] < 0.5, "sy1": INITIAL["l1mode"] > 0.5,
             "hz2": INITIAL["l2mode"] < 0.5, "sy2": INITIAL["l2mode"] > 0.5}
    if cond in ("free", "sync") and area in sync:
        c = (sync[area] < 0.5) if cond == "free" else (sync[area] > 0.5)
    else:
        c = conds.get(cond, True)
    return ok and c


# ---- control specs ----------------------------------------------------------------------------------

@dataclass
class Ctl:
    cls: str                      # live.dial / live.tab / live.text / live.slider / live.menu / live.numbox
    var: str                      # scripting name (page / mode / role rules)
    rect: list[float]             # presentation rect
    vo: dict | None               # valueof (None = no parameter)
    gen: str | None = None        # gen~ Param name ("prepend <gen>")
    scale: float | None = None    # multiply before gen~ (percent -> 0..1)
    pv: str | None = None         # "pv <name>" to the display
    pages: str | None = None      # message name to the page switcher
    extra: dict = field(default_factory=dict)
    accent: list[float] | None = None


def controls() -> list[Ctl]:
    c: list[Ctl] = []

    def dial(var, rect, vo, gen, accent=NEUTRAL, **kw):
        c.append(Ctl("live.dial", var, rect, vo, gen, accent=accent, **kw))

    def tab(var, rect, vo, gen, **kw):
        c.append(Ctl("live.tab", var, rect, vo, gen, **kw))

    def pill(var, rect, vo, gen, text, texton=None, **kw):
        c.append(Ctl("live.text", var, rect, vo, gen, extra={"mode": 1, "text": text, "texton": texton or text}, **kw))

    def enum(long, short, items, init, info):
        return valueof(long, short, T_ENUM, enum=items, initial=init, modmode=MOD_ABSOLUTE, info=info)

    # ---- pointer rows (always visible) ----
    for k, (p, name, y0, acc) in enumerate((("w", "Write", 6.0, WRITE), ("r", "Read", 87.0, READ))):
        gp = p if p == "w" else "r"
        tab(f"{p}_mode", [8.0, y0 + 18, 54.0, 14.0], enum(f"{name} Mode", f"{name[0]} Mode", ["Hz", "Sync"], 0,
            f"{name} pointer rate: Hz = free pitch, Sync = note value x multiplier at Live's tempo."),
            f"{gp}mode", pages=f"{gp}mode")
        c.append(Ctl("live.numbox", f"{p}_sync_mult", [31.0, y0 + 36, 31.0, 14.0], valueof(
            f"{name} Mult", "Mult", T_INT, mmin=1, mmax=64, initial=1, unitstyle=U_CUSTOM, units="×%d",
            modmode=MOD_ABSOLUTE, info=f"Sync mode: the note value's rate times this, so synced {name.lower()} "
                                       "rates reach the audio range."), f"{gp}mult"))
        pitch_max, pitch_init = (130, 71) if p == "w" else (64, -30)
        info_p = ("Write pointer pitch in semitones around note 60 (-64..130 like the original). Above about half "
                  "the sample rate the written pattern depends on the sample rate (44.1 and 48 kHz differ)."
                  if p == "w" else "Read pointer pitch in semitones around note 60.")
        dial(f"{p}_free_pitch", [68.0, y0 + 15, 40.0, 45.0], valueof(
            f"{name} Pitch", "Pitch", T_INT, mmin=-64, mmax=pitch_max, initial=pitch_init, unitstyle=U_ST,
            modmode=MOD_ABSOLUTE, info=info_p), f"{gp}pitch", accent=acc)
        dial(f"{p}_sync_note", [68.0, y0 + 15, 40.0, 45.0], enum(
            f"{name} Rate", "Rate", NOTES, 13, f"Sync mode: {name.lower()} pointer note value (bars are 4/4)."),
            f"{gp}note", accent=acc)
        dial(f"{p}_fine", [110.0, y0 + 15, 40.0, 45.0], valueof(
            f"{name} Fine", "Fine", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.217 if p == "w" else 0.0,
            unitstyle=U_CUSTOM, units="%0.3f st", modmode=MOD_BIPOLAR,
            info="Fine pitch in semitones; in Sync mode a detune against the tempo grid (Resync re-locks it)."),
            f"{gp}fine", accent=acc)
        if p == "w":
            dial("w_sym", [152.0, y0 + 15, 40.0, 45.0], valueof(
                "Write Symmetry", "Sym", T_FLOAT, mmin=-1.0, mmax=1.0, initial=0.0, modmode=MOD_BIPOLAR,
                info="Write triangle skew: +1 rising saw, 0 triangle, -1 falling saw."), "wsym", accent=acc)
            tab("w_shape", [196.0, y0 + 17, 104.0, 18.0], enum(
                "Write Shape", "W Shape", ["Ramp", "Tri", "Tri ±", "=Read"], 1,
                "Write pointer: ramp, triangle 0..1, the original's -1..1 triangle (negative half clipped to the "
                "first cell), or the read pointer itself."), "wshape")
            pill("w_active", [196.0, y0 + 40, 50.0, 14.0], enum(
                "Write Active", "W Active", ["Off", "On"], 1, "Off freezes the table: only the read pointer runs."),
                "wactive", "Active")
        else:
            dial("r_spread", [152.0, y0 + 15, 40.0, 45.0], valueof(
                "Read Spread", "Spread", T_FLOAT, mmin=0.0, mmax=6.0, initial=2.0, unitstyle=U_CUSTOM,
                units="%0.2f st", modmode=MOD_BIPOLAR, info="Read pitch spread across the 5 voices."),
                "rspread", accent=acc)
            tab("r_shape", [196.0, y0 + 17, 104.0, 18.0], enum(
                "Read Shape", "R Shape", ["Ramp", "Tri"], 0, "Read pointer: ramp or triangle (Direction)."),
                "rshape")
            pill("r_smooth", [196.0, y0 + 40, 50.0, 14.0], enum(
                "Smooth", "Smooth", ["Off", "On"], 0, "Read interpolation: off reads whole cells (raw), on is linear."),
                "smoothread", "Smooth")
            pill("r_dir", [250.0, y0 + 40, 50.0, 14.0], enum(
                "Read Direction", "Direction", ["1-Way", "2-Way"], 0,
                "Read triangle: one way (rising ramp) or both ways."), "rdir", "1-Way", "2-Way")

    # ---- Size bar overlaid on the display (R9) ----
    c.append(Ctl("live.slider", "tbl_size", [312.0, 150.0, 320.0, 11.0], valueof(
        "Size", "Size", T_FLOAT, mmin=0.1, mmax=100.0, initial=10.0, unitstyle=U_PCT, exponent=2.0,
        modmode=MOD_BIPOLAR, info="Pointer span: both pointers cover only this part of the table; the display "
                                  "zooms to it."), "size", scale=0.01, pv="size",
        extra={"orientation": 1, "relative": 1, "showname": 0, "shownumber": 1}))

    # ---- page selector (stored only) ----
    c.append(Ctl("live.tab", "page", [644.0, 6.0, 316.0, 16.0], valueof(
        "Page", "Page", T_ENUM, enum=["LFO", "Mod", "Tone", "Out"], invisible=STORED_ONLY,
        info="Shows the LFO, Mod, Tone or Out controls."), None, pages="page"))

    # ---- LFO page (R3) ----
    for k in (1, 2):
        lx = 644.0 + (k - 1) * 163.0
        free_hz, sync_init, shape_init, retrig_init, phase_init, mode_init = (
            (0.15, 7, 0, 0, 0.0, 0) if k == 1 else (0.07, 3, 5, 2, 90.0, 1))
        tab(f"lfo_l{k}mode", [lx + 95, 28.0, 58.0, 13.0], enum(
            f"LFO {k} Mode", f"L{k} Mode", ["Hz", "Sync"], mode_init, f"LFO {k} rate: Hz or a note value."),
            f"l{k}mode", pages=f"l{k}mode")
        tab(f"lfo_l{k}shape", [lx, 45.0, 153.0, 16.0], enum(
            f"LFO {k} Shape", f"L{k} Shape", LFO_SHAPES, shape_init, f"LFO {k} waveform."), f"l{k}shape")
        dial(f"lfo_hz{k}_rate", [lx + 3.5, 77.0, 46.0, 42.0], valueof(
            f"LFO {k} Rate", "Rate", T_FLOAT, mmin=0.01, mmax=20.0, initial=free_hz, unitstyle=U_HZ, exponent=3.0,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate in Hz (each voice runs slightly faster or slower: Spread)."),
            f"l{k}rate")
        dial(f"lfo_sy{k}_note", [lx + 3.5, 77.0, 46.0, 42.0], enum(
            f"LFO {k} Sync Rate", "Rate", NOTES, sync_init, f"LFO {k} note value at Live's tempo."), f"l{k}note")
        dial(f"lfo_l{k}phase", [lx + 53.5, 77.0, 46.0, 42.0], valueof(
            f"LFO {k} Phase", "Phase", T_FLOAT, mmin=0.0, mmax=360.0, initial=phase_init, unitstyle=U_CUSTOM,
            units="%0.0f°", modmode=MOD_BIPOLAR, info=f"LFO {k} start phase (used on retrigger)."),
            f"l{k}phase")
        dial(f"lfo_l{k}spread", [lx + 103.5, 77.0, 46.0, 42.0], valueof(
            f"LFO {k} Spread", "Spread", T_FLOAT, mmin=0.0, mmax=100.0, initial=50.0, unitstyle=U_PCT,
            modmode=MOD_BIPOLAR, info=f"LFO {k} rate spread across the 5 voices (100 % = +-half an octave)."),
            f"l{k}spread")
        tab(f"lfo_l{k}retrig", [lx + 34, 125.0, 119.0, 13.0], enum(
            f"LFO {k} Retrig", f"L{k} Retrig", ["Off", "Note", "Bar"], retrig_init,
            f"LFO {k} restart: never, on every MIDI note-on, or on every bar while Live's transport runs."),
            f"l{k}retrig")

    # ---- Mod page (R4) ----
    defaults = {1: (1, 1), 2: (2, 2), 3: (0, 0), 4: (0, 0)}
    for s in range(1, 5):
        y = 44.0 + (s - 1) * 27.0
        src, tgt = defaults[s]
        c.append(Ctl("live.menu", f"mod_m{s}src", [662.0, y, 80.0, 18.0], enum(
            f"Mod {s} Source", "Source", MOD_SOURCES, src, f"Mod slot {s} source."), f"m{s}src"))
        c.append(Ctl("live.menu", f"mod_m{s}tgt", [758.0, y, 96.0, 18.0], enum(
            f"Mod {s} Target", "Target", MOD_TARGETS, tgt, f"Mod slot {s} target."), f"m{s}tgt"))
        c.append(Ctl("live.slider", f"mod_m{s}depth", [860.0, y + 2, 100.0, 14.0], valueof(
            f"Mod {s} Depth", "Depth", T_FLOAT, mmin=-100.0, mmax=100.0, initial=0.0, unitstyle=U_PCT,
            modmode=MOD_BIPOLAR, info=f"Mod slot {s} depth. Pitch targets: +-24 st x depth^3; Size +-3 octaves; "
                                      "Band +-4/5 octaves; Output +-24 dB."), f"m{s}depth",
            extra={"orientation": 1, "relative": 1, "showname": 0, "shownumber": 1}))

    # ---- Tone page (R16-R18) ----
    dial("tone_drive", [644.0, 52.0, 36.0, 36.0], valueof(
        "Drive", "Drive", T_FLOAT, mmin=0.0, mmax=24.0, initial=0.0, unitstyle=U_DB, modmode=MOD_BIPOLAR,
        info="Saturation before the band (tanh); 0 dB = clean."), "drive")
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
        dial(f"tone_band_{key}", [694.0 + 36.0 * k, 52.0, 36.0, 36.0], valueof(
            long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, units=units, exponent=expo,
            modmode=MOD_BIPOLAR, info=info), gen, accent=WRITE,
            pv={"center": "center", "width": "bwidth", "res": "bres"}.get(key))
    tab("tone_band_mode", [877.0, 55.0, 62.0, 13.0], enum(
        "Band Mode", "B Mode", ["Pass", "Reject"], 0, "Pass keeps the band, Reject removes it (band-stop)."),
        "bmode", pv="bmode")
    tab("tone_band_slope", [877.0, 72.0, 62.0, 13.0], enum(
        "Band Slope", "B Slope", ["12", "24 dB"], 1, "Band edge slope: 12 or 24 dB per octave."),
        "bslope", pv="bslope")
    res = [("freq", "Res Freq", "Freq", 20.0, 5000.0, 140.0, U_HZ, 3.0, "rsfreq",
            "Resonator frequency (inactive while Track follows the read pointer)."),
           ("fb", "Res Feedback", "Fdbk", -95.0, 95.0, 50.0, U_PCT, None, "rsfb",
            "Resonator feedback: + = peaks (metallic), - = notches (hollow)."),
           ("mix", "Res Mix", "Mix", 0.0, 100.0, 0.0, U_PCT, None, "rsmix", "Resonator mix; 0 = bypass.")]
    for k, (key, long, short, lo, hi, init, us, expo, gen, info) in enumerate(res):
        dial(f"tone_res_{key}", [656.0 + 36.0 * k, 117.0, 36.0, 36.0], valueof(
            long, short, T_FLOAT, mmin=lo, mmax=hi, initial=init, unitstyle=us, exponent=expo,
            modmode=MOD_BIPOLAR, info=info), gen, accent=READ, pv=gen)
    pill("tone_res_track", [767.0, 122.0, 64.0, 13.0], enum(
        "Res Track", "Track", ["Off", "On"], 1, "Resonator follows each voice's read pointer frequency."),
        "rstrack", "Track Read", pv="rstrack", pages="track")
    pill("tone_clip", [847.0, 122.0, 40.0, 13.0], enum(
        "Clip", "Clip", ["Off", "On"], 1, "Soft clip (tanh) on the output."), "softclip", "Clip")

    # ---- Out page (R13) ----
    tab("out_gate", [644.0, 41.0, 118.0, 16.0], enum(
        "Gate", "Gate", ["Drone", "MIDI"], 0,
        "Drone: the voices always run (Live's device switch turns them off). MIDI: sound while a note is held; "
        "every note-on restarts the pointers."), "gatemode")
    tab("out_resync", [644.0, 74.0, 118.0, 16.0], enum(
        "Resync", "Resync", ["Off", "1", "2", "4", "8"], 0,
        "Re-locks synced pointers every 1, 2, 4 or 8 bars while Live's transport runs (counted from the start)."),
        "resync")
    c.append(Ctl("live.text", "out_syncnow", [644.0, 98.0, 118.0, 16.0], enum(
        "Sync", "Sync", ["Off", "On"], 0, "Restarts both pointers now."), None,
        extra={"mode": 0, "text": "Sync now", "texton": "Sync now"}))
    pill("out_aa", [644.0, 120.0, 118.0, 16.0], enum(
        "Ramp AA", "Ramp AA", ["Off", "On"], 0,
        "Anti-aliased ramps (PolyBLEP) for both pointers, like the original's oscillators; off = naive."),
        "aaramp", "Ramp AA")
    for k, (var, vo, gen, scale) in enumerate((
            ("out_transpose", valueof("Transpose", "Transp", T_INT, mmin=-12, mmax=12, initial=0, unitstyle=U_ST,
                                      modmode=MOD_ABSOLUTE, info="Transposes both pointers (Free mode)."),
             "transpose", None),
            ("out_width", valueof("Width", "Width", T_FLOAT, mmin=0.0, mmax=200.0, initial=100.0, unitstyle=U_PCT,
                                  modmode=MOD_BIPOLAR, info="Stereo spread of the 5 voices: 0 mono, 100 even, 200 wide."),
             "width", 0.01),
            ("out_output", valueof("Output", "Output", T_FLOAT, mmin=-36.0, mmax=0.0, initial=-6.0, unitstyle=U_DB,
                                   modmode=MOD_BIPOLAR, info="Output level (the 5-voice sum is compensated by -14 dB)."),
             "output", None))):
        c.append(Ctl("live.dial", var, [772.0 + 46.0 * k, 41.0, 44.0, 45.0], vo, gen, scale=scale, accent=NEUTRAL))
    return c


# label texts and rects (live.comment), (text, rect, varname, size, bold, justification)
def labels() -> list[tuple[str, list[float], str, float, bool, int]]:
    out: list[tuple[str, list[float], str, float, bool, int]] = []
    for p, name, y0 in (("w", "WRITE", 6.0), ("r", "READ", 87.0)):
        out.append((name, [8.0, y0 + 1, 54.0, 14.0], f"{p}_title", 9.0, True, 0))
        out.append(("Mult", [6.0, y0 + 37, 24.0, 13.0], f"{p}_sync_multlbl", 8.0, False, 0))
        out.append(("Pitch", [68.0, y0 + 3, 40.0, 12.0], f"{p}_free_lbl1", 9.0, False, 1))
        out.append(("Rate", [68.0, y0 + 3, 40.0, 12.0], f"{p}_sync_lbl1", 9.0, False, 1))
        out.append(("Fine", [110.0, y0 + 3, 40.0, 12.0], f"{p}_free_lbl2", 9.0, False, 1))
        out.append(("Detune", [110.0, y0 + 3, 40.0, 12.0], f"{p}_sync_lbl2", 9.0, False, 1))
        out.append(("Sym" if p == "w" else "Spread", [152.0, y0 + 3, 40.0, 12.0], f"{p}_lbl3", 9.0, False, 1))
        out.append(("Shape", [196.0, y0 + 3, 60.0, 12.0], f"{p}_shapelbl", 9.0, False, 0))
    for k in (1, 2):
        lx = 644.0 + (k - 1) * 163.0
        out.append((f"LFO {k}", [lx, 27.0, 60.0, 14.0], f"lfo_l{k}title", 9.0, True, 0))
        for j, t in enumerate(("Rate", "Phase", "Spread")):
            out.append((t, [lx + 3.5 + 50.0 * j, 65.0, 46.0, 12.0], f"lfo_l{k}lbl{j}", 9.0, False, 1))
        out.append(("Retrig", [lx, 125.0, 34.0, 13.0], f"lfo_l{k}retriglbl", 8.0, False, 0))
    out.append(("Source", [662.0, 28.0, 60.0, 12.0], "mod_hsrc", 8.0, False, 0))
    out.append(("Target", [758.0, 28.0, 60.0, 12.0], "mod_htgt", 8.0, False, 0))
    out.append(("Depth", [860.0, 28.0, 60.0, 12.0], "mod_hdepth", 8.0, False, 0))
    for s in range(1, 5):
        y = 44.0 + (s - 1) * 27.0
        out.append((str(s), [644.0, y + 2, 14.0, 14.0], f"mod_n{s}", 8.0, False, 1))
        out.append(("→", [744.0, y + 2, 14.0, 14.0], f"mod_arrow{s}", 9.0, False, 1))
    out.append(("Slots 1-2: LFO 1 → Write Pitch, LFO 2 → Read Pitch (depth 0 at start).",
                [644.0, 152.0, 316.0, 13.0], "mod_note", 8.0, False, 0))
    out.append(("DRIVE", [644.0, 27.0, 36.0, 11.0], "tone_tdrive", 8.0, True, 0))
    out.append(("Drive", [644.0, 41.0, 36.0, 11.0], "tone_ldrive", 8.0, False, 1))
    out.append(("›", [682.0, 60.0, 10.0, 14.0], "tone_arrow1", 9.0, False, 1))
    out.append(("BAND", [694.0, 27.0, 180.0, 11.0], "tone_tband", 8.0, True, 0))
    for k, t in enumerate(("Center", "Width", "Res", "FM", "Spread")):
        out.append((t, [694.0 + 36.0 * k, 41.0, 36.0, 11.0], f"tone_lband{k}", 8.0, False, 1))
    out.append(("›", [644.0, 122.0, 10.0, 14.0], "tone_arrow2", 9.0, False, 1))
    out.append(("RESONATOR", [656.0, 92.0, 108.0, 11.0], "tone_tres", 8.0, True, 0))
    for k, t in enumerate(("Freq", "Fdbk", "Mix")):
        out.append((t, [656.0 + 36.0 * k, 106.0, 36.0, 11.0], f"tone_lres{k}", 8.0, False, 1))
    out.append(("›", [835.0, 122.0, 10.0, 14.0], "tone_arrow3", 9.0, False, 1))
    out.append(("OUT", [847.0, 92.0, 50.0, 11.0], "tone_tout", 8.0, True, 0))
    out.append(("Gate", [644.0, 28.0, 118.0, 12.0], "out_lgate", 8.0, False, 0))
    out.append(("Resync (bars)", [644.0, 61.0, 118.0, 12.0], "out_lresync", 8.0, False, 0))
    for k, t in enumerate(("Transp", "Width", "Output")):
        out.append((t, [772.0 + 46.0 * k, 28.0, 44.0, 12.0], f"out_l{k}", 9.0, False, 1))
    out.append(("Aliasing v0.2 \u00b7 after D. Pank", [772.0, 146.0, 160.0, 13.0], "out_info", 8.0, False, 0))
    return out


# divider lines (live.line): (rect, varname)
LINES = [([8.0, 82.0, 292.0, 5.0], "w_divider"),
         ([644.0, 38.0, 36.0, 3.0], "tone_udrive"), ([694.0, 38.0, 245.0, 3.0], "tone_uband"),
         ([656.0, 103.0, 108.0, 3.0], "tone_ures"), ([847.0, 103.0, 50.0, 3.0], "tone_uout")]


def build(template: dict) -> dict:
    pat = template["patcher"]
    plugout = next(b["box"] for b in pat["boxes"] if b["box"].get("text") == "plugout~")
    p = Patch()
    p.boxes.append({"box": {**plugout, "id": "obj-plugout", "patching_rect": [40.0, 980.0, 120.0, 22.0]}})

    def hide_rule(box: dict) -> dict:
        vis = visible_at_load(str(box.get("varname", "")))
        if vis is False:
            box["hidden"] = 1
        return box

    # ---- core --------------------------------------------------------------------------------------
    gen = p.obj("gen~ @gen aliasing @atab ---atab @aheads ---aheads", 40.0, 920.0, 4, ["signal", "signal"], w=330.0)
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

    # ---- display, pages, storage ------------------------------------------------------------------
    disp = p.add({"maxclass": "v8ui", "filename": "aliasing_display.js", "embed": 0, "numinlets": 1,
                  "numoutlets": 2, "outlettype": ["", ""], "parameter_enable": 0,
                  "patching_rect": [308.0, 6.0, 328.0, 157.0], "presentation": 1,
                  "presentation_rect": [308.0, 6.0, 328.0, 157.0], "varname": "display",
                  "textfile": {"filename": "aliasing_display.js", "flags": 0, "embed": 0, "autowatch": 1}})
    pages = p.obj("v8 aliasing_pages.js", 840.0, 560.0, 1, [], w=140.0,
                  saved_object_attributes={"embed": 0, "parameter_enable": 0},
                  textfile={"filename": "aliasing_pages.js", "flags": 0, "embed": 0, "autowatch": 1})
    thisdev = p.obj("live.thisdevice", 840.0, 480.0, 1, ["bang", "int", "int"], w=105.0)
    init = p.obj("t b b", 840.0, 520.0, 1, ["bang", "bang"])
    bufmsg = p.msg("buffers ---atab ---aheads", 960.0, 520.0)
    p.wire(thisdev, 0, init, 0)
    p.wire(init, 1, bufmsg, 0)
    p.wire(bufmsg, 0, disp, 0)
    p.wire(init, 0, pages, 0)  # after load: apply the stored page and modes

    # the display's gestures -> parameters; the stored Display Mode tab (not on the face)
    route_names = ["mode", "center", "bwidth", "bres", "bmode", "rsfreq", "rsfb", "rsmix", "rstrack"]
    route = p.obj("route " + " ".join(route_names), 960.0, 600.0, len(route_names) + 1,
                  [""] * (len(route_names) + 1), w=420.0)
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
        return 40.0 + (k % 9) * 150.0, 220.0 + (k // 9) * 30.0

    for ctl_ in controls():
        rect = ctl_.rect
        box: dict = {"maxclass": ctl_.cls, "varname": ctl_.var, "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]],
                     "presentation": 1, "presentation_rect": rect, "jspainterfile": PAINTER[ctl_.cls],
                     "fontname": FONT, "fontsize": 9.0}
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
               "rstrack": "tone_res_track"}
    for k, name in enumerate(route_names):
        if name in targets:
            p.wire(route, k, by_var[targets[name]], 0)

    # Sync button -> click~ -> gen~ in2
    ssel = p.obj("sel 1", 1100.0, 600.0, 2, ["bang", ""])
    sclick = p.obj("click~", 1100.0, 640.0, 1, ["signal"])
    p.wire(by_var["out_syncnow"], 0, ssel, 0)
    p.wire(ssel, 0, sclick, 0)
    p.wire(sclick, 0, gen, 1)

    # output meter
    for k in (0, 1):
        m = p.add(hide_rule({"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2,
                             "outlettype": ["float", "int"], "patching_rect": [700.0 + 20.0 * k, 920.0, 7.0, 128.0],
                             "presentation": 1, "presentation_rect": [941.0 + 10.0 * k, 30.0, 7.0, 128.0],
                             "varname": f"out_meter{'lr'[k]}"}))
        p.wire(gen, k, m, 0)

    # ---- labels and dividers ---------------------------------------------------------------------------
    for text, rect, var, size, bold, just in labels():
        box = {"maxclass": "live.comment", "text": text, "numinlets": 1, "numoutlets": 0,
               "patching_rect": [rect[0], rect[1] + 1200.0, rect[2], rect[3]], "presentation": 1,
               "presentation_rect": rect, "fontname": FONT_BOLD if bold else FONT, "fontsize": size,
               "textjustification": just, "varname": var}
        if rect[3] > 16:
            box["linecount"] = 2
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
    new["description"] = ("Aliasing v0.2: a 5-voice drone where a table is written and read at different speeds, "
                          "with tempo sync, LFOs, mod slots and a tone section. Inspired by 'aliasing Synth' by "
                          "Dietrich Pank (Reaktor User Library #5241, 2008).")
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
            rng = " / ".join(vo["parameter_enum"]) if len(vo["parameter_enum"]) <= 6 else (
                f"{vo['parameter_enum'][0]} ... {vo['parameter_enum'][-1]} ({len(vo['parameter_enum'])})")
            init = vo["parameter_enum"][int(vo["parameter_initial"][0])]
        else:
            rng = f"{vo.get('parameter_mmin', 0)} ... {vo.get('parameter_mmax')}"
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
