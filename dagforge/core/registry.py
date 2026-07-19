"""Plugin registry for DAG Forge.

Provides a decorator-based registration system for parsers, validators,
and renderers. This enables extensibility without modifying core code.

Usage:
    from dagforge.core.registry import registry

    @registry.parser("csv")
    class CsvParser(BaseParser):
        ...

    # Later, retrieve it:
    parser_cls = registry.get_parser("csv")
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, TypeVar

from dagforge.core.exceptions import PluginError

if TYPE_CHECKING:
    from dagforge.parsers.base import BaseParser
    from dagforge.renderers.base import BaseRenderer
    from dagforge.validators.base import BaseValidator
    from dagforge.policies.base import BasePolicy


logger = logging.getLogger(__name__)

T = TypeVar("T")


class PluginRegistry:
    """Central registry for all DAG Forge plugins.

    Plugins are registered by name and can be retrieved later.
    The registry supports three plugin types: parsers, validators, and renderers.
    """

    def __init__(self) -> None:
        self._parsers: dict[str, type[BaseParser]] = {}
        self._validators: dict[str, type[BaseValidator]] = {}
        self._renderers: dict[str, type[BaseRenderer]] = {}
        self._policies: dict[str, type[BasePolicy]] = {}

    # -----------------------------------------------------------------------
    # Parser registration
    # -----------------------------------------------------------------------

    def parser(self, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a parser plugin.

        Args:
            name: Unique name for this parser (e.g., 'excel', 'yaml', 'json').

        Example:
            @registry.parser("csv")
            class CsvParser(BaseParser):
                ...
        """
        def decorator(cls: type[BaseParser]) -> type[BaseParser]:
            if name in self._parsers:
                raise PluginError(
                    f"Parser '{name}' is already registered by {self._parsers[name].__name__}"
                )
            self._parsers[name] = cls
            logger.debug("Registered parser: %s -> %s", name, cls.__name__)
            return cls
        return decorator

    def get_parser(self, name: str) -> type[BaseParser]:
        """Retrieve a registered parser by name."""
        if name not in self._parsers:
            available = ", ".join(sorted(self._parsers.keys())) or "none"
            raise PluginError(
                f"No parser registered for '{name}'. Available parsers: {available}"
            )
        return self._parsers[name]

    @property
    def available_parsers(self) -> list[str]:
        """List all registered parser names."""
        return sorted(self._parsers.keys())

    # -----------------------------------------------------------------------
    # Validator registration
    # -----------------------------------------------------------------------

    def validator(self, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a validator plugin.

        Args:
            name: Unique name for this validator.

        Example:
            @registry.validator("no_manual_dags")
            class NoManualDagsValidator(BaseValidator):
                ...
        """
        def decorator(cls: type[BaseValidator]) -> type[BaseValidator]:
            if name in self._validators:
                raise PluginError(
                    f"Validator '{name}' is already registered by "
                    f"{self._validators[name].__name__}"
                )
            self._validators[name] = cls
            logger.debug("Registered validator: %s -> %s", name, cls.__name__)
            return cls
        return decorator

    def get_validator(self, name: str) -> type[BaseValidator]:
        """Retrieve a registered validator by name."""
        if name not in self._validators:
            available = ", ".join(sorted(self._validators.keys())) or "none"
            raise PluginError(
                f"No validator registered for '{name}'. Available: {available}"
            )
        return self._validators[name]

    @property
    def available_validators(self) -> list[str]:
        """List all registered validator names."""
        return sorted(self._validators.keys())

    # -----------------------------------------------------------------------
    # Renderer registration
    # -----------------------------------------------------------------------

    def renderer(self, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a renderer plugin.

        Args:
            name: Unique name for this renderer.

        Example:
            @registry.renderer("airflow_python")
            class AirflowPythonRenderer(BaseRenderer):
                ...
        """
        def decorator(cls: type[BaseRenderer]) -> type[BaseRenderer]:
            if name in self._renderers:
                raise PluginError(
                    f"Renderer '{name}' is already registered by "
                    f"{self._renderers[name].__name__}"
                )
            self._renderers[name] = cls
            logger.debug("Registered renderer: %s -> %s", name, cls.__name__)
            return cls
        return decorator

    def get_renderer(self, name: str) -> type[BaseRenderer]:
        """Retrieve a registered renderer by name."""
        if name not in self._renderers:
            available = ", ".join(sorted(self._renderers.keys())) or "none"
            raise PluginError(
                f"No renderer registered for '{name}'. Available: {available}"
            )
        return self._renderers[name]

    @property
    def available_renderers(self) -> list[str]:
        """List all registered renderer names."""
        return sorted(self._renderers.keys())

    # -----------------------------------------------------------------------
    # Policy registration
    # -----------------------------------------------------------------------

    def policy(self, name: str):  # type: ignore[no-untyped-def]
        """Decorator to register a policy plugin."""
        def decorator(cls: type[BasePolicy]) -> type[BasePolicy]:
            if name in self._policies:
                raise PluginError(
                    f"Policy '{name}' is already registered by {self._policies[name].__name__}"
                )
            self._policies[name] = cls
            logger.debug("Registered policy: %s -> %s", name, cls.__name__)
            return cls
        return decorator

    def get_policy(self, name: str) -> type[BasePolicy]:
        """Retrieve a registered policy by name."""
        if name not in self._policies:
            available = ", ".join(sorted(self._policies.keys())) or "none"
            raise PluginError(f"No policy registered for '{name}'. Available: {available}")
        return self._policies[name]

    @property
    def available_policies(self) -> list[str]:
        """List all registered policy names."""
        return sorted(self._policies.keys())

    # -----------------------------------------------------------------------
    # Introspection & Discovery
    # -----------------------------------------------------------------------

    def discover_plugins(self) -> None:
        """Discover plugins using importlib.metadata entry_points."""
        import sys
        if sys.version_info >= (3, 10):
            from importlib.metadata import entry_points
        else:
            try:
                from importlib_metadata import entry_points
            except ImportError:
                return

        for group in ["dagforge.parsers", "dagforge.validators", "dagforge.renderers", "dagforge.policies"]:
            try:
                eps = entry_points(group=group)
                for ep in eps:
                    ep.load()
                    logger.debug("Discovered plugin %s from %s", ep.name, ep.value)
            except Exception as e:
                logger.debug("Failed to discover plugins for group %s: %s", group, e)

    def summary(self) -> dict[str, list[str]]:
        """Return a summary of all registered plugins."""
        return {
            "parsers": self.available_parsers,
            "validators": self.available_validators,
            "renderers": self.available_renderers,
            "policies": self.available_policies,
        }


# Global singleton registry
registry = PluginRegistry()
