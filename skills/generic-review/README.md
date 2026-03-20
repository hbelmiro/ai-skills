# generic-review

Shared code-review workflow for any change set: obtain (or reuse) a full diff, apply general requirements, route to Kubeflow Pipelines or language-specific skills, classify severity, and format output.

## When to use

- Local or branch review without a GitHub PR URL
- Pre-push or pre-merge review in the workspace

Use [`pr-review`](../pr-review/) when the user provides a PR link; that skill collects `gh` context and threads, then delegates here for the core review pipeline.

## Files

- `SKILL.md` — entrypoint and routing
- `generic-review-checklist.md` — diff acquisition (git), full-diff review, discussion check, risk/tests

## Install

See [skills/README.md](../README.md) for Striatum-based install.
