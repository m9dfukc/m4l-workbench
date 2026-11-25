#!/usr/bin/env node
// The optional Live automation of this workbench: install it, switch it on or off, see its state,
// and run the harness's own scripts only while it is on.
//
//   node tools/live/harness.mjs status                    read-only: switch, clone + pin, Remote Script link, Places
//   node tools/live/harness.mjs install [--dry-run]       clone at the pin, link the Remote Script, add device folders
//                                                         to Places (Live quit), then print the manual steps
//   node tools/live/harness.mjs on | off                  the switch (tools/live/local.json, gitignored; off by default)
//   node tools/live/harness.mjs run <doctor|relaunch|quit|roundtrip|cli> [args...]
//                                                         a harness script, refused while the switch is off
//   --harness <dir>   the harness clone (default: ../ableton-live-test-harness next to this repo)
//
// The harness is eladefrati/ableton-live-test-harness, pinned below after reading its source.
// Rules: CLAUDE.md -> Decisions -> "Exception, Live test harness". Setup: tools/live/README.md.
// install and run need to run outside Claude's sandbox (writes outside the repo, UDP to Live).

import { execFileSync, spawnSync } from "node:child_process";
import fs from "node:fs";
import os from "node:os";
import path from "node:path";

export const PIN = "ad756c1e";
const HARNESS_REPO = "https://github.com/eladefrati/ableton-live-test-harness";
const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const LOCAL = path.join(REPO, "tools", "live", "local.json");
const DEFAULT_DIR = path.resolve(REPO, "..", "ableton-live-test-harness");
const SCRIPTS = { doctor: "harness/doctor.js", relaunch: "harness/relaunch.js", quit: "harness/quit.js", roundtrip: "harness/checks/record-roundtrip.js", cli: "harness/cli.js" };

// ---------- the switch

export function readLocal() {
  try {
    return { enabled: false, harness: null, ...JSON.parse(fs.readFileSync(LOCAL, "utf8")) };
  } catch {
    return { enabled: false, harness: null };
  }
}

function writeLocal(values) {
  fs.writeFileSync(LOCAL, JSON.stringify({ ...readLocal(), ...values }, null, 2) + "\n");
}

// The harness clone: --harness, else the switch file's, else next to the repo.
export function harnessDir(given) {
  return path.resolve(given || readLocal().harness || DEFAULT_DIR);
}

// ---------- what is installed

function git(dir, ...args) {
  return execFileSync("git", ["--no-optional-locks", "-C", dir, ...args], { encoding: "utf8", stdio: ["ignore", "pipe", "ignore"] }).trim();
}

function cloneState(dir) {
  if (!fs.existsSync(path.join(dir, "manager.py"))) return { present: false };
  try {
    const head = git(dir, "rev-parse", "HEAD");
    return { present: true, head, pinned: head.startsWith(PIN), dirty: git(dir, "status", "--porcelain").split("\n").filter(Boolean) };
  } catch (error) {
    return { present: true, error: String(error.message || error) };
  }
}

// The installed Lives (newest version last) and the preferences folder of the newest.
function liveInstall() {
  const apps = fs.readdirSync("/Applications").filter((f) => /^Ableton Live .*\.app$/.test(f)).map((f) => path.join("/Applications", f));
  const withVersion = apps.map((app) => {
    try {
      const plist = JSON.parse(execFileSync("plutil", ["-convert", "json", "-o", "-", path.join(app, "Contents", "Info.plist")], { encoding: "utf8" }));
      return { app, version: String(plist.CFBundleShortVersionString).split(" ")[0] };
    } catch {
      return null;
    }
  }).filter(Boolean).sort((a, b) => a.version.localeCompare(b.version, "en", { numeric: true }));
  const live = withVersion.at(-1);
  if (!live) return null;
  const prefs = path.join(os.homedir(), "Library", "Preferences", "Ableton", `Live ${live.version}`);
  return { ...live, all: withVersion.map((l) => l.app), prefs, libraryCfg: path.join(prefs, "Library.cfg") };
}

