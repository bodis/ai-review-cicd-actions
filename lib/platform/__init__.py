"""
Platform abstraction layer for code review integrations.

This module provides a clean separation between different code review platforms
(GitHub, GitLab, etc.) through abstract interfaces.
"""

from .base import CodeReviewPlatform, CommentDeduplicationConfig, PlatformConfig
from .factory import create_platform, create_reporter, detect_platform, load_platform_config

__all__ = [
    "CodeReviewPlatform",
    "CommentDeduplicationConfig",
    "PlatformConfig",
    "create_platform",
    "create_reporter",
    "detect_platform",
    "load_platform_config",
]
