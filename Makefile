.PHONY: help install dev inspect run test lint format clean check-deps install-deps bump-version docs docs-serve docs-build
.PHONY: test-llm llm-test llm-info secrets-check doppler-setup doppler-run

# Configuration
PROJECT ?= $(CURDIR)
USE_DOPPLER ?= yes  # Set to 'no' to disable Doppler (USE_DOPPLER=no)

# Doppler wrapper - prepends doppler run if USE_DOPPLER=yes
ifneq ($(USE_DOPPLER),no)
    DOPPLER_CMD = DOPPLER_ENV=1 doppler run -- env
    DOPPLER_STATUS = ✓ Using Doppler for secrets
else
    DOPPLER_CMD = env
    DOPPLER_STATUS = ✗ Doppler disabled
endif

help: ## Show this help message
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  🦦 Otter - The IDE for AI Agents"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo ""
	@echo "📦 Setup & Installation"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | grep -E '(install|check|doppler-setup)' | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
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
	@echo "  USE_DOPPLER=yes|no            Enable/disable Doppler (default: yes)"
	@echo ""
	@echo "Current Config:"
	@echo "  Project:  $(PROJECT)"
	@echo "  Doppler:  $(DOPPLER_STATUS)"
	@echo ""
	@echo "Examples:"
	@echo "  make dev PROJECT=/path/to/my-project"
	@echo "  make test-llm                          # Test LLM infrastructure"
	@echo "  make secrets-check                     # Check configured providers"
	@echo "  make run USE_DOPPLER=no                # Run without Doppler"
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

doppler-setup: ## Configure Doppler for this project
	@echo "Setting up Doppler..."
	@command -v doppler >/dev/null 2>&1 || { echo "❌ Doppler CLI not installed. Install from: https://docs.doppler.com/docs/install-cli"; exit 1; }
	doppler setup
	@echo ""
	@echo "✅ Doppler configured!"
	@echo "Add your LLM API keys with:"
	@echo "  doppler secrets set ANTHROPIC_API_KEY 'your-key'"
	@echo "  doppler secrets set OPENAI_API_KEY 'your-key'"
	@echo "  doppler secrets set GOOGLE_API_KEY 'your-key'"

dev: ## Run MCP server in development mode with inspector
	@echo "Starting MCP inspector for project: $(PROJECT)"
	@echo "Doppler: $(DOPPLER_STATUS)"
	$(DOPPLER_CMD) PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run mcp dev src/main.py

inspect: dev ## Alias for dev (run with MCP inspector)

run: ## Run MCP server in production mode
	@echo "Starting MCP server for project: $(PROJECT)"
	@echo "Doppler: $(DOPPLER_STATUS)"
	$(DOPPLER_CMD) PYTHONPATH=src IDE_PROJECT_PATH=$(PROJECT) uv run python -m otter.mcp_server

doppler-run: ## Generic Doppler command runner (usage: make doppler-run CMD="your command")
	@test -n "$(CMD)" || { echo "Usage: make doppler-run CMD=\"your command\""; exit 1; }
	$(DOPPLER_CMD) $(CMD)

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
	$(DOPPLER_CMD) PYTHONPATH=src uv run python scripts/check_llm_config.py

llm-info: secrets-check ## Alias for secrets-check

test-llm: ## Test LLM infrastructure (requires API keys)
	@echo "Testing LLM infrastructure..."
	@echo "Doppler: $(DOPPLER_STATUS)"
	@echo ""
	$(DOPPLER_CMD) uv run python examples/test_llm_infrastructure.py

llm-test: test-llm ## Alias for test-llm