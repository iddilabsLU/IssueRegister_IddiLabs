"""Tests for audit service."""

import pytest

from src.database import queries
from src.database.models import Issue, User, AuditLogEntry, Status, UserRole
from src.services.audit import AuditService, get_audit_service


@pytest.fixture
def audit_service():
    """Create an AuditService for testing."""
    return AuditService()


@pytest.fixture
def admin_user(temp_db):
    """Create an admin user in the database."""
    import bcrypt
    password_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="admin_test",
        password_hash=password_hash,
        role=UserRole.ADMINISTRATOR.value,
        departments=[]
    )
    return queries.create_user(user)


@pytest.fixture
def editor_user(temp_db):
    """Create an editor user in the database."""
    import bcrypt
    password_hash = bcrypt.hashpw("editor".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="editor_test",
        password_hash=password_hash,
        role=UserRole.EDITOR.value,
        departments=[]
    )
    return queries.create_user(user)


@pytest.fixture
def sample_issue(temp_db, admin_user):
    """Create a sample issue in the database."""
    issue = Issue(
        title="Test Issue",
        status=Status.OPEN.value,
        department="IT",
        summary_description="Test summary",
        topic="System Error",
        identified_by="Test User",
        owner="Test Owner"
    )
    return queries.create_issue(issue)


class TestIssueAuditLogging:
    """Test audit logging for issue actions."""

    def test_log_issue_created(self, audit_service, admin_user, temp_db):
        """Issue creation is logged."""
        issue = Issue(
            id=1,
            title="New Issue",
            status=Status.OPEN.value,
            department="IT"
        )

        audit_service.log_issue_created(admin_user, issue)

        # Verify log entry exists
        logs = queries.list_audit_logs(entity_type="issue", action="created")
        assert len(logs) >= 1

        log = logs[0]
        assert log.username == admin_user.username
        assert log.action == "created"
        assert log.entity_type == "issue"
        assert log.entity_id == issue.id
        assert log.details["title"] == "New Issue"

    def test_log_issue_updated(self, audit_service, admin_user, sample_issue, temp_db):
        """Issue update is logged with before/after values."""
        before = {"title": "Old Title", "status": "Open"}
        after = {"title": "New Title", "status": "Open"}

        audit_service.log_issue_updated(admin_user, sample_issue.id, before, after)

        logs = queries.list_audit_logs(entity_type="issue", action="updated")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "updated"
        assert "changes" in log.details
        assert "title" in log.details["changes"]
        assert log.details["changes"]["title"]["before"] == "Old Title"
        assert log.details["changes"]["title"]["after"] == "New Title"

    def test_log_issue_updated_no_changes(self, audit_service, admin_user, sample_issue, temp_db):
        """No log entry when there are no actual changes."""
        before = {"title": "Same Title", "status": "Open"}
        after = {"title": "Same Title", "status": "Open"}

        audit_service.log_issue_updated(admin_user, sample_issue.id, before, after)

        # Should not create log entry when nothing changed
        logs = queries.list_audit_logs(entity_type="issue", action="updated")
        assert len(logs) == 0

    def test_log_issue_status_changed(self, audit_service, admin_user, sample_issue, temp_db):
        """Status change is logged separately."""
        audit_service.log_issue_status_changed(
            admin_user, sample_issue.id, Status.OPEN.value, Status.IN_PROGRESS.value
        )

        logs = queries.list_audit_logs(entity_type="issue", action="status_changed")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "status_changed"
        assert log.details["before"] == Status.OPEN.value
        assert log.details["after"] == Status.IN_PROGRESS.value

    def test_log_issue_deleted(self, audit_service, admin_user, sample_issue, temp_db):
        """Issue deletion is logged."""
        audit_service.log_issue_deleted(admin_user, sample_issue)

        logs = queries.list_audit_logs(entity_type="issue", action="deleted")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "deleted"
        assert log.entity_id == sample_issue.id
        assert log.details["title"] == sample_issue.title


