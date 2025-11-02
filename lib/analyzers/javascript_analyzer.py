"""
JavaScript/TypeScript static analysis using ESLint, Prettier, and TSC.
"""
import json
import re
from typing import Any

from ..models import Finding, FindingCategory, Severity
from .base_analyzer import BaseAnalyzer


class JavaScriptAnalyzer(BaseAnalyzer):
    """Analyzes JavaScript/TypeScript code."""

    def __init__(self, project_root: str = ".", tools: list[str] | None = None):
        """
        Initialize JavaScript analyzer.

        Args:
            project_root: Root directory of the project
            tools: List of tools to use (default: all available)
        """
        super().__init__(project_root)
        self.tools = tools or ['eslint', 'prettier', 'tsc']

    def get_tool_name(self) -> str:
        """Get the name of the analysis tool."""
        return "JavaScript/TypeScript Static Analysis"

    def is_available(self) -> bool:
        """Check if JavaScript analysis tools are available."""
        # Check for node_modules or global installations
        for tool in self.tools:
            try:
                if tool == 'tsc':
                    result = self.run_command(['npx', 'tsc', '--version'])
                else:
                    result = self.run_command(['npx', tool, '--version'])

                if result.returncode == 0:
                    return True
            except RuntimeError:
                continue

        return False

    def run_analysis(self, files: list[str]) -> list[Finding]:
        """
        Run JavaScript/TypeScript analysis on specified files.

        Args:
            files: List of file paths to analyze

        Returns:
            List of findings
        """
        # Filter for JS/TS files
        js_files = self.filter_files_by_extension(
            files,
            ['.js', '.jsx', '.ts', '.tsx', '.mjs', '.cjs']
        )

        if not js_files:
            return []

        all_findings = []

        # Run each tool
        for tool in self.tools:
            try:
                if tool == 'eslint':
                    findings = self._run_eslint(js_files)
                elif tool == 'prettier':
                    findings = self._run_prettier(js_files)
                elif tool == 'tsc':
                    findings = self._run_tsc()
                else:
                    continue

                all_findings.extend(findings)
            except Exception as e:
                print(f"Warning: {tool} analysis failed: {e}")
                continue

        return all_findings

    def _run_eslint(self, files: list[str]) -> list[Finding]:
        """Run ESLint."""
        try:
            result = self.run_command(
                ['npx', 'eslint', '--format=json'] + files
            )

            # ESLint returns exit code 1 if issues found
            if not result.stdout:
                return []

            raw_output = json.loads(result.stdout)
            findings = []

            for file_result in raw_output:
                file_path = file_result.get('filePath', '')
                for message in file_result.get('messages', []):
                    message['filePath'] = file_path
                    finding = self._convert_eslint_result(message)
                    if finding:
                        findings.append(finding)

            return findings

        except Exception as e:
            print(f"ESLint analysis failed: {e}")
            return []

    def _run_prettier(self, files: list[str]) -> list[Finding]:
        """Run Prettier format checker."""
        try:
            result = self.run_command(
                ['npx', 'prettier', '--check'] + files
            )

            # Prettier returns 0 if all files formatted, 1 if some need formatting
            findings = []

            # Parse output to find unformatted files
            for line in result.stderr.splitlines():
                match = re.search(r'(.+\.(?:js|jsx|ts|tsx))', line)
                if match:
                    file_path = match.group(1)
                    findings.append(Finding(
                        file_path=file_path,
                        line_number=None,
                        severity=Severity.INFO,
                        category=FindingCategory.STYLE,
                        message="File is not formatted according to Prettier rules",
                        suggestion="Run 'prettier --write' to format this file",
                        tool='prettier',
                        rule_id='prettier/formatting'
                    ))

            return findings

        except Exception as e:
            print(f"Prettier check failed: {e}")
            return []

    def _run_tsc(self) -> list[Finding]:
        """Run TypeScript compiler for type checking."""
        try:
            # Check if tsconfig.json exists
            tsconfig_path = self.project_root / 'tsconfig.json'
            if not tsconfig_path.exists():
                return []

            result = self.run_command(
                ['npx', 'tsc', '--noEmit', '--pretty', 'false']
            )

            # Parse TSC output
            findings = []
            for line in result.stdout.splitlines():
                finding = self._parse_tsc_line(line)
                if finding:
                    findings.append(finding)

            return findings

        except Exception as e:
            print(f"TypeScript compilation check failed: {e}")
            return []

    def _parse_tsc_line(self, line: str) -> Finding | None:
        """Parse a single TypeScript compiler output line."""
        # Format: file.ts(line,col): error TSxxxx: message
        pattern = r'^(.+?)\((\d+),\d+\):\s*(\w+)\s+(TS\d+):\s*(.+)$'
        match = re.match(pattern, line)

        if not match:
            return None

        file_path, line_num, severity, code, message = match.groups()

        # Map TSC severity
        if severity.lower() == 'error':
            sev = Severity.HIGH
        elif severity.lower() == 'warning':
            sev = Severity.MEDIUM
        else:
            sev = Severity.INFO

        return Finding(
            file_path=file_path,
            line_number=int(line_num),
            severity=sev,
            category=FindingCategory.CODE_QUALITY,
            message=message,
            tool='tsc',
            rule_id=code
        )

    def _convert_to_finding(
        self,
        raw_result: dict[str, Any],
        tool_name: str
    ) -> Finding | None:
        """
        Convert tool-specific result to Finding.

        Args:
            raw_result: Raw result from tool
            tool_name: Name of the tool

        Returns:
            Finding object or None
        """
        if tool_name == 'eslint':
            return self._convert_eslint_result(raw_result)
        else:
            return None

    def _convert_eslint_result(self, result: dict[str, Any]) -> Finding | None:
        """Convert ESLint result to Finding."""
        severity_map = {
            2: Severity.HIGH,     # Error
            1: Severity.MEDIUM,   # Warning
            0: Severity.INFO      # Off/Info
        }

        severity_level = result.get('severity', 1)
        severity = severity_map.get(severity_level, Severity.MEDIUM)

        rule_id = result.get('ruleId', '')
        message = result.get('message', '')

        # Enhance security severity for security-related rules
        if any(term in rule_id.lower() for term in [
            'security', 'xss', 'injection', 'eval', 'dangerous'
        ]):
            if severity == Severity.HIGH:
                severity = Severity.CRITICAL

        return Finding(
            file_path=result.get('filePath', ''),
            line_number=result.get('line'),
            severity=severity,
            category=self.map_category(rule_id, message),
            message=message,
            suggestion=result.get('fix', {}).get('text') if result.get('fix') else None,
            tool='eslint',
            rule_id=rule_id
        )
