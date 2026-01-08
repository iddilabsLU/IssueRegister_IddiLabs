"""Database query functions for Issue Register."""

import json
from datetime import date, datetime
from typing import Optional

from .connection import DatabaseConnection
from .models import Issue, User, AuditLogEntry, Status, RiskLevel


# =============================================================================
# Issue Queries
# =============================================================================

def create_issue(issue: Issue) -> Issue:
    """
    Create a new issue in the database.

    Args:
        issue: Issue object to create (id will be assigned)

    Returns:
        Issue with assigned id and timestamps
    """
    db = DatabaseConnection.get_instance()

    now = datetime.now()
    sql = """
        INSERT INTO issues (
            title, status, summary_description, topic, identified_by, owner,
            department, description, remediation_action, risk_description,
            risk_level, identification_date, due_date, follow_up_date,
            updates, closing_date, supporting_docs, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    params = (
        issue.title,
        issue.status,
        issue.summary_description,
        issue.topic,
        issue.identified_by,
        issue.owner,
        issue.department,
        issue.description,
        issue.remediation_action,
        issue.risk_description,
        issue.risk_level,
        issue.identification_date.isoformat() if issue.identification_date else None,
        issue.due_date.isoformat() if issue.due_date else None,
        issue.follow_up_date.isoformat() if issue.follow_up_date else None,
        issue.updates,
        issue.closing_date.isoformat() if issue.closing_date else None,
        json.dumps(issue.supporting_docs),
        now.isoformat(),
        now.isoformat(),
    )

    cursor = db.execute(sql, params)
    db.commit()

    issue.id = cursor.lastrowid
    issue.created_at = now
    issue.updated_at = now

    return issue


def get_issue(issue_id: int) -> Optional[Issue]:
    """
    Get an issue by ID.

    Args:
        issue_id: Issue ID to retrieve

    Returns:
        Issue object or None if not found
    """
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT * FROM issues WHERE id = ?", (issue_id,))

    if row is None:
        return None

    return Issue.from_row(row)


def update_issue(issue: Issue) -> Issue:
    """
    Update an existing issue.

    Args:
        issue: Issue object with updated values

    Returns:
        Updated Issue object
    """
    if issue.id is None:
        raise ValueError("Cannot update issue without id")

    db = DatabaseConnection.get_instance()
    now = datetime.now()

    sql = """
        UPDATE issues SET
            title = ?, status = ?, summary_description = ?, topic = ?,
            identified_by = ?, owner = ?, department = ?, description = ?,
            remediation_action = ?, risk_description = ?, risk_level = ?,
            identification_date = ?, due_date = ?, follow_up_date = ?,
            updates = ?, closing_date = ?, supporting_docs = ?, updated_at = ?
        WHERE id = ?
    """

    params = (
        issue.title,
        issue.status,
        issue.summary_description,
        issue.topic,
        issue.identified_by,
        issue.owner,
        issue.department,
        issue.description,
        issue.remediation_action,
        issue.risk_description,
        issue.risk_level,
        issue.identification_date.isoformat() if issue.identification_date else None,
        issue.due_date.isoformat() if issue.due_date else None,
        issue.follow_up_date.isoformat() if issue.follow_up_date else None,
        issue.updates,
        issue.closing_date.isoformat() if issue.closing_date else None,
        json.dumps(issue.supporting_docs),
        now.isoformat(),
        issue.id,
    )

    db.execute(sql, params)
    db.commit()

    issue.updated_at = now
    return issue


def delete_issue(issue_id: int) -> bool:
    """
    Delete an issue by ID.

    Args:
        issue_id: Issue ID to delete

    Returns:
        True if deleted, False if not found
    """
    db = DatabaseConnection.get_instance()
    cursor = db.execute("DELETE FROM issues WHERE id = ?", (issue_id,))
    db.commit()
    return cursor.rowcount > 0


def list_issues(
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
    List issues with optional filters.

    Args:
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
        List of Issue objects matching filters
    """
    db = DatabaseConnection.get_instance()

    conditions = []
    params = []

    if status:
        placeholders = ", ".join("?" * len(status))
        conditions.append(f"status IN ({placeholders})")
        params.extend(status)

    if risk_level:
        placeholders = ", ".join("?" * len(risk_level))
        conditions.append(f"risk_level IN ({placeholders})")
        params.extend(risk_level)

    if department:
        placeholders = ", ".join("?" * len(department))
        conditions.append(f"department IN ({placeholders})")
        params.extend(department)

    if owner:
        placeholders = ", ".join("?" * len(owner))
        conditions.append(f"owner IN ({placeholders})")
        params.extend(owner)

    if identified_by:
        placeholders = ", ".join("?" * len(identified_by))
        conditions.append(f"identified_by IN ({placeholders})")
        params.extend(identified_by)

    if topic:
        placeholders = ", ".join("?" * len(topic))
        conditions.append(f"topic IN ({placeholders})")
        params.extend(topic)

    if due_date_from:
        conditions.append("due_date >= ?")
        params.append(due_date_from.isoformat())

    if due_date_to:
        conditions.append("due_date <= ?")
        params.append(due_date_to.isoformat())

    if identification_date_from:
        conditions.append("identification_date >= ?")
        params.append(identification_date_from.isoformat())

    if identification_date_to:
        conditions.append("identification_date <= ?")
        params.append(identification_date_to.isoformat())

    # Build query
    sql = "SELECT * FROM issues"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    # Validate order_by to prevent SQL injection
    valid_columns = [
        "id", "title", "status", "topic", "identified_by", "owner",
        "department", "risk_level", "due_date", "created_at", "updated_at"
    ]
    if order_by not in valid_columns:
        order_by = "id"
    if order_dir.upper() not in ["ASC", "DESC"]:
        order_dir = "DESC"

    sql += f" ORDER BY {order_by} {order_dir}"

    rows = db.fetchall(sql, tuple(params))
    return [Issue.from_row(row) for row in rows]


