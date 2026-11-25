# M4L GUI patterns for a dense 169-px synth face

Date: 2026-11-25 · Scope: Live 12.4.16, Max 9.2.x (development) / 9.1.5 (Live's bundled Max) ·
Device context: `devices/aliasing/` v0.3 face, 968 × 169 px
(`devices/aliasing/docs/mockup-v0.3/layout.md`, `devices/aliasing/docs/v0.3-design.md` §1, §3).
This note is the evidence base for the face redesign.

## Questions

1. Which M4L devices are widely regarded as well designed? How do their faces handle density:
   size, controls per view, dial and font sizes, labels, colour, pages and other hiding schemes?
2. Local ground truth: what sizes and attributes do the M4L devices shipped on this machine use
   for `live.dial`, `live.comment`, `live.tab`, `live.numbox`, `live.text` and `panel`?
3. How are Ableton's modulation matrices laid out (Wavetable, Meld, Drift, M4L devices), and
   which patterns reduce clutter?
4. Why can jspainter / mgraphics text look blurrier than native Live text, and what are concrete
   rules for crisp text and lines?

Related notes, not repeated here:
- `m4l-custom-ui-and-sync-2026-11-24.md`:
  - A1: restyling `live.*` objects;
  - A2: `jspainterfile` and the automation-dot API (dots `[open]` on 9.1.5);
  - A6: the 22 built-in Live devices are encrypted;
  - Results: jspainter scripts run on the legacy ES5 engine.
- Update to A6: devices in the **Factory Packs** under `~/Music/Ableton/Factory Packs/` are frozen
  containers, but they are **readable**.
  - 215 of 225 `.amxd` files there are readable.
  - CV Tools (10 devices) is encrypted.
  - Reading them stayed read-only, through `m4l-boxref`'s default roots and the scripts described
    in §2.

---

## Summary: what matters for a dense 169-px synth face

Each bullet is meant to be actionable. "Modern Ableton devices" means the 31 readable devices from
Creative Extensions, Granulator III, PitchLoop89, Inspired by Nature, MIDI Tools, Sequencers,
Performance Pack and Generators, saved by Max 8.0–9.0.9 (§2).

1. **15 px is the standard control height; ours is 12–14 px.** [measured: §2]
   - In modern Ableton devices, 618 of 653 `live.numbox`, all 117 `live.menu` and most 1-row
     `live.tab` / `live.text` are 15 px tall (tabs 15–21 px).
   - Ours: matrix cells 12 px, tabs 13–16 px, buttons 13–14 px.
   - Move every single-line control to ≥ 15 px.
2. **Labels are Ableton Sans Medium 9.5 pt in an 18-px box; ours are 7.5–8 pt in 11-px boxes.**
   [measured: §2]
   - Shipped: 327 of 381 `live.comment` use the default font, which is Ableton Sans Medium 9.5
     (`transform-defaults.json`). 376 of 381 are 18 px tall.
   - Shipped: 201 of 208 plain `comment` boxes are set explicitly to Ableton Sans Medium 9.5.
   - Ours: 69 of 77 `live.comment` labels are 7.5–8 pt, in 11-px boxes.
   - Use 9.5 pt everywhere. Ableton's densest numeric table (Polyrhythm, 150 px wide) still uses
     10 pt headers and abbreviates the words instead ("Len.", "Den.", "Vel.").
3. **Dial boxes: about 40–52 × 48 px with the name and value inside the box.** [measured: §2]
   - 111 of 193 modern `live.dial` boxes are 48 px tall.
   - 61 % use native `showname` + `shownumber` (name above the knob, value below), with no
     separate label object.
   - Secondary controls use the small appearance (≈ 47–51 × 36) or the tiny one (25 × 23).
   - Ours: 34 × 40 and 36 × 36 dials, each with a separate 11-px label row.
4. **Show far fewer controls at once.** [measured: §2.4]
   - Ableton's large instruments show about 30–60 controls at once: Granulator III 35, Poli 58,
     Bass 61, PitchLoop89 49, Emit 32.
   - They hide the rest: Granulator III has 114 hidden controls, Emit 109, Vector Grain 93.
   - Our Mod page shows about 130 controls at once, including the 108 matrix cells.
5. **Replace the full 9 × 12 grid with a destination-based matrix.** [sourced + measured: §3]
   - Wavetable and Meld list only the modulated targets plus the currently clicked parameter as
     rows. Sources are the columns.
   - Cells are about 40–48 × 19 px at 1×.
   - A cell shows a number and a short depth bar only when its value is non-zero; empty cells are
     flat neutral tiles.
   - Alternative: Granulator III's per-parameter strip, i.e. one row of source amounts for the
     selected main parameter.
6. **All 108 depth parameters can stay; only their visibility changes.** [measured: §3.4]
   - Granulator III keeps 77 hidden mod-amount `live.numbox` parameters and shows one row at a
     time.
   - So "rows on demand" needs no change in parameters, only show/hide logic.
7. **Colour the source family, not each cell.** [measured: Wavetable screenshot, §3.1]
   - Wavetable colours envelope columns cyan and LFO columns orange. Header underlines and cell
     numbers share that colour.
   - Meld uses one colour per engine (B = amber).
   - Keep the scheme (a few family hues, values in the family hue, neutral empty cells), but pick
     hues from Live's theme.
8. **Use Ableton's theme colours for surfaces.** [measured: §2.3]
   - Displays and LCD strips: `themecolor.live_lcd_bg` (64 panels).
   - Control areas: `live_surface_bg`.
   - Header chips: `live_macro_title`.
   - Labels on LCD areas: text colour `live_lcd_control_fg_zombie` (114 comments).
   - 16 of 31 modern devices use such theme references. Granulator III (310 references) and the
     Sequencers pack (143–631) use them throughout.
9. **Group by panels and spacing; avoid many bold section titles.** [measured: §2]
   - Only 4 of 381 shipped `live.comment` labels are bold.
   - Sections are made by rounded panels (radius 4–6 in modern devices) and gaps; PitchLoop89 and
     Granulator III have no bold caps titles at all.
   - Our 7 bold-caps titles plus 4 title-toggles add visual noise.
10. **Use icon buttons for modes.** [measured: §2]
    - 189 of 459 modern `live.text` are picture buttons, at 15 × 15, 17 × 17 or 19 × 19.
    - Vector Grain switches its whole side panel with a 25-px column of four 19 × 19 icon buttons.
    - Text buttons cost width; icons are theme-aware with `remapsvgcolors` (previous note A1).
11. **Width.** [measured + sourced]
    - 968 px is wider than every modern Ableton pack device measured: Poli 802, PitchLoop89 787,
      Granulator III 729, Bass 675, Emit 623.
    - The guidelines suggest a fold-out (`live.thisdevice` `setwidth`, present in 9.1.5), a tabbed
      view or an overlay. A pop-out window is "ideally avoided" and, if used, should be floating
      (`reference/m4l-production-guidelines.md` §Device Width, §Pop-out Windows).
12. **Crisp painter text: round to whole pixels and use 9.5 pt.** [sourced + code: §4]
    - Our `text()` centres at a fractional x (`x − w/2`) and puts the dial baseline at `h − 2.5`.
    - Round both x and baseline. Use 9.5 pt, as Ableton's own painters do (Color Limiter).
    - Never put `scale()` around text.
13. **Crisp painter lines: integer widths for straight lines.** [sourced: Cairo FAQ, C74 guide; code]
    - Use 1 px at a +0.5 offset, or 2 px on integers.
    - Our painters use 1.1, 1.4, 1.5, 1.8, 2.5 and 2.6 px.
    - Arcs are antialiased anyway, so their widths matter less.
14. **The HTML mock-up is not a fair reference.** [code]
    - It renders **Inter** (Google Fonts, weights 400–600), not Ableton Sans:
      `font-family: Inter, 'Ableton Sans', …` in `mockup-v0.3/Main.dc.html`.
    - The next mock-up should use Ableton Sans Medium 9.5 at 100 % zoom and be compared with Live
      at 1:1 pixels.
    - The dial geometry itself is not smaller in the painter than in the mock-up (§4.1).
15. **Set `livemode 1` on every `live.tab`.**
    - The guidelines recommend it for pixel snapping, and 30 of 45 shipped modern tabs have it.
    - All 16 of our tabs lack it. [measured + sourced]

---

## 1. Well-designed M4L devices and their faces

Method:
- **Ableton pack devices** were measured from their saved patch geometry (§2 explains how).
  Screenshots and design statements come from the web.
- **Third-party devices** come from the web only.
- Widths are `devicewidth` or, when it is 0, the extent of the visible presentation boxes.
- "Visible" and "hidden" refer to the saved state of each box; scripts may hide or show more at
  runtime.
- All image URLs below were checked to return an image, except the Attack Magazine ones.

### 1.1 Granulator III — Robert Henke with Ableton (Max 8.6.4)

- **Credits:** concept and UX by Henke; UX by Marco Tonni; user interface design by Eric Carl and
  Kostya Kazhev [sourced: https://roberthenke.com/technology/granulator3.html].
- **Face:** 729 px wide, built in three horizontal bands [measured]:
  1. **Main display**, 696 × 89 px (`panel` with `themecolor.live_lcd_bg`, `waveform~`, sample drop
     zone, zoom icons 15 × 15). Icon buttons on the left switch it between sample and envelope /
     LFO / filter views, or to "Auto". In Auto, the view follows the clicked parameter [sourced:
     Henke page].
  2. **Modulation strip**, 21 px, also `live_lcd_bg`. One row of nine LCD `live.numbox`
     (39 × 15, appearance 4) under 9.5-pt source labels: Key, Vel, Note PB, Slide, Press, Env2,
     LFO, Rand, Variation.
     - It shows the modulation of the **selected** main parameter only.
     - A small triangle (`live.text` 32 × 10) marks which parameter that is; Henke: "A little
       triangle indicates for which main parameter the modulations are shown".
     - The strip has no section title; the source labels are its only text [measured].
  3. **One row of 11 dials**, 50 × 48 each, with native name and value on a 51-px pitch. Control
     groups sit on `live_surface_bg` panels (rounded 4). On the right is a Voices / Mono / Hold
     block.
- **Counts** [measured]:
  - 35 visible controls, 114 hidden (envelope, filter, LFO and capture panels, plus 77 hidden
    mod-amount numboxes).
  - 310 theme-colour references.
  - No jspainter.
- **Reviews:** Sound On Sound describes a constant row of knobs, a top half that switches views,
  and modulation in a narrow row, and says this decluttered the display [sourced:
  https://www.soundonsound.com/techniques/ableton-live-12-granulator-iii].
- **Screenshots:** https://roberthenke.com/files_images/technology/g3/g3-interface.png. The same
  folder has `g3-main.png`, `g3-lfo.jpeg`, `g3-filter.png` and others.

### 1.2 PitchLoop89 — Robert Henke, UI by Eric Carl (Max 9.0.9)

- **Face:** 787 px wide, everything visible: 49 controls, 0 hidden [measured].
- **Layout:** two mirrored channel rows. Section labels sit above the top row and below the bottom
  row: Global, Tune, Delay, Position Mod, Filter [sourced: https://roberthenke.com/technology/pitchloop89.html].
- **Dials** [measured]:
  - 22 dials in 11 sizes, e.g. 48 × 38, 37 × 24 (tiny), 55 × 50.
  - 20 of them have `showname 0`; the names are separate `live.comment` labels set to 10 pt (29
    labels).
- **Colour:** no theme references; panels are 0.14 grey, rounded 4 [measured].
- **Screenshots:**
  - https://beta-ableton.imgix.net/media/5vgdffeq/pitchloop89-2x.png
  - https://roberthenke.com/files_images/technology/pitchloop89/pitchloop89.jpg

### 1.3 Poli and Bass — Creative Extensions (Ableton with Amazing Noises; Max 8.0)

- **Poli** [measured]:
  - 802 px wide; 58 visible controls, 12 hidden.
  - 20 dials, 40 × 48, with native name and value.
  - 25 LCD numboxes for envelope values, 41 × 13.
  - 44 comment labels in Ableton Sans Medium 9.5 (41 at 9.5, 3 at 9.4).
  - Panels rounded 6 in two shades: light 0.53 and dark 0.16. The dark ones hold the
    display-like areas.
  - 3 tabs, one `jit.pwindow` display.
- **Bass** [measured]:
  - 675 px wide; 61 visible controls.
  - Dials 41 × 48 and 41 × 37; LCD numboxes 36 × 13.
  - Labels 9.5 pt; panels 0.16, rounded 6.
- The guidelines cite Poli as the reference width for a feature-rich synth
  (`reference/m4l-production-guidelines.md` §Device Width).
- **Screenshots:**
  - https://ableton-production.imgix.net/blog/creative-extensions/poli.gif
  - https://beta-ableton.imgix.net/media/mvcmtly0/bass-2x.png

### 1.4 Color Limiter — Creative Extensions (Max 8.0)

- **Face:** 240 px, 8 visible controls [measured].
  - Dials 52 × 48.
  - One 52 × 39 "Loudness" dial is painted by **Ableton's own jspainter**, `livedial_override.js`.
    It draws a 300° arc with radius 17 and line width 2.33, and no text.
  - A `jsui` gain-reduction meter (`grmeterbg.js`, Nico Starke @ Ableton, April 2018) draws its
    scale numbers in Ableton Sans Medium **9.5** with `text_path` + `fill`.
  - Label comments are 9.5 pt [measured: embedded files of the frozen device].
- This is the only jspainter among the 215 readable pack devices [measured].
- **Screenshot:** https://beta-ableton.imgix.net/media/asbdrnui/color-limiter-2x.png

### 1.5 Inspired by Nature — Dillon Bastan (Max 8.6)

- **Vector Grain, FM, Delay and Map** share one scheme [measured], left to right:
  - a 169 × 169 square particle display (`jit.pwindow` 143 × 143), with 18-px X/Y `live.slider`s
    along two of its edges;
  - a 57-px column of 3 small dials (49 × 36, appearance 1) plus a numbox and a toggle;
  - a 25-px column of **four 19 × 19 icon buttons** (Sample, Grain, Force and Particle settings)
    that switch a **240-px side panel**;
  - an ADSR column of 4 stacked 51 × 36 dials.
- About 18 controls are visible and 79–93 are hidden in those side panels.
- Modulation uses 5 **source slots** (X, Y, Mag, Vel, Mass). Each slot is a tiny amount dial
  (25 × 23) plus a destination `live.menu` (43 × 15) [measured].
- Attack Magazine describes the side icons revealing a filter page and a physics page [sourced:
  https://www.attackmagazine.com/technique/tutorials/getting-freaky-with-live-11s-new-inspired-by-nature-devices/].
- **Tree Tone, Emit, Bouncy Notes:**
  - widths 520, 623 and 593 px; 32–36 visible controls;
  - dials 43–51 × 48;
  - Emit uses `live.tab` page selectors (257 × 16) and hides 109 controls.
- All labels are `live.comment` at the default font (9.5), 18 px tall. Panels are rounded 6, in
  0.53 / 0.16 grey [measured].
- **Design statement:** Bastan says the devices move away from knobs toward "simulation,
  visualization, audio process". Quote: "instead of changing a filter knob you might be changing
  the gravity" [sourced: https://www.ableton.com/en/blog/dillon-bastan-water-ripples-and-sound-waves/].
- **Screenshots:**
  - https://beta-ableton.imgix.net/media/n3ulgfv4/vector-grain-2x.png (972 × 376, i.e. about
    486 px wide at 1× including device chrome)
  - https://beta-ableton.imgix.net/media/44dlg2po/tree-tone-2x.png
  - https://beta-ableton.imgix.net/media/nlypkvmi/bouncy-notes-2x.png

### 1.6 DS drum devices (Live 12 built-ins, encrypted) and the older DrumSynth cells

- **DS Kick** (manual screenshot) [measured: https://ableton-production.imgix.net/live-manual/12/MaxDSKickL12.png,
  314 × 376 at 2×]:
  - about 157 px wide;
  - a dark display holds an icon, a large Pitch readout and small LCD fields for Drive/OT and
    Attack, plus Click and Ø buttons;
  - below it are 3 native dials (Decay, Env, Volume), each with its name above and value below,
    on a pitch of about 47 px and with a knob of about 25 px.
- The manual describes the sliders that live inside the display [sourced:
  https://www.ableton.com/en/live-manual/12/max-for-live-devices/].
- **Older Max for Live Essentials "DrumSynth Kick"** (Max 7) [measured]:
  - 402 px wide; a **fold-out to 803 px** via `live.thisdevice` `setwidth`;
  - 18 dials, 51 numboxes, panels rounded 10.

### 1.7 Sequencers pack (Rhythmic Steps, SQ Sequencer, Step Arp; Max 9.0.7)

- **Rhythmic Steps** [measured]:
  - grids of 17 × 17 picture toggles;
  - LCD numboxes 26–40 × 15;
  - 631 theme-colour references (`theme_elementcolor`, `live_control_selection`, `live_lcd_bg`, …).
- **SQ Sequencer** [measured]:
  - 64 LCD numboxes, 29 × 15;
  - pages through `script hide` / `show`, with 119 hidden controls;
  - a fold-out via `setwidth`.
- **Step Arp** [measured]:
  - a 6-line vertical `live.tab` (72 × 145) as a lane selector;
  - 123 hidden controls.
- Ableton says "their intuitive design sits on top of deep potential" [sourced:
  https://www.ableton.com/en/packs/sequencers/].

### 1.8 Polyrhythm — MIDI Tools by Philip Meyer (Max 8.6.4)

- **Face:** 150 px wide (the MIDI Tools panel) [measured].
  - A **6 × 5 numeric table**: `live.numbox` cells 27–28 × 15, adjacent on a 26-px column pitch so
    neighbours share a 1-px border, and a 16-px row pitch.
  - Header labels at 10 pt with abbreviations: "+Sd", "Len.", "Den.", "Var.", "Vel.".
  - Each row has a 15 × 15 enable toggle.
- This is Ableton's densest shipped table pattern, and it still keeps 15-px cells and 10-pt text.

### 1.9 LFO, Envelope Follower, MPE Control, Convolution Reverb Pro (density widgets)

- **Live 12 built-ins** (manual):
  - LFO, Shaper and Envelope Follower have a "Show/Hide Multimap button at the top right of the
    display", an **overlay** with up to 8 targets.
  - Envelope Follower has a triangle toggle that expands Audio Routing.
  - MPE Control has a triangular button that will "unfold the advanced settings panel" [sourced:
    https://www.ableton.com/en/live-manual/12/max-for-live-devices/].
  - Screenshots: https://ableton-production.imgix.net/live-manual/12/MaxLFOMultimapL12.png and
    https://ableton-production.imgix.net/live-manual/12/MaxMPEControlExpandedViewL12.png.
- **Convolution Reverb Pro** (Essentials, Max 7) [measured]:
  - 458 px wide;
  - a vertical 5-line `live.tab` (51 × 92) switches EQ / pan / modulation panels.
  - The guidelines' example of a "Tabbed view" (`reference/m4l-production-guidelines.md`
    §Device Width).

### 1.10 Third-party devices with UI reputation (web only)

| Device | Reputation evidence | Density strategy | Screenshot |
|---|---|---|---|
| **Fors Opal** | MusicRadar headline: "one of the coolest Max for Live devices we've ever seen" (https://musicradar.com/news/fors-opal-max-for-live) | **In-Rack and Pop-Out** versions; the pop-out window scales "up to 4 times the size". View tabs (Sequencer / Mixer / Settings); a 5-track icon column picks the one engine shown; about 5 main controls per engine, drawn as curves and bars; a **4 × 4 mod matrix** (Vel, LFO, Env, Rand × 4 destinations; click a column header to change its destination); one user-chosen accent hue per instance on dark greys [sourced: guide PDF https://ssphauycfiathltetpfq.supabase.co/storage/v1/object/public/manuals/opal-guide.pdf, https://fors.fm/opal] | https://api.fors.fm/storage/v1/object/public/images/devices/opal/opal-big.png |
| **Fors Chiral** | Sold by Ableton (https://www.ableton.com/en/packs/chiral/) | 3D oscilloscope display plus a "vast Modulation Matrix" | https://api.fors.fm/storage/v1/object/public/images/devices/chiral/chiral.png |
| **Max for Cats Bengal** | Sold by Ableton (https://www.ableton.com/en/packs/bengal/) | A "giant Patch panel" with cables, 50+ sources × 60 targets; a central visual panel switching Scope / Phase / Spectrum. Its 2048 × 1261 image suggests a window larger than the device strip [hypothesis] | https://beta-ableton.imgix.net/media/aarjgk3i/bengal-2x.png |
| **Dillon Bastan Iota** | Sold by Ableton (https://www.ableton.com/en/packs/iota/) | Boxes drawn on a spectrogram; each box "has its own bank" of controls (select one, edit it) | pack art only |
| **Surreal Machines Dub Machines** | Ableton calls them "expertly designed" (https://www.ableton.com/en/packs/dub-machines/) | "All relevant parameters can be tweaked directly in the device interface": no hidden pages | (vendor images may show the plug-in versions) |

Recurring patterns (summary of §1):
- **A display-centred face**, where the display carries controls or changes view (Granulator III,
  DS drums, Inspired by Nature, Bengal).
- **Select one item, edit it in a strip** (Granulator III modulators, Opal tracks, Iota boxes).
- **Small reveal controls:** icon side-tabs, Show/Hide overlays, triangles that unfold panels.
- **Fold-out width** via `setwidth`.
- **Few hues on greys.**

---

## 2. Local ground truth from shipped devices

### 2.1 Method

- **`m4l-boxref`** (`UV_CACHE_DIR=.uv-cache uv run --project tools m4l-boxref <class> --keys`)
  lists Max-saved boxes per class.
  - For example: `live.dial` → 87 boxes in 7 Creative Extensions devices;
    `panel` → 11,108 boxes in 2,167 of 7,281 files, Max help included.
- **Face resolution.** For per-face distributions, a temporary script (in `$TMPDIR`, not
  committed) does the following:
  - parses each frozen `.amxd` container (`mx@c` chunk plus the `dlst`/`dire` file directory);
  - resolves `bpatcher` references to the embedded `.maxpat` files;
  - walks the presentation view recursively, using the bpatcher `offset` and clipping;
  - keeps only boxes inside 169 px;
  - records class, rect, font, `showname`/`shownumber`, appearance, `num_lines_presentation`,
    `livemode`, `usepicture`, panel colours and `saved_attribute_attributes.*.expression`
    (theme colours).
  - A `--face` mode for `m4l-boxref` would make this reproducible [hypothesis: worth adding].
- **Corpus:** 215 readable Factory Pack devices, in three groups:
  - **modern** (31; Max 8.0–9.0.9): Creative Extensions 8, Granulator III, PitchLoop89, Inspired by
    Nature 7, MIDI Tools 5, Sequencers 3, Performance Pack 4, Generators 2;
  - **essentials** (35; Max 6.1–7.1): Max for Live Essentials, including the 13 DrumSynth cells,
    LFO and Poli/Bass v1;
  - **legacy** (149): M4L Building Tools 138, Big Three 3, Granulator II 3, Hypnus Slink 5.
    The Slink faces sit in `$CC#…` bpatchers that did not resolve, so they contribute nothing.
- **Not covered:** the 22 built-in devices and CV Tools are encrypted [measured]. Third-party
  devices other than Slink are not installed.
- **Comparison:** our shell, `devices/aliasing/Aliasing.amxd` (v0.3), measured the same way.

### 2.2 Distributions (counts; "default" = attribute absent)

**`live.dial` (presentation size, w × h)**

| Group | n / devices | Most common sizes | Heights | showname / shownumber / appearance |
|---|---|---|---|---|
| modern | 193 / 20 | 47×48 (28), 40×48 (22), 41×48 (17), 25×23 (15), 45×48 (12), 50×48 (11), 49×36 (11), 51×36 (9), 47×37 (8) | 48: 111 · 36–38: 52 · 23–24: 23 · 50–54: 6 | 1/1/0: 117 · 0/1/0: 27 · 1/1/1 (small): 23 · 0/0/1: 15 · 0/1/1: 8 |
| essentials | 265 / 29 | 44×47 (104), 47×36 (92), 47×47 (17), 50×36 (10), 50×80 (10) | 47: 127 · 36: 121 · 80: 10 | 1/1/0: 131 · 1/1/1: 106 · 1/1/2 (panel): 10 |
| legacy | 443 / 92 | 44×47 (314), 44×53 (46), 47×36 (41) | 47: 324 · 36: 65 · 53: 46 | 1/1/0: 378 · 1/1/1: 51 |
| **aliasing v0.3** | 36 | 36×36 (17), 34×40 (11), 40×45 (8) | 36–45 | painter draws value; separate label |

- Dial font: 163 of 193 modern dials use the default; 25 are set to 10 pt (PitchLoop89); 5 use
  Ableton Sans Book.
- jspainter: 1 of 193 modern dials, 0 of 708 older ones.

**Labels**

| Group | `live.comment` font (n) | `live.comment` height | plain `comment` font (n) |
|---|---|---|---|
| modern | default 327 · 10 pt 50 · Bold 4 (of 381, 20 devices) | 18 px: 376 · 29 px: 5 | Ableton Sans Medium 9.5: 180 · "Medium Regular" 9.5: 15 · "Ableton Sans" 9.5: 6 · 9.4: 3 · 9.0: 2 (of 208) |
| essentials | none | — | Arial Bold 10: 276 · Arial 10: 127 · Helvetica Bold Oblique 18 (titles): 13 |
| legacy | 25 | 18 px | Arial Bold 10: 814 · Arial 10: 279 · Arial Bold 9: 109 · Arial Bold 8: 81 |
| **aliasing v0.3** | 8 pt: 56 · 7.5 pt: 13 · Bold 9: 7 · 9: 1 (of 77) | 11 px: 66 · 13: 7 · 12: 4 | — |

- The default `live.comment` font is Ableton Sans Medium 9.5 in
  `/Applications/Max.app/Contents/Resources/C74/interfaces/transform-defaults/transform-defaults.json`
  [code]. The same file sets plain `comment` to Arial 12, which is why Ableton sets 9.5
  explicitly on plain comments.
- The guidelines name Ableton Sans for all text (`reference/m4l-production-guidelines.md` §Fonts).

**`live.tab`, `live.numbox`, `live.text`, `live.menu` (modern unless noted)**

| Class | Distribution |
|---|---|
| `live.tab` (45 / 16 devices) | **heights** 15: 10 · 19: 8 · 21: 4 · 31: 4 · 17: 3 · 20: 3 · 16: 2 · 101: 3 (vertical) · **sizes** 59×19 (8), 159×101 (3), 59×15 (2), 256×21 (2) · **num_lines_presentation** 1: 32 · 2: 9 · 3: 2 · 4: 1 · 6: 1 · **usepicture** 16 · **livemode 1**: 30 (absent 15). Essentials/legacy: no num_lines saved; heights 16–48 |
| **aliasing `live.tab`** (16) | heights 13: 6 · 14: 5 · 16: 3 · 18: 1 · 32: 1 · livemode absent in all 16 |
| `live.numbox` (653 / 24) | **height** 15: 618 · 13: 33 (Poli/Bass envelope LCDs) · **appearance** 4 LCD: 532 · 2 slider: 61 · 0: 47 · 3 bipolar: 10 · **widths** 29 (116), 39 (85), 41 (77), 47 (61), 17 (29), 26 (28). Essentials: 538 of 538 at 15 px, mostly 36 wide, appearance 0 |
| **aliasing `live.numbox`** (112) | height 12: 108 (matrix cells, 20 wide) · 14: 4 |
| `live.text` (459 / 26) | **sizes** 15×15 (84), 17×17 (47), 67×15 (24), 31×15 (22), 19×19 (16), 21×17 (15), 63×15 (10) · **appearance / picture** picture buttons: 189 · plain text: 139 · LCD (app 2): 86 + 27 with picture · label (app 1): 18 |
| **aliasing `live.text`** (9) | 48–80 × 13–14, all text |
| `live.menu` (117 / 23) | height 15: 117 |

**`panel` and theme colours (modern: 294 panels in 30 devices)**

- **Corner radius:** 0: 125 · 6: 82 · 4: 37 · default: 30 · 2: 9.
  - Essentials: radius 10 (101), with background `[0.14, 0.15, 0.16, 0.4]` (103).
  - Legacy: radius 16 (77).
- **Saved `bgcolor`:** 0.16 grey: 94 · 0.53 grey: 61 · 0.11: 30 · 0.14: 17 · accent cyan
  `[0.43, 0.84, 1, 1]`: 12 · accent amber `[1, 0.71, 0.2, 1]`: 11.
- **Theme expressions on panels:** 80 of 294.
  - `themecolor.live_lcd_bg` as `bgfillcolor`: 64
  - `live_surface_bg`: 7
  - `live_macro_title`: 5
  - `live_surface_frame`: 1
  - `live_active_automation`: 1
- **Most frequent theme references across all classes** (16 of 31 modern devices use any):
  - `comment.textcolor = live_lcd_control_fg_zombie` (114)
  - `live.numbox.lcdcolor = live_value_arc` (68)
  - `panel.bgfillcolor = live_lcd_bg` (64)
  - `live.toggle.bgcolor = theme_elementcolor` (64)
  - `live.numbox.lcdcolor = live_lcd_control_fg_alt` (61)
  - `live.text.activebgcolor = live_lcd_bg` (53)
  - `live.text.textoffcolor = live_lcd_control_fg_zombie` (52)
  - `live.comment.textcolor = live_lcd_control_fg_zombie` (38)
- **Whole factory corpus (all 215 devices, every theme expression):**
  `live_lcd_control_fg_zombie` 302, `live_lcd_bg` 180, `live_value_arc` 114,
  `live_lcd_control_fg` 74, `live_selection` 58, `live_control_fg` 58 [measured: grep over all pack `.amxd`].
- Essentials and legacy use no theme expressions (they predate Live 11 dynamic colours).

**Whole pixels**

- 56 of 459 top-level modern `live.*` rects have fractional coordinates. Ableton does not always
  follow its own guideline of "whole pixels to avoid blurry shapes on non-retina screens"
  (`reference/m4l-production-guidelines.md` §live.* Objects).
- Our layout table uses whole pixels throughout [code].

### 2.3 Typical roles of theme colours (reading of §2.2, [hypothesis] where not explicit)

- **Display or LCD areas:**
  - fill `live_lcd_bg`;
  - text and labels `live_lcd_control_fg_zombie`;
  - active values `live_lcd_control_fg` / `_alt`;
  - numbox LCD colour `live_value_arc`.
- **Control surfaces:** `live_surface_bg`.
- **Small header chips** (Granulator III, SQ Sequencer): `live_macro_title`.

### 2.4 Visible versus hidden controls (saved state)

Granulator III 35 / 114 · Emit 32 / 109 · Vector Grain 19 / 93 · Tree Tone 36 / 50 ·
Step Arp 58 / 123 · Poli 58 / 12 · Bass 61 / 9 · PitchLoop89 49 / 0 · Re-Enveloper 24 / 0 ·
Polyrhythm 51 / 1 (150 px) · DrumSynth Kick 93 / 0 (with fold-out) · SQ Sequencer 177 / 119
(includes per-mode overlapping objects) [measured].

Hiding mechanisms found in the saved patches [measured]:
- `hidden $1` / `script sendbox <name> hidden $1` (Granulator III: 40 + 4 messages);
- `pak hidden i` (Vector FM);
- `script show/hide` (SQ Sequencer);
- `presentation_rect …` messages that move boxes (Granulator III);
- `setwidth $1` to `live.thisdevice` (DrumSynth cells, Map8, SQ Sequencer).

`setwidth` is documented in 9.2 and present in 9.1.5's refpage: "setwidth 0" returns to automatic
width, and the width is not stored with the Set
(`…/C74/docs/refpages/m4l-ref/live.thisdevice.maxref.xml`).

---

## 3. Mod matrices in Ableton instruments

### 3.1 Wavetable (native; Live 10–12)

Source text: Live 12 manual §31.13.5 "Matrix Tab" and §31.13.7 "MIDI Tab"
(https://www.ableton.com/en/live-manual/12/live-instrument-reference/). Screenshot:
https://ableton-production.imgix.net/live-manual/12/WavetableMatrixTabL12.png (1965 × 376, 2×).

- **Place.** It lives in the right-hand display area, which shares four tabs: **Mod Sources |
  Matrix | MIDI | MPE** [measured: screenshot].
- **Columns are sources.**
  - Matrix tab: Amp, Env 2, Env 3, LFO 1, LFO 2.
  - MIDI tab: Velocity, Note, Pitch Bend, Aftertouch, Mod Wheel, Random.
  - The column headers are clickable and jump to that source's panel in Mod Sources [sourced:
    manual].
- **Rows are targets, and they are not fixed.** [sourced: manual]
  - Clicking any parameter in the instrument temporarily brings it into the matrix.
  - It stays if modulation is applied; otherwise it disappears when another parameter is clicked.
  - Matrix and MIDI share the same rows.
  - About 7 rows are visible with a vertical scrollbar [measured: screenshot].
  - The selected target's row label is bold white, the others grey. A faint bar behind each row
    label seems to show the target's own value [measured: screenshot; meaning = hypothesis].
- **Depth.** [sourced: manual; measured: screenshot]
  - Edited by click-drag in the cell.
  - A cell with a value shows a **number** (e.g. "98", "-27", "7.8") in the source's colour, with
    a short **bar** below it showing the depth, drawn from the centre for bipolar values.
  - Empty cells are flat mid-grey tiles with no text.
  - Some targets are additive (neutral 0, bipolar or unipolar sources) and others multiplicative
    (neutral 1), e.g. Sustain, Amount, Volume.
- **Global controls.** A footer row "Global" holds **Time** (scales the speed of all modulators)
  and **Amount** (overall depth) [sourced: manual; measured: screenshot].
- **Colour.** [measured: screenshot]
  - Envelope columns (Amp, Env 2, Env 3) are **cyan**; LFO columns are **orange/amber**.
  - Each header has a coloured underline, and cell numbers and bars share the column colour.
  - The background is the dark display colour.
  - So the colour encodes the source family. That is what makes it scannable; the specific hues
    are what the user dislikes.
- **Geometry at 1×** (approximate, ±1 px) [measured: from the 2× manual screenshot]:
  - matrix panel ≈ 317 px wide;
  - label column ≈ 78 px;
  - source columns ≈ 42 px apart;
  - row pitch ≈ 19 px;
  - cells about 40 × 18 px with 1–2 px gaps.
- **Design rationale** (Ableton blog, 2017-11-29) [sourced:
  https://www.ableton.com/en/blog/new-wave-depth-look-wavetable/]:
  - Matt Jackson: "We called it destination based modulation", i.e. pick what modulates a
    parameter, rather than picking a modulator and then a target.
  - Ian Hobson: showing modulation on the parameters themselves did not fit a Live device, so the
    team chose a matrix and worked to make it inviting rather than technical.
  - Each section started with a minimal set of controls; more were added only for a specific
    purpose.
  - Matrix screenshot from 2017:
    https://cdn-resources.ableton.com/resources/filer_thumbnails/08/5d/085d9586-4209-4a64-acc3-623230c5462b/matrix.jpg__800x275_q85_crop_subsampling-2_upscale.jpg

### 3.2 Meld (native; Live 12)

Source: manual §31.8.6; screenshots
https://ableton-production.imgix.net/live-manual/12/MeldModMatrixL12.png and
https://ableton-production.imgix.net/live-manual/12/MeldExpandedViewL12.png.

- **Same orientation as Wavetable:** sources across the top, targets down the side; click-drag a
  cell up or down. Visible sources: A Env, M Env, LFO 1, LFO 1 FX, LFO 2, Spread; MIDI and MPE are
  sub-tabs [sourced + measured].
- **Targets on demand**, as in Wavetable. They are added to the matrix of the engine currently
  selected [sourced].
- **Engines.** Each engine (A and B) has its own matrix, switched by A/B tabs. "Copy to A/B" and an
  ✕ (clear all) button sit in the matrix header. Expanded View shows all sources and targets
  [sourced + measured].
- **Colour:** one colour per engine. Engine B's matrix is entirely amber (headers, numbers, bars);
  that engine A is cyan is [hypothesis].
- **Cells:** number plus bar when non-zero; about 48 × 19 px at 1× [measured: screenshot].

### 3.3 Drift (native; Live 11.3+)

Source: manual §31.3.6; screenshot https://ableton-production.imgix.net/live-manual/12/DriftModL12.png.

- **No grid.**
  - **Three slots** stacked in a "Mod" tab that shares its area with the LFO tab.
  - Each slot has three lines: Source chooser, Amount (−100 … +100 %), Destination chooser.
  - Choosers are orange; amounts are cyan on the dark display panel [sourced + measured].
- **Fixed routings beside their targets:** Pitch Mod (Env 2 / LFO with amounts), Freq Mod (Env 2 /
  Press with amounts) and the Osc 1 Shape mod source with amount [measured: screenshot].
- Clutter therefore grows with use, not with the number of sources × targets.

### 3.4 Matrix-like patterns in M4L devices

- **Granulator III, per-parameter strip.** [measured]
  - One 21-px row of up to 9 LCD amount boxes (39 × 15) under 9.5-pt source labels, for the
    selected main parameter.
  - Targets have different source subsets; Henke: "Parameters have different sets of modulators".
    For example, "Note PB > Pitch" exists, but there is no "Slide > Pitch".
  - 77 further mod-amount `live.numbox` parameters are stored hidden at the same rect and swapped
    in.
  - This is the destination-based idea in one row.
- **Inspired by Nature, source slots.** 5 fixed sources, each with a tiny amount dial (25 × 23)
  and a destination menu (43 × 15), on a hidden side page [measured].
- **Fors Opal, small full matrix.** 4 × 4 (Vel, LFO, Env, Rand × 4 destinations). Column headers
  are destination pickers [sourced: Opal guide].
- **Bengal, patch panel.** Cables between 50+ sources and 60 targets in a large panel [sourced:
  https://www.ableton.com/en/packs/bengal/].
- **Polyrhythm, numeric table.** 6 × 5 abutting 27 × 15 cells, 10-pt abbreviated headers
  [measured; §1.8].
- **Live LFO / Shaper / Envelope Follower, Multimap.** Up to 8 targets in an overlay [sourced:
  manual chapter 33].

### 3.5 Patterns that reduce clutter, applied to 9 sources × 12 targets [hypothesis unless marked]

**What Ableton's matrices do** [sourced / measured above]:
- Rows appear only for targets that are modulated or selected.
- A non-zero cell shows a number and a mini bar; zero shows nothing.
- Colour by source family (Wavetable) or by engine (Meld).
- About 40 × 19 px cells and 9.5-pt text.
- A scrollbar instead of shrinking.
- One global Amount (and Time).

**Fitting it into our 314-px page area:**
- Wavetable-sized cells (≈ 42 px) allow about 5–6 source columns next to a 70-px label column.
  So 9 sources need about 30 px per column at 17–19 px rows.
- 9 × 30 + 48 (labels) ≈ 318 px, i.e. just within the page area.
- Showing only modulated targets plus the selected one gives, in practice, about 3–6 rows instead
  of 12.

**Options for the designer:**
- **(A) Wavetable-style.** Sources as columns (9 × ~30 px). Rows = targets in use plus the target
  of the last-clicked control. A "show all 12" toggle.
- **(B) Granulator III-style strip.** Clicking a target control (Write Pitch, Size, Drive, …)
  shows its 9 source amounts in one 15–19 px row under the display or page header, with a triangle
  marker on the selected control. This needs no Mod page at all.
- **(C) Slots.** For example 8–10 rows of [source menu][amount][target menu], like Drift and the
  Vector devices. This would require a parameter redesign (menus as parameters).
  - Not compatible with D10/D25 as decided.
  - Note it as an alternative only.

For (A) and (B), all 108 cell parameters stay; only visibility changes, as in Granulator III
(§2.4 mechanisms). Hidden cells keep automation, so a row with automated depth should count as
"in use" [hypothesis].

---

## 4. Text sharpness of painted controls

### 4.1 Causes

1. **Implementation.**
   - mgraphics is "inspired by and analogous to the Cairo API" but "drawn using JUCE"; JUCE
     cannot be called directly. There is no antialias or hinting API [sourced:
     https://sdk.cdn.cycling74.com/max-sdk-8.2.0/group__jgraphics.html; MGraphics reference
     https://docs.cycling74.com/apiref/js/mgraphics/ lists no such method].
   - The only text-AA setting is global: `; max maxcharheightforsubpixelantialiasing <pt>`, the
     "threshold font size in points for native subpixel a[ntialiasing]"
     (`…/userguide/content/controlling_max_with_messages.json`).
   - It probably has no effect on current macOS, which dropped subpixel AA in 10.14 [hypothesis;
     https://bugs.webkit.org/show_bug.cgi?id=193095].
2. **Edges between pixels.**
   - Integer coordinates are pixel corners, so 1-px lines need a 0.5 offset [sourced:
     https://www.cairographics.org/FAQ/#sharp_lines].
   - Cycling '74's own jspainter example draws its 1-px border as `rectangle(0.5, 0.5, width-1, …)`
     (`…/userguide/content/custom_ui_objects.json`;
     `/Applications/Max.app/Contents/Resources/Examples/javascript/jspainter/border-override.js`).
   - Fractional widths, and fractional x or baseline for text, land between device pixels.
   - Our painters [code]:
     - `paint_max.ts` `text()` centres at `x − w/2` without rounding;
     - `aliasing_paint_dial.ts` puts the baseline at `h − 2.5`;
     - the cell and number painters at `h/2 + 3` (fractional for odd heights);
     - line widths 1.1 / 1.4 / 1.5 / 1.8 / 2.5 / 2.6;
     - `aliasing_paint_cell.ts:28` fills a 1-px bar at `round(w/2) − 0.5`, which spreads over two
       pixels at 1×.
3. **Small sizes.**
   - Our painters use 7.5–9 pt (cells 7.5, tabs 8–9, dials 8–9). Native Live text is 9.5 pt
     (§2.2).
   - Ableton's own mgraphics code (Color Limiter `grmeterbg.js`) uses Ableton Sans Medium 9.5.
   - Cycling '74's `C74/jsui/jsui_live_color_picker.js` uses Ableton Sans Medium 10 [code].
   - At 7.5–8 pt, Ableton Sans Medium strokes are thinner than one device pixel at 1× [hypothesis].
4. **Transparent backgrounds.** The SDK suggests disabling `useimagebuffer` for text on transparent
   backgrounds when the system cannot antialias to them (`jgraphics_system_canantialiastexttotransparentbg`).
   Our dial painter draws its value text with no opaque fill behind it. Thinner grayscale AA is
   possible there [sourced: SDK; effect = hypothesis].
5. **Offscreen images.** `Image()` / `push_group` caches render at 1× on Retina unless built at 2×
   and drawn at `scale(0.5, 0.5)` [sourced, user reports:
   https://cycling74.com/forums/mgraphics-image-differs-from-standard-drawing-on-2x-retina-displays,
   https://cycling74.com/forums/improve-image-resolution-of-text-in-mgraphics]. Our painters use
   none [code].
6. **Zoom.**
   - SDK device coordinates are "before any zooming", so a painter cannot see Live's or Max's zoom
     factor [sourced: SDK].
   - At fractional zoom (e.g. 125 % on a 2× display = 2.5 device px per px), no alignment is fully
     crisp [hypothesis].
   - No Ableton source found on how Live's Zoom Display scales M4L views; the help article returned
     403 [open].
7. **The mock-up compares different fonts.** [code + sourced]
   - `Main.dc.html` loads Inter 400/500/600 from Google Fonts and lists it first.
   - Browsers default to subpixel-style font smoothing on macOS; `-webkit-font-smoothing:
     antialiased` "makes it look lighter" (https://developer.mozilla.org/en-US/docs/Web/CSS/font-smooth).
8. **"Dials look smaller" is not geometry.** [code: computed from the painter and the mock-up
   sources]
   - Painter knob radius is 13 / 9.5 / 11.5 px (boxes 40 × 45, 36 × 36, 34 × 40); the mock-up
     radius is 12.75 / 9.4 / 10.5 px.
   - The native DS Kick dial knob is about 25 px wide, in a box about 47 px wide [measured, §1.6].
   - Likely causes [hypothesis]: viewing scale (browser zoom / fit-to-width preview against Live at
     100 %), Inter's heavier rendering, and the thin 2.5-px track in our dials.

### 4.2 Rules for a crisp jspainter `paint()`

[sourced] where backed by a source above, otherwise [hypothesis]:

1. **Read the size on every paint.** Use `mgraphics.size` inside `paint()`;
   `relative_coords = 0`; no hard-coded sizes [sourced: MGraphics reference; Ableton's
   `livedial_override.js` does the same].
2. **Font.** Ableton Sans Medium **9.5** for values and labels; Bold only where a title is really
   needed. Never below 9 pt on the face [sourced: native default 9.5; Ableton's painter 9.5;
   minimum = hypothesis].
3. **Text order.** `select_font_face` and `set_font_size` **before** `text_measure`.
4. **Text position.** Round to whole pixels:
   - x = `Math.round(cx − w/2)`;
   - baseline = `Math.round(cy + (ascent − descent)/2)` from `font_extents()`.
   - `show_text` ignores matrix transforms ("Matrix transforms will not affect this drawing"), so
     never rely on `scale()` / `translate()` for text placement [sourced: MGraphics reference;
     rounding = hypothesis].
5. **Straight lines.** 1 px strokes centred on `floor(x) + 0.5`; 2 px strokes on integers; filled
   hairlines as `rectangle(Math.round(x), y, 1, h)`. Integer widths only [sourced: Cairo FAQ, C74
   example].
6. **Arcs and curves** are always antialiased. A 2–2.5 px arc width is fine; Ableton's dial uses
   2.33 [code: Color Limiter].
7. **No `scale()`.** It "affects line widths" [sourced: MGraphics reference].
8. **Contrast and background.** Draw text fully opaque in the theme text colour, over an opaque
   fill in the surface colour where possible. Dim inactive text by colour, not by low alpha
   [hypothesis; Ableton's meter uses white at alpha 0.46 on a dark fill].
9. **No `Image()` caches.** If one is needed, build it at 2× and draw it with `scale(0.5, 0.5)`;
   rebuild it on resize [sourced: forum reports].
10. **Verify crispness:**
    - in Live at Zoom Display 100 % on Retina, and on a 1× display if one is available;
    - compare with native `live.comment` text at 9.5;
    - judge the mock-up only after it uses Ableton Sans at 100 % and the same pixel scale
      [hypothesis].
11. **Box sizes:** whole-pixel presentation rects; `live.tab` with `livemode 1` [sourced: guidelines
    §live.* Objects].

---

## 5. Open points

| # | Check |
|---|---|
| GUI-1 | How Live's Zoom Display (Look/Feel) scales M4L device views and jspainter text: no source found (help.ableton.com 403) |
| GUI-2 | Whether `live.tab` `livemode 1` changes jspainter-painted tabs at all (the painter replaces drawing) |
| GUI-3 | Text weight with and without an opaque fill behind painter text (cause 4), at 1× and 2× |
| GUI-4 | Real width of the Vector devices in Live (saved `devicewidth` 256, content to ~320 px, side panels to ~500; the 2× screenshot suggests ~470 px) |
| GUI-5 | Theme hues for "source family" colours that are not Wavetable's cyan and orange, checked in Light and Dark themes |
| GUI-6 | Granulator III's runtime visibility logic in detail (only saved states were read) |

---

## Sources

**Local (read-only)**
- `~/Music/Ableton/Factory Packs/**/*.amxd` (215 readable frozen devices, 10 encrypted CV Tools).
  Key files:
  - `Granulator III/Granulator III/Ableton Folder Info/Granulator III.amxd`
  - `PitchLoop89/PitchLoop89/Ableton Folder Info/PitchLoop89.amxd`
  - `Creative Extensions/Instruments/{Poli,Bass}/Ableton Folder Info/*.amxd`
  - `Creative Extensions/Audio Effects/Color Limiter/…` (embedded `livedial_override.js`,
    `grmeterbg.js`, `grmeter.js`)
  - `Inspired by Nature by Dillon Bastan/**`
  - `MIDI Tools by Philip Meyer/MIDI Tools/Generators/Polyrhythm.amxd`
  - `Sequencers/**`
  - `Max for Live Essentials/**` (DrumSynth cells, LFO, Convolution Reverb Pro)
- `tools/src/m4l_tools/boxref.py` (`m4l-boxref`)
- `/Applications/Max.app/Contents/Resources/C74/interfaces/transform-defaults/transform-defaults.json`
- `/Applications/Max.app/Contents/Resources/C74/docs/refpages/m4l-ref/{live.dial,live.tab,live.text,live.numbox,live.thisdevice}.maxref.xml`;
  9.1.5 copy of `live.thisdevice.maxref.xml` under `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Max/…`
- `/Applications/Max.app/Contents/Resources/C74/docs/userguide/content/{custom_ui_objects,controlling_max_with_messages}.json`,
  `…/m4l/live_userinterfaces.json` ("height of all Live devices is fixed at 169 pixels")
- `/Applications/Max.app/Contents/Resources/Examples/javascript/jspainter/border-override.js`,
  `/Applications/Max.app/Contents/Resources/C74/jsui/jsui_live_color_picker.js`
- Repo:
  - `reference/m4l-production-guidelines.md` (§Design: Live Color Themes, Fonts, Device Width,
    Custom Device Width, live.* Objects, Pop-out Windows)
  - `reference/m4l.md`
  - `devices/aliasing/Aliasing.amxd`
  - `devices/aliasing/docs/mockup-v0.3/{layout.md,Main.dc.html}`
  - `devices/aliasing/docs/v0.3-design.md`
  - `devices/aliasing/js/src/{paint_max,aliasing_paint_dial,aliasing_paint_cell,aliasing_paint_tab,aliasing_paint_number,aliasing_paint_toggle}.ts`
  - `docs/research/notes/m4l-custom-ui-and-sync-2026-11-24.md`

**Web: Ableton manual and blog**
- Live 12 manual, Instrument Reference (Wavetable §31.13.5–7, Meld §31.8.6, Drift §31.3.6): https://www.ableton.com/en/live-manual/12/live-instrument-reference/
- Live 12 manual, Max for Live devices (LFO, Shaper, Envelope Follower, MPE Control, DS drums): https://www.ableton.com/en/live-manual/12/max-for-live-devices/
- Manual images:
  - https://ableton-production.imgix.net/live-manual/12/WavetableMatrixTabL12.png
  - https://ableton-production.imgix.net/live-manual/12/MeldModMatrixL12.png
  - https://ableton-production.imgix.net/live-manual/12/MeldExpandedViewL12.png
  - https://ableton-production.imgix.net/live-manual/12/DriftModL12.png
  - https://ableton-production.imgix.net/live-manual/12/MaxDSKickL12.png
  - https://ableton-production.imgix.net/live-manual/12/MaxLFOMultimapL12.png
  - https://ableton-production.imgix.net/live-manual/12/MaxMPEControlExpandedViewL12.png
- Ableton blog, "New Wave: An In-Depth Look at Wavetable" (2017-11-29): https://www.ableton.com/en/blog/new-wave-depth-look-wavetable/
- Ableton blog, Dillon Bastan interview: https://www.ableton.com/en/blog/dillon-bastan-water-ripples-and-sound-waves/
- Pack pages:
  - https://www.ableton.com/en/packs/granulator-iii/
  - https://www.ableton.com/en/packs/pitchloop89/
  - https://www.ableton.com/en/packs/inspired-nature/
  - https://www.ableton.com/en/packs/creative-extensions/
  - https://www.ableton.com/en/packs/midi-tools/
  - https://www.ableton.com/en/packs/sequencers/
  - https://www.ableton.com/en/packs/cv-tools/
  - https://www.ableton.com/en/packs/chiral/
  - https://www.ableton.com/en/packs/bengal/
  - https://www.ableton.com/en/packs/iota/
  - https://www.ableton.com/en/packs/dub-machines/
- Ableton Max for Live page (device images): https://www.ableton.com/en/live/max-for-live/
- Ableton maxdevtools (guidelines source): https://github.com/Ableton/maxdevtools

**Web: device screenshots**
- https://roberthenke.com/technology/granulator3.html, https://roberthenke.com/files_images/technology/g3/g3-interface.png
- https://roberthenke.com/technology/pitchloop89.html, https://beta-ableton.imgix.net/media/5vgdffeq/pitchloop89-2x.png
- https://beta-ableton.imgix.net/media/n3ulgfv4/vector-grain-2x.png
- https://beta-ableton.imgix.net/media/44dlg2po/tree-tone-2x.png
- https://beta-ableton.imgix.net/media/nlypkvmi/bouncy-notes-2x.png
- https://ableton-production.imgix.net/blog/creative-extensions/poli.gif
- https://beta-ableton.imgix.net/media/mvcmtly0/bass-2x.png
- https://beta-ableton.imgix.net/media/asbdrnui/color-limiter-2x.png
- https://beta-ableton.imgix.net/media/aarjgk3i/bengal-2x.png
- https://api.fors.fm/storage/v1/object/public/images/devices/opal/opal-big.png
- https://api.fors.fm/storage/v1/object/public/images/devices/chiral/chiral.png

**Web: third-party and reviews**
- https://fors.fm/opal; Opal guide PDF https://ssphauycfiathltetpfq.supabase.co/storage/v1/object/public/manuals/opal-guide.pdf
- https://musicradar.com/news/fors-opal-max-for-live
- https://www.soundonsound.com/techniques/ableton-live-12-granulator-iii
- https://www.attackmagazine.com/technique/tutorials/getting-freaky-with-live-11s-new-inspired-by-nature-devices/
- https://www.attackmagazine.com/technique/tutorials/10-common-modulation-routings-using-abletons-wavetable/

**Web: rendering**
- MGraphics JS reference: https://docs.cycling74.com/apiref/js/mgraphics/
- Max SDK JGraphics: https://sdk.cdn.cycling74.com/max-sdk-8.2.0/group__jgraphics.html
- Cairo FAQ, sharp lines: https://www.cairographics.org/FAQ/#sharp_lines
- Forum threads:
  - https://cycling74.com/forums/mgraphics-image-differs-from-standard-drawing-on-2x-retina-displays
  - https://cycling74.com/forums/improve-image-resolution-of-text-in-mgraphics
  - https://cycling74.com/forums/way-to-truly-non-anti-antialiased-lines-using-jgraphics
- MDN font-smooth: https://developer.mozilla.org/en-US/docs/Web/CSS/font-smooth
- WebKit subpixel AA removal: https://bugs.webkit.org/show_bug.cgi?id=193095
- Cycling '74 user guide, M4L user interfaces: https://docs.cycling74.com/userguide/m4l/live_userinterfaces/

**Failed or not read**
- help.ableton.com (HTTP 403)
- dillonbastan.com (no connection / JS-only)
- surrealmachines.com product pages (404/502)
- isotonikstudios.com (403)
- Ableton pack slugs `/packs/drum-synths/` and `/packs/grain-scanner/` (404)
