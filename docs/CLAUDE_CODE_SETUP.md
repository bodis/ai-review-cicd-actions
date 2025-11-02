# Claude Code CLI Setup Guide

This project uses Claude Code CLI for AI-powered code reviews in CI/CD pipelines.

## Overview

The system uses a **hybrid architecture**:
- **Claude Code CLI**: For semantic code analysis (deep understanding)
- **Direct Anthropic API**: For fast PR comment generation
- **Cost**: ~$0.03-0.05 per PR review

## Authentication Options

### Option 1: API Key (Recommended for CI/CD)

**Best for**: GitHub Actions, automated pipelines, pay-as-you-go usage

1. **Get API Key** from [Anthropic Console](https://console.anthropic.com/)

2. **Add to GitHub Secrets** (ONLY ONE SECRET NEEDED):
   ```
   Repository Settings → Secrets and variables → Actions → New secret
   Name: ANTHROPIC_API_KEY
   Value: sk-ant-api03-...
   ```

   **Note**: `GITHUB_TOKEN` is automatically provided by GitHub Actions - you don't need to add it!

3. **How it works**:
   - Claude Code CLI uses `ANTHROPIC_API_KEY` from environment
   - GitHub Actions provides `GITHUB_TOKEN` automatically
   - Workflow sets both in the environment for the review script

**Cost**: Pay-as-you-go API rates
- Claude 3.5 Sonnet: $3/1M input tokens, $15/1M output tokens
- Estimated: $0.01-0.05 per PR review

### Option 2: OAuth Token (For Local Development)

**Best for**: Local testing with Claude Pro/Team subscription

```bash
# Generate long-lived token
claude setup-token

# Export for current session
export CLAUDE_CODE_OAUTH_TOKEN=$(cat ~/.claude/oauth_token)
```

## Installation

### In GitHub Actions (Automated)

The workflow automatically installs Claude Code CLI:

```yaml
- name: Install Claude Code CLI
  run: npm install -g @anthropic-ai/claude-code
```

### Local Development

```bash
# Install Claude Code via npm
npm install -g @anthropic-ai/claude-code

# Verify installation
claude --version
```

## Configuration

### Set API Key

```bash
# Export for current session
export ANTHROPIC_API_KEY="sk-ant-api03-..."

# Add to shell profile for persistence
echo 'export ANTHROPIC_API_KEY="sk-ant-api03-..."' >> ~/.bashrc
source ~/.bashrc
```

### Environment Variables

The system uses these environment variables:

```bash
# Required for local development
export ANTHROPIC_API_KEY="sk-ant-..."      # For Claude Code CLI & direct API
export GITHUB_TOKEN="ghp_..."              # For GitHub API access (local only)

# Optional (set automatically in CI)
export CLAUDE_CODE_HEADLESS="1"            # Disable interactive features
export NO_COLOR="1"                        # Disable ANSI colors
```

**Important Notes**:

- **In GitHub Actions**: `GITHUB_TOKEN` is **automatically provided** by GitHub. You don't need to add it to secrets.
- **Locally**: You need to create a personal access token for `GITHUB_TOKEN`

**What you need to add to GitHub Secrets**:
- ✅ `ANTHROPIC_API_KEY` - Required (not auto-provided)
- ❌ `GITHUB_TOKEN` - Not needed (auto-provided by GitHub Actions)

## Checking Authentication Status

### In Claude Code

```bash
# Test authentication
echo "Test" | claude --print "Say 'OK'"

# Should output: OK
```

### Check Usage

Run `/status` in a Claude Code session to see:
- Authentication method (API key or subscription)
- Current model
- Token usage (if applicable)

## Troubleshooting

### "Claude Code CLI not found"

```bash
# Install via npm
npm install -g @anthropic-ai/claude-code

# Verify
which claude
claude --version
```

### "Authentication failed"

```bash
# Check API key format
echo $ANTHROPIC_API_KEY | grep "^sk-ant-" || echo "Invalid format"

# Test authentication
echo "Test" | claude --print "Say OK"
```

### "Permission denied in CI"

The workflow uses `--dangerously-skip-permissions` flag (safe in sandboxed CI environments):

```bash
claude --print --dangerously-skip-permissions prompt.txt
```

### "Command not found" after installation

```bash
# The install script adds Claude to ~/.local/bin
# Make sure it's in your PATH
echo $PATH | grep ".local/bin" || echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

## Cost Management

### Tracking Token Usage

The system automatically tracks and logs token usage:

```
📊 Tokens: 1234 in, 567 out
💰 Cost: $0.0123
```

### Best Practices

1. **Set Spending Limits** in Anthropic Console
2. **Monitor Usage** - Check usage dashboard regularly
3. **Use Caching** - Enable prompt caching to reduce costs
4. **Filter Reviews** - Only run on important PRs

### Cost Optimization

- **Prompt caching**: Reuses system prompts (90% discount)
- **Batch operations**: Generates multiple comments in one API call
- **Selective analysis**: Only reviews changed files
- **Hybrid approach**: Uses cheaper API for simple tasks

## Local Testing

### Test the Complete Pipeline

```bash
# 1. Set environment variables
export ANTHROPIC_API_KEY="sk-ant-..."
export GITHUB_TOKEN="ghp_..."

# 2. Activate virtual environment
source .venv/bin/activate

# 3. Test Claude Code CLI
claude --print "Analyze this code: print('hello')"

# 4. Run review locally (without posting to GitHub)
python main.py \
  --repo owner/repo \
  --pr 123 \
  --no-github-post \
  --output local-review.json

# 5. Check results
cat local-review.json | jq '.should_block, .all_findings | length'
```

### Test Just the Comment Generator

```python
from lib.comment_generator import CommentGenerator
from lib.models import Finding, Severity, FindingCategory

# Create test finding
finding = Finding(
    file_path="test.py",
    line_number=10,
    severity=Severity.HIGH,
    category=FindingCategory.SECURITY,
    message="SQL injection vulnerability",
    tool="test"
)

# Generate comment
generator = CommentGenerator()
comment = generator.generate_inline_comment(finding)
print(comment)
```

## API vs CLI Usage

### When Claude Code CLI is Used

- Security reviews
- Architecture reviews
- Code quality analysis
- Complex semantic understanding

**Why**: Deep context understanding, tool usage capabilities

### When Direct API is Used

- PR summary comments
- Inline comments (batch generation)
- Simple text formatting

**Why**: 10x faster, 37% cheaper, better batching

## GitHub Actions Integration

### Minimal Workflow

```yaml
name: AI Code Review

on:
  pull_request:
    types: [opened, synchronize]

jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Install UV
        uses: astral-sh/setup-uv@v3

      - name: Setup Python
        run: uv python install 3.11

      - name: Install dependencies
        run: uv sync

      - name: Install Claude Code CLI
        run: npm install -g @anthropic-ai/claude-code

      - name: Run Review
        env:
          ANTHROPIC_API_KEY: ${{ secrets.ANTHROPIC_API_KEY }}
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
          CLAUDE_CODE_HEADLESS: '1'
        run: |
          uv run python main.py \
            --repo ${{ github.repository }} \
            --pr ${{ github.event.pull_request.number }}
```

## FAQ

**Q: Do I need a Claude Pro subscription?**
A: No, you just need an Anthropic API key (pay-as-you-go).

**Q: Can I use my existing Claude subscription instead of API key?**
A: For local development, yes. For CI/CD, use API key.

**Q: How much does it cost per PR?**
A: Typically $0.03-0.05 per PR, depending on size and complexity.

**Q: Can I limit costs?**
A: Yes, set spending limits in Anthropic Console and use selective PR reviews.

**Q: What if Claude Code CLI fails?**
A: The system falls back to simple template-based comments.

**Q: Is my code sent to Anthropic?**
A: Yes, changed files are sent for analysis. Don't use on sensitive codebases without approval.

## Support

- **Claude Code Issues**: https://github.com/anthropics/claude-code/issues
- **Anthropic Support**: https://support.anthropic.com/
- **This Project**: https://github.com/your-org/ai-review-cicd-actions/issues
