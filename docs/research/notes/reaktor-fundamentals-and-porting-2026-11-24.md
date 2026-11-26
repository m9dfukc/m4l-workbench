# Reaktor fundamentals and porting method

**Date:** 2026-11-24
**Scope:** What Reaktor is and how it processes signals; the `.ens` file format; how people have ported Reaktor patches elsewhere; a step-by-step method for porting an ensemble such as "Aliasing Synth" (User Library item 5241). The Max side (gen~, RNBO) and the Aliasing Synth analysis are covered in separate notes.

**Evidence markers**

- **[sourced]**: an NI manual, the local install, or a named external source says so (cited).
- **[inference]**: my conclusion from sourced material or a byte-level look. Not checked in Reaktor.
- **[untested]**: a proposed procedure that has not been tried yet.
- **[open]**: the user has to check this in Reaktor itself.

**Primary sources used.** The local install at `/Applications/Native Instruments/Reaktor 6/` has no PDF manuals: `Documentation/` contains only `Readme.txt` (history up to 6.4.0) and the EULAs. NI's manual PDFs were therefore downloaded from `docs.native-instruments.com/pdf-guides/` and converted to text for searching. The old `www.native-instruments.com/fileadmin/.../manuals/` URLs now 301-redirect there. Working copies sit in the session scratchpad, which is not durable. The URLs are in the source list.

---

## Executive summary

1. Reaktor began as Generator 0.96 in 1996. Reaktor 6.0 came out on 2015-09-09, and 6.5.0 (2023-04-13) added native Apple Silicon and VST3. The local install is **6.5.2**, a universal x86_64/arm64 binary. NI has said there is **no Reaktor 7**. NI went through insolvency proceedings in 2026 and inMusic agreed to buy it (announced 2026-05-08). Reaktor is in maintenance mode, not dead. **[sourced]**
2. Reaktor has two levels that work very differently. **Primary** has audio signals plus *events*, processed sequentially and depth-first at a global control rate (default **400 Hz**, saved with the ensemble). **Core** is a sample-clocked event graph in which parallel paths count as simultaneous. **[sourced]**
3. Signals are **32-bit float** by default: Primary wires always, Core unless set to 64-bit per cell or macro. gen~ computes in 64-bit double, so a faithful port can come out *cleaner* than the original. That matters most where the sound depends on numerical "errors", as in Aliasing Synth. **[sourced]**/**[inference]**
4. Audio Table rules that shape the sound: write positions are **rounded down**; values written outside the table's Min/Max are **clipped**; reads can be interpolated (none / X / Y / XY linear); and **wrap is on by default**. The Ramp oscillator in Standard mode accumulates phase in float, which the manual says causes "floating point accumulation errors". **[sourced]**
5. Primary oscillators "have anti-aliasing" (algorithm not documented). The Core library also has naive versions. **[sourced]**
6. The `.ens` format is **undocumented**. Reaktor 6 files wrap a `KEnsemble` object stream (the same one Reaktor 5 wrote raw) in NI's `hsin`/`DSIN` container. NI had the main reverse-engineering project (`monomadic/ni-file`) taken down by DMCA in April 2024, citing EULA §3.1, which forbids reverse engineering. **Do not build a parser.** Inventory by screenshots and the Properties panes instead. **[sourced]**
7. A read-only byte look at the two local copies gives the same **326 module records** in each. It also turns up readable author text, macro help texts and about 40 snapshot names, plus a header with control rate 400 and BPM 120. The 2008 copy additionally carries **48000** in the slot that is probably the sample rate. **[inference]**
8. I found no published sample-accurate Reaktor→Max (or →Pd/Faust/JUCE) port. Forum ports (Skrewell to Max/gen~ and Pd; Reaktor filters in gen~) agree on three points. **Filters and feedback loops are the hard part**, Primary filters are "closed" (built-in) while Core filters port 1:1, and literal graphical translation does not work. **[sourced]**
9. Recommended method: inventory, signal-flow document, and a rate decision for every path. Then make deterministic reference renders of the Reaktor VST3/AU in Live (48 kHz, 32-bit float, fixed MIDI and snapshot, reloaded before each take), and port module by module with per-module test renders. Judge the chaotic paths by **spectral/statistical comparison, not sample nulls**. **[untested]**

---

## 1. What Reaktor is: history, status, editions

### History

| Year | Version | Notable | Source |
|---|---|---|---|
| 1996 | Generator 0.96 | Modular PC synth; needed a proprietary sound card | Wikipedia "Reaktor" [sourced] |
| 1999 | Reaktor 2.0 (Generator/Transformator) | Win + Mac | same [sourced] |
| 2001 | 3.0 | New audio engine | same [sourced] |
| Apr 2005 | 5.0 | **Core** technology (Vadim Zavalishin, Martijn Zwartjes) | same [sourced] |
| 2010 | 5.5 | Revised UI (the module/application references used here are 5.5) | same [sourced] |
| 2015-09-09 | 6.0 | **Blocks**, Table framework, Core Scoped Buses and Bundles, unified Core Cells | Wikipedia; *Building in Core* §1.3 [sourced] |
| 2016–2020 | 6.0.3 … 6.4 | GUI Core Cell (6.0.3), "Better Blocks" (6.3), User Blocks in Racks (6.4.0) | *What Is New* 07/2020; local `Readme.txt` [sourced] |
| 2023-04-13 | 6.5.0 | Native Apple Silicon, VST3; VST2 stays Intel-only | KVR news 2023-04-18; NI community [sourced] |
| local | **6.5.2** | `CFBundleShortVersionString` = 6.5.2; universal binary (x86_64 + arm64); bundle copyright "6.5.0 (R0) … 2023"; Stand-alone, `Reaktor 6.component` (AU), `Reaktor 6.vst3` installed | `Reaktor 6.app/Contents/Info.plist`, `file …/MacOS/Reaktor 6`, `/Library/Audio/Plug-Ins/` [sourced] |

No public release notes for 6.5.1 or 6.5.2 turned up, and the bundled `Readme.txt` stops at 6.4.0. **[sourced: negative search]** The local Aliasing Synth `.ens` ends with the UTF-16 string `6.5.0.0`, which is probably the version that saved it. **[inference]**

### Status in 2026

- **Company:** NI entered preliminary administration (insolvency) on **2026-01-27**. On **2026-05-08** NI and inMusic announced that inMusic would acquire NI (Wikipedia "Native Instruments"; inMusic press release). One secondary blog says the deal closed on 2026-06-30 and that Reaktor stays with NI under inMusic, while iZotope went to Boris FX. That closing date is single-source. **[sourced, partly single-source]**
- **Development:** In late July 2026 an NI staff member said the SuperStarSaw synth was "the first product built on a new Reaktor platform update", including standalone-plugin export for builders. NI staff then said there are **no plans for Reaktor 7** (Synth Anatomy, 2026-08-03; Gearnews; NI community thread 51427). 6.5 (2023) is the last major update. **[sourced]**
- **Practical consequence:** Reaktor still runs natively on Apple Silicon. NI's specifications page lists current macOS versions, though NI pages disagree with each other on the exact list. As a reference machine it should hold for the duration of this port. No new DSP features should be expected. **[sourced]**/**[inference]**

