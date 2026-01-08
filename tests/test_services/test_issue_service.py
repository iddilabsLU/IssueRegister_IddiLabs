"""Tests for issue service."""

import pytest
from datetime import date

from src.database import queries
from src.database.models import Issue, User, Status, UserRole
from src.services.issue_service import IssueService, get_issue_service, reset_issue_service
from src.services.permissions import PermissionService


@pytest.fixture
def issue_service(temp_db):
    """Create an IssueService for testing."""
    reset_issue_service()
    return IssueService()


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
def restricted_user(temp_db):
    """Create a restricted user with department access."""
    import bcrypt
    password_hash = bcrypt.hashpw("restricted".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="restricted_test",
        password_hash=password_hash,
        role=UserRole.RESTRICTED.value,
        departments=["IT", "HR"]
    )
    return queries.create_user(user)


@pytest.fixture
def viewer_user(temp_db):
    """Create a viewer user."""
    import bcrypt
    password_hash = bcrypt.hashpw("viewer".encode(), bcrypt.gensalt()).decode()
    user = User(
        username="viewer_test",
        password_hash=password_hash,
        role=UserRole.VIEWER.value,
        departments=["IT"]
    )
    return queries.create_user(user)


@pytest.fixture
def sample_issue():
    """Create a sample issue for testing."""
    return Issue(
        title="Test Issue",
        status=Status.OPEN.value,
        summary_description="Test summary",
        topic="System Error",
        identified_by="Test User",
        owner="Test Owner",
        department="IT",
        description="Detailed description",
        remediation_action="Fix the issue",
        risk_description="Low impact",
        risk_level="Medium",
        identification_date=date.today(),
        due_date=date.today(),
        follow_up_date=None,
        updates="",
        closing_date=None,
        supporting_docs=[]
    )


class TestCreateIssue:
    """Test issue creation with permissions."""

    def test_admin_creates_issue_with_open_status(self, issue_service, admin_user, sample_issue):
        """Admin creates issue with default Open status."""
        sample_issue.status = Status.DRAFT.value  # Start as draft
        created, error = issue_service.create_issue(admin_user, sample_issue)

        assert error == ""
        assert created is not None
        assert created.status == Status.OPEN.value  # Should be auto-set to Open

    def test_restricted_creates_issue_with_draft_status(self, issue_service, restricted_user, sample_issue):
        """Restricted user creates issue that stays as Draft."""
        sample_issue.status = Status.DRAFT.value
        sample_issue.department = "IT"  # Restricted user can only create in their dept
        created, error = issue_service.create_issue(restricted_user, sample_issue)

        assert error == ""
        assert created is not None
        assert created.status == Status.DRAFT.value

    def test_viewer_cannot_create_issue(self, issue_service, viewer_user, sample_issue):
        """Viewer cannot create issues."""
        created, error = issue_service.create_issue(viewer_user, sample_issue)

        assert created is None
        assert "permission" in error.lower()

    def test_create_issue_sets_identification_date(self, issue_service, admin_user, sample_issue):
        """Issue creation sets identification date if not provided."""
        sample_issue.identification_date = None
        created, error = issue_service.create_issue(admin_user, sample_issue)

        assert created is not None
        assert created.identification_date == date.today()


class TestUpdateIssue:
    """Test issue updates with permissions."""

    def test_admin_can_update_all_fields(self, issue_service, admin_user, sample_issue):
        """Admin can update any field."""
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        updates = {
            "title": "Updated Title",
            "department": "Finance",
            "risk_level": "High"
        }
        updated, error = issue_service.update_issue(admin_user, created.id, updates)

        assert error == ""
        assert updated.title == "Updated Title"
        assert updated.department == "Finance"
        assert updated.risk_level == "High"

    def test_restricted_can_only_update_limited_fields(self, issue_service, admin_user, restricted_user, sample_issue):
        """Restricted user can only update specific fields."""
        sample_issue.department = "IT"
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        # Restricted can update 'updates' field
        valid_update, error = issue_service.update_issue(
            restricted_user, created.id, {"updates": "New update"}
        )
        assert error == ""
        assert "New update" in valid_update.updates

    def test_restricted_cannot_update_title(self, issue_service, admin_user, restricted_user, sample_issue):
        """Restricted user cannot update title."""
        sample_issue.department = "IT"
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        # Restricted cannot update 'title'
        updated, error = issue_service.update_issue(
            restricted_user, created.id, {"title": "New Title"}
        )
        assert updated is None
        assert "permission" in error.lower()

    def test_update_nonexistent_issue(self, issue_service, admin_user):
        """Updating non-existent issue returns error."""
        updated, error = issue_service.update_issue(admin_user, 99999, {"title": "New"})
        assert updated is None
        assert "not found" in error.lower()


