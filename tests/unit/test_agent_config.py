"""
Unit Tests for Agent Configuration

Tests for:
- System prompt generation
- Agent configuration settings
- Conversation history formatting
"""

import os
import pytest
from datetime import datetime
from unittest.mock import Mock

from src.agent.config import (
    get_system_prompt,
    get_agent_config,
    format_conversation_history,
    AGENT_MODEL,
    AGENT_TEMPERATURE,
    AGENT_MAX_TOKENS,
    MAX_CONVERSATION_HISTORY,
    MCP_SERVER_URL,
)
from src.models.message import MessageRole


class TestSystemPrompt:
    """Test system prompt generation"""

    def test_get_system_prompt_returns_string(self):
        """System prompt should return a non-empty string"""
        prompt = get_system_prompt()
        assert isinstance(prompt, str)
        assert len(prompt) > 0

    def test_system_prompt_includes_role_description(self):
        """Prompt should describe agent's role"""
        prompt = get_system_prompt()
        assert "Todo Assistant" in prompt
        assert "task" in prompt.lower()

    def test_system_prompt_documents_all_tools(self):
        """Prompt should document all 5 MCP tools"""
        prompt = get_system_prompt()

        # Check all tool names are mentioned
        assert "add_task" in prompt
        assert "list_tasks" in prompt
        assert "complete_task" in prompt
        assert "delete_task" in prompt
        assert "update_task" in prompt

    def test_system_prompt_includes_tool_parameters(self):
        """Prompt should document tool parameters"""
        prompt = get_system_prompt()

        # Check key parameters are documented
        assert "user_id" in prompt
        assert "title" in prompt
        assert "priority" in prompt
        assert "category" in prompt

    def test_system_prompt_includes_examples(self):
        """Prompt should include usage examples"""
        prompt = get_system_prompt()

        # Check for example indicators
        assert "Example" in prompt or "example" in prompt
        assert "→" in prompt or "->" in prompt  # Example arrows

    def test_system_prompt_includes_priority_values(self):
        """Prompt should list valid priority values"""
        prompt = get_system_prompt()

        assert "high" in prompt
        assert "medium" in prompt
        assert "low" in prompt
        assert "none" in prompt

    def test_system_prompt_includes_category_values(self):
        """Prompt should list valid category values"""
        prompt = get_system_prompt()

        assert "work" in prompt
        assert "personal" in prompt
        assert "shopping" in prompt
        assert "health" in prompt
        assert "other" in prompt

    def test_system_prompt_includes_intent_recognition(self):
        """Prompt should include intent recognition guidelines"""
        prompt = get_system_prompt()

        # Check for intent recognition section
        assert "intent" in prompt.lower() or "recognize" in prompt.lower()

    def test_system_prompt_includes_response_guidelines(self):
        """Prompt should include response formatting guidelines"""
        prompt = get_system_prompt()

        assert "response" in prompt.lower() or "conversational" in prompt.lower()


class TestAgentConfig:
    """Test agent configuration"""

    def test_get_agent_config_returns_dict(self):
        """Config should return a dictionary"""
        config = get_agent_config()
        assert isinstance(config, dict)

    def test_agent_config_includes_model(self):
        """Config should include model setting"""
        config = get_agent_config()
        assert "model" in config
        assert config["model"] == AGENT_MODEL

    def test_agent_config_includes_temperature(self):
        """Config should include temperature setting"""
        config = get_agent_config()
        assert "temperature" in config
        assert config["temperature"] == AGENT_TEMPERATURE
        assert isinstance(config["temperature"], float)

    def test_agent_config_includes_max_tokens(self):
        """Config should include max_tokens setting"""
        config = get_agent_config()
        assert "max_tokens" in config
        assert config["max_tokens"] == AGENT_MAX_TOKENS
        assert isinstance(config["max_tokens"], int)

    def test_agent_config_includes_mcp_server_url(self):
        """Config should include MCP server URL"""
        config = get_agent_config()
        assert "mcp_server_url" in config
        assert config["mcp_server_url"] == MCP_SERVER_URL

    def test_agent_config_includes_max_history(self):
        """Config should include max conversation history"""
        config = get_agent_config()
        assert "max_conversation_history" in config
        assert config["max_conversation_history"] == MAX_CONVERSATION_HISTORY

    def test_default_model_is_gemini(self):
        """Default model should be Gemini"""
        assert "gemini" in AGENT_MODEL.lower()

    def test_temperature_in_valid_range(self):
        """Temperature should be between 0 and 2"""
        assert 0.0 <= AGENT_TEMPERATURE <= 2.0

    def test_max_tokens_is_positive(self):
        """Max tokens should be positive"""
        assert AGENT_MAX_TOKENS > 0

    def test_max_history_is_positive(self):
        """Max conversation history should be positive"""
        assert MAX_CONVERSATION_HISTORY > 0


