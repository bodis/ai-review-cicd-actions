# AI Code Review - Modern Task Runner
# Uses UV package manager with pyproject.toml configuration

set shell := ["bash", "-c"]

# Show available commands
default:
    @just --list

# Install dependencies and setup pre-commit hooks
install:
    @echo "📦 Installing dependencies..."
    uv sync
    @echo "🪝 Setting up pre-commit hooks..."
    uv run pre-commit install
    @echo "✅ Installation complete"

# Run all quality checks (same as CI)
quality: lint typecheck security test
    @echo ""
    @echo "✅ All quality checks passed!"
    @echo "   Ready to commit and push."

# Format code automatically
format:
    @echo "✨ Formatting code with Ruff..."
    uv run ruff format .
    uv run ruff check --fix .
    @echo "✅ Code formatted"

# Check formatting without changes
check-format:
    @echo "🔍 Checking code format..."
    uv run ruff format --check .

# Lint with Ruff
lint:
    @echo "🔍 Running Ruff linter..."
    uv run ruff check .

# Type check with mypy
typecheck:
    @echo "🔍 Running mypy type checking..."
    uv run mypy lib/ main.py

# Security scan with Bandit
security:
    @echo "🔒 Running Bandit security scan..."
    uv run bandit -r lib/ main.py -f screen

# Run Pylint (informational only)
pylint:
    @echo "🔍 Running Pylint (informational)..."
    -uv run pylint lib/ main.py || echo "⚠️ Pylint warnings (non-blocking)"

# Run tests with coverage
test:
    @echo "🧪 Running tests with coverage..."
    uv run pytest --cov=lib --cov-report=term --cov-report=html -v

# Run tests quickly (no coverage)
test-quick:
    @echo "🧪 Running tests (no coverage)..."
    uv run pytest -v

# Clean generated files
clean:
    @echo "🧹 Cleaning generated files..."
    rm -rf .pytest_cache htmlcov .coverage .ruff_cache .mypy_cache
    rm -rf *.egg-info dist build
    find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
    @echo "✅ Cleanup complete"

# Update pre-commit hooks
update-hooks:
    @echo "🔄 Updating pre-commit hooks..."
    uv run pre-commit autoupdate
    @echo "✅ Hooks updated"

# Run pre-commit on all files
pre-commit-all:
    @echo "🪝 Running pre-commit on all files..."
    uv run pre-commit run --all-files
