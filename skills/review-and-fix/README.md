# Review and Fix

Workflow skill for reviewing the current change set and fixing issues in a loop:
run [`generic-review`](../generic-review/) with fresh eyes, fix accepted
findings (using [`tdd`](../tdd/) when behavior or coverage is in play), and
repeat until the review comes back clean. The clean review output is saved to
`<project>/.hbelmiro/reviews/` for the record. The agent **never** commits or
pushes; the user owns git history and remotes.

## Files

- `SKILL.md` — entrypoint and workflow rules
- `artifact.json` — Striatum manifest and dependencies
- `review-and-fix-checklist.md` — ordered checks

## Install

See the [root README](../../README.md#installing-skills). Installing this skill
pulls **`tdd`** and **`generic-review`** (and their shared transitive review
stack).
