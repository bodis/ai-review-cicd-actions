# Python Integration Guide

Complete guide for integrating Python static analysis tools into the AI Code Review pipeline.

## Overview

The pipeline uses multiple Python analysis tools to catch different types of issues:
- **Ruff**: Fast linting and code formatting checks
- **Pylint**: Code quality and maintainability analysis
- **Bandit**: Security vulnerability scanning
- **mypy**: Static type checking

## Quick Start

### Minimal Setup

**1. Ensure your project uses UV and pyproject.toml**

Your project should have a `pyproject.toml` with dev dependencies:

```toml
[project]
name = "my-project"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.104.0"]

[tool.uv]
dev-dependencies = [
    "ruff>=0.1.6",
    "pylint>=3.0.0",
    "bandit>=1.7.5",
    "mypy>=1.7.0",
]
```

**2. Add workflow to your project** (`.github/workflows/code-review.yml`):

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-python-analysis: true
      python-version: '3.11'
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

The workflow will automatically:
1. Install UV (fast Python package manager)
2. Set up Python using UV
3. Install analysis tools (Ruff, Pylint, Bandit, mypy)
4. Run all configured checks
5. Post findings as PR comments

**Note**: This review system itself uses UV. Your project can use any dependency manager (UV, Poetry, pip), but the review system will use UV internally.

## Analysis Tools

### 1. Ruff

**Purpose**: Lightning-fast Python linter and formatter (10-100x faster than other tools)

**What it checks:**
- PEP 8 style violations
- Import sorting and organization
- Line length and formatting
- Unused imports and variables
- Common Python anti-patterns

**Configuration** (`.ruff.toml` or `pyproject.toml`):
```toml
[tool.ruff]
line-length = 88
target-version = "py311"

select = [
    "E",   # pycodestyle errors
    "W",   # pycodestyle warnings
    "F",   # pyflakes
    "I",   # isort
    "B",   # flake8-bugbear
    "C4",  # flake8-comprehensions
]

ignore = [
    "E501",  # line too long (handled by formatter)
]

[tool.ruff.per-file-ignores]
"__init__.py" = ["F401"]  # Allow unused imports in __init__.py
```

**Command line**:
```bash
ruff check .
ruff format .  # Auto-fix formatting
```

### 2. Pylint

**Purpose**: Comprehensive code quality analyzer

**What it checks:**
- Code smells and bad practices
- Cyclomatic complexity
- Duplicate code patterns
- Naming conventions
- Class and function design
- Documentation completeness

**Configuration** (`.pylintrc` or `pyproject.toml`):
```toml
[tool.pylint.main]
max-line-length = 88
good-names = ["i", "j", "k", "ex", "Run", "_", "id"]

[tool.pylint.design]
max-args = 7
max-locals = 15
max-branches = 12
max-statements = 50

[tool.pylint.messages_control]
disable = [
    "too-few-public-methods",
    "missing-module-docstring",
]
```

**Command line**:
```bash
pylint src/
```

### 3. Bandit

**Purpose**: Security vulnerability scanner for Python code

**What it checks:**
- SQL injection vulnerabilities
- Hardcoded passwords/secrets
- Use of `eval()` or `exec()`
- Insecure hash functions (MD5, SHA1)
- Insecure random number generation
- Unsafe YAML/pickle loading
- Shell injection risks

**Configuration** (`.bandit` or `pyproject.toml`):
```toml
[tool.bandit]
exclude_dirs = ["/tests"]
skips = ["B101", "B601"]  # Skip assert statements and paramiko calls
```

**Command line**:
```bash
bandit -r src/
bandit -r src/ -f json -o bandit-report.json
```

**Common findings**:
- `B201`: Flask app with debug=True
- `B608`: SQL injection via string formatting
- `B106`: Hardcoded password
- `B324`: Insecure hash function

### 4. mypy

**Purpose**: Static type checker for Python

**What it checks:**
- Type hint violations
- Type compatibility
- Missing return types
- Incompatible argument types
- Optional type usage

**Configuration** (`mypy.ini` or `pyproject.toml`):
```toml
[tool.mypy]
python_version = "3.11"
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_any_unimported = false
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
check_untyped_defs = true
strict_optional = true

[[tool.mypy.overrides]]
module = "tests.*"
disallow_untyped_defs = false
```

