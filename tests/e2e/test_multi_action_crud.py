"""
E2E Tests for Multi-Action Task Management (Phase 7 - User Story 3)

These tests verify users can view, complete, update, and delete tasks via
natural language through the chat interface.

Test Coverage:
- T060: Task listing via chat
- T061: Task completion via chat
- T062: Task update via chat
- T063: Task deletion via chat
- T064: All 5 MCP tools through natural language
- T065: Error handling (task not found, etc.)
- T066: Multi-turn conversations with context

Note: Tests marked with @pytest.mark.skip - will be executed at end after MCP fix
"""

import pytest
from fastapi.testclient import TestClient
import json

from main import app


@pytest.fixture
def client():
    return TestClient(app)


# T060: Task Listing
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_list_tasks_via_chat(client):
    """User asks 'Show my tasks' and receives list of tasks"""
    pass  # TODO: Implement after MCP fix


# T061: Task Completion
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_complete_task_via_chat(client):
    """User says 'Mark task 2 as done' and task is completed"""
    pass  # TODO: Implement after MCP fix


# T062: Task Update
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_update_task_via_chat(client):
    """User says 'Update task title to...' and task is updated"""
    pass  # TODO: Implement after MCP fix


# T063: Task Deletion
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_delete_task_via_chat(client):
    """User says 'Delete task 3' and task is removed"""
    pass  # TODO: Implement after MCP fix


# T064: All MCP Tools
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
@pytest.mark.parametrize("action,tool", [
    ("Add task to buy milk", "add_task"),
    ("Show my tasks", "list_tasks"),
    ("Mark task 1 complete", "complete_task"),
    ("Update task 2 title to 'New title'", "update_task"),
    ("Delete task 3", "delete_task"),
])
def test_all_mcp_tools_via_natural_language(client, action, tool):
    """Verify all 5 MCP tools accessible through natural language"""
    pass  # TODO: Implement after MCP fix


# T065: Error Handling
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_task_not_found_error_handling(client):
    """Agent handles 'complete task 999' gracefully with user-friendly message"""
    pass  # TODO: Implement after MCP fix


# T066: Multi-turn Conversations
@pytest.mark.skip(reason="Testing deferred to end - see KNOWN_ISSUES.md")
def test_multi_turn_conversation_with_context(client):
    """
    User: 'Show my tasks'
    Agent: [lists tasks]
    User: 'Mark task 2 done'
    Agent: [marks task 2 complete using context]
    """
    pass  # TODO: Implement after MCP fix
