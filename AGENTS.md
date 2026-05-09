# AI Agents Directory

This file tracks AI agents and skills within the monorepo.

## Maintenance Rule

- Keep this file up to date whenever a skill is added, removed, renamed,
  moved, or when any `skills/*/artifact.json` dependency metadata changes.

## Agent Registry

- `go-code-review` (Code Review, Active) in `skills/go-code-review/`
  Go code review workflow for correctness, reliability, security, and tests.
- `python-code-review` (Code Review, Active) in
  `skills/python-code-review/`
  Python code review workflow for correctness, security, type safety,
  and tests.
- `kubeflow-pipelines-code-review` (Code Review, Active) in
  `skills/kubeflow-pipelines-code-review/`
  KFP review workflow layered on Go and Python baseline checks plus
  control-plane rules.
- `generic-review` (Code Review, Active) in `skills/generic-review/`
  Full-diff review without a PR URL, with shared requirements, routing,
  severity, output template, and review-of-review validation.
- `pr-review` (Code Review, Active) in `skills/pr-review/`
  PR URL review with gh context and comment validation, then delegation
  to generic review.
- `tdd` (Development, Active) in `skills/tdd/`
  Test-first workflow with scenario gates, overlap checks, and final
  review/fix loop.
- `fix-pr-comments` (Development, Active) in
  `skills/fix-pr-comments/`
  Implement PR review feedback from a PR URL (including bot nitpicks),
  using TDD where applicable, then a fresh `generic-review` fix loop before
  the closing per-comment summary; does not commit or push.
- `review-and-fix` (Development, Active) in `skills/review-and-fix/`
  Review-and-fix loop: run `generic-review` with fresh eyes, fix issues
  using TDD where applicable, repeat until clean, then save the clean
  review to `<project>/.hbelmiro/reviews/`; does not commit or push.
- `pr-review-to-file` (Code Review, Active) in
  `skills/pr-review-to-file/`
  Run `pr-review` for a PR URL and save the review output to
  `<project>/.hbelmiro/reviews/`; does not commit or push.

## Skill Dependency Graph (`artifact.json`)

Dependency source: `skills/*/artifact.json` (`dependencies` field).

- `review-shared` (base; no dependencies)
- `go-code-review` -> `review-shared`
- `python-code-review` -> `review-shared`
- `kubeflow-pipelines-code-review` ->
  `go-code-review`, `python-code-review`
- `generic-review` ->
  `review-shared`, `kubeflow-pipelines-code-review`,
  `go-code-review`, `python-code-review`
- `pr-review` -> `generic-review`
- `tdd` -> `generic-review`
- `fix-pr-comments` -> `tdd`, `pr-review`
- `review-and-fix` -> `tdd`, `generic-review`
- `pr-review-to-file` -> `pr-review`

### Dependency Layers

- **Layer 0 (foundation):** `review-shared`
- **Layer 1 (language):** `go-code-review`, `python-code-review`
- **Layer 2 (domain orchestration):**
  `kubeflow-pipelines-code-review`, `generic-review`
- **Layer 3 (entry workflows):** `pr-review`, `tdd`
- **Layer 4 (fix workflows):** `fix-pr-comments`, `review-and-fix`,
  `pr-review-to-file`

### Deduplication Guidance

- Keep global review rules and output conventions in `review-shared`.
- Keep language-specific checks in
  `go-code-review` and `python-code-review`.
- Keep routing/orchestration logic in `generic-review`.
- Keep PR-context collection in `pr-review` and TDD phase flow in `tdd`.
- In downstream skills, reference dependency skills
  instead of duplicating shared instructions.

### Single Source of Truth Rules

- This is a **strict policy**. PRs must fix violations before merge.
- `review-shared` owns:
  independent reviewer mode, severity rubric, output template, and
  review-the-review criteria.
- `generic-review` owns:
  full-diff local-review flow, routing rules, and shared risk/test checks.
- `go-code-review` and `python-code-review` own:
  language-specific checks only.
- `kubeflow-pipelines-code-review` owns:
  KFP-specific checks only; rely on Go/Python skills for language baseline.
- `pr-review` owns:
  PR metadata/thread collection only; rely on `generic-review` for findings.
- `tdd` owns:
  phase sequencing only; rely on `generic-review` for final review behavior.
- `fix-pr-comments` owns:
  triage and implement review feedback for a PR URL; rely on `pr-review`
  for thread collection and `tdd` for test-first work when it applies;
  require a fresh-eyes `generic-review` fix loop on the current git diff
  before presenting the PR-comment summary; **never** commit or push (user
  owns git history and remotes).
- `review-and-fix` owns:
  the standalone review-fix-save loop on the current change set; rely on
  `generic-review` for the full-diff review workflow and `tdd` for
  test-first fixes when behavior or coverage is in play; save the clean
  review to `<project>/.hbelmiro/reviews/`; **never** commit or push (user
  owns git history and remotes).
- `pr-review-to-file` owns:
  the PR-review-to-file workflow; rely on `pr-review` for full PR review
  (gh context, comment validation, generic-review pipeline); save the
  review to `<project>/.hbelmiro/reviews/`; **never** commit or push (user
  owns git history and remotes).
- If a rule already exists in an upstream dependency,
  link/reference it instead of repeating the same prose.

## Adding New Agents

1. Create a new directory under `skills/`
2. Follow the structure outlined in the [root README](README.md#skill-structure)
3. Add your agent to the registry section above
4. Include a clear description and usage instructions

## Code Quality Rules

- **Never suppress `ty` diagnostics.** Do not use `# ty: ignore[...]` or
  `# type: ignore[...]` comments to silence type-checking errors. Fix the
  underlying type issue instead (e.g. use explicit narrowing helpers like
  `_as_json_object` to convert untyped data to properly-typed structures).

## Agent Guidelines

- **Self-contained**: Each agent should be modular and portable, and may
  depend on upstream shared skills without duplicating their instructions
- **Documented**: Include clear README with usage instructions
- **Configurable**: Use config files for customizable parameters
- **Testable**: Include tests where applicable
- **Categorized**: Assign to appropriate category for discoverability

## Integration Patterns

- Use `shared/utils/` for common functionality
- Follow consistent naming conventions
- Implement standard interfaces where possible
- Document API endpoints and data formats
