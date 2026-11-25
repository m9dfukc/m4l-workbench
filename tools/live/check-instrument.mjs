#!/usr/bin/env node
// In-Live check of a Max for Live instrument from this repo, on the Live test harness
// (eladefrati/ableton-live-test-harness, pinned in tools/live/harness.mjs). Spike, 2026-11-25.
//
// What it does, in a Set the harness started (relaunch.js) or with --any-set:
//   1. reads the parameters the .amxd declares (no Live needed; --offline stops here)
//   2. loads the device from Live's Places onto a new MIDI track "m4l-dut"
//   3. collects the Max console since the load from Live's Log.txt AND MaxPlugLib.log
//   4. compares Live's parameter list (names, ranges, enum items, initial values) with the .amxd
//   5. sets --set values, plays a clip of notes and records the device's Post FX on an audio
//      track "m4l-rec" - silently: the device track sits at -inf and the recording track's
//      monitoring is Off (both checked before Play), and the harness Set has Main at -inf
//   6. checks the take (finite, not silent, peak within the safety clip, DC) and writes
//      result.json + take.wav to build/<device>/live/<stamp>/
//
//   node tools/live/check-instrument.mjs devices/aliasing/Aliasing.amxd [options]
//     --offline              only step 1, print the expected parameters
//     --beats <n>            length of the take in beats (default 8)
//     --tempo <bpm>          song tempo (default 120)
//     --notes <list>         pitch:start:duration[:velocity],... in beats (default 48:0:3.5,55:4:3.5)
//     --set <name=value>     set a parameter by long name before recording (repeatable;
//                            a value that is not a number picks an enum item by name)
//     --expect-post <regex>  a console line that must appear after the load (repeatable)
//     --any-set              allow a Set the harness did not start (the user said it is disposable)
//     --keep                 leave the two tracks in the Set
//     --out <dir>            output folder (default build/<device>/live/<stamp>)
//   Needs the Live automation switched on (node tools/live/harness.mjs status|on|off); --offline
//   works without it. The harness folder comes from that switch (LIVE_HARNESS overrides it).
//
// Exit 0 = PASS, 1 = FAIL (findings printed and in result.json), 2 = could not run.
// Runs outside the sandbox (UDP to Live on localhost).

import { createHash } from "node:crypto";
import { execFileSync } from "node:child_process";
import fs from "node:fs";
import { createRequire } from "node:module";
import os from "node:os";
import path from "node:path";
import { harnessDir, readLocal } from "./harness.mjs";

const REPO = path.resolve(path.dirname(new URL(import.meta.url).pathname), "..", "..");
const MAXPLUGLIB = path.join(os.homedir(), "Library", "Application Support", "Cycling '74", "Max 9", "Logs", "MaxPlugLib.log");
const DUT = "m4l-dut";
const REC = "m4l-rec";
const MONITOR_OFF = 2; // Track.current_monitoring_state: 0 In, 1 Auto, 2 Off
const ERROR_TEXT = /\berror\b|exception|not found|could not|couldn't|can't|no such|undefined|is not a function|failed|bad (arg|number)/i;
const NOISE = [/mactimer: thread policy/];

// ---------- arguments

function parseArgs(argv) {
  const opts = { beats: 8, tempo: 120, notes: "48:0:3.5,55:4:3.5", set: [], expectPost: [], offline: false, anySet: false, keep: false, out: null, device: null };
  for (let i = 0; i < argv.length; i++) {
    const a = argv[i];
    const next = () => { if (i + 1 >= argv.length) throw new Error(`${a} needs a value`); return argv[++i]; };
    if (a === "--offline") opts.offline = true;
    else if (a === "--any-set") opts.anySet = true;
    else if (a === "--keep") opts.keep = true;
    else if (a === "--beats") opts.beats = Number(next());
    else if (a === "--tempo") opts.tempo = Number(next());
    else if (a === "--notes") opts.notes = next();
    else if (a === "--set") opts.set.push(next());
    else if (a === "--expect-post") opts.expectPost.push(next());
    else if (a === "--out") opts.out = next();
    else if (a === "-h" || a === "--help") opts.help = true;
    else if (a.startsWith("--")) throw new Error(`unknown option ${a}`);
    else if (!opts.device) opts.device = a;
    else throw new Error(`unexpected argument ${a}`);
  }
  if (!opts.help && !opts.device) throw new Error("name the device's .amxd");
  if (!(opts.beats > 0) || !(opts.tempo > 0)) throw new Error("--beats and --tempo must be positive numbers");
  return opts;
}

