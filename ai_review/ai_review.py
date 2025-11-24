"""
AI Review Engine - Execute AI-driven code reviews using Claude Code CLI.
"""

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from .injection import InjectionSystem
from .models import Finding, FindingCategory, Metrics, PRContext, Severity


class AIReviewEngine:
    """Executes AI-driven code reviews using Claude Code CLI."""

    def __init__(
        self,
        project_root: str = ".",
        config: dict[str, Any] | None = None,
        metrics: Metrics | None = None,
    ):
        """
        Initialize AI review engine.

        Args:
            project_root: Root directory of the project
            config: Configuration dictionary
            metrics: Metrics object for tracking token usage
        """
        self.project_root = Path(project_root)
        self.config = config or {}
        self.injection_system = InjectionSystem(config)
        self.metrics = metrics  # Optional metrics tracking

    def run_claude_review(self, prompt: str, max_retries: int | None = None) -> dict[str, Any]:
        """
        Execute Claude Code with validation and retry logic.

        Args:
            prompt: The prompt to send to Claude
            max_retries: Maximum number of retry attempts (default from config)

        Returns:
            Parsed JSON response from Claude
        """
        # Use config value if not specified
        if max_retries is None:
            max_retries = self.config.get("performance", {}).get("ai_review_max_retries", 1)

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
                    raise RuntimeError(
                        f"Failed to get valid JSON after {max_retries} attempts"
                    ) from e

            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"AI review failed (attempt {attempt + 1}/{max_retries}): {e}")
                    time.sleep(2)
                else:
                    raise

        raise RuntimeError("AI review failed after all retries")

    def _execute_claude_code(self, prompt: str) -> str:
        """
        Execute Claude Code CLI in non-interactive mode for CI/CD.

        Args:
            prompt: The review prompt to send to Claude

        Returns:
            JSON string with findings

        Raises:
            RuntimeError: If Claude Code fails or times out
            FileNotFoundError: If Claude Code CLI is not installed
        """
        try:
            # Debug: Save prompt to debug file if enabled
            if os.getenv("DEBUG_AI_PROMPTS"):
                debug_file = self.project_root / f".claude_debug_{int(time.time())}.txt"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(prompt)
                print(f"   🐛 Debug prompt saved to: {debug_file}")

            # Build command with debug flags if enabled
            claude_cmd = [
                "claude",
                "-p",
                prompt,  # Pass prompt directly via -p flag
                "--output-format",
                "json",  # Structured output
                "--dangerously-skip-permissions",  # Skip permission prompts in CI
            ]

            # Add verbose flag for debugging
            if os.getenv("DEBUG_AI_PROMPTS"):
                claude_cmd.append("--verbose")
                print("   🐛 Debug mode enabled, using --verbose flag")

            # Execute Claude Code with proper CI/CD flags
            result = subprocess.run(
                claude_cmd,
                capture_output=True,
                text=True,
                timeout=300,  # 5 minute timeout
                cwd=str(self.project_root),
                env={
                    **os.environ,
                    "ANTHROPIC_API_KEY": os.getenv("ANTHROPIC_API_KEY"),
                    "CLAUDE_CODE_HEADLESS": "1",  # Disable interactive features
                    "NO_COLOR": "1",  # Disable ANSI color codes
                },
            )

            if result.returncode != 0:
                stderr = result.stderr or "No error output"
                raise RuntimeError(
                    f"Claude Code CLI failed with exit code {result.returncode}\n"
                    f"Error: {stderr}\n"
                    f"Output: {result.stdout[:500]}"
                )

            # Extract and log token usage from stderr
            usage_info = self._extract_token_usage(result.stderr)
            if usage_info:
                print(f"📊 Tokens: {usage_info['input']} in, {usage_info['output']} out")
                print(f"💰 Cost: ${usage_info['cost']:.4f}")

                # Track in metrics if available
                if self.metrics:
                    self.metrics.add_tokens(
                        usage_info["input"], usage_info["output"], usage_info.get("cache", 0)
                    )

            # Debug: Log raw output for investigation
            if not result.stdout or len(result.stdout.strip()) < 10:
                print(
                    f"⚠️ Warning: Claude Code returned minimal output ({len(result.stdout)} chars)"
                )
                print(f"   Stdout preview: {result.stdout[:200]}")
                print(f"   Stderr preview: {result.stderr[:200]}")

            return result.stdout

        except subprocess.TimeoutExpired as e:
            raise RuntimeError(
                "Claude Code CLI timed out after 300s. "
                "Consider reducing prompt size or increasing timeout."
            ) from e
        except FileNotFoundError as e:
            raise RuntimeError(
                "Claude Code CLI not found in PATH. "
                "Install: npm install -g @anthropic-ai/claude-code"
            ) from e

    def _validate_json_output(self, output: str) -> dict[str, Any]:
        """
        Validate and parse JSON output from AI.

        Handles two formats:
        1. Claude Code CLI JSON wrapper: {"content": [{"text": "..."}]}
        2. Direct Claude response with JSON

        Args:
            output: Raw output string

        Returns:
            Parsed JSON dictionary
        """
        json_str = output.strip()

        # Debug: Show what we received
        if len(json_str) < 200:
            print(f"   📥 Raw output ({len(json_str)} chars): {json_str}")
        else:
            print(f"   📥 Output length: {len(json_str)} chars")
            print(f"   📥 First 200 chars: {json_str[:200]}")
            print(f"   📥 Last 100 chars: {json_str[-100:]}")

        # If output is empty, return empty findings
        if not json_str or json_str in ["OK", "ok", "Ok"]:
            print("   ⚠️ No output received, returning empty findings")
            return {"findings": []}

        # Try to parse as JSON first (might be CLI wrapper)
        try:
            parsed = json.loads(json_str)

            # Check if it's Claude Code CLI JSON wrapper format
            if isinstance(parsed, dict):
                # Format 1a: CLI wrapper with "result" field (newer CLI format)
                if "result" in parsed and isinstance(parsed["result"], str):
                    print("   🔍 Detected CLI JSON wrapper (result field), extracting content...")
                    claude_text = parsed["result"]
                    print(f"   📝 Extracted Claude response ({len(claude_text)} chars)")
                    # Recursively parse the extracted text
                    return self._parse_claude_response(claude_text)

                # Format 1b: CLI wrapper with content array (older format)
                if "content" in parsed and isinstance(parsed["content"], list):
                    print("   🔍 Detected CLI JSON wrapper (content array), extracting content...")
                    # Extract text from first content block
                    if len(parsed["content"]) > 0 and "text" in parsed["content"][0]:
                        claude_text = parsed["content"][0]["text"]
                        print(f"   📝 Extracted Claude response ({len(claude_text)} chars)")
                        # Recursively parse the extracted text
                        return self._parse_claude_response(claude_text)

                # Format 2: Direct findings object
                if "findings" in parsed:
                    print(f"   ✅ Direct findings object with {len(parsed['findings'])} findings")
                    return parsed

            # Format 3: List of findings
            if isinstance(parsed, list):
                print(f"   ✅ Direct findings list with {len(parsed)} findings, wrapping in object")
                return {"findings": parsed}

        except json.JSONDecodeError:
            # Not valid JSON, might be text with JSON inside
            print("   ⚠️ Not valid JSON, attempting to extract JSON from text...")
            pass

        # Try to extract JSON from text (markdown code blocks, etc.)
        return self._parse_claude_response(json_str)

    def _parse_claude_response(self, text: str) -> dict[str, Any]:
        """
        Parse Claude's text response, extracting JSON from markdown code blocks if needed.

        Args:
            text: Claude's response text

        Returns:
            Parsed findings dictionary
        """
        json_str = text.strip()

        # Remove markdown code fences if present
        if json_str.startswith("```json"):
            json_str = json_str[7:]  # Remove ```json
        elif json_str.startswith("```"):
            json_str = json_str[3:]

        if json_str.endswith("```"):
            json_str = json_str[:-3]

        json_str = json_str.strip()

        # Try to find JSON object in text
        import re

        json_match = re.search(r'\{[\s\S]*"findings"[\s\S]*\}', json_str)
        if json_match:
            json_str = json_match.group(0)
            print(f"   🔍 Extracted JSON block from text ({len(json_str)} chars)")

        # Parse JSON
        try:
            parsed = json.loads(json_str)
        except json.JSONDecodeError as e:
            print(f"   ❌ JSON parse error: {e}")
            print(f"   📄 Attempted to parse: {json_str[:300]}")
            raise

        # Validate schema
        if isinstance(parsed, list):
            print(f"   ✅ Findings list with {len(parsed)} items, wrapping in object")
            return {"findings": parsed}

        if isinstance(parsed, dict) and "findings" in parsed:
            print(f"   ✅ Findings object with {len(parsed['findings'])} findings")
            return parsed

        raise ValueError("Missing required field 'findings' in response")

    def _build_correction_prompt(self, original_prompt: str, failed_output: str, error: str) -> str:
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
        aspect: dict[str, Any],
        pr_context: PRContext,
        shared_context: dict[str, Any] | None = None,
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
        # Load base prompt template (with fallback to bundled prompts)
        prompt_file = aspect.get("prompt_file")
        if not prompt_file:
            raise ValueError(f"No prompt_file specified for aspect: {aspect['name']}")

        # Use resource loader to find prompt (project override → bundled)
        from .resources import get_prompt

        try:
            base_prompt = get_prompt(prompt_file, self.project_root)
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Prompt file not found: {prompt_file}\n"
                f"Checked: project/prompts/, .github/prompts/, .gitlab/prompts/, and bundled prompts."
            ) from e

        # Apply injections
        prompt = self.injection_system.inject_all(base_prompt, pr_context, shared_context)

        return prompt

    def parse_ai_findings(
        self, ai_response: dict[str, Any], aspect_name: str | None = None
    ) -> list[Finding]:
        """
        Parse AI response into Finding objects.

        Args:
            ai_response: Parsed JSON response from AI
            aspect_name: Name of the review aspect (e.g., "security_review")

        Returns:
            List of Finding objects
        """
        findings = []

        for item in ai_response.get("findings", []):
            try:
                finding = Finding(
                    file_path=item.get("file_path", ""),
                    line_number=item.get("line_number"),
                    severity=Severity(item.get("severity", "medium")),
                    category=FindingCategory(item.get("category", "code_quality")),
                    message=item.get("message", ""),
                    suggestion=item.get("suggestion"),
                    tool="claude-ai",
                    rule_id=item.get("rule_id", "ai-review"),
                    aspect=aspect_name,  # Track which aspect found this
                )
                findings.append(finding)
            except Exception as e:
                print(f"Warning: Failed to parse finding: {e}")
                continue

        return findings

    def _extract_token_usage(self, stderr: str) -> dict[str, Any] | None:
        """
        Extract token usage from Claude Code stderr output.

        Args:
            stderr: stderr output from Claude Code

        Returns:
            Dict with token counts and cost, or None if not found
        """
        import re

        if not stderr:
            return None

        # Claude Code outputs usage like: "Tokens: 1234 input, 567 output"
        # or "tokens used: 1234 input, 567 output"
        match = re.search(
            r"tokens?[:\s]+(\d+)[^\d]+input[^\d]+(\d+)[^\d]+output", stderr, re.IGNORECASE
        )

        if match:
            input_tokens = int(match.group(1))
            output_tokens = int(match.group(2))

            # Claude 3.5 Sonnet pricing (as of 2025-01)
            input_cost = input_tokens * 0.000003  # $3 per 1M tokens
            output_cost = output_tokens * 0.000015  # $15 per 1M tokens
            total_cost = input_cost + output_cost

            return {"input": input_tokens, "output": output_tokens, "cost": total_cost}

        return None

    def run_review(
        self,
        aspect: dict[str, Any],
        pr_context: PRContext,
        shared_context: dict[str, Any] | None = None,
    ) -> list[Finding]:
        """
        Run a complete AI review for an aspect.

        Args:
            aspect: Review aspect configuration
            pr_context: PR context
            shared_context: Shared context from previous reviews

        Returns:
            List of findings with aspect tracking
        """
        try:
            # Build prompt
            prompt = self.build_review_prompt(aspect, pr_context, shared_context)

            # Execute review
            ai_response = self.run_claude_review(prompt)

            # Parse findings with aspect name
            aspect_name = aspect.get("name")
            findings = self.parse_ai_findings(ai_response, aspect_name)

            return findings

        except Exception as e:
            print(f"AI review failed for {aspect['name']}: {e}")
            return []