class TestStatusTransitions:
    """Test status transition rules."""

    def test_valid_status_transition(self, issue_service, admin_user, sample_issue):
        """Valid status transitions work."""
        sample_issue.status = Status.OPEN.value
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        # Open -> In Progress (valid)
        updated, error = issue_service.update_issue(
            admin_user, created.id, {"status": Status.IN_PROGRESS.value}
        )
        assert error == ""
        assert updated.status == Status.IN_PROGRESS.value

    def test_invalid_status_transition_blocked(self, issue_service, admin_user, sample_issue):
        """Invalid status transitions are blocked."""
        # Create issue and close it
        sample_issue.status = Status.REMEDIATED.value
        created, _ = issue_service.create_issue(admin_user, sample_issue)
        issue_service.update_issue(admin_user, created.id, {"status": Status.CLOSED.value})

        # Closed -> Open (invalid - closed issues cannot transition)
        updated, error = issue_service.update_issue(
            admin_user, created.id, {"status": Status.OPEN.value}
        )
        assert updated is None
        assert "cannot change status" in error.lower()

    def test_restricted_cannot_close_issues(self, issue_service, admin_user, restricted_user, sample_issue):
        """Restricted users cannot close issues."""
        sample_issue.department = "IT"
        sample_issue.status = Status.REMEDIATED.value
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        # Remediated -> Closed (not allowed for restricted)
        updated, error = issue_service.update_issue(
            restricted_user, created.id, {"status": Status.CLOSED.value}
        )
        assert updated is None
        assert "cannot change status" in error.lower()

    def test_auto_closing_date_on_close(self, issue_service, admin_user, sample_issue):
        """Closing date is auto-set when issue is closed."""
        sample_issue.status = Status.REMEDIATED.value
        created, _ = issue_service.create_issue(admin_user, sample_issue)
        assert created.closing_date is None

        # Close the issue
        updated, error = issue_service.update_issue(
            admin_user, created.id, {"status": Status.CLOSED.value}
        )
        assert error == ""
        assert updated.closing_date == date.today()


class TestDeleteIssue:
    """Test issue deletion with permissions."""

    def test_admin_can_delete(self, issue_service, admin_user, sample_issue):
        """Admin can delete issues."""
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        success, error = issue_service.delete_issue(admin_user, created.id)
        assert success is True
        assert error == ""

        # Verify deleted
        issue, _ = issue_service.get_issue(admin_user, created.id)
        assert issue is None

    def test_editor_cannot_delete(self, issue_service, admin_user, editor_user, sample_issue):
        """Editor cannot delete issues."""
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        success, error = issue_service.delete_issue(editor_user, created.id)
        assert success is False
        assert "permission" in error.lower()

    def test_delete_nonexistent_issue(self, issue_service, admin_user):
        """Deleting non-existent issue returns error."""
        success, error = issue_service.delete_issue(admin_user, 99999)
        assert success is False
        assert "not found" in error.lower()


class TestListIssues:
    """Test issue listing with filters and permissions."""

    def test_list_issues_with_status_filter(self, issue_service, admin_user, sample_issue):
        """Filter issues by status."""
        # Create issues with different statuses
        sample_issue.status = Status.OPEN.value
        issue_service.create_issue(admin_user, sample_issue)

        sample_issue.title = "Closed Issue"
        sample_issue.status = Status.REMEDIATED.value
        created2, _ = issue_service.create_issue(admin_user, sample_issue)
        issue_service.update_issue(admin_user, created2.id, {"status": Status.CLOSED.value})

        # Filter by Open status
        issues = issue_service.list_issues(admin_user, status=[Status.OPEN.value])
        assert all(i.status == Status.OPEN.value for i in issues)

    def test_restricted_user_sees_only_their_department(self, issue_service, admin_user, restricted_user, sample_issue):
        """Restricted user only sees issues in their departments."""
        # Create IT issue (visible to restricted)
        sample_issue.department = "IT"
        issue_service.create_issue(admin_user, sample_issue)

        # Create Finance issue (not visible to restricted)
        sample_issue.title = "Finance Issue"
        sample_issue.department = "Finance"
        issue_service.create_issue(admin_user, sample_issue)

        # Restricted user should only see IT issues
        issues = issue_service.list_issues(restricted_user)
        assert all(i.department in restricted_user.departments for i in issues)