def get_distinct_values(column: str) -> list[str]:
    """
    Get distinct values for a column (for dropdown population).

    Args:
        column: Column name

    Returns:
        List of distinct non-null values
    """
    # Validate column name to prevent SQL injection
    valid_columns = ["topic", "identified_by", "owner", "department"]
    if column not in valid_columns:
        raise ValueError(f"Invalid column: {column}")

    db = DatabaseConnection.get_instance()
    rows = db.fetchall(
        f"SELECT DISTINCT {column} FROM issues WHERE {column} IS NOT NULL ORDER BY {column}"
    )
    return [row[column] for row in rows]


# =============================================================================
# Dashboard Queries
# =============================================================================

def get_issue_count() -> int:
    """Get total issue count."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT COUNT(*) as count FROM issues")
    return row["count"] if row else 0


def get_active_issue_count() -> int:
    """Get count of active issues (Open, In Progress, Remediated)."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone(
        "SELECT COUNT(*) as count FROM issues WHERE status IN (?, ?, ?)",
        (Status.OPEN.value, Status.IN_PROGRESS.value, Status.REMEDIATED.value)
    )
    return row["count"] if row else 0


def get_high_priority_open_count() -> int:
    """Get count of high priority open issues."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone(
        "SELECT COUNT(*) as count FROM issues WHERE status = ? AND risk_level = ?",
        (Status.OPEN.value, RiskLevel.HIGH.value)
    )
    return row["count"] if row else 0


def get_overdue_count() -> int:
    """Get count of overdue issues (past due date, not closed)."""
    db = DatabaseConnection.get_instance()
    today = date.today().isoformat()
    row = db.fetchone(
        "SELECT COUNT(*) as count FROM issues WHERE due_date < ? AND status != ?",
        (today, Status.CLOSED.value)
    )
    return row["count"] if row else 0


def get_closed_count() -> int:
    """Get count of closed issues."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone(
        "SELECT COUNT(*) as count FROM issues WHERE status = ?",
        (Status.CLOSED.value,)
    )
    return row["count"] if row else 0


