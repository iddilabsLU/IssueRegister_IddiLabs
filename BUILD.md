# Building Issue Register

This document describes how to build the Issue Register application as a standalone Windows executable.

## Prerequisites

- **Python 3.11+** - Download from [python.org](https://www.python.org/downloads/)
- **Windows 10/11** - The build script is designed for Windows

## Quick Build

1. Open a command prompt in the project directory
2. Run the build script:

```batch
build.bat
```

The executable will be created at `dist\IssueRegister.exe`.

## Manual Build Steps

If you prefer to build manually or encounter issues:

### 1. Create Virtual Environment

```batch
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```batch
pip install -r requirements-dev.txt
pip install pyinstaller
```

### 3. Run PyInstaller

Using the spec file (recommended):
```batch
pyinstaller IssueRegister.spec --clean
```

Or manually:
```batch
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

The `IssueRegister.spec` file is pre-configured with all necessary hidden imports for file attachments and other features.

### 4. Find the Executable

The built application will be at: `dist\IssueRegister.exe`

## Adding an Application Icon

To add a custom icon to the executable:

1. Place your icon file (must be `.ico` format) in the project
2. Add the `--icon` flag to the PyInstaller command:

```batch
pyinstaller --onefile --windowed --name "IssueRegister" --icon=myicon.ico src/main.py
```

## Troubleshooting

### Build Fails with Import Errors

Make sure all dependencies are installed:

```batch
pip install -r requirements-dev.txt
```

### Antivirus Blocks the Build

Some antivirus software may block PyInstaller. Solutions:
- Add the project folder to antivirus exclusions
- Temporarily disable real-time protection during build

### Application Won't Start

1. Run from command line to see error messages:
   ```batch
   dist\IssueRegister.exe
   ```
2. Check that `src/resources` folder is included in the build

### Missing Qt Plugins

If you see Qt plugin errors, add these hidden imports:

```batch
--hidden-import "PySide6.QtCore"
--hidden-import "PySide6.QtWidgets"
--hidden-import "PySide6.QtGui"
```

## Distribution

The built executable (`dist\IssueRegister.exe`) is self-contained and can be distributed to users without requiring Python installation.

On first run, the application will prompt the user to select or create a database location. The chosen path is saved in `%APPDATA%\IssueRegister\config.json`.

### File Attachments

When users attach files to issues, the files are copied to an `attachments` folder next to the database:
```
database_folder/
├── issue_register.db
└── attachments/
    ├── 1/           # Files for issue #1
    ├── 2/           # Files for issue #2
    └── _deleted/    # Soft-deleted files
```

## Development vs Production

- **Development**: Run with `python -m src.main`
- **Production**: Use the built executable

## Updating After Code Changes

After making code changes, re-run `build.bat` to create a new executable with the updates.
