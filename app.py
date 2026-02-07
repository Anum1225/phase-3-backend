"""
Hugging Face Spaces entry point for FastAPI application.

This file imports the FastAPI app from main.py to make it compatible
with Hugging Face Spaces deployment requirements.
"""

# Import the FastAPI app from main.py
from main import app

# The app is already configured in main.py
# Hugging Face Spaces will use this app instance
