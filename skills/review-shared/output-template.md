# Review Output Template

Use this output format for reviews.

## Document order

- **PR-linked reviews** (started from a PR URL via `pr-review`): present sections in this order — **Pull request context** → **GitHub Review Comments** → **Findings not repeated (already in PR discussion)** → **Open Questions** → **Discussion Resolution Check** → **Coverage Check** → **Change Summary**.
- **Non-PR reviews** (`generic-review` only, no PR URL): **omit** **Pull request context** and **Findings not repeated** entirely.

## Pull request context (PR reviews only)

Place this section **first** in the document (before numbered findings). Reproduce the author’s intent from `gh pr view`; do not bury the PR body at the end of the review.

Include at minimum:

- **Title:** (PR title)
- **URL / number:** (link or owner/repo#n)
- **Description (author body):** full PR body as returned by `gh pr view` (preserve structure; use normal markdown)
- **Base / head:** branch or ref names
- **Author:** from PR JSON

Optional: changed file count, additions/deletions from PR JSON.

**Non-PR reviews:** omit this entire section.

## GitHub Review Comments (Ready To Paste)

For each finding, output the metadata fields (File, Line, Severity) as plain
text followed by the comment body as regular markdown. Since the output file is
already a markdown document, do NOT wrap the comment body in a fenced code
block. Write it as normal markdown prose so it renders correctly, including any
embedded code blocks for suggested fixes.

Template (repeat for each finding, incrementing the number):

### Comment 1

File: BACKTICK path/to/file BACKTICK
Line: BACKTICK 42 BACKTICK
Severity: BACKTICK High BACKTICK

Description of the issue — what is wrong.

**Why it matters:** impact and risk description. (Include only when the risk is
not obvious from the context. Omit for self-evident issues.)

**Suggested fix:** concrete remediation with code if applicable.

### Comment 2

...

In the template above, replace BACKTICK with a single backtick character.
The placeholder is used here only because real backticks inside this template
would be consumed by the markdown parser instead of being reproduced in output.

## Findings not repeated (already in PR discussion)

**PR reviews only.** Omit this section when not PR-linked or when nothing was suppressed.

For each suppressed finding (same concern already raised on the PR), add one bullet: what was skipped, which prior thread it matches (author, short quote, or permalink if available). If a **new** finding **narrows** or **replaces** a duplicate rather than duplicating it, note that there instead of repeating the issue twice in **GitHub Review Comments**.

## Open Questions

- \<question where intended behavior is unclear\>

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
- Adversarial scenario gaps still open: list or "none"

## Change Summary

The reviewer’s concise read of **what the diff does and whether it hangs together** — **not** a repeat of the PR body (the author description belongs in **Pull request context**).
