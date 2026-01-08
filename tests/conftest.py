"""Pytest configuration and shared fixtures."""

import os
import tempfile
from pathlib import Path

import pytest

from src.database.connection import DatabaseConnection
from src.database.migrations import run_migrations


@pytest.fixture
def temp_db():
    """
    Create a temporary database for testing.

    Yields the database path, cleans up after test.
    """
    # Create a temporary file for the database
    fd, db_path = tempfile.mkstemp(suffix=".db")
    os.close(fd)

    # Reset any existing singleton and set up new database
    DatabaseConnection.reset_instance()
    db = DatabaseConnection.get_instance(db_path)

    # Initialize schema
    run_migrations()

    yield db_path

    # Cleanup
    DatabaseConnection.reset_instance()
    try:
        os.unlink(db_path)
        # Also remove WAL and SHM files if they exist
        wal_path = db_path + "-wal"
        shm_path = db_path + "-shm"
        if os.path.exists(wal_path):
            os.unlink(wal_path)
        if os.path.exists(shm_path):
            os.unlink(shm_path)
    except OSError:
        pass


@pytest.fixture
def db_connection(temp_db):
    """Get database connection for testing."""
    return DatabaseConnection.get_instance()


@pytest.fixture
def sample_issue_data():
    """Sample issue data for testing."""
    from datetime import date
    return {
        "title": "Test Issue",
        "status": "Open",
        "summary_description": "Test summary",
        "topic": "System Error",
        "identified_by": "Test User",
        "owner": "Test Owner",
        "department": "IT",
        "description": "Detailed description of the test issue.",
        "remediation_action": "Fix the issue by doing X, Y, Z.",
        "risk_description": "This could impact operations.",
        "risk_level": "Medium",
        "identification_date": date.today(),
        "due_date": date.today(),
        "follow_up_date": date.today(),
        "updates": "Initial update entry.",
        "closing_date": None,
        "supporting_docs": [],
    }


@pytest.fixture
def sample_user_data():
    """Sample user data for testing."""
    import bcrypt
    password_hash = bcrypt.hashpw("testpass".encode(), bcrypt.gensalt()).decode()
    return {
        "username": "testuser",
        "password_hash": password_hash,
        "role": "Editor",
        "departments": [],
    }
