---
name: fresh-review
description: Review a document of this workbench with fresh eyes - read-only reviewer subagents that see the document, its sources and the code but none of this conversation check it against the project's standard through one or more lenses (trace, code, risk, reader); this session consolidates the findings into a local report and the user decides. Use it for decision lists Claude made (e.g. A1-A33 in v0.2-build.md), build notes and specs before a test or release, handovers and checklists the user will execute, and to check whether a doc still matches the code - "frischer Blick", "fresh eyes", "goldfish", "lass das gegenprüfen", "stimmt die Doku noch", "review the decisions". Not for reviewing a code diff (code-review) and not for questioning the user (grilling).
---

# Fresh review

The session that made decisions or wrote a document is its worst reader: it knows what was
meant, so it does not see what is missing, assumed or contradicted. A reviewer that starts
without this conversation reads only what is on the page and in the repo. (Idea from the
Elephant-Goldfish Model, github.com/google/elephant-goldfish-model, evaluated 2026-11-25; this
is our own minimal version instead of the plugin.)

Roles: the **reviewers** (subagent `fresh-reviewer`, read-only) find problems. **This session**
briefs them, consolidates and gives its own view on each finding. The **user** decides. The
target does not change during the review.

## 1. Intake

- **Target:** one file, optionally a scope (section heading, decision ids, line range). Re-read
  it now; line numbers come from this read.
- **Kind → default lenses** (lens files: `.claude/skills/fresh-review/lenses/<lens>.md`; the
  user can add or drop lenses):

  | Kind | Example | Lenses |
  |---|---|---|
  | Decision list | `v0.2-build.md` §1, `port-decisions.md` | trace, code, risk |
  | Build notes / spec | `v0.2-build.md` §2–§5, `gui.md` | code, risk, trace |
  | Handover / checklist | `v0.2-build.md` §6, a handover saved to a file | reader, code |
  | Research note | `docs/research/notes/*` | trace |

- **Context list**, built mechanically from the scope: every repo file it links or names by
  path, plus the documents its decisions cite as their source (`redesign-t1.md` for R-ids,
  `port-decisions.md` for Q-ids, `feedback-t1.md`, a cited test log entry). Do not add or leave
  out files by what you expect the review to find. Never in the list: `docs/handoffs/`,
  `docs/reviews/`, `devices/*/reference/reaktor/`.
- **Long scope** (more than ~20 decisions or ~150 lines): split it into halves, one reviewer
  per lens and half.
- Say in one line what will run (target, scope, lenses, number of reviewers) and start. Ask
  only if the target or the scope is unclear.

## 2. Brief: the only thing a reviewer gets

Spawn one Agent per lens (and half), all in one message so they run in parallel.

- `subagent_type: "fresh-reviewer"`. If that type is not available in this session, use
  `general-purpose` and add the line "You are read-only: do not edit, write or run anything."
  **Never `fork`**: a fork inherits this conversation, which is what the review must not see.
- Model: the session's by default; `model: "sonnet"` only when the user asks for a quick pass.
- Prompt: the template below, filled in, and nothing else. No summary of the conversation, no
  reasons for decisions beyond what the document says, no hints where problems are, no "known
  issues", no verdict of your own. If something a reviewer needs exists only in this
  conversation, that is a gap in the document: leave it out and let the review find it.

```text
You are reviewing a document of the m4l-workbench repository (<absolute repo path>) with fresh eyes.
1. Read your lens: <repo>/.claude/skills/fresh-review/lenses/<lens>.md
2. Read the standard: <repo>/.claude/skills/fresh-review/standard.md
3. Target: <repo-relative path>, scope: <section / ids / lines a-b>. Read the whole file for
   orientation; report only on the scope.
4. Start with these files; open any other repo file you need, except docs/handoffs/,
   docs/reviews/ and devices/*/reference/reaktor/:
   - <repo-relative path>
   - ...
Report in the format your lens gives.
```

## 3. Consolidate

When all reviewers are back:

- A reviewer that failed or returned no report: retry once, otherwise record it as **not run**,
  never as "no findings".
- Merge duplicates (keep every lens that raised one). Number the findings F1, F2, …
- Check each finding in the repo yourself (open the cited file and line) before giving a view.
  Then add **Author's view**: `agree`, `contest: <reason with file:line or quote>`, or
  `user's call` (taste, priority, or a decision only the user can make). Contesting is allowed,
  dropping is not: every finding stays in the report.
- Write `docs/reviews/<YYYY-MM-DD>-<doc-stem>[-<scope>].md` (local only, gitignored):

  ```markdown
  # Fresh review: <target> <scope> (<date>)

  - Lenses: <lens: completed | not run>, model <model>, round <n>
  - Context given: <the list>

  | # | Sev | Lens | Where | Finding | Suggestion | Author's view |
  |---|---|---|---|---|---|---|

  ## Reader paraphrase
  <verbatim, reader lens only>
  ```

- Tell the user, in their language: the report path, counts by severity, each blocker and
  major in one line, and which findings you contest and why. Raw reviewer output stays out of
  the chat.

## 4. Afterwards

- Do not edit the target inside this skill. Decision lists (A-, R-, Q-ids) change only after
  the user has decided, best in one sitting, grilling style; other documents after the user
  says which findings to fix.
- Doc and code disagree: decide with the user which side is right, then fix that side; run
  `tools/check.sh <device>` after code changes.
- Second round only on request: new reviewers, the same brief, nothing from round 1. Mark
  repeats as "repeat of F<n> (round 1)"; a finding raised again after its fix means the fix did
  not land. Stop after two rounds unless the user asks for more.
- Carry results out: changed decisions go into the document with the review report named as
  the reason, open items into `TODO.md`.
