# AI Code Review Pipeline - Claude Code Context

## Project Overview

This is a **research demonstration project** implementing multi-layered code review pipeline patterns to mitigate risks in AI-assisted development. Based on research documented at https://bodis.github.io/website/blog/2025/11/01/ai-coding-reality-check-index/

**Key Insight**: This addresses three systemic problems:
1. 47% exploitable vulnerability rate in AI-generated code
2. Accelerated architecture drift (93% negative business outcomes)
3. "Almost right, but not quite" semantic correctness issues (66% frustration)

**What it is**: Working demonstration of defense-in-depth review patterns
**What it is NOT**: Production-ready enterprise solution

## Architecture

### Core Pattern: Multi-Layer Defense

```
PR Event
  ↓
Context Extraction (files, diff, languages)
  ↓
Change Detection (dependencies, security patterns, breaking changes)
  ↓
Configuration Merge (default → company → project)
  ↓
Review Execution
  ├─ Classical Tools (parallel): Ruff, ESLint, SpotBugs, etc.
  └─ AI Reviews (sequential with context): Security, Architecture, Quality, Performance, Testing
  ↓
Result Aggregation (deduplicate, categorize)
  ↓
Blocking Rules (severity thresholds)
  ↓
GitHub Reporting (comments, status checks)
```

### Key Design Decisions

1. **Hybrid Analysis**: Classical tools catch patterns, AI understands semantics
2. **Sequential AI Reviews**: Later reviews see earlier findings for better context
3. **Policy Injection**: Company/project constraints injected into AI prompts
4. **Change Detection**: Automatically identifies dependency changes, security risks, breaking changes
5. **Fail-Safe Defaults**: Block on uncertainty, require explicit approval

## Project Structure

```
├── lib/                          # Core implementation
│   ├── analyzers/               # Language-specific static analysis
│   │   ├── base_analyzer.py    # Abstract base class
│   │   ├── python_analyzer.py  # Ruff, Pylint, Bandit, mypy
│   │   └── javascript_analyzer.py  # ESLint, Prettier, TSC
│   ├── orchestrator.py          # Pipeline coordinator
│   ├── pr_context.py            # PR analysis & change detection
│   ├── config_manager.py        # Multi-level config system
│   ├── injection.py             # Policy injection into prompts
│   ├── ai_review.py             # Claude integration
│   ├── github_reporter.py       # PR feedback
│   └── models.py                # Data models
│
├── prompts/                      # AI review prompts
│   ├── security-review.md       # OWASP Top 10, auth flaws
│   ├── architecture-review.md   # SOLID, patterns, drift
│   ├── base-review.md           # Code quality, maintainability
│   ├── performance-review.md    # N+1 queries, algorithms
│   └── testing-review.md        # Coverage, edge cases
│
├── docs/                         # Specialized integration guides
│   ├── PYTHON_INTEGRATION.md    # Ruff, Pylint, Bandit, mypy
│   ├── JAVASCRIPT_INTEGRATION.md # ESLint, Prettier, TSC
│   ├── JAVA_INTEGRATION.md      # SpotBugs, PMD, Checkstyle, OWASP
│   └── AI_CONFIGURATION.md      # Claude setup, prompts, costs
│
├── examples/                     # Working configurations
│   ├── project-config.yml       # Python FastAPI example
│   ├── company-policies.yml     # Organization standards
│   └── java-workflow-example.yml # Complete Java workflow
│
├── config/
│   └── default-config.yml       # Built-in baseline
│
└── main.py                       # CLI entry point
```

## Supported Languages

| Language | Tools | Implementation |
|----------|-------|----------------|
| **Python** | Ruff, Pylint, Bandit, mypy | `lib/analyzers/python_analyzer.py` |
| **JavaScript/TypeScript** | ESLint, Prettier, TSC | `lib/analyzers/javascript_analyzer.py` |
| **Java** | SpotBugs, PMD, Checkstyle, JaCoCo, OWASP | Documented, not yet implemented |

AI reviews are language-agnostic and work across all languages.

## Configuration System

### Three-Level Precedence

```
1. Default Config (built-in)
   ↓ (overridden by)
2. Company Policies (github://org/policies/main/code-review.yml)
   ↓ (overridden by)
3. Project Config (.github/ai-review-config.yml)
```

### Key Configuration Files

**Project Config** (`.github/ai-review-config.yml`):
```yaml
project_context:
  name: "Payment API"
  architecture: "FastAPI Microservice"
  critical_paths:
    - "src/payment/"
    - "src/auth/"

project_constraints:
  - "All payment operations must be idempotent"
  - "Use Decimal for monetary values"

review_aspects:
  - name: python_static_analysis
    enabled: true
    parallel: true
  - name: security_review
    enabled: true
    parallel: false

blocking_rules:
  block_on_critical: true
  max_findings:
    critical: 0
    high: 3
```

