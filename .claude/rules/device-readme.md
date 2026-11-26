---
paths:
  - "devices/*/README.md"
  - "devices/*/docs/img/**"
  - "tools/readme_params.py"
---

# Device README (user, 2026-11-26)

Every device has a user-facing `devices/<name>/README.md` in this order (`devices/aliasing/README.md`
is the example):

1. **Title and images at the very top:** the device in Live's light and dark theme, a table with the
   columns Light | Dark and one row per face, files `docs/img/<name>-<face>-<light|dark>.png` (PNG,
   ≤ ~300 KB each). Before 1.0 they may be preview renders, marked as such under the table; from 1.0 on
   Live screenshots: freshly loaded, default page, about 5 s of sound with the track muted, cropped to the
   device with its title bar.
2. **What it does**, for musicians (the sound and the controls, not "inspired by …"), and a short
   quick start that starts with ear safety (limiter, monitor down).
3. **Install and requirements:** release link and asset, Live/Max versions tested.
4. **Faces**, if the device has more than one.
5. **Parameters:** every automatable parameter, grouped as in the device (each heading says where the
   group sits), in `<!-- params: Long Name, … -->` blocks; a mod matrix in `<!-- params-matrix -->`, the
   rest in `<!-- params-hidden -->`. `tools/readme_params.py` fills the blocks from the `.amxd` (step 6 of
   `tools/check.sh`), so the descriptions are the `parameter_info` texts: write those for users (Live
   shows them in its Info View), no decision IDs. Prose around the blocks explains what the table can't.
6. **Status** of the version: tested, untested, missing.
7. **Origin and credits** (ports: original author as `CLAUDE.md` names them, link, licence note) and
   the licence.
8. **For developers:** how it is built, links into `docs/`, folder layout.

Images of our own devices are committed only here, as README images in `devices/<name>/docs/img/`.
