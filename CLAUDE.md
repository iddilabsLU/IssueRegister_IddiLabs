# Issue Register — Development Guidelines

> This file provides context for AI coding assistants (Claude, GitHub Copilot, Cursor, etc.) and developers working on this project.

## Project Overview

Desktop application for tracking organizational issues with role-based access control. Supports file attachments, configurable database location, and multi-user access via shared network folders.

**Target users:** Organizations needing local data sovereignty for issue tracking (regulated industries, compliance-focused teams).

## Tech Stack

| Component | Technology | Notes |
|-----------|------------|-------|
| Language | Python 3.11+ | Developed with 3.13, compatible with 3.11+ |
| UI Framework | PySide6 (Qt6) | Native desktop look and feel |
| Database | SQLite | WAL mode for concurrent access |
| Charts | QtCharts | Integrated with PySide6 |
| Auth | bcrypt | Password hashing |
| Excel I/O | openpyxl | Import/export functionality |
| Testing | pytest + pytest-qt | UI and unit tests |
| Packaging | PyInstaller | Single .exe distribution |

## Project Structure

```
src/
├── database/          # Database layer
│   ├── connection.py      # SQLite singleton connection
│   ├── migrations.py      # Schema creation and updates
│   ├── models.py          # Data classes and enums
│   └── queries.py         # All SQL queries (parameterized)
├── services/          # Business logic layer
│   ├── auth.py            # Authentication service
│   ├── audit.py           # Audit logging service
│   ├── config.py          # App configuration (paths, settings)
│   ├── export.py          # Excel export/import
│   ├── file_service.py    # File attachment management
│   ├── issue_service.py   # Issue CRUD and business logic
│   └── permissions.py     # Role-based access control
├── ui/                # Presentation layer
│   ├── login.py           # Login + DatabaseSelectionDialog
│   ├── main_window.py     # Main app window with navigation
│   ├── register.py        # Issue list view (table)
│   ├── dashboard.py       # KPIs and charts
│   ├── settings.py        # Settings + User management
│   ├── issue_dialog.py    # Issue detail/edit dialog
│   └── widgets/           # Reusable UI components
│       ├── charts.py          # QtCharts wrappers
│       ├── filter_panel.py    # Collapsible filters + MultiSelectComboBox
│       └── kpi_card.py        # Dashboard KPI cards
└── resources/         # Static assets
    └── styles.qss         # Qt stylesheet
tests/                 # Test suite (pytest)
```

## Development Setup

```bash
# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate          # Windows
source venv/bin/activate       # Linux/Mac

# Install all dependencies (including dev tools)
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run application
python -m src.main
```

## Key Architecture Patterns

### Database Access

- **Singleton connection:** Use `DatabaseConnection.get_instance()`
- **Centralized queries:** All SQL in `src/database/queries.py`
- **Parameterized queries only:** Never concatenate user input into SQL
- **Migrations:** Schema updates handled in `src/database/migrations.py`

```python
# Good
from src.database.connection import DatabaseConnection
conn = DatabaseConnection.get_instance()

# Bad - don't create direct connections
import sqlite3
conn = sqlite3.connect(path)  # Don't do this
```

### Configuration

- **Database path:** Stored in `%APPDATA%\IssueRegister\config.json` (Windows)
- **App-level config:** Use `src/services/config.py`
- **First launch:** Shows `DatabaseSelectionDialog` to choose location

### File Attachments

- **Singleton service:** Use `get_file_service()` from `src/services/file_service.py`
- **Storage location:** `attachments/` folder adjacent to database
- **Soft delete:** Deleted files move to `attachments/_deleted/`
- **New issues:** Files staged in `attachments/_staging/{uuid}/` until saved

```python
from src.services.file_service import get_file_service

file_service = get_file_service()
file_service.add_file(issue_id, source_path)
file_service.open_file(issue_id, filename)  # Opens in default app
file_service.remove_file(issue_id, filename)  # Soft delete
```

### Permissions System

- **Check via:** `src/services/permissions.py`
- **Four roles:** Administrator, Editor, Restricted, Viewer
- **Status transitions:** Have permission gates (see workflow below)
- **Department restrictions:** Editor has separate view/edit lists

```python
from src.services.permissions import can_edit_issue, can_transition_status

if can_edit_issue(current_user, issue):
    # Allow editing
```

### Force Password Change

- **Flag:** `force_password_change` column in users table
- **UI:** `ChangePasswordDialog(forced=True)` blocks until changed
- **Admin action:** Can flag any user in Settings

## Status Workflow

```
Draft ──[Editor/Admin]──> Open ──[Any]──> In Progress ──[Any]──> Remediated ──[Editor/Admin]──> Closed
```

- **Restricted users:** Create in Draft, cannot do Draft→Open or Remediated→Closed
- **Editor/Admin:** Can perform all transitions

## UI Styling Conventions

The application uses a consistent visual language defined in `src/resources/styles.qss`.

### Design Tokens

| Token | Value | Usage |
|-------|-------|-------|
| Primary color | `#2D3E50` | Headers, primary buttons, icons |
| Border radius (buttons/inputs) | `6px` | Standard interactive elements |
| Border radius (cards) | `8px` | Card containers |
| Secondary button border | `1px solid #D1CCC3` | Non-primary actions |
| Danger button | `#B91C1C` | Destructive actions |

### Property-Based Styling

Use Qt properties to apply styles:

```python
# Primary button
button.setProperty("primary", True)

# Danger button
button.setProperty("danger", True)

# Card container
frame.setProperty("card", True)

# Status badge
label.setProperty("status", "Open")  # Auto-colors based on status

# Risk badge
label.setProperty("risk", "High")  # Auto-colors based on risk level
```

## Testing Guidelines

- **Database tests:** Use temporary SQLite files (pytest fixtures handle cleanup)
- **UI tests:** Use `pytest-qt` fixtures for Qt event loop
- **Coverage target:** >80%

```bash
# Run with coverage report
pytest tests/ -v --cov=src --cov-report=term-missing
```

## Build Process

```bash
# Using spec file (recommended)
pyinstaller IssueRegister.spec --clean

# Or using build script
build.bat
```

The spec file includes all hidden imports (PySide6, bcrypt, openpyxl, ctypes).

Output: `dist/IssueRegister.exe`

## Default Credentials

| Account | Value |
|---------|-------|
| Username | `admin` |
| Password | `admin` |
| Master password | `masterpass123` |

> ⚠️ Change these immediately in production deployments.

## Common Tasks

### Adding a New Database Field

1. Add column to schema in `migrations.py`
2. Update `models.py` dataclass
3. Add to `queries.py` (INSERT, UPDATE, SELECT)
4. Update UI in `issue_dialog.py`
5. Add to export/import in `export.py`
6. Write tests

### Adding a New Permission Check

1. Add check function in `permissions.py`
2. Call from relevant UI/service code
3. Write tests for all roles

### Adding a New Chart

1. Create chart widget in `src/ui/widgets/charts.py`
2. Add to dashboard layout in `dashboard.py`
3. Connect to filter panel for interactivity
