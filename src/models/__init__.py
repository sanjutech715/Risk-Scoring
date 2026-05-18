"""Data models and schemas for SAN Project"""
from dataclasses import dataclass
from typing import Any, Dict, Optional


@dataclass
class DataModel:
    """Base data model."""
    id: str
    data: Dict[str, Any]
    metadata: Optional[Dict[str, Any]] = None


@dataclass
class ResultModel:
    """Result data model."""
    status: str
    data: Any
    timestamp: str
    error: Optional[str] = None
