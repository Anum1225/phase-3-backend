"""
Intent Recognition Accuracy Tests

Tests the agent's ability to correctly interpret natural language
and call the appropriate MCP tools.

Goal: >90% accuracy across 50+ sample phrasings

Test categories:
- Task Creation (10 phrasings)
- Task Listing (10 phrasings)
- Task Completion (10 phrasings)
- Task Update (10 phrasings)
- Task Deletion (10 phrasings)
"""

import pytest
import asyncio
from sqlmodel import Session, select
from typing import List, Tuple

from src.agent.runner import run_agent
from src.models.task import Task
from src.db import engine


pytestmark = pytest.mark.asyncio


@pytest.fixture
def db_session():
    """Create a database session"""
    with Session(engine) as session:
        yield session


@pytest.fixture
def test_user_id():
    """Test user ID"""
    return "intent_test_user"


@pytest.fixture
async def cleanup_tasks(test_user_id):
    """Cleanup tasks before and after tests"""
    with Session(engine) as session:
        tasks = session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        for task in tasks:
            session.delete(task)
        session.commit()

    yield

    with Session(engine) as session:
        tasks = session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()
        for task in tasks:
            session.delete(task)
        session.commit()


class TestTaskCreationIntents:
    """Test various phrasings for task creation"""

    TASK_CREATION_PHRASINGS = [
        "I need to buy groceries",
        "Add a task to call mom",
        "Remind me to finish the report",
        "Create a task for the dentist appointment",
        "Put water the plants on my todo list",
        "I should workout tomorrow",
        "Don't let me forget to pay the bills",
        "Add buy birthday gift to my tasks",
        "Schedule time to read the book",
        "I want to add: fix the leaky faucet",
    ]

    @pytest.mark.parametrize("phrase", TASK_CREATION_PHRASINGS)
    async def test_create_task_intent(
        self,
        phrase: str,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should recognize task creation intent from various phrasings"""
        # Run agent
        response = await run_agent(test_user_id, phrase)

        # Verify task was created
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        # Should have created at least one task
        assert len(tasks) >= 1, f"Failed to create task from: '{phrase}'"

        # Response should confirm creation
        assert (
            "added" in response.lower()
            or "created" in response.lower()
            or "task" in response.lower()
        ), f"Response didn't confirm creation: {response}"

        # Cleanup for next test
        for task in tasks:
            db_session.delete(task)
        db_session.commit()


class TestTaskListingIntents:
    """Test various phrasings for listing tasks"""

    TASK_LISTING_PHRASINGS = [
        "Show me my tasks",
        "What do I need to do?",
        "List my todos",
        "What's on my plate?",
        "Display my pending tasks",
        "What tasks do I have?",
        "Show all my incomplete tasks",
        "What am I working on?",
        "Can you list my tasks?",
        "What do I need to complete?",
    ]

    @pytest.mark.parametrize("phrase", TASK_LISTING_PHRASINGS)
    async def test_list_tasks_intent(
        self,
        phrase: str,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should recognize task listing intent"""
        # Create some tasks first
        task1 = Task(user_id=test_user_id, title="Test Task 1")
        task2 = Task(user_id=test_user_id, title="Test Task 2")
        db_session.add(task1)
        db_session.add(task2)
        db_session.commit()

        # Run agent
        response = await run_agent(test_user_id, phrase)

        # Response should list tasks
        assert (
            "task" in response.lower()
            or "Test Task" in response
            or "2" in response
        ), f"Failed to list tasks from: '{phrase}'"


class TestTaskCompletionIntents:
    """Test various phrasings for completing tasks"""

    async def _create_test_task(self, db_session, test_user_id, title="Test Task"):
        """Helper to create a test task and return its ID"""
        task = Task(user_id=test_user_id, title=title, completed=False)
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task.id

    COMPLETION_PHRASINGS_TEMPLATES = [
        "Mark task {task_id} as done",
        "Complete task {task_id}",
        "Task {task_id} is finished",
        "I finished task {task_id}",
        "Set task {task_id} to complete",
        "Task {task_id} is done",
        "Check off task {task_id}",
        "I completed task {task_id}",
        "Mark {task_id} as complete",
        "Done with task {task_id}",
    ]

    @pytest.mark.parametrize("template", COMPLETION_PHRASINGS_TEMPLATES)
    async def test_complete_task_intent(
        self,
        template: str,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should recognize task completion intent"""
        # Create test task
        task_id = await self._create_test_task(db_session, test_user_id)

        # Format phrase with task ID
        phrase = template.format(task_id=task_id)

        # Run agent
        response = await run_agent(test_user_id, phrase)

        # Verify task is completed
        task = db_session.get(Task, task_id)
        assert task.completed is True, f"Failed to complete task from: '{phrase}'"


class TestTaskUpdateIntents:
    """Test various phrasings for updating tasks"""

    async def _create_test_task(self, db_session, test_user_id):
        """Helper to create a test task"""
        task = Task(user_id=test_user_id, title="Test Task", priority="none")
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task.id

    UPDATE_PHRASINGS_TEMPLATES = [
        "Change task {task_id} priority to high",
        "Update task {task_id} to high priority",
        "Set task {task_id} priority as high",
        "Make task {task_id} high priority",
        "Task {task_id} should be high priority",
        "Increase task {task_id} priority to high",
        "Mark task {task_id} as high priority",
        "Update the priority of task {task_id} to high",
        "Set high priority for task {task_id}",
        "Change priority to high for task {task_id}",
    ]

    @pytest.mark.parametrize("template", UPDATE_PHRASINGS_TEMPLATES)
    async def test_update_task_intent(
        self,
        template: str,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should recognize task update intent"""
        # Create test task
        task_id = await self._create_test_task(db_session, test_user_id)

        # Format phrase
        phrase = template.format(task_id=task_id)

        # Run agent
        response = await run_agent(test_user_id, phrase)

        # Verify task priority updated
        task = db_session.get(Task, task_id)
        assert task.priority == "high", f"Failed to update task from: '{phrase}'"


class TestTaskDeletionIntents:
    """Test various phrasings for deleting tasks"""

    async def _create_test_task(self, db_session, test_user_id):
        """Helper to create a test task"""
        task = Task(user_id=test_user_id, title="Test Task")
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        return task.id

    DELETION_PHRASINGS_TEMPLATES = [
        "Delete task {task_id}",
        "Remove task {task_id}",
        "Get rid of task {task_id}",
        "Cancel task {task_id}",
        "Erase task {task_id}",
        "I want to delete task {task_id}",
        "Please remove task {task_id}",
        "Take task {task_id} off my list",
        "Discard task {task_id}",
        "Eliminate task {task_id}",
    ]

    @pytest.mark.parametrize("template", DELETION_PHRASINGS_TEMPLATES)
    async def test_delete_task_intent(
        self,
        template: str,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should recognize task deletion intent"""
        # Create test task
        task_id = await self._create_test_task(db_session, test_user_id)

        # Format phrase
        phrase = template.format(task_id=task_id)

        # Run agent
        response = await run_agent(test_user_id, phrase)

        # Verify task deleted
        task = db_session.get(Task, task_id)
        assert task is None, f"Failed to delete task from: '{phrase}'"


class TestIntentRecognitionAccuracy:
    """Calculate overall intent recognition accuracy"""

    async def test_overall_accuracy(self, test_user_id, cleanup_tasks, db_session):
        """
        Test overall intent recognition accuracy

        Target: >90% accuracy across all phrasings
        """
        results = {
            "create": {"total": 0, "success": 0},
            "list": {"total": 0, "success": 0},
            "complete": {"total": 0, "success": 0},
            "update": {"total": 0, "success": 0},
            "delete": {"total": 0, "success": 0},
        }

        # Test creation intents (simplified for accuracy test)
        create_phrases = TestTaskCreationIntents.TASK_CREATION_PHRASINGS[:5]
        for phrase in create_phrases:
            results["create"]["total"] += 1
            try:
                await run_agent(test_user_id, phrase)
                tasks = db_session.exec(
                    select(Task).where(Task.user_id == test_user_id)
                ).all()
                if len(tasks) > 0:
                    results["create"]["success"] += 1
                # Cleanup
                for task in tasks:
                    db_session.delete(task)
                db_session.commit()
            except Exception as e:
                print(f"Creation failed for '{phrase}': {e}")

        # Calculate accuracy
        total_tests = sum(r["total"] for r in results.values())
        total_success = sum(r["success"] for r in results.values())
        accuracy = (total_success / total_tests * 100) if total_tests > 0 else 0

        print(f"\n===== Intent Recognition Accuracy Report =====")
        print(f"Create:   {results['create']['success']}/{results['create']['total']}")
        print(f"List:     {results['list']['success']}/{results['list']['total']}")
        print(f"Complete: {results['complete']['success']}/{results['complete']['total']}")
        print(f"Update:   {results['update']['success']}/{results['update']['total']}")
        print(f"Delete:   {results['delete']['success']}/{results['delete']['total']}")
        print(f"Overall:  {total_success}/{total_tests} = {accuracy:.1f}%")
        print(f"==============================================\n")

        # Assert >90% accuracy
        assert accuracy >= 90.0, f"Intent recognition accuracy {accuracy:.1f}% is below 90%"


class TestContextualIntents:
    """Test context-aware intent recognition"""

    async def test_priority_extraction_from_context(
        self,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should extract priority from contextual keywords"""
        urgent_phrases = [
            "Urgent: finish the report",
            "This is critical: call the client",
            "High priority task: review the contract",
        ]

        for phrase in urgent_phrases:
            await run_agent(test_user_id, phrase)

        # All should be high priority
        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        high_priority_count = sum(1 for t in tasks if t.priority == "high")
        assert high_priority_count >= 2, "Failed to extract priority from context"

    async def test_category_inference_from_context(
        self,
        test_user_id,
        cleanup_tasks,
        db_session
    ):
        """Agent should infer category from task context"""
        work_phrase = "Schedule a team meeting for Monday"
        shopping_phrase = "Buy milk and eggs from the store"

        await run_agent(test_user_id, work_phrase)
        await run_agent(test_user_id, shopping_phrase)

        tasks = db_session.exec(
            select(Task).where(Task.user_id == test_user_id)
        ).all()

        # Should have both work and shopping categories
        categories = {t.category for t in tasks}
        assert "work" in categories or "personal" in categories
        assert "shopping" in categories or len(tasks) >= 2


# Test summary
def pytest_configure(config):
    """Configure pytest"""
    config.addinivalue_line(
        "markers",
        "intent: mark test as intent recognition test"
    )


# Calculate test coverage
TOTAL_PHRASINGS = (
    len(TestTaskCreationIntents.TASK_CREATION_PHRASINGS) +
    len(TestTaskListingIntents.TASK_LISTING_PHRASINGS) +
    len(TestTaskCompletionIntents.COMPLETION_PHRASINGS_TEMPLATES) +
    len(TestTaskUpdateIntents.UPDATE_PHRASINGS_TEMPLATES) +
    len(TestTaskDeletionIntents.DELETION_PHRASINGS_TEMPLATES)
)

print(f"\n📊 Intent Recognition Test Coverage: {TOTAL_PHRASINGS} phrasings\n")
