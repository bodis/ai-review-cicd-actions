#!/usr/bin/env python3
"""
Main entry point for AI Code Review System.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

from lib.config_manager import ConfigManager
from lib.orchestrator import ReviewOrchestrator
from lib.platform import create_platform, create_reporter, detect_platform, load_platform_config


def validate_environment(platform: str) -> tuple[str | None, str]:
    """
    Validate all required environment variables and tools.

    Args:
        platform: Platform type ('github' or 'gitlab')

    Returns:
        Tuple of (platform_token, anthropic_api_key)

    Raises:
        SystemExit: If validation fails
    """
    errors = []

    # Validate platform-specific token
    if platform == "github":
        platform_token = os.getenv("GITHUB_TOKEN")
        if not platform_token:
            errors.append("❌ GITHUB_TOKEN environment variable is required")
        elif not (platform_token.startswith("ghp_") or platform_token.startswith("ghs_")):
            errors.append("❌ GITHUB_TOKEN appears invalid (should start with ghp_ or ghs_)")
    else:  # gitlab
        # GitLab CI provides CI_JOB_TOKEN automatically, or use GITLAB_TOKEN
        platform_token = os.getenv("CI_JOB_TOKEN") or os.getenv("GITLAB_TOKEN")
        if not platform_token:
            errors.append(
                "❌ GitLab token required (CI_JOB_TOKEN or GITLAB_TOKEN environment variable)\n"
                "   CI_JOB_TOKEN is automatically provided in GitLab CI\n"
                "   For local testing, set GITLAB_TOKEN with 'api' scope"
            )

    # Validate Anthropic API key
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    if not anthropic_key:
        errors.append(
            "❌ ANTHROPIC_API_KEY environment variable is required\n"
            "   Get your API key from: https://console.anthropic.com/\n"
            f"   Add to {platform.title()} Secrets: ANTHROPIC_API_KEY"
        )
    elif not anthropic_key.startswith("sk-ant-"):
        errors.append("❌ ANTHROPIC_API_KEY appears invalid (should start with sk-ant-)")

    # Test Claude Code CLI availability
    try:
        result = subprocess.run(
            ["claude", "--version"], capture_output=True, timeout=5, check=False
        )
        if result.returncode == 0:
            version = result.stdout.decode("utf-8").strip()
            print(f"✅ Claude Code CLI found: {version}")
        else:
            errors.append("❌ Claude Code CLI is installed but not working")
    except FileNotFoundError:
        errors.append(
            "❌ Claude Code CLI not found in PATH\n"
            "   Install: curl -fsSL https://storage.googleapis.com/anthropic-files/claude-code/install.sh | bash\n"
            "   Or: npm install -g @anthropic-ai/claude-code"
        )
    except subprocess.TimeoutExpired:
        errors.append("❌ Claude Code CLI check timed out")

    # Print all errors
    if errors:
        print("=" * 80, file=sys.stderr)
        print("ENVIRONMENT VALIDATION FAILED", file=sys.stderr)
        print("=" * 80, file=sys.stderr)
        for error in errors:
            print(f"\n{error}", file=sys.stderr)
        print("\n" + "=" * 80, file=sys.stderr)
        sys.exit(1)

    print(f"✅ Environment validation passed ({platform})")
    return platform_token, anthropic_key


def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="AI-Driven Code Review System (GitHub & GitLab)")

    # Platform selection
    parser.add_argument(
        "--platform", choices=["github", "gitlab"], help="Platform (auto-detected if not specified)"
    )

    # Project identification (works for both platforms)
    parser.add_argument(
        "--repo",
        required=True,
        help="Project identifier (GitHub: owner/repo, GitLab: project-id or namespace/project)",
    )

    parser.add_argument("--pr", type=int, required=True, help="Pull/Merge request number")

    # Configuration
    parser.add_argument("--config", help="Path to project configuration file")

    parser.add_argument("--company-config", help="URL or path to company configuration")

    parser.add_argument("--output", help="Output file for results (JSON)")

    parser.add_argument("--no-post", action="store_true", help="Skip posting results to platform")

    parser.add_argument("--project-root", default=".", help="Project root directory")

    args = parser.parse_args()

    # Auto-detect or use specified platform
    platform = args.platform or detect_platform()
    print(f"Platform: {platform}")

    # Validate environment (API keys and tools)
    platform_token, anthropic_key = validate_environment(platform)

    try:
        # Load configuration
        print("\nLoading configuration...")
        config_manager = ConfigManager(args.project_root)
        config = config_manager.load_all_configs(
            project_config_path=args.config, company_config_source=args.company_config
        )

        # Create platform client
        print("Initializing platform client...")
        platform_client = create_platform(platform, platform_token)

        # Get MR/PR context
        print(f"\nFetching {platform} MR/PR #{args.pr}...")
        pr_context = platform_client.get_context(args.repo, args.pr)

        print(f"Title: {pr_context.title}")
        print(f"Changed files: {len(pr_context.changed_files)}")
        print(f"Languages: {', '.join(pr_context.detected_languages)}")
        print(f"Change types: {', '.join([ct.value for ct in pr_context.change_types])}")

        # Run review pipeline
        print("\nRunning review pipeline...")
        orchestrator = ReviewOrchestrator(config, args.project_root)
        results = orchestrator.run_review_pipeline_with_context(pr_context)

        # Save results to file if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(results.to_dict(), f, indent=2)

            print(f"\nResults saved to: {output_path}")

        # Post to platform
        if not args.no_post:
            # Get model from config (optional)
            anthropic_model = config.get("anthropic", {}).get("model")

            # Load platform config
            platform_config = load_platform_config(config)

            # Create reporter
            reporter = create_reporter(
                platform_client, anthropic_key, results.metrics, anthropic_model
            )

            # Post results
            reporter.post_review_results(args.repo, args.pr, results, platform_config)
            print(f"✓ Results posted to {platform}")

        # Generate summary
        summary = orchestrator.generate_summary(results)
        print("\n" + "=" * 80)
        print(summary)
        print("=" * 80)

        for _ in [1, 2, 3, 4, 5, 10]:
            print("relevant logs")

        # Exit with error code if blocking
        if results.should_block:
            print(f"\n❌ Review BLOCKED: {results.blocking_reason}")
            sys.exit(1)
        else:
            print("\n✅ Review PASSED")
            sys.exit(0)

    except Exception as e:
        print(f"\nError: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
