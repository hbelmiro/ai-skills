---
name: pr-review
description: Review GitHub pull requests from a PR URL using gh, including full diff inspection, addressed-comment validation, then the generic-review pipeline for routing and output. Use when the user shares a PR link or asks for a pull request review.
---

# PR Review

## Scope

Use this skill when the user provides a pull request URL or asks for a full PR review.

## Review workflow

1. Parse owner/repo/PR number from the provided URL.
2. Read `pr-review-checklist.md` and execute every check (PR context, full diff via `gh`, comment-thread validation).
3. Read and follow `../generic-review/SKILL.md` for the remainder of the review. **Do not** duplicate `general-review-requirements` or routing steps before that—`generic-review` owns them.
4. When continuing from this skill: **skip** diff-acquisition commands in `../generic-review/generic-review-checklist.md` and use the diff already obtained with `gh pr diff <url>`.

## Routing rules

Routing to specialized skills is defined in `../generic-review/SKILL.md` (KFP/DSP precedence, then Go/Python; multiple languages when materially changed; state limitations if a language skill is unavailable).
