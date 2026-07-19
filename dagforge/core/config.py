"""Configuration management for DAG Forge.

Provides hierarchical configuration with sensible defaults that can be
overridden via dagforge.toml, environment variables, or CLI arguments.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


logger = logging.getLogger(__name__)


class ForgeConfig(BaseModel):
    """Global configuration for a DAG Forge session.

    Configuration precedence (highest to lowest):
    1. CLI arguments
    2. Environment variables (DAGFORGE_*)
    3. dagforge.toml in working directory
    4. Default values
    """

    # Input/Output paths
    input_dir: Path = Field(
        default=Path("input_files"),
        description="Directory containing input files",
    )
    output_dir: Path = Field(
        default=Path("output_yamls"),
        description="Directory for generated YAML output",
    )

    # Default DAG arguments
    default_owner: str = Field(
        default="airflow",
        description="Default owner for all DAGs",
    )
    default_start_date: str = Field(
        default="2024-01-01",
        description="Default start date for all DAGs",
    )
    default_catchup: bool = Field(
        default=False,
        description="Default catchup setting for all DAGs",
    )

    # Processing options
    strict_mode: bool = Field(
        default=False,
        description="Treat warnings as errors",
    )
    verbose: bool = Field(
        default=False,
        description="Enable verbose output",
    )

    # Phase 2 Features
    templates_dirs: list[str] = Field(
        default_factory=list,
        description="List of paths to custom template directories",
    )
    policies: dict[str, Any] = Field(
        default_factory=dict,
        description="Policy engine configuration",
    )
    environments: dict[str, Any] = Field(
        default_factory=dict,
        description="Environment-specific overlays (dev, prod, etc.)",
    )

    @property
    def default_args(self) -> dict[str, Any]:
        """Build the default_args dict from config values."""
        return {
            "owner": self.default_owner,
            "start_date": self.default_start_date,
        }

    @classmethod
    def load(cls, config_path: Path | None = None) -> ForgeConfig:
        """Load configuration from file and environment.

        Args:
            config_path: Optional path to a dagforge.toml file.
                         If None, looks in the current directory.

        Returns:
            Resolved ForgeConfig instance.
        """
        config_data: dict[str, Any] = {}

        # Try to load from dagforge.toml
        if config_path is None:
            config_path = Path("dagforge.toml")

        if config_path.exists():
            logger.info("Loading config from %s", config_path)
            try:
                import tomllib
            except ImportError:
                import tomli as tomllib  # type: ignore[no-redef]

            with open(config_path, "rb") as f:
                toml_data = tomllib.load(f)
                config_data.update(toml_data.get("dagforge", {}))

        return cls(**config_data)
