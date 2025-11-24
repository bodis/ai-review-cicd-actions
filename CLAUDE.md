# AI Code Review Pipeline - Claude Context

## Project Type

**Code review automation system** - An installable Python package that other projects use.

**Key characteristic**: This is distributed as a pip-installable package. Changes affect downstream users.

---

## Critical Architecture Points

### 1. Package-Based Distribution

This project is distributed as a **Python package** (`ai_review`), not just source files.

**Installation:**
```bash
# From git (recommended for CI)
uv pip install "ai-review-cicd-actions @ git+https://github.com/bodis/ai-review-cicd-actions.git@v1.0.0"

# Local development
uv sync
```

**CLI usage:**
```bash
uv run ai-review --repo owner/repo --pr 123
```

### 2. Self-Reviewing System

**This project reviews itself using its own review system.**

```
PR → .github/workflows/ai-code-review.yml
  → uv run ai-review --config .github/ai-review-config.yml
  → review_aspects:
     ├─ python_static_analysis (Ruff, Pylint, Bandit, mypy)
     ├─ security_review (AI)
     └─ other AI reviews
```

**DO NOT add separate CI workflows for quality checks** - they already run via the review system.

### 3. Platform Abstraction

Supports both GitHub and GitLab via clean abstraction:

- `ai_review/platform/base.py` - Abstract interface + `PlatformReporter`
- `ai_review/platform/github_platform.py` - GitHub implementation
- `ai_review/platform/gitlab_platform.py` - GitLab implementation
- `ai_review/platform/factory.py` - Auto-detection + config loading

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

### 4. Bundled Resources

Prompts and default config are **bundled inside the package**:

```
ai_review/
├── prompts/           # Bundled prompts (fallback)
│   ├── security-review.md
│   ├── architecture-review.md
│   └── ...
├── config/            # Bundled defaults
│   └── default-config.yml
└── resources.py       # Resource loader with fallback logic
```

**Prompt loading order:**
1. `project/prompts/` (user override)
2. `project/.github/prompts/` (GitHub convention)
3. `project/.gitlab/prompts/` (GitLab convention)
4. Bundled `ai_review/prompts/` (fallback)

### 5. Deduplication Systems

Two separate deduplication mechanisms:

| System | File | Purpose |
|--------|------|---------|
| **Finding Deduplication** | `ai_review/ai_deduplication.py` | Merges duplicate findings *within a single run* (before posting) |
| **Comment Deduplication** | `ai_review/comment_deduplication.py` | Prevents duplicate comments *across multiple runs* on same PR |

Both use Claude Haiku for fast, cheap AI comparison. Config in `ai_review/config/default-config.yml`.

### 6. Configuration Layers

Three-level precedence:
1. `ai_review/config/default-config.yml` - Built-in defaults (bundled)
2. Company policies (remote) - Organization standards
3. `.github/ai-review-config.yml` or `.gitlab/ai-review-config.yml` - Project-specific

Tools (Ruff, Pylint, etc.) read config from `pyproject.toml`.

### 7. Claude Code CLI Integration

**The Python package spawns Claude Code CLI as a subprocess for AI reviews.**

```
ai-review (Python CLI)
    │
    └─→ subprocess.run(["claude", ...])  # ai_review/ai_review.py:106-122
            │
            └─→ Claude Code CLI (Node.js)
                    │
                    └─→ Anthropic API
```

**CI/CD implications:**
- Claude Code CLI must be installed: `npm install -g @anthropic-ai/claude-code`
- The `claude` command must be in PATH when `ai-review` runs
- `ANTHROPIC_API_KEY` env var must be set (passed to subprocess)

**Why this architecture:**
- Claude Code CLI provides robust Claude interaction with retries, streaming, tool use
- Python package handles orchestration, static analysis, platform integration
- Separation allows each component to be updated independently

---

## Project Structure

```
ai_review/                # Main package (pip-installable)
├── __init__.py
├── cli.py               # CLI entry point (ai-review command)
├── resources.py         # Bundled resource loader
├── orchestrator.py      # Pipeline coordinator
├── ai_review.py         # Claude integration
├── config_manager.py    # Multi-level config system
├── models.py            # Data models
├── platform/            # Platform abstraction (GitHub/GitLab)
├── analyzers/           # Static analysis tools (Python, JS, Java)
├── prompts/             # Bundled AI prompts
└── config/              # Bundled default config

.github/
├── workflows/
│   ├── ai-code-review.yml      # CI for THIS project
│   └── reusable-ai-review.yml  # Reusable workflow for other projects
└── ai-review-config.yml        # Review configuration for THIS project

docs/                    # Integration guides
tests/                   # Unit tests
```

