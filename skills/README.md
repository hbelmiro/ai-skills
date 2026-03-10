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

## Naming Convention

- Use lowercase with hyphens for directory names (e.g., `text-summarization`, `image-classification`)
- Include a brief description in the skill's README
- Tag skills by category (NLP, Computer Vision, etc.)