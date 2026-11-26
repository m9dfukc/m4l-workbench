# Fresh-review standard (m4l-workbench)

The bar a reviewed document in this repository is held to. Your lens says which parts to apply.

## Rules and trust

- `CLAUDE.md` (roles, evidence markers, architecture, safety rules, Max compatibility) and the
  path rules in `.claude/rules/` (`gen.md`, `max-patch.md`, `v8-js.md`, `device-readme.md`) are
  the project's rules. Check the document against them.
- The status lines in `CLAUDE.md` and `TODO.md`, and every document under `devices/*/docs/`,
  were written by the same author as the target. What they say is a claim, not evidence.
  Evidence is code, script output, a test log, the user's recorded words, or a linked
  external source.
- The user's decisions outrank Claude's: Q-ids (`devices/aliasing/docs/port-decisions.md`),
  R-ids (`devices/aliasing/docs/redesign-t1.md`) and quoted user statements are the user's.
  A-ids and anything marked "(proposal)" are Claude's.

## A document passes if

1. **Evidence.** Every claim about Max, Live, Reaktor, the device's behaviour or a result
   carries the right marker: [sourced] with a link, [code], [hypothesis], [measured] with a
   reference to the test log or script, [open]. [measured] without a reference, or a marker
   stronger than its reference supports, fails. "Ran in Live" needs a test log.
2. **Traceability.** Each decision says what it rests on (a user decision, a measurement, a
   source) and contradicts no user decision and no earlier decision it does not explicitly
   replace.
3. **Code fit.** Paths, names, parameter names, ranges, units, defaults and counts, constants
   and behaviour that the document states match the files it names.
4. **Safety.** Development DSP ends in a safety stage (`fixnan`/`fixdenorm` + `clip`); no path
   can jump to full scale without the document saying so; every listening step comes after a
   limiter on the device's output and a turned-down monitor.
5. **Compatibility.** A device meant for release runs on stock Live's bundled Max 9.1.5:
   GenExpr passes gencheck for 9.1.5 and 9.2.0, jspainter code is ES5, no audio in JS, `live.*`
   parameters follow `reference/m4l-production-guidelines.md`.
6. **Executability** (handovers, checklists). The user can do every step without asking: what
   to load (path), settings by panel name, what to listen or look for, what counts as pass or
   fail, what to report, the way back.
7. **Language.** English; no term a reader of this repository would not know, unless it is
   explained.

## Severity

- **blocker**: risks ears or speakers, would break the device on stock Live, contradicts a user
  decision, or makes a handover step impossible.
- **major**: a claim without backing (missing or wrong marker or reference), doc and code
  disagree, a decision without a reason, a step a reader cannot do without asking.
- **nit**: wording, order, small omissions that would not change what anyone does.
