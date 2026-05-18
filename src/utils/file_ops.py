"""Utility functions for file operations"""
import json
import csv
from pathlib import Path
from typing import List, Dict, Any, Union


def load_json(file_path: Union[str, Path]) -> Any:
    """Load JSON file."""
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(data: Any, file_path: Union[str, Path], indent: int = 2) -> None:
    """Save data to JSON file."""
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent)


def load_csv(file_path: Union[str, Path]) -> List[Dict[str, Any]]:
    """Load CSV file as list of dictionaries."""
    data = []
    with open(file_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        data = list(reader)
    return data


def save_csv(data: List[Dict[str, Any]], file_path: Union[str, Path]) -> None:
    """Save list of dictionaries to CSV file."""
    if not data:
        return
    
    file_path = Path(file_path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(file_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
