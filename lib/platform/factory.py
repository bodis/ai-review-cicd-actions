"""
Platform factory - Creates the appropriate platform implementation.

Handles platform detection and instantiation of the correct platform client.
"""

import os
from typing import Literal

from .base import CodeReviewPlatform, PlatformConfig, PlatformReporter

PlatformType = Literal["github", "gitlab"]


def detect_platform() -> PlatformType:
    """
    Auto-detect which platform we're running on.

    Returns:
        Platform type ('github' or 'gitlab')
    """
    # Check for GitLab CI environment
    if os.getenv("GITLAB_CI"):
        return "gitlab"

    # Check for GitHub Actions environment
    if os.getenv("GITHUB_ACTIONS"):
        return "github"

    # Default to GitHub (for local development)
    return "github"


def create_platform(
    platform_type: PlatformType | None = None, token: str | None = None
) -> CodeReviewPlatform:
    """
    Create platform implementation.

    Args:
        platform_type: Platform type ('github', 'gitlab', or None for auto-detect)
        token: API token (if None, uses environment variables)

    Returns:
        Platform implementation instance

    Raises:
        ValueError: If platform type is unsupported
    """
    # Auto-detect if not specified
    if platform_type is None:
        platform_type = detect_platform()

    print(f"Creating platform client: {platform_type}")

    # Import and instantiate appropriate platform
    if platform_type == "github":
        from .github_platform import GitHubPlatform

        return GitHubPlatform(token)

    elif platform_type == "gitlab":
        from .gitlab_platform import GitLabPlatform

        return GitLabPlatform(token)

    else:
        raise ValueError(f"Unsupported platform: {platform_type}")


def create_reporter(
    platform: CodeReviewPlatform,
    anthropic_api_key: str | None = None,
    metrics: any = None,
    anthropic_model: str | None = None,
) -> PlatformReporter:
    """
    Create platform reporter.

    Args:
        platform: Platform implementation
        anthropic_api_key: Anthropic API key for AI comment generation
        metrics: Metrics object
        anthropic_model: Claude model to use

    Returns:
        Platform reporter instance
    """
    # Import appropriate reporter based on platform type
    platform_name = platform.get_platform_name().lower()

    if platform_name == "github":
        from .github_platform import GitHubReporter

        return GitHubReporter(platform, anthropic_api_key, metrics, anthropic_model)

    elif platform_name == "gitlab":
        from .gitlab_platform import GitLabReporter

        return GitLabReporter(platform, anthropic_api_key, metrics, anthropic_model)

    else:
        raise ValueError(f"No reporter implementation for platform: {platform_name}")


def load_platform_config(config: dict) -> PlatformConfig:
    """
    Load platform configuration from config dict.

    Args:
        config: Full configuration dictionary

    Returns:
        PlatformConfig instance
    """
    # Try platform-specific config first, fall back to 'github' key for backwards compatibility
    platform_type = detect_platform()
    platform_config = config.get(platform_type, config.get("github", {}))

    return PlatformConfig(
        post_summary_comment=platform_config.get("post_summary_comment", True),
        post_inline_comments=platform_config.get("post_inline_comments", True),
        inline_comment_severity_threshold=platform_config.get(
            "inline_comment_severity_threshold", "high"
        ),
        update_status_check=platform_config.get("update_status_check", True),
        extras=platform_config.get("extras"),
    )
