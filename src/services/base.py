"""Data models and base classes for services"""
from abc import ABC, abstractmethod
from typing import Any, Dict, Optional


class BaseService(ABC):
    """Base service class for all services."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize base service with optional configuration."""
        self.config = config or {}
    
    @abstractmethod
    def process(self, data: Any) -> Any:
        """Process data. Must be implemented by subclasses."""
        pass
    
    def validate_input(self, data: Any) -> bool:
        """Validate input data. Can be overridden by subclasses."""
        return data is not None


class Result:
    """Result wrapper for service responses."""
    
    def __init__(self, data: Any = None, error: Optional[str] = None, success: bool = True):
        """Initialize result object."""
        self.data = data
        self.error = error
        self.success = success
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert result to dictionary."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
        }
