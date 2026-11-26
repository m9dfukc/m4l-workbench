#!/usr/bin/env python3
"""Generate InfoProbe.amxd: which objects hand an info text to Live's Info View (and Max's clue window)?

aliasing t8 (2026-11-26): a `panel` in the background layer with `annotation` / `annotation_name` showed
Live's default device text ("The Aliasing Instrument") instead of its own. In 377 shipped devices (Live's
resources, Max's Max for Live package, the Factory Packs) every annotated non-parameter object is in the
foreground, none is a panel or a comment, and where such an object has a title-like name it is its
scripting name, not `annotation_name` [measured 2026-11-26]. This probe puts the candidates side by side:
nine numbered tiles, each with its own text "PROBE <n>: ..." and, where set, the title "Title <n>".

  1  panel, background layer          annotation + annotation_name   (what the device has now)
  2  panel, foreground                annotation + annotation_name
  3  panel, foreground                annotation only, scripting name "Probe Three"
  4  live.comment                     annotation + annotation_name
  5  comment                          annotation + annotation_name
  6  ubutton (invisible)              annotation + annotation_name, on a frame without a text
  7  live.comment with ignoreclick    text 7a, lying on a foreground panel with text 7b
  8  live.dial "Probe Info Dial"      annotation_name / parameter_annotation_name "Title 8" (not the long name)
  9  live.meter~                      annotation + annotation_name

Starts from Live's blank audio effect template (audio passes through untouched, the probe makes no sound).
Stdlib only; reuses Patch / read_amxd / write_amxd / valueof from devices/aliasing/scripts/bootstrap_shell.py.

Usage: python3 devices/aliasing/test/probe-info/make_infoprobe.py [--template PATH] [--out PATH] [--force]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.dont_write_bytecode = True  # no __pycache__ next to bootstrap_shell.py
sys.path.insert(0, str(HERE.parents[1] / "scripts"))
from bootstrap_shell import (  # noqa: E402
    FONT, MOD_BIPOLAR, T_FLOAT, U_FLOAT, Patch, read_amxd, valueof, write_amxd,
)

MAX_DEVICES = Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices")
TEMPLATE = MAX_DEVICES / "Max Audio Effect.amxd"
TILE_W, TILE_H, STEP_X = 116.0, 54.0, 124.0
ROWS_Y = (6.0, 88.0)
WIDTH = 8.0 + 5 * STEP_X
FILL = [0.5, 0.5, 0.5, 0.35]
FRAME = [0.5, 0.5, 0.5, 0.12]


def tile_rect(n: int) -> list[float]:
    """Presentation rect of tile n (1..10): five per row."""
    return [8.0 + ((n - 1) % 5) * STEP_X, ROWS_Y[(n - 1) // 5], TILE_W, TILE_H]


def text_of(n: int | str, what: str) -> str:
    return f"PROBE {n}: {what}"


def build(template: dict) -> dict:
    pat = template["patcher"]
    p = Patch()
    # keep the template's plugin~ / plugout~ and their cords (audio passes through untouched)
    keep = {b["box"]["id"] for b in pat["boxes"] if b["box"].get("text") in ("plugin~", "plugout~")}
    p.boxes.extend(b for b in pat["boxes"] if b["box"]["id"] in keep)
    p.lines.extend(ln for ln in pat["lines"]
                   if ln["patchline"]["source"][0] in keep and ln["patchline"]["destination"][0] in keep)

    def patching(rect: list[float]) -> list[float]:
        return [rect[0], rect[1] + 300.0, rect[2], rect[3]]

    def panel(rect: list[float], fill: list[float], background: int, **extra) -> str:
        return p.add({"maxclass": "panel", "numinlets": 1, "numoutlets": 0, "background": background, "mode": 0,
                      "border": 0, "rounded": 4, "bgcolor": fill, "bgfillcolor": fill,
                      "patching_rect": patching(rect), "presentation": 1, "presentation_rect": rect, **extra})

    def caption(n: int, text: str) -> None:
        x, y, w, h = tile_rect(n)
        rect = [x, y + h + 1.0, w, 14.0]
        p.add({"maxclass": "comment", "text": f"{n}  {text}", "numinlets": 1, "numoutlets": 0, "fontname": FONT,
               "fontsize": 9.0, "patching_rect": patching(rect), "presentation": 1, "presentation_rect": rect})

    # 1: the device's present way
    panel(tile_rect(1), FILL, 1, varname="probe_panel_bg", annotation_name="Title 1",
          annotation=text_of(1, "a panel in the background layer with annotation and annotation_name."))
    caption(1, "panel, background")
    # 2: the same panel in the foreground
    panel(tile_rect(2), FILL, 0, varname="probe_panel_fg", annotation_name="Title 2",
          annotation=text_of(2, "a panel in the foreground with annotation and annotation_name."))
    caption(2, "panel, foreground")
    # 3: title from the scripting name?
    panel(tile_rect(3), FILL, 0, varname="Probe Three",
          annotation=text_of(3, "a foreground panel with an annotation only; its scripting name is Probe Three."))
    caption(3, "panel, scripting name")
    # 4, 5: labels
    for n, cls in ((4, "live.comment"), (5, "comment")):
        rect = tile_rect(n)
        panel(rect, FRAME, 1)
        p.add({"maxclass": cls, "text": f"{cls} {cls} {cls} {cls} {cls} {cls}", "numinlets": 1, "numoutlets": 0,
               "fontname": FONT, "fontsize": 9.0, "linecount": 3, "varname": f"probe_label_{n}",
               "annotation_name": f"Title {n}",
               "annotation": text_of(n, f"a {cls} with annotation and annotation_name."),
               "patching_rect": patching(rect), "presentation": 1, "presentation_rect": rect,
               **({"presentation_linecount": 3} if cls == "comment" else {})})
        caption(n, cls)
    # 6: an invisible hover zone (ubutton box as Max saves it: m4l-boxref ubutton)
    rect = tile_rect(6)
    panel(rect, FRAME, 1)
    p.add({"maxclass": "ubutton", "handoff": "", "numinlets": 1, "numoutlets": 4,
           "outlettype": ["bang", "bang", "", "int"], "parameter_enable": 0, "varname": "probe_ubutton",
           "annotation_name": "Title 6",
           "annotation": text_of(6, "an invisible ubutton with annotation and annotation_name."),
           "patching_rect": patching(rect), "presentation": 1, "presentation_rect": rect})
    caption(6, "ubutton (invisible)")
    # 7: does a label with ignoreclick let the hover through to what lies below?
    rect = tile_rect(7)
    panel(rect, FILL, 0, varname="probe_panel_under", annotation_name="Title 7b",
          annotation=text_of("7b", "the foreground panel under a live.comment with ignoreclick."))
    p.add({"maxclass": "live.comment", "text": "live.comment ignoreclick ignoreclick ignoreclick", "numinlets": 1,
           "numoutlets": 0, "fontname": FONT, "fontsize": 9.0, "ignoreclick": 1, "varname": "probe_label_ign",
           "annotation_name": "Title 7a",
           "annotation": text_of("7a", "a live.comment with ignoreclick, lying on a panel."),
           "patching_rect": patching(rect), "presentation": 1, "presentation_rect": rect})
    caption(7, "comment, ignoreclick")
    # 8: a parameter whose info title is not its long name
    rect = tile_rect(8)
    dial_text = text_of(8, "a live.dial; its long name is Probe Info Dial, its info title Title 8.")
    vo = valueof("Probe Info Dial", "Info Dial", T_FLOAT, mmin=0.0, mmax=1.0, initial=0.5, unitstyle=U_FLOAT,
                 modmode=MOD_BIPOLAR, info=dial_text)
    vo["parameter_annotation_name"] = "Title 8"
    p.add({"maxclass": "live.dial", "numinlets": 1, "numoutlets": 2, "outlettype": ["", "float"],
           "parameter_enable": 1, "varname": "probe_dial", "annotation": dial_text, "annotation_name": "Title 8",
           "patching_rect": patching(rect), "presentation": 1,
           "presentation_rect": [rect[0] + 36.0, rect[1] + 3.0, 44.0, 48.0],
           "saved_attribute_attributes": {"valueof": vo}})
    caption(8, "live.dial, own title")
    # 9: a meter
    rect = tile_rect(9)
    panel(rect, FRAME, 1)
    p.add({"maxclass": "live.meter~", "numinlets": 1, "numoutlets": 2, "outlettype": ["float", "int"],
           "orientation": 1, "varname": "probe_meter", "annotation_name": "Title 9",
           "annotation": text_of(9, "a live.meter~ with annotation and annotation_name."),
           "patching_rect": patching(rect), "presentation": 1,
           "presentation_rect": [rect[0] + 4.0, rect[1] + 20.0, rect[2] - 8.0, 14.0]})
    caption(9, "live.meter~")

    new = dict(pat)
    new["boxes"] = p.boxes
    new["lines"] = p.lines
    new["openinpresentation"] = 1
    new["devicewidth"] = WIDTH
    new["title"] = "InfoProbe"
    new["description"] = text_of("patcher", "the patcher's description field.")
    new["dependency_cache"] = []
    return {"patcher": new}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--template", type=Path, default=TEMPLATE, help="Live's Max Audio Effect.amxd")
    ap.add_argument("--out", type=Path, default=HERE / "InfoProbe.amxd", help="output .amxd")
    ap.add_argument("--force", action="store_true", help="overwrite an existing output")
    args = ap.parse_args(argv)
    if args.out.exists() and not args.force:
        print(f"make_infoprobe: {args.out} exists; use --force to overwrite (ask first whether it is open in Max)",
              file=sys.stderr)
        return 3
    head, patch = read_amxd(args.template)
    if not head.startswith(b"ampf") or b"aaaa" not in head[:16]:
        print(f"make_infoprobe: {args.template} is not an audio effect .amxd", file=sys.stderr)
        return 2
    write_amxd(args.out, head, build(patch))
    print(f"wrote {args.out} (from {args.template.name})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
