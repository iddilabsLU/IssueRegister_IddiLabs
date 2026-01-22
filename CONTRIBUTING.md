# Contributing to Issue Register

Thank you for your interest in contributing to Issue Register! This document provides guidelines and information for contributors.

## Code of Conduct

By participating in this project, you agree to maintain a respectful and inclusive environment. Be kind, constructive, and professional in all interactions.

## How to Contribute

### Reporting Bugs

1. **Search existing issues** to avoid duplicates
2. **Open a new issue** with a clear title and description
3. Include:
   - Steps to reproduce the bug
   - Expected behavior
   - Actual behavior
   - Screenshots if applicable
   - Your environment (OS version, Python version)

### Suggesting Features

1. **Search existing issues** to see if it's already proposed
2. **Open a feature request** describing:
   - The problem you're trying to solve
   - Your proposed solution
   - Any alternatives you've considered

### Submitting Code

1. **Fork** the repository
2. **Create a feature branch** from `main`:
   ```bash
   git checkout -b feature/your-feature-name
   ```
3. **Make your changes** following our coding standards
4. **Write or update tests** for your changes
5. **Run the test suite** to ensure everything passes:
   ```bash
   pytest tests/ -v
   ```
6. **Commit your changes** with clear commit messages
7. **Push** to your fork
8. **Open a Pull Request** against `main`

## Development Setup

```bash
# Clone your fork
git clone https://github.com/YOUR-USERNAME/issue-register.git
cd issue-register

# Create virtual environment
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements-dev.txt

# Run the application
python -m src.main

# Run tests
pytest tests/ -v
```

## Coding Standards

### Python Style

- Follow [PEP 8](https://pep8.org/) style guidelines
- Use meaningful variable and function names
- Keep functions focused and reasonably sized
- Add docstrings to public functions and classes

### Code Organization

- **Database queries** go in `src/database/queries.py`
- **Business logic** goes in `src/services/`
- **UI code** goes in `src/ui/`
- **Reusable widgets** go in `src/ui/widgets/`

### Security

- Always use parameterized queries (never concatenate SQL)
- Never log sensitive information (passwords, tokens)
- Validate user input at system boundaries

### Testing

- Write tests for new functionality
- Update tests when modifying existing code
- Aim for >80% code coverage
- Use pytest fixtures for setup/teardown

Example test structure:

```python
# tests/test_example.py
import pytest
from src.services.example import example_function

def test_example_basic():
    """Test basic functionality."""
    result = example_function("input")
    assert result == "expected_output"

def test_example_edge_case():
    """Test edge case handling."""
    with pytest.raises(ValueError):
        example_function(None)
```

## Pull Request Guidelines

### Before Submitting

- [ ] Tests pass locally (`pytest tests/ -v`)
- [ ] Code follows project style guidelines
- [ ] New features have tests
- [ ] Documentation is updated if needed

### PR Description

Include:
- **What** the PR does
- **Why** the change is needed
- **How** to test the changes

### Review Process

1. Maintainers will review your PR
2. Address any feedback or requested changes
3. Once approved, a maintainer will merge your PR

## Project Architecture

Understanding the codebase structure helps you contribute effectively:

```
src/
├── database/      # Data layer
│   ├── connection.py   # SQLite singleton
│   ├── migrations.py   # Schema management
│   ├── models.py       # Data classes
│   └── queries.py      # All SQL queries
├── services/      # Business logic layer
│   ├── auth.py         # Authentication
│   ├── audit.py        # Audit logging
│   ├── permissions.py  # RBAC
│   └── ...
├── ui/            # Presentation layer
│   ├── main_window.py  # App shell
│   ├── register.py     # Issue list
│   ├── dashboard.py    # Analytics
│   └── widgets/        # Reusable components
└── resources/     # Static files
```

### Key Patterns

- **Singleton pattern** for database connection and file service
- **Service layer** for business logic (not in UI code)
- **Property-based styling** for Qt widgets

See [CLAUDE.md](CLAUDE.md) for detailed architecture documentation.

## Types of Contributions

### Good First Issues

Look for issues labeled `good first issue` — these are suitable for newcomers to the codebase.

### Documentation

- Improve README, guides, or code comments
- Add examples or tutorials
- Fix typos or clarify confusing sections

### Bug Fixes

- Fix reported bugs
- Add regression tests

### Features

- Implement requested features
- Propose and build new functionality

### Testing

- Increase test coverage
- Add edge case tests
- Improve test performance

## Getting Help

- **Questions?** Open a [Discussion](../../discussions)
- **Found a bug?** Open an [Issue](../../issues)
- **Want to chat?** Reach out to the maintainers

## Recognition

Contributors are recognized in:
- Git commit history
- GitHub contributors page
- Release notes for significant contributions

Thank you for contributing to Issue Register!
