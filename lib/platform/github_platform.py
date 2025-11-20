"""
GitHub platform implementation.

Implements the CodeReviewPlatform interface for GitHub using PyGithub.
"""

import os

from github import Github
from github.PullRequest import PullRequest

from ..models import (
    AggregatedResults,
    ChangeType,
    FileChange,
    Finding,
    PRContext,
    Severity,
)
from .base import CodeReviewPlatform, PlatformReporter


class GitHubPlatform(CodeReviewPlatform):
    """GitHub API implementation of CodeReviewPlatform."""

    # Language and dependency file detection (reused from pr_context.py)
    LANGUAGE_EXTENSIONS = {
        ".py": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".java": "java",
        ".kt": "kotlin",
        ".kts": "kotlin",
        ".go": "go",
        ".rs": "rust",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "csharp",
        ".cpp": "cpp",
        ".c": "c",
        ".h": "c",
        ".hpp": "cpp",
        ".sh": "shell",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".json": "json",
        ".md": "markdown",
        ".xml": "xml",
        ".gradle": "gradle",
        ".properties": "properties",
    }

    DEPENDENCY_FILES = {
        # Python
        "requirements.txt": "python",
        "requirements-dev.txt": "python",
        "requirements.in": "python",
        "pyproject.toml": "python",
        "poetry.lock": "python",
        "uv.lock": "python",
        "Pipfile": "python",
        "Pipfile.lock": "python",
        "setup.py": "python",
        "setup.cfg": "python",
        # JavaScript/TypeScript
        "package.json": "javascript",
        "package-lock.json": "javascript",
        "yarn.lock": "javascript",
        "pnpm-lock.yaml": "javascript",
        "bun.lockb": "javascript",
        # Java
        "pom.xml": "java",
        "build.gradle": "java",
        "build.gradle.kts": "java",
        "gradle.properties": "java",
        # Other
        "go.mod": "go",
        "go.sum": "go",
        "Cargo.toml": "rust",
        "Cargo.lock": "rust",
        "Gemfile": "ruby",
        "Gemfile.lock": "ruby",
        "composer.json": "php",
        "composer.lock": "php",
    }

    def __init__(self, github_token: str | None = None):
        """
        Initialize GitHub platform client.

        Args:
            github_token: GitHub API token (uses GITHUB_TOKEN env var if None)
        """
        token = github_token or os.getenv("GITHUB_TOKEN")
        if not token:
            raise ValueError("GitHub token is required (GITHUB_TOKEN environment variable)")

        self.github = Github(token)
        self._pr_cache = {}  # Cache PR objects to avoid repeated API calls

    def get_platform_name(self) -> str:
        """Get platform name."""
        return "GitHub"

    def get_context(self, project_identifier: str, pr_number: int) -> PRContext:
        """
        Fetch GitHub PR context.

        Args:
            project_identifier: Repository name (format: 'owner/repo')
            pr_number: Pull request number

        Returns:
            PRContext object with PR information
        """
        repo = self.github.get_repo(project_identifier)
        pr = repo.get_pull(pr_number)

        # Cache PR for later use
        cache_key = f"{project_identifier}#{pr_number}"
        self._pr_cache[cache_key] = pr

        # Build context
        metadata = {
            "title": pr.title,
            "description": pr.body or "",
            "author": pr.user.login,
            "base_branch": pr.base.ref,
            "head_branch": pr.head.ref,
            "labels": [label.name for label in pr.labels],
        }

        changed_files = self._get_changed_files(pr)
        diff = self._get_pr_diff(changed_files)
        detected_languages = self._detect_languages(changed_files)
        change_types = self._detect_change_types(changed_files, diff)

        return PRContext(
            pr_number=pr_number,
            title=metadata["title"],
            description=metadata["description"],
            author=metadata["author"],
            base_branch=metadata["base_branch"],
            head_branch=metadata["head_branch"],
            labels=metadata["labels"],
            changed_files=changed_files,
            diff=diff,
            detected_languages=detected_languages,
            change_types=change_types,
        )

    def post_summary_comment(self, project_identifier: str, pr_number: int, comment: str) -> None:
        """
        Post or update summary comment on GitHub PR.

        Args:
            project_identifier: Repository name ('owner/repo')
            pr_number: Pull request number
            comment: Comment text (markdown)
        """
        pr = self._get_pr(project_identifier, pr_number)

        # Check for existing comment (look for our marker)
        existing_comment = None
        for issue_comment in pr.get_issue_comments():
            if issue_comment.body.startswith("# 🤖 AI Code Review"):
                existing_comment = issue_comment
                break

        if existing_comment:
            # Update existing comment
            existing_comment.edit(comment)
        else:
            # Create new comment
            pr.create_issue_comment(comment)

    def post_inline_comments(
        self,
        project_identifier: str,
        pr_number: int,
        findings: list[Finding],
        comment_texts: list[str],
    ) -> None:
        """
        Post inline review comments on GitHub PR.

        Args:
            project_identifier: Repository name ('owner/repo')
            pr_number: Pull request number
            findings: List of findings with file/line information
            comment_texts: Corresponding comment texts
        """
        pr = self._get_pr(project_identifier, pr_number)

        # Get latest commit
        commits = list(pr.get_commits())
        if not commits:
            print("  ⚠️ No commits found, cannot post inline comments")
            return

        latest_commit = commits[-1]

        # Post review comments
        for finding, comment_body in zip(findings, comment_texts, strict=True):
            if not finding.line_number:
                continue

            try:
                # Normalize file path to relative path
                file_path = self._normalize_file_path(finding.file_path, project_identifier)

                # Create review comment
                pr.create_review_comment(
                    body=comment_body,
                    commit=latest_commit,
                    path=file_path,
                    line=finding.line_number,
                )
            except Exception as e:
                print(
                    f"  ⚠️ Failed to post comment on {finding.file_path}:{finding.line_number}: {e}"
                )

    def update_status(
        self,
        project_identifier: str,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "AI Code Review",
    ) -> None:
        """
        Update GitHub commit status.

        Args:
            project_identifier: Repository name ('owner/repo')
            commit_sha: Commit SHA
            state: Status state ('success', 'failure', 'pending')
            description: Status description
            context: Status check context name
        """
        repo = self.github.get_repo(project_identifier)
        commit = repo.get_commit(commit_sha)

        try:
            commit.create_status(
                state=state,
                description=description,
                context=context,
                target_url=None,  # Could link to detailed report
            )
        except Exception as e:
            raise Exception(f"Failed to update GitHub status: {e}") from e

    def _get_pr(self, project_identifier: str, pr_number: int) -> PullRequest:
        """Get PR object from cache or fetch it."""
        cache_key = f"{project_identifier}#{pr_number}"

        if cache_key in self._pr_cache:
            return self._pr_cache[cache_key]

        # Fetch and cache
        repo = self.github.get_repo(project_identifier)
        pr = repo.get_pull(pr_number)
        self._pr_cache[cache_key] = pr
        return pr

    def _get_changed_files(self, pr: PullRequest) -> list[FileChange]:
        """Extract changed files from PR."""
        changed_files = []

        for file in pr.get_files():
            change = FileChange(
                path=file.filename,
                status=file.status,
                additions=file.additions,
                deletions=file.deletions,
                changes=file.changes,
                patch=file.patch if hasattr(file, "patch") else None,
                old_path=file.previous_filename if file.status == "renamed" else None,
            )
            changed_files.append(change)

        return changed_files

    def _get_pr_diff(self, changed_files: list[FileChange]) -> str:
        """Build unified diff string from changed files."""
        diff_parts = []

        for file_change in changed_files:
            if file_change.patch:
                diff_parts.append(f"--- {file_change.path}")
                diff_parts.append(file_change.patch)
                diff_parts.append("")

        return "\n".join(diff_parts)

    def _detect_languages(self, changed_files: list[FileChange]) -> list[str]:
        """Detect programming languages from file extensions."""
        languages: set[str] = set()

        for file_change in changed_files:
            path = file_change.path.lower()
            for ext, lang in self.LANGUAGE_EXTENSIONS.items():
                if path.endswith(ext):
                    languages.add(lang)
                    break

        return sorted(languages)

    def _detect_change_types(self, changed_files: list[FileChange], diff: str) -> list[ChangeType]:
        """Detect types of changes in the PR."""

        change_types: set[ChangeType] = set()

        # Check for dependency changes
        if self._has_dependency_changes(changed_files):
            change_types.add(ChangeType.DEPENDENCY_CHANGE)

        # Check for test changes
        if self._has_test_changes(changed_files):
            change_types.add(ChangeType.TEST_CHANGE)

        # Check for documentation changes
        if self._has_documentation_changes(changed_files):
            change_types.add(ChangeType.DOCUMENTATION)

        # Analyze diff patterns
        if self._has_security_patterns(diff):
            change_types.add(ChangeType.SECURITY_RISK)

        if self._has_breaking_change_patterns(diff):
            change_types.add(ChangeType.BREAKING_CHANGE)

        # Default to feature
        if not change_types:
            change_types.add(ChangeType.FEATURE)

        return sorted(change_types, key=lambda x: x.value)

    def _has_dependency_changes(self, changed_files: list[FileChange]) -> bool:
        """Check if PR includes dependency file changes."""
        for file_change in changed_files:
            filename = os.path.basename(file_change.path)
            if filename in self.DEPENDENCY_FILES:
                return True
        return False

    def _has_test_changes(self, changed_files: list[FileChange]) -> bool:
        """Check if PR includes test file changes."""
        import re

        test_patterns = [
            r"test_.*\.py$",
            r".*_test\.py$",
            r".*\.test\.(js|ts|jsx|tsx)$",
            r".*\.spec\.(js|ts|jsx|tsx)$",
            r"tests?/",
            r"__tests__/",
        ]

        for file_change in changed_files:
            path = file_change.path.lower()
            for pattern in test_patterns:
                if re.search(pattern, path):
                    return True
        return False

    def _has_documentation_changes(self, changed_files: list[FileChange]) -> bool:
        """Check if PR includes documentation changes."""
        import re

        doc_patterns = [r"\.md$", r"\.rst$", r"docs?/", r"README", r"CHANGELOG"]

        for file_change in changed_files:
            path = file_change.path
            for pattern in doc_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return True
        return False

    def _has_security_patterns(self, diff: str) -> bool:
        """Check for security-sensitive patterns in diff."""
        import re

        security_patterns = [
            r"(password|secret|api[_-]?key|token|auth)",
            r"eval\s*\(",
            r"exec\s*\(",
            r"(subprocess|os\.system)",
            r"(innerHTML|dangerouslySetInnerHTML)",
            r"(md5|sha1)\s*\(",
        ]

        diff_lower = diff.lower()
        for pattern in security_patterns:
            if re.search(pattern, diff_lower):
                return True
        return False

    def _has_breaking_change_patterns(self, diff: str) -> bool:
        """Check for potential breaking changes in diff."""
        import re

        breaking_patterns = [
            r"^\-\s*(def|function|class|export)\s+\w+",
            r"BREAKING CHANGE",
            r"!:",
        ]

        for pattern in breaking_patterns:
            if re.search(pattern, diff, re.MULTILINE | re.IGNORECASE):
                return True
        return False

    def _normalize_file_path(self, file_path: str, project_identifier: str) -> str:
        """
        Normalize file path to relative path for GitHub API.

        GitHub API expects paths relative to repo root.
        Handles cases where absolute paths are provided.
        """
        if "/" not in file_path:
            return file_path

        # Remove absolute path prefixes if present
        # Handles: /home/runner/work/repo/repo/lib/file.py -> lib/file.py
        parts = file_path.split("/")

        # Look for duplicate repo name pattern (common in GitHub Actions)
        for i in range(len(parts) - 1):
            if i > 0 and parts[i] == parts[i - 1]:
                file_path = "/".join(parts[i + 1 :])
                break
        else:
            # If no duplicate found, check for common prefixes
            if file_path.startswith("/home/runner/work/"):
                repo_parts = file_path.split("/")
                if len(repo_parts) > 5:
                    file_path = "/".join(repo_parts[5:])

        return file_path