// The User Library Live uses (Library.cfg <UserLibrary>: ProjectPath + ProjectName) and its Places.
export function libraryInfo(text) {
  const block = text.match(/<UserLibrary>([\s\S]*?)<\/UserLibrary>/);
  const value = (name) => block?.[1].match(new RegExp(`<${name} Value="([^"]*)"`))?.[1];
  const unescape = (s) => s.replace(/&lt;/g, "<").replace(/&gt;/g, ">").replace(/&quot;/g, "\"").replace(/&amp;/g, "&");
  const root = value("ProjectPath"), name = value("ProjectName");
  return {
    userLibrary: root && name ? path.join(unescape(root), unescape(name)) : null,
    places: [...text.matchAll(/<UserFolderInfo\b[^>]*?\bPath="([^"]*)"/g)].map((m) => path.resolve(unescape(m[1]))),
    emptyPlaces: /<UserFolderInfoList\s*\/>/.test(text),
  };
}

function linkState(link, dir) {
  let stat;
  try {
    stat = fs.lstatSync(link);
  } catch {
    return "missing";
  }
  if (!stat.isSymbolicLink()) return "folder";
  let real;
  try {
    real = fs.realpathSync(link);
  } catch {
    return "dangling";
  }
  return real === fs.realpathSync(dir) ? "ours" : `other:${real}`;
}

function deviceFolders() {
  const root = path.join(REPO, "devices");
  return fs.readdirSync(root).map((d) => path.join(root, d))
    .filter((d) => fs.statSync(d).isDirectory() && fs.readdirSync(d).some((f) => f.endsWith(".amxd")));
}

function liveRunning() {
  try {
    return execFileSync("pgrep", ["-x", "Live"], { encoding: "utf8" }).trim().length > 0;
  } catch (error) {
    return error.status === 1 ? false : null; // null: can't tell (sandbox)
  }
}

