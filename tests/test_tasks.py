"""
Integration tests for task management endpoints (User Story 1).

Tests the complete task CRUD functionality including:
- Task creation (POST /api/{user_id}/tasks)
- Task listing (GET /api/{user_id}/tasks)
- Task retrieval (GET /api/{user_id}/tasks/{task_id})
- Task update (PUT /api/{user_id}/tasks/{task_id})
- Task deletion (DELETE /api/{user_id}/tasks/{task_id})
- Task completion toggle (PATCH /api/{user_id}/tasks/{task_id}/complete)
- User isolation enforcement
- Error handling
"""

import jwt
import pytest
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlmodel import Session

from models import User, Task, TaskPriority, TaskCategory


# JWT token generation helper
def create_test_jwt(user_id: str, secret: str = "test-secret", expiry_minutes: int = 30) -> str:
    """
    Create a test JWT token for authentication.

    Args:
        user_id: User ID to encode in token
        secret: JWT secret (must match BETTER_AUTH_SECRET)
        expiry_minutes: Token expiration time in minutes

    Returns:
        Encoded JWT token string
    """
    payload = {
        "sub": user_id,
        "user_id": user_id,
        "exp": datetime.utcnow() + timedelta(minutes=expiry_minutes),
    }
    return jwt.encode(payload, secret, algorithm="HS256")


