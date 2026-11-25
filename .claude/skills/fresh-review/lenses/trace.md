# Lens: trace

You check that every decision and claim in the scope stands on something, and that the
decisions agree with each other and with the decisions they build on.

For each decision or claim in the scope:

- **What does it rest on?** A user decision (Q-id, R-id, quoted user statement), a measurement
  (test log, script output), a linked source. When the document says it rests on X, open X
  and check that X says that.
- **Contradictions:** does it contradict a user decision, or another decision in the same or
  an earlier document, without saying that it replaces it?
- **Reason:** is the stated reason a reason, or only the decision said again? Is the stated
  cost of changing it ("Change?") plausible from what the document and code show?
- **Marker:** does the evidence marker match what backs it (standard §1)?

Do not judge whether a decision is a good idea musically, only whether it is grounded and
consistent. If a decision looks risky, add it as a nit and leave the rest to the risk lens.

## Output

For each finding:

- **Severity:** blocker | major | nit (standard, "Severity")
- **Where:** file:line or decision id
- **Finding:** what is wrong or missing
- **Evidence:** file:line or a short quote of what contradicts it, or where the backing should
  be and is not
- **Suggestion:** what would fix it

End with `Coverage: <ids or sections you checked>`. If the scope is sound, write
"No finding" and the coverage line.
