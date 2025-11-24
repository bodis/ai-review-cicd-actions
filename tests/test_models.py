"""
Tests for data models.
"""

from ai_review.models import (
    AggregatedResults,
    ChangeType,
    FileChange,
    Finding,
    FindingCategory,
    PRContext,
    ReviewResult,
    Severity,
)


class TestFinding:
    """Test Finding model."""

    def test_finding_creation(self):
        """Test creating a Finding instance."""
        finding = Finding(
            file_path="test.py",
            line_number=10,
            severity=Severity.HIGH,
            category=FindingCategory.SECURITY,
            message="SQL injection vulnerability",
            suggestion="Use parameterized queries",
        )

        assert finding.file_path == "test.py"
        assert finding.line_number == 10
        assert finding.severity == Severity.HIGH
        assert finding.category == FindingCategory.SECURITY

    def test_finding_to_dict(self):
        """Test converting Finding to dictionary."""
        finding = Finding(
            file_path="test.py",
            line_number=10,
            severity=Severity.HIGH,
            category=FindingCategory.SECURITY,
            message="Test message",
            tool="bandit",
            rule_id="B608",
        )

        result = finding.to_dict()

        assert result["file_path"] == "test.py"
        assert result["line_number"] == 10
        assert result["severity"] == "high"
        assert result["category"] == "security"
        assert result["tool"] == "bandit"


class TestPRContext:
    """Test PRContext model."""

    def test_pr_context_creation(self):
        """Test creating a PRContext instance."""
        file_change = FileChange(
            path="test.py", status="modified", additions=10, deletions=5, changes=15
        )

        pr_context = PRContext(
            pr_number=123,
            title="Test PR",
            description="Test description",
            author="testuser",
            base_branch="main",
            head_branch="feature/test",
            labels=["bug", "high-priority"],
            changed_files=[file_change],
            diff="test diff",
            detected_languages=["python"],
            change_types=[ChangeType.BUGFIX],
        )

        assert pr_context.pr_number == 123
        assert pr_context.title == "Test PR"
        assert len(pr_context.changed_files) == 1
        assert pr_context.detected_languages == ["python"]
        assert ChangeType.BUGFIX in pr_context.change_types


class TestReviewResult:
    """Test ReviewResult model."""

    def test_review_result_creation(self):
        """Test creating a ReviewResult instance."""
        finding = Finding(
            file_path="test.py",
            line_number=10,
            severity=Severity.MEDIUM,
            category=FindingCategory.CODE_QUALITY,
            message="Test finding",
        )

        result = ReviewResult(
            aspect_name="code_quality", findings=[finding], execution_time=1.5, success=True
        )

        assert result.aspect_name == "code_quality"
        assert len(result.findings) == 1
        assert result.execution_time == 1.5
        assert result.success is True


class TestAggregatedResults:
    """Test AggregatedResults model."""

    def test_aggregated_results_to_dict(self):
        """Test converting AggregatedResults to dictionary."""
        file_change = FileChange(
            path="test.py", status="modified", additions=10, deletions=5, changes=15
        )

        pr_context = PRContext(
            pr_number=123,
            title="Test PR",
            description="Test",
            author="testuser",
            base_branch="main",
            head_branch="feature/test",
            labels=[],
            changed_files=[file_change],
            diff="",
            detected_languages=["python"],
        )

        finding = Finding(
            file_path="test.py",
            line_number=10,
            severity=Severity.HIGH,
            category=FindingCategory.SECURITY,
            message="Test finding",
        )

        review_result = ReviewResult(
            aspect_name="security", findings=[finding], execution_time=1.0, success=True
        )

        aggregated = AggregatedResults(
            pr_context=pr_context,
            review_results=[review_result],
            all_findings=[finding],
            statistics={"total": 1},
            should_block=True,
            blocking_reason="Critical issues found",
            total_execution_time=2.5,
        )

        result_dict = aggregated.to_dict()

        assert result_dict["pr_number"] == 123
        assert result_dict["should_block"] is True
        assert result_dict["blocking_reason"] == "Critical issues found"
        assert result_dict["total_execution_time"] == 2.5
        assert len(result_dict["findings"]) == 1
        assert len(result_dict["review_results"]) == 1


class TestEnums:
    """Test enum types."""

    def test_severity_enum(self):
        """Test Severity enum."""
        assert Severity.CRITICAL.value == "critical"
        assert Severity.HIGH.value == "high"
        assert Severity.MEDIUM.value == "medium"
        assert Severity.LOW.value == "low"
        assert Severity.INFO.value == "info"

    def test_finding_category_enum(self):
        """Test FindingCategory enum."""
        assert FindingCategory.SECURITY.value == "security"
        assert FindingCategory.PERFORMANCE.value == "performance"
        assert FindingCategory.ARCHITECTURE.value == "architecture"

    def test_change_type_enum(self):
        """Test ChangeType enum."""
        assert ChangeType.FEATURE.value == "feature"
        assert ChangeType.BUGFIX.value == "bugfix"
        assert ChangeType.SECURITY_RISK.value == "security_risk"
