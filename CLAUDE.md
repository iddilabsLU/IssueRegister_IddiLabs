# Issue Register - Development Guidelines

## Project Overview
Desktop application for tracking organizational issues with role-based access control.

## Tech Stack
- **Language:** Python 3.11+
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
├── database/     # SQLite connection, models, queries
├── services/     # Business logic (auth, permissions, export)
├── ui/           # PySide6 views and widgets
└── resources/    # Stylesheets and icons
tests/            # pytest test files
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

### Permissions
- Check permissions via `src/services/permissions.py`
- Four roles: Administrator, Editor, Restricted, Viewer
- Status transitions have permission gates

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
pyinstaller --onefile --windowed --name "IssueRegister" --icon=src/resources/icons/app_icon.ico src/main.py
```

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
