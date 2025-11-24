"""
Base analyzer class for all static analysis tools.
"""

import subprocess
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from ..models import Finding, FindingCategory, Severity


class BaseAnalyzer(ABC):
    """Abstract base class for all code analyzers."""

    def __init__(self, project_root: str = "."):
        """
        Initialize analyzer.

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)

    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if the analysis tool is available.

        Returns:
            True if tool is installed and ready
        """
        pass

    @abstractmethod
    def run_analysis(self, files: list[str]) -> list[Finding]:
        """
        Run analysis on specified files.

        Args:
            files: List of file paths to analyze

        Returns:
            List of findings
        """
        pass

    @abstractmethod
    def get_tool_name(self) -> str:
        """Get the name of the analysis tool."""
        pass

    def run_command(
        self, command: list[str], cwd: str | None = None, capture_output: bool = True
    ) -> subprocess.CompletedProcess:
        """
        Run a shell command.

        Args:
            command: Command and arguments as list
            cwd: Working directory
            capture_output: Whether to capture stdout/stderr

        Returns:
            CompletedProcess object
        """
        try:
            result = subprocess.run(
                command,
                cwd=cwd or str(self.project_root),
                capture_output=capture_output,
                text=True,
                timeout=300,  # 5 minute timeout
            )
            return result
        except subprocess.TimeoutExpired as e:
            raise RuntimeError(f"Command timed out: {' '.join(command)}") from e
        except FileNotFoundError as e:
            raise RuntimeError(f"Command not found: {command[0]}") from e

    def filter_files_by_extension(self, files: list[str], extensions: list[str]) -> list[str]:
        """
        Filter files by extension.

        Args:
            files: List of file paths
            extensions: List of extensions to keep (e.g., ['.py', '.pyx'])

        Returns:
            Filtered list of files
        """
        return [f for f in files if any(f.endswith(ext) for ext in extensions)]

    def standardize_results(
        self, raw_results: list[dict[str, Any]], tool_name: str
    ) -> list[Finding]:
        """
        Convert tool-specific results to standard Finding objects.

        Args:
            raw_results: Raw results from analysis tool
            tool_name: Name of the tool

        Returns:
            List of standardized Finding objects
        """
        findings = []

        for result in raw_results:
            finding = self._convert_to_finding(result, tool_name)
            if finding:
                findings.append(finding)

        return findings

    @abstractmethod
    def _convert_to_finding(self, raw_result: dict[str, Any], tool_name: str) -> Finding | None:
        """
        Convert a single raw result to a Finding object.
        Must be implemented by each analyzer.

        Args:
            raw_result: Raw result from tool
            tool_name: Name of the tool

        Returns:
            Finding object or None if result should be skipped
        """
        pass

    def map_severity(
        self, tool_severity: str, severity_map: dict[str, Severity] | None = None
    ) -> Severity:
        """
        Map tool-specific severity to standard severity level.

        Args:
            tool_severity: Severity string from tool
            severity_map: Custom severity mapping

        Returns:
            Standard Severity enum value
        """
        if severity_map and tool_severity.lower() in severity_map:
            return severity_map[tool_severity.lower()]

        # Default mapping
        severity_lower = tool_severity.lower()

        if severity_lower in ["critical", "error", "high"]:
            return Severity.HIGH
        elif severity_lower in ["warning", "medium", "moderate"]:
            return Severity.MEDIUM
        elif severity_lower in ["low", "minor"]:
            return Severity.LOW
        elif severity_lower in ["info", "note", "style"]:
            return Severity.INFO
        else:
            return Severity.MEDIUM  # Default to medium if unknown

    def map_category(self, rule_id: str, message: str) -> FindingCategory:
        """
        Determine finding category based on rule ID and message.

        Args:
            rule_id: Rule identifier
            message: Finding message

        Returns:
            FindingCategory enum value
        """
        rule_lower = rule_id.lower()
        msg_lower = message.lower()

        # Security-related
        if any(
            term in rule_lower or term in msg_lower
            for term in [
                "security",
                "sql",
                "injection",
                "xss",
                "csrf",
                "auth",
                "crypto",
                "password",
                "secret",
                "vulnerability",
                "cve",
            ]
        ):
            return FindingCategory.SECURITY

        # Performance-related
        if any(
            term in rule_lower or term in msg_lower
            for term in [
                "performance",
                "slow",
                "optimization",
                "efficiency",
                "loop",
                "algorithm",
                "complexity",
                "n+1",
            ]
        ):
            return FindingCategory.PERFORMANCE

        # Architecture-related
        if any(
            term in rule_lower or term in msg_lower
            for term in [
                "architecture",
                "design",
                "coupling",
                "cohesion",
                "dependency",
                "layer",
                "separation",
            ]
        ):
            return FindingCategory.ARCHITECTURE

        # Testing-related
        if any(
            term in rule_lower or term in msg_lower
            for term in ["test", "coverage", "assertion", "mock"]
        ):
            return FindingCategory.TESTING

        # Documentation-related
        if any(
            term in rule_lower or term in msg_lower
            for term in ["documentation", "docstring", "comment", "doc", "missing-doc"]
        ):
            return FindingCategory.DOCUMENTATION

        # Style-related
        if any(
            term in rule_lower or term in msg_lower
            for term in [
                "style",
                "format",
                "naming",
                "convention",
                "whitespace",
                "indent",
                "line-length",
            ]
        ):
            return FindingCategory.STYLE

        # Default to code quality
        return FindingCategory.CODE_QUALITY
