# PR Review Skill

Review GitHub pull requests from a PR URL using `gh`, with mandatory full-diff review and comment-resolution validation.

## Files

- `SKILL.md`: Entrypoint and routing workflow.
- `pr-review-checklist.md`: Mandatory PR-specific checks.

## Usage

Use when a user shares a pull request URL or asks for a PR review. The skill routes to Kubeflow Pipelines review for KFP/DSP repositories; otherwise it applies language-specific review checklists based on project languages.
