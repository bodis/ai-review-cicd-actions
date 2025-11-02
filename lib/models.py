"""
Data models for the code review system.
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum


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
    line_number: Optional[int]
    severity: Severity
    category: FindingCategory
    message: str
    suggestion: Optional[str] = None
    tool: Optional[str] = None
    rule_id: Optional[str] = None
    code_snippet: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
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
            "code_snippet": self.code_snippet
        }


@dataclass
class FileChange:
    """Represents a file change in a PR."""
    path: str
    status: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    changes: int
    patch: Optional[str] = None
    old_path: Optional[str] = None  # For renamed files


@dataclass
class PRContext:
    """Context information about a Pull Request."""
    pr_number: int
    title: str
    description: str
    author: str
    base_branch: str
    head_branch: str
    labels: List[str]
    changed_files: List[FileChange]
    diff: str
    detected_languages: List[str] = field(default_factory=list)
    change_types: List[ChangeType] = field(default_factory=list)


@dataclass
class ReviewResult:
    """Result from a single review aspect."""
    aspect_name: str
    findings: List[Finding]
    execution_time: float
    success: bool
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AggregatedResults:
    """Aggregated results from all review aspects."""
    pr_context: PRContext
    review_results: List[ReviewResult]
    all_findings: List[Finding]
    statistics: Dict[str, int]
    should_block: bool
    blocking_reason: Optional[str] = None
    total_execution_time: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert aggregated results to dictionary."""
        return {
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
                    "error": r.error_message
                }
                for r in self.review_results
            ]
        }


@dataclass
class DependencyChange:
    """Represents a dependency change."""
    file: str
    package_name: str
    old_version: Optional[str]
    new_version: Optional[str]
    change_type: str  # added, removed, updated
    is_major_update: bool = False
    has_vulnerabilities: bool = False
    vulnerability_details: List[Dict[str, Any]] = field(default_factory=list)
