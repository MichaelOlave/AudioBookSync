# ============================================================================
# Makefile - Development Commands
# ============================================================================
# Usage: make <command>
#
# Available commands:
#   make help              Show this help message
#   make install           Install development dependencies
#   make format            Format code with Black and isort
#   make lint              Run all linting checks
#   make type-check        Run type checking with mypy
#   make security          Run security checks with bandit
#   make test              Run pytest tests
#   make test-cov          Run tests with coverage report
#   make pre-commit        Run pre-commit hooks on all files
#   make pre-commit-install Install pre-commit hooks
#   make check             Run all checks (format + lint + type-check + security)
#   make clean             Clean up cache and temporary files

.PHONY: help install format lint type-check security test test-cov pre-commit pre-commit-install check clean

# ============================================================================
# VARIABLES
# ============================================================================
PYTHON := python3
PIP := pip
SRC_DIR := src
TEST_DIR := tests

# ============================================================================
# TARGETS
# ============================================================================

help:
	@echo "Development Commands"
	@echo "===================="
	@grep -E "^[a-zA-Z_-]+:" Makefile | sed 's/:.*##/: ##/' | sed 's/^\([a-zA-Z_-]*\):/\1/' | awk '{print "  make " $$1}' | sort

install: ## Install development dependencies
	$(PIP) install -r requirements.txt

format: ## Format code with Black and isort
	@echo "Running isort..."
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR)
	@echo "Running Black..."
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR) --line-length=100

lint: ## Run all linting checks (isort, Black, Flake8)
	@echo "Checking import sorting with isort..."
	$(PYTHON) -m isort $(SRC_DIR) $(TEST_DIR) --check-only --diff
	@echo "Checking code formatting with Black..."
	$(PYTHON) -m black $(SRC_DIR) $(TEST_DIR) --check --line-length=100
	@echo "Running Flake8..."
	$(PYTHON) -m flake8 $(SRC_DIR) $(TEST_DIR)

type-check: ## Run type checking with mypy
	@echo "Running mypy type checker..."
	$(PYTHON) -m mypy $(SRC_DIR) --ignore-missing-imports

security: ## Run security checks with bandit
	@echo "Running bandit security scanner..."
	$(PYTHON) -m bandit -r $(SRC_DIR) -c .bandit

test: ## Run pytest tests
	@echo "Running pytest..."
	$(PYTHON) -m pytest $(TEST_DIR) -v

test-cov: ## Run tests with coverage report
	@echo "Running pytest with coverage..."
	$(PYTHON) -m pytest $(TEST_DIR) -v --cov=$(SRC_DIR) --cov-report=html --cov-report=term-missing
	@echo "Coverage report generated in htmlcov/index.html"

pre-commit-install: ## Install pre-commit hooks
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "Pre-commit hooks installed successfully"

pre-commit: ## Run pre-commit hooks on all files
	@echo "Running pre-commit on all files..."
	pre-commit run --all-files

check: format lint type-check security ## Run all checks
	@echo "✓ All checks passed!"

clean: ## Clean up cache and temporary files
	@echo "Cleaning up cache files..."
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .coverage -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name htmlcov -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name .coverage -delete
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "Clean completed"