**Command line**:
```bash
mypy src/
```

## Project Configuration

### Basic Configuration

Create `.github/ai-review-config.yml` in your project:

```yaml
# Python-specific configuration
review_aspects:
  - name: python_static_analysis
    enabled: true
    type: classical
    tools:
      - ruff
      - pylint
      - bandit
      - mypy
    parallel: true

# Custom rules for Python
custom_rules:
  - pattern: "eval\\("
    message: "Use of eval() is a security risk"
    severity: "critical"

  - pattern: "exec\\("
    message: "Use of exec() is a security risk"
    severity: "critical"

  - pattern: "import pickle"
    message: "Pickle is insecure for untrusted data"
    severity: "high"

  - pattern: "password.*=.*['\"].*['\"]"
    message: "Hardcoded password detected"
    severity: "critical"
```

### Python Project Constraints

Add Python-specific constraints:

```yaml
project_constraints:
  - "All functions must have type hints"
  - "All public APIs must have docstrings"
  - "Use dataclasses or Pydantic for structured data"
  - "Async functions must handle CancelledError"
  - "Database operations must use async context managers"
```

### Blocking Rules

Configure when to block merges:

```yaml
blocking_rules:
  block_on_critical: true
  block_on_high: true
  max_findings:
    critical: 0    # Zero tolerance for security issues
    high: 3        # Allow up to 3 high-severity issues
    medium: 15
```

## Working Examples

### Example 1: FastAPI Project

See [`examples/python-fastapi-config.yml`](../examples/python-fastapi-config.yml):

```yaml
project_context:
  name: "FastAPI Microservice"
  architecture: "Async REST API"
  critical_paths:
    - "app/api/routes/"
    - "app/core/security.py"

project_constraints:
  - "All API routes must have Depends(get_current_user)"
  - "Use Pydantic models for request/response validation"
  - "Database operations must use async SQLAlchemy"
  - "All endpoints must have proper error handling"

custom_rules:
  - pattern: "@router\\.(get|post|put|delete).*\\n[^@]*def (?!.*Depends)"
    message: "API endpoint missing authentication dependency"
    severity: "critical"
```

### Example 2: Data Science Project

Configuration for ML/data projects:

```yaml
project_context:
  name: "ML Pipeline"
  architecture: "Data Processing"

project_constraints:
  - "Use NumPy/Pandas for data manipulation"
  - "All experiments must be reproducible (set seeds)"
  - "Model artifacts must be versioned"
  - "Large datasets must use streaming/batching"

custom_rules:
  - pattern: "pd\\.read_csv\\([^,)]*\\)(?!.*chunksize)"
    message: "Large CSV files should use chunksize parameter"
    severity: "medium"
```

## Common Issues and Fixes

### Issue: Type Checking Fails on Third-Party Libraries

**Problem**: mypy complains about missing type stubs

**Solution**:
```bash
# Install type stubs
pip install types-requests types-redis types-python-dateutil

# Or ignore specific modules in mypy.ini
[[tool.mypy.overrides]]
module = "untyped_library.*"
ignore_missing_imports = true
```

### Issue: Too Many Style Warnings

**Problem**: Ruff/Pylint generates hundreds of warnings

**Solution**: Gradually enable rules
```toml
[tool.ruff]
# Start with minimal rules
select = ["E", "F"]

# Add more over time
# select = ["E", "F", "I", "B", "C4"]
```

### Issue: Bandit False Positives

**Problem**: Bandit flags safe code (e.g., assert in tests)

**Solution**:
```python
# Inline suppression
result = subprocess.run(cmd, shell=True)  # nosec B602

# Or configure in pyproject.toml
[tool.bandit]
skips = ["B101"]  # Skip assert warnings in tests
```

### Issue: Slow Analysis on Large Codebase

**Problem**: Analysis takes too long in CI

**Solution**:
```yaml
# Only analyze changed files
with:
  analyze-changed-files-only: true

# Or cache dependencies
- name: Cache Python packages
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ hashFiles('**/requirements.txt') }}
```

## Integration with IDE

### VS Code

Install extensions:
- Ruff (charliermarsh.ruff)
- Pylint (ms-python.pylint)
- Mypy Type Checker (ms-python.mypy-type-checker)

