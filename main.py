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
from lib.github_reporter import GitHubReporter
from lib.orchestrator import ReviewOrchestrator


def validate_environment() -> tuple[str, str]:
    """
    Validate all required environment variables and tools.

    Returns:
        Tuple of (github_token, anthropic_api_key)

    Raises:
        SystemExit: If validation fails
    """
    errors = []

    # Validate GitHub token
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        errors.append("❌ GITHUB_TOKEN environment variable is required")
    elif not (github_token.startswith('ghp_') or github_token.startswith('ghs_')):
        errors.append("❌ GITHUB_TOKEN appears invalid (should start with ghp_ or ghs_)")

    # Validate Anthropic API key
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    if not anthropic_key:
        errors.append(
            "❌ ANTHROPIC_API_KEY environment variable is required\n"
            "   Get your API key from: https://console.anthropic.com/\n"
            "   Add to GitHub Secrets: Settings → Secrets → ANTHROPIC_API_KEY"
        )
    elif not anthropic_key.startswith('sk-ant-'):
        errors.append("❌ ANTHROPIC_API_KEY appears invalid (should start with sk-ant-)")

    # Test Claude Code CLI availability
    try:
        result = subprocess.run(
            ['claude', '--version'],
            capture_output=True,
            timeout=5,
            check=False
        )
        if result.returncode == 0:
            version = result.stdout.decode('utf-8').strip()
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

    print("✅ Environment validation passed")
    return github_token, anthropic_key


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='AI-Driven Code Review System'
    )

    parser.add_argument(
        '--repo',
        required=True,
        help='Repository name (owner/repo)'
    )

    parser.add_argument(
        '--pr',
        type=int,
        required=True,
        help='Pull request number'
    )

    parser.add_argument(
        '--config',
        help='Path to project configuration file'
    )

    parser.add_argument(
        '--company-config',
        help='URL or path to company configuration'
    )

    parser.add_argument(
        '--output',
        help='Output file for results (JSON)'
    )

    parser.add_argument(
        '--no-github-post',
        action='store_true',
        help='Skip posting results to GitHub'
    )

    parser.add_argument(
        '--project-root',
        default='.',
        help='Project root directory'
    )

    args = parser.parse_args()

    # Validate environment (API keys and tools)
    github_token, anthropic_key = validate_environment()

    try:
        # Load configuration
        print("Loading configuration...")
        config_manager = ConfigManager(args.project_root)
        config = config_manager.load_all_configs(
            project_config_path=args.config,
            company_config_source=args.company_config
        )

        # Run review pipeline
        print(f"\nStarting review for {args.repo} PR #{args.pr}...")
        orchestrator = ReviewOrchestrator(config, args.project_root)
        results = orchestrator.run_review_pipeline(
            repo_name=args.repo,
            pr_number=args.pr,
            github_token=github_token
        )

        # Save results to file if requested
        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results.to_dict(), f, indent=2)

            print(f"\nResults saved to: {output_path}")

        # Post to GitHub
        if not args.no_github_post:
            print("\nPosting results to GitHub...")

            # Get model from config (optional)
            anthropic_model = config.get('anthropic', {}).get('model')

            reporter = GitHubReporter(
                github_token=github_token,
                anthropic_api_key=anthropic_key,
                metrics=results.metrics,
                anthropic_model=anthropic_model
            )
            reporter.post_review_results(
                repo_name=args.repo,
                pr_number=args.pr,
                results=results,
                config=config
            )
            print("✓ Results posted to GitHub")

        # Generate summary
        summary = orchestrator.generate_summary(results)
        print("\n" + "=" * 80)
        print(summary)
        print("=" * 80)

        for _ in [1, 2, 3, 4, 5, 10]:
            print('relevant logs')

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


if __name__ == '__main__':
    main()
