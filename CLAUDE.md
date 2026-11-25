# m4l-workbench — Max for Live devices, built code-first

Workbench for the user's own **Max for Live (M4L) devices**, built with Claude Code. Some devices
are **ports of Native Instruments Reaktor ensembles**; others are original designs. Goals, in this order:

1. **Workbench:** a reproducible, text-first way to build M4L devices: DSP as GenExpr text,
   logic as TypeScript → v8 JavaScript, the `.amxd` as a thin, diffable shell. Offline checks
   before anything is loaded in Max or Live.
2. **First device: `aliasing`**, a port of the Reaktor User Library ensemble **Aliasing Synth**
   (`devices/aliasing/`). An audio table is written and read at different ("careless") speeds;
   the resulting errors are the sound. 5 voices; HP+FM, LP+FM and a notch behind it.
3. Further devices later, each in its own `devices/<name>/` folder.

## Environment (checked 2026-11-24)

- **Max 9.2.0** standalone at `/Applications/Max.app` (full licence: Gen/MC authoring and gen~
  code export need it). Bundled packages (Gen, RNBO 1.4.5, Node for Max) live in
  `Max.app/Contents/Resources/C74/packages/`. Refpages:
  `/Applications/Max.app/Contents/Resources/C74/docs/refpages/` (2161 `*.maxref.xml`): the local
  ground truth for object names, inlets, outlets, attributes. Max examples:
  `/Applications/Max.app/Contents/Resources/Examples/gen/`.
- **Ableton Live 12 Suite 12.4.16**; it runs its bundled Max **9.1.5** [sourced: Live `Log.txt`].
  Development targets Max 9.2 in Live too (user, 2026-11-24): Live Settings → File & Folder →
  Max Application → standalone Max, restart; confirm with the `Max: Version …` line in Live's
  log. Released devices must still run on stock Live's 9.1.5 (see GenExpr rule).
- **Live's log** `~/Library/Preferences/Ableton/Live <version>/Log.txt` contains Max errors of
  loaded devices (`Message from Max: …`) — read it after a user test instead of asking for a
  console copy where that is enough. Stock devices log unrelated "incorrect architecture"
  errors; filter by device name.
- Live's blank instrument template (start of every instrument shell):
  `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Instrument.amxd`.
  Ableton's Poli / Bass (Max for Live Essentials) show the `poly~` + `gen~` voice pattern.
- **Reaktor 6.5.2** (for reference renders of the originals; no CLI).
- Node v26 (nvm), pnpm, tsc 5.9; Python 3.14 via **uv**; Apple clang 21, cmake; git, gh.

## Decisions (user, 2026-11-24)

- **Repo:** this directory, public on GitHub as **`m9dfukc/m4l-workbench`** (remote `origin`,
  `git@github.com:m9dfukc/m4l-workbench.git`, branch `main`, MIT; first push 2026-11-24).
- **Monorepo:** one folder per device under `devices/<name>/`; no submodules.
- **Third-party Reaktor material stays local:** `.ens` files and screenshots live in
  `devices/<name>/reference/reaktor/` (gitignored, provenance + SHA-256 in the committed
  README there). Only our own analyses, code and recordings of our own devices go into git.
- **Max version:** develop against Max 9.2 (standalone and in Live); check compatibility with
  Live's bundled Max only before a release.
- **Roles:** the **user operates Max and Live**: loads devices, listens, reads the Max
  console and reports back. Claude builds, runs the offline checks and keeps the test logs.
  Claude does not drive Max/Live via computer use or MCP, apart from the two exceptions below.
  An MCP inspector may come later, on the user's request, and only in a separate sandbox device
  (re-evaluated 2026-11-25: still no Max MCP; `docs/research/notes/live-automation-mcp-2026-11-25.md`).
- **Exception, standalone Max for unattended tests (user, 2026-11-24, round 2):** Claude may
  launch standalone Max from the command line with a **test patch from this repo** that renders
  with the NonRealTime driver (no sound) or exports gen~ C++, then quits itself. Conditions:
  never Live, never the user's own patches, and only after the user confirmed that no Max with
  unsaved work is open (Max reuses a running instance). Restore the audio driver afterwards.
