"""Tests for permissions service."""

import pytest

from src.services.permissions import PermissionService, get_permission_service
from src.database.models import Issue, User, Status, UserRole


@pytest.fixture
def permission_service():
    """Create a PermissionService for testing."""
    return PermissionService()


@pytest.fixture
def admin_user():
    """Create an admin user."""
    return User(
        id=1,
        username="admin",
        password_hash="hash",
        role=UserRole.ADMINISTRATOR.value,
        departments=[]
    )


@pytest.fixture
def editor_user():
    """Create an editor user."""
    return User(
        id=2,
        username="editor",
        password_hash="hash",
        role=UserRole.EDITOR.value,
        departments=[]
    )


@pytest.fixture
def restricted_user():
    """Create a restricted user with department access."""
    return User(
        id=3,
        username="restricted",
        password_hash="hash",
        role=UserRole.RESTRICTED.value,
        departments=["IT", "HR"]
    )


@pytest.fixture
def viewer_user():
    """Create a viewer user."""
    return User(
        id=4,
        username="viewer",
        password_hash="hash",
        role=UserRole.VIEWER.value,
        departments=["IT"]
    )


@pytest.fixture
def sample_issue():
    """Create a sample issue for testing."""
    return Issue(
        id=1,
        title="Test Issue",
        status=Status.OPEN.value,
        department="IT"
    )


class TestCreateIssuePermissions:
    """Test issue creation permissions."""

    def test_admin_can_create(self, permission_service, admin_user):
        assert permission_service.can_create_issue(admin_user) is True

    def test_editor_can_create(self, permission_service, editor_user):
        assert permission_service.can_create_issue(editor_user) is True

    def test_restricted_can_create(self, permission_service, restricted_user):
        assert permission_service.can_create_issue(restricted_user) is True

    def test_viewer_cannot_create(self, permission_service, viewer_user):
        assert permission_service.can_create_issue(viewer_user) is False


