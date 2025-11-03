"""
AI-powered semantic deduplication using Claude Haiku.

Uses a fast, cheap model to intelligently detect duplicate findings
that describe the same issue with different wording.
"""
import json
import os

import anthropic

from .models import Finding, Metrics, Severity


class AIDeduplicator:
    """AI-powered finding deduplication using Claude."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "claude-haiku-4-5",
        metrics: Metrics | None = None
    ):
        """
        Initialize AI deduplicator.

        Args:
            api_key: Anthropic API key (uses ANTHROPIC_API_KEY env var if not provided)
            model: Claude model to use (default: Haiku 3.5 - fast and cheap)
            metrics: Optional metrics tracking object
        """
        self.api_key = api_key or os.getenv('ANTHROPIC_API_KEY')
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for AI deduplication")

        self.client = anthropic.Anthropic(api_key=self.api_key)
        self.model = model
        self.metrics = metrics

    def deduplicate_group(
        self,
        findings: list[Finding],
        proximity_threshold: int = 10
    ) -> list[Finding]:
        """
        Use AI to identify and merge duplicate findings within a group.

        Args:
            findings: List of findings from same file + category
            proximity_threshold: Max line distance to consider for deduplication

        Returns:
            Deduplicated list of findings
        """
        if len(findings) <= 1:
            return findings

        # Sort by line number
        sorted_findings = sorted(
            findings,
            key=lambda f: f.line_number if f.line_number is not None else 0
        )

        # Build prompt for AI to identify duplicates
        findings_json = []
        for i, finding in enumerate(sorted_findings):
            findings_json.append({
                "id": i,
                "line": finding.line_number,
                "severity": finding.severity.value,
                "message": finding.message,
                "tool": finding.tool,
                "aspect": finding.aspect
            })

        prompt = f"""You are analyzing code review findings to identify duplicates.

**Task**: Group findings that describe the SAME underlying issue, even if worded differently.

**Rules**:
1. Findings are duplicates if they describe the same code problem at nearby locations (within {proximity_threshold} lines)
2. Different wording, emojis, or phrasing doesn't make them different issues
3. Same issue in DIFFERENT locations (far apart lines) = NOT duplicates
4. Different severity levels can still be duplicates if describing same issue

**Findings to analyze**:
```json
{json.dumps(findings_json, indent=2)}
```

**Output format** (JSON only, no explanation):
```json
{{
  "duplicate_groups": [
    [0, 1, 2],  // IDs of findings that are duplicates
    [5]         // Finding that is unique
  ]
}}
```

Only group findings that are clearly about the same issue. When in doubt, keep them separate.
"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=1000,
                temperature=0.0,  # Deterministic for consistency
                messages=[{"role": "user", "content": prompt}]
            )

            # Extract text from response
            first_block = response.content[0]
            response_text = first_block.text if hasattr(first_block, 'text') else str(first_block)

            # Parse JSON response
            # Remove markdown code fences if present
            response_text = response_text.strip()
            if response_text.startswith('```json'):
                response_text = response_text[7:]
            elif response_text.startswith('```'):
                response_text = response_text[3:]
            if response_text.endswith('```'):
                response_text = response_text[:-3]

            result = json.loads(response_text.strip())
            duplicate_groups = result.get('duplicate_groups', [])

            # Track usage
            if self.metrics:
                usage = response.usage
                self.metrics.add_tokens(
                    getattr(usage, 'input_tokens', 0),
                    getattr(usage, 'output_tokens', 0),
                    getattr(usage, 'cache_read_input_tokens', 0)
                )

            # Merge duplicate groups
            merged_findings = []
            processed_indices = set()

            for group in duplicate_groups:
                # Validate indices and filter out-of-bounds
                valid_indices = [idx for idx in group if 0 <= idx < len(sorted_findings)]

                if len(valid_indices) < len(group):
                    invalid_count = len(group) - len(valid_indices)
                    print(f"⚠️ AI returned {invalid_count} invalid finding index/indices, ignoring")

                if not valid_indices:
                    continue

                if len(valid_indices) == 1:
                    # Single finding, no merge needed
                    merged_findings.append(sorted_findings[valid_indices[0]])
                    processed_indices.add(valid_indices[0])
                else:
                    # Merge group
                    group_findings = [sorted_findings[idx] for idx in valid_indices]
                    merged = self._merge_findings(group_findings)
                    merged_findings.append(merged)
                    processed_indices.update(valid_indices)

            # Add any findings that weren't grouped (shouldn't happen, but safety net)
            for i, finding in enumerate(sorted_findings):
                if i not in processed_indices:
                    merged_findings.append(finding)

            return merged_findings

        except Exception as e:
            print(f"⚠️ AI deduplication failed ({type(e).__name__}): {str(e)[:100]}")
            print(f"   Falling back to original {len(findings)} findings (no deduplication)")
            return findings

    def _merge_findings(self, findings: list[Finding]) -> Finding:
        """
        Merge multiple findings into one comprehensive finding.

        Args:
            findings: List of findings to merge

        Returns:
            Merged finding
        """
        # Sort by severity (most severe first)
        severity_order = [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]
        sorted_findings = sorted(findings, key=lambda f: severity_order.index(f.severity))

        # Use the most severe finding as base
        base = sorted_findings[0]

        # Collect metadata from all findings
        tools = set()
        rule_ids = set()
        aspects = set()
        suggestions = []

        for finding in findings:
            if finding.tool:
                tools.add(finding.tool)
            if finding.rule_id:
                rule_ids.add(finding.rule_id)
            if finding.aspect:
                aspects.add(finding.aspect)
            if finding.suggestion and finding.suggestion not in suggestions:
                suggestions.append(finding.suggestion)

        # Use earliest line number
        line_numbers = [f.line_number for f in findings if f.line_number is not None]
        earliest_line = min(line_numbers) if line_numbers else base.line_number

        # Combine metadata
        combined_tool = ", ".join(sorted(tools)) if tools else base.tool
        combined_rule_id = ", ".join(sorted(rule_ids)) if rule_ids else base.rule_id
        combined_aspect = ", ".join(sorted(aspects)) if aspects else base.aspect
        combined_suggestion = suggestions[0] if suggestions else base.suggestion

        return Finding(
            file_path=base.file_path,
            line_number=earliest_line,
            severity=base.severity,  # Highest severity
            category=base.category,
            message=base.message,  # Most severe finding's message
            suggestion=combined_suggestion,
            tool=combined_tool,
            rule_id=combined_rule_id,
            code_snippet=base.code_snippet,
            aspect=combined_aspect
        )
