.PHONY: help install install-dev test test-unit test-async test-db test-all test-verbose test-fast test-failed coverage coverage-html lint format clean clean-py clean-test clean-all docs run debug setup-db docker-build docker-run docker-stop

# Project variables
PYTHON := python3
PIP := pip3
PROJECT_NAME := AudioBookSync
PYTHON_VERSION := 3.9+
SRC_DIR := src
TESTS_DIR := tests
DOCS_DIR := docs

# Color output
BLUE := \033[0;34m
GREEN := \033[0;32m
RED := \033[0;31m
YELLOW := \033[0;33m
NC := \033[0m # No Color

help: ## Display this help message
	@echo "$(BLUE)=================================$(NC)"
	@echo "$(BLUE)$(PROJECT_NAME) - Development Commands$(NC)"
	@echo "$(BLUE)=================================$(NC)"
	@echo ""
	@echo "$(GREEN)Installation:$(NC)"
	@grep -E '^\s*(install|setup).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Testing:$(NC)"
	@grep -E '^\s*test.*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Code Quality:$(NC)"
	@grep -E '^\s*(lint|format).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Cleanup:$(NC)"
	@grep -E '^\s*clean.*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Development:$(NC)"
	@grep -E '^\s*(run|debug|docs).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(GREEN)Database:$(NC)"
	@grep -E '^\s*(setup-db|docker).*:.*##' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(YELLOW)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# ==============================================================================
# Installation & Setup
# ==============================================================================

install: ## Install project dependencies
	@echo "$(BLUE)Installing dependencies...$(NC)"
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

install-dev: install ## Install development dependencies
	@echo "$(BLUE)Installing development dependencies...$(NC)"
	$(PIP) install pytest pytest-asyncio pytest-cov black flake8 isort mypy
	@echo "$(GREEN)✓ Development dependencies installed$(NC)"

setup: install-dev ## Complete project setup
	@echo "$(BLUE)Setting up project...$(NC)"
	@echo "$(YELLOW)• Creating directories...$(NC)"
	mkdir -p logs audiobooks/downloaded audiobooks/decrypted
	@echo "$(YELLOW)• Checking Python version...$(NC)"
	@$(PYTHON) --version
	@echo "$(GREEN)✓ Project setup complete$(NC)"

# ==============================================================================
# Testing
# ==============================================================================

test: ## Run all tests
	@echo "$(BLUE)Running all tests...$(NC)"
	pytest $(TESTS_DIR) -v
	@echo "$(GREEN)✓ Tests completed$(NC)"

test-unit: ## Run unit tests only
	@echo "$(BLUE)Running unit tests...$(NC)"
	pytest $(TESTS_DIR) -m unit -v
	@echo "$(GREEN)✓ Unit tests completed$(NC)"

test-async: ## Run async tests only
	@echo "$(BLUE)Running async tests...$(NC)"
	pytest $(TESTS_DIR) -m asyncio -v
	@echo "$(GREEN)✓ Async tests completed$(NC)"

test-db: ## Run database tests only
	@echo "$(BLUE)Running database tests...$(NC)"
	pytest $(TESTS_DIR) -m db -v
	@echo "$(GREEN)✓ Database tests completed$(NC)"

test-all: clean-test test ## Clean and run all tests
	@echo "$(GREEN)✓ All tests completed$(NC)"

test-verbose: ## Run tests with verbose output and stdout
	@echo "$(BLUE)Running tests in verbose mode...$(NC)"
	pytest $(TESTS_DIR) -vv -s
	@echo "$(GREEN)✓ Verbose tests completed$(NC)"

test-fast: ## Run tests with minimal output (fail fast)
	@echo "$(BLUE)Running tests in fast mode...$(NC)"
	pytest $(TESTS_DIR) -x -q
	@echo "$(GREEN)✓ Fast tests completed$(NC)"

test-failed: ## Run only previously failed tests
	@echo "$(BLUE)Running failed tests...$(NC)"
	pytest $(TESTS_DIR) --lf -v
	@echo "$(GREEN)✓ Failed tests completed$(NC)"

test-watch: ## Run tests in watch mode (requires pytest-watch)
	@echo "$(BLUE)Running tests in watch mode...$(NC)"
	ptw $(TESTS_DIR) -v
	@echo "$(GREEN)✓ Watch mode enabled$(NC)"

# ==============================================================================
# Coverage & Reporting
# ==============================================================================

coverage: ## Generate coverage report in terminal
	@echo "$(BLUE)Generating coverage report...$(NC)"
	pytest $(TESTS_DIR) --cov=$(SRC_DIR) --cov-report=term-missing
	@echo "$(GREEN)✓ Coverage report generated$(NC)"

coverage-html: ## Generate HTML coverage report
	@echo "$(BLUE)Generating HTML coverage report...$(NC)"
	pytest $(TESTS_DIR) --cov=$(SRC_DIR) --cov-report=html
	@echo "$(GREEN)✓ HTML coverage report generated in htmlcov/$(NC)"
	@echo "$(YELLOW)  Open htmlcov/index.html to view$(NC)"

coverage-open: coverage-html ## Generate and open HTML coverage report
	@echo "$(BLUE)Opening coverage report...$(NC)"
	@command -v open >/dev/null 2>&1 && open htmlcov/index.html || xdg-open htmlcov/index.html || echo "Please open htmlcov/index.html manually"

# ==============================================================================
# Code Quality
# ==============================================================================

lint: ## Run linting checks (flake8)
	@echo "$(BLUE)Running linting checks...$(NC)"
	flake8 $(SRC_DIR) $(TESTS_DIR) --max-line-length=100 --exclude=__pycache__,venv,migrations
	@echo "$(GREEN)✓ Linting checks passed$(NC)"

format: ## Format code (black)
	@echo "$(BLUE)Formatting code...$(NC)"
	black $(SRC_DIR) $(TESTS_DIR)
	isort $(SRC_DIR) $(TESTS_DIR)
	@echo "$(GREEN)✓ Code formatted$(NC)"

format-check: ## Check code formatting without changes
	@echo "$(BLUE)Checking code formatting...$(NC)"
	black --check $(SRC_DIR) $(TESTS_DIR)
	isort --check-only $(SRC_DIR) $(TESTS_DIR)
	@echo "$(GREEN)✓ Code formatting is correct$(NC)"

type-check: ## Run type checking (mypy)
	@echo "$(BLUE)Running type checks...$(NC)"
	mypy $(SRC_DIR) --ignore-missing-imports
	@echo "$(GREEN)✓ Type checking passed$(NC)"

qa: format lint type-check ## Run all code quality checks

# ==============================================================================
# Cleanup
# ==============================================================================

clean: clean-py clean-test clean-build ## Remove all build, test, and Python artifacts

clean-build: ## Remove build artifacts
	@echo "$(BLUE)Cleaning build artifacts...$(NC)"
	rm -fr build/
	rm -fr dist/
	rm -fr .eggs/
	find . -name '*.egg-info' -exec rm -fr {} +
	find . -name '*.egg' -exec rm -f {} +
	@echo "$(GREEN)✓ Build artifacts cleaned$(NC)"

clean-py: ## Remove Python file artifacts
	@echo "$(BLUE)Cleaning Python artifacts...$(NC)"
	find . -type f -name '*.py[cod]' -delete
	find . -type f -name '*~' -delete
	find . -type d -name '__pycache__' -exec rm -fr {} +
	find . -type d -name '*.egg-info' -exec rm -fr {} +
	find . -type d -name '.mypy_cache' -exec rm -fr {} +
	find . -type d -name '.pytest_cache' -exec rm -fr {} +
	@echo "$(GREEN)✓ Python artifacts cleaned$(NC)"

clean-test: ## Remove test and coverage artifacts
	@echo "$(BLUE)Cleaning test artifacts...$(NC)"
	rm -fr .tox/
	rm -f .coverage
	rm -fr htmlcov/
	rm -fr .pytest_cache/
	@echo "$(GREEN)✓ Test artifacts cleaned$(NC)"

clean-all: clean ## Remove all artifacts including caches
	@echo "$(BLUE)Cleaning all artifacts...$(NC)"
	rm -rf venv/
	rm -rf .venv/
	find . -type d -name '.DS_Store' -delete
	@echo "$(GREEN)✓ All artifacts cleaned$(NC)"

# ==============================================================================
# Documentation
# ==============================================================================

docs: ## Build documentation
	@echo "$(BLUE)Building documentation...$(NC)"
	@if [ -d "$(DOCS_DIR)" ]; then \
		echo "$(YELLOW)Documentation files:$(NC)"; \
		ls -la $(DOCS_DIR)/*.md 2>/dev/null || echo "$(YELLOW)No markdown docs found$(NC)"; \
	fi
	@echo "$(YELLOW)Test documentation:$(NC)"
	@ls -la TESTING.md TEST_SUMMARY.md TESTS_BY_MODULE.md TESTS_CHECKLIST.md 2>/dev/null
	@echo "$(GREEN)✓ Documentation overview complete$(NC)"

docs-test: ## View testing documentation
	@echo "$(BLUE)Opening testing documentation...$(NC)"
	@command -v less >/dev/null 2>&1 && less TESTING.md || cat TESTING.md

docs-summary: ## View test summary
	@echo "$(BLUE)Displaying test summary...$(NC)"
	@head -50 TEST_SUMMARY.md

# ==============================================================================
# Development & Running
# ==============================================================================

run: ## Run the application
	@echo "$(BLUE)Running $(PROJECT_NAME)...$(NC)"
	$(PYTHON) -m src.main
	@echo "$(GREEN)✓ Application finished$(NC)"

run-dev: ## Run application in development mode with reload
	@echo "$(BLUE)Running in development mode...$(NC)"
	$(PYTHON) -m src.main --debug
	@echo "$(GREEN)✓ Development mode finished$(NC)"

debug: ## Run application with debug output
	@echo "$(BLUE)Running with debug output...$(NC)"
	$(PYTHON) -m pdb src/main.py
	@echo "$(GREEN)✓ Debug session finished$(NC)"

shell: ## Start Python interactive shell with project context
	@echo "$(BLUE)Starting Python shell...$(NC)"
	$(PYTHON) -c "import sys; sys.path.insert(0, '.'); from src.core.config import Config; print('Config loaded'); import code; code.interact(local=locals())"

check: test lint format-check ## Run all checks (test, lint, format check)

# ==============================================================================
# Database
# ==============================================================================

setup-db: ## Initialize database
	@echo "$(BLUE)Setting up database...$(NC)"
	@echo "$(YELLOW)• This requires a running PostgreSQL instance$(NC)"
	@echo "$(YELLOW)• Ensure DATABASE_URL is set in .env$(NC)"
	@echo "$(YELLOW)• Run: python -m src.database.init$(NC)"
	@echo "$(GREEN)✓ Database setup instructions displayed$(NC)"

db-reset: ## Reset database (warning: destructive)
	@echo "$(RED)WARNING: This will delete all database data!$(NC)"
	@echo "$(YELLOW)Continue? [y/N] $(NC)"
	@read -r response; if [ "$$response" = "y" ]; then \
		echo "$(BLUE)Resetting database...$(NC)"; \
		echo "$(YELLOW)Run: python -m src.database.reset$(NC)"; \
	else \
		echo "$(YELLOW)Operation cancelled$(NC)"; \
	fi

db-migrate: ## Run database migrations
	@echo "$(BLUE)Running migrations...$(NC)"
	@echo "$(YELLOW)Run: python -m src.database.migrate$(NC)"

db-seed: ## Seed database with test data
	@echo "$(BLUE)Seeding database...$(NC)"
	@echo "$(YELLOW)Run: python -m src.database.seed$(NC)"

# ==============================================================================
# Docker
# ==============================================================================

docker-build: ## Build Docker image
	@echo "$(BLUE)Building Docker image...$(NC)"
	@if [ -f "Dockerfile" ]; then \
		docker build -t $(PROJECT_NAME):latest .; \
		echo "$(GREEN)✓ Docker image built$(NC)"; \
	else \
		echo "$(RED)Dockerfile not found$(NC)"; \
	fi

docker-run: ## Run Docker container
	@echo "$(BLUE)Running Docker container...$(NC)"
	@if command -v docker >/dev/null 2>&1; then \
		docker run -it --env-file .env $(PROJECT_NAME):latest; \
		echo "$(GREEN)✓ Container finished$(NC)"; \
	else \
		echo "$(RED)Docker is not installed$(NC)"; \
	fi

docker-stop: ## Stop all Docker containers
	@echo "$(BLUE)Stopping Docker containers...$(NC)"
	@docker ps -q | xargs -r docker stop
	@echo "$(GREEN)✓ Containers stopped$(NC)"

docker-compose-up: ## Start services with docker-compose
	@echo "$(BLUE)Starting services...$(NC)"
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose up -d; \
		echo "$(GREEN)✓ Services started$(NC)"; \
	else \
		echo "$(RED)docker-compose.yml not found$(NC)"; \
	fi

docker-compose-down: ## Stop services with docker-compose
	@echo "$(BLUE)Stopping services...$(NC)"
	@if [ -f "docker-compose.yml" ]; then \
		docker-compose down; \
		echo "$(GREEN)✓ Services stopped$(NC)"; \
	else \
		echo "$(RED)docker-compose.yml not found$(NC)"; \
	fi

# ==============================================================================
# Utility & Info
# ==============================================================================

info: ## Display project information
	@echo "$(BLUE)Project Information$(NC)"
	@echo "$(YELLOW)Name:$(NC) $(PROJECT_NAME)"
	@echo "$(YELLOW)Python:$(NC) $(PYTHON_VERSION)"
	@echo "$(YELLOW)Source:$(NC) $(SRC_DIR)/"
	@echo "$(YELLOW)Tests:$(NC) $(TESTS_DIR)/"
	@echo "$(YELLOW)Docs:$(NC) $(DOCS_DIR)/"
	@echo ""
	@echo "$(BLUE)Project Stats$(NC)"
	@echo "$(YELLOW)Python Files:$(NC) $$(find $(SRC_DIR) -name '*.py' | wc -l)"
	@echo "$(YELLOW)Test Files:$(NC) $$(find $(TESTS_DIR) -name 'test_*.py' | wc -l)"
	@echo "$(YELLOW)Test Cases:$(NC) $$(grep -r 'def test_' $(TESTS_DIR) 2>/dev/null | wc -l)"
	@echo ""
	@echo "$(BLUE)Dependencies$(NC)"
	@echo "$(YELLOW)Total:$(NC) $$(wc -l < requirements.txt) packages"
	@echo "$(YELLOW)Core:$(NC) $$(head -1 requirements.txt)"

version: ## Display version information
	@echo "$(BLUE)$(PROJECT_NAME)$(NC) - Version Info"
	@$(PYTHON) --version
	$(PIP) --version
	@echo ""
	@echo "$(YELLOW)Key Dependencies:$(NC)"
	@$(PIP) list | grep -E "pytest|audible|cryptography|loguru|psycopg2" || true

env-check: ## Check environment setup
	@echo "$(BLUE)Environment Check$(NC)"
	@echo ""
	@echo "$(YELLOW)Python:$(NC)"
	@command -v $(PYTHON) >/dev/null 2>&1 && echo "  ✓ Python found at $$(which $(PYTHON))" || echo "  ✗ Python not found"
	@echo ""
	@echo "$(YELLOW)Package Manager:$(NC)"
	@command -v $(PIP) >/dev/null 2>&1 && echo "  ✓ pip found at $$(which $(PIP))" || echo "  ✗ pip not found"
	@echo ""
	@echo "$(YELLOW)Database:$(NC)"
	@command -v psql >/dev/null 2>&1 && echo "  ✓ PostgreSQL found" || echo "  ✗ PostgreSQL not found (optional)"
	@echo ""
	@echo "$(YELLOW)Docker:$(NC)"
	@command -v docker >/dev/null 2>&1 && echo "  ✓ Docker found" || echo "  ✗ Docker not found (optional)"
	@echo ""
	@echo "$(YELLOW)Environment File:$(NC)"
	@[ -f ".env" ] && echo "  ✓ .env file exists" || echo "  ✗ .env file not found"
	@echo ""

# ==============================================================================
# CI/CD Helpers
# ==============================================================================

ci-test: clean-test test coverage ## Run tests with coverage (CI mode)

ci-check: ci-test lint format-check ## Run full CI checks

pre-commit: format lint test ## Run pre-commit checks

# ==============================================================================
# Default target
# ==============================================================================

.DEFAULT_GOAL := help
