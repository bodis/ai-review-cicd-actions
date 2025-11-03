"""
Orchestrator - Coordinates execution of all review aspects.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from .analyzers.java_analyzer import JavaAnalyzer
from .analyzers.javascript_analyzer import JavaScriptAnalyzer
from .analyzers.python_analyzer import PythonAnalyzer
from .models import (
    AggregatedResults,
    Finding,
    Metrics,
    PRContext,
    ReviewResult,
    Severity,
)
from .pr_context import PRContextBuilder


class ReviewOrchestrator:
    """Orchestrates the entire code review pipeline."""

    def __init__(self, config: dict[str, Any], project_root: str = "."):
        """
        Initialize orchestrator.

        Args:
            config: Configuration dictionary
            project_root: Root directory of the project
        """
        self.config = config
        self.project_root = project_root
        self.review_results: list[ReviewResult] = []
        self.metrics = Metrics()  # Initialize metrics tracking
        self._ai_deduplicator = None  # Lazy-loaded AIDeduplicator (reused across calls)

    def run_review_pipeline(
        self,
        repo_name: str,
        pr_number: int,
        github_token: str | None = None
    ) -> AggregatedResults:
        """
        Main entry point for running the complete review pipeline with error recovery.

        Args:
            repo_name: Repository name (owner/repo)
            pr_number: Pull request number
            github_token: GitHub API token

        Returns:
            AggregatedResults with all findings
        """
        start_time = time.time()
        errors = []
        warnings = []

        # Step 1: Build PR context with error recovery
        print(f"Building context for PR #{pr_number}...")
        try:
            pr_builder = PRContextBuilder(github_token)
            pr_context = pr_builder.build_context(repo_name, pr_number)

            print(f"PR: {pr_context.title}")
            print(f"Changed files: {len(pr_context.changed_files)}")
            print(f"Languages: {', '.join(pr_context.detected_languages)}")
            print(f"Change types: {', '.join([ct.value for ct in pr_context.change_types])}")

        except Exception as e:
            error_msg = f"Failed to fetch PR context: {str(e)[:200]}"
            errors.append(error_msg)
            print(f"  ✗ ERROR: {error_msg}")

            # Create minimal context to allow pipeline to continue
            pr_context = PRContext(
                pr_number=pr_number,
                title="[Error fetching PR]",
                description="",
                author="unknown",
                base_branch="main",
                head_branch="unknown",
                labels=[],
                changed_files=[],
                diff="",
                detected_languages=[],
                change_types=[]
            )
            warnings.append("Using minimal PR context due to fetch failure")

        # Step 2: Execute review aspects with error recovery
        print("\nRunning review aspects...")
        review_aspects = self.config.get('review_aspects', [])
        enabled_aspects = [a for a in review_aspects if a.get('enabled', True)]

        self.review_results, aspect_errors = self.execute_review_aspects_with_recovery(
            enabled_aspects,
            pr_context
        )
        errors.extend(aspect_errors)

        # Step 3: Evaluate if we have enough results
        failed_count = sum(1 for r in self.review_results if not r.success)
        if failed_count > len(enabled_aspects) / 2:
            warnings.append(f"Too many aspects failed ({failed_count}/{len(enabled_aspects)})")
            should_block = True
            blocking_reason = "Too many review aspects failed - results uncertain"
        elif len(self.review_results) == 0 or all(not r.success for r in self.review_results):
            errors.append("All review aspects failed")
            should_block = True
            blocking_reason = "Review pipeline encountered critical errors"
        else:
            should_block = False
            blocking_reason = None

        # Step 4: Aggregate results
        print("\nAggregating results...")
        aggregated = self.aggregate_results(pr_context, self.review_results)
        aggregated.errors = errors
        aggregated.warnings = warnings

        # Step 5: Apply blocking rules (only if we have some successful results)
        if not should_block:
            should_block, blocking_reason = self.apply_blocking_rules(
                aggregated.all_findings,
                self.config.get('blocking_rules', {})
            )

        aggregated.should_block = should_block
        aggregated.blocking_reason = blocking_reason

        # Step 6: Finalize metrics
        self.metrics.total_duration = time.time() - start_time
        aggregated.total_execution_time = self.metrics.total_duration
        aggregated.metrics = self.metrics

        # Print summary
        print(f"\n{'='*80}")
        print(f"Review complete in {aggregated.total_execution_time:.2f}s")
        print(f"Findings: {len(aggregated.all_findings)}")
        print(f"Successful aspects: {len([r for r in self.review_results if r.success])}/{len(enabled_aspects)}")
        print(f"Failed aspects: {failed_count}")
        print(f"Status: {'❌ BLOCKED' if should_block else '✅ APPROVED'}")
        if blocking_reason:
            print(f"Reason: {blocking_reason}")

        # Print metrics if available
        if self.metrics.api_calls > 0:
            print("\n📊 API Usage:")
            print(f"  Calls: {self.metrics.api_calls}")
            print(f"  Tokens: {self.metrics.input_tokens} in, {self.metrics.output_tokens} out")
            if self.metrics.cache_read_tokens > 0:
                print(f"  Cache: {self.metrics.cache_read_tokens} tokens")
            print(f"  Cost: ${self.metrics.estimated_cost_usd:.4f}")

        print(f"{'='*80}\n")

        return aggregated

    def execute_review_aspects_with_recovery(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[list[ReviewResult], list[str]]:
        """
        Execute all review aspects with error recovery and timeout handling.

        Args:
            aspects: List of review aspect configurations
            pr_context: PR context information

        Returns:
            Tuple of (review results, errors)
        """
        results = []
        errors = []

        # Separate parallel and sequential aspects
        parallel_aspects = [a for a in aspects if a.get('parallel', True)]
        sequential_aspects = [a for a in aspects if not a.get('parallel', True)]

        # Run parallel aspects with error recovery
        if parallel_aspects:
            print(f"Running {len(parallel_aspects)} aspects in parallel...")
            parallel_results, parallel_errors = self._execute_parallel_with_recovery(
                parallel_aspects, pr_context
            )
            results.extend(parallel_results)
            errors.extend(parallel_errors)

        # Run sequential aspects with error recovery
        if sequential_aspects:
            print(f"Running {len(sequential_aspects)} aspects sequentially...")
            sequential_results, sequential_errors = self._execute_sequential_with_recovery(
                sequential_aspects, pr_context
            )
            results.extend(sequential_results)
            errors.extend(sequential_errors)

        return results, errors

    def execute_review_aspects(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> list[ReviewResult]:
        """
        Execute all review aspects in parallel or sequential based on config.

        Deprecated: Use execute_review_aspects_with_recovery instead.

        Args:
            aspects: List of review aspect configurations
            pr_context: PR context information

        Returns:
            List of review results
        """
        results, _ = self.execute_review_aspects_with_recovery(aspects, pr_context)
        return results

    def _execute_parallel_with_recovery(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[list[ReviewResult], list[str]]:
        """Execute review aspects in parallel with timeout and error recovery."""
        results = []
        errors = []
        timeout = self.config.get('aspect_timeout', 300)  # 5 minutes default

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_aspect = {
                executor.submit(
                    self._execute_single_aspect_with_timeout,
                    aspect,
                    pr_context,
                    timeout
                ): aspect
                for aspect in aspects
            }

            for future in as_completed(future_to_aspect):
                aspect = future_to_aspect[future]
                try:
                    result = future.result()
                    results.append(result)

                    if result.success:
                        print(f"  ✓ {aspect['name']}: {len(result.findings)} findings ({result.execution_time:.1f}s)")
                    else:
                        print(f"  ✗ {aspect['name']}: Failed - {result.error_message}")
                        errors.append(f"Aspect '{aspect['name']}' failed: {result.error_message}")

                except Exception as e:
                    error_msg = f"Aspect '{aspect['name']}' crashed: {str(e)[:100]}"
                    errors.append(error_msg)
                    print(f"  ✗ {aspect['name']}: CRASHED - {str(e)[:100]}")

                    results.append(ReviewResult(
                        aspect_name=aspect['name'],
                        findings=[],
                        execution_time=0.0,
                        success=False,
                        error_message=str(e)
                    ))

        return results, errors

    def _execute_parallel(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> list[ReviewResult]:
        """Execute review aspects in parallel (deprecated)."""
        results, _ = self._execute_parallel_with_recovery(aspects, pr_context)
        return results

    def _execute_sequential_with_recovery(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[list[ReviewResult], list[str]]:
        """Execute review aspects sequentially with timeout and error recovery."""
        results = []
        errors = []
        shared_context = {}
        timeout = self.config.get('aspect_timeout', 300)

        for aspect in aspects:
            try:
                result = self._execute_single_aspect_with_timeout(
                    aspect,
                    pr_context,
                    timeout,
                    shared_context
                )
                results.append(result)

                if result.success:
                    print(f"  ✓ {aspect['name']}: {len(result.findings)} findings ({result.execution_time:.1f}s)")

                    # Update shared context for next aspect
                    shared_context[aspect['name']] = {
                        'findings': result.findings,
                        'metadata': result.metadata
                    }
                else:
                    print(f"  ✗ {aspect['name']}: Failed - {result.error_message}")
                    errors.append(f"Aspect '{aspect['name']}' failed: {result.error_message}")

                    # Continue with other aspects despite failure
                    continue

            except Exception as e:
                error_msg = f"Aspect '{aspect['name']}' crashed: {str(e)[:100]}"
                errors.append(error_msg)
                print(f"  ✗ {aspect['name']}: CRASHED - {str(e)[:100]}")

                results.append(ReviewResult(
                    aspect_name=aspect['name'],
                    findings=[],
                    execution_time=0.0,
                    success=False,
                    error_message=str(e)
                ))

                # Continue with other aspects
                continue

        return results, errors

    def _execute_sequential(
        self,
        aspects: list[dict[str, Any]],
        pr_context: PRContext
    ) -> list[ReviewResult]:
        """Execute review aspects sequentially (deprecated)."""
        results, _ = self._execute_sequential_with_recovery(aspects, pr_context)
        return results

    def _execute_single_aspect_with_timeout(
        self,
        aspect: dict[str, Any],
        pr_context: PRContext,
        timeout: int,
        shared_context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        Execute a single review aspect with timeout.

        Args:
            aspect: Aspect configuration
            pr_context: PR context
            timeout: Timeout in seconds
            shared_context: Context from previous sequential reviews

        Returns:
            ReviewResult
        """
        from concurrent.futures import TimeoutError as FuturesTimeoutError

        start_time = time.time()
        aspect_name = aspect.get('name')

        try:
            with ThreadPoolExecutor(max_workers=1) as executor:
                future = executor.submit(
                    self._execute_single_aspect,
                    aspect,
                    pr_context,
                    shared_context
                )

                try:
                    result = future.result(timeout=timeout)

                    # Track aspect duration in metrics
                    self.metrics.aspect_durations[aspect_name] = result.execution_time

                    return result

                except FuturesTimeoutError:
                    execution_time = time.time() - start_time
                    self.metrics.aspect_durations[aspect_name] = execution_time

                    return ReviewResult(
                        aspect_name=aspect_name,
                        findings=[],
                        execution_time=execution_time,
                        success=False,
                        error_message=f"Timeout after {timeout}s"
                    )

        except Exception as e:
            execution_time = time.time() - start_time
            self.metrics.aspect_durations[aspect_name] = execution_time

            return ReviewResult(
                aspect_name=aspect_name,
                findings=[],
                execution_time=execution_time,
                success=False,
                error_message=str(e)
            )

    def _execute_single_aspect(
        self,
        aspect: dict[str, Any],
        pr_context: PRContext,
        shared_context: dict[str, Any] | None = None
    ) -> ReviewResult:
        """
        Execute a single review aspect.

        Args:
            aspect: Aspect configuration
            pr_context: PR context
            shared_context: Context from previous sequential reviews

        Returns:
            ReviewResult
        """
        start_time = time.time()
        aspect_type = aspect.get('type')
        aspect_name = aspect.get('name')

        findings = []

        if aspect_type == 'classical':
            findings = self._run_classical_analysis(aspect, pr_context)
        elif aspect_type == 'ai':
            findings = self._run_ai_review(aspect, pr_context, shared_context)

        execution_time = time.time() - start_time

        return ReviewResult(
            aspect_name=aspect_name,
            findings=findings,
            execution_time=execution_time,
            success=True,
            metadata={}
        )

    def _run_classical_analysis(
        self,
        aspect: dict[str, Any],
        pr_context: PRContext
    ) -> list[Finding]:
        """Run classical static analysis tools."""
        findings = []
        changed_file_paths = [f.path for f in pr_context.changed_files]
        aspect_name = aspect.get('name')

        # Determine which analyzer to use based on detected languages
        if 'python' in pr_context.detected_languages:
            analyzer = PythonAnalyzer(
                self.project_root,
                tools=aspect.get('tools')
            )
            if analyzer.is_available():
                findings.extend(analyzer.run_analysis(changed_file_paths))

        if any(lang in pr_context.detected_languages for lang in ['javascript', 'typescript']):
            analyzer = JavaScriptAnalyzer(
                self.project_root,
                tools=aspect.get('tools')
            )
            if analyzer.is_available():
                findings.extend(analyzer.run_analysis(changed_file_paths))

        if 'java' in pr_context.detected_languages:
            analyzer = JavaAnalyzer(
                self.project_root,
                tools=aspect.get('tools')
            )
            if analyzer.is_available():
                findings.extend(analyzer.run_analysis(changed_file_paths))

        # Add aspect tracking to all classical findings
        for finding in findings:
            finding.aspect = aspect_name

        # Filter findings to only include lines changed in the PR (if enabled)
        if self.config.get('filtering', {}).get('only_changed_lines', True):
            filtered_findings = self._filter_findings_by_diff(findings, pr_context)
            print(f"   Filtered {len(findings)} findings → {len(filtered_findings)} on changed lines")
            return filtered_findings
        return findings

    def _filter_findings_by_diff(
        self,
        findings: list[Finding],
        pr_context: PRContext
    ) -> list[Finding]:
        """
        Filter findings to only include lines that were changed in the PR.

        Args:
            findings: All findings from static analysis
            pr_context: PR context with file changes

        Returns:
            Filtered findings only on changed lines
        """
        # Build a map of file -> set of changed line numbers
        changed_lines_map: dict[str, set[int]] = {}

        for file_change in pr_context.changed_files:
            if not file_change.patch:
                # If no patch (e.g., binary file), skip filtering for this file
                # Include all findings for files without patches
                continue

            changed_lines = self._extract_changed_lines_from_patch(file_change.patch)
            # Normalize path - handle both absolute and relative paths
            normalized_path = file_change.path.lstrip('./')
            changed_lines_map[normalized_path] = changed_lines

        # Filter findings
        filtered_findings = []
        for finding in findings:
            # Normalize the finding file path
            finding_path = finding.file_path.lstrip('./')
            # Remove absolute path prefix if present
            if '/' in finding_path:
                # Try to extract relative path
                parts = finding_path.split('/')
                # Look for common patterns like /home/runner/work/repo/repo/file.py
                for i in range(len(parts)):
                    potential_path = '/'.join(parts[i:])
                    if potential_path in changed_lines_map:
                        finding_path = potential_path
                        break
                else:
                    # If no match found, use the last component as fallback
                    finding_path = '/'.join(parts[-2:]) if len(parts) >= 2 else parts[-1]

            # Check if this file has changed lines info
            if finding_path not in changed_lines_map:
                # File not in diff (shouldn't happen since we only analyze changed files)
                # but include it to be safe
                filtered_findings.append(finding)
                continue

            # Check if the finding is on a changed line
            if finding.line_number is None:
                # File-level finding, include it
                filtered_findings.append(finding)
            elif finding.line_number in changed_lines_map[finding_path]:
                # Finding is on a changed line
                filtered_findings.append(finding)
            # else: Finding is on an unchanged line, skip it

        return filtered_findings

    def _extract_changed_lines_from_patch(self, patch: str) -> set[int]:
        """
        Extract line numbers that were added or modified from a git patch.

        Args:
            patch: Git diff patch string

        Returns:
            Set of line numbers that were changed
        """
        import re

        changed_lines = set()
        current_line = 0  # Initialize to 0, will be set by chunk header

        # Parse unified diff format
        # Look for chunk headers like: @@ -10,7 +10,8 @@
        # This means: old file starts at line 10 (7 lines), new file starts at line 10 (8 lines)
        for line in patch.split('\n'):
            # Find chunk header
            if line.startswith('@@'):
                match = re.match(r'@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@', line)
                if match:
                    start_line = int(match.group(1))
                    current_line = start_line
                continue

            # Only process lines if we've seen a chunk header (current_line > 0)
            if current_line == 0:
                continue

            # Track added/modified lines (lines starting with + but not ++)
            if line.startswith('+') and not line.startswith('+++'):
                changed_lines.add(current_line)
                current_line += 1
            elif line.startswith(' '):
                # Context line, advance line number
                current_line += 1
            # Lines starting with - are deletions, don't advance line number

        return changed_lines

    def _run_ai_review(
        self,
        aspect: dict[str, Any],
        pr_context: PRContext,
        shared_context: dict[str, Any] | None = None
    ) -> list[Finding]:
        """
        Run AI-driven review using Claude Code CLI.

        Args:
            aspect: AI review aspect configuration
            pr_context: PR context
            shared_context: Context from previous reviews

        Returns:
            List of findings from AI review
        """
        from .ai_review import AIReviewEngine

        try:
            # Create AI review engine with metrics tracking
            ai_engine = AIReviewEngine(
                project_root=str(self.project_root),
                config=self.config,
                metrics=self.metrics
            )

            # Run the review
            findings = ai_engine.run_review(aspect, pr_context, shared_context)

            return findings

        except Exception as e:
            print(f"  AI review '{aspect['name']}' failed: {str(e)[:100]}")
            return []

    def aggregate_results(
        self,
        pr_context: PRContext,
        review_results: list[ReviewResult]
    ) -> AggregatedResults:
        """
        Aggregate results from all review aspects.

        Args:
            pr_context: PR context
            review_results: List of review results

        Returns:
            AggregatedResults with deduplicated findings
        """
        # Collect all findings
        all_findings = []
        for result in review_results:
            all_findings.extend(result.findings)

        # Deduplicate findings
        deduplicated = self._deduplicate_findings(all_findings)

        # Calculate statistics
        statistics = self._calculate_statistics(deduplicated)

        return AggregatedResults(
            pr_context=pr_context,
            review_results=review_results,
            all_findings=deduplicated,
            statistics=statistics,
            should_block=False,  # Will be set by apply_blocking_rules
            blocking_reason=None
        )

    def _deduplicate_findings(self, findings: list[Finding]) -> list[Finding]:
        """
        Deduplicate semantically similar findings at nearby locations.

        Strategy:
        - Can use AI-powered deduplication (configurable) or word-based similarity
        - Groups findings by file and category
        - Within each group, merges findings that are semantically similar AND nearby
        - "Nearby" = within configurable threshold (default: 10 lines)
        - Different files or distant lines = separate findings (not duplicates)
        - Preserves highest severity and combines unique insights

        Examples:
        - SQL injection on lines 43, 44, 45 → merged into one finding
        - Same SQL injection in different files → separate findings
        - Same issue 50 lines apart in same file → separate findings

        Args:
            findings: List of findings

        Returns:
            Deduplicated list of findings
        """
        if not findings:
            return []

        # Get deduplication config
        dedup_config = self.config.get('deduplication', {})
        proximity_threshold = dedup_config.get('proximity_threshold', 10)

        # Group by file only (not category) to catch cross-category duplicates
        # Example: SQL injection reported as both "security" AND "architecture" should merge
        file_groups: dict[str, list[Finding]] = {}

        for finding in findings:
            group_key = finding.file_path

            if group_key not in file_groups:
                file_groups[group_key] = []
            file_groups[group_key].append(finding)

        # Process each group with AI deduplication
        deduplicated = []

        for group_key, group_findings in file_groups.items():
            if len(group_findings) > 1:
                # Always use AI-powered deduplication
                print(f"\n🔍 Deduplicating {len(group_findings)} findings in {group_key}")
                try:
                    merged_findings = self._deduplicate_with_ai(
                        group_findings,
                        proximity_threshold
                    )
                    reduction = len(group_findings) - len(merged_findings)
                    if reduction > 0:
                        print(f"   ✅ Merged {len(group_findings)} → {len(merged_findings)} (removed {reduction} duplicates)")
                    else:
                        print(f"   ℹ️  No duplicates detected, kept all {len(merged_findings)} findings")
                    deduplicated.extend(merged_findings)
                except Exception as e:
                    # Fail-safe: keep original findings if AI deduplication fails
                    print(f"   ⚠️ AI deduplication failed ({type(e).__name__}): {str(e)[:100]}")
                    print(f"   Keeping {len(group_findings)} original findings (no deduplication)")
                    deduplicated.extend(group_findings)
            else:
                # Single finding, no deduplication needed
                deduplicated.extend(group_findings)

        return deduplicated

    def _deduplicate_with_ai(
        self,
        findings: list[Finding],
        proximity_threshold: int
    ) -> list[Finding]:
        """
        Use AI to deduplicate findings (fast Haiku model).

        Uses a singleton AIDeduplicator instance to avoid recreating
        the Anthropic client on every call (performance optimization).

        Args:
            findings: List of findings from same file + category
            proximity_threshold: Max line distance for deduplication

        Returns:
            Deduplicated findings
        """
        # Lazy-load AIDeduplicator (create once, reuse)
        if self._ai_deduplicator is None:
            from .ai_deduplication import AIDeduplicator

            dedup_config = self.config.get('deduplication', {})
            model = dedup_config.get('model', 'claude-haiku-4-5')

            self._ai_deduplicator = AIDeduplicator(
                model=model,
                metrics=self.metrics
            )

        return self._ai_deduplicator.deduplicate_group(findings, proximity_threshold)

    def _calculate_statistics(self, findings: list[Finding]) -> dict[str, int]:
        """Calculate statistics from findings."""
        stats = {
            'total': len(findings),
            'by_severity': {},
            'by_category': {}
        }

        # Count by severity
        for severity in Severity:
            count = sum(1 for f in findings if f.severity == severity)
            stats['by_severity'][severity.value] = count

        # Count by category
        from .models import FindingCategory
        for category in FindingCategory:
            count = sum(1 for f in findings if f.category == category)
            stats['by_category'][category.value] = count

        return stats

    def apply_blocking_rules(
        self,
        findings: list[Finding],
        blocking_rules: dict[str, Any]
    ) -> tuple[bool, str | None]:
        """
        Determine if PR should be blocked based on findings.

        Args:
            findings: List of findings
            blocking_rules: Blocking rules configuration

        Returns:
            Tuple of (should_block, reason)
        """
        # Check for critical findings
        if blocking_rules.get('block_on_critical', True):
            critical_count = sum(
                1 for f in findings if f.severity == Severity.CRITICAL
            )
            if critical_count > 0:
                return True, f"Found {critical_count} critical issue(s)"

        # Check for high severity findings
        if blocking_rules.get('block_on_high', False):
            high_count = sum(
                1 for f in findings if f.severity == Severity.HIGH
            )
            if high_count > 0:
                return True, f"Found {high_count} high severity issue(s)"

        # Check maximum findings thresholds
        max_findings = blocking_rules.get('max_findings', {})

        for severity_name, max_count in max_findings.items():
            severity = Severity(severity_name)
            count = sum(1 for f in findings if f.severity == severity)

            if count > max_count:
                return True, f"Exceeded maximum {severity_name} findings ({count} > {max_count})"

        return False, None

    def generate_summary(self, aggregated: AggregatedResults) -> str:
        """
        Generate human-readable summary of review results.

        Args:
            aggregated: Aggregated results

        Returns:
            Markdown-formatted summary
        """
        lines = []
        lines.append("# 🤖 AI Code Review Summary\n")

        # PR Info
        lines.append(f"**PR:** #{aggregated.pr_context.pr_number} - {aggregated.pr_context.title}")
        lines.append(f"**Author:** @{aggregated.pr_context.author}")
        lines.append(f"**Changed Files:** {len(aggregated.pr_context.changed_files)}")
        lines.append(f"**Languages:** {', '.join(aggregated.pr_context.detected_languages)}\n")

        # Statistics
        lines.append("## 📊 Review Statistics\n")
        lines.append(f"- **Total Findings:** {aggregated.statistics['total']}")
        lines.append(f"- **Execution Time:** {aggregated.total_execution_time:.2f}s\n")

        # Severity breakdown
        lines.append("### By Severity\n")
        severity_emoji = {
            'critical': '🔴',
            'high': '🟠',
            'medium': '🟡',
            'low': '🔵',
            'info': '⚪'
        }

        for severity, count in aggregated.statistics['by_severity'].items():
            if count > 0:
                emoji = severity_emoji.get(severity, '•')
                lines.append(f"- {emoji} **{severity.capitalize()}:** {count}")

        # Category breakdown
        lines.append("\n### By Category\n")
        for category, count in aggregated.statistics['by_category'].items():
            if count > 0:
                lines.append(f"- **{category.replace('_', ' ').title()}:** {count}")

        # Blocking status
        lines.append(f"\n## 🚦 Status: {'❌ BLOCKED' if aggregated.should_block else '✅ APPROVED'}\n")
        if aggregated.blocking_reason:
            lines.append(f"**Reason:** {aggregated.blocking_reason}\n")

        # Top findings
        if aggregated.all_findings:
            lines.append("## 🔍 Top Issues\n")
            # Show top 5 most severe findings
            sorted_findings = sorted(
                aggregated.all_findings,
                key=lambda f: list(Severity).index(f.severity)
            )
            for finding in sorted_findings[:5]:
                emoji = severity_emoji.get(finding.severity.value, '•')
                lines.append(f"### {emoji} {finding.category.value.replace('_', ' ').title()}")
                lines.append(f"**File:** `{finding.file_path}`")
                if finding.line_number:
                    lines.append(f" (Line {finding.line_number})")
                lines.append(f"\n{finding.message}\n")
                if finding.suggestion:
                    lines.append(f"**💡 Suggestion:** {finding.suggestion}\n")

        return "\n".join(lines)