def get_status_distribution() -> dict[str, int]:
    """Get issue count by status."""
    db = DatabaseConnection.get_instance()
    rows = db.fetchall(
        "SELECT status, COUNT(*) as count FROM issues GROUP BY status"
    )
    result = {s.value: 0 for s in Status}
    for row in rows:
        result[row["status"]] = row["count"]
    return result


def get_risk_distribution() -> dict[str, int]:
    """Get issue count by risk level."""
    db = DatabaseConnection.get_instance()
    rows = db.fetchall(
        "SELECT risk_level, COUNT(*) as count FROM issues GROUP BY risk_level"
    )
    result = {r.value: 0 for r in RiskLevel}
    for row in rows:
        result[row["risk_level"]] = row["count"]
    return result


def get_department_distribution() -> dict[str, dict[str, int]]:
    """Get issue count by department, broken down by status."""
    db = DatabaseConnection.get_instance()
    rows = db.fetchall("""
        SELECT department, status, COUNT(*) as count
        FROM issues
        WHERE department IS NOT NULL
        GROUP BY department, status
        ORDER BY department
    """)

    result = {}
    for row in rows:
        dept = row["department"]
        if dept not in result:
            result[dept] = {s.value: 0 for s in Status}
        result[dept][row["status"]] = row["count"]

    return result


def get_topic_distribution() -> dict[str, dict[str, int]]:
    """Get issue count by topic, broken down by status."""
    db = DatabaseConnection.get_instance()
    rows = db.fetchall("""
        SELECT topic, status, COUNT(*) as count
        FROM issues
        WHERE topic IS NOT NULL
        GROUP BY topic, status
        ORDER BY topic
    """)

    result = {}
    for row in rows:
        topic = row["topic"]
        if topic not in result:
            result[topic] = {s.value: 0 for s in Status}
        result[topic][row["status"]] = row["count"]

    return result


# =============================================================================
# User Queries
# =============================================================================

def create_user(user: User) -> User:
    """
    Create a new user.

    Args:
        user: User object to create

    Returns:
        User with assigned id
    """
    db = DatabaseConnection.get_instance()
    now = datetime.now()

    sql = """
        INSERT INTO users (username, password_hash, role, departments, created_at)
        VALUES (?, ?, ?, ?, ?)
    """

    # Use to_dict() for proper department serialization (handles Editor format)
    user_dict = user.to_dict()

    params = (
        user.username,
        user.password_hash,
        user.role,
        user_dict["departments"],
        now.isoformat(),
    )

    cursor = db.execute(sql, params)
    db.commit()

    user.id = cursor.lastrowid
    user.created_at = now

    return user


def get_user(user_id: int) -> Optional[User]:
    """Get a user by ID."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT * FROM users WHERE id = ?", (user_id,))
    return User.from_row(row) if row else None


def get_user_by_username(username: str) -> Optional[User]:
    """Get a user by username."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT * FROM users WHERE username = ?", (username,))
    return User.from_row(row) if row else None


def update_user(user: User) -> User:
    """Update an existing user."""
    if user.id is None:
        raise ValueError("Cannot update user without id")

    db = DatabaseConnection.get_instance()

    sql = """
        UPDATE users SET
            username = ?, password_hash = ?, role = ?, departments = ?
        WHERE id = ?
    """

    # Use to_dict() for proper department serialization (handles Editor format)
    user_dict = user.to_dict()

    params = (
        user.username,
        user.password_hash,
        user.role,
        user_dict["departments"],
        user.id,
    )

    db.execute(sql, params)
    db.commit()

    return user


