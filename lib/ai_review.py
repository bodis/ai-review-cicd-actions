"""
AI Review Engine - Execute AI-driven code reviews using Claude Code CLI.
"""
import os
import json
import subprocess
import time
from typing import List, Dict, Any, Optional
from pathlib import Path

from .models import Finding, Severity, FindingCategory, PRContext
from .injection import InjectionSystem


class AIReviewEngine:
    """Executes AI-driven code reviews using Claude Code CLI."""

    def __init__(self, project_root: str = ".", config: Optional[Dict[str, Any]] = None):
        """
        Initialize AI review engine.

        Args:
            project_root: Root directory of the project
            config: Configuration dictionary
        """
        self.project_root = Path(project_root)
        self.config = config or {}
        self.injection_system = InjectionSystem(config)

    def run_claude_review(
        self,
        prompt: str,
        max_retries: int = 3
    ) -> Dict[str, Any]:
        """
        Execute Claude Code with validation and retry logic.

        Args:
            prompt: The prompt to send to Claude
            max_retries: Maximum number of retry attempts

        Returns:
            Parsed JSON response from Claude
        """
        for attempt in range(max_retries):
            try:
                # Run Claude Code in non-interactive mode
                result = self._execute_claude_code(prompt)

                # Validate and parse JSON output
                validated_result = self._validate_json_output(result)

                return validated_result

            except json.JSONDecodeError as e:
                if attempt < max_retries - 1:
                    print(f"JSON validation failed (attempt {attempt + 1}/{max_retries}): {e}")
                    # Retry with correction prompt
                    prompt = self._build_correction_prompt(prompt, result, str(e))
                    time.sleep(1)  # Brief delay before retry
                else:
                    raise RuntimeError(f"Failed to get valid JSON after {max_retries} attempts")

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"AI review failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    raise

        raise RuntimeError("AI review failed after all retries")

    def _execute_claude_code(self, prompt: str) -> str:
        """
        Execute Claude Code CLI.

        Args:
            prompt: Prompt to send

        Returns:
            Raw output from Claude
        """
        # Write prompt to temporary file
        prompt_file = self.project_root / '.claude_prompt_temp.txt'
        try:
            with open(prompt_file, 'w') as f:
                f.write(prompt)

            # Execute Claude Code (this is a placeholder - actual implementation may vary)
            # In practice, you might use the Claude API directly
            result = subprocess.run(
                ['claude', '--yes', '--input', str(prompt_file)],
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.project_root)
            )

            if result.returncode != 0:
                raise RuntimeError(f"Claude Code failed: {result.stderr}")

            return result.stdout

        finally:
            # Clean up temp file
            if prompt_file.exists():
                prompt_file.unlink()

    def _validate_json_output(self, output: str) -> Dict[str, Any]:
        """
        Validate and parse JSON output from AI.

        Args:
            output: Raw output string

        Returns:
            Parsed JSON dictionary
        """
        # Try to extract JSON from output (may be wrapped in markdown code blocks)
        json_str = output.strip()

        # Remove markdown code fences if present
        if json_str.startswith('```json'):
            json_str = json_str[7:]  # Remove ```json
        if json_str.startswith('```'):
            json_str = json_str[3:]
        if json_str.endswith('```'):
            json_str = json_str[:-3]

        json_str = json_str.strip()

        # Parse JSON
        parsed = json.loads(json_str)

        # Validate schema
        required_fields = ['findings']
        for field in required_fields:
            if field not in parsed:
                raise ValueError(f"Missing required field: {field}")

        return parsed

    def _build_correction_prompt(
        self,
        original_prompt: str,
        failed_output: str,
        error: str
    ) -> str:
        """
        Build a prompt to correct malformed JSON output.

        Args:
            original_prompt: The original prompt
            failed_output: The output that failed validation
            error: Error message

        Returns:
            Correction prompt
        """
        return f"""
The previous response had a JSON formatting error: {error}

Original prompt:
{original_prompt}

Your previous response:
{failed_output}

Please provide a corrected response with valid JSON in this exact format:
{{
  "findings": [
    {{
      "file_path": "path/to/file",
      "line_number": 123,
      "severity": "critical|high|medium|low|info",
      "category": "security|performance|architecture|code_quality|testing|documentation|style",
      "message": "Description of the issue",
      "suggestion": "How to fix it"
    }}
  ]
}}
"""

    def build_review_prompt(
        self,
        aspect: Dict[str, Any],
        pr_context: PRContext,
        shared_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Build AI prompt with all injections.

        Args:
            aspect: Review aspect configuration
            pr_context: PR context
            shared_context: Context from previous reviews

        Returns:
            Complete prompt string
        """
        # Load base prompt template
        prompt_file = aspect.get('prompt_file')
        if not prompt_file:
            raise ValueError(f"No prompt_file specified for aspect: {aspect['name']}")

        prompt_path = self.project_root / prompt_file
        if not prompt_path.exists():
            raise FileNotFoundError(f"Prompt file not found: {prompt_path}")

        with open(prompt_path, 'r') as f:
            base_prompt = f.read()

        # Apply injections
        prompt = self.injection_system.inject_all(
            base_prompt,
            pr_context,
            shared_context
        )

        return prompt

    def parse_ai_findings(self, ai_response: Dict[str, Any]) -> List[Finding]:
        """
        Parse AI response into Finding objects.

        Args:
            ai_response: Parsed JSON response from AI

        Returns:
            List of Finding objects
        """
        findings = []

        for item in ai_response.get('findings', []):
            try:
                finding = Finding(
                    file_path=item.get('file_path', ''),
                    line_number=item.get('line_number'),
                    severity=Severity(item.get('severity', 'medium')),
                    category=FindingCategory(item.get('category', 'code_quality')),
                    message=item.get('message', ''),
                    suggestion=item.get('suggestion'),
                    tool='claude-ai',
                    rule_id=item.get('rule_id', 'ai-review')
                )
                findings.append(finding)
            except Exception as e:
                print(f"Warning: Failed to parse finding: {e}")
                continue

        return findings

    def run_review(
        self,
        aspect: Dict[str, Any],
        pr_context: PRContext,
        shared_context: Optional[Dict[str, Any]] = None
    ) -> List[Finding]:
        """
        Run a complete AI review for an aspect.

        Args:
            aspect: Review aspect configuration
            pr_context: PR context
            shared_context: Shared context from previous reviews

        Returns:
            List of findings
        """
        try:
            # Build prompt
            prompt = self.build_review_prompt(aspect, pr_context, shared_context)

            # Execute review
            ai_response = self.run_claude_review(prompt)

            # Parse findings
            findings = self.parse_ai_findings(ai_response)

            return findings

        except Exception as e:
            print(f"AI review failed for {aspect['name']}: {e}")
            return []
