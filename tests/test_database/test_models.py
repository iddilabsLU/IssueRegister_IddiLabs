"""Tests for database models."""

from datetime import date, datetime
import json

import pytest

from src.database.models import Issue, User, Status, RiskLevel, UserRole


class TestStatusEnum:
    """Test suite for Status enum."""

    def test_status_values(self):
        """Test all status values are present."""
        expected = ["Draft", "Open", "In Progress", "Remediated", "Closed"]
        assert Status.values() == expected

    def test_status_string_comparison(self):
        """Test status can be compared with strings."""
        assert Status.OPEN.value == "Open"
        assert Status.CLOSED.value == "Closed"


class TestRiskLevelEnum:
    """Test suite for RiskLevel enum."""

    def test_risk_level_values(self):
        """Test all risk level values are present."""
        expected = ["None", "Low", "Medium", "High"]
        assert RiskLevel.values() == expected


class TestUserRoleEnum:
    """Test suite for UserRole enum."""

    def test_user_role_values(self):
        """Test all user role values are present."""
        expected = ["Administrator", "Editor", "Restricted", "Viewer"]
        assert UserRole.values() == expected


class TestIssueModel:
    """Test suite for Issue model."""

    def test_create_issue_minimal(self):
        """Test creating issue with minimal data."""
        issue = Issue(title="Test Issue")
        assert issue.title == "Test Issue"
        assert issue.status == Status.DRAFT.value
        assert issue.risk_level == RiskLevel.NONE.value
        assert issue.id is None

    def test_create_issue_full(self):
        """Test creating issue with all fields."""
        today = date.today()
        now = datetime.now()

        issue = Issue(
            id=1,
            title="Full Test Issue",
            status=Status.OPEN.value,
            summary_description="Summary",
            topic="System Error",
            identified_by="John",
            owner="Jane",
            department="IT",
            description="Detailed description",
            remediation_action="Fix it",
            risk_description="Risk description",
            risk_level=RiskLevel.HIGH.value,
            identification_date=today,
            due_date=today,
            follow_up_date=today,
            updates="Update notes",
            closing_date=None,
            supporting_docs=["doc1.pdf", "doc2.pdf"],
            created_at=now,
            updated_at=now,
        )

        assert issue.id == 1
        assert issue.title == "Full Test Issue"
        assert issue.status == Status.OPEN.value
        assert issue.supporting_docs == ["doc1.pdf", "doc2.pdf"]

    def test_issue_to_dict(self):
        """Test converting issue to dictionary."""
        today = date.today()
        issue = Issue(
            title="Test",
            due_date=today,
            supporting_docs=["doc.pdf"]
        )

        data = issue.to_dict()
        assert data["title"] == "Test"
        assert data["due_date"] == today.isoformat()
        assert data["supporting_docs"] == '["doc.pdf"]'

    def test_issue_from_row(self):
        """Test creating issue from database row."""
        row = {
            "id": 1,
            "title": "Row Issue",
            "status": "Open",
            "summary_description": "Summary",
            "topic": "Test",
            "identified_by": "User",
            "owner": "Owner",
            "department": "IT",
            "description": "Desc",
            "remediation_action": "Action",
            "risk_description": "Risk",
            "risk_level": "High",
            "identification_date": "2024-01-15",
            "due_date": "2024-02-15",
            "follow_up_date": "2024-01-20",
            "updates": "Updates",
            "closing_date": None,
            "supporting_docs": '["file.pdf"]',
            "created_at": "2024-01-15T10:00:00",
            "updated_at": "2024-01-15T10:00:00",
        }

        issue = Issue.from_row(row)
        assert issue.id == 1
        assert issue.title == "Row Issue"
        assert issue.identification_date == date(2024, 1, 15)
        assert issue.supporting_docs == ["file.pdf"]

    def test_issue_from_row_none_raises(self):
        """Test that from_row with None raises ValueError."""
        with pytest.raises(ValueError):
            Issue.from_row(None)

    def test_issue_from_row_invalid_json(self):
        """Test handling invalid JSON in supporting_docs."""
        row = {
            "id": 1,
            "title": "Test",
            "status": "Open",
            "summary_description": None,
            "topic": None,
            "identified_by": None,
            "owner": None,
            "department": None,
            "description": None,
            "remediation_action": None,
            "risk_description": None,
            "risk_level": "None",
            "identification_date": None,
            "due_date": None,
            "follow_up_date": None,
            "updates": None,
            "closing_date": None,
            "supporting_docs": "invalid json",
            "created_at": None,
            "updated_at": None,
        }

        issue = Issue.from_row(row)
        assert issue.supporting_docs == []

    def test_issue_is_overdue(self):
        """Test overdue detection."""
        past_date = date.today() - date.resolution * 5

        overdue_issue = Issue(
            title="Overdue",
            status=Status.OPEN.value,
            due_date=past_date
        )
        assert overdue_issue.is_overdue() is True

        closed_issue = Issue(
            title="Closed",
            status=Status.CLOSED.value,
            due_date=past_date
        )
        assert closed_issue.is_overdue() is False

        no_date_issue = Issue(title="No Date")
        assert no_date_issue.is_overdue() is False

    def test_issue_is_active(self):
        """Test active status detection."""
        for status in [Status.OPEN, Status.IN_PROGRESS, Status.REMEDIATED]:
            issue = Issue(title="Test", status=status.value)
            assert issue.is_active() is True

        for status in [Status.DRAFT, Status.CLOSED]:
            issue = Issue(title="Test", status=status.value)
            assert issue.is_active() is False


