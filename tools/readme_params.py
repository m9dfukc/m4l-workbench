#!/usr/bin/env python3
"""Parameter reference of a device README, generated from its unfrozen .amxd shells.

The device README (devices/<name>/README.md) holds marker blocks; this tool fills them from the
live.* parameters of every top-level .amxd in the device folder (saved_attribute_attributes.valueof)
and checks that nothing drifts:

  <!-- params: Write Pitch, Write Fine -->       one table: long name, range, default, description
  ...generated...                                 (the description is Live's Info View text,
  <!-- /params -->                                parameter_info, without decision IDs like "(D6)")

  <!-- params-matrix -->                          summary of all "<Source> > <Target>" parameters
  ...generated...                                 (a mod matrix: one parameter per pair)
  <!-- /params-matrix -->

  <!-- params-hidden: Aliasing.amxd = A -->       every parameter Live does not automate
  ...generated...                                 (parameter_invisible 1 = stored only, 2 = hidden);
  <!-- /params-hidden -->                         optional "file = label" pairs name the shells

Errors (exit 1): a name in a block that no shell has; an automatable parameter in no block (or in
two); a matrix parameter outside the matrix block; shells that disagree on an automatable parameter;
in check mode, a block whose text differs from what this tool generates. A README without blocks is
reported and passes (the m4l-release skill asks for the reference before a release).

Usage: python3 tools/readme_params.py [--write] DEVICE_DIR
       DEVICE_DIR   e.g. devices/aliasing
       --write      rewrite the blocks in place (default: check only, print a diff)
"""

from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import struct
import sys
from pathlib import Path

T_FLOAT, T_INT, T_ENUM, T_BLOB, T_FILE = 0, 1, 2, 3, 4
UNIT = {2: "ms", 3: "Hz", 4: "dB", 5: "%", 7: "st"}  # parameter_unitstyle (m4l-ref/parameters.maxref.xml)
ENUM_LIST_MAX = 9  # longer enums are shortened to "first, second, … last (n values)"
BLOCK = re.compile(r"(<!-- (params(?:-matrix|-hidden)?)(?::([^>]*))? -->\n)(.*?)(<!-- /\2 -->)", re.S)
DECISION = re.compile(r"\s*\(D\d+(?:\s*[,–-]\s*D?\d+)*\)")


def read_amxd(path: Path) -> dict:
    data = path.read_bytes()
    i = data.index(b"ptch")
    n = struct.unpack("<I", data[i + 4:i + 8])[0]
    return json.loads(data[i + 8:i + 8 + n].rstrip(b"\x00").decode("utf-8"))


def params_of(patcher: dict, out: dict[str, dict]) -> dict[str, dict]:
    """long name -> valueof of every parameter box, nested patchers included."""
    for b in patcher.get("boxes", []):
        box = b["box"]
        vo = (box.get("saved_attribute_attributes") or {}).get("valueof")
        if vo and "parameter_longname" in vo:
            out[vo["parameter_longname"]] = vo
        if isinstance(box.get("patcher"), dict):
            params_of(box["patcher"], out)
    return out


def automatable(vo: dict) -> bool:
    return not vo.get("parameter_invisible")


def num(x: float, signed: bool) -> str:
    s = f"{x:.3f}".rstrip("0").rstrip(".") if isinstance(x, float) and x != int(x) else str(int(x))
    s = s.replace("-", "−")
    return ("+" + s) if signed and x > 0 else s


def fmt(vo: dict, x: float, signed: bool) -> str:
    units = vo.get("parameter_units")
    if vo.get("parameter_unitstyle") == 9 and units:
        try:
            s = units % (int(round(x)) if "%d" in units else x)
        except (TypeError, ValueError):
            s = f"{num(x, False)} {units}"
        s = s.replace("-", "−")
        return ("+" + s) if signed and x > 0 and not s.startswith(("+", "×", "÷")) else s
    unit = UNIT.get(vo.get("parameter_unitstyle", 1))
    return num(x, signed) + (f" {unit}" if unit else "")


