"""Configuration module for SAN Project"""
import os
import json
from pathlib import Path
from typing import Dict, Any

# Project root directory
PROJECT_ROOT = Path(__file__).parent.absolute()

# Data directories
DATA_DIR = PROJECT_ROOT / "data"
INPUT_DIR = DATA_DIR / "input"
OUTPUT_DIR = DATA_DIR / "output"
GENERATED_DIR = DATA_DIR / "generated_files"

# Config directory
CONFIG_DIR = PROJECT_ROOT / "config"

# Logs directory
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for directory in [INPUT_DIR, OUTPUT_DIR, GENERATED_DIR, CONFIG_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)


def load_config(config_file: str = "data/act.json") -> Dict[str, Any]:
    """Load configuration from JSON file."""
    config_path = CONFIG_DIR / config_file
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


def get_project_paths() -> Dict[str, Path]:
    """Return all project paths."""
    return {
        "root": PROJECT_ROOT,
        "src": PROJECT_ROOT / "src",
        "tests": PROJECT_ROOT / "tests",
        "data": DATA_DIR,
        "input": INPUT_DIR,
        "output": OUTPUT_DIR,
        "generated": GENERATED_DIR,
        "config": CONFIG_DIR,
        "docs": PROJECT_ROOT / "docs",
        "logs": LOGS_DIR,
    }


# Environment variables
DEBUG = os.getenv("DEBUG", "False").lower() == "true"
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
