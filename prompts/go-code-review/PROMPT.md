---
name: go-code-review
description: Go review checklist — correctness, security, concurrency safety, and test coverage.
---
# Go Code Review

## Scope

Use for Go review only. Apply all checklist item.

Apply [`../review-policy/PROMPT.md`](../review-policy/PROMPT.md).

## Review Workflow

1. Read [`../review-shared/general-review-requirements.md`](../review-shared/general-review-requirements.md) and apply all requirement.
2. Read [`go-review-checklist.md`](go-review-checklist.md) and execute every check.
3. Inspect changed and impacted call path, not just edited line.
4. Prioritize finding by user impact and failure likelihood.
5. Report finding use [`../review-shared/output-template.md`](../review-shared/output-template.md).

## Required Focus Areas

- Error handling and contextual wrapping consistency.
- Context propagation and cancellation behavior.
- Concurrency correctness, goroutine lifecycle safety, and shared-state protection.
- Logging quality without secret or payload leakage.
- Failure-path and boundary-condition test coverage.