// The app macOS holds responsible for Claude's commands: the nearest ancestor that is an .app.
function responsibleApp() {
  try {
    let pid = process.pid;
    for (let i = 0; i < 12 && pid > 1; i++) {
      const [ppid, ...comm] = execFileSync("ps", ["-o", "ppid=,comm=", "-p", String(pid)], { encoding: "utf8" }).trim().split(/\s+/);
      const command = comm.join(" ");
      const m = command.match(/^(.*?\.app)\/Contents\/MacOS\//);
      if (m && !/Claude\.app\/Contents\/Helpers\//.test(command)) return m[1];
      pid = Number(ppid);
    }
  } catch {}
  return null;
}

// ---------- commands

function status(dir) {
  const local = readLocal();
  const clone = cloneState(dir);
  const live = liveInstall();
  const say = (tag, text) => console.log(`${tag.padEnd(4)} ${text}`);
  say(local.enabled ? "on" : "off", `Live automation is ${local.enabled ? "ON" : "OFF"} (${path.relative(REPO, LOCAL)}${fs.existsSync(LOCAL) ? "" : " absent"})`);
  if (!clone.present) say("miss", `no harness clone at ${dir} (node tools/live/harness.mjs install)`);
  else if (clone.error) say("warn", `harness clone at ${dir}: ${clone.error}`);
  else {
    say(clone.pinned ? "ok" : "warn", `harness clone at ${dir}, HEAD ${clone.head.slice(0, 8)}${clone.pinned ? " = pin" : `, pin is ${PIN}`}`);
    if (clone.dirty.length) say("warn", `harness clone has local changes: ${clone.dirty.join(", ")}`);
  }
  if (!live) {
    say("miss", "no Ableton Live in /Applications");
  } else {
    say("ok", `Live ${live.version} (${live.app}), preferences ${live.prefs}`);
    if (fs.existsSync(live.libraryCfg)) {
      const lib = libraryInfo(fs.readFileSync(live.libraryCfg, "utf8"));
      const link = lib.userLibrary ? path.join(lib.userLibrary, "Remote Scripts", "AbletonOSC") : null;
      const state = link ? linkState(link, dir) : "unknown";
      say(state === "ours" ? "ok" : "miss", `Remote Script link ${link || "(User Library unknown)"}: ${state}`);
      for (const folder of deviceFolders()) {
        const inPlaces = lib.places.includes(folder);
        say(inPlaces ? "ok" : "miss", `Places: ${path.relative(REPO, folder)} ${inPlaces ? "listed" : "not listed"}`);
      }
    } else say("miss", `no ${live.libraryCfg}: start this Live once`);
  }
  say("info", "Live settings, permissions and AbletonOSC itself: node tools/live/harness.mjs run doctor (Live open)");
  return local.enabled && clone.present && clone.pinned ? 0 : 1;
}

function install(dir, dryRun) {
  const act = (text, fn) => {
    console.log(`${dryRun ? "would" : "do  "} ${text}`);
    if (!dryRun) fn();
  };
  // 1. Clone at the pin.
  const clone = cloneState(dir);
  if (!clone.present) {
    act(`clone ${HARNESS_REPO} to ${dir} and switch to ${PIN}`, () => {
      execFileSync("git", ["clone", HARNESS_REPO, dir], { stdio: "inherit" });
      execFileSync("git", ["-C", dir, "switch", "--detach", PIN], { stdio: "inherit" });
    });
  } else if (!clone.pinned) {
    console.log(`warn harness at ${(clone.head || "?").slice(0, 8)}, pin is ${PIN}: read the new commits first (tools/live/README.md), then `
      + `git -C "${dir}" switch --detach <commit> and update PIN in tools/live/harness.mjs`);
  } else console.log(`ok   harness clone at ${dir} = pin`);

  const live = liveInstall();
  if (!live || !fs.existsSync(live.libraryCfg)) {
    console.log("FAIL no Live with a Library.cfg found: install Live and start it once, then run install again");
    return 1;
  }
  const lib = libraryInfo(fs.readFileSync(live.libraryCfg, "utf8"));
  if (!lib.userLibrary) {
    console.log(`FAIL can't read the User Library from ${live.libraryCfg}`);
    return 1;
  }

  // 2. Remote Script link (absolute; a relative link resolves from Remote Scripts and dangles).
  const scripts = path.join(lib.userLibrary, "Remote Scripts");
  const link = path.join(scripts, "AbletonOSC");
  const state = linkState(link, dir);
  if (state === "ours") console.log(`ok   ${link} -> ${dir}`);
  else if (state === "missing" || state === "dangling") {
    act(`link ${link} -> ${dir}`, () => {
      fs.mkdirSync(scripts, { recursive: true });
      if (state === "dangling") fs.unlinkSync(link);
      fs.symlinkSync(dir, link);
    });
  } else {
    console.log(`FAIL ${link} is ${state === "folder" ? "a folder (another AbletonOSC?)" : `a link to ${state.slice(6)}`}: move it out of Remote Scripts yourself, then run install again`);
    return 1;
  }

  // 3. Places for every device folder (Live must be quit; Library.cfg is Live's).
  const missing = deviceFolders().filter((f) => !lib.places.includes(f));
  if (!missing.length) console.log("ok   every device folder is in Places");
  else if (liveRunning() !== false) {
    console.log(`todo quit Live, then run install again to add ${missing.map((f) => path.relative(REPO, f)).join(", ")} to Places`);
  } else {
    if (lib.emptyPlaces) {
      // Live writes an empty list as <UserFolderInfoList />, which add-place.js (at the pin) refuses.
      act(`back up ${live.libraryCfg} to build/live/ and expand its empty Places list`, () => {
        const backup = path.join(REPO, "build", "live", `Library.cfg.${Date.now()}.bak`);
        fs.mkdirSync(path.dirname(backup), { recursive: true });
        fs.copyFileSync(live.libraryCfg, backup);
        const text = fs.readFileSync(live.libraryCfg, "utf8");
        const nl = text.includes("\r\n") ? "\r\n" : "\n";
        const expanded = text.replace(/([ \t]*)<UserFolderInfoList\s*\/>/, (_, indent) => `${indent}<UserFolderInfoList>${nl}${indent}</UserFolderInfoList>`);
        fs.writeFileSync(`${live.libraryCfg}.tmp`, expanded);
        fs.renameSync(`${live.libraryCfg}.tmp`, live.libraryCfg);
      });
    }
    for (const folder of missing) {
      act(`add ${path.relative(REPO, folder)} to Places (harness add-place.js)`, () => {
        execFileSync(process.execPath, [path.join(dir, "harness", "add-place.js"), folder, "--app", live.app], { stdio: "inherit" });
      });
    }
  }

  // 4. What only the user can do.
  const app = responsibleApp();
  console.log(`
Still by hand (once), then switch it on:
  1. Live: Settings > Link, Tempo & MIDI > a free Control Surface slot = AbletonOSC (Input/Output None);
     Language English (restart Live); Record, Warp & Launch > Bit Depth 32-bit float; Count-In None.
  2. macOS: System Settings > Privacy & Security > Accessibility ("Gerätesteuerung und Datenzugriff")
     > + > Cmd+Shift+G > ${app || "the Claude Code app (tools/live/README.md, step 4)"} > switch it on.
     Automation > System Events for the same app (macOS asks on first use).
  3. node tools/live/harness.mjs on
  4. With Live open: node tools/live/harness.mjs run doctor, then node tools/live/harness.mjs run roundtrip`);
  return 0;
}

function run(dir, script, args) {
  if (!readLocal().enabled) {
    console.error("Live automation is OFF: Claude does not start, drive or quit Live. Switch it on with node tools/live/harness.mjs on");
    return 2;
  }
  const file = SCRIPTS[script];
  if (!file) {
    console.error(`unknown script ${script}; one of ${Object.keys(SCRIPTS).join(", ")}`);
    return 2;
  }
  const clone = cloneState(dir);
  if (!clone.present) {
    console.error(`no harness clone at ${dir} (node tools/live/harness.mjs install)`);
    return 2;
  }
  if (!clone.pinned) console.error(`warn harness at ${(clone.head || "?").slice(0, 8)}, pin is ${PIN}`);
  const result = spawnSync(process.execPath, [path.join(dir, file), ...args], { stdio: "inherit" });
  return result.status ?? 2;
}

function main(argv) {
  let given = null, dryRun = false;
  const rest = [];
  for (let i = 0; i < argv.length; i++) {
    if (argv[i] === "--harness") given = argv[++i];
    else if (argv[i] === "--dry-run") dryRun = true;
    else rest.push(argv[i]);
  }
  const [command, ...args] = rest;
  const dir = harnessDir(given);
  switch (command) {
    case "status": return status(dir);
    case "install": return install(dir, dryRun);
    case "on":
      writeLocal({ enabled: true, harness: dir, pin: PIN });
      console.log(`Live automation ON (harness ${dir}); off again with node tools/live/harness.mjs off`);
      return cloneState(dir).present ? 0 : (console.log(`warn no harness clone at ${dir} yet (install)`), 0);
    case "off":
      writeLocal({ enabled: false });
      console.log("Live automation OFF: Claude hands every Live test to you (live-test skill)");
      return 0;
    case "run": return run(dir, args[0], args.slice(1));
    default:
      console.log(fs.readFileSync(new URL(import.meta.url), "utf8").split("\n").filter((l) => l.startsWith("//")).slice(0, 16).map((l) => l.slice(3)).join("\n"));
      return command ? 2 : 0;
  }
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  process.exitCode = main(process.argv.slice(2));
}
