# Self-Review Setup

This directory contains the configuration for **this project to review itself** (dogfooding). It demonstrates the **recommended pattern** for integrating the AI code review system into your own projects.

## 📁 Contents

- **`config.yml`** - Review configuration (Python-only analysis for this project)
- **`workflow.yml`** - GitHub Actions workflow (copy this to `.github/workflows/`)

## 🎯 Purpose

This setup serves two purposes:

1. **Dogfooding** - We use our own review system on every PR to this repository
2. **Example** - Shows the **simple, recommended pattern** for other projects

## 🚀 How It Works

### For This Project

The workflow in `.github/workflows/ai-code-review.yml` uses `self/config.yml` to review Python code in every PR.

### For Your Project

**Copy this pattern:**

```bash
# 1. Copy the workflow to your repo
cp self/workflow.yml .github/workflows/ai-review.yml

# 2. Create your own config (or use examples/)
cp self/config.yml .github/ai-review-config.yml

# 3. Customize for your languages
# Edit .github/ai-review-config.yml to enable JS/TS/Java if needed

# 4. Add secret to GitHub
# Settings → Secrets → Actions → New secret
# Name: ANTHROPIC_API_KEY
# Value: sk-ant-...
```

## 📝 Configuration Explained

```yaml
review_aspects:
  # Static analysis (fast, parallel)
  - name: python_static_analysis
    enabled: true
    type: classical
    parallel: true
    tools:
      - ruff
      - pylint
      - bandit
      - mypy

  # AI reviews (deep, sequential)
  - name: security_review
    enabled: true
    type: ai
    parallel: false
    prompt_file: prompts/security-review.md

blocking_rules:
  block_on_critical: true    # Block if ANY critical issues
  block_on_high: false        # Don't block on high severity
  max_findings:
    critical: 0               # Allow 0 critical
    high: 5                   # Allow up to 5 high severity

github:
  post_summary_comment: true
  post_inline_comments: true
  inline_comment_severity_threshold: high
  update_status_check: true
```

## 🔧 Key Design Decisions

### Why No Inline Python Code?

Notice `workflow.yml` has **no inline Python scripts**. That's because:

✅ **`main.py` already handles exit codes properly**:
- Returns exit code `1` if review blocks
- Returns exit code `0` if review passes
- GitHub Actions automatically fails on non-zero exit code

❌ **Don't do this** (you'll see this in other examples):
```yaml
# BAD: Inline result checking
- name: Check review status
  run: |
    cat > check_results.py << 'EOF'
    import json
    # ... 20 lines of inline Python ...
    EOF
    python check_results.py
```

✅ **Do this instead** (what we do):
```yaml
# GOOD: Just run main.py - it handles everything
- name: Run AI Code Review
  run: |
    uv run python main.py --repo ... --pr ...
# That's it! Workflow fails automatically if review blocks
```

### Why Separate `self/` Directory?

**Separation of concerns**:
- `self/` = How THIS project reviews itself
- `.github/workflows/` = Actual workflows that run
- `examples/` = Example configs for OTHER projects

This makes it clear:
- **Want to use this system?** → Look at `self/` and `examples/`
- **Want to understand the code?** → Look at `lib/`
- **Want to see it running?** → Look at `.github/workflows/`

### Why Python-Only for Self-Review?

This project is **pure Python** - no JavaScript, no Java. The config reflects that:
- ✅ Python static analyzers (Ruff, Pylint, Bandit, mypy)
- ✅ AI reviews (security, architecture, quality)
- ❌ No ESLint, TSC, SpotBugs (not needed)

For **multi-language projects**, see `examples/` for full configurations.

## 🧪 Testing Locally

```bash
# Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_TOKEN="ghp_..."  # Your personal token

# Run review on a PR
uv run python main.py \
  --repo your-username/ai-review-cicd-actions \
  --pr YOUR_PR_NUMBER \
  --config self/config.yml \
  --output self-review-results.json

# Check results
cat self-review-results.json | jq '.should_block, .all_findings | length'
```

## 💡 What's Different From Other Examples?

### Complex Reusable Workflow (`reusable-ai-review.yml`)

**Purpose**: For organizations with many repos
**Pattern**: External repo → Clone review system → Run on target repo
**Complexity**: High (multiple checkouts, input parameters, secret passing)
**Use case**: Centralized review system across 50+ repositories

### Simple Self-Review (`self/workflow.yml`)

**Purpose**: Single project reviewing itself
**Pattern**: Use code from PR branch directly
**Complexity**: Low (single checkout, simple config)
**Use case**: Individual projects (like this one)

**Most projects should use the simple pattern!**

## 📚 See Also

- **[Main README](../README.md)** - Project overview
- **[Examples](../examples/)** - Multi-language configurations
- **[Python Integration](../docs/PYTHON_INTEGRATION.md)** - Python setup guide
- **[Claude Code Setup](../docs/CLAUDE_CODE_SETUP.md)** - Authentication guide

## ❓ FAQ

**Q: Do I need to copy the inline Python code for checking results?**
A: No! `main.py` already returns the correct exit code. Just run it.

**Q: Can I customize the config for my project?**
A: Yes! See `examples/` for different language combinations.

**Q: Do I need the reusable workflow?**
A: Only if you're managing 10+ repositories. Most projects use the simple pattern.

**Q: Where do I add the ANTHROPIC_API_KEY secret?**
A: Repository Settings → Secrets and variables → Actions → New repository secret

**Q: What about GITHUB_TOKEN?**
A: It's automatically provided by GitHub Actions. Don't add it to secrets.
