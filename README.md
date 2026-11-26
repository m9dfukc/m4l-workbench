# m4l-workbench

A workbench for building **Max for Live** devices code-first with Claude Code — original
designs and some ports of Native Instruments **Reaktor** ensembles.

Each device keeps its sound and logic in text files that diff and review well:

- **DSP** in GenExpr (`devices/<name>/gen/*.genexpr`), compiled into the `.gendsp` that `gen~`
  loads,
- **control logic** in TypeScript, bundled to CommonJS for Max's `v8` object,
- the **`.amxd`** itself as a thin shell (I/O, `gen~`, `v8`, `live.*` parameters, layout), kept
  unfrozen in git and diffed with Ableton's `maxdiff`.

## Devices

| Device | Status | Origin |
|---|---|---|
| [`aliasing`](devices/aliasing/) | **0.3.0-beta.1** (two faces, A and B; [releases](https://github.com/m9dfukc/m4l-workbench/releases)) | original design, inspired by the Reaktor User Library ensemble *aliasing Synth* by D. Pank |

## Layout

```
devices/<name>/        one device: <Name>.amxd + generated .gendsp/.js (flat), gen/, js/src/, docs/
reference/             shared ground truth (hand-built reference device, external references)
docs/research/notes/   research reports with sources
tools/                 Python (uv) analysis tools and the offline check chain
tools/live/            optional Live automation (install, on/off, in-Live checks)
```

## Requirements

**Using a released device** (the frozen `.amxd` from
[Releases](https://github.com/m9dfukc/m4l-workbench/releases)): Ableton Live 12 with Max for Live (Suite,
or Standard with the Max for Live add-on). The devices need **Max 9**, which Live bundles since 12.2;
no separate Max install is needed. Tested Max versions are listed in each release (aliasing
0.3.0-beta.1: Live 12.4.16 with its bundled Max 9.1.5, and Max 9.2.1).

**Developing in this workbench:** a standalone **Max 9.2+** with a full licence (gen~ code export for
the offline tests), Node.js + pnpm, Python via [uv](https://docs.astral.sh/uv/). The GenExpr is
checked against Max 9.1.5 and 9.2.0 rules so that released devices run on Live's bundled Max.
Details: `docs/research/notes/m4l-toolchain-dependencies-2026-11-24.md`.

Optional, off by default: **Live automation** — Claude loads a device in Live, reads the Max
console, checks its parameters and records it silently, through
[ableton-live-test-harness](https://github.com/eladefrati/ableton-live-test-harness). Install and
on/off switch: [`tools/live/README.md`](tools/live/README.md).

## Credits

Ported devices credit and link their originals in their own README. Practice and rules here draw
on Ableton's [maxdevtools](https://github.com/Ableton/maxdevtools), mforhm's
[max-gen-helper](https://github.com/mforhm/max-gen-helper) and the projects listed in
`docs/research/notes/`.

## Licence

MIT (see `LICENSE`) for the code and docs in this repository. Third-party originals (Reaktor
ensembles, screenshots) are not part of the repository.
