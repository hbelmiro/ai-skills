# PR Review Checklist

Apply every check explicitly.

## PR Context Collection

- Read PR overview with `gh pr view <url> --json title,body,baseRefName,headRefName,author,changedFiles,additions,deletions,mergeStateStatus`.
- Gather review comments and threads with `gh pr view <url> --comments` and `gh api` queries when thread resolution state is required.
- Review commit history and discussion chronology to understand why changes were made.
- Detect project language mix from repository signals (for example `go.mod`, `pyproject.toml`) and changed file types.

## Mandatory Diff Review

- Fetch and retain the full PR diff with `gh pr diff <url>`.
- Ensure the diff includes every changed file; pass this full diff to
  `generic-review` for risk analysis and findings.
- Ensure mandatory full-diff inspection is executed in
  `generic-review-checklist.md`; do not skip that review step.

## Comment Resolution Validation

- Check whether all prior review comments are addressed in code.
- For resolved conversations, verify the final code actually satisfies the concern.
- Flag resolutions that are stale, incomplete, or unsupported by code changes.
- List unresolved threads and any resolved-but-questionable threads in the report.
