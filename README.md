# Issue Register

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-green.svg)](https://www.python.org/downloads/)
[![PySide6](https://img.shields.io/badge/UI-PySide6%20(Qt6)-41CD52.svg)](https://doc.qt.io/qtforpython/)

An open-source desktop application for tracking issues across organisational departments from identification through closure. Built with Python and Qt for a native Windows experience.

<!-- Screenshots: Add application screenshots to docs/screenshots/ and update this section -->
<!-- ![Issue Register](docs/screenshots/main.png) -->

## Features

- **Issue Lifecycle Management** — Track issues from Draft → Open → In Progress → Remediated → Closed
- **Role-Based Access Control** — Administrator, Editor, Restricted, and Viewer roles with department restrictions
- **File Attachments** — Attach supporting documents to any issue
- **Dashboard Analytics** — KPIs, charts, and progress tracking at a glance
- **Excel Integration** — Import/export issues and audit logs to Excel
- **Audit Trail** — Complete logging of all changes for compliance
- **Local-First** — SQLite database for data sovereignty and privacy
- **Flexible Deployment** — Single-user or multi-user via shared network folder
- **Zero Installation** — Single `.exe` file, no dependencies required

## Quick Start

### For Users

**Download** the latest `IssueRegister.exe` from the [Releases](../../releases) page — no installation required.

On first launch, the application will prompt you to select or create a database location.

### Default Credentials

| Username | Password | Role |
|----------|----------|------|
| admin | admin | Administrator |

**Master Password** (for recovery): `masterpass123`

> ⚠️ **Important**: Change default credentials immediately in production!

## For Developers

### Prerequisites

- Python 3.11 or higher
- Windows 10/11

### Setup

```bash
# Clone the repository
git clone https://github.com/iddilabs/issue-register.git
cd issue-register

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python -m src.main
```

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest tests/ -v
```

### Building the Executable

```bash
build.bat
```

The executable will be created at `dist/IssueRegister.exe`. See [BUILD.md](BUILD.md) for detailed build instructions.

## User Roles

| Role | Permissions |
|------|-------------|
| **Administrator** | Full access: user management, database config, all issues |
| **Editor** | Edit all issues, can close issues, separate view/edit department restrictions |
| **Restricted** | Limited to assigned departments, cannot close issues or transition Draft→Open |
| **Viewer** | Read-only access |

## Status Workflow

```
Draft → Open → In Progress → Remediated → Closed
```

- Restricted users create issues in **Draft** status
- **Editor/Admin** required for Draft→Open and Remediated→Closed transitions

## Project Structure

```
src/
├── database/       # SQLite connection, models, queries, migrations
├── services/       # Business logic (auth, permissions, export, file attachments)
├── ui/             # PySide6 views and widgets
└── resources/      # Stylesheets and icons
tests/              # pytest test files
```

## Documentation

- [BUILD.md](BUILD.md) — Detailed build and packaging instructions
- [SPECIFICATION.md](SPECIFICATION.md) — Complete product specification
- [CONTRIBUTING.md](CONTRIBUTING.md) — How to contribute to this project
- [CLAUDE.md](CLAUDE.md) — Development guidelines for AI-assisted coding

## Contributing

Contributions are welcome! Please read our [Contributing Guidelines](CONTRIBUTING.md) before submitting a pull request.

### Quick Contribution Guide

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest tests/ -v`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Tech Stack

| Component | Technology |
|-----------|------------|
| Language | Python 3.11+ |
| UI Framework | PySide6 (Qt6) |
| Database | SQLite (WAL mode) |
| Charts | QtCharts |
| Excel I/O | openpyxl |
| Authentication | bcrypt |
| Packaging | PyInstaller |

## License

This project is licensed under the MIT License — see the [LICENSE](LICENSE) file for details.

## Acknowledgments

Developed by [IddiLabs](https://github.com/iddilabs).

---

**Found a bug?** [Open an issue](../../issues/new)
**Have a question?** [Start a discussion](../../discussions)
