# GitLab Integration Guide

Complete guide for integrating the AI Code Review Pipeline into your GitLab projects.

---

## 📋 Table of Contents

1. [Overview](#overview)
2. [How It Works](#how-it-works)
3. [Quick Start](#quick-start)
4. [Step-by-Step Setup](#step-by-step-setup)
5. [GitLab CI Configuration](#gitlab-ci-configuration)
6. [Environment Variables](#environment-variables)
7. [Platform Differences](#platform-differences)
8. [Advanced Configuration](#advanced-configuration)
9. [Troubleshooting](#troubleshooting)
10. [Examples](#examples)

---

## Overview

This AI Code Review Pipeline supports **both GitHub and GitLab** through a clean platform abstraction layer. The core review logic (static analysis, AI reviews, orchestration) is identical across platforms - only the API integration differs.

### What Works on GitLab

✅ **Merge Request (MR) Analysis** - Same as GitHub PR analysis
✅ **Automated Comments** - Summary and inline comments on MRs
✅ **Pipeline Status Updates** - Pass/fail status on commits
✅ **Multi-language Support** - Python, JavaScript/TypeScript, Java
✅ **AI-powered Reviews** - Security, architecture, quality, performance
✅ **Static Analysis** - Ruff, ESLint, SpotBugs, etc.
✅ **Auto-detection** - Automatically detects GitLab CI environment

### Key Benefits

- **Zero code changes** - Same configuration files work on both platforms
- **Language detection** - Automatically detects Python, JS/TS, Java
- **Respects tool configs** - Uses your project's `pyproject.toml`, `.eslintrc`, etc.
- **Flexible deployment** - Run from same repo or centralized system

---

## How It Works

```
┌──────────────────────────────────────────────────┐
│         Developer Creates Merge Request         │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│           GitLab CI Pipeline Triggered           │
│  • Auto-detected via CI_PIPELINE_SOURCE          │
│  • Runs in your GitLab runner                    │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│      Review System Execution                     │
│  1. Install UV (Python package manager)          │
│  2. Clone/sync review system code                │
│  3. Install dependencies (cached)                │
│  4. Run static analysis (Ruff, ESLint, etc.)     │
│  5. Run AI reviews (Claude API)                  │
│  6. Aggregate and deduplicate findings           │
│  7. Check blocking rules                         │
└─────────────────┬────────────────────────────────┘
                  │
┌─────────────────▼────────────────────────────────┐
│         Post Results to GitLab                   │
│  • Summary note on MR                            │
│  • Inline discussions on code                    │
│  • Commit status (success/failed)                │
│  • Exit code (0 = pass, 1 = block)               │
└──────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

1. **GitLab project** (SaaS or self-hosted)
2. **Anthropic API key** - Get from [Anthropic Console](https://console.anthropic.com/)
3. **GitLab CI/CD enabled** - Should be on by default

### 5-Minute Setup

**1. Add API Key to GitLab**

Go to your project: `Settings → CI/CD → Variables → Add variable`

- **Key**: `ANTHROPIC_API_KEY`
- **Value**: Your Anthropic API key (starts with `sk-ant-`)
- **Flags**: ✅ Protect variable, ✅ Mask variable

**2. Create `.gitlab-ci.yml`** (in your project root):

```yaml
ai-review:
  stage: test
  image: python:3.12-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    # Install UV (Python package manager)
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.local/bin:$PATH"

    # Install Node.js (for Claude Code CLI)
    - apt-get update && apt-get install -y curl git
    - curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    - apt-get install -y nodejs

    # Install Claude Code CLI
    - npm install -g @anthropic-ai/claude-code

    # Install AI Review package
    - uv pip install "ai-code-review @ git+https://github.com/bodis/ai-review-cicd-actions.git@main"

  script:
    # Run review (auto-detects GitLab)
    - |
      uv run ai-review \
        --repo "$CI_PROJECT_ID" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --output review-results.json

  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
    CLAUDE_CODE_HEADLESS: '1'
    # CI_JOB_TOKEN is automatically provided by GitLab
```

**3. Project Configuration** (`.gitlab/ai-review-config.yml`) - **Optional but Recommended**:

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

**4. Create a Merge Request** - Reviews run automatically with these defaults:
   - ✅ Python: Ruff, Pylint, Bandit, mypy
   - ✅ JavaScript/TypeScript: ESLint, Prettier, TSC
   - ✅ AI: Security, Architecture, Code Quality reviews
   - ✅ Blocks on: Critical issues only (0 tolerance)
   - ✅ Filters: Only changed lines reported

   (Customize by adding `.gitlab/ai-review-config.yml` - see Step 5)

---

## Step-by-Step Setup

### Step 1: Understand Integration Patterns

There are **two patterns** for integrating the review system:

#### Pattern A: Centralized (Recommended for organizations)

✅ **Single source of truth** - One repo hosts the review system
✅ **Zero code duplication** - All projects clone from central repo
✅ **Easy updates** - Update central repo, all projects get changes
❌ **External dependency** - Requires access to central repo

**Use when**: You have 5+ projects and want consistent standards.

#### Pattern B: Embedded (For single projects)

✅ **Full control** - Review system lives in your project
✅ **No external deps** - Everything self-contained
❌ **Manual updates** - Must update each project individually
❌ **Code duplication** - Each project has a copy

**Use when**: Single project or full customization needed.

This guide focuses on **Pattern A (Centralized)**, which is recommended.

---

### Step 2: Prepare Your Project

**2.1. Ensure Tool Configuration Files Exist**

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

### Step 3: Configure GitLab CI

**3.1. Create `.gitlab-ci.yml`**

Choose the appropriate template based on your language:

#### Python Project

```yaml
stages:
  - test

ai-review:
  stage: test
  image: python:3.11-slim

  # Only run on merge requests
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

  before_script:
    # Install UV
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

  script:
    # Clone centralized review system
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review
    - uv sync

    # Run review
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR" \
        --config "$CI_PROJECT_DIR/.gitlab/ai-review-config.yml"

  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY

  # Optional: Control when job runs
  interruptible: true
  timeout: 15m
```

#### JavaScript/TypeScript Project

```yaml
stages:
  - test

ai-review:
  stage: test
  image: node:20-slim

  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

  before_script:
    # Install Python + UV
    - apt-get update && apt-get install -y python3.11 curl
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

    # Install project dependencies
    - cd "$CI_PROJECT_DIR" && npm ci

  script:
    # Clone and run review system
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR"

  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

#### Multi-language Project

```yaml
ai-review:
  stage: test
  image: ubuntu:22.04

  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"

  before_script:
    # Install all language toolchains
    - apt-get update
    - apt-get install -y curl git python3.11 python3.11-venv

    # Install Node.js
    - curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    - apt-get install -y nodejs

    # Install Java (if needed)
    - apt-get install -y openjdk-17-jdk maven

    # Install UV
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

  script:
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR"

  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

---

### Step 4: Add Secrets to GitLab

**4.1. Navigate to CI/CD Settings**

Go to: `Your Project → Settings → CI/CD → Variables`

**4.2. Add ANTHROPIC_API_KEY**

Click **"Add variable"** and configure:

- **Key**: `ANTHROPIC_API_KEY`
- **Value**: Your API key (get from [Anthropic Console](https://console.anthropic.com/))
- **Type**: Variable
- **Environment scope**: All (default)
- **Flags**:
  - ✅ **Protect variable** - Only available to protected branches
  - ✅ **Mask variable** - Hide in job logs
  - ❌ **Expand variable** - Leave unchecked

**4.3. Verify CI_JOB_TOKEN**

GitLab automatically provides `CI_JOB_TOKEN` - you don't need to add it manually. This token is used to post comments and update pipeline status.

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

**Create `.gitlab/ai-review-config.yml`** in your project root:

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
    type: static
    tools: ["ruff", "pylint", "bandit", "mypy"]

  # AI reviews
  - name: security_review
    type: ai
    prompt_file: prompts/security-review.md

  - name: architecture_review
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

**6.1. Create a Test Merge Request**

Make a simple code change and create an MR:

```bash
git checkout -b test-ai-review
echo "# Test" >> README.md
git add README.md
git commit -m "Test AI review integration"
git push origin test-ai-review
```

Then create an MR in GitLab UI.

**6.2. Monitor Pipeline**

Go to: `Your MR → Pipelines Tab`

You should see:
- ✅ `ai-review` job running
- ⏱️ Typically takes 1-2 minutes
- 📊 View logs to see progress

**6.3. Check Results**

After completion:
- **Summary Comment** - Posted to MR overview
- **Inline Discussions** - On specific lines with issues
- **Pipeline Status** - Green (passed) or red (blocked)

---

## GitLab CI Configuration

### Environment Variables Reference

#### Required Variables

| Variable | Source | Description |
|----------|--------|-------------|
| `ANTHROPIC_API_KEY` | CI/CD Settings | Your Anthropic API key for Claude |
| `CI_JOB_TOKEN` | Auto-provided | GitLab token for API access |
| `CI_PROJECT_PATH` | Auto-provided | Project namespace/name (e.g., `myorg/myproject`) |
| `CI_MERGE_REQUEST_IID` | Auto-provided | Internal MR number |
| `CI_PROJECT_DIR` | Auto-provided | Path to cloned project |

#### Optional Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `CI_SERVER_URL` | `https://gitlab.com` | GitLab instance URL (for self-hosted) |
| `GITLAB_TOKEN` | - | Alternative to `CI_JOB_TOKEN` (for personal access tokens) |
| `CLAUDE_API_URL` | - | Custom Claude API endpoint (for proxy) |

### Job Configuration Options

```yaml
ai-review:
  stage: test  # or 'review', 'quality', etc.

  # Runner tags (if using specific runners)
  tags:
    - docker
    - linux

  # Resource limits
  timeout: 15m  # Max time for review

  # Allow manual triggering
  when: manual  # Change to 'on_success' for automatic

  # Allow cancellation
  interruptible: true

  # Retry on failure
  retry:
    max: 1
    when:
      - runner_system_failure
      - stuck_or_timeout_failure

  # Cache dependencies
  cache:
    key: ${CI_COMMIT_REF_SLUG}
    paths:
      - .uv/
      - /tmp/review/.venv/
```

---

## Platform Differences

### API Terminology

| Concept | GitHub | GitLab |
|---------|--------|--------|
| **Change Request** | Pull Request (PR) | Merge Request (MR) |
| **Identifier** | PR number | MR IID (internal ID) |
| **Comment** | Issue comment | Note |
| **Inline Comment** | Review comment | Discussion |
| **Status Check** | Commit status | Pipeline status |
| **Token** | `GITHUB_TOKEN` | `CI_JOB_TOKEN` or `GITLAB_TOKEN` |

### Command Line Arguments

**GitHub**:
```bash
python main.py --repo owner/repo --pr 123
```

**GitLab**:
```bash
# Using namespace/project
python main.py --repo myorg/myproject --pr 456

# Using numeric project ID
python main.py --repo 12345 --pr 456
```

Both are auto-detected - you don't need to specify `--platform`.

### Auto-detection

The system detects the platform via environment variables:

```python
# GitLab detected when:
os.getenv('GITLAB_CI') == 'true'  # Auto-set in GitLab CI

# GitHub detected when:
os.getenv('GITHUB_ACTIONS') == 'true'  # Auto-set in GitHub Actions
```

### Comment Formatting

The same comment formatting works on both platforms:

- ✅ Markdown syntax (headers, lists, code blocks)
- ✅ Emoji support
- ✅ Code syntax highlighting
- ✅ Collapsible sections (HTML `<details>`)

### Status States

| State | GitHub | GitLab |
|-------|--------|--------|
| **Success** | `success` | `success` |
| **Failure** | `failure` | `failed` |
| **Pending** | `pending` | `running` |

The platform abstraction handles this automatically.

---

## Advanced Configuration

### Self-Hosted GitLab Instance

If using self-hosted GitLab, set the instance URL:

```yaml
variables:
  CI_SERVER_URL: "https://gitlab.company.com"
  ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

### Using Personal Access Token

Instead of `CI_JOB_TOKEN`, you can use a personal access token:

1. Create token: `User Settings → Access Tokens`
2. Scopes needed: `api`, `read_repository`, `write_repository`
3. Add to CI/CD variables as `GITLAB_TOKEN`

```yaml
variables:
  GITLAB_TOKEN: $GITLAB_TOKEN  # Instead of CI_JOB_TOKEN
  ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

### Company-Wide Policies

Load organization-wide standards from a centralized config:

```yaml
script:
  - |
    uv run python main.py \
      --repo "$CI_PROJECT_PATH" \
      --pr "$CI_MERGE_REQUEST_IID" \
      --project-root "$CI_PROJECT_DIR" \
      --company-config "https://gitlab.com/your-org/policies/-/raw/main/code-review.yml"
```

The company config is merged with project config (project wins).

### Caching Dependencies

Speed up subsequent runs by caching:

```yaml
cache:
  key: ai-review-deps
  paths:
    - .uv/cache/
    - /tmp/review/.venv/
  policy: pull-push

variables:
  UV_CACHE_DIR: .uv/cache
```

### Parallel Jobs

Run reviews in parallel for faster results:

```yaml
ai-review-static:
  extends: .ai-review-base
  script:
    - uv run python main.py --only-static ...

ai-review-ai:
  extends: .ai-review-base
  script:
    - uv run python main.py --only-ai ...
```

(Note: Requires custom orchestration - not built-in yet)

---

## Troubleshooting

### Issue: "GitLab token required"

**Cause**: `CI_JOB_TOKEN` not available or insufficient permissions.

**Solution**:
1. Verify CI/CD is enabled: `Settings → General → Visibility → CI/CD → Enabled`
2. Check permissions: Job needs `read_api` and `write_repository` access
3. Or use personal access token as `GITLAB_TOKEN`

### Issue: "Cannot fetch merge request"

**Cause**: Wrong project identifier or MR doesn't exist.

**Solution**:
```bash
# Check variables in job logs:
echo "Project: $CI_PROJECT_PATH"
echo "MR IID: $CI_MERGE_REQUEST_IID"

# Verify MR exists:
curl --header "PRIVATE-TOKEN: $CI_JOB_TOKEN" \
  "$CI_API_V4_URL/projects/$CI_PROJECT_ID/merge_requests/$CI_MERGE_REQUEST_IID"
```

### Issue: "Failed to post comment"

**Cause**: Token lacks permissions to write notes.

**Solution**:
- Ensure `CI_JOB_TOKEN` has `write_repository` scope
- Or create personal access token with `api` scope
- Check project settings allow API access

### Issue: "Review system clone failed"

**Cause**: Network issues or private repo access.

**Solution**:
```yaml
# Use HTTPS with token for private repos:
script:
  - git clone https://oauth2:$GITLAB_TOKEN@gitlab.com/your-org/review-system.git

# Or use SSH with deploy keys
```

### Issue: "UV installation failed"

**Cause**: Network issues or architecture mismatch.

**Solution**:
```yaml
before_script:
  # Add retry logic
  - for i in 1 2 3; do curl -LsSf https://astral.sh/uv/install.sh | sh && break || sleep 5; done
  - export PATH="$HOME/.cargo/bin:$PATH"
  - uv --version  # Verify installation
```

### Issue: "Python version mismatch"

**Cause**: Image has wrong Python version.

**Solution**:
```yaml
# Use specific Python image
image: python:3.11-slim

# Or install specific version with UV:
script:
  - uv python install 3.11
  - uv python pin 3.11
```

### Debugging Tips

**Enable verbose logging**:
```yaml
variables:
  PYTHONUNBUFFERED: "1"  # Real-time output
  DEBUG: "1"              # If review system supports it
```

**Check environment**:
```yaml
script:
  - echo "=== Environment ==="
  - env | grep CI_
  - echo "=== Git Info ==="
  - git branch -a
  - git log -1
```

**Test locally with GitLab CLI**:
```bash
# Install glab CLI
brew install glab

# Test MR fetch
glab mr view 123

# Test API access
curl --header "PRIVATE-TOKEN: $TOKEN" \
  "https://gitlab.com/api/v4/projects/12345/merge_requests/123"
```

---

## Examples

### Example 1: Python FastAPI Project

**`.gitlab-ci.yml`**:
```yaml
stages:
  - test
  - review

# Run tests first
test:
  stage: test
  image: python:3.11
  script:
    - pip install -r requirements.txt
    - pytest

# Then run AI review
ai-review:
  stage: review
  image: python:3.11-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"
  script:
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR" \
        --config "$CI_PROJECT_DIR/.gitlab/ai-review-config.yml"
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

**`.gitlab/ai-review-config.yml`**:
```yaml
project_context:
  name: "Payment API"
  architecture: "FastAPI Microservice"

project_constraints:
  - "Use Decimal for money, never float"
  - "All endpoints must have OpenAPI docs"

review_aspects:
  - name: python_static_analysis
    type: static
    tools: ["ruff", "bandit", "mypy"]

  - name: security_review
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

### Example 2: React TypeScript Project

**`.gitlab-ci.yml`**:
```yaml
ai-review:
  stage: test
  image: node:20
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    # Install Python + UV
    - apt-get update && apt-get install -y python3.11 curl
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

    # Install project deps
    - npm ci
  script:
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR"
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

### Example 3: Monorepo (Python + TypeScript)

**`.gitlab-ci.yml`**:
```yaml
ai-review:
  stage: test
  image: ubuntu:22.04
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    - apt-get update
    - apt-get install -y curl git python3.11

    # Node.js
    - curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
    - apt-get install -y nodejs

    # UV
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.cargo/bin:$PATH"

    # Install all project deps
    - cd "$CI_PROJECT_DIR/backend" && uv sync
    - cd "$CI_PROJECT_DIR/frontend" && npm ci
  script:
    - git clone --depth 1 https://github.com/your-org/ai-review-cicd-actions.git /tmp/review
    - cd /tmp/review && uv sync
    - |
      uv run python main.py \
        --repo "$CI_PROJECT_PATH" \
        --pr "$CI_MERGE_REQUEST_IID" \
        --project-root "$CI_PROJECT_DIR"
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
```

---

## Next Steps

1. **Test Integration** - Create a test MR and verify comments appear
2. **Tune Configuration** - Adjust blocking rules and review aspects
3. **Share Knowledge** - Document your setup for team members
4. **Monitor Costs** - Track Anthropic API usage (typically $0.03-0.05 per MR)
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
