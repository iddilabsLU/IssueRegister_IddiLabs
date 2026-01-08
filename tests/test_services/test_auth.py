"""Tests for authentication service."""

import pytest

from src.services.auth import AuthService, get_auth_service, reset_auth_service
from src.database import queries
from src.database.models import User, UserRole


@pytest.fixture
def auth_service(db_connection):
    """Create a fresh AuthService for testing."""
    reset_auth_service()
    return AuthService()


class TestPasswordHashing:
    """Test password hashing and verification."""

    def test_hash_password(self, auth_service):
        """Test password hashing produces valid hash."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)

        assert hashed != password
        assert len(hashed) > 0

    def test_verify_password_correct(self, auth_service):
        """Test verifying correct password."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password(password, hashed) is True

    def test_verify_password_incorrect(self, auth_service):
        """Test verifying incorrect password."""
        password = "testpassword123"
        hashed = auth_service.hash_password(password)

        assert auth_service.verify_password("wrongpassword", hashed) is False

    def test_verify_password_invalid_hash(self, auth_service):
        """Test verifying against invalid hash returns False."""
        assert auth_service.verify_password("password", "invalid_hash") is False


class TestAuthentication:
    """Test user authentication."""

    def test_authenticate_valid_credentials(self, auth_service, db_connection):
        """Test authentication with valid credentials."""
        # Default admin user exists
        user = auth_service.authenticate("admin", "admin")
        assert user is not None
        assert user.username == "admin"

    def test_authenticate_invalid_password(self, auth_service, db_connection):
        """Test authentication with wrong password."""
        user = auth_service.authenticate("admin", "wrongpassword")
        assert user is None

    def test_authenticate_invalid_username(self, auth_service, db_connection):
        """Test authentication with non-existent user."""
        user = auth_service.authenticate("nonexistent", "password")
        assert user is None


class TestSessionManagement:
    """Test session management."""

    def test_login(self, auth_service, db_connection):
        """Test logging in sets current user."""
        user = queries.get_user_by_username("admin")
        auth_service.login(user)

        assert auth_service.is_logged_in is True
        assert auth_service.current_user == user

    def test_logout(self, auth_service, db_connection):
        """Test logging out clears current user."""
        user = queries.get_user_by_username("admin")
        auth_service.login(user)
        auth_service.logout()

        assert auth_service.is_logged_in is False
        assert auth_service.current_user is None

    def test_login_as_admin(self, auth_service, db_connection):
        """Test login_as_admin sets admin user."""
        auth_service.login_as_admin()

        assert auth_service.is_logged_in is True
        assert auth_service.current_user.role == UserRole.ADMINISTRATOR.value


class TestAuthenticationSettings:
    """Test authentication enable/disable."""

    def test_auth_disabled_by_default(self, auth_service, db_connection):
        """Test authentication is disabled by default."""
        assert auth_service.is_auth_enabled is False

    def test_enable_authentication(self, auth_service, db_connection):
        """Test enabling authentication."""
        auth_service.enable_authentication(True)
        auth_service.refresh_auth_setting()

        assert auth_service.is_auth_enabled is True

    def test_disable_authentication(self, auth_service, db_connection):
        """Test disabling authentication."""
        auth_service.enable_authentication(True)
        auth_service.enable_authentication(False)
        auth_service.refresh_auth_setting()

        assert auth_service.is_auth_enabled is False


class TestMasterPassword:
    """Test master password functionality."""

    def test_verify_master_password_correct(self, auth_service, db_connection):
        """Test verifying correct master password."""
        # Master password is set during migration
        assert auth_service.verify_master_password("masterpass123") is True

    def test_verify_master_password_incorrect(self, auth_service, db_connection):
        """Test verifying incorrect master password."""
        assert auth_service.verify_master_password("wrongmaster") is False


class TestUserManagement:
    """Test user management functions."""

    def test_create_user(self, auth_service, db_connection):
        """Test creating a new user."""
        user = auth_service.create_user(
            username="newuser",
            password="newpassword",
            role=UserRole.EDITOR.value,
            departments=[]
        )

        assert user is not None
        assert user.username == "newuser"
        assert user.role == UserRole.EDITOR.value

    def test_create_user_duplicate_username(self, auth_service, db_connection):
        """Test creating user with existing username fails."""
        auth_service.create_user("testuser", "password")
        user = auth_service.create_user("testuser", "password")

        assert user is None

    def test_change_password(self, auth_service, db_connection):
        """Test changing user password."""
        user = auth_service.create_user("pwuser", "oldpassword")

        result = auth_service.change_password(user.id, "newpassword")
        assert result is True

        # Verify old password no longer works
        auth_result = auth_service.authenticate("pwuser", "oldpassword")
        assert auth_result is None

        # Verify new password works
        auth_result = auth_service.authenticate("pwuser", "newpassword")
        assert auth_result is not None

    def test_update_user(self, auth_service, db_connection):
        """Test updating user details."""
        user = auth_service.create_user("updateuser", "password")

        updated = auth_service.update_user(
            user.id,
            role=UserRole.RESTRICTED.value,
            departments=["IT", "HR"]
        )

        assert updated is not None
        assert updated.role == UserRole.RESTRICTED.value
        assert updated.departments == ["IT", "HR"]

    def test_update_user_username(self, auth_service, db_connection):
        """Test updating username."""
        user = auth_service.create_user("oldname", "password")

        updated = auth_service.update_user(user.id, username="newname")

        assert updated is not None
        assert updated.username == "newname"

    def test_update_user_duplicate_username_fails(self, auth_service, db_connection):
        """Test updating to existing username fails."""
        auth_service.create_user("user1", "password")
        user2 = auth_service.create_user("user2", "password")

        updated = auth_service.update_user(user2.id, username="user1")
        assert updated is None

    def test_delete_user(self, auth_service, db_connection):
        """Test deleting a user."""
        user = auth_service.create_user("deleteuser", "password")

        result = auth_service.delete_user(user.id)
        assert result is True

        # Verify user is gone
        deleted = queries.get_user(user.id)
        assert deleted is None

    def test_cannot_delete_last_admin(self, auth_service, db_connection):
        """Test that the last admin cannot be deleted."""
        admin = queries.get_user_by_username("admin")

        result = auth_service.delete_user(admin.id)
        assert result is False

        # Verify admin still exists
        still_exists = queries.get_user(admin.id)
        assert still_exists is not None


class TestSingleton:
    """Test singleton pattern."""

    def test_get_auth_service_singleton(self, db_connection):
        """Test get_auth_service returns same instance."""
        reset_auth_service()
        service1 = get_auth_service()
        service2 = get_auth_service()

        assert service1 is service2

    def test_reset_auth_service(self, db_connection):
        """Test reset creates new instance."""
        reset_auth_service()
        service1 = get_auth_service()
        reset_auth_service()
        service2 = get_auth_service()

        assert service1 is not service2