### Editions and libraries

- **Modes** (*Getting Started* §1.2) **[sourced]**:
  - **Full** (licensed Reaktor 6 or Komplete): everything.
  - **Player** (free Reaktor Player): play and change settings, but the structure cannot be edited.
  - **Demo**: full functions, but sound stops after 30 min and saving is disabled.
  - Porting needs **Full** mode to open structures.
- **Factory Library:** NI instruments and effects plus **Blocks**, "a new modular synthesizer framework" of rack-style modules (*Getting Started* §1.3). Since 6.4, User Blocks can go into Racks (`.nksr`) (`Readme.txt` 6.4.0). **[sourced]**
- **User Library:** "thousands of REAKTOR Ensembles" shared by users on NI's site (*Getting Started* §1). User Library ensembles are open: their structure can be inspected in Full mode (Wikipedia). **[sourced]** Licensing of user uploads is a separate question: crediting or asking the author (D. Pank, per the file's info text) is **[open]** (update 2026-11-26: credit only, see `devices/aliasing/docs/port-decisions.md` Q21).
- **File types:**
  - `.ens` Ensemble: all instruments, snapshots, and the global **Sample Rate, Control Rate, BPM**.
  - `.ism` Instrument.
  - `.mdl` Macro.
  - `.rcc` Core Cell.
  - `.nksr` Rack.

  Sources: *Getting Started* "Getting to Know"; *Application Reference 5.5* p. ~20. **[sourced]**

---

## 2. Architecture

- **Hierarchy:** Ensemble → Instruments → Macros → Modules, plus Core Cells. Core Cells hold Core Macros and Core built-in modules (*Getting Started* "Instruments", "Modules and Macros", "Core Cells"). An Instrument "represent[s] the so-called Primary level" and bundles the Structure, MIDI processing, Panel and Snapshots. **[sourced]**
- **Panel vs Structure:** The Panel is the user interface (controls, displays). The Structure is the wiring. A panel control is also a structure module, and its Properties (Min/Max, step size, default, mouse resolution) define its range. **[sourced]** (*Building in Primary* ch. 2/12)
- **Snapshots:**
  - Snapshots are Reaktor's presets. Snapshot banks, plus **Morph** and **Random** functions, appear in the Snapshot side pane (*Diving Deeper* §5.6–5.7).
  - Morph blends continuous values. Binary controls (buttons, switches) do not blend, and the Morph slider has a blend time. **[sourced]**
  - A snapshot recall is a **burst of events** into the structure, so it is not an instant state swap. **[inference]**
- **Voices / polyphony** (*Building in Primary* §2.4; *Application Reference* §9.3) **[sourced]**:
  - Voices are set per Instrument or Ensemble, 1–1024; the new-ensemble default is 1. Unison has Max/Min voices and a Spread setting.
  - Assignment is *Oldest / Newest / Nearest*, plus a *Reassign* checkbox. There is also "Automatic Voice Reduction" under CPU load.
  - Modules are **Mono or Poly**. A mono output may feed a poly input, but not the other way round. Poly signals must go through a **Voice Combiner** before mono modules and outputs.
  - With 1 voice, everything is effectively mono.
- **Primary vs Core:** Primary is the module-and-event world. Core is the low-level DSP language inside Core Cells. A Core Cell's ports are audio-mode or event-mode toward Primary; since R6 there is a single Core Cell type (*Building in Core* §1.3). **[sourced]**
- **Threads:** Panel mouse events and Display-Clock events run in the **GUI thread**. Control-rate events (e.g. LFO), MIDI, OSC and host automation run in the **audio thread**. Core Cells lock between the two (*What Is New*, 6.0.3 "GUI Core Cell"). **[sourced]**

---

## 3. Primary-level semantics

### Signal types and rates

