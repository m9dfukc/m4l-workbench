# m4l-workbench — Max for Live devices, built code-first

Workbench for the user's own **Max for Live (M4L) devices**, built with Claude Code. Some devices
are **ports of Native Instruments Reaktor ensembles**; others are original designs. Goals, in this order:

1. **Workbench:** a reproducible, text-first way to build M4L devices: DSP as GenExpr text,
   logic as TypeScript → v8 JavaScript, the `.amxd` as a thin, diffable shell. Offline checks
   before anything is loaded in Max or Live.
2. **First device: `aliasing`** (`devices/aliasing/`), begun as a port and since v0.3 an **original
   design inspired by** the Reaktor User Library ensemble **aliasing Synth** by D. Pank (user,
   2026-11-26: name the author only as "D. Pank"; no author contact before releases). An audio table
   is written and read at different ("careless") speeds; the resulting errors are the sound. 5 voices.
3. Further devices later, each in its own `devices/<name>/` folder.

## Environment (checked 2026-11-24, Max version 2026-11-26)

- **Max 9.2.1** standalone at `/Applications/Max.app` (full licence: Gen/MC authoring and gen~
  code export need it). Refpages: `/Applications/Max.app/Contents/Resources/C74/docs/refpages/`
  (`*.maxref.xml`), the local ground truth for object names, inlets, outlets, attributes. Gen
  examples: `/Applications/Max.app/Contents/Resources/Examples/gen/`.
