# Reaktor file parsers: ismsnoop, reaktor_tools, and a feasibility probe

Date: 2026-11-24. Follow-up to `reaktor-fundamentals-and-porting-2026-11-24.md` §6, after the
user decided they have no objection to parsing `.ens`/`.ism` files for the port (user,
2026-11-24). Evidence markers as in `CLAUDE.md`.

## Summary

Neither public tool reads ensemble **structure**. ismsnoop extracts only an instrument's name, info
text and panel background image; reaktor_tools documents the string-list framing and generates a
Multi Text macro. A read-only probe of the 2008 original shows a cleanly framed record stream
(bracketed records, length-prefixed class names, numeric module type IDs, little-endian u32 and
float32 fields), so a **local parser that dumps modules, names, values and ports is feasible**. The
manual part is mapping numeric type IDs to Reaktor module types; small test instruments saved from
Reaktor 6 (one known module each) can provide that mapping.

## ismsnoop (Penhorse/ismsnoop)

- https://github.com/Penhorse/ismsnoop — 3 stars, last commit `ea24508f` (2017-04-26), **no licence
  file** (GitHub reports none) [sourced: GitHub API].
- C++ library (CMake, submodules `rtw` and Catch). Public API: `ismsnoop_open/close`,
  `ismsnoop_get_name`, `ismsnoop_get_panel_icon_size/bytes` [sourced: `library/include/ismsnoop/ismsnoop.h`].
  Purpose stated in the README: "peek inside Reaktor instrument files and extract various kinds of
  information".
- Method: reads a version u32 at offset `0x24`, picks a handler for R6.0.0 / 6.0.3 / 6.1.1, then
  scans 128-word windows for **magic u32 patterns** that look like the background image or the info
  text [sourced: `ismsnoop.cpp`, `r611_handler.cpp`]. No record parsing, no modules, no
  connections, no values.
- Use for us: **none** beyond confirming that `.ism` files are little-endian u32-structured. Not
  vendored (no licence, wrong scope).

## reaktor_tools (Normalised/reaktor_tools)

- https://github.com/Normalised/reaktor_tools — 8 stars, last commit `0e0765c3` (2016-01-20), **no
  licence file** [sourced: GitHub API].
- `MacroFormat.txt` (203 bytes): a text-entry list is `u32 count` + strings as `u32 length` + chars;
  records are bracketed by `0x5b` `[` and `0x5d` `]`; record class IDs `KSModul`, `KInPort`,
  `KOutPort` [sourced].
- `createMultiText/createMultiText.js`: writes a Primary macro (`.mdl`) with a Multi Text module
  from a fixed header/footer and a string list [sourced]. Use for us: the framing notes only.
- Found via GitHub code search for `KSModul`; searches for "reaktor ensemble parser", "reaktor ens",
  "reaktor file format", "reaktor ism", "reaktor reverse engineering" found nothing else relevant
  [sourced: `gh search`, 2026-11-24]. The DMCA'd `monomadic/ni-file` (see the fundamentals note) is
  the only known general NI-container parser.

## Feasibility probe (read-only, original 2008 `.ens`)

Script: a throwaway Python probe in the session scratchpad (not kept). File: the original 2008
ensemble (144 346 bytes, SHA-256 `62ec413e…`).

- 326 `KSModul` records; every one is preceded by `]` `[` (byte 5 before the class name is always
  `0x5b`) [measured].
- Record head: `5b` + u32 name length (7) + `KSModul` + u32 `1` (version?) + `00 ab 21 00`
  (constant marker) + **u32 module type ID** — e.g. `6` (followed by the length-prefixed name
  "Module"), `0x1f4` = 500, `0x1f5` = 501, `9` in the first four records [measured; field meanings
  inference].
- Fields after the head are u32 counts/flags and float32 values (e.g. `0x3f000000` = 0.5); strings
  are u32-length-prefixed ASCII [measured; layout inference].
- `KInPort`/`KOutPort` records (396 / 371) presumably carry the wiring [inference].
- The saved instrument `aliasing Synth.ism` (Reaktor 6.5.2 save, 252 003 bytes) starts with `NRKT`
  and `" (R0)"`, contains the same `KSModul`/`KInPort`/`KOutPort` stream (323 / 396 / 355) inside
  NI `hsin`/`DSIN` container chunks, plus the absolute path it was saved to [measured].

## Recommendation [inference]

- Write a **local, read-only parser** as a time-boxed spike in the aliasing port session: dump the
  record tree (module type ID, name, help text, u32/float32 fields, ports) as JSON/text from the
  2008 `.ens`.
- Build a **type-ID table** from test instruments the user saves in Reaktor 6 (one known module
  each: Ramp Osc in each mode, Audio Table, Multi/2-pole filter, Peak EQ, Saturator, Knob, …) and
  from the screenshots; record each mapping with its evidence.
- Treat parser output as **[observed: parser]** and cross-check against screenshots/Properties pages
  before it drives a port decision. It complements the capture list; it does not replace renders.
- Publication: NI enforced its EULA (§3.1, reverse engineering) against a **public** parser in 2024.
  Decision (user, 2026-11-24): the parser code stays **local only** (`tools/local/`, gitignored);
  only its findings go into the repo.
