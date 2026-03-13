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
Each successful install is tracked in `~/.ai-skills/installed-skills.yaml`.

```bash
# Install for all projects (personal)
uv run python src/install.py --personal --skill go-code-review

# Install for a specific project
uv run python src/install.py --project /path/to/my-project --skill kubeflow-pipelines-review

# Uninstall
uv run python src/install.py --personal --uninstall --skill go-code-review

# Force-replace conflicting symlinks
uv run python src/install.py --personal --force --skill go-code-review

# Reinstall every tracked skill (personal + project entries)
uv run python src/install.py --reinstall-all

# Reinstall tracked skills and force-replace conflicting symlinks
uv run python src/install.py --reinstall-all --force
```

Run `uv run python src/install.py --help` for full usage.

## Install Tracking Database

The installer stores a global database at `~/.ai-skills/installed-skills.yaml`.

- One global list is used for all installs.
- Personal installs are stored with `target: personal`.
- Project installs are stored with `target: project` and `project_path`.
- `--reinstall-all` replays all entries, continues on errors, and prints a final report.
- Failed entries are marked with `status: error` and include `last_error`.

## Naming Convention

- Use lowercase with hyphens for directory names (e.g., `text-summarization`, `image-classification`)
- Include a brief description in the skill's README
- Tag skills by category (NLP, Computer Vision, etc.)