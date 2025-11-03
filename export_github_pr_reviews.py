#!/usr/bin/env python3
"""
Export GitHub PR reviews to JSON/YAML for analysis.

Usage:
    # Auto-detect repo from git remote
    python export_github_pr_reviews.py --pr 123

    # Or specify repo explicitly
    python export_github_pr_reviews.py --repo owner/repo --pr 123 --format json
    python export_github_pr_reviews.py --repo owner/repo --pr 123 --format yaml
"""
import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

try:
    from github import Github, Auth
except ImportError:
    print("Error: PyGithub not installed. Run: pip install PyGithub")
    sys.exit(1)

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False

try:
    from dotenv import load_dotenv
    HAS_DOTENV = True
except ImportError:
    HAS_DOTENV = False


def load_env_file():
    """Load .env file if it exists and python-dotenv is available."""
    if not HAS_DOTENV:
        return

    # Check for .env in current directory
    env_file = Path('.env')
    if env_file.exists():
        load_dotenv(env_file)
        print("📄 Loaded .env file")


def get_github_repo_from_git() -> str | None:
    """
    Extract GitHub repo name (owner/repo) from git remote.

    Returns:
        Repo name in format "owner/repo" or None if not found
    """
    try:
        # Get git remote URL
        result = subprocess.run(
            ['git', 'remote', 'get-url', 'origin'],
            capture_output=True,
            text=True,
            check=True
        )
        remote_url = result.stdout.strip()

        # Parse different GitHub URL formats
        # SSH: git@github.com:owner/repo.git
        # HTTPS: https://github.com/owner/repo.git

        # Try SSH format
        ssh_match = re.match(r'git@github\.com:(.+)/(.+?)(?:\.git)?$', remote_url)
        if ssh_match:
            owner, repo = ssh_match.groups()
            return f"{owner}/{repo}"

        # Try HTTPS format
        https_match = re.match(r'https://github\.com/(.+)/(.+?)(?:\.git)?$', remote_url)
        if https_match:
            owner, repo = https_match.groups()
            return f"{owner}/{repo}"

        return None

    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def export_pr_reviews(repo_name: str, pr_number: int, github_token: str | None = None) -> dict:
    """
    Export ONLY unresolved/open issues and comments from a PR.

    Focuses on actionable items - skips resolved threads, commits, and file diffs.

    Args:
        repo_name: Repository name (owner/repo)
        pr_number: Pull request number
        github_token: GitHub token (optional for public repos, uses GITHUB_TOKEN env var if not provided)

    Returns:
        Dictionary with open/unresolved PR issues only
    """
    token = github_token or os.getenv('GITHUB_TOKEN')

    # Create GitHub client (works without token for public repos, but with lower rate limits)
    if token:
        auth = Auth.Token(token)
        github = Github(auth=auth)
        print("🔑 Using authenticated access (higher rate limits)")
    else:
        github = Github()
        print("⚠️  Using unauthenticated access (60 requests/hour limit)")
        print("   Set GITHUB_TOKEN for higher rate limits (5000 requests/hour)")

    # Track API calls
    api_calls = 0

    repo = github.get_repo(repo_name)
    api_calls += 1  # get_repo

    pr = repo.get_pull(pr_number)
    api_calls += 1  # get_pull

    # Minimal PR metadata
    export_data = {
        "metadata": {
            "exported_at": datetime.now().astimezone().isoformat(),
            "repository": repo_name,
            "pr_number": pr_number,
        },
        "pull_request": {
            "title": pr.title,
            "state": pr.state,
            "url": pr.html_url,
        },
        "unresolved_review_comments": [],
        "general_comments": [],
    }

    # Get ONLY unresolved review comments (inline code comments)
    print(f"Fetching unresolved review comments for PR #{pr_number}...")
    unresolved_count = 0
    resolved_count = 0

    api_calls += 1  # get_review_comments (paginated)
    for comment in pr.get_review_comments():
        # Check if comment thread is resolved
        # In GitHub API, if a comment has no 'in_reply_to_id', it's a top-level comment
        # We check the conversation_id and whether it was resolved
        is_resolved = False

        # Try to get resolution status (may not be available in all API versions)
        try:
            # If comment has these attributes, it's been resolved
            if hasattr(comment, '_rawData'):
                raw_data = comment._rawData
                # Check if conversation is resolved or outdated
                if raw_data.get('pull_request_review_id') and raw_data.get('position') is None:
                    is_resolved = True  # Outdated/resolved
        except:
            pass  # Keep as unresolved if we can't determine

        if not is_resolved:
            export_data["unresolved_review_comments"].append({
                "id": comment.id,
                "user": comment.user.login if comment.user else "unknown",
                "body": comment.body,
                "path": comment.path,
                "line": comment.line,
                "created_at": comment.created_at.isoformat(),
                "url": comment.html_url,
            })
            unresolved_count += 1
        else:
            resolved_count += 1

    # Get general PR comments (issue comments)
    print("Fetching general comments...")
    api_calls += 1  # get_issue_comments (paginated)
    for comment in pr.get_issue_comments():
        export_data["general_comments"].append({
            "id": comment.id,
            "user": comment.user.login if comment.user else "unknown",
            "body": comment.body,
            "created_at": comment.created_at.isoformat(),
            "url": comment.html_url,
        })

    # Get rate limit info
    try:
        rate_limit = github.get_rate_limit()
        remaining = rate_limit.core.remaining if hasattr(rate_limit, 'core') else rate_limit.rate.remaining
    except Exception:
        remaining = "unknown"

    print(f"\n✅ Exported PR #{pr_number} open items:")
    print(f"   - {unresolved_count} unresolved review comments")
    print(f"   - {len(export_data['general_comments'])} general comments")
    print(f"   - Skipped: {resolved_count} resolved threads")
    print("\n📊 API Usage:")
    print(f"   - API calls made: ~{api_calls}")
    print(f"   - Rate limit remaining: {remaining}")

    # Add API stats to export
    export_data["metadata"]["api_calls"] = api_calls
    export_data["metadata"]["rate_limit_remaining"] = remaining

    return export_data


