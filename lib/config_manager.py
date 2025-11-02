"""
Configuration manager for multi-level configuration loading and merging.
"""
import json
import os
from pathlib import Path
from typing import Any

import requests
import yaml
from jsonschema import ValidationError, validate


class ConfigurationError(Exception):
    """Raised when configuration is invalid."""
    pass


class ConfigManager:
    """Manages loading and merging of multi-level configurations."""

    CONFIG_SCHEMA = {
        "type": "object",
        "properties": {
            "review_aspects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "enabled": {"type": "boolean"},
                        "type": {"type": "string", "enum": ["classical", "ai"]},
                        "tools": {"type": "array", "items": {"type": "string"}},
                        "prompt_file": {"type": "string"},
                        "parallel": {"type": "boolean"}
                    },
                    "required": ["name", "enabled", "type"]
                }
            },
            "blocking_rules": {
                "type": "object",
                "properties": {
                    "block_on_critical": {"type": "boolean"},
                    "block_on_high": {"type": "boolean"},
                    "max_findings": {
                        "type": "object",
                        "properties": {
                            "critical": {"type": "integer"},
                            "high": {"type": "integer"},
                            "medium": {"type": "integer"}
                        }
                    }
                }
            },
            "company_policies_source": {"type": "string"},
            "project_context": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "architecture": {"type": "string"},
                    "critical_paths": {"type": "array", "items": {"type": "string"}}
                }
            },
            "project_constraints": {"type": "array", "items": {"type": "string"}},
            "custom_rules": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string"},
                        "message": {"type": "string"},
                        "severity": {"type": "string"}
                    }
                }
            }
        }
    }

    DEFAULT_CONFIG = {
        "review_aspects": [
            {
                "name": "python_static_analysis",
                "enabled": True,
                "type": "classical",
                "tools": ["ruff", "pylint", "bandit", "mypy"],
                "parallel": True
            },
            {
                "name": "javascript_static_analysis",
                "enabled": True,
                "type": "classical",
                "tools": ["eslint", "prettier"],
                "parallel": True
            },
            {
                "name": "security_review",
                "enabled": True,
                "type": "ai",
                "prompt_file": "prompts/security-review.md",
                "parallel": False
            },
            {
                "name": "architecture_review",
                "enabled": True,
                "type": "ai",
                "prompt_file": "prompts/architecture-review.md",
                "parallel": False
            },
            {
                "name": "code_quality_review",
                "enabled": True,
                "type": "ai",
                "prompt_file": "prompts/base-review.md",
                "parallel": False
            }
        ],
        "blocking_rules": {
            "block_on_critical": True,
            "block_on_high": False,
            "max_findings": {
                "critical": 0,
                "high": 5,
                "medium": 20
            }
        },
        "github": {
            "post_summary_comment": True,
            "post_inline_comments": True,
            "update_status_check": True,
            "inline_comment_severity_threshold": "high"
        }
    }

    def __init__(self, project_root: str = "."):
        """Initialize configuration manager."""
        self.project_root = Path(project_root)
        self.config: dict[str, Any] = {}

    def load_default_config(self) -> dict[str, Any]:
        """Load built-in default configuration."""
        return self.DEFAULT_CONFIG.copy()

    def load_project_config(self, path: str | None = None) -> dict[str, Any]:
        """
        Load project-level configuration from repository.

        Args:
            path: Path to config file. If None, looks for standard locations.

        Returns:
            Project configuration dictionary.
        """
        if path is None:
            # Try standard locations
            possible_paths = [
                self.project_root / ".github" / "ai-review-config.yml",
                self.project_root / ".github" / "ai-review-config.yaml",
                self.project_root / "ai-review-config.yml"
            ]

            for config_path in possible_paths:
                if config_path.exists():
                    path = str(config_path)
                    break

        if path is None or not Path(path).exists():
            return {}

        try:
            with open(path, encoding='utf-8') as f:
                if path.endswith('.json'):
                    return json.load(f)
                return yaml.safe_load(f) or {}
        except Exception as e:
            raise ConfigurationError(f"Failed to load project config from {path}: {e}") from e

    def load_company_config(self, source: str | None = None) -> dict[str, Any]:
        """
        Load company-level configuration from external source.

        Args:
            source: Source URL or path for company config.
                   Supports: github://, https://, file://

        Returns:
            Company configuration dictionary.
        """
        if not source:
            return {}

        try:
            if source.startswith('github://'):
                return self._fetch_from_github(source)
            elif source.startswith('http://') or source.startswith('https://'):
                return self._fetch_from_url(source)
            elif source.startswith('file://'):
                file_path = source.replace('file://', '')
                with open(file_path, encoding='utf-8') as f:
                    return yaml.safe_load(f) or {}
            # Assume it's a file path
            with open(source, encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"Warning: Failed to load company config from {source}: {e}")
            return {}

    def _fetch_from_github(self, source: str) -> dict[str, Any]:
        """
        Fetch configuration from GitHub.

        Format: github://org/repo/path/to/file.yml[@branch]
        """
        # Parse github:// URL
        parts = source.replace('github://', '').split('/')
        if len(parts) < 3:
            raise ConfigurationError(f"Invalid GitHub URL format: {source}")

        org = parts[0]
        repo = parts[1]
        file_path = '/'.join(parts[2:])

        # Check for branch specification
        branch = 'main'
        if '@' in file_path:
            file_path, branch = file_path.rsplit('@', 1)

        # Construct raw GitHub URL
        url = f"https://raw.githubusercontent.com/{org}/{repo}/{branch}/{file_path}"
        return self._fetch_from_url(url)

    def _fetch_from_url(self, url: str) -> dict[str, Any]:
        """Fetch configuration from HTTP(S) URL."""
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        content = response.text
        if url.endswith('.json'):
            return json.loads(content)
        else:
            return yaml.safe_load(content) or {}

    def merge_configs(self, *configs: dict[str, Any]) -> dict[str, Any]:
        """
        Merge multiple configuration dictionaries with proper precedence.
        Later configs override earlier ones.

        Args:
            *configs: Configuration dictionaries to merge.

        Returns:
            Merged configuration.
        """
        merged = {}

        for config in configs:
            merged = self._deep_merge(merged, config)

        return merged

    def _deep_merge(self, base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
        """Deep merge two dictionaries."""
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._deep_merge(result[key], value)
            else:
                result[key] = value

        return result

    def validate_config(self, config: dict[str, Any]) -> None:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate.

        Raises:
            ConfigurationError: If configuration is invalid.
        """
        try:
            validate(instance=config, schema=self.CONFIG_SCHEMA)
        except ValidationError as e:
            raise ConfigurationError(f"Configuration validation failed: {e.message}") from e

    def load_all_configs(
        self,
        project_config_path: str | None = None,
        company_config_source: str | None = None
    ) -> dict[str, Any]:
        """
        Load and merge all configuration levels.

        Args:
            project_config_path: Path to project config.
            company_config_source: Source for company config.

        Returns:
            Final merged configuration.
        """
        # Load all levels
        default_config = self.load_default_config()
        company_config = self.load_company_config(company_config_source)
        project_config = self.load_project_config(project_config_path)

        # Merge with proper precedence: default < company < project
        self.config = self.merge_configs(default_config, company_config, project_config)

        # Validate final config
        try:
            self.validate_config(self.config)
        except ConfigurationError as e:
            print(f"Warning: Configuration validation failed: {e}")
            # Use defaults for safety
            self.config = default_config

        return self.config

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by key."""
        keys = key.split('.')
        value = self.config

        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default

        return value if value is not None else default

    def resolve_config_references(self, config: dict[str, Any]) -> dict[str, Any]:
        """
        Resolve variable references in configuration.
        Supports ${VAR_NAME} syntax for environment variables.

        Args:
            config: Configuration with potential references.

        Returns:
            Configuration with resolved references.
        """
        resolved = {}

        for key, value in config.items():
            if isinstance(value, str):
                # Resolve environment variable references
                if '${' in value:
                    import re
                    matches = re.findall(r'\$\{([^}]+)\}', value)
                    for match in matches:
                        env_value = os.getenv(match, '')
                        value = value.replace(f'${{{match}}}', env_value)
                resolved[key] = value
            elif isinstance(value, dict):
                resolved[key] = self.resolve_config_references(value)
            elif isinstance(value, list):
                resolved[key] = [
                    self.resolve_config_references(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                resolved[key] = value

        return resolved
