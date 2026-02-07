"""
Phase 3 chatbot models package.

This package contains SQLModel definitions for conversation and message persistence.
"""

from .conversation import Conversation
from .message import Message, MessageRole

__all__ = [
    "Conversation",
    "Message",
    "MessageRole",
]
