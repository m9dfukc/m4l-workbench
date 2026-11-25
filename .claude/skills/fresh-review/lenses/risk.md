# Lens: risk

You look for what can go wrong when this runs as a Max for Live device in Ableton Live: in the
DSP, the patch, the JavaScript and Live itself. Check the scope and the code it names.

- **Ears and speakers:** level jumps, feedback, filters blowing up at extreme settings
  (resonance, FM into filters, cutoff near Nyquist), modulation that pushes a value out of its
  safe range, a missing or bypassable safety stage (standard §4).
- **Numerics:** division by zero, nan/inf, denormals, `pow`/`log` of negative values, phase
  and index wrap at the table seam, state that has to survive a sample-rate change or a reload
  (`History`, `Data`, `Buffer`).
- **Max and Live:** differences between Max 9.1.5 and 9.2 (`.claude/rules/gen.md`), the JS
  thread (no audio in JS, low-priority timing), jspainter on the legacy ES5 engine, `live.*`
  parameter behaviour (automation, MIDI mapping, saving with the set, Push banks),
  transport and tempo edge cases (stopped transport, tempo changes, time signatures other than
  4/4, sample-rate changes), CPU with all voices running.
- **Edge cases of the stated behaviour:** first load, every parameter at its minimum and
  maximum, fast parameter changes, several instances of the device.

A risk the document already names and handles is not a finding. Name the concrete setting or
sequence that triggers each risk.

## Output

For each finding:

- **Severity:** blocker | major | nit (standard, "Severity")
- **Where:** document file:line or decision id, and code file:line if it applies
- **Trigger:** the setting or sequence that causes it
- **Finding:** what happens and why
- **Suggestion:** a mitigation, or a check for the next test in Live

End with `Coverage: <ids or sections you checked>`. If the scope is sound, write
"No finding" and the coverage line.
