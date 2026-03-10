"""Main entry point for the example skill."""

from utils.common import load_config, process_data


def main():
    """Main function demonstrating the skill."""
    print("Running example AI skill...")

    # Example usage of shared utilities
    config = load_config()
    result = process_data("example input")

    print(f"Config: {config}")
    print(f"Processed result: {result}")
    print("Example skill completed successfully!")


if __name__ == "__main__":
    main()
