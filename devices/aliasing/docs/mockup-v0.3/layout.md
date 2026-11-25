# aliasing — v0.3 face layout (from the mock-up)

Generated from the mock-up's layout table (`mockup-v0.3/Main.dc.html`, `buildLayout()`), so every rect
here is exactly what the mock-up draws. Face 968 × 169 px; rects are presentation rects in face
coordinates (whole pixels). Spec: `../v0.3-design.md` (D1–D30). Published canvas:
https://claude.ai/artifact/Q7WjdTv3XSUBiQkBwCKwt3 (private Design canvas, v0.3 face).

Scripting-name rules are the v0.2 ones (`js/src/pages_model.ts`): area prefix `w_ r_` (always),
`tbl_` (hidden on Tone), `lfo_ mod_ tone_ out_` (pages 0–3; the Global page keeps the `out_`
prefix), condition `free/sync`, `hz1/sy1`, `hz2/sy2`. **New rule needed:** the five Sym labels
`w_symlbl_*` are shown by Write Shape (one per shape group, same rect).

Counts: 261 elements; 108 matrix cells; 174 controls (incl. Page and the matrix);
77 live.comment labels; 4 panels; 3 live.line.

Measured limits kept (v0.3-design.md §3): horizontal live.slider 18 px with stock name/number off;
live.numbox 12–14 px; 2-row live.tab 32 px; nothing overlaps the display (v8ui). No two elements
that can be visible at the same time overlap (checked over all page × mode × shape states), and every
element lies inside one of the four panels.

## 1. Panels and colours

| Panel | Rect x y w h |
|---|---|
| `panel_w` (Write section surface) | 4 4 300 79 |
| `panel_r` (Read section surface) | 4 86 300 79 |
| `panel_disp` (display + Size slider surface) | 306 4 332 161 |
| `panel_page` (page area surface) | 642 4 322 161 |

Max `panel`, rounded 4, no border. Colours (mock-up, Live 12 "Default … Neutral Medium" themes):

| Theme | Device background (Live `SurfaceBackground`) | Panel "Auto" | Alternative |
|---|---|---|---|
| Light | #a5a5a5 [measured: t3 screenshot pixel 165] | #989898 (darker) | #b3b3b3 (lighter) |
| Dark | #363636 [sourced: Default Dark Neutral Medium.ask] | #414141 (lighter) | #2d2d2d (darker) |

Mapping to Max theme colours **[hypothesis]**: no single `themecolor.*` is known to give "a bit darker
than the device in Light and a bit lighter in Dark". Max's own defaults (`interfaces/maxcolors.json`)
name `live_surface_bg` "Device Background", `live_lcd_bg` "LCD Background", `live_macro_title`
"Control Header", `live_control_bg` "Control Off", `live_control_text_bg` "Text Background";
shipped devices fill large panels with `themecolor.live_lcd_bg` (SQ Sequencer, Slice Shuffler) and
`themecolor.live_macro_title` (SQ Sequencer) [measured: m4l-boxref]. Their values in Live's
themes are not documented locally. Suggested shell approach: compute the panel colour from
`max.getcolor("live_surface_bg")` in the pages script (v8) — luminance > 0.5: mix 8 % toward black,
else 6 % toward white — and set `bgfillcolor` on the four `panel_*` objects at load and on a theme
change (`live.colors` or a repaint check); Max itself derives style colours by mixing
`live_control_bg` and `live_surface_bg` (`interfaces/theme_constructor.js`, line 1209). Fallback if
that fails: `themecolor.live_lcd_bg` (to be checked in both themes, t4).

## 2. Pointer rows, display, page tabs (always visible)

