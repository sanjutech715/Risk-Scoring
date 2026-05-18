"""API routes and endpoints"""
from typing import Dict, Any


class APIHandler:
    """Base API handler."""
    
    @staticmethod
    def get_routes() -> Dict[str, str]:
        """Return available routes."""
        return {
            "/health": "Health check",
            "/process": "Process data",
            "/results": "Get results",
        }
