# Issue Register

An open-source desktop application for tracking issues across organisational departments from identification through closure.

## Features

- **Issue Tracking**: Complete lifecycle management from Draft to Closed
- **Role-Based Access Control**: Administrator, Editor, Restricted, and Viewer roles
- **File Attachments**: Attach supporting documents to issues
- **Dashboard Analytics**: KPIs, charts, and progress tracking
- **Excel Integration**: Import/export issues to Excel
- **Audit Logging**: Track all changes with exportable audit trail
- **Local Database**: SQLite for data sovereignty
- **Flexible Database Location**: Choose where to store your database
- **Shared Access**: Optional multi-user via network folder

## Installation

### Prerequisites

- Python 3.11 or higher
- Windows 10 or later

### Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd issueregister_iddilabs
   ```

2. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Run the application:
   ```bash
   python -m src.main
   ```

### Build Executable

To create a standalone Windows executable:

```bash
build.bat
```

The executable will be created at `dist/IssueRegister.exe`.

## Default Credentials

When authentication is enabled:

| Username | Password | Role |
|----------|----------|------|
| admin | admin | Administrator |
| editor1 | editor1 | Editor |
| restricted1 | restricted1 | Restricted |
| viewer1 | viewer1 | Viewer |

**Master Password**: `masterpass123` (for password recovery)

> **Important**: Change default credentials immediately in production!

## User Roles

| Role | Permissions |
|------|-------------|
| **Administrator** | Full access: user management, database config, all issues |
| **Editor** | Edit all issues, can close issues |
| **Restricted** | Limited to assigned departments, cannot close issues |
| **Viewer** | Read-only access |

## Status Workflow

```
Draft → Open → In Progress → Remediated → Closed
```

- Restricted users create issues in Draft
- Editor/Admin required to transition Draft→Open and Remediated→Closed

## Development

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Project Structure

```
src/
├── database/       # SQLite connection, models, queries
├── services/       # Business logic (auth, permissions, export)
├── ui/             # PySide6 views and widgets
└── resources/      # Stylesheets and icons
tests/              # pytest test files
```

## License

Open Source - See LICENSE file for details.

## Credits

Developed by IDDI Labs.
