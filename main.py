#!/usr/bin/env python3
"""
Main entry point for AI Code Review System.

This is a wrapper that imports from the ai_review package.
For direct usage, install the package and use: ai-review --help
"""

from ai_review.cli import main

if __name__ == "__main__":
    main()
