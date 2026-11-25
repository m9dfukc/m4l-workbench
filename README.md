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
| [`aliasing`](devices/aliasing/) | port in preparation | Reaktor User Library ensemble *Aliasing Synth* |

## Layout

```
devices/<name>/        one device: <Name>.amxd + generated .gendsp/.js (flat), gen/, js/src/, docs/
reference/             shared ground truth (hand-built reference device, external references)
docs/research/notes/   research reports with sources
tools/                 Python (uv) analysis tools and the offline check chain
tools/live/            optional Live automation (install, on/off, in-Live checks)
```

## Requirements

Max 9.2+, Ableton Live 12 Suite (Max for Live), Node.js + pnpm, Python via
[uv](https://docs.astral.sh/uv/). Details: `docs/research/notes/m4l-toolchain-dependencies-2026-11-24.md`.

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
