"""Issue management service."""

from datetime import date, datetime
from typing import Optional

from src.database import queries
from src.database.models import Issue, User, Status
from src.services.audit import get_audit_service


class IssueService:
    """
    Business logic for issue management.

    Handles issue CRUD with permission awareness and business rules.
    """

    def __init__(self, permission_service=None):
        """
        Initialize issue service.

        Args:
            permission_service: PermissionService instance (optional, uses singleton if not provided)
        """
        if permission_service is None:
            from src.services.permissions import get_permission_service
            permission_service = get_permission_service()
        self._permissions = permission_service

    def create_issue(self, user: User, issue: Issue) -> tuple[Optional[Issue], str]:
        """
        Create a new issue with permission checking.

        Args:
            user: User creating the issue
            issue: Issue data to create

        Returns:
            Tuple of (created_issue, error_message)
        """
        if not self._permissions.can_create_issue(user):
            return None, "You do not have permission to create issues."

        # Set default status based on role
        if issue.status == Status.DRAFT.value and user.role != "Restricted":
            # Non-restricted users default to Open
            issue.status = self._permissions.get_default_status_for_role(user)

        # Set identification date if not provided
        if issue.identification_date is None:
            issue.identification_date = date.today()

        created = queries.create_issue(issue)

        # Log the creation
        get_audit_service().log_issue_created(user, created)

        return created, ""

    def update_issue(
        self,
        user: User,
        issue_id: int,
        updates: dict
    ) -> tuple[Optional[Issue], str]:
        """
        Update an issue with permission checking.

        Args:
            user: User making the update
            issue_id: ID of issue to update
            updates: Dictionary of field updates

        Returns:
            Tuple of (updated_issue, error_message)
        """
        original = queries.get_issue(issue_id)
        if original is None:
            return None, "Issue not found."

        if not self._permissions.can_edit_issue(user, original):
            return None, "You do not have permission to edit this issue."

        # Store original values for audit logging
        original_dict = original.to_dict()
        original_status = original.status

        editable_fields = self._permissions.get_editable_fields(user, original)

        # Apply updates only to editable fields
        for field, value in updates.items():
            if field in editable_fields:
                setattr(original, field, value)
            elif field not in ["id", "created_at", "updated_at"]:
                return None, f"You do not have permission to edit the '{field}' field."

        # Handle status change validation
        if "status" in updates:
            new_status = updates["status"]
            if not self._permissions.can_change_status(user, original_status, new_status):
                return None, f"You cannot change status from '{original_status}' to '{new_status}'."

            # Auto-set closing date when moving to Closed
            if new_status == Status.CLOSED.value and original.closing_date is None:
                original.closing_date = date.today()

        updated = queries.update_issue(original)

        # Log the update
        updated_dict = updated.to_dict()
        get_audit_service().log_issue_updated(user, issue_id, original_dict, updated_dict)

        # Log status change specifically if it occurred
        if "status" in updates and updates["status"] != original_status:
            get_audit_service().log_issue_status_changed(user, issue_id, original_status, updates["status"])

        return updated, ""

    def delete_issue(self, user: User, issue_id: int) -> tuple[bool, str]:
        """
        Delete an issue with permission checking.

        Args:
            user: User deleting the issue
            issue_id: ID of issue to delete

        Returns:
            Tuple of (success, error_message)
        """
        if not self._permissions.can_delete_issue(user):
            return False, "You do not have permission to delete issues."

        issue = queries.get_issue(issue_id)
        if issue is None:
            return False, "Issue not found."

        result = queries.delete_issue(issue_id)

        if result:
            # Log the deletion
            get_audit_service().log_issue_deleted(user, issue)

        return result, "" if result else "Failed to delete issue."

    def get_issue(self, user: User, issue_id: int) -> tuple[Optional[Issue], str]:
        """
        Get an issue with permission checking.

        Args:
            user: User requesting the issue
            issue_id: ID of issue to retrieve

        Returns:
            Tuple of (issue, error_message)
        """
        issue = queries.get_issue(issue_id)
        if issue is None:
            return None, "Issue not found."

        if not self._permissions.can_view_issue(user, issue):
            return None, "You do not have permission to view this issue."

        return issue, ""

    def list_issues(
        self,
        user: User,
        status: Optional[list[str]] = None,
        risk_level: Optional[list[str]] = None,
        department: Optional[list[str]] = None,
        owner: Optional[list[str]] = None,
        identified_by: Optional[list[str]] = None,
        topic: Optional[list[str]] = None,
        due_date_from: Optional[date] = None,
        due_date_to: Optional[date] = None,
        identification_date_from: Optional[date] = None,
        identification_date_to: Optional[date] = None,
        order_by: str = "id",
        order_dir: str = "DESC",
    ) -> list[Issue]:
        """
        List issues with filtering and permission checking.

        Args:
            user: User requesting issues
            status: Filter by status values
            risk_level: Filter by risk level values
            department: Filter by department values
            owner: Filter by owner values
            identified_by: Filter by identified_by values
            topic: Filter by topic values
            due_date_from: Filter by due date (from)
            due_date_to: Filter by due date (to)
            identification_date_from: Filter by identification date (from)
            identification_date_to: Filter by identification date (to)
            order_by: Column to order by
            order_dir: Order direction (ASC or DESC)

        Returns:
            List of issues the user can access
        """
        issues = queries.list_issues(
            status=status,
            risk_level=risk_level,
            department=department,
            owner=owner,
            identified_by=identified_by,
            topic=topic,
            due_date_from=due_date_from,
            due_date_to=due_date_to,
            identification_date_from=identification_date_from,
            identification_date_to=identification_date_to,
            order_by=order_by,
            order_dir=order_dir,
        )

        # Filter by user permissions
        return self._permissions.filter_issues_by_permission(user, issues)

    def get_dashboard_data(self, user: User, filters: Optional[dict] = None) -> dict:
        """
        Get dashboard data with permission filtering.

        Args:
            user: User requesting data
            filters: Optional filters to apply (same as list_issues)

        Returns:
            Dictionary with dashboard metrics
        """
        # Get issues with optional filtering
        if filters:
            accessible_issues = self.list_issues(user, **filters)
        else:
            # Get all issues and filter by permission
            all_issues = queries.list_issues()
            accessible_issues = self._permissions.filter_issues_by_permission(user, all_issues)

        # Calculate metrics from accessible issues
        total = len(accessible_issues)
        active = sum(1 for i in accessible_issues if i.is_active())
        high_priority_open = sum(
            1 for i in accessible_issues
            if i.status == Status.OPEN.value and i.risk_level == "High"
        )
        overdue = sum(1 for i in accessible_issues if i.is_overdue())
        closed = sum(1 for i in accessible_issues if i.status == Status.CLOSED.value)
        resolution_rate = (closed / total * 100) if total > 0 else 0

        # Status distribution
        status_dist = {}
        for status in Status.values():
            status_dist[status] = sum(
                1 for i in accessible_issues if i.status == status
            )

        # Risk distribution
        risk_dist = {}
        for risk in ["None", "Low", "Medium", "High"]:
            risk_dist[risk] = sum(
                1 for i in accessible_issues if i.risk_level == risk
            )

        # Department distribution
        dept_dist = {}
        for issue in accessible_issues:
            dept = issue.department or "Unassigned"
            if dept not in dept_dist:
                dept_dist[dept] = {s: 0 for s in Status.values()}
            dept_dist[dept][issue.status] += 1

        # Topic distribution
        topic_dist = {}
        for issue in accessible_issues:
            topic = issue.topic or "Unassigned"
            if topic not in topic_dist:
                topic_dist[topic] = {s: 0 for s in Status.values()}
            topic_dist[topic][issue.status] += 1

        # Owner distribution (by status) - Chart 1
        owner_dist = {}
        for issue in accessible_issues:
            owner = issue.owner or "Unassigned"
            if owner not in owner_dist:
                owner_dist[owner] = {s: 0 for s in Status.values()}
            owner_dist[owner][issue.status] += 1

        # Identified By distribution (by status) - Chart 2
        identified_by_dist = {}
        for issue in accessible_issues:
            identified_by = issue.identified_by or "Unassigned"
            if identified_by not in identified_by_dist:
                identified_by_dist[identified_by] = {s: 0 for s in Status.values()}
            identified_by_dist[identified_by][issue.status] += 1

        # Risk values for risk-based distributions
        risk_values = ["None", "Low", "Medium", "High"]

        # Department distribution by risk - Chart 3
        dept_risk_dist = {}
        for issue in accessible_issues:
            dept = issue.department or "Unassigned"
            if dept not in dept_risk_dist:
                dept_risk_dist[dept] = {r: 0 for r in risk_values}
            dept_risk_dist[dept][issue.risk_level] += 1

        # Topic distribution by risk - Chart 4
        topic_risk_dist = {}
        for issue in accessible_issues:
            topic = issue.topic or "Unassigned"
            if topic not in topic_risk_dist:
                topic_risk_dist[topic] = {r: 0 for r in risk_values}
            topic_risk_dist[topic][issue.risk_level] += 1

        # Owner distribution by risk - Chart 5
        owner_risk_dist = {}
        for issue in accessible_issues:
            owner = issue.owner or "Unassigned"
            if owner not in owner_risk_dist:
                owner_risk_dist[owner] = {r: 0 for r in risk_values}
            owner_risk_dist[owner][issue.risk_level] += 1

        # Identified By distribution by risk - Chart 6
        identified_by_risk_dist = {}
        for issue in accessible_issues:
            identified_by = issue.identified_by or "Unassigned"
            if identified_by not in identified_by_risk_dist:
                identified_by_risk_dist[identified_by] = {r: 0 for r in risk_values}
            identified_by_risk_dist[identified_by][issue.risk_level] += 1

        # Risk by due date (monthly buckets) - Chart 7
        risk_by_duedate = {}
        for issue in accessible_issues:
            if issue.due_date:
                month_key = issue.due_date.strftime("%b %Y")
                if month_key not in risk_by_duedate:
                    risk_by_duedate[month_key] = {r: 0 for r in risk_values}
                risk_by_duedate[month_key][issue.risk_level] += 1
        # Sort by date for chronological order
        sorted_risk_by_duedate = dict(sorted(
            risk_by_duedate.items(),
            key=lambda x: datetime.strptime(x[0], "%b %Y")
        ))

        # Topic by due date (monthly buckets) - Chart 8
        topic_by_duedate = {}
        all_topics_set = set()
        for issue in accessible_issues:
            if issue.due_date:
                month_key = issue.due_date.strftime("%b %Y")
                topic = issue.topic or "Unassigned"
                all_topics_set.add(topic)
                if month_key not in topic_by_duedate:
                    topic_by_duedate[month_key] = {}
                if topic not in topic_by_duedate[month_key]:
                    topic_by_duedate[month_key][topic] = 0
                topic_by_duedate[month_key][topic] += 1
        # Sort by date for chronological order
        sorted_topic_by_duedate = dict(sorted(
            topic_by_duedate.items(),
            key=lambda x: datetime.strptime(x[0], "%b %Y")
        ))

        # Aging Analysis - how long non-closed issues have been open
        # Buckets: 0-30, 31-60, 61-90, 91-180, 180+ days
        aging_buckets = ["0-30 days", "31-60 days", "61-90 days", "91-180 days", "180+ days"]
        aging_distribution = {bucket: {r: 0 for r in risk_values} for bucket in aging_buckets}
        today = date.today()

        for issue in accessible_issues:
            # Exclude closed issues
            if issue.status == Status.CLOSED.value:
                continue
            # Calculate age from identification_date
            if issue.identification_date:
                age_days = (today - issue.identification_date).days
                if age_days <= 30:
                    bucket = "0-30 days"
                elif age_days <= 60:
                    bucket = "31-60 days"
                elif age_days <= 90:
                    bucket = "61-90 days"
                elif age_days <= 180:
                    bucket = "91-180 days"
                else:
                    bucket = "180+ days"
                aging_distribution[bucket][issue.risk_level] += 1

        # Overdue Breakdown - how long overdue non-closed issues are
        # Buckets: 0-30, 31-60, 61-90, 90+ days overdue
        overdue_buckets = ["0-30 days", "31-60 days", "61-90 days", "90+ days"]
        overdue_breakdown = {bucket: {r: 0 for r in risk_values} for bucket in overdue_buckets}

        for issue in accessible_issues:
            # Exclude closed issues
            if issue.status == Status.CLOSED.value:
                continue
            # Only include issues that are overdue (past due date)
            if issue.due_date and issue.due_date < today:
                overdue_days = (today - issue.due_date).days
                if overdue_days <= 30:
                    bucket = "0-30 days"
                elif overdue_days <= 60:
                    bucket = "31-60 days"
                elif overdue_days <= 90:
                    bucket = "61-90 days"
                else:
                    bucket = "90+ days"
                overdue_breakdown[bucket][issue.risk_level] += 1

        return {
            "total_issues": total,
            "active_issues": active,
            "high_priority_open": high_priority_open,
            "overdue": overdue,
            "closed": closed,
            "resolution_rate": resolution_rate,
            "status_distribution": status_dist,
            "risk_distribution": risk_dist,
            "department_distribution": dept_dist,
            "topic_distribution": topic_dist,
            # New distributions for 8 additional charts
            "owner_distribution": owner_dist,
            "identified_by_distribution": identified_by_dist,
            "department_risk_distribution": dept_risk_dist,
            "topic_risk_distribution": topic_risk_dist,
            "owner_risk_distribution": owner_risk_dist,
            "identified_by_risk_distribution": identified_by_risk_dist,
            "risk_by_duedate": sorted_risk_by_duedate,
            "topic_by_duedate": sorted_topic_by_duedate,
            "all_topics": list(all_topics_set),
            # Aging and Overdue charts
            "aging_distribution": aging_distribution,
            "overdue_breakdown": overdue_breakdown,
        }

    def add_update_note(
        self,
        user: User,
        issue_id: int,
        note: str
    ) -> tuple[Optional[Issue], str]:
        """
        Add an update note to an issue.

        Args:
            user: User adding the note
            issue_id: ID of issue to update
            note: Note text to add

        Returns:
            Tuple of (updated_issue, error_message)
        """
        issue = queries.get_issue(issue_id)
        if issue is None:
            return None, "Issue not found."

        if not self._permissions.can_edit_issue(user, issue):
            return None, "You do not have permission to update this issue."

        # Format new update entry
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        new_entry = f"[{timestamp}] {user.username}: {note}"

        # Append to existing updates
        if issue.updates:
            issue.updates = issue.updates + "\n" + new_entry
        else:
            issue.updates = new_entry

        updated = queries.update_issue(issue)
        return updated, ""


# Singleton instance
_issue_service: Optional[IssueService] = None


def get_issue_service() -> IssueService:
    """Get the singleton IssueService instance."""
    global _issue_service
    if _issue_service is None:
        _issue_service = IssueService()
    return _issue_service


def reset_issue_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _issue_service
    _issue_service = None
