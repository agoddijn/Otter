.PHONY: help install dev inspect run test lint format clean check-deps install-deps bump-version docs docs-serve docs-build
.PHONY: test-llm llm-test llm-info secrets-check

# Configuration
PROJECT ?= $(CURDIR)

# Check if .env file exists and load it
ifneq (,$(wildcard .env))
    include .env
    export
    ENV_STATUS = ✓ Using .env file
else
    ENV_STATUS = ⚠ No .env file found
endif

help: ## Show this help message
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  🦦 Otter - The IDE for AI Agents"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📦 Setup & Installation"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(install|check)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🚀 Development"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(dev|run|inspect)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🧪 Testing"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'test' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🤖 AI Features (LLM)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(llm|secrets)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "🔧 Code Quality"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(lint|format|typecheck|clean)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "📚 Documentation"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E 'docs' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Options:"
	@echo "  PROJECT=/path/to/project      Set project path (default: current directory)"
	@echo ""
	@echo "Current Config:"
	@echo "  Project:  $(PROJECT)"
	@echo "  .env:     $(ENV_STATUS)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev PROJECT=/path/to/my-project"
	@echo "  make test-llm                          # Test LLM infrastructure"
	@echo "  make secrets-check                     # Check configured providers"
	@echo ""
	@echo "Setup:"
	@echo "  1. Copy .env.example to .env"
	@echo "  2. Add your API keys to .env"
	@echo "  3. Run make dev or make run"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

install: ## Install Python dependencies
	uv sync

check-deps: ## Check system dependencies are installed
	@echo "Checking system dependencies..."
	@PYTHONPATH=src uv run python -c "from otter.utils.dependencies import check_all_dependencies; ok, missing = check_all_dependencies(verbose=True); exit(0 if ok else 1)"
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
	@echo ".env: $(ENV_STATUS)"
	PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run mcp dev src/main.py

inspect: dev ## Alias for dev (run with MCP inspector)

run: ## Run MCP server in production mode
	@echo "Starting MCP server for project: $(PROJECT)"
	@echo ".env: $(ENV_STATUS)"
	PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run python -m otter.mcp_server

test: ## Run all tests
	PYTHONPATH=src uv run pytest tests/

test-unit: ## Run unit tests only
	PYTHONPATH=src uv run pytest tests/unit/ -v

test-integration: ## Run integration tests only
	PYTHONPATH=src uv run pytest tests/integration/ -v

test-watch: ## Run tests in watch mode
	PYTHONPATH=src uv run pytest-watch tests/

test-coverage: ## Run tests with coverage report
	PYTHONPATH=src uv run pytest tests/ --cov=src/otter --cov-report=html --cov-report=term

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

bump-version:
	uv run python scripts/bump_version.py $(or $(bump),patch)
	uv sync

docs-serve: ## Serve documentation locally with auto-reload
	uv run --group docs mkdocs serve

docs-build: ## Build documentation site
	uv run --group docs mkdocs build

docs: docs-serve ## Alias for docs-serve

# ============================================================================
# AI Features (LLM)
# ============================================================================

secrets-check: ## Check which LLM providers are configured
	@echo "Checking LLM provider configuration..."
	@echo ""
	PYTHONPATH=src uv run python scripts/check_llm_config.py

llm-info: secrets-check ## Alias for secrets-check

test-llm: ## Test LLM infrastructure (requires API keys)
	@echo "Testing LLM infrastructure..."
	@echo ".env: $(ENV_STATUS)"
	@echo ""
	uv run python examples/test_llm_infrastructure.py

llm-test: test-llm ## Alias for test-llm