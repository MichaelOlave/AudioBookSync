# Code Quality & Linting Guide

This project uses a comprehensive set of tools to maintain code quality, consistency, and security. This guide explains how to use them.

## Quick Start

### 1. Install Development Tools
```bash
pip install -r requirements.txt
```

### 2. Install Pre-commit Hooks (Recommended)
```bash
make pre-commit-install
```

This automatically runs linting checks before each commit.

### 3. Format Your Code
```bash
make format
```

## Available Tools

### Black - Code Formatter
**Purpose:** Enforces consistent code formatting

**Config:** `pyproject.toml` → `[tool.black]`
- **Line length:** 100 characters
- **Target:** Python 3.10+

**Usage:**
```bash
# Format code
python -m black src/ tests/ --line-length=100

# Check (don't modify)
python -m black src/ tests/ --check --line-length=100
```

### isort - Import Sorter
**Purpose:** Organizes imports consistently

**Config:** `pyproject.toml` → `[tool.isort]`
- **Profile:** Black-compatible
- **Order:** stdlib → third-party → first-party → local
- **Line length:** 100 characters

**Usage:**
```bash
# Sort imports
python -m isort src/ tests/

# Check (don't modify)
python -m isort src/ tests/ --check-only --diff
```

### Flake8 - Linter
**Purpose:** Detects code style issues and potential bugs

**Config:** `.flake8`
- **Max line length:** 100 characters
- **Max complexity:** 10
- **Docstring convention:** Google style

**Usage:**
```bash
python -m flake8 src/ tests/
```

**Common Errors:**
- `E501`: Line too long (Black handles this)
- `W503`: Line break before operator (Black handles this)
- `D100`: Missing module docstring (configurable)
- `F401`: Imported but unused

### Mypy - Type Checker
**Purpose:** Validates type hints and catches type-related errors

**Config:** `pyproject.toml` → `[tool.mypy]`
- **Python version:** 3.10
- **Mode:** Strict optional, check untyped defs

**Usage:**
```bash
python -m mypy src/ --ignore-missing-imports
```

### Bandit - Security Scanner
**Purpose:** Scans for common security vulnerabilities

**Config:** `.bandit`

**Usage:**
```bash
python -m bandit -r src/ -c .bandit
```

## Make Commands

Convenient shortcuts for all tools:

```bash
make format        # Format code with Black and isort
make lint          # Run linting checks (isort, Black, Flake8)
make type-check    # Run mypy type checking
make security      # Run bandit security scan
make test          # Run pytest tests
make test-cov      # Run tests with coverage report
make check         # Run all checks
make clean         # Clean cache files
```

## Pre-commit Hooks

The `.pre-commit-config.yaml` automatically runs:
1. General file checks (merge conflicts, large files, etc.)
2. isort for import ordering
3. Black for code formatting
4. Flake8 for linting
5. Mypy for type checking
6. Bandit for security scanning
7. Pydocstyle for docstring checking

### Install Hooks
```bash
make pre-commit-install
# or
pre-commit install
```

### Run Manually
```bash
make pre-commit
# or
pre-commit run --all-files
```

### Bypass Hooks (Not Recommended)
```bash
git commit --no-verify
```

## Typical Workflow

1. **Write code** in your feature branch

2. **Format before committing:**
   ```bash
   make format
   ```

3. **Run all checks:**
   ```bash
   make check
   ```

4. **Commit when all checks pass:**
   ```bash
   git commit -m "Your message"
   ```
   Pre-commit hooks will run automatically

5. **Push to repository:**
   ```bash
   git push origin your-branch
   ```

## Configuration Details

### Import Organization (isort)
Your imports should follow this order:

```python
# Standard library imports
from typing import Optional, List
import json
from datetime import datetime

# Third-party imports
from fastapi import APIRouter
from sqlalchemy import select
from loguru import logger

# First-party (project) imports
from src.database.models import Book
from src.api.schemas import BookSchema

# Local imports
from .utils import helper_function
```

### Type Hints Standards
All functions should have type hints:

```python
# Good
async def get_book(db: AsyncSession, book_id: str) -> Optional[Book]:
    """Retrieve a book by ID."""
    ...

# Also good (explicit import)
from typing import Optional, List, Dict, Any
async def update_books(
    db: AsyncSession,
    books: List[Dict[str, Any]]
) -> bool:
    """Update multiple books."""
    ...
```

### Docstring Format (Google Style)
```python
def function_name(param1: str, param2: int) -> bool:
    """
    One-line summary ending with period.

    Longer description if needed. Explain what the function does,
    any important side effects, and why it exists.

    Args:
        param1: Description of param1
        param2: Description of param2

    Returns:
        Description of return value

    Raises:
        ValueError: When param1 is invalid
        TypeError: When param2 is not an int

    Example:
        >>> function_name("test", 42)
        True
    """
    ...
```

### Complexity Limits
- **Max line length:** 100 characters
- **Max function complexity:** 10 (McCabe complexity)

Break complex functions into smaller ones if you exceed this.

## Enforcing Standards in CI/CD

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions
- name: Run linting
  run: make lint

- name: Type checking
  run: make type-check

- name: Security scan
  run: make security

- name: Tests
  run: make test-cov
```

## Excluding Files/Directories

Most tools respect `.gitignore` and have built-in exclusions:
- `.venv/`, `venv/`
- `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`
- `build/`, `dist/`, `*.egg-info`
- `migrations/`

## Troubleshooting

### Pre-commit hook fails
```bash
# Check what's wrong
pre-commit run --all-files --verbose

# Fix and try again
make format  # Fixes most issues
```

### Type checking errors
```bash
# Add type ignore comment for known issues (use sparingly)
result = some_function()  # type: ignore

# Or suppress specific error
result = some_function()  # type: ignore[arg-type]
```

### Linting errors not in config
Check these files:
1. `pyproject.toml` - Black, isort, mypy config
2. `.flake8` - Flake8 config
3. `.bandit` - Bandit config

## Additional Resources

- [Black Documentation](https://black.readthedocs.io/)
- [isort Documentation](https://pycqa.github.io/isort/)
- [Flake8 Documentation](https://flake8.pycqa.org/)
- [Mypy Documentation](https://mypy.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [Pre-commit Documentation](https://pre-commit.com/)
