---
name: python-code-review
description: Python review checklist — correctness, security, type safety, and test coverage.
---
# Python Code Review

## Scope

Python-only reviews. Apply every checklist item.

Apply [`../review-policy/PROMPT.md`](../review-policy/PROMPT.md).

## Review Workflow

1. Read [`../review-shared/general-review-requirements.md`](../review-shared/general-review-requirements.md), apply all requirements.
2. Read [`python-review-checklist.md`](python-review-checklist.md), execute every check.
3. Inspect changed/impacted call paths, not just edited lines.
4. Prioritize findings by user impact, failure likelihood.
5. Report findings using [`../review-shared/output-template.md`](../review-shared/output-template.md).

## Required Focus Areas

- Exception handling, error propagation consistency.
- Type annotation coverage on public APIs.
- Resource cleanup via context managers.
- No `eval`/`exec`/`pickle` on untrusted input; no secrets in code/logs.
- Failure-path, boundary-condition test coverage.
