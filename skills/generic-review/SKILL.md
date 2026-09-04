---
name: generic-review
description: Review a local change set without a PR URL using full-diff and applicable language/domain checks.
---

# Generic Review

Use for working-tree, staged, or branch-range reviews without a PR URL.

1. Read [`../../prompts/review-policy/PROMPT.md`](../../prompts/review-policy/PROMPT.md).
2. Read and execute [`generic-review-checklist.md`](generic-review-checklist.md). For a handoff from `pr-review`, skip Git diff acquisition and use the complete `gh pr diff` already collected.
3. Read [`../../prompts/review-shared/general-review-requirements.md`](../../prompts/review-shared/general-review-requirements.md).
4. Route after inspecting changed paths:
   - KFP/DSP: [`../../prompts/kubeflow-pipelines-code-review/PROMPT.md`](../../prompts/kubeflow-pipelines-code-review/PROMPT.md)
   - Go: [`../../prompts/go-code-review/PROMPT.md`](../../prompts/go-code-review/PROMPT.md)
   - Python: [`../../prompts/python-code-review/PROMPT.md`](../../prompts/python-code-review/PROMPT.md)
5. Format with [`../../prompts/review-shared/output-template.md`](../../prompts/review-shared/output-template.md), then apply [`../../prompts/review-shared/review-the-review.md`](../../prompts/review-shared/review-the-review.md).

When continuing from `pr-review`, use its already-collected PR diff and return to its duplicate-suppression phase.
