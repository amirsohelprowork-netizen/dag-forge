"""Custom exception hierarchy for DAG Forge.

All exceptions inherit from DagForgeError for easy catching at the CLI boundary.
Each exception type maps to a specific error category with its own exit code.
"""

from __future__ import annotations


class DagForgeError(Exception):
    """Base exception for all DAG Forge errors."""

    exit_code: int = 1

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        self.message = message
        self.details = details or []
        super().__init__(message)


class ParseError(DagForgeError):
    """Raised when an input file cannot be parsed.

    Exit code 2 — indicates the input file is malformed or unreadable.
    """

    exit_code = 2

    def __init__(self, message: str, source: str = "", details: list[str] | None = None) -> None:
        self.source = source
        super().__init__(message, details)


class ValidationError(DagForgeError):
    """Raised when validation fails on parsed data.

    Exit code 1 — indicates the data is structurally valid but semantically incorrect.
    """

    exit_code = 1


class RenderError(DagForgeError):
    """Raised when output rendering fails.

    Exit code 3 — indicates an error during YAML/report generation.
    """

    exit_code = 3


class ConfigError(DagForgeError):
    """Raised when configuration is invalid or missing.

    Exit code 4 — indicates a problem with dagforge.toml or environment settings.
    """

    exit_code = 4


class PluginError(DagForgeError):
    """Raised when a plugin fails to load or register.

    Exit code 5 — indicates a problem with the plugin system.
    """

    exit_code = 5
