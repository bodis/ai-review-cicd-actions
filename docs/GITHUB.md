# GitHub Integration Guide

Complete guide for integrating the AI Code Review Pipeline into your GitHub repositories.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Quick Start](#quick-start)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [Integration Patterns](#integration-patterns)
6. [GitHub Actions Configuration](#github-actions-configuration)
7. [Environment Variables](#environment-variables)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Examples](#examples)

---

## Overview

This AI Code Review Pipeline provides automated code reviews for GitHub Pull Requests. The core review logic (static analysis, AI reviews, orchestration) works seamlessly with GitHub's PR system through the GitHub Actions platform.

### What Works on GitHub

✅ **Pull Request (PR) Analysis** - Automated code review on every PR
✅ **Automated Comments** - Summary and inline comments with AI-generated feedback
✅ **Status Checks** - Pass/fail checks that can block merging
✅ **Review Events** - Approve, request changes, or comment
✅ **Multi-language Support** - Python, JavaScript/TypeScript, Java
✅ **AI-powered Reviews** - Security, architecture, quality, performance
✅ **Static Analysis** - Ruff, ESLint, SpotBugs, etc.
✅ **Auto-detection** - Automatically detects GitHub Actions environment

### Key Benefits

- **Zero manual setup for repos** - Workflow runs automatically on PRs
- **Language detection** - Automatically detects Python, JS/TS, Java
- **Respects tool configs** - Uses your project's `pyproject.toml`, `.eslintrc`, etc.
- **Flexible deployment** - Run from same repo or centralized system
- **Familiar GitHub UI** - Comments appear like regular PR reviews

---

## How It Works

```
┌──────────────────────────────────────────────────┐
│         Developer Creates Pull Request          │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│         GitHub Actions Workflow Triggered        │
│  • Auto-triggered via pull_request event         │
│  • Runs in GitHub-hosted or self-hosted runner   │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│      Review System Execution                     │
│  1. Checkout PR code                             │
│  2. Install UV (Python package manager)          │
│  3. Install dependencies (cached)                │
│  4. Run static analysis (Ruff, ESLint, etc.)     │
│  5. Run AI reviews (Claude API)                  │
│  6. Aggregate and deduplicate findings           │
│  7. Check blocking rules                         │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│         Post Results to GitHub                   │
│  • Summary comment on PR                         │
│  • Inline comments on code                       │
│  • Commit status (success/failure)               │
│  • Review event (approve/request changes)        │
│  • Exit code (0 = pass, 1 = block)               │
└──────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

1. **GitHub repository** with admin access
2. **Anthropic API key** - Get from [Anthropic Console](https://console.anthropic.com/)
3. **GitHub Actions enabled** - Should be on by default for public repos

### 5-Minute Setup

**1. Add API Key to GitHub Secrets**

Go to your repository: `Settings → Secrets and variables → Actions → New repository secret`

- **Name**: `ANTHROPIC_API_KEY`
- **Secret**: Your Anthropic API key (starts with `sk-ant-`)

**2. Create Workflow File** (`.github/workflows/ai-code-review.yml`):

**Option A: Using the reusable workflow (Recommended)**:
```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    uses: bodis/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      python-version: '3.12'
      package-version: 'main'  # Or pin to a tag like 'v1.0.0'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Option B: Direct installation (More control)**:
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
  ai-review:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install UV
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.12

      - name: Install AI Review package
        run: |
          uv pip install "ai-code-review @ git+https://github.com/bodis/ai-review-cicd-actions.git@main"

      - name: Install Claude Code CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          CLAUDE_CODE_HEADLESS: '1'
        run: |
          uv run ai-review \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }} \
            --output review-results.json
```

**3. Project Configuration** (`.github/ai-review-config.yml`) - **Optional but Recommended**:

If you don't provide this file, the system uses **sensible defaults**:
- ✅ Runs: Python (Ruff, Pylint, Bandit, mypy), JS/TS (ESLint, Prettier), AI reviews (Security, Architecture, Quality)
- ✅ Blocks on: Critical issues only (0 allowed)
- ✅ Filters: Only reports issues on changed lines
- ✅ Uses: Claude Sonnet 4.5

**Create this file to customize behavior**:

```yaml
project_context:
  name: "My Project"
  architecture: "FastAPI Microservice"

blocking_rules:
  block_on_critical: true
  max_findings:
    critical: 0
    high: 5
```

**4. Create a Pull Request** - Reviews run automatically with these defaults:
   - ✅ Python: Ruff, Pylint, Bandit, mypy
   - ✅ JavaScript/TypeScript: ESLint, Prettier, TSC
   - ✅ AI: Security, Architecture, Code Quality reviews
   - ✅ Blocks on: Critical issues only (0 tolerance)
   - ✅ Filters: Only changed lines reported

   (Customize by adding `.github/ai-review-config.yml` - see Step 5)

---

## Step-by-Step Setup

### Step 1: Choose Integration Pattern

There are **two patterns** for integrating the review system:

#### Pattern A: Local/Embedded (Copy to your repo)

✅ **Full control** - Review system lives in your project
✅ **No external deps** - Everything self-contained
✅ **Easy customization** - Modify anything
❌ **Manual updates** - Must update each project individually
❌ **Code duplication** - Each project has a copy

**Use when**: Single project, small team, need full control, or heavily customized reviews.

#### Pattern B: Centralized/Reusable (Reference central repo)

✅ **Single source of truth** - One repo hosts the review system
✅ **Zero code duplication** - All projects reference central repo
✅ **Easy updates** - Update central repo, all projects get changes
✅ **Consistent standards** - Same review rules across organization
❌ **External dependency** - Requires access to central repo
❌ **Less flexibility** - Per-project customization limited

**Use when**: 5+ projects, organization-wide standards, or maintaining consistency.

---

### Step 2: Add Secrets to GitHub

**2.1. Navigate to Repository Settings**

Go to: `Your Repo → Settings → Secrets and variables → Actions`

**2.2. Add ANTHROPIC_API_KEY**

Click **"New repository secret"** and configure:

- **Name**: `ANTHROPIC_API_KEY`
- **Secret**: Your API key (get from [Anthropic Console](https://console.anthropic.com/))

**Important**: Repository secrets are encrypted and masked in logs automatically.

**2.3. Verify GITHUB_TOKEN**

GitHub automatically provides `GITHUB_TOKEN` - you don't need to add it manually. This token is:
- ✅ Auto-provided in every workflow run
- ✅ Has permissions based on workflow `permissions:` block
- ✅ Expires after the workflow completes
- ❌ **Don't add it to secrets** - it's automatic!

---

### Step 3: Prepare Your Project

**3.1. Ensure Tool Configuration Files Exist**

The review system respects your project's tool configurations:

**Python projects** - `pyproject.toml`:
```toml
[project]
name = "my-project"
requires-python = ">=3.11"
dependencies = ["fastapi>=0.104.0"]

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.mypy]
python_version = "3.11"
warn_return_any = true
```

**JavaScript/TypeScript** - `package.json` + `.eslintrc.js`:
```json
{
  "name": "my-project",
  "devDependencies": {
    "eslint": "^8.0.0",
    "prettier": "^3.0.0"
  }
}
```

**Java** - `pom.xml` or `build.gradle`:
```xml
<project>
  <build>
    <plugins>
      <plugin>
        <groupId>com.github.spotbugs</groupId>
        <artifactId>spotbugs-maven-plugin</artifactId>
      </plugin>
    </plugins>
  </build>
