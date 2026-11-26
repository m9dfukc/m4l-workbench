#!/usr/bin/env python3
"""Render the README images of both Aliasing faces from the canvas preview (no Max, no Live).

Placeholder images until the 1.0 release, where Live screenshots replace them (user, 2026-11-26).
For each face it builds the preview of the default page (make_preview.mjs --only), lets headless
Chrome paint it, reads each canvas back as PNG (2x pixels) and writes
<out>/aliasing-<a|b>-<dark|light>.png. Temporary files go to build/aliasing/readme-images/.

Chrome refuses to start inside Claude Code's sandbox (no socket directory); run this outside it.

Usage: python3 devices/aliasing/test/preview/readme_images.py [--out DIR] [--chrome PATH]
"""

from __future__ import annotations

import argparse
import base64
import html
import re
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEVICE = HERE.parents[1]
ROOT = DEVICE.parents[1]
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
# face letter -> (shell, preview title of its default page)
FACES = {"a": ("Aliasing.amxd", "LFO · Env page"), "b": ("Aliasing B.amxd", "LFO 1 page")}
# Appended to the preview: after the painters ran, each canvas becomes a <pre> with its PNG data URL.
HOOK = """<script>
setTimeout(() => {
  document.querySelectorAll('canvas').forEach((c) => {
    const pre = document.createElement('pre');
    pre.className = 'png'; pre.dataset.title = c.previousSibling.textContent;
    pre.textContent = c.toDataURL('image/png');
    document.body.appendChild(pre);
  });
}, 2000);
</script></body></html>"""


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", type=Path, default=DEVICE / "docs" / "img", help="output folder (default: the device's docs/img)")
    ap.add_argument("--chrome", default=CHROME, help="Chrome binary (headless)")
    args = ap.parse_args(argv)
    work = ROOT / "build" / "aliasing" / "readme-images"
    work.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    written = 0
    with tempfile.TemporaryDirectory() as profile:
        for face, (shell, title) in FACES.items():
            page = work / f"{face}.html"
            subprocess.run(["node", str(HERE / "make_preview.mjs"), str(page), str(DEVICE / shell), "--only", title],
                           check=True)
            page.write_text(page.read_text(encoding="utf-8").replace("</body></html>", HOOK), encoding="utf-8")
            dom = subprocess.run([args.chrome, "--headless=new", "--disable-gpu", "--no-first-run",
                                  f"--user-data-dir={profile}", "--virtual-time-budget=10000", "--dump-dom",
                                  page.as_uri()], check=True, capture_output=True, text=True).stdout
            found = re.findall(r'<pre class="png" data-title="([^"]*)">data:image/png;base64,([^<]*)</pre>', dom)
            for t, data in found:
                theme = "dark" if "(dark)" in html.unescape(t) else "light"
                out = args.out / f"aliasing-{face}-{theme}.png"
                out.write_bytes(base64.b64decode(data))
                print(f"wrote {out.relative_to(ROOT) if out.is_relative_to(ROOT) else out} ({html.unescape(t)})")
                written += 1
    if written != 2 * len(FACES):
        print(f"readme_images: expected {2 * len(FACES)} images, wrote {written}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
