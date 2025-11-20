"""
Generate rich PR comments using direct Anthropic API.

This module uses the Anthropic SDK directly (not Claude Code CLI) for performance:
- 10x faster than CLI subprocess calls
- Batch comment generation
- Prompt caching support
- Better cost efficiency
"""

import os

import anthropic

from .models import AggregatedResults, Finding, Metrics, Severity


class CommentGenerator:
    """Generate GitHub PR comments using Anthropic API."""

    # System prompt with caching
    SYSTEM_PROMPT = """You are a helpful code review assistant for GitHub Pull Requests.

Your role:
- Generate clear, actionable code review comments
- Be professional but friendly
- Focus on helping developers improve their code
- Provide specific fix suggestions with code examples
- Use appropriate emoji for visual clarity

Comment style guide:
- 🔒 Use for security issues
- ⚡ Use for performance issues
- 🏗️ Use for architecture issues
- ✨ Use for code quality improvements
- 🧪 Use for testing issues
- Keep comments concise (under 500 characters for inline, 2000 for summary)
- Always include "why this matters" and "how to fix"
- Use code blocks with syntax highlighting"""

    def __init__(
        self, api_key: str | None = None, metrics: Metrics | None = None, model: str | None = None
    ):
        """
        Initialize comment generator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            metrics: Metrics object for tracking token usage
            model: Claude model to use (default: claude-sonnet-4-5-20250929)
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model or "claude-sonnet-4-5-20250929"
        self.metrics = metrics  # Optional metrics tracking

    def generate_inline_comment(self, finding: Finding) -> str:
        """
        Generate a single inline PR comment.

        Args:
            finding: The finding to create a comment for

        Returns:
            Formatted comment text
        """
        severity_emoji = {
            Severity.CRITICAL: "🔴",
            Severity.HIGH: "🟠",
            Severity.MEDIUM: "🟡",
            Severity.LOW: "🔵",
            Severity.INFO: "⚪",
        }

        category_emoji = {
            "security": "🔒",
            "performance": "⚡",
            "architecture": "🏗️",
            "code_quality": "✨",
            "testing": "🧪",
        }

        # Build aspect information if available
        aspect_info = ""
        if finding.aspect:
            aspect_display = finding.aspect.replace("_", " ").title()
            aspect_info = f"\n**Review Aspect**: {aspect_display}"

        prompt = f"""Generate a concise GitHub PR inline comment for this code issue:

**Severity**: {finding.severity.value.upper()} {severity_emoji.get(finding.severity, "")}
**Category**: {finding.category.value} {category_emoji.get(finding.category.value, "")}{aspect_info}
**Issue**: {finding.message}

Code context:
```python
{finding.code_snippet if finding.code_snippet else "(code snippet not available)"}
```

Generate a comment that:
1. Explains the issue clearly (1-2 sentences)
2. Shows why it matters (security risk? performance impact? maintainability?)
3. Provides a specific fix with code example
4. Stays under 500 characters
5. Include aspect information at the bottom

Format:
{category_emoji.get(finding.category.value, "•")} **[Issue description]**

Why this matters: [brief explanation]

**Fix**:
```[language]
[code example]
```

*Detected by: {aspect_display if finding.aspect else "AI Review"}*

