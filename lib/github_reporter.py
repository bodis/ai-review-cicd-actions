"""
GitHub Reporter - Post results back to GitHub PR.
"""

import os
from typing import Any

from github import Github
from github.PullRequest import PullRequest

from .comment_generator import CommentGenerator
from .models import AggregatedResults, Finding, Metrics, Severity


class GitHubReporter:
    """Posts review results back to GitHub PR."""

    def __init__(
        self,
        github_token: str | None = None,
        anthropic_api_key: str | None = None,
        metrics: Metrics | None = None,
        anthropic_model: str | None = None,
    ):
        """
        Initialize GitHub reporter.

        Args:
            github_token: GitHub API token. If None, uses GITHUB_TOKEN env var.
            anthropic_api_key: Anthropic API key for comment generation
            metrics: Metrics object for tracking token usage
            anthropic_model: Claude model to use (default: claude-sonnet-4-5-20250929)
        """
        token = github_token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required")

        self.github = Github(token)
        self.metrics = metrics

        # Initialize comment generator with direct API (for fast, rich comments)
        api_key = anthropic_api_key or os.getenv("ANTHROPIC_API_KEY")
        try:
            self.comment_generator = (
                CommentGenerator(api_key, metrics=metrics, model=anthropic_model)
                if api_key
                else None
            )
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize CommentGenerator: {e}")
            print("   Falling back to simple comment formatting")
            self.comment_generator = None

    def post_review_results(
        self, repo_name: str, pr_number: int, results: AggregatedResults, config: dict[str, Any]
    ) -> None:
        """
        Post complete review results to GitHub PR.

        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            results: Aggregated review results
            config: Configuration dictionary
        """
        repo = self.github.get_repo(repo_name)
        pr = repo.get_pull(pr_number)

        github_config = config.get("github", {})

        # Post summary comment
        if github_config.get("post_summary_comment", True):
            self.post_summary_comment(pr, results)

        # Post inline comments
        if github_config.get("post_inline_comments", True):
            threshold = github_config.get("inline_comment_severity_threshold", "high")
            self.post_inline_comments(pr, results, threshold)

        # Update status check
        if github_config.get("update_status_check", True):
            self.update_status_check(repo_name, pr, results)

    def post_summary_comment(self, pr: PullRequest, results: AggregatedResults) -> None:
        """
        Post AI-generated summary comment on PR.

        Args:
            pr: Pull request object
            results: Aggregated results
        """
        # Use AI to generate rich summary if available
        if self.comment_generator:
            try:
                print("Generating AI summary comment...")
                summary = self.comment_generator.generate_summary_comment(results)
            except Exception as e:
                print(f"⚠️ AI summary generation failed: {e}, falling back to simple template")
                summary = self._generate_summary(results)
        else:
            summary = self._generate_summary(results)

        # Check if we already posted a comment (look for our marker)
        existing_comment = None
        for comment in pr.get_issue_comments():
            if comment.body.startswith("# 🤖 AI Code Review"):
                existing_comment = comment
                break

        if existing_comment:
            # Update existing comment
            existing_comment.edit(summary)
        else:
            # Create new comment
            pr.create_issue_comment(summary)

    def post_inline_comments(
        self, pr: PullRequest, results: AggregatedResults, severity_threshold: str = "high"
    ) -> None:
        """
        Post AI-generated inline comments on specific lines.

        Args:
            pr: Pull request object
            results: Aggregated results
            severity_threshold: Minimum severity for inline comments
        """
        # Map severity threshold to enum
        severity_levels = {
            "critical": [Severity.CRITICAL],
            "high": [Severity.CRITICAL, Severity.HIGH],
            "medium": [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM],
            "low": [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW],
            "info": list(Severity),
        }

        allowed_severities = severity_levels.get(
            severity_threshold, [Severity.CRITICAL, Severity.HIGH]
        )

        # Filter findings by severity
        inline_findings = [
            f
            for f in results.all_findings
            if f.severity in allowed_severities and f.line_number is not None
        ]

        if not inline_findings:
            return

        print(f"Generating {len(inline_findings)} inline comments...")

        # Generate comments with AI (batch for efficiency)
        if self.comment_generator:
            try:
                comments = self.comment_generator.generate_batch_comments(inline_findings)
            except Exception as e:
                print(f"⚠️ AI comment generation failed: {e}, falling back to simple formatting")
                comments = [self._format_inline_comment(f) for f in inline_findings]
        else:
            comments = [self._format_inline_comment(f) for f in inline_findings]

        # Get the latest commit
        commits = list(pr.get_commits())
        if not commits:
            return

        latest_commit = commits[-1]

        # Post review comments
        for finding, comment_body in zip(inline_findings, comments, strict=True):
            try:
                # Normalize file path to relative path
                # GitHub API expects paths relative to repo root
                file_path = finding.file_path

                # Remove absolute path prefixes if present
                # Handles: /home/runner/work/repo/repo/lib/file.py -> lib/file.py
                if "/" in file_path:
                    # Try to find the repo name in the path and remove everything before it
                    parts = file_path.split("/")
                    # Look for duplicate repo name pattern (common in GH Actions)
                    for i in range(len(parts) - 1):
                        if i > 0 and parts[i] == parts[i - 1]:
                            file_path = "/".join(parts[i + 1 :])
                            break
                    else:
                        # If no duplicate found, check if path starts with common prefixes
                        if file_path.startswith("/home/runner/work/"):
                            # Extract after the repo name duplication
                            repo_parts = file_path.split("/")
                            if len(repo_parts) > 5:
                                file_path = "/".join(repo_parts[5:])

                # Create review comment on specific line
                pr.create_review_comment(
                    body=comment_body,
                    commit=latest_commit,
                    path=file_path,
                    line=finding.line_number,
                )
            except Exception as e:
                print(f"Failed to post inline comment on {file_path}:{finding.line_number}: {e}")

    def update_status_check(
        self, repo_name: str, pr: PullRequest, results: AggregatedResults
    ) -> None:
        """
        Update PR status check.

        Args:
            repo_name: Repository name (unused, kept for API compatibility)
            pr: Pull request object
            results: Aggregated results
        """
        # Get the latest commit
        commits = list(pr.get_commits())
        if not commits:
            return

        latest_commit = commits[-1]

        # Determine state
        if results.should_block:
            state = "failure"
            description = results.blocking_reason or "Code review found blocking issues"
        else:
            state = "success"
            description = f"Code review passed ({results.statistics['total']} findings)"

        # Create status
        try:
            latest_commit.create_status(
                state=state,
                description=description,
                context="AI Code Review",
                target_url=None,  # Could link to detailed report
            )
        except Exception as e:
            print(f"Failed to update status check: {e}")

    def _generate_summary(self, results: AggregatedResults) -> str:
        """Generate summary comment text."""
        lines = []
        lines.append("# 🤖 AI Code Review\n")

        # Status badge
        if results.should_block:
            lines.append("## ❌ Review Status: BLOCKED\n")
            if results.blocking_reason:
                lines.append(f"**Reason:** {results.blocking_reason}\n")
        else:
            lines.append("## ✅ Review Status: APPROVED\n")

        # Statistics
        lines.append("### 📊 Summary\n")
        stats = results.statistics
        lines.append(f"- **Total Findings:** {stats['total']}")
        lines.append(f"- **Execution Time:** {results.total_execution_time:.2f}s")
        lines.append(f"- **Files Changed:** {len(results.pr_context.changed_files)}")
        lines.append(f"- **Languages:** {', '.join(results.pr_context.detected_languages)}\n")

        # Severity breakdown
        if stats["by_severity"]:
            lines.append("### Findings by Severity\n")
            severity_emoji = {
                "critical": "🔴",
                "high": "🟠",
                "medium": "🟡",
                "low": "🔵",
                "info": "⚪",
            }

            for severity, count in stats["by_severity"].items():
                if count > 0:
                    emoji = severity_emoji.get(severity, "•")
                    lines.append(f"- {emoji} **{severity.upper()}:** {count}")

        # Category breakdown
        if stats["by_category"]:
            lines.append("\n### Findings by Category\n")
            for category, count in stats["by_category"].items():
                if count > 0:
                    cat_name = category.replace("_", " ").title()
                    lines.append(f"- **{cat_name}:** {count}")

        # Review aspects summary
        lines.append("\n### Review Aspects\n")
        for review in results.review_results:
            status_emoji = "✅" if review.success else "❌"
            lines.append(
                f"- {status_emoji} **{review.aspect_name}** "
                f"({len(review.findings)} findings, {review.execution_time:.2f}s)"
            )

        # Top findings
        if results.all_findings:
            lines.append("\n### 🔍 Key Findings\n")

            # Sort by severity and show top 10
            sorted_findings = sorted(
                results.all_findings,
                key=lambda f: (list(Severity).index(f.severity), f.category.value),
            )

            for finding in sorted_findings[:10]:
                severity_emoji = {
                    Severity.CRITICAL: "🔴",
                    Severity.HIGH: "🟠",
                    Severity.MEDIUM: "🟡",
                    Severity.LOW: "🔵",
                    Severity.INFO: "⚪",
                }.get(finding.severity, "•")

                lines.append(
                    f"\n#### {severity_emoji} {finding.category.value.replace('_', ' ').title()}"
                )

                # Build file location line
                file_location = f"**File:** `{finding.file_path}`"
                if finding.line_number:
                    file_location += f" (Line {finding.line_number})"
                lines.append(file_location)

                lines.append(f"\n{finding.message}")

                if finding.suggestion:
                    lines.append(f"\n💡 **Suggestion:** {finding.suggestion}")

            if len(sorted_findings) > 10:
                lines.append(f"\n... and {len(sorted_findings) - 10} more findings.")

        # Optional Improvements section for approved PRs
        if not results.should_block and results.all_findings:
            low_severity_findings = [
                f
                for f in results.all_findings
                if f.severity in [Severity.MEDIUM, Severity.LOW, Severity.INFO]
            ]

            if low_severity_findings:
                lines.append("\n### 💡 Optional Improvements\n")
                lines.append(
                    "Consider addressing these lower-priority items to further improve code quality:\n"
                )

                for finding in low_severity_findings[:5]:
                    lines.append(
                        f"- **{finding.category.value.replace('_', ' ').title()}**: {finding.message[:100]}"
                    )
                    if finding.aspect:
                        aspect_display = finding.aspect.replace("_", " ").title()
                        lines.append(f"  *(from {aspect_display})*")

        # Footer
        lines.append("\n---")
        lines.append("*Automated review powered by AI Code Review System*")

        return "\n".join(lines)

    def _format_inline_comment(self, finding: Finding) -> str:
        """Format an inline comment for a finding."""
        severity_emoji = {
            Severity.CRITICAL: "🔴 CRITICAL",
            Severity.HIGH: "🟠 HIGH",
            Severity.MEDIUM: "🟡 MEDIUM",
            Severity.LOW: "🔵 LOW",
            Severity.INFO: "⚪ INFO",
        }.get(finding.severity, finding.severity.value)

        lines = []
        lines.append(f"### {severity_emoji}: {finding.category.value.replace('_', ' ').title()}\n")
        lines.append(finding.message)

        if finding.suggestion:
            lines.append(f"\n💡 **Suggestion:**\n{finding.suggestion}")

        # Add detection source information
        detection_parts = []
        if finding.aspect:
            # Format aspect name nicely (e.g., "security_review" -> "Security Review")
            aspect_display = finding.aspect.replace("_", " ").title()
            detection_parts.append(f"Aspect: **{aspect_display}**")

        if finding.tool:
            detection_parts.append(f"Tool: {finding.tool}")
            if finding.rule_id:
                detection_parts.append(f"Rule: `{finding.rule_id}`")

        if detection_parts:
            lines.append(f"\n*{' | '.join(detection_parts)}*")

        return "\n".join(lines)

    def create_review_event(self, pr: PullRequest, results: AggregatedResults) -> None:
        """
        Create a GitHub review event (approve/request changes/comment).

        Args:
            pr: Pull request object
            results: Aggregated results
        """
        # Determine review event type
        if results.should_block:
            event = "REQUEST_CHANGES"
            body = f"Code review found blocking issues.\n\n{results.blocking_reason}"
        else:
            critical_or_high = sum(
                1 for f in results.all_findings if f.severity in [Severity.CRITICAL, Severity.HIGH]
            )

            if critical_or_high > 0:
                event = "COMMENT"
                body = f"Code review found {critical_or_high} issues that should be addressed."
            else:
                event = "APPROVE"
                body = "Code review looks good! No blocking issues found."

        # Create review
        try:
            pr.create_review(body=body, event=event)
        except Exception as e:
            print(f"Failed to create review event: {e}")
