---
name: generic-review
description: >-
  Review a change set without a PR URL: full diff (git or already fetched), shared review requirements,
  language/domain routing (KFP, Go, Python), severity rubric, output template, and review-the-review
  self-validation. Use for local or branch reviews, pre-push review, or after pr-review has collected
  the PR diff via gh.
---

# Generic Review

## Scope

Use this skill when reviewing changes **without** requiring a pull request link—for example working tree or branch diffs, or a commit range.

If you are **continuing immediately after** [`../pr-review/SKILL.md`](../pr-review/SKILL.md), the full diff should already be available from `gh pr diff`. In that case **skip** the diff-acquisition steps in `generic-review-checklist.md` and use that diff and the PR file list.

## Prerequisites

Before the workflow below, you must have:

- The **full unified diff** for the change under review (every touched file), unless you are about to obtain it via `generic-review-checklist.md`.
- Enough context to route (changed paths, repo signals such as `go.mod` / `pyproject.toml`).

## Review workflow

1. Read `../review-shared/general-review-requirements.md` and apply all requirements.
2. Read `generic-review-checklist.md` and execute every check (honor the skip rule above when continuing from `pr-review`).
3. Route to the correct specialized review skill:
   - If project/repo context indicates Kubeflow Pipelines or Data Science Pipelines, apply `../kubeflow-pipelines-review/SKILL.md`.
   - Otherwise infer languages used by the project and apply matching language skills:
     - Go: `../go-code-review/SKILL.md`
     - Python: `../python-code-review/SKILL.md`
4. Classify findings with `../review-shared/severity-rubric.md`.
5. Present results using `../review-shared/output-template.md`.
6. Read `../review-shared/review-the-review.md` and apply it to your completed review. Fix any issues in-place before presenting.

## Routing rules

- KFP/DSP takes precedence over language-only routing.
- For non-KFP/DSP repositories, apply all relevant language checklists when multiple languages are materially changed.
- If a language-specific skill is unavailable for a detected language, continue with shared checks and state that limitation explicitly.
