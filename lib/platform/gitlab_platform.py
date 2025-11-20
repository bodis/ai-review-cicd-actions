"""
GitLab platform implementation.

Implements the CodeReviewPlatform interface for GitLab using python-gitlab.
"""

import os

import gitlab

from ..models import (
    AggregatedResults,
    ChangeType,
    FileChange,
    Finding,
    PRContext,
)
from .base import CodeReviewPlatform, PlatformReporter


class GitLabPlatform(CodeReviewPlatform):
    """GitLab API implementation of CodeReviewPlatform."""

    def __init__(self, gitlab_token: str | None = None):
        """
        Initialize GitLab platform client.

        Args:
            gitlab_token: GitLab API token
                Uses in order: provided token, CI_JOB_TOKEN, GITLAB_TOKEN env var
        """
        token = gitlab_token or os.getenv("CI_JOB_TOKEN") or os.getenv("GITLAB_TOKEN")
        if not token:
            raise ValueError(
                "GitLab token is required (CI_JOB_TOKEN or GITLAB_TOKEN environment variable)"
            )

        # Get GitLab URL (supports self-hosted instances)
        gitlab_url = os.getenv("CI_SERVER_URL", "https://gitlab.com")

        self.gl = gitlab.Gitlab(gitlab_url, private_token=token)
        self._mr_cache = {}  # Cache MR objects

    def get_platform_name(self) -> str:
        """Get platform name."""
        return "GitLab"

    def get_context(self, project_identifier: str, mr_iid: int) -> PRContext:
        """
        Fetch GitLab MR context.

        Args:
            project_identifier: Project ID (numeric ID or 'namespace/project')
            mr_iid: Merge request IID (internal ID, not global ID)

        Returns:
            PRContext object with MR information
        """
        project = self.gl.projects.get(project_identifier)
        mr = project.mergerequests.get(mr_iid)

        # Cache MR for later use
        cache_key = f"{project_identifier}!{mr_iid}"
        self._mr_cache[cache_key] = (project, mr)

        # Build context
        metadata = {
            "title": mr.title,
            "description": mr.description or "",
            "author": mr.author["username"],
            "base_branch": mr.target_branch,
            "head_branch": mr.source_branch,
            "labels": mr.labels,
        }

        changed_files = self._get_changed_files(mr)
        diff = self._get_mr_diff(changed_files)
        detected_languages = self._detect_languages(changed_files)
        change_types = self._detect_change_types(changed_files, diff)

        return PRContext(
            pr_number=mr_iid,
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

    def post_summary_comment(self, project_identifier: str, mr_iid: int, comment: str) -> None:
        """
        Post or update summary note on GitLab MR.

        Args:
            project_identifier: Project ID (numeric or 'namespace/project')
            mr_iid: Merge request IID
            comment: Comment text (markdown)
        """
        project, mr = self._get_mr(project_identifier, mr_iid)

        # Check for existing note (look for our marker)
        notes = mr.notes.list(get_all=True)
        existing_note = None
        for note in notes:
            if note.body.startswith("# 🤖 AI Code Review"):
                existing_note = note
                break

        if existing_note:
            # Update existing note
            existing_note.body = comment
            existing_note.save()
        else:
            # Create new note
            mr.notes.create({"body": comment})

    def post_inline_comments(
        self,
        project_identifier: str,
        mr_iid: int,
        findings: list[Finding],
        comment_texts: list[str],
    ) -> None:
        """
        Post inline discussions on GitLab MR diff.

        Args:
            project_identifier: Project ID (numeric or 'namespace/project')
            mr_iid: Merge request IID
            findings: List of findings with file/line information
            comment_texts: Corresponding comment texts
        """
        project, mr = self._get_mr(project_identifier, mr_iid)

        # Get diff refs required for positioning
        try:
            diff_refs = mr.diff_refs
        except AttributeError:
            print("  ⚠️ Could not get diff_refs, MR may not have commits yet")
            return

        # Post discussions
        for finding, comment_body in zip(findings, comment_texts, strict=True):
            if not finding.line_number:
                continue

            try:
                # GitLab discussions require detailed position data
                discussion_data = {
                    "body": comment_body,
                    "position": {
                        "position_type": "text",
                        "new_path": finding.file_path,
                        "new_line": finding.line_number,
                        "base_sha": diff_refs["base_sha"],
                        "head_sha": diff_refs["head_sha"],
                        "start_sha": diff_refs["start_sha"],
                    },
                }

                mr.discussions.create(discussion_data)
            except Exception as e:
                print(
                    f"  ⚠️ Failed to post discussion on {finding.file_path}:{finding.line_number}: {e}"
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
        Update GitLab commit status.

        Args:
            project_identifier: Project ID (numeric or 'namespace/project')
            commit_sha: Commit SHA
            state: Status state ('success', 'failure', 'pending')
            description: Status description
            context: Status check name
        """
        project = self.gl.projects.get(project_identifier)
        commit = project.commits.get(commit_sha)

        # Map GitHub-style states to GitLab states
        state_map = {"success": "success", "failure": "failed", "pending": "running"}
        gitlab_state = state_map.get(state, "failed")

        try:
            commit.statuses.create(
                {
                    "state": gitlab_state,
                    "name": context,
                    "description": description[:255],  # GitLab has a 255 char limit
                }
            )
        except Exception as e:
            raise Exception(f"Failed to update GitLab status: {e}") from e

    def _get_mr(self, project_identifier: str, mr_iid: int):
        """Get MR object from cache or fetch it."""
        cache_key = f"{project_identifier}!{mr_iid}"

        if cache_key in self._mr_cache:
            return self._mr_cache[cache_key]

        # Fetch and cache
        project = self.gl.projects.get(project_identifier)
        mr = project.mergerequests.get(mr_iid)
        self._mr_cache[cache_key] = (project, mr)
        return project, mr

    def _get_changed_files(self, mr) -> list[FileChange]:
        """Extract changed files from MR."""
        changed_files = []

        try:
            changes_data = mr.changes()
            changes_list = changes_data.get("changes", [])
        except Exception as e:
            print(f"  ⚠️ Could not fetch MR changes: {e}")
            return changed_files

        for change in changes_list:
            # Determine status
            if change.get("new_file"):
                status = "added"
            elif change.get("deleted_file"):
                status = "removed"
            elif change.get("renamed_file"):
                status = "renamed"
            else:
                status = "modified"

            # Calculate additions/deletions from diff
            diff_text = change.get("diff", "")
            additions = diff_text.count("\n+") if diff_text else 0
            deletions = diff_text.count("\n-") if diff_text else 0

            file_change = FileChange(
                path=change.get("new_path", change.get("old_path", "")),
                status=status,
                additions=additions,
                deletions=deletions,
                changes=additions + deletions,
                patch=diff_text if diff_text else None,
                old_path=change.get("old_path") if change.get("renamed_file") else None,
            )
            changed_files.append(file_change)

        return changed_files

    def _get_mr_diff(self, changed_files: list[FileChange]) -> str:
        """Build unified diff string from changed files."""
        diff_parts = []

        for file_change in changed_files:
            if file_change.patch:
                diff_parts.append(f"--- {file_change.path}")
                diff_parts.append(file_change.patch)
                diff_parts.append("")

        return "\n".join(diff_parts)

    def _detect_languages(self, changed_files: list[FileChange]) -> list[str]:
        """Detect programming languages (reuse GitHub's logic)."""
        from .github_platform import GitHubPlatform

        languages: set[str] = set()
        for file_change in changed_files:
            path = file_change.path.lower()
            for ext, lang in GitHubPlatform.LANGUAGE_EXTENSIONS.items():
                if path.endswith(ext):
                    languages.add(lang)
                    break

        return sorted(languages)

    def _detect_change_types(self, changed_files: list[FileChange], diff: str) -> list[ChangeType]:
        """Detect types of changes (reuse GitHub's logic)."""

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
        """Check for dependency file changes."""
        from .github_platform import GitHubPlatform

        for file_change in changed_files:
            filename = os.path.basename(file_change.path)
            if filename in GitHubPlatform.DEPENDENCY_FILES:
                return True
        return False

    def _has_test_changes(self, changed_files: list[FileChange]) -> bool:
        """Check for test file changes."""
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
        """Check for documentation changes."""
        import re

        doc_patterns = [r"\.md$", r"\.rst$", r"docs?/", r"README", r"CHANGELOG"]

        for file_change in changed_files:
            path = file_change.path
            for pattern in doc_patterns:
                if re.search(pattern, path, re.IGNORECASE):
                    return True
        return False

    def _has_security_patterns(self, diff: str) -> bool:
        """Check for security-sensitive patterns."""
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
        """Check for breaking change patterns."""
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


class GitLabReporter(PlatformReporter):
    """GitLab-specific reporter implementation."""

    def _generate_simple_summary(self, results: AggregatedResults) -> str:
        """
        Generate simple summary comment for GitLab.

        Uses same format as GitHub for consistency.
        """
        # Reuse GitHub's formatting (it works well for GitLab too)
        from .github_platform import GitHubReporter

        github_reporter = GitHubReporter.__new__(GitHubReporter)
        return github_reporter._generate_simple_summary(results)

    def _format_inline_comment(self, finding: Finding) -> str:
        """
        Format inline comment for GitLab.

        Uses same format as GitHub for consistency.
        """
        # Reuse GitHub's formatting
        from .github_platform import GitHubReporter

        github_reporter = GitHubReporter.__new__(GitHubReporter)
        return github_reporter._format_inline_comment(finding)

    def _get_commit_sha_from_results(self, results: AggregatedResults) -> str | None:
        """
        Extract commit SHA from GitLab MR.

        For GitLab, we can get the SHA from the cached MR object.
        """
        # Get platform instance from results (if available)
        # This is a limitation - we need access to the platform/MR
        # For now, return None and handle in update_status_check
        return None

    def _update_status_check(self, project_identifier: str, results: AggregatedResults) -> None:
        """
        Override status check update to get SHA from cached MR.

        GitLab-specific implementation that accesses cached MR data.
        """
        # Get the GitLab platform instance
        platform = self.platform
        if not isinstance(platform, GitLabPlatform):
            print("  ⚠️ Platform is not GitLabPlatform, skipping status update")
            return

        # Get MR from cache to extract SHA
        cache_key = f"{project_identifier}!{results.pr_context.pr_number}"
        if cache_key not in platform._mr_cache:
            print("  ⚠️ MR not in cache, cannot update status")
            return

        _, mr = platform._mr_cache[cache_key]

        try:
            commit_sha = mr.sha
        except AttributeError:
            print("  ⚠️ Could not get commit SHA from MR")
            return

        # Determine status
        if results.should_block:
            state = "failure"
            description = results.blocking_reason or "Code review found blocking issues"
        else:
            state = "success"
            description = f"Code review passed ({results.statistics['total']} findings)"

        # Update platform status
        try:
            platform.update_status(project_identifier, commit_sha, state, description)
            print(f"  ✓ Status updated: {state}")
        except Exception as e:
            print(f"  ⚠️ Failed to update status: {e}")