Settings (`.vscode/settings.json`):
```json
{
  "python.linting.enabled": true,
  "python.linting.ruffEnabled": true,
  "python.linting.pylintEnabled": true,
  "python.linting.banditEnabled": true,
  "python.linting.mypyEnabled": true,
  "editor.formatOnSave": true,
  "python.formatting.provider": "black"
}
```

### PyCharm

1. Settings → Tools → External Tools
2. Add Ruff, Bandit, mypy as external tools
3. Configure file watchers for auto-run

## Performance Optimization

### Caching Strategy

```yaml
# In your workflow
- name: Cache Analysis Tools
  uses: actions/cache@v3
  with:
    path: |
      ~/.cache/pip
      ~/.cache/pylint
      .mypy_cache
      .ruff_cache
    key: python-analysis-${{ hashFiles('**/requirements.txt') }}
```

### Parallel Execution

The pipeline automatically runs tools in parallel:
- Ruff, Pylint, Bandit, mypy run concurrently
- Reduces analysis time by ~60%

### Changed Files Only

```yaml
with:
  analyze-changed-files-only: true
  # Only analyze files changed in the PR
```

## Best Practices

1. **Start Simple**: Begin with Ruff only, add tools gradually
2. **Configure Incrementally**: Don't enable all rules at once
3. **Document Suppressions**: Explain why you're ignoring specific warnings
4. **Keep Tools Updated**: Run `pip install --upgrade ruff pylint bandit mypy`
5. **Use Pre-commit Hooks**: Catch issues before pushing
6. **Set Team Standards**: Agree on rules in company config

## Pre-commit Integration

Install pre-commit hooks for local development:

`.pre-commit-config.yaml`:
```yaml
repos:
  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.1.6
    hooks:
      - id: ruff
        args: [--fix]
      - id: ruff-format

  - repo: https://github.com/PyCQA/bandit
    rev: 1.7.5
    hooks:
      - id: bandit
        args: ['-c', 'pyproject.toml']

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.7.1
    hooks:
      - id: mypy
        additional_dependencies: [types-all]
```

Install:
```bash
pip install pre-commit
pre-commit install
```

## Dependencies

### Using UV (Recommended)

```bash
uv add --dev ruff pylint bandit mypy
uv add --dev types-requests types-redis types-python-dateutil
```

Your `pyproject.toml`:
```toml
[project]
name = "my-project"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.104.0",
]

[tool.uv]
dev-dependencies = [
    "ruff>=0.1.6",
    "pylint>=3.0.0",
    "bandit>=1.7.5",
    "mypy>=1.7.0",
    "types-requests",
]
```

### Using Poetry

```bash
poetry add --group dev ruff pylint bandit mypy
poetry add --group dev types-requests types-redis
```

Your `pyproject.toml`:
```toml
[tool.poetry.group.dev.dependencies]
ruff = "^0.1.6"
pylint = "^3.0.0"
bandit = "^1.7.5"
mypy = "^1.7.0"
types-requests = "^2.31.0"
```

### Using requirements.txt (Traditional)

`requirements-dev.txt`:
```
ruff>=0.1.6
pylint>=3.0.0
bandit>=1.7.5
mypy>=1.7.0
types-requests
types-redis
types-python-dateutil
```

## Troubleshooting

### Tool Not Found Error

**Solution**: Ensure tools are installed in workflow
```yaml
- name: Install Analysis Tools
  run: |
    pip install ruff pylint bandit mypy
```

### Configuration Not Applied

**Solution**: Check file names and locations
- Ruff: `.ruff.toml` or `pyproject.toml`
- Pylint: `.pylintrc` or `pyproject.toml`
- Bandit: `.bandit` or `pyproject.toml`
- mypy: `mypy.ini` or `pyproject.toml`

### Too Many False Positives

**Solution**: Tune configuration and use suppressions judiciously

## Next Steps

1. Review [AI_CONFIGURATION.md](AI_CONFIGURATION.md) for AI-powered review setup
2. Check [examples/python-fastapi-config.yml](../examples/python-fastapi-config.yml) for working configurations
3. See main [README.md](../README.md) for overall architecture

## Resources

- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pylint Documentation](https://pylint.readthedocs.io/)
- [Bandit Documentation](https://bandit.readthedocs.io/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [Python Type Hints (PEP 484)](https://peps.python.org/pep-0484/)
