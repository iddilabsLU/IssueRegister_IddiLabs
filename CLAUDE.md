# Issue Register - Development Guidelines

## Project Overview
Desktop application for tracking organizational issues with role-based access control. Supports file attachments, configurable database location, and multi-user access via shared network folders.

## Tech Stack
- **Language:** Python 3.13+ (compatible with 3.11+)
- **UI Framework:** PySide6 (Qt6)
- **Database:** SQLite (WAL mode for concurrency)
- **Charts:** QtCharts
- **Auth:** bcrypt for password hashing
- **Excel I/O:** openpyxl
- **Testing:** pytest + pytest-qt
- **Packaging:** PyInstaller

## Project Structure
```
src/
├── database/      # SQLite connection, models, queries, migrations
├── services/      # Business logic
│   ├── auth.py        # Authentication service
│   ├── audit.py       # Audit logging service
│   ├── config.py      # App configuration (database path in AppData)
│   ├── export.py      # Excel export/import
│   ├── file_service.py # File attachment management
│   ├── issue_service.py # Issue CRUD and business logic
│   └── permissions.py  # Role-based access control
├── ui/            # PySide6 views and widgets
│   ├── login.py       # Login + DatabaseSelectionDialog
│   ├── main_window.py # Main app window
│   ├── register.py    # Issue list view
│   ├── dashboard.py   # KPIs and charts
│   ├── settings.py    # Settings + User management
│   ├── issue_dialog.py # Issue detail dialog
│   └── widgets/       # Reusable widgets (charts, filters, kpi_card)
└── resources/     # Stylesheets and icons
tests/             # pytest test files
```

## Development Setup
```bash
# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run application
python -m src.main
```

## Key Patterns

### Database Access
- Use `DatabaseConnection.get_instance()` for singleton connection
- All queries go through `src/database/queries.py`
- Always use parameterized queries (no SQL injection)
- Migrations in `src/database/migrations.py` handle schema updates

### Configuration
- Database path stored in `%APPDATA%\IssueRegister\config.json`
- Use `src/services/config.py` for app-level config outside the database
- First launch shows `DatabaseSelectionDialog` for database location

### File Attachments
- Use `get_file_service()` singleton from `src/services/file_service.py`
- Files stored in `attachments/` folder next to database
- Deleted files moved to `attachments/_deleted/` (soft delete)
- New issues use staging folder until saved: `attachments/_staging/{uuid}/`

### Permissions
- Check permissions via `src/services/permissions.py`
- Four roles: Administrator, Editor, Restricted, Viewer
- Status transitions have permission gates
- Editor role supports separate view/edit department restrictions

### Force Password Change
- Users can be flagged to require password change on next login
- `force_password_change` column in users table
- `ChangePasswordDialog(forced=True)` blocks until password changed

### UI Components
- Custom widgets in `src/ui/widgets/`
- Follow specification color palette (#2D3E50 primary)
- Use styles.qss for consistent styling

### UI Styling Conventions
- **Border radius:** 6px for buttons/inputs, 8px for cards
- **Secondary buttons:** Include border (1px solid #D1CCC3)
- **Danger buttons:** Use #B91C1C background
- **Property-based styling:** Use Qt properties like `primary="true"`, `danger="true"`, `card="true"`
- **Status badges:** Use `status="Open"` property for automatic coloring
- **Risk badges:** Use `risk="High"` property for automatic coloring

## Testing
- Database tests use temporary SQLite files
- UI tests use pytest-qt fixtures
- Target: >80% code coverage

## Build
```bash
# Using spec file (recommended)
pyinstaller IssueRegister.spec --clean

# Or use build script
build.bat
```

The spec file (`IssueRegister.spec`) includes all necessary hidden imports and data files.

## Default Credentials
- Username: `admin`
- Password: `admin`
- Master password: `masterpass123`

## Status Workflow
```
Draft -> Open -> In Progress -> Remediated -> Closed
```
- Restricted users cannot: Draft->Open, Remediated->Closed
- Only Admin/Editor can close issues

## Key Features

### Database Management
- Database selection dialog on first launch
- Change database from Settings or Login screen
- Config stored in `%APPDATA%\IssueRegister\`

### File Attachments
- Attach supporting documents to issues
- Files copied to `attachments/{issue_id}/` next to database
- Open files (copies to Downloads, opens with system app)
- Soft delete moves files to `_deleted/` folder

### Dashboard
- KPI cards with issue metrics
- Charts: status distribution, risk levels, department breakdown
- Collapsible filter panel

### Audit Logging
- All actions logged to `audit_log` table
- Export audit log to Excel (Admin/Editor only)

### User Management (Admin only)
- Create/edit/delete users
- Force password change on next login
- Export user list to Excel
