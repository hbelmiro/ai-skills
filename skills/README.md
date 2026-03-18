# Skills Directory

This directory contains individual AI skills. Each skill is an OCI artifact with an `artifact.json` manifest.

## Skill Structure

```
skill-name/
├── artifact.json      # OCI artifact manifest (name, version, files, dependencies)
├── SKILL.md           # Entrypoint read by the AI agent
├── README.md          # Human-readable description (optional)
└── *.md               # Additional checklist/reference files
```

## Prerequisites

- [striatum](https://github.com/hbelmiro/striatum) on `PATH`
- An OCI registry (e.g. `docker run -d -p 5050:5000 registry:2`)
- `STRIATUM_REGISTRY` env var pointing to the registry base (e.g. `localhost:5050/skills`)

## Installing Skills

The install script validates, packs, pushes, and installs skills via striatum. Dependencies are resolved from `artifact.json` and pushed in the correct order.

```bash
# Install for all projects (personal)
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --personal --skill go-code-review

# Install for a specific project
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --project /path/to/my-project --skill kubeflow-pipelines-review

# Uninstall
uv run python src/install.py --personal --uninstall --skill go-code-review

# Force-replace conflicting versions
STRIATUM_REGISTRY=localhost:5050/skills uv run python src/install.py --personal --force --skill go-code-review

# Reinstall all tracked skills
uv run python src/install.py --reinstall-all

# Reinstall with force
uv run python src/install.py --reinstall-all --force
```

Run `uv run python src/install.py --help` for full usage.

## Naming Convention

- Use lowercase with hyphens for directory names (e.g., `go-code-review`, `python-code-review`)
- Include a brief description in the skill's README
- Tag skills by category for discoverability