</project>
```

The review system will automatically use these configurations.

---

### Step 4: Create GitHub Actions Workflow

**4.1. Choose Based on Your Pattern**

#### Pattern A: Local/Embedded

Create `.github/workflows/ai-code-review.yml`:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

# Prevent multiple runs on rapid pushes
concurrency:
  group: ai-review-${{ github.ref }}
  cancel-in-progress: true

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  ai-review:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - name: Checkout code
        uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Full history for better context

      - name: Install UV
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync

      # Install Node.js for JS/TS projects
      - name: Install Node.js
        if: hashFiles('package.json') != ''
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install JS dependencies
        if: hashFiles('package.json') != ''
        run: npm ci

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          uv run python main.py \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }} \
            --config .github/ai-review-config.yml \
            --output review-results.json

      - name: Upload review results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: review-results-pr-${{ github.event.pull_request.number }}
          path: review-results.json
          retention-days: 30
```

#### Pattern B: Centralized/Reusable

Create `.github/workflows/ai-code-review.yml`:

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
  ai-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      enable-python-analysis: true
      enable-javascript-analysis: true
      python-version: '3.11'
      node-version: '20'
      company-config-url: 'github://your-org/policies/main/code-review.yml'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

### Step 5: Configure Review Behavior (Optional but Recommended)