class TestViewIssuePermissions:
    """Test issue viewing permissions."""

    def test_admin_can_view_any(self, permission_service, admin_user, sample_issue):
        sample_issue.department = "Finance"
        assert permission_service.can_view_issue(admin_user, sample_issue) is True

    def test_editor_can_view_any(self, permission_service, editor_user, sample_issue):
        sample_issue.department = "Finance"
        assert permission_service.can_view_issue(editor_user, sample_issue) is True

    def test_restricted_can_view_own_department(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        assert permission_service.can_view_issue(restricted_user, sample_issue) is True

    def test_restricted_cannot_view_other_department(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "Finance"
        assert permission_service.can_view_issue(restricted_user, sample_issue) is False

    def test_viewer_can_view_own_department(self, permission_service, viewer_user, sample_issue):
        sample_issue.department = "IT"
        assert permission_service.can_view_issue(viewer_user, sample_issue) is True


class TestEditIssuePermissions:
    """Test issue editing permissions."""

    def test_admin_can_edit(self, permission_service, admin_user, sample_issue):
        assert permission_service.can_edit_issue(admin_user, sample_issue) is True

    def test_editor_can_edit(self, permission_service, editor_user, sample_issue):
        assert permission_service.can_edit_issue(editor_user, sample_issue) is True

    def test_restricted_can_edit_own_department(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        assert permission_service.can_edit_issue(restricted_user, sample_issue) is True

    def test_restricted_cannot_edit_other_department(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "Finance"
        assert permission_service.can_edit_issue(restricted_user, sample_issue) is False

    def test_restricted_cannot_edit_closed(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        sample_issue.status = Status.CLOSED.value
        assert permission_service.can_edit_issue(restricted_user, sample_issue) is False

    def test_restricted_cannot_edit_draft(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        sample_issue.status = Status.DRAFT.value
        assert permission_service.can_edit_issue(restricted_user, sample_issue) is False

    def test_viewer_cannot_edit(self, permission_service, viewer_user, sample_issue):
        sample_issue.department = "IT"
        assert permission_service.can_edit_issue(viewer_user, sample_issue) is False


class TestDeleteIssuePermissions:
    """Test issue deletion permissions."""

    def test_admin_can_delete(self, permission_service, admin_user):
        assert permission_service.can_delete_issue(admin_user) is True

    def test_editor_cannot_delete(self, permission_service, editor_user):
        assert permission_service.can_delete_issue(editor_user) is False

    def test_restricted_cannot_delete(self, permission_service, restricted_user):
        assert permission_service.can_delete_issue(restricted_user) is False

    def test_viewer_cannot_delete(self, permission_service, viewer_user):
        assert permission_service.can_delete_issue(viewer_user) is False


class TestEditableFields:
    """Test editable field determination."""

    def test_admin_all_fields(self, permission_service, admin_user, sample_issue):
        fields = permission_service.get_editable_fields(admin_user, sample_issue)
        assert "title" in fields
        assert "status" in fields
        assert "department" in fields

    def test_editor_all_fields(self, permission_service, editor_user, sample_issue):
        fields = permission_service.get_editable_fields(editor_user, sample_issue)
        assert "title" in fields
        assert "risk_level" in fields

    def test_restricted_limited_fields(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        fields = permission_service.get_editable_fields(restricted_user, sample_issue)

        assert "status" in fields
        assert "updates" in fields
        assert "supporting_docs" in fields
        assert "follow_up_date" in fields
        assert "title" not in fields
        assert "department" not in fields

    def test_viewer_no_fields(self, permission_service, viewer_user, sample_issue):
        sample_issue.department = "IT"
        fields = permission_service.get_editable_fields(viewer_user, sample_issue)
        assert len(fields) == 0


class TestStatusTransitions:
    """Test status transition permissions."""

    def test_same_status_always_allowed(self, permission_service, viewer_user):
        """Same status transition is always allowed (no change)."""
        assert permission_service.can_change_status(
            viewer_user, Status.OPEN.value, Status.OPEN.value
        ) is True

    def test_admin_any_valid_transition(self, permission_service, admin_user):
        """Admin can make any valid status transition."""
        assert permission_service.can_change_status(
            admin_user, Status.DRAFT.value, Status.OPEN.value
        ) is True
        assert permission_service.can_change_status(
            admin_user, Status.REMEDIATED.value, Status.CLOSED.value
        ) is True

    def test_editor_any_valid_transition(self, permission_service, editor_user):
        """Editor can make any valid status transition."""
        assert permission_service.can_change_status(
            editor_user, Status.DRAFT.value, Status.OPEN.value
        ) is True
        assert permission_service.can_change_status(
            editor_user, Status.REMEDIATED.value, Status.CLOSED.value
        ) is True

    def test_restricted_cannot_draft_to_open(self, permission_service, restricted_user):
        """Restricted users cannot transition Draft -> Open."""
        assert permission_service.can_change_status(
            restricted_user, Status.DRAFT.value, Status.OPEN.value
        ) is False

    def test_restricted_cannot_close(self, permission_service, restricted_user):
        """Restricted users cannot close issues."""
        assert permission_service.can_change_status(
            restricted_user, Status.REMEDIATED.value, Status.CLOSED.value
        ) is False

    def test_restricted_allowed_transitions(self, permission_service, restricted_user):
        """Restricted users can transition between Open, In Progress, Remediated."""
        assert permission_service.can_change_status(
            restricted_user, Status.OPEN.value, Status.IN_PROGRESS.value
        ) is True
        assert permission_service.can_change_status(
            restricted_user, Status.IN_PROGRESS.value, Status.REMEDIATED.value
        ) is True
        assert permission_service.can_change_status(
            restricted_user, Status.REMEDIATED.value, Status.IN_PROGRESS.value
        ) is True

    def test_viewer_cannot_change_status(self, permission_service, viewer_user):
        """Viewer cannot change any status."""
        assert permission_service.can_change_status(
            viewer_user, Status.OPEN.value, Status.IN_PROGRESS.value
        ) is False

    def test_invalid_transition_rejected(self, permission_service, admin_user):
        """Invalid transitions are rejected for all users."""
        # Cannot go from Draft directly to Closed
        assert permission_service.can_change_status(
            admin_user, Status.DRAFT.value, Status.CLOSED.value
        ) is False

        # Cannot transition from Closed
        assert permission_service.can_change_status(
            admin_user, Status.CLOSED.value, Status.OPEN.value
        ) is False


class TestAdminPermissions:
    """Test admin-only permissions."""

    def test_admin_can_manage_users(self, permission_service, admin_user):
        assert permission_service.can_manage_users(admin_user) is True

    def test_editor_cannot_manage_users(self, permission_service, editor_user):
        assert permission_service.can_manage_users(editor_user) is False

    def test_admin_can_configure_database(self, permission_service, admin_user):
        assert permission_service.can_configure_database(admin_user) is True

    def test_admin_can_import_backup(self, permission_service, admin_user):
        assert permission_service.can_import_backup(admin_user) is True

    def test_admin_can_bulk_import(self, permission_service, admin_user):
        assert permission_service.can_bulk_import(admin_user) is True


class TestExportPermissions:
    """Test export permissions."""

    def test_all_users_can_export(self, permission_service, admin_user, editor_user, restricted_user, viewer_user):
        assert permission_service.can_export_data(admin_user) is True
        assert permission_service.can_export_data(editor_user) is True
        assert permission_service.can_export_data(restricted_user) is True
        assert permission_service.can_export_data(viewer_user) is True


class TestIssueFiltering:
    """Test issue filtering by permissions."""

    def test_filter_issues_by_department(self, permission_service, restricted_user):
        """Test that issues are filtered by user's department access."""
        issues = [
            Issue(id=1, title="IT Issue", department="IT"),
            Issue(id=2, title="HR Issue", department="HR"),
            Issue(id=3, title="Finance Issue", department="Finance"),
        ]

        filtered = permission_service.filter_issues_by_permission(restricted_user, issues)

        assert len(filtered) == 2
        departments = [i.department for i in filtered]
        assert "IT" in departments
        assert "HR" in departments
        assert "Finance" not in departments

    def test_admin_sees_all(self, permission_service, admin_user):
        """Admin can see all issues."""
        issues = [
            Issue(id=1, title="IT Issue", department="IT"),
            Issue(id=2, title="Finance Issue", department="Finance"),
        ]

        filtered = permission_service.filter_issues_by_permission(admin_user, issues)
        assert len(filtered) == 2


class TestDefaultStatus:
    """Test default status for new issues."""

    def test_restricted_user_creates_draft(self, permission_service, restricted_user):
        status = permission_service.get_default_status_for_role(restricted_user)
        assert status == Status.DRAFT.value

    def test_admin_creates_open(self, permission_service, admin_user):
        status = permission_service.get_default_status_for_role(admin_user)
        assert status == Status.OPEN.value

    def test_editor_creates_open(self, permission_service, editor_user):
        status = permission_service.get_default_status_for_role(editor_user)
        assert status == Status.OPEN.value


class TestValidateIssueEdit:
    """Test issue edit validation."""

    def test_valid_edit(self, permission_service, admin_user, sample_issue):
        updated = Issue(
            id=1,
            title="Updated Title",
            status=Status.OPEN.value,
            department="IT"
        )

        is_valid, error = permission_service.validate_issue_edit(
            admin_user, sample_issue, updated
        )
        assert is_valid is True
        assert error == ""

    def test_restricted_cannot_edit_title(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        updated = Issue(
            id=1,
            title="New Title",  # Changed
            status=Status.OPEN.value,
            department="IT"
        )

        is_valid, error = permission_service.validate_issue_edit(
            restricted_user, sample_issue, updated
        )
        assert is_valid is False
        assert "title" in error.lower()

    def test_invalid_status_transition(self, permission_service, restricted_user, sample_issue):
        sample_issue.department = "IT"
        sample_issue.status = Status.REMEDIATED.value
        updated = Issue(
            id=1,
            title="Test Issue",
            status=Status.CLOSED.value,  # Restricted can't close
            department="IT"
        )

        is_valid, error = permission_service.validate_issue_edit(
            restricted_user, sample_issue, updated
        )
        assert is_valid is False
        assert "status" in error.lower()
