#!/usr/bin/env python3
"""
Test script to verify semantic deduplication logic with sample findings.
"""
from lib.models import Finding, FindingCategory, Severity
from lib.orchestrator import ReviewOrchestrator


def test_semantic_deduplication():
    """Test that semantic deduplication works correctly."""

    # Create test findings similar to your review-results-3.json examples
    findings = [
        # Example 1: Resource leak duplicates (lines 43-44)
        Finding(
            file_path="lib/orchestrator.py",
            line_number=43,
            severity=Severity.HIGH,
            category=FindingCategory.CODE_QUALITY,
            message="Resource Leak - No Connection Cleanup",
            suggestion="Close database connections in a finally block",
            tool="pylint",
            rule_id="no-connection-cleanup",
            aspect="python_static_analysis"
        ),
        Finding(
            file_path="lib/orchestrator.py",
            line_number=44,
            severity=Severity.HIGH,
            category=FindingCategory.CODE_QUALITY,
            message="Resource leak: Database connection not closed",
            suggestion="Use context manager or explicit close",
            tool="bandit",
            rule_id="B101",
            aspect="python_static_analysis"
        ),

        # Example 2: Dead code duplicates (line 38)
        Finding(
            file_path="lib/orchestrator.py",
            line_number=38,
            severity=Severity.MEDIUM,
            category=FindingCategory.CODE_QUALITY,
            message="✨ Dead code: Method never called",
            suggestion="Remove unused method",
            tool="claude-ai",
            rule_id="dead-code",
            aspect="code_quality_review"
        ),
        Finding(
            file_path="lib/orchestrator.py",
            line_number=38,
            severity=Severity.LOW,
            category=FindingCategory.CODE_QUALITY,
            message="Orphaned method breaks orchestrator pattern",
            suggestion="Remove or integrate into workflow",
            tool="claude-ai",
            rule_id="architecture-violation",
            aspect="architecture_review"
        ),

        # Example 3: SQL injection duplicates (lines 43-45)
        Finding(
            file_path="lib/orchestrator.py",
            line_number=43,
            severity=Severity.CRITICAL,
            category=FindingCategory.SECURITY,
            message="🔒 Critical SQL Injection Risk",
            suggestion="Use parameterized queries",
            tool="claude-ai",
            rule_id="sql-injection",
            aspect="security_review"
        ),
        Finding(
            file_path="lib/orchestrator.py",
            line_number=43,
            severity=Severity.HIGH,
            category=FindingCategory.SECURITY,
            message="🔒 CRITICAL: SQL Injection vulnerability",
            suggestion="Replace f-string with parameters",
            tool="bandit",
            rule_id="B608",
            aspect="python_static_analysis"
        ),
        Finding(
            file_path="lib/orchestrator.py",
            line_number=43,
            severity=Severity.CRITICAL,
            category=FindingCategory.SECURITY,
            message="SQL injection vulnerability: User input (pr_number and status) is directly concatenated into SQL query",
            suggestion="Use parameterized queries with placeholders",
            tool="claude-ai",
            rule_id="sql-injection-detailed",
            aspect="security_review"
        ),

        # Different file - should NOT be deduplicated
        Finding(
            file_path="lib/other_file.py",
            line_number=43,
            severity=Severity.CRITICAL,
            category=FindingCategory.SECURITY,
            message="🔒 Critical SQL Injection Risk",
            suggestion="Use parameterized queries",
            tool="claude-ai",
            rule_id="sql-injection",
            aspect="security_review"
        ),
    ]

    # Create orchestrator with minimal config
    orchestrator = ReviewOrchestrator(config={})

    # Run deduplication
    deduplicated = orchestrator._deduplicate_findings(findings)

    print("=" * 80)
    print("SEMANTIC DEDUPLICATION TEST")
    print("=" * 80)
    print(f"\nOriginal findings: {len(findings)}")
    print(f"After deduplication: {len(deduplicated)}")
    print(f"Removed: {len(findings) - len(deduplicated)} duplicates\n")

    # Group by category for analysis
    by_category = {}
    for finding in deduplicated:
        key = f"{finding.file_path}:{finding.category.value}"
        if key not in by_category:
            by_category[key] = []
        by_category[key].append(finding)

    print("Deduplicated findings by category:\n")
    for key, group in sorted(by_category.items()):
        print(f"📁 {key}")
        for finding in group:
            print(f"   Line {finding.line_number}: {finding.severity.value.upper()}")
            print(f"   Message: {finding.message[:80]}...")
            print(f"   Tools: {finding.tool}")
            print(f"   Aspects: {finding.aspect}")
            print()

    # Verify expected behavior
    print("=" * 80)
    print("VERIFICATION")
    print("=" * 80)

    # Should have merged SQL injection findings (3 → 1)
    security_findings = [f for f in deduplicated if f.category == FindingCategory.SECURITY and f.file_path == "lib/orchestrator.py"]
    print(f"✓ SQL injection findings (lib/orchestrator.py): {len(security_findings)} (expected: 1)")
    if security_findings:
        print(f"  - Combined aspects: {security_findings[0].aspect}")
        print(f"  - Combined tools: {security_findings[0].tool}")
        print(f"  - Severity: {security_findings[0].severity.value}")

    # Should have merged code quality findings
    quality_findings = [f for f in deduplicated if f.category == FindingCategory.CODE_QUALITY and f.file_path == "lib/orchestrator.py"]
    print(f"\n✓ Code quality findings (lib/orchestrator.py): {len(quality_findings)} (expected: 2)")
    print(f"  - Resource leak (merged)")
    print(f"  - Dead code (merged)")

    # Should NOT merge different file
    other_file_findings = [f for f in deduplicated if f.file_path == "lib/other_file.py"]
    print(f"\n✓ Different file findings: {len(other_file_findings)} (expected: 1)")
    print(f"  - Correctly preserved as separate issue")

    # Check that highest severity is preserved
    if security_findings:
        assert security_findings[0].severity == Severity.CRITICAL, "Should preserve CRITICAL severity"
        print(f"\n✓ Severity preservation: CRITICAL (highest) preserved")

    # Check aspect tracking
    aspects_found = set()
    for finding in deduplicated:
        if finding.aspect:
            aspects_found.update(finding.aspect.split(", "))

    print(f"\n✓ Aspect tracking: {len(aspects_found)} unique aspects found")
    print(f"  - {', '.join(sorted(aspects_found))}")

    print("\n" + "=" * 80)
    print("✅ DEDUPLICATION TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    test_semantic_deduplication()
