# PR Review to File

Review a GitHub pull request via [`pr-review`](../pr-review/) and save the
review output to `.hbelmiro/reviews/` for the record. The agent
**never** commits or pushes; the user owns git history and remotes.

## Files

- `SKILL.md` — entrypoint and workflow rules
- `artifact.json` — Striatum manifest and dependencies
- `pr-review-to-file-checklist.md` — ordered checks

## Install

See the [root README](../../README.md#installing-skills). Installing this skill
pulls **`pr-review`** (and its transitive review stack).
