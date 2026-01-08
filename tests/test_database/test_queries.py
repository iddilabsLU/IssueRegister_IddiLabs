"""Tests for database queries module."""

from datetime import date, timedelta

import pytest

from src.database import queries
from src.database.models import Issue, User, Status, RiskLevel, UserRole


class TestIssueQueries:
    """Test suite for issue-related queries."""

    def test_create_issue(self, db_connection, sample_issue_data):
        """Test creating a new issue."""
        issue = Issue(**sample_issue_data)
        created = queries.create_issue(issue)

        assert created.id is not None
        assert created.title == sample_issue_data["title"]
        assert created.created_at is not None
        assert created.updated_at is not None

    def test_get_issue(self, db_connection, sample_issue_data):
        """Test retrieving an issue by ID."""
        issue = Issue(**sample_issue_data)
        created = queries.create_issue(issue)

        retrieved = queries.get_issue(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.title == created.title

    def test_get_issue_not_found(self, db_connection):
        """Test retrieving non-existent issue returns None."""
        result = queries.get_issue(99999)
        assert result is None

    def test_update_issue(self, db_connection, sample_issue_data):
        """Test updating an issue."""
        issue = Issue(**sample_issue_data)
        created = queries.create_issue(issue)

        created.title = "Updated Title"
        created.status = Status.IN_PROGRESS.value
        updated = queries.update_issue(created)

        retrieved = queries.get_issue(created.id)
        assert retrieved.title == "Updated Title"
        assert retrieved.status == Status.IN_PROGRESS.value

    def test_update_issue_without_id_raises(self, db_connection, sample_issue_data):
        """Test that updating issue without ID raises ValueError."""
        issue = Issue(**sample_issue_data)
        with pytest.raises(ValueError):
            queries.update_issue(issue)

    def test_delete_issue(self, db_connection, sample_issue_data):
        """Test deleting an issue."""
        issue = Issue(**sample_issue_data)
        created = queries.create_issue(issue)

        result = queries.delete_issue(created.id)
        assert result is True

        retrieved = queries.get_issue(created.id)
        assert retrieved is None

    def test_delete_issue_not_found(self, db_connection):
        """Test deleting non-existent issue returns False."""
        result = queries.delete_issue(99999)
        assert result is False

    def test_list_issues_no_filters(self, db_connection, sample_issue_data):
        """Test listing all issues without filters."""
        # Create multiple issues
        for i in range(3):
            data = sample_issue_data.copy()
            data["title"] = f"Issue {i}"
            queries.create_issue(Issue(**data))

        issues = queries.list_issues()
        assert len(issues) >= 3

    def test_list_issues_filter_by_status(self, db_connection, sample_issue_data):
        """Test filtering issues by status."""
        # Create issues with different statuses
        data1 = sample_issue_data.copy()
        data1["title"] = "Open Issue"
        data1["status"] = Status.OPEN.value
        queries.create_issue(Issue(**data1))

        data2 = sample_issue_data.copy()
        data2["title"] = "Closed Issue"
        data2["status"] = Status.CLOSED.value
        queries.create_issue(Issue(**data2))

        open_issues = queries.list_issues(status=[Status.OPEN.value])
        assert all(i.status == Status.OPEN.value for i in open_issues)

    def test_list_issues_filter_by_department(self, db_connection, sample_issue_data):
        """Test filtering issues by department."""
        data1 = sample_issue_data.copy()
        data1["title"] = "IT Issue"
        data1["department"] = "IT"
        queries.create_issue(Issue(**data1))

        data2 = sample_issue_data.copy()
        data2["title"] = "HR Issue"
        data2["department"] = "HR"
        queries.create_issue(Issue(**data2))

        it_issues = queries.list_issues(department=["IT"])
        assert all(i.department == "IT" for i in it_issues)

    def test_list_issues_filter_by_date_range(self, db_connection, sample_issue_data):
        """Test filtering issues by due date range."""
        today = date.today()

        data1 = sample_issue_data.copy()
        data1["title"] = "Due Today"
        data1["due_date"] = today
        queries.create_issue(Issue(**data1))

        data2 = sample_issue_data.copy()
        data2["title"] = "Due Next Week"
        data2["due_date"] = today + timedelta(days=7)
        queries.create_issue(Issue(**data2))

        issues = queries.list_issues(
            due_date_from=today,
            due_date_to=today + timedelta(days=1)
        )
        assert all(i.due_date <= today + timedelta(days=1) for i in issues if i.due_date)

    def test_list_issues_multiple_filters(self, db_connection, sample_issue_data):
        """Test combining multiple filters (AND logic)."""
        data = sample_issue_data.copy()
        data["title"] = "High Risk IT Open Issue"
        data["department"] = "IT"
        data["risk_level"] = RiskLevel.HIGH.value
        data["status"] = Status.OPEN.value
        queries.create_issue(Issue(**data))

        issues = queries.list_issues(
            department=["IT"],
            risk_level=[RiskLevel.HIGH.value],
            status=[Status.OPEN.value]
        )
        assert len(issues) >= 1
        for issue in issues:
            assert issue.department == "IT"
            assert issue.risk_level == RiskLevel.HIGH.value
            assert issue.status == Status.OPEN.value

    def test_list_issues_ordering(self, db_connection, sample_issue_data):
        """Test issue ordering."""
        for i in range(3):
            data = sample_issue_data.copy()
            data["title"] = f"Issue {i}"
            queries.create_issue(Issue(**data))

        asc_issues = queries.list_issues(order_by="id", order_dir="ASC")
        desc_issues = queries.list_issues(order_by="id", order_dir="DESC")

        assert asc_issues[0].id < asc_issues[-1].id
        assert desc_issues[0].id > desc_issues[-1].id

    def test_get_distinct_values(self, db_connection, sample_issue_data):
        """Test getting distinct column values."""
        departments = ["IT", "HR", "Finance"]
        for dept in departments:
            data = sample_issue_data.copy()
            data["title"] = f"{dept} Issue"
            data["department"] = dept
            queries.create_issue(Issue(**data))

        distinct_depts = queries.get_distinct_values("department")
        for dept in departments:
            assert dept in distinct_depts

    def test_get_distinct_values_invalid_column(self, db_connection):
        """Test that invalid column raises ValueError."""
        with pytest.raises(ValueError):
            queries.get_distinct_values("invalid_column")


class TestDashboardQueries:
    """Test suite for dashboard-related queries."""

    def test_get_issue_count(self, db_connection, sample_issue_data):
        """Test total issue count."""
        initial_count = queries.get_issue_count()

        queries.create_issue(Issue(**sample_issue_data))
        queries.create_issue(Issue(**sample_issue_data))

        new_count = queries.get_issue_count()
        assert new_count == initial_count + 2

    def test_get_active_issue_count(self, db_connection, sample_issue_data):
        """Test active issue count."""
        for status in [Status.OPEN.value, Status.IN_PROGRESS.value, Status.REMEDIATED.value]:
            data = sample_issue_data.copy()
            data["status"] = status
            queries.create_issue(Issue(**data))

        data = sample_issue_data.copy()
        data["status"] = Status.CLOSED.value
        queries.create_issue(Issue(**data))

        active_count = queries.get_active_issue_count()
        assert active_count >= 3

    def test_get_high_priority_open_count(self, db_connection, sample_issue_data):
        """Test high priority open issue count."""
        data = sample_issue_data.copy()
        data["status"] = Status.OPEN.value
        data["risk_level"] = RiskLevel.HIGH.value
        queries.create_issue(Issue(**data))

        count = queries.get_high_priority_open_count()
        assert count >= 1

    def test_get_overdue_count(self, db_connection, sample_issue_data):
        """Test overdue issue count."""
        data = sample_issue_data.copy()
        data["status"] = Status.OPEN.value
        data["due_date"] = date.today() - timedelta(days=5)
        queries.create_issue(Issue(**data))

        count = queries.get_overdue_count()
        assert count >= 1

    def test_get_status_distribution(self, db_connection, sample_issue_data):
        """Test status distribution."""
        for status in Status.values():
            data = sample_issue_data.copy()
            data["status"] = status
            queries.create_issue(Issue(**data))

        distribution = queries.get_status_distribution()
        assert all(status in distribution for status in Status.values())

    def test_get_risk_distribution(self, db_connection, sample_issue_data):
        """Test risk level distribution."""
        for risk in RiskLevel.values():
            data = sample_issue_data.copy()
            data["risk_level"] = risk
            queries.create_issue(Issue(**data))

        distribution = queries.get_risk_distribution()
        assert all(risk in distribution for risk in RiskLevel.values())

    def test_get_department_distribution(self, db_connection, sample_issue_data):
        """Test department distribution."""
        departments = ["IT", "HR"]
        for dept in departments:
            data = sample_issue_data.copy()
            data["department"] = dept
            queries.create_issue(Issue(**data))

        distribution = queries.get_department_distribution()
        for dept in departments:
            assert dept in distribution
            assert Status.OPEN.value in distribution[dept]


class TestUserQueries:
    """Test suite for user-related queries."""

    def test_create_user(self, db_connection, sample_user_data):
        """Test creating a new user."""
        user = User(**sample_user_data)
        created = queries.create_user(user)

        assert created.id is not None
        assert created.username == sample_user_data["username"]

    def test_get_user(self, db_connection, sample_user_data):
        """Test retrieving a user by ID."""
        user = User(**sample_user_data)
        created = queries.create_user(user)

        retrieved = queries.get_user(created.id)
        assert retrieved is not None
        assert retrieved.username == created.username

    def test_get_user_by_username(self, db_connection, sample_user_data):
        """Test retrieving a user by username."""
        user = User(**sample_user_data)
        queries.create_user(user)

        retrieved = queries.get_user_by_username(sample_user_data["username"])
        assert retrieved is not None
        assert retrieved.username == sample_user_data["username"]

    def test_update_user(self, db_connection, sample_user_data):
        """Test updating a user."""
        user = User(**sample_user_data)
        created = queries.create_user(user)

        created.role = UserRole.ADMINISTRATOR.value
        queries.update_user(created)

        retrieved = queries.get_user(created.id)
        assert retrieved.role == UserRole.ADMINISTRATOR.value

    def test_delete_user(self, db_connection, sample_user_data):
        """Test deleting a user."""
        user = User(**sample_user_data)
        created = queries.create_user(user)

        result = queries.delete_user(created.id)
        assert result is True

        retrieved = queries.get_user(created.id)
        assert retrieved is None

    def test_list_users(self, db_connection, sample_user_data):
        """Test listing all users."""
        user = User(**sample_user_data)
        queries.create_user(user)

        users = queries.list_users()
        # Should have at least the default admin and our test user
        assert len(users) >= 1

    def test_user_exists(self, db_connection, sample_user_data):
        """Test checking if username exists."""
        user = User(**sample_user_data)
        queries.create_user(user)

        assert queries.user_exists(sample_user_data["username"]) is True
        assert queries.user_exists("nonexistent") is False


class TestSettingsQueries:
    """Test suite for settings-related queries."""

    def test_set_and_get_setting(self, db_connection):
        """Test setting and getting a value."""
        queries.set_setting("test_setting", "test_value")

        value = queries.get_setting("test_setting")
        assert value == "test_value"

    def test_get_setting_default(self, db_connection):
        """Test getting non-existent setting returns default."""
        value = queries.get_setting("nonexistent", "default")
        assert value == "default"

    def test_get_setting_none_default(self, db_connection):
        """Test getting non-existent setting returns None by default."""
        value = queries.get_setting("nonexistent")
        assert value is None

    def test_update_setting(self, db_connection):
        """Test updating an existing setting."""
        queries.set_setting("update_test", "original")
        queries.set_setting("update_test", "updated")

        value = queries.get_setting("update_test")
        assert value == "updated"

    def test_delete_setting(self, db_connection):
        """Test deleting a setting."""
        queries.set_setting("delete_test", "value")

        result = queries.delete_setting("delete_test")
        assert result is True

        value = queries.get_setting("delete_test")
        assert value is None

    def test_delete_setting_not_found(self, db_connection):
        """Test deleting non-existent setting returns False."""
        result = queries.delete_setting("nonexistent")
        assert result is False