**Company Policies** (remote):
```yaml
coding_standards:
  python:
    - "Use type hints for all function signatures"
    - "Maximum function length: 50 lines"

security_requirements:
  - "All API endpoints must have authentication"
  - "Secrets must be stored in environment variables"
```

## Change Detection System

**Location**: `lib/pr_context.py`

**Detected Types**:
- `DEPENDENCY_CHANGE`: pyproject.toml, uv.lock, poetry.lock, package.json, pom.xml
- `TEST_CHANGE`: Modified test files
- `SECURITY_RISK`: eval(), exec(), hardcoded secrets, weak crypto
- `BREAKING_CHANGE`: Removed exports, "BREAKING CHANGE" markers
- `DOCUMENTATION`: README, docs changes
- `FEATURE`: Default for code changes

**How It's Used**:
1. Displayed in console output during execution
2. Injected into AI review prompts for context-aware analysis
3. Included in PR summary comments
4. Influences impact scoring and risk levels

**Impact Formula**:
```
Impact Score = (files × 5) + (total changes ÷ 10) + (change types × 10)
Risk Level = High (>70) | Medium (40-70) | Low (<40)
```

## AI Review System

**Implementation**: `lib/ai_review.py`

**Review Aspects** (sequential execution for context sharing):
1. **Security Review** (`prompts/security-review.md`)
   - OWASP Top 10, SQL injection, XSS, auth bypass
2. **Architecture Review** (`prompts/architecture-review.md`)
   - SOLID principles, layer violations, design patterns
3. **Code Quality Review** (`prompts/base-review.md`)
   - Complexity, duplication, maintainability
4. **Performance Review** (`prompts/performance-review.md`)
   - N+1 queries, algorithm efficiency, caching
5. **Testing Review** (`prompts/testing-review.md`)
   - Coverage, edge cases, test quality

**Prompt Injection Flow** (`lib/injection.py`):
```
Base Prompt
  + Company Policies
  + Project Constraints
  + Project Context (architecture, critical paths)
  + Change Types (from detection)
  + PR Diff
  = Final Prompt sent to Claude
```

## Python Dependency Management

**This project uses UV**: Modern, fast Python package manager

**Project Structure**:
- `pyproject.toml` - Project metadata, dependencies, tool configs
- `uv.lock` - Locked dependency versions (generated by UV)
- No `requirements.txt` or `pytest.ini` (migrated to pyproject.toml)

**Why UV?**:
- 10-100x faster than pip/poetry
- Single tool for packages, environments, and Python versions
- Compatible with standard Python packaging (PEP 621)
- Global cache for space efficiency

**Your projects can use**:
- UV: `pyproject.toml` + `uv.lock` ✅ Recommended
- Poetry: `pyproject.toml` + `poetry.lock`
- pip-tools: `requirements.in` + `requirements.txt`
- Traditional: `requirements.txt`

**Detection**: `lib/pr_context.py` DEPENDENCY_FILES dict recognizes all formats

## Development Workflow

### Setup

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Install all dependencies (creates .venv if needed)
uv sync

# Activate virtual environment
source .venv/bin/activate

# Verify setup (within venv)
python --version
pytest --version
```

**IMPORTANT for AI Assistants**: This project uses UV for dependency management. Two equivalent approaches:

1. **UV run (recommended)**: `uv run pytest` - UV manages the venv automatically
2. **Manual venv**: `source .venv/bin/activate && pytest` - Traditional Python workflow

Both work identically. Use `uv run` for consistency with project documentation.

### Running Locally

```bash
uv run python main.py \
  --repo owner/repo \
  --pr 123 \
  --config .github/ai-review-config.yml \
  --company-config github://your-org/policies/main/code-review.yml \
  --output results.json
```

### Testing

```bash
uv run pytest                          # Run all tests
uv run pytest --cov=lib --cov-report=html  # With coverage (optional)
uv run pytest tests/test_models.py -v  # Specific test file
uv run pytest -m unit                  # Only unit tests
```

### Adding Dependencies

```bash
# These commands work outside venv (UV manages the environment)
uv add package-name        # Production dependency
uv add --dev package-name  # Dev dependency
uv lock --upgrade          # Update all dependencies
uv sync                    # Sync venv after changes
```

### Adding New Language Analyzer

1. Create `lib/analyzers/newlang_analyzer.py` extending `BaseAnalyzer`
2. Implement:
   - `setup_tool()`: Install/configure tools
   - `run_analysis(files)`: Execute analysis
   - `parse_results()`: Convert to standard format
   - `map_severity()`: Map tool severity to standard levels
3. Register in `lib/orchestrator.py`
4. Add language extension to `pr_context.py` LANGUAGE_EXTENSIONS
5. Document in `docs/NEWLANG_INTEGRATION.md`

### Adding New AI Review Aspect

1. Create prompt file in `prompts/new-aspect.md`
2. Define clear instructions and JSON output format
3. Add to default config `config/default-config.yml`:
```yaml
review_aspects:
  - name: new_aspect_review
    enabled: true
    type: ai
    prompt_file: prompts/new-aspect.md
    parallel: false
