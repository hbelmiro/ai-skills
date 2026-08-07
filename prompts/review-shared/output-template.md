# Review Output Template

Use format for reviews.

## Document order

- **PR-linked reviews** (from PR URL via `pr-review`): order sections — **Pull request context** → **GitHub Review Comments** → **Findings not repeated (already in PR discussion)** → **Open Questions** → **Discussion Resolution Check** → **Coverage Check** → **Change Summary**.
- **Non-PR reviews** (`generic-review`, no PR URL): **omit** **Pull request context** and **Findings not repeated** entirely.

## Pull request context (PR reviews only)

Place section **first** (before numbered findings). Reproduce author intent from `gh pr view`; no bury PR body at end.

Include minimum:

- **Title:** (PR title)
- **URL / number:** (link or owner/repo#n)
- **Description (author body):** full PR body from `gh pr view` (preserve structure; use normal markdown)
- **Base / head:** branch or ref names
- **Author:** from PR JSON

Optional: file count, additions/deletions from PR JSON.

**Non-PR reviews:** omit section.

## GitHub Review Comments (Ready To Paste)

For each finding, output metadata fields (File, Line) as plain text then comment body as regular markdown. Output file already markdown document, no wrap comment body in fenced code block. Write as normal markdown prose for correct render, include embedded code blocks for suggested fixes.

Template (repeat per finding, increment number):

### Comment 1

File: BACKTICK path/to/file BACKTICK
Line: BACKTICK 42 BACKTICK

Description of the issue — what is wrong.

**Why it matters:** impact and risk description. (Include only when the risk is
not obvious from the context. Omit for self-evident issues.)

**Suggested fix:** concrete remediation with code if applicable.

### Comment 2

...

In template above, replace BACKTICK with single backtick character. Placeholder used here only because real backticks inside template consumed by markdown parser instead of reproduced in output.

**Deleted-line findings:** When finding about code **removed** in diff, deleted lines have no valid line number in current file. Use nearest surviving line as anchor and note deletion explicitly — e.g., Line: BACKTICK 139 BACKTICK (deleted line — visible only in diff). Never cite line number pointing to unrelated code in current file.

## Findings not repeated (already in PR discussion)

**PR reviews only.** Omit section when not PR-linked or nothing suppressed.

For each suppressed finding (same concern already raised on PR), add bullet: what skipped, which prior thread matches (author, short quote, or permalink if available). If **new** finding **narrows** or **replaces** duplicate rather than duplicate it, note there instead of repeat issue twice in **GitHub Review Comments**.

## Open Questions

Before list anything here, **try answer question yourself** from diff, surrounding code, tests, configs, and (for PR reviews) PR body or linked context. Read call sites, types, existing tests; search repo for related behavior. **List only questions remain unanswerable** from what you can inspect in repository and materials already in scope for review.

In rendered review, use **one bullet per remaining question**, or **exactly one** bullet `- None` if investigation resolved every uncertainty (no mix question bullets with `- None`).
- \<each question stays unanswered after investigation\>

## Discussion Resolution Check

- Prior comments/discussions reviewed: yes/no
- Unresolved discussions: list or "none"
- Resolved-but-questionable discussions: list or "none"

## Coverage Check

- Go baseline checklist: complete/incomplete
- Python baseline checklist: complete/incomplete
- KFP checklist (if applicable): complete/incomplete
- Independent reviewer mode applied: yes/no with brief evidence note
- Tests and edge cases reviewed: yes/no with notes
- Do tests cover enough scenarios?: yes/no with notes
- Broken link check: complete/incomplete
- Structural quality check: complete/incomplete
- Adversarial scenario gaps still open: list or "none"

## Change Summary

Reviewer concise read of **what diff does and whether hangs together** — **not** repeat of PR body (author description belongs in **Pull request context**).