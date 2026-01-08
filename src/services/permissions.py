"""Permission service for role-based access control."""

from typing import Optional

from src.database.models import Issue, User, Status, UserRole


class PermissionService:
    """
    Handles role-based access control for Issue Register.

    Role Permissions:
    - Administrator: Full system access
    - Editor: Full issue editing across all departments
    - Restricted: Limited to assigned departments, controlled status transitions
    - Viewer: Read-only access

    Status Transition Rules:
    - Draft -> Open: Editor/Admin only
    - Open -> In Progress: Any with edit access
    - In Progress -> Remediated: Any with edit access
    - Remediated -> Closed: Editor/Admin only
    """

    # Fields that Restricted users can edit
    RESTRICTED_EDITABLE_FIELDS = [
        "status",
        "updates",
        "supporting_docs",
        "follow_up_date",
    ]

    # Status transitions allowed for Restricted users
    RESTRICTED_STATUS_TRANSITIONS = {
        Status.OPEN.value: [Status.IN_PROGRESS.value],
        Status.IN_PROGRESS.value: [Status.OPEN.value, Status.REMEDIATED.value],
        Status.REMEDIATED.value: [Status.IN_PROGRESS.value],
    }

    # All valid status transitions
    ALL_STATUS_TRANSITIONS = {
        Status.DRAFT.value: [Status.OPEN.value],
        Status.OPEN.value: [Status.IN_PROGRESS.value, Status.CLOSED.value],
        Status.IN_PROGRESS.value: [Status.OPEN.value, Status.REMEDIATED.value, Status.CLOSED.value],
        Status.REMEDIATED.value: [Status.IN_PROGRESS.value, Status.CLOSED.value],
        Status.CLOSED.value: [],  # Closed issues cannot transition
    }

    def can_create_issue(self, user: User) -> bool:
        """
        Check if user can create new issues.

        Args:
            user: User to check

        Returns:
            True if user can create issues
        """
        # Viewers cannot create issues
        return user.role != UserRole.VIEWER.value

    def can_view_issue(self, user: User, issue: Issue) -> bool:
        """
        Check if user can view a specific issue.

        Args:
            user: User to check
            issue: Issue to view

        Returns:
            True if user can view the issue
        """
        return user.can_access_department(issue.department)

    def can_edit_issue(self, user: User, issue: Issue) -> bool:
        """
        Check if user can edit a specific issue.

        Args:
            user: User to check
            issue: Issue to edit

        Returns:
            True if user can edit the issue
        """
        # Viewers cannot edit
        if user.role == UserRole.VIEWER.value:
            return False

        # Administrators can edit everything
        if user.role == UserRole.ADMINISTRATOR.value:
            return True

        # Editors: check edit_departments restriction
        if user.role == UserRole.EDITOR.value:
            return user.can_edit_department(issue.department)

        # Restricted users: must have department access and status restrictions
        if user.role == UserRole.RESTRICTED.value:
            if not user.can_access_department(issue.department):
                return False
            if issue.status in [Status.CLOSED.value, Status.DRAFT.value]:
                return False

        return True

    def can_delete_issue(self, user: User) -> bool:
        """
        Check if user can delete issues.

        Args:
            user: User to check

        Returns:
            True if user can delete issues
        """
        # Only Administrators can delete
        return user.role == UserRole.ADMINISTRATOR.value

    def get_editable_fields(self, user: User, issue: Issue) -> list[str]:
        """
        Get list of fields the user can edit for a specific issue.

        Args:
            user: User to check
            issue: Issue being edited

        Returns:
            List of field names that can be edited
        """
        if not self.can_edit_issue(user, issue):
            return []

        # Admin and Editor can edit all fields
        if user.role in [UserRole.ADMINISTRATOR.value, UserRole.EDITOR.value]:
            return [
                "title", "status", "summary_description", "topic",
                "identified_by", "owner", "department", "description",
                "remediation_action", "risk_description", "risk_level",
                "identification_date", "due_date", "follow_up_date",
                "updates", "closing_date", "supporting_docs"
            ]

        # Restricted users can only edit specific fields
        return self.RESTRICTED_EDITABLE_FIELDS.copy()

    def can_change_status(
        self,
        user: User,
        current_status: str,
        new_status: str
    ) -> bool:
        """
        Check if user can change issue status.

        Args:
            user: User attempting the change
            current_status: Current issue status
            new_status: Desired new status

        Returns:
            True if transition is allowed
        """
        if current_status == new_status:
            return True

        # Viewer cannot change status
        if user.role == UserRole.VIEWER.value:
            return False

        # Get allowed transitions for the current status
        allowed = self.ALL_STATUS_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            return False

        # Check role-specific restrictions
        if user.role == UserRole.RESTRICTED.value:
            restricted_allowed = self.RESTRICTED_STATUS_TRANSITIONS.get(current_status, [])
            return new_status in restricted_allowed

        return True

    def can_manage_users(self, user: User) -> bool:
        """
        Check if user can manage user accounts.

        Args:
            user: User to check

        Returns:
            True if user can manage users
        """
        return user.role == UserRole.ADMINISTRATOR.value

    def can_configure_database(self, user: User) -> bool:
        """
        Check if user can configure database settings.

        Args:
            user: User to check

        Returns:
            True if user can configure database
        """
        return user.role == UserRole.ADMINISTRATOR.value

    def can_import_backup(self, user: User) -> bool:
        """
        Check if user can import database backups.

        Args:
            user: User to check

        Returns:
            True if user can import backups
        """
        return user.role == UserRole.ADMINISTRATOR.value

    def can_bulk_import(self, user: User) -> bool:
        """
        Check if user can perform bulk imports.

        Args:
            user: User to check

        Returns:
            True if user can bulk import
        """
        return user.role == UserRole.ADMINISTRATOR.value

    def can_export_data(self, user: User) -> bool:
        """
        Check if user can export data.

        Args:
            user: User to check

        Returns:
            True if user can export (all users can)
        """
        return True

    def filter_issues_by_permission(
        self,
        user: User,
        issues: list[Issue]
    ) -> list[Issue]:
        """
        Filter issues list to only those user can access.

        Args:
            user: User to filter for
            issues: List of issues to filter

        Returns:
            Filtered list of accessible issues
        """
        return [
            issue for issue in issues
            if self.can_view_issue(user, issue)
        ]

    def get_default_status_for_role(self, user: User) -> str:
        """
        Get the default status for new issues based on user role.

        Args:
            user: User creating the issue

        Returns:
            Default status value
        """
        if user.role == UserRole.RESTRICTED.value:
            return Status.DRAFT.value
        return Status.OPEN.value

    def validate_issue_edit(
        self,
        user: User,
        original: Issue,
        updated: Issue
    ) -> tuple[bool, str]:
        """
        Validate that user is allowed to make the proposed changes.

        Args:
            user: User making the edit
            original: Original issue state
            updated: Proposed updated issue

        Returns:
            Tuple of (is_valid, error_message)
        """
        if not self.can_edit_issue(user, original):
            return False, "You do not have permission to edit this issue."

        editable_fields = self.get_editable_fields(user, original)

        # Check each changed field
        for field in [
            "title", "summary_description", "topic", "identified_by",
            "owner", "department", "description", "remediation_action",
            "risk_description", "risk_level", "identification_date",
            "due_date", "follow_up_date", "updates", "closing_date",
            "supporting_docs"
        ]:
            original_value = getattr(original, field)
            updated_value = getattr(updated, field)

            if original_value != updated_value and field not in editable_fields:
                return False, f"You do not have permission to edit the '{field}' field."

        # Check status change
        if original.status != updated.status:
            if not self.can_change_status(user, original.status, updated.status):
                return False, f"You cannot change status from '{original.status}' to '{updated.status}'."

        return True, ""


# Singleton instance
_permission_service: Optional[PermissionService] = None


def get_permission_service() -> PermissionService:
    """Get the singleton PermissionService instance."""
    global _permission_service
    if _permission_service is None:
        _permission_service = PermissionService()
    return _permission_service