def items(vo: dict) -> list[str]:
    return [str(v) for v in vo.get("parameter_enum", [])]


def value_range(vo: dict) -> str:
    t = vo.get("parameter_type")
    if t == T_ENUM:
        e = items(vo)
        return " · ".join(e) if len(e) <= ENUM_LIST_MAX else f"{e[0]}, {e[1]}, … {e[-1]} ({len(e)} values)"
    if t == T_BLOB:
        return "data"
    if t == T_FILE:
        return "file path"
    lo, hi = vo.get("parameter_mmin", 0), vo.get("parameter_mmax", 1)
    signed = lo < 0
    return f"{fmt(vo, lo, signed)} … {fmt(vo, hi, signed)}"


def default(vo: dict) -> str:
    init = vo.get("parameter_initial")
    if not vo.get("parameter_initial_enable") or not init:
        return "–"
    x = init[0]
    if vo.get("parameter_type") == T_ENUM:
        e = items(vo)
        return e[int(x)] if 0 <= int(x) < len(e) else str(x)
    return fmt(vo, x, vo.get("parameter_mmin", 0) < 0)


def info(vo: dict) -> str:
    return DECISION.sub("", vo.get("parameter_info", "")).replace("|", "\\|").strip() or "–"


def cell(s: str) -> str:
    return s.replace("|", "\\|")


class Device:
    def __init__(self, folder: Path) -> None:
        self.shells = sorted(folder.glob("*.amxd"), key=lambda p: p.stem)
        self.params = {p.name: params_of(read_amxd(p).get("patcher", {}), {}) for p in self.shells}
        self.errors: list[str] = []
        # one valueof per automatable name; shells must agree on it
        self.auto: dict[str, dict] = {}
        for shell, ps in self.params.items():
            for name, vo in ps.items():
                if not automatable(vo):
                    continue
                if name in self.auto and self.auto[name] != vo:
                    diff = sorted(k for k in set(vo) | set(self.auto[name]) if vo.get(k) != self.auto[name].get(k))
                    self.errors.append(f"shells disagree on automatable parameter '{name}': {', '.join(diff)}")
                self.auto.setdefault(name, vo)
        for name in self.auto:
            missing = [s for s, ps in self.params.items() if name not in ps]
            if missing:
                self.errors.append(f"automatable parameter '{name}' is missing in {', '.join(missing)}")

    def table(self, names: list[str]) -> str:
        rows = ["| Parameter | Range | Default | What it does |", "|---|---|---|---|"]
        for n in names:
            vo = self.auto.get(n)
            if vo is None:
                hidden = any(n in ps for ps in self.params.values())
                self.errors.append(f"'{n}' is listed but is {'not automatable (params-hidden lists it)' if hidden else 'in no shell'}")
                continue
            if " > " in n:
                self.errors.append(f"'{n}' is a matrix parameter: it belongs in the params-matrix block")
            rows.append(f"| {cell(n)} | {cell(value_range(vo))} | {cell(default(vo))} | {info(vo)} |")
        return "\n".join(rows) + "\n"

    def matrix(self) -> str:
        names = [n for n in self.auto if " > " in n]
        if not names:
            self.errors.append("params-matrix block, but no '<Source> > <Target>' parameters")
            return ""
        srcs: list[str] = []
        tgts: list[str] = []
        for n in names:
            s, t = n.split(" > ", 1)
            if s not in srcs:
                srcs.append(s)
            if t not in tgts:
                tgts.append(t)
        missing = [f"{s} > {t}" for s in srcs for t in tgts if f"{s} > {t}" not in self.auto]
        if missing:
            self.errors.append(f"matrix incomplete, missing: {', '.join(missing)}")
        kinds = {(value_range(self.auto[n]), default(self.auto[n])) for n in names}
        if len(kinds) == 1:
            rng, dflt = kinds.pop()
            each = f"each {rng}, default {dflt}"
        else:
            each = "ranges differ: see Live's Info View"
        return (f"**{len(names)} parameters** named `<Source> > <Target>` (e.g. `{names[0]}`), {each}.\n\n"
                f"- Sources ({len(srcs)}): {', '.join(srcs)}\n- Targets ({len(tgts)}): {', '.join(tgts)}\n")

    def hidden(self, arg: str) -> str:
        labels = {Path(s).stem: Path(s).stem for s in self.params}
        for pair in (a for a in arg.split(",") if "=" in a):
            f, label = (x.strip() for x in pair.split("=", 1))
            if f not in self.params:
                self.errors.append(f"params-hidden names '{f}', which is not a shell of this device")
            labels[Path(f).stem] = label
        rows = ["| Parameter | Values | Kind | What it does |", "|---|---|---|---|"]
        names: list[str] = []
        for ps in self.params.values():
            names += [n for n, vo in ps.items() if not automatable(vo) and n not in names]
        for n in names:
            per = {s: ps[n] for s, ps in self.params.items() if n in ps}
            vos = list(per.values())
            kind = "stored with the Set" if vos[0].get("parameter_invisible") == 1 else "not stored"
            same = all(v == vos[0] for v in vos)
            if same:
                values, text = value_range(vos[0]), info(vos[0])
            else:
                values = "; ".join(f"{labels[Path(s).stem]}: {value_range(v)}" for s, v in per.items())
                texts = sorted({info(v) for v in vos})
                common = os.path.commonprefix(texts)
                cut = max(common.rfind(":"), common.rfind("."))
                text = texts[0] if len(texts) == 1 else (common[:cut].strip() + "." if cut > 0 else "differs per shell")
            only = "" if len(per) == len(self.params) else f" (only {', '.join(labels[Path(s).stem] for s in per)})"
            rows.append(f"| {cell(n)}{only} | {cell(values)} | {kind} | {text} |")
        return "\n".join(rows) + "\n"


