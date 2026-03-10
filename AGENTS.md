# AI Agents Directory

This file tracks AI agents and skills within the monorepo.

## Agent Registry

| Name | Category | Description | Status | Location |
|------|----------|-------------|--------|----------|
| example-skill | Template | Template agent for demonstrating structure | Active | `skills/example-skill/` |

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