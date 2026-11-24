# aliasing — redesign backlog from test t1 (2026-11-24)

The user's critique after the first load of v0.1 in Live (verbatim German in
`testlog/aliasing/2026-11-24.md`, t1; local only). Each item below is the user's point
[measured, user report] followed by what it touches and the questions to settle with the user
(grilling) before building. Nothing here is decided yet unless marked **decided (user)**.

## 0. Bug found in the same test

- **B1** `v8ui: missing arguments for message size` (thousands of times in Live's Log.txt):
  `v8ui` has a built-in `size` message (box size), which swallows our `size <float>`; the display
  never got Size. Fix: rename the display message (e.g. `span`) in `aliasing_display.ts` and the
  shell's `prepend`. [measured: Live Log.txt 2026-11-24 20:00–20:16]
  **Fixed [code], 2026-11-24:** handler renamed to `span`; `Aliasing.amxd` got `prepend span`
  (Size slider → v8ui), the `prepend size` → v8ui cord is gone (`bootstrap_shell.py` matches);
  `tools/js-build.mjs` now rejects handler names the box handles itself (`RESERVED`). Confirm
  in t2: no `missing arguments for message size` in Live's log, the display follows Size.
- Architecture decisions for F1, F4, F15, F16, F17, F19: `redesign-t1.md` (R1–R7).

## 1. Global / left column

| # | User point | Touches | Questions |
|---|---|---|---|
| F1 | Activate button is unnecessary | shell, gen~ gate (`activate` Param, D2 in `v0.1-core.md`) | Is the drone then always on, or only MIDI-gated? Keep a hidden/automatable "Hold"? What does a fresh device do on load (sound immediately)? Where does the phase restart (Q2) come from then — first note, Sync, transport start? |
| F2 | WRITE/READ labels too close to the Pitch dials | layout | — (spacing fix; part of the overall redesign) |
| F3 | Write/read switches (Shape tabs, Active/Smooth toggles) inelegant, text clips; the mock-up looked different | live.tab/live.text look at 9 pt in 44×15 / 44×45 | Custom-drawn controls (v8ui) instead of live.tab/live.text, or restyled live.* (font size, rects, `live.menu`)? The mock-up rendered at a different scale — check G3. |
| F4 | Optional clock sync for write and read | gen~ pitch → rate; transport/tempo input (`plugsync~`/`transport` / Live tempo) | Sync per pointer: free (Hz/pitch) vs. synced (note divisions)? Which divisions (1/1 … 1/64, dotted, triplets)? Phase-lock to the song position (restart on bar) or only rate? How does Fine work in sync mode? |

## 2. Display

| # | User point | Touches | Questions |
|---|---|---|---|
| F5 | **decided (user):** the display always runs — drop View on/off | shell (`display_on` param), JS (`display` message) | — |
| F6 | Size slider inelegant → integrate into the display | shell (`live.slider` Size), display drag | Size still needs a `live.*` parameter for automation: keep it hidden (no visible slider) and drive it from the display? Undo behaviour of drags. |
| F7 | The shown table section should stretch/shrink with Size (zoom to `Size·1024` cells) | display maths | Zoom only the x axis to the active span, with a small overview of the whole row? Animate? |
| F8 | The display should look better | display | References the user likes? Line weights, glow, grid, fonts. |
| F9 | Draw into the table with the mouse (especially with Write off, but also while writing) | display → table writes (`buffer~` poke from JS, `Buffer.poke`) | Per voice lane or all voices? Pen modes (draw, smooth, line, reset to ramp)? Undo? Writing from the low-priority thread is fine for a table edit [hypothesis]. Persist the drawn table with the set (pattr/dict/`buffer~` save)? |
| F10 | Accent colours less saturated / more monochrome | `display_model.ts` colours, dial/tab accents | Candidate palette to show (muted pink/blue, or one hue with two lightnesses). |
| F11 | Line view in separate lanes per voice, like 2D | display | Lanes stacked 5× ≈ 24 px each at 134 px height; keep an overlay option? |
| F12 | Line/2D switch inelegant | shell tab | Toggle drawn inside the display (icon) instead of a `live.tab`? |

## 3. Paged area

| # | User point | Touches | Questions |
|---|---|---|---|
| F13 | Mod/Tone/Out page switch inelegant | `live.tab` Page | Drawn tabs, or no pages (wider device / scrolling)? |
| F14 | Mod page as inelegant as the write/read rows; tab/toggle menus do not fit | Mod controls | See F3. |
| F15 | Mod page: global clock sync "with all the variants it needs" | LFOs in gen~ | Per-LFO sync (rate in note values), retrigger on note/bar, phase offset, waveform choice? |
| F16 | Mod page: freer than the original, flexible routing/mapping, defaults to write/read | gen~ mod matrix | How many sources (2 LFOs? + envelope, random, MIDI velocity/note?) and targets (pitch W/R, Size, Symmetry, Spread, Tone, pan…)? Depth per route, per-voice spread of the mod (the original's `u(V)` rate spread)? Max 9.1.5-safe GenExpr. |
| F17 | Tone missing; look at Live's **Auto Filter** for ideas | v0.2 tone section (Q9) | Which Auto Filter parts: filter types/circuits (Clean/OSR/MS2/SMP/PRD), morph filter, drive, envelope follower, LFO with sync, sidechain? Licence: ideas only, own DSP. Research note first (`research` skill → `docs/research/notes/`). |
| F18 | Out section looks unfinished, inelegant | Out page | What belongs there (Width, Output, Transpose, meter, limiter/soft clip, dry/wet?) |

## 4. Overall

- **F19** The interface should look more modern; it feels old-fashioned. Suggestion (optional):
  a JavaScript canvas-drawn UI. Facts to bring into that decision:
  - Live parameters (automation, MIDI map, Push, undo, save with the set) exist only on `live.*`
    objects in parameter mode. A custom UI therefore draws in `v8ui` (mgraphics, already used for
    the display) or `jsui`, and drives **hidden-in-presentation `live.*` parameter objects**,
    and must follow them back when Live automates them. [sourced: `.claude/rules/max-patch.md`,
    M4L Production Guidelines]
  - Options: (a) restyle `live.*` objects (cheapest, theme-aware), (b) one large `v8ui` face for
    all controls with hidden `live.*` params, (c) `jweb` (HTML canvas, Chromium) — heavy in Live,
    unclear on Push/Windows. [hypothesis; research before choosing]
  - Theme colours: `live.colors` / Max dynamic colours for a custom UI.

## Suggested order (proposal)

1. B1 fix (small, unblocks the display).
2. Grilling round on F1, F4/F15, F16, F17, F19 (architecture-level choices), then on the visual
   items with a new interactive mock-up (the t1 mock-up looked better than the real live.* objects:
   build the next mock-up from what Max can actually draw).
3. Research note: Live Auto Filter feature set (F17) and custom-UI options in M4L (F19).
4. Rebuild the face, then v0.2 tone.