| Scripting name | Max class | Rect x y w h | Page | Shown when | Content / notes |
|---|---|---|---|---|---|
| `w_title` | live.comment | 10 11 52 13 | always |  | "WRITE" (title, bold 9) |
| `w_mode` | live.tab | 10 28 52 14 | always |  | Hz / Sync |
| `w_sync_mult` | live.numbox | 10 46 25 14 | always | Write Sync | x 1-128 (units "×%d") |
| `w_sync_div` | live.numbox | 37 46 25 14 | always | Write Sync | ÷ 1-32 (units "÷%d") |
| `w_free_lbl1` | live.comment | 66 11 40 11 | always | Write Hz | "Pitch" |
| `w_sync_lbl1` | live.comment | 66 11 40 11 | always | Write Sync | "Rate" |
| `w_free_lbl2` | live.comment | 106 11 40 11 | always | Write Hz | "Fine" |
| `w_sync_lbl2` | live.comment | 106 11 40 11 | always | Write Sync | "Detune" |
| `w_free_pitch` | live.dial | 66 22 40 45 | always | Write Hz | −64…+130 st, default 0, steps 195 |
| `w_sync_note` | live.dial | 66 22 40 45 | always | Write Sync | note value enum (19) |
| `w_fine` | live.dial | 106 22 40 45 | always |  | −1…+1 st, default 0, steps 2001 |
| `w_symlbl_curve` | live.comment | 146 11 40 11 | always | Write Shape ∈ {ramp} | "Curve"; shown for ramp |
| `w_symlbl_skew` | live.comment | 146 11 40 11 | always | Write Shape ∈ {tri,tripm,sine} | "Skew"; shown for tri,tripm,sine |
| `w_symlbl_width` | live.comment | 146 11 40 11 | always | Write Shape ∈ {pulse,spike} | "Width"; shown for pulse,spike |
| `w_symlbl_duty` | live.comment | 146 11 40 11 | always | Write Shape ∈ {pulsar} | "Duty"; shown for pulsar |
| `w_symlbl_smooth` | live.comment | 146 11 40 11 | always | Write Shape ∈ {noise} | "Smooth"; shown for noise |
| `w_sym` | live.dial | 146 22 40 45 | always |  | −1…+1, 0.01 grid (201 steps) |
| `w_shapelbl` | live.comment | 190 11 60 11 | always |  | "Shape" |
| `w_shape` | live.tab | 190 23 108 32 | always |  | Ramp / Tri / Tri ± / Sine / Pulse / Pulsar / Spike / Noise, 2 rows; 2 rows × 4 icons (num_lines 2) |
| `w_active` | live.tab | 190 59 108 14 | always |  | Freeze / Write / Clean; Write State, default Write |
| `r_title` | live.comment | 10 93 52 13 | always |  | "READ" (title, bold 9) |
| `r_mode` | live.tab | 10 110 52 14 | always |  | Hz / Sync |
| `r_sync_mult` | live.numbox | 10 128 25 14 | always | Read Sync | x 1-128 (units "×%d") |
| `r_sync_div` | live.numbox | 37 128 25 14 | always | Read Sync | ÷ 1-32 (units "÷%d") |
| `r_free_lbl1` | live.comment | 66 93 40 11 | always | Read Hz | "Pitch" |
| `r_sync_lbl1` | live.comment | 66 93 40 11 | always | Read Sync | "Rate" |
| `r_free_lbl2` | live.comment | 106 93 40 11 | always | Read Hz | "Fine" |
| `r_sync_lbl2` | live.comment | 106 93 40 11 | always | Read Sync | "Detune" |
| `r_free_pitch` | live.dial | 66 104 40 45 | always | Read Hz | −64…+130 st, default 0, steps 195 |
| `r_sync_note` | live.dial | 66 104 40 45 | always | Read Sync | note value enum (19) |
| `r_fine` | live.dial | 106 104 40 45 | always |  | −1…+1 st, default 0, steps 2001 |
| `r_lbl3` | live.comment | 146 93 40 11 | always |  | "Spread" |
| `r_spread` | live.dial | 146 104 40 45 | always |  |  |
| `r_shapelbl` | live.comment | 190 93 60 11 | always |  | "Shape" |
| `r_shape` | live.tab | 190 105 108 18 | always |  | Ramp / Tri |
| `r_smooth` | live.text | 190 127 52 14 | always |  | "Smooth" (toggle) |
| `r_dir` | live.text | 246 127 52 14 | always |  | "1-Way" / "2-Way" (toggle) |
| `display` | v8ui | 308 6 328 136; **Tone: 308 6 328 157** (y 6–163) | always |  | aliasing_display.js; header 3–15, lanes 17–127 (5 × 22), overview 130–134; on Tone (Size slider hidden) the box grows to 157 px: curve rect x 4 y 17 w 320 h = box h − 31 (126), frequency labels below |
| `page` | live.tab | 646 8 314 16 | always |  | LFO · Env / Mod / Tone / Global; stored only |
| `tbl_size` | live.slider | 308 145 328 18 | all but Tone |  | horizontal, showname 0, shownumber 0 (painter draws "Size" and the value) |

