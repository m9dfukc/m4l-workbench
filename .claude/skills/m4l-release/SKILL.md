---
name: m4l-release
description: Prepare and publish a release of one Max for Live device from this workbench - pre-release checks (parameters per the Ableton M4L Production Guidelines, compatibility with Live's bundled Max, licence and attribution of the ported original), the freeze done by the user, a test of the frozen device in a fresh Live set, tag and GitHub release. Use when the user wants to release, share, publish or freeze a device ("mach ein Release", "freeze das Device", "ich will das teilen", "v0.1.0 taggen").
---

# Release a device

Freezing embeds `.gendsp`, `.js` and other dependencies into the `.amxd`. Only the user can do
it (Max editor). Frozen devices never go into git; they are attached to the GitHub release and
kept locally under `dist/`.

## 1. Pre-release checks (Claude)

- Working tree clean for the device, offline checks green (`tools/check.sh <device>`), the last
  `live-test` log entry for exactly this state shows a clean console.
- **Parameters** (from the unfrozen `.amxd`, via maxdiff): every `live.*` has a unique readable
  long name and a short name, initial enable + sensible initial value, correct type, range and
  unit style, modulation mode per the Ableton M4L Production Guidelines (copy in `reference/`).
  No leftover debug objects, `print`, or `autowatch = 1`. List findings for the user.
- **Safety stage** in the DSP: kept or removed deliberately (`.claude/rules/gen.md`).
- **Freeze list:** the device project (`patcher.project.contents.code`) names every runtime file,
  painters included; Freeze embeds nothing else (`.claude/rules/max-patch.md`, aliasing t7).
- **Compatibility:** the release notes state the Max version tested. If the device needs Max
  9.2 features, say so; otherwise the user checks once with Live's bundled Max.
- **Licence and attribution** for ports: the device README credits the original's author and
  links the original; the terms of the original (e.g. Reaktor User Library) allow publishing a
  port — if unclear, **stop and ask the user** before anything public.
- Version: SemVer per device, tag `<device>-v<MAJOR.MINOR.PATCH>` (monorepo); CHANGELOG entry
  in `devices/<name>/CHANGELOG.md`.

## 2. Freeze and fresh-set test (user)

Hand over (like `live-test`):

1. Open the unfrozen `.amxd` in Live, Max editor → **Freeze**, save as
   `dist/<Device Name> <version>.amxd` (`dist/` is gitignored), close without saving the
   unfrozen one.
2. In a **fresh Live set** (ideally with the workbench folder not on any search path, e.g.
   temporarily renamed), load the frozen device from `dist/`: console clean? parameters and
   presets restore after save/reload of the set? sound as in the last test?
3. Report the console and the result.

Log the result as a `live-test` entry (label `rel-<version>`).

## 3. Publish (only on the user's explicit command naming the action)

- Commit (CHANGELOG, docs) after approval; tag `<device>-v<version>` on that commit.
- `gh release create <tag> --repo m9dfukc/m4l-workbench --title "<Device> <version>"
  --notes-file <notes> "dist/<Device Name> <version>.amxd"` — only after the user said to
  push/publish. Notes: what it is, controls, tested Max/Live versions, known deviations from
  the original, attribution.
- Update `CLAUDE.md` "Status" and `TODO.md`.