- **Ableton Live 12 Suite 12.4.16**. Its bundled Max is **9.1.5**, but development runs the
  standalone Max in Live too (Live Settings → File & Folder → Max Application; confirm with the
  `Max: Version …` line in Live's log). **Released devices must still run on stock Live's 9.1.5:**
  GenExpr passes gencheck for 9.1.5 and 9.2.0 (`tools/check.sh`), and the bundled-Max round in
  Live happens before a release.
- **Logs** (read-only; read them after a user test instead of asking for a console copy where
  that is enough): Live's `~/Library/Preferences/Ableton/Live <version>/Log.txt` (`Message from
  Max: …`; stock devices log unrelated "incorrect architecture" errors, filter by device name);
  console lines of devices in Live in `~/Library/Application Support/Cycling '74/Max 9/Logs/MaxPlugLib.log`;
  standalone Max in `Max.log` next to it.
- **Reaktor 6.5.2** (for reference renders of the originals; no CLI).
- Node v26 (nvm), pnpm, tsc 5.9, esbuild; Python 3.14 via **uv**; Apple clang 21, cmake; git, gh.

## Decisions (user)

- **Repo:** this directory, public on GitHub as **`m9dfukc/m4l-workbench`** (remote `origin`,
  branch `main`, MIT). Monorepo: one folder per device under `devices/<name>/`; no submodules.
- **Third-party Reaktor material stays local:** `.ens` files and screenshots live in
  `devices/<name>/reference/reaktor/` (gitignored, provenance + SHA-256 in the committed
  README there). Only our own analyses, code and recordings of our own devices go into git.
- **Roles:** the **user operates Max and Live**: loads devices, listens, reads the Max
  console and reports back. Claude builds, runs the offline checks and keeps the test logs.
  Claude does not drive Max/Live via computer use or MCP, apart from the two exceptions below.
  An MCP inspector may come later, on the user's request, and only in a separate sandbox device
  (no Max MCP so far; `docs/research/notes/live-automation-mcp-2026-11-25.md`).
- **Exception, standalone Max for unattended tests (user, 2026-11-24):** Claude may launch
  standalone Max from the command line with a **test patch from this repo** that renders with
  the NonRealTime driver (no sound) or exports gen~ C++, then quits itself. Conditions: never
  Live, never the user's own patches, and only after the user confirmed that no Max with
  unsaved work is open (Max reuses a running instance). Restore the audio driver afterwards.
  Max reopens its last session's patches at start (Crash Recovery workspace): every run parks
  that file first and restores it afterwards (`tools/max-workspace.sh park|restore|clean`). The
  existing runners do all of this: `tools/gen-export.sh`, `devices/<name>/test/*/run_*.sh`.
- **Exception, Live test harness (user, 2026-11-25) — optional, only while switched on:** the
  Live automation is **off by default** (no `tools/live/local.json`); the user switches it with
  `node tools/live/harness.mjs on|off`, and the scripts refuse to touch Live while it is off
  (then every Live test is a `live-test` handover). While on, Claude may run the pinned
  `eladefrati/ableton-live-test-harness` and the checks in `tools/live/` on the harness's empty
  Set: procedure in the `live-harness` skill, setup in `tools/live/README.md`. Conditions: ask
  the user whether Live is free (a relaunch **discards unsaved work**) before the first relaunch
  of a session and whenever the doctor says the open Set was not started by the harness; never
  the user's own Sets or templates; recordings only from the device track's Post FX with that
  track at −inf and the recording track's monitoring Off (the checks enforce it); no real mouse clicks (`device-ui.js`) and no window
  captures unless the user asks; the harness stays at the pinned commit until a new one has
  been read. Listening, A/B against Reaktor, the bundled-Max round and the freeze stay with
  the user.
- **Reaktor file parsing** is allowed (user, 2026-11-24): a read-only parser for `.ens`/`.ism`
  lives **only locally** in `tools/local/` (gitignored, never committed or published — NI has
  enforced its EULA against a public parser). Its findings go into `devices/<name>/docs/`
  marked `[observed: parser]`.
- **Languages/tools:** control logic in TypeScript, bundled by esbuild to CommonJS for `v8`
  (`tools/js-build.mjs`); Python tools (analysis, null tests, spectra) as a uv project in
  `tools/`. max-gen-helper is installed as a Claude Code plugin (skill `gen-pitfalls` + guard
  hook); scripts use the vendored gencheck.
- **Open questions to the user** go through the `grilling` skill (question rounds with a
  recommended answer each), not one by one in passing.

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

### Device README

Every device has a user-facing `devices/<name>/README.md` with a fixed structure (images, what
it does, install, faces, generated parameter blocks, status, credits, developer part). The
convention is the rule `.claude/rules/device-readme.md`; it loads with the device READMEs.

## Evidence markers (all docs)

- **[sourced]**: an external source exists (docs, repo, forum), linked.
- **[code]**: derived from our code or a generator's output, not yet run in Max/Live.
- **[hypothesis]**: conclusion, untested.
- **[measured]**: confirmed or refuted in Max/Live or by an offline measurement, with a
  reference to the test log or the script output.
- **[open]**: must be checked in Max, Live or Reaktor by the user.

Only upgrade a marker with a reference to the test/source. A document may define extra markers
at its top (port documents: `[observed: parser]`, `[observed: <screenshot>]`).

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
| `devices/<name>/` | One device: `<Name>.amxd` + generated runtime files (flat), `README.md` (user-facing), `CHANGELOG.md`, `gen/`, `js/src/`, `scripts/` (shell generator + checks), `test/`, `docs/` (`img/` = README images), `reference/` |
| `docs/research/notes/` | Research reports with all URLs. **Search here before researching anew** |
| `docs/handoffs/` | Session handoffs — local only, gitignored; newest is current, never delete |
| `docs/reviews/` | Reports of the `fresh-review` skill — local only, gitignored |
| `tools/check.sh <device>` | Offline check chain: gencheck (Max 9.1.5 + 9.2.0, strict) → regenerate `.gendsp` → TS build → maxdiff parse of every patch → device `scripts/check_*.py` → README parameter blocks (`tools/readme_params.py`). Must pass before every `live-test` handover and commit |
| `tools/setup-git.sh` | Sets the maxdiff textconv drivers in `.git/config` (run once per clone) |
| `tools/live/` | **Optional** Live automation (off by default): `harness.mjs`, `check-instrument.mjs` (output in `build/<device>/live/`), `README.md` = install; `local.json` = the switch (gitignored) |
| `tools/` (uv project) | `m4l-analyze` (health check, Welch-PSD distance, `--null`), `m4l-boxref <class>` (real Max-saved box JSON from the local Max/Live installation — ground truth for patch JSON), py2max for test patches; `tools/vendor/` = pinned gencheck + maxdiff (`VENDOR.md`) |
| `reference/` | `m4l-production-guidelines.md`, `patch-code-standard.md` (Ableton), `m4l.md` (compact `live.*` reference) |
| `build/`, `dist/`, `testlog/` | gen~ exports and test output; frozen release builds; test logs of the `live-test` skill — all local only, gitignored |
| `_tmp/` | User's scratch space; ignored, never delete |
| `.claude/` | `rules/` (`gen.md`, `max-patch.md`, `v8-js.md`, `device-readme.md`, loaded by path), `skills/` (own: `live-test`, `live-harness`, `reaktor-port`, `m4l-release`, `fresh-review`; from `mattpocock/skills` @ `5863806`: `grill-me`/`grilling`, `research`, `handoff` — the last adapted to save in `docs/handoffs/`), `agents/fresh-reviewer.md` |

## Conventions

- Python via **uv** (`uv run`, `uv add`); in the sandbox `~/.cache/uv` is not writable:
  `UV_CACHE_DIR=.uv-cache uv run …`.
- Foreign sources as **tarballs from codeload.github.com**, each into its own fresh directory
  (sandboxed `git clone` fails on `.git` writes). Vendored copies record repo + commit.
- `git` and `gh` run outside the sandbox (`excludedCommands`). **Commit and push only after
  the user's explicit approval naming the action**; an "ok" to something else does not count.
  `gh` always with explicit `--repo m9dfukc/…`.
- Before any commit: `git status --short` shows no WAVs, frozen devices, `.ens` files,
  third-party screenshots (Reaktor material stays in `devices/*/reference/reaktor/`) or anything
  private beyond the username. Images of our own devices are committed only as README images in
  `devices/<name>/docs/img/`.
- Tool CLIs: English help texts, arguments instead of hard-coded paths.
- **Shell stays at the repo root** (avoids permission prompts). max-gen-helper's guard hook
  asks the user whenever a command that writes files names a Max file (`.amxd .maxpat .gendsp
  .genexpr .gen …`, "codebox") outside the session's *current* cwd or in a place it cannot
  resolve. So: no bare `cd` into a subfolder (use `(cd x && …)` or absolute paths), Max-file
  paths written literally rather than via `$VAR`, Max files edited with Edit/Write.

## Status (2026-11-26)

Only the version and the next step live here; everything else (open items, open checks, done
log) is in `TODO.md`.

- **`aliasing` 0.3.0-beta.1** released 2026-11-26 as a GitHub pre-release (tag
  `aliasing-v0.3.0-beta.1`): two faces on one DSP, `Aliasing.amxd` ("Aliasing A") and
  `Aliasing B.amxd` ("Aliasing B"). Design: `devices/aliasing/docs/v0.3-design.md`; changes:
  `devices/aliasing/CHANGELOG.md`.
- **Next:** tests t5 and t6 in Live (the user picks the face for 1.0; real sample drags).
