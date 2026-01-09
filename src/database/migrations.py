"""Database schema creation and demo data generation."""

import random
from datetime import date, datetime, timedelta

import bcrypt

from .connection import DatabaseConnection
from .models import Status, RiskLevel, UserRole
from . import queries


# =============================================================================
# Schema Definition
# =============================================================================

SCHEMA_SQL = """
-- Issues table
CREATE TABLE IF NOT EXISTS issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT CHECK(status IN ('Draft', 'Open', 'In Progress', 'Remediated', 'Closed')) DEFAULT 'Draft',
    summary_description TEXT,
    topic TEXT,
    identified_by TEXT,
    owner TEXT,
    department TEXT,
    description TEXT,
    remediation_action TEXT,
    risk_description TEXT,
    risk_level TEXT CHECK(risk_level IN ('None', 'Low', 'Medium', 'High')) DEFAULT 'None',
    identification_date DATE,
    due_date DATE,
    follow_up_date DATE,
    updates TEXT,
    closing_date DATE,
    supporting_docs TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('Administrator', 'Editor', 'Restricted', 'Viewer')) DEFAULT 'Viewer',
    departments TEXT,
    force_password_change INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Audit log table
CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_type TEXT NOT NULL,
    entity_id INTEGER,
    details TEXT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_issues_status ON issues(status);
CREATE INDEX IF NOT EXISTS idx_issues_department ON issues(department);
CREATE INDEX IF NOT EXISTS idx_issues_due_date ON issues(due_date);
CREATE INDEX IF NOT EXISTS idx_issues_risk_level ON issues(risk_level);
CREATE INDEX IF NOT EXISTS idx_issues_owner ON issues(owner);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX IF NOT EXISTS idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX IF NOT EXISTS idx_audit_log_user ON audit_log(user_id);
"""


def init_database() -> None:
    """Initialize database schema."""
    db = DatabaseConnection.get_instance()
    db.get_connection().executescript(SCHEMA_SQL)
    db.commit()


def create_default_admin() -> None:
    """Create the default admin user if no users exist."""
    db = DatabaseConnection.get_instance()
    row = db.fetchone("SELECT COUNT(*) as count FROM users")

    if row and row["count"] == 0:
        # Hash the default password
        password_hash = bcrypt.hashpw("admin".encode(), bcrypt.gensalt()).decode()

        db.execute(
            "INSERT INTO users (username, password_hash, role, departments, created_at) VALUES (?, ?, ?, ?, ?)",
            ("admin", password_hash, UserRole.ADMINISTRATOR.value, "[]", datetime.now().isoformat())
        )
        db.commit()


def set_master_password(password: str = "masterpass123") -> None:
    """Set the master password for password recovery."""
    password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    queries.set_setting(queries.SETTING_MASTER_PASSWORD, password_hash)


def database_needs_init() -> bool:
    """Check if database needs initialization (no tables exist)."""
    db = DatabaseConnection.get_instance()
    try:
        row = db.fetchone("SELECT name FROM sqlite_master WHERE type='table' AND name='issues'")
        return row is None
    except Exception:
        return True


def ensure_all_tables_exist() -> None:
    """
    Ensure all required tables exist in the database.

    This handles the case where a database was created before new tables
    (like audit_log) were added. Uses CREATE TABLE IF NOT EXISTS so it's
    safe to run on existing databases. Also runs column migrations.
    """
    init_database()
    migrate_add_force_password_change()


def migrate_add_force_password_change() -> None:
    """Add force_password_change column to users table if it doesn't exist."""
    db = DatabaseConnection.get_instance()

    # Check if column exists
    row = db.fetchone("PRAGMA table_info(users)")
    columns = db.fetchall("PRAGMA table_info(users)")
    column_names = [col["name"] for col in columns]

    if "force_password_change" not in column_names:
        db.execute("ALTER TABLE users ADD COLUMN force_password_change INTEGER DEFAULT 0")
        db.commit()


def run_migrations() -> None:
    """Run all migrations to set up the database."""
    init_database()
    create_default_admin()
    set_master_password()
    migrate_add_force_password_change()


# =============================================================================
# Demo Data Generation
# =============================================================================

DEPARTMENTS = ["Finance", "Operations", "IT", "HR", "Compliance"]

