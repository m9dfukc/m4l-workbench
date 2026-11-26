# aliasing

Max for Live instrument **inspired by** the Reaktor User Library ensemble **aliasing Synth** by
**Dietrich Pank** (2008-09-18, UL version 1.0, Reaktor 5): the same mechanism, our own DSP,
GUI and presets — not an emulation. Status: **0.3.0-beta.1** (2026-11-26, GitHub pre-release
"Aliasing 0.3.0-beta.1", `CHANGELOG.md`) as two faces for an A/B in Live: `Aliasing.amxd` (released as
"Aliasing A", hybrid, 918 px) and `Aliasing B.amxd` (option (b), 800 px), same DSP and parameters
(`docs/v0.3-design.md` D33–D49; earlier decisions `docs/port-decisions.md`, `docs/redesign-t1.md`,
`docs/v0.2-build.md`). One face stays for 1.0.

**Sample drop** (both faces, D50–D54): drop an audio file from Live's browser or the Finder onto the
table display and it becomes the table of all five voices — **FIT** (header pill) resamples the whole
file (up to 10 min) into the 1024 cells, **1:1** takes its first 1024 samples. The drop switches Write
State to Freeze so the sample stays; switch to Write and the write head eats it.

**Requirements:** Live 12 with Max for Live and **Max 9** (the device uses `v8`; Live bundles Max 9 since
12.2). Tested: Live 12.4.16 with its bundled Max 9.1.5 and with Max 9.2.1 (testlog 2026-11-26, t7); Max
9.0.x (Live 12.2, 12.3) untested. Max 9.2 is only needed to develop the device here.

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

## Layout

```
devices/aliasing/
├── Aliasing.amxd          # unfrozen shell (Max Instrument), hybrid face
├── Aliasing B.amxd        # unfrozen shell, option (b) face (same runtime files, D40)
├── aliasing.gendsp        # generated from gen/aliasing.genexpr (one gen~, 5-voice loop)
├── aliasing_*.js          # bundled from js/src/*.ts (v8ui display incl. sample drop, v8 pages, painters)
├── presets/               # own presets as JSON (planned, v0.4)
├── gen/                   # GenExpr sources
├── js/src/                # TypeScript (display, pages, painters in ES5) + js/test/
├── scripts/               # bootstrap_shell.py (shell generator), check_shell.py, table_sim.py
├── test/                  # host/ (gen~ export test), smoke/ (standalone Max), preview/, probe-ui/,
│                          # dial-probe/ (live.dial size probe), shapes/ (v0.3 shapes study)
├── docs/                  # inventory, signal flow, port decisions, deviations from the original
└── reference/
    ├── reaktor/           # local only: original .ens + screenshots
    └── renders/           # local only: reference renders from Reaktor
```
