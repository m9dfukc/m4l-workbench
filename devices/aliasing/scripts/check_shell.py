#!/usr/bin/env python3
"""Structural checks of an Aliasing shell (Aliasing.amxd = hybrid face, Aliasing B.amxd = face b) without Max.

- every patch cord connects existing boxes within their inlet/outlet counts
- scripting names and parameter long names are unique; parameters have long and short names
- every "prepend <name>" wired into gen~ names a Param of gen/aliasing.genexpr, and every Param
  is driven by one
- the gen~ box has as many inlets as the GenExpr uses (in1..inN)
- presentation rects lie inside the device (968 or 800 x 169) and visible objects do not overlap in any
  page / Hz|Sync / write-shape / strip-target state (rules of js/src/pages_model.ts, mirrored in
  bootstrap_shell.visible_in); the theme panels (D22) lie behind everything (first in the box order) and
  every visible control lies inside one of them; nothing overlaps the v8ui display (it would cover the
  object in Live, t3). Allowed: a divider (live.line) under a comment, a dial's name-row overlay
  (live.comment, ignoreclick, after its dial in the box order, h.2) on that dial, and the sample drop's
  invisible live.drop at the display's rect right behind it (D50)
- sample drop (D50-D54): one live.drop, ignoreclick, transparent, Hidden parameter, wired to the display;
  a mono buffer~ ---adrop named in the display's buffers message
- live.dial heights as Live draws them: 48 with showname 1 + shownumber 1, 36 with showname 0 +
  shownumber 1 [measured: dial probe 2026-11-25]; live.text toggles switch on mouse up (D38); a multi-row
  live.tab has multiline 1 (D44)
- every painted live.* object names an existing aliasing_paint_*.js; referenced JS files exist

Usage: python3 devices/aliasing/scripts/check_shell.py [AMXD ...]   (default: every devices/aliasing/Aliasing*.amxd)
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
from bootstrap_shell import FACE_PAGES, FACE_WIDTH, TGTS, initial_state, read_amxd, visible_in  # noqa: E402

HEIGHT = 169.0
# The pages script grows the hybrid's display on its Tone page to this height, keeping x, y and width
# (pages_model.ts displayRectFor, D31).
DISPLAY_H_TONE = 157.0


def tone_rect(b: dict) -> list[float]:
    x, y, w, _ = b["presentation_rect"]
    return [x, y, w, DISPLAY_H_TONE]


def face_of(boxes: dict) -> str:
    for b in boxes.values():
        t = str(b.get("text", ""))
        if t.startswith("v8 aliasing_pages.js"):
            parts = t.split()
            return parts[2] if len(parts) > 2 else "hybrid"
    return "hybrid"


def rect_in(b: dict, st: dict) -> list[float]:
    if b.get("varname") == "display" and st["face"] == "hybrid" and st["page"] == 2:
        return tone_rect(b)
    return b["presentation_rect"]


def visible(varname: str, hidden: bool, st: dict) -> bool:
    """pages_model.ts rule; objects without a rule keep their saved hidden state."""
    v = visible_in(varname, st)
    return (not hidden) if v is None else v


def states_of(face: str) -> list[dict]:
    out = []
    targets = range(len(TGTS)) if face == "b" else (0,)
    for pg, wm, rm, l1, l2, ws, tg in itertools.product(range(len(FACE_PAGES[face])), (0, 1), (0, 1), (0, 1), (0, 1),
                                                        range(5), targets):
        out.append({**initial_state(face), "page": pg, "wmode": wm, "rmode": rm, "l1mode": l1, "l2mode": l2,
                    "wshape": ws, "target": tg})
    return out


def main(argv: list[str]) -> int:
    files = [Path(a) for a in argv] or sorted(DEVICE.glob("Aliasing*.amxd"))
    return max(check(f) for f in files)


def check(amxd: Path) -> int:
    _, pat = read_amxd(amxd)
    boxes = {b["box"]["id"]: b["box"] for b in pat["patcher"]["boxes"]}
    face = face_of(boxes)
    width = FACE_WIDTH.get(face, 968.0)
    if abs(float(pat["patcher"].get("devicewidth", 0)) - width) > 0.01:
        errors_pre = [f"devicewidth {pat['patcher'].get('devicewidth')} != {width} (face {face})"]
    else:
        errors_pre = []
    lines = [l["patchline"] for l in pat["patcher"]["lines"]]
    errors: list[str] = list(errors_pre)

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
    # live.dial height is fixed by showname / shownumber; the painter gets that, not the saved rect
    # (dial probe 2026-11-25: 48 / 36 / 28 px at 9.5 pt whatever was saved)
    for b in boxes.values():
        if b["maxclass"] == "live.dial" and b.get("presentation_rect"):
            sn, nb = b.get("showname", 1), b.get("shownumber", 1)
            want = 48.0 if (sn and nb) else 36.0 if nb else None
            h = b["presentation_rect"][3]
            if want is not None and abs(h - want) > 0.01:
                errors.append(f"live.dial {b.get('varname')}: saved h {h}, Live draws {want} (showname {sn}, shownumber {nb})")
            if b.get("fontsize", 9.5) != 9.5:
                errors.append(f"live.dial {b.get('varname')}: fontsize {b.get('fontsize')} (the probe measured 9.5)")
        if b["maxclass"] == "live.text" and b.get("mode", 1) == 1 and b.get("parameter_enable") and b.get("outputmode", 0) != 1:
            errors.append(f"live.text {b.get('varname')}: toggle without outputmode 1 (Mouse Up, D38)")

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
        if x < 0 or y < 0 or x + w > width + 0.01 or y + h > HEIGHT + 0.01:
            errors.append(f"{b.get('varname', b['maxclass'])} outside the device: {b['presentation_rect']}")
    states = states_of(face)
    panels = [b for b in pres if b["maxclass"] == "panel" and str(b.get("varname", "")).startswith("panel_")]
    order = [b["box"]["id"] for b in pat["patcher"]["boxes"]]
    first_other = min(order.index(i) for i, b in boxes.items() if b["maxclass"] != "panel")
    for b in [b for b in pres if b["maxclass"] == "panel"]:
        if order.index(b["id"]) > first_other:
            errors.append(f"panel {b.get('varname')} is not behind the controls (box order)")

    def is_overlay_on(a: dict, c: dict) -> bool:
        """a = a dial's name-row overlay lying on dial c, after it in the box order (h.2)."""
        if a["maxclass"] != "live.comment" or not a.get("ignoreclick") or c["maxclass"] != "live.dial":
            return False
        ax, ay, aw, ah = a["presentation_rect"]
        cx, cy, cw, ch = c["presentation_rect"]
        return abs(ax - cx) < 0.01 and abs(aw - cw) < 0.01 and cy - 1.01 <= ay <= cy and ay + ah <= cy + 16 and \
            order.index(a["id"]) > order.index(c["id"])

    def is_drop_zone(a: dict, c: dict) -> bool:
        """a = the sample drop's live.drop at display c's rect, right behind it, clicks passing through (D50)."""
        return a["maxclass"] == "live.drop" and c["maxclass"] == "v8ui" and bool(a.get("ignoreclick")) and \
            a["presentation_rect"] == c["presentation_rect"] and order.index(a["id"]) == order.index(c["id"]) - 1

    def allowed(a: dict, c: dict) -> bool:
        kinds = {a["maxclass"], c["maxclass"]}
        if kinds == {"live.line", "live.comment"}:
            return True
        return is_overlay_on(a, c) or is_overlay_on(c, a) or is_drop_zone(a, c) or is_drop_zone(c, a)
    for b in boxes.values():
        if b["maxclass"] == "live.comment" and b.get("ignoreclick") and b.get("presentation"):
            if not any(is_overlay_on(b, c) for c in boxes.values() if c["maxclass"] == "live.dial"):
                errors.append(f"overlay {b.get('varname')} lies on no dial (or before it in the box order)")

    def inside(a: list[float], o: list[float]) -> bool:
        return a[0] >= o[0] - 0.01 and a[1] >= o[1] - 0.01 and a[0] + a[2] <= o[0] + o[2] + 0.01 and \
            a[1] + a[3] <= o[1] + o[3] + 0.01
    for b in pres:
        rects = [b["presentation_rect"]] + ([tone_rect(b)] if b.get("varname") == "display" and face == "hybrid" else [])
        if b["maxclass"] != "panel" and not all(any(inside(rc, o["presentation_rect"]) for o in panels) for rc in rects):
            errors.append(f"{b.get('varname', b['maxclass'])} lies in no panel: {b['presentation_rect']}")
    overlaps: set[tuple[str, str]] = set()
    seen: set[tuple] = set()
    for st in states:
        vis = [b for b in pres if b["maxclass"] != "panel"
               and visible(str(b.get("varname", "")), bool(b.get("hidden")), st)]
        sig = (tuple(b["id"] for b in vis), st["face"] == "hybrid" and st["page"] == 2)
        if sig in seen:
            continue
        seen.add(sig)
        for a, c in itertools.combinations(vis, 2):
            ax, ay, aw, ah = rect_in(a, st)
            cx, cy, cw, ch = rect_in(c, st)
            if ax < cx + cw - 0.5 and cx < ax + aw - 0.5 and ay < cy + ch - 0.5 and cy < ay + ah - 0.5:
                if allowed(a, c):
                    continue
                pair = tuple(sorted((str(a.get("varname", a["maxclass"])), str(c.get("varname", c["maxclass"])))))
                overlaps.add(pair)
    for a, c in sorted(overlaps):
        errors.append(f"overlap: {a} / {c}")

    # sample drop (D50-D54): one invisible live.drop right behind the display at its rect, Hidden parameter
    # (no re-import at load), wired to the display; a mono drop buffer named in the buffers message
    drops = [b for b in boxes.values() if b["maxclass"] == "live.drop"]
    disp_box = next((b for b in boxes.values() if b.get("varname") == "display"), None)
    if len(drops) != 1 or disp_box is None:
        errors.append(f"sample drop: {len(drops)} live.drop boxes (want 1) or no display")
    else:
        dz = drops[0]
        if not is_drop_zone(dz, disp_box):
            errors.append("sample drop: the live.drop must lie at the display's rect, right behind it, with ignoreclick 1")
        vo = (dz.get("saved_attribute_attributes") or {}).get("valueof") or {}
        if vo.get("parameter_invisible") != 2:
            errors.append("sample drop: live.drop parameter must be Hidden (parameter_invisible 2)")
        if any((dz.get(k) or [0, 0, 0, 1])[3] != 0 for k in ("bordercolor", "focusbordercolor", "textcolor")) or dz.get("legend"):
            errors.append("sample drop: live.drop must draw nothing (transparent colours, no legend)")
        if not any(ln["source"][0] == dz["id"] and str(boxes[ln["destination"][0]].get("text", "")) == "prepend droppath"
                   for ln in lines):
            errors.append("sample drop: live.drop is not wired to 'prepend droppath'")
    texts = [str(b.get("text", "")) for b in boxes.values()]
    if "buffer~ ---adrop @samps 1 1" not in texts or not any(t.startswith("buffers ") and t.split()[-1] == "---adrop" for t in texts):
        errors.append("sample drop: no mono 'buffer~ ---adrop @samps 1 1' named in the display's buffers message")

    # freeze (t7): every runtime file (gen~ @gen, v8 / v8ui scripts, jspainter painters) is listed in the device
    # project, since Freeze embeds what the project lists and missed the attribute-only painters
    from bootstrap_shell import runtime_files  # noqa: E402
    need = runtime_files(pat["patcher"]["boxes"])
    code = (((pat["patcher"].get("project") or {}).get("contents") or {}).get("code") or {})
    for f in need:
        kind = "gendsp" if f.endswith(".gendsp") else "javascript"
        if (code.get(f) or {}).get("kind") != kind:
            errors.append(f"project: runtime file {f} not listed as {kind} in project.contents.code (Freeze would miss it)")
    core = {"aliasing.gendsp", "aliasing_display.js", "aliasing_pages.js"}
    if not core <= set(need) or not any(f.startswith("aliasing_paint_") for f in need):
        errors.append(f"project: runtime files incomplete ({need})")

    # files
    for b in boxes.values():
        if b["maxclass"].startswith("live.") and b["maxclass"] != "live.drop" and b.get("parameter_enable") and \
                b.get("presentation"):
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
    print(f"check_shell: {amxd.name} (face {face}): {len(boxes)} boxes, {len(lines)} cords, {n_params} parameters, "
          f"{len(params)} gen~ Params, {len(states)} page/mode/shape/target states ({len(seen)} distinct), "
          f"{len(panels)} panels")
    for e in errors:
        print("FAIL", e)
    print("check_shell: OK" if not errors else f"check_shell: {len(errors)} problems")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