TOPICS = [
    "Policy Violation",
    "System Error",
    "Process Gap",
    "Compliance Issue",
    "Security Incident",
    "Training Gap"
]

OWNERS = [
    "John Smith",
    "Jane Doe",
    "Mike Johnson",
    "Sarah Williams",
    "Tom Brown"
]

IDENTIFIERS = [
    "Internal Audit",
    "Risk Committee",
    "Department Head",
    "External Auditor",
    "Compliance Officer"
]

SAMPLE_ISSUES = [
    {
        "title": "Outdated Access Control Policy",
        "summary": "Access control policy has not been reviewed in 18 months",
        "topic": "Policy Violation",
        "risk_level": RiskLevel.HIGH.value,
        "description": "The access control policy document was last reviewed in June 2023. Per regulatory requirements, all security policies must be reviewed annually. This creates compliance exposure.",
        "remediation": "Schedule policy review with IT Security and Compliance teams. Update policy to reflect current access management practices."
    },
    {
        "title": "Server Backup Failure",
        "summary": "Weekly backup job failed for 3 consecutive weeks",
        "topic": "System Error",
        "risk_level": RiskLevel.HIGH.value,
        "description": "The automated backup job for the finance server has failed for the past three weeks. Error logs indicate disk space issues on the backup storage.",
        "remediation": "Expand backup storage capacity. Implement disk space monitoring alerts. Verify backup integrity after fix."
    },
    {
        "title": "Missing Approval Signatures",
        "summary": "Purchase orders lacking required dual approval",
        "topic": "Process Gap",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Audit sample revealed 12% of purchase orders over $5,000 were missing secondary approval signatures as required by procurement policy.",
        "remediation": "Implement automated workflow requiring dual approval before PO processing. Train staff on approval requirements."
    },
    {
        "title": "GDPR Data Retention Non-Compliance",
        "summary": "Customer data retained beyond allowed period",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.HIGH.value,
        "description": "Customer personal data in the legacy CRM system has been retained for 7+ years, exceeding the 5-year retention limit specified in our privacy policy.",
        "remediation": "Implement data purging process for records beyond retention period. Update CRM with automated retention rules."
    },
    {
        "title": "Unpatched Critical Vulnerability",
        "summary": "CVE-2024-1234 not applied to production servers",
        "topic": "Security Incident",
        "risk_level": RiskLevel.HIGH.value,
        "description": "Critical vulnerability CVE-2024-1234 affecting the web application framework remains unpatched on 5 production servers after 45 days.",
        "remediation": "Schedule emergency patching window. Apply patch to all affected systems. Verify patch application."
    },
    {
        "title": "Incomplete Security Awareness Training",
        "summary": "30% of staff have not completed annual security training",
        "topic": "Training Gap",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Review of training records shows 47 employees (30%) have not completed mandatory annual security awareness training.",
        "remediation": "Send reminder notices to non-compliant staff. Set deadline for completion. Escalate to managers for persistent non-compliance."
    },
    {
        "title": "Segregation of Duties Violation",
        "summary": "Single user has incompatible system access",
        "topic": "Process Gap",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "User account analysis revealed one staff member has both invoice creation and payment approval access in the ERP system.",
        "remediation": "Remove conflicting access. Implement quarterly access review process. Document compensating controls."
    },
    {
        "title": "Expired SSL Certificates",
        "summary": "3 internal applications have expired certificates",
        "topic": "System Error",
        "risk_level": RiskLevel.LOW.value,
        "description": "Three internal applications are showing certificate errors due to expired SSL certificates.",
        "remediation": "Renew certificates. Implement certificate expiration monitoring. Add to renewal calendar."
    },
    {
        "title": "Audit Trail Gaps",
        "summary": "Financial system missing 2 days of audit logs",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Audit log analysis revealed missing entries from March 15-16 in the core financial system. Log server disk full during that period.",
        "remediation": "Implement log storage monitoring. Review affected transactions manually. Document gap in audit report."
    },
    {
        "title": "Third-Party Risk Assessment Overdue",
        "summary": "5 vendors missing annual risk assessments",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Annual risk assessments for 5 critical vendors are more than 90 days overdue.",
        "remediation": "Schedule assessments with vendor contacts. Update vendor risk register. Implement reminder system."
    },
    {
        "title": "Password Policy Non-Enforcement",
        "summary": "Legacy system not enforcing password complexity",
        "topic": "Security Incident",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "The legacy HR system does not enforce the corporate password complexity requirements.",
        "remediation": "Configure password policy settings. Force password reset for all users. Plan system upgrade."
    },
    {
        "title": "Business Continuity Plan Testing",
        "summary": "BCP not tested in current year",
        "topic": "Process Gap",
        "risk_level": RiskLevel.LOW.value,
        "description": "The business continuity plan for Operations department has not been tested in the current calendar year as required by policy.",
        "remediation": "Schedule BCP test exercise. Document results. Update plan based on findings."
    },
    {
        "title": "Unauthorized Software Installation",
        "summary": "Unapproved software found on 8 workstations",
        "topic": "Policy Violation",
        "risk_level": RiskLevel.LOW.value,
        "description": "IT scan discovered unauthorized software installed on 8 employee workstations, including file sharing and remote access tools.",
        "remediation": "Remove unauthorized software. Reinforce software policy with staff. Enable software installation controls."
    },
    {
        "title": "Data Classification Inconsistency",
        "summary": "Confidential documents stored in public folders",
        "topic": "Policy Violation",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "File server audit found confidential HR documents stored in departmental shared folders accessible to all staff.",
        "remediation": "Move files to restricted folders. Review folder permissions. Conduct data classification training."
    },
    {
        "title": "Disaster Recovery Site Audit Finding",
        "summary": "DR site hardware inventory incomplete",
        "topic": "Process Gap",
        "risk_level": RiskLevel.LOW.value,
        "description": "External audit noted that DR site hardware inventory does not match production environment specification.",
        "remediation": "Complete DR hardware inventory. Procure missing equipment. Update DR documentation."
    },
    {
        "title": "Endpoint Protection Coverage Gap",
        "summary": "15 devices missing antivirus agent",
        "topic": "Security Incident",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Endpoint security console shows 15 devices have not reported to management server in 30+ days.",
        "remediation": "Locate missing devices. Reinstall security agents. Implement alerting for offline endpoints."
    },
    {
        "title": "Change Management Process Bypass",
        "summary": "Production change made without CAB approval",
        "topic": "Process Gap",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Review found that a firewall rule change was implemented without going through the Change Advisory Board.",
        "remediation": "Document the change retrospectively. Reinforce change process with IT team. Add controls to prevent bypass."
    },
    {
        "title": "Contract Review Backlog",
        "summary": "12 vendor contracts pending legal review",
        "topic": "Process Gap",
        "risk_level": RiskLevel.LOW.value,
        "description": "Legal department has 12 vendor contracts pending review, some for over 60 days.",
        "remediation": "Prioritize contract review queue. Add temporary legal resource. Implement contract SLA tracking."
    },
    {
        "title": "Physical Access Log Gaps",
        "summary": "Server room access log book incomplete",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.LOW.value,
        "description": "Review of physical access logs found incomplete entries for server room access during night shift.",
        "remediation": "Reinforce logging requirements. Consider electronic access system. Audit access cards."
    },
    {
        "title": "Incident Response Plan Update",
        "summary": "IR plan contact list outdated",
        "topic": "Process Gap",
        "risk_level": RiskLevel.LOW.value,
        "description": "The incident response plan contains contact information for staff who left the organization 6+ months ago.",
        "remediation": "Update contact list. Implement quarterly contact verification. Link to HR system for auto-updates."
    },
    {
        "title": "Network Segmentation Review",
        "summary": "Flat network design poses security risk",
        "topic": "Security Incident",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Penetration test revealed that the internal network lacks proper segmentation between departments.",
        "remediation": "Design network segmentation plan. Implement VLANs. Configure inter-VLAN firewall rules."
    },
    {
        "title": "Mobile Device Management Gaps",
        "summary": "Corporate email on unmanaged personal devices",
        "topic": "Policy Violation",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Security review found 23 employees accessing corporate email on personal devices not enrolled in MDM.",
        "remediation": "Enroll devices in MDM. Block non-compliant devices. Update BYOD policy."
    },
    {
        "title": "Supplier Security Questionnaire",
        "summary": "New vendor onboarded without security review",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.LOW.value,
        "description": "New IT vendor was onboarded without completing the required security questionnaire.",
        "remediation": "Complete vendor security assessment. Add checkpoint to procurement process."
    },
    {
        "title": "Code Review Process Gap",
        "summary": "Applications deployed without peer code review",
        "topic": "Process Gap",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "Development team audit found 4 recent deployments that bypassed the mandatory peer code review step.",
        "remediation": "Reinforce code review requirements. Enable branch protection rules. Train developers on process."
    },
    {
        "title": "Privilege Access Review Overdue",
        "summary": "Quarterly admin access review not completed",
        "topic": "Compliance Issue",
        "risk_level": RiskLevel.MEDIUM.value,
        "description": "The Q3 privileged access review for system administrators is 45 days overdue.",
        "remediation": "Complete access review immediately. Document findings. Set calendar reminders for future reviews."
    },
]


