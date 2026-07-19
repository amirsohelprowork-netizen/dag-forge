"""Abstract base class for output renderers.

Renderers take validated DagDefinitions and produce output in
various formats (YAML, reports, graphs, etc.).
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from pathlib import Path

from dagforge.core.models import DagDefinition


logger = logging.getLogger(__name__)


class BaseRenderer(ABC):
    """Abstract base class for all output renderers.

    Subclasses must implement:
        - render(dag): Render a single DagDefinition to string
        - file_extension: Property returning the output file extension

    Example:
        @registry.renderer("airflow_python")
        class AirflowPythonRenderer(BaseRenderer):
            @property
            def file_extension(self) -> str:
                return ".py"

            def render(self, dag: DagDefinition) -> str:
                ...
    """

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for output files (e.g., '.yaml')."""
        ...

    @abstractmethod
    def render(self, dag: DagDefinition) -> str:
        """Render a single DAG definition to string.

        Args:
            dag: The DagDefinition to render.

        Returns:
            String representation of the rendered output.

        Raises:
            RenderError: If rendering fails.
        """
        ...

    def render_to_file(self, dag: DagDefinition, output_dir: Path) -> Path:
        """Render a DAG and write to a file.

        Args:
            dag: The DagDefinition to render.
            output_dir: Directory to write the output file.

        Returns:
            Path to the created file.
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        output_path = output_dir / f"{dag.dag_id}{self.file_extension}"
        content = self.render(dag)
        output_path.write_text(content, encoding="utf-8")
        logger.info("Rendered %s -> %s", dag.dag_id, output_path)
        return output_path

    def render_batch(self, dags: list[DagDefinition], output_dir: Path) -> list[Path]:
        """Render multiple DAGs to files.

        Args:
            dags: List of DagDefinitions to render.
            output_dir: Directory to write the output files.

        Returns:
            List of paths to created files.
        """
        return [self.render_to_file(dag, output_dir) for dag in dags]
