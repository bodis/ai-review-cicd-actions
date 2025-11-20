"""
Data models for the code review system.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class Severity(str, Enum):
    """Finding severity levels."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class FindingCategory(str, Enum):
    """Categories of code review findings."""

    SECURITY = "security"
    PERFORMANCE = "performance"
    ARCHITECTURE = "architecture"
    STYLE = "style"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    CODE_QUALITY = "code_quality"
    BREAKING_CHANGE = "breaking_change"


class ChangeType(str, Enum):
    """Types of changes detected in PRs."""

    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    ARCHITECTURE_DRIFT = "architecture_drift"
    BREAKING_CHANGE = "breaking_change"
    SECURITY_RISK = "security_risk"
    PERFORMANCE_REGRESSION = "performance_regression"
    TEST_CHANGE = "test_change"
    DEPENDENCY_CHANGE = "dependency_change"
    DOCUMENTATION = "documentation"


@dataclass
class Finding:
    """Represents a single code review finding."""

    file_path: str
    line_number: int | None
    severity: Severity
    category: FindingCategory
    message: str
    suggestion: str | None = None
    tool: str | None = None
    rule_id: str | None = None
    code_snippet: str | None = None
    aspect: str | None = (
        None  # Review aspect that found this issue (e.g., "security_review", "python_static_analysis")
    )

    def to_dict(self) -> dict[str, Any]:
        """Convert finding to dictionary."""
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "severity": self.severity.value,
            "category": self.category.value,
            "message": self.message,
            "suggestion": self.suggestion,
            "tool": self.tool,
            "rule_id": self.rule_id,
            "code_snippet": self.code_snippet,
            "aspect": self.aspect,
        }


@dataclass
class FileChange:
    """Represents a file change in a PR."""

    path: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    changes: int
    patch: str | None = None
    old_path: str | None = None  # For renamed files


@dataclass
class PRContext:
    """Context information about a Pull Request."""

    pr_number: int
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    labels: list[str]
    changed_files: list[FileChange]
    diff: str
    detected_languages: list[str] = field(default_factory=list)
    change_types: list[ChangeType] = field(default_factory=list)


@dataclass
class ReviewResult:
    """Result from a single review aspect."""

    aspect_name: str
    findings: list[Finding]
    execution_time: float
    success: bool
    error_message: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class Metrics:
    """Performance and cost metrics for review pipeline."""

    total_duration: float = 0.0
    aspect_durations: dict[str, float] = field(default_factory=dict)
    api_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    cache_read_tokens: int = 0
    estimated_cost_usd: float = 0.0

    def add_tokens(self, input_tokens: int, output_tokens: int, cache_tokens: int = 0):
        """Add token usage and calculate costs."""
        self.api_calls += 1
        self.input_tokens += input_tokens
        self.output_tokens += output_tokens
        self.cache_read_tokens += cache_tokens

        # Claude 3.5 Sonnet pricing (per million tokens)
        input_cost = input_tokens * 0.000003  # $3/1M input
        output_cost = output_tokens * 0.000015  # $15/1M output
        cache_cost = cache_tokens * 0.0000003  # $0.30/1M cache reads (90% discount)

        self.estimated_cost_usd += input_cost + output_cost + cache_cost

    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "performance": {
                "total_duration_seconds": round(self.total_duration, 2),
                "aspect_durations": {k: round(v, 2) for k, v in self.aspect_durations.items()},
            },
            "api_usage": {
                "total_calls": self.api_calls,
                "input_tokens": self.input_tokens,
                "output_tokens": self.output_tokens,
                "cache_read_tokens": self.cache_read_tokens,
                "estimated_cost_usd": round(self.estimated_cost_usd, 4),
            },
        }


@dataclass
class AggregatedResults:
    """Aggregated results from all review aspects."""

    pr_context: PRContext
    review_results: list[ReviewResult]
    all_findings: list[Finding]
    statistics: dict[str, int]
    should_block: bool
    blocking_reason: str | None = None
    total_execution_time: float = 0.0
    metrics: Optional["Metrics"] = None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert aggregated results to dictionary."""
        result = {
            "pr_number": self.pr_context.pr_number,
            "should_block": self.should_block,
            "blocking_reason": self.blocking_reason,
            "statistics": self.statistics,
            "total_execution_time": self.total_execution_time,
            "findings": [f.to_dict() for f in self.all_findings],
            "review_results": [
                {
                    "aspect": r.aspect_name,
                    "success": r.success,
                    "execution_time": r.execution_time,
                    "findings_count": len(r.findings),
                    "error": r.error_message,
                }
                for r in self.review_results
            ],
        }

        if self.metrics:
            result["metrics"] = self.metrics.to_dict()

        if self.errors:
            result["errors"] = self.errors

        if self.warnings:
            result["warnings"] = self.warnings

        return result


@dataclass
class DependencyChange:
    """Represents a dependency change."""

    file: str
    package_name: str
    old_version: str | None
    new_version: str | None
    change_type: str  # added, removed, updated
    is_major_update: bool = False
    has_vulnerabilities: bool = False
    vulnerability_details: list[dict[str, Any]] = field(default_factory=list)
