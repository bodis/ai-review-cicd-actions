"""
Resource loader for bundled files.

Provides functions to load prompts and config files with fallback:
1. First check project directory (user override)
2. Then use bundled resources from package
"""

from importlib import resources
from pathlib import Path


def get_prompt(prompt_name: str, project_root: Path | None = None) -> str:
    """
    Load a prompt file, checking project directory first, then bundled.

    Args:
        prompt_name: Name of the prompt file (e.g., "security-review.md")
        project_root: Optional project root for user overrides

    Returns:
        Prompt content as string

    Raises:
        FileNotFoundError: If prompt not found in either location
    """
    # Normalize prompt name (remove leading path components if present)
    if "/" in prompt_name:
        prompt_name = prompt_name.split("/")[-1]

    # 1. Check project directory for user override
    if project_root:
        user_prompt_paths = [
            project_root / "prompts" / prompt_name,
            project_root / ".github" / "prompts" / prompt_name,
            project_root / ".gitlab" / "prompts" / prompt_name,
        ]
        for path in user_prompt_paths:
            if path.exists():
                return path.read_text(encoding="utf-8")

    # 2. Fall back to bundled prompt
    try:
        prompt_files = resources.files("ai_review.prompts")
        prompt_file = prompt_files.joinpath(prompt_name)
        return prompt_file.read_text(encoding="utf-8")
    except (FileNotFoundError, TypeError) as e:
        raise FileNotFoundError(
            f"Prompt '{prompt_name}' not found. "
            f"Checked: project/prompts/, .github/prompts/, .gitlab/prompts/, and bundled prompts."
        ) from e


def get_default_config() -> dict:
    """
    Load the default configuration from bundled resources.

    Returns:
        Default configuration dictionary
    """
    import yaml

    try:
        config_files = resources.files("ai_review.config")
        config_file = config_files.joinpath("default-config.yml")
        content = config_file.read_text(encoding="utf-8")
        return yaml.safe_load(content) or {}
    except (FileNotFoundError, TypeError):
        # Return minimal default if bundled config not found
        return {
            "review_aspects": [],
            "blocking_rules": {"block_on_critical": True},
        }


def get_project_config_paths(project_root: Path) -> list[Path]:
    """
    Get list of possible config file paths for a project.

    Supports both GitHub (.github/) and GitLab (.gitlab/) conventions.

    Args:
        project_root: Project root directory

    Returns:
        List of possible config file paths (in priority order)
    """
    return [
        # GitHub convention
        project_root / ".github" / "ai-review-config.yml",
        project_root / ".github" / "ai-review-config.yaml",
        # GitLab convention
        project_root / ".gitlab" / "ai-review-config.yml",
        project_root / ".gitlab" / "ai-review-config.yaml",
        # Root level (platform-agnostic)
        project_root / "ai-review-config.yml",
        project_root / "ai-review-config.yaml",
    ]


def find_project_config(project_root: Path) -> Path | None:
    """
    Find the first existing project config file.

    Args:
        project_root: Project root directory

    Returns:
        Path to config file if found, None otherwise
    """
    for config_path in get_project_config_paths(project_root):
        if config_path.exists():
            return config_path
    return None
