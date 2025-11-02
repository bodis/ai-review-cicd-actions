"""
Java static analysis using SpotBugs, PMD, Checkstyle, and other tools.
Supports both free open-source tools and commercial solutions.
"""
import json
import re
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional
from pathlib import Path

from .base_analyzer import BaseAnalyzer
from ..models import Finding, Severity, FindingCategory


class JavaAnalyzer(BaseAnalyzer):
    """
    Analyzes Java code using multiple tools.

    Supported Free Tools:
    - SpotBugs: Bytecode analysis for bugs (400+ patterns)
    - PMD: Source code analysis for bugs and code smells
    - Checkstyle: Code style and standards enforcement
    - JaCoCo: Test coverage measurement
    - ArchUnit: Architecture rule testing
    - OWASP Dependency-Check: Dependency vulnerability scanning
    - Find Security Bugs: Security-focused SpotBugs plugin

    Supported Paid Tools (integration ready):
    - SonarQube/SonarCloud: Comprehensive SAST platform
    - Qodana: JetBrains IDE inspections for CI
    - Snyk: Dependency and code vulnerability scanning
    """

    # Free tools that can be run directly
    FREE_TOOLS = ['spotbugs', 'pmd', 'checkstyle', 'jacoco', 'archunit', 'owasp-dependency-check']

    # Paid tools (require external setup)
    PAID_TOOLS = ['sonarqube', 'sonarcloud', 'qodana', 'snyk']

    def __init__(
        self,
        project_root: str = ".",
        tools: Optional[List[str]] = None,
        build_tool: str = "auto"  # auto, maven, gradle
    ):
        """
        Initialize Java analyzer.

        Args:
            project_root: Root directory of the project
            tools: List of tools to use (default: free tools only)
            build_tool: Build tool to use (auto-detect by default)
        """
        super().__init__(project_root)
        self.tools = tools or self.FREE_TOOLS
        self.build_tool = self._detect_build_tool() if build_tool == "auto" else build_tool

    def get_tool_name(self) -> str:
        """Get the name of the analysis tool."""
        return "Java Static Analysis"

    def _detect_build_tool(self) -> str:
        """Detect the build tool used in the project."""
        if (self.project_root / "pom.xml").exists():
            return "maven"
        elif (self.project_root / "build.gradle").exists() or \
             (self.project_root / "build.gradle.kts").exists():
            return "gradle"
        return "maven"  # Default to maven

    def is_available(self) -> bool:
        """Check if Java analysis tools are available."""
        # Check if build tool is available
        try:
            if self.build_tool == "maven":
                result = self.run_command(['mvn', '--version'])
            elif self.build_tool == "gradle":
                result = self.run_command(['gradle', '--version'])
            else:
                return False

            return result.returncode == 0
        except RuntimeError:
            return False

    def run_analysis(self, files: List[str]) -> List[Finding]:
        """
        Run Java analysis on specified files.

        Args:
            files: List of file paths to analyze

        Returns:
            List of findings
        """
        # Filter for Java files
        java_files = self.filter_files_by_extension(files, ['.java'])

        if not java_files:
            return []

        all_findings = []

        # Run each configured tool
        for tool in self.tools:
            try:
                if tool == 'spotbugs':
                    findings = self._run_spotbugs()
                elif tool == 'pmd':
                    findings = self._run_pmd(java_files)
                elif tool == 'checkstyle':
                    findings = self._run_checkstyle(java_files)
                elif tool == 'jacoco':
                    findings = self._run_jacoco()
                elif tool == 'owasp-dependency-check':
                    findings = self._run_owasp_dependency_check()
                elif tool == 'archunit':
                    findings = self._run_archunit()
                elif tool in self.PAID_TOOLS:
                    findings = self._run_paid_tool(tool)
                else:
                    continue

                all_findings.extend(findings)
            except Exception as e:
                print(f"Warning: {tool} analysis failed: {e}")
                continue

        return all_findings

    def _run_spotbugs(self) -> List[Finding]:
        """
        Run SpotBugs analysis via Maven/Gradle.

        SpotBugs analyzes Java bytecode for 400+ bug patterns including:
        - Null pointer dereferences
        - Resource leaks
        - Concurrency issues
        - Bad practices
        """
        try:
            output_file = self.project_root / "target" / "spotbugsXml.xml"

            if self.build_tool == "maven":
                # Run SpotBugs via Maven plugin
                result = self.run_command([
                    'mvn', 'spotbugs:spotbugs',
                    '-Dspotbugs.xmlOutput=true',
                    f'-Dspotbugs.xmlOutputDirectory={output_file.parent}'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'spotbugsMain',
                    '-Pspotbugs.reportDir=' + str(output_file.parent)
                ])

            if not output_file.exists():
                return []

            # Parse SpotBugs XML report
            return self._parse_spotbugs_xml(output_file)

        except Exception as e:
            print(f"SpotBugs analysis failed: {e}")
            return []

    def _run_pmd(self, files: List[str]) -> List[Finding]:
        """
        Run PMD analysis.

        PMD performs source code analysis for:
        - Possible bugs
        - Suboptimal code
        - Overcomplicated expressions
        - Duplicate code (via CPD)
        """
        try:
            output_file = self.project_root / "target" / "pmd.xml"

            if self.build_tool == "maven":
                result = self.run_command([
                    'mvn', 'pmd:pmd',
                    f'-Dpmd.reportFormat=xml',
                    f'-Dpmd.outputDirectory={output_file.parent}'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'pmdMain',
                    f'-Ppmd.reportsDir={output_file.parent}'
                ])

            if not output_file.exists():
                return []

            return self._parse_pmd_xml(output_file)

        except Exception as e:
            print(f"PMD analysis failed: {e}")
            return []

    def _run_checkstyle(self, files: List[str]) -> List[Finding]:
        """
        Run Checkstyle analysis.

        Checkstyle enforces coding standards:
        - Naming conventions
        - Code formatting
        - Javadoc requirements
        - Brace usage
        """
        try:
            output_file = self.project_root / "target" / "checkstyle-result.xml"

            if self.build_tool == "maven":
                result = self.run_command([
                    'mvn', 'checkstyle:checkstyle',
                    f'-Dcheckstyle.output.file={output_file}'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'checkstyleMain',
                    f'-Pcheckstyle.reportsDir={output_file.parent}'
                ])

            if not output_file.exists():
                return []

            return self._parse_checkstyle_xml(output_file)

        except Exception as e:
            print(f"Checkstyle analysis failed: {e}")
            return []

    def _run_jacoco(self) -> List[Finding]:
        """
        Run JaCoCo coverage analysis.

        JaCoCo measures test coverage and can fail builds based on thresholds.
        """
        try:
            if self.build_tool == "maven":
                result = self.run_command([
                    'mvn', 'jacoco:report'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'jacocoTestReport'
                ])

            # Parse coverage report and generate findings for low coverage
            coverage_file = self.project_root / "target" / "site" / "jacoco" / "jacoco.xml"
            if coverage_file.exists():
                return self._parse_jacoco_xml(coverage_file)

            return []

        except Exception as e:
            print(f"JaCoCo analysis failed: {e}")
            return []

    def _run_owasp_dependency_check(self) -> List[Finding]:
        """
        Run OWASP Dependency-Check.

        Identifies known CVE vulnerabilities in project dependencies.
        Note: First run downloads NVD database (~500MB).
        """
        try:
            output_file = self.project_root / "target" / "dependency-check-report.json"

            if self.build_tool == "maven":
                result = self.run_command([
                    'mvn', 'dependency-check:check',
                    f'-DoutputDirectory={output_file.parent}',
                    '-Dformat=JSON'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'dependencyCheckAnalyze',
                    f'-Pdependency-check.outputDirectory={output_file.parent}'
                ])

            if not output_file.exists():
                return []

            return self._parse_dependency_check_json(output_file)

        except Exception as e:
            print(f"OWASP Dependency-Check failed: {e}")
            return []

    def _run_archunit(self) -> List[Finding]:
        """
        Run ArchUnit tests.

        ArchUnit tests architectural rules as JUnit tests.
        This runs as part of the test suite, so we check test results.
        """
        try:
            if self.build_tool == "maven":
                result = self.run_command([
                    'mvn', 'test',
                    '-Dtest=*ArchTest'
                ])
            else:  # gradle
                result = self.run_command([
                    'gradle', 'test',
                    '--tests', '*ArchTest'
                ])

            # Parse test results for architectural violations
            # ArchUnit failures show up in standard test reports
            return []  # Would need to parse surefire-reports

        except Exception as e:
            print(f"ArchUnit tests failed: {e}")
            return []

    def _run_paid_tool(self, tool: str) -> List[Finding]:
        """
        Placeholder for paid tool integration.

        Args:
            tool: Name of the paid tool (sonarqube, qodana, snyk, etc.)

        Returns:
            Empty list (actual integration requires external setup)
        """
        print(f"  ℹ️  {tool.upper()} integration available but requires external setup")
        print(f"     See documentation for {tool} configuration")
        return []

    def _parse_spotbugs_xml(self, xml_file: Path) -> List[Finding]:
        """Parse SpotBugs XML report."""
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for bug in root.findall('.//BugInstance'):
                priority = bug.get('priority', '2')
                severity = self._map_spotbugs_priority(priority)
                category = bug.get('category', 'CORRECTNESS')

                source_line = bug.find('.//SourceLine')
                if source_line is not None:
                    file_path = source_line.get('sourcepath', '')
                    line_number = int(source_line.get('start', 0))
                    message = bug.find('.//LongMessage')
                    message_text = message.text if message is not None else bug.get('type', '')

                    findings.append(Finding(
                        file_path=file_path,
                        line_number=line_number,
                        severity=severity,
                        category=self._map_spotbugs_category(category),
                        message=message_text,
                        tool='spotbugs',
                        rule_id=bug.get('type')
                    ))

        except Exception as e:
            print(f"Failed to parse SpotBugs XML: {e}")

        return findings

    def _parse_pmd_xml(self, xml_file: Path) -> List[Finding]:
        """Parse PMD XML report."""
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for file_elem in root.findall('.//file'):
                file_path = file_elem.get('name', '')

                for violation in file_elem.findall('.//violation'):
                    priority = int(violation.get('priority', 3))
                    severity = self._map_pmd_priority(priority)

                    findings.append(Finding(
                        file_path=file_path,
                        line_number=int(violation.get('beginline', 0)),
                        severity=severity,
                        category=self.map_category(
                            violation.get('rule', ''),
                            violation.text or ''
                        ),
                        message=violation.text.strip() if violation.text else '',
                        tool='pmd',
                        rule_id=violation.get('rule')
                    ))

        except Exception as e:
            print(f"Failed to parse PMD XML: {e}")

        return findings

    def _parse_checkstyle_xml(self, xml_file: Path) -> List[Finding]:
        """Parse Checkstyle XML report."""
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            for file_elem in root.findall('.//file'):
                file_path = file_elem.get('name', '')

                for error in file_elem.findall('.//error'):
                    severity_str = error.get('severity', 'warning')
                    severity = self._map_checkstyle_severity(severity_str)

                    findings.append(Finding(
                        file_path=file_path,
                        line_number=int(error.get('line', 0)),
                        severity=severity,
                        category=FindingCategory.STYLE,  # Checkstyle is primarily style
                        message=error.get('message', ''),
                        tool='checkstyle',
                        rule_id=error.get('source', '').split('.')[-1]
                    ))

        except Exception as e:
            print(f"Failed to parse Checkstyle XML: {e}")

        return findings

    def _parse_jacoco_xml(self, xml_file: Path) -> List[Finding]:
        """Parse JaCoCo coverage XML report."""
        findings = []
        try:
            tree = ET.parse(xml_file)
            root = tree.getroot()

            # Look for packages/classes with low coverage
            for package in root.findall('.//package'):
                package_name = package.get('name', '')

                for class_elem in package.findall('.//class'):
                    class_name = class_elem.get('name', '')
                    source_file = class_elem.get('sourcefilename', '')

                    # Calculate coverage percentages
                    line_counter = class_elem.find(".//counter[@type='LINE']")
                    if line_counter is not None:
                        covered = int(line_counter.get('covered', 0))
                        missed = int(line_counter.get('missed', 0))
                        total = covered + missed

                        if total > 0:
                            coverage = (covered / total) * 100

                            # Flag low coverage
                            if coverage < 80:
                                severity = Severity.MEDIUM if coverage < 50 else Severity.LOW

                                findings.append(Finding(
                                    file_path=f"{package_name}/{source_file}",
                                    line_number=None,
                                    severity=severity,
                                    category=FindingCategory.TESTING,
                                    message=f"Low test coverage: {coverage:.1f}% ({covered}/{total} lines covered)",
                                    suggestion=f"Add tests to increase coverage above 80%",
                                    tool='jacoco'
                                ))

        except Exception as e:
            print(f"Failed to parse JaCoCo XML: {e}")

        return findings

    def _parse_dependency_check_json(self, json_file: Path) -> List[Finding]:
        """Parse OWASP Dependency-Check JSON report."""
        findings = []
        try:
            with open(json_file, 'r') as f:
                data = json.load(f)

            for dependency in data.get('dependencies', []):
                file_name = dependency.get('fileName', '')
                vulnerabilities = dependency.get('vulnerabilities', [])

                for vuln in vulnerabilities:
                    severity_str = vuln.get('severity', 'MEDIUM')
                    severity = self._map_cvss_severity(severity_str)

                    cve_id = vuln.get('name', '')
                    description = vuln.get('description', '')

                    findings.append(Finding(
                        file_path=file_name,
                        line_number=None,
                        severity=severity,
                        category=FindingCategory.SECURITY,
                        message=f"{cve_id}: {description}",
                        suggestion=f"Update dependency to fix {cve_id}",
                        tool='owasp-dependency-check',
                        rule_id=cve_id
                    ))

        except Exception as e:
            print(f"Failed to parse OWASP Dependency-Check JSON: {e}")

        return findings

    def _map_spotbugs_priority(self, priority: str) -> Severity:
        """Map SpotBugs priority to severity."""
        priority_map = {
            '1': Severity.HIGH,     # High priority
            '2': Severity.MEDIUM,   # Medium priority
            '3': Severity.LOW,      # Low priority
        }
        return priority_map.get(priority, Severity.MEDIUM)

    def _map_pmd_priority(self, priority: int) -> Severity:
        """Map PMD priority (1-5) to severity."""
        if priority <= 2:
            return Severity.HIGH
        elif priority == 3:
            return Severity.MEDIUM
        else:
            return Severity.LOW

    def _map_checkstyle_severity(self, severity: str) -> Severity:
        """Map Checkstyle severity to standard severity."""
        severity_map = {
            'error': Severity.HIGH,
            'warning': Severity.MEDIUM,
            'info': Severity.LOW
        }
        return severity_map.get(severity.lower(), Severity.MEDIUM)

    def _map_cvss_severity(self, severity: str) -> Severity:
        """Map CVSS severity to standard severity."""
        severity_map = {
            'CRITICAL': Severity.CRITICAL,
            'HIGH': Severity.HIGH,
            'MEDIUM': Severity.MEDIUM,
            'LOW': Severity.LOW
        }
        return severity_map.get(severity.upper(), Severity.MEDIUM)

    def _map_spotbugs_category(self, category: str) -> FindingCategory:
        """Map SpotBugs category to finding category."""
        category_map = {
            'SECURITY': FindingCategory.SECURITY,
            'PERFORMANCE': FindingCategory.PERFORMANCE,
            'CORRECTNESS': FindingCategory.CODE_QUALITY,
            'BAD_PRACTICE': FindingCategory.CODE_QUALITY,
            'STYLE': FindingCategory.STYLE,
            'MT_CORRECTNESS': FindingCategory.CODE_QUALITY,  # Multi-threading
        }
        return category_map.get(category, FindingCategory.CODE_QUALITY)

    def _convert_to_finding(
        self,
        raw_result: Dict[str, Any],
        tool_name: str
    ) -> Optional[Finding]:
        """Convert tool-specific result to Finding."""
        # This is handled by specific parsers above
        return None