- **Exception, Live test harness (user, 2026-11-25, spike) — optional, only while switched on:**
  the Live automation is **off by default** (fresh clone, no `tools/live/local.json`); the user
  switches it with `node tools/live/harness.mjs on|off`, `status` shows it, and the scripts refuse
  to touch Live while it is off. Off = every Live test is a `live-test` handover, as before.
  While on, Claude may run the pinned
  `eladefrati/ableton-live-test-harness` (AbletonOSC fork as a Remote Script, setup in
  `tools/live/README.md`, skill `live-harness`) and our checks in `tools/live/`: relaunch Live on the harness's empty
  Set (Main at −inf dB), load a device of this repo from Places, set parameters, record it
  silently, read Live's `Log.txt` and `MaxPlugLib.log`. Conditions: ask the user whether Live is
  free (relaunch **discards unsaved work**) before the first relaunch of a session and whenever
  `doctor.js` says the open Set was not started by the harness; never the user's own Sets or
  templates; recordings only from the device track's Post FX with that track at −inf and the
  recording track's monitoring Off (the checks enforce it); no real mouse clicks
  (`device-ui.js`) and no window captures unless the user asks; the harness stays at the pinned
  commit until a new one has been read. Listening, A/B against Reaktor, the bundled-Max round
  and the freeze stay with the user.
- **Live's log** may be read (read-only) after a user test to collect Max errors.
- **Reaktor file parsing** is allowed (user, 2026-11-24): a read-only parser for `.ens`/`.ism`
  lives **only locally** in `tools/local/` (gitignored, never committed or published — NI has
  enforced its EULA against a public parser). Its findings go into `devices/<name>/docs/`
  marked `[observed: parser]`.
- **Max compatibility:** GenExpr must pass gencheck for 9.1.5 and 9.2.0 (`tools/check.sh`), so a
  released device runs on stock Live; development happens in 9.2.
- **Languages/tools:** control logic in TypeScript → CommonJS for `v8`, but the TS toolchain is
  set up only when a device first needs JS (tsc vs. esbuild decided then); Python tools
  (analysis, null tests, spectra) as a uv project in `tools/`. max-gen-helper is installed as a
  Claude Code plugin (skill `gen-pitfalls` + guard hook); scripts use the vendored gencheck.
- **Skills:** `grill-me`/`grilling`, `handoff`, `research` kept; `live-test`, `reaktor-port`,
  `m4l-release` new; path rules for GenExpr, patches and v8 JS.
- **Fresh-eyes reviews (user, 2026-11-25):** Google's Elephant-Goldfish Model plugin was
  evaluated and not installed (its draft/brainstorm/bootstrap duplicate our docs, its reviewers
  target web software); its core idea lives on as the own skill `fresh-review`.

## Architecture (every device)

Three layers; the rules in `.claude/rules/` load with the matching files.

| Layer | Lives in | Edited by | Source of truth |
|---|---|---|---|
| **Shell**: `.amxd` with `plugin~`/`plugout~` or MIDI in, `gen~ @gen …`, `v8 …`, `live.*` parameters, presentation layout | `devices/<name>/<Name>.amxd` (unfrozen) | mostly the user in the Max editor; Claude only via a generator or careful JSON edits | the unfrozen `.amxd` (after the first bootstrap, not a generator script) |
| **DSP**: GenExpr | `devices/<name>/gen/*.genexpr` → generated `devices/<name>/*.gendsp` | Claude | the `.genexpr` text |
| **Logic**: v8 JavaScript | `devices/<name>/js/src/*.ts` → bundled `devices/<name>/*.js` | Claude | the `.ts` sources |

- Everything a device needs at runtime lies **flat in `devices/<name>/`** next to the `.amxd`,
  so Max finds it on the device's search path. Generated files are committed (the device must
  load from a plain clone), with a header comment naming their source.
- **No audio in JS** (v8 runs in the low-priority thread). No DSP in the patch beyond wiring.
- **Never commit frozen devices.** Releases attach a frozen copy (`m4l-release` skill).
- Max **reloads a file that changes on disk and drops unsaved editor changes without asking**
  (in-place writes). Before writing a `.amxd`/`.maxpat`, ask whether it is open in Max with
  unsaved changes. Writing `.gendsp`/`.js` while the device is open is intended (hot reload).

## Evidence markers (all docs)