function parseNotes(text) {
  return text.split(",").map((item) => {
    const [pitch, start, duration, velocity = 100] = item.split(":").map(Number);
    if (![pitch, start, duration, velocity].every(Number.isFinite)) throw new Error(`bad note ${item} (pitch:start:duration[:velocity])`);
    return { pitch, start, duration, velocity };
  });
}

function parseSets(list) {
  return list.map((item) => {
    const at = item.indexOf("=");
    if (at < 1) throw new Error(`bad --set ${item} (name=value)`);
    const raw = item.slice(at + 1);
    const number = Number(raw);
    return { name: item.slice(0, at), value: raw.trim() !== "" && Number.isFinite(number) ? number : raw };
  });
}

// ---------- the .amxd's declared parameters (step 1)

export function patcherJson(file) {
  const data = fs.readFileSync(file);
  for (let at = 0; at + 8 <= data.length;) {
    const length = data.readUInt32LE(at + 4);
    if (data.toString("latin1", at, at + 4) === "ptch") {
      const text = data.subarray(at + 8, at + 8 + length).toString("utf8").replace(/\0+$/, "");
      if (!text.startsWith("{")) throw new Error(`${file} is frozen or not a JSON device; check the unfrozen device`);
      return JSON.parse(text);
    }
    at += 8 + length;
  }
  throw new Error(`${file} has no ptch chunk`);
}

// Every parameter-enabled box: { longname, shortname, type, min, max, enum, initial, visible }.
// type 0 float, 1 int, 2 enum; visible = listed by the LOM (parameter_invisible 0 or absent).
export function declaredParameters(patcher) {
  const out = [];
  const walk = (p) => {
    for (const { box } of p.boxes || []) {
      const v = box.saved_attribute_attributes?.valueof;
      if (v?.parameter_longname !== undefined && box.parameter_enable !== 0) {
        const type = v.parameter_type ?? 0;
        // live.text: Live lists and shows the box attributes automation / automationon (default
        // val1 / val2), not parameter_enum [sourced: live.text.maxref.xml "Automation Off/On Label";
        // measured: LOM, testlog t4-auto 2026-11-25]
        const items = box.maxclass === "live.text"
          ? [box.automation ?? "val1", box.automationon ?? "val2"]
          : (v.parameter_enum ?? []);
        out.push({
          longname: v.parameter_longname,
          shortname: v.parameter_shortname ?? v.parameter_longname,
          type,
          min: type === 2 ? 0 : (v.parameter_mmin ?? 0),
          max: type === 2 ? Math.max(items.length - 1, 0) : (v.parameter_mmax ?? 127),
          exponent: v.parameter_exponent ?? 1,
          enum: type === 2 ? items : null,
          declaredEnum: v.parameter_enum ?? null,
          initial: v.parameter_initial_enable ? (v.parameter_initial ?? [0])[0] : null,
          visible: !v.parameter_invisible,
          maxclass: box.maxclass,
        });
      }
      if (box.patcher) walk(box.patcher);
    }
  };
  walk(patcher.patcher || patcher);
  return out;
}

