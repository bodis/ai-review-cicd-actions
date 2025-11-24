"""
AI-powered cross-run comment deduplication.

Compares new findings against existing PR/MR comments to avoid duplicates.
Uses a lightweight LLM model to semantically compare comments.
"""

import json
import os
from dataclasses import dataclass
from enum import Enum

import anthropic

from .models import ExistingComment, Finding, Metrics


class CommentAction(str, Enum):
    """Action to take for a new finding based on existing comments."""

    NEW = "new"  # Post as new comment
    UPDATE = "update"  # Update existing comment with new insights
    SKIP = "skip"  # Skip - duplicate with no new info


@dataclass
class DeduplicationResult:
    """Result of comparing a finding against existing comments."""

    action: CommentAction
    finding: Finding
    comment_text: str  # The comment text to post/update with
    existing_comment_id: str | None = None  # If updating, which comment
    existing_comment_body: str | None = None  # Original body for merge


class CommentDeduplicator:
    """AI-powered cross-run comment deduplication."""

    SYSTEM_PROMPT = """You are an expert at comparing code review comments to identify duplicates.

Your task is to compare NEW code review findings against EXISTING comments already posted on a PR.

Key principles:
1. SAME ISSUE = Comments about the same code problem, even if worded differently
2. PROXIMITY MATTERS = Comments on nearby lines (within threshold) about similar issues are likely duplicates
3. NEW INSIGHTS = If a new finding has additional useful information not in the existing comment, it should be merged
4. DIFFERENT ISSUES = If the comments are about genuinely different problems, they are not duplicates

Be conservative: when in doubt, treat as NEW to avoid missing important issues."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5",
        proximity_threshold: int = 10,
        metrics: Metrics | None = None,
    ):
        """
        Initialize comment deduplicator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use (default: Haiku 4.5 - fast and cheap)
            proximity_threshold: Max line distance to consider for deduplication
            metrics: Optional metrics tracking object
        """
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for comment deduplication")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.proximity_threshold = proximity_threshold
        self.metrics = metrics

    def deduplicate_comments(
        self,
        findings: list[Finding],
        comment_texts: list[str],
        existing_comments: list[ExistingComment],
    ) -> list[DeduplicationResult]:
        """
        Compare new findings against existing comments to determine actions.

        Args:
            findings: New findings to potentially post
            comment_texts: Generated comment texts for each finding
            existing_comments: Existing comments already on the PR

        Returns:
            List of DeduplicationResult with action for each finding
        """
        if not existing_comments:
            # No existing comments - all findings are new
            return [
                DeduplicationResult(
                    action=CommentAction.NEW,
                    finding=finding,
                    comment_text=self._add_marker(comment_text, finding),
                )
                for finding, comment_text in zip(findings, comment_texts, strict=True)
            ]

        results = []

        for finding, comment_text in zip(findings, comment_texts, strict=True):
            # Find nearby existing comments (same file, within proximity threshold)
            nearby_comments = self._find_nearby_comments(finding, existing_comments)

            if not nearby_comments:
                # No nearby comments - this is a new finding
                results.append(
                    DeduplicationResult(
                        action=CommentAction.NEW,
                        finding=finding,
                        comment_text=self._add_marker(comment_text, finding),
                    )
                )
            else:
                # Use AI to compare with nearby comments
                result = self._compare_with_ai(finding, comment_text, nearby_comments)
                results.append(result)

        return results

    def get_comments_to_delete(
        self,
        existing_comments: list[ExistingComment],
        matched_comment_ids: set[str],
    ) -> list[ExistingComment]:
        """
        Identify existing comments that should be deleted (issue resolved).

        Args:
            existing_comments: All existing AI review comments
            matched_comment_ids: IDs of comments that matched new findings

        Returns:
            List of comments to delete (no longer relevant)
        """
        return [
            comment
            for comment in existing_comments
            if comment.comment_id not in matched_comment_ids
        ]

    def _find_nearby_comments(
        self, finding: Finding, existing_comments: list[ExistingComment]
    ) -> list[ExistingComment]:
        """Find existing comments near the finding's location."""
        nearby = []

        for comment in existing_comments:
            # Must be same file
            if comment.file_path != finding.file_path:
                continue

            # Check line proximity
            if comment.line_number is None or finding.line_number is None:
                continue

            line_distance = abs(comment.line_number - finding.line_number)
            if line_distance <= self.proximity_threshold:
                nearby.append(comment)

        return nearby

    def _compare_with_ai(
        self,
        finding: Finding,
        comment_text: str,
        nearby_comments: list[ExistingComment],
    ) -> DeduplicationResult:
        """Use AI to compare finding against nearby existing comments."""
        # Build comparison prompt
        existing_json = [
            {
                "id": comment.comment_id,
                "line": comment.line_number,
                "body": comment.body[:500],  # Truncate for efficiency
            }
            for comment in nearby_comments
        ]

        new_finding_json = {
            "line": finding.line_number,
            "severity": finding.severity.value,
            "category": finding.category.value,
            "message": finding.message,
            "proposed_comment": comment_text[:500],
        }

        prompt = f"""Compare this NEW finding against EXISTING comments on the same file.

**NEW FINDING**:
```json
{json.dumps(new_finding_json, indent=2)}
```

**EXISTING COMMENTS** (within {self.proximity_threshold} lines):
```json
{json.dumps(existing_json, indent=2)}
```

**Determine**:
1. Is this NEW finding about the SAME issue as any EXISTING comment?
2. If same issue: does the NEW finding have ADDITIONAL insights not in the existing comment?

**Output format** (JSON only, no explanation):
```json
{{
  "is_duplicate": true/false,
  "matching_comment_id": "id or null",
  "has_new_insights": true/false,
  "merged_comment": "merged text if has_new_insights, else null"
}}
```

Be conservative: if unsure, set is_duplicate=false to ensure important issues aren't missed.
When merging, combine the best parts of both comments into a cohesive, non-redundant message."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.0,  # Deterministic for consistency
                system=self.SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )

            # Extract text from response
            first_block = response.content[0]
            response_text = first_block.text if hasattr(first_block, "text") else str(first_block)

            # Parse JSON response
            response_text = response_text.strip()
            if response_text.startswith("```json"):
                response_text = response_text[7:]
            elif response_text.startswith("```"):
                response_text = response_text[3:]
            if response_text.endswith("```"):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())

            # Track usage
            if self.metrics:
                usage = response.usage
                self.metrics.add_tokens(
                    getattr(usage, "input_tokens", 0),
                    getattr(usage, "output_tokens", 0),
                    getattr(usage, "cache_read_input_tokens", 0),
                )

            is_duplicate = result.get("is_duplicate", False)
            matching_id = result.get("matching_comment_id")
            has_new_insights = result.get("has_new_insights", False)
            merged_comment = result.get("merged_comment")

            if not is_duplicate:
                # Not a duplicate - post as new
                return DeduplicationResult(
                    action=CommentAction.NEW,
                    finding=finding,
                    comment_text=self._add_marker(comment_text, finding),
                )
            elif has_new_insights and merged_comment:
                # Duplicate but with new insights - update existing comment
                # Find the matching comment's body
                matching_comment = next(
                    (c for c in nearby_comments if c.comment_id == matching_id), None
                )
                return DeduplicationResult(
                    action=CommentAction.UPDATE,
                    finding=finding,
                    comment_text=self._add_marker(merged_comment, finding),
                    existing_comment_id=matching_id,
                    existing_comment_body=matching_comment.body if matching_comment else None,
                )
            else:
                # Pure duplicate - skip
                return DeduplicationResult(
                    action=CommentAction.SKIP,
                    finding=finding,
                    comment_text=comment_text,
                    existing_comment_id=matching_id,
                )

        except Exception as e:
            print(f"  ⚠️ AI comparison failed ({type(e).__name__}): {str(e)[:100]}")
            print("     Treating as NEW comment to be safe")
            # Fail-safe: treat as new to avoid missing issues
            return DeduplicationResult(
                action=CommentAction.NEW,
                finding=finding,
                comment_text=self._add_marker(comment_text, finding),
            )

    def _add_marker(self, comment_text: str, finding: Finding) -> str:
        """Add AI-REVIEW marker to comment for future identification."""
        marker = ExistingComment.create_marker(finding)
        return f"{comment_text}\n\n{marker}"
