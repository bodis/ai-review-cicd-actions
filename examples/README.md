# Integration Examples

This directory contains complete examples for integrating the AI code review system into your projects. There are **two integration patterns**, each with different use cases and tradeoffs.

## 📁 Directory Structure

```
examples/
├── README.md                    # This file
├── local-pattern/               # Copy review system into your project
│   ├── python-workflow.yml     # Python project example
│   ├── python-config.yml
│   ├── java-workflow.yml       # Java/Spring Boot example
│   └── java-config.yml
├── reusable-pattern/            # Reference centralized review system
│   ├── python-workflow.yml     # Python project example
│   ├── java-workflow.yml       # Java/Spring Boot example
│   └── config-example.yml
└── company-policies/            # Company-wide policy examples
    └── example-policies.yml
```

---

## 🎯 Two Integration Patterns

### 1. Local Pattern (`local-pattern/`)

**Copy the review system code into your project**

```
Your Project Repo
├── .github/workflows/ai-review.yml  ← Workflow runs locally
├── lib/                              ← Review system code (copied)
├── prompts/                          ← Review prompts (copied)
├── main.py                           ← Review entry point (copied)
└── your-code/
```

**When to use**:
- ✅ Single project or small team
- ✅ Want full control over review logic
- ✅ Can customize review code per project
- ✅ Don't mind code duplication

**Pros**:
- Full control and customization
- Can modify review logic
- No external dependencies
- Simpler to understand

**Cons**:
- Must update review code manually in each repo
- Code duplication across projects
- Harder to maintain consistency

**Setup**:
```bash
# 1. Copy review system to your project
cp -r /path/to/ai-review-cicd-actions/{lib,prompts,main.py,pyproject.toml} .

# 2. Copy workflow
cp examples/local-pattern/python-workflow.yml .github/workflows/ai-review.yml

# 3. Copy config
cp examples/local-pattern/python-config.yml .github/ai-review-config.yml

# 4. Add secret: ANTHROPIC_API_KEY
```

---

### 2. Reusable Pattern (`reusable-pattern/`)

**Reference a centralized review system (no code copy needed)**

```
Your Project Repo
├── .github/workflows/ai-review.yml  ← Calls external workflow
└── your-code/

Centralized Review System Repo (separate)
├── .github/workflows/reusable-ai-review.yml  ← Reusable workflow
├── lib/                                       ← Review system code
├── prompts/
└── main.py
```

**When to use**:
- ✅ Multiple projects (10+ repos)
- ✅ Want centralized maintenance
- ✅ Need consistent review standards
- ✅ Have DevOps/platform team

**Pros**:
- Zero code duplication
- Single source of truth
- Easy to update all projects at once
- Enforces consistency

**Cons**:
- External dependency on review system repo
- Less flexibility per project
- Requires understanding reusable workflows
- Can't easily customize per repo

**Setup**:
```bash
# 1. Copy workflow (just 20 lines!)
cp examples/reusable-pattern/python-workflow.yml .github/workflows/ai-review.yml

# 2. Edit to point to YOUR review system repo
# Change: your-org/ai-review-cicd-actions
# To: your-actual-org/actual-repo-name

# 3. Add config (optional, can use defaults)
cp examples/reusable-pattern/config-example.yml .github/ai-review-config.yml

# 4. Add secret: ANTHROPIC_API_KEY
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

### For Single Project (Recommended: Local Pattern)

```bash
# 1. Choose your language
LANG="python"  # or "java"

# 2. Copy the review system
git clone https://github.com/your-org/ai-review-cicd-actions review-system
cp -r review-system/{lib,prompts,main.py,pyproject.toml,uv.lock} .

# 3. Copy workflow and config
cp review-system/examples/local-pattern/${LANG}-workflow.yml .github/workflows/ai-review.yml
cp review-system/examples/local-pattern/${LANG}-config.yml .github/ai-review-config.yml

# 4. Clean up
rm -rf review-system

# 5. Add secret on GitHub
# Settings → Secrets → Actions → New secret
# Name: ANTHROPIC_API_KEY
# Value: sk-ant-...

# 6. Create a PR and watch it work!
```

### For Organization (Recommended: Reusable Pattern)

```bash
# 1. Set up centralized review system repo (one time)
# - Fork or clone ai-review-cicd-actions
# - Deploy to your-org/code-review-system

# 2. For each project:
LANG="python"  # or "java"

# Copy minimal workflow
cp examples/reusable-pattern/${LANG}-workflow.yml .github/workflows/ai-review.yml

# Edit workflow to reference YOUR repo
sed -i 's|your-org/ai-review-cicd-actions|your-org/code-review-system|' .github/workflows/ai-review.yml

# Optional: Add project config
cp examples/reusable-pattern/config-example.yml .github/ai-review-config.yml

# 3. Add secret: ANTHROPIC_API_KEY

# 4. Done! All projects now use centralized review system
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

| Feature | Local Pattern | Reusable Pattern |
|---------|--------------|------------------|
| **Setup complexity** | Medium | Low |
| **Code duplication** | High (copy all code) | None (reference only) |
| **Customization** | Full (edit anything) | Limited (config only) |
| **Maintenance** | Per-repo updates | Central updates |
| **Best for** | 1-10 projects | 10+ projects |
| **Team size** | Small teams | Organizations |
| **Consistency** | Manual effort | Enforced |

---

## ❓ FAQ

**Q: Which pattern should I use?**
A: Local pattern for single/few projects. Reusable pattern for organizations with 10+ repos.

**Q: Can I switch patterns later?**
A: Yes! The config format is the same. Just change the workflow file.

**Q: Do I need both patterns?**
A: No, choose one. We show both for different use cases.

**Q: What about JavaScript/TypeScript?**
A: Python examples work similarly. See [docs/JAVASCRIPT_INTEGRATION.md](../docs/JAVASCRIPT_INTEGRATION.md).

**Q: Can I mix patterns?**
A: Yes, some projects can use local, others reusable. Depends on needs.

**Q: How do I update the review system?**
A:
- **Local**: Git pull + copy files to each repo
- **Reusable**: Update central repo once, all projects get update

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
