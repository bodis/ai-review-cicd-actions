#!/usr/bin/env python3
"""
Main entry point for AI Code Review System.
"""
import os
import sys
import json
import argparse
from pathlib import Path

from lib.config_manager import ConfigManager
from lib.orchestrator import ReviewOrchestrator
from lib.github_reporter import GitHubReporter


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

    # Validate environment
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        print("Error: GITHUB_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

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

            with open(output_path, 'w') as f:
                json.dump(results.to_dict(), f, indent=2)

            print(f"\nResults saved to: {output_path}")

        # Post to GitHub
        if not args.no_github_post:
            print("\nPosting results to GitHub...")
            reporter = GitHubReporter(github_token)
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