def render(text: str, dev: Device) -> str:
    listed: dict[str, int] = {}

    def fill(m: re.Match) -> str:
        head, kind, arg, _old, tail = m.groups()
        if kind == "params":
            names = [n.strip() for n in (arg or "").split(",") if n.strip()]
            for n in names:
                listed[n] = listed.get(n, 0) + 1
            body = dev.table(names)
        elif kind == "params-matrix":
            body = dev.matrix()
            for n in dev.auto:
                if " > " in n:
                    listed[n] = listed.get(n, 0) + 1
        else:
            body = dev.hidden(arg or "")
        return head + body + tail

    out = BLOCK.sub(fill, text)
    for n in dev.auto:
        if listed.get(n, 0) == 0:
            dev.errors.append(f"automatable parameter '{n}' is in no params block")
        elif listed[n] > 1:
            dev.errors.append(f"'{n}' is listed in {listed[n]} blocks")
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("device", type=Path, help="device folder, e.g. devices/aliasing")
    ap.add_argument("--write", action="store_true", help="rewrite the README blocks in place")
    args = ap.parse_args(argv)
    readme = args.device / "README.md"
    dev = Device(args.device)
    if not dev.shells:
        print(f"readme_params: no .amxd in {args.device}", file=sys.stderr)
        return 2
    if not readme.exists() or not BLOCK.search(readme.read_text(encoding="utf-8")):
        print(f"README: no parameter blocks in {readme} (convention: CLAUDE.md 'Device README')")
        return 0
    old = readme.read_text(encoding="utf-8")
    new = render(old, dev)
    n_auto = len(dev.auto)
    for e in dev.errors:
        print(f"README: {e}")
    if new != old:
        if args.write:
            readme.write_text(new, encoding="utf-8")
            print(f"README.md parameter blocks rewritten ({n_auto} automatable parameters, {len(dev.shells)} shells)")
        else:
            sys.stdout.writelines(difflib.unified_diff(old.splitlines(True), new.splitlines(True),
                                                       "README.md", "README.md (generated)", n=1))
            print("README: parameter blocks differ from the shells (run with --write)")
            return 1
    else:
        print(f"README.md parameter blocks up to date ({n_auto} automatable parameters, {len(dev.shells)} shells)")
    return 1 if dev.errors else 0


if __name__ == "__main__":
    sys.exit(main())