```

## Important Implementation Notes

### What IS Implemented

✅ PR context extraction with GitHub API
✅ Change detection (6 types)
✅ Impact scoring and risk levels
✅ Multi-level configuration merge
✅ Policy injection into AI prompts
✅ Python analyzer (Ruff, Pylint, Bandit, mypy)
✅ JavaScript analyzer (ESLint, Prettier, TSC)
✅ Claude integration with retry logic
✅ Result aggregation and deduplication
✅ GitHub PR commenting and status checks
✅ Blocking rules based on severity

### What is NOT Implemented

❌ Java analyzer (documented only, see `docs/JAVA_INTEGRATION.md`)
❌ Advanced dependency vulnerability scanning
❌ Semantic diff analysis (AST-level)
❌ Historical learning from past reviews
❌ Auto-fix generation
❌ Cross-repository impact analysis
❌ Performance benchmarking
❌ Visual regression testing

### Known Limitations

- **Demo quality**: Missing comprehensive error handling
- **No caching**: Static analysis tools re-run fully each time
- **Limited scale testing**: Not tested on large repositories (>1000 files)
- **No metrics/observability**: No detailed performance tracking
- **Basic secrets management**: Environment variables only
- **Single repository**: No multi-repo orchestration

## Research Context

This project demonstrates patterns from "The Hard Parts of AI-Assisted Development" research:

**Problem 1: Security Vulnerability Rate (47%)**
→ **Solution**: Multi-layer defense with both pattern-based (Bandit, ESLint security) and semantic (AI) analysis

**Problem 2: Architecture Drift (93% negative outcomes)**
→ **Solution**: AI architecture review + policy injection + change detection

**Problem 3: Semantic Correctness ("almost right")**
→ **Solution**: AI reviews understand context and intent, not just syntax

## Common Tasks

### Updating Documentation

After code changes, update relevant docs:
- Core changes → Update this CLAUDE.md
- Language changes → Update `docs/{PYTHON,JAVASCRIPT,JAVA}_INTEGRATION.md`
- AI/prompts → Update `docs/AI_CONFIGURATION.md`
- Examples → Update files in `examples/`
- Overview → Update main `README.md`

### Adding Company Policy

1. Create `company-policies.yml` in central repo
2. Add standards under `coding_standards`, `security_requirements`, `architectural_rules`
3. Reference in workflow: `company-config-url: 'github://org/policies/main/code-review.yml'`
4. Policies auto-inject into AI prompts via `lib/injection.py`

### Debugging Review Issues

1. Check orchestrator output: `python main.py --repo ... --pr ...`
2. Look for change detection output: "Change types: ..."
3. Verify AI prompt injection: Check `lib/injection.py` logs
4. Review GitHub API calls: Check `lib/github_reporter.py`
5. Test analyzer individually: Import and run in Python REPL

## References

- Research article: https://bodis.github.io/website/blog/2025/11/01/ai-coding-reality-check-index/
- Main README: [`README.md`](../README.md)
- Python guide: [`docs/PYTHON_INTEGRATION.md`](../docs/PYTHON_INTEGRATION.md)
- JavaScript guide: [`docs/JAVASCRIPT_INTEGRATION.md`](../docs/JAVASCRIPT_INTEGRATION.md)
- Java guide: [`docs/JAVA_INTEGRATION.md`](../docs/JAVA_INTEGRATION.md)
- AI config: [`docs/AI_CONFIGURATION.md`](../docs/AI_CONFIGURATION.md)

## For Future AI Assistants

When working on this project:

1. **Remember the scope**: This is a demonstration, not production software
2. **Prioritize clarity**: Code should be readable and educational
3. **Document extensively**: Each pattern should be clear for learning
4. **Test thoroughly**: Even demos should work correctly
5. **Update all docs**: Keep README, guides, and this file in sync
6. **Maintain research context**: Keep focus on mitigating the three core problems
7. **Don't over-engineer**: Simple, clear patterns > complex abstractions

The goal is to demonstrate effective patterns, not to build enterprise software.
