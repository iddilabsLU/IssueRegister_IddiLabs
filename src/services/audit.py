"""Audit logging service for tracking user actions."""

from typing import Optional

from src.database import queries
from src.database.models import AuditLogEntry, Issue, User


class AuditService:
    """
    Handles audit logging for Issue Register.

    Logs actions on:
    - Issues: created, updated, status_changed, deleted
    - Users: created, updated, deleted, login, logout
    - Settings: auth_changed, db_path_changed
    """

    def log_issue_created(self, user: User, issue: Issue) -> None:
        """Log issue creation."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="created",
            entity_type="issue",
            entity_id=issue.id,
            details={"title": issue.title, "status": issue.status}
        )
        queries.create_audit_log(entry)

    def log_issue_updated(
        self,
        user: User,
        issue_id: int,
        before: dict,
        after: dict
    ) -> None:
        """Log issue update with before/after values."""
        # Calculate changed fields only
        changes = {}
        for key in after:
            if before.get(key) != after.get(key):
                changes[key] = {"before": before.get(key), "after": after.get(key)}

        if not changes:
            return  # No actual changes

        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="updated",
            entity_type="issue",
            entity_id=issue_id,
            details={"changes": changes}
        )
        queries.create_audit_log(entry)

    def log_issue_status_changed(
        self,
        user: User,
        issue_id: int,
        old_status: str,
        new_status: str
    ) -> None:
        """Log status change specifically."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="status_changed",
            entity_type="issue",
            entity_id=issue_id,
            details={"before": old_status, "after": new_status}
        )
        queries.create_audit_log(entry)

    def log_issue_deleted(self, user: User, issue: Issue) -> None:
        """Log issue deletion."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="deleted",
            entity_type="issue",
            entity_id=issue.id,
            details={"title": issue.title}
        )
        queries.create_audit_log(entry)

    def log_user_login(self, user: User) -> None:
        """Log user login."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="login",
            entity_type="user",
            entity_id=user.id,
            details=None
        )
        queries.create_audit_log(entry)

    def log_user_logout(self, user: User) -> None:
        """Log user logout."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="logout",
            entity_type="user",
            entity_id=user.id,
            details=None
        )
        queries.create_audit_log(entry)

    def log_user_created(self, admin: User, new_user: User) -> None:
        """Log user creation by admin."""
        entry = AuditLogEntry(
            user_id=admin.id,
            username=admin.username,
            action="created",
            entity_type="user",
            entity_id=new_user.id,
            details={"username": new_user.username, "role": new_user.role}
        )
        queries.create_audit_log(entry)

    def log_user_updated(self, admin: User, updated_user: User, changes: dict) -> None:
        """Log user update by admin."""
        entry = AuditLogEntry(
            user_id=admin.id,
            username=admin.username,
            action="updated",
            entity_type="user",
            entity_id=updated_user.id,
            details={"username": updated_user.username, "changes": changes}
        )
        queries.create_audit_log(entry)

    def log_user_deleted(self, admin: User, deleted_user: User) -> None:
        """Log user deletion by admin."""
        entry = AuditLogEntry(
            user_id=admin.id,
            username=admin.username,
            action="deleted",
            entity_type="user",
            entity_id=deleted_user.id,
            details={"username": deleted_user.username}
        )
        queries.create_audit_log(entry)

    def log_settings_changed(self, user: User, setting: str, old_value: str, new_value: str) -> None:
        """Log settings change."""
        entry = AuditLogEntry(
            user_id=user.id,
            username=user.username,
            action="changed",
            entity_type="settings",
            entity_id=None,
            details={"setting": setting, "before": old_value, "after": new_value}
        )
        queries.create_audit_log(entry)


# Singleton instance
_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    """Get the singleton audit service instance."""
    global _audit_service
    if _audit_service is None:
        _audit_service = AuditService()
    return _audit_service
