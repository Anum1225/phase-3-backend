"""
Application entry point for deployment platforms.

This module re-exports the FastAPI app from the root main.py to ensure
compatibility with platforms like Render that expect the app at src.main:app
"""

# Import the FastAPI app from the root main module
import sys
from pathlib import Path

# Add parent directory to path so we can import main
parent_dir = Path(__file__).parent.parent
sys.path.insert(0, str(parent_dir))

from main import app

__all__ = ["app"]
