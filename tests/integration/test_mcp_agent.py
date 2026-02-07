"""
Integration Tests for Agent + MCP Tool Execution

Tests the complete flow:
- Agent receives natural language input
- Agent calls appropriate MCP tools
- MCP tools execute database operations
- Agent returns natural language response

Prerequisites:
- Backend server must be running (uvicorn main:app)
- MCP server must be mounted at /api/mcp
- Database must be accessible
- GOOGLE_API_KEY must be set
"""

import pytest
import asyncio
from datetime import datetime
from sqlmodel import Session, select

from src.agent.runner import run_agent, create_agent
from src.models.task import Task
from src.db import engine


pytestmark = pytest.mark.asyncio


@pytest.fixture
def db_session():
    """Create a database session for testing"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user_id():
    """Provide a test user ID"""
    return "test_user_agent_integration"


@pytest.fixture
async def cleanup_tasks(test_user_id):
    """Cleanup test tasks before and after tests"""
    # Cleanup before test
    with Session(engine) as session:
        tasks = session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        for task in tasks:
            session.delete(task)
        session.commit()

    yield

    # Cleanup after test
    with Session(engine) as session:
        tasks = session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        for task in tasks:
            session.delete(task)
        session.commit()


class TestAgentMCPIntegration:
    """Test agent with MCP tool execution"""

    async def test_agent_can_create(self):
        """Test that agent can be created successfully"""
        agent, mcp_server = await create_agent()

        try:
            assert agent is not None
            assert agent.name == "Todo Assistant"
            assert mcp_server is not None
        finally:
            await mcp_server.__aexit__(None, None, None)

    async def test_agent_has_mcp_tools(self):
        """Test that agent has access to MCP tools"""
        agent, mcp_server = await create_agent()

        try:
            # Agent should have MCP servers configured
            assert len(agent.mcp_servers) > 0
            assert agent.mcp_servers[0].name == "Todo MCP Server"
        finally:
            await mcp_server.__aexit__(None, None, None)


class TestAgentTaskCreation:
    """Test agent creating tasks via natural language"""

    async def test_create_task_simple(self, test_user_id, cleanup_tasks, db_session):
        """Agent should create task from simple phrase"""
        response = await run_agent(
            user_id=test_user_id,
            message="I need to buy groceries"
        )

        # Check response
        assert response is not None
        assert "groceries" in response.lower() or "task" in response.lower()

        # Verify task was created in database
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        assert len(tasks) >= 1
        # Find the grocery task
        grocery_task = next(
            (t for t in tasks if "groceries" in t.title.lower()),
            None
        )
        assert grocery_task is not None

    async def test_create_task_with_priority(self, test_user_id, cleanup_tasks, db_session):
        """Agent should extract priority from natural language"""
        response = await run_agent(
            user_id=test_user_id,
            message="Urgent: Finish the quarterly report by Friday"
        )

        # Verify task was created with high priority
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        assert len(tasks) >= 1
        report_task = next(
            (t for t in tasks if "report" in t.title.lower()),
            None
        )
        assert report_task is not None
        assert report_task.priority == "high"

    async def test_create_task_with_category(self, test_user_id, cleanup_tasks, db_session):
        """Agent should infer category from context"""
        response = await run_agent(
            user_id=test_user_id,
            message="Schedule a team meeting for next week"
        )

        # Verify task was created with work category
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        meeting_task = next(
            (t for t in tasks if "meeting" in t.title.lower()),
            None
        )
        assert meeting_task is not None
        assert meeting_task.category == "work"


class TestAgentTaskListing:
    """Test agent listing tasks via natural language"""

    async def test_list_all_tasks(self, test_user_id, cleanup_tasks, db_session):
        """Agent should list all tasks"""
        # Create some tasks first
        task1 = Task(user_id=test_user_id, title="Task 1", completed=False)
        task2 = Task(user_id=test_user_id, title="Task 2", completed=True)
        db_session.add(task1)
        db_session.add(task2)
        db_session.commit()

        response = await run_agent(
            user_id=test_user_id,
            message="Show me my tasks"
        )

        # Response should mention tasks
        assert "task" in response.lower()
        # Should mention count or list
        assert "2" in response or "Task 1" in response or "Task 2" in response

    async def test_list_pending_tasks(self, test_user_id, cleanup_tasks, db_session):
        """Agent should filter pending tasks"""
        # Create tasks
        pending = Task(user_id=test_user_id, title="Pending Task", completed=False)
        completed = Task(user_id=test_user_id, title="Done Task", completed=True)
        db_session.add(pending)
        db_session.add(completed)
        db_session.commit()

        response = await run_agent(
            user_id=test_user_id,
            message="Show me my pending tasks"
        )

        # Should list pending tasks
        assert "pending" in response.lower() or "task" in response.lower()


class TestAgentTaskCompletion:
    """Test agent completing tasks"""

    async def test_complete_task_by_id(self, test_user_id, cleanup_tasks, db_session):
        """Agent should complete task when given task ID"""
        # Create task
        task = Task(user_id=test_user_id, title="Test Task", completed=False)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        task_id = task.id

        response = await run_agent(
            user_id=test_user_id,
            message=f"Mark task {task_id} as complete"
        )

        # Verify task is completed
        db_session.refresh(task)
        assert task.completed is True


class TestAgentTaskUpdate:
    """Test agent updating tasks"""

    async def test_update_task_priority(self, test_user_id, cleanup_tasks, db_session):
        """Agent should update task priority"""
        # Create task
        task = Task(
            user_id=test_user_id,
            title="Important Task",
            priority="none"
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        task_id = task.id

        response = await run_agent(
            user_id=test_user_id,
            message=f"Change task {task_id} priority to high"
        )

        # Verify priority updated
        db_session.refresh(task)
        assert task.priority == "high"


class TestAgentTaskDeletion:
    """Test agent deleting tasks"""

    async def test_delete_task(self, test_user_id, cleanup_tasks, db_session):
        """Agent should delete task"""
        # Create task
        task = Task(user_id=test_user_id, title="Task to Delete")
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)

        task_id = task.id

        response = await run_agent(
            user_id=test_user_id,
            message=f"Delete task {task_id}"
        )

        # Verify task deleted
        deleted_task = db_session.get(Task, task_id)
        assert deleted_task is None


class TestAgentConversationalFlow:
    """Test multi-turn conversations"""

    async def test_multi_turn_conversation(self, test_user_id, cleanup_tasks, db_session):
        """Agent should handle multi-turn conversation"""
        # Turn 1: Create task
        response1 = await run_agent(
            user_id=test_user_id,
            message="Add a task to call the dentist"
        )
        assert "dentist" in response1.lower() or "task" in response1.lower()

        # Verify task created
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        assert len(tasks) >= 1

        # Turn 2: List tasks
        response2 = await run_agent(
            user_id=test_user_id,
            message="Show me what I need to do"
        )
        assert "task" in response2.lower()


class TestAgentErrorHandling:
    """Test agent error handling"""

    async def test_invalid_task_id(self, test_user_id, cleanup_tasks):
        """Agent should handle invalid task ID gracefully"""
        response = await run_agent(
            user_id=test_user_id,
            message="Complete task 999999"
        )

        # Should indicate task not found
        assert "not found" in response.lower() or "couldn't find" in response.lower()

    async def test_empty_message(self, test_user_id, cleanup_tasks):
        """Agent should handle empty/unclear messages"""
        response = await run_agent(
            user_id=test_user_id,
            message="hello"
        )

        # Should respond appropriately
        assert response is not None
        assert len(response) > 0


# Skip these tests if MCP server is not running
@pytest.mark.skipif(
    not pytest.config.getoption("--run-integration", default=False),
    reason="Integration tests require running MCP server"
)
class TestAgentWithRunningServer:
    """Tests that require MCP server to be running"""

    async def test_end_to_end_flow(self, test_user_id, cleanup_tasks, db_session):
        """Complete end-to-end flow: create, list, update, complete, delete"""
        # Create
        await run_agent(test_user_id, "I need to buy milk")

        # List
        response = await run_agent(test_user_id, "Show my tasks")
        assert "milk" in response.lower() or "task" in response.lower()

        # Get task ID
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        task_id = tasks[0].id

        # Update
        await run_agent(test_user_id, f"Change task {task_id} to high priority")

        # Complete
        await run_agent(test_user_id, f"Mark task {task_id} done")

        # Delete
        await run_agent(test_user_id, f"Delete task {task_id}")

        # Verify deleted
        final_tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        assert len(final_tasks) == 0