## 3. Pages

### LFO · Env (page 0)

| Scripting name | Max class | Rect x y w h | Page | Shown when | Content / notes |
|---|---|---|---|---|---|
| `lfo_l1title` | live.comment | 646 30 44 13 | LFO · Env |  | "LFO 1" (title, bold 9) |
| `lfo_l1mode` | live.tab | 696 30 52 13 | LFO · Env |  | Hz / Sync |
| `lfo_l1shape` | live.tab | 646 49 102 16 | LFO · Env |  | Sine / Tri / Saw / Square / S&H / Random |
| `lfo_l1lbl0` | live.comment | 646 72 34 11 | LFO · Env |  | "Rate" |
| `lfo_l1lbl1` | live.comment | 680 72 34 11 | LFO · Env |  | "Phase" |
| `lfo_l1lbl2` | live.comment | 714 72 34 11 | LFO · Env |  | "Spread" |
| `lfo_hz1_rate` | live.dial | 646 83 34 40 | LFO · Env | LFO 1 Hz |  |
| `lfo_sy1_note` | live.dial | 646 83 34 40 | LFO · Env | LFO 1 Sync |  |
| `lfo_l1phase` | live.dial | 680 83 34 40 | LFO · Env |  |  |
| `lfo_l1spread` | live.dial | 714 83 34 40 | LFO · Env |  |  |
| `lfo_l1retriglbl` | live.comment | 646 137 30 13 | LFO · Env |  | "Retrig"; same text line as the tab: vertically centred, font 8 like the tab [check in Live] |
| `lfo_l1retrig` | live.tab | 678 137 70 13 | LFO · Env |  | Off / Note / Bar |
| `lfo_l2title` | live.comment | 752 30 44 13 | LFO · Env |  | "LFO 2" (title, bold 9) |
| `lfo_l2mode` | live.tab | 802 30 52 13 | LFO · Env |  | Hz / Sync |
| `lfo_l2shape` | live.tab | 752 49 102 16 | LFO · Env |  | Sine / Tri / Saw / Square / S&H / Random |
| `lfo_l2lbl0` | live.comment | 752 72 34 11 | LFO · Env |  | "Rate" |
| `lfo_l2lbl1` | live.comment | 786 72 34 11 | LFO · Env |  | "Phase" |
| `lfo_l2lbl2` | live.comment | 820 72 34 11 | LFO · Env |  | "Spread" |
| `lfo_hz2_rate` | live.dial | 752 83 34 40 | LFO · Env | LFO 2 Hz |  |
| `lfo_sy2_note` | live.dial | 752 83 34 40 | LFO · Env | LFO 2 Sync |  |
| `lfo_l2phase` | live.dial | 786 83 34 40 | LFO · Env |  |  |
| `lfo_l2spread` | live.dial | 820 83 34 40 | LFO · Env |  |  |
| `lfo_l2retriglbl` | live.comment | 752 137 30 13 | LFO · Env |  | "Retrig"; same text line as the tab: vertically centred, font 8 like the tab [check in Live] |
| `lfo_l2retrig` | live.tab | 784 137 70 13 | LFO · Env |  | Off / Note / Bar |
| `lfo_div1` | live.line | 750 32 1 118 | LFO · Env |  |  |
| `lfo_div2` | live.line | 856 32 1 118 | LFO · Env |  |  |
| `lfo_envtitle` | live.comment | 858 30 102 13 | LFO · Env |  | "ENV FOLLOWER" (title, bold 9) |
| `lfo_envmeter` | live.meter~ | 858 52 102 10 | LFO · Env |  | OPTIONAL (beyond spec): follower level, horizontal; needs a gen~ outlet for the env value |
| `lfo_envlbl0` | live.comment | 858 72 34 11 | LFO · Env |  | "Attack" |
| `lfo_envlbl1` | live.comment | 892 72 34 11 | LFO · Env |  | "Release" |
| `lfo_envlbl2` | live.comment | 926 72 34 11 | LFO · Env |  | "Gain" |
| `lfo_env_att` | live.dial | 858 83 34 40 | LFO · Env |  | 0.1–100 ms, default 5 |
| `lfo_env_rel` | live.dial | 892 83 34 40 | LFO · Env |  | 10–2000 ms, default 150 |
| `lfo_env_gain` | live.dial | 926 83 34 40 | LFO · Env |  | −24…+24 dB, default +12 |
| `lfo_envnote` | live.comment | 858 137 102 13 | LFO · Env |  | "post Tone · pre Limiter" (8 pt) |

