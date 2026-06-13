# Thorough Review

Parallel fan-out review with adversarial verification of each finding.

## Architecture

```text
Phase 1: Review (parallel)
  ├── Go reviewer
  ├── Python reviewer
  └── Generic reviewer

Phase 2: Verify (per finding, as they arrive)
  └── Skeptic agent per finding — refute or confirm

Phase 3: Write
  └── Merge survivors, dedup, format output
```

## How it works

1. **Review** — Three reviewer agents run concurrently, each applying
   language-specific or cross-cutting checks. Each returns structured
   findings with file, line, title, description, and suggested fix.

2. **Verify** — For each finding, a skeptic agent reads the actual source
   code and attempts to refute the claim. Findings survive only if the
   skeptic cannot disprove them. This eliminates hallucinated or
   speculative findings.

3. **Write** — A synthesis agent merges surviving findings, deduplicates
   across reviewers, applies review-the-review self-validation, and
   formats the output.

## Dependencies

- [`review-shared`](../../prompts/review-shared/) — output template,
  general review requirements
- [`go-code-review`](../../prompts/go-code-review/) — Go-specific checklist
- [`python-code-review`](../../prompts/python-code-review/) — Python-specific
  checklist

## When to use

Use this workflow for thorough audits where accuracy matters more than
speed. For fast single-pass reviews, use
[`pr-review`](../../skills/pr-review/) instead.
