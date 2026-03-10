# Shared Resources

This directory contains non-Python shared resources and utilities.

## Structure

- `javascript/` - JavaScript/Node.js shared utilities (add when needed)
- `go/` - Go shared utilities (add when needed)
- `configs/` - Shared configuration files
- `templates/` - Project templates and scaffolding

## Python Shared Code

Python shared utilities have been moved to `src/` to follow standard Python packaging practices.

## Usage

For Python projects, import shared utilities:
```python
from utils.common import load_config, process_data
```

For other languages, organize utilities in language-specific directories as needed.