### Mod (page 1)

Matrix: 9 rows (sources) × 12 columns (targets), cell pitch 21 px, 3-px gaps between the target groups
write | read | table | tone | out. Column x: wp 694, sy 715, wa 736, rp 760, sp 781, sz 805, dv 829, bc 850, bw 871, rf 892, rb 913, ou 937.
Row y: l1 42, l2 55, en 68, dr 81, ve 94, mw 107, vo 120, nb 133, ro 146.
Cell = `live.numbox` 20 × 12, scripting name `mod_<src>_<tgt>` (gen~ Param `mx_<src>_<tgt>`), long name
"<Source> > <Target>", −100…+100 %, default 0, painter: bipolar bar from the centre, value text when ≠ 0,
bar colour = write accent (W Pit, Sym, Write), read accent (R Pit, Sprd), neutral otherwise.

| Scripting name | Max class | Rect x y w h | Page | Shown when | Content / notes |
|---|---|---|---|---|---|
| `mod_cl_wp` | live.comment | 694 29 20 11 | Mod |  | "W Pit" (7.5 pt); Write Pitch |
| `mod_cl_sy` | live.comment | 715 29 20 11 | Mod |  | "Sym" (7.5 pt); Write Sym |
| `mod_cl_wa` | live.comment | 736 29 20 11 | Mod |  | "Write" (7.5 pt); Write |
| `mod_cl_rp` | live.comment | 760 29 20 11 | Mod |  | "R Pit" (7.5 pt); Read Pitch |
| `mod_cl_sp` | live.comment | 781 29 20 11 | Mod |  | "Sprd" (7.5 pt); Read Spread |
| `mod_cl_sz` | live.comment | 805 29 20 11 | Mod |  | "Size" (7.5 pt); Size |
| `mod_cl_dv` | live.comment | 829 29 20 11 | Mod |  | "Drive" (7.5 pt); Drive |
| `mod_cl_bc` | live.comment | 850 29 20 11 | Mod |  | "Ctr" (7.5 pt); Band Center |
| `mod_cl_bw` | live.comment | 871 29 20 11 | Mod |  | "Wid" (7.5 pt); Band Width |
| `mod_cl_rf` | live.comment | 892 29 20 11 | Mod |  | "R Frq" (7.5 pt); Res Freq |
| `mod_cl_rb` | live.comment | 913 29 20 11 | Mod |  | "R Fb" (7.5 pt); Res Fdbk |
| `mod_cl_ou` | live.comment | 937 29 20 11 | Mod |  | "Out" (7.5 pt); Output |
| `mod_rl_l1` | live.comment | 646 42 46 12 | Mod |  | "LFO 1" (8 pt) |
| `mod_rl_l2` | live.comment | 646 55 46 12 | Mod |  | "LFO 2" (8 pt) |
| `mod_rl_en` | live.comment | 646 68 46 12 | Mod |  | "Env" (8 pt) |
| `mod_rl_dr` | live.comment | 646 81 46 12 | Mod |  | "Drift" (8 pt) |
| `mod_rl_ve` | live.comment | 646 94 46 12 | Mod |  | "Velocity" (8 pt) |
| `mod_rl_mw` | live.comment | 646 107 46 12 | Mod |  | "Mod Wheel" (8 pt) |
| `mod_rl_vo` | live.comment | 646 120 46 12 | Mod |  | "Voice" (8 pt) |
| `mod_rl_nb` | live.comment | 646 133 46 12 | Mod |  | "Neighbour" (8 pt) |
| `mod_rl_ro` | live.comment | 646 146 46 12 | Mod |  | "Read Osc" (8 pt) |

### Tone (page 2)

