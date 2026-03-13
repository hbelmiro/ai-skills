# Skills Directory

This directory contains individual AI skills and projects. Each skill should be self-contained with its own configuration and dependencies.

## Skill Template Structure

When creating a new skill, consider this structure:

```
skill-name/
├── README.md          # Skill description and usage
├── src/              # Source code
├── config/           # Configuration files
└── pyproject.toml    # uv project configuration (optional)
```

## Installing Skills

Use the install script to symlink a skill into your Cursor configuration.
The script auto-detects shared dependencies (e.g., `review-shared`) and symlinks them too.

```bash
# Install for all projects (personal)
uv run python src/install.py --personal --skill go-code-review

# Install for a specific project
uv run python src/install.py --project /path/to/my-project --skill kubeflow-pipelines-review

# Uninstall
uv run python src/install.py --personal --uninstall --skill go-code-review

# Force-replace conflicting symlinks
uv run python src/install.py --personal --force --skill go-code-review
```

Run `uv run python src/install.py --help` for full usage.

## Naming Convention

- Use lowercase with hyphens for directory names (e.g., `text-summarization`, `image-classification`)
- Include a brief description in the skill's README
- Tag skills by category (NLP, Computer Vision, etc.)