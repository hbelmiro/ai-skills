# AI Skills Monorepo

A collection of AI skills and projects organized in a single repository.

## Structure

- `src/` - Main package source code and shared utilities
- `skills/` - Individual AI skills and projects
- `docs/` - Documentation and guides

## Getting Started

1. Install [uv](https://docs.astral.sh/uv/) for Python project management
2. Install dependencies: `uv sync`
3. Navigate to the specific skill directory you want to work with
4. Follow the README instructions in that skill's directory

## Project Structure

The project uses a src layout for shared utilities:

```python
# Skills can import shared utilities (when run with uv)
from utils.common import load_config, process_data

# Or with explicit PYTHONPATH
# PYTHONPATH=../../src python src/main.py
```

## Development

- Install all development dependencies: `uv sync --group dev`
- Install specific groups: `uv sync --group lint` / `--group test` / `--group security` / `--group assessment` / `--group git-hooks`
- Run linting: `uv run ruff check .`
- Run formatting: `uv run ruff format .`
- Run type checking: `uv run ty check .`

## Dependency Groups

- `lint`: Linting and type checking tools (ruff, ty)
- `test`: Testing tools (empty for now, add pytest, etc. as needed)
- `security`: Security scanning tools (safety)
- `assessment`: Code assessment tools (agentready)
- `git-hooks`: Git hooks and pre-commit tools (pre-commit)
- `dev`: All development tools (inherits from all groups)

## Adding a New Skill

1. Create a new directory under `skills/`
2. Add a README.md with project description and setup instructions
3. Include any necessary configuration files
4. Update the `AGENTS.md` registry with your new skill

## Skills

<!-- Add links to your skills here as you create them -->

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