def delete_user(user_id: int) -> bool:
    """Delete a user by ID."""
    db = DatabaseConnection.get_instance()
    cursor = db.execute("DELETE FROM users WHERE id = ?", (user_id,))
    db.commit()
    return cursor.rowcount > 0


def list_users() -> list[User]:
    """Get all users."""
    db = DatabaseConnection.get_instance()
    rows = db.fetchall("SELECT * FROM users ORDER BY username")
    return [User.from_row(row) for row in rows]


def user_exists(username: str) -> bool:
    """Check if a username already exists."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone(
        "SELECT COUNT(*) as count FROM users WHERE username = ?",
        (username,)
    )
    return row["count"] > 0 if row else False


# =============================================================================
# Settings Queries
# =============================================================================

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT value FROM settings WHERE key = ?", (key,))
    return row["value"] if row else default


def set_setting(key: str, value: str) -> None:
    """Set a setting value (insert or update)."""
    db = DatabaseConnection.get_instance()
    db.execute(
        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
        (key, value)
    )
    db.commit()


def delete_setting(key: str) -> bool:
    """Delete a setting by key."""
    db = DatabaseConnection.get_instance()
    cursor = db.execute("DELETE FROM settings WHERE key = ?", (key,))
    db.commit()
    return cursor.rowcount > 0


# Settings keys
SETTING_AUTH_ENABLED = "auth_enabled"
SETTING_MASTER_PASSWORD = "master_password"
SETTING_DB_PATH = "db_path"


# =============================================================================
# Audit Log Queries
# =============================================================================

def create_audit_log(entry: AuditLogEntry) -> AuditLogEntry:
    """
    Create a new audit log entry.

    Args:
        entry: AuditLogEntry object to create

    Returns:
        AuditLogEntry with assigned id and timestamp
    """
    db = DatabaseConnection.get_instance()
    now = datetime.now()

    sql = """
        INSERT INTO audit_log (user_id, username, action, entity_type, entity_id, details, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """

    params = (
        entry.user_id,
        entry.username,
        entry.action,
        entry.entity_type,
        entry.entity_id,
        json.dumps(entry.details) if entry.details else None,
        now.isoformat(),
    )

    cursor = db.execute(sql, params)
    db.commit()

    entry.id = cursor.lastrowid
    entry.timestamp = now

    return entry


def list_audit_logs(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    user_id: Optional[int] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 1000,
) -> list[AuditLogEntry]:
    """
    List audit log entries with optional filters.

    Args:
        entity_type: Filter by entity type (issue, user, settings)
        entity_id: Filter by entity ID
        user_id: Filter by user ID
        action: Filter by action type
        from_date: Filter by timestamp (from)
        to_date: Filter by timestamp (to)
        limit: Maximum number of entries to return

    Returns:
        List of AuditLogEntry objects
    """
    db = DatabaseConnection.get_instance()

    conditions = []
    params = []

    if entity_type:
        conditions.append("entity_type = ?")
        params.append(entity_type)

    if entity_id is not None:
        conditions.append("entity_id = ?")
        params.append(entity_id)

    if user_id is not None:
        conditions.append("user_id = ?")
        params.append(user_id)

    if action:
        conditions.append("action = ?")
        params.append(action)

    if from_date:
        conditions.append("timestamp >= ?")
        params.append(from_date.isoformat())

    if to_date:
        conditions.append("timestamp <= ?")
        params.append(to_date.isoformat())

    sql = "SELECT * FROM audit_log"
    if conditions:
        sql += " WHERE " + " AND ".join(conditions)
    sql += f" ORDER BY timestamp DESC LIMIT {limit}"

    rows = db.fetchall(sql, tuple(params))
    return [AuditLogEntry.from_row(row) for row in rows]


def get_audit_log_count() -> int:
    """Get total audit log entry count."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT COUNT(*) as count FROM audit_log")
    return row["count"] if row else 0