- **[sourced]**: an external source exists (docs, repo, forum), linked.
- **[code]**: derived from our code or a generator's output, not yet run in Max/Live.
- **[hypothesis]**: conclusion, untested.
- **[measured]**: confirmed or refuted in Max/Live or by an offline measurement, with a
  reference to the test log or the script output.
- **[open]**: must be checked in Max, Live or Reaktor by the user.

Only upgrade a marker with a reference to the test/source.

## Language policy

- Conversation: German or English — follow the user.
- **All artifacts are English:** docs, code comments, identifiers, commit messages, skills,
  rules, TODO entries. Imported reference material stays in its language.

## Safety rules

- **Ears and speakers:** listening tests only with a **limiter after the device** and the
  monitor turned down. Aliasing, FM into filters and feedback can jump to full scale or blow
  up. Development builds end their DSP with a safety stage (`fixnan`/`fixdenorm` + `clip`) —
  see `.claude/rules/gen.md`.
- **Never play audio** on the user's machine (`afplay` etc.) and never drive Live or the
  user's Max session; the user does that. The only exceptions are the unattended standalone-Max
  test run and the Live test harness, under the conditions in "Decisions".
- Do not touch `devices/*/reference/reaktor/` contents (read-only references), the user's Live
  projects, or anything under `~/Music/Ableton` / `~/Documents/Max 9` unless asked.

## Files

| Path | Content |
|---|---|
| `TODO.md` | Open points, open checks in Max/Live, done log — **start here** |
| `README.md` | Overview for outsiders |
| `CLAUDE.md` | This file |
| `devices/<name>/` | One device: `<Name>.amxd` + generated runtime files (flat), `gen/`, `js/src/`, `docs/`, `reference/` |
| `devices/aliasing/` | First device; `reference/reaktor/` = local-only Reaktor originals + screenshots |
| `docs/research/notes/` | Research reports with all URLs. **Search here before researching anew** |
| `docs/handoffs/` | Session handoffs — local only, gitignored; newest is current, never delete |
| `docs/reviews/` | Reports of the `fresh-review` skill — local only, gitignored |
| `tools/check.sh <device>` | Offline check chain: gencheck (Max 9.1.5 + 9.2.0, strict) → regenerate `.gendsp` → TS build → maxdiff parse of every patch. Must pass before every `live-test` handover and commit |
| `tools/setup-git.sh` | Sets the maxdiff textconv drivers in `.git/config` (run once per clone) |
| `tools/max-workspace.sh` | park / restore / check standalone Max's Crash Recovery workspace around unattended runs (otherwise Max reopens the user's last patches) |
| `tools/live/` | **Optional** Live automation (spike, 2026-11-25; off by default): `harness.mjs` = status / install / on / off / run (doctor, relaunch, quit, roundtrip); `check-instrument.mjs` = load an instrument from Places, console from both logs, parameters against the `.amxd`, silent take + health (output `build/<device>/live/`); `README.md` = install + spike checks L1–L6; `local.json` = the switch (gitignored) |
| `tools/` (uv project) | `m4l-analyze` (health check, Welch-PSD distance, `--null`), `m4l-boxref <class>` (real Max-saved box JSON from the local Max/Live installation — ground truth for patch JSON), py2max for test patches; `tools/vendor/` = pinned gencheck + maxdiff (`VENDOR.md`) |
| `reference/` | `m4l-production-guidelines.md`, `patch-code-standard.md` (Ableton), `m4l.md` (compact `live.*` reference); README explains `m4l-boxref` |
| `build/` | gen~ C++ exports, host-test binaries — gitignored |
| `testlog/` | Test logs of the `live-test` skill — local only, gitignored |
| `dist/` | Frozen release builds — local only, gitignored |
| `_tmp/` | User's scratch space; ignored, never delete |
| `.claude/rules/` | `gen.md`, `max-patch.md`, `v8-js.md` — load with matching files |
| `.claude/skills/` | Project skills (see below) |
| `.claude/agents/` | `fresh-reviewer`: read-only subagent of the `fresh-review` skill |

## Conventions

- Python via **uv** (`uv run`, `uv add`); in the sandbox `~/.cache/uv` is not writable:
  `UV_CACHE_DIR=.uv-cache uv run …`.
- Foreign sources as **tarballs from codeload.github.com**, each into its own fresh directory
  (sandboxed `git clone` fails on `.git` writes). Vendored copies record repo + commit.
