# 🤖 AI-Driven Code Review System

A comprehensive, reusable GitHub Actions-based code review system that combines classical static analysis with AI-driven intelligent review. Designed for multi-language projects with customizable company and project-level policies.

## ✨ Features

### 🔍 Multi-Layered Review System
- **Classical Static Analysis**: Ruff, Pylint, Bandit, mypy for Python; ESLint, Prettier, TSC for JavaScript/TypeScript
- **AI-Driven Reviews**: Security, architecture, code quality, performance, and testing reviews powered by Claude
- **Change Detection**: Identifies architecture drift, breaking changes, security risks, and dependency updates

### ⚙️ Flexible Configuration
- **Three-Level Config**: Default → Company → Project configuration with proper precedence
- **Policy Injection**: Enforce company-wide coding standards and project-specific constraints
- **Customizable Rules**: Define pattern-based rules specific to your project

### 🚀 GitHub Integration
- **Automated PR Comments**: Summary comments and inline comments on specific lines
- **Status Checks**: Pass/fail status with configurable blocking rules
- **Review Events**: Automatic GitHub review creation (approve/request changes)

### 📊 Comprehensive Reporting
- **Severity Levels**: Critical, High, Medium, Low, Info
- **Categories**: Security, Performance, Architecture, Code Quality, Testing, Documentation, Style
- **Actionable Suggestions**: AI-generated fix suggestions for each finding

## 🚀 Quick Start

### For Repository Administrators (Setting up the review system)

1. **Create a central review system repository:**
   ```bash
   git clone https://github.com/your-org/ai-review-cicd-actions.git
   cd ai-review-cicd-actions
   ```

2. **Configure secrets:**
   - Add `ANTHROPIC_API_KEY` to repository secrets (if using Claude API)

3. **Customize company policies** (optional):
   - Create `config/company-policies.yml` with your organization's standards
   - Host it in a central location (GitHub repo, S3, etc.)

### For Project Teams (Using the review system)

1. **Create workflow file** in your project at `.github/workflows/code-review.yml`:

   ```yaml
   name: AI Code Review

   on:
     pull_request:
       types: [opened, synchronize, reopened]

   jobs:
     code-review:
       uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
       with:
         company-config-url: 'github://your-org/policies/main/code-review-policies.yml'
       secrets:
         GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
         ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
       permissions:
         contents: read
         pull-requests: write
         statuses: write
   ```

2. **Optional: Create project config** at `.github/ai-review-config.yml`:

   ```yaml
   project_context:
     name: "My Project"
     architecture: "Microservices"
     critical_paths:
       - "src/payment/"

   project_constraints:
     - "All payment operations must be idempotent"
     - "Use Decimal for monetary values"

   blocking_rules:
     block_on_critical: true
     max_findings:
       critical: 0
       high: 5
   ```

3. **Create a PR** and watch the AI review in action! 🎉

## 📖 Documentation

### Configuration

#### Review Aspects

Configure which review aspects to run:

```yaml
review_aspects:
  - name: python_static_analysis
    enabled: true
    type: classical
    tools: [ruff, pylint, bandit, mypy]
    parallel: true

  - name: security_review
    enabled: true
    type: ai
    prompt_file: prompts/security-review.md
    parallel: false
```

**Available Review Aspects:**
- `python_static_analysis` - Ruff, Pylint, Bandit, mypy
- `javascript_static_analysis` - ESLint, Prettier, TSC
- `security_review` - AI-driven security analysis (OWASP Top 10)
- `architecture_review` - Architectural consistency and design patterns
- `code_quality_review` - Code complexity, duplication, readability
- `performance_review` - Algorithm efficiency, N+1 queries, caching
- `testing_review` - Test coverage and quality

#### Blocking Rules

Define when to block PR merges:

```yaml
blocking_rules:
  block_on_critical: true  # Always block if critical issues found
  block_on_high: false     # Don't block on high severity alone

  max_findings:
    critical: 0   # Zero tolerance
    high: 5       # Allow up to 5 high severity issues
    medium: 20
```

#### Company Policies

Create a central `company-policies.yml`:

```yaml
coding_standards:
  python:
    - "Use type hints for all function signatures"
    - "Maximum function length: 50 lines"

security_requirements:
  - "All API endpoints must have authentication"
  - "Secrets must be stored in environment variables"

architectural_rules:
  - "Backend must not import from frontend"
  - "Business logic only in service layer"
```

#### Project Constraints

Add project-specific rules in `.github/ai-review-config.yml`:

```yaml
project_constraints:
  - "All payment operations must be idempotent"
  - "Transaction amounts must use Decimal, not float"

custom_rules:
  - pattern: "float.*amount|price|total"
    message: "Use Decimal for monetary values"
    severity: "critical"
```

### Usage Examples

#### Minimal Setup

```yaml
# .github/workflows/code-review.yml
jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
```

