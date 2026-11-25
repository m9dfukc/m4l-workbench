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
  Claude does not drive Max/Live via computer use or MCP. An MCP inspector may come later, on
  the user's request, and only in a separate sandbox device.
- **Exception, standalone Max for unattended tests (user, 2026-11-24, round 2):** Claude may
  launch standalone Max from the command line with a **test patch from this repo** that renders
  with the NonRealTime driver (no sound) or exports gen~ C++, then quits itself. Conditions:
  never Live, never the user's own patches, and only after the user confirmed that no Max with
  unsaved work is open (Max reuses a running instance). Restore the audio driver afterwards.
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
  user's Max session; the user does that. The only exception is the unattended standalone-Max
  test run under the conditions in "Decisions".
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
| `tools/check.sh <device>` | Offline check chain: gencheck (Max 9.1.5 + 9.2.0, strict) → regenerate `.gendsp` → TS build → maxdiff parse of every patch. Must pass before every `live-test` handover and commit |
| `tools/setup-git.sh` | Sets the maxdiff textconv drivers in `.git/config` (run once per clone) |
| `tools/` (uv project) | `m4l-analyze` (health check, Welch-PSD distance, `--null`), `m4l-boxref <class>` (real Max-saved box JSON from the local Max/Live installation — ground truth for patch JSON), py2max for test patches; `tools/vendor/` = pinned gencheck + maxdiff (`VENDOR.md`) |
| `reference/` | `m4l-production-guidelines.md`, `patch-code-standard.md` (Ableton), `m4l.md` (compact `live.*` reference); README explains `m4l-boxref` |
| `build/` | gen~ C++ exports, host-test binaries — gitignored |
| `testlog/` | Test logs of the `live-test` skill — local only, gitignored |
| `dist/` | Frozen release builds — local only, gitignored |
| `_tmp/` | User's scratch space; ignored, never delete |
| `.claude/rules/` | `gen.md`, `max-patch.md`, `v8-js.md` — load with matching files |
| `.claude/skills/` | Project skills (see below) |

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

## Status (2026-11-25)

- `aliasing` **v0.2** built (unattended session 2026-11-25): DSP, painted face, display, shell;
  offline chain, host test, smoke test in standalone Max 9.2.1 all pass. **Not yet loaded in Live**
  (next: test t3, `devices/aliasing/docs/v0.2-build.md` §6) and its decisions A1–A33 are to be
  reviewed with the user. Local commits only (a3f0466 v0.1b, 002b2da DSP, f725478 face, …).
- Standalone Max is **9.2.1** (Live uses it); jspainter scripts run on Max's legacy JS engine:
  painters must be ES5 (`tools/js-build.mjs` builds `<device>_paint_*.ts` with target es5).
- Unattended standalone-Max runs: `tools/gen-export.sh`, `devices/aliasing/test/smoke/run_smoke.sh`
  (NonRealTime driver, restores the driver, reads `Max 9/Logs/Max.log`). Devices' console errors in
  Live land in `~/Library/Application Support/Cycling '74/Max 9/Logs/MaxPlugLib.log`.
- Research (2026-11-24) in `docs/research/notes/`: `m4l-toolchain-dependencies-*`,
  `reaktor-fundamentals-and-porting-*`, `max-port-targets-gen-rnbo-*`, `aliasing-synth-sources-*`,
  `m4l-custom-ui-and-sync-*`, `live-auto-filter-*`.

## Skills and rules (project-local, `.claude/`)

- `reaktor-port` (own): method for porting a Reaktor ensemble — inventory, reference renders,
  signal-flow doc, layer mapping, module-by-module port with offline tests, A/B comparison.
- `live-test` (own): hand a test state to the user (what to load, what to listen for, what to
  report), then write the test log from the user's report. Use it for everything that runs in Max/Live.
- `m4l-release` (own): freeze, test in a fresh set, tag and GitHub release.
- From `mattpocock/skills` @ `5863806`: `grill-me`/`grilling` (question rounds before design
  decisions — use for every open question to the user), `handoff`, `research` (reports go to
  `docs/research/notes/`).
- Rules: `gen.md` (GenExpr), `max-patch.md` (`.amxd`/`.maxpat`), `v8-js.md` (TS/JS for v8).
