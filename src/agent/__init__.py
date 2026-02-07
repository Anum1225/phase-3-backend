"""
AI Agent Package for Todo Chatbot

This package contains the OpenAI Agent implementation that:
- Interprets natural language commands
- Calls appropriate MCP tools
- Manages conversation context
"""

from .config import get_agent_config, get_system_prompt
from .runner import create_agent, run_agent

__all__ = [
    "get_agent_config",
    "get_system_prompt",
    "create_agent",
    "run_agent",
]
