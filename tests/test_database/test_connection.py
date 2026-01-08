"""Tests for database connection module."""

import os
import sqlite3
import tempfile

import pytest

from src.database.connection import DatabaseConnection


class TestDatabaseConnection:
    """Test suite for DatabaseConnection class."""

    def test_singleton_pattern(self, temp_db):
        """Test that get_instance returns the same instance."""
        db1 = DatabaseConnection.get_instance()
        db2 = DatabaseConnection.get_instance()
        assert db1 is db2

    def test_reset_instance(self, temp_db):
        """Test that reset_instance creates new instance."""
        db1 = DatabaseConnection.get_instance()
        DatabaseConnection.reset_instance()
        db2 = DatabaseConnection.get_instance(temp_db)
        assert db1 is not db2

    def test_connection_creates_file(self):
        """Test that getting connection creates database file."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(db_path)  # Remove so we can test creation

        try:
            DatabaseConnection.reset_instance()
            db = DatabaseConnection.get_instance(db_path)
            db.get_connection()
            assert os.path.exists(db_path)
        finally:
            DatabaseConnection.reset_instance()
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_wal_mode_enabled(self, db_connection):
        """Test that WAL mode is enabled."""
        result = db_connection.fetchone("PRAGMA journal_mode")
        assert result[0].lower() == "wal"

    def test_foreign_keys_enabled(self, db_connection):
        """Test that foreign keys are enabled."""
        result = db_connection.fetchone("PRAGMA foreign_keys")
        assert result[0] == 1

    def test_execute_and_fetchone(self, db_connection):
        """Test execute and fetchone methods."""
        db_connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("test_key", "test_value")
        )
        db_connection.commit()

        result = db_connection.fetchone(
            "SELECT value FROM settings WHERE key = ?",
            ("test_key",)
        )
        assert result["value"] == "test_value"

    def test_fetchall(self, db_connection):
        """Test fetchall method."""
        db_connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("key1", "value1")
        )
        db_connection.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?)",
            ("key2", "value2")
        )
        db_connection.commit()

        results = db_connection.fetchall("SELECT * FROM settings ORDER BY key")
        assert len(results) >= 2

    def test_transaction_commit(self, db_connection):
        """Test transaction context manager commits on success."""
        with db_connection.transaction() as conn:
            conn.execute(
                "INSERT INTO settings (key, value) VALUES (?, ?)",
                ("tx_key", "tx_value")
            )

        result = db_connection.fetchone(
            "SELECT value FROM settings WHERE key = ?",
            ("tx_key",)
        )
        assert result["value"] == "tx_value"

    def test_transaction_rollback(self, db_connection):
        """Test transaction context manager rolls back on exception."""
        try:
            with db_connection.transaction() as conn:
                conn.execute(
                    "INSERT INTO settings (key, value) VALUES (?, ?)",
                    ("rollback_key", "rollback_value")
                )
                raise ValueError("Simulated error")
        except ValueError:
            pass

        result = db_connection.fetchone(
            "SELECT value FROM settings WHERE key = ?",
            ("rollback_key",)
        )
        assert result is None

    def test_db_exists_property(self, temp_db):
        """Test db_exists property."""
        db = DatabaseConnection.get_instance()
        assert db.db_exists is True

    def test_db_path_property(self, temp_db):
        """Test db_path property returns Path object."""
        db = DatabaseConnection.get_instance()
        assert db.db_path.exists()

    def test_context_manager(self):
        """Test context manager closes connection."""
        fd, db_path = tempfile.mkstemp(suffix=".db")
        os.close(fd)

        try:
            DatabaseConnection.reset_instance()
            with DatabaseConnection.get_instance(db_path) as db:
                db.execute("SELECT 1")
            # Connection should be closed after context
        finally:
            DatabaseConnection.reset_instance()
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_set_database_path(self):
        """Test changing database path."""
        fd1, db_path1 = tempfile.mkstemp(suffix=".db")
        fd2, db_path2 = tempfile.mkstemp(suffix=".db")
        os.close(fd1)
        os.close(fd2)

        try:
            DatabaseConnection.reset_instance()
            db1 = DatabaseConnection.get_instance(db_path1)
            assert str(db1.db_path) == db_path1

            db2 = DatabaseConnection.set_database_path(db_path2)
            assert str(db2.db_path) == db_path2
        finally:
            DatabaseConnection.reset_instance()
            for path in [db_path1, db_path2]:
                if os.path.exists(path):
                    os.unlink(path)
