---
name: tdd
description: Guide test-first development with scenario audits, implementation, and a final review loop.
---

# Test-Driven Development

Use for new behavior, bug fixes, or refactors where tests should lead design. Skip strict red-first only when the user explicitly requests implementation-first or a spike.

1. Read [`../../prompts/review-policy/PROMPT.md`](../../prompts/review-policy/PROMPT.md) for independent scenario review.
2. Follow [`../../prompts/plan/PROMPT.md`](../../prompts/plan/PROMPT.md) and wait for explicit approval before Phase A.
3. Execute Phases A–G below. Use [`scenario-coverage.md`](scenario-coverage.md) for both scenario audits.
4. Execute Phase H as the final gate for a non-trivial change.

## A — Red

Capture the behavior contract, add tests that express it, and confirm expected failures.

## B — Pre-implementation scenarios

Audit the scenarios reference, add missing tests, and repeat until the contract’s happy paths, errors, boundaries, and applicable consistency rules are represented.

## C — Green

Implement the smallest change that passes the tests. Run the full relevant test scope. If implementation reveals new behavior, return to B before coding that delta.

## D — Post-implementation scenarios

Audit current code paths and tests again; add and implement tests for required defensive branches or integration seams until coverage is sufficient.

## E — Refactor

With tests green, simplify structure without changing behavior. Prefer deletion and reuse of existing architecture over new layers.

## F/G — Overlap and gap loop

Map tests to distinct behaviors, merge or delete unjustified duplicates, re-run tests, then re-audit the scenario contract. Repeat F → G until coverage is complete without redundant cases.

## H — Final review

Run [`../generic-review/SKILL.md`](../generic-review/SKILL.md) as an independent reviewer, fix accepted findings, re-run checks, and repeat until clean.

## Handoff

Track approval, phases A–G, and the Phase H review/fix loop; record N/A reasons where a phase does not apply.