- **Audio** signals run at the sample rate. **Event** signals run at the **Control Rate, default 400 Hz** (*Building in Primary* §2.3, §14.5). **[sourced]**
  - Control Rate is chosen in Settings and "**is a setting that is saved along with your Ensemble**" (*Application Reference* §3, "Changing the Control Rate"). **[sourced]**
  - At 48 kHz and 400 Hz, one control tick is 120 samples (2.5 ms). **[inference]** Whether CR ticks are spaced evenly in samples, or line up with the host buffer, is undocumented. **[open]**
- **Mixed-rate modules:** many Math modules adopt the rate of their connections. If any port connects to an audio port, the module runs at audio rate (*Building in Primary* §2.3). **[sourced]**
- **Event → audio:** "Event outputs can connect to Audio inputs, but not vice versa" (*Building in Primary* §2.2). **[sourced]** The audio input then holds the last event value (zero-order hold), so stepped control produces zipper noise unless an **Audio Smoother** or **Event Smoother** sits in between. **[inference]** The smoother modules are sourced (§18.16.4).
- **Audio → event:**
  - **A/E** resamples at the Control Rate.
  - **A to E Trig** samples on a rising edge.
  - **A to E Perm** resamples at rate F.

  Source: *Building in Primary* §18.16.1. **[sourced]**
- **Control-rate sources:** LFO modules output "a stream of Events at the Control Rate" (*Module Reference* §9.1). The System Info module's `CR` output gives the rate. Hold and Slow Random also use the CR clock. **[sourced]**

### Event order and initialisation

- **Sequential fan-out:** on Primary, an event sent to several destinations "is forwarded to each of these destinations in turn". If the paths later merge, **two or more events arrive** at the merge point, e.g. an Add fed twice fires twice (*Building in Core* §4.2, describing Primary). Use the **Order** module to force a sequence (*Building in Primary* §5). **[sourced]**
- **Initialisation on load** (*Building in Primary* §2.5.4 and ch. 9) **[sourced]**:
  - Each module initialises once, in an order shown by *Debug Structure → Show Event Init Order*.
  - During init, Add sends a **single** event.
  - Order sends only from output 1 during init.
  - Merge forwards only the **bottommost** input and initialises its sources top to bottom.

  A port must reproduce the *post-init state*, not just the steady-state behaviour. **[inference]**
- **Audio processing order and feedback** **[sourced]**:
  - Audio modules run in a sorted order, shown by *Show Module Sorting*.
  - A feedback loop without an explicit Unit Delay gets an **automatic one-sample delay**, marked "Z" (*Building in Primary* §2.5.3, §4.2.3, §18.13.1).

### Built-in modules that matter for synths

- **Oscillators:** Reaktor's oscillators "with waveforms that have strong transients (like the Sawtooth Module) have anti-aliasing" and are therefore poor LFOs (*Module Reference* ch. 6 intro). **[sourced]** The method (BLEP, BLIT, …) is not documented. **[open]** Measure it with a spectrum analyser when it matters.
  - Pitch inputs `P` are in semitones (69 = 440 Hz). FM variants add a linear `F` (Hz) audio input. **[sourced]**
- **Ramp oscillator (Ramp Osc)**, the usual table read/write pointer, has three modes (*Module Reference* §6.36.2) **[sourced]**:
  - **Standard**: no anti-aliasing, "tempo/pitch inaccuracies due to floating point accumulation errors".
  - **Anti-Aliased Sync**.
  - **Hi-Res**: "internal resolution is set to 48 bits".
- **Filters** (*Building in Primary* §18.12; *Module Reference* §10) **[sourced]**:
  - Basic 1-, 2- and 4-pole filters, each with **FM variants** whose cutoff can be modulated at audio rate. The non-FM versions take cutoff as an event-rate `P`.
  - Modelled filters: Pro-52, Ladder, Ladder FM. Also Modal Bank, EQs, Differentiator/Integrator.
  - For Multi 2-Pole: `P` range is typically 20–120 semitones (≈26 Hz–8.4 kHz) with `P=0` ≈ 8 Hz. `Res` runs 0–1, with self-oscillation at 1 and **Q ≅ 1/(2 − 2·Res)**. "Very large amplitudes" appear as Res approaches 1.
  - Topology and saturation are undocumented. **[open]**
- **Audio Table** (*Module Reference* §12.17; *Application Reference* §11.2) **[sourced]**:
  - 1-D or 2-D table. Ports: `RX/RY` read position, `WX/WY` write position, `In`, `W` (write while W > 0), and display ports `XO/XR/YO/YR`. Outputs: `Out`, plus `DX/DY` (table size).
  - **Write position is rounded down** to a cell: "0.6 … happens to the table cell at X position 0".
  - The table has **Min/Max**, and incoming values outside that range **are clipped** on write.
  - **Clip / Wrap XY** controls out-of-range positions. Reads can be **interpolated** (None, X, Y or XY linear); with Wrap, interpolation runs from the last cell to the first.
  - **Units** for X/Y (Index, [0…1], milliseconds via the Samples/Sec field, …) also change how the `RX/WX` values are *interpreted*.
  - Wrap is the default for Event Table and Audio Table (*Building in Primary* §14.8).
  - The Audio Table is **not** part of the newer Table Framework (§18.14.4).
  - The `In` port takes a "Monophonic Audio signal", so writes are mono (§12.17.1). How poly reads behave is **[open]**.
- **Event Table:** same model at event rate. When `RX` and `R` arrive together it applies them in the correct order (*Building in Primary* §5). **[sourced]**

---

## 4. Core-level semantics

All from *REAKTOR 6 Building in Core* (2015-11) unless noted. **[sourced]**

