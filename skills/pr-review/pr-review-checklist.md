# PR Review Checklist

Apply every check explicitly. **Phase 1** runs before delegating to `generic-review`. **Phase 2** runs after generic-review produces draft findings (see `SKILL.md`).

## Phase 1 — Before generic-review

### PR Context Collection

- Read PR overview with `gh pr view <url> --json title,body,baseRefName,headRefName,author,changedFiles,additions,deletions,mergeStateStatus`.
- Gather review comments and threads with `gh pr view <url> --comments` and `gh api` queries when thread resolution state is required. Use read-only `gh api` for inline review comments on the PR (for example pull review comments) when `--comments` does not expose enough thread detail.
- Review commit history and discussion chronology to understand why changes were made.
- Detect project language mix from repository signals (for example `go.mod`, `pyproject.toml`) and changed file types.

### Mandatory Diff Review

- Fetch and retain the full PR diff with `gh pr diff <url>`.
- Ensure the diff includes every changed file; pass this full diff to
  `generic-review` for risk analysis and findings.
- Ensure mandatory full-diff inspection is executed in
  `generic-review-checklist.md`; do not skip that review step.

### Comment Resolution Validation

- Check whether all prior review comments are addressed in code.
- For resolved conversations, verify the final code actually satisfies the concern.
- Flag resolutions that are stale, incomplete, or unsupported by code changes.
- List unresolved threads and any resolved-but-questionable threads in the report.

### Output order (PR reviews)

- The final written review MUST follow `../../prompts/review-shared/output-template.md` section order. For PR URLs, the **Pull request context** block (title, link, full PR **body**, base/head, author) MUST appear **first**, before **GitHub Review Comments** (numbered findings).

## Phase 2 — After generic-review output

### Suppress duplicate PR comments

- Use **all** thread sources collected in Phase 1 (issue comments, review summaries, inline review comments).
- For each candidate finding in **GitHub Review Comments**, **omit** it from the numbered list if a prior PR comment or review already raises the **same concrete concern** on the **same or overlapping code** (file and line or region). Match on substance, not exact wording.
- **Still emit a finding** when: the earlier thread is stale relative to the current diff, the concern was marked resolved but the code still violates it, or the new finding is a **distinct** sub-issue not covered by the earlier comment.
- Record suppressed items briefly under **Findings not repeated (already in PR discussion)** in the output template — not as full duplicate comments.
