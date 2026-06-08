# Severity Rubric

Use this rubric to classify findings.

## Critical

Must fix before merge. Examples:

- Security vulnerabilities, secret leakage, or privilege escalation risk.
- Data loss/corruption, lineage corruption, or irreversible state drift.
- Control plane regressions that break existing clients or runtime behavior.
- Concurrency bugs likely to deadlock, race, or leak goroutines.

## High

Strongly recommended before merge. Examples:

- Incorrect error handling that can mask failures.
- Missing compatibility updates across API, persistence, and clients.
- Risky caching or idempotency behavior under retries/reconciles.

## Medium

Should fix soon. Examples:

- Missing edge-case tests for failure and boundary paths.
- Logging context gaps that hinder debugging.
- Maintainability issues that materially increase defect risk.

## Low

Quality improvements. Examples:

- Style consistency, naming, and minor refactors.
- Removing self-evident comments in favor of intent-focused comments.