Output only the comment, no preamble."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=400,
            temperature=0.3,  # Lower temperature for consistent formatting
            system=[
                {
                    "type": "text",
                    "text": self.SYSTEM_PROMPT,
                    "cache_control": {"type": "ephemeral"},  # Cache system prompt
                }
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response, handling different content block types
        first_block = response.content[0]
        if hasattr(first_block, "text"):
            comment = first_block.text.strip()
        else:
            comment = str(first_block).strip()

        # Track usage
        self._log_usage(response.usage, "inline_comment")

        return comment

    def generate_batch_comments(self, findings: list[Finding], batch_size: int = 5) -> list[str]:
        """
        Generate multiple inline comments efficiently.

        Args:
            findings: List of findings to generate comments for
            batch_size: Number of findings per API call (max 5 for quality)

        Returns:
            List of comments (same order as findings)
        """
        all_comments = []

        # Process in batches
        for i in range(0, len(findings), batch_size):
            batch = findings[i : i + batch_size]
            batch_comments = self._generate_batch_internal(batch)
            all_comments.extend(batch_comments)

        return all_comments

    def _generate_batch_internal(self, findings: list[Finding]) -> list[str]:
        """Generate comments for a batch of findings in one API call."""

        # Build batch prompt
        prompt = "Generate concise GitHub PR comments for these code issues:\n\n"

        for i, finding in enumerate(findings, 1):
            aspect_text = f" ({finding.aspect.replace('_', ' ').title()})" if finding.aspect else ""
            prompt += f"""**Finding {i}**:
- Severity: {finding.severity.value}
- Category: {finding.category.value}{aspect_text}
- Issue: {finding.message}
- Location: {finding.file_path}:{finding.line_number}
- Code: {finding.code_snippet[:100] if finding.code_snippet else "N/A"}

"""

        prompt += """For each finding, generate a comment with:
- Appropriate emoji (🔒 security, ⚡ performance, 🏗️ architecture, ✨ quality, 🧪 testing)
- Clear issue description
- Why it matters
- Specific fix with code example
- Under 500 characters each

Output format:
### Finding 1
[comment text]

### Finding 2
[comment text]

etc."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=2000,
            temperature=0.3,
            system=[
                {"type": "text", "text": self.SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        # Parse batch response, handling different content block types
        first_block = response.content[0]
        if hasattr(first_block, "text"):
            batch_text = first_block.text
        else:
            batch_text = str(first_block)
        comments = self._parse_batch_response(batch_text, len(findings))

        # Track usage
        self._log_usage(response.usage, f"batch_{len(findings)}_comments")

        return comments

    def _parse_batch_response(self, batch_text: str, expected_count: int) -> list[str]:
        """Parse batch response into individual comments."""
        import re

        comments = []
        sections = re.split(r"### Finding \d+", batch_text)

        for section in sections[1:]:  # Skip first empty section
            comment = section.strip()
            if comment:
                comments.append(comment)

        # Fallback if parsing fails
        if len(comments) != expected_count:
            print(f"⚠️ Warning: Expected {expected_count} comments, got {len(comments)}")
            # Pad with simple messages
            while len(comments) < expected_count:
                comments.append("Code review finding (see details in summary)")

        return comments[:expected_count]

    def generate_summary_comment(self, results: AggregatedResults) -> str:
        """
        Generate comprehensive PR summary comment.

        Args:
            results: Aggregated review results

        Returns:
            Rich markdown summary comment
        """
        # Build statistics
        stats = results.statistics
        critical_count = stats["by_severity"].get("critical", 0)
        high_count = stats["by_severity"].get("high", 0)
        medium_count = stats["by_severity"].get("medium", 0)

        # Get top issues (max 5)
        top_findings = sorted(
            results.all_findings, key=lambda f: (f.severity.value, f.category.value)
        )[:5]

        top_issues_text = ""
        for i, finding in enumerate(top_findings, 1):
            top_issues_text += (
                f"{i}. **{finding.severity.value.upper()}** - {finding.message[:100]}\n"
            )

        # Build improvement suggestions for approved PRs
        improvements_section = ""
        if not results.should_block and stats["total"] > 0:
            # Get lower severity findings for improvement suggestions
            low_severity_findings = [
                f
                for f in results.all_findings
                if f.severity in [Severity.MEDIUM, Severity.LOW, Severity.INFO]
            ]
            if low_severity_findings:
                improvements_text = "\n**Lower Priority Improvements**:\n"
                for f in low_severity_findings[:5]:  # Top 5 improvement suggestions
                    improvements_text += f"- {f.message[:80]}...\n"
                improvements_section = f"\n{improvements_text}"

        prompt = f"""Generate an engaging GitHub Pull Request summary comment for code review results.

**Review Status**: {"❌ BLOCKED" if results.should_block else "✅ APPROVED"}
{f"**Block Reason**: {results.blocking_reason}" if results.should_block else ""}

**Statistics**:
- Total findings: {stats["total"]}
- 🔴 Critical: {critical_count}
- 🟠 High: {high_count}
- 🟡 Medium: {medium_count}
- ⏱️ Execution time: {results.total_execution_time:.1f}s
- 📁 Files changed: {len(results.pr_context.changed_files)}
- 🔤 Languages: {", ".join(results.pr_context.detected_languages)}

**Top Issues**:
{top_issues_text}

**Review Aspects Executed**:
{", ".join([r.aspect_name for r in results.review_results])}{improvements_section}

Create a professional, encouraging summary comment with:

1. **Clear status badge** at top (✅ APPROVED or ❌ BLOCKED)
2. **Executive summary** (2-3 sentences about overall code quality)
3. **Key metrics table** (well-formatted markdown)
4. **Top 3-5 issues** highlighted with severity
5. **Category breakdown** (security, architecture, quality, etc.)
6. **Actionable next steps** for the developer
7. {"**Optional Improvements section** (if approved but has lower-severity findings)" if not results.should_block and stats["total"] > 0 else ""}
8. **Encouraging tone** (celebrate good practices, guide on improvements)
9. **Emoji usage** for visual clarity
10. **Maximum 2000 characters**

Use proper markdown formatting: tables, bold, lists, code blocks where appropriate.

Output only the comment, no preamble."""

        response = self.client.messages.create(
            model=self.model,
            max_tokens=1500,
            temperature=0.5,  # Slightly higher for engaging tone
            system=[
                {"type": "text", "text": self.SYSTEM_PROMPT, "cache_control": {"type": "ephemeral"}}
            ],
            messages=[{"role": "user", "content": prompt}],
        )

        # Extract text from response, handling different content block types
        first_block = response.content[0]
        if hasattr(first_block, "text"):
            summary = first_block.text.strip()
        else:
            summary = str(first_block).strip()

        # Track usage
        self._log_usage(response.usage, "summary_comment")

        return summary

    def _log_usage(self, usage, operation: str):
        """Log token usage and cost, and track in metrics."""
        input_tokens = getattr(usage, "input_tokens", 0)
        output_tokens = getattr(usage, "output_tokens", 0)
        cache_read_tokens = getattr(usage, "cache_read_input_tokens", 0)
        cache_creation_tokens = getattr(usage, "cache_creation_input_tokens", 0)

        # Calculate cost (Claude 3.5 Sonnet pricing)
        input_cost = input_tokens * 0.000003
        output_cost = output_tokens * 0.000015
        cache_read_cost = cache_read_tokens * 0.0000003  # 90% discount
        cache_write_cost = cache_creation_tokens * 0.00000375  # 25% markup

        total_cost = input_cost + output_cost + cache_read_cost + cache_write_cost

        print(f"💬 {operation}: {input_tokens} in, {output_tokens} out, ${total_cost:.4f}")

        if cache_read_tokens > 0:
            savings = cache_read_tokens * 0.0000027
            print(f"   📦 Cache hit: {cache_read_tokens} tokens (saved ${savings:.4f})")

        # Track in metrics if available
        if self.metrics:
            self.metrics.add_tokens(input_tokens, output_tokens, cache_read_tokens)