# Fixtures for test users and authentication
@pytest.fixture(name="test_user")
def test_user_fixture(session: Session):
    """Create a test user in the database"""
    from lib.password import hash_password

    user = User(
        email="testuser@example.com",
        name="Test User",
        password_hash=hash_password("TestPass123!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="other_user")
def other_user_fixture(session: Session):
    """Create a second test user for isolation testing"""
    from lib.password import hash_password

    user = User(
        email="otheruser@example.com",
        name="Other User",
        password_hash=hash_password("OtherPass123!"),
    )
    session.add(user)
    session.commit()
    session.refresh(user)
    return user


@pytest.fixture(name="auth_headers")
def auth_headers_fixture(test_user: User):
    """Generate authentication headers with JWT token"""
    token = create_test_jwt(test_user.id)
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(name="other_auth_headers")
def other_auth_headers_fixture(other_user: User):
    """Generate authentication headers for second user"""
    token = create_test_jwt(other_user.id)
    return {"Authorization": f"Bearer {token}"}


# ===== T023: Test task creation with valid data =====


class TestTaskCreation:
    """Test task creation endpoint"""

    def test_create_task_with_valid_data_returns_201(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T023: Test creating a task with valid data returns 201 Created"""
        # Arrange
        task_data = {
            "title": "Complete project proposal",
            "description": "Draft and submit Q1 proposal",
            "priority": "high",
            "category": "work",
        }

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Complete project proposal"
        assert data["description"] == "Draft and submit Q1 proposal"
        assert data["priority"] == "high"
        assert data["category"] == "work"
        assert data["completed"] is False
        assert data["user_id"] == test_user.id
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_task_with_minimal_data(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test creating a task with only required fields (title)"""
        # Arrange
        task_data = {"title": "Buy groceries"}

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()

        assert data["title"] == "Buy groceries"
        assert data["description"] is None
        assert data["priority"] == "none"  # Default
        assert data["category"] == "other"  # Default
        assert data["completed"] is False

    def test_create_task_defaults_priority_and_category(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test that priority and category default to 'none' and 'other'"""
        # Arrange
        task_data = {"title": "Default task"}

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 201
        data = response.json()
        assert data["priority"] == "none"
        assert data["category"] == "other"


# ===== T024: Test task creation with invalid data =====


class TestTaskCreationValidation:
    """Test task creation validation errors"""

    def test_create_task_with_empty_title_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T024: Test creating task with empty title returns 422 Unprocessable Entity"""
        # Arrange
        task_data = {"title": ""}

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422

    def test_create_task_with_title_too_long_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T024: Test creating task with title >200 chars returns 422"""
        # Arrange
        task_data = {"title": "A" * 201}  # 201 characters

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422

    def test_create_task_with_description_too_long_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T024: Test creating task with description >1000 chars returns 422"""
        # Arrange
        task_data = {
            "title": "Valid title",
            "description": "A" * 1001,  # 1001 characters
        }

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422

    def test_create_task_with_invalid_priority_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test creating task with invalid priority value returns 422"""
        # Arrange
        task_data = {
            "title": "Valid title",
            "priority": "invalid_priority",
        }

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422

    def test_create_task_with_invalid_category_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test creating task with invalid category value returns 422"""
        # Arrange
        task_data = {
            "title": "Valid title",
            "category": "invalid_category",
        }

        # Act
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json=task_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 422


# ===== T025: Test GET all tasks returns user's tasks only =====


class TestGetAllTasks:
    """Test listing all tasks for a user"""

    def test_get_all_tasks_returns_only_user_tasks(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """T025: Test GET /api/{user_id}/tasks returns only user's tasks"""
        # Arrange - Create tasks for both users
        task1 = Task(user_id=test_user.id, title="User 1 Task 1")
        task2 = Task(user_id=test_user.id, title="User 1 Task 2")
        task3 = Task(user_id=other_user.id, title="User 2 Task 1")

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert len(data) == 2
        titles = [task["title"] for task in data]
        assert "User 1 Task 1" in titles
        assert "User 1 Task 2" in titles
        assert "User 2 Task 1" not in titles

    def test_get_all_tasks_empty_list_when_no_tasks(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test GET all tasks returns empty list when user has no tasks"""
        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == []


# ===== T026: Test GET single task by ID =====


class TestGetSingleTask:
    """Test retrieving a single task"""

    def test_get_task_by_id_returns_200(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """T026: Test GET /api/{user_id}/tasks/{task_id} returns task details"""
        # Arrange
        task = Task(
            user_id=test_user.id,
            title="Test Task",
            description="Test Description",
            priority=TaskPriority.HIGH,
            category=TaskCategory.WORK,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks/{task.id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["id"] == task.id
        assert data["title"] == "Test Task"
        assert data["description"] == "Test Description"
        assert data["priority"] == "high"
        assert data["category"] == "work"


# ===== T027: Test UPDATE task =====


class TestUpdateTask:
    """Test updating task fields"""

    def test_update_task_updates_fields_correctly(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """T027: Test PUT /api/{user_id}/tasks/{task_id} updates task fields"""
        # Arrange
        task = Task(user_id=test_user.id, title="Original Title")
        session.add(task)
        session.commit()
        session.refresh(task)

        update_data = {
            "title": "Updated Title",
            "description": "Updated Description",
            "priority": "medium",
            "category": "personal",
            "completed": True,
        }

        # Act
        response = client.put(
            f"/api/{test_user.id}/tasks/{task.id}",
            json=update_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        assert data["title"] == "Updated Title"
        assert data["description"] == "Updated Description"
        assert data["priority"] == "medium"
        assert data["category"] == "personal"
        assert data["completed"] is True

    def test_update_task_partial_update_only_changes_provided_fields(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """Test partial update only changes provided fields"""
        # Arrange
        task = Task(
            user_id=test_user.id,
            title="Original Title",
            description="Original Description",
            priority=TaskPriority.LOW,
        )
        session.add(task)
        session.commit()
        session.refresh(task)

        # Only update priority
        update_data = {"priority": "high"}

        # Act
        response = client.put(
            f"/api/{test_user.id}/tasks/{task.id}",
            json=update_data,
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Priority should be updated
        assert data["priority"] == "high"
        # Other fields should remain unchanged
        assert data["title"] == "Original Title"
        assert data["description"] == "Original Description"


# ===== T028: Test DELETE task =====


class TestDeleteTask:
    """Test task deletion"""

    def test_delete_task_removes_from_database(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """T028: Test DELETE /api/{user_id}/tasks/{task_id} removes task"""
        # Arrange
        task = Task(user_id=test_user.id, title="Task to Delete")
        session.add(task)
        session.commit()
        session.refresh(task)
        task_id = task.id

        # Act
        response = client.delete(
            f"/api/{test_user.id}/tasks/{task_id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 204

        # Verify task was deleted
        deleted_task = session.get(Task, task_id)
        assert deleted_task is None


# ===== T029: Test PATCH toggle completion =====


class TestToggleTaskCompletion:
    """Test toggling task completion status"""

    def test_toggle_completion_changes_status(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        auth_headers: dict,
    ):
        """T029: Test PATCH /api/{user_id}/tasks/{task_id}/complete toggles status"""
        # Arrange
        task = Task(user_id=test_user.id, title="Task", completed=False)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act - Toggle from False to True
        response = client.patch(
            f"/api/{test_user.id}/tasks/{task.id}/complete",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is True

        # Act - Toggle back from True to False
        response = client.patch(
            f"/api/{test_user.id}/tasks/{task.id}/complete",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["completed"] is False


# ===== T030: Test user isolation =====


class TestUserIsolation:
    """Test user isolation - users cannot access other users' tasks"""

    def test_user_cannot_access_other_users_tasks(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """T030: Test user cannot access tasks belonging to another user"""
        # Arrange - Create task for other_user
        task = Task(user_id=other_user.id, title="Other User's Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act - test_user tries to access other_user's task
        response = client.get(
            f"/api/{other_user.id}/tasks/{task.id}",
            headers=auth_headers,  # test_user's token
        )

        # Assert
        assert response.status_code == 403
        assert "Not authorized" in response.json()["detail"]

    def test_user_cannot_create_task_for_other_user(
        self,
        client: TestClient,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """Test user cannot create tasks for another user"""
        # Arrange
        task_data = {"title": "Task for other user"}

        # Act - test_user tries to create task for other_user
        response = client.post(
            f"/api/{other_user.id}/tasks",
            json=task_data,
            headers=auth_headers,  # test_user's token
        )

        # Assert
        assert response.status_code == 403

    def test_user_cannot_update_other_users_task(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """Test user cannot update tasks belonging to another user"""
        # Arrange
        task = Task(user_id=other_user.id, title="Other User's Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act - test_user tries to update other_user's task
        response = client.put(
            f"/api/{other_user.id}/tasks/{task.id}",
            json={"title": "Hacked title"},
            headers=auth_headers,  # test_user's token
        )

        # Assert
        assert response.status_code == 403

    def test_user_cannot_delete_other_users_task(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """Test user cannot delete tasks belonging to another user"""
        # Arrange
        task = Task(user_id=other_user.id, title="Other User's Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act - test_user tries to delete other_user's task
        response = client.delete(
            f"/api/{other_user.id}/tasks/{task.id}",
            headers=auth_headers,  # test_user's token
        )

        # Assert
        assert response.status_code == 403


# ===== T031: Test 404 error when task ID does not exist =====


class TestTaskNotFound:
    """Test 404 errors for non-existent tasks"""

    def test_get_nonexistent_task_returns_404(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T031: Test GET non-existent task returns 404 Not Found"""
        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks/99999",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()

    def test_update_nonexistent_task_returns_404(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test UPDATE non-existent task returns 404"""
        # Act
        response = client.put(
            f"/api/{test_user.id}/tasks/99999",
            json={"title": "Updated"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404

    def test_delete_nonexistent_task_returns_404(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test DELETE non-existent task returns 404"""
        # Act
        response = client.delete(
            f"/api/{test_user.id}/tasks/99999",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404

    def test_toggle_completion_nonexistent_task_returns_404(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """Test PATCH completion on non-existent task returns 404"""
        # Act
        response = client.patch(
            f"/api/{test_user.id}/tasks/99999/complete",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 404


# ===== T032: Test 403 error when user_id mismatch =====


class TestUserIdMismatch:
    """Test 403 Forbidden errors for user_id mismatch"""

    def test_access_with_mismatched_user_id_returns_403(
        self,
        client: TestClient,
        session: Session,
        test_user: User,
        other_user: User,
        auth_headers: dict,
    ):
        """T032: Test accessing tasks with user_id != JWT token user_id returns 403"""
        # Arrange
        task = Task(user_id=test_user.id, title="Test Task")
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act - Use test_user's token but try to access other_user's endpoint
        response = client.get(
            f"/api/{other_user.id}/tasks",
            headers=auth_headers,  # test_user's token
        )

        # Assert
        assert response.status_code == 403
        assert "authorized" in response.json()["detail"].lower()


# ===== Unauthenticated Access Tests =====


class TestUnauthenticatedAccess:
    """Test that all endpoints require authentication"""

    def test_get_tasks_without_auth_returns_401(
        self, client: TestClient, test_user: User
    ):
        """Test GET tasks without authentication returns 401"""
        response = client.get(f"/api/{test_user.id}/tasks")
        assert response.status_code == 401

    def test_create_task_without_auth_returns_401(
        self, client: TestClient, test_user: User
    ):
        """Test POST task without authentication returns 401"""
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json={"title": "Test"},
        )
        assert response.status_code == 401

    def test_update_task_without_auth_returns_401(
        self, client: TestClient, test_user: User
    ):
        """Test PUT task without authentication returns 401"""
        response = client.put(
            f"/api/{test_user.id}/tasks/1",
            json={"title": "Updated"},
        )
        assert response.status_code == 401

    def test_delete_task_without_auth_returns_401(
        self, client: TestClient, test_user: User
    ):
        """Test DELETE task without authentication returns 401"""
        response = client.delete(f"/api/{test_user.id}/tasks/1")
        assert response.status_code == 401


# ===============================================================================
# USER STORY 2: TASK PRIORITIZATION TESTS (T038-T043)
# ===============================================================================


class TestPriorityFiltering:
    """Test priority filtering and sorting (User Story 2)"""

    def test_create_task_with_each_priority_level(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T038: Test creating tasks with different priority levels"""
        priorities = ["high", "medium", "low", "none"]

        for priority in priorities:
            response = client.post(
                f"/api/{test_user.id}/tasks",
                json={"title": f"Task with {priority} priority", "priority": priority},
                headers=auth_headers,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["priority"] == priority

    def test_update_task_priority(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T039: Test updating task priority"""
        # Arrange
        task = Task(user_id=test_user.id, title="Task", priority=TaskPriority.LOW)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act
        response = client.put(
            f"/api/{test_user.id}/tasks/{task.id}",
            json={"priority": "high"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["priority"] == "high"

    def test_filter_by_priority_returns_only_matching_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T040: Test filtering by priority returns only matching tasks"""
        # Arrange - Create tasks with different priorities
        task1 = Task(user_id=test_user.id, title="High priority", priority=TaskPriority.HIGH)
        task2 = Task(user_id=test_user.id, title="Medium priority", priority=TaskPriority.MEDIUM)
        task3 = Task(user_id=test_user.id, title="Another high", priority=TaskPriority.HIGH)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act - Filter by high priority
        response = client.get(
            f"/api/{test_user.id}/tasks?priority=high",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for task in data:
            assert task["priority"] == "high"

    def test_invalid_priority_value_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T041: Test creating task with invalid priority returns 422"""
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json={"title": "Task", "priority": "invalid"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_sort_by_priority_orders_correctly(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T042: Test sorting by priority orders tasks correctly (high, medium, low, none)"""
        # Arrange - Create tasks in random order
        task1 = Task(user_id=test_user.id, title="None priority", priority=TaskPriority.NONE)
        task2 = Task(user_id=test_user.id, title="High priority", priority=TaskPriority.HIGH)
        task3 = Task(user_id=test_user.id, title="Low priority", priority=TaskPriority.LOW)
        task4 = Task(user_id=test_user.id, title="Medium priority", priority=TaskPriority.MEDIUM)

        session.add_all([task1, task2, task3, task4])
        session.commit()

        # Act - Sort by priority descending (high to none)
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=priority&order=desc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        priorities = [task["priority"] for task in data]
        assert priorities == ["high", "medium", "low", "none"]

    def test_priority_defaults_to_none(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T043: Test priority defaults to 'none' when not specified"""
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json={"title": "Task without priority"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["priority"] == "none"


# ===============================================================================
# USER STORY 3: TASK CATEGORIZATION TESTS (T048-T053)
# ===============================================================================


class TestCategoryFiltering:
    """Test category filtering (User Story 3)"""

    def test_create_task_with_each_category(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T048: Test creating tasks with different categories"""
        categories = ["work", "personal", "shopping", "health", "other"]

        for category in categories:
            response = client.post(
                f"/api/{test_user.id}/tasks",
                json={"title": f"Task in {category}", "category": category},
                headers=auth_headers,
            )
            assert response.status_code == 201
            data = response.json()
            assert data["category"] == category

    def test_update_task_category(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T049: Test updating task category"""
        # Arrange
        task = Task(user_id=test_user.id, title="Task", category=TaskCategory.OTHER)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act
        response = client.put(
            f"/api/{test_user.id}/tasks/{task.id}",
            json={"category": "work"},
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["category"] == "work"

    def test_filter_by_category_returns_only_matching_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T050: Test filtering by category returns only matching tasks"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Work task", category=TaskCategory.WORK)
        task2 = Task(user_id=test_user.id, title="Personal task", category=TaskCategory.PERSONAL)
        task3 = Task(user_id=test_user.id, title="Another work", category=TaskCategory.WORK)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?category=work",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for task in data:
            assert task["category"] == "work"

    def test_invalid_category_value_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T051: Test creating task with invalid category returns 422"""
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json={"title": "Task", "category": "invalid_category"},
            headers=auth_headers,
        )
        assert response.status_code == 422

    def test_category_defaults_to_other(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T052: Test category defaults to 'other' when not specified"""
        response = client.post(
            f"/api/{test_user.id}/tasks",
            json={"title": "Task without category"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["category"] == "other"

    def test_task_displays_assigned_category(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T053: Test each task displays its assigned category in response"""
        # Arrange
        task = Task(user_id=test_user.id, title="Shopping", category=TaskCategory.SHOPPING)
        session.add(task)
        session.commit()
        session.refresh(task)

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks/{task.id}",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json()["category"] == "shopping"


# ===============================================================================
# USER STORY 4: TASK SEARCH TESTS (T060-T066)
# ===============================================================================


class TestTaskSearch:
    """Test search functionality (User Story 4)"""

    def test_search_in_title_returns_matching_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T060: Test search in title returns matching tasks"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Meeting with team")
        task2 = Task(user_id=test_user.id, title="Buy groceries")
        task3 = Task(user_id=test_user.id, title="Schedule meeting")

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?search=meeting",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        titles = [task["title"] for task in data]
        assert "Meeting with team" in titles
        assert "Schedule meeting" in titles

    def test_search_in_description_returns_matching_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T061: Test search in description returns matching tasks"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1", description="Discuss project timeline")
        task2 = Task(user_id=test_user.id, title="Task 2", description="Review code")
        task3 = Task(user_id=test_user.id, title="Task 3", description="Update project docs")

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?search=project",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2

    def test_search_is_case_insensitive(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T062: Test search is case-insensitive"""
        # Arrange
        task = Task(user_id=test_user.id, title="important meeting")
        session.add(task)
        session.commit()

        # Act - Search with different cases
        for query in ["MEETING", "Meeting", "meeting", "MeEtInG"]:
            response = client.get(
                f"/api/{test_user.id}/tasks?search={query}",
                headers=auth_headers,
            )
            assert response.status_code == 200
            assert len(response.json()) == 1

    def test_search_with_no_matches_returns_empty_list(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T063: Test search with no matches returns empty list"""
        # Arrange
        task = Task(user_id=test_user.id, title="Buy groceries")
        session.add(task)
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?search=nonexistent",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_search_with_special_characters_is_safe(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T064: Test search with special characters is safe (no SQL injection)"""
        # Arrange
        task = Task(user_id=test_user.id, title="Normal task")
        session.add(task)
        session.commit()

        # Act - Try SQL injection patterns
        sql_injection_patterns = [
            "'; DROP TABLE task; --",
            "1' OR '1'='1",
            "%'; DELETE FROM task WHERE '1'='1",
        ]

        for pattern in sql_injection_patterns:
            response = client.get(
                f"/api/{test_user.id}/tasks?search={pattern}",
                headers=auth_headers,
            )
            # Should not crash, should return safe results
            assert response.status_code == 200

    def test_empty_search_query_returns_all_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T065: Test empty/missing search query returns all tasks"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1")
        task2 = Task(user_id=test_user.id, title="Task 2")
        session.add_all([task1, task2])
        session.commit()

        # Act - No search parameter
        response = client.get(
            f"/api/{test_user.id}/tasks",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert len(response.json()) == 2

    def test_search_with_multiple_matching_tasks(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T066: Test search returns all matching tasks"""
        # Arrange
        tasks = [
            Task(user_id=test_user.id, title=f"Project task {i}")
            for i in range(1, 6)
        ]
        session.add_all(tasks)
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?search=project",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert len(response.json()) == 5


# ===============================================================================
# USER STORY 5: MULTI-CRITERIA FILTERING TESTS (T071-T077)
# ===============================================================================


class TestMultiCriteriaFiltering:
    """Test multi-criteria filtering (User Story 5)"""

    def test_filter_by_status_only(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T071: Test filtering by status (pending, completed)"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Pending task", completed=False)
        task2 = Task(user_id=test_user.id, title="Completed task", completed=True)
        task3 = Task(user_id=test_user.id, title="Another pending", completed=False)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act - Filter by pending
        response = client.get(
            f"/api/{test_user.id}/tasks?status=pending",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        for task in data:
            assert task["completed"] is False

    def test_filter_by_status_and_priority(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T072: Test filtering by status + priority combination"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1", completed=False, priority=TaskPriority.HIGH)
        task2 = Task(user_id=test_user.id, title="Task 2", completed=True, priority=TaskPriority.HIGH)
        task3 = Task(user_id=test_user.id, title="Task 3", completed=False, priority=TaskPriority.LOW)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act - Filter by pending + high priority
        response = client.get(
            f"/api/{test_user.id}/tasks?status=pending&priority=high",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["completed"] is False
        assert data[0]["priority"] == "high"

    def test_filter_by_status_and_category(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T073: Test filtering by status + category combination"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1", completed=False, category=TaskCategory.WORK)
        task2 = Task(user_id=test_user.id, title="Task 2", completed=True, category=TaskCategory.WORK)
        task3 = Task(user_id=test_user.id, title="Task 3", completed=False, category=TaskCategory.PERSONAL)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?status=pending&category=work",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["completed"] is False
        assert data[0]["category"] == "work"

    def test_filter_by_priority_and_category(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T074: Test filtering by priority + category combination"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1", priority=TaskPriority.HIGH, category=TaskCategory.WORK)
        task2 = Task(user_id=test_user.id, title="Task 2", priority=TaskPriority.HIGH, category=TaskCategory.PERSONAL)
        task3 = Task(user_id=test_user.id, title="Task 3", priority=TaskPriority.LOW, category=TaskCategory.WORK)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?priority=high&category=work",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["priority"] == "high"
        assert data[0]["category"] == "work"

    def test_filter_by_all_three_criteria(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T075: Test filtering by status + priority + category (all three)"""
        # Arrange
        task1 = Task(
            user_id=test_user.id,
            title="Perfect match",
            completed=False,
            priority=TaskPriority.HIGH,
            category=TaskCategory.WORK,
        )
        task2 = Task(
            user_id=test_user.id,
            title="Wrong status",
            completed=True,
            priority=TaskPriority.HIGH,
            category=TaskCategory.WORK,
        )
        task3 = Task(
            user_id=test_user.id,
            title="Wrong priority",
            completed=False,
            priority=TaskPriority.LOW,
            category=TaskCategory.WORK,
        )

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?status=pending&priority=high&category=work",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["title"] == "Perfect match"

    def test_filter_combination_with_no_matches(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T076: Test filter combination with no matches returns empty list"""
        # Arrange
        task = Task(user_id=test_user.id, title="Task", priority=TaskPriority.LOW)
        session.add(task)
        session.commit()

        # Act - Filter for impossible combination
        response = client.get(
            f"/api/{test_user.id}/tasks?priority=high&category=work",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        assert response.json() == []

    def test_invalid_status_value_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T077: Test invalid status value returns 422 Bad Request"""
        response = client.get(
            f"/api/{test_user.id}/tasks?status=invalid_status",
            headers=auth_headers,
        )
        assert response.status_code == 422


# ===============================================================================
# USER STORY 6: FLEXIBLE SORTING TESTS (T083-T091)
# ===============================================================================


class TestFlexibleSorting:
    """Test flexible sorting functionality (User Story 6)"""

    def test_sort_by_created_at_ascending(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T083: Test sorting by created_at ascending (oldest first)"""
        # Arrange
        from datetime import timedelta
        base_time = datetime.utcnow()

        task1 = Task(user_id=test_user.id, title="Oldest", created_at=base_time)
        task2 = Task(user_id=test_user.id, title="Middle", created_at=base_time + timedelta(hours=1))
        task3 = Task(user_id=test_user.id, title="Newest", created_at=base_time + timedelta(hours=2))

        session.add_all([task3, task1, task2])  # Add in random order
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=created_at&order=asc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        titles = [task["title"] for task in data]
        assert titles == ["Oldest", "Middle", "Newest"]

    def test_sort_by_created_at_descending(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T084: Test sorting by created_at descending (newest first)"""
        # Arrange
        from datetime import timedelta
        base_time = datetime.utcnow()

        task1 = Task(user_id=test_user.id, title="Oldest", created_at=base_time)
        task2 = Task(user_id=test_user.id, title="Newest", created_at=base_time + timedelta(hours=1))

        session.add_all([task1, task2])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=created_at&order=desc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        titles = [task["title"] for task in data]
        assert titles == ["Newest", "Oldest"]

    def test_sort_by_title_alphabetically(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T085: Test sorting by title alphabetically (A-Z)"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Zebra")
        task2 = Task(user_id=test_user.id, title="Apple")
        task3 = Task(user_id=test_user.id, title="Mango")

        session.add_all([task1, task2, task3])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=title&order=asc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        titles = [task["title"] for task in data]
        assert titles == ["Apple", "Mango", "Zebra"]

    def test_sort_by_priority_orders_correctly(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T086: Test sorting by priority orders correctly"""
        # Already tested in T042 (User Story 2)
        pass

    def test_sort_by_status_groups_by_completion(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T087: Test sorting by status groups by completion"""
        # Arrange
        task1 = Task(user_id=test_user.id, title="Task 1", completed=True)
        task2 = Task(user_id=test_user.id, title="Task 2", completed=False)
        task3 = Task(user_id=test_user.id, title="Task 3", completed=True)

        session.add_all([task1, task2, task3])
        session.commit()

        # Act - Sort by status ascending (False first, then True)
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=status&order=asc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        statuses = [task["completed"] for task in data]
        # All False should come before True
        assert statuses == [False, True, True]

    def test_sort_by_updated_at(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T088: Test sorting by updated_at"""
        # Arrange
        from datetime import timedelta
        base_time = datetime.utcnow()

        task1 = Task(user_id=test_user.id, title="Old update", updated_at=base_time)
        task2 = Task(user_id=test_user.id, title="Recent update", updated_at=base_time + timedelta(hours=1))

        session.add_all([task1, task2])
        session.commit()

        # Act
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=updated_at&order=desc",
            headers=auth_headers,
        )

        # Assert
        assert response.status_code == 200
        data = response.json()
        titles = [task["title"] for task in data]
        assert titles == ["Recent update", "Old update"]

    def test_default_sort_when_not_specified(
        self, client: TestClient, session: Session, test_user: User, auth_headers: dict
    ):
        """T089: Test default sort (created_at desc) when no sort specified"""
        # Arrange
        from datetime import timedelta
        base_time = datetime.utcnow()

        task1 = Task(user_id=test_user.id, title="Older", created_at=base_time)
        task2 = Task(user_id=test_user.id, title="Newer", created_at=base_time + timedelta(seconds=1))

        session.add_all([task1, task2])
        session.commit()

        # Act - No sort parameters
        response = client.get(
            f"/api/{test_user.id}/tasks",
            headers=auth_headers,
        )

        # Assert - Should default to created_at desc (newest first)
        assert response.status_code == 200
        data = response.json()
        titles = [task["title"] for task in data]
        assert titles == ["Newer", "Older"]

    def test_invalid_sort_by_value_returns_400(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T090: Test invalid sort_by value returns 400 Bad Request"""
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=invalid_field",
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "Invalid sort_by" in response.json()["detail"]

    def test_invalid_order_value_returns_422(
        self, client: TestClient, test_user: User, auth_headers: dict
    ):
        """T091: Test invalid order value returns 422 Validation Error"""
        response = client.get(
            f"/api/{test_user.id}/tasks?sort_by=title&order=invalid",
            headers=auth_headers,
        )
        assert response.status_code == 422