class TestUserModel:
    """Test suite for User model."""

    def test_create_user_minimal(self):
        """Test creating user with minimal data."""
        user = User(username="test", password_hash="hash")
        assert user.username == "test"
        assert user.role == UserRole.VIEWER.value
        assert user.departments == []

    def test_create_user_full(self):
        """Test creating user with all fields."""
        now = datetime.now()
        user = User(
            id=1,
            username="admin",
            password_hash="hash",
            role=UserRole.ADMINISTRATOR.value,
            departments=["IT", "HR"],
            created_at=now,
        )

        assert user.id == 1
        assert user.role == UserRole.ADMINISTRATOR.value
        assert user.departments == ["IT", "HR"]

    def test_user_to_dict(self):
        """Test converting user to dictionary."""
        user = User(
            username="test",
            password_hash="hash",
            departments=["IT"]
        )

        data = user.to_dict()
        assert data["username"] == "test"
        assert data["departments"] == '["IT"]'

    def test_user_from_row(self):
        """Test creating user from database row."""
        row = {
            "id": 1,
            "username": "testuser",
            "password_hash": "hash",
            "role": "Editor",
            "departments": '["IT", "HR"]',
            "created_at": "2024-01-15T10:00:00",
        }

        user = User.from_row(row)
        assert user.id == 1
        assert user.username == "testuser"
        assert user.departments == ["IT", "HR"]

    def test_user_from_row_none_raises(self):
        """Test that from_row with None raises ValueError."""
        with pytest.raises(ValueError):
            User.from_row(None)

    def test_user_role_checks(self):
        """Test role checking methods."""
        admin = User(username="a", password_hash="h", role=UserRole.ADMINISTRATOR.value)
        assert admin.is_admin() is True
        assert admin.is_editor() is False

        editor = User(username="e", password_hash="h", role=UserRole.EDITOR.value)
        assert editor.is_editor() is True
        assert editor.is_admin() is False

        restricted = User(username="r", password_hash="h", role=UserRole.RESTRICTED.value)
        assert restricted.is_restricted() is True

        viewer = User(username="v", password_hash="h", role=UserRole.VIEWER.value)
        assert viewer.is_viewer() is True

    def test_user_department_access(self):
        """Test department access checking."""
        # Admin can access any department
        admin = User(username="a", password_hash="h", role=UserRole.ADMINISTRATOR.value)
        assert admin.can_access_department("IT") is True
        assert admin.can_access_department("HR") is True

        # Editor can access any department
        editor = User(username="e", password_hash="h", role=UserRole.EDITOR.value)
        assert editor.can_access_department("IT") is True

        # Restricted with departments can only access those
        restricted = User(
            username="r",
            password_hash="h",
            role=UserRole.RESTRICTED.value,
            departments=["IT", "HR"]
        )
        assert restricted.can_access_department("IT") is True
        assert restricted.can_access_department("Finance") is False

        # Restricted with empty departments can access all
        restricted_all = User(
            username="r2",
            password_hash="h",
            role=UserRole.RESTRICTED.value,
            departments=[]
        )
        assert restricted_all.can_access_department("Finance") is True

        # Access to None department is always allowed
        assert restricted.can_access_department(None) is True