| Scripting name | Max class | Rect x y w h | Page | Shown when | Content / notes |
|---|---|---|---|---|---|
| `tone_drive_on` | live.text | 646 29 44 13 | Tone |  | "DRIVE" (section power toggle); section power (toggle), default on |
| `tone_ldrive` | live.comment | 646 45 40 11 | Tone |  | "Amount" |
| `tone_drive` | live.dial | 648 56 36 36 | Tone |  |  |
| `tone_arrow1` | live.comment | 688 66 10 12 | Tone |  | "›" (9 pt) |
| `tone_band_on` | live.text | 698 29 44 13 | Tone |  | "BAND" (section power toggle); section power, default on |
| `tone_lband0` | live.comment | 698 45 36 11 | Tone |  | "Center" |
| `tone_band_center` | live.dial | 698 56 36 36 | Tone |  |  |
| `tone_lband1` | live.comment | 734 45 36 11 | Tone |  | "Width" |
| `tone_band_width` | live.dial | 734 56 36 36 | Tone |  |  |
| `tone_lband2` | live.comment | 770 45 36 11 | Tone |  | "Res" |
| `tone_band_res` | live.dial | 770 56 36 36 | Tone |  |  |
| `tone_lband3` | live.comment | 806 45 36 11 | Tone |  | "FM" |
| `tone_band_fm` | live.dial | 806 56 36 36 | Tone |  |  |
| `tone_lband4` | live.comment | 842 45 36 11 | Tone |  | "Spread" |
| `tone_band_spread` | live.dial | 842 56 36 36 | Tone |  |  |
| `tone_band_mode` | live.tab | 884 58 76 13 | Tone |  | Pass / Reject |
| `tone_band_slope` | live.tab | 884 75 76 13 | Tone |  | 12 / 24 dB |
| `tone_res_on` | live.text | 646 98 70 13 | Tone |  | "RESONATOR" (section power toggle); section power, default off |
| `tone_res_track` | live.text | 722 98 64 13 | Tone |  | "Track Read" (toggle) |
| `tone_lres0` | live.comment | 646 114 36 11 | Tone |  | "Freq" |
| `tone_res_freq` | live.dial | 646 125 36 36 | Tone |  |  |
| `tone_lres1` | live.comment | 682 114 36 11 | Tone |  | "Fdbk" |
| `tone_res_fb` | live.dial | 682 125 36 36 | Tone |  |  |
| `tone_lres2` | live.comment | 718 114 36 11 | Tone |  | "Mix" |
| `tone_res_mix` | live.dial | 718 125 36 36 | Tone |  |  |

### Global (page 3, prefix out_)

| Scripting name | Max class | Rect x y w h | Page | Shown when | Content / notes |
|---|---|---|---|---|---|
| `out_tplay` | live.comment | 646 29 50 13 | Global |  | "PLAY" (title, bold 9) |
| `out_lgate` | live.comment | 646 44 100 11 | Global |  | "Gate" (above the tab; shell deviation, see §5) |
| `out_gate` | live.tab | 646 55 100 14 | Global |  | Drone / MIDI |
| `out_lresync` | live.comment | 646 72 100 11 | Global |  | "Resync (bars)" (above the tab) |
| `out_resync` | live.tab | 646 83 100 14 | Global |  | Off / 1 / 2 / 4 / 8; bars |
| `out_syncnow` | live.text | 646 101 48 14 | Global |  | "Sync now" (momentary) |
| `out_aa` | live.text | 698 101 48 14 | Global |  | "Ramp AA" (toggle) |
| `out_ltransp` | live.comment | 646 118 44 11 | Global |  | "Transpose" |
| `out_transpose` | live.dial | 650 129 36 36 | Global |  | −48…+48 st, steps 97 |
| `out_div` | live.line | 749 32 1 128 | Global |  |  |
| `out_lim_on` | live.text | 752 29 56 13 | Global |  | "LIMITER" (section power toggle); Color Limiter on/off, default on |
| `out_llim0` | live.comment | 752 45 36 11 | Global |  | "Gain" |
| `out_lim_gain` | live.dial | 752 56 36 36 | Global |  |  |
| `out_llim1` | live.comment | 788 45 36 11 | Global |  | "Sat" |
| `out_lim_sat` | live.dial | 788 56 36 36 | Global |  |  |
| `out_llim2` | live.comment | 824 45 36 11 | Global |  | "Color" |
| `out_lim_color` | live.dial | 824 56 36 36 | Global |  |  |
| `out_llim3` | live.comment | 860 45 36 11 | Global |  | "Release" |
| `out_lim_rel` | live.dial | 860 56 36 36 | Global |  |  |
| `out_llim4` | live.comment | 896 45 36 11 | Global |  | "Ceiling" |
| `out_lim_ceil` | live.dial | 896 56 36 36 | Global |  |  |
| `out_tout` | live.comment | 752 98 60 13 | Global |  | "OUTPUT" (title, bold 9) |
| `out_lwidth` | live.comment | 752 114 36 11 | Global |  | "Width" |
| `out_width` | live.dial | 752 125 36 36 | Global |  |  |
| `out_loutput` | live.comment | 788 114 36 11 | Global |  | "Output" |
| `out_output` | live.dial | 788 125 36 36 | Global |  |  |
| `out_meter` | live.meter~ | 942 29 18 132 | Global |  | stereo, vertical |
| `out_info` | live.comment | 830 150 108 11 | Global |  | "Aliasing v0.3 · after D. Pank" (7.5 pt) |

