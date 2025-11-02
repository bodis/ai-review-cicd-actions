# Quick Start Guide

Get up and running with AI Code Review in 5 minutes!

## 🚀 For Project Teams (Using the System)

### Step 1: Add the Workflow

Create `.github/workflows/code-review.yml` in your project:

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize, reopened]

jobs:
  code-review:
    uses: your-org/ai-review-cicd-actions/.github/workflows/reusable-ai-review.yml@main
    secrets:
      GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
      ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
    permissions:
      contents: read
      pull-requests: write
      statuses: write
```

### Step 2: Add API Key

1. Go to your repository Settings → Secrets and variables → Actions
2. Add `ANTHROPIC_API_KEY` with your Claude API key

### Step 3: Create a Pull Request

That's it! Create a PR and watch the AI review happen automatically.

## 🎨 Customization (Optional)

### Add Project Configuration

Create `.github/ai-review-config.yml`:

```yaml
project_context:
  name: "My Awesome Project"
  architecture: "Microservices"

blocking_rules:
  block_on_critical: true
  max_findings:
    critical: 0
    high: 3
```

### Add Custom Rules

```yaml
custom_rules:
  - pattern: "console.log"
    message: "Remove console.log before merging"
    severity: "medium"

  - pattern: "TODO:"
    message: "Create a ticket for this TODO"
    severity: "low"
```

## 📊 What You'll Get

### PR Summary Comment

```markdown
# 🤖 AI Code Review

## ✅ Review Status: APPROVED

### 📊 Summary
- Total Findings: 12
- Execution Time: 45.2s
- Files Changed: 8
- Languages: python, javascript

### Findings by Severity
- 🔴 CRITICAL: 0
- 🟠 HIGH: 2
- 🟡 MEDIUM: 5
- 🔵 LOW: 5
```

### Inline Comments

Comments on specific lines with:
- Severity and category
- Clear description
- Actionable suggestions
- Tool that detected it

### Status Checks

✅ or ❌ status check that can block merging

## 🔧 Troubleshooting

### Review Fails to Run

**Problem:** Workflow doesn't trigger
- Check that the workflow file is in `.github/workflows/`
- Verify the `on:` trigger includes `pull_request`
- Make sure you have the correct permissions

**Problem:** Missing ANTHROPIC_API_KEY
- Add the secret in repository settings
- Use organization-level secrets for multiple repos

### Review Blocks PR Unexpectedly

**Problem:** Too strict blocking rules
- Adjust `blocking_rules` in your config
- Increase `max_findings` thresholds
- Set `block_on_high: false` if needed

### Analysis Tools Not Found

**Problem:** Python/JS tools missing
- Make sure `requirements.txt` or `package.json` exists
- The workflow installs tools automatically
- Check workflow logs for installation errors

## 💡 Tips

1. **Start with defaults** - Use the system without customization first
2. **Tune gradually** - Adjust blocking rules based on your team's needs
3. **Add custom rules** - Define project-specific patterns over time
4. **Review the reviews** - Periodically check if findings are helpful
5. **Provide feedback** - File issues for false positives or missing checks

## 📚 Next Steps

- Read the full [README.md](README.md)
- Check out [examples/](examples/) for advanced configurations
- Join discussions in our GitHub Discussions

## 🆘 Need Help?

- Check [GitHub Issues](https://github.com/your-org/ai-review-cicd-actions/issues)
- Read the [FAQ](docs/FAQ.md)
- Contact your DevOps team

---

Happy reviewing! 🎉
