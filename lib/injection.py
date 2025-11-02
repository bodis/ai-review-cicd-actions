"""
Injection System - Inject company and project-level rules into prompts.
"""
import os
import re
from typing import Dict, Any, Optional, List
from pathlib import Path

from .models import PRContext


class InjectionSystem:
    """Manages injection of company and project policies into AI prompts."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize injection system.

        Args:
            config: Configuration dictionary
        """
        self.config = config or {}

    def inject_all(
        self,
        base_prompt: str,
        pr_context: PRContext,
        shared_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Apply all injections to base prompt.

        Args:
            base_prompt: Base prompt template
            pr_context: PR context
            shared_context: Context from previous reviews

        Returns:
            Final prompt with all injections
        """
        prompt = base_prompt

        # 1. Inject company policies
        if '{COMPANY_POLICIES}' in prompt:
            policies = self._get_company_policies()
            prompt = prompt.replace('{COMPANY_POLICIES}', policies)

        # 2. Inject project context
        if '{PROJECT_CONTEXT}' in prompt:
            context = self._format_project_context()
            prompt = prompt.replace('{PROJECT_CONTEXT}', context)

        # 3. Inject project constraints
        if '{PROJECT_CONSTRAINTS}' in prompt:
            constraints = self._format_project_constraints()
            prompt = prompt.replace('{PROJECT_CONSTRAINTS}', constraints)

        # 4. Inject custom rules
        if '{CUSTOM_RULES}' in prompt:
            rules = self._format_custom_rules()
            prompt = prompt.replace('{CUSTOM_RULES}', rules)

        # 5. Inject PR content
        prompt = self._inject_pr_content(prompt, pr_context)

        # 6. Inject shared context from previous reviews
        if shared_context and '{SHARED_CONTEXT}' in prompt:
            context_text = self._format_shared_context(shared_context)
            prompt = prompt.replace('{SHARED_CONTEXT}', context_text)

        return prompt

    def _get_company_policies(self) -> str:
        """
        Load and format company policies.

        Returns:
            Formatted company policies text
        """
        company_policies = self.config.get('company_policies', {})

        if not company_policies:
            return "No company-specific policies configured."

        sections = []

        # Coding standards
        if 'coding_standards' in company_policies:
            sections.append("### Coding Standards\n")
            for lang, standards in company_policies['coding_standards'].items():
                sections.append(f"**{lang.upper()}:**")
                for standard in standards:
                    sections.append(f"- {standard}")
                sections.append("")

        # Security requirements
        if 'security_requirements' in company_policies:
            sections.append("### Security Requirements\n")
            for req in company_policies['security_requirements']:
                sections.append(f"- {req}")
            sections.append("")

        # Architectural rules
        if 'architectural_rules' in company_policies:
            sections.append("### Architectural Rules\n")
            for rule in company_policies['architectural_rules']:
                sections.append(f"- {rule}")
            sections.append("")

        # Documentation requirements
        if 'documentation_requirements' in company_policies:
            sections.append("### Documentation Requirements\n")
            for req in company_policies['documentation_requirements']:
                sections.append(f"- {req}")
            sections.append("")

        if not sections:
            return "No company-specific policies configured."

        header = "## Company-Wide Policies\n\n"
        header += "**IMPORTANT:** Verify compliance with these organization-wide standards. "
        header += "Flag any violations as HIGH severity.\n\n"

        return header + "\n".join(sections)

    def _format_project_context(self) -> str:
        """Format project context information."""
        project_context = self.config.get('project_context', {})

        if not project_context:
            return "No project context configured."

        lines = ["## Project Context\n"]

        if 'name' in project_context:
            lines.append(f"**Project Name:** {project_context['name']}")

        if 'architecture' in project_context:
            lines.append(f"**Architecture:** {project_context['architecture']}")

        if 'critical_paths' in project_context:
            paths = project_context['critical_paths']
            lines.append(f"\n**Critical Paths:** {', '.join(paths)}")
            lines.append("\n⚠️ Changes in critical paths require extra scrutiny.")

        if 'technology_stack' in project_context:
            stack = project_context['technology_stack']
            lines.append(f"\n**Tech Stack:** {', '.join(stack)}")

        return "\n".join(lines) + "\n"

    def _format_project_constraints(self) -> str:
        """Format project-specific constraints."""
        constraints = self.config.get('project_constraints', [])

        if not constraints:
            return "No project-specific constraints configured."

        lines = ["## Project-Specific Constraints\n"]
        lines.append("These constraints are specific to this project:\n")

        for constraint in constraints:
            lines.append(f"- {constraint}")

        return "\n".join(lines) + "\n"

    def _format_custom_rules(self) -> str:
        """Format custom pattern-based rules."""
        custom_rules = self.config.get('custom_rules', [])

        if not custom_rules:
            return ""

        lines = ["## Custom Pattern Rules\n"]
        lines.append("Check for these project-specific patterns:\n")

        for rule in custom_rules:
            pattern = rule.get('pattern', '')
            message = rule.get('message', '')
            severity = rule.get('severity', 'medium')

            lines.append(f"\n**Pattern:** `{pattern}`")
            lines.append(f"**Severity:** {severity}")
            lines.append(f"**Message:** {message}")

        return "\n".join(lines) + "\n"

    def _inject_pr_content(self, prompt: str, pr_context: PRContext) -> str:
        """
        Inject PR-specific content into prompt.

        Args:
            prompt: Prompt template
            pr_context: PR context

        Returns:
            Prompt with PR content injected
        """
        # Replace PR metadata
        replacements = {
            '{PR_NUMBER}': str(pr_context.pr_number),
            '{PR_TITLE}': pr_context.title,
            '{PR_DESCRIPTION}': pr_context.description or "No description provided",
            '{PR_AUTHOR}': pr_context.author,
            '{BASE_BRANCH}': pr_context.base_branch,
            '{HEAD_BRANCH}': pr_context.head_branch,
        }

        for placeholder, value in replacements.items():
            prompt = prompt.replace(placeholder, value)

        # Replace changed files
        if '{CHANGED_FILES}' in prompt:
            files_text = self._format_changed_files(pr_context)
            prompt = prompt.replace('{CHANGED_FILES}', files_text)

        # Replace diff
        if '{PR_DIFF}' in prompt:
            # Limit diff size to prevent token overflow
            diff = pr_context.diff
            max_diff_size = 50000  # characters
            if len(diff) > max_diff_size:
                diff = diff[:max_diff_size] + "\n\n... (diff truncated for size)"
            prompt = prompt.replace('{PR_DIFF}', diff)

        # Replace detected languages
        if '{LANGUAGES}' in prompt:
            langs = ', '.join(pr_context.detected_languages) or 'Not detected'
            prompt = prompt.replace('{LANGUAGES}', langs)

        # Replace change types
        if '{CHANGE_TYPES}' in prompt:
            types = ', '.join([ct.value for ct in pr_context.change_types])
            prompt = prompt.replace('{CHANGE_TYPES}', types)

        return prompt

    def _format_changed_files(self, pr_context: PRContext) -> str:
        """Format changed files list."""
        lines = ["### Changed Files\n"]

        for file_change in pr_context.changed_files:
            status_emoji = {
                'added': '✨',
                'modified': '📝',
                'deleted': '🗑️',
                'renamed': '🔄'
            }.get(file_change.status, '•')

            lines.append(
                f"{status_emoji} `{file_change.path}` "
                f"(+{file_change.additions}/-{file_change.deletions})"
            )

        return "\n".join(lines)

    def _format_shared_context(self, shared_context: Dict[str, Any]) -> str:
        """
        Format shared context from previous reviews.

        Args:
            shared_context: Context dictionary from previous reviews

        Returns:
            Formatted context text
        """
        if not shared_context:
            return "No prior review context available."

        lines = ["## Context from Previous Reviews\n"]

        for aspect_name, context in shared_context.items():
            findings = context.get('findings', [])
            if findings:
                lines.append(f"\n### {aspect_name}")
                lines.append(f"Found {len(findings)} issues:")

                # Show top 3 findings
                for finding in findings[:3]:
                    lines.append(f"- [{finding.severity.value}] {finding.message}")

        return "\n".join(lines) + "\n"

    def inject_company_policies(self, prompt: str, policies: Dict[str, Any]) -> str:
        """
        Inject company policies into prompt.

        Args:
            prompt: Base prompt
            policies: Company policies dictionary

        Returns:
            Prompt with policies injected
        """
        policies_text = self._format_policies(policies)

        if '{COMPANY_POLICIES}' in prompt:
            return prompt.replace('{COMPANY_POLICIES}', policies_text)

        # If no placeholder, append to end
        return prompt + "\n\n" + policies_text

    def inject_project_constraints(
        self,
        prompt: str,
        constraints: List[str]
    ) -> str:
        """
        Inject project constraints into prompt.

        Args:
            prompt: Base prompt
            constraints: List of constraint strings

        Returns:
            Prompt with constraints injected
        """
        constraints_text = "\n".join(f"- {c}" for c in constraints)
        constraint_section = f"\n## Project Constraints\n{constraints_text}\n"

        if '{PROJECT_CONSTRAINTS}' in prompt:
            return prompt.replace('{PROJECT_CONSTRAINTS}', constraint_section)

        return prompt + "\n" + constraint_section

    def _format_policies(self, policies: Dict[str, Any]) -> str:
        """Format policies dictionary into readable text."""
        lines = ["## Company Policies\n"]

        for category, items in policies.items():
            category_title = category.replace('_', ' ').title()
            lines.append(f"\n### {category_title}")

            if isinstance(items, list):
                for item in items:
                    lines.append(f"- {item}")
            elif isinstance(items, dict):
                for key, value in items.items():
                    if isinstance(value, list):
                        lines.append(f"\n**{key}:**")
                        for v in value:
                            lines.append(f"  - {v}")

        return "\n".join(lines)
