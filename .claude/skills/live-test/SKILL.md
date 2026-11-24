---
name: live-test
description: Hand a device state to the user for a test in Max or Live and keep the paper trail - the offline checks before, the handover (what to load, what to listen for, what to report), and the test log once the user reports back. Use this whenever something is meant to run in Max or Live - a first load, a console check, a listening test, an A/B against the Reaktor original, a CPU reading, "kannst du das testen lassen", "ich will das in Live hören", "lade ich mal" - and whenever the user reports what a device did (console errors, what was heard, CPU, screenshots), even without mentioning a log.
---

# Test in Max / Live

Claude cannot hear and does not drive Max or Live. Every test is a round trip through the user,
which costs minutes (open Live, load, set up limiter, play, copy the console), so each one must be
traceable and worth it:

**change → offline checks → handover → the user tests → report → test log**

Roles: Claude builds, checks and records. The **user** loads the device, plays, listens, reads
the Max console and reports. Nothing written may claim a device ran in Max/Live before the user
says so.

## 1. Before the handover

- **Know what the test is for** and what the user should check. One question per test where
  possible ("does it compile with audio on", "does voice stealing click", "A/B snapshot 3 vs.
  Reaktor render"). If the current state cannot answer it, say so instead of handing it over.
- **Run the offline checks** and fix failures first: `tools/check.sh <device>` (gencheck +
  `.gendsp` regeneration, TS build, patch validation, maxdiff summary) and the device's offline
  tests (reference model, null tests). Never hand over a state with failing checks.
- **Pick the label:** `t<N>` for a test of `devices/<name>/`, continuing the series in
  `testlog/<name>/` (`ls` it). The label names the state, not the result.
- **Record the state** before handing over (the log needs it later): git short SHA, whether the
  tree is dirty (`git status --short` for the device folder; save `git diff` of the device to
  `testlog/<name>/<label>.diff` if dirty), SHA-256 of the runtime files in `devices/<name>/`
  (`.amxd`, `.gendsp`, `.js`), Max version the user will test in.
- **Riders:** open checks in `TODO.md` ("Open checks in Max/Live") that the same session can
  answer cheaply go at the end of the handover.

## 2. Hand over

Tell the user, in the user's language, without making them open any file:

1. what changed since the last test and what this test should answer,
2. what to load and where: the clickable path of the `.amxd` (or the test patch), and whether
   to reload a device that is already open (hot reload of `.gendsp`/`.js` vs. reopening),
3. **safety first:** limiter after the device, monitor turned down, especially on first load,
4. exactly what to do: notes/range to play, parameter settings (by their panel names), the
   Reaktor reference to compare against if any,
5. what to report: the full Max console (copy all, including warnings), what was heard (in
   their own words), CPU meter reading if relevant, screenshots of anything visual,
6. the way back if something breaks (previous tag/commit, or remove the device from the set).

Then stop and wait for the report.

## 3. Test log

When the user reports back, write it down **before** doing anything else: the user's
observations are measurements and the next session has no other source for them. For tests
in Live, also read the newest `~/Library/Preferences/Ableton/Live */Log.txt` (read-only) for
`Message from Max` lines of this device since the test started, and log them next to what the
user copied (filter out unrelated stock-device errors).

`testlog/<name>/<YYYY-MM-DD>.md` (local only, gitignored), one `##` section per test:

```markdown
## <label> — <one-line purpose>

- State: <short SHA>, <clean | dirty: testlog/<name>/<label>.diff>, runtime files
  <sha256 prefixes>, Max <version> in <Live 12.x | Max standalone>.
- Tested by the user: <how: device in Live / test patch in Max; limiter yes/no>.
- Console: <verbatim errors/warnings, or "clean", or "not reported">
- Observed (user): "<their words, original language>" — <English rendering> [measured, user report]
- Readings: <table: parameter settings, notes, CPU, A/B result; enough to read without the build>
- Riders: <result of each piggybacked check, or "not done">
- Interpretation [hypothesis]: <your reading, kept apart from the observations>
- Follow-up: <next change or decision>
```

Keep observation and interpretation apart and mark them. What was not reported is "not
reported", not a guess. If a report contradicts the code, log it as `[open]` instead of
smoothing it over. A later correction is a new entry, never a rewrite.

Then answer the user: what you logged, what it means, and — once, together — the missing
conditions that matter for the conclusion.

## 4. Afterwards

- Carry durable results out of the local log: `TODO.md` (done/open items, open checks),
  `CLAUDE.md` "Status", the device's `docs/` (port status, measured CPU, known deviations from
  the original).
- Upgrade evidence markers only as far as the observation reaches, with a reference to the log
  entry (`testlog/<name>/<date>.md, <label>`).
- Commits only after the user approved the commit by name.
