---
name: python-code-review
description: Review Python code for correctness, security, type safety, and test coverage using project review standards. Use when reviewing Python pull requests, SDK changes, scripts, or when the user asks for a Python code review.
---

# Python Code Review

## Scope

Use this skill for Python-only reviews. Apply every checklist item explicitly.

## Review Workflow

1. Read `../review-shared/general-review-requirements.md` and apply all requirements.
2. Read `python-review-checklist.md` and execute every check.
3. Inspect changed and impacted call paths, not just edited lines.
4. Prioritize findings by user impact and failure likelihood.
5. Report findings using:
   - `../review-shared/severity-rubric.md`
   - `../review-shared/output-template.md`

## Required Focus Areas

- Exception handling and error propagation consistency.
- Type annotation coverage on public APIs.
- Resource cleanup via context managers.
- No use of `eval`/`exec`/`pickle` on untrusted input; no secrets in code or logs.
- Failure-path and boundary-condition test coverage.
