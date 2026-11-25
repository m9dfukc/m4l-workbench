#!/usr/bin/env python3
"""Structural checks of the Aliasing shell (devices/aliasing/Aliasing.amxd) without Max.

- every patch cord connects existing boxes within their inlet/outlet counts
- scripting names and parameter long names are unique; parameters have long and short names
- every "prepend <name>" wired into gen~ names a Param of gen/aliasing.genexpr, and every Param
  is driven by one
- the gen~ box has as many inlets as the GenExpr uses (in1..inN)
- presentation rects lie inside the device (968 x 169) and visible objects do not overlap in any
  page / Hz|Sync / write-shape state (rules of js/src/pages_model.ts); the theme panels (D22) lie
  behind everything (first in the box order) and every visible control lies inside one of them;
  nothing overlaps the v8ui display (it would cover the object in Live, t3)
- every painted live.* object names an existing aliasing_paint_*.js; referenced JS files exist

Usage: python3 devices/aliasing/scripts/check_shell.py [AMXD]
Exit 0 when all checks pass, 1 otherwise.
"""

from __future__ import annotations

import itertools
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICE = HERE.parent
sys.path.insert(0, str(HERE))
from bootstrap_shell import WIDTH, read_amxd  # noqa: E402

HEIGHT = 169.0
PAGES = ["lfo", "mod", "tone", "out"]
ALLOWED_OVERLAP: set[frozenset[str]] = set()
# The pages script grows the display on the Tone page (pages_model.ts displayRectFor, D31).
DISPLAY_RECT_TONE = [308.0, 6.0, 328.0, 157.0]


def rect_in(b: dict, st: dict) -> list[float]:
    if b.get("varname") == "display" and st["page"] == 2:
        return DISPLAY_RECT_TONE
    return b["presentation_rect"]


def sym_label_of(shape: int) -> str:
    """pages_model.ts symLabelOf (D6)."""
    return "curve" if shape <= 0 else "skew" if shape <= 3 else "duty" if shape == 5 else \
        "smooth" if shape == 7 else "width"


def visible(varname: str, hidden: bool, st: dict) -> bool:
    """pages_model.ts rule; objects without a rule keep their saved hidden state."""
    parts = varname.split("_") if varname else []
    if len(parts) < 2:
        return not hidden
    area, cond = parts[0], parts[1]
    if area in PAGES:
        ok = PAGES.index(area) == st["page"]
    elif area == "tbl":
        ok = st["page"] != 2
    elif area in ("w", "r"):
        ok = True
    else:
        return not hidden
    if cond in ("free", "sync") and area in ("w", "r"):
        m = st["wmode" if area == "w" else "rmode"]
        c = (m == 0) if cond == "free" else (m == 1)
    elif cond in ("hz1", "sy1"):
        c = (st["l1mode"] == 0) == (cond == "hz1")
    elif cond in ("hz2", "sy2"):
        c = (st["l2mode"] == 0) == (cond == "hz2")
    elif cond == "symlbl" and area == "w":
        c = sym_label_of(st["wshape"]) == (parts[2] if len(parts) > 2 else "")
    else:
        c = True
    return ok and c