- `git` and `gh` run outside the sandbox (`excludedCommands`). **Commit and push only after
  the user's explicit approval naming the action**; an "ok" to something else does not count.
  `gh` always with explicit `--repo m9dfukc/…`.
- Before any commit: `git status --short` shows no WAVs, frozen devices, `.ens` files,
  screenshots or anything private beyond the username.
- Tool CLIs: English help texts, arguments instead of hard-coded paths.
- **Shell stays at the repo root** (avoids permission prompts). max-gen-helper's guard hook
  (`guard_user_files.py`, PreToolUse) asks the user whenever a command that writes files names a
  Max file (`.amxd .maxpat .gendsp .genexpr .gen …`, "codebox") outside the session's *current*
  cwd or in a place it cannot resolve. So: no bare `cd` into a subfolder (use `(cd x && …)` or
  absolute paths), Max-file paths written literally rather than via `$VAR`, Max files edited
  with Edit/Write. Auto mode approves everything else here; a hook `ask` overrides it
  [measured: session transcripts 2026-11-25, 5 of 5 Python prompts came from this hook].

## Status (2026-11-25)

- `aliasing` **v0.3b** built (2026-11-25): two faces for an A/B in Live on one DSP (D33–D44 in
  `devices/aliasing/docs/v0.3-design.md`): `Aliasing.amxd` = hybrid, `Aliasing B.amxd` = option (b),
  both from `scripts/bootstrap_shell.py --face hybrid|b`. Dial probe PASS (a `showname 1` dial is 48 px
  whatever the saved rect); offline chain, host test, smoke test (standalone Max 9.2.1) and the Live
  harness (both devices) pass. **Next: test t5 in Live** (§6b there): look and feel of both faces, the
  user picks one. Earlier: 9c23f87 (Write Shape fix, face review), 9b1d5d7 v0.3, …
- Standalone Max **restores its last session's patches at start** (Crash Recovery workspace):
  every unattended run parks that file first (`tools/max-workspace.sh`, user, 2026-11-25).
- Standalone Max is **9.2.1** (Live uses it); jspainter scripts run on Max's legacy JS engine:
  painters must be ES5 (`tools/js-build.mjs` builds `<device>_paint_*.ts` with target es5).
- Unattended standalone-Max runs: `tools/gen-export.sh`, `devices/aliasing/test/smoke/run_smoke.sh
  [hybrid|b]`, `devices/aliasing/test/dial-probe/run_dialprobe.sh` (NonRealTime driver, restores the
  driver and Max's workspace file, reads `Max 9/Logs/Max.log`). Devices' console errors in
  Live land in `~/Library/Application Support/Cycling '74/Max 9/Logs/MaxPlugLib.log`.
- Research (2026-11-24) in `docs/research/notes/`: `m4l-toolchain-dependencies-*`,
  `reaktor-fundamentals-and-porting-*`, `max-port-targets-gen-rnbo-*`, `aliasing-synth-sources-*`,
  `m4l-custom-ui-and-sync-*`, `live-auto-filter-*`.

## Skills and rules (project-local, `.claude/`)

- `reaktor-port` (own): method for porting a Reaktor ensemble — inventory, reference renders,
  signal-flow doc, layer mapping, module-by-module port with offline tests, A/B comparison.
- `live-test` (own): hand a test state to the user (what to load, what to listen for, what to
  report), then write the test log from the user's report. Use it for everything that runs in Max/Live.
- `live-harness` (own): the optional Live automation — status/on/off/install, relaunch Live on an
  empty test Set, `check-instrument.mjs` (load, console, parameters, silent take), quit; runs
  before a `live-test` handover only while switched on.
- `m4l-release` (own): freeze, test in a fresh set, tag and GitHub release.
- `fresh-review` (own): read-only reviewers without this conversation check a document through
  lenses (trace, code, risk, reader) against the project standard; this session consolidates
  and gives its view, the user decides. Use it for decision lists Claude made, build notes
  before a test or release, and handovers the user will execute.
- From `mattpocock/skills` @ `5863806`: `grill-me`/`grilling` (question rounds before design
  decisions — use for every open question to the user), `handoff`, `research` (reports go to
  `docs/research/notes/`).
- Rules: `gen.md` (GenExpr), `max-patch.md` (`.amxd`/`.maxpat`), `v8-js.md` (TS/JS for v8).
