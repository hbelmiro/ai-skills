---
name: pr-review
description: Review GitHub pull requests from a PR URL using gh, including full diff inspection, addressed-comment validation, and language/domain-specific review checklists. Use when the user shares a PR link or asks for a pull request review.
---

# PR Review

## Scope

Use this skill when the user provides a pull request URL or asks for a full PR review.

## Review Workflow

1. Read `../review-shared/general-review-requirements.md` and apply all requirements.
2. Read `pr-review-checklist.md` and execute every check.
3. Parse owner/repo/PR number from the provided URL.
4. Collect PR metadata, comments, and review context with `gh`.
5. Validate whether all review comments were addressed and whether each resolution is technically sound.
6. Review the complete pull request diff before writing findings.
7. Route to the correct specialized review skill:
   - If project/repo context indicates Kubeflow Pipelines or Data Science Pipelines, apply `../kubeflow-pipelines-review/SKILL.md`.
   - Otherwise infer languages used by the project and apply matching language skills:
     - Go: `../go-code-review/SKILL.md`
     - Python: `../python-code-review/SKILL.md`
8. Classify findings with `../review-shared/severity-rubric.md`.
9. Present results using `../review-shared/output-template.md`.

## Routing Rules

- KFP/DSP takes precedence over language-only routing.
- For non-KFP/DSP repositories, apply all relevant language checklists when multiple languages are materially changed.
- If a language-specific skill is unavailable for a detected language, continue with shared checks and state that limitation explicitly.
