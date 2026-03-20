# AI Agents Directory

This file tracks AI agents and skills within the monorepo.

## Agent Registry

| Name | Category | Description | Status | Location |
|------|----------|-------------|--------|----------|
| go-code-review | Code Review | General Go code review workflow for correctness, reliability, security, and tests | Active | `skills/go-code-review/` |
| python-code-review | Code Review | General Python code review workflow for correctness, security, type safety, and tests | Active | `skills/python-code-review/` |
| kubeflow-pipelines-review | Code Review | KFP-specific review workflow layered on Go and Python baseline checks and control-plane rules | Active | `skills/kubeflow-pipelines-review/` |
| generic-review | Code Review | Full-diff review without a PR URL: shared requirements, KFP/Go/Python routing, severity and output template; used by TDD Phase H and after pr-review | Active | `skills/generic-review/` |
| pr-review | Code Review | PR URL plus gh context and comment-thread validation, then generic-review for routing and output | Active | `skills/pr-review/` |
| tdd | Development | Test-first workflow with scenario gates before/after implementation, overlap pass and post-overlap scenario re-audit (F↔G), review/fix loop last | Active | `skills/tdd/` |

## Adding New Agents

1. Create a new directory under `skills/`
2. Follow the structure outlined in `skills/README.md`
3. Add your agent to the registry table above
4. Include a clear description and usage instructions

## Agent Guidelines

- **Self-contained**: Each agent should be independent and portable
- **Documented**: Include clear README with usage instructions
- **Configurable**: Use config files for customizable parameters
- **Testable**: Include tests where applicable
- **Categorized**: Assign to appropriate category for discoverability

## Integration Patterns

- Use `shared/utils/` for common functionality
- Follow consistent naming conventions
- Implement standard interfaces where possible
- Document API endpoints and data formats