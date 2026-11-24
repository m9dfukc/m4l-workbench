# M4L workbench: toolchain and dependencies (state 2026-11-24)

Research note for the code-first Max for Live workbench. Starting point: the German guide
`Max for Live mit Claude bauen.md` (repo root, tool data as of 2026-11-19). First device: a port of the
Reaktor "Aliasing Synth" (5 voices, an audio table written and read at different speeds, HP+FM, LP+FM,
notch), so the device is an **instrument** (MIDI in, up to 5 voices).

**Evidence markers:** **[sourced]** = read in the linked source (for Max docs: the local copy shipped
with Max 9.2.0 under `/Applications/Max.app/Contents/Resources/C74/docs/`, which mirrors
docs.cycling74.com); **[inference]** = derived, not stated by a source; **[untested]** = command not run
for this note; **[open]** = must be checked in Max/Live by the user. Repo metadata (stars, push dates,
licences, commit hashes) come from the GitHub REST API on 2026-11-24; package versions from PyPI and the
npm registry on the same day. Nothing was installed for this note.

## Summary and recommendation

The guide's three-layer architecture holds up, with three corrections and one big addition. The
corrections: (1) maxdiff uses **three** diff drivers (`maxpat`, `amxd`, `als`), not `diff=maxdiff` as the
guide sketches; (2) `m4l-typescript-base` is not an esbuild/v8 template but a **tsc → ES5 legacy `js`**
template under **GPL-3.0**, so we take ideas from it, not code; (3) **Live 12.4.16 is currently running
the bundled Max 9.1.5** (seen in Live's own log), and switching it to Max 9.2 is a single setting
(Settings → File & Folder → Max Application, restart), but that also means the device must stay
compatible with 9.1.5 for anyone using stock Live. The addition: Claude can verify DSP **without the
user's ears** in two fully scripted loops. (a) The exported C++ of the voice `gen~` patcher
(`exportcode`/`autoexport`) can be compiled with the local clang into a host harness and fed with
stimulus files. (b) Max standalone can render faster than real time with the **NonRealTime** audio
driver plus `sfrecord~`, launched from the command line and quit by `; max quit`. Comparison happens in
Python (numpy/scipy/soundfile/matplotlib). The gen~ → C++ step needs Max running (no headless Max
exists), but no clicks if the test patch triggers `exportcode` itself. **Recommendation:** set up now
gencheck (plugin + vendored script), maxdiff (vendored), the Production Guidelines (vendored), the
Python analysis set, and the gen-export host harness. Add TypeScript/esbuild only when the device gets
real control logic (for v1 the voice allocation can be done by Max objects). Postpone every MCP server
and the Live-side test harness until a device exists.

## Dependency overview

| Dependency | Purpose | Required now / later / optional | Install method | Version / last activity | Licence | Source |
|---|---|---|---|---|---|---|
| Max 9.2.0 standalone | Authoring, gen~ export, NRT renders | now (present) | installed | 9.2.0 (e9c80e453de) | proprietary | local `Info.plist` |
| Live 12.4.16 Suite + bundled Max 9.1.5 | Target host | now (present) | installed | 12.4.16 / Max 9.1.5 (3db35fa476d) | proprietary | local `Info.plist`, Live `Log.txt` |
| mforhm/max-gen-helper (skill `gen-pitfalls`, `gencheck`, guard hook) | Static GenExpr check, `.genexpr` → `.gendsp` | **now** | Claude Code plugin **and** vendor `scripts/gencheck/{gencheck,genflow}.py` | v0.1.2, commit `a7a05a72` (2026-10-14), 0 stars | MIT | [repo](https://github.com/mforhm/max-gen-helper) |
| Ableton/maxdevtools `maxdiff/` | git textconv for `.amxd`/`.maxpat`/`.als` | **now** | vendor `maxdiff/` (stdlib Python ≥ 3.10) | commit `5b39dec9` (2026-09-11), 385 stars | MIT | [repo](https://github.com/Ableton/maxdevtools) |
| M4L Production Guidelines | Parameter/release checklist | **now** (reference) | vendor the `.md` | same commit | MIT | [guidelines](https://github.com/Ableton/maxdevtools/blob/main/m4l-production-guidelines/m4l-production-guidelines.md) |
| numpy / scipy / soundfile / matplotlib | Null tests, spectra, plots | **now** | `uv add` (dev group) | 2.5.5 / 1.18.1 / 0.14.0 / 3.11.2, all with Python 3.14 arm64 wheels | BSD / BSD / BSD / PSF-style | PyPI |
| clang++ (Command Line Tools) | Build the gen~ export host harness | **now** (present) | installed | Apple clang 21.0.0; cmake 4.5.0 also present | – | local |
| `gen~` code export (built into Max) | C++ of the DSP for host tests | **now** | none (needs full Max licence: [sourced](https://docs.cycling74.com/userguide/m4l/live_limitations/)) | Max 9.2.0 | exported-code licence: see §4 [open] | local refpage `gen~.maxref.xml` |
| shakfu/py2max | Generate the standalone test patch, `py2max validate`, read `.amxd` | now (dev) | `uv add --dev py2max==0.6.0` | 0.6.0 (2026-10-11), commit `f0e29874` | MIT | [repo](https://github.com/shakfu/py2max), [PyPI](https://pypi.org/project/py2max/) |
| ssdvtechno `references/m4l.md` | Compact M4L/`live.*` port table | now (reference) | vendor one file | commit `a132b5b5` (2026-10-07) | MIT | [file](https://github.com/ssdvtechno/maxpylang-claude-plugin/blob/main/skills/maxpylang/references/m4l.md) |
| jpdrecourt/maxpat-render | PNG of patches for vision checks | optional (later) | `uv add --dev` from git, pinned | commit `cb8b9088` (2026-07-29), 0 stars; Python ≥ 3.10, deps py2max + resvg_py | MIT | [repo](https://github.com/jpdrecourt/maxpat-render) |
| Node + pnpm + esbuild + TypeScript + `@types/maxmsp` | v8 logic from TS | later | `pnpm add -D` (project-local) | Node 26.13 present; esbuild 0.28.2 (2026-08-08); TS latest 7.0.2, local tsc 5.9.3; `@types/maxmsp` 1.0.16 (2026-10-21) | MIT / Apache-2.0 / MIT | npm registry |
| python-osc | Drive a running Max via its integrated OSC server | later | `uv add --dev python-osc` | 1.10.3 (2026-11-15) | Unlicense | PyPI |
| mikecfisher/ableton-lom-skill | LOM reference skill (Live 12.3) | later (only if Live API is used) | `npx skills add mikecfisher/ableton-lom-skill` | commit `7c7d1895` (2026-05-22), 24 stars | README says MIT, **no LICENSE file** | [repo](https://github.com/mikecfisher/ableton-lom-skill) |
| isabelgk/gen-fmt | GenExpr formatter | optional | release binary (Gatekeeper `xattr`) | v0.1.0-alpha3 (2026-03-04) | **no LICENSE file**; source build depends on `isabelgk/tree-sitter-genexpr`, which returns 404 | [repo](https://github.com/isabelgk/gen-fmt) |
| pdmeyer/GenExpr_VSCode | Syntax highlighting | optional | VS Code extension (marketplace listing not verified) | 0.0.1, last push 2025-09-17 | **no LICENSE file** | [repo](https://github.com/pdmeyer/GenExpr_VSCode) |
| zsteinkamp/m4l-typescript-base | TS template (ideas only) | no | do not adopt | commit `813d0612` (2026-08-11), 39 stars | **GPL-3.0** (LICENSE) vs "MIT" in package.json | [repo](https://github.com/zsteinkamp/m4l-typescript-base) |
| codebrain/m4l-builder | Python `.amxd` builder | optional / not needed | `uv add --dev m4l-builder==0.7.0` | PyPI 0.7.0 (2026-03-04); repo HEAD says 0.8.0 (`f3c480d7`, 2026-07-13) | MIT | [repo](https://github.com/codebrain/m4l-builder) |
| Cycling74/gen-plugin-export | Reference for the export API | reference only | none | last push 2025-07-14, 242 stars | MIT (C74 part; JUCE separate) | [repo](https://github.com/Cycling74/gen-plugin-export) |
| RNBO | Alternative export path | not for v1 | bundled in `Max.app/.../packages/RNBO` | 1.4.5 | add-on licence | local `package-info.json` |
| eladefrati/ableton-live-test-harness | Automated in-Live checks | later | git clone + symlink as Remote Script | commit `ad756c1e` (2026-11-23), 0 stars | MIT | [repo](https://github.com/eladefrati/ableton-live-test-harness) |
| bschoepke/ableton-live-mcp (Agent Audio Tap) | Capture audio inside Live | optional (later) | per README (agent-driven) | commit `89f3b4ef` (2026-10-06), 238 stars | MIT | [repo](https://github.com/bschoepke/ableton-live-mcp) |
| adamjmurray/producer-pal | Live MCP / REST as `.amxd` | optional | download `Producer_Pal.amxd` | v2.5.0 (2026-10-28), v2.6.0-rc1 (2026-11-17), 390 stars | MIT | [repo](https://github.com/adamjmurray/producer-pal) |
| ulm0/ableton-live-mcp | Live Extension MCP, `render_track_audio` | optional | npm + Extension Host | commit `29d3ca64` (2026-11-07), 1 star | MIT | [repo](https://github.com/ulm0/ableton-live-mcp) |
| ersatzben/maxmsp-mcp (+ miravassor fork) | Max inspector MCP | optional (later) | git + `claude mcp add` | ersatzben `ff70f6ab` (2026-07-10); miravassor 37 ahead / 2 behind | MIT | [ersatzben](https://github.com/ersatzben/maxmsp-mcp), [miravassor](https://github.com/miravassor/maxmsp-mcp-fork) |
| librosa | MIR features | not needed | – | 1.0.1 (2026-11-12), pulls numba | ISC | PyPI |

## 1. Core tools: status, install, licence, vendor vs install, fit

### 1.1 mforhm/max-gen-helper (gencheck, gen-pitfalls) — keep, core

- Status: v0.1.2, last commit `a7a05a72` "0.1.2: docs checked against the code" on 2026-10-14; MIT;
  0 stars [sourced: GitHub API, `.claude-plugin/plugin.json`]. Rules measured in Max 9.1.4 and 9.2.0,
  round 22 also in **9.1.5** (the Max inside Live 12) [sourced:
  [README](https://github.com/mforhm/max-gen-helper/blob/main/README.md)].
- Plugin install (from the README) [sourced, untested]:
  ```
  /plugin marketplace add mforhm/max-gen-helper
  /plugin install max-gen-helper@mforhm
  ```
  The marketplace is named `mforhm`, the plugin `max-gen-helper` [sourced: `.claude-plugin/marketplace.json`].
  CLI form, analogous to the ssdvtechno README's `claude plugin marketplace add …` [untested]:
  `claude plugin marketplace add mforhm/max-gen-helper && claude plugin install max-gen-helper@mforhm`.
  Local try-out: `claude --plugin-dir path/to/max-gen-helper` [sourced].
- The plugin also installs a **PreToolUse hook** (`hooks/guard_user_files.py`, matcher
  `Edit|Write|MultiEdit|NotebookEdit|Bash|mcp__terminal__run_in_terminal`) that asks before Claude changes
  Max files (`.maxpat`, `.amxd`, `.gendsp`, `.genexpr`, …) **outside the folder Claude was started in**
  [sourced: `hooks/hooks.json`, README]. That fits our "everything inside the repo" rule; it will prompt
  for writes into `~/Music/Ableton/User Library` [inference].
- Logging: when the skill runs gencheck it passes `--log` and appends one line (no code, no file names) to
  `~/.claude/plugins/data/<plugin id>/gencheck-log.jsonl`; nothing is sent anywhere [sourced].
- **gencheck CLI** (from the source docstring of `gencheck.py` at `a7a05a72`) [sourced]:
  ```
  usage: gencheck.py [options] FILE...
    --old OLD              older version of the same codebox (G302 name collisions)
    --io NIN NOUT          expected inlet/outlet counts (G504)
    --strict               warnings also give exit code 1
    --info                 list info findings
    --json                 findings as JSON
    --gen-ref DIR          Gen refpages folder (default: Max install, or $GENCHECK_GEN_REF)
    --max-version V        judge as Max version V (default: the Max started last, read from
                           ~/Library/Application Support/Cycling '74/Max 9/Logs; $GENCHECK_MAX_LOGS)
    --gen-path DIR         extra folder with *.gendsp abstractions and require() *.genexpr libraries
    --param NAME           a [param] box of the gen patcher (repeatable); --complete-params
    --max-per-rule N       default 5, 0 = all
    --write-gendsp OUT.gendsp   with ONE codebox text file and no error: also write a gen patcher
                           (codebox wired to in/out) to use as [gen~ @gen OUT];
                           a .gendsp gencheck did not write is kept
    --log FILE / --log-mismatch TEXT / --log-code / --log-summary / --log-mark-sent
  exit: 0 ok, 1 error (or warn with --strict), 2 usage/unreadable file, 3 gencheck failed
  ```
  Example for us [untested]:
  `python3 tools/vendor/gencheck/gencheck.py --max-version 9.1.5 --strict --write-gendsp devices/aliasing/aliasvoice.gendsp gen/aliasvoice.genexpr`
- Pitfall for our setup: by default gencheck judges by **the Max started last**, read from Max's log
  folder; the Live-hosted Max writes its own log there too (`MaxPlugLib.log` shows "Max is starting:
  Version 9.1.5") [sourced: local logs]. Alternating between Live and Max 9.2 would silently change the
  verdict, so **always pass `--max-version`** and run both `9.1.5` and `9.2.0` while Live is on the
  bundled Max [inference]. gencheck judges 9.1.5 by the 9.1.4 rules [sourced: README].
- Open `[gen~ @gen name]` picks up a new `.gendsp` by itself — **measured on Max 9.2.0 only**
  [sourced: README]. Whether the 9.1.5 inside Live does the same is [open].
- Vendor vs install: install the **plugin** (skill + hook, Claude-facing). Additionally **vendor**
  `scripts/gencheck/gencheck.py` + `genflow.py` (stdlib only, MIT) pinned at `a7a05a72` into
  `tools/vendor/gencheck/` so scripts and CI call a fixed version and the path does not depend on
  `~/.claude/plugins` [inference]. gencheck reads the Gen operator list from the Max install
  (`C74/packages/Gen/docs/refpages`); without Max (CI) it skips some checks and says so [sourced].
- Fit: excellent; it is the only tool here with measured rules.

### 1.2 Ableton/maxdevtools: maxdiff — keep, core (guide's setup was wrong)

- Status: MIT, 385 stars, last commit `5b39dec9` (2026-09-11) [sourced: GitHub API]. `maxdiff/*.py` import
  only the stdlib plus sibling modules (`patch_printer`, `print_unicode`, `frozen_device_printer`)
  [sourced: source]. Requires **Python ≥ 3.10** as `python3` [sourced:
  [maxdiff README](https://github.com/Ableton/maxdevtools/blob/main/maxdiff/README.md)].
- **Exact setup from the README** [sourced]:
  `.gitattributes`
  ```text
  *.maxpat              diff=maxpat
  *.amxd                diff=amxd
  *.als                 diff=als
  ```
  `.git/config`
  ```text
  [diff "maxpat"]
    textconv = python3 ~/maxdevtools/maxdiff/maxpat_textconv.py
  [diff "amxd"]
    textconv = python3 ~/maxdevtools/maxdiff/amxd_textconv.py
    binary = true
  [diff "als"]
   textconv = python3 ~/maxdevtools/maxdiff/als_textconv.py
   binary = true
  ```
  The guide's sketch (`*.amxd diff=maxdiff`) does not match this.
- Workbench variant with a vendored copy (git config is not versioned, so ship a setup script)
  [untested; relative path assumes git runs textconv from the work-tree root — inference]:
  ```bash
  git config diff.maxpat.textconv "python3 tools/vendor/maxdevtools/maxdiff/maxpat_textconv.py"
  git config diff.amxd.textconv   "python3 tools/vendor/maxdevtools/maxdiff/amxd_textconv.py"
  git config diff.amxd.binary true
  git config diff.als.textconv    "python3 tools/vendor/maxdevtools/maxdiff/als_textconv.py"
  git config diff.als.binary true
  ```
  `.gendsp` is patcher JSON as well; `*.gendsp diff=maxpat` probably works but is [untested]. Since our
  `.gendsp` files are generated, marking them `linguist-generated` is enough [inference].
- Manual check: `python3 ./maxdiff/amxd_textconv.py <device.amxd>` [sourced].
- maxdiff shows frozen-device statistics; Ableton recommends **never committing frozen devices**
  [sourced].
- Vendor: copy `maxdiff/` without `tests/` and `m4l-production-guidelines/m4l-production-guidelines.md`
  (+ `patch-code-standard/patch-code-standard.md` if wanted), document the source commit [inference].

### 1.3 M4L Production Guidelines — vendor as reference

Highlights relevant for an instrument [sourced: guidelines]: freeze before sharing, keep developing from
the unfrozen version; `---` prefix makes `send`/`buffer~`/`coll` names device-local; Long Name is
the identity Live uses for parameter recall ("avoid changing the Long Name … when updating the device");
modulation mode Bipolar for Float, Absolute for Int; Int type is limited to 0–255; parameters driven from
inside the patch must be **Hidden** or they flood Live's undo history; initialise with `trigger`, not
`delay`/`deferlow`; "Render consistency: The device sounds identical on playback, on a frozen track, and on
rendering an audio file"; "Sample rate consistency" check; MPE checklist item is for MIDI devices
(`is_mpe`). The final checklist is a ready-made release checklist.

### 1.4 shakfu/py2max — use for the test patch, not as source of truth for the device

- PyPI 0.6.0 (2026-10-11), MIT, no runtime deps, `requires_python >= 3.9` [sourced: PyPI]. Reads/writes
  `.amxd` (`device_type`: `audio_effect`, `instrument`, `midi_effect`), claims "byte-for-byte compatible
  with Max-exported devices"; CLI `py2max new|info|preview|optimize|validate`; `add_gen_codebox()`
  [sourced: [README](https://github.com/shakfu/py2max)].
- Caveat [sourced: README "Caveats"]: Max 9.2.0+ reloads an open patch when the file changes on disk;
  "Unsaved edits made in Max are discarded without a prompt"; only in-place writes trigger the reload.
- Counter-evidence for generated instrument containers: bschoepke's AGENTS.md says to preserve Ableton's
  role-specific AMXD wrappers from Live's blank templates, "Do not hand-roll a generic AMXD container for
  instruments … Live can load it as an audio effect, leaving MIDI synth tracks silent" [sourced:
  [AGENTS.md](https://github.com/bschoepke/ableton-live-mcp/blob/main/AGENTS.md)].
- Ground truth on this machine: `/Applications/Ableton Live 12 Suite.app/Contents/App-Resources/Misc/Max Devices/Max Instrument.amxd`
  (3800 bytes; header `ampf` + type `iiii`, then `meta`, `ptch` + plain patcher JSON with `midiin` and
  `plugout~`, saved by Max 8.1.2) [sourced: read locally].
- Install [untested]: `UV_CACHE_DIR=.uv-cache uv add --dev py2max==0.6.0`.
- Fit: use it to **generate the standalone NRT test patch** (`.maxpat`) and to validate/inspect. Build the
  device shell by copying Live's `Max Instrument.amxd` template and editing it once in Max [inference].

### 1.5 codebrain/m4l-builder — not needed

PyPI 0.7.0 (2026-03-04), MIT; the PyPI project URL points to `alaarab/m4l-builder`, which the GitHub API
reports as Not Found; code lives at `codebrain/m4l-builder` (HEAD `pyproject.toml` says 0.8.0, unreleased)
[sourced]. `Instrument` exists but "Instruments and MIDI effects leave I/O to you"; writes into the User
Library by default [sourced: README]. Overlaps with py2max; skip for v1 [inference].

### 1.6 jpdrecourt/maxpat-render — optional

MIT, commit `cb8b9088` (2026-07-29), Python ≥ 3.10, deps `py2max`, `resvg_py`; CLI
`maxpat-render file.maxpat -o out [--zoom 2.0 --no-ids --no-subpatchers --svg --tile-px 4000]`; handles
`.amxd`; **presentation mode is not rendered**; ships `skills/maxpat-render/SKILL.md` [sourced:
[README](https://github.com/jpdrecourt/maxpat-render)]. Install [untested]:
`UV_CACHE_DIR=.uv-cache uv add --dev "maxpat-render @ git+https://github.com/jpdrecourt/maxpat-render@cb8b9088"`.
Vendor the skill folder into `.claude/skills/` if wanted (MIT). Fit: nice for reviewing a 10–20 box
shell; low priority.

### 1.7 isabelgk/gen-fmt — optional, do not vendor

Formatter built on Topiary + tree-sitter-genexpr; `gen-fmt -i file.genexpr`; latest release
`v0.1.0-alpha3` (2026-03-04) with macOS arm64 binaries; downloaded binaries need
`xattr -d com.apple.quarantine gen-fmt` [sourced: README, releases API]. No LICENSE file (GitHub reports
none). `Cargo.toml` pulls `tree-sitter-genexpr` from `github.com/isabelgk/tree-sitter-genexpr`, which the
API reports as Not Found, so `cargo install --path .` will likely fail [sourced/inference]. The only
public grammar found is `sadguitarius/tree-sitter-genexpr` (MIT, 2026-10-09) [sourced: GitHub search].
Fit: cosmetic; skip until licence and build are clarified.

### 1.8 pdmeyer/GenExpr_VSCode — optional

Syntax highlighting + snippets for `.genexpr`/`.gendsp`; `package.json` version 0.0.1 with
`"publisher": "your-publisher-id"`, last push 2025-09-17, no LICENSE file [sourced]. Whether it is really
on the VS Code Marketplace is [open]. Irrelevant for Claude; nice-to-have for the user.

### 1.9 mikecfisher/ableton-lom-skill — later

Covers the Live 12.3.x LOM (45 objects incl. `this_device`), install `npx skills add mikecfisher/ableton-lom-skill`
[sourced: README]. README says MIT but there is no LICENSE file → install, don't vendor. Not needed while
the instrument does not use the Live API [inference].

### 1.10 zsteinkamp/m4l-typescript-base — ideas only

Uses **Docker + VS Code devcontainer**, `tsc --watch` (not esbuild), `tsconfig` `target: es5`,
`lib: ["es5"]`, `module: CommonJS`, outDir `Project/`, `@types/maxmsp ^1.0.12`, and the hack
`const module = {}; export = {}` at the end of every entry `.ts` "so that tsc generates valid JS for
Max" — i.e. it targets the legacy `js` object, not `v8` [sourced: repo files at `813d0612`]. The repo
LICENSE is **GPL-3.0** while `package.json` says MIT [sourced]. The author's newer device Knobbler4 also
uses tsc/ES5 for Max code and esbuild only for a `node.script` part [sourced:
[package.json](https://github.com/zsteinkamp/m4l-Knobbler4/blob/main/package.json)]. Fit: do not adopt;
our own 20-line setup is simpler (§3).

### 1.11 ssdvtechno `references/m4l.md` — vendor one file

MIT, commit `a132b5b5` (2026-10-07). Gives device-type I/O (`instrument`: `notein` or `midiin → midiparse`
in, `plugout~` out), `.amxd` layout (`ampf` chunk, `meta`, `ptch` JSON), the
`saved_attribute_attributes.valueof` keys of `live.*` parameters, and inlet/outlet counts of `live.*`
objects "checked against real Max-saved patches on GitHub" [sourced]. The plugin itself says generated
`gen~` boxes and device faces "have not been opened in Max yet" [sourced: README]. Vendor
`m4l.md` only; skip the plugin.

## 2. Which Max does Live use, and what 9.2 changes for gen~

- **Measured on this machine:** Live's log shows `info: Max: Version 9.1.5 (3db35fa476d)` at every start
  (2026-11-03, 2026-11-19) [sourced: `~/Library/Preferences/Ableton/Live 12.4.15/Log.txt`]; the bundled
  `Max.app` inside Live 12.4.16 is 9.1.5, the standalone is 9.2.0 [sourced: `Info.plist`s]. Note: there is
  no `Live 12.4.16` preferences folder yet, the newest is `Live 12.4.15`.
- **How to switch** [sourced: Ableton help "Using a separate Max for Live installation", updated
  2026-10-21, https://help.ableton.com/hc/en-us/articles/209070309]: "Open Live's Preferences → File Folder
  → Max Application. Click Browse, locate the standalone version of Max, then click Open. Restart Live."
  (In Live 12 the window is called Settings → File & Folder.) The article names no separate "use bundled
  Max" toggle. "Recommended Max versions" (updated 2026-02-03) says Live 12 bundles Max 9 and you may
  install a standalone Max 9 [sourced: https://help.ableton.com/hc/en-us/articles/209772305]. No source
  states that Max 9.2 is officially supported in Live 12.4 → [open].
- **Gen changes in 9.2.0** [sourced: [Max 9.2.0 release notes](https://cycling74.com/releases/max/9.2.0)]:
  "nested requires now work"; "added support for require statements used in codeboxes for gendsp files
  used as functions"; fixes for require'd functions resolving to the wrong abstraction and for multiple
  `.gendsp` abstractions; "fixed Dead Code Elimination bugs"; "disabled collapsing simple assignments
  (x = y)"; `@file` became an alias of `@gen`. max-gen-helper adds: 9.2.0 refuses `phi = …` (assignments
  to constant names) that 9.1.4 runs; 9.1.4 fails on some user functions 9.2.0 runs; 9.2.0 changed DCE and
  constant folding, so "code that compiles on both versions may still sound different" [sourced: README].
- **Hot reload:** gen~ `@gen` picking up a changed file is measured on 9.2.0 [sourced: max-gen-helper];
  patcher reload on disk change is described for 9.2.0+ ("Earlier versions do not reload") [sourced:
  py2max caveats]. The 9.2.0 release notes themselves contain no "reload on disk change" item [sourced].
  gen~ also has an explicit `reload` message [sourced: local `gen~.maxref.xml`] — wire a hidden button to
  it as fallback.
- **v8 in 9.2.0:** engine 14.6.202; native `setTimeout`/`setInterval`/`setImmediate`/`queueMicrotask`;
  `fetch`/http/udp/tcp/websocket workalikes; native console; `MaxFFT`, `MaxFFT2D` [sourced: release
  notes]. The (older) user guide still says timers are not available and to use `Task` [sourced: local
  `javascript` page, publishDate 2024-10-30]. Anything that must run in **stock Live (9.1.5)** must not
  rely on 9.2-only APIs [inference].
- **Consequence:** Develop against 9.2 if the user switches Live, but keep the GenExpr flat (no nested
  `require`) and gencheck-clean for **both** 9.1.5 and 9.2.0 so the released device works in stock Live
  [inference]. Decision for the user: switch Live to 9.2 for development or not.

## 3. TypeScript for v8

- **Type definitions:** `@types/maxmsp` 1.0.16 (2026-10-21, MIT, DefinitelyTyped; contributors twhiston,
  FrancescElies) declares the jsthis globals (`inlets`, `outlets`, `autowatch`, `jsarguments`,
  `messagename`, `post`, `outlet`, `error`, …) and classes `Buffer`, `Dict`, `File`, `Folder`, `Global`,
  `LiveAPI`, `Max`, `Maxobj`, `MaxobjListener`, `Patcher`, `PolyBuffer`, `Task`, `SQLite`, `MGraphics`,
  Jitter classes [sourced: package contents]. Its header points at the Max 8 `jsglobal` vignette, and it
  does **not** declare the 9.2 additions (`MaxFFT`, timers are standard) [sourced/inference]. Other names
  checked on npm: `@types/max-api` 2.0.3 (2023, types for **Node for Max** `max-api`, not for v8);
  `max-api` 2.0.0 is a placeholder stub; `@types/maxforlive`, `@cycling74/max-api`, `maxmsp-ts`,
  `@types/max-for-live` do not exist [sourced: npm registry].
- **Module system:** v8 supports `require("my-lib.js")` of **CommonJS** modules (`exports` /
  `module.exports`) [sourced: local userguide `javascript`]. The `v8` refpage: "Exposes the Javascript
  language (ECMAScript 6+)" [sourced: `v8.maxref.xml`]. Max calls global functions by message name and
  binds jsthis to `this`; `foo.local = 1` hides a function [sourced: userguide]. JS always runs in the
  **low-priority thread**; MIDI arriving from high priority is deferred [sourced: userguide] — so no voice
  timing in JS.
- **`autowatch`:** a jsthis global (`declare var autowatch: number` in `@types/maxmsp`) that reloads the
  script when the file changes [sourced: types; semantics from the Max JS API, not re-read for this note →
  inference]. Set `autowatch = 1` in the entry file.
- **v8 vs legacy `js`:** the user guide says the old engine (JS 1.8.5) is kept only for backwards
  compatibility and new code should use `v8`/`v8ui` [sourced]. Use `v8`.
- **Recommended build** [inference, untested]: two options.
  1. *No bundler* (simplest): `tsc` with `module: commonjs`, `target: es2020`, one `.js` per `.ts`, and
     Max's own `require` loads the siblings. No tree-shaking risk.
  2. *esbuild* (one file, can inline npm deps):
     ```bash
     pnpm add -D esbuild typescript @types/maxmsp
     pnpm exec esbuild src/aliasing.ts --bundle --format=cjs --platform=neutral \
       --target=es2020 --outfile=devices/aliasing/aliasing.js
     ```
     With `--bundle`, esbuild tree-shakes, so handler functions that nothing references are dropped.
     Either make them exported and re-attach them (`Object.assign(globalThis, { bang, list, msg_int })`)
     or keep them as top-level `function` declarations in a non-bundled entry. Whether Max resolves
     handlers attached to `globalThis` in v8 is **[open]** (one-line test in Max). Keep `tsc --noEmit` for
     type checking; esbuild does not type-check. Target `es2020` is a conservative guess because the v8
     version inside Max 9.1.5 is not documented in the sources read here [inference].
  Fit for the Aliasing Synth: v1 needs no JS at all if voice allocation is done by `poly`/
  `mc.noteallocator~` (§7). Add the TS layer when presets, table management or UI logic appear.

## 4. Host-side DSP verification (GenExpr outside Max)

Options found:

| Option | What | CLI-automatable? | Verdict |
|---|---|---|---|
| **gen~ C++ export + own harness** | `exportcode` writes `<name>.cpp/.h` + `gen_dsp/` (genlib) into `@exportfolder`, file name `@exportname`; `@autoexport` = "Automatically export on edit"; `@exportnotifier` names a receive for completion [sourced: local `gen~.maxref.xml`; gen-plugin-export README lists the output files] | Needs **Max running** (no headless Max), but no clicks: a test patch can send `exportcode` on load, or rely on `autoexport` (oopsy: "gen~ will re-export on every edit" [sourced: [oopsy README](https://github.com/electro-smith/oopsy)]) | **Recommended.** Same code as Max, double precision → expect a near-bit-exact null against a Max render [inference] |
| RNBO C++ export | `rnbo~` message `export cpp-export cpp-code-export [config]`, status via `@dumpoutlet 1` (`exportstatus success/error`) [sourced: RNBO 1.4.5 `rnbo~.maxref.xml`] | Same (needs Max), scriptable | Only if the device itself were RNBO; adds licence questions in M4L (below) |
| Python/numpy reference model | Independent re-implementation | fully | Useful for **design** questions (what should the algorithm do), not for proving the gen~ code |
| GenExpr interpreter / transpiler | none found; only grammars (`sadguitarius/tree-sitter-genexpr`, `zeffii/GenExpr_Grammar`, `larme/genexpr-mode`) [sourced: GitHub search 2026-11-24] | – | Does not exist; do not build one |
| taylorbrook `dsp_sim` | Offline sim named in the guide | not re-checked here | Skip |
| ssdvtechno `audio_check.py` | Browser engine render of ~330 Max objects, "runs no control messages" [sourced] | yes | Not for gen~ |

Exported-code API (from gen-plugin-export practice): set `@exportname`, export, then the build includes the
generated `.cpp` and `gen_dsp/` [sourced: gen-plugin-export README]. The exact C++ entry points
(`create`, `perform`, `setparameter`, `num_inputs/num_outputs`, `destroy`) are what the exported header
declares — read them from the first export, do not guess [inference]. **Licence of exported code:**
Cycling '74's "Gen Code Export Licensing FAQ" exists (linked by gen-plugin-export and oopsy) but returned
HTTP 403 to the fetcher; for a private test harness this is not a distribution issue, but do not commit
exported `gen_dsp/` to the public repo until the FAQ is read [open]. Also: with only a Max-for-Live
authorisation, Gen code export is not available — the user's full Max licence covers it [sourced: local
userguide `m4l/live_limitations`].

Design implications for the Aliasing Synth [inference]:
- Make **one gen patcher = one voice** (`aliasvoice.genexpr`), stateful table in a gen `Data` (not a
  `Buffer` bound to an external `buffer~`), because exported code then contains the table and the
  harness needs no host buffer plumbing. Pitch/gate/velocity enter as **signal inputs**, so the same
  stimulus file drives Max and the C++ harness sample-exactly.
- The device instantiates the voice 5 times (`mc.gen~ @chans 5` or `poly~ 5` with `gen~` inside), the
  harness instantiates it 5 times in C++.

**Recommended loop:**
1. Claude edits `gen/aliasvoice.genexpr` → `gencheck --max-version 9.1.5` and `--max-version 9.2.0`
   (both must pass) → `--write-gendsp devices/aliasing/aliasvoice.gendsp`.
2. A standing Max test patch `tests/max/aliasvoice-export.maxpat` (generated with py2max) holds
   `[gen~ @gen aliasvoice @exportfolder <repo>/build/genexport @exportname aliasvoice @autoexport 1]`; when
   the `.gendsp` changes, Max reloads and re-exports [open: does autoexport fire on file reload, or only
   on edits inside Max? Fallback: a `[loadbang]→[exportcode(` plus a `reload` trigger].
3. `clang++ -std=c++17 -O2 tests/host/harness.cpp build/genexport/aliasvoice.cpp build/genexport/gen_dsp/genlib.cpp -Ibuild/genexport -Ibuild/genexport/gen_dsp -o build/host/aliasvoice`
   [untested; exact file list from the first export] reads stimulus WAVs (pitch/gate as float signals),
   writes output WAVs.
4. Python (`tools/analysis/`) checks: no NaN/inf, peak/DC limits, determinism (two runs bit-identical),
   spectral fingerprints against stored references (§6), and — once (5) exists — null vs Max.
5. Periodically, Max NRT render of the same stimulus (§5) → null test C++ vs Max (expected ≤ −120 dBFS or
   bit-exact [inference]) — this proves the export path, so step 3 can be trusted day to day.

## 5. Getting audio out of Max/Live without the user

- **Headless Max:** none. Max 9.2.0 fixed "a crash when launching Max via the command line with a
  relative path" [sourced: release notes], so `/Applications/Max.app/Contents/MacOS/Max path/to/test.maxpat`
  or `open -a /Applications/Max.app path/to/test.maxpat` is the launch path [untested; `open` is blocked
  inside Claude's sandbox, so the user approves an unsandboxed run or runs it].
- **Non-real-time rendering (standalone Max):** select the **NonRealTime** driver; hardware I/O is off,
  "Max runs the audio thread as fast as possible"; typical patch: enable DSP, monitor `dsptime~`, stop
  automatically, record with `sfrecord~` (≈10 s of audio in 100 ms in the doc's example) [sourced: local
  userguide `non_realtime`]. The driver can be selected by message: `; dsp setdriver <name>` ("If the word
  setdriver is followed by a symbol that names a valid driver, the new driver is selected by name")
  [sourced: `dsp.maxref.xml`]; Max quits with `; max clean` (clear dirty flag) then `; max quit`
  [sourced: userguide "Controlling Max with messages"]. Hence a fully scripted render:
  launch Max with `tests/max/render-aliasvoice.maxpat` → `loadbang` → `; dsp setdriver NonRealTime`
  → open stimulus `buffer~`s and `sfrecord~` target → `; dsp start` → stop after N samples (`dsptime~`)
  → `; dsp setdriver "Core Audio"` → `; max clean` → `; max quit` [untested; the driver choice is a
  global Max preference, so restoring it matters — inference]. Feed events as **signals** (stimulus
  WAVs), not as scheduler messages: in NRT the control/audio timing relation is not guaranteed
  [inference]. Authorisation or update dialogs at Max start would block this [open].
- **Remote control of a running Max:** Max 9 integrated OSC: enable the UDP server in preferences or per
  patcher; parameters get addresses `/<patcher name>/param/<parameter name>/<attribute>`; OSCQuery on
  `http://localhost:30339` when enabled [sourced: userguide `OSC`]. With `python-osc` Claude can set
  parameters/trigger renders. Integrated OSC is **not** functional when Max is authorised only via Live
  [sourced: `m4l/live_limitations`]. Alternative: v8 in 9.2 has native UDP/WebSocket [sourced: release
  notes]; `node.script` runs a separate Node process [sourced: userguide].
- **Max console without copy/paste:** Live writes Max errors into its own log, e.g.
  `error: Message from Max: mfl_device spectrumdraw~: could not load due to incorrect architecture`
  [sourced: local `Log.txt`]. Claude can read `~/Library/Preferences/Ableton/Live <version>/Log.txt`
  after a load (errors seen; whether `post()` lines also appear is [open]). The standalone Max log
  (`~/Library/Application Support/Cycling '74/Max 9/Logs/Max.log`) contains startup tracing, not console
  output [sourced: local file].
- **Live-side options:**
  - Live has no CLI render; Export Audio is a GUI dialog [inference].
  - eladefrati/ableton-live-test-harness: AbletonOSC fork (MIT, 2026-11-23, macOS, Live 12.4, Node ≥ 18,
    Live language English), symlinked into Remote Scripts as `AbletonOSC`, listens on 127.0.0.1:11000;
    `node harness/doctor.js`, `node harness/checks/record-roundtrip.js` records one track into another;
    needs Accessibility, Automation and Screen Recording permissions; `relaunch.js`/`quit.js` discard
    unsaved changes; `verify-ableton` skill reports PASS/FAIL [sourced: README]. Realistic for later
    regression tests (record instrument track → audio track → WAV).
  - bschoepke Agent Audio Tap: an M4L audio effect `m4l/AgentAudioTap.amxd` that records the signal at its
    insertion point via `live_agent_audio_tap` `{"command":"start","path":…}` / `{"command":"stop"}`
    [sourced: AGENTS.md]. Place it after our instrument → WAV without user clicks once set up; but the
    MCP executes arbitrary Python inside Live ("Back up your Live Set before using this") [sourced: README].
  - ulm0 `render_track_audio`: renders "the **pre-FX** audio of an **audio track**" to a WAV, optional
    `analyze: true` (peak/RMS/clipping/silence) [sourced: README]. It does **not** render an instrument's
    output directly; needs Live 12.4.5+ Extensions (README's example points at a "Live 12 Beta" app;
    whether the release 12.4.16 runs Extensions is [open]).
  - producer-pal: Live 12.3+ MCP/REST device, set read/write; no audio-capture claim found in the README
    [sourced].
- **Realistic today:** fully automatic = C++ harness (§4) and Max-standalone NRT renders (after the user
  allows launching Max once). Needs the user's hands = everything inside Live (first load, parameter
  inspector, listening, A/B with Reaktor), until a Live harness is installed. Reaktor reference renders
  are always manual (Reaktor 6.5.2 has no CLI) [inference].

## 6. Python analysis set

Minimal, all with wheels for Python 3.14 on macOS arm64 [sourced: PyPI]:
`numpy 2.5.5`, `scipy 1.18.1` (`signal.welch`, `signal.spectrogram`, `signal.stft`, filters),
`soundfile 0.14.0` (float32/64 WAV I/O incl. bundled libsndfile), `matplotlib 3.11.2` (plots for the
user). Install [untested]:
```bash
UV_CACHE_DIR=.uv-cache uv add --dev numpy scipy soundfile matplotlib
```
Not needed: `librosa 1.0.1` (pulls `numba`; its features are MIR-oriented) [sourced/inference];
`pedalboard` (GPL-3.0) only if we ever host a VST3 offline [sourced: PyPI licence].

Method for aliasing-heavy signals [inference]: sample-exact null tests only make sense between gen~ in
Max and its own C++ export (same code). Against the Reaktor original and between code revisions, compare
**distributions**, not waveforms: long-window Welch PSD in dB (Hann, large `nperseg`, ≥ 50 % overlap,
render at 48 kHz and optionally 96 kHz to see which components fold), log-spectral distance between
PSDs, spectral centroid/flatness over time, spectrogram images for the user, and level/DC/peak checks.
Use fixed seeds and fixed stimuli so renders are deterministic.

## 7. Missing from the guide (instrument workbench specifics)

- **Instrument shell:** Live's own blank template has `midiin` and `plugout~` (comments "MIDI from Live",
  "Audio to Live") [sourced: local `Max Instrument.amxd`]. ssdvtechno: instrument input `notein` or
  `midiin → midiparse`, output `plugout~` [sourced]. MIDI in M4L comes from Live, not from Max's drivers
  [sourced: `m4l/live_limitations`].
- **Voices:** `poly~` with `param` objects, `mc.poly~`/`mcs.poly~` wrappers; MC alternatives
  `mc.noteallocator~` (note-on/off → voice numbers, busy-state multichannel input to hold voices during
  release) and `mc.voiceallocator~` [sourced: userguide `polyphony`, `mc.noteallocator~.maxref.xml`].
  For 5 voices of one gen patcher, `mc.gen~ @chans 5` + `mc.noteallocator~` or `poly~ 5` are both viable;
  choose in the design round [inference]. MC editing needs a standalone Max authorisation (users of the
  frozen device only run it) [sourced: `m4l/live_limitations`].
- **Initialisation:** `live.thisdevice` instead of `loadbang`; init chains with `trigger` [sourced:
  guidelines, m4l.md].
- **Parameters vs pattr:** Only parameter-mode objects are stored with the Set; `autopattr` cannot
  batch-register into the parameter system; `pattrstorage` in Parameter Mode stores its whole state in the
  Set/preset (no external file) [sourced: `m4l/live_limitations`]. Keep v1 to `live.*` parameters.
- **Files and search path:** Max searches (1) the folder of the open patch, (2) its project, (3) the Max 9
  folder, (4) the search path [sourced: userguide `search_path`]. "All Max for Live devices are projects";
  device projects can have a **Development Path**; freezing includes all files in the Project window
  [sourced: userguide `projects`]. So a flat device folder (`.amxd` + `.gendsp` + `.js`) works in Max;
  that Live-hosted M4L resolves `@gen aliasvoice` from the device folder is [open] (guide item 3).
- **Freeze / Collect All:** freeze before sharing; Max 8.5.4 added a device preference to include
  packages when freezing [sourced via search excerpt of the Max changelog; not re-read]. Test the frozen
  copy in a fresh Set [sourced: guidelines].
- **Code signing / notarisation:** nothing found for `.amxd`; only third-party externals must be built
  per platform [sourced: guidelines "OS Compatibility"]; our device uses no externals, so no signing
  [inference].
- **Package Manager:** nothing required. RNBO 1.4.5, Gen, ableton-dsp, maxforlive-elements, Node for Max
  are already in `Max.app/Contents/Resources/C74/packages`; note `~/Documents/Max 9/Packages` contains no
  RNBO (the inventory said it does) [sourced: local listing]. Ableton's "Building Max Devices" pack is
  the official tutorial set [sourced: userguide `m4l/live_midieffects`].
- **RNBO in M4L:** Cycling '74 support says: with standalone Max + Max for Live you can open, edit and
  export RNBO patches in M4L but not save them; with standalone Max + RNBO + Max for Live you get full
  access; the RNBO demo mode has no expiry but cannot save [sourced via search excerpt of
  https://support.cycling74.com/hc/en-us/articles/10536073075219-Can-I-use-RNBO-in-Max-for-Live; page
  itself 403 to the fetcher]. Not needed for v1.
- **Live 12.4.15 log noise:** the user's Live log shows stock M4L devices failing with "incorrect
  architecture" (`spectrumdraw~`, `multiconvolve~`, `bufreverse~`) [sourced: `Log.txt`] — unrelated, but
  it pollutes console-based checks; filter by device name [inference].

## 8. Optional MCP inspectors — recommendation: later

- ersatzben/maxmsp-mcp: last commit 2026-07-10; miravassor fork is 37 commits ahead and 2 behind
  (diverged), last push 2026-05-25; newest ersatzben forks with activity: MarvinHauke (2026-10-29),
  garytyler (2026-09-19) [sourced: GitHub API]. No `.amxd` save, no parameter metadata in ersatzben
  (guide). **Not now.**
- producer-pal: very active (v2.6.0-rc1 2026-11-17), installs as one `.amxd`, Live 12.3+ (12.4
  recommended) [sourced]. Best Live-side option if Set automation is wanted. **Later.**
- bschoepke/ableton-live-mcp: last commit 2026-10-06; arbitrary Python in Live + Agent Audio Tap
  [sourced]. Most useful for **audio capture in Live**; high blast radius. **Later, in a throwaway Set.**
- Rationale: our loop is file-based; the MCPs add value only for in-Live load/capture, which comes after
  the DSP is right [inference].

## Proposed vendoring list (pinned)

| Upstream | Path in workbench | Pin |
|---|---|---|
| `mforhm/max-gen-helper` `scripts/gencheck/gencheck.py`, `genflow.py`, `LICENSE` | `tools/vendor/gencheck/` | `a7a05a72` |
| `Ableton/maxdevtools` `maxdiff/` (no tests), `m4l-production-guidelines/m4l-production-guidelines.md`, `LICENSE.txt` | `tools/vendor/maxdevtools/`, `docs/reference/` | `5b39dec9` |
| `ssdvtechno/maxpylang-claude-plugin` `skills/maxpylang/references/m4l.md`, `LICENSE` | `docs/reference/m4l.md` | `a132b5b5` |
| Live's `Max Instrument.amxd` template | starting point of the device shell (copied, then edited in Max) | Live 12.4.16 |

Fetch as tarballs from codeload.github.com, record commit + date in a `VENDOR.md` [inference, matches the
user's convention of tarball snapshots].

## Open checks in Max/Live

1. Switch Live to the standalone Max 9.2 (Settings → File & Folder → Max Application, restart) or stay on
   9.1.5? Confirm afterwards with Live's `Log.txt` line `Max: Version …`. Does Live 12.4.16 accept 9.2
   without problems?
2. In Live-hosted Max (9.1.5 and/or 9.2): does `[gen~ @gen aliasvoice]` in an `.amxd` find
   `aliasvoice.gendsp` in the device folder, and does it pick up a rewritten file without reopening?
3. In standalone Max 9.2: does `@autoexport 1` re-export C++ when the `.gendsp` is replaced on disk, or
   only on edits inside Max? What exactly does the export folder contain (file list for the harness)?
4. Can Max be launched from the command line with a test patch and run unattended (no authorisation or
   update dialogs), and does `; dsp setdriver NonRealTime` work by name? Restore the audio driver after.
5. Does a v8 handler attached via `globalThis.<name> = fn` (esbuild bundle) receive messages, or must
   handlers be top-level declarations? (Only when the TS layer is added.)
6. Do `post()` lines from a device appear in Live's `Log.txt`, or only errors?
7. Is pdmeyer's GenExpr extension actually on the VS Code Marketplace (if the user wants it)?
8. Read Cycling '74's Gen Code Export Licensing FAQ before committing any exported C++ to the public repo.
9. Does the frozen instrument load and play in a fresh Set with stock Live (Max 9.1.5)? (Release gate.)

## Sources (primary, read for this note)

- GitHub repos/READMEs/files at the commits named above: mforhm/max-gen-helper, Ableton/maxdevtools
  (maxdiff README, production guidelines), shakfu/py2max, codebrain/m4l-builder, jpdrecourt/maxpat-render,
  isabelgk/gen-fmt, pdmeyer/GenExpr_VSCode, mikecfisher/ableton-lom-skill, zsteinkamp/m4l-typescript-base,
  zsteinkamp/m4l-Knobbler4, ssdvtechno/maxpylang-claude-plugin, Cycling74/gen-plugin-export,
  electro-smith/oopsy, eladefrati/ableton-live-test-harness, bschoepke/ableton-live-mcp (README, AGENTS.md),
  ulm0/ableton-live-mcp, adamjmurray/producer-pal, ersatzben/maxmsp-mcp, miravassor/maxmsp-mcp-fork.
- PyPI JSON API: py2max, m4l-builder, maxpylang, numpy, scipy, soundfile, matplotlib, librosa, numba,
  python-osc, pedalboard. npm registry: @types/maxmsp (tarball contents), @types/max-api, max-api, esbuild,
  typescript, @rnbo/js.
- Cycling '74: [Max 9.2.0 release notes](https://cycling74.com/releases/max/9.2.0); local Max 9.2.0 docs
  (userguide pages `javascript`, `non_realtime`, `OSC`, `search_path`, `projects`, `polyphony`, `rnbo`,
  `new_in_max9`, `controlling_max_with_messages`, `m4l/live_limitations`, `m4l/live_files`,
  `m4l/live_midieffects`; refpages `v8`, `gen~`, `dsp`, `mc.noteallocator~`, RNBO `rnbo~`), online
  equivalents under https://docs.cycling74.com/userguide/ and https://docs.cycling74.com/reference/.
- Ableton: help articles 209070309 "Using a separate Max for Live installation" (updated 2026-10-21) and
  209772305 "Recommended Max versions" (updated 2026-02-03) via the Zendesk JSON API;
  [Live 12 manual, Max for Live](https://www.ableton.com/en/live-manual/12/max-for-live/).
- Local machine (read-only): `Info.plist` of both Max apps and Live, Live `Log.txt`, Max logs, Live's
  `Misc/Max Devices/*.amxd` templates.
- Search excerpts only (pages not fetchable): Cycling '74 support "Can I use RNBO in Max for Live",
  "Gen Code Export Licensing FAQ".
