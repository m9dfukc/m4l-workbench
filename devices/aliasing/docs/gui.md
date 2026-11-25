# aliasing — GUI layout (v0.1)

> **Superseded for v0.2** by `redesign-t1.md` (R8–R19, approved mock-up `mockup-v0.2/`) and
> `v0.2-build.md` (as built). Kept as the record of the v0.1 face.

The device face approved by the user on 2026-11-24 after review of an interactive HTML mock-up
(review canvas: https://claude.ai/artifact/X3E1185X9a8xbtu3jddGRq, private). Basis:
`port-decisions.md` §2–§3. This file is the reference when the shell `Aliasing.amxd` is built;
after that, the unfrozen `.amxd` is the source of truth and this file is updated from it.

Evidence: everything here is **[code]** (mock-up only) unless marked; nothing has run in Max or
Live yet. Items marked **[open]** must be checked in Max.

## 1. Frame

| Item | Value |
|---|---|
| Face | **834 × 169 px** presentation area (`openinpresentation 1`, device width 834) |
| Margins | 8 px left and right; elements in whole pixels |
| Areas (left → right) | global column x 8–68 · write/read rows x 84–270 · display x 286–586 · paged area x 602–830 |
| Dividers | `live.line` at x 76, 278, 594 (y 10, h 141) |
| Font | Ableton Sans (mock-up used Inter as a stand-in), 9 pt for labels and values, Bold 9 for section labels |
| Colours | Live dynamic colours on every `live.*` object (follow the theme, including the inactive state); fixed colours only for the two accents and the display content |

## 2. Colours

| Role | Value | Used on |
|---|---|---|
| **Write accent** | `#ff5c8a` (in light themes shaded 22 % darker on device surfaces) | write dials' value arc, write toggles/tabs "on", "WRITE" labels, write head markers |
| **Read accent** | `#3cc6f0` (same shading rule) | read dials, read toggles/tabs, "READ" labels, read head markers |
| Global / tone / out controls | Live's own dynamic colours (on = theme accent, e.g. `#ffad56` dark / `#ffb901` light) | Activate, Sync, Tone and Out pages |
| Display background | dark in both themes (`#181818` dark, `#242424` light, i.e. Live's `DisplayBackground` / `RetroDisplayBackground`) | v8ui |
| **Voice lines / cells** | **grey ramp** (user, 2026-11-24): `#f2f2f2`, `#cfcfcf`, `#aaaaaa`, `#868686`, `#666666` for voices 1–5 | display only |

The user rejected coloured voice lines: the voices are monochrome so that only the write and
read markers carry colour. Warm and cool monochrome ramps were offered in the mock-up as
alternatives; grey is the decision.

Reference values for the mock-up came from Live 12's theme files
(`…/App-Resources/Themes/Default Dark|Light Neutral Medium.ask`). In the device, theme-following
colours come from Max's dynamic colours (`live_*`), not from these hex values.

## 3. Elements

Presentation rects as `x y w h` (origin top-left of the face). **P**: A = automatable Live
parameter (34), S = stored with the set only (`parameter_visibility` "Stored Only"), — = no
parameter. Long names are final once a version is out (`.claude/rules/max-patch.md`).

### Always visible

| Element | Max object | Long name | Values | P | Rect |
|---|---|---|---|---|---|
| Activate | `live.text` toggle | Activate | Off / On; MIDI note gates it | A | 8 10 60 26 |
| Sync | `live.text` button | Sync | momentary | A | 8 40 60 15 |
| "Preset" label | `comment` | | | — | 8 118 60 12 |
| Preset menu | `live.menu` | Preset | names from `presets/*.json` (v8) | S | 8 132 60 15 |
| "WRITE" label | `comment`, write accent | | | — | 84 8 80 12 |
| Write Pitch | `live.dial` | Write Pitch | −64 … +64 st, int | A | 84 20 44 47 |
| Write Fine | `live.dial` | Write Fine | −1 … +1 st | A | 130 20 44 47 |
| Write Shape | `live.tab`, 3 rows | Write Shape | Ramp / Tri / =Read | A | 178 22 44 45 |
| Write Active | `live.text` toggle | Write Active | Off / On | A | 226 22 44 15 |
| Row divider | `live.line` | | | — | 84 80 186 1 |
| "READ" label | `comment`, read accent | | | — | 84 86 80 12 |
| Read Pitch | `live.dial` | Read Pitch | −64 … +64 st, int | A | 84 98 44 47 |
| Read Fine | `live.dial` | Read Fine | −1 … +1 st | A | 130 98 44 47 |
| Read Shape | `live.tab`, 2 rows | Read Shape | Ramp / Tri | A | 178 100 44 30 |
| Smooth | `live.text` toggle | Smooth | Off / Linear | A | 226 100 44 15 |
| Table display | `v8ui` `aliasing_display.js` | | | — | 286 8 300 134 |
| "Size" label | `comment` | | | — | 286 147 26 13 |
| Size bar | `live.slider`, horizontal | Size | 0.001 … 1 | A | 312 146 180 15 |
| Display mode | `live.tab` | Display Mode | Line / 2D | S | 496 146 56 15 |
| Display on/off | `live.text` toggle, picture (eye) | Display | Off / On | S | 556 146 30 15 |
| Page selector | `live.tab` | Page | Mod / Tone / Out | S | 602 8 228 15 |

### Page Mod

| Element | Max object | Long name | Values | P | Rect |
|---|---|---|---|---|---|
| "WRITE" label | `comment`, write accent | | | — | 602 50 40 12 |
| Write Symmetry | `live.dial` | Write Symmetry | −1 … +1 | A | 644 32 44 47 |
| Write LFO Rate | `live.dial` | Write LFO Rate | 0 … 12 | A | 736 32 44 47 |
| Write LFO Depth | `live.dial` | Write LFO Depth | 0 … 1 (depth⁵ st) | A | 782 32 44 47 |
| Row divider | `live.line` | | | — | 602 88 228 1 |
| "READ" label | `comment`, read accent | | | — | 602 116 40 12 |
| Read Direction | `live.tab`, 2 rows | Read Direction | 1-way / Both | A | 644 106 44 30 |
| Read Spread | `live.dial` | Read Spread | 0 … 6 st | A | 690 98 44 47 |
| Read LFO Rate | `live.dial` | Read LFO Rate | 0 … 12 | A | 736 98 44 47 |
| Read LFO Depth | `live.dial` | Read LFO Depth | 0 … 1 (depth⁵ st) | A | 782 98 44 47 |

Columns line up by meaning: x 644 = triangle skew (Symmetry / Direction), x 736 = LFO Rate,
x 782 = LFO Depth; the read row sits at the same y as the left read row (98).

### Page Tone

| Element | Max object | Long name | Values | P | Rect |
|---|---|---|---|---|---|
| Notch On | `live.text` toggle | Notch On | Off / On | A | 602 30 54 15 |
| Filter On | `live.text` toggle | Filter On | Off / On (HP4 → Sat → LP4) | A | 660 30 112 15 |
| DC Block | `live.text` toggle | DC Block | Off / On | A | 776 30 54 15 |
| Notch Freq | `live.dial` | Notch Freq | 20 Hz … 10 kHz, log | A | 607 50 44 47 |
| HP Freq | `live.dial` | HP Freq | 20 Hz … 20 kHz, log | A | 665 50 44 47 |
| LP Freq | `live.dial` | LP Freq | 20 Hz … 20 kHz, log | A | 723 50 44 47 |
| Drive | `live.dial` | Drive | 0 … 30 dB | A | 781 50 44 47 |
| Notch Q | `live.numbox` | Notch Q | 0 … 0.98 | A | 602 110 54 15 |
| Notch Gain | `live.numbox` | Notch Gain | −30 … +20 dB | A | 602 138 54 15 |
| HP Reso | `live.numbox` | HP Reso | 0 … 0.98 | A | 660 110 54 15 |
| HP FM | `live.numbox` | HP FM | 0 … 3000 Hz | A | 660 138 54 15 |
| LP Reso | `live.numbox` | LP Reso | 0 … 0.98 | A | 718 110 54 15 |
| LP FM | `live.numbox` | LP FM | 0 … 3000 Hz | A | 718 138 54 15 |
| Numbox labels | `comment` ×6 ("Q", "Gain", "Reso", "FM") | | | — | above each numbox: y 99 / 127, h 11, same x/w |

### Page Out

| Element | Max object | Long name | Values | P | Rect |
|---|---|---|---|---|---|
| Transpose | `live.dial` | Transpose | −12 … +12 st, int | A | 607 50 44 47 |
| Width | `live.dial` | Width | 0 … 2 | A | 665 50 44 47 |
| Output | `live.dial` | Output | −36 … 0 dB | A | 723 50 44 47 |
| Output meter | `live.meter~` | | stereo level | — | 790 32 36 116 |
| Info line | `comment` | | "5 voices · drone · MIDI note gates Activate" | — | 607 118 170 11 |

Count: 11 always visible + 7 Mod + 13 Tone + 3 Out = **34 automatable parameters**, matching
`port-decisions.md` §2.

## 4. Display (`v8ui`)

- 300 × 134 px, reads `buffer~ ---atab` (5 ch × 1024) plus the 10 head positions from gen~
  (`snapshot~`), redraw ≤ 30 fps; the buffer name is passed by message (no `---` inside JS).
- **Line mode:** 5 voice rows overlaid as polylines (grey ramp), faint quarter grid; per voice a
  write head (filled dot on the curve + tick at the bottom edge, write accent) and a read head
  (ring on the curve + tick at the top edge, read accent). Label "LINE" top-left, legend
  "● write ○ read" top-right.
- **2D mode:** 5 rows (≈ 26.8 px each), 100 columns, cell brightness = table value (grey
  ramp colour, opacity 0.06 + 0.94·value); write and read heads as vertical lines in their row.
- **Size in the display:** the part of the table beyond `Size·1024` is dimmed; a dashed edge with
  a small handle at `x = Size·300` can be dragged and sets the Size parameter (a user gesture,
  so undo entries are wanted here).
- **Click** (without drag) toggles Line / 2D, mirrored in the Display Mode tab.
- **Display off:** drawing stops, the last frame stays dimmed with the text
  "DISPLAY OFF"; DSP unaffected.

## 5. Page switching (proposal)

The Page `live.tab` shows one of three object groups at the same place. Proposal: every page
object gets a scripting name with a page prefix (`mod_*`, `tone_*`, `out_*`) and a small v8
handler (in `aliasing_presets.js` or its own file) sets `hidden` per group; alternatively three
`bpatcher`s. Decide when the shell is built; parameters inside `bpatcher`s need
`embed 1` and unique long names. [open]

## 6. Differences from `port-decisions.md` §3 (approved with the mock-up)

- **Smooth** moved from the Out page to the left read row (it is read interpolation); its slot
  mirrors **Write Active** in the write row.
- **Preset menu** in the left column under Activate/Sync.
- **Size** as a horizontal `live.slider` directly under the display, plus the draggable edge
  inside the display.
- **Display Mode, Display on/off and Page** are stored-only parameters (not automatable).
- **Tone page:** frequencies and Drive as dials; Q, Gain, Reso, FM as `live.numbox` (13
  controls do not fit as dials in 228 × 130 px); one Filter On toggle spans HP and LP.
- **Out page:** Transpose, Width, Output and an output meter.
- Voice lines monochrome (grey ramp), accents only for write/read.

## 7. Open checks in Max

| # | Check |
|---|---|
| G1 | Does a horizontal `live.slider` (180 × 15) show its value inside the bar, or is a separate value display needed? |
| G2 | Does `live.dial` draw a bipolar parameter's arc from the centre (Write/Read Fine, Symmetry, Transpose)? The mock-up assumes it does. |
| G3 | Do vertical `live.tab`s with 3 rows × 15 px (Write Shape) stay legible at 9 pt? |
| G4 | `live.text` with a picture (eye icon) follows the theme's text colour in both states? |
| G5 | Page switching via `hidden` (§5): any flicker, and do hidden `live.*` objects still respond to automation? |
| G6 | v8ui at 30 fps with 5 × 1024 reads: UI CPU in Live with Display on vs. off. |
| G7 | Light themes: contrast of the shaded accents on the device surface (dial arcs). |