def generate_demo_data() -> None:
    """Generate demo issues and users for testing."""
    db = DatabaseConnection.get_instance()

    # Check if demo data already exists
    row = db.fetchone("SELECT COUNT(*) as count FROM issues")
    if row and row["count"] > 0:
        return  # Demo data already exists

    today = date.today()

    # Create demo users
    demo_users = [
        ("editor1", "editor1", UserRole.EDITOR.value, []),
        ("restricted1", "restricted1", UserRole.RESTRICTED.value, ["Finance", "HR"]),
        ("restricted2", "restricted2", UserRole.RESTRICTED.value, ["IT", "Operations"]),
        ("viewer1", "viewer1", UserRole.VIEWER.value, []),
    ]

    for username, password, role, departments in demo_users:
        if not queries.user_exists(username):
            password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
            db.execute(
                "INSERT INTO users (username, password_hash, role, departments, created_at) VALUES (?, ?, ?, ?, ?)",
                (username, password_hash, role, "[]" if not departments else str(departments).replace("'", '"'), datetime.now().isoformat())
            )

    db.commit()

    # Generate demo issues
    statuses = [s.value for s in Status]

    for i, issue_data in enumerate(SAMPLE_ISSUES):
        # Assign varied statuses
        if i < 3:
            status = Status.DRAFT.value
        elif i < 8:
            status = Status.OPEN.value
        elif i < 14:
            status = Status.IN_PROGRESS.value
        elif i < 20:
            status = Status.REMEDIATED.value
        else:
            status = Status.CLOSED.value

        # Generate dates
        identification_date = today - timedelta(days=random.randint(10, 90))
        due_date = today + timedelta(days=random.randint(-10, 30))  # Some overdue
        follow_up_date = today + timedelta(days=random.randint(1, 14))
        closing_date = (today - timedelta(days=random.randint(1, 5))) if status == Status.CLOSED.value else None

        # Random assignments
        department = random.choice(DEPARTMENTS)
        owner = random.choice(OWNERS)
        identified_by = random.choice(IDENTIFIERS)

        updates = None
        if status in [Status.IN_PROGRESS.value, Status.REMEDIATED.value, Status.CLOSED.value]:
            updates = f"[{(today - timedelta(days=5)).isoformat()}] Initial assessment completed.\n"
            updates += f"[{(today - timedelta(days=2)).isoformat()}] Work in progress on remediation actions."

        db.execute("""
            INSERT INTO issues (
                title, status, summary_description, topic, identified_by, owner,
                department, description, remediation_action, risk_description,
                risk_level, identification_date, due_date, follow_up_date,
                updates, closing_date, supporting_docs, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            issue_data["title"],
            status,
            issue_data["summary"],
            issue_data["topic"],
            identified_by,
            owner,
            department,
            issue_data["description"],
            issue_data["remediation"],
            f"Risk assessment: {issue_data['risk_level']} priority issue requiring attention.",
            issue_data["risk_level"],
            identification_date.isoformat(),
            due_date.isoformat(),
            follow_up_date.isoformat(),
            updates,
            closing_date.isoformat() if closing_date else None,
            "[]",
            datetime.now().isoformat(),
            datetime.now().isoformat(),
        ))

    db.commit()


def setup_database_with_demo_data() -> None:
    """Complete database setup including demo data."""
    run_migrations()
    generate_demo_data()