class GitHubReporter(PlatformReporter):
    """GitHub-specific reporter implementation."""

    def _generate_simple_summary(self, results: AggregatedResults) -> str:
        """Generate simple summary comment for GitHub."""
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
                file_location = f"**File:** `{finding.file_path}`"
                if finding.line_number:
                    file_location += f" (Line {finding.line_number})"
                lines.append(file_location)
                lines.append(f"\n{finding.message}")

                if finding.suggestion:
                    lines.append(f"\n💡 **Suggestion:** {finding.suggestion}")

            if len(sorted_findings) > 10:
                lines.append(f"\n... and {len(sorted_findings) - 10} more findings.")

        # Footer
        lines.append("\n---")
        lines.append("*Automated review powered by AI Code Review System*")

        return "\n".join(lines)

    def _format_inline_comment(self, finding: Finding) -> str:
        """Format inline comment for GitHub."""
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

        # Add detection source
        detection_parts = []
        if finding.aspect:
            aspect_display = finding.aspect.replace("_", " ").title()
            detection_parts.append(f"Aspect: **{aspect_display}**")
        if finding.tool:
            detection_parts.append(f"Tool: {finding.tool}")
            if finding.rule_id:
                detection_parts.append(f"Rule: `{finding.rule_id}`")

        if detection_parts:
            lines.append(f"\n*{' | '.join(detection_parts)}*")

        return "\n".join(lines)

    def _get_commit_sha_from_results(self, results: AggregatedResults) -> str | None:
        """Extract commit SHA from PR context (GitHub doesn't store it in PRContext)."""
        # For GitHub, we need to get the latest commit from the PR
        # This is a limitation - we'll need to fetch it from the platform
        # For now, return None and handle in the update method
        return None
