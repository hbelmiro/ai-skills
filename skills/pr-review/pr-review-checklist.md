# PR Review Checklist

Apply every check explicitly.

## PR Context Collection

- Read PR overview with `gh pr view <url> --json title,body,baseRefName,headRefName,author,changedFiles,additions,deletions,mergeStateStatus`.
- Gather review comments and threads with `gh pr view <url> --comments` and `gh api` queries when thread resolution state is required.
- Review commit history and discussion chronology to understand why changes were made.
- Detect project language mix from repository signals (for example `go.mod`, `pyproject.toml`) and changed file types.

## Mandatory Diff Review

- Review the full PR diff (`gh pr diff <url>`) before reporting findings.
- Do not limit review to selected files or snippets when assessing correctness and risk.
- Inspect impacted call paths and cross-file effects, not only edited lines.

## Comment Resolution Validation

- Check whether all prior review comments are addressed in code.
- For resolved conversations, verify the final code actually satisfies the concern.
- Flag resolutions that are stale, incomplete, or unsupported by code changes.
- List unresolved threads and any resolved-but-questionable threads in the report.