- **Everything is an event.** An audio signal is just "events regularly sent at the sampling rate" (§4.1).
  - Audio-mode Core Cell inputs emit at the sample rate.
  - Audio-mode outputs expose the value of the most recent event.
  - Event outputs pass events to Primary, top-to-bottom when they are simultaneous.
  - `Allow Audio Events` (off by default) blocks audio-rate event streams into Primary.
- **Processing order (§4.2):** parallel paths from one event are **simultaneous**: one event in gives one event out at a merge, unlike Primary. Modules on a directed path run upstream first; with no path between them, the order is undefined. Memory (OBC) accesses from unordered modules are "serial and unordered".
- **OBC and memory (§4.3, §4.7):**
  - Read/Write modules joined by an OBC wire share one storage cell.
  - Arrays are OBC-connected memory blocks with index modules. Out-of-range access is guarded only through the library's index macros.
  - Order of writes is guaranteed only along one OBC wire; macro boundaries do not order anything.
- **Initialisation (§4.4):**
  - All memory and output states are **zeroed**.
  - One **simultaneous init event** comes from audio inputs (always), event inputs (only if Primary sends one) and constants. Constants never fire again after that.
  - In R6, **`SR.C` sends no init event** (§1.3; R5 ensembles get adapter macros).
- **Clocks and latches (§4.5, §4.9):**
  - Bundles `SR` (C = clock, R = rate, Reset) and `CR` are scoped buses. Unconnected `SR`/`CR` inputs pick them up automatically.
  - **Core's default `CR` equals the audio rate** and "has nothing to do with the Control Rate source in the REAKTOR Primary" (import with *CR From Prim*). CR division and cross-rate smoothers exist.
  - Latches store a value without propagating it: the "non-triggering" input idiom.
- **Feedback (§4.10):** loops are resolved automatically with an implicit delay clocked by `SR.C`. The library `z^-1 fbk` macro holds the delay explicitly.
- **Numeric types (§2.x, §5.4):**
  - Scalars are **float or int**. float→int conversion **rounds to nearest**, and it is the only rounding mode.
  - Integer division rounds **toward zero**.
  - FP precision per module, macro or cell can be Default / 32 / 64 bit. Default "is 32 bit, the same as within Primary level", and "The 32 bit float is the type used by Primary audio and event connections". Precision means "at least" 32 or 64 bits.
- **Denormals and bad numbers (§5.5):**
  - The `DN Cancel` module adds a small constant. The library `z^-1 fbk` includes it, and therefore "acts as an internal excitation source for the self-oscillating filters".
  - No built-in NaN/INF killer exists.
- **Iteration:** Primary has an Iteration module for event bursts. In Core, iteration is built from routing and merge loops (§4.8). **[sourced, brief]**
- **Reaktor 5 reference:** R5's *Core Reference* (still online) describes the older SR.C/SR.R module style that pre-R6 ensembles may contain. **[sourced]**

Why this matters for gen~: gen~ runs a one-sample graph in 64-bit with no event concept. Core's "simultaneous" model maps fairly directly onto it. Primary's sequential, double-firing events and control-rate ticks do **not** map directly and must be emulated on purpose where they affect the sound (§7). **[inference]**

---

## 5. Implementation details that change the *sound* of a port

| Detail | What Reaktor does | Port consequence |
|---|---|---|
| Float precision | Primary wires 32-bit float; Core default 32-bit [sourced] | A 64-bit port loses float32 rounding noise and accumulation drift. Emulate float32 rounding only where it is audible (phase accumulators, table pointers, feedback) [inference] |
| Ramp/phase accumulation | Standard mode has "floating point accumulation errors"; Hi-Res is 48-bit [sourced] | In Aliasing Synth the read/write pointer "errors" are part of the sound (its info text: "Because of the 'careless' speeds it produces many errors"). Check the Ramp mode of each pointer [open] |
| Table write | Index rounded down; values clipped to table Min/Max [sourced] | Use `floor()`, not round, for writes. Clip to the table's Min/Max before writing [inference] |
| Table read | Interpolation None/X/Y/XY; wrap/clip; units change how RX is interpreted [sourced] | Record every table's Properties (size, units, interpolation, clip/wrap, Min/Max) [open] |
| Oscillators | Primary oscillators anti-aliased; Core library has a naive saw; LFO macros not anti-aliased [sourced] | Do not swap in naive or polyBLEP blindly. Measure the spectrum of each Reaktor oscillator at a few pitches [untested] |
| Filters | Built-in Primary filters are closed boxes; Q ≅ 1/(2−2·Res); topology and saturation undocumented [sourced]. The Core library has ZDF/TPT filters after Zavalishin's *The Art of VA Filter Design* (NI PDF) [sourced] | Fit Primary filters by measurement (impulse/sweep responses at several P/Res settings; resonance blow-up behaviour) [untested] |
| Control rate | 400 Hz default, saved per ensemble; event pitch inputs step at CR [sourced] | Stepping at 2.5 ms gives audible zipper or "grain" on fast sweeps. A port at audio rate is smoother than the original. Either emulate CR sample-and-hold or document the change [inference] |
| Event→audio | Allowed; the value holds until the next event [sourced]/[inference] | Explicit sample-and-hold in the port [inference] |
| Automatic feedback delay | One sample, at a point Reaktor chooses ("Z" marker) [sourced] | Find every "Z" (Show Module Sorting) and put the delay in the same place [open] |
| Denormal canceller | Adds a tiny DC/noise offset; excites self-oscillating filters [sourced] | A port without it may stay silent where Reaktor self-oscillates [inference] |
| Sample rate | Ensembles can store a Fixed sample rate; some factory ensembles run higher than the host [sourced] (*Getting Started* §2.2.4.1) | Aliasing is SR-dependent, so read the ensemble's SR on load [open] (see §6) |
| Voice allocation | Oldest/Newest/Nearest, Reassign, Unison Min/Max/Spread [sourced] | Copy the exact allocation policy, otherwise note-stealing artefacts differ [inference] |
| Randomness | Randomize/Slow Random etc., seeded via the Set Random module [sourced] | Renders may not be bit-repeatable. Test with two Reaktor renders first [untested] |

