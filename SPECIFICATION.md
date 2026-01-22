# Issue Register — Product Specification

> **Version:** 2.0
> **Status:** Implemented
> **License:** [MIT](LICENSE)
> **Repository:** [github.com/iddilabs/issue-register](https://github.com/iddilabs/issue-register)

An open-source desktop application for tracking issues across organisational departments from identification through closure. Locally installable with optional shared database access, file attachments, and comprehensive audit logging.

This document serves as the complete product specification for contributors and users who want to understand the full feature set and technical details.

---

## Executive Summary

Issue Register is a privacy-first issue tracking system designed for regulated industries and organisations requiring local data control. It provides comprehensive issue lifecycle management, role-based access control, file attachment management, audit logging, and analytical dashboards — all without reliance on cloud infrastructure.

**Core value proposition:** Data sovereignty through local installation with optional team collaboration via shared SQLite database. Complete audit trail for compliance requirements.

---

## Technical Architecture

| Component | Technology |
|-----------|------------|
| Language | Python 3.13+ (compatible with 3.11+) |
| UI Framework | PySide6 (Qt6) |
| Database | SQLite (file-based, shareable via network folders) |
| Charts | QtCharts |
| Excel I/O | openpyxl |
| Authentication | bcrypt (password hashing) |
| Configuration | JSON file in %APPDATA% |
| Packaging | PyInstaller → single .exe |

**Why this stack:**
- SQLite is first-class in Python — no ORM gymnastics required
- Qt produces native-feeling, professional desktop UIs
- Single-language codebase — no frontend/backend split
- PyInstaller creates proven, reliable Windows executables
- Minimal dependency churn — boring and stable

**Database considerations:**
- Enable WAL (Write-Ahead Logging) mode for better concurrent access
- Suitable for teams under 10 concurrent users
- Database file can be placed on shared network folder for multi-user access
- Database path stored in `%APPDATA%\IssueRegister\config.json` (persists across sessions)

**File storage:**
- Attachments stored in `attachments/` folder adjacent to database file
- Portable: moving database folder includes all attachments

---

## Application Structure

The application comprises four primary views accessible through segmented navigation:

1. **Login Page** — Authentication and access control
2. **Issue Register** — Core data management interface
3. **Dashboard** — Analytics and visualisation
4. **Settings** — Configuration and user management

---

## 1. Login Page

### First Launch — Database Selection

On first launch (or when no valid database path is saved), the application displays a **Database Selection Dialog**:

| Element | Description |
|---------|-------------|
| Open Existing Database | QFileDialog to browse for existing .db file |
| Create New Database | QFileDialog to choose location for new database |
| Location display | Shows selected path with status indicator |
| Connect button | Proceeds to login after selection |

The selected path is saved to `%APPDATA%\IssueRegister\config.json` for future sessions.

### Authentication Components

| Element | Description |
|---------|-------------|
| Username field | QLineEdit for user identification |
| Password field | QLineEdit with echo mode set to Password |
| Login button | QPushButton, primary action |
| Forgot Password link | QLabel with link styling, initiates recovery |
| Change Database link | Opens database selection dialog |

### Password Recovery Workflow

Password recovery uses a master password system:

1. User clicks "Forgot Password"
2. Dialog prompts for master password
3. Successful entry grants temporary administrator privileges
4. User accesses Settings to reset required credentials

This approach eliminates dependency on email infrastructure while maintaining security.

### Force Password Change

When a user's account is flagged for password change:

1. User logs in with current credentials
2. Change Password dialog appears immediately (cannot be dismissed)
3. User must enter current password and choose new password
4. Only after successful change can user access the application

Administrators can flag any user for forced password change via Settings.

### Default Credentials

| Account | Username | Password |
|---------|----------|----------|
| Administrator | `admin` | `admin` |
| Master Password | — | `masterpass123` |

**Important:** Administrators should change default credentials immediately upon first login.

---

## 2. Issue Register

The Issue Register serves as the primary data management interface, providing comprehensive issue tracking from identification through closure.

### Data Model

| Field | Type | SQLite Type | Description |
|-------|------|-------------|-------------|
| id | Auto-generated | INTEGER PRIMARY KEY | Unique system-assigned identifier |
| title | Text | TEXT NOT NULL | Brief descriptive title for the issue |
| status | Enum | TEXT CHECK(...) | Draft, Open, In Progress, Remediated, Closed |
| summary_description | Text | TEXT | Concise overview of the issue |
| topic | Dropdown | TEXT | Categorical classification of the issue |
| identified_by | Dropdown | TEXT | Person who discovered/reported the issue |
| owner | Dropdown | TEXT | Person responsible for resolution |
| department | Dropdown | TEXT | Organisational unit associated with the issue |
| description | Long Text | TEXT | Detailed explanation of the issue |
| remediation_action | Long Text | TEXT | Planned or completed corrective actions |
| risk_description | Long Text | TEXT | Assessment of potential impact |
| risk_level | Enum | TEXT CHECK(...) | None, Low, Medium, High |
| identification_date | Date | DATE | Date issue was first identified |
| due_date | Date | DATE | Target date for resolution |
| follow_up_date | Date | DATE | Scheduled date for next review |
| updates | Long Text | TEXT | Chronological progress notes |
| closing_date | Date | DATE | Date issue was formally closed |
| supporting_docs | File paths | TEXT | JSON array of file paths |

### SQLite Schema

```sql
-- Issues table
CREATE TABLE issues (
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
    supporting_docs TEXT,              -- JSON array of filenames
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Users table
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT CHECK(role IN ('Administrator', 'Editor', 'Restricted', 'Viewer')) DEFAULT 'Viewer',
    departments TEXT,                   -- JSON array for department restrictions
    force_password_change INTEGER DEFAULT 0,  -- Flag to require password change on login
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Settings table
CREATE TABLE settings (
    key TEXT PRIMARY KEY,
    value TEXT
);

-- Audit log table
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT NOT NULL,
    action TEXT NOT NULL,               -- e.g., 'ISSUE_CREATED', 'USER_UPDATED'
    entity_type TEXT NOT NULL,          -- e.g., 'issue', 'user', 'settings'
    entity_id INTEGER,
    details TEXT,                       -- JSON with change details
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for common queries
CREATE INDEX idx_issues_status ON issues(status);
CREATE INDEX idx_issues_department ON issues(department);
CREATE INDEX idx_issues_due_date ON issues(due_date);
CREATE INDEX idx_issues_risk_level ON issues(risk_level);
CREATE INDEX idx_issues_owner ON issues(owner);
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_audit_log_timestamp ON audit_log(timestamp);
CREATE INDEX idx_audit_log_entity ON audit_log(entity_type, entity_id);
CREATE INDEX idx_audit_log_user ON audit_log(user_id);
```

### Register Table View

The register displays issues in a QTableView with the following visible columns:

- ID
- Title
- Status
- Topic
- Identified By
- Owner
- Risk Level
- Due Date

**Row interaction:** Double-clicking any row opens a detailed view displaying all fields.

### Issue Detail View

- QDialog or stacked widget displaying all fields
- Editable if user has appropriate permissions
- Save and Cancel buttons
- Cancel discards unsaved changes

### Filter System

A collapsible filter panel enables narrowing the displayed issues. The panel can be collapsed to a vertical strip showing "FILTERS" text to maximise table space.

| Filter | Widget Type |
|--------|-------------|
| Status | MultiSelectComboBox (checkboxes) |
| Identified By | MultiSelectComboBox |
| Owner | MultiSelectComboBox |
| Department | MultiSelectComboBox |
| Risk Level | MultiSelectComboBox |
| Identification Date | QDateEdit (from/to range) |
| Due Date | QDateEdit (from/to range) |

**Filter logic:**
- Within a filter: OR logic (selecting "Open" and "Closed" shows both)
- Between filters: AND logic (Department="IT" AND Status="Open")
- Only issues matching all filter criteria appear

### Issue Creation

- New issues created via QPushButton with "+" icon
- Can add directly in register or through full detail view
- Common fields (Identified By, Department, Owner) use QComboBox
- Dropdowns populated from existing values via DISTINCT queries
- Editable combobox allows typing new entries

### Export Functionality

- Export button (QPushButton) in register header
- Uses openpyxl to generate XLSX file
- QFileDialog for save location
- Exports all issues user has permission to view
- Respects active filters

### File Attachments

Each issue can have multiple supporting documents attached. Files are managed through the Issue Detail View.

**Storage structure:**
```
database_folder/
├── issue_register.db
└── attachments/
    ├── 1/                    # Files for issue #1
    │   ├── report.pdf
    │   └── screenshot.png
    ├── 2/                    # Files for issue #2
    ├── _deleted/             # Soft-deleted files (recoverable)
    │   └── 1/
    │       └── old_doc.pdf
    └── _staging/             # Temporary files for new issues
        └── {uuid}/
```

**File operations:**

| Action | Behaviour |
|--------|-----------|
| Add File | Copies file to `attachments/{issue_id}/`. Handles duplicates with numbering (e.g., `report (2).pdf`) |
| Open File | Copies to user's Downloads folder and opens with system default application |
| Remove File | Moves to `_deleted/{issue_id}/` (soft delete, not permanent) |

**New issue workflow:**
1. Files attached before saving go to `_staging/{uuid}/`
2. On issue save, files migrate to `attachments/{issue_id}/`
3. On cancel, staging folder is cleaned up

**UI components:**
- QListWidget showing attached files with icons
- Add button opens QFileDialog
- Open button copies to Downloads and launches
- Remove button (with confirmation) performs soft delete

---

## 3. Dashboard

The dashboard provides real-time analytics based on user access permissions. All visualisations update automatically when underlying data changes.

**Features:**
- Independent collapsible filter panel (same filters as Issue Register)
- Filters affect all KPI cards and charts simultaneously
- Real-time updates when data changes

### KPI Cards (Top Row)

Use QFrame with QVBoxLayout for each card.

| Metric | Definition | SQL |
|--------|------------|-----|
| Total Issues | Count of all issues in scope | `SELECT COUNT(*) FROM issues` |
| Active Issues | Open + In Progress + Remediated | `SELECT COUNT(*) FROM issues WHERE status IN ('Open', 'In Progress', 'Remediated')` |
| High Priority Open | Open issues with High risk | `SELECT COUNT(*) FROM issues WHERE status = 'Open' AND risk_level = 'High'` |
| Overdue | Past due date, not closed | `SELECT COUNT(*) FROM issues WHERE due_date < DATE('now') AND status != 'Closed'` |
| Resolution Rate | Closed / Total × 100 | Computed from above |

### Distribution Charts (Pie/Donut)

Use QtCharts QPieSeries or Matplotlib:

1. **Status Distribution** — Breakdown by Draft, Open, In Progress, Remediated, Closed
2. **Risk Level Distribution** — Breakdown by None, Low, Medium, High

### Progress Bars

Use QProgressBar widgets:

| Indicator | Description |
|-----------|-------------|
| Overall Resolution Rate | Closed vs total issues |
| In Progress | Issues currently being worked on |
| Awaiting Action (Open) | Issues not yet started |
| Draft Issues | Issues not yet submitted |

### Analytical Charts (Stacked Bar)

Use QtCharts QStackedBarSeries or Matplotlib:

1. **Issues by Department** — Horizontal bars per department, segmented by status
2. **Issues by Topic** — Horizontal bars per topic, segmented by status

---

## 4. Settings

### Database Configuration

Database path display with buttons for switching databases:

| Element | Description |
|---------|-------------|
| Current Database | Read-only QLineEdit showing current path |
| Status indicator | Shows "Connected" with green text |
| Open Existing Database | Browse for different .db file |
| Create New Database | Create new database at chosen location |

When switching databases:
- Application reconnects to selected database
- User must re-authenticate if authentication is enabled
- New path is saved to config file for future sessions

### Authentication Management

By default, all users have administrator access and authentication is disabled.

**Enabling authentication:**

1. Administrator enables QCheckBox "Enable Authentication"
2. Default credentials become active (admin/admin)
3. Only administrators can create and manage user accounts
4. Users connecting to shared database must log in

### User Roles and Permissions

| Role | Permissions |
|------|-------------|
| **Administrator** | Full system access: user management, database configuration, backup import, bulk import, all issue operations, audit log export |
| **Editor** | Editing access to issues (can be restricted by department). Can create, modify, and close issues. Can export audit log. Separate View and Edit department restrictions |
| **Restricted** | Limited to assigned department(s). Can create draft issues. Can edit: Status (Open/In Progress/Remediated only), Updates, Supporting Documentation, Follow-up Date. Cannot modify Closed or Draft issues |
| **Viewer** | Read-only access. Can view issues within assigned department(s) or all issues if granted full access. Cannot create or modify issues |

**Department restrictions:**
- **Administrator:** No restrictions (full access)
- **Editor:** Separate "View Departments" and "Edit Departments" lists. Empty list = all departments
- **Restricted/Viewer:** Single department list applies to both viewing and editing

**User table display:** Shows columns for Username, Role, Editor Rights, and Viewer Rights for easy access review.

### Status Transition Logic

The Restricted role implements a controlled workflow:

```
Draft ──[Editor/Admin]──> Open ──[Any with access]──> In Progress ──> Remediated ──[Editor/Admin]──> Closed
```

- New issues from Restricted users begin in Draft status
- Draft → Open requires Editor or Administrator
- Restricted users can transition between Open, In Progress, and Remediated
- Remediated → Closed requires Editor or Administrator (review gate)

### User Management (Administrator only)

| Action | Description |
|--------|-------------|
| Add User | Create new user with username, password, role, and department restrictions |
| Edit User | Modify user details including role and departments |
| Delete User | Remove user account (with confirmation) |
| Force Password Change | Checkbox to require user to change password on next login |
| Search | Filter user list by username |

### Data Management

#### Backup Export
- All users can export backup of issues they have permission to view
- Uses openpyxl for Excel format

#### Export Users (Administrator only)
- Exports user list to Excel file
- Includes: Username, Role, Departments

#### Export Audit Log (Administrator and Editor)
- Exports complete audit trail to Excel
- Includes: Timestamp, User, Action, Entity Type, Entity ID, Details

#### Backup Import (Administrator only)
- Import backup files to restore database
- **Warning:** Overwrites existing data
- Confirmation dialog required

#### Bulk Import (Administrator only)

- Import issues from Excel files via openpyxl
- Downloadable template with pre-filled example row
- Issue IDs auto-generated (import file IDs ignored)
- Invalid field values result in empty fields (no import errors)
- QMessageBox displays success count and fields requiring correction

### Audit Logging

All significant actions are automatically logged to the `audit_log` table:

| Action Type | What's Logged |
|-------------|---------------|
| Issue Created | New issue details |
| Issue Updated | Changed fields |
| Issue Deleted | Deleted issue info |
| Status Changed | Old and new status |
| User Created | New user details |
| User Updated | Changed user info |
| User Deleted | Deleted user info |
| Settings Changed | Configuration changes |
| Login/Logout | Authentication events |

Audit logs cannot be modified or deleted. Export is the only way to access historical data.

---

## UI/UX Design

### Design Philosophy

| Principle | Description |
|-----------|-------------|
| Professional & Serious | Financial compliance tool, not playful |
| Clean & Uncluttered | Generous spacing, breathing room |
| Sophisticated Neutrality | Muted tones, no vibrant colours |
| Desktop-First | Optimised for professional workstations |
| Light Mode Only | No dark theme (regulatory clarity focus) |

### Colour Palette

#### Primary Colours

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Primary (Ink Blue) | `#2D3E50` | 45, 62, 80 | Headers, buttons, key actions, icons |
| Primary Foreground | `#FFFFFF` | 255, 255, 255 | Text on primary colour elements |

#### Secondary/Accent

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Secondary (Warm Grey-Beige) | `#E6E2DA` | 230, 226, 218 | Secondary actions, subtle highlights |

#### Backgrounds

| Name | Hex | RGB | Usage |
|------|-----|-----|-------|
| Background | `#F9FAFB` | 249, 250, 251 | Main application background |
| Card/Panel | `#FFFFFF` | 255, 255, 255 | Cards, dialogs, elevated surfaces |
| Muted | `#F3F4F6` | 243, 244, 246 | Table row stripes, input backgrounds |
| Border | `#E5E7EB` | 229, 231, 235 | Borders, dividers |

### Qt Stylesheet

```css
/* Main Window */
QMainWindow {
    background-color: #F9FAFB;
}

/* Primary Buttons */
QPushButton[primary="true"] {
    background-color: #2D3E50;
    color: #FFFFFF;
    border: none;
    padding: 8px 16px;
    border-radius: 6px;
    font-weight: bold;
}

QPushButton[primary="true"]:hover {
    background-color: #3D4E60;
}

/* Secondary Buttons */
QPushButton {
    background-color: #E6E2DA;
    color: #2D3E50;
    border: 1px solid #D1CCC3;
    padding: 8px 16px;
    border-radius: 6px;
}

/* Danger Buttons */
QPushButton[danger="true"] {
    background-color: #B91C1C;
    color: #FFFFFF;
    border: none;
}

/* Input Fields */
QLineEdit, QTextEdit, QComboBox, QDateEdit {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    padding: 6px 10px;
    border-radius: 6px;
}

QLineEdit:focus, QTextEdit:focus, QComboBox:focus {
    border: 1px solid #2D3E50;
}

/* Table */
QTableView {
    background-color: #FFFFFF;
    alternate-background-color: #F3F4F6;
    border: 1px solid #E5E7EB;
    gridline-color: #E5E7EB;
}

QTableView::item:selected {
    background-color: #2D3E50;
    color: #FFFFFF;
}

QHeaderView::section {
    background-color: #2D3E50;
    color: #FFFFFF;
    padding: 8px;
    border: none;
    font-weight: bold;
}

/* Cards/Panels */
QFrame[card="true"] {
    background-color: #FFFFFF;
    border: 1px solid #E5E7EB;
    border-radius: 8px;
}

/* Labels */
QLabel[heading="true"] {
    color: #2D3E50;
    font-size: 16px;
    font-weight: bold;
}

/* Progress Bars */
QProgressBar {
    background-color: #F3F4F6;
    border: none;
    border-radius: 4px;
    height: 8px;
}

QProgressBar::chunk {
    background-color: #2D3E50;
    border-radius: 4px;
}
```

---

## Deployment and Distribution

### Package Format

Single Windows executable (.exe) built with PyInstaller, bundling Python runtime and all dependencies.

### Build Command

Using the spec file (recommended):
```bash
pyinstaller IssueRegister.spec --clean
```

Or using build script:
```bash
build.bat
```

The spec file includes all necessary hidden imports for PySide6, bcrypt, openpyxl, and ctypes (for file attachment features).

### Deployment Workflow (Team Environment)

1. **Administrator Setup:** Run application, select/create database on shared network folder
2. **Enable Authentication:** Activate user authentication in Settings
3. **Create User Accounts:** Establish accounts with appropriate role assignments
4. **Distribute Application:** Share .exe with team members (no installation required)
5. **User First Launch:** Application prompts for database selection
6. **Connect to Shared Database:** Users browse to shared network database location
7. **Authenticate:** Users log in with provided credentials

**Note:** Each user's database path is saved locally in `%APPDATA%\IssueRegister\config.json`.

### Standalone Operation

For individual users, the application functions without network requirements. On first launch, user selects where to create the local database. Complete functionality available offline.

### File Attachments in Shared Environment

When using a shared database on a network folder:
- The `attachments/` folder is created alongside the database
- All users access the same attachment files
- Ensure all users have read/write permissions to the folder

---

## Appendix

### Status Definitions

| Status | Definition |
|--------|------------|
| **Draft** | Issue created but not yet submitted. Used when Restricted users pre-fill issues pending Editor/Administrator review |
| **Open** | Issue formally submitted and acknowledged. Work has not commenced. Awaiting assignment or prioritisation |
| **In Progress** | Active remediation work underway. Assigned owner implementing corrective actions |
| **Remediated** | Corrective actions completed. Awaits review by Editor/Administrator before formal closure |
| **Closed** | Issue fully resolved and verified. No further action required. Closing date recorded for audit |

### Risk Level Definitions

| Level | Criteria |
|-------|----------|
| **None** | No identified risk impact |
| **Low** | Minor impact, easily mitigated |
| **Medium** | Moderate impact, requires attention |
| **High** | Significant impact, priority resolution required |

---

## Project Structure

```
issue-register/
├── src/
│   ├── __init__.py
│   ├── main.py                  # Application entry point
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py        # SQLite connection management (singleton)
│   │   ├── migrations.py        # Schema creation and migrations
│   │   ├── models.py            # Data classes for Issue, User, enums
│   │   └── queries.py           # SQL query functions
│   ├── ui/
│   │   ├── __init__.py
│   │   ├── main_window.py       # QMainWindow with navigation
│   │   ├── login.py             # Login + DatabaseSelectionDialog
│   │   ├── register.py          # Issue register view
│   │   ├── dashboard.py         # Dashboard view
│   │   ├── settings.py          # Settings + ChangePasswordDialog + UserDialog
│   │   ├── issue_dialog.py      # Issue detail/edit dialog
│   │   ├── bulk_delete_dialog.py # Bulk delete confirmation
│   │   └── widgets/             # Custom reusable widgets
│   │       ├── __init__.py
│   │       ├── kpi_card.py      # KPI card component
│   │       ├── filter_panel.py  # Collapsible filter panel + MultiSelectComboBox
│   │       └── charts.py        # QtCharts wrappers
│   ├── services/
│   │   ├── __init__.py
│   │   ├── auth.py              # Authentication logic
│   │   ├── audit.py             # Audit logging service
│   │   ├── config.py            # App configuration (database path)
│   │   ├── export.py            # Excel export/import
│   │   ├── file_service.py      # File attachment management
│   │   ├── issue_service.py     # Issue CRUD and business logic
│   │   └── permissions.py       # Role-based access control
│   └── resources/
│       └── styles.qss           # Qt stylesheet
├── tests/
│   ├── test_auth.py
│   ├── test_audit.py
│   ├── test_database.py
│   ├── test_export.py
│   ├── test_issue_service.py
│   └── test_permissions.py
├── requirements.txt
├── requirements-dev.txt
├── IssueRegister.spec           # PyInstaller spec file
├── build.bat                    # Build script
├── SPECIFICATION.md
├── CLAUDE.md                    # Development guidelines
├── BUILD.md                     # Build instructions
├── FIXES.md                     # Enhancement history
└── README.md
```

### Dependencies (requirements.txt)

```
PySide6>=6.8.0
bcrypt>=4.1.0
openpyxl>=3.1.0
```

### Development Dependencies (requirements-dev.txt)

```
pytest>=8.0.0
pytest-qt>=4.3.0
pytest-cov>=4.1.0
pyinstaller>=6.0.0
```

### Minimum System Requirements

- Windows 10 or later
- 4 GB RAM
- 100 MB disk space
- Network access (only for shared database mode)

---

*End of Specification*
