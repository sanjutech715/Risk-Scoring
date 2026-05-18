"""Main application entry point"""
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from config import get_project_paths, load_config


def main():
    """Main application entry point."""
    print("=" * 60)
    print("SAN Project - Advanced Scoring and Analysis System")
    print("=" * 60)
    
    # Load project configuration
    paths = get_project_paths()
    config = load_config()
    
    print(f"\nProject Root: {paths['root']}")
    print(f"Configuration loaded: {bool(config)}")
    print("\nAvailable commands:")
    print("  - python src/main.py          : Run main application")
    print("  - python src/interactive_cli.py: Interactive CLI mode")
    print("  - python src/demo.py          : Run demo")
    print("  - pytest tests/               : Run tests")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
