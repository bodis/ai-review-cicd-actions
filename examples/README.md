# Integration Examples

This directory contains complete examples for integrating the AI code review system into your projects.

## 📁 Directory Structure

```
examples/
├── README.md                    # This file
├── local-pattern/               # Configuration examples
│   ├── python-config.yml       # Python project config
│   └── java-config.yml         # Java/Spring Boot config
├── reusable-pattern/            # Workflow examples
│   ├── python-workflow.yml     # Python project workflow
│   ├── java-workflow.yml       # Java/Spring Boot workflow
│   └── config-example.yml      # Generic config
└── company-policies/            # Company-wide policy examples
    └── example-policies.yml
```

---

## 🎯 Integration Patterns

### 1. Package Installation (Recommended)

**Install the review system as a pip package**

```
Your Project Repo
├── .github/workflows/ai-review.yml  ← Installs package and runs
├── .github/ai-review-config.yml     ← Optional: project config
└── your-code/
```

**When to use**:
- ✅ Any project size
- ✅ Want version pinning
- ✅ Easy updates via version tags
- ✅ Works for both GitHub and GitLab

**Setup**:
```bash
# 1. Create workflow file
# See examples/reusable-pattern/python-workflow.yml

# 2. Add config (optional, uses sensible defaults)
cp examples/local-pattern/python-config.yml .github/ai-review-config.yml

# 3. Add secret: ANTHROPIC_API_KEY
```

**Workflow snippet**:
```yaml
- name: Install AI Review package
  run: |
    uv pip install "ai-code-review @ git+https://github.com/bodis/ai-review-cicd-actions.git@v1.0.0"

- name: Run AI Code Review
  run: uv run ai-review --repo ${{ github.repository }} --pr ${{ github.event.pull_request.number }}
```

---

### 2. Reusable Workflow (GitHub only)

**Use the pre-built reusable workflow**

```
Your Project Repo
├── .github/workflows/ai-review.yml  ← Calls reusable workflow (10 lines!)
└── your-code/
```

**When to use**:
- ✅ GitHub-only projects
- ✅ Minimal setup required
- ✅ Want automatic updates

**Setup**:
```yaml
# .github/workflows/ai-review.yml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    uses: bodis/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      python-version: '3.12'
      package-version: 'main'  # Or pin: 'v1.0.0'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
```

---

## 📚 Example Files Explained

### Local Pattern Examples

#### `python-workflow.yml`
Complete GitHub Actions workflow for Python projects using the local pattern.
- Checks out YOUR code
- Installs UV, Python, dependencies
- Installs Claude Code CLI
- Runs review locally
- Posts results to PR

**Copy to**: `.github/workflows/ai-review.yml`

#### `python-config.yml`
Configuration for Python projects:
- Python static analyzers (Ruff, Pylint, Bandit, mypy)
- AI reviews (security, architecture, quality)
- Blocking rules (when to fail PRs)

**Copy to**: `.github/ai-review-config.yml`

#### `java-workflow.yml`
Complete workflow for Java/Spring Boot projects.
- Builds with Maven
- Runs SpotBugs, PMD, Checkstyle
- Runs AI reviews
- Posts results

**Copy to**: `.github/workflows/ai-review.yml`

#### `java-config.yml`
Configuration for Java projects with Spring Boot specifics.

**Copy to**: `.github/ai-review-config.yml`

---

### Reusable Pattern Examples

#### `python-workflow.yml`
Minimal workflow that calls the centralized review system.
- **Just 20 lines** (vs 80+ for local pattern)
- References external reusable workflow
- Passes configuration and secrets

**Copy to**: `.github/workflows/ai-review.yml`

**Important**: Edit line with `your-org/ai-review-cicd-actions` to point to YOUR centralized review system repo!

#### `java-workflow.yml`
Reusable pattern for Java projects.
- Pre-build step runs Java static analysis
- Then calls centralized AI review

**Copy to**: `.github/workflows/ai-review.yml`

#### `config-example.yml`
Generic configuration that works for both patterns.

**Copy to**: `.github/ai-review-config.yml`

---

### Company Policies Example

#### `example-policies.yml`
Shows how to define company-wide coding standards, security requirements, and architectural rules.

**Use with reusable pattern**:
```yaml
with:
  company-config-url: 'github://your-org/policies/main/code-review.yml'
secrets:
  COMPANY_CONFIG_TOKEN: ${{ secrets.COMPANY_CONFIG_TOKEN }}
```

This allows centralized enforcement of organizational standards across all projects.

---

## 🚀 Quick Start Guides

### For Any Project (Package Installation)

```bash
# 1. Create workflow file (.github/workflows/ai-review.yml)
cat > .github/workflows/ai-review.yml << 'EOF'
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  ai-review:
    uses: bodis/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    with:
      python-version: '3.12'
      package-version: 'main'
    secrets:
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
EOF

# 2. Add secret on GitHub
# Settings → Secrets → Actions → New secret
# Name: ANTHROPIC_API_KEY
# Value: sk-ant-...

# 3. Create a PR and watch it work!
```

### For GitLab Projects

