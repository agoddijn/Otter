.PHONY: help install dev inspect run test lint format clean check-deps install-deps

# Project path can be overridden: make dev PROJECT=/path/to/project
PROJECT ?= $(CURDIR)

help: ## Show this help message
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "Options:"
	@echo "  PROJECT=/path/to/project  Set the project path (default: current directory)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev PROJECT=/path/to/my-project"
	@echo "  make run PROJECT=~/code/app"

install: ## Install Python dependencies
	uv sync

check-deps: ## Check system dependencies are installed
	@echo "Checking system dependencies..."
	@PYTHONPATH=src uv run python -c "from cli_ide.utils.dependencies import check_all_dependencies; ok, missing = check_all_dependencies(verbose=True); exit(0 if ok else 1)"
	@echo ""
	@echo "✅ All required dependencies are installed!"

install-deps: ## Install system dependencies (macOS only)
	@echo "Installing system dependencies via Homebrew..."
	@command -v brew >/dev/null 2>&1 || { echo "❌ Homebrew not installed. Install from https://brew.sh"; exit 1; }
	@echo "Installing Neovim..."
	@brew install neovim || true
	@echo "Installing ripgrep..."
	@brew install ripgrep || true
	@echo "Installing Node.js..."
	@brew install node || true
	@echo "Installing Git..."
	@brew install git || true
	@echo ""
	@echo "✅ System dependencies installed!"
	@echo ""
	@echo "Now run: make install  # to install Python dependencies"

dev: ## Run MCP server in development mode with inspector
	@echo "Starting MCP inspector for project: $(PROJECT)"
	PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run mcp dev src/main.py

inspect: dev ## Alias for dev (run with MCP inspector)

run: ## Run MCP server in production mode
	@echo "Starting MCP server for project: $(PROJECT)"
	PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run python -m cli_ide.mcp_server

test: ## Run all tests
	PYTHONPATH=src uv run pytest tests/

test-unit: ## Run unit tests only
	PYTHONPATH=src uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	PYTHONPATH=src uv run pytest tests/integration/ -v

test-watch: ## Run tests in watch mode
	PYTHONPATH=src uv run pytest-watch tests/

test-coverage: ## Run tests with coverage report
	PYTHONPATH=src uv run pytest tests/ --cov=src/cli_ide --cov-report=html --cov-report=term

lint: ## Run linter checks
	uv run ruff check src/

format: ## Format code
	uv run ruff format src/

typecheck: ## Run type checks
	uv run mypy src/

clean: ## Clean up temporary files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
