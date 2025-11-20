"""
Python static analysis using Ruff, Pylint, Bandit, and mypy.
"""

import json
import re
from typing import Any

from ..models import Finding, FindingCategory, Severity
from .base_analyzer import BaseAnalyzer


class PythonAnalyzer(BaseAnalyzer):
    """Analyzes Python code using multiple tools."""

    def __init__(self, project_root: str = ".", tools: list[str] | None = None):
        """
        Initialize Python analyzer.

        Args:
            project_root: Root directory of the project
            tools: List of tools to use (default: all available)
        """
        super().__init__(project_root)
        self.tools = tools or ["ruff", "pylint", "bandit", "mypy"]

    def get_tool_name(self) -> str:
        """Get the name of the analysis tool."""
        return "Python Static Analysis"

    def is_available(self) -> bool:
        """Check if Python analysis tools are available."""
        available_tools = []
        for tool in self.tools:
            try:
                result = self.run_command([tool, "--version"])
                if result.returncode == 0:
                    available_tools.append(tool)
            except RuntimeError:
                pass

        return len(available_tools) > 0

    def run_analysis(self, files: list[str]) -> list[Finding]:
        """
        Run Python analysis on specified files.

        Args:
            files: List of file paths to analyze

        Returns:
            List of findings
        """
        # Filter for Python files
        python_files = self.filter_files_by_extension(files, [".py"])

        if not python_files:
            return []

        all_findings = []

        # Run each tool
        for tool in self.tools:
            try:
                if tool == "ruff":
                    findings = self._run_ruff(python_files)
                elif tool == "pylint":
                    findings = self._run_pylint(python_files)
                elif tool == "bandit":
                    findings = self._run_bandit(python_files)
                elif tool == "mypy":
                    findings = self._run_mypy(python_files)
                else:
                    continue

                all_findings.extend(findings)
            except Exception as e:
                print(f"Warning: {tool} analysis failed: {e}")
                continue

        return all_findings

    def _run_ruff(self, files: list[str]) -> list[Finding]:
        """Run Ruff linter."""
        try:
            result = self.run_command(["ruff", "check", "--output-format=json"] + files)

            # Ruff returns exit code 1 if issues found, which is expected
            if result.returncode not in [0, 1]:
                return []

            if not result.stdout:
                return []

            raw_results = json.loads(result.stdout)
            return self.standardize_results(raw_results, "ruff")

        except Exception as e:
            print(f"Ruff analysis failed: {e}")
            return []

    def _run_pylint(self, files: list[str]) -> list[Finding]:
        """Run Pylint."""
        try:
            result = self.run_command(["pylint", "--output-format=json"] + files)

            # Pylint returns non-zero on issues, which is expected
            if not result.stdout:
                return []

            raw_results = json.loads(result.stdout)
            return self.standardize_results(raw_results, "pylint")

        except Exception as e:
            print(f"Pylint analysis failed: {e}")
            return []

    def _run_bandit(self, files: list[str]) -> list[Finding]:
        """Run Bandit security scanner."""
        try:
            result = self.run_command(["bandit", "-f", "json", "-r"] + files)

            # Bandit returns non-zero on issues
            if not result.stdout:
                return []

            raw_output = json.loads(result.stdout)
            raw_results = raw_output.get("results", [])
            return self.standardize_results(raw_results, "bandit")

        except Exception as e:
            print(f"Bandit analysis failed: {e}")
            return []

    def _run_mypy(self, files: list[str]) -> list[Finding]:
        """Run mypy type checker."""
        try:
            result = self.run_command(
                ["mypy", "--no-error-summary", "--show-column-numbers"] + files
            )

            # Parse text output
            findings = []
            for line in result.stdout.splitlines():
                finding = self._parse_mypy_line(line)
                if finding:
                    findings.append(finding)

            return findings

        except Exception as e:
            print(f"Mypy analysis failed: {e}")
            return []

    def _parse_mypy_line(self, line: str) -> Finding | None:
        """Parse a single mypy output line."""
        # Format: file.py:line:col: error: message
        pattern = r"^(.+?):(\d+):(?:\d+:)?\s*(\w+):\s*(.+)$"
        match = re.match(pattern, line)

        if not match:
            return None

        file_path, line_num, severity, message = match.groups()

        # Map mypy severity
        if severity.lower() == "error":
            sev = Severity.HIGH
        elif severity.lower() == "warning":
            sev = Severity.MEDIUM
        else:
            sev = Severity.INFO

        return Finding(
            file_path=file_path,
            line_number=int(line_num),
            severity=sev,
            category=FindingCategory.CODE_QUALITY,
            message=message,
            tool="mypy",
            rule_id=f"mypy-{severity}",
        )

    def _convert_to_finding(self, raw_result: dict[str, Any], tool_name: str) -> Finding | None:
        """
        Convert tool-specific result to Finding.

        Args:
            raw_result: Raw result from tool
            tool_name: Name of the tool

        Returns:
            Finding object or None
        """
        if tool_name == "ruff":
            return self._convert_ruff_result(raw_result)
        elif tool_name == "pylint":
            return self._convert_pylint_result(raw_result)
        elif tool_name == "bandit":
            return self._convert_bandit_result(raw_result)
        else:
            return None

    def _convert_ruff_result(self, result: dict[str, Any]) -> Finding | None:
        """Convert Ruff result to Finding."""
        severity_map = {
            "E": Severity.HIGH,  # Error
            "W": Severity.MEDIUM,  # Warning
            "F": Severity.HIGH,  # Pyflakes
            "C": Severity.LOW,  # Convention
            "N": Severity.INFO,  # Naming
            "D": Severity.INFO,  # Docstring
            "I": Severity.INFO,  # Import
        }

        code = result.get("code", "")
        severity = severity_map.get(code[0] if code else "W", Severity.MEDIUM)

        return Finding(
            file_path=result.get("filename", ""),
            line_number=result.get("location", {}).get("row"),
            severity=severity,
            category=self.map_category(code, result.get("message", "")),
            message=result.get("message", ""),
            tool="ruff",
            rule_id=code,
        )

    def _convert_pylint_result(self, result: dict[str, Any]) -> Finding | None:
        """Convert Pylint result to Finding."""
        severity_map = {
            "fatal": Severity.CRITICAL,
            "error": Severity.HIGH,
            "warning": Severity.MEDIUM,
            "convention": Severity.LOW,
            "refactor": Severity.LOW,
            "info": Severity.INFO,
        }

        msg_type = result.get("type", "warning")
        severity = severity_map.get(msg_type, Severity.MEDIUM)

        return Finding(
            file_path=result.get("path", ""),
            line_number=result.get("line"),
            severity=severity,
            category=self.map_category(result.get("symbol", ""), result.get("message", "")),
            message=result.get("message", ""),
            suggestion=None,
            tool="pylint",
            rule_id=result.get("symbol"),
        )

    def _convert_bandit_result(self, result: dict[str, Any]) -> Finding | None:
        """Convert Bandit result to Finding."""
        severity_map = {"HIGH": Severity.CRITICAL, "MEDIUM": Severity.HIGH, "LOW": Severity.MEDIUM}

        issue_severity = result.get("issue_severity", "MEDIUM")
        severity = severity_map.get(issue_severity, Severity.MEDIUM)

        return Finding(
            file_path=result.get("filename", ""),
            line_number=result.get("line_number"),
            severity=severity,
            category=FindingCategory.SECURITY,  # Bandit is security-focused
            message=result.get("issue_text", ""),
            suggestion=None,
            tool="bandit",
            rule_id=result.get("test_id"),
            code_snippet=result.get("code"),
        )
