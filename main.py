"""
Launcher for the Summary & Risk Scoring API

This file launches the FastAPI application from the src/ directory.
"""

import sys
import os

# Add project root to path so the src package can be imported
sys.path.insert(0, os.path.dirname(__file__))

# Import and run the app from the src package
from src.main import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000)