---

## Control Points: Before Making Changes

### ALWAYS Check These First

```bash
# 1. Does this functionality already exist?
cat .github/ai-review-config.yml          # Review aspects
cat ai_review/analyzers/python_analyzer.py # Static analysis tools

# 2. What runs in CI?
cat .github/workflows/ai-code-review.yml

# 3. Where are tools configured?
grep "\[tool\." pyproject.toml

# 4. Test the CLI
uv run ai-review --help
```

### Common Mistake to Avoid

- **Don't create**: `.github/workflows/code-quality.yml` or similar
- Ruff/Pylint/Bandit/mypy already run via `python_static_analysis` aspect
- Would cause double-execution

**Instead**: Modify `.github/ai-review-config.yml` or `pyproject.toml`

---

## Key Files to Understand

| File | Purpose | Why Important |
|------|---------|---------------|
| `ai_review/cli.py` | CLI entry point | `ai-review` command |
| `ai_review/resources.py` | Resource loader | Bundled prompts/config with fallback |
| `ai_review/orchestrator.py` | Pipeline | Coordinates all review aspects |
| `ai_review/platform/base.py` | Abstraction | Platform-agnostic interface |
| `.github/ai-review-config.yml` | Review config | Defines what runs on THIS project |
| `pyproject.toml` | Package + tool config | Package metadata, Ruff/Pylint settings |

---

## Dependencies

**Package Manager**: UV (modern Python package manager)

```bash
uv sync                 # Install dependencies
uv add package-name     # Add dependency
uv run pytest           # Run tests
uv run ai-review        # Run CLI
```

**Python**: 3.11+

**Key Dependencies**:
- `PyGithub` - GitHub API
- `python-gitlab` - GitLab API
- `anthropic` - Claude API (for deduplication only)
- Static analysis tools (Ruff, Pylint, Bandit, mypy)

**External Runtime Dependency**:
- `@anthropic-ai/claude-code` (Node.js) - Claude Code CLI, spawned as subprocess for AI reviews

---

## Development Workflow

### Local Testing

```bash
# Format and check
uv run ruff check ai_review/
uv run pytest tests/

# Test CLI
uv run ai-review --help

# Run full review on a PR (requires ANTHROPIC_API_KEY)
uv run ai-review --repo owner/repo --pr 123 --config .github/ai-review-config.yml
```

### Adding Language Support

1. Create `ai_review/analyzers/newlang_analyzer.py` extending `BaseAnalyzer`
2. Register in `ai_review/orchestrator.py`
3. Add language extension to `LANGUAGE_EXTENSIONS` in platform implementations
4. Document in `docs/NEWLANG_INTEGRATION.md`

### Adding AI Review Aspect

1. Create prompt in `ai_review/prompts/new-aspect.md`
2. Add to `ai_review/config/default-config.yml`:
```yaml
review_aspects:
  - name: new_aspect_review
    type: ai
    prompt_file: prompts/new-aspect.md
```

---

## For AI Assistants

### Investigation Protocol

**Before implementing any change:**

1. Read this file
2. Check if functionality exists (see Control Points above)
3. Consider downstream impact (this is a distributed package!)
4. **Ask user if unclear** - show what exists, explain options

### Safe vs Risky Changes

**Safe**:
- Documentation (`docs/*.md`, `README.md`)
- Prompts in `ai_review/prompts/`
- Tool configs in `pyproject.toml`

**Risky** (discuss first):
- New workflows in `.github/workflows/`
- Changes to `ai_review/cli.py` or `ai_review/platform/`
- Changes to `pyproject.toml` package metadata
- Changes to core orchestration

### The Rule

**"If it already works via the review system, don't add a separate workflow for it."**

---

## Documentation

- `README.md` - Overview and quick start
- `docs/ARCHITECTURE.md` - Platform abstraction details
- `docs/GITHUB.md` - GitHub Actions integration
- `docs/GITLAB.md` - GitLab CI integration
- `docs/PYTHON_INTEGRATION.md` - Python analyzer setup
- `docs/JAVASCRIPT_INTEGRATION.md` - JS/TS analyzer setup
- `docs/AI_CONFIGURATION.md` - Claude model and prompt configuration