class TestUserAuditLogging:
    """Test audit logging for user actions."""

    def test_log_user_login(self, audit_service, admin_user, temp_db):
        """User login is logged."""
        audit_service.log_user_login(admin_user)

        logs = queries.list_audit_logs(entity_type="user", action="login")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "login"
        assert log.username == admin_user.username

    def test_log_user_logout(self, audit_service, admin_user, temp_db):
        """User logout is logged."""
        audit_service.log_user_logout(admin_user)

        logs = queries.list_audit_logs(entity_type="user", action="logout")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "logout"

    def test_log_user_created(self, audit_service, admin_user, editor_user, temp_db):
        """User creation by admin is logged."""
        audit_service.log_user_created(admin_user, editor_user)

        logs = queries.list_audit_logs(entity_type="user", action="created")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "created"
        assert log.username == admin_user.username  # Admin performed the action
        assert log.details["username"] == editor_user.username
        assert log.details["role"] == editor_user.role

    def test_log_user_updated(self, audit_service, admin_user, editor_user, temp_db):
        """User update is logged with changes."""
        changes = {"role": {"before": "Editor", "after": "Administrator"}}
        audit_service.log_user_updated(admin_user, editor_user, changes)

        logs = queries.list_audit_logs(entity_type="user", action="updated")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "updated"
        assert log.details["username"] == editor_user.username
        assert "changes" in log.details

    def test_log_user_deleted(self, audit_service, admin_user, editor_user, temp_db):
        """User deletion is logged."""
        audit_service.log_user_deleted(admin_user, editor_user)

        logs = queries.list_audit_logs(entity_type="user", action="deleted")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "deleted"
        assert log.details["username"] == editor_user.username


class TestSettingsAuditLogging:
    """Test audit logging for settings changes."""

    def test_log_settings_changed(self, audit_service, admin_user, temp_db):
        """Settings change is logged."""
        audit_service.log_settings_changed(
            admin_user, "auth_enabled", "false", "true"
        )

        logs = queries.list_audit_logs(entity_type="settings", action="changed")
        assert len(logs) >= 1

        log = logs[0]
        assert log.action == "changed"
        assert log.details["setting"] == "auth_enabled"
        assert log.details["before"] == "false"
        assert log.details["after"] == "true"


class TestAuditLogFiltering:
    """Test audit log filtering capabilities."""

    def test_filter_by_entity_type(self, audit_service, admin_user, sample_issue, temp_db):
        """Filter audit logs by entity type."""
        # Create logs of different types
        audit_service.log_user_login(admin_user)
        audit_service.log_issue_created(admin_user, sample_issue)

        # Filter by issue only
        issue_logs = queries.list_audit_logs(entity_type="issue")
        assert all(log.entity_type == "issue" for log in issue_logs)

        # Filter by user only
        user_logs = queries.list_audit_logs(entity_type="user")
        assert all(log.entity_type == "user" for log in user_logs)

    def test_filter_by_action(self, audit_service, admin_user, sample_issue, temp_db):
        """Filter audit logs by action."""
        audit_service.log_issue_created(admin_user, sample_issue)
        audit_service.log_issue_deleted(admin_user, sample_issue)

        # Filter by created only
        created_logs = queries.list_audit_logs(action="created")
        assert all(log.action == "created" for log in created_logs)

    def test_user_attribution(self, audit_service, admin_user, editor_user, sample_issue, temp_db):
        """Verify correct user is attributed to actions."""
        audit_service.log_issue_created(admin_user, sample_issue)
        audit_service.log_issue_deleted(editor_user, sample_issue)

        logs = queries.list_audit_logs(entity_type="issue")

        # Find logs by username
        admin_logs = [l for l in logs if l.username == admin_user.username]
        editor_logs = [l for l in logs if l.username == editor_user.username]

        assert len(admin_logs) >= 1
        assert len(editor_logs) >= 1


class TestSingletonPattern:
    """Test singleton pattern for audit service."""

    def test_get_audit_service_returns_same_instance(self, temp_db):
        """get_audit_service returns the same instance."""
        service1 = get_audit_service()
        service2 = get_audit_service()
        assert service1 is service2
