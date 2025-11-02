"""
Orchestrator - Coordinates execution of all review aspects.
"""
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from .models import (
    PRContext, ReviewResult, AggregatedResults,
    Finding, Severity, ChangeType, Metrics
)
from .config_manager import ConfigManager
from .pr_context import PRContextBuilder
from .analyzers.python_analyzer import PythonAnalyzer
from .analyzers.javascript_analyzer import JavaScriptAnalyzer
from .analyzers.java_analyzer import JavaAnalyzer


class ReviewOrchestrator:
    """Orchestrates the entire code review pipeline."""

    def __init__(self, config: Dict[str, Any], project_root: str = "."):
        """
        Initialize orchestrator.

        Args:
            config: Configuration dictionary
            project_root: Root directory of the project
        """
        self.config = config
        self.project_root = project_root
        self.review_results: List[ReviewResult] = []
        self.metrics = Metrics()  # Initialize metrics tracking

    def run_review_pipeline(
        self,
        repo_name: str,
        pr_number: int,
        github_token: Optional[str] = None
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
            print(f"\n📊 API Usage:")
            print(f"  Calls: {self.metrics.api_calls}")
            print(f"  Tokens: {self.metrics.input_tokens} in, {self.metrics.output_tokens} out")
            if self.metrics.cache_read_tokens > 0:
                print(f"  Cache: {self.metrics.cache_read_tokens} tokens")
            print(f"  Cost: ${self.metrics.estimated_cost_usd:.4f}")

        print(f"{'='*80}\n")

        return aggregated

    def execute_review_aspects_with_recovery(
        self,
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[List[ReviewResult], List[str]]:
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
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> List[ReviewResult]:
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
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[List[ReviewResult], List[str]]:
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
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> List[ReviewResult]:
        """Execute review aspects in parallel (deprecated)."""
        results, _ = self._execute_parallel_with_recovery(aspects, pr_context)
        return results

    def _execute_sequential_with_recovery(
        self,
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> tuple[List[ReviewResult], List[str]]:
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
        aspects: List[Dict[str, Any]],
        pr_context: PRContext
    ) -> List[ReviewResult]:
        """Execute review aspects sequentially (deprecated)."""
        results, _ = self._execute_sequential_with_recovery(aspects, pr_context)
        return results

    def _execute_single_aspect_with_timeout(
        self,
        aspect: Dict[str, Any],
        pr_context: PRContext,
        timeout: int,
        shared_context: Optional[Dict[str, Any]] = None
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
        aspect: Dict[str, Any],
        pr_context: PRContext,
        shared_context: Optional[Dict[str, Any]] = None
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
        aspect: Dict[str, Any],
        pr_context: PRContext
    ) -> List[Finding]:
        """Run classical static analysis tools."""
        findings = []
        changed_file_paths = [f.path for f in pr_context.changed_files]

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

        return findings

    def _run_ai_review(
        self,
        aspect: Dict[str, Any],
        pr_context: PRContext,
        shared_context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
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
        review_results: List[ReviewResult]
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

    def _deduplicate_findings(self, findings: List[Finding]) -> List[Finding]:
        """
        Deduplicate findings based on file, line, and message.

        Args:
            findings: List of findings

        Returns:
            Deduplicated list of findings
        """
        seen = set()
        deduplicated = []

        for finding in findings:
            # Create unique key
            key = (
                finding.file_path,
                finding.line_number,
                finding.message,
                finding.category.value
            )

            if key not in seen:
                seen.add(key)
                deduplicated.append(finding)

        return deduplicated

    def _calculate_statistics(self, findings: List[Finding]) -> Dict[str, int]:
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
        findings: List[Finding],
        blocking_rules: Dict[str, Any]
    ) -> tuple[bool, Optional[str]]:
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
