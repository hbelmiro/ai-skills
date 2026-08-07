# PR Review Checklist

Run all checks. **Phase 1** before `generic-review`. **Phase 2** after draft findings (see `SKILL.md`).

## Phase 1 — Before generic-review

### PR Context Collection

- Read PR overview with `gh pr view <url> --json title,body,baseRefName,headRefName,author,changedFiles,additions,deletions,mergeStateStatus`.
- Gather review comments with `gh pr view <url> --comments` and `gh api` when thread state needed. Use read-only `gh api` for inline review comments when `--comments` miss detail.
- Review commit history + discussion timeline. Understand why changes made.
- Detect project language from signals (`go.mod`, `pyproject.toml`) + changed file types.

### Mandatory Diff Review

- Fetch full PR diff with `gh pr diff <url>`.
- Diff include all changed files. Pass full diff to `generic-review` for risk analysis.
- Run mandatory full-diff inspection in [`generic-review-checklist.md`](../generic-review/generic-review-checklist.md). No skip.

### Comment Resolution Validation

- Check all prior review comments addressed in code.
- For resolved conversations, verify final code satisfy concern.
- Flag resolutions: stale, incomplete, unsupported by code changes.
- List unresolved threads + questionable resolved threads in report.

### Output order (PR reviews)

- Final review MUST follow [`../../prompts/review-shared/output-template.md`](../../prompts/review-shared/output-template.md) section order. For PR URLs, **Pull request context** block (title, link, full PR **body**, base/head, author) MUST appear **first**, before **GitHub Review Comments** (numbered findings).

## Phase 2 — After generic-review output

### Suppress duplicate PR comments

- Use **all** thread sources from Phase 1 (issue comments, review summaries, inline review comments).
- For each finding in **GitHub Review Comments**, **omit** from numbered list if prior PR comment raise **same concern** on **same code** (file + line/region). Match substance, not wording.
- **Still emit finding** when: earlier thread stale vs current diff, concern marked resolved but code still violate, new finding **distinct** sub-issue not covered by earlier comment.
- Record suppressed items brief under **Findings not repeated (already in PR discussion)** in output template. Not full duplicate comments.