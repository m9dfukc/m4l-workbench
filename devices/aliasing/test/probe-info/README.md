# InfoProbe: which objects hand an info text to Live's Info View?

A throwaway **audio effect** (audio passes through untouched, it makes no sound) for aliasing t8
(2026-11-26). In the device, `live.*` parameters show their title and text in Live's Info View, but a
`live.comment` label and a `panel` in the background layer show Live's default device text ("The
Aliasing Instrument") [measured: `testlog/aliasing/2026-11-26.md`, t8]. The probe asks which
non-parameter object does hand its `annotation` over, and where the title comes from.

Nine numbered tiles; each says "PROBE <n>: …" with the title "Title <n>" if its text reaches Live:

| # | Object | Fields | Question |
|---|---|---|---|
| 1 | `panel`, background layer | annotation + annotation_name | control: the device's way (expected: default text) |
| 2 | `panel`, foreground | annotation + annotation_name | is the background layer the reason? |
| 3 | `panel`, foreground | annotation only, scripting name "Probe Three" | does the title come from the scripting name? |
| 4 | `live.comment` | annotation + annotation_name | control: the device's labels (expected: default text) |
| 5 | `comment` | annotation + annotation_name | does a plain comment behave differently? |
| 6 | `ubutton`, invisible | annotation + annotation_name | an invisible hover zone for labels and empty areas |
| 7 | `live.comment` with ignoreclick on a foreground panel | 7a (comment), 7b (panel) | does the hover fall through to the panel? |
| 8 | `live.dial` "Probe Info Dial" | info title "Title 8" | title = annotation_name or the long name? |
| 9 | `live.meter~` | annotation + annotation_name | do the device's meters show their texts? |

**Result (user, Live 12.4.16, 2026-11-26):** only 6 (`ubutton`), 8 (`live.dial`) and 9 (`live.meter~`, on
the meter itself) showed their text; 1–5 and 7 showed Live's default text for the device. Titles not
reported. Tile 7 is void: Max lists boxes front to back, so its comment lay behind the panel, not on it.
Log: `testlog/aliasing/2026-11-26.md`; conclusions:
`docs/research/notes/live-info-view-device-text-2026-11-26.md`.

| File | What |
|---|---|
| `make_infoprobe.py` | Generator (python3, stdlib only) → `InfoProbe.amxd` from Live's `Max Audio Effect.amxd` |
| `InfoProbe.amxd` | Generated device (unfrozen). Regenerate rather than edit; it is a probe |

```sh
python3 -B devices/aliasing/test/probe-info/make_infoprobe.py --force
```

(Close the device in Max first: Max reloads changed files and drops unsaved edits.)