---

## 6. The `.ens` file format

### Documentation and tools

- **No public specification exists.** A 2018 KVR thread asking for one got no technical answers. **[sourced]**
- NI-container parsers exist for *other* NI formats:
  - `hansfbaier/nfm8-format`: FM8, describes the container as a "tagged node tree (hsin / DSIN)".
  - `31core/Krontact`: Kontakt `.nki` item tree.
  - `monomadic/ni-file`: generic NI formats in Rust. **Blocked on GitHub by an NI DMCA notice dated 2024-04-04**, which cites EULA §3.1 ("expressly forbids to reverse engineer"). **[sourced]**
- None of these is known to decode the Reaktor `KEnsemble` payload. **[sourced: negative search]**
- **EULA:** the local `EULA_Native Instruments English.rtf` §3.1 says the licensee may not "decompile … reverse engineer … the Product or parts thereof". **[sourced]**
  - Applying it to *user-made ensemble files* is a legal question this note does not answer.
  - Given NI's 2024 enforcement, the safe course is **not to write or publish a `.ens` parser**. Limit any look at the file to a read-only glance for one's own interoperability, as below. **[inference]**
- **Export as text or image:** neither manual describes a structure export, and I found none. **[sourced: negative search]**
  - Reaktor can save Macros (`.mdl`), Instruments (`.ism`) and Core Cells (`.rcc`), but these use the same binary family. **[inference]**
  - The practical route is **screenshots of every structure level plus the Properties pages, and a written parameter inventory** (§8).

### Read-only look at the two local copies

Files inspected with `xxd`/`strings`; nothing was modified:

- **A:** a Reaktor 6 re-save of the same ensemble from one of the user's Live projects (not kept in the repo; the 2008 original is the only reference), 259 201 bytes, Reaktor 6 format.
- **B:** `/Users/m9dfukc/Downloads/_Playground_/m4l/devices/aliasing/reference/reaktor/Aliasing Synth 515 (original 2008).ens`, 144 346 bytes, 2008, Reaktor 5 format.

**Container (file A only):**

- Starts with a little-endian u64 equal to the **file size** (`0x3F481` = 259 201), then `hsin`, a version u32, and a 16-byte GUID.
- Nested `DSIN` chunks follow, with one-letter type tags: `DSINv`, `DSINj`, `DSINu`, `DSINs`, `DSINh`, `DSINe/l/m/t/y` (78 each), and so on.
- There are 18 `RTKR` chunks, which reads as "RKTR" reversed; their meaning is unknown.
- A `NRKT` chunk at `0x263` has version-like u32s and the string " (R0)".
- The file ends with the UTF-16 string `6.5.0.0`.
- **[sourced: own hex dump]**; tag meanings **[inference]**.

**Payload:**