## 4. Decisions in the mock-up beyond the spec (for review)

- Absolute layout with four panels: Write 4 4 300 79, Read 4 86 300 79, display 306 4 332 161,
  page area 642 4 322 161; the v0.2 column x positions stay (rows 10–298, display 308–636, pages
  646–960).
- Matrix columns grouped by area (W Pit, Sym, Write | R Pit, Sprd | Size | Drive, Ctr, Wid, R Frq,
  R Fb | Out) instead of the D14 list order; column labels coloured by group.
- Section power switches are the section titles themselves (DRIVE, BAND, RESONATOR, LIMITER as
  `live.text` toggles, filled when on), not a separate power icon.
- Drive dial label "Amount" (the title already says DRIVE).
- Env Follower: optional level bar `lfo_envmeter` (needs a gen~ outlet for the follower value) and a
  hint line "post Tone · pre Limiter".
- Global page: Gate and Resync labels left of their tabs (no label row); Sync now and Ramp AA side by
  side; Transpose dial below; meter at the far right over both rows; info line moved to the Output row.
- The write title has no accent dot (v0.2 mock-up had one).
- Write Shape icons: position over one cycle; Pulsar/Spike draw their rest as a flat line at 0.

## 5. Changes in the shell after the mock-up (Claude, 2026-11-25)

Found in the canvas preview of the generated shell (`test/preview/make_preview.mjs`, real painters):

- **Global, left column:** Gate and Resync labels moved above their tabs and the tabs widened to
  100 px (Resync 5 × 20 px), because "Off" did not fit a 14-px segment at 8 pt (shown as "O.");
  Sync now / Ramp AA and Transpose moved down accordingly (rows above updated).
- **Vertical dividers** are `live.line` boxes 3 px wide (the line is drawn centred), x 749 / 855 / 748.
- **Labels next to a painted tab or cell** ("Retrig", the matrix row labels, "post Tone · pre Limiter")
  sit 1 px lower than their tab/cell (t3: the "Retrig" baseline was 1 px above the tab text).
- **Painter palette** = this mock-up's THEME and Graphite accent values; with the old v0.2 palette
  the outlines of pills and tabs (#424242) vanished on the dark panels (#414141).
- **Panels** are coloured by the pages script from `live.colors` → `live_surface_bg` (8 % darker on a
  light, 6 % lighter on a dark background; tested values: #a5a5a5 → #989898, #363636 → #424242).
- **Tone display height (D31):** the pages script (`displayRectFor`) resizes the v8ui to 308 6 328 157 on
  the Tone page and to 308 6 328 136 elsewhere; `check_shell.py` checks both rects.
- **Section power switches (D32, variant E chosen by the user):** `tone_drive_on` 646 29 48 13,
  `tone_band_on` 698 29 48 13, `tone_res_on` 646 98 80 13, `out_lim_on` 752 29 64 13: the toggle painter
  draws the bold title and a power symbol right after it (no pill); `tone_res_track` moves to 730 98 64 13.
  Mock-ups of the alternatives: `node test/preview/make_preview.mjs OUT.html SHELL.amxd variants`.