```bash
# 1. Create .gitlab-ci.yml
cat > .gitlab-ci.yml << 'EOF'
ai-review:
  stage: test
  image: python:3.12-slim
  rules:
    - if: $CI_PIPELINE_SOURCE == "merge_request_event"
  before_script:
    - curl -LsSf https://astral.sh/uv/install.sh | sh
    - export PATH="$HOME/.local/bin:$PATH"
    - apt-get update && apt-get install -y nodejs npm git
    - npm install -g @anthropic-ai/claude-code
    - uv pip install "ai-code-review @ git+https://github.com/bodis/ai-review-cicd-actions.git@main"
  script:
    - uv run ai-review --repo "$CI_PROJECT_ID" --pr "$CI_MERGE_REQUEST_IID"
  variables:
    ANTHROPIC_API_KEY: $ANTHROPIC_API_KEY
    CLAUDE_CODE_HEADLESS: '1'
EOF

# 2. Add ANTHROPIC_API_KEY variable in GitLab CI/CD settings

# 3. Create an MR and watch it work!
```

---

## 🔑 Required Secrets

Both patterns need:

### `ANTHROPIC_API_KEY` (Required)
- Get from: https://console.anthropic.com/
- Add to: Repository Settings → Secrets → Actions
- Used for: Claude Code CLI and AI comment generation

### `GITHUB_TOKEN` (Automatic)
- Automatically provided by GitHub Actions
- **Don't add manually** - it's always available
- Used for: PR comments, status checks

### `COMPANY_CONFIG_TOKEN` (Optional, reusable pattern only)
- Only if using private company policies repo
- Personal access token with `repo` scope
- Used for: Fetching company-wide policies

---

## 🔧 Customization Guide

### Adjusting Blocking Rules

Edit your config file:

```yaml
blocking_rules:
  block_on_critical: true    # Block if ANY critical issues
  block_on_high: false        # Don't block on high severity
  max_findings:
    critical: 0               # Allow 0 critical
    high: 5                   # Allow up to 5 high
    medium: 20                # Allow up to 20 medium
```

### Adding Company Policies (Reusable Pattern)

1. Create `code-review-policies` repo
2. Add `code-review.yml`:
```yaml
coding_standards:
  python:
    - "Use type hints for all functions"
    - "Maximum function length: 50 lines"

security_requirements:
  - "All API endpoints must have authentication"
  - "Secrets must be in environment variables"
```

3. Reference in workflow:
```yaml
with:
  company-config-url: 'github://your-org/code-review-policies/main/code-review.yml'
```

### Disabling Specific Reviews

In your config:

```yaml
review_aspects:
  - name: security_review
    enabled: false  # Skip security review

  - name: performance_review
    enabled: true
    type: ai
    prompt_file: prompts/performance-review.md
```

---

## 📊 Pattern Comparison

| Feature | Package Install | Reusable Workflow |
|---------|-----------------|-------------------|
| **Setup complexity** | Low | Very Low |
| **Code duplication** | None (pip install) | None (workflow reference) |
| **Customization** | Full (config only) | Limited (inputs only) |
| **Maintenance** | Version pinning | Auto-updates |
| **Best for** | All projects | GitHub-only |
| **Platform support** | GitHub + GitLab | GitHub only |
| **Version control** | Git tags (v1.0.0) | Branch reference |

---

## ❓ FAQ

**Q: Which pattern should I use?**
A: Package installation for all projects (works on GitHub + GitLab). Reusable workflow for GitHub-only with minimal setup.

**Q: Can I switch patterns later?**
A: Yes! The config format is the same. Just change the workflow file.

**Q: How do I pin to a specific version?**
A: Use git tags: `git+https://github.com/bodis/ai-review-cicd-actions.git@v1.0.0`

**Q: What about JavaScript/TypeScript?**
A: Works automatically! The system detects languages. See [docs/JAVASCRIPT_INTEGRATION.md](../docs/JAVASCRIPT_INTEGRATION.md).

**Q: How do I update the review system?**
A:
- **Package install**: Change version tag in workflow
- **Reusable workflow**: Change `@main` to `@v2.0.0` or update automatically

**Q: Do I need to copy any files?**
A: No! Prompts and config are bundled in the package. Only create `.github/ai-review-config.yml` if you want to customize.

---

## 📖 See Also

- [Main README](../README.md) - Project overview
- [Python Integration Guide](../docs/PYTHON_INTEGRATION.md)
- [JavaScript Integration Guide](../docs/JAVASCRIPT_INTEGRATION.md)
- [Java Integration Guide](../docs/JAVA_INTEGRATION.md)
- [Claude Code Setup](../docs/CLAUDE_CODE_SETUP.md)

---

## 💡 Next Steps

1. **Choose your pattern** (local or reusable)
2. **Pick your language** (Python or Java examples)
3. **Copy the files** to your project
4. **Add ANTHROPIC_API_KEY** secret
5. **Create a PR** to test it!

The review workflow runs automatically on every PR. You'll see:
- ✅ PR check status (pass/fail)
- 💬 Summary comment with statistics
- 📝 Inline comments on specific issues (optional)

Happy reviewing! 🚀
