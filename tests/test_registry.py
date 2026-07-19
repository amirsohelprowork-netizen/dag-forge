"""Tests for DAG Forge plugin registry."""

from __future__ import annotations

import pytest

from dagforge.core.exceptions import PluginError
from dagforge.core.registry import PluginRegistry
from dagforge.parsers.base import BaseParser
from dagforge.validators.base import BaseValidator
from dagforge.renderers.base import BaseRenderer


class TestPluginRegistry:
    """Tests for the plugin registry."""

    def setup_method(self):
        self.registry = PluginRegistry()

    def test_register_parser(self):
        @self.registry.parser("test")
        class TestParser(BaseParser):
            @property
            def supported_extensions(self):
                return {".test"}
            def parse(self, source):
                return None

        assert "test" in self.registry.available_parsers
        assert self.registry.get_parser("test") == TestParser

    def test_duplicate_parser_raises(self):
        @self.registry.parser("dup")
        class Parser1(BaseParser):
            @property
            def supported_extensions(self):
                return set()
            def parse(self, source):
                return None

        with pytest.raises(PluginError):
            @self.registry.parser("dup")
            class Parser2(BaseParser):
                @property
                def supported_extensions(self):
                    return set()
                def parse(self, source):
                    return None

    def test_get_unknown_parser_raises(self):
        with pytest.raises(PluginError):
            self.registry.get_parser("nonexistent")

    def test_register_validator(self):
        @self.registry.validator("test")
        class TestValidator(BaseValidator):
            def validate(self, dag):
                return None

        assert "test" in self.registry.available_validators

    def test_register_renderer(self):
        @self.registry.renderer("test")
        class TestRenderer(BaseRenderer):
            @property
            def file_extension(self):
                return ".test"
            def render(self, dag):
                return ""

        assert "test" in self.registry.available_renderers

    def test_summary(self):
        summary = self.registry.summary()
        assert "parsers" in summary
        assert "validators" in summary
        assert "renderers" in summary

    def test_global_registry_has_plugins(self):
        """Test that the global registry has built-in plugins registered."""
        from dagforge.core.registry import registry

        # Import modules to trigger registration
        import dagforge.parsers.excel_parser  # noqa: F401
        import dagforge.parsers.yaml_parser  # noqa: F401
        import dagforge.parsers.json_parser  # noqa: F401
        import dagforge.validators.graph_validator  # noqa: F401
        import dagforge.validators.operator_validator  # noqa: F401
        import dagforge.validators.schedule_validator  # noqa: F401
        import dagforge.validators.schema_validator  # noqa: F401
        import dagforge.renderers.dagfactory_renderer  # noqa: F401
        import dagforge.renderers.report_renderer  # noqa: F401

        assert "excel" in registry.available_parsers
        assert "yaml" in registry.available_parsers
        assert "json" in registry.available_parsers
        assert "graph" in registry.available_validators
        assert "operator" in registry.available_validators
        assert "schedule" in registry.available_validators
        assert "schema" in registry.available_validators
        assert "dagfactory" in registry.available_renderers
        assert "report" in registry.available_renderers
