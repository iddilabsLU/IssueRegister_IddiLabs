"""Authentication service for Issue Register."""

from typing import Optional

import bcrypt

from src.database import queries
from src.database.models import User, UserRole
from src.services.audit import get_audit_service


class AuthService:
    """
    Handles user authentication and session management.

    Usage:
        auth = AuthService()
        user = auth.authenticate("admin", "admin")
        if user:
            auth.login(user)
            print(f"Logged in as {auth.current_user.username}")
    """

    def __init__(self):
        """Initialize authentication service."""
        self._current_user: Optional[User] = None
        self._auth_enabled: Optional[bool] = None

    @property
    def current_user(self) -> Optional[User]:
        """Get the currently logged in user."""
        return self._current_user

    @property
    def is_logged_in(self) -> bool:
        """Check if a user is logged in."""
        return self._current_user is not None

    @property
    def is_auth_enabled(self) -> bool:
        """Check if authentication is enabled."""
        if self._auth_enabled is None:
            self._auth_enabled = self._check_auth_enabled()
        return self._auth_enabled

    def _check_auth_enabled(self) -> bool:
        """Check if authentication is enabled in settings."""
        value = queries.get_setting(queries.SETTING_AUTH_ENABLED, "false")
        return value.lower() == "true"

    def refresh_auth_setting(self) -> bool:
        """Refresh the auth enabled setting from database."""
        self._auth_enabled = self._check_auth_enabled()
        return self._auth_enabled

    def enable_authentication(self, enable: bool = True) -> None:
        """
        Enable or disable authentication.

        Args:
            enable: True to enable, False to disable
        """
        queries.set_setting(queries.SETTING_AUTH_ENABLED, str(enable).lower())
        self._auth_enabled = enable

    @staticmethod
    def hash_password(password: str) -> str:
        """
        Hash a password using bcrypt.

        Args:
            password: Plain text password

        Returns:
            Hashed password string
        """
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        """
        Verify a password against its hash.

        Args:
            password: Plain text password to verify
            password_hash: Stored password hash

        Returns:
            True if password matches
        """
        try:
            return bcrypt.checkpw(password.encode(), password_hash.encode())
        except Exception:
            return False

    def authenticate(self, username: str, password: str) -> Optional[User]:
        """
        Authenticate a user with username and password.

        Args:
            username: User's username
            password: User's plain text password

        Returns:
            User object if authentication successful, None otherwise
        """
        user = queries.get_user_by_username(username)
        if user is None:
            return None

        if not self.verify_password(password, user.password_hash):
            return None

        return user

    def login(self, user: User) -> None:
        """
        Set the current user session.

        Args:
            user: User to log in
        """
        self._current_user = user
        # Log the login
        get_audit_service().log_user_login(user)

    def logout(self) -> None:
        """Clear the current user session."""
        if self._current_user:
            # Log the logout
            get_audit_service().log_user_logout(self._current_user)
        self._current_user = None

    def login_as_admin(self) -> None:
        """
        Login as default admin (for when auth is disabled).

        Creates a virtual admin user for permission checks.
        """
        # Get actual admin user if exists
        admin = queries.get_user_by_username("admin")
        if admin:
            self._current_user = admin
        else:
            # Create virtual admin
            self._current_user = User(
                id=0,
                username="admin",
                password_hash="",
                role=UserRole.ADMINISTRATOR.value,
                departments=[],
            )

    def verify_master_password(self, password: str) -> bool:
        """
        Verify the master password for password recovery.

        Args:
            password: Master password to verify

        Returns:
            True if master password is correct
        """
        master_hash = queries.get_setting(queries.SETTING_MASTER_PASSWORD)
        if master_hash is None:
            return False

        return self.verify_password(password, master_hash)

    def change_password(self, user_id: int, new_password: str) -> bool:
        """
        Change a user's password.

        Args:
            user_id: ID of user to update
            new_password: New plain text password

        Returns:
            True if successful
        """
        user = queries.get_user(user_id)
        if user is None:
            return False

        user.password_hash = self.hash_password(new_password)
        queries.update_user(user)
        return True

    def create_user(
        self,
        username: str,
        password: str,
        role: str = UserRole.VIEWER.value,
        departments: Optional[list[str]] = None,
        view_departments: Optional[list[str]] = None,
        edit_departments: Optional[list[str]] = None
    ) -> Optional[User]:
        """
        Create a new user account.

        Args:
            username: Unique username
            password: Plain text password
            role: User role
            departments: Department restrictions (for Restricted/Viewer)
            view_departments: Departments Editor can VIEW (for Editor role)
            edit_departments: Departments Editor can EDIT (for Editor role)

        Returns:
            Created User or None if username exists
        """
        if queries.user_exists(username):
            return None

        user = User(
            username=username,
            password_hash=self.hash_password(password),
            role=role,
            departments=departments or [],
            view_departments=view_departments or [],
            edit_departments=edit_departments or [],
        )

        created = queries.create_user(user)

        # Log the creation if we have a current user (admin)
        if self._current_user and created:
            get_audit_service().log_user_created(self._current_user, created)

        return created

    def update_user(
        self,
        user_id: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        role: Optional[str] = None,
        departments: Optional[list[str]] = None,
        view_departments: Optional[list[str]] = None,
        edit_departments: Optional[list[str]] = None
    ) -> Optional[User]:
        """
        Update an existing user.

        Args:
            user_id: ID of user to update
            username: New username (optional)
            password: New password (optional)
            role: New role (optional)
            departments: New department list (for Restricted/Viewer)
            view_departments: Departments Editor can VIEW (for Editor role)
            edit_departments: Departments Editor can EDIT (for Editor role)

        Returns:
            Updated User or None if not found
        """
        user = queries.get_user(user_id)
        if user is None:
            return None

        changes = {}

        if username is not None:
            # Check if new username is taken by another user
            existing = queries.get_user_by_username(username)
            if existing and existing.id != user_id:
                return None
            if user.username != username:
                changes["username"] = {"before": user.username, "after": username}
            user.username = username

        if password is not None:
            user.password_hash = self.hash_password(password)
            changes["password"] = "changed"

        if role is not None:
            if user.role != role:
                changes["role"] = {"before": user.role, "after": role}
            user.role = role

        if departments is not None:
            user.departments = departments

        if view_departments is not None:
            user.view_departments = view_departments

        if edit_departments is not None:
            user.edit_departments = edit_departments

        updated = queries.update_user(user)

        # Log the update if we have a current user (admin) and there were changes
        if self._current_user and updated and changes:
            get_audit_service().log_user_updated(self._current_user, updated, changes)

        return updated

    def delete_user(self, user_id: int) -> bool:
        """
        Delete a user account.

        Args:
            user_id: ID of user to delete

        Returns:
            True if deleted successfully
        """
        # Don't allow deleting the last admin
        user = queries.get_user(user_id)
        if user is None:
            return False

        if user.role == UserRole.ADMINISTRATOR.value:
            admins = [u for u in queries.list_users() if u.role == UserRole.ADMINISTRATOR.value]
            if len(admins) <= 1:
                return False

        result = queries.delete_user(user_id)

        # Log the deletion if we have a current user (admin)
        if result and self._current_user:
            get_audit_service().log_user_deleted(self._current_user, user)

        return result


# Singleton instance
_auth_service: Optional[AuthService] = None


def get_auth_service() -> AuthService:
    """Get the singleton AuthService instance."""
    global _auth_service
    if _auth_service is None:
        _auth_service = AuthService()
    return _auth_service


def reset_auth_service() -> None:
    """Reset the singleton instance (for testing)."""
    global _auth_service
    _auth_service = None
