"""SQLite database connection management with WAL mode support."""

import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, date
from pathlib import Path
from typing import Optional

# Default database location in user's documents
DEFAULT_DB_NAME = "issue_register.db"


# Custom datetime adapters and converters for Python 3.13 compatibility
# Python 3.13 deprecated the default sqlite3 TIMESTAMP converter
def _adapt_datetime(dt: datetime) -> str:
    """Convert datetime to ISO format string for storage."""
    return dt.isoformat(" ")  # Use space separator for sqlite compatibility


def _adapt_date(d: date) -> str:
    """Convert date to ISO format string for storage."""
    return d.isoformat()


def _convert_datetime(val: bytes) -> datetime:
    """Convert stored string back to datetime."""
    decoded = val.decode("utf-8")
    # Handle both "T" separator (ISO) and space separator
    if "T" in decoded:
        decoded = decoded.replace("T", " ")
    # Handle optional microseconds and timezone
    try:
        # Try with microseconds first
        if "." in decoded:
            # Remove timezone info if present
            if "+" in decoded:
                decoded = decoded.split("+")[0]
            elif decoded.endswith("Z"):
                decoded = decoded[:-1]
            return datetime.strptime(decoded, "%Y-%m-%d %H:%M:%S.%f")
        else:
            return datetime.strptime(decoded, "%Y-%m-%d %H:%M:%S")
    except ValueError:
        # Fall back to date only
        return datetime.strptime(decoded[:10], "%Y-%m-%d")


def _convert_date(val: bytes) -> date:
    """Convert stored string back to date."""
    decoded = val.decode("utf-8")
    return datetime.strptime(decoded[:10], "%Y-%m-%d").date()


# Register adapters (Python object -> SQLite)
sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_adapter(date, _adapt_date)

# Register converters (SQLite -> Python object)
sqlite3.register_converter("TIMESTAMP", _convert_datetime)
sqlite3.register_converter("DATETIME", _convert_datetime)
sqlite3.register_converter("DATE", _convert_date)


class DatabaseConnection:
    """
    Singleton database connection manager with WAL mode for concurrent access.

    Usage:
        db = DatabaseConnection.get_instance()
        with db.get_connection() as conn:
            cursor = conn.execute("SELECT * FROM issues")
    """

    _instance: Optional["DatabaseConnection"] = None
    _lock = threading.Lock()

    def __init__(self, db_path: Optional[str] = None):
        """
        Initialize database connection.

        Args:
            db_path: Path to SQLite database file. If None, uses default location.
        """
        if db_path is None:
            # Default to application directory
            self._db_path = Path(__file__).parent.parent.parent / DEFAULT_DB_NAME
        else:
            self._db_path = Path(db_path)

        self._connection: Optional[sqlite3.Connection] = None
        self._local = threading.local()

    @classmethod
    def get_instance(cls, db_path: Optional[str] = None) -> "DatabaseConnection":
        """
        Get the singleton instance of DatabaseConnection.

        Args:
            db_path: Optional path to database file. Only used on first call.

        Returns:
            DatabaseConnection singleton instance
        """
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls(db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        with cls._lock:
            if cls._instance is not None:
                cls._instance.close()
                cls._instance = None

    @classmethod
    def set_database_path(cls, db_path: str) -> "DatabaseConnection":
        """
        Change the database path and reset the connection.

        Args:
            db_path: New path to database file

        Returns:
            New DatabaseConnection instance
        """
        cls.reset_instance()
        cls._instance = cls(db_path)
        return cls._instance

    @property
    def db_path(self) -> Path:
        """Get the current database file path."""
        return self._db_path

    @property
    def db_exists(self) -> bool:
        """Check if the database file exists."""
        return self._db_path.exists()

    def _create_connection(self) -> sqlite3.Connection:
        """
        Create a new database connection with proper settings.

        Returns:
            Configured SQLite connection
        """
        # Ensure parent directory exists
        self._db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = sqlite3.connect(
            str(self._db_path),
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES,
            timeout=30.0,  # 30 second timeout for busy database
            check_same_thread=False  # Allow connection sharing across threads
        )

        # Enable WAL mode for better concurrent access
        conn.execute("PRAGMA journal_mode=WAL")

        # Enable foreign key constraints
        conn.execute("PRAGMA foreign_keys=ON")

        # Return rows as dictionaries
        conn.row_factory = sqlite3.Row

        return conn

    def get_connection(self) -> sqlite3.Connection:
        """
        Get the database connection, creating if necessary.

        Returns:
            SQLite connection object
        """
        if self._connection is None:
            self._connection = self._create_connection()
        return self._connection

    @contextmanager
    def transaction(self):
        """
        Context manager for database transactions.

        Usage:
            with db.transaction() as conn:
                conn.execute("INSERT INTO ...")
                conn.execute("UPDATE ...")
            # Auto-commits on success, rollback on exception
        """
        conn = self.get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise

    def execute(self, sql: str, parameters: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a SQL statement.

        Args:
            sql: SQL statement to execute
            parameters: Parameters for the SQL statement

        Returns:
            Cursor with results
        """
        conn = self.get_connection()
        return conn.execute(sql, parameters)

    def executemany(self, sql: str, parameters: list) -> sqlite3.Cursor:
        """
        Execute a SQL statement with multiple parameter sets.

        Args:
            sql: SQL statement to execute
            parameters: List of parameter tuples

        Returns:
            Cursor with results
        """
        conn = self.get_connection()
        return conn.executemany(sql, parameters)

    def fetchone(self, sql: str, parameters: tuple = ()) -> Optional[sqlite3.Row]:
        """
        Execute SQL and fetch one result.

        Args:
            sql: SQL query
            parameters: Query parameters

        Returns:
            Single row or None
        """
        cursor = self.execute(sql, parameters)
        return cursor.fetchone()

    def fetchall(self, sql: str, parameters: tuple = ()) -> list[sqlite3.Row]:
        """
        Execute SQL and fetch all results.

        Args:
            sql: SQL query
            parameters: Query parameters

        Returns:
            List of rows
        """
        cursor = self.execute(sql, parameters)
        return cursor.fetchall()

    def commit(self) -> None:
        """Commit the current transaction."""
        if self._connection:
            self._connection.commit()

    def rollback(self) -> None:
        """Rollback the current transaction."""
        if self._connection:
            self._connection.rollback()

    def close(self) -> None:
        """Close the database connection."""
        if self._connection:
            self._connection.close()
            self._connection = None

    def __enter__(self) -> "DatabaseConnection":
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - close connection."""
        self.close()