def main(argv: list[str]) -> int:
    amxd = Path(argv[0]) if argv else DEVICE / "Aliasing.amxd"
    _, pat = read_amxd(amxd)
    boxes = {b["box"]["id"]: b["box"] for b in pat["patcher"]["boxes"]}
    lines = [l["patchline"] for l in pat["patcher"]["lines"]]
    errors: list[str] = []

    # cords
    for ln in lines:
        (s, so), (d, di) = ln["source"], ln["destination"]
        if s not in boxes or d not in boxes:
            errors.append(f"cord {s}:{so} -> {d}:{di}: missing box")
            continue
        if so >= boxes[s].get("numoutlets", 0):
            errors.append(f"cord from {boxes[s].get('text', boxes[s]['maxclass'])} outlet {so} out of range")
        if di >= boxes[d].get("numinlets", 0):
            errors.append(f"cord into {boxes[d].get('text', boxes[d]['maxclass'])} inlet {di} out of range")

    # names
    varnames = [b.get("varname") for b in boxes.values() if b.get("varname")]
    for v in sorted({v for v in varnames if varnames.count(v) > 1}):
        errors.append(f"scripting name used twice: {v}")
    longnames: list[str] = []
    for b in boxes.values():
        vo = (b.get("saved_attribute_attributes") or {}).get("valueof")
        if vo:
            if not vo.get("parameter_longname") or not vo.get("parameter_shortname"):
                errors.append(f"parameter without long/short name: {b.get('varname')}")
            longnames.append(vo.get("parameter_longname", ""))
    for n in sorted({n for n in longnames if longnames.count(n) > 1}):
        errors.append(f"parameter long name used twice: {n}")
    # live.text shows its values in Live by automation / automationon, not parameter_enum: without
    # them Live shows "val1"/"val2" (Ableton checklist "Enum labels"; testlog t4-auto, 2026-11-25)
    for b in boxes.values():
        vo = (b.get("saved_attribute_attributes") or {}).get("valueof") or {}
        if b["maxclass"] == "live.text" and b.get("parameter_enable"):
            labels = [b.get("automation", "val1"), b.get("automationon", "val2")]
            if "val1" in labels or "val2" in labels:
                errors.append(f"live.text {vo.get('parameter_longname')}: Live would show val1/val2 (set automation/automationon)")
            elif vo.get("parameter_enum") and vo["parameter_enum"] != labels:
                errors.append(f"live.text {vo.get('parameter_longname')}: automation labels {labels} differ from parameter_enum {vo['parameter_enum']}")
    # live.tab lays out (and hit-tests) num_lines rows only with multiline on; with multiline 0 it is
    # one row whatever the painter draws (m4l-boxref live.tab; t4, Write Shape grid felt like a slider)
    for b in boxes.values():
        if b["maxclass"] == "live.tab":
            rows = max(b.get("num_lines_presentation", 1), b.get("num_lines_patching", 1))
            if rows > 1 and b.get("multiline", 1) == 0:
                errors.append(f"live.tab {b.get('varname')}: {rows} rows with multiline 0 (Max lays it out as one row)")

    # gen~ Params and inlets
    src = (DEVICE / "gen" / "aliasing.genexpr").read_text()
    params = set(re.findall(r"\bParam\s+(\w+)\s*\(", src))  # several Params per line are fine
    nin = max(int(n) for n in re.findall(r"\bin(\d+)\b", src))
    gen_id = next(i for i, b in boxes.items() if str(b.get("text", "")).startswith("gen~ "))
    if boxes[gen_id]["numinlets"] != nin:
        errors.append(f"gen~ box has {boxes[gen_id]['numinlets']} inlets, the GenExpr uses in1..in{nin}")
    driven: set[str] = set()
    for ln in lines:
        (s, _), (d, di) = ln["source"], ln["destination"]
        if d == gen_id and di == 0:
            t = str(boxes[s].get("text", ""))
            if t.startswith("prepend "):
                name = t.split()[1]
                driven.add(name)
                if name not in params:
                    errors.append(f"prepend {name} -> gen~: no such Param in the GenExpr")
    for p in sorted(params - driven):
        errors.append(f"gen~ Param {p} is not driven by the shell")

    # layout
    pres = [b for b in boxes.values() if b.get("presentation") and b.get("presentation_rect")]
    for b in pres:
        x, y, w, h = b["presentation_rect"]
        if x < 0 or y < 0 or x + w > WIDTH + 0.01 or y + h > HEIGHT + 0.01:
            errors.append(f"{b.get('varname', b['maxclass'])} outside the device: {b['presentation_rect']}")
    states = [dict(page=p, wmode=wm, rmode=rm, l1mode=l1, l2mode=l2, wshape=ws)
              for p, wm, rm, l1, l2, ws in itertools.product(range(4), (0, 1), (0, 1), (0, 1), (0, 1),
                                                             (0, 1, 4, 5, 7))]
    panels = [b for b in pres if b["maxclass"] == "panel"]
    order = [b["box"]["id"] for b in pat["patcher"]["boxes"]]
    first_other = min(order.index(i) for i, b in boxes.items() if b["maxclass"] != "panel")
    for b in panels:
        if order.index(b["id"]) > first_other:
            errors.append(f"panel {b.get('varname')} is not behind the controls (box order)")

    def inside(a: list[float], o: list[float]) -> bool:
        return a[0] >= o[0] - 0.01 and a[1] >= o[1] - 0.01 and a[0] + a[2] <= o[0] + o[2] + 0.01 and \
            a[1] + a[3] <= o[1] + o[3] + 0.01
    for b in pres:
        rects = [b["presentation_rect"]] + ([DISPLAY_RECT_TONE] if b.get("varname") == "display" else [])
        if b["maxclass"] != "panel" and not all(any(inside(rc, o["presentation_rect"]) for o in panels) for rc in rects):
            errors.append(f"{b.get('varname', b['maxclass'])} lies in no panel: {b['presentation_rect']}")
    overlaps: set[tuple[str, str]] = set()
    for st in states:
        vis = [b for b in pres if b["maxclass"] != "panel"
               and visible(str(b.get("varname", "")), bool(b.get("hidden")), st)]
        for a, c in itertools.combinations(vis, 2):
            ax, ay, aw, ah = rect_in(a, st)
            cx, cy, cw, ch = rect_in(c, st)
            if ax < cx + cw - 0.5 and cx < ax + aw - 0.5 and ay < cy + ch - 0.5 and cy < ay + ah - 0.5:
                pair = tuple(sorted((str(a.get("varname", a["maxclass"])), str(c.get("varname", c["maxclass"])))))
                if frozenset(pair) not in ALLOWED_OVERLAP:
                    overlaps.add(pair)
    for a, c in sorted(overlaps):
        errors.append(f"overlap: {a} / {c}")

    # files
    for b in boxes.values():
        if b["maxclass"].startswith("live.") and b.get("parameter_enable") and b.get("presentation"):
            f = b.get("jspainterfile")
            if not f:
                errors.append(f"{b.get('varname')}: no jspainterfile")
            elif not (DEVICE / f).is_file():
                errors.append(f"{b.get('varname')}: {f} missing")
        for key in ("filename",):
            f = b.get(key)
            if f and not (DEVICE / f).is_file():
                errors.append(f"{b.get('varname', b['maxclass'])}: {f} missing")
    if not (DEVICE / "aliasing.gendsp").is_file():
        errors.append("aliasing.gendsp missing")

    n_params = len(longnames)
    print(f"check_shell: {len(boxes)} boxes, {len(lines)} cords, {n_params} parameters, {len(params)} gen~ Params, "
          f"{len(states)} page/mode/shape states, {len(panels)} panels")
    for e in errors:
        print("FAIL", e)
    print("check_shell: OK" if not errors else f"check_shell: {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