**Without this file**, the system uses built-in defaults:
- All Python tools (Ruff, Pylint, Bandit, mypy)
- All JavaScript tools (ESLint, Prettier, TSC)
- AI reviews: Security, Architecture, Code Quality
- Blocks only on critical issues (0 allowed)
- Reports only on changed lines

**Why create a config file?**
- 💰 **Save costs** - Disable AI reviews you don't need ($0.01-0.02 per review)
- 🎯 **Add context** - Project name, architecture, constraints help AI reviews
- ⚖️ **Tune blocking** - Stricter (block on high) or looser (allow more issues)
- 🚀 **Skip irrelevant tools** - Disable JS analysis for Python-only projects

**Create `.github/ai-review-config.yml`** in your project root:

```yaml
# Project metadata
project_context:
  name: "Payment Service"
  architecture: "FastAPI Microservice"
  description: "Handles payment processing and refunds"

# Project-specific constraints
project_constraints:
  - "All monetary values must use Decimal, never float"
  - "Payment operations must be idempotent"
  - "Always log payment attempts for audit"

# What to review
review_aspects:
  # Static analysis
  - name: python_static_analysis
    enabled: true
    type: classical
    tools: ["ruff", "pylint", "bandit", "mypy"]

  # AI reviews
  - name: security_review
    enabled: true
    type: ai
    prompt_file: prompts/security-review.md

  - name: architecture_review
    enabled: true
    type: ai
    prompt_file: prompts/architecture-review.md

# Blocking rules
blocking_rules:
  block_on_critical: true  # Always block on critical issues
  block_on_high: false     # Don't block on high-severity
  max_findings:
    critical: 0  # Zero tolerance for critical
    high: 10     # Allow up to 10 high-severity

# Filtering
filtering:
  only_changed_lines: true  # Only report on changed lines
  min_severity: "info"      # Report all severities

# Performance
performance:
  parallel_reviews: true
  ai_review_max_retries: 1
```

---

### Step 6: Test the Integration

**6.1. Create a Test Pull Request**

Make a simple code change and create a PR:

```bash
git checkout -b test-ai-review
echo "# Test" >> README.md
git add README.md
git commit -m "Test AI review integration"
git push origin test-ai-review
```

Then create a PR in GitHub UI.

**6.2. Monitor Workflow**

Go to: `Your PR → Checks Tab`

You should see:
- ✅ `AI Code Review` workflow running
- ⏱️ Typically takes 1-2 minutes
- 📊 Click to view logs and see progress

**6.3. Check Results**

After completion:
- **Summary Comment** - Posted to PR with overview
- **Inline Comments** - On specific lines with issues
- **Status Check** - Green checkmark (passed) or red X (blocked)
- **Review Event** - Approve, request changes, or comment

---

## Integration Patterns

### Pattern A: Local/Embedded

**Directory structure**:
```
your-project/
├── .github/
│   ├── workflows/
│   │   └── ai-code-review.yml
│   └── ai-review-config.yml
├── lib/                    # Review system code (copied here)
│   ├── analyzers/
│   ├── orchestrator.py
│   └── ...
├── prompts/                # AI review prompts
├── config/                 # Default configs
├── main.py                 # Review entry point
└── pyproject.toml         # Your project config
```

**Pros**:
- ✅ Full control over review logic
- ✅ Can customize anything
- ✅ No external dependencies
- ✅ Works without network access to other repos

**Cons**:
- ❌ Code duplication across projects
- ❌ Manual updates needed
- ❌ Harder to maintain consistency

**Best for**: Single project, small teams, heavily customized needs.

---

### Pattern B: Centralized/Reusable

**Directory structure**:
```
your-project/
├── .github/
│   ├── workflows/
│   │   └── ai-code-review.yml  # References central repo
│   └── ai-review-config.yml    # Project-specific config only
├── src/                         # Your application code
└── pyproject.toml              # Your project config

central-repo/ (separate repository)
├── lib/                    # Review system code
├── prompts/
├── config/
└── main.py
```

