# Contributing

## Prerequisites

- Python 3.14+
- [uv](https://docs.astral.sh/uv/) for dependency management
- Git

## Setup

1. Clone the repository
2. Install dependencies: `uv sync --group dev`
3. Create a new branch: `git checkout -b feature/your-feature`

## Development

### Code Quality

Run before committing:

```bash
uv run ruff check .      # Lint
uv run ruff format .     # Format
uv run ty check .        # Type check
```

### Adding Skills

1. Create directory under `skills/your-skill/`, `prompts/your-prompt/`, or `memories/your-memory/`
2. Follow the structure in the [root README](README.md#skill-structure)
3. Import shared utilities: `from utils.common import ...`

### Pull Requests

- Use clear, descriptive titles
- All CI checks must pass
- Request review from maintainers

## Questions?

Open an issue or discussion.