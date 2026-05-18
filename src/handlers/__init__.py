"""Event handlers and request handlers"""
from typing import Dict, Any


class EventHandler:
    """Base event handler."""
    
    @staticmethod
    def handle_event(event_type: str, data: Dict[str, Any]) -> None:
        """Handle events."""
        print(f"Event: {event_type}, Data: {data}")
