---
name: pr-review
description: Review a GitHub pull request with gh, then run the generic review pipeline.
---

# PR Review

Use when the user gives a PR URL or requests a full PR review.

1. Parse the owner, repository, and PR number.
2. Execute Phase 1 of [`pr-review-checklist.md`](pr-review-checklist.md).
3. Delegate the review to [`../generic-review/SKILL.md`](../generic-review/SKILL.md), using the PR diff already collected and skipping Git diff acquisition.
4. Execute Phase 2 of [`pr-review-checklist.md`](pr-review-checklist.md) before presenting results.
