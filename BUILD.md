# Building Issue Register

This guide explains how to build Issue Register as a standalone Windows executable.

## Prerequisites

- **Python 3.11+** — [Download from python.org](https://www.python.org/downloads/)
- **Windows 10/11** — The build process targets Windows

## Quick Build

```bash
# From the project root directory
build.bat
```

Output: `dist\IssueRegister.exe`

## Step-by-Step Build

### 1. Set Up Environment

```bash
# Create virtual environment
python -m venv venv

# Activate it
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install all dependencies including PyInstaller
pip install -r requirements-dev.txt
```

### 3. Build the Executable

**Option A: Using the spec file (recommended)**

```bash
pyinstaller IssueRegister.spec --clean
```

**Option B: Manual PyInstaller command**

```bash
pyinstaller --onefile ^
    --windowed ^
    --name "IssueRegister" ^
    --add-data "src/resources;src/resources" ^
    --hidden-import "PySide6.QtCharts" ^
    --hidden-import "bcrypt" ^
    --hidden-import "openpyxl" ^
    --hidden-import "ctypes" ^
    --hidden-import "ctypes.wintypes" ^
    src/main.py
```

### 4. Locate the Executable

The built application is at: `dist\IssueRegister.exe`

## Adding a Custom Icon

1. Create or obtain an `.ico` file (Windows icon format)
2. Place it in the project root
3. Build with the `--icon` flag:

```bash
pyinstaller IssueRegister.spec --clean
# Or add to manual command:
pyinstaller --onefile --windowed --icon=app.ico --name "IssueRegister" src/main.py
```

## What's Included in the Build

The `IssueRegister.spec` file configures PyInstaller to include:

| Component | Purpose |
|-----------|---------|
| `src/resources/` | Stylesheets and icons |
| PySide6.QtCharts | Dashboard charts |
| bcrypt | Password hashing |
| openpyxl | Excel import/export |
| ctypes | File attachment handling |

## Troubleshooting

### Import Errors During Build

Ensure all dependencies are installed:

```bash
pip install -r requirements-dev.txt
```

### Antivirus Interference

Some antivirus software may flag or block PyInstaller. Solutions:

1. Add the project folder to antivirus exclusions
2. Temporarily disable real-time protection during build
3. Submit a false positive report to your antivirus vendor

### Application Won't Start

Run from command line to see error messages:

```bash
dist\IssueRegister.exe
```

Common issues:
- Missing resources — ensure `src/resources` is included
- Missing Qt plugins — add hidden imports for PySide6 modules

### Missing Qt Plugins

Add these hidden imports if you see Qt plugin errors:

```bash
--hidden-import "PySide6.QtCore"
--hidden-import "PySide6.QtWidgets"
--hidden-import "PySide6.QtGui"
```

## Distribution

The built executable is self-contained:

- **No Python installation required** on target machines
- **No dependencies to install** — everything is bundled
- **Single file** — easy to distribute via file share, email, etc.

### First Run Behavior

When users first run the application:

1. Application prompts for database location
2. User can create a new database or open an existing one
3. Path is saved to `%APPDATA%\IssueRegister\config.json`

### File Attachments Structure

When users attach files to issues, they're stored alongside the database:

```
database_folder/
├── issue_register.db      # The database
└── attachments/           # File attachments
    ├── 1/                     # Files for issue #1
    ├── 2/                     # Files for issue #2
    ├── _deleted/              # Soft-deleted files
    └── _staging/              # Temporary files for new issues
```

### Shared Network Deployment

For multi-user setups:

1. Place the database on a shared network folder
2. Distribute the `.exe` to team members
3. Each user points to the same database location
4. Ensure all users have read/write access to the folder

## Development vs Production

| Mode | How to Run |
|------|------------|
| Development | `python -m src.main` |
| Production | `dist\IssueRegister.exe` |

## Rebuilding After Changes

After making code changes:

```bash
# Clean and rebuild
pyinstaller IssueRegister.spec --clean
```

The `--clean` flag ensures a fresh build without cached artifacts.

## CI/CD Integration

For automated builds (GitHub Actions, etc.):

```yaml
- name: Build executable
  run: |
    pip install -r requirements-dev.txt
    pyinstaller IssueRegister.spec --clean

- name: Upload artifact
  uses: actions/upload-artifact@v4
  with:
    name: IssueRegister
    path: dist/IssueRegister.exe
```
