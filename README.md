# 🤖 AI Code Review Pipeline - Research Demonstration

A demonstration of multi-layered, generalized code review pipeline architecture designed to mitigate risks in AI-assisted development. This project implements the technical mitigation strategies described in the research article [The Hard Parts of AI-Assisted Development](https://bodis.github.io/website/blog/2025/11/01/ai-coding-reality-check-index/).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![GitHub Actions](https://img.shields.io/badge/CI-GitHub%20Actions-2088FF?logo=github-actions)](https://github.com/features/actions)

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [Research Context](#research-context)
3. [Features](#features)
4. [Supported Languages](#supported-languages)
5. [Quick Start](#quick-start)
6. [Architecture](#architecture)
7. [Configuration](#configuration)
8. [Usage Examples](#usage-examples)
9. [Development](#development)
10. [Documentation](#documentation)
11. [Contributing](#contributing)
12. [License](#license)

---

## Overview

This is a **demonstration project**, not an enterprise-ready solution. It showcases how to implement a multi-layered, extensible code review pipeline that addresses the three critical problems identified in AI-assisted development research:

1. **Systematic security vulnerabilities** (47% exploitable bug rate in AI-generated code)
2. **Accelerated architecture drift** (93% negative business outcomes from doc misalignment)
3. **Inadequate review processes** (66% "almost right, but not quite" frustration rate)

The system combines classical static analysis tools with AI-driven reviews, demonstrating patterns for:

- 🏢 **Multi-level configuration** (default → company → project)
- 🔍 **Hybrid analysis** (classical tools + AI, each addressing different failure modes)
- 🌍 **Multi-language support** (Python, JS/TS, Java/Spring Boot)
- 🔒 **Security-first design** (OWASP patterns, CVE detection, context-aware vulnerability scanning)
- 📊 **Actionable feedback** (severity-based blocking, inline suggestions, statistical reporting)
- ⚙️ **Extensible architecture** (add new analyzers, review aspects, or policy layers)

### Core Principles

- **Defense in depth**: Multiple independent analysis layers catch different failure patterns
- **Fail-safe defaults**: Block on uncertainty, require explicit approval for high-risk changes
- **Layered execution**: Fast static checks first (parallel), deep semantic analysis later (sequential)
- **Structured output**: JSON schema with standardized severity, category, and evidence fields
- **Policy as code**: Company and project-specific constraints injected into review prompts
- **Extensible by design**: Add new languages, tools, or review aspects without core changes

---

## Research Context

This implementation is based on the analysis presented in [The Hard Parts of AI-Assisted Development](https://bodis.github.io/website/blog/2025/11/01/ai-coding-reality-check-index/), which synthesizes findings from:

- **Georgetown CSET**: 47% exploitable vulnerabilities in AI-generated code
- **METR study**: 19% slowdown for experienced developers on real codebases despite 24% predicted speedup
- **CodeSecEval**: Only 55% of AI-generated code passed security checks
- **GitClear analysis**: 50% increase in copy-paste code, 60% drop in refactoring between 2021-2024
- **Stack Overflow survey**: 38% report AI provides inaccurate information more than half the time

The research identifies three systemic problems that don't solve themselves through better prompting or newer models:

1. **Security performance hasn't improved** as models get better at syntax
2. **Architecture drift accelerates** because AI lacks understanding of system boundaries and organizational patterns
3. **Semantic correctness gaps** create "compiles but broken" code that passes type checking but fails in production

This project demonstrates the **Multi-Layer Defense Pattern** and **Multi-Agent Review System** architectures described in the technical mitigation section, showing how organizations can treat AI integration as a systems challenge rather than just a tooling problem.

---

## Features

### 🔍 Multi-Layered Review System

#### Classical Static Analysis

| Language | Tools | What They Check |
|----------|-------|-----------------|
| **Python** | Ruff, Pylint, Bandit, mypy | Style, bugs, security, type safety |
| **JavaScript/TypeScript** | ESLint, Prettier, TSC | Style, bugs, type errors |
| **Java/Spring Boot** | SpotBugs, PMD, Checkstyle, JaCoCo, OWASP Dependency-Check, ArchUnit | Bytecode bugs, code smells, style, coverage, CVEs, architecture |

**Free open-source tools** with optional **paid tool integration** (SonarQube, Qodana, Snyk, Codacy).

#### AI-Driven Reviews

Powered by Claude, specialized prompts for:

- 🔒 **Security Review** - OWASP Top 10, injection vulnerabilities, authentication flaws
- 🏗️ **Architecture Review** - SOLID principles, layering, design patterns
- ✨ **Code Quality Review** - Complexity, duplication, readability, maintainability
- ⚡ **Performance Review** - N+1 queries, algorithm efficiency, caching opportunities
- 🧪 **Testing Review** - Coverage, edge cases, test quality

### ⚙️ Flexible Configuration

```
┌─────────────────┐
│ Default Config  │  ← Built-in baseline
└────────┬────────┘
         ↓
┌─────────────────┐
│ Company Policies│  ← Organization-wide standards
└────────┬────────┘
         ↓
┌─────────────────┐
│ Project Config  │  ← Project-specific overrides
└─────────────────┘
```

- **Three-tier configuration**: Default → Company → Project with proper precedence
- **Policy injection**: Dynamic enforcement of coding standards in AI prompts
- **Custom rules**: Pattern-based detection for project-specific requirements
- **Remote config loading**: GitHub URLs, HTTP endpoints, S3 buckets

### 🚀 GitHub Integration

- ✅ **Automated PR comments** with summary and statistics
- ✅ **Inline comments** on specific lines for critical/high issues
- ✅ **Status checks** (pass/fail) that can block merging
- ✅ **Review events** (approve/request changes/comment)
- ✅ **Configurable blocking rules** based on severity thresholds

### 📊 Comprehensive Reporting

**Severity Levels:**
- 🔴 **Critical** - Exploitable vulnerabilities, critical bugs
- 🟠 **High** - Serious issues requiring immediate attention
- 🟡 **Medium** - Moderate concerns, code smells
- 🔵 **Low** - Minor improvements, suggestions
- ⚪ **Info** - Informational, best practices

**Categories:**
- 🔒 Security - Vulnerabilities, data exposure
- ⚡ Performance - Inefficient algorithms, N+1 queries
- 🏗️ Architecture - Pattern violations, coupling issues
- ✨ Code Quality - Complexity, duplication
- 🧪 Testing - Coverage, test quality
- 📚 Documentation - Missing docs, unclear code
- 🎨 Style - Formatting, conventions

---

## Supported Languages

| Language | Tools | What It Detects | Documentation |
|----------|-------|-----------------|---------------|
| **Python** | Ruff, Pylint, Bandit, mypy | Style, complexity, security, types | [Python Guide](docs/PYTHON_INTEGRATION.md) |
| **JavaScript/TypeScript** | ESLint, Prettier, TSC | Style, bugs, type errors | [JS/TS Guide](docs/JAVASCRIPT_INTEGRATION.md) |
| **Java/Spring Boot** | SpotBugs, PMD, Checkstyle, JaCoCo, OWASP | Bugs, security, CVEs, architecture | [Java Guide](docs/JAVA_INTEGRATION.md) |

**AI Reviews** (language-agnostic): Security, Architecture, Quality, Performance, Testing → [AI Guide](docs/AI_CONFIGURATION.md)

---

## Quick Start

### 🎯 Recommended: Simple Self-Review Pattern

**For single projects** (like this repository reviews itself):

See **[`self/`](self/)** directory for the **recommended simple pattern**:
- ✅ Single workflow file to copy
- ✅ Simple configuration
- ✅ No reusable workflow complexity
- ✅ Uses code from PR branch directly

**Copy and adapt**:
```bash
cp self/workflow.yml .github/workflows/ai-review.yml
cp self/config.yml .github/ai-review-config.yml
# Customize config.yml for your languages
```

See [self/README.md](self/README.md) for complete guide.

---

### 🏢 For Organizations: Reusable Workflow Pattern

**For 10+ repositories** with centralized review system:

This example shows the reusable workflow approach for organizations.

**Prerequisites**: Only one secret needed!
- ✅ `ANTHROPIC_API_KEY` - Get from [Anthropic Console](https://console.anthropic.com/)
- ❌ `GITHUB_TOKEN` - Automatically provided by GitHub Actions (don't add to secrets!)

**1. Ensure pyproject.toml** (your project):

```toml
[project]
name = "payment-api"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.104.0", "pydantic>=2.0"]

[tool.uv]
dev-dependencies = [
    "ruff>=0.1.6",
    "pytest>=7.4.0",
]
```

**2. Add Workflow File** (`.github/workflows/code-review.yml`):

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-python-analysis: true
      python-version: '3.11'
      company-config-url: 'github://your-org/policies/main/code-review.yml'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**3. Optional Project Configuration** (`.github/ai-review-config.yml`):

```yaml
project_context:
  name: "Payment API"
  architecture: "FastAPI Microservice"

project_constraints:
  - "All payment operations must be idempotent"
  - "Use Decimal for monetary values"

blocking_rules:
  block_on_critical: true
  max_findings:
    critical: 0
    high: 3
```

**4. Create a PR** - Reviews run automatically!

**What happens**:
- GitHub Actions installs UV (2-3 seconds, cached)
- UV installs Python + dependencies (5-10 seconds, cached)
- Classical analysis runs (Ruff, Pylint, Bandit, mypy)
- AI reviews analyze semantics (security, architecture, quality)
- Results posted as PR comments with blocking if configured

### Other Languages

- **JavaScript/TypeScript**: See [JS/TS Guide](docs/JAVASCRIPT_INTEGRATION.md)
- **Java/Spring Boot**: See [Java Guide](docs/JAVA_INTEGRATION.md) and [example workflow](examples/java-workflow-example.yml)
- **Multi-language projects**: Enable multiple analyzers in the same workflow

---

## Architecture

### System Overview

```
┌─────────────────────────────────────────────────┐
│              GitHub Pull Request                │
└────────────────────┬────────────────────────────┘
                     │
         ┌───────────▼───────────┐
         │  GitHub Actions       │
         │  Workflow Trigger     │
         └───────────┬───────────┘
                     │
    ┌────────────────┼────────────────┐
    │                │                │
┌───▼────┐    ┌─────▼─────┐    ┌────▼───────┐
│   PR   │───▶│   Config  │───▶│Orchestrator│
│Context │    │  Manager  │    │            │
└────────┘    └───────────┘    └──────┬─────┘
                                      │
            ┌─────────────────────────┼──────────────┐
            │                         │              │
    ┌───────▼─────────┐      ┌────────▼────┐         │
    │   Classical     │      │ AI Review   │         │
    │   Analyzers     │      │   Engine    │         │
    │                 │      │             │         │
    │ • Python        │      │ • Security  │         │
    │ • JavaScript    │      │ • Architect │         │
    │ • Java          │      │ • Quality   │         │
    └───────┬─────────┘      └──────┬──────┘         │
            │                       │                │
            └──────────┬────────────┘                │
                       │                             │
               ┌───────▼────────┐                    │
               │   Aggregator   │                    │
               │  • Deduplicate │                    │
               │  • Categorize  │                    │
               └───────┬────────┘                    │
                       │                             │
               ┌───────▼────────┐                    │
               │ Blocking Rules │                    │
               │    Checker     │                    │
               └───────┬────────┘                    │
                       │                             │
               ┌───────▼────────┐                    │
               │    GitHub      │                    │
               │   Reporter     │                    │
               │ • Comments     │                    │
               │ • Status Check │                    │
               └────────────────┘                    │
                                                     │
                            ┌────────────────────────▼──┐
                            │   Change Detection        │
                            │   • Architecture Drift    │
                            │   • Breaking Changes      │
                            │   • Security Risks        │
                            └───────────────────────────┘
```

### Validation Flow for Projects

Here's how a project can integrate this validation into their workflow:

```
┌──────────────────────────────────────────────────────────────┐
│                   Developer Workflow                         │
└──────────────────────────────────────────────────────────────┘

 1. Developer Creates PR
      ↓
 2. GitHub Actions Triggered
      ↓
┌─────────────────────────────────────────────────────────┐
│  Environment Validation                                 │
│  ✓ Check GITHUB_TOKEN exists                            │
│  ✓ Check ANTHROPIC_API_KEY exists and valid format      │
│  ✓ Install Claude Code CLI                              │
│  ✓ Test CLI authentication                              │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  Static Analysis (Parallel - Fast)                      │
│  • Ruff: Python linting & formatting                    │
│  • Pylint: Code quality                                 │
│  • Bandit: Security patterns                            │
│  • mypy: Type checking                                  │
│  • ESLint: JavaScript/TypeScript                        │
│  Duration: 10-30 seconds                                │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  AI Semantic Analysis (Sequential - Deep)               │
│  Using Claude Code CLI:                                 │
│  • Security Review → Architecture Review                │
│    → Code Quality → Performance → Testing               │
│  Each review sees previous findings for context         │
│  Duration: 30-90 seconds                                │
│  Cost: ~$0.02-0.03                                      │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  Result Aggregation                                     │
│  • Merge static + AI findings                           │
│  • Deduplicate overlapping issues                       │
│  • Calculate statistics                                 │
│  • Determine risk level                                 │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  Comment Generation (Direct Anthropic API)              │
│  • Generate rich summary comment                        │
│  • Batch generate inline comments                       │
│  • Format with emoji, code examples                     │
│  Duration: 5-10 seconds                                 │
│  Cost: ~$0.01                                           │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  Blocking Rules Evaluation                              │
│  • Check critical findings (threshold: 0)               │
│  • Check high findings (threshold: configurable)        │
│  • Apply project-specific rules                         │
│  Decision: BLOCK or APPROVE                             │
└────────────────┬────────────────────────────────────────┘
                 ↓
┌─────────────────────────────────────────────────────────┐
│  GitHub Integration                                     │
│  • Post summary comment to PR                           │
│  • Post inline comments on code                         │
│  • Update status check (✅ or ❌)                        │
│  • Exit with code (0 = pass, 1 = block)                 │
└─────────────────────────────────────────────────────────┘
                 ↓
  ┌──────────────┴──────────────┐
  │                             │
  ▼                             ▼
APPROVED                     BLOCKED
✅ PR can merge           ❌ Changes required
Developer continues       Developer fixes issues
```

**Key Features of This Flow**:
- **Environment Validation First**: Fails fast if credentials missing
- **Static Analysis in Parallel**: Quick feedback on obvious issues
- **AI Analysis Sequential**: Each review builds on previous context
- **Hybrid Comment Generation**: Fast API for comments, deep CLI for analysis
- **Clear Blocking Rules**: Transparent decision making
- **Rich Feedback**: Summary + inline comments + status checks

**Total Time**: ~1-2 minutes per PR (depends on project size)
**Total Cost**: ~$0.03-0.05 per PR (depends on project and PR size)

### Core Components

| Component | Purpose | Key Functions |
|-----------|---------|---------------|
| **Orchestrator** | Coordinates review pipeline | Parallel/sequential execution, result aggregation |
| **PR Context Builder** | Extracts PR information | Diff analysis, language detection, change classification |
| **Configuration Manager** | Loads & merges configs | Multi-level precedence, remote loading, validation |
| **Classical Analyzers** | Static analysis tools | Python/JS/Java tool integration, result standardization |
| **AI Review Engine** | Claude-powered reviews | Prompt management, JSON validation, retry logic |
| **Injection System** | Policy enforcement | Company/project policy injection into AI prompts |
| **Result Aggregator** | Combines findings | Deduplication, categorization, statistics |
| **GitHub Reporter** | Posts results to GitHub | Summary comments, inline comments, status checks |

### Execution Flow

1. **PR Event** → GitHub Actions triggered
2. **Context Extraction** → Files, diff, languages detected
3. **Change Detection** → Analyzes PR for:
   - Dependency changes (pyproject.toml, uv.lock, package.json, etc.)
   - Test changes (new/modified test files)
   - Security risk patterns (eval, exec, weak crypto, hardcoded secrets)
   - Breaking changes (removed functions/classes, API changes)
   - Impact scoring (based on file count, change size, change types)
4. **Configuration Loading** → Default ← Company ← Project merged
5. **Review Execution**:
   - **Parallel**: Classical tools (Python, JS, Java analyzers)
   - **Sequential**: AI reviews receive change detection context in prompts
6. **Aggregation** → Deduplicate, categorize, calculate statistics
7. **Blocking Check** → Apply severity thresholds
8. **GitHub Reporting** → Comment includes change types and risk level

### How Change Detection Works

The system automatically detects change characteristics that inform the review process:

**Detected Change Types**:
- `DEPENDENCY_CHANGE`: Modified package files
  - Python: pyproject.toml, uv.lock, poetry.lock, requirements.txt
  - JavaScript: package.json, pnpm-lock.yaml, yarn.lock
  - Java: pom.xml, build.gradle
- `TEST_CHANGE`: Added/modified test files
- `SECURITY_RISK`: Patterns like eval(), hardcoded passwords, weak crypto
- `BREAKING_CHANGE`: Removed exports, "BREAKING CHANGE" in commits
- `DOCUMENTATION`: README, docs changes
- `FEATURE`: Default for code changes

**Impact Calculation**:
```
Impact Score = (files × 5) + (total changes ÷ 10) + (change types × 10)
Risk Level = High (>70) | Medium (40-70) | Low (<40)
```

**Usage in Reviews**:
1. **Console Output**: Displays detected change types during execution
2. **AI Context Injection**: Change types are injected into AI review prompts
   - Example: "This PR includes DEPENDENCY_CHANGE and SECURITY_RISK"
   - AI reviews become more focused on relevant concerns
3. **PR Comments**: Risk level and change types appear in summary comments
4. **Blocking Rules**: Can configure stricter rules for high-risk changes

**Example**:
If a PR modifies `pyproject.toml` (UV/Poetry dependencies) and includes `eval()` calls:
- Detected types: `DEPENDENCY_CHANGE`, `SECURITY_RISK`
- Impact score: Elevated due to multiple risk factors
- AI prompts: Enhanced with "Pay special attention to new dependencies and security patterns"
- Result: More thorough security review automatically triggered

---

## Configuration

Configuration happens at three levels with proper precedence:

```
Default Config (built-in)
    ↓
Company Policies (organization-wide)
    ↓
Project Config (repository-specific)
```

**Key configuration options**:
- **Review aspects**: Enable/disable specific analyses
- **Blocking rules**: Control when PRs are blocked
- **Custom rules**: Pattern-based project-specific checks
- **Company policies**: Organization-wide standards

For detailed configuration options, see:
- [Python Configuration](docs/PYTHON_INTEGRATION.md#project-configuration)
- [JavaScript Configuration](docs/JAVASCRIPT_INTEGRATION.md#project-configuration)
- [Java Configuration](docs/JAVA_INTEGRATION.md#configuration)
- [AI Configuration](docs/AI_CONFIGURATION.md#configuration)
- [Example Configs](examples/)

---

## Development

### Prerequisites

- [UV](https://docs.astral.sh/uv/) - Fast Python package manager
- Python 3.11+ (UV will install this)
- Node.js 20+ (for JS/TS analysis)
- Java 17+ (for Java analysis, optional)

### Installation

```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone repository
git clone https://github.com/your-org/ai-review-cicd-actions.git
cd ai-review-cicd-actions

# Install Python and all dependencies (dev + prod)
uv sync

# Verify installation
uv run python --version
```

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage (optional for demo)
uv run pytest --cov=lib --cov-report=html

# Run specific test
uv run pytest tests/test_orchestrator.py -v

# Run with markers
uv run pytest -m unit  # Only unit tests
```

### Running Locally

```bash
# Run review on a PR
uv run python main.py \
  --repo owner/repo \
  --pr 123 \
  --output results.json

# With custom config
uv run python main.py \
  --repo owner/repo \
  --pr 123 \
  --config .github/ai-review-config.yml \
  --company-config github://your-org/policies/main/code-review.yml
```

### Adding Dependencies

```bash
# Add production dependency
uv add pyyaml

# Add dev dependency
uv add --dev pytest

# Update all dependencies
uv lock --upgrade
```

### Project Structure

```
ai-review-cicd-actions/
├── .github/workflows/
│   ├── ai-code-review.yml          # Self-review workflow
│   └── reusable-ai-review.yml      # Reusable template
├── lib/
│   ├── analyzers/                  # Static analysis tools
│   │   ├── base_analyzer.py
│   │   ├── python_analyzer.py
│   │   ├── javascript_analyzer.py
│   │   └── java_analyzer.py
│   ├── ai_review.py                # AI review engine
│   ├── config_manager.py           # Configuration system
│   ├── github_reporter.py          # GitHub integration
│   ├── injection.py                # Policy injection
│   ├── models.py                   # Data models
│   ├── orchestrator.py             # Pipeline coordinator
│   └── pr_context.py               # PR analysis
├── prompts/                        # AI review prompts
│   ├── security-review.md
│   ├── architecture-review.md
│   ├── base-review.md
│   ├── performance-review.md
│   └── testing-review.md
├── config/
│   └── default-config.yml          # Default configuration
├── examples/                       # Usage examples
│   ├── company-policies.yml
│   ├── project-config.yml
│   ├── java-spring-boot-config.yml
│   └── java-workflow-example.yml
├── tests/                          # Test suite
├── docs/                           # Documentation
│   ├── QUICKSTART.md
│   ├── JAVA_INTEGRATION.md
│   ├── IMPLEMENTATION_SUMMARY.md
│   └── REQUIREMENTS.md
├── main.py                         # CLI entry point
├── requirements.txt                # Dependencies
└── README.md                       # This file
```

---

## Documentation

The documentation is organized into four specialized guides based on integration needs:

### Language-Specific Integration Guides

Each guide covers tool setup, configuration, troubleshooting, and working examples:

- 🐍 **[Python Integration](docs/PYTHON_INTEGRATION.md)** - Ruff, Pylint, Bandit, mypy setup
- 🟨 **[JavaScript/TypeScript Integration](docs/JAVASCRIPT_INTEGRATION.md)** - ESLint, Prettier, TSC configuration
- ☕ **[Java Integration](docs/JAVA_INTEGRATION.md)** - SpotBugs, PMD, Checkstyle, JaCoCo, OWASP integration
- 🤖 **[AI Configuration](docs/AI_CONFIGURATION.md)** - Claude-powered semantic reviews

### Working Examples

- [Python FastAPI Config](examples/project-config.yml) - Complete project configuration
- [Java Spring Boot Workflow](examples/java-workflow-example.yml) - Full GitHub Actions workflow
- [Company Policies Template](examples/company-policies.yml) - Organization-wide standards

### Implementation Reference

- Configuration system: [`lib/config_manager.py`](lib/config_manager.py)
- Data models: [`lib/models.py`](lib/models.py)
- Language analyzers: [`lib/analyzers/`](lib/analyzers/)
- AI review prompts: [`prompts/`](prompts/)

---

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Follow PEP 8 for Python code
- Add tests for new features
- Update documentation
- Use type hints
- Keep functions under 50 lines

---

## Troubleshooting

### Common Issues

**Issue**: Review fails with "GitHub token required"
- **Solution**: Ensure `GITHUB_TOKEN` is passed in workflow secrets

**Issue**: AI review times out
- **Solution**: Reduce diff size or split into smaller PRs

**Issue**: Java OWASP Dependency-Check is slow
- **Solution**: Get free NVD API key and add to secrets

**Issue**: False positives in security scanning
- **Solution**: Tune blocking rules or add suppressions in tool configs

### Getting Help

- 📝 Check [documentation](docs/)
- 🐛 Report [issues](https://github.com/your-org/ai-review-cicd-actions/issues)
- 💬 Join [discussions](https://github.com/your-org/ai-review-cicd-actions/discussions)

---

## License

This project is licensed under the MIT License so you can use freely.

---

## Project Status & Future Work

This is a **demonstration and research project** showcasing architectural patterns for AI-assisted development mitigation. It is:

✅ **Functional** - Core pipeline works with Python, JS/TS, and Java
✅ **Educational** - Demonstrates multi-layer defense and policy injection patterns
✅ **Extensible** - Architecture supports adding new analyzers and review aspects

### 🚀 Future Enhancements

This demonstration project is production-ready for its research scope. Optional enhancements for enterprise deployment:

1. **Caching System** - Cache review results by file content hash to avoid re-analyzing unchanged code across PRs (potential 80% time/cost savings)

2. **Demo Project** - Create `demo/` directory with intentionally flawed code for testing and demonstration

3. **Configuration Validation** - JSON Schema validation for configuration files to catch errors early

4. **Additional Documentation** - Quick-start guide, troubleshooting guide, cost estimation guide

5. **Rate Limiting** - Implement rate limiting for API calls to prevent quota exhaustion

6. **Advanced Features** - Auto-fix suggestions via GitHub suggestion comments, historical quality trends, cross-language API contract validation

**Note**: Core features (error recovery, metrics tracking, timeout handling) are already implemented. Secrets are automatically redacted by GitHub Actions. For **production** deployments, consider established commercial solutions (SonarQube, Codacy, CodeRabbit, Qodo Merge) or extend these patterns to your needs.

---

## Acknowledgments

This project was researched and developed with AI assistance (Claude Code), implementing multi-layer defense patterns to address the systemic issues identified in AI-assisted development research.

---

<div align="center">

**A research demonstration of multi-layer defense patterns for AI-assisted development**

[Python Guide](docs/PYTHON_INTEGRATION.md) • [JavaScript Guide](docs/JAVASCRIPT_INTEGRATION.md) • [Java Guide](docs/JAVA_INTEGRATION.md) • [AI Config](docs/AI_CONFIGURATION.md)

</div>
