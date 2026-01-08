"""Data models for Issue Register."""

from dataclasses import dataclass, field
from datetime import date, datetime
from enum import Enum
from typing import Optional
import json


class Status(str, Enum):
    """Issue status values."""
    DRAFT = "Draft"
    OPEN = "Open"
    IN_PROGRESS = "In Progress"
    REMEDIATED = "Remediated"
    CLOSED = "Closed"

    @classmethod
    def values(cls) -> list[str]:
        """Get all status values as strings."""
        return [s.value for s in cls]


class RiskLevel(str, Enum):
    """Risk level values."""
    NONE = "None"
    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

    @classmethod
    def values(cls) -> list[str]:
        """Get all risk level values as strings."""
        return [r.value for r in cls]


class UserRole(str, Enum):
    """User role values."""
    ADMINISTRATOR = "Administrator"
    EDITOR = "Editor"
    RESTRICTED = "Restricted"
    VIEWER = "Viewer"

    @classmethod
    def values(cls) -> list[str]:
        """Get all role values as strings."""
        return [r.value for r in cls]


@dataclass
class Issue:
    """
    Represents an issue in the register.

    Attributes:
        id: Unique system-assigned identifier
        title: Brief descriptive title for the issue
        status: Current status (Draft, Open, In Progress, Remediated, Closed)
        summary_description: Concise overview of the issue
        topic: Categorical classification
        identified_by: Person who discovered/reported the issue
        owner: Person responsible for resolution
        department: Organisational unit associated with the issue
        description: Detailed explanation of the issue
        remediation_action: Planned or completed corrective actions
        risk_description: Assessment of potential impact
        risk_level: None, Low, Medium, High
        identification_date: Date issue was first identified
        due_date: Target date for resolution
        follow_up_date: Scheduled date for next review
        updates: Chronological progress notes
        closing_date: Date issue was formally closed
        supporting_docs: JSON array of file paths
        created_at: Record creation timestamp
        updated_at: Record last update timestamp
    """
    title: str
    id: Optional[int] = None
    status: str = Status.DRAFT.value
    summary_description: Optional[str] = None
    topic: Optional[str] = None
    identified_by: Optional[str] = None
    owner: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    remediation_action: Optional[str] = None
    risk_description: Optional[str] = None
    risk_level: str = RiskLevel.NONE.value
    identification_date: Optional[date] = None
    due_date: Optional[date] = None
    follow_up_date: Optional[date] = None
    updates: Optional[str] = None
    closing_date: Optional[date] = None
    supporting_docs: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert issue to dictionary for database operations."""
        return {
            "id": self.id,
            "title": self.title,
            "status": self.status,
            "summary_description": self.summary_description,
            "topic": self.topic,
            "identified_by": self.identified_by,
            "owner": self.owner,
            "department": self.department,
            "description": self.description,
            "remediation_action": self.remediation_action,
            "risk_description": self.risk_description,
            "risk_level": self.risk_level,
            "identification_date": self.identification_date.isoformat() if self.identification_date else None,
            "due_date": self.due_date.isoformat() if self.due_date else None,
            "follow_up_date": self.follow_up_date.isoformat() if self.follow_up_date else None,
            "updates": self.updates,
            "closing_date": self.closing_date.isoformat() if self.closing_date else None,
            "supporting_docs": json.dumps(self.supporting_docs),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_row(cls, row) -> "Issue":
        """Create Issue from database row."""
        if row is None:
            raise ValueError("Cannot create Issue from None row")

        # Parse supporting_docs from JSON
        supporting_docs = []
        if row["supporting_docs"]:
            try:
                supporting_docs = json.loads(row["supporting_docs"])
            except json.JSONDecodeError:
                supporting_docs = []

        # Parse dates
        def parse_date(value) -> Optional[date]:
            if value is None:
                return None
            if isinstance(value, date):
                return value
            if isinstance(value, str):
                return date.fromisoformat(value)
            return None

        def parse_datetime(value) -> Optional[datetime]:
            if value is None:
                return None
            if isinstance(value, datetime):
                return value
            if isinstance(value, str):
                return datetime.fromisoformat(value)
            return None

        return cls(
            id=row["id"],
            title=row["title"],
            status=row["status"],
            summary_description=row["summary_description"],
            topic=row["topic"],
            identified_by=row["identified_by"],
            owner=row["owner"],
            department=row["department"],
            description=row["description"],
            remediation_action=row["remediation_action"],
            risk_description=row["risk_description"],
            risk_level=row["risk_level"],
            identification_date=parse_date(row["identification_date"]),
            due_date=parse_date(row["due_date"]),
            follow_up_date=parse_date(row["follow_up_date"]),
            updates=row["updates"],
            closing_date=parse_date(row["closing_date"]),
            supporting_docs=supporting_docs,
            created_at=parse_datetime(row["created_at"]),
            updated_at=parse_datetime(row["updated_at"]),
        )

    def is_overdue(self) -> bool:
        """Check if issue is overdue."""
        if self.due_date is None:
            return False
        if self.status == Status.CLOSED.value:
            return False
        return self.due_date < date.today()

    def is_active(self) -> bool:
        """Check if issue is in an active status."""
        return self.status in [
            Status.OPEN.value,
            Status.IN_PROGRESS.value,
            Status.REMEDIATED.value
        ]


@dataclass
class User:
    """
    Represents a user account.

    Attributes:
        id: Unique user identifier
        username: Login username
        password_hash: bcrypt hashed password
        role: User role (Administrator, Editor, Restricted, Viewer)
        departments: List of departments for Restricted/Viewer roles
        view_departments: List of departments Editor can VIEW (empty = all)
        edit_departments: List of departments Editor can EDIT (empty = all)
        created_at: Account creation timestamp
    """
    username: str
    password_hash: str
    role: str = UserRole.VIEWER.value
    id: Optional[int] = None
    departments: list[str] = field(default_factory=list)
    view_departments: list[str] = field(default_factory=list)
    edit_departments: list[str] = field(default_factory=list)
    created_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert user to dictionary for database operations."""
        # For Editors, store view/edit departments as JSON object
        # For other roles, store departments as array
        if self.role == UserRole.EDITOR.value:
            dept_data = {
                "view": self.view_departments,
                "edit": self.edit_departments
            }
        else:
            dept_data = self.departments

        return {
            "id": self.id,
            "username": self.username,
            "password_hash": self.password_hash,
            "role": self.role,
            "departments": json.dumps(dept_data),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def from_row(cls, row) -> "User":
        """Create User from database row."""
        if row is None:
            raise ValueError("Cannot create User from None row")

        # Parse departments from JSON
        departments = []
        view_departments = []
        edit_departments = []

        if row["departments"]:
            try:
                dept_data = json.loads(row["departments"])
                if isinstance(dept_data, dict):
                    # Editor format: {"view": [...], "edit": [...]}
                    view_departments = dept_data.get("view", [])
                    edit_departments = dept_data.get("edit", [])
                elif isinstance(dept_data, list):
                    # Restricted/Viewer format: [...]
                    departments = dept_data
            except json.JSONDecodeError:
                pass

        # Parse datetime
        created_at = None
        if row["created_at"]:
            if isinstance(row["created_at"], datetime):
                created_at = row["created_at"]
            elif isinstance(row["created_at"], str):
                created_at = datetime.fromisoformat(row["created_at"])

        return cls(
            id=row["id"],
            username=row["username"],
            password_hash=row["password_hash"],
            role=row["role"],
            departments=departments,
            view_departments=view_departments,
            edit_departments=edit_departments,
            created_at=created_at,
        )

    def is_admin(self) -> bool:
        """Check if user is an administrator."""
        return self.role == UserRole.ADMINISTRATOR.value

    def is_editor(self) -> bool:
        """Check if user is an editor."""
        return self.role == UserRole.EDITOR.value

    def is_restricted(self) -> bool:
        """Check if user has restricted access."""
        return self.role == UserRole.RESTRICTED.value

    def is_viewer(self) -> bool:
        """Check if user is view-only."""
        return self.role == UserRole.VIEWER.value

    def can_access_department(self, department: Optional[str]) -> bool:
        """
        Check if user can access a specific department.

        Administrators can access all departments.
        Editors check view_departments if set.
        Restricted and Viewer users can only access their assigned departments.
        """
        if self.role == UserRole.ADMINISTRATOR.value:
            return True
        if self.role == UserRole.EDITOR.value:
            # Editors use view_departments if set
            if not self.view_departments:  # Empty means all departments
                return True
            if department is None:
                return True
            return department in self.view_departments
        # Restricted and Viewer
        if not self.departments:  # Empty means all departments
            return True
        if department is None:
            return True
        return department in self.departments

    def can_edit_department(self, department: Optional[str]) -> bool:
        """
        Check if user can edit issues in a specific department.

        Administrators can edit all departments.
        Editors check edit_departments if set.
        Restricted users can only edit in their assigned departments.
        Viewers cannot edit.
        """
        if self.role == UserRole.ADMINISTRATOR.value:
            return True
        if self.role == UserRole.VIEWER.value:
            return False
        if self.role == UserRole.EDITOR.value:
            # Editors use edit_departments if set
            if not self.edit_departments:  # Empty means all departments
                return True
            if department is None:
                return True
            return department in self.edit_departments
        # Restricted
        if not self.departments:  # Empty means all departments
            return True
        if department is None:
            return True
        return department in self.departments


@dataclass
class AuditLogEntry:
    """
    Represents an audit log entry.

    Attributes:
        id: Unique audit log identifier
        user_id: ID of the user who performed the action
        username: Username of the user (stored for historical reference)
        action: Action performed (created, updated, deleted, status_changed, login, logout)
        entity_type: Type of entity (issue, user, settings)
        entity_id: ID of the affected entity (null for settings)
        details: JSON with before/after values or additional context
        timestamp: When the action occurred
    """
    username: str
    action: str
    entity_type: str
    id: Optional[int] = None
    user_id: Optional[int] = None
    entity_id: Optional[int] = None
    details: Optional[dict] = None
    timestamp: Optional[datetime] = None

    def to_dict(self) -> dict:
        """Convert audit log entry to dictionary for database operations."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "username": self.username,
            "action": self.action,
            "entity_type": self.entity_type,
            "entity_id": self.entity_id,
            "details": json.dumps(self.details) if self.details else None,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
        }

    @classmethod
    def from_row(cls, row) -> "AuditLogEntry":
        """Create AuditLogEntry from database row."""
        if row is None:
            raise ValueError("Cannot create AuditLogEntry from None row")

        # Parse details from JSON
        details = None
        if row["details"]:
            try:
                details = json.loads(row["details"])
            except json.JSONDecodeError:
                details = None

        # Parse datetime
        timestamp = None
        if row["timestamp"]:
            if isinstance(row["timestamp"], datetime):
                timestamp = row["timestamp"]
            elif isinstance(row["timestamp"], str):
                timestamp = datetime.fromisoformat(row["timestamp"])

        return cls(
            id=row["id"],
            user_id=row["user_id"],
            username=row["username"],
            action=row["action"],
            entity_type=row["entity_type"],
            entity_id=row["entity_id"],
            details=details,
            timestamp=timestamp,
        )
