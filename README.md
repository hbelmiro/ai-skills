# AI Skills Monorepo

A collection of AI skills and projects organized in a single repository.

## Structure

- `src/` - Main package source code and shared utilities
- `skills/` - Individual AI skills and projects

## Skill Structure

Each skill is an OCI artifact with an `artifact.json` manifest:

```text
skill-name/
├── artifact.json      # OCI artifact manifest (name, version, files, dependencies)
├── SKILL.md           # Entrypoint read by the AI agent
├── README.md          # Human-readable description (optional)
└── *.md               # Additional checklist/reference files
```

## Getting Started

1. Install [uv](https://docs.astral.sh/uv/) for Python project management
2. Install dependencies: `uv sync`
3. Navigate to the specific skill directory you want to work with
4. Follow the README instructions in that skill's directory

## Development

- Install all development dependencies: `uv sync --group dev`
- Install specific groups: `uv sync --group lint` / `--group test` / `--group security` / `--group assessment` / `--group git-hooks`
- Run linting: `uv run ruff check .`
- Run formatting: `uv run ruff format .`
- Run type checking: `uv run ty check .`
- Manage skill installs/reinstalls via `src/install.py` (see [Installing Skills](#installing-skills))

Skills can import shared utilities via the src layout (requires `uv run`, or set `PYTHONPATH=../../src`):

```python
from utils.common import load_config, process_data
```

### Dependency Groups

- `lint`: Linting and type checking tools (ruff, ty)
- `test`: Testing tools (empty for now, add pytest, etc. as needed)
- `security`: Security scanning tools (safety)
- `assessment`: Code assessment tools (agentready)
- `git-hooks`: Git hooks and pre-commit tools (pre-commit)
- `dev`: All development tools (inherits from all groups)

## Installing Skills

### Prerequisites

- [striatum](https://github.com/hbelmiro/striatum) on `PATH`
- An OCI registry (e.g. `docker run -d -p 5050:5000 registry:2`)
- `STRIATUM_REGISTRY` env var pointing to the registry base (e.g. `localhost:5050/skills`)

The install script validates, packs, pushes, and installs skills via striatum. Dependencies are resolved from `artifact.json` and pushed in the correct order.

**Transitive install:** Installing a skill also runs `striatum skill install` for **each** transitive dependency (dependency order first, then the requested skill). They appear as separate directories under `~/.cursor/skills/` (or `<project>/.cursor/skills/`), which keeps relative paths like `../generic-review/SKILL.md` working.

**Uninstall:** `--uninstall` removes **only** the named skill. Dependency skills installed alongside it are not removed automatically (they may still be required by other skills). Remove them with additional `--uninstall` invocations if you want a clean tree, or delete the extra directories manually.

```bash
# Install for all projects (personal)
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --personal --skill go-code-review

# Install for a specific project
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --project /path/to/my-project --skill kubeflow-pipelines-review

# Uninstall
uv run python src/install.py --personal --uninstall --skill go-code-review

# Force-replace conflicting versions
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --personal --force --skill go-code-review

# Install every skill under skills/ (each once, dependency order)
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --personal --install-all

# Same for a specific project
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --project /path/to/my-project --install-all

# Reinstall all tracked skills
uv run python src/install.py --reinstall-all

# Reinstall with force
uv run python src/install.py --reinstall-all --force
```

Run `uv run python src/install.py --help` for full usage.

## Adding a New Skill

1. Create a new directory under `skills/`
2. Use lowercase with hyphens for directory names (e.g., `go-code-review`, `python-code-review`)
3. Add a README.md with project description and setup instructions
4. Include any necessary configuration files
5. Update the `AGENTS.md` registry with your new skill
6. Tag skills by category for discoverability

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