class TestDashboardData:
    """Test dashboard data retrieval."""

    def test_dashboard_data_structure(self, issue_service, admin_user, sample_issue):
        """Dashboard data has correct structure."""
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        assert "total_issues" in data
        assert "active_issues" in data
        assert "high_priority_open" in data
        assert "overdue" in data
        assert "resolution_rate" in data
        assert "status_distribution" in data
        assert "risk_distribution" in data
        assert "department_distribution" in data
        assert "topic_distribution" in data

    def test_dashboard_data_with_filters(self, issue_service, admin_user, sample_issue):
        """Dashboard data respects filters."""
        sample_issue.department = "IT"
        issue_service.create_issue(admin_user, sample_issue)

        sample_issue.title = "HR Issue"
        sample_issue.department = "HR"
        issue_service.create_issue(admin_user, sample_issue)

        # Filter to IT only
        data = issue_service.get_dashboard_data(admin_user, {"department": ["IT"]})
        assert data["total_issues"] == 1

    def test_dashboard_data_has_new_distributions(self, issue_service, admin_user, sample_issue):
        """Dashboard data includes all new distribution keys for 8 charts."""
        sample_issue.due_date = date.today()
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        # New keys for 8 additional charts
        assert "owner_distribution" in data
        assert "identified_by_distribution" in data
        assert "department_risk_distribution" in data
        assert "topic_risk_distribution" in data
        assert "owner_risk_distribution" in data
        assert "identified_by_risk_distribution" in data
        assert "risk_by_duedate" in data
        assert "topic_by_duedate" in data
        assert "all_topics" in data

    def test_dashboard_risk_distribution_structure(self, issue_service, admin_user, sample_issue):
        """Risk distributions have correct segment structure."""
        sample_issue.department = "IT"
        sample_issue.risk_level = "Medium"
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        # Check structure of risk distribution
        dept_risk = data["department_risk_distribution"]
        assert "IT" in dept_risk
        assert set(dept_risk["IT"].keys()) == {"None", "Low", "Medium", "High"}
        assert dept_risk["IT"]["Medium"] == 1

    def test_dashboard_duedate_monthly_buckets(self, issue_service, admin_user, sample_issue):
        """Due date charts use monthly bucket format."""
        sample_issue.due_date = date(2026, 1, 15)
        sample_issue.topic = "System Error"
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        # Check monthly bucket format
        assert "Jan 2026" in data["risk_by_duedate"]
        assert "Jan 2026" in data["topic_by_duedate"]

    def test_dashboard_duedate_excludes_null_dates(self, issue_service, admin_user, sample_issue):
        """Issues without due dates are excluded from date-based charts."""
        sample_issue.due_date = None
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        # No entries when no due dates
        assert data["risk_by_duedate"] == {}
        assert data["topic_by_duedate"] == {}

    def test_dashboard_owner_distribution(self, issue_service, admin_user, sample_issue):
        """Owner distribution groups by owner with status segments."""
        sample_issue.owner = "John Doe"
        sample_issue.status = Status.OPEN.value
        issue_service.create_issue(admin_user, sample_issue)

        sample_issue.title = "Another Issue"
        sample_issue.owner = "Jane Smith"
        sample_issue.status = Status.IN_PROGRESS.value
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        owner_dist = data["owner_distribution"]
        assert "John Doe" in owner_dist
        assert "Jane Smith" in owner_dist
        assert owner_dist["John Doe"][Status.OPEN.value] == 1
        assert owner_dist["Jane Smith"][Status.IN_PROGRESS.value] == 1

    def test_dashboard_all_topics_list(self, issue_service, admin_user, sample_issue):
        """all_topics contains unique topics from issues with due dates."""
        sample_issue.due_date = date.today()
        sample_issue.topic = "System Error"
        issue_service.create_issue(admin_user, sample_issue)

        sample_issue.title = "Another Issue"
        sample_issue.topic = "Security"
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        assert "System Error" in data["all_topics"]
        assert "Security" in data["all_topics"]

    def test_dashboard_aging_distribution_structure(self, issue_service, admin_user, sample_issue):
        """Aging distribution has correct bucket structure."""
        sample_issue.identification_date = date.today()
        sample_issue.status = Status.OPEN.value
        sample_issue.risk_level = "Medium"
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        aging = data["aging_distribution"]
        # Check all buckets exist
        assert "0-30 days" in aging
        assert "31-60 days" in aging
        assert "61-90 days" in aging
        assert "91-180 days" in aging
        assert "180+ days" in aging
        # Check risk levels are segments
        assert set(aging["0-30 days"].keys()) == {"None", "Low", "Medium", "High"}
        # New issue should be in 0-30 days bucket
        assert aging["0-30 days"]["Medium"] == 1

    def test_dashboard_aging_excludes_closed(self, issue_service, admin_user, sample_issue):
        """Aging distribution excludes closed issues."""
        sample_issue.identification_date = date.today()
        sample_issue.status = Status.CLOSED.value
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        aging = data["aging_distribution"]
        # All buckets should have zero counts
        total = sum(
            sum(risks.values())
            for risks in aging.values()
        )
        assert total == 0

    def test_dashboard_overdue_breakdown_structure(self, issue_service, admin_user, sample_issue):
        """Overdue breakdown has correct bucket structure."""
        from datetime import timedelta
        # Create an issue that is 10 days overdue
        sample_issue.due_date = date.today() - timedelta(days=10)
        sample_issue.status = Status.OPEN.value
        sample_issue.risk_level = "High"
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        overdue = data["overdue_breakdown"]
        # Check all buckets exist
        assert "0-30 days" in overdue
        assert "31-60 days" in overdue
        assert "61-90 days" in overdue
        assert "90+ days" in overdue
        # Check risk levels are segments
        assert set(overdue["0-30 days"].keys()) == {"None", "Low", "Medium", "High"}
        # 10 days overdue should be in 0-30 days bucket
        assert overdue["0-30 days"]["High"] == 1

    def test_dashboard_overdue_excludes_closed(self, issue_service, admin_user, sample_issue):
        """Overdue breakdown excludes closed issues."""
        from datetime import timedelta
        sample_issue.due_date = date.today() - timedelta(days=10)
        sample_issue.status = Status.CLOSED.value
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        overdue = data["overdue_breakdown"]
        # All buckets should have zero counts
        total = sum(
            sum(risks.values())
            for risks in overdue.values()
        )
        assert total == 0

    def test_dashboard_overdue_excludes_not_overdue(self, issue_service, admin_user, sample_issue):
        """Overdue breakdown excludes issues not yet due."""
        from datetime import timedelta
        # Issue due tomorrow (not overdue)
        sample_issue.due_date = date.today() + timedelta(days=1)
        sample_issue.status = Status.OPEN.value
        issue_service.create_issue(admin_user, sample_issue)

        data = issue_service.get_dashboard_data(admin_user)

        overdue = data["overdue_breakdown"]
        # All buckets should have zero counts
        total = sum(
            sum(risks.values())
            for risks in overdue.values()
        )
        assert total == 0


class TestAddUpdateNote:
    """Test adding update notes to issues."""

    def test_add_update_note(self, issue_service, admin_user, sample_issue):
        """Adding update note appends with timestamp."""
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        updated, error = issue_service.add_update_note(admin_user, created.id, "Test note")

        assert error == ""
        assert "Test note" in updated.updates
        assert admin_user.username in updated.updates

    def test_add_update_note_appends(self, issue_service, admin_user, sample_issue):
        """Multiple notes are appended."""
        sample_issue.updates = "Initial note"
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        updated, _ = issue_service.add_update_note(admin_user, created.id, "Second note")

        assert "Initial note" in updated.updates
        assert "Second note" in updated.updates

    def test_viewer_cannot_add_note(self, issue_service, admin_user, viewer_user, sample_issue):
        """Viewer cannot add update notes."""
        sample_issue.department = "IT"
        created, _ = issue_service.create_issue(admin_user, sample_issue)

        updated, error = issue_service.add_update_note(viewer_user, created.id, "Note")

        assert updated is None
        assert "permission" in error.lower()
