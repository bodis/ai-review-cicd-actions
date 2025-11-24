# AI Code Review Pipeline - Claude Context

## Project Type

**Code review automation system** - A library/framework that other projects use.

**Key characteristic**: Changes here affect downstream users who copy/reference this repo.

---

## Critical Architecture Points

### 1. Self-Reviewing System

**This project reviews itself using its own review system.**

```
PR → .github/workflows/ai-code-review.yml
  → main.py --config .github/ai-review-config.yml
  → review_aspects:
     ├─ python_static_analysis (Ruff, Pylint, Bandit, mypy)
     ├─ security_review (AI)
     └─ other AI reviews
```

**DO NOT add separate CI workflows for quality checks** - they already run via the review system.

### 2. Platform Abstraction

Supports both GitHub and GitLab via clean abstraction:

- `lib/platform/base.py` - Abstract interface + `PlatformReporter`
- `lib/platform/github_platform.py` - GitHub implementation
- `lib/platform/gitlab_platform.py` - GitLab implementation
- `lib/platform/factory.py` - Auto-detection + config loading

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for details.

### 3. Deduplication Systems

Two separate deduplication mechanisms:

| System | File | Purpose |
|--------|------|---------|
| **Finding Deduplication** | `lib/ai_deduplication.py` | Merges duplicate findings *within a single run* (before posting) |
| **Comment Deduplication** | `lib/comment_deduplication.py` | Prevents duplicate comments *across multiple runs* on same PR |

Both use Claude Haiku for fast, cheap AI comparison. Config in `config/default-config.yml`.

### 4. Configuration Layers

Three-level precedence:
1. `config/default-config.yml` - Built-in defaults
2. Company policies (remote) - Organization standards
3. `.github/ai-review-config.yml` - Project-specific

Tools (Ruff, Pylint, etc.) read config from `pyproject.toml`.

---

## Project Structure

```
lib/
├── platform/          # Platform abstraction (GitHub/GitLab)
├── analyzers/         # Static analysis tools (Python, JS, Java)
├── orchestrator.py    # Pipeline coordinator
├── ai_review.py       # Claude integration
├── config_manager.py  # Multi-level config system
└── models.py          # Data models

.github/
├── workflows/
│   └── ai-code-review.yml    # Single CI workflow (runs on this project)
└── ai-review-config.yml      # Review configuration for THIS project

prompts/               # AI review prompts (security, architecture, etc.)
config/                # Default configurations
docs/                  # Integration guides
```

---

## Control Points: Before Making Changes

### ⚠️ ALWAYS Check These First

```bash
# 1. Does this functionality already exist?
cat .github/ai-review-config.yml    # Review aspects
cat lib/analyzers/python_analyzer.py # Static analysis tools

# 2. What runs in CI?
cat .github/workflows/ai-code-review.yml

# 3. Where are tools configured?
grep "\[tool\." pyproject.toml
```

### Common Mistake to Avoid

❌ **Don't create**: `.github/workflows/code-quality.yml` or similar
- Ruff/Pylint/Bandit/mypy already run via `python_static_analysis` aspect
- Would cause double-execution
- Downstream projects would inherit it

✅ **Instead**: Modify `.github/ai-review-config.yml` or `pyproject.toml`

### Impact Questions

Before adding files to `.github/workflows/`:

1. Will projects that copy this repo inherit it?
2. Is this specific to THIS project or general-purpose?
3. Does this duplicate existing functionality?

---

## Key Files to Understand

| File | Purpose | Why Important |
|------|---------|---------------|
| `main.py` | Entry point | Platform-agnostic review execution |
| `lib/orchestrator.py` | Pipeline | Coordinates all review aspects |
| `lib/analyzers/python_analyzer.py` | Static analysis | Runs Ruff, Pylint, Bandit, mypy |
| `.github/ai-review-config.yml` | Review config | Defines what runs on THIS project |
| `pyproject.toml` | Tool config | Ruff/Pylint/Bandit/mypy settings |

---

## Dependencies

**Package Manager**: UV (modern Python package manager)

```bash
uv sync                 # Install dependencies
uv add package-name     # Add dependency
uv run pytest           # Run tests
```

**Python**: 3.11+

**Key Dependencies**:
- `PyGithub` - GitHub API
- `python-gitlab` - GitLab API
- `anthropic` - Claude API
- Static analysis tools (Ruff, Pylint, Bandit, mypy)

---

## Development Workflow

### Local Testing

```bash
# Format and check (no AI review)
make format
make lint
make test

# Run full review on a PR (requires ANTHROPIC_API_KEY)
python main.py --repo owner/repo --pr 123 --config .github/ai-review-config.yml
```

### Adding Language Support

1. Create `lib/analyzers/newlang_analyzer.py` extending `BaseAnalyzer`
2. Register in `lib/orchestrator.py`
3. Add language extension to `LANGUAGE_EXTENSIONS` in platform implementations
4. Document in `docs/NEWLANG_INTEGRATION.md`

### Adding AI Review Aspect

1. Create prompt in `prompts/new-aspect.md`
2. Add to `config/default-config.yml`:
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

1. ✅ Read this file
2. ✅ Check if functionality exists (see Control Points above)
3. ✅ Consider downstream impact
4. ✅ **Ask user if unclear** - show what exists, explain options

### Safe vs Risky Changes

**Safe**:
- ✅ Documentation (`docs/*.md`, `README.md`)
- ✅ Makefile (local dev only)
- ✅ Tool configs in `pyproject.toml`
- ✅ Prompts in `prompts/`

**Risky** (discuss first):
- ⚠️ New workflows in `.github/workflows/`
- ⚠️ Changes to `main.py` or `lib/platform/`
- ⚠️ Changes to core orchestration

### The Rule

**"If it already works via the review system, don't add a separate workflow for it."**

---

## Documentation

- `README.md` - Overview and quick start
- `docs/ARCHITECTURE.md` - Platform abstraction details
- `docs/PYTHON_INTEGRATION.md` - Python analyzer setup
- `docs/JAVASCRIPT_INTEGRATION.md` - JS/TS analyzer setup
- `docs/AI_CONFIGURATION.md` - Claude model and prompt configuration

---

## Research Context

This project addresses three problems in AI-assisted development:
1. 47% exploitable vulnerability rate in AI-generated code
2. 93% architecture drift (negative business outcomes)
3. 66% "almost right, but not quite" semantic issues

**Design**: Multi-layer defense (static analysis + AI reviews) with policy injection.

**Goal**: Demonstrate effective patterns, not build enterprise software.
