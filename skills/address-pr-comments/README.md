# Address PR comments

Workflow skill for implementing **review feedback** from a GitHub PR URL: collect
threads via the shared [`pr-review`](../pr-review/) Phase 1 checklist, fix what
makes sense (including bot nitpicks when appropriate), use
[`tdd`](../tdd/) when behavior or tests should lead, then run
[`generic-review`](../generic-review/) in a **fresh-eyes** fix loop on the
current git diff until clear, and only then present a **full comment-by-comment
summary** of what was fixed, skipped, or deferred. The agent **never** commits
or pushes; the user owns git history and remotes.

## Files

- `SKILL.md` — entrypoint and workflow rules
- `artifact.json` — Striatum manifest and dependencies
- `address-pr-comments-checklist.md` — ordered checks

## Install

See the [root README](../../README.md#installing-skills). Installing this skill
pulls **`tdd`** and **`pr-review`** (and their shared transitive review stack,
including `generic-review`).
