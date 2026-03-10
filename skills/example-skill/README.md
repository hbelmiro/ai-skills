# Example Skill

A template/example skill demonstrating the recommended structure for AI skills in this monorepo.

## Description

This is an example skill that shows how to organize code, tests, and documentation for an AI project.

## Structure

```
example-skill/
├── README.md          # This file
├── src/               # Source code
│   ├── __init__.py
│   └── main.py        # Entry point
└── config/            # Configuration files
    └── config.yaml
```

This skill demonstrates importing shared utilities:
```python
from utils.common import load_config, process_data
```

## Setup

1. Navigate to the skill directory:
   ```bash
   cd skills/example-skill
   ```

2. Run the example:
   ```bash
   # With uv (recommended - handles imports automatically)
   uv run python src/main.py

   # Or with explicit PYTHONPATH
   PYTHONPATH=../../src python src/main.py
   ```

## Usage

Describe how to use your skill here.

## API

If your skill exposes an API, document it here.

