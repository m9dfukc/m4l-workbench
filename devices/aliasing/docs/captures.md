# aliasing — capture list for Reaktor (user)

What only Reaktor can show. The parser already gives the structure, wiring, control ranges,
snapshot values and table data (`inventory.md`), so this list covers only what is still
**[open]**. Each item names the reason and where the answer goes.

**Setup:** Reaktor 6.5.2 standalone, **Full mode**, open
`reference/reaktor/Aliasing Synth 515 (original 2008).ens` **fresh** (do not load a snapshot
before C2). Save screenshots into `reference/reaktor/screenshots/` (local only) with the capture
number in the name, e.g. `C4a line view table function.png`. Breadcrumb visible, as before.

**Needed (port-decisions Q11): C4 and C6 only.** The port is "inspired by", not an emulation
(Q1), so C1 is optional and C2, C3, C5, C7, C8 are kept below only as optional background.

## C1 — Settings and instrument properties

- [ ] *Settings* (sample rate display: **Host or Fixed?**, value) and *Settings → Control Rate*.
- [ ] Instrument "aliasing Synth" → *Properties*: every page (voices, unison min/max/spread,
      voice assign mode, reassign, MIDI channel, mono flag).

Why: the parser reads 48 kHz / 400 Hz / 5 voices from the file, but not how Reaktor 6 applies
them in the plugin. Goes to `inventory.md` §1.

## C2 — Switch positions in the saved state (no snapshot loaded)

Look at the panel right after opening and write down what each switch shows:

- [ ] write osc **Qulity** (hi / lo / =read?)  — stored value 0.667
- [ ] read **Qulity** (hi / lo)  — stored 0.5
- [ ] SaturatorFilter **on**, **−DC**; Notch **on**  — stored 1, 1, 0.5
- [ ] **view** (line / 2D), AT view switch, **activate** and write **active** (lit or not)
- [ ] Then load snapshot **"quak"** and note the same positions once more.

Why: the stored numbers don't say which input is active (buttons also store 0.5, so the field
may not even be the current value); your two readings let the parser map all 38 snapshots.
Goes to `inventory.md` §4.

## C3 — Names of six unidentified modules (hover tooltip, or *Properties* title)

- [ ] **Notch**: the small "**S**" between the Reso knob and the Peak EQ's Res input.
- [ ] **SaturatorFilter**: the two "**S**" boxes before HP4 Res and LP4 Res (probably the same).
- [ ] **size bar**: the "**S**" with the loop at the left.
- [ ] **from voice>LR**: the module between "1 ÷ Vcs" and the `+` with Lvl (expected: a
      lin → dB "Log" module).
- [ ] **read › Osc › from last Gate**: the 1-in/1-out module after the `X` whose output is unused.
- [ ] **AT view**: the 1-input module at the top (fed from the view macro's output).

Why: the "S" module shapes the filter resonance input; the rest is completeness. Goes to
`inventory.md` §2.

## C4 — Audio Tables (both: AT view › line view and › 2D view) — **done 2026-11-24**, results in `table-behaviour.md` §6

- [ ] *Properties*, all pages (Function, Table/View, any "Connect"): **X units**
      (Index / [0…1] / ms / ticks), X/Y size, Min/Max, **interpolation** (off / X / Y / XY),
      **clip or wrap** for X and Y, Samples/sec, "save/retain table data", any table
      reference/sharing between the two.
- [ ] One screenshot of the table display right after opening (row contents).

Why: decides the pointer → cell mapping and what happens to the write triangle's negative half.
Highest-impact open item. Goes to `inventory.md` §5 and `port-decisions.md`.

## C5 — Internal connections

- [ ] *Properties → Connect* (or the IC tab) of: the IC sends `>read PIC`, `>write PIC`,
      `>write fineIC`, `sw>`, the OUT reset button's send, and the write osc **reset** button.
- [ ] One test: press write osc **reset** — does read **out Pitch** jump? Press read **reset** —
      do write **In-Pitch** and **fine** jump?

Why: reproduces the "sync" gestures the snapshot names refer to ("re-activate to sync").

## C6 — Oscillator and filter properties — **oscillators done 2026-11-24** (Ramp Osc: Anti-Aliased Sync), `table-behaviour.md` §6

- [ ] **Ramp Osc** (write osc and read › Osc): *Properties* — mode (Standard / Anti-aliased /
      Hi-Res or whatever R6 shows for this R5 module).
- [ ] **Tri/Par Symm** (both): *Properties*.
- [ ] **LFO** (write osc › LFO, read › LFO): *Properties* (waveform options, if any).
- [ ] **4-Pole HP**, **4-Pole Filter**, **Peak EQ**, **1-Pole Filter**, **Saturator**, **Mixer**:
      *Properties*, one screenshot each (any mode, curve or level option).

Why: oscillator aliasing is part of the sound; filter/saturator options must be matched.

## C7 — XY panel elements

- [ ] **size bar** XY and **Button (2-mode)** XY: *Properties* (X range, Y range, step, MX/MY/MB
      output ranges).

Why: the size bar scales both pointers; its range fixes the speed mapping.

## C8 — Processing order

- [ ] *Debug Structure → Show Module Sorting* screenshots of: the instrument top level, AT view,
      line view, write osc, read › Osc.
- [ ] *Show Event Init Order* of the instrument top level and write osc.

Why: confirms that there are no hidden "Z" delays and how Merge/Value initialise on load
(the write spread vs LFO question).

## Not needed any more

Knob ranges, defaults and snapshot values, the table header size/range and stored contents,
the macro wiring, and the type-ID test instruments: the parser covers them (cross-checked
against the 25 screenshots). The only test-instrument case left is if C3 leaves a module
unnamed; then one tiny Reaktor 6 ensemble with that module, renamed "probe", is enough.
