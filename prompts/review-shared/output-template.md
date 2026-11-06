# Review Output Template

Use this output format for reviews.

Sections in order: **GitHub Review Comments** → **Open Questions** → **Discussion Resolution Check** → **Coverage Check** → **Change Summary**.

## GitHub Review Comments (Ready To Paste)

For each finding, output metadata fields (File, Line) as plain text then comment body as regular markdown. Output file already markdown document, no wrap comment body in fenced code block. Write as normal markdown prose for correct render.

Each finding is **1–3 sentences total**: what is wrong and how to fix it. Fold risk/impact into the issue sentence only when not obvious from context. Include a code block only when the fix cannot be stated clearly in words.

Template (repeat per finding, increment number):

### Comment 1

File: BACKTICK path/to/file BACKTICK
Line: BACKTICK 42 BACKTICK

Issue and fix in 1–3 sentences.

### Comment 2

...

In template above, replace BACKTICK with single backtick character. Placeholder used here only because real backticks inside template consumed by markdown parser instead of reproduced in output.

**Deleted-line findings:** When finding about code **removed** in diff, deleted lines have no valid line number in current file. Use nearest surviving line as anchor and note deletion explicitly — e.g., Line: BACKTICK 139 BACKTICK (deleted line — visible only in diff). Never cite line number pointing to unrelated code in current file.

## Open Questions

Before list anything here, **try answer question yourself** from diff, surrounding code, tests, configs, and (for PR reviews) PR body or linked context. Read call sites, types, existing tests; search repo for related behavior. **List only questions remain unanswerable** from what you can inspect.

No preamble. **One bullet per remaining question**, or **exactly one** bullet `- None` if investigation resolved every uncertainty (no mix question bullets with `- None`).
- \<each question stays unanswered after investigation\>

## Discussion Resolution Check

One line when all clear: `- Prior discussions: all resolved and verified` (or `- No prior discussions` when none exist). List bullets **only** for unresolved or resolved-but-questionable discussions.

## Coverage Check

Default single line when nothing is open:

`All applicable checklists complete (Go/Python/KFP as applicable); no open gaps.`

Add explicit bullets **only** for:
- incomplete or skipped checklists (with reason, including tool availability such as `golangci-lint`)
- adversarial scenario gaps still open

Silence means complete.

## Change Summary

Reviewer concise read of **what diff does and whether hangs together** — 2–4 sentences max, **not** repeat of PR body.
