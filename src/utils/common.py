"""Common utilities shared across AI skills."""

import json
import os
from typing import Dict, Any


def load_config(config_path: str | None = None) -> Dict[str, Any]:
    """Load configuration from a JSON or YAML file.

    Args:
        config_path: Path to configuration file. If None, uses default.

    Returns:
        Configuration dictionary.
    """
    if config_path is None:
        # Default configuration
        return {"model_name": "example-model", "max_length": 512, "temperature": 0.7}

    # Load from file (implement as needed)
    with open(config_path, "r") as f:
        return json.load(f)


def process_data(input_data: str) -> str:
    """Example data processing function.

    Args:
        input_data: Input string to process.

    Returns:
        Processed string.
    """
    # Simple example processing
    return f"Processed: {input_data.upper()}"


def save_results(results: Dict[str, Any], output_path: str) -> None:
    """Save results to a JSON file.

    Args:
        results: Results dictionary to save.
        output_path: Path where to save the results.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
