# Lens: code

You check that what the document says about the device matches the files.

- For every path, file, object, parameter (name, range, unit, default, count), constant,
  formula, routing and behaviour the scope states: open the file and compare.
- Generated files (`*.gendsp`, bundled `*.js` next to the `.amxd`) come from
  `gen/*.genexpr` and `js/src/*.ts`. Compare against the sources; say so if a generated file
  looks stale (its header names its source).
- The reverse direction: behaviour in the code within the scope's topic that the document does
  not mention, when it would change what a reader expects (an extra clamp, a different
  default, a parameter the document does not list).
- Commands and scripts the document tells someone to run: do they exist, with these arguments?
- [measured] claims: does the referenced log or script exist and say that?

You cannot run anything. Where only a run in Max or Live would tell, write "not checkable by
reading" instead of guessing.

## Output

For each finding:

- **Severity:** blocker | major | nit (standard, "Severity")
- **Where:** document file:line or decision id
- **Finding:** what disagrees
- **Evidence:** both sides: document file:line (quote) vs. code file:line (quote)
- **Suggestion:** which side probably needs to change, and how

End with `Coverage: <ids or sections you checked>`. If the scope is sound, write
"No finding" and the coverage line.
