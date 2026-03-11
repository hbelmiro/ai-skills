---
name: go-code-review
description: Review Go code for correctness, security, concurrency safety, and test coverage using project review standards. Use when reviewing Go pull requests, backend changes, controllers, services, or when the user asks for a golang code review.
---

# Go Code Review

## Scope

Use this skill for Go-only reviews. Apply every checklist item explicitly.

## Review Workflow

1. Read `../review-shared/general-review-requirements.md` and apply all requirements.
2. Read `../review-shared/go-review-checklist.md` and execute every check.
3. Inspect changed and impacted call paths, not just edited lines.
4. Prioritize findings by user impact and failure likelihood.
5. Report findings using:
   - `../review-shared/severity-rubric.md`
   - `../review-shared/output-template.md`

## Required Focus Areas

- Error handling and contextual wrapping consistency.
- Context propagation and cancellation behavior.
- Concurrency correctness, goroutine lifecycle safety, and shared-state protection.
- Logging quality without secret or payload leakage.
- Failure-path and boundary-condition test coverage.