def main():
    # Load .env file first (before parsing args)
    load_env_file()

    parser = argparse.ArgumentParser(
        description="Export GitHub PR reviews to JSON/YAML",
        epilog="If --repo is not specified, attempts to auto-detect from git remote. "
               "Loads GITHUB_TOKEN from .env file if present."
    )
    parser.add_argument(
        "--repo",
        help="Repository name (owner/repo). Auto-detected from git remote if not specified."
    )
    parser.add_argument(
        "--pr",
        type=int,
        required=True,
        help="Pull request number"
    )
    parser.add_argument(
        "--format",
        choices=["json", "yaml"],
        default="json",
        help="Output format (default: json)"
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file (default: pr-{number}-reviews.{format})"
    )
    parser.add_argument(
        "--token",
        help="GitHub token (default: GITHUB_TOKEN from .env or env var)"
    )
    parser.add_argument(
        "--pretty",
        action="store_true",
        help="Pretty-print JSON output"
    )

    args = parser.parse_args()

    # Auto-detect repo if not specified
    repo_name = args.repo
    if not repo_name:
        print("🔍 Auto-detecting repository from git remote...")
        repo_name = get_github_repo_from_git()
        if not repo_name:
            print("Error: Could not auto-detect repository from git remote")
            print("Please specify --repo owner/repo")
            sys.exit(1)
        print(f"   Detected: {repo_name}")

    # Check YAML support
    if args.format == "yaml" and not HAS_YAML:
        print("Error: PyYAML not installed. Run: pip install pyyaml")
        print("Or use --format json instead")
        sys.exit(1)

    # Export data
    try:
        data = export_pr_reviews(repo_name, args.pr, args.token)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

    # Determine output file
    if args.output:
        output_file = args.output
    else:
        output_file = f"pr-{args.pr}-reviews.{args.format}"

    # Write to file
    print(f"\n📝 Writing to {output_file}...")
    with open(output_file, 'w', encoding='utf-8') as f:
        if args.format == "json":
            if args.pretty:
                json.dump(data, f, indent=2, ensure_ascii=False)
            else:
                json.dump(data, f, ensure_ascii=False)
        else:  # yaml
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)

    print(f"✅ Successfully exported to {output_file}")


if __name__ == "__main__":
    main()