**Pros**:
- ✅ Zero code duplication
- ✅ Single source of truth
- ✅ Automatic updates
- ✅ Organization-wide consistency

**Cons**:
- ❌ Requires access to central repo
- ❌ Less flexibility per project
- ❌ Need to manage central repo updates

**Best for**: Organizations, 5+ projects, consistent standards.

---

## GitHub Actions Configuration

### Environment Variables Reference

#### Required Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | Repository Secrets | Your Anthropic API key for Claude |
| `GITHUB_TOKEN` | Auto-provided | GitHub token for API access (don't add manually!) |

#### Auto-Provided Variables (GitHub Actions)

| Variable | Example | Description |
|----------|---------|-------------|
| `GITHUB_REPOSITORY` | `owner/repo` | Repository identifier |
| `GITHUB_EVENT_NAME` | `pull_request` | Event that triggered workflow |
| `GITHUB_REF` | `refs/pull/123/merge` | Git ref |
| `GITHUB_SHA` | `abc123...` | Commit SHA |
| `GITHUB_ACTOR` | `username` | User who triggered workflow |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CLAUDE_API_URL` | - | Custom Claude API endpoint (for proxy) |

### Workflow Configuration Options

```yaml
jobs:
  ai-review:
    runs-on: ubuntu-latest  # or: self-hosted, macos-latest

    # Resource limits
    timeout-minutes: 15  # Max time for review

    # Concurrency control
    concurrency:
      group: ai-review-${{ github.ref }}
      cancel-in-progress: true  # Cancel old runs on new push

    # Runner tags (for self-hosted)
    runs-on:
      - self-hosted
      - linux
      - x64

    # Conditional execution
    if: github.event.pull_request.draft == false

    # Job dependencies
    needs: [test, build]  # Run after other jobs
```

---

## Advanced Configuration

### Organization-Wide Policies

Load organization-wide standards from a centralized config:

```yaml
- name: Run AI Code Review
  run: |
    uv run python main.py \
      --repo ${{ github.repository }} \
      --pr ${{ github.event.pull_request.number }} \
      --company-config "github://your-org/policies/main/code-review.yml"
```

The company config is merged with project config (project wins on conflicts).

---

### Caching Dependencies

Speed up subsequent runs by caching:

```yaml
- name: Install UV
  uses: astral-sh/setup-uv@v3
  with:
    enable-cache: true  # Caches UV itself

- name: Cache Python dependencies
  uses: actions/cache@v4
  with:
    path: |
      ~/.cache/uv
      .venv/
    key: ${{ runner.os }}-uv-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-uv-

- name: Cache Node modules
  if: hashFiles('package.json') != ''
  uses: actions/cache@v4
  with:
    path: ~/.npm
    key: ${{ runner.os }}-node-${{ hashFiles('**/package-lock.json') }}
```

---

### Matrix Strategy (Multiple Python Versions)

Test reviews across Python versions:

```yaml
strategy:
  matrix:
    python-version: ['3.11', '3.12']

steps:
  - name: Set up Python ${{ matrix.python-version }}
    run: uv python install ${{ matrix.python-version }}
```

---

### Self-Hosted Runners

Run on your own infrastructure:

```yaml
jobs:
  ai-review:
    runs-on: [self-hosted, linux]

    steps:
      # Ensure UV is installed on runner
      - name: Setup UV
        run: |
          if ! command -v uv &> /dev/null; then
            curl -LsSf https://astral.sh/uv/install.sh | sh
          fi
```

---

### Skip Reviews for Certain Files

Only run reviews when relevant files change:

```yaml
on:
  pull_request:
    paths:
      - '**.py'
      - '**.js'
      - '**.ts'
      - 'pyproject.toml'
      - 'package.json'
```

---

## Troubleshooting

### Issue: "ANTHROPIC_API_KEY secret not set"

**Cause**: API key not added to repository secrets.

**Solution**:
1. Go to `Settings → Secrets and variables → Actions`
2. Add `ANTHROPIC_API_KEY` with your key
3. Verify key starts with `sk-ant-`

---

### Issue: "GITHUB_TOKEN permissions insufficient"

**Cause**: Workflow doesn't have required permissions.

**Solution**:
Add to workflow:
```yaml
permissions:
  contents: read
  pull-requests: write
  statuses: write
```

---

### Issue: "Failed to post comment to PR"

**Cause**: Token lacks permissions or PR is from fork.

**Solution**:
1. For forks, use `pull_request_target` (be careful with untrusted code!)
2. Or require contributors open PRs from branches, not forks

```yaml
on:
  pull_request_target:  # Has write permissions even from forks
    types: [opened, synchronize]
```

---

### Issue: "UV installation failed"

**Cause**: Network issues or runner architecture.

**Solution**:
```yaml
- name: Install UV with retry
  run: |
    for i in 1 2 3; do
      curl -LsSf https://astral.sh/uv/install.sh | sh && break || sleep 5
    done
  shell: bash
```

---

### Issue: "Review times out after 15 minutes"

**Cause**: Large PR or slow network.

**Solution**:
1. Increase timeout:
```yaml
timeout-minutes: 30
```

2. Or split into smaller PRs
3. Or disable some AI reviews to save time

---

### Debugging Tips

**Enable debug logging**:
```yaml
- name: Run AI Code Review
  env:
    ACTIONS_STEP_DEBUG: true
    GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
    ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

**Check environment**:
```yaml
- name: Debug Info
  run: |
    echo "=== Environment ==="
    env | sort
    echo "=== Git Info ==="
    git branch -a
    git log -1
```

---

## Examples

### Example 1: Python FastAPI Project

**`.github/workflows/ai-code-review.yml`**:
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
  ai-review:
    runs-on: ubuntu-latest
    timeout-minutes: 15

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: Install UV
        uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Set up Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          uv run python main.py \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }} \
            --config .github/ai-review-config.yml