- File A has the payload at `0x296`. File B *starts* at offset 10 with the same `KEnsemble` record, without the `hsin` wrapper.
- So Reaktor 6 wraps the old Reaktor 5 object stream in the NI container. **[inference]**
- Both files contain **326 `KSModul` records**. Port records: 396 `KInPort` / 371 `KOutPort` in B against 398 / 355 in A, so the R6 re-save changed some port records. **[sourced: own count]**/**[inference]**
- There are no Core-related class names, so the ensemble is **probably Primary-only**. **[inference, weak]** Check in Reaktor. **[open]**

**Encoding:**

- Strings are u32-length-prefixed ASCII. Values are little-endian float32; for example `0x3F333333` = 0.7, and runs of `0xBF800000` = −1.0 sit near the start of B.
- Positions of module and wire coordinates are unknown. **[inference]**

**Global settings in the `KEnsemble` header:**

- Both files contain u32 **400** and float32 **120.0** a few bytes after the record name, plausibly **Control Rate = 400 Hz** and **BPM = 120**.
- File B has u32 **48000** just before the 400, plausibly a **fixed 48 kHz sample rate** in the 2008 original. File A has `0` in that slot, which might mean "Host/System".
- File A also has a u32 96000 directly after the 120.0, meaning unknown.
- These readings are **[inference]**. The application reference confirms that the ensemble stores Sample Rate, Control Rate and BPM **[sourced]**.
- **To check [open]:** load each file in the standalone and read the toolbar sample-rate display and *Settings → Control Rate*.

**Readable content (both files):**

- Title "aliasing Synth" and author "D. Pank".
- Info text: "Audiotable is read and written at the same time but in different speeds…".
- Macro help texts: "SaturatorFilter — Split filter with Saturator between the two 2-pole filter units", "Notch", "EQ filter", "KeyTrack 0/1/2", "polyphone LFO", "read Quality — on: precise reading / off: bidirection possible", "stereo spread 0/1/2", "Switch2x2", "Button (2-mode) … by mAtze".
- About 40 snapshot names ("quak", "seti filtered", "machine room", …, "flashs (re-activate to sync)").
- Old sample paths (`D:\sounds\Vokator Library\…`, Battery 2 library).
- Useful as a checklist for the inventory. **[sourced: own strings]**

**Verdict:** the strings are good for a checklist. Structure and connections cannot be recovered without real reverse engineering, which we avoid. **[inference]**

**Update 2026-11-24 (user decision):** parsing is allowed for this port; see `reaktor-file-parsers-2026-11-24.md` for the framing probe and the parser plan.

---

## 7. Porting experience in the wild, and generic pitfalls

### Documented examples

- **Skrewell (Reaktor factory ensemble) → Max/gen~ and Pd** (Cycling '74 forum thread "Problem rebuilding Reaktors Skrewell in Max/Gen"; undated, many years old) **[sourced]**:
  - The chaos comes from "the 2-pole filter"; one builder said that with Max "nothing happens".
  - Skrewell's built-in filters "cannot be cracked open", whereas TG-8H uses Core filters that port 1:1.
  - Feedback loops forced the work into gen~. In Pd it needed block size 2 plus a delay line.
  - Suggested method: compare filter output numerically against Reaktor.
- **"Collaborate on building Reaktor filters in Gen?"** (Cycling '74 gen~ forum, around 2014) **[sourced]**:
  - "Exact porting (graphically) is never the way to go"; you must "thoroughly understand the reaktor-core latching / bus / rates system".
  - "in gen~ there is no clock as such".
  - Over-complex interpolation is common in Core and not needed in gen~.
  - Zipper noise is a smoothing question, not a question of inlet type.
  - One poster measured gen~ as roughly 20 % slower than Core. ZDF ladders exist for Max (smFilterPack `sm.ladder~`).
- **"Building Blocs – Reaktor to Max/MSP"** (Cycling '74 forum) **[sourced]**:
  - Reaktor oscillators and filters take **MIDI pitch, not Hz**; volume modules take **dB, not linear gain**.
  - Reaktor's top-to-bottom inputs become left-to-right in Max; one user lost days to wrong order.
- **Euro Reakt (Reaktor Blocks) → VCV Rack:** Michael Hetrick (Unfiltered Audio) ported many of his own Euro Reakt blocks into HetrickCV. The README says "Many of these are ported from Euro Reakt for Reaktor 6". That is an author port with access to his own designs, not a structure translation. **[sourced]**
- **Theory bridge:** Zavalishin's *The Art of VA Filter Design* (NI PDF, rev. 2.1.0, 2018), by a Core co-author, covers the TPT/ZDF method behind the Core filter library. **[sourced]**
- **Reaktor as a plugin inside Max:** Max can host Reaktor through `vst~`, and the ensemble is restored by saving and reloading the plugin state (Cycling '74 thread "Open Reaktor ensemble"). This makes A/B tests inside one Max patch possible. **[sourced]**
- **Not found:** a published Reaktor→Faust, →SuperCollider or →JUCE port with a quantitative comparison. **[sourced: negative search]**

### Generic pitfalls (summary)

1. **Rate:** Primary event paths tick at CR (400 Hz) or fire only on change; audio paths run per sample. A port that runs everything at audio rate changes the modulation texture.
2. **Event semantics:** on Primary, fan-out followed by merge **fires twice**. Order module behaviour and init order all have to be emulated where the result depends on them.
3. **Voices:** allocation mode, unison, mono/poly boundaries and voice combiners.
4. **Tables:** floor on write, value clipping, interpolation and wrap modes, units, and read/write at different rates (the core of Aliasing Synth).
5. **Precision:** 32-bit float vs gen~'s 64-bit double; phase accumulator drift.
6. **Sample-rate dependence:** stored fixed SR; aliasing and the "errors" scale with SR.
7. **Closed built-in filters and oscillators:** fit them by measurement.
8. **Init state:** zeroed Core memory; Primary init events; snapshot recall bursts.
9. **Units:** pitch in semitones, dB levels, table units.

---

## 8. Recommended porting method (for an ensemble like Aliasing Synth)

**Step 0: settings snapshot [open, user in Reaktor].** Load the `.ens` in the **standalone, Full mode**. Record:

- Reaktor version.
- Sample-rate display (Host or Fixed value).
- *Settings → Control Rate*.
- BPM.
- Each instrument's Voices, Unison Min/Max/Spread, Assign mode and Reassign.

Check both copies (2008 and R6), because they may differ.

**Step 1: inventory.** For each structure level:

1. Take a screenshot at readable zoom.
2. Turn on *Debug Structure* → *Show Module Sorting* and *Show Event Init Order*, and screenshot again.
3. For every module and macro, record: type, mono/poly, and all Properties pages. That means Function (range, step, default, units, interpolation, clip/wrap, table size, Ramp mode, filter type, FM vs non-FM) and Connection.
4. For every panel control: label, Min/Max/step/default, and the value in each snapshot. A spreadsheet works: rows = controls, columns = snapshots.

Use the `strings` checklist in §6 to make sure nothing is missed. **[untested]**

**Step 2: signal-flow document.** Draw the block diagram from the screenshots. Mark every:

- event→audio crossing;
- automatic "Z" feedback delay;
- table read/write pair, with its rates;
- voice-combiner boundary.

**Step 3: rate decision per path.** For each event path, choose one:

- (a) exact emulation at CR (sample-and-hold every N = SR/CR samples);
- (b) per-sample update, an intentional improvement that must be documented;
- (c) param-rate update on change only.

Default to (a) wherever the path feeds a table pointer or pitch that shapes the aliasing. **[inference]**

**Step 4: reference renders (deterministic as far as possible).**

- **Preferred:** **Reaktor 6 VST3/AU in Ableton Live** at **48 kHz**. **[untested]**
  - One MIDI clip per test: single notes at several pitches, a chord, held notes for 10–20 s, and a velocity ramp.
  - One snapshot per render. Set Reaktor's internal SR to what the ensemble demands; if it is Fixed, note it.
  - **Reload the ensemble or snapshot before every take**, because the Audio Table keeps its history.
  - Export at **32-bit float WAV**, warping off, no master processing.
  - Render each take **twice** and null the two against each other. If they do not null, the patch is non-deterministic (randomness, table history, thread timing), and comparison must be statistical.
- **Alternative:** the standalone **File Recorder**. It records the first two outputs and can start on Note-On or clock start. It writes **16-bit** WAV/AIFF at the engine SR (*Diving Deeper* §6.2), so it is fine for listening and too coarse for nulls. **[sourced]**
- **Module tests:** copy a single macro (e.g. the SaturatorFilter) into a test ensemble with an Audio In, and run it as an *effect* in Live. Feed impulses, sine sweeps and noise at several knob settings, and record transfer functions and drive curves. **[untested]**

**Step 5: module-by-module re-implementation with unit tests.** Port the leaf modules first: oscillator, Ramp, Audio Table semantics, filters, saturator. Each gets a host-side test that compares against the per-module Reaktor renders:

- impulse/frequency response within ±0.5 dB below Nyquist/2;
- level and DC behaviour;
- for the table, exact index arithmetic.

These tolerances are proposals. **[untested]**

**Step 6: integration and A/B.** Compare with matched MIDI and parameters:

- level-matched listening;
- long-term average spectrum;
- spectrogram difference;
- aliasing-product positions (the patch depends on them);
- RMS envelopes;
- crest factor.

For chaotic or feedback paths, expect sample divergence. Judge on statistics and by ear, and log every intentional deviation (precision, rate). **[inference]**

**Step 7: document deviations**, each with an evidence marker. Typical entries: 64-bit vs 32-bit, CR emulation, filter fit error.

---

## Reaktor concept → what it means for a port → risk

| Reaktor concept | What it means for the port | Risk |
|---|---|---|
| Primary event at Control Rate (400 Hz default, per ensemble) | Emulate sample-and-hold at SR/CR where audible, or update per sample on purpose | **High** for pitch/pointer paths; low for UI |
| Primary sequential fan-out (double events at merges), Order/Merge init rules | Reproduce the order only where logic depends on it (counters, toggles, sequencers) | Medium |
| Event → audio connection (implicit hold) | Explicit hold plus optional smoother | Medium (zipper) |
| Core "simultaneous" events, latches, SR.C | Maps naturally to a per-sample graph; latches become plain variables | Low–medium |
| 32-bit float everywhere (Core 64-bit optional) | Port is cleaner; emulate float32 where "errors" are the sound | **High** for Aliasing Synth |
| Ramp Osc Standard / Anti-Aliased / Hi-Res | Match the mode; Standard implies float drift | High |
| Audio Table: floor on write, clip to Min/Max, interp None/X/Y/XY, wrap default, units | Implement exactly; inventory each table's Properties | **High** |
| Built-in anti-aliased oscillators (undocumented method) | Measure and match the spectrum | Medium |
| Built-in Primary filters (closed; Q ≅ 1/(2−2·Res)) | Fit by measurement; watch high-Res blow-up | **High** |
| Automatic one-sample feedback delay ("Z") | Put the same delay at the same point | Medium |
| DN Cancel in `z^-1 fbk` | Add a tiny excitation if self-oscillation must start by itself | Low–medium |
| Voices / unison / assign mode / voice combiner | Same allocation policy and voice count | Medium |
| Stored ensemble sample rate (Host vs Fixed) | Fix the port's SR or scale; aliasing is SR-dependent | **High**, [open] |
| Snapshots (incl. morph) | Preset table; snapshot recall as an event burst; morph optional | Low–medium |
| `.ens` format undocumented, RE forbidden by EULA | Manual inventory by screenshots; no parser | Process risk (time) |
| Non-determinism (random, table history) | Statistical A/B instead of nulls | Medium |

Max-side mapping (gen~ codebox/`history`/`data`/`peek`/`poke`, `param` vs signal, poly~/mc) belongs to the separate Max research note. **[pointer]**

---

## Open items for the user (check in Reaktor)

1. Sample-rate setting of each `.ens` on load (Host vs Fixed 48 kHz?), the Control Rate, and BPM.
2. Voices, Unison and Assign settings of the instrument.
3. Every Audio Table's Properties: size, units, Min/Max, interpolation, clip/wrap, and whether contents are stored with the ensemble.
4. The Ramp Osc mode of each read/write pointer.
5. Whether any Core Cells exist (byte look suggests none).
6. Filter module types: FM vs non-FM, 2-pole/notch/EQ variants.
7. Locations of the "Z" (automatic feedback delay) markers.
8. Whether two identical renders null (determinism).
9. Permission or credit terms for porting a User Library ensemble by D. Pank.

---

## Source list

**Local**

- `/Applications/Native Instruments/Reaktor 6/Reaktor 6.app/Contents/Info.plist`: version 6.5.2. `file …/Contents/MacOS/Reaktor 6`: universal x86_64 + arm64.
- `/Applications/Native Instruments/Reaktor 6/Documentation/Readme.txt`: version history to 6.4.0, ©2020.
- `/Applications/Native Instruments/Reaktor 6/Documentation/License Agreement/EULA_Native Instruments English.rtf`: §3.1.
- `/Applications/Native Instruments/Reaktor 6/Library/` (Primary and Core macro libraries).
- `/Library/Audio/Plug-Ins/Components/Reaktor 6.component`, `/Library/Audio/Plug-Ins/VST3/Reaktor 6.vst3`.
- a Reaktor 6 re-save of the same ensemble from one of the user's Live projects (not kept in the repo; the 2008 original is the only reference): read-only `xxd`/`strings`.
- `/Users/m9dfukc/Downloads/_Playground_/m4l/devices/aliasing/reference/reaktor/Aliasing Synth 515 (original 2008).ens`: read-only `xxd`/`strings`.

**Native Instruments manuals (primary)**

- REAKTOR 6 Building in Primary (6.3, 04/2019): https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Building_in_Primary_English_0419.pdf
- REAKTOR 6 Building in Core (2015-11): https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Building_in_Core_English_2015_11.pdf
- REAKTOR 6 Diving Deeper (2015-11): https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Diving_Deeper_English_2015_11.pdf
- REAKTOR 6 Getting Started (12/2016): https://docs.native-instruments.com/pdf-guides/REAKTOR_6_Getting_Started_English_122016.pdf
- REAKTOR 6 What Is New (6.4, 07/2020): https://docs.native-instruments.com/pdf-guides/REAKTOR_6_What_Is_New_English_072220.pdf
- REAKTOR 5.5 Module Reference (Modules and Macros): https://docs.native-instruments.com/pdf-guides/Reaktor_5_Modules_and_Macros_Reference_English.pdf
- REAKTOR 5.5 Application Reference: https://docs.native-instruments.com/pdf-guides/Reaktor_5_Application_Reference_English.pdf
- REAKTOR 5 Core Reference: https://docs.native-instruments.com/pdf-guides/Reaktor_5_Core_Reference_English.pdf
- V. Zavalishin, The Art of VA Filter Design 2.1.0 (NI): https://www.native-instruments.com/fileadmin/ni_media/downloads/pdf/VAFilterDesign_2.1.0.pdf
- Reaktor 6 specifications: https://www.native-instruments.com/en/products/komplete/synths/reaktor-6/specifications/
- Reaktor Player specifications: https://www.native-instruments.com/en/products/komplete/synths/reaktor-6-player/specifications/
- NI community, "Official update status – Reaktor (current version: 6.5.0)": https://community.native-instruments.com/discussion/56/
- NI community, Reaktor 6.5.0 beta and release threads: https://community.native-instruments.com/discussion/8851/reaktor-6-5-0-announcing-start-of-beta-phase-for-january-2023/p5
- NI community, "reaktor update" (staff on Reaktor 7): https://community.native-instruments.com/discussion/51427/reaktor-update
- Euro Reakt (User Library): https://www.native-instruments.com/reaktor-community/reaktor-user-library/entry/show/9093/

**Company and status (secondary)**

- Wikipedia, Reaktor: https://en.wikipedia.org/wiki/Reaktor
- Wikipedia, Native Instruments: https://en.wikipedia.org/wiki/Native_Instruments
- inMusic press release: https://www.inmusicbrands.com/press/inmusic-native/
- Engadget on the inMusic deal: https://www.engadget.com/2168045/inmusic-will-acquire-native-instruments-putting-it-under-the-same-umbrella-as-akai/
- Closing date and brand split (single-source blog): https://www.lukaswojcik.com/blog/en/music-production/what-happened-to-native-instruments-2026-insolvency-inmusic-brand-split/
- Synth Anatomy, "There are no plans for Reaktor 7" (2026-08-03): https://synthanatomy.com/2026/08/is-native-instruments-reaktor-7-with-vst-export-in-the-pipeline.html
- Gearnews, Reaktor 7 denial: https://www.gearnews.com/reaktor-7-native-instruments-synths/
- KVR news, Reaktor 6.5.0 with Apple Silicon and VST3: https://www.kvraudio.com/news/native-instruments-updates-kontakt-to-v7-3-0-and-reaktor-to-v6-5-0-incl-apple-silicon-and-vst3-57626

**File format**

- GitHub DMCA notice by Native Instruments (2024-04-04) against monomadic/ni-file: https://github.com/github/dmca/blob/master/2024/04/2024-04-04-native-instruments.md
- monomadic/ni-file (blocked): https://github.com/monomadic/ni-file
- hansfbaier/nfm8-format: https://github.com/hansfbaier/nfm8-format
- 31core/Krontact: https://github.com/31core/Krontact
- KVR, "Editing Reaktor ensemble files (.ens) via a generic text editor" (2018): https://www.kvraudio.com/forum/viewtopic.php?t=517375

**Porting experience**

- Cycling '74, "Problem rebuilding Reaktors Skrewell in Max/Gen": https://cycling74.com/forums/problem-rebuilding-the-reaktors-skrewell-in-maxgen
- Cycling '74, "Collaborate on building Reaktor filters in Gen?": https://cycling74.com/forums/collaborate-on-building-reaktor-filters-in-gen
- Cycling '74, "Building Blocs – Reaktor to Max/Msp": https://cycling74.com/forums/building-blocs-reaktor-to-maxmsp
- Cycling '74, "Open Reaktor ensemble": https://cycling74.com/forums/open-reaktor-ensemble
- HetrickCV (Euro Reakt → VCV Rack): https://github.com/mhetrick/hetrickcv
- Gearspace, "Reaktor versus Max": https://gearspace.com/board/music-computers/1152936-reaktor-versus-max.html
