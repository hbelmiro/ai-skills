---
name: kubeflow-pipelines-review
description: Review Kubeflow Pipelines changes across backend, persistence, scheduling, cache, SDK, manifests, and frontend with mandatory Go and Python baseline checks. Use when reviewing KFP pull requests, pipeline control plane changes, or code mentioning kubeflow, kfp, pipelines, scheduled workflows, MLMD, or Argo integration.
---

# Kubeflow Pipelines Review

## Scope

Use this skill for repository-level KFP reviews across Go backend, controllers, manifests, SDK, and UI contracts.

## Review Workflow

1. Read `../review-shared/general-review-requirements.md` and apply all requirements.
2. Start with Go baseline checks by reading `../go-code-review/go-review-checklist.md`.
3. Apply Python baseline checks by reading `../python-code-review/python-review-checklist.md`.
4. Apply KFP-specific checks from `kfp-review-checklist.md`.
5. Review cross-component parity (one-off runs vs recurring runs, v1 vs v2 where applicable).
6. Classify findings with `../review-shared/severity-rubric.md`.
7. Present results using `../review-shared/output-template.md`.
