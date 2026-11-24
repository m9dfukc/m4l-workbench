# aliasing

Max for Live instrument **inspired by** the Reaktor User Library ensemble **aliasing Synth** by
**Dietrich Pank** (2008-09-18, UL version 1.0, Reaktor 5): the same mechanism, our own DSP,
GUI and presets — not an emulation. Status: **design decided, no device files yet**
(`docs/port-decisions.md`).

## The original

An audio table is written and read at the same time but at different speeds; the "careless"
speeds produce many errors, and those errors are the sound. The finest moves in speed cause
surprising, dramatic changes. Five voices. A high-pass with FM, a low-pass with FM and a notch
behind them shape the error sound from bizarre to atmospheric (summary of the original's
description; details and sources in
`../../docs/research/notes/aliasing-synth-sources-2026-11-24.md`).

- Reaktor User Library: https://userlibrary.native-instruments.com/reaktor/item/5241
- Discussions: [scsynth.org (SuperCollider replication)](https://scsynth.org/t/replicating-aliasing-synth-a-gem-in-reaktors-user-library/9054),
  [dogsonacid](https://www.dogsonacid.com/threads/introducing-aliasing-synth-reaktor-synth-for-sick-drones-reeses.690224/)
- Local reference material (not in git): `reference/reaktor/` — see its README.

Analysis of the original: `docs/inventory.md` and `docs/signal-flow.md`. What the first research found [sourced/observed, details in the research note]: one shared
Audio Table of 1024 × 5 cells (one row per voice, values 0..1, contents stored in the file);
each voice writes its read pointer's phase at the write pointer's position and reads it back
(`2·value − 1`); pointers are Ramp oscillators ("hi" quality) or asymmetric triangles ("lo",
bidirectional); post chain Peak EQ ("Notch") → HP 4-pole + FM → drive/saturator → LP 4-pole +
FM → DC block → drive/saturator; per-voice pan; the file stores 48 kHz and a 400 Hz control
rate. Open points for capture in Reaktor are listed in the research note and in `TODO.md`.

**Licence:** the User Library terms leave copyright with the author and grant no licence to
redistribute. This device is an own implementation of the mechanism with full credit; the
`.ens`, its snapshots and its stored table contents are not used in or shipped with the device.
Telling/asking the author before a public release is planned (nice to have).

## Planned layout

```
devices/aliasing/
├── Aliasing.amxd          # unfrozen shell (Max Instrument)
├── aliasing.gendsp        # generated from gen/aliasing.genexpr (one gen~, 5-voice loop)
├── aliasing_*.js          # bundled from js/src/*.ts (v8ui display, presets)
├── presets/               # own presets as JSON
├── gen/                   # GenExpr sources
├── js/src/                # TypeScript for v8, if needed
├── docs/                  # inventory, signal flow, port decisions, deviations from the original
└── reference/
    ├── reaktor/           # local only: original .ens + screenshots
    └── renders/           # local only: reference renders from Reaktor
```