#### Full Configuration

```yaml
jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      python-version: '3.11'
      node-version: '20'
      config-file: '.github/ai-review-config.yml'
      company-config-url: 'github://your-org/policies/main/code-review-policies.yml'
      enable-js-analysis: true
      enable-python-analysis: true
      fail-on-blocking: true
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
      COMPANY_CONFIG_TOKEN: ${{ secrets.COMPANY_CONFIG_TOKEN }}
```

#### Running Locally

```bash
python main.py \
  --repo owner/repo \
  --pr 123 \
  --config .github/ai-review-config.yml \
  --output results.json
```

## 🏗️ Architecture

### Component Overview

```
┌─────────────────────────────────────────────────┐
│              GitHub Actions Workflow             │
└────────────────┬────────────────────────────────┘
                 │
                 ▼
┌─────────────────────────────────────────────────┐
│         Orchestrator (lib/orchestrator.py)       │
│  - Coordinates review pipeline                   │
│  - Manages parallel/sequential execution         │
└─────┬───────────────────────────────────────────┘
      │
      ├─────────────────────────────────────────────┐
      │                                             │
      ▼                                             ▼
┌──────────────────┐                    ┌──────────────────┐
│  Classical       │                    │  AI Review       │
│  Analyzers       │                    │  Engine          │
│                  │                    │                  │
│  - Python        │                    │  - Security      │
│  - JavaScript    │                    │  - Architecture  │
│  - TypeScript    │                    │  - Code Quality  │
└──────────────────┘                    └──────────────────┘
      │                                             │
      └─────────────────┬───────────────────────────┘
                        ▼
              ┌──────────────────┐
              │  Aggregator      │
              │  - Deduplicate   │
              │  - Categorize    │
              │  - Statistics    │
              └────────┬─────────┘
                       ▼
              ┌──────────────────┐
              │  GitHub Reporter │
              │  - Comments      │
              │  - Status checks │
              └──────────────────┘
```

### Key Components

- **Orchestrator** (`lib/orchestrator.py`): Coordinates execution of all review aspects
- **PR Context Builder** (`lib/pr_context.py`): Extracts PR information and metadata
- **Configuration Manager** (`lib/config_manager.py`): Loads and merges multi-level configs
- **Classical Analyzers** (`lib/analyzers/`): Integrates static analysis tools
- **AI Review Engine** (`lib/ai_review.py`): Executes AI-driven reviews with Claude
- **Injection System** (`lib/injection.py`): Injects company/project policies into prompts
- **GitHub Reporter** (`lib/github_reporter.py`): Posts results back to GitHub

## 🛠️ Development

### Prerequisites

- Python 3.11+
- Node.js 20+ (for JavaScript/TypeScript analysis)
- GitHub account with API access

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/ai-review-cicd-actions.git
cd ai-review-cicd-actions

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install pytest pytest-cov pytest-mock
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=lib --cov-report=html

# Run specific test
pytest tests/test_orchestrator.py
```

### Project Structure

```
ai-review-cicd-actions/
├── .github/
│   └── workflows/
│       ├── ai-code-review.yml          # Self-review workflow
│       └── reusable-ai-review.yml      # Reusable workflow for other projects
├── lib/
│   ├── analyzers/
│   │   ├── base_analyzer.py
│   │   ├── python_analyzer.py
│   │   └── javascript_analyzer.py
│   ├── config_manager.py
│   ├── orchestrator.py
│   ├── pr_context.py
│   ├── ai_review.py
│   ├── injection.py
│   ├── github_reporter.py
│   └── models.py
├── prompts/
│   ├── base-review.md
│   ├── security-review.md
│   ├── architecture-review.md
│   ├── performance-review.md
│   └── testing-review.md
├── config/
│   └── default-config.yml
├── examples/
│   ├── company-policies.yml
│   ├── project-config.yml
│   └── usage-in-project.yml
├── tests/
├── main.py
├── requirements.txt
└── README.md
```

## 📝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`pytest`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [PyGithub](https://github.com/PyGithub/PyGithub) for GitHub API integration
- AI-powered reviews using Claude by Anthropic
- Static analysis tools: Ruff, Pylint, Bandit, mypy, ESLint, Prettier, TSC

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/your-org/ai-review-cicd-actions/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/ai-review-cicd-actions/discussions)
- **Documentation**: [Wiki](https://github.com/your-org/ai-review-cicd-actions/wiki)

## 🗺️ Roadmap

- [ ] Additional language support (Go, Rust, Java, C#)
- [ ] Semantic diff analysis
- [ ] Historical learning from past reviews
- [ ] Auto-fix generation
- [ ] Performance benchmarking
- [ ] Visual regression testing
- [ ] Cross-repository impact analysis
- [ ] Smart test selection

---

**Made with ❤️ by your engineering team**