// Pairs Live's parameter names (after Device On) with declared parameters. The harness found
// that Live lists a Max device's visible parameters in code-unit order of the long name and
// reports short names (harness/live.js, parameterIndices); if that does not hold, each name is
// matched to the one declared parameter with that short (or long) name.
// Returns { list: [declared | null per Live index - 1], sortedOrder, unmatched: [names] }.
export function mapParameters(liveNames, visible) {
  const sorted = [...visible].sort((a, b) => (a.longname < b.longname ? -1 : a.longname > b.longname ? 1 : 0));
  const fits = (name, p) => p && (name === p.shortname || p.longname.endsWith(name));
  if (liveNames.length === sorted.length && liveNames.every((name, i) => fits(name, sorted[i]))) {
    return { list: sorted, sortedOrder: true, unmatched: [] };
  }
  const unmatched = [];
  const list = liveNames.map((name) => {
    const candidates = visible.filter((p) => p.shortname === name || p.longname === name);
    if (candidates.length === 1) return candidates[0];
    unmatched.push(name);
    return null;
  });
  return { list, sortedOrder: false, unmatched };
}

// ---------- console from both logs (step 3)

function stamp(time, sep) {
  const d = new Date(time);
  const pad = (n, w = 2) => String(n).padStart(w, "0");
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}${sep}${pad(d.getHours())}:${pad(d.getMinutes())}:`
    + `${pad(d.getSeconds())}.${pad(d.getMilliseconds(), 3)}`;
}

// MaxPlugLib.log lines "[YYYY-MM-DD HH:MM:SS.micro level] [id] text" from `since` on.
export function maxPlugLibLines(text, since) {
  const from = stamp(since, " ");
  const out = [];
  for (const line of text.split("\n")) {
    const m = line.match(/^\[(\d{4}-\d\d-\d\d [\d:.]+) (\w+)\] \[\d+\] (.*)$/);
    if (m && m[1] >= from) out.push({ at: m[1], level: m[2], text: m[3], log: "MaxPlugLib.log" });
  }
  return out;
}

export function classify(lines) {
  const kept = lines.filter((l) => l.text.trim() !== "" && !NOISE.some((re) => re.test(l.text)));
  const errors = kept.filter((l) => l.level === "error" || ERROR_TEXT.test(l.text));
  const warnings = kept.filter((l) => !errors.includes(l) && (l.level.startsWith("warn") || /deprecated|warning/i.test(l.text)));
  return { lines: kept, errors, warnings };
}

// ---------- the take (step 6)

export function health(channels) {
  return channels.map((x) => {
    let bad = 0, peak = 0, sum = 0, sq = 0;
    for (const v of x) {
      if (!Number.isFinite(v)) { bad++; continue; }
      const a = Math.abs(v);
      if (a > peak) peak = a;
      sum += v;
      sq += v * v;
    }
    const n = Math.max(x.length - bad, 1);
    const db = (v) => (v > 0 ? 20 * Math.log10(v) : -Infinity);
    return { samples: x.length, nonFinite: bad, peak, peakDb: db(peak), rmsDb: db(Math.sqrt(sq / n)), dc: sum / n };
  });
}

// ---------- helpers

function sha256(file) {
  return createHash("sha256").update(fs.readFileSync(file)).digest("hex").slice(0, 12);
}

function gitState(deviceDir) {
  const git = (...args) => execFileSync("git", ["-C", REPO, ...args], { encoding: "utf8" }).trim();
  try {
    const rel = path.relative(REPO, deviceDir);
    return { head: git("rev-parse", "--short", "HEAD"), dirty: git("status", "--short", "--", rel).split("\n").filter(Boolean) };
  } catch (error) {
    return { error: String(error.message || error) };
  }
}

function runtimeFiles(deviceDir) {
  return Object.fromEntries(fs.readdirSync(deviceDir)
    .filter((f) => /\.(amxd|gendsp|js)$/.test(f))
    .sort()
    .map((f) => [f, sha256(path.join(deviceDir, f))]));
}

const near = (a, b, range) => Math.abs(a - b) <= 1e-4 * Math.max(Math.abs(range), 1) + 1e-6;

// What the LOM reports for a declared value. For a parameter with an exponent it reports the
// control's position mapped linearly onto min..max, not the value itself:
// min + (max - min) * ((value - min) / (max - min)) ^ (1 / exponent)
// [measured: 8 of 8 exponent parameters of aliasing v0.3, run 20261125-170715].
export function lomValue(p, value) {
  if (p.type === 2 || !p.exponent || p.exponent === 1 || p.max === p.min) return value;
  const n = Math.min(Math.max((value - p.min) / (p.max - p.min), 0), 1);
  return p.min + (p.max - p.min) * n ** (1 / p.exponent);
}

// ---------- main

async function main() {
  let opts;
  try {
    opts = parseArgs(process.argv.slice(2));
  } catch (error) {
    console.error(`check-instrument: ${error.message}`);
    return 2;
  }
  if (opts.help) {
    console.log(fs.readFileSync(new URL(import.meta.url), "utf8").split("\n").filter((l) => l.startsWith("//")).slice(0, 30).map((l) => l.slice(3)).join("\n"));
    return 0;
  }

  const deviceFile = path.resolve(opts.device);
  const deviceDir = path.dirname(deviceFile);
  const build = path.basename(deviceFile);
  const declared = declaredParameters(patcherJson(deviceFile));
  const visible = declared.filter((p) => p.visible);
  if (opts.offline) {
    console.log(JSON.stringify({ device: path.relative(REPO, deviceFile), parameters: declared.length, visible: visible.length,
      hidden: declared.filter((p) => !p.visible).map((p) => p.longname), list: visible }, null, 2));
    return 0;
  }

  const notes = parseNotes(opts.notes);
  const sets = parseSets(opts.set);
  // The optional Live automation: refuse while its switch is off (tools/live/harness.mjs).
  if (!readLocal().enabled) {
    console.error("check-instrument: Live automation is OFF (node tools/live/harness.mjs status); hand the test to the user "
      + "(live-test skill) or switch it on with node tools/live/harness.mjs on");
    return 2;
  }
  const harness = process.env.LIVE_HARNESS || path.join(harnessDir(), "harness");
  if (!fs.existsSync(path.join(harness, "live.js"))) {
    console.error(`check-instrument: no harness at ${harness} (node tools/live/harness.mjs install; tools/live/README.md)`);
    return 2;
  }
  const require = createRequire(import.meta.url);
  const { connect } = require(path.join(harness, "live.js"));
  const { float } = require(path.join(harness, "osc.js"));
  const { maxMessages } = require(path.join(harness, "log.js"));
  const { requireRecordBitDepth, sampleRate } = require(path.join(harness, "settings.js"));
  const { recordedSamples } = require(path.join(harness, "audio.js"));
  const { inHarnessTemp } = require(path.join(harness, "macos.js"));
  const { placesProblem } = require(path.join(harness, "device-checks.js"));

  const deviceName = path.basename(deviceDir);
  const runStamp = stamp(Date.now(), "T").replace(/[-:]/g, "").replace("T", "-").slice(0, 15);
  const out = path.resolve(opts.out || path.join(REPO, "build", deviceName, "live", runStamp));
  const findings = [];
  const result = { device: path.relative(REPO, deviceFile), started: new Date().toISOString(), state: { git: gitState(deviceDir), runtime: runtimeFiles(deviceDir) }, options: { beats: opts.beats, tempo: opts.tempo, notes, sets }, findings };
  const fail = (what) => { findings.push(what); console.log(`FAIL ${what}`); };
  const pass = (what) => console.log(`PASS ${what}`);

  const live = await connect({ timeout: 5000 });
  let dut = null, rec = null;
  try {
    // Preconditions: a Set the harness made, 32-bit float takes, the build in exactly one Places folder.
    const setFile = await live.get("song", "file_path");
    if (!opts.anySet && !(setFile && inHarnessTemp(setFile))) {
      console.error(`check-instrument: the open Set (${setFile || "never saved"}) was not started by the harness; `
        + "relaunch Live with harness/relaunch.js (after the user confirmed Live is free) or pass --any-set if the user said it is disposable");
      return 2;
    }
    await requireRecordBitDepth(32);
    result.sampleRate = (await sampleRate()).rate;
    const places = await live.query("/live/browser/get/places_with", build);
    const problem = placesProblem(build, deviceDir, places);
    if (problem) {
      console.error(`check-instrument: ${problem}`);
      return 2;
    }

    // 2. Load.
    dut = await live.createMidiTrack(DUT);
    live.set("track", "volume", dut, float(0));
    const since = Date.now();
    const device = await live.loadDevice(dut, "*", build, { settleMs: 30000, readyMs: 2000 });
    live.set("track", "arm", dut, 0);
    await live.sync();
    pass(`loaded ${build} on track ${dut} as device ${device}`);

    // 3. Console since the load.
    await new Promise((r) => setTimeout(r, 1000));
    const liveLog = (await maxMessages({ since })).map((l) => ({ ...l, log: "Log.txt" }));
    const plugLog = fs.existsSync(MAXPLUGLIB) ? maxPlugLibLines(fs.readFileSync(MAXPLUGLIB, "utf8"), since) : [];
    const maxVersion = fs.existsSync(MAXPLUGLIB) ? (fs.readFileSync(MAXPLUGLIB, "utf8").match(/Max is starting: Version ([^\n]+)/g) || []).pop() : null;
    const consoleLines = classify([...liveLog, ...plugLog]);
    result.max = maxVersion;
    result.console = consoleLines;
    for (const e of consoleLines.errors) fail(`console: ${e.text} (${e.log})`);
    for (const re of opts.expectPost) {
      if (consoleLines.lines.some((l) => new RegExp(re).test(l.text))) pass(`console has /${re}/`);
      else fail(`console lacks /${re}/`);
    }
    if (!consoleLines.errors.length) pass(`console: ${consoleLines.lines.length} lines since the load, no errors, ${consoleLines.warnings.length} warnings`);

    // 4. Parameters: Live lists Device On, then the visible ones in code-unit order of the long name.
    const q = async (what) => (await live.query(`/live/device/get/parameters/${what}`, dut, device)).slice(2);
    const lom = { name: await q("name"), min: await q("min"), max: await q("max"), value: await q("value"), quantized: await q("is_quantized") };
    const mapping = mapParameters(lom.name.slice(1), visible);
    const rows = [];
    if (lom.name.length - 1 !== visible.length) {
      fail(`parameters: Live lists ${lom.name.length - 1} after Device On, the .amxd declares ${visible.length} visible`);
    }
    if (!mapping.sortedOrder) fail("parameters: Live's order is not the long names' code-unit order; matched by short name instead");
    for (const name of mapping.unmatched) fail(`parameter "${name}" in Live has no unique declared parameter`);
    for (let i = 0; i < mapping.list.length; i++) {
      const e = mapping.list[i], at = i + 1;
      if (!e) continue;
      const row = { index: at, longname: e.longname, live: { name: lom.name[at], min: lom.min[at], max: lom.max[at], value: lom.value[at] }, declared: e, problems: [] };
      if (lom.name[at] !== e.shortname && !e.longname.endsWith(lom.name[at])) row.problems.push(`name "${lom.name[at]}", declared "${e.shortname}"`);
      if (!near(lom.min[at], e.min, e.max - e.min) || !near(lom.max[at], e.max, e.max - e.min)) row.problems.push(`range ${lom.min[at]}..${lom.max[at]}, declared ${e.min}..${e.max}`);
      if (e.initial !== null && !near(lom.value[at], lomValue(e, e.initial), e.max - e.min)) {
        row.problems.push(`value after load ${lom.value[at]}, initial ${e.initial} (LOM ${lomValue(e, e.initial)})`);
      }
      if (e.type === 2) {
        const items = (await live.query("/live/device/get/parameter/value_items", dut, device, at)).slice(3);
        if (JSON.stringify(items) !== JSON.stringify(e.enum)) row.problems.push(`items [${items.join(", ")}], declared [${e.enum.join(", ")}]`);
        row.live.items = items;
      }
      if (e.type === 2 || e.exponent !== 1) {
        row.live.text = (await live.query("/live/device/get/parameter/value_string", dut, device, at)).slice(3)[0];
      }
      for (const p of row.problems) fail(`parameter ${e.longname}: ${p}`);
      rows.push(row);
    }
    result.parameters = rows;
    if (rows.every((r) => !r.problems.length) && lom.name.length - 1 === visible.length && mapping.sortedOrder && !mapping.unmatched.length) {
      pass(`parameters: ${rows.length} match the .amxd`);
    }

    // 5. Settings, clip, silent recording.
    for (const { name, value } of sets) {
      const index = mapping.list.findIndex((p) => p && p.longname === name) + 1;
      if (index < 1) throw new Error(`--set ${name}: no visible parameter with that long name`);
      let number = value;
      if (typeof value === "string") {
        const items = (await live.query("/live/device/get/parameter/value_items", dut, device, index)).slice(3);
        number = items.indexOf(value);
        if (number < 0) throw new Error(`--set ${name}: no item ${value} (items: ${items.join(", ")})`);
      }
      live.setParameter(dut, device, index, float(number));
    }
    live.set("song", "tempo", float(opts.tempo));
    await live.sync();
    await live.placeClip(dut, notes, opts.beats);
    live.send("/live/clip_slot/delete_clip", dut, 0);
    rec = await live.createAudioTrack(REC);
    await live.setInputRouting(rec, DUT, "Post FX");
    live.set("track", "current_monitoring_state", rec, MONITOR_OFF);
    live.set("track", "volume", dut, float(0));
    await live.sync();
    const dutVolume = await live.get("track", "volume", dut);
    const recMonitor = await live.get("track", "current_monitoring_state", rec);
    if (dutVolume !== 0 || recMonitor !== MONITOR_OFF) {
      console.error(`check-instrument: not silent (device track volume ${dutVolume}, recording monitor ${recMonitor}); not playing`);
      return 2;
    }
    live.set("track", "arm", rec, 1);
    try {
      await live.recordArrangement({ start: 0, length: opts.beats, tracks: [rec] });
    } finally {
      live.set("track", "arm", rec, 0);
      await live.sync();
    }
    const take = await recordedSamples(live, rec);
    fs.mkdirSync(out, { recursive: true });
    fs.copyFileSync(take.file, path.join(out, "take.wav"));
    result.take = { file: path.relative(REPO, path.join(out, "take.wav")), sampleRate: take.sampleRate, bits: take.bits, float: take.float };

    // 6. Health of the take.
    const h = health(take.channels);
    result.health = h;
    h.forEach((c, ch) => {
      if (c.nonFinite) fail(`take channel ${ch}: ${c.nonFinite} non-finite samples`);
      if (c.peak < 1e-3) fail(`take channel ${ch}: silent (peak ${c.peakDb.toFixed(1)} dBFS)`);
      if (c.peak > 1 + 1e-6) fail(`take channel ${ch}: peak ${c.peak.toFixed(3)} above the safety clip`);
      if (Math.abs(c.dc) > 0.05) fail(`take channel ${ch}: DC ${c.dc.toFixed(3)}`);
    });
    if (!h.some((c) => c.nonFinite || c.peak < 1e-3 || c.peak > 1 + 1e-6 || Math.abs(c.dc) > 0.05)) {
      pass(`take: ${h.map((c) => `peak ${c.peakDb.toFixed(1)} dBFS, rms ${c.rmsDb.toFixed(1)} dBFS`).join(" | ")}`);
    }
  } finally {
    if (!opts.keep && (dut !== null || rec !== null)) await live.deleteTracks([DUT, REC]).catch((error) => console.error(`cleanup: ${error.message}`));
    live.close();
    fs.mkdirSync(out, { recursive: true });
    result.finished = new Date().toISOString();
    fs.writeFileSync(path.join(out, "result.json"), JSON.stringify(result, null, 2));
    console.log(`result: ${path.relative(REPO, path.join(out, "result.json"))}`);
  }
  console.log(findings.length ? `FAIL (${findings.length} findings)` : "PASS");
  return findings.length ? 1 : 0;
}

if (process.argv[1] && path.resolve(process.argv[1]) === path.resolve(new URL(import.meta.url).pathname)) {
  main().then((code) => process.exit(code), (error) => {
    console.error(`check-instrument: ${error.stack || error}`);
    process.exit(2);
  });
}
