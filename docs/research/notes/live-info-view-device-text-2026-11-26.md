# Info texts of a Max for Live device: which fields Max and Live show (2026-11-26)

Question: where do the texts of Max's clue window and Live's Info View come from, per control and for
the device as a whole? Evidence markers as in `CLAUDE.md`.

## Per object

- `annotation` is the text, `annotation_name` the title. Both are box attributes ("Description" section
  of the object inspector). [sourced: local refpages `max-ref/jbox.maxref.xml` ("Sets the text that will
  be displayed in the Clue window when the user moves the mouse over the object"),
  `m4l-ref/live.dial.maxref.xml` (`annotation_name`: "This shows up in the Info pane in Live, and the
  clue window in Max"); Ableton, M4L Production Guidelines, "Info Text",
  <https://github.com/Ableton/maxdevtools/blob/main/m4l-production-guidelines/m4l-production-guidelines.md>]
- Max mirrors both into a parameter's `valueof` as `parameter_info` and `parameter_annotation_name`
  (`m4l-ref/paraminspector.maxref.xml`: the header "By default … is the Long Name of the parameter").
  [measured: 11 271 Max-saved parameter boxes in Max's Max for Live package, its `help/m4l` and Live's
  App-Resources, 2026-11-26: 2 373 carry `annotation` only, 181 `annotation` + `parameter_annotation_name`,
  109 `annotation` + `annotation_name` + `parameter_annotation_name`, 78 all four, 0 `parameter_info`
  without `annotation`.] So `annotation` is the field to trust; `parameter_info` alone is not enough.
- Non-parameter objects (panel, bpatcher): a forum user reports an annotation works "if they're
  clickable", another suggests a `[panel]` in the background whose scripting name is the header and whose
  annotation is the text; neither is confirmed. [sourced, unofficial:
  <https://cycling74.com/forums/max-for-live-device-title-bar-and-info-view-description>,
  <https://cycling74.com/forums/change-m4l-info-text>] → [open] for our panels and `live.comment` labels
  (aliasing t8).
- [measured: aliasing t8, user in Live 12.4.16, 2026-11-26] `live.dial` and `live.menu` parameters show
  `annotation_name` / `annotation`. A `live.comment` (foreground, no ignoreclick) and a `panel` in the
  background layer, both with `annotation` + `annotation_name` and a scripting name, show Live's default
  device text instead.
- [measured 2026-11-26] 377 shipped `.amxd` (Live's App-Resources, Max's Max for Live package, the
  Factory Packs): the annotated non-parameter objects are `live.meter~` (36), `waveform~` (24),
  `textbutton` (18), `multislider` (14), `ubutton` (10), `jsui` (10), `live.arrows` (9), `bpatcher` (12)
  and a few more, all in the foreground; no `panel`, no `comment`, no `live.comment`. Where they have a
  readable title it is the scripting name (`Gain Reduction Meter`, `Note Order`), `annotation_name` is
  unset.
- [measured: probe `devices/aliasing/test/probe-info/InfoProbe.amxd`, user in Live 12.4.16, 2026-11-26;
  `testlog/aliasing/2026-11-26.md`] Of nine candidates with their own text, Live's Info View showed it for
  an invisible **`ubutton`**, a **`live.dial`** and a **`live.meter~`** (on the meter itself). It showed
  the default device text for a `panel` in the background layer, a `panel` in the foreground (with
  `annotation_name` or with a scripting name only), a `live.comment`, a `comment`, and a `live.comment`
  with ignoreclick lying on a foreground panel. So the layer is not the reason: panels and comments do
  not hand an annotation to Live. Not reported: which title the three working tiles showed, the `v8ui`.
- Pattern that follows: an invisible `ubutton` (`hilite 0`, as in Ableton's Gated Delay) at the rect of a
  label, in front of it, carries the label's text. `devices/aliasing/scripts/bootstrap_shell.py` `tip_zone()`.
- **Box order = z-order, front to back:** the first box of a patcher's `boxes` array is the frontmost of
  its layer. [measured 2026-11-26: in 68 Max-saved devices with a foreground `panel` under controls, 593
  of 598 such controls come before their panel in the file; aliasing t8b: `ubutton` zones listed before
  the controls took the hover of every dial and meter (the user saw the zone's text everywhere).] A
  generated zone therefore goes right *before* the object it covers, and nothing large may be listed
  before the controls. The background layer (`background: 1`) lies behind everything whatever the order.
  Consequence for the probe: tile 7's `live.comment` was listed after its panel, i.e. behind it, so tile
  7 says nothing about ignoreclick.

## For the device (title bar)

- Live shows a default text for a device ("The Aliasing Instrument" for `Aliasing.amxd` [measured: user
  report, aliasing t8, 2026-11-26; where the mouse was is not reported]).
- No field of the `.amxd` is known to set it: the patcher inspector's fields were tried without effect
  ("No field in the patcher inspector seems to correspond with the title or description in the 'info
  view'"; "didn't see anything in the patcher inspector though that worked for me"). The one way named
  is Live's own context menu "Edit Info Text", stored with the Live Set or a device preset, not in the
  `.amxd`. [sourced, unofficial, no staff answer: the two threads above; Ableton manual, "Edit Info Text",
  <https://www.ableton.com/en/manual/first-steps/>]
- None of the 110 `.amxd` files in Live 12.4.16's App-Resources has a patcher `description`. [measured
  2026-11-26] Whether Live's bundled Max devices get their device text from Live's own (packed)
  language resources is [hypothesis].
- <https://cycling74.com/forums/ableton-live-info-text> asks about reading the text through the Live API;
  no answer.

## Consequence for this workbench

Texts go into `annotation` + `annotation_name` (and the two `valueof` mirrors) of parameters, meters and
displays; labels get a `ubutton` zone with the text in front of them; panels and comments carry none; the
device's description sits on the title lines of the Global page (user, 2026-11-26).
`devices/aliasing/scripts/check_shell.py` enforces it. The patcher `description` stays as metadata. A
device-level text on the title bar is not something the device can ship.
