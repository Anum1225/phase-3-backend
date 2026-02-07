"""
E2E Tests for Task Creation via Chat (Phase 6 - User Story 1)

These tests verify the MVP functionality: Users can create tasks via natural
language without forms or UI clicks.

Test Coverage:
- T055: Basic task creation via chat
- T056: Natural language variations (10+ phrasings)
- T057: Task appears in user's task list
- T058: Complex multi-part task descriptions
- T059: Friendly confirmation messages

Note: These tests require the MCP server to be running and accessible.
"""

import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, select
import json

from main import app
from models import Task, User
from db import get_session
from src.models import Conversation, Message


# Fixtures

@pytest.fixture
def client():
    """FastAPI test client"""
    return TestClient(app)


@pytest.fixture
def test_user(client):
    """Create a test user for authentication"""
    # Note: In production, this would use Better Auth
    # For testing, we'll create a user directly
    user_data = {
        "email": "test@example.com",
        "name": "Test User"
    }

    response = client.post("/test/users", params=user_data)
    assert response.status_code == 200

    return response.json()


@pytest.fixture
def auth_headers(test_user):
    """Generate JWT token headers for test user"""
    # Note: In production, this would use Better Auth to generate real JWT
    # For testing, we'll use a mock token
    # TODO: Implement proper JWT generation for tests
    return {
        "Authorization": f"Bearer mock-token-{test_user['id']}"
    }


# Test Suite: T055 - Basic Task Creation


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
def test_create_task_via_chat_basic(client, test_user, auth_headers):
    """
    T055: Basic task creation via chat

    User sends: "I need to buy groceries"
    Expected: Task created with title "Buy groceries"
    """
    user_id = test_user["id"]

    # Send chat message
    response = client.post(
        f"/api/{user_id}/chat",
        json={"message": "I need to buy groceries"},
        headers=auth_headers
    )

    # Should return SSE stream with 200
    assert response.status_code == 200

    # Parse SSE response
    sse_data = response.text.split("data: ")[1] if "data: " in response.text else None
    assert sse_data is not None

    response_data = json.loads(sse_data)

    # Verify conversation created
    assert "conversation_id" in response_data
    conversation_id = response_data["conversation_id"]

    # Verify friendly confirmation
    assert "message" in response_data
    assert any(keyword in response_data["message"].lower()
               for keyword in ["created", "added", "task", "groceries"])

    # Verify task was created in database
    response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    assert response.status_code == 200

    tasks = response.json()
    assert len(tasks) > 0

    # Find the grocery task
    grocery_task = next(
        (task for task in tasks if "groceries" in task["title"].lower()),
        None
    )
    assert grocery_task is not None
    assert grocery_task["user_id"] == user_id
    assert grocery_task["completed"] is False


