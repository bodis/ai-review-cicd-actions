"""
Tests for ConfigManager.
"""

import pytest
import yaml

from ai_review.config_manager import ConfigManager, ConfigurationError


class TestConfigManager:
    """Test suite for ConfigManager."""

    def test_load_default_config(self):
        """Test loading default configuration."""
        manager = ConfigManager()
        config = manager.load_default_config()

        assert "review_aspects" in config
        assert "blocking_rules" in config
        assert isinstance(config["review_aspects"], list)

    def test_merge_configs(self):
        """Test merging multiple configurations."""
        manager = ConfigManager()

        base = {
            "review_aspects": [{"name": "test", "enabled": True}],
            "blocking_rules": {"block_on_critical": True},
        }

        override = {"blocking_rules": {"block_on_critical": False}, "new_key": "value"}

        merged = manager.merge_configs(base, override)

        assert merged["blocking_rules"]["block_on_critical"] is False
        assert merged["new_key"] == "value"
        assert merged["review_aspects"] == base["review_aspects"]

    def test_deep_merge(self):
        """Test deep merging of nested dictionaries."""
        manager = ConfigManager()

        base = {"level1": {"level2": {"key1": "value1", "key2": "value2"}}}

        override = {"level1": {"level2": {"key2": "new_value2", "key3": "value3"}}}

        merged = manager._deep_merge(base, override)

        assert merged["level1"]["level2"]["key1"] == "value1"
        assert merged["level1"]["level2"]["key2"] == "new_value2"
        assert merged["level1"]["level2"]["key3"] == "value3"

    def test_validate_config_valid(self):
        """Test validation of valid configuration."""
        manager = ConfigManager()
        config = manager.load_default_config()

        # Should not raise exception
        manager.validate_config(config)

    def test_validate_config_invalid(self):
        """Test validation of invalid configuration."""
        manager = ConfigManager()
        invalid_config = {
            "review_aspects": "not a list"  # Should be a list
        }

        with pytest.raises(ConfigurationError):
            manager.validate_config(invalid_config)

    def test_get_config_value(self):
        """Test getting configuration values by key."""
        manager = ConfigManager()
        manager.config = {"level1": {"level2": {"key": "value"}}}

        assert manager.get("level1.level2.key") == "value"
        assert manager.get("level1.level2.missing", "default") == "default"
        assert manager.get("missing.key", "default") == "default"

    def test_resolve_config_references(self, monkeypatch):
        """Test resolving environment variable references."""
        monkeypatch.setenv("TEST_VAR", "test_value")

        manager = ConfigManager()
        config = {
            "key1": "${TEST_VAR}",
            "key2": "prefix_${TEST_VAR}_suffix",
            "nested": {"key3": "${TEST_VAR}"},
        }

        resolved = manager.resolve_config_references(config)

        assert resolved["key1"] == "test_value"
        assert resolved["key2"] == "prefix_test_value_suffix"
        assert resolved["nested"]["key3"] == "test_value"


class TestConfigLoading:
    """Test configuration loading from various sources."""

    def test_load_project_config_file(self, tmp_path):
        """Test loading project config from file."""
        config_file = tmp_path / "config.yml"
        config_data = {"project_context": {"name": "Test Project"}}

        with open(config_file, "w") as f:
            yaml.dump(config_data, f)

        manager = ConfigManager(str(tmp_path))
        config = manager.load_project_config(str(config_file))

        assert config["project_context"]["name"] == "Test Project"

    def test_load_project_config_missing_file(self, tmp_path):
        """Test loading config from non-existent file."""
        manager = ConfigManager(str(tmp_path))
        config = manager.load_project_config("/nonexistent/config.yml")

        assert config == {}

    def test_load_all_configs(self, tmp_path):
        """Test loading and merging all configuration levels."""
        # Create project config
        project_config = tmp_path / "project-config.yml"
        with open(project_config, "w") as f:
            yaml.dump({"blocking_rules": {"block_on_high": True}}, f)

        manager = ConfigManager(str(tmp_path))
        config = manager.load_all_configs(project_config_path=str(project_config))

        # Should have default config merged with project config
        assert "review_aspects" in config  # From default
        assert config["blocking_rules"]["block_on_high"] is True  # From project