class TestConversationHistoryFormatting:
    """Test conversation history formatting"""

    def test_format_empty_history(self):
        """Should handle empty message list"""
        formatted = format_conversation_history([])
        assert formatted == []

    def test_format_single_user_message(self):
        """Should format single user message"""
        # Create mock message
        msg = Mock()
        msg.role = MessageRole.user
        msg.content = "Hello"

        formatted = format_conversation_history([msg])

        assert len(formatted) == 1
        assert formatted[0]["role"] == "user"
        assert formatted[0]["content"] == "Hello"

    def test_format_single_assistant_message(self):
        """Should format single assistant message"""
        msg = Mock()
        msg.role = MessageRole.assistant
        msg.content = "Hi there!"

        formatted = format_conversation_history([msg])

        assert len(formatted) == 1
        assert formatted[0]["role"] == "assistant"
        assert formatted[0]["content"] == "Hi there!"

    def test_format_multiple_messages(self):
        """Should format multiple messages in order"""
        msg1 = Mock()
        msg1.role = MessageRole.USER
        msg1.content = "Create a task"

        msg2 = Mock()
        msg2.role = MessageRole.ASSISTANT
        msg2.content = "I've created the task!"

        msg3 = Mock()
        msg3.role = MessageRole.USER
        msg3.content = "Thanks"

        formatted = format_conversation_history([msg1, msg2, msg3])

        assert len(formatted) == 3
        assert formatted[0]["role"] == "user"
        assert formatted[1]["role"] == "assistant"
        assert formatted[2]["role"] == "user"

    def test_format_preserves_message_content(self):
        """Should preserve exact message content"""
        msg = Mock()
        msg.role = MessageRole.user
        msg.content = "This is a test message with special chars: !@#$%"

        formatted = format_conversation_history([msg])

        assert formatted[0]["content"] == msg.content

    def test_format_converts_enum_to_lowercase(self):
        """Should convert MessageRole enum to lowercase string"""
        msg = Mock()
        msg.role = MessageRole.user
        msg.content = "Test"

        formatted = format_conversation_history([msg])

        # Should be lowercase "user", not "USER"
        assert formatted[0]["role"] == "user"
        assert formatted[0]["role"].islower()


class TestEnvironmentConfiguration:
    """Test environment variable configuration"""

    def test_agent_model_from_env(self):
        """Should read AGENT_MODEL from environment"""
        # This tests that the config reads from env
        # Actual value depends on .env file
        assert AGENT_MODEL is not None
        assert isinstance(AGENT_MODEL, str)

    def test_mcp_server_url_has_default(self):
        """MCP_SERVER_URL should have a default value"""
        # Should have localhost default if not set
        assert MCP_SERVER_URL is not None
        assert "mcp" in MCP_SERVER_URL.lower()


# Test configuration values are reasonable
class TestConfigurationDefaults:
    """Test default configuration values"""

    def test_default_temperature_is_reasonable(self):
        """Default temperature should be reasonable for chat"""
        # 0.7 is a good default for conversational AI
        assert 0.5 <= AGENT_TEMPERATURE <= 1.0

    def test_default_max_tokens_is_sufficient(self):
        """Default max tokens should be sufficient for responses"""
        # Should allow for detailed responses
        assert AGENT_MAX_TOKENS >= 500

    def test_default_max_history_is_reasonable(self):
        """Default max history should balance context and cost"""
        # 50 messages is a reasonable default
        assert 10 <= MAX_CONVERSATION_HISTORY <= 100