# Test Suite: T056 - Natural Language Variations


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
@pytest.mark.parametrize("message,expected_keyword", [
    ("Add a task to buy milk", "milk"),
    ("I need to call the doctor", "doctor"),
    ("Remind me to send the email", "email"),
    ("Don't forget to finish the report", "report"),
    ("Schedule a meeting with the team", "meeting"),
    ("Buy birthday gift for mom", "gift"),
    ("Complete the project presentation", "presentation"),
    ("Pay the electricity bill", "bill"),
    ("Book flight tickets for vacation", "flight"),
    ("Water the plants", "plants"),
])
def test_create_task_natural_language_variations(
    client, test_user, auth_headers, message, expected_keyword
):
    """
    T056: Test task creation with 10 different natural language phrasings

    Verifies that the agent correctly interprets various ways users might
    express task creation intent.
    """
    user_id = test_user["id"]

    # Send chat message
    response = client.post(
        f"/api/{user_id}/chat",
        json={"message": message},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Parse response
    sse_data = response.text.split("data: ")[1] if "data: " in response.text else None
    response_data = json.loads(sse_data)

    # Verify task created
    tasks_response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    tasks = tasks_response.json()

    # Find task with expected keyword
    matching_task = next(
        (task for task in tasks if expected_keyword.lower() in task["title"].lower()),
        None
    )

    assert matching_task is not None, f"Task with keyword '{expected_keyword}' not found"
    assert matching_task["user_id"] == user_id


# Test Suite: T057 - Task Verification


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
def test_task_appears_in_list_after_chat_creation(client, test_user, auth_headers):
    """
    T057: Verify task appears in user's task list after creation via chat

    Complete flow:
    1. User has no tasks initially
    2. User creates task via chat
    3. Task appears in GET /tasks endpoint
    4. Task has correct properties
    """
    user_id = test_user["id"]

    # 1. Verify user has no tasks initially
    response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    initial_tasks = response.json()
    initial_count = len(initial_tasks)

    # 2. Create task via chat
    chat_message = "Add a task to prepare presentation for Monday"
    response = client.post(
        f"/api/{user_id}/chat",
        json={"message": chat_message},
        headers=auth_headers
    )
    assert response.status_code == 200

    # 3. Verify task appears in list
    response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    assert response.status_code == 200

    final_tasks = response.json()
    assert len(final_tasks) == initial_count + 1, "Task count should increase by 1"

    # 4. Verify task properties
    new_task = final_tasks[-1]  # Assuming newest task is last
    assert "presentation" in new_task["title"].lower()
    assert new_task["user_id"] == user_id
    assert new_task["completed"] is False
    assert "id" in new_task
    assert "created_at" in new_task


# Test Suite: T058 - Complex Descriptions


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
@pytest.mark.parametrize("complex_message,expected_elements", [
    (
        "I need to buy groceries: milk, bread, eggs, and cheese from the store",
        ["milk", "bread", "eggs", "cheese"]
    ),
    (
        "Prepare for meeting: review slides, print handouts, and set up projector",
        ["slides", "handouts", "projector"]
    ),
    (
        "Complete project tasks: finish coding, write tests, update documentation, and submit PR",
        ["coding", "tests", "documentation"]
    ),
])
def test_create_task_with_complex_description(
    client, test_user, auth_headers, complex_message, expected_elements
):
    """
    T058: Test task creation with complex multi-part descriptions

    Verifies that the agent can handle detailed task descriptions with
    multiple components and creates appropriate tasks.
    """
    user_id = test_user["id"]

    # Send complex message
    response = client.post(
        f"/api/{user_id}/chat",
        json={"message": complex_message},
        headers=auth_headers
    )

    assert response.status_code == 200

    # Get tasks
    tasks_response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    tasks = tasks_response.json()

    # Verify task was created and contains key elements
    # Note: The agent might create one task or multiple sub-tasks
    # We verify that at least one task contains the main elements

    all_task_text = " ".join(
        [task.get("title", "") + " " + task.get("description", "")
         for task in tasks]
    ).lower()

    for element in expected_elements:
        assert element.lower() in all_task_text, \
            f"Expected element '{element}' not found in created tasks"


# Test Suite: T059 - Friendly Confirmations


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
def test_agent_provides_friendly_confirmation(client, test_user, auth_headers):
    """
    T059: Verify agent provides friendly confirmation messages

    The agent should respond with natural, helpful confirmations that:
    - Acknowledge the task was created
    - Mention the task details
    - Use friendly, conversational language
    """
    user_id = test_user["id"]

    # Test messages and expected confirmation patterns
    test_cases = [
        {
            "message": "Add a task to call mom",
            "confirmation_patterns": [
                "created",
                "added",
                "task",
                "call",
                "mom"
            ]
        },
        {
            "message": "I need to finish homework",
            "confirmation_patterns": [
                "created",
                "added",
                "homework"
            ]
        },
    ]

    for test_case in test_cases:
        # Send message
        response = client.post(
            f"/api/{user_id}/chat",
            json={"message": test_case["message"]},
            headers=auth_headers
        )

        assert response.status_code == 200

        # Parse response
        sse_data = response.text.split("data: ")[1] if "data: " in response.text else None
        response_data = json.loads(sse_data)

        # Verify friendly confirmation
        confirmation_message = response_data["message"].lower()

        # Check for friendly tone indicators
        assert any(pattern in confirmation_message
                   for pattern in test_case["confirmation_patterns"]), \
            f"Confirmation '{confirmation_message}' doesn't match expected patterns"

        # Verify it's not just a generic "OK" or "Done"
        assert len(confirmation_message.split()) > 2, \
            "Confirmation should be conversational, not just 1-2 words"


# Integration Test: Complete Flow


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
def test_complete_task_creation_flow(client, test_user, auth_headers):
    """
    Integration test: Complete task creation flow from chat to task list

    Verifies the entire user journey:
    1. User sends natural language message
    2. Agent interprets intent
    3. Agent calls MCP add_task tool
    4. Task is created in database
    5. Agent responds with confirmation
    6. Task appears in user's task list
    7. Conversation is persisted
    """
    user_id = test_user["id"]

    # 1. User sends message
    message = "I need to prepare for tomorrow's presentation"

    response = client.post(
        f"/api/{user_id}/chat",
        json={"message": message},
        headers=auth_headers
    )

    assert response.status_code == 200

    # 2. Parse agent response
    sse_data = response.text.split("data: ")[1] if "data: " in response.text else None
    response_data = json.loads(sse_data)

    conversation_id = response_data["conversation_id"]

    # 3. Verify task created
    tasks_response = client.get(f"/api/{user_id}/tasks", headers=auth_headers)
    tasks = tasks_response.json()

    presentation_task = next(
        (task for task in tasks if "presentation" in task["title"].lower()),
        None
    )

    assert presentation_task is not None

    # 4. Verify conversation persisted
    conv_response = client.get(
        f"/api/{user_id}/conversations/{conversation_id}",
        headers=auth_headers
    )

    assert conv_response.status_code == 200

    conversation = conv_response.json()
    assert "messages" in conversation
    assert len(conversation["messages"]) >= 2  # User message + Assistant response

    # Verify user message
    user_message = next(
        (msg for msg in conversation["messages"] if msg["role"] == "USER"),
        None
    )
    assert user_message is not None
    assert user_message["content"] == message

    # Verify assistant response
    assistant_message = next(
        (msg for msg in conversation["messages"] if msg["role"] == "ASSISTANT"),
        None
    )
    assert assistant_message is not None
    assert len(assistant_message["content"]) > 0


# Performance Test


@pytest.mark.skip(reason="MCP server connection issue - see KNOWN_ISSUES.md")
@pytest.mark.slow
def test_task_creation_performance(client, test_user, auth_headers):
    """
    Performance test: Task creation should complete within acceptable time

    Target: < 2 seconds average response time (per spec)
    """
    import time

    user_id = test_user["id"]
    response_times = []

    test_messages = [
        "Add task: buy milk",
        "I need to call John",
        "Remind me to send email",
    ]

    for message in test_messages:
        start_time = time.time()

        response = client.post(
            f"/api/{user_id}/chat",
            json={"message": message},
            headers=auth_headers
        )

        end_time = time.time()
        response_time = end_time - start_time
        response_times.append(response_time)

        assert response.status_code == 200

    avg_response_time = sum(response_times) / len(response_times)

    assert avg_response_time < 2.0, \
        f"Average response time {avg_response_time:.2f}s exceeds 2s target"

    print(f"\nPerformance Results:")
    print(f"  Average: {avg_response_time:.2f}s")
    print(f"  Min: {min(response_times):.2f}s")
    print(f"  Max: {max(response_times):.2f}s")
