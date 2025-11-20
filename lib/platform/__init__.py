"""
Platform abstraction layer for code review integrations.

This module provides a clean separation between different code review platforms
(GitHub, GitLab, etc.) through abstract interfaces.
"""

from .base import CodeReviewPlatform, PlatformConfig
from .factory import create_platform, detect_platform

__all__ = [
    "CodeReviewPlatform",
    "PlatformConfig",
    "create_platform",
    "detect_platform",
]