```

**`.github/ai-review-config.yml`**:
```yaml
project_context:
  name: "Payment API"
  architecture: "FastAPI Microservice"

project_constraints:
  - "Use Decimal for money, never float"
  - "All endpoints must have OpenAPI docs"

review_aspects:
  - name: python_static_analysis
    enabled: true
    type: classical
    tools: ["ruff", "bandit", "mypy"]

  - name: security_review
    enabled: true
    type: ai
    prompt_file: prompts/security-review.md

blocking_rules:
  block_on_critical: true
  max_findings:
    critical: 0
    high: 5

filtering:
  only_changed_lines: true
```

---

### Example 2: React TypeScript Project

**`.github/workflows/ai-code-review.yml`**:
```yaml
name: AI Code Review

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  ai-review:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v3
      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: |
          uv python install 3.11
          uv sync
          npm ci

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          uv run python main.py \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }}
```

---

### Example 3: Monorepo (Python + TypeScript)

**`.github/workflows/ai-code-review.yml`**:
```yaml
name: AI Code Review

on:
  pull_request:

permissions:
  contents: read
  pull-requests: write
  statuses: write

jobs:
  ai-review:
    runs-on: ubuntu-latest
    timeout-minutes: 20

    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - uses: astral-sh/setup-uv@v3
        with:
          enable-cache: true

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install all dependencies
        run: |
          # Python (backend)
          uv python install 3.11
          cd backend && uv sync && cd ..

          # JavaScript (frontend)
          cd frontend && npm ci && cd ..

      - name: Run AI Code Review
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
        run: |
          uv run python main.py \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }} \
            --project-root .
```

---

## Next Steps

1. **Test Integration** - Create a test PR and verify comments appear
2. **Tune Configuration** - Adjust blocking rules and review aspects
3. **Share Knowledge** - Document your setup for team members
4. **Monitor Costs** - Track Anthropic API usage (typically $0.03-0.05 per PR)
5. **Iterate** - Refine based on team feedback

---

## Additional Resources

- [Platform Architecture](ARCHITECTURE.md) - Technical details of GitHub/GitLab abstraction
- [Python Integration](PYTHON_INTEGRATION.md) - Python-specific setup
- [JavaScript Integration](JAVASCRIPT_INTEGRATION.md) - JS/TS-specific setup
- [AI Configuration](AI_CONFIGURATION.md) - Customize AI review prompts

---

## Getting Help

- 📚 Check other [documentation](../docs/)
- 🐛 Report [issues](https://github.com/your-org/ai-review-cicd-actions/issues)
- 💬 Join [discussions](https://github.com/your-org/ai-review-cicd-actions/discussions)

---

**Happy Reviewing! 🚀**
