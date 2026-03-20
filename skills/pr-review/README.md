# PR Review Skill

Review GitHub pull requests from a PR URL using `gh`, with mandatory full-diff review and comment-resolution validation, then the shared [`generic-review`](../generic-review/) pipeline for routing and output.

## Files

- `SKILL.md`: Entrypoint; PR prelude then delegates to `generic-review`.
- `pr-review-checklist.md`: Mandatory PR-specific checks (`gh`, threads).

## Usage

Use when a user shares a pull request URL or asks for a PR review. After PR context and diff collection, routing matches `generic-review` (KFP/DSP when applicable, otherwise Go/Python by project signals).
