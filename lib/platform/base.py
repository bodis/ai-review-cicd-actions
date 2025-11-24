"""
Abstract base classes for platform integrations.

Defines the contract that all platform implementations (GitHub, GitLab) must follow.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from ..models import AggregatedResults, ExistingComment, Finding, PRContext


@dataclass
class CommentDeduplicationConfig:
    """Configuration for cross-run comment deduplication."""

    enabled: bool = True
    model: str = "claude-haiku-4-5"  # Fast, cheap model for comparison
    proximity_threshold: int = 10  # Lines range for considering duplicates
    cleanup_resolved: bool = True  # Delete comments for resolved issues


@dataclass
class PlatformConfig:
    """Platform-specific configuration."""

    # Common settings
    post_summary_comment: bool = True
    post_inline_comments: bool = True
    inline_comment_severity_threshold: str = "high"
    update_status_check: bool = True

    # Comment deduplication settings
    comment_deduplication: CommentDeduplicationConfig | None = None

    # Platform-specific extras
    extras: dict[str, Any] | None = None


class CodeReviewPlatform(ABC):
    """
    Abstract interface for code review platforms.

    This defines the contract that all platform implementations must follow.
    Each platform (GitHub, GitLab, etc.) provides its own implementation of
    these methods using their specific APIs.
    """

    @abstractmethod
    def get_context(self, project_identifier: str, mr_number: int) -> PRContext:
        """
        Fetch merge/pull request context.

        Args:
            project_identifier: Platform-specific project ID
                GitHub: 'owner/repo'
                GitLab: project_id (int) or 'namespace/project'
            mr_number: Merge/Pull request number

        Returns:
            PRContext object with all MR/PR information
        """
        pass

    @abstractmethod
    def post_summary_comment(self, project_identifier: str, mr_number: int, comment: str) -> None:
        """
        Post or update summary comment on MR/PR.

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number
            comment: Comment text (markdown formatted)
        """
        pass

    @abstractmethod
    def post_inline_comments(
        self,
        project_identifier: str,
        mr_number: int,
        findings: list[Finding],
        comment_texts: list[str],
    ) -> None:
        """
        Post inline comments on specific code lines.

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number
            findings: List of findings with file/line information
            comment_texts: Corresponding comment texts (same order as findings)
        """
        pass

    @abstractmethod
    def get_existing_inline_comments(
        self,
        project_identifier: str,
        mr_number: int,
    ) -> list[ExistingComment]:
        """
        Get existing inline comments posted by AI review on the PR/MR.

        Used for cross-run deduplication to avoid posting duplicate comments.
        Only returns comments that have the AI-REVIEW marker or match known patterns.

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number

        Returns:
            List of existing AI review comments
        """
        pass

    @abstractmethod
    def update_inline_comment(
        self,
        project_identifier: str,
        mr_number: int,
        comment_id: str,
        new_body: str,
    ) -> bool:
        """
        Update an existing inline comment.

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number
            comment_id: Platform-specific comment ID
            new_body: New comment content

        Returns:
            True if update succeeded, False otherwise
        """
        pass

    @abstractmethod
    def delete_inline_comment(
        self,
        project_identifier: str,
        mr_number: int,
        comment_id: str,
    ) -> bool:
        """
        Delete an inline comment (for resolved issues).

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number
            comment_id: Platform-specific comment ID

        Returns:
            True if deletion succeeded, False otherwise
        """
        pass

    @abstractmethod
    def update_status(
        self,
        project_identifier: str,
        commit_sha: str,
        state: str,
        description: str,
        context: str = "AI Code Review",
    ) -> None:
        """
        Update commit/pipeline status.

        Args:
            project_identifier: Platform-specific project ID
            commit_sha: Commit SHA to update
            state: Status state ('success', 'failure', 'pending')
            description: Status description text
            context: Status check context/name
        """
        pass

    @abstractmethod
    def get_platform_name(self) -> str:
        """
        Get platform name for logging/display.

        Returns:
            Platform name (e.g., 'GitHub', 'GitLab')
        """
        pass


class PlatformReporter(ABC):
    """
    Abstract interface for posting review results to platforms.

    This separates the reporting logic from the core platform API operations,
    allowing for different reporting strategies while maintaining the same API contract.
    """

    def __init__(
        self,
        platform: CodeReviewPlatform,
        anthropic_api_key: str | None = None,
        metrics: Any | None = None,
        anthropic_model: str | None = None,
    ):
        """
        Initialize platform reporter.

        Args:
            platform: Platform implementation (GitHub/GitLab)
            anthropic_api_key: Anthropic API key for AI comment generation
            metrics: Metrics object for tracking usage
            anthropic_model: Claude model to use
        """
        self.platform = platform
        self.metrics = metrics
        self.anthropic_model = anthropic_model

        # Initialize comment generator (shared across platforms)
        self.comment_generator = self._init_comment_generator(anthropic_api_key)

    def _init_comment_generator(self, api_key: str | None):
        """Initialize AI comment generator if API key is available."""
        if not api_key:
            return None

        try:
            from ..comment_generator import CommentGenerator

            return CommentGenerator(api_key, metrics=self.metrics, model=self.anthropic_model)
        except Exception as e:
            print(f"⚠️ Warning: Could not initialize CommentGenerator: {e}")
            print("   Falling back to simple comment formatting")
            return None

    def post_review_results(
        self,
        project_identifier: str,
        mr_number: int,
        results: AggregatedResults,
        config: PlatformConfig,
    ) -> None:
        """
        Post complete review results to platform.

        Args:
            project_identifier: Platform-specific project ID
            mr_number: Merge/Pull request number
            results: Aggregated review results
            config: Platform configuration
        """
        print(f"\nPosting results to {self.platform.get_platform_name()}...")

        # Post summary comment
        if config.post_summary_comment:
            summary = self._generate_summary(results)
            self.platform.post_summary_comment(project_identifier, mr_number, summary)
            print("  ✓ Summary comment posted")

        # Post inline comments
        if config.post_inline_comments:
            self._post_inline_comments_with_threshold(
                project_identifier, mr_number, results, config
            )

        # Update status check
        if config.update_status_check:
            self._update_status_check(project_identifier, results)

    def _generate_summary(self, results: AggregatedResults) -> str:
        """Generate summary comment using AI or fallback."""
        if self.comment_generator:
            try:
                print("  Generating AI summary comment...")
                return self.comment_generator.generate_summary_comment(results)
            except Exception as e:
                print(f"  ⚠️ AI summary generation failed: {e}, using simple template")

        return self._generate_simple_summary(results)

    def _post_inline_comments_with_threshold(
        self,
        project_identifier: str,
        mr_number: int,
        results: AggregatedResults,
        config: PlatformConfig,
    ) -> None:
        """Post inline comments filtered by severity threshold with deduplication."""
        from ..models import Severity

        severity_threshold = config.inline_comment_severity_threshold

        # Map severity threshold
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

        # Filter findings
        inline_findings = [
            f
            for f in results.all_findings
            if f.severity in allowed_severities and f.line_number is not None
        ]

        if not inline_findings:
            print("  No inline comments to post")
            return

        print(f"  Generating {len(inline_findings)} inline comments...")

        # Generate comment texts
        if self.comment_generator:
            try:
                comment_texts = self.comment_generator.generate_batch_comments(inline_findings)
            except Exception as e:
                print(f"  ⚠️ AI comment generation failed: {e}, using simple formatting")
                comment_texts = [self._format_inline_comment(f) for f in inline_findings]
        else:
            comment_texts = [self._format_inline_comment(f) for f in inline_findings]

        # Check if deduplication is enabled
        dedup_config = config.comment_deduplication
        if dedup_config and dedup_config.enabled:
            self._post_with_deduplication(
                project_identifier, mr_number, inline_findings, comment_texts, dedup_config
            )
        else:
            # Post directly without deduplication (legacy behavior)
            self.platform.post_inline_comments(
                project_identifier, mr_number, inline_findings, comment_texts
            )
            print(f"  ✓ Posted {len(inline_findings)} inline comments")

    def _post_with_deduplication(
        self,
        project_identifier: str,
        mr_number: int,
        findings: list[Finding],
        comment_texts: list[str],
        dedup_config: CommentDeduplicationConfig,
    ) -> None:
        """Post inline comments with cross-run deduplication."""
        from ..comment_deduplication import CommentAction, CommentDeduplicator

        print("  Fetching existing comments for deduplication...")

        # Get existing AI review comments from the PR
        existing_comments = self.platform.get_existing_inline_comments(
            project_identifier, mr_number
        )
        print(f"  Found {len(existing_comments)} existing AI review comments")

        if not existing_comments:
            # No existing comments - post all as new (with markers)
            from ..models import ExistingComment as EC

            marked_texts = [
                f"{text}\n\n{EC.create_marker(finding)}"
                for text, finding in zip(comment_texts, findings, strict=True)
            ]
            self.platform.post_inline_comments(
                project_identifier, mr_number, findings, marked_texts
            )
            print(f"  ✓ Posted {len(findings)} new inline comments")
            return

        # Initialize deduplicator
        try:
            deduplicator = CommentDeduplicator(
                model=dedup_config.model,
                proximity_threshold=dedup_config.proximity_threshold,
                metrics=self.metrics,
            )
        except Exception as e:
            print(f"  ⚠️ Could not initialize deduplicator: {e}")
            print("     Falling back to direct posting")
            self.platform.post_inline_comments(
                project_identifier, mr_number, findings, comment_texts
            )
            return

        # Compare new findings against existing comments
        print("  Comparing findings against existing comments...")
        dedup_results = deduplicator.deduplicate_comments(
            findings, comment_texts, existing_comments
        )

        # Process results
        new_count = 0
        update_count = 0
        skip_count = 0
        matched_comment_ids: set[str] = set()

        new_findings = []
        new_texts = []

        for result in dedup_results:
            if result.action == CommentAction.NEW:
                new_findings.append(result.finding)
                new_texts.append(result.comment_text)
                new_count += 1
            elif result.action == CommentAction.UPDATE:
                # Update existing comment with merged content
                if result.existing_comment_id:
                    success = self.platform.update_inline_comment(
                        project_identifier,
                        mr_number,
                        result.existing_comment_id,
                        result.comment_text,
                    )
                    if success:
                        update_count += 1
                        matched_comment_ids.add(result.existing_comment_id)
                    else:
                        # Failed to update - post as new instead
                        new_findings.append(result.finding)
                        new_texts.append(result.comment_text)
                        new_count += 1
            elif result.action == CommentAction.SKIP:
                skip_count += 1
                if result.existing_comment_id:
                    matched_comment_ids.add(result.existing_comment_id)

        # Post new comments
        if new_findings:
            self.platform.post_inline_comments(
                project_identifier, mr_number, new_findings, new_texts
            )

        # Clean up resolved comments (if enabled)
        deleted_count = 0
        if dedup_config.cleanup_resolved:
            comments_to_delete = deduplicator.get_comments_to_delete(
                existing_comments, matched_comment_ids
            )
            for comment in comments_to_delete:
                success = self.platform.delete_inline_comment(
                    project_identifier, mr_number, comment.comment_id
                )
                if success:
                    deleted_count += 1

        # Report summary
        print("  ✓ Comment deduplication complete:")
        print(f"    - New: {new_count}")
        print(f"    - Updated: {update_count}")
        print(f"    - Skipped (duplicates): {skip_count}")
        if deleted_count > 0:
            print(f"    - Deleted (resolved): {deleted_count}")

    def _update_status_check(self, project_identifier: str, results: AggregatedResults) -> None:
        """Update commit status based on results."""
        # Get commit SHA from PR context
        commit_sha = self._get_commit_sha_from_results(results)

        if not commit_sha:
            print("  ⚠️ Could not determine commit SHA, skipping status update")
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
            self.platform.update_status(project_identifier, commit_sha, state, description)
            print(f"  ✓ Status updated: {state}")
        except Exception as e:
            print(f"  ⚠️ Failed to update status: {e}")

    @abstractmethod
    def _generate_simple_summary(self, results: AggregatedResults) -> str:
        """Generate simple text summary (platform-specific formatting)."""
        pass

    @abstractmethod
    def _format_inline_comment(self, finding: Finding) -> str:
        """Format inline comment text (platform-specific formatting)."""
        pass

    @abstractmethod
    def _get_commit_sha_from_results(self, results: AggregatedResults) -> str | None:
        """Extract commit SHA from results (platform-specific)."""
        pass
