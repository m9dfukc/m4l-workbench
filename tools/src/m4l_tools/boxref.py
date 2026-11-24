"""Find real, Max-saved examples of a Max object box (ground truth for patch JSON).

Searches the patch files that Max and Ableton ship on this machine — Max's help patches and
Max for Live devices from Live and the installed packs — for boxes of one class, e.g.
live.dial, and prints them with their source file and the Max version that saved them.

Use it before writing or editing box JSON by hand: copy the structure of a real box (keys,
saved_attribute_attributes, parameter_* fields) instead of inventing it. Nothing is copied
into the repo; the examples are read from the local installation each time.
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from collections.abc import Iterator
from pathlib import Path

DEFAULT_ROOTS = [
    Path("/Applications/Max.app/Contents/Resources/C74/help"),
    Path("/Applications/Max.app/Contents/Resources/C74/packages"),
    Path("/Applications/Ableton Live 12 Suite.app/Contents/App-Resources"),
    Path.home() / "Music/Ableton/Factory Packs",
]
PATCH_SUFFIXES = {".maxpat", ".maxhelp", ".amxd"}
_decoder = json.JSONDecoder()


def patchers_in_amxd(data: bytes) -> Iterator[dict]:
    """Yield top-level patcher dicts from an .amxd (plain or frozen container)."""
    text = data.decode("utf-8", errors="replace")
    start = 0
    while True:
        i = text.find('"patcher"', start)
        if i < 0:
            return
        brace = text.rfind("{", 0, i)
        if brace < 0:
            start = i + 1
            continue
        try:
            obj, end = _decoder.raw_decode(text, brace)
        except json.JSONDecodeError:
            start = i + 1
            continue
        if isinstance(obj, dict) and isinstance(obj.get("patcher"), dict):
            yield obj["patcher"]
        start = end


def patchers_in_file(path: Path) -> Iterator[dict]:
    try:
        data = path.read_bytes()
    except OSError:
        return
    if path.suffix == ".amxd":
        yield from patchers_in_amxd(data)
        return
    try:
        obj = json.loads(data.decode("utf-8", errors="replace"))
    except json.JSONDecodeError:
        return
    if isinstance(obj, dict) and isinstance(obj.get("patcher"), dict):
        yield obj["patcher"]


def boxes(patcher: dict, version: str) -> Iterator[tuple[dict, str]]:
    """All boxes, recursively through subpatchers, with the Max version that saved them."""
    av = patcher.get("appversion")
    if isinstance(av, dict):
        version = f"{av.get('major')}.{av.get('minor')}.{av.get('revision')}"
    for entry in patcher.get("boxes", []):
        box = entry.get("box", {}) if isinstance(entry, dict) else {}
        yield box, version
        sub = box.get("patcher")
        if isinstance(sub, dict):
            yield from boxes(sub, version)


def box_class(box: dict) -> str:
    cls = box.get("maxclass", "")
    if cls in ("newobj", "message") and isinstance(box.get("text"), str):
        return box["text"].split(" ")[0] if cls == "newobj" else cls
    return cls


def version_key(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except ValueError:
        return (0,)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("objclass", help="object class, e.g. live.dial, live.menu, gen~, poly~")
    ap.add_argument("-n", "--examples", type=int, default=1, help="number of full examples to print (default 1)")
    ap.add_argument("--root", action="append", type=Path,
                    help="search root (repeatable; default: Max help/packages, Live resources, Factory Packs)")
    ap.add_argument("--keys", action="store_true",
                    help="also list how often each box key and parameter attribute occurs")
    args = ap.parse_args(argv)

    roots = args.root or DEFAULT_ROOTS
    found: list[tuple[str, Path, dict]] = []
    files_seen = 0
    for root in roots:
        if not root.exists():
            continue
        for path in sorted(root.rglob("*")):
            if path.suffix not in PATCH_SUFFIXES or not path.is_file():
                continue
            files_seen += 1
            for patcher in patchers_in_file(path):
                for box, version in boxes(patcher, "?"):
                    if box_class(box) == args.objclass:
                        found.append((version, path, box))

    print(f"{args.objclass}: {len(found)} boxes in {len({p for _, p, _ in found})} of {files_seen} files",
          file=sys.stderr)
    if not found:
        return 1

    # Newest Max version first; prefer help files (written by Cycling '74 for exactly this object).
    found.sort(key=lambda t: (version_key(t[0]), t[1].suffix == ".maxhelp"), reverse=True)

    if args.keys:
        keys = collections.Counter(k for _, _, b in found for k in b)
        params = collections.Counter(
            k for _, _, b in found
            for k in b.get("saved_attribute_attributes", {}).get("valueof", {}))
        print("# box keys (count)")
        for k, c in keys.most_common():
            print(f"  {c:5d}  {k}")
        print("# saved_attribute_attributes.valueof (count)")
        for k, c in params.most_common():
            print(f"  {c:5d}  {k}")

    for version, path, box in found[: args.examples]:
        print(f"# source: {path}  (saved by Max {version})")
        print(json.dumps(box, indent=1